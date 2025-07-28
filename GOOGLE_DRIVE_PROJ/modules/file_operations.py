#!/usr/bin/env python3
"""
Google Drive Shell - File Operations Module
从google_drive_shell.py重构而来的file_operations模块
"""

import os
import sys
import json
import time
import hashlib
import warnings
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
import platform
import psutil
from typing import Dict
from ..google_drive_api import GoogleDriveService

class FileOperations:
    """Google Drive Shell File Operations"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def cmd_upload_folder(self, folder_path, target_path=".", keep_zip=False):
        """
        上传文件夹到Google Drive
        
        流程：打包 -> 上传zip文件（作为普通文件）
        
        Args:
            folder_path (str): 要上传的文件夹路径
            target_path (str): 目标路径（相对于当前shell路径）
            keep_zip (bool): 是否保留本地zip文件（远端总是保留zip文件）
            
        Returns:
            dict: 上传结果
        """
        try:
            print(f"🚀 开始上传文件夹: {folder_path}")
            
            # 步骤1: 打包文件夹
            print("📦 步骤1: 打包文件夹...")
            zip_result = self._zip_folder(folder_path)
            if not zip_result["success"]:
                return {"success": False, "error": f"打包失败: {zip_result['error']}"}
            
            zip_path = zip_result["zip_path"]
            zip_filename = Path(zip_path).name
            
            try:
                # 步骤2: 上传zip文件并自动解压
                print("📤 步骤2: 上传zip文件并自动解压...")
                
                # 传递文件夹上传的特殊参数
                upload_result = self.cmd_upload([zip_path], target_path, force=False, 
                                              folder_upload_info={
                                                  "is_folder_upload": True,
                                                  "zip_filename": zip_filename,
                                                  "keep_zip": keep_zip
                                              })
                if not upload_result["success"]:
                    return {"success": False, "error": f"上传失败: {upload_result['error']}"}
                
                # 成功完成
                folder_name = Path(folder_path).name
                print(f"Folder upload successful: {folder_name}")
                
                return {
                    "success": True,
                    "message": f"成功上传文件夹: {folder_name}",
                    "original_folder": folder_path,
                    "zip_uploaded": zip_filename,
                    "zip_kept": keep_zip,
                    "target_path": target_path,
                    "zip_size": zip_result.get("zip_size", 0),
                    "method": "zip_upload_and_extract",
                    "upload_details": upload_result
                }
                
            finally:
                # 根据keep_zip参数决定是否清理本地临时zip文件
                if not keep_zip:
                    try:
                        if Path(zip_path).exists():
                            Path(zip_path).unlink()
                            print(f"🧹 已清理本地临时文件: {zip_filename}")
                    except Exception as e:
                        print(f"⚠️ 清理临时文件失败: {e}")
                else:
                    print(f"📁 保留本地zip文件: {zip_path}")
                    
        except Exception as e:
            # 如果出错，也要清理临时文件
            try:
                if 'zip_path' in locals() and Path(zip_path).exists():
                    Path(zip_path).unlink()
                    print(f"🧹 已清理本地临时文件: {zip_path}")
            except:
                pass
            return {"success": False, "error": f"文件夹上传过程出错: {e}"}

    def cmd_upload(self, source_files, target_path=".", force=False, folder_upload_info=None, remove_local=False):
        """
        GDS UPLOAD 命令实现
        
        Args:
            source_files (list): 要上传的源文件路径列表
            target_path (str): 目标路径（相对于当前 shell 路径）
            force (bool): 是否强制覆盖现有文件
            
        Returns:
            dict: 上传结果
        """
        try:
            # 0. 检查Google Drive Desktop是否运行
            if not self.ensure_google_drive_desktop_running():
                return {"success": False, "error": "用户取消上传操作"}
            
            # 1. 验证输入参数
            if not source_files:
                return {"success": False, "error": "请指定要上传的文件"}
            
            if isinstance(source_files, str):
                source_files = [source_files]
            
            # 1.5. 检查大文件并分离处理
            normal_files, large_files = self._check_large_files(source_files)
            
            # 处理大文件
            if large_files:
                large_file_result = self._handle_large_files(large_files, target_path, current_shell)
                if not large_file_result["success"]:
                    return large_file_result
            
            # 如果没有正常大小的文件需要处理，但有大文件，需要等待手动上传完成
            if not normal_files:
                if large_files:
                    # 等待大文件手动上传完成
                    large_file_names = [Path(f["path"]).name for f in large_files]
                    print(f"\n⏳ 等待手动上传完成...")
                    
                    # 创建虚拟file_moves用于计算超时时间
                    virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                    sync_result = self.wait_for_file_sync(large_file_names, virtual_file_moves)
                    
                    if sync_result["success"]:
                        
                        return {
                            "success": True,
                            "message": f"✅ Large files manual upload completed: {len(large_files)} files",
                            "large_files_handled": True,
                            "sync_time": sync_result.get("sync_time", 0)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Manual upload failed: {sync_result.get('error', 'Unknown error')}",
                            "large_files_handled": True
                        }
                else:
                    return {"success": False, "error": "Cannot find valid files"}
            
            # 继续处理正常大小的文件
            source_files = normal_files
            
            # 2. 获取当前 shell
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            # 3. 解析目标路径
            target_folder_id, target_display_path = self._resolve_target_path_for_upload(target_path, current_shell)
            if target_folder_id is None and self.drive_service:
                # 目标路径不存在，但这是正常的，我们会在远端创建它
                # 静默处理目标路径创建
                target_folder_id = None  # 标记为需要创建
                target_display_path = target_path
            elif not self.drive_service:
                print("⚠️ 警告: Google Drive API 服务未初始化，将使用模拟模式")
            
            # 3.5. 检查目标文件是否已存在，避免冲突（除非使用--force）
            overridden_files = []
            if not force:
                conflict_check_result = self._check_target_file_conflicts_before_move(source_files, target_path)
                if not conflict_check_result["success"]:
                    return conflict_check_result
            else:
                # Force模式：检查哪些文件会被覆盖，记录警告
                override_check_result = self._check_files_to_override(source_files, target_path)
                if override_check_result["success"] and override_check_result.get("overridden_files"):
                    overridden_files = override_check_result["overridden_files"]
                    for file_path in overridden_files:
                        print(f"⚠️ Warning: Overriding remote file {file_path}")
            
            # 4. 移动文件到 LOCAL_EQUIVALENT
            file_moves = []
            failed_moves = []
            
            for source_file in source_files:
                move_result = self.move_to_local_equivalent(source_file)
                if move_result["success"]:
                    file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "original_filename": move_result["original_filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"]
                    })
                    # 静默处理文件移动
                    if move_result["renamed"]:
                        print(f"   (已重命名避免冲突)")
                else:
                    failed_moves.append({
                        "file": source_file,
                        "error": move_result["error"]
                    })
                    print(f"❌ 文件移动失败: {source_file} - {move_result['error']}")
            
            if not file_moves:
                return {
                    "success": False,
                    "error": "所有文件移动失败",
                    "failed_moves": failed_moves
                }
            
            # 5. 检测网络连接
            network_result = self.check_network_connection()
            if not network_result["success"]:
                print(f"⚠️ 网络连接检测: {network_result['error']}")
                print("📱 将继续执行，但请确保网络连接正常")
            else:
                # 静默处理网络检查
                pass
            
            # 6. 等待文件同步到 DRIVE_EQUIVALENT
            expected_filenames = [fm.get("original_filename", fm["filename"]) for fm in file_moves]
            
            sync_result = self.wait_for_file_sync(expected_filenames, file_moves)
            
            if not sync_result["success"]:
                # 检查是否是小文件超时（文件总大小 < 10MB）
                total_size_mb = sum(
                    os.path.getsize(fm["new_path"]) / (1024 * 1024) 
                    for fm in file_moves 
                    if os.path.exists(fm["new_path"])
                )
                
                if total_size_mb < 10:  # 小文件超时，尝试重启Google Drive Desktop并重试
                    print(f"⚠️ 小文件上传同步超时，尝试重启Google Drive Desktop并重试...")
                    
                    # 重启Google Drive Desktop
                    restart_result = self._restart_google_drive_desktop()
                    if restart_result:
                        print("✅ Google Drive Desktop重启成功，开始重试上传...")
                        
                        # 重新计算超时时间并增加60秒
                        original_timeout = self.calculate_timeout_from_file_sizes(file_moves)
                        retry_timeout = original_timeout + 60  # 从+10秒增加到+60秒
                        print(f"🔄 重试超时时间: {retry_timeout}秒 (原{original_timeout}秒 + 60秒)")
                        
                        # 重试同步检测
                        retry_sync_result = self._wait_for_file_sync_with_timeout(expected_filenames, file_moves, retry_timeout)
                        
                        if retry_sync_result["success"]:
                            print("✅ 重试上传成功!")
                            sync_result = retry_sync_result
                        else:
                            return {
                                "success": False,
                                "error": f"小文件上传重试失败: {retry_sync_result.get('error', '未知错误')}",
                                "file_moves": file_moves,
                                "total_size_mb": total_size_mb,
                                "sync_time": retry_sync_result.get("sync_time", 0),
                                "retry_attempted": True,
                                "suggestion": "Google Drive Desktop重启后仍然失败，请检查网络连接或手动上传"
                            }
                    else:
                        return {
                            "success": False,
                            "error": f"小文件上传同步超时，且Google Drive Desktop重启失败",
                            "file_moves": file_moves,
                            "total_size_mb": total_size_mb,
                            "sync_time": sync_result.get("sync_time", 0),
                            "retry_attempted": False,
                            "suggestion": "请手动重启Google Drive Desktop后重试"
                        }
                
                print(f"⚠️ 文件同步检测: {sync_result['error']}")
                print("📱 将继续执行，但请手动确认文件已同步")
                # 在没有同步检测的情况下，假设文件已同步
                sync_result = {
                    "success": True,
                    "synced_files": expected_filenames,
                    "sync_time": 0,
                    "base_sync_time": 0
                }
            else:
                base_time = sync_result.get("base_sync_time", sync_result.get("sync_time", 0))
                # 静默处理文件同步完成
                sync_result["sync_time"] = base_time
            
            # 7. 静默验证文件同步状态
            self._verify_files_available(file_moves)
            
            # 8. 静默生成远端命令
            remote_command = self.generate_remote_commands(file_moves, target_path, folder_upload_info)
            
            # 7.5. 远端目录创建已经集成到generate_remote_commands中，无需额外处理
            
            # 8. 使用统一的远端命令执行接口
            context_info = {
                "expected_filenames": expected_filenames,
                "target_folder_id": target_folder_id,
                "target_path": target_path,
                "file_moves": file_moves
            }
            
            execution_result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="upload",
                context_info=context_info
            )
            
            # 如果执行失败，直接返回错误
            if not execution_result["success"]:
                return {
                    "success": False,
                    "error": execution_result["message"],
                    "remote_command": remote_command,
                    "execution_result": execution_result
                }
            
            # 执行成功，使用返回的验证结果
            verify_result = execution_result
            
            # 9. 上传和远端命令执行完成后，清理LOCAL_EQUIVALENT中的文件
            if verify_result["success"]:
                self._cleanup_local_equivalent_files(file_moves)
                
                # 如果指定了 --remove-local 选项，删除本地源文件
                if remove_local:
                    removed_files = []
                    failed_removals = []
                    for source_file in source_files:
                        try:
                            if os.path.exists(source_file):
                                os.unlink(source_file)
                                removed_files.append(source_file)
                        except Exception as e:
                            failed_removals.append({"file": source_file, "error": str(e)})
            
            result = {
                "success": verify_result["success"],
                "uploaded_files": verify_result.get("found_files", []),
                "failed_files": verify_result.get("missing_files", []) + [fm["file"] for fm in failed_moves],
                "target_path": target_display_path,
                "target_folder_id": target_folder_id,
                "total_attempted": len(source_files),
                "total_succeeded": len(verify_result.get("found_files", [])),
                "remote_command": remote_command,
                "file_moves": file_moves,
                "failed_moves": failed_moves,
                "sync_time": sync_result.get("sync_time", 0),
                "message": f"Upload completed: {len(verify_result.get('found_files', []))}/{len(source_files)} files" if verify_result["success"] else f"⚠️ Partially uploaded: {len(verify_result.get('found_files', []))}/{len(source_files)} files",
                "api_available": self.drive_service is not None
            }
            
            # 添加本地文件删除信息
            if remove_local and verify_result["success"]:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Upload error: {str(e)}"
            }

    def cmd_pwd(self):
        """显示当前路径"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            return {
                "success": True,
                "current_path": current_shell.get("current_path", "~"),
                "home_url": self.main_instance.HOME_URL,
                "shell_id": current_shell["id"],
                "shell_name": current_shell["name"]
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取当前路径时出错: {e}"}

    def cmd_ls(self, path=None, detailed=False, recursive=False, show_hidden=False):
        """列出目录内容，支持递归、详细模式和扩展信息模式"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if path is None or path == "." or path == "~":
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                display_path = current_shell.get("current_path", "~")
            else:
                target_folder_id, display_path = self.main_instance.resolve_path(path, current_shell)
                if not target_folder_id:
                    return {"success": False, "error": f"目录不存在: {path}"}
            
            if recursive:
                return self._ls_recursive(target_folder_id, display_path, detailed, show_hidden)
            else:
                return self._ls_single(target_folder_id, display_path, detailed, show_hidden)
                
        except Exception as e:
            return {"success": False, "error": f"执行ls命令时出错: {e}"}

    def _ls_recursive(self, root_folder_id, root_path, detailed, show_hidden=False):
        """递归列出目录内容"""
        try:
            all_items = []
            
            def scan_folder(folder_id, folder_path, depth=0):
                result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
                if not result['success']:
                    return
                
                files = result['files']
                
                # 添加网页链接
                for file in files:
                    file['url'] = self._generate_web_url(file)
                    file['path'] = folder_path
                    file['depth'] = depth
                    all_items.append(file)
                    
                    # 如果是文件夹，递归扫描
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        sub_path = f"{folder_path}/{file['name']}" if folder_path != "~" else f"~/{file['name']}"
                        scan_folder(file['id'], sub_path, depth + 1)
            
            # 开始递归扫描
            scan_folder(root_folder_id, root_path)
            
            # 按路径和名称排序
            all_items.sort(key=lambda x: (x['path'], x['name'].lower()))
            
            # 分离文件夹和文件
            folders = [f for f in all_items if f['mimeType'] == 'application/vnd.google-apps.folder']
            other_files = [f for f in all_items if f['mimeType'] != 'application/vnd.google-apps.folder']
            
            if detailed:
                # 详细模式：返回嵌套的树形结构
                nested_structure = self._build_nested_structure(all_items, root_path)
                
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "folder_url": self._generate_folder_url(root_folder_id),
                    "files": nested_structure["files"],
                    "folders": nested_structure["folders"],  # 每个文件夹包含自己的files和folders
                    "count": len(all_items),
                    "mode": "recursive_detailed"
                }
            else:
                # 简单模式：只返回基本信息
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "files": other_files,
                    "folders": folders,
                    "all_items": all_items,
                    "count": len(all_items),
                    "mode": "recursive_bash"
                }
                
        except Exception as e:
            return {"success": False, "error": f"递归列出目录时出错: {e}"}

    def _build_nested_structure(self, all_items, root_path):
        """构建嵌套的文件夹结构，每个文件夹包含自己的files和folders"""
        try:
            # 按路径分组所有项目
            path_groups = {}
            
            for item in all_items:
                path = item['path']
                if path not in path_groups:
                    path_groups[path] = {'files': [], 'folders': []}
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    path_groups[path]['folders'].append(item)
                else:
                    path_groups[path]['files'].append(item)
            
            # 构建嵌套结构
            def build_folder_content(folder_path):
                content = path_groups.get(folder_path, {'files': [], 'folders': []})
                
                # 为每个子文件夹递归构建内容
                enriched_folders = []
                for folder in content['folders']:
                    folder_copy = folder.copy()
                    sub_path = f"{folder_path}/{folder['name']}" if folder_path != "~" else f"~/{folder['name']}"
                    sub_content = build_folder_content(sub_path)
                    
                    # 将子内容添加到文件夹中
                    folder_copy['files'] = sub_content['files']
                    folder_copy['folders'] = sub_content['folders']
                    enriched_folders.append(folder_copy)
                
                return {
                    'files': content['files'],
                    'folders': enriched_folders
                }
            
            # 从根路径开始构建
            return build_folder_content(root_path)
            
        except Exception as e:
            return {'files': [], 'folders': [], 'error': str(e)}

    def _build_folder_tree(self, folders):
        """构建文件夹树结构，便于显示层次关系"""
        try:
            tree = {}
            
            for folder in folders:
                path_parts = folder['path'].split('/')
                current_level = tree
                
                for i, part in enumerate(path_parts):
                    if part not in current_level:
                        current_level[part] = {
                            'folders': {},
                            'info': None
                        }
                    current_level = current_level[part]['folders']
                
                # 在最终位置添加当前文件夹信息
                current_level[folder['name']] = {
                    'folders': {},
                    'info': {
                        'id': folder['id'],
                        'url': folder['url'],
                        'name': folder['name'],
                        'path': folder['path'],
                        'depth': folder['depth']
                    }
                }
            
            return tree
            
        except Exception as e:
            print(f"构建文件夹树时出错: {e}")
            return {}

    def _generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return f"https://drive.google.com/drive/folders/{folder_id}"

    def _generate_web_url(self, file):
        """为文件生成网页链接"""
        file_id = file['id']
        mime_type = file['mimeType']
        
        if mime_type == 'application/vnd.google.colaboratory':
            # Colab文件
            return f"https://colab.research.google.com/drive/{file_id}"
        elif mime_type == 'application/vnd.google-apps.document':
            # Google文档
            return f"https://docs.google.com/document/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google表格
            return f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.presentation':
            # Google幻灯片
            return f"https://docs.google.com/presentation/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.folder':
            # 文件夹
            return f"https://drive.google.com/drive/folders/{file_id}"
        else:
            # 其他文件（预览或下载）
            return f"https://drive.google.com/file/d/{file_id}/view"

    def cmd_cd(self, path):
        """切换目录"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                path = "~"
            
            target_id, target_path = self.main_instance.resolve_path(path, current_shell)
            
            if not target_id:
                return {"success": False, "error": f"目录不存在: {path}"}
            
            shells_data = self.load_shells()
            shell_id = current_shell['id']
            
            shells_data["shells"][shell_id]["current_path"] = target_path
            shells_data["shells"][shell_id]["current_folder_id"] = target_id
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "new_path": target_path,
                    "folder_id": target_id,
                    "message": f"✅ 已切换到目录: {target_path}"
                }
            else:
                return {"success": False, "error": "保存shell状态失败"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cd命令时出错: {e}"}

    def cmd_mkdir(self, path, recursive=False):
        """创建目录，通过远程命令界面执行以确保由用户账户创建"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                return {"success": False, "error": "请指定要创建的目录名称"}
            
            # 调用统一的mkdir_remote方法
            return self.cmd_mkdir_remote(path, recursive)
                
        except Exception as e:
            return {"success": False, "error": f"执行mkdir命令时出错: {e}"}

    def _ls_single(self, target_folder_id, display_path, detailed, show_hidden=False):
        """列出单个目录内容（统一实现，包含去重处理）"""
        try:
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=50)
            
            if result['success']:
                files = result['files']
                
                # 添加网页链接到每个文件
                for file in files:
                    file['url'] = self._generate_web_url(file)
                
                # 按名称排序，文件夹优先
                folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                               key=lambda x: x['name'].lower())
                other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                
                # 去重处理
                seen_names = set()
                clean_folders = []
                clean_files = []
                
                # 处理文件夹
                for folder in folders:
                    if folder["name"] not in seen_names:
                        clean_folders.append(folder)
                        seen_names.add(folder["name"])
                
                # 处理文件
                for file in other_files:
                    if file["name"] not in seen_names:
                        clean_files.append(file)
                        seen_names.add(file["name"])
                
                if detailed:
                    # 详细模式：返回完整JSON
                    return {
                        "success": True,
                        "path": display_path,
                        "folder_id": target_folder_id,
                        "folder_url": self._generate_folder_url(target_folder_id),
                        "files": clean_files,  # 只有非文件夹文件
                        "folders": clean_folders,  # 只有文件夹
                        "count": len(clean_folders) + len(clean_files),
                        "mode": "detailed"
                    }
                else:
                    # bash风格：只返回文件名列表
                    return {
                        "success": True,
                        "path": display_path,
                        "folder_id": target_folder_id,
                        "files": clean_files,  # 只有非文件夹文件
                        "folders": clean_folders,  # 只有文件夹
                        "count": len(clean_folders) + len(clean_files),
                        "mode": "bash"
                    }
            else:
                return {"success": False, "error": f"列出文件失败: {result['error']}"}
                
        except Exception as e:
            return {"success": False, "error": f"列出单个目录时出错: {e}"}

    def _find_folder(self, folder_name, parent_id):
        """在指定父目录中查找文件夹"""
        try:
            files_result = self.drive_service.list_files(folder_id=parent_id, max_results=100)
            if not files_result['success']:
                return None
            
            for file in files_result['files']:
                if (file['name'] == folder_name and 
                    file['mimeType'] == 'application/vnd.google-apps.folder'):
                    return file
            
            return None
            
        except Exception:
            return None

    def cmd_rm(self, path, recursive=False, force=False):
        """删除文件或目录，通过远程rm命令执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
            
            if not path:
                return {"success": False, "error": "Please specify file or directory to delete"}
            
            # 解析远程绝对路径
            absolute_path = self.resolve_remote_absolute_path(path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {path}"}
            
            # 构建rm命令
            rm_flags = ""
            if recursive:
                rm_flags += "r"
            if force:
                rm_flags += "f"
            
            if rm_flags:
                remote_command = f'rm -{rm_flags} "{absolute_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            else:
                remote_command = f'rm "{absolute_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
            # 执行远程命令
            result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="rm",
                context_info={
                    "target_path": path,
                    "absolute_path": absolute_path,
                    "recursive": recursive,
                    "force": force
                }
            )
            
            if result["success"]:
                # 简化验证逻辑：如果远程命令执行成功，就认为删除成功
                # 避免复杂的验证逻辑导致误报
                return {
                    "success": True,
                    "path": path,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，像bash shell一样
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Error executing rm command: {e}"}

    def cmd_echo(self, text, output_file=None):
        """echo命令 - 输出文本或创建文件"""
        try:
            if not text:
                return {"success": True, "output": ""}
            
            if output_file:
                # echo "text" > file - 创建文件
                return self._create_text_file(output_file, text)
            else:
                # echo "text" - 输出文本
                return {"success": True, "output": text}
                
        except Exception as e:
            return {"success": False, "error": f"执行echo命令时出错: {e}"}

    def cmd_cat(self, filename):
        """cat命令 - 显示文件内容"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not filename:
                return {"success": False, "error": "请指定要查看的文件"}
            
            # 查找文件
            file_info = self._find_file(filename, current_shell)
            if not file_info:
                return {"success": False, "error": f"文件或目录不存在: {filename}"}
            
            # 检查是否为文件
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"cat: {filename}: Is a directory"}
            
            # 下载并读取文件内容
            try:
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                request = self.drive_service.service.files().get_media(fileId=file_info['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8', errors='replace')
                return {"success": True, "output": content, "filename": filename}
                
            except Exception as e:
                return {"success": False, "error": f"无法读取文件内容: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cat命令时出错: {e}"}

    def cmd_grep(self, pattern, *filenames):
        """grep命令 - 在文件中搜索模式，支持多文件和regex"""
        import re
        
        try:
            if not pattern:
                return {"success": False, "error": "请指定搜索模式"}
            
            if not filenames:
                return {"success": False, "error": "请指定要搜索的文件"}
            
            # 编译正则表达式
            try:
                regex = re.compile(pattern)
            except re.error as e:
                return {"success": False, "error": f"无效的正则表达式: {e}"}
            
            result = {}
            
            for filename in filenames:
                # 获取文件内容
                cat_result = self.cmd_cat(filename)
                if not cat_result["success"]:
                    result[filename] = {
                        "local_file": None,
                        "occurrences": [],
                        "error": cat_result["error"]
                    }
                    continue
                
                content = cat_result["output"]
                lines = content.split('\n')
                
                # 搜索匹配的位置
                occurrences = {}
                for line_num, line in enumerate(lines, 1):
                    line_matches = []
                    for match in regex.finditer(line):
                        line_matches.append(match.start())
                    if line_matches:
                        occurrences[line_num] = line_matches
                
                # 转换为所需格式: {line_num: [positions]}
                formatted_occurrences = occurrences
                
                # 获取本地缓存文件路径
                local_file = self._get_local_cache_path(filename)
                
                result[filename] = {
                    "local_file": local_file,
                    "occurrences": formatted_occurrences
                }
            
            return {"success": True, "result": result}
                
        except Exception as e:
            return {"success": False, "error": f"执行grep命令时出错: {e}"}

    def cmd_upload_multi(self, file_pairs, force=False, remove_local=False):
        """
        多文件上传命令，支持 [[src1, dst1], [src2, dst2], ...] 语法
        
        Args:
            file_pairs (list): 文件对列表，每个元素为 [源文件路径, 远端目标路径]
            
        Returns:
            dict: 上传结果
        """
        try:
            # 0. 检查Google Drive Desktop是否运行
            if not self.ensure_google_drive_desktop_running():
                return {"success": False, "error": "用户取消上传操作"}
            
            if not file_pairs:
                return {"success": False, "error": "Please specify file pairs to upload"}
            
            # 验证文件对格式和源文件唯一性
            validated_pairs = []
            source_files = set()
            
            for pair in file_pairs:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    return {"success": False, "error": "File pair format error, each element should be [source_file, remote_path]"}
                src_file, dst_path = pair
                if not os.path.exists(src_file):
                    return {"success": False, "error": f"Source file does not exist: {src_file}"}
                
                # 检查源文件是否重复
                abs_src_file = os.path.abspath(src_file)
                if abs_src_file in source_files:
                    return {
                        "success": False,
                        "error": f"Source file conflict: {src_file} cannot be uploaded to multiple locations"
                    }
                source_files.add(abs_src_file)
                
                validated_pairs.append([src_file, dst_path])
            
            # 第一阶段：检查目标目录冲突和文件存在冲突
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
            
            # 检查目标目录是否有重复
            target_paths = set()
            for src_file, dst_path in validated_pairs:
                filename = Path(src_file).name
                
                # 判断 dst_path 是文件还是文件夹
                # 使用原来的逻辑：检查路径最后一个部分是否包含点号
                last_part = dst_path.split('/')[-1]
                is_file = '.' in last_part and last_part != '.' and last_part != '..'
                
                # 计算完整的远端目标路径
                if is_file:
                    # dst_path 是文件名，需要放在当前目录中
                    if dst_path.startswith("/"):
                        # 绝对路径文件名
                        full_target_path = dst_path
                    else:
                        # 相对路径文件名，放在当前shell目录中
                        current_path = current_shell.get("current_path", "~")
                        if current_path == "~":
                            full_target_path = f"~/{dst_path}"
                        else:
                            full_target_path = f"{current_path}/{dst_path}"
                else:
                    # dst_path 是文件夹，在后面添加文件名
                    if dst_path.startswith("/"):
                        full_target_path = f"{dst_path.rstrip('/')}/{filename}"
                    elif dst_path == "." or dst_path == "":
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                full_target_path = f"{current_path}/{filename}"
                            else:
                                full_target_path = f"~/{filename}"
                        else:
                            full_target_path = f"~/{filename}"
                    else:
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    full_target_path = f"~/{base_path}/{dst_path.strip('/')}/{filename}"
                                else:
                                    full_target_path = f"~/{dst_path.strip('/')}/{filename}"
                            else:
                                full_target_path = f"~/{dst_path.strip('/')}/{filename}"
                        else:
                            full_target_path = f"~/{dst_path.strip('/')}/{filename}"
                
                if full_target_path in target_paths:
                    return {
                        "success": False,
                        "error": f"Target path conflict: {full_target_path} specified by multiple files"
                    }
                target_paths.add(full_target_path)
            
            # 检查每个目标文件是否已存在（除非使用--force）
            overridden_files = []
            if not force:
                for src_file, dst_path in validated_pairs:
                    filename = Path(src_file).name
                    
                    # 计算远端绝对路径
                    if dst_path.startswith("/"):
                        remote_file_path = f"{dst_path.rstrip('/')}/{filename}"
                    elif dst_path == "." or dst_path == "":
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                remote_file_path = f"{current_path}/{filename}"
                            else:
                                remote_file_path = f"~/{filename}"
                        else:
                            remote_file_path = f"~/{filename}"
                    else:
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    remote_file_path = f"~/{base_path}/{dst_path.strip('/')}/{filename}"
                                else:
                                    remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                            else:
                                remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                        else:
                            remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                    
                    # 检查文件是否存在
                    dir_path = '/'.join(remote_file_path.split('/')[:-1]) if remote_file_path.count('/') > 0 else "~"
                    file_name = remote_file_path.split('/')[-1]
                    
                    ls_result = self.main_instance.cmd_ls(dir_path, detailed=False, recursive=False)
                    if ls_result["success"] and "files" in ls_result:
                        existing_files = [f["name"] for f in ls_result["files"]]
                        if file_name in existing_files:
                            return {
                                "success": False,
                                "error": f"File exists: {remote_file_path}"
                            }
            else:
                # Force模式：检查哪些文件会被覆盖，记录警告
                for src_file, dst_path in validated_pairs:
                    filename = Path(src_file).name
                    
                    # 计算远端绝对路径
                    if dst_path.startswith("/"):
                        remote_file_path = f"{dst_path.rstrip('/')}/{filename}"
                    elif dst_path == "." or dst_path == "":
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                remote_file_path = f"{current_path}/{filename}"
                            else:
                                remote_file_path = f"~/{filename}"
                        else:
                            remote_file_path = f"~/{filename}"
                    else:
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    remote_file_path = f"~/{base_path}/{dst_path.strip('/')}/{filename}"
                                else:
                                    remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                            else:
                                remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                        else:
                            remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                    
                    # 检查文件是否存在，如果存在则记录为覆盖
                    dir_path = '/'.join(remote_file_path.split('/')[:-1]) if remote_file_path.count('/') > 0 else "~"
                    file_name = remote_file_path.split('/')[-1]
                    
                    ls_result = self.main_instance.cmd_ls(dir_path, detailed=False, recursive=False)
                    if ls_result["success"] and "files" in ls_result:
                        existing_files = [f["name"] for f in ls_result["files"]]
                        if file_name in existing_files:
                            overridden_files.append(remote_file_path)
                            print(f"⚠️ Warning: Overriding remote file {remote_file_path}")
            
            # 第二阶段：执行多文件上传
            all_file_moves = []
            failed_moves = []
            
            # 移动所有文件到LOCAL_EQUIVALENT
            for src_file, dst_path in validated_pairs:
                move_result = self.move_to_local_equivalent(src_file)
                if move_result["success"]:
                    all_file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"],
                        "target_path": dst_path
                    })
                else:
                    failed_moves.append({
                        "file": src_file,
                        "error": move_result["error"]
                    })
            
            if not all_file_moves:
                return {
                    "success": False,
                    "error": "所有文件移动失败",
                    "failed_moves": failed_moves
                }
            
            # 等待文件同步到DRIVE_EQUIVALENT
            expected_filenames = [fm["filename"] for fm in all_file_moves]
            sync_result = self.wait_for_file_sync(expected_filenames, all_file_moves)
            
            if not sync_result["success"]:
                return {
                    "success": False,
                    "error": f"文件同步检测失败: {sync_result.get('error', '未知错误')}",
                    "file_moves": all_file_moves,
                    "sync_time": sync_result.get("sync_time", 0)
                }
            
            # 生成异步远端命令
            remote_command = self._generate_multi_file_remote_commands(all_file_moves)
            
            # 执行远端命令
            context_info = {
                "file_moves": all_file_moves,
                "multi_file": True
            }
            
            execution_result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="upload",
                context_info=context_info
            )
            
            if not execution_result["success"]:
                return {
                    "success": False,
                    "error": execution_result["message"],
                    "remote_command": remote_command,
                    "execution_result": execution_result
                }
            
            # 如果指定了 --remove-local 选项，删除本地源文件
            removed_files = []
            failed_removals = []
            if remove_local and execution_result["success"]:
                for src_file, _ in validated_pairs:
                    try:
                        if os.path.exists(src_file):
                            os.unlink(src_file)
                            removed_files.append(src_file)
                    except Exception as e:
                        failed_removals.append({"file": src_file, "error": str(e)})
            
            result = {
                "success": True,
                "uploaded_files": [{"name": fm["filename"], "target_path": fm["target_path"]} for fm in all_file_moves],
                "failed_files": [fm["file"] for fm in failed_moves],
                "total_attempted": len(validated_pairs),
                "total_succeeded": len(all_file_moves),
                "message": f"✅ 多文件上传完成: {len(all_file_moves)}/{len(validated_pairs)} 个文件成功",
                "sync_time": sync_result.get("sync_time", 0),
                "remote_command": remote_command
            }
            
            # 添加本地文件删除信息
            if remove_local:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"多文件上传时出错: {e}"}

    def cmd_download(self, filename, local_path=None, force=False):
        """
        download命令 - 从Google Drive下载文件并缓存
        用法：
        - download A: 下载到缓存目录，显示哈希文件名
        - download A B: 下载到缓存目录，然后复制到指定位置（类似cp操作）
        - download --force A: 强制重新下载，替换缓存
        """
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "缓存管理器未找到"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远端绝对路径
            remote_absolute_path = self.resolve_remote_absolute_path(filename, current_shell)
            
            # 检查是否已经缓存（如果force=True则跳过缓存检查）
            if not force and cache_manager.is_file_cached(remote_absolute_path):
                cached_info = cache_manager.get_cached_file(remote_absolute_path)
                cached_path = cache_manager.get_cached_file_path(remote_absolute_path)
                
                if local_path:
                    # 如果指定了本地目标，复制缓存文件到目标位置（cp操作）
                    import shutil
                    if os.path.isdir(local_path):
                        # 从原始filename中提取实际文件名（不包含路径部分）
                        actual_filename = os.path.basename(filename)
                        target_path = os.path.join(local_path, actual_filename)
                    else:
                        target_path = local_path
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                    shutil.copy2(cached_path, target_path)
                    
                    return {
                        "success": True,
                        "message": f"Using cached file: {target_path}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "local_path": target_path,
                        "cache_status": cached_info["status"]
                    }
                else:
                    # 只显示缓存信息
                    return {
                        "success": True,
                        "message": f"Using cached file: {cached_info['cache_file']}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "cached_path": cached_path,
                        "cache_status": cached_info["status"]
                    }
            
            # 文件未缓存或强制重新下载
            # 如果是强制模式且文件已缓存，先删除旧缓存
            if force and cache_manager.is_file_cached(remote_absolute_path):
                old_cached_info = cache_manager.get_cached_file(remote_absolute_path)
                old_cache_file = old_cached_info.get("cache_file")
                
                # 删除旧的缓存文件
                cleanup_result = cache_manager.cleanup_cache(remote_absolute_path)
                force_info = {
                    "force_mode": True,
                    "removed_old_cache": cleanup_result.get("success", False),
                    "old_cache_file": old_cache_file
                }
            else:
                force_info = {"force_mode": False}
            
            # 解析路径以获取目标文件夹和文件名
            file_info = None
            target_folder_id = None
            actual_filename = None
            
            # 分析路径：分离目录路径和文件名
            if '/' in filename:
                # 包含路径分隔符，需要解析路径
                path_parts = filename.rsplit('/', 1)  # 从右边分割，只分割一次
                dir_path = path_parts[0] if path_parts[0] else '/'
                actual_filename = path_parts[1]
                
                # 解析目录路径
                target_folder_id, resolved_path = self.main_instance.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    return {"success": False, "error": f"Download failed: directory not found: {dir_path}"}
            else:
                # 没有路径分隔符，在当前目录查找
                target_folder_id = current_shell.get("current_folder_id")
                actual_filename = filename
            
            # 在目标文件夹中查找文件
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if result['success']:
                files = result['files']
                for file in files:
                    if file['name'] == actual_filename:
                        file_info = file
                        break
            
            if not file_info:
                return {"success": False, "error": f"Download failed: file not found: {actual_filename}"}
            
            # 检查是否为文件（不是文件夹）
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"download: {actual_filename}: 是一个目录，无法下载"}
            
            # 使用Google Drive API直接下载文件
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{actual_filename}") as temp_file:
                temp_path = temp_file.name
            
            try:
                # 使用Google Drive API下载文件内容
                file_id = file_info['id']
                request = self.drive_service.service.files().get_media(fileId=file_id)
                content = request.execute()
                
                # 将内容写入临时文件
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                # 下载成功，缓存文件
                cache_result = cache_manager.cache_file(
                    remote_path=remote_absolute_path,
                    temp_file_path=temp_path
                )
                
                if cache_result["success"]:
                    if local_path:
                        # 如果指定了本地目标，也复制到目标位置（cp操作）
                        import shutil
                        if os.path.isdir(local_path):
                            target_path = os.path.join(local_path, actual_filename)
                        else:
                            target_path = local_path
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                        shutil.copy2(temp_path, target_path)
                        
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {target_path}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"],
                            "local_path": target_path
                        }
                        result.update(force_info)
                        return result
                    else:
                        # 只显示缓存信息
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {cache_result['cache_file']}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"]
                        }
                        result.update(force_info)
                        return result
                else:
                    return {"success": False, "error": f"Download failed: {cache_result.get('error')}"}
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            return {"success": False, "error": f"下载文件时出错: {e}"}

    def cmd_mv_multi(self, file_pairs, force=False):
        """
        多文件移动命令，支持 [[src1, dst1], [src2, dst2], ...] 语法
        
        Args:
            file_pairs (list): 文件对列表，每个元素为 [源远端路径, 目标远端路径]
            
        Returns:
            dict: 移动结果
        """
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            if not file_pairs:
                return {"success": False, "error": "请指定要移动的文件对"}
            
            # 验证文件对格式并检查冲突
            validated_pairs = []
            target_destinations = set()
            source_files = set()
            
            for pair in file_pairs:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    return {"success": False, "error": "文件对格式错误，每个元素应为 [源路径, 目标路径]"}
                
                source, destination = pair
                if not source or not destination:
                    return {"success": False, "error": "Source and destination paths cannot be empty"}
                
                # 检查源文件是否重复
                abs_source_path = self.resolve_remote_absolute_path(source, current_shell)
                if abs_source_path in source_files:
                    return {
                        "success": False,
                        "error": f"Source file conflict: {source} cannot be moved to multiple destinations"
                    }
                source_files.add(abs_source_path)
                
                # 计算目标的远端绝对路径用于重复检测
                if destination.startswith("/"):
                    abs_destination = destination
                else:
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:] if len(current_path) > 2 else ""
                            if relative_path:
                                abs_destination = f"~/{relative_path}/{destination}"
                            else:
                                abs_destination = f"~/{destination}"
                        else:
                            abs_destination = f"~/{destination}"
                    else:
                        abs_destination = f"~/{destination}"
                
                # 检查目标路径是否重复
                if abs_destination in target_destinations:
                    return {
                        "success": False,
                        "error": f"Destination path conflict: {abs_destination} specified by multiple files"
                    }
                target_destinations.add(abs_destination)
                
                # 检查目标是否已存在
                destination_check_result = self._check_mv_destination_conflict(destination, current_shell)
                if not destination_check_result["success"]:
                    return destination_check_result
                
                validated_pairs.append([source, destination])
            
            # 生成多文件mv的远端命令
            remote_command = self._generate_multi_mv_remote_commands(validated_pairs, current_shell)
            
            # 执行远端命令
            context_info = {
                "file_pairs": validated_pairs,
                "multi_file": True
            }
            
            result = self.execute_remote_command_interface(
                remote_command=remote_command, 
                command_type="move", 
                context_info=context_info
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "moved_files": [{"source": src, "destination": dst} for src, dst in validated_pairs],
                    "total_moved": len(validated_pairs),
                    "message": f"✅ 多文件移动完成: {len(validated_pairs)} 个文件",
                    "verification": "success"
                }
            else:
                error_msg = result.get("message", result.get("error", "未知错误"))
                return {
                    "success": False,
                    "error": f"多文件移动失败: {error_msg}",
                    "verification": "failed"
                }
                
        except Exception as e:
            return {"success": False, "error": f"多文件移动时出错: {e}"}

    def cmd_mv(self, source, destination, force=False):
        """mv命令 - 移动/重命名文件或文件夹（使用远端指令执行）"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            if not source or not destination:
                return {"success": False, "error": "用法: mv <source> <destination>"}
            
            # 检查目标是否已存在（避免覆盖）
            destination_check_result = self._check_mv_destination_conflict(destination, current_shell)
            if not destination_check_result["success"]:
                return destination_check_result
            
            # 构建远端mv命令 - 需要计算绝对路径
            source_absolute_path = self.resolve_remote_absolute_path(source, current_shell)
            destination_absolute_path = self.resolve_remote_absolute_path(destination, current_shell)
            
            # 构建增强的远端命令，包含成功/失败提示
            base_command = f"mv {source_absolute_path} {destination_absolute_path}"
            remote_command = f"({base_command}) && clear && echo \"✅ 执行成功\" || echo \"❌ 执行失败\""
            
            # 使用远端指令执行接口
            result = self.execute_remote_command_interface(remote_command, "move", {
                "source": source,
                "destination": destination
            })
            
            if result.get("success"):
                # 验证移动是否成功
                verification_result = self._verify_mv_with_ls(source, destination, current_shell)
                
                if verification_result.get("success"):
                    # 移动成功，更新缓存路径映射
                    cache_update_result = self._update_cache_after_mv(source, destination, current_shell)
                    
                    return {
                        "success": True,
                        "source": source,
                        "destination": destination,
                        "message": f"✅ 已移动 {source} -> {destination}",
                        "cache_updated": cache_update_result.get("success", False),
                        "verification": "success"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"移动命令执行但验证失败: {verification_result.get('error')}",
                        "verification": "failed"
                    }
            else:
                # 处理不同类型的失败
                error_msg = "未知错误"
                if result.get("user_reported_failure"):
                    error_info = result.get("error_info")
                    if error_info:
                        error_msg = f"执行失败：{error_info}"
                    else:
                        error_msg = "执行失败"
                elif result.get("cancelled"):
                    error_msg = "用户取消操作"
                elif result.get("window_error"):
                    error_msg = result.get("error_info", "窗口显示错误")
                else:
                    error_msg = result.get("message", result.get("error", "未知错误"))
                
                return {
                    "success": False,
                    "error": f"远端mv命令执行失败: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"执行mv命令时出错: {e}"}

    def _find_file(self, filepath, current_shell):
        """查找文件，支持路径解析"""
        try:
            # 如果包含路径分隔符，需要解析路径
            if '/' in filepath:
                # 分离目录和文件名
                dir_path, filename = filepath.rsplit('/', 1)
                
                # 解析目录路径
                target_folder_id, _ = self.main_instance.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    return None
            else:
                # 在当前目录查找
                filename = filepath
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            
            # 列出目标目录内容
            files_result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not files_result['success']:
                return None
            
            # 查找匹配的文件
            for file in files_result['files']:
                if file['name'] == filename:
                    return file
            
            return None
            
        except Exception:
            return None

    def cmd_python(self, code=None, filename=None, save_output=False):
        """python命令 - 执行Python代码"""
        try:
            if filename:
                # 执行Drive中的Python文件
                return self._execute_python_file(filename, save_output)
            elif code:
                # 执行直接提供的Python代码
                return self._execute_python_code(code, save_output)
            else:
                return {"success": False, "error": "请提供Python代码或文件名"}
                
        except Exception as e:
            return {"success": False, "error": f"执行Python命令时出错: {e}"}

    def _execute_python_file(self, filename, save_output=False):
        """执行Google Drive中的Python文件"""
        try:
            # 首先读取文件内容
            cat_result = self.cmd_cat(filename)
            if not cat_result["success"]:
                return cat_result
            
            python_code = cat_result["output"]
            return self._execute_python_code(python_code, save_output, filename)
            
        except Exception as e:
            return {"success": False, "error": f"执行Python文件时出错: {e}"}

    def _execute_python_code(self, code, save_output=False, filename=None):
        """执行Python代码并返回结果"""
        try:
            import subprocess
            import tempfile
            import os
            
            # 创建临时Python文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # 执行Python代码
                result = subprocess.run(
                    ['/usr/bin/python3', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30秒超时
                )
                
                # 清理临时文件
                os.unlink(temp_file_path)
                
                # 准备结果
                execution_result = {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "filename": filename
                }
                
                # 如果需要保存输出到Drive
                if save_output and (result.stdout or result.stderr):
                    output_filename = f"{filename}_output.txt" if filename else "python_output.txt"
                    output_content = f"=== Python Execution Result ===\n"
                    output_content += f"Return code: {result.returncode}\n\n"
                    
                    if result.stdout:
                        output_content += f"=== STDOUT ===\n{result.stdout}\n"
                    
                    if result.stderr:
                        output_content += f"=== STDERR ===\n{result.stderr}\n"
                    
                    # 尝试保存到Drive（如果失败也不影响主要功能）
                    try:
                        save_result = self._create_text_file(output_filename, output_content)
                        if save_result["success"]:
                            execution_result["output_saved"] = output_filename
                    except:
                        pass  # 保存失败不影响主要功能
                
                return execution_result
                
            except subprocess.TimeoutExpired:
                os.unlink(temp_file_path)
                return {"success": False, "error": "Python代码执行超时（30秒）"}
            except Exception as e:
                os.unlink(temp_file_path)
                return {"success": False, "error": f"执行Python代码时出错: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"准备Python执行环境时出错: {e}"}

    def cmd_mkdir_remote(self, target_path, recursive=False):
        """
        通过远端命令创建目录的接口（使用统一接口）
        
        Args:
            target_path (str): 目标路径
            recursive (bool): 是否递归创建
            
        Returns:
            dict: 创建结果
        """
        try:
            # 获取当前shell以解析相对路径
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 解析绝对路径
            absolute_path = self._resolve_absolute_mkdir_path(target_path, current_shell, recursive)
            if not absolute_path:
                return {"success": False, "error": f"无法解析路径: {target_path}"}
            
            # 生成远端mkdir命令，添加清屏和成功/失败提示（总是使用-p确保父目录存在）
            remote_command = f'mkdir -p "{absolute_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
            # 准备上下文信息
            context_info = {
                "target_path": target_path,
                "absolute_path": absolute_path,
                "recursive": recursive
            }
            
            # 使用统一接口执行远端命令
            execution_result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="mkdir",
                context_info=context_info
            )
            
            if execution_result["success"]:
                # 简洁返回，像bash shell一样成功时不显示任何信息
                return {
                    "success": True,
                    "path": target_path,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，不显示任何内容
                    "verification": {"success": True}
                }
            else:
                return execution_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"远端mkdir命令生成失败: {e}"
            }

    def cmd_read(self, filename, *args):
        """读取远端文件内容，支持智能缓存和行数范围"""
        try:
            if not filename:
                return {"success": False, "error": "请指定要读取的文件"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            remote_absolute_path = self.resolve_remote_absolute_path(filename, current_shell)
            if not remote_absolute_path:
                return {"success": False, "error": f"无法解析文件路径: {filename}"}
            
            line_ranges = self._parse_line_ranges(args)
            if line_ranges is False:
                return {"success": False, "error": "行数范围参数格式错误"}
            elif isinstance(line_ranges, dict) and "error" in line_ranges:
                return {"success": False, "error": line_ranges["error"]}
            
            freshness_result = self.is_cached_file_up_to_date(remote_absolute_path)
            
            file_content = None
            source = "unknown"
            
            if (freshness_result["success"] and 
                freshness_result["is_cached"] and 
                freshness_result["is_up_to_date"]):
                
                cache_status = self.is_remote_file_cached(remote_absolute_path)
                cache_file_path = cache_status["cache_file_path"]
                
                if cache_file_path and Path(cache_file_path).exists():
                    with open(cache_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_content = f.read()
                    source = "cache"
                else:
                    download_result = self._download_and_get_content(filename, remote_absolute_path)
                    if not download_result["success"]:
                        return download_result
                    file_content = download_result["content"]
                    source = "download"
            else:
                download_result = self._download_and_get_content(filename, remote_absolute_path)
                if not download_result["success"]:
                    return download_result
                file_content = download_result["content"]
                source = "download"
            
            lines = file_content.split('\n')
            
            if not line_ranges:
                selected_lines = [(i, line) for i, line in enumerate(lines)]
            else:
                selected_lines = []
                for start, end in line_ranges:
                    start = max(0, start)
                    end = min(len(lines), end)
                    
                    for i in range(start, end):
                        if i < len(lines):
                            selected_lines.append((i, lines[i]))
                
                selected_lines = list(dict(selected_lines).items())
                selected_lines.sort(key=lambda x: x[0])
            
            formatted_output = self._format_read_output(selected_lines)
            
            return {
                "success": True,
                "filename": filename,
                "remote_path": remote_absolute_path,
                "source": source,
                "total_lines": len(lines),
                "selected_lines": len(selected_lines),
                "line_ranges": line_ranges,
                "output": formatted_output,
                "lines_data": selected_lines
            }
            
        except Exception as e:
            return {"success": False, "error": f"读取文件时出错: {e}"}

    def cmd_find(self, *args):
        """
        GDS find命令实现，类似bash find
        
        用法:
            find [path] -name [pattern]
            find [path] -iname [pattern]  # 大小写不敏感
            find [path] -type f -name [pattern]  # 只查找文件
            find [path] -type d -name [pattern]  # 只查找目录
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 查找结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "用法: find [path] -name [pattern] 或 find [path] -type [f|d] -name [pattern]"
                }
            
            # 解析参数
            parsed_args = self._parse_find_args(args)
            if not parsed_args["success"]:
                return parsed_args
            
            search_path = parsed_args["path"]
            pattern = parsed_args["pattern"]
            case_sensitive = parsed_args["case_sensitive"]
            file_type = parsed_args["file_type"]  # "f" for files, "d" for directories, None for both
            
            # 递归搜索文件
            results = self._recursive_find(search_path, pattern, case_sensitive, file_type)
            
            if results["success"]:
                found_files = results["files"]
                
                # 格式化输出
                output_lines = []
                for file_path in sorted(found_files):
                    output_lines.append(file_path)
                
                return {
                    "success": True,
                    "files": found_files,
                    "count": len(found_files),
                    "output": "\n".join(output_lines) if output_lines else "No files found matching the pattern."
                }
            else:
                return results
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Find命令执行错误: {e}"
            }

    def cmd_edit(self, filename, replacement_spec, preview=False, backup=False):
        """
        GDS edit命令 - 支持多段文本同步替换的文件编辑功能
        
        Args:
            filename (str): 要编辑的文件名
            replacement_spec (str): 替换规范，支持多种格式
            preview (bool): 预览模式，只显示修改结果不实际保存
            backup (bool): 是否创建备份文件
            
        Returns:
            dict: 编辑结果
            
        支持的替换格式:
        1. 行号替换: '[[[1, 2], "new content"], [[5, 7], "another content"]]'
        2. 文本搜索替换: '[["old text", "new text"], ["another old", "another new"]]'
        3. 混合模式: '[[[1, 1], "line replacement"], ["text search", "text replace"]]'
        """
        try:
            import json
            import re
            import tempfile
            import shutil
            from datetime import datetime
            
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "缓存管理器未找到"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 1. 解析替换规范
            try:
                replacements = json.loads(replacement_spec)
                if not isinstance(replacements, list):
                    return {"success": False, "error": "替换规范必须是数组格式"}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"替换规范JSON解析失败: {e}"}
            
            # 2. 下载文件到缓存
            download_result = self.cmd_download(filename, force=True)  # 强制重新下载确保最新内容
            if not download_result["success"]:
                return {"success": False, "error": f"{download_result.get('error')}"}
            
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            if not cache_file_path or not os.path.exists(cache_file_path):
                return {"success": False, "error": "无法获取缓存文件路径"}
            
            # 3. 读取文件内容
            try:
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    original_lines = f.readlines()
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(cache_file_path, 'r', encoding='gbk') as f:
                        original_lines = f.readlines()
                except:
                    return {"success": False, "error": "文件编码不支持，请确保文件为UTF-8或GBK编码"}
            except Exception as e:
                return {"success": False, "error": f"读取文件失败: {e}"}
            
            # 4. 解析和验证替换操作
            parsed_replacements = []
            for i, replacement in enumerate(replacements):
                if not isinstance(replacement, list) or len(replacement) != 2:
                    return {"success": False, "error": f"替换规范第{i+1}项格式错误，应为[source, target]格式"}
                
                source, target = replacement
                
                if isinstance(source, list) and len(source) == 2 and all(isinstance(x, int) for x in source):
                    # 行号替换模式: [[start_line, end_line], "new_content"] (0-based, [a, b) 语法)
                    start_line, end_line = source
                    # 使用0-based索引，[a, b) 语法
                    start_idx = start_line
                    end_idx = end_line - 1  # end_line是exclusive的
                    
                    if start_idx < 0 or start_idx >= len(original_lines) or end_line > len(original_lines) or start_idx > end_idx:
                        return {"success": False, "error": f"行号范围错误: [{start_line}, {end_line})，文件共{len(original_lines)}行 (0-based索引)"}
                    
                    parsed_replacements.append({
                        "type": "line_range",
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "start_line": start_line,
                        "end_line": end_line,
                        "new_content": target,
                        "original_content": "".join(original_lines[start_idx:end_line]).rstrip()
                    })
                    
                elif isinstance(source, str):
                    # 文本搜索替换模式: ["old_text", "new_text"]
                    if source not in "".join(original_lines):
                        return {"success": False, "error": f"未找到要替换的文本: {source[:50]}..."}
                    
                    parsed_replacements.append({
                        "type": "text_search",
                        "old_text": source,
                        "new_text": target
                    })
                else:
                    return {"success": False, "error": f"替换规范第{i+1}项的源格式不支持，应为行号数组[start, end]或文本字符串"}
            
            # 5. 执行替换操作
            modified_lines = original_lines.copy()
            
            # 按行号倒序处理行替换，避免行号变化影响后续替换
            line_replacements = [r for r in parsed_replacements if r["type"] == "line_range"]
            line_replacements.sort(key=lambda x: x["start_idx"], reverse=True)
            
            for replacement in line_replacements:
                start_idx = replacement["start_idx"]
                end_idx = replacement["end_idx"]
                new_content = replacement["new_content"]
                
                # 确保新内容以换行符结尾（如果原内容有换行符）
                if not new_content.endswith('\n') and end_idx < len(modified_lines) - 1:
                    new_content += '\n'
                elif new_content.endswith('\n') and end_idx == len(modified_lines) - 1 and not original_lines[-1].endswith('\n'):
                    new_content = new_content.rstrip('\n')
                
                # 替换行范围 (使用[a, b)语法)
                modified_lines[start_idx:replacement["end_line"]] = [new_content] if new_content else []
            
            # 处理文本搜索替换
            text_replacements = [r for r in parsed_replacements if r["type"] == "text_search"]
            if text_replacements:
                file_content = "".join(modified_lines)
                for replacement in text_replacements:
                    file_content = file_content.replace(replacement["old_text"], replacement["new_text"])
                modified_lines = file_content.splitlines(keepends=True)
            
            # 6. 生成结果预览
            diff_info = self._generate_edit_diff(original_lines, modified_lines, parsed_replacements)
            
            if preview:
                # 预览模式：只返回修改预览，不实际保存
                return {
                    "success": True,
                    "mode": "preview",
                    "filename": filename,
                    "original_lines": len(original_lines),
                    "modified_lines": len(modified_lines),
                    "replacements_applied": len(parsed_replacements),
                    "diff": diff_info,
                    "preview_content": "".join(modified_lines)
                }
            
            # 7. 创建备份（如果需要）
            backup_info = {}
            if backup:
                backup_filename = f"{filename}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_result = self._create_backup(filename, backup_filename)
                backup_info = {
                    "backup_created": backup_result["success"],
                    "backup_filename": backup_filename if backup_result["success"] else None,
                    "backup_error": backup_result.get("error") if not backup_result["success"] else None
                }
            
            # 8. 保存修改后的文件到临时位置，使用正确的文件名
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, filename)
            
            # 如果临时文件已存在，添加时间戳避免冲突
            if os.path.exists(temp_file_path):
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    temp_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    temp_filename = f"{filename}_{timestamp}"
                temp_file_path = os.path.join(temp_dir, temp_filename)
            
            with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
                temp_file.writelines(modified_lines)
            
            try:
                # 9. 更新缓存
                remote_absolute_path = self.resolve_remote_absolute_path(filename, current_shell)
                cache_result = cache_manager.cache_file(remote_absolute_path, temp_file_path)
                
                if not cache_result["success"]:
                    return {"success": False, "error": f"更新缓存失败: {cache_result.get('error')}"}
                
                # 10. 上传修改后的文件，使用多文件上传语法指定目标文件名
                file_pairs = [[temp_file_path, filename]]
                upload_result = self.cmd_upload_multi(file_pairs, force=True)
                
                if upload_result["success"]:
                    result = {
                        "success": True,
                        "filename": filename,
                        "original_lines": len(original_lines),
                        "modified_lines": len(modified_lines),
                        "replacements_applied": len(parsed_replacements),
                        "diff": diff_info,
                        "cache_updated": True,
                        "uploaded": True,
                        "message": f"文件 {filename} 编辑完成，应用了 {len(parsed_replacements)} 个替换操作"
                    }
                    result.update(backup_info)
                    return result
                else:
                    return {
                        "success": False,
                        "error": f"上传修改后的文件失败: {upload_result.get('error')}",
                        "cache_updated": True,
                        "diff": diff_info
                    }
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except Exception as e:
            return {"success": False, "error": f"编辑操作失败: {str(e)}"}
