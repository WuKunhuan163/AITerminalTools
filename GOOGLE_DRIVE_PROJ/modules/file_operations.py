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

try:
    from ..google_drive_api import GoogleDriveService
except ImportError:
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService

# 导入debug捕获系统
from .remote_commands import debug_capture, debug_print

class FileOperations:
    """Google Drive Shell File Operations"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def check_network_connection(self):
        """委托到sync_manager的网络连接检查"""
        return self.main_instance.sync_manager.check_network_connection()
    
    def _verify_files_available(self, file_moves):
        """委托到file_utils的文件可用性验证"""
        return self.main_instance.file_utils._verify_files_available(file_moves)
    
    def generate_remote_commands(self, *args, **kwargs):
        """委托到remote_commands的远程命令生成"""
        return self.main_instance.remote_commands.generate_remote_commands(*args, **kwargs)
    
    def _cleanup_local_equivalent_files(self, file_moves):
        """委托到cache_manager的本地等效文件清理"""
        return self.main_instance.cache_manager._cleanup_local_equivalent_files(file_moves)
    
    def ensure_google_drive_desktop_running(self):
        """确保Google Drive Desktop正在运行"""
        try:
            # 检查Google Drive Desktop是否正在运行
            result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and bool(result.stdout.strip()):
                return True
            
            # 如果没有运行，尝试启动
            print("🚀 启动Google Drive Desktop...")
            if platform.system() == "Darwin":  # macOS
                subprocess.run(['open', '-a', 'Google Drive'], check=False)
            elif platform.system() == "Linux":
                subprocess.run(['google-drive'], check=False)
            elif platform.system() == "Windows":
                subprocess.run(['start', 'GoogleDrive'], shell=True, check=False)
            
            # 等待启动
            for i in range(10):
                time.sleep(1)
                result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and bool(result.stdout.strip()):
                    print("✅ Google Drive Desktop started successfully")
                    return True
            
            print("❌ Google Drive Desktop failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error checking/starting Google Drive Desktop: {e}")
            return False
    
    def _check_large_files(self, source_files):
        """检查大文件并分离处理（大于1G的文件）"""
        normal_files = []
        large_files = []
        
        for file_path in source_files:
            try:
                file_size = os.path.getsize(file_path)
                # 1G = 1024 * 1024 * 1024 bytes
                if file_size > 1024 * 1024 * 1024:
                    large_files.append({
                        "path": file_path,
                        "size": file_size,
                        "name": os.path.basename(file_path)
                    })
                else:
                    normal_files.append(file_path)
            except OSError:
                # 文件不存在或无法访问，加入normal_files让后续处理报错
                normal_files.append(file_path)
        
        return normal_files, large_files
    
    def _handle_large_files(self, large_files, target_path, current_shell):
        """处理大文件上传"""
        print(f"\n📁 Detected {len(large_files)} large files (>1GB):")
        for file_info in large_files:
            size_gb = file_info["size"] / (1024 * 1024 * 1024)
            print(f"  - {file_info['name']} ({size_gb:.1f} GB)")
        
        print(f"\n💡 Large files need to be manually uploaded to Google Drive:")
        print(f"  1. Open Google Drive web version")
        print(f"  2. Manually drag and drop these large files")
        print(f"  3. Wait for upload to complete")
        
        return {"success": True, "message": "Large files detected, manual upload required"}
    
    def wait_for_file_sync(self, file_names, file_moves):
        """等待文件同步完成"""
        return self.main_instance.sync_manager.wait_for_file_sync(file_names, file_moves)
    
    def _resolve_target_path_for_upload(self, target_path, current_shell):
        """解析上传目标路径 - 委托给path_resolver"""
        debug_print(f"🔧 DEBUG: Before _resolve_target_path_for_upload - target_path='{target_path}'")
        debug_print(f"🔧 DEBUG: current_shell={current_shell}")
        
        # 委托给path_resolver中的完整实现
        result = self.main_instance.path_resolver._resolve_target_path_for_upload(target_path, current_shell)
        
        debug_print(f"🔧 DEBUG: After _resolve_target_path_for_upload - target_folder_id='{result[0]}', target_display_path='{result[1]}'")
        return result
    
    def _check_target_file_conflicts_before_move(self, file_moves, force=False):
        """检查目标文件冲突"""
        # 简化实现，如果force=True直接返回成功
        if force:
            return {"success": True, "conflicts": []}
        
        # 否则检查文件是否已存在（简化版本）
        conflicts = []
        for move in file_moves:
            target_path = move.get("new_path", "")
            if os.path.exists(target_path):
                conflicts.append({
                    "file": move.get("source", ""),
                    "target": target_path,
                    "reason": "File already exists"
                })
        
        if conflicts:
            return {
                "success": False,
                "conflicts": conflicts,
                "error": f"Found {len(conflicts)} file conflicts"
            }
        
        return {"success": True, "conflicts": []}
    

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
            folder_name = Path(folder_path).name
            print(f"📦 Packing {folder_name} ...", end="", flush=True)
            
            # 步骤1: 打包文件夹
            zip_result = self.main_instance.file_utils._zip_folder(folder_path)
            if not zip_result["success"]:
                print(f" ✗")
                return {"success": False, "error": f"打包失败: {zip_result['error']}"}
            else: 
                print(f" √")
            
            zip_path = zip_result["zip_path"]
            zip_filename = Path(zip_path).name
            
            try:
                # 步骤2: 上传zip文件并自动解压
                # 传递文件夹上传的特殊参数
                upload_result = self.cmd_upload([zip_path], target_path, force=False, 
                                              folder_upload_info={
                                                  "is_folder_upload": True,
                                                  "zip_filename": zip_filename,
                                                  "keep_zip": keep_zip
                                              })
                if not upload_result["success"]:
                    print(f" ✗")
                    return {"success": False, "error": f"上传失败: {upload_result['error']}"}
                
                # 成功完成
                print(f" √")
                return {
                    "success": True,
                    "message": f"Uploaded folder: {folder_name}",
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
                            print(f"🧹 Cleaned up local temporary file: {zip_filename}")
                    except Exception as e:
                        print(f"⚠️ Failed to clean up temporary file: {e}")
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
            # 立即显示进度消息
            print("⏳ Waiting for upload ...", end="", flush=True)
            
            # 启动debug信息捕获
            debug_capture.start_capture()
            debug_print(f"🔧 DEBUG: cmd_upload called with source_files={source_files}, target_path='{target_path}', force={force}")
            
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
                    print(f"\n⏳ Waiting for large files manual upload ...")
                    
                    # 创建虚拟file_moves用于计算超时时间
                    virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                    sync_result = self.wait_for_file_sync(large_file_names, virtual_file_moves)
                    
                    if sync_result["success"]:
                        return {
                            "success": True,
                            "message": f"\nLarge files manual upload completed: {len(large_files)} files",
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
            debug_print(f"🔧 DEBUG: Before _resolve_target_path_for_upload - target_path='{target_path}'")
            debug_print(f"🔧 DEBUG: current_shell={current_shell}")
            target_folder_id, target_display_path = self._resolve_target_path_for_upload(target_path, current_shell)
            debug_print(f"🔧 DEBUG: After _resolve_target_path_for_upload - target_folder_id='{target_folder_id}', target_display_path='{target_display_path}'")
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
                override_check_result = self.main_instance.file_utils._check_files_to_override(source_files, target_path)
                if override_check_result["success"] and override_check_result.get("overridden_files"):
                    overridden_files = override_check_result["overridden_files"]
                    for file_path in overridden_files:
                        print(f"⚠️ Warning: Overriding remote file {file_path}")
            
            # 4. 移动文件到 LOCAL_EQUIVALENT
            file_moves = []
            failed_moves = []
            
            for source_file in source_files:
                move_result = self.main_instance.sync_manager.move_to_local_equivalent(source_file)
                if move_result["success"]:
                    file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "original_filename": move_result["original_filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"]
                    })
                else:
                    failed_moves.append({
                        "file": source_file,
                        "error": move_result.get("error", "Unknown error")
                    })
                    print(f"\n✗ {move_result['error']}")
            
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
            # 对于同步检测，使用重命名后的文件名（在DRIVE_EQUIVALENT中的实际文件名）
            expected_filenames = [fm["filename"] for fm in file_moves]
            
            sync_result = self.wait_for_file_sync(expected_filenames, file_moves)
            
            if not sync_result["success"]:
                # 同步检测失败，但继续执行
                print(f"⚠️ File sync check failed: {sync_result.get('error', 'Unknown error')}")
                print("📱 Upload may have succeeded, please manually verify files have been uploaded")
                print("💡 You can retry upload if needed")
                
                # 返回失败结果，让用户决定是否重试
                return {
                    "success": False,
                    "error": f"Upload sync verification failed: {sync_result.get('error', 'Unknown error')}",
                    "file_moves": file_moves,
                    "sync_time": sync_result.get("sync_time", 0),
                    "suggestion": "Files may have been uploaded successfully. Please check manually and retry if needed."
                }
            else:
                base_time = sync_result.get("base_sync_time", sync_result.get("sync_time", 0))
                # 静默处理文件同步完成
                sync_result["sync_time"] = base_time
            
            # 7. 静默验证文件同步状态
            self._verify_files_available(file_moves)
            
            # 8. 静默生成远端命令
            debug_print(f"🔧 DEBUG: Before generate_remote_commands - file_moves={file_moves}")
            debug_print(f"🔧 DEBUG: Before generate_remote_commands - target_path='{target_path}'")
            remote_command = self.generate_remote_commands(file_moves, target_path, folder_upload_info)
            debug_print(f"🔧 DEBUG: After generate_remote_commands - remote_command preview: {remote_command[:200]}...")
            
            # 7.5. 远端目录创建已经集成到generate_remote_commands中，无需额外处理
            
            # 8. 使用统一的远端命令执行接口
            # 对于文件夹上传，跳过文件验证因为验证的是zip文件而不是解压后的内容
            if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
                # 文件夹上传：跳过文件验证，信任远程命令执行结果
                context_info = {
                    "expected_filenames": None,  # 跳过验证
                    "sync_filenames": expected_filenames,
                    "target_folder_id": target_folder_id,
                    "target_path": target_path,
                    "file_moves": file_moves,
                    "is_folder_upload": True
                }
            else:
                # 普通文件上传：正常验证
                context_info = {
                    "expected_filenames": [fm.get("original_filename", fm["filename"]) for fm in file_moves],  # 验证阶段用原始文件名
                    "sync_filenames": expected_filenames,  # 同步阶段用重命名后的文件名
                    "target_folder_id": target_folder_id,
                    "target_path": target_path,
                    "file_moves": file_moves
                }
            
            execution_result = self.main_instance.execute_remote_command_interface(
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
            
            # 执行完成，使用返回的验证结果
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
                "message": f"\nUpload completed: {len(verify_result.get('found_files', []))}/{len(source_files)} files" if verify_result["success"] else f" ✗\n⚠️ Partially uploaded: {len(verify_result.get('found_files', []))}/{len(source_files)} files",
                "api_available": self.drive_service is not None
            }
            
            # Add debug information when upload fails or user used direct feedback
            used_direct_feedback = verify_result.get("source") == "direct_feedback"
            upload_failed = not verify_result["success"]
            
            if upload_failed or used_direct_feedback:
                if used_direct_feedback:
                    debug_print("🔧 DEBUG: User used direct feedback, showing debug information:")
                else:
                    debug_print("🔧 DEBUG: Upload failed, showing debug information:")
                
                debug_print(f"🔧 DEBUG: verify_result={verify_result}")
                debug_print(f"🔧 DEBUG: sync_result={sync_result}")
                debug_print(f"🔧 DEBUG: target_folder_id='{target_folder_id}'")
                debug_print(f"🔧 DEBUG: target_display_path='{target_display_path}'")
                
                # Also print debug capture buffer
                captured_debug = debug_capture.get_debug_info()
                if captured_debug:
                    print("🔧 DEBUG: Captured debug output:")
                    print(captured_debug)
            
            # 添加本地文件删除信息
            if remove_local and verify_result["success"]:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            # 停止debug信息捕获
            debug_capture.stop_capture()
            return result
            
        except Exception as e:
            # 停止debug信息捕获
            debug_capture.stop_capture()
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
                    return {"success": False, "error": f"Directory does not exist: {path}"}
            
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
                return {"success": False, "error": f"Directory does not exist: {path}"}
            
            shells_data = self.main_instance.load_shells()
            shell_id = current_shell['id']
            
            shells_data["shells"][shell_id]["current_path"] = target_path
            shells_data["shells"][shell_id]["current_folder_id"] = target_id
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.main_instance.save_shells(shells_data):
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

    def cmd_touch(self, filename):
        """创建空文件，通过远程命令界面执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not filename:
                return {"success": False, "error": "请指定要创建的文件名"}
            
            # 解析绝对路径
            current_path = current_shell.get("current_path", "~")
            if filename.startswith("/"):
                # 绝对路径
                absolute_path = filename.replace("~", "/content/drive/MyDrive/REMOTE_ROOT", 1)
            else:
                # 相对路径
                if current_path == "~":
                    current_path = "/content/drive/MyDrive/REMOTE_ROOT"
                else:
                    current_path = current_path.replace("~", "/content/drive/MyDrive/REMOTE_ROOT", 1)
                absolute_path = f"{current_path}/{filename}"
            
            # 生成远端touch命令（创建空文件）
            remote_command = f'touch "{absolute_path}" && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            
            # 准备上下文信息
            context_info = {
                "filename": filename,
                "absolute_path": absolute_path
            }
            
            # 使用统一接口执行远端命令
            execution_result = self.main_instance.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="touch",
                context_info=context_info
            )
            
            if execution_result["success"]:
                # 简洁返回，像bash shell一样成功时不显示任何信息
                return {
                    "success": True,
                    "filename": filename,
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
                "message": f"远端touch命令生成失败: {e}"
            }

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
            absolute_path = self.main_instance.resolve_remote_absolute_path(path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {path}"}
            
            # 构建rm命令
            rm_flags = ""
            if recursive:
                rm_flags += "r"
            if force:
                rm_flags += "f"
            
            if rm_flags:
                remote_command = f'rm -{rm_flags} "{absolute_path}" && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            else:
                remote_command = f'rm "{absolute_path}" && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            
            # 执行远程命令
            result = self.main_instance.execute_remote_command_interface(
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
                # 简化验证逻辑：如果远程命令执行完成，就认为删除成功
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

    # cmd_echo 已删除 - 统一使用 google_drive_shell.py 中的 _handle_unified_echo_command

    def _create_text_file(self, filename, content):
        """通过远程命令创建文本文件"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远程echo命令
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 使用base64编码来完全避免引号和特殊字符问题
            import base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('ascii')
            
            # 构建远程命令 - 使用base64解码避免所有引号问题
            remote_command = f'echo "{content_base64}" | base64 -d > "{remote_absolute_path}" && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            
            # 使用远程命令执行接口
            result = self.main_instance.execute_remote_command_interface(remote_command, "echo", {
                "filename": filename,
                "content": content,
                "absolute_path": remote_absolute_path
            })
            
            if result.get("success"):
                return {
                    "success": True,
                    "filename": filename,
                    "message": f"✅ 文件已创建: {filename}"
                }
            else:
                # 优先使用用户提供的错误信息
                error_msg = result.get('error_info') or result.get('error') or 'Unknown error'
                return {
                    "success": False,
                    "error": f"创建文件失败: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"创建文件时出错: {e}"}

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
                return {"success": False, "error": f"File or directory does not exist: {filename}"}
            
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
                        "error": cat_result["error_info"]
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
                local_file = self.main_instance.cache_manager._get_local_cache_path(filename)
                
                result[filename] = {
                    "local_file": local_file,
                    "occurrences": formatted_occurrences
                }
            
            return {"success": True, "result": result}
                
        except Exception as e:
            return {"success": False, "error": f"Grep command error: {e}"}

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
                move_result = self.main_instance.move_to_local_equivalent(src_file)
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
                        "error": move_result["error_info"]
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
            
            execution_result = self.main_instance.execute_remote_command_interface(
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
            cache_manager_path = Path(__file__).parent.parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "缓存管理器未找到"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远端绝对路径
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
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
                abs_source_path = self.main_instance.resolve_remote_absolute_path(source, current_shell)
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
                
                # 简化版本：不进行复杂的冲突检查
                
                validated_pairs.append([source, destination])
            
            # 生成多文件mv的远端命令
            remote_command = self._generate_multi_mv_remote_commands(validated_pairs, current_shell)
            
            # 执行远端命令
            context_info = {
                "file_pairs": validated_pairs,
                "multi_file": True
            }
            
            result = self.main_instance.execute_remote_command_interface(
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
            
            # 简化版本：不进行复杂的冲突检查
            
            # 构建远端mv命令 - 需要计算绝对路径
            source_absolute_path = self.main_instance.resolve_remote_absolute_path(source, current_shell)
            destination_absolute_path = self.main_instance.resolve_remote_absolute_path(destination, current_shell)
            
            # 构建增强的远端命令，包含成功/失败提示
            base_command = f"mv {source_absolute_path} {destination_absolute_path}"
            remote_command = f"({base_command}) && clear && echo \"✅ 执行完成\" || echo \"❌ 执行失败\""
            
            # 使用远端指令执行接口
            result = self.main_instance.execute_remote_command_interface(remote_command, "move", {
                "source": source,
                "destination": destination
            })
            
            if result.get("success"):
                return {
                    "success": True,
                    "source": source,
                    "destination": destination,
                    "message": f"✅ 已移动 {source} -> {destination}"
                }
            else:
                # 优先使用用户提供的错误信息
                error_msg = result.get('error_info') or result.get('error') or 'Unknown error'
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

    def cmd_python(self, code=None, filename=None, python_args=None, save_output=False):
        """python命令 - 执行Python代码"""
        try:
            if filename:
                # 执行Drive中的Python文件
                return self._execute_python_file(filename, save_output, python_args)
            elif code:
                # 执行直接提供的Python代码
                return self._execute_python_code(code, save_output)
            else:
                return {"success": False, "error": "请提供Python代码或文件名"}
                
        except Exception as e:
            return {"success": False, "error": f"执行Python命令时出错: {e}"}

    def _execute_python_file(self, filename, save_output=False, python_args=None):
        """执行Google Drive中的Python文件"""
        try:
            # 直接在远端执行Python文件，不需要先读取文件内容
            return self._execute_python_file_remote(filename, save_output, python_args)
            
        except Exception as e:
            return {"success": False, "error": f"执行Python文件时出错: {e}"}
    
    def _execute_python_file_remote(self, filename, save_output=False, python_args=None):
        """远程执行Python文件"""
        try:
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
            env_file = f"{tmp_dir}/venv_env_{shell_id}.sh"
            
            # 构建Python命令，包含文件名和参数
            python_cmd_parts = ['python3', filename]
            if python_args:
                python_cmd_parts.extend(python_args)
            python_cmd = ' '.join(python_cmd_parts)
            
            # 构建远程命令：检查并应用虚拟环境，然后执行Python文件
            commands = [
                # source环境文件，如果失败则忽略（会使用默认的PYTHONPATH）
                f"source {env_file} 2>/dev/null || true",
                python_cmd
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success"):
                return {
                    "success": True,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "return_code": result.get("exit_code", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"Remote Python file execution failed: {result.get('error', '')}",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python文件执行时出错: {e}"}

    def _execute_python_code(self, code, save_output=False, filename=None):
        """执行Python代码并返回结果"""
        try:
            # 直接尝试远程执行，在远程命令中检查和应用虚拟环境
            return self._execute_python_code_remote_unified(code, save_output, filename)
                
        except Exception as e:
            return {"success": False, "error": f"执行Python代码时出错: {e}"}

    def _execute_python_code_remote_unified(self, code, save_output=False, filename=None):
        """统一的远程Python执行方法，在一个命令中检查虚拟环境并执行代码"""
        try:
            import base64
            import time
            import random
            
            # 使用base64编码避免所有bash转义问题
            code_bytes = code.encode('utf-8')
            code_base64 = base64.b64encode(code_bytes).decode('ascii')
            
            # 生成唯一的临时文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            temp_filename = f"python_code_{timestamp}_{random_id}.b64"
            
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
            env_file = f"{tmp_dir}/venv_env_{shell_id}.sh"
            temp_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{temp_filename}"
            
            # 构建统一的远程命令：
            # 1. 确保tmp目录存在
            # 2. 将base64字符串写入临时文件
            # 3. source环境文件
            # 4. 从临时文件读取base64并解码执行
            # 5. 清理临时文件
            commands = [
                # 确保tmp目录存在
                f"mkdir -p {self.main_instance.REMOTE_ROOT}/tmp",
                # 将base64编码的Python代码写入临时文件
                f'echo "{code_base64}" > "{temp_file_path}"',
                # source环境文件，如果失败则忽略（会使用默认的PYTHONPATH）
                f"source {env_file} 2>/dev/null || true",
                # 从临时文件读取base64，解码并执行Python代码
                f'python3 -c "import base64; exec(base64.b64decode(open(\\"{temp_file_path}\\").read().strip()).decode(\\"utf-8\\"))"',
                # 清理临时文件
                f'rm -f "{temp_file_path}"'
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success"):
                return {
                    "success": True,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "return_code": result.get("exit_code", 0),
                    "source": result.get("source", "")
                }
            else:
                return {
                    "success": False,
                    "error": f"User direct feedback is as above. ",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python执行时出错: {e}"}

    def _execute_non_bash_safe_commands(self, commands, action_description, context_name=None, expected_pythonpath=None):
        """
        生成非bash-safe命令供用户在远端主shell中执行，并自动验证结果
        """
        try:
            import time
            import random
            import json
            import os
            
            # 生成唯一的结果文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            result_filename = f"venv_result_{timestamp}_{random_id}.json"
            # 生成远程和本地文件路径
            import os
            bin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            local_result_file = f"{bin_dir}/GOOGLE_DRIVE_DATA/remote_files/{result_filename}"
            # 使用远程路径而不是本地路径
            remote_result_file = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/{result_filename}"
            
            # 生成包含验证的完整命令
            original_command = " && ".join(commands)
            full_commands = [
                "mkdir -p /content/drive/MyDrive/REMOTE_ROOT/tmp",  # 确保远程tmp目录存在
                original_command,
                # 验证PYTHONPATH并输出到远程JSON文件
                f'echo "{{" > {remote_result_file}',
                f'echo "  \\"success\\": true," >> {remote_result_file}',
                f'echo "  \\"action\\": \\"{action_description}\\"," >> {remote_result_file}',
                f'echo "  \\"pythonpath\\": \\"$PYTHONPATH\\"," >> {remote_result_file}',
                f'echo "  \\"timestamp\\": \\"$(date)\\"" >> {remote_result_file}',
                f'echo "}}" >> {remote_result_file}'
            ]
            
            full_command_with_verification = " && ".join(full_commands)
            
            # 使用统一的tkinter窗口界面
            context_str = f" '{context_name}'" if context_name else ""
            window_title = f"Execute command to {action_description}{context_str}"
            
            # 调用统一的远程命令窗口
            try:
                result = self.main_instance.remote_commands._show_generic_command_window(
                    action_description,  # cmd
                    [context_name] if context_name else [],  # args
                    full_command_with_verification,  # remote_command
                    window_title  # debug_info
                )
                
                if result.get("action") == "failed":
                    return {
                        "success": False, 
                        "error": result.get("message", "User reported execution failed"),
                        "source": "user_reported_failure"
                    }
                elif result.get("action") == "direct_feedback":
                    # 用户提供了直接反馈，跳过文件检测
                    print ()
                    return {
                        "success": True,
                        "message": result.get("message", "Command executed successfully"),
                        "source": "direct_feedback"
                    }
            except Exception as e:
                # 如果tkinter窗口失败，回退到终端提示
                print(f"\n🔧 Execute the following command in remote main shell to {action_description}{context_str}:")
                print(f"Command: {full_command_with_verification}")
                print("💡 Copy and execute the above command, then press Ctrl+D")
            
            # 如果使用了tkinter窗口，等待文件检测
            remote_file_path = f"~/tmp/{result_filename}"
            
            # 等待并检测结果文件
            print("⏳ Validating results ...", end="", flush=True)
            max_attempts = 60
            
            for attempt in range(max_attempts):
                try:
                    # 检查远程文件是否存在
                    check_result = self.main_instance.remote_commands._check_remote_file_exists_absolute(remote_result_file)
                    
                    if check_result.get("exists"):
                        # 文件存在，读取内容
                        print("√")  # 成功标记
                        read_result = self.main_instance.remote_commands._read_result_file_via_gds(result_filename)
                        
                        if read_result.get("success"):
                            result_data = read_result.get("data", {})
                            
                            # 验证结果（PYTHONPATH验证或其他验证）
                            if expected_pythonpath:
                                # PYTHONPATH验证模式（用于虚拟环境）
                                actual_pythonpath = result_data.get("pythonpath", "")
                                
                                if expected_pythonpath in actual_pythonpath:
                                    return {
                                        "success": True,
                                        "message": f"{action_description.capitalize()}{context_str} completed and verified",
                                        "pythonpath": actual_pythonpath,
                                        "result_data": result_data
                                    }
                                else:
                                    return {
                                        "success": False,
                                        "error": f"PYTHONPATH verification failed: expected {expected_pythonpath}, got {actual_pythonpath}",
                                        "result_data": result_data
                                    }
                            else:
                                # 通用验证模式（用于pip等命令）
                                return {
                                    "success": True,
                                    "message": f"{action_description.capitalize()}{context_str} completed successfully",
                                    "result_data": result_data
                                }
                        else:
                            return {"success": False, "error": f"Error reading result: {read_result.get('error')}"}
                    
                    # 文件不存在，等待1秒并输出进度点
                    time.sleep(1)
                    print(".", end="", flush=True)
                    
                except Exception as e:
                    print(f"\n❌ Error checking result file: {str(e)[:100]}")
                    return {"success": False, "error": f"Error checking result: {e}"}
            
            print(f"\n❌ Timeout: No result file found after {max_attempts} seconds")
            return {"success": False, "error": "Execution timeout - no result file found"}
            
        except Exception as e:
            print(f"Error: {e}")
            return {"success": False, "error": f"Error generating command: {e}"}

    def _get_current_venv(self):
        """获取当前激活的虚拟环境名称"""
        debug_print("_get_current_venv called")
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                debug_print("No current shell found")
                return None
            
            shell_id = current_shell.get("id", "default")
            tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
            current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
            debug_print(f"Checking venv file: {current_venv_file}")
            
            # 通过远程命令检查虚拟环境状态文件
            check_command = f'cat "{current_venv_file}" 2>/dev/null || echo "none"'
            debug_print("About to call execute_generic_remote_command for GET_CURRENT_VENV")
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", check_command])
            debug_print(f"execute_generic_remote_command for GET_CURRENT_VENV returned: success={result.get('success')}")
            
            if result.get("success") and result.get("stdout"):
                venv_name = result["stdout"].strip()
                return venv_name if venv_name != "none" else None
            
            return None
            
        except Exception as e:
            print(f"⚠️ 获取当前虚拟环境失败: {e}")
            return None

    def _execute_python_code_remote(self, code, venv_name, save_output=False, filename=None):
        """在远程虚拟环境中执行Python代码"""
        try:
            # 转义Python代码中的引号和反斜杠
            escaped_code = code.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
            
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
            env_file = f"{tmp_dir}/venv_env_{shell_id}.sh"
            
            # 构建远程命令：source环境文件并执行Python代码
            commands = [
                # source环境文件，如果失败则忽略
                f"source {env_file} 2>/dev/null || true",
                f'python3 -c "{escaped_code}"'
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success"):
                return {
                    "success": True,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "return_code": result.get("exit_code", 0),
                    "environment": venv_name
                }
            else:
                return {
                    "success": False,
                    "error": f"User directed feedback is as above. ",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python执行时出错: {e}"}

    def _execute_python_code_local(self, code, save_output=False, filename=None):
        """在本地执行Python代码"""
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
            absolute_path = self.main_instance._resolve_absolute_mkdir_path(target_path, current_shell, recursive)
            if not absolute_path:
                return {"success": False, "error": f"无法解析路径: {target_path}"}
            
            # 生成远端mkdir命令，添加清屏和成功/失败提示（总是使用-p确保父目录存在）
            remote_command = f'mkdir -p "{absolute_path}" && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            
            # 准备上下文信息
            context_info = {
                "target_path": target_path,
                "absolute_path": absolute_path,
                "recursive": recursive
            }
            
            # 使用统一接口执行远端命令
            execution_result = self.main_instance.execute_remote_command_interface(
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

    def _parse_line_ranges(self, args):
        """
        解析行数范围参数
        
        参数格式:
        - 无参数: 返回None (读取全部)
        - 单个数字: 返回[(start, None)] (从start行开始读取到末尾)
        - 两个数字: 返回[(start, end)] (读取start到end行)
        - JSON格式多范围: "[[start1, end1], [start2, end2], ...]"
        
        返回:
        - None: 读取全部行
        - [(start, end), ...]: 行数范围列表
        - False: 参数格式错误
        - {"error_info": str}: 错误信息
        """
        try:
            # 过滤掉None参数
            filtered_args = [arg for arg in args if arg is not None]
            
            if not filtered_args:
                return None  # 读取全部
            
            # 检查是否是被空格分割的JSON字符串，尝试重新组合
            if len(filtered_args) > 1 and any(arg.startswith('[') for arg in filtered_args):
                # 尝试将所有参数连接成一个JSON字符串
                combined_arg = ' '.join(str(arg) for arg in filtered_args)
                if combined_arg.startswith('[') and combined_arg.endswith(']'):
                    try:
                        import json
                        ranges = json.loads(combined_arg)
                        if isinstance(ranges, list):
                            # 成功解析为JSON，处理多范围
                            parsed_ranges = []
                            for range_item in ranges:
                                if not isinstance(range_item, list) or len(range_item) != 2:
                                    return {"error_info": "每个范围必须是包含两个数字的列表 [start, end]"}
                                
                                start, end = range_item
                                if not isinstance(start, int) or not isinstance(end, int):
                                    return {"error_info": "范围的起始和结束位置必须是整数"}
                                
                                if start < 0 or end < 0:
                                    return {"error_info": "行号不能为负数"}
                                
                                if start > end:
                                    return {"error_info": f"起始行号({start})不能大于结束行号({end})"}
                                
                                parsed_ranges.append((start, end))
                            
                            return parsed_ranges
                    except json.JSONDecodeError:
                        pass  # 继续处理其他情况
            
            if len(filtered_args) == 1:
                # 单个参数：可能是数字或JSON格式的多范围
                arg = filtered_args[0]
                
                # 检查是否是JSON格式的多范围
                if isinstance(arg, str) and arg.strip().startswith('['):
                    try:
                        import json
                        ranges = json.loads(arg)
                        if not isinstance(ranges, list):
                            return {"error_info": "多范围格式必须是列表"}
                        
                        parsed_ranges = []
                        for range_item in ranges:
                            if not isinstance(range_item, list) or len(range_item) != 2:
                                return {"error_info": "每个范围必须是包含两个数字的列表 [start, end]"}
                            
                            start, end = range_item
                            if not isinstance(start, int) or not isinstance(end, int):
                                return {"error_info": "范围的起始和结束位置必须是整数"}
                            
                            if start < 0 or end < 0:
                                return {"error_info": "行号不能为负数"}
                            
                            if start > end:
                                return {"error_info": f"起始行号({start})不能大于结束行号({end})"}
                            
                            parsed_ranges.append((start, end))
                        
                        return parsed_ranges
                    
                    except json.JSONDecodeError as e:
                        return {"error_info": f"JSON格式错误: {str(e)}"}
                
                # 尝试解析为单个数字
                try:
                    start = int(arg)
                    if start < 0:
                        return {"error_info": "行号不能为负数"}
                    return [(start, None)]
                except ValueError:
                    return {"error_info": "参数必须是数字或有效的JSON格式多范围"}
            
            elif len(filtered_args) == 2:
                # 两个参数：读取指定范围
                try:
                    start = int(filtered_args[0])
                    end = int(filtered_args[1])
                    if start < 0 or end < 0:
                        return {"error_info": "行号不能为负数"}
                    if start > end:
                        return {"error_info": "起始行号不能大于结束行号"}
                    return [(start, end)]
                except ValueError:
                    return {"error_info": "行号必须是数字"}
            
            else:
                return {"error_info": "参数过多，支持格式: read file [start end] 或 read file '[[start1,end1],[start2,end2]]'"}
                
        except Exception as e:
            return {"error_info": f"解析行数范围时出错: {e}"}

    def _download_and_get_content(self, filename, remote_absolute_path, force=False):
        """
        下载文件并获取内容（用于read命令）
        
        Args:
            filename (str): 文件名
            remote_absolute_path (str): 远程绝对路径
            force (bool): 是否强制下载并更新缓存
        """
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 解析路径以获取目标文件夹和文件名
            path_parts = remote_absolute_path.strip('/').split('/')
            actual_filename = path_parts[-1]
            
            # 对于绝对路径，需要特殊处理
            if remote_absolute_path.startswith('/content/drive/MyDrive/REMOTE_ROOT/'):
                # 移除前缀，获取相对于REMOTE_ROOT的路径
                relative_path = remote_absolute_path.replace('/content/drive/MyDrive/REMOTE_ROOT/', '')
                relative_parts = relative_path.split('/')
                actual_filename = relative_parts[-1]
                parent_relative_path = '/'.join(relative_parts[:-1]) if len(relative_parts) > 1 else ''
                
                if parent_relative_path:
                    # 转换为~路径格式
                    parent_logical_path = '~/' + parent_relative_path
                    resolve_result = self.main_instance.path_resolver.resolve_path(parent_logical_path, current_shell)
                    if isinstance(resolve_result, tuple) and len(resolve_result) >= 2:
                        target_folder_id, _ = resolve_result
                        if not target_folder_id:
                            return {"success": False, "error": f"无法解析目标路径: {parent_logical_path}"}
                    else:
                        return {"success": False, "error": f"路径解析返回格式错误: {parent_logical_path}"}
                else:
                    # 文件在REMOTE_ROOT根目录
                    target_folder_id = self.main_instance.REMOTE_ROOT_FOLDER_ID
            else:
                # 使用当前shell的文件夹ID
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            
            # 在目标文件夹中查找文件
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not result['success']:
                return {"success": False, "error": f"无法列出文件夹内容: {result.get('error', '未知错误')}"}
            
            file_info = None
            files = result['files']
            for file in files:
                if file['name'] == actual_filename:
                    file_info = file
                    break
            
            if not file_info:
                return {"success": False, "error": f"File does not exist: {actual_filename}"}
            
            # 检查是否为文件（不是文件夹）
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"{actual_filename} 是一个目录，无法读取"}
            
            # 使用Google Drive API下载文件内容
            try:
                file_id = file_info['id']
                request = self.drive_service.service.files().get_media(fileId=file_id)
                content = request.execute()
                
                # 将字节内容转换为字符串
                if isinstance(content, bytes):
                    try:
                        content_str = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            content_str = content.decode('gbk')
                        except UnicodeDecodeError:
                            content_str = content.decode('utf-8', errors='replace')
                else:
                    content_str = str(content)
                

                
                return {
                    "success": True,
                    "content": content_str,
                    "file_info": file_info
                }
                
            except Exception as e:
                return {"success": False, "error": f"下载文件内容失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"下载和获取内容时出错: {e}"}

    def _format_read_output(self, selected_lines):
        """
        格式化读取输出
        
        Args:
            selected_lines: 包含(line_number, line_content)元组的列表
            
        Returns:
            str: 格式化后的输出字符串
        """
        if not selected_lines:
            return ""
        
        # 格式化每行，显示行号和内容
        formatted_lines = ["line_num: line_content"]
        for line_num, line_content in selected_lines:
            # 行号从0开始, 0-indexed
            formatted_lines.append(f"{line_num:4d}: {line_content}")
        
        return "\n".join(formatted_lines)

    def cmd_read(self, filename, *args, force=False):
        """读取远端文件内容，支持智能缓存和行数范围
        
        Args:
            filename (str): 文件名
            *args: 行数范围参数
            force (bool): 是否强制从远端重新下载，忽略缓存
        """
        try:
            if not filename:
                return {"success": False, "error": "请指定要读取的文件"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            if not remote_absolute_path:
                return {"success": False, "error": f"无法解析文件路径: {filename}"}
            
            line_ranges = self._parse_line_ranges(args)
            
            if line_ranges is False:
                return {"success": False, "error": "行数范围参数格式错误"}
            elif isinstance(line_ranges, dict) and "error" in line_ranges:
                return {"success": False, "error": line_ranges["error_info"]}
            
            file_content = None
            source = "unknown"
            
            # 确保Path已导入
            from pathlib import Path
            
            # 如果force=True，跳过缓存检查，直接下载并更新缓存
            if force:
                # 使用cmd_download来下载并更新缓存
                download_result = self.cmd_download(filename, force=True)
                if not download_result["success"]:
                    return download_result
                
                # 从缓存读取内容
                cache_status = self.main_instance.is_remote_file_cached(remote_absolute_path)
                cache_file_path = cache_status["cache_file_path"]
                
                if cache_file_path and Path(cache_file_path).exists():
                    with open(cache_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_content = f.read()
                    source = "download (forced)"
                else:
                    return {"success": False, "error": "Failed to read from updated cache"}
            else:
                # 正常的缓存检查逻辑
                freshness_result = self.main_instance.is_cached_file_up_to_date(remote_absolute_path)
                
                if (freshness_result["success"] and 
                    freshness_result["is_cached"] and 
                    freshness_result["is_up_to_date"]):
                    
                    cache_status = self.main_instance.is_remote_file_cached(remote_absolute_path)
                    cache_file_path = cache_status["cache_file_path"]
                    
                    if cache_file_path and Path(cache_file_path).exists():
                        with open(cache_file_path, 'r', encoding='utf-8', errors='replace') as f:
                            file_content = f.read()
                        source = "cache"
                    else:
                        download_result = self._download_and_get_content(filename, remote_absolute_path, force=False)
                        if not download_result["success"]:
                            return download_result
                        file_content = download_result["content"]
                        source = "download"
                else:
                    download_result = self._download_and_get_content(filename, remote_absolute_path, force=False)
                    if not download_result["success"]:
                        return download_result
                    file_content = download_result["content"]
                    source = "download"
            
            lines = file_content.split('\n')
            
            if not line_ranges:
                selected_lines = [(i, line) for i, line in enumerate(lines)]
            else:
                selected_lines = []
                
                for range_item in line_ranges:
                    try:
                        # 尝试解包
                        if isinstance(range_item, (tuple, list)) and len(range_item) == 2:
                            start, end = range_item
                        else:
                            return {"success": False, "error": f"Invalid range format: {range_item}"}
                            
                        # 处理行数范围
                        if end is None:
                            # 从start行开始到文件末尾
                            for i in range(max(0, start), len(lines)):
                                selected_lines.append((i, lines[i]))
                        else:
                            # 从start行到end行
                            for i in range(max(0, start), min(len(lines), end + 1)):
                                selected_lines.append((i, lines[i]))
                                
                    except Exception as e:
                        return {"success": False, "error": f"Error processing line range: {e}"}
            
            formatted_output = self._format_read_output(selected_lines)
            
            return {
                "success": True,
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

    def _parse_find_args(self, args):
        """解析find命令参数"""
        try:
            args_list = list(args)
            
            # 默认值
            path = "."
            pattern = "*"
            case_sensitive = True
            file_type = None  # None=both, "f"=files, "d"=directories
            
            i = 0
            while i < len(args_list):
                arg = args_list[i]
                
                if arg == "-name" and i + 1 < len(args_list):
                    pattern = args_list[i + 1]
                    case_sensitive = True
                    i += 2
                elif arg == "-iname" and i + 1 < len(args_list):
                    pattern = args_list[i + 1]
                    case_sensitive = False
                    i += 2
                elif arg == "-type" and i + 1 < len(args_list):
                    file_type = args_list[i + 1]
                    if file_type not in ["f", "d"]:
                        return {"success": False, "error": "无效的文件类型，使用 'f' (文件) 或 'd' (目录)"}
                    i += 2
                elif not arg.startswith("-"):
                    # 这是路径参数
                    path = arg
                    i += 1
                else:
                    i += 1
            
            return {
                "success": True,
                "path": path,
                "pattern": pattern,
                "case_sensitive": case_sensitive,
                "file_type": file_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"参数解析错误: {e}"}
    
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
                "error": f"Find command error: {e}"
            }

    def _recursive_find(self, search_path, pattern, case_sensitive=True, file_type=None):
        """
        递归查找匹配的文件和目录
        
        Args:
            search_path: 搜索路径
            pattern: 搜索模式（支持通配符）
            case_sensitive: 是否大小写敏感
            file_type: 文件类型过滤 ("f" for files, "d" for directories, None for both)
        
        Returns:
            dict: {"success": bool, "files": list, "error": str}
        """
        try:
            import fnmatch
            
            # 解析搜索路径
            if search_path == ".":
                # 使用当前shell路径
                current_shell = self.main_instance.get_current_shell()
                if current_shell:
                    search_path = current_shell.get("current_path", "~")
            
            # 将~转换为实际的REMOTE_ROOT路径
            if search_path.startswith("~"):
                search_path = search_path.replace("~", "/content/drive/MyDrive/REMOTE_ROOT", 1)
            
            # 生成远程find命令
            find_cmd_parts = ["find", f'"{search_path}"']
            
            # 添加文件类型过滤
            if file_type == "f":
                find_cmd_parts.append("-type f")
            elif file_type == "d":
                find_cmd_parts.append("-type d")
            
            # 添加名称模式
            if case_sensitive:
                find_cmd_parts.append(f'-name "{pattern}"')
            else:
                find_cmd_parts.append(f'-iname "{pattern}"')
            
            find_command = " ".join(find_cmd_parts)
            
            # 执行远程find命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", find_command])
            
            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                if stdout:
                    # 分割输出为文件路径列表
                    files = [line.strip() for line in stdout.split("\n") if line.strip()]
                    return {
                        "success": True,
                        "files": files
                    }
                else:
                    return {
                        "success": True,
                        "files": []
                    }
            else:
                return {
                    "success": False,
                    "error": f"Remote find command failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing find: {e}"
            }

    def _generate_edit_diff(self, original_lines, modified_lines, parsed_replacements):
        """
        生成编辑差异信息
        
        Args:
            original_lines: 原始文件行列表
            modified_lines: 修改后文件行列表
            parsed_replacements: 解析后的替换操作列表
            
        Returns:
            dict: 差异信息
        """
        try:
            import difflib
            
            # 生成unified diff
            diff = list(difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile='original',
                tofile='modified',
                lineterm=''
            ))
            
            # 统计变更信息
            lines_added = len(modified_lines) - len(original_lines)
            changes_count = len(parsed_replacements)
            
            # 生成简化的变更摘要
            changes_summary = []
            for replacement in parsed_replacements:
                if replacement["type"] == "line_range":
                    changes_summary.append(f"Lines {replacement['start_line']}-{replacement['end_line']}: range replacement")
                elif replacement["type"] == "line_insert":
                    changes_summary.append(f"Line {replacement['insert_line']}: content insertion")
                elif replacement["type"] == "text_search":
                    changes_summary.append(f"Text search: '{replacement['old_text'][:50]}...' -> '{replacement['new_text'][:50]}...'")
            
            return {
                "diff_lines": diff,
                "lines_added": lines_added,
                "changes_count": changes_count,
                "changes_summary": changes_summary,
                "original_line_count": len(original_lines),
                "modified_line_count": len(modified_lines)
            }
            
        except Exception as e:
            return {
                "error": f"Failed to generate diff: {e}",
                "diff_lines": [],
                "lines_added": 0,
                "changes_count": 0,
                "changes_summary": []
            }

    def _generate_local_diff_preview(self, filename, original_lines, modified_lines, parsed_replacements):
        """
        生成本地diff预览，只显示修改的部分
        
        Args:
            filename (str): 文件名
            original_lines (list): 原始文件行
            modified_lines (list): 修改后文件行
            parsed_replacements (list): 解析后的替换操作
            
        Returns:
            dict: 包含diff输出和变更摘要
        """
        try:
            import tempfile
            import os
            import subprocess
            import hashlib
            import time
            
            # 创建临时目录
            temp_base_dir = os.path.join(os.path.expanduser("~"), ".local", "bin", "GOOGLE_DRIVE_DATA", "tmp")
            os.makedirs(temp_base_dir, exist_ok=True)
            
            # 生成带时间戳的哈希文件名
            timestamp = str(int(time.time() * 1000))
            content_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
            
            original_filename = f"{content_hash}_{timestamp}_original.tmp"
            modified_filename = f"{content_hash}_{timestamp}_modified.tmp"
            
            original_path = os.path.join(temp_base_dir, original_filename)
            modified_path = os.path.join(temp_base_dir, modified_filename)
            
            try:
                # 写入原始文件
                with open(original_path, 'w', encoding='utf-8') as f:
                    f.writelines(original_lines)
                
                # 写入修改后文件
                with open(modified_path, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
                
                # 执行diff命令
                diff_cmd = ['diff', '-u', original_path, modified_path]
                result = subprocess.run(diff_cmd, capture_output=True, text=True, encoding='utf-8')
                
                # diff命令返回码：0=无差异，1=有差异，2=错误
                if result.returncode == 0:
                    diff_output = "No changes detected"
                elif result.returncode == 1:
                    # 有差异，处理输出
                    diff_lines = result.stdout.splitlines()
                    # 移除文件路径行，只保留差异内容
                    filtered_lines = []
                    for line in diff_lines:
                        if line.startswith('---') or line.startswith('+++'):
                            # 替换临时文件路径为实际文件名
                            if line.startswith('---'):
                                filtered_lines.append(f"--- {filename} (original)")
                            elif line.startswith('+++'):
                                filtered_lines.append(f"+++ {filename} (modified)")
                        else:
                            filtered_lines.append(line)
                    diff_output = '\n'.join(filtered_lines)
                else:
                    diff_output = f"Diff command error: {result.stderr}"
                
                # 生成变更摘要
                changes_summary = []
                for replacement in parsed_replacements:
                    if replacement["type"] == "line_range":
                        changes_summary.append(f"Lines {replacement['start_line']}-{replacement['end_line']}: range replacement")
                    elif replacement["type"] == "line_insert":
                        changes_summary.append(f"Line {replacement['insert_line']}: content insertion")
                    elif replacement["type"] == "text_search":
                        changes_summary.append(f"Text search: '{replacement['old_text'][:50]}...' -> '{replacement['new_text'][:50]}...'")
                
                return {
                    "diff_output": diff_output,
                    "changes_summary": changes_summary,
                    "temp_files_created": [original_path, modified_path]
                }
                
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(original_path):
                        os.unlink(original_path)
                    if os.path.exists(modified_path):
                        os.unlink(modified_path)
                except Exception as cleanup_error:
                    # 清理失败不影响主要功能
                    pass
                    
        except Exception as e:
            return {
                "diff_output": f"Failed to generate diff preview: {str(e)}",
                "changes_summary": [],
                "temp_files_created": []
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
        2. 行号插入: '[[[1, null], "content to insert"], [[5, null], "another insert"]]'
        3. 文本搜索替换: '[["old text", "new text"], ["another old", "another new"]]'
        4. 混合模式: '[[[1, 1], "line replacement"], [[3, null], "insertion"], ["text", "replace"]]'
        """
        # Debug信息收集器
        debug_info = []
        # 初始化变量以避免作用域问题
        files_to_upload = []
        
        def debug_log(message):
            debug_info.append(message)
        
        try:
            
            import json
            import re
            import tempfile
            import shutil
            import os
            from datetime import datetime
            
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent.parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "Cache manager not found"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 1. 解析替换规范
            try:
                replacements = json.loads(replacement_spec)
                if not isinstance(replacements, list):
                    return {"success": False, "error": "Replacement specification must be an array"}
            except json.JSONDecodeError as e:
                # 提供更有建设性的错误信息
                error_msg = f"JSON parsing failed: {e}\n\n"
                error_msg += "Common issues:\n"
                error_msg += "1. Missing quotes around strings\n"
                error_msg += "2. Unescaped quotes inside strings (use \\\" instead of \")\n" 
                error_msg += "3. Missing commas between array elements\n"
                error_msg += "4. Shell quote conflicts. Try using single quotes around JSON\n\n"
                error_msg += f"Your input: {repr(replacement_spec)}\n"
                error_msg += "Correct format examples:\n"
                error_msg += "  Text replacement: '[[\"old\", \"new\"]]'\n"
                error_msg += "  Line replacement: '[[[1, 3], \"new content\"]]'\n"
                error_msg += "  Mixed: '[[[1, 2], \"line\"], [\"old\", \"new\"]]'"
                return {"success": False, "error": error_msg}
            
            # 2. 下载文件到缓存
            download_result = self.cmd_download(filename, force=True)  # 强制重新下载确保最新内容
            if not download_result["success"]:
                return {"success": False, "error": f"{download_result.get('error')}"}  #TODO
            
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            if not cache_file_path or not os.path.exists(cache_file_path):
                return {"success": False, "error": "Failed to get cache file path"}
            
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
                    return {"success": False, "error": "Unsupported file encoding, please ensure the file is UTF-8 or GBK encoded"}
            except Exception as e:
                return {"success": False, "error": f"Failed to read file: {e}"}
            
            # 4. 解析和验证替换操作
            parsed_replacements = []
            for i, replacement in enumerate(replacements):
                if not isinstance(replacement, list) or len(replacement) != 2:
                    return {"success": False, "error": f"Replacement specification item {i+1} has incorrect format, should be [source, target] format"}
                
                source, target = replacement
                
                if isinstance(source, list) and len(source) == 2:
                    start_line, end_line = source
                    
                    # 检查插入模式：[a, null] 或 [a, ""] 或 [a, None]
                    if end_line is None or end_line == "" or end_line == "null":
                        # 插入模式: [[line_number, null], "content_to_insert"]
                        if not isinstance(start_line, int):
                            return {"success": False, "error": f"Insert mode requires integer line number, got: {start_line}"}
                        
                        if start_line < 0 or start_line > len(original_lines):
                            return {"success": False, "error": f"Insert line number error: {start_line} (valid range: 0-{len(original_lines)}, 0-based index)"}
                        
                        parsed_replacements.append({
                            "type": "line_insert",
                            "insert_after_idx": start_line,
                            "insert_line": start_line,
                            "new_content": target,
                            "original_content": ""  # 插入模式没有原始内容
                        })
                        
                    elif isinstance(start_line, int) and isinstance(end_line, int):
                        # 替换模式: [[start_line, end_line], "new_content"] (0-based, [a, b] 包含语法)
                        # 使用0-based索引，[a, b] 包含语法，与read命令保持一致
                        start_idx = start_line
                        end_idx = end_line  # end_line是inclusive的
                        
                        if start_idx < 0 or start_idx >= len(original_lines) or end_line >= len(original_lines) or start_idx > end_idx:
                            return {"success": False, "error": f"Line number range error: [{start_line}, {end_line}] in file with {len(original_lines)} lines (0-based index)"}
                        
                        parsed_replacements.append({
                            "type": "line_range",
                            "start_idx": start_idx,
                            "end_idx": end_idx,
                            "start_line": start_line,
                            "end_line": end_line,
                            "new_content": target,
                            "original_content": "".join(original_lines[start_idx:end_line + 1]).rstrip()
                        })
                    else:
                        return {"success": False, "error": f"Invalid line specification: [{start_line}, {end_line}]. Use [start, end] for replacement or [line, null] for insertion."}
                    
                elif isinstance(source, str):
                    # 文本搜索替换模式: ["old_text", "new_text"]
                    if source not in "".join(original_lines):
                        return {"success": False, "error": f"Text not found to replace: {source[:50]}..."}
                    
                    parsed_replacements.append({
                        "type": "text_search",
                        "old_text": source,
                        "new_text": target
                    })
                else:
                    return {"success": False, "error": f"Source format for replacement specification item {i+1} is not supported, should be line number array [start, end] or text string"}
            
            # 5. 执行替换和插入操作
            modified_lines = original_lines.copy()
            
            # 先处理插入操作（按行号倒序，避免行号变化影响后续插入）
            line_insertions = [r for r in parsed_replacements if r["type"] == "line_insert"]
            line_insertions.sort(key=lambda x: x["insert_after_idx"], reverse=True)
            
            for insertion in line_insertions:
                insert_after_idx = insertion["insert_after_idx"]
                new_content = insertion["new_content"]
                
                # 将新内容按换行符拆分成行列表，正确处理\n
                if new_content:
                    # 处理换行符，将\n转换为实际换行
                    processed_content = new_content.replace('\\n', '\n')
                    # 处理空格占位符，支持多种格式
                    processed_content = processed_content.replace('_SPACE_', ' ')  # 单个空格
                    processed_content = processed_content.replace('_SP_', ' ')     # 简写形式
                    processed_content = processed_content.replace('_4SP_', '    ') # 4个空格（常用缩进）
                    processed_content = processed_content.replace('_TAB_', '\t')   # 制表符
                    new_lines = processed_content.split('\n')
                    
                    # 确保每行都以换行符结尾
                    formatted_new_lines = []
                    for i, line in enumerate(new_lines):
                        if i < len(new_lines) - 1:  # 不是最后一行
                            formatted_new_lines.append(line + '\n')
                        else:  # 最后一行
                            formatted_new_lines.append(line + '\n')  # 插入的内容总是添加换行符
                    
                    # 在指定行之后插入内容
                    # insert_after_idx = 0 表示在第0行后插入（即第1行之前）
                    # insert_after_idx = len(lines) 表示在文件末尾插入
                    insert_position = insert_after_idx + 1 if insert_after_idx < len(modified_lines) else len(modified_lines)
                    modified_lines[insert_position:insert_position] = formatted_new_lines
            
            # 然后按行号倒序处理行替换，避免行号变化影响后续替换
            line_replacements = [r for r in parsed_replacements if r["type"] == "line_range"]
            line_replacements.sort(key=lambda x: x["start_idx"], reverse=True)
            
            for replacement in line_replacements:
                start_idx = replacement["start_idx"]
                end_idx = replacement["end_idx"]
                new_content = replacement["new_content"]
                
                # 将新内容按换行符拆分成行列表，正确处理\n
                if new_content:
                    # 处理换行符，将\n转换为实际换行
                    processed_content = new_content.replace('\\n', '\n')
                    # 处理空格占位符，支持多种格式
                    processed_content = processed_content.replace('_SPACE_', ' ')  # 单个空格
                    processed_content = processed_content.replace('_SP_', ' ')     # 简写形式
                    processed_content = processed_content.replace('_4SP_', '    ') # 4个空格（常用缩进）
                    processed_content = processed_content.replace('_TAB_', '\t')   # 制表符
                    new_lines = processed_content.split('\n')
                    
                    # 确保每行都以换行符结尾（除了最后一行）
                    formatted_new_lines = []
                    for i, line in enumerate(new_lines):
                        if i < len(new_lines) - 1:  # 不是最后一行
                            formatted_new_lines.append(line + '\n')
                        else:  # 最后一行
                            # 根据原文件的最后一行是否有换行符来决定
                            if end_idx == len(original_lines) and original_lines and not original_lines[-1].endswith('\n'):
                                formatted_new_lines.append(line)  # 不添加换行符
                            else:
                                formatted_new_lines.append(line + '\n')  # 添加换行符
                    
                    # 替换行范围 (使用[a, b]包含语法)
                    modified_lines[start_idx:end_idx + 1] = formatted_new_lines
                else:
                    # 空内容，删除行范围
                    modified_lines[start_idx:end_idx + 1] = []
            
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
                # 预览模式：使用diff显示修改内容，不保存文件
                diff_result = self._generate_local_diff_preview(filename, original_lines, modified_lines, parsed_replacements)
                return {
                    "success": True,
                    "mode": "preview",
                    "filename": filename,
                    "original_lines": len(original_lines),
                    "modified_lines": len(modified_lines),
                    "replacements_applied": len(parsed_replacements),
                    "diff_output": diff_result.get("diff_output", ""),
                    "changes_summary": diff_result.get("changes_summary", []),
                    "message": f"📝 预览模式 - 文件: {filename}\n原始行数: {len(original_lines)}, 修改后行数: {len(modified_lines)}\n应用替换: {len(parsed_replacements)} 个"
                }
            
            # 7. 准备临时目录和文件上传列表
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            
            # 从完整路径中提取文件名，保持原始文件名用于替换
            actual_filename = os.path.basename(filename)
            # 使用原始文件名，不添加时间戳，这样upload时会直接替换
            temp_file_path = os.path.join(temp_dir, actual_filename)
            
            files_to_upload = []
            backup_info = {}
            
            if backup:
                # 使用更精确的时间戳避免冲突，包含毫秒
                import time
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') + f"_{int(time.time() * 1000) % 10000:04d}"
                backup_filename = f"{filename}.backup.{timestamp}"
                
                debug_log("Creating backup file for batch upload...")
                # 下载原文件到缓存
                download_result = self.cmd_download(filename, force=True)
                if download_result["success"]:
                    cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
                    if cache_file_path and os.path.exists(cache_file_path):
                        # 创建临时备份文件
                        temp_backup_path = os.path.join(temp_dir, backup_filename)
                        import shutil
                        shutil.copy2(cache_file_path, temp_backup_path)
                        files_to_upload.append(temp_backup_path)
                        debug_log(f"Backup file prepared: {temp_backup_path}")
                        
                        backup_info = {
                            "backup_created": True,
                            "backup_filename": backup_filename,
                            "backup_temp_path": temp_backup_path
                        }
                    else:
                        backup_info = {
                            "backup_created": False,
                            "backup_error": "Failed to get cache file for backup"
                        }
                else:
                    backup_info = {
                        "backup_created": False,
                        "backup_error": f"Failed to download original file for backup: {download_result.get('error')}"
                    }
            
            # 添加修改后的文件到上传列表
            files_to_upload.append(temp_file_path)
            debug_log(f"Files to upload: {files_to_upload}")
            
            # 8. 保存修改后的文件到临时位置，使用原始文件名
            debug_log(f"Using temp_file_path='{temp_file_path}' for original filename='{actual_filename}'")
            
            with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
                temp_file.writelines(modified_lines)
            
            try:
                # 9. 更新缓存
                remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
                cache_result = cache_manager.cache_file(remote_absolute_path, temp_file_path)
                
                if not cache_result["success"]:
                    return {"success": False, "error": f"Failed to update cache: {cache_result.get('error')}"}
                
                # 10. 上传修改后的文件，确保缓存状态正确更新
                debug_log(f"About to upload edited file - temp_file_path='{temp_file_path}', filename='{filename}'")
                debug_log(f"temp_file exists: {os.path.exists(temp_file_path)}")
                if os.path.exists(temp_file_path):
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        content_preview = f.read()[:200]
                    debug_log(f"temp_file content preview: {content_preview}...")
                
                # 批量上传所有文件（备份文件+修改后的文件）
                debug_log("Starting batch upload...")
                upload_result = self.cmd_upload(files_to_upload, force=True)
                debug_log(f"Batch upload result: {upload_result}")
                
                if upload_result["success"]:
                    # 生成diff预览用于显示
                    diff_result = self._generate_local_diff_preview(filename, original_lines, modified_lines, parsed_replacements)
                    
                    result = {
                        "success": True,
                        "filename": filename,
                        "original_lines": len(original_lines),
                        "modified_lines": len(modified_lines),
                        "replacements_applied": len(parsed_replacements),
                        "diff": diff_info,
                        "diff_output": diff_result.get("diff_output", ""),
                        "cache_updated": True,
                        "uploaded": True,
                        "message": f"File {filename} edited successfully, applied {len(parsed_replacements)} replacements"
                    }
                    result.update(backup_info)
                    
                    # 如果有备份文件，添加成功信息
                    if backup_info.get("backup_created"):
                        result["message"] += f"\n📋 Backup created: {backup_info['backup_filename']}"
                    
                    return result
                else:
                    return {
                        "success": False,
                        "error": f"Failed to upload files: {upload_result.get('error')}",
                        "cache_updated": True,
                        "diff": diff_info,
                        "backup_info": backup_info
                    }
                    
            finally:
                # 清理所有临时文件
                for temp_path in files_to_upload:
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            debug_log(f"Cleaned up temp file: {temp_path}")
                    except Exception as cleanup_error:
                        debug_log(f"Failed to cleanup temp file {temp_path}: {cleanup_error}")
            
        except KeyboardInterrupt:
            # 用户中断，输出debug信息
            if debug_info:
                print("\n🔧 DEBUG INFO (due to KeyboardInterrupt):")
                for i, info in enumerate(debug_info, 1):
                    print(f"  {i}. {info}")
            raise  # 重新抛出KeyboardInterrupt
        except Exception as e:
            # 输出debug信息用于异常诊断
            if debug_info:
                print("🔧 DEBUG INFO (due to exception):")
                for i, info in enumerate(debug_info, 1):
                    print(f"  {i}. {info}")
            return {"success": False, "error": f"Edit operation failed: {str(e)}"}

    def _create_backup(self, filename, backup_filename):
        """
        创建文件的备份副本
        
        Args:
            filename (str): 原文件名
            backup_filename (str): 备份文件名
            
        Returns:
            dict: 备份结果
        """
        # 备份debug信息收集器
        backup_debug = []
        
        def backup_debug_log(message):
            backup_debug.append(message)
        
        try:
            backup_debug_log(f"Starting backup: {filename} -> {backup_filename}")
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                backup_debug_log("ERROR: No active remote shell")
                return {"success": False, "error": "No active remote shell"}
            
            backup_debug_log(f"Current shell: {current_shell.get('id', 'unknown')}")
            
            # 下载原文件到缓存
            backup_debug_log("Step 1: Downloading original file to cache...")
            download_result = self.cmd_download(filename, force=True)
            backup_debug_log(f"Download result: success={download_result.get('success')}, error={download_result.get('error')}")
            
            if not download_result["success"]:
                if backup_debug:
                    print("🔧 BACKUP DEBUG INFO (download failed):")
                    for i, info in enumerate(backup_debug, 1):
                        print(f"  {i}. {info}")
                return {"success": False, "error": f"Failed to download original file for backup: {download_result.get('error')}"}
            
            import os
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            backup_debug_log(f"Cache file path: {cache_file_path}")
            backup_debug_log(f"Cache file exists: {os.path.exists(cache_file_path) if cache_file_path else False}")
            
            if not cache_file_path or not os.path.exists(cache_file_path):
                if backup_debug:
                    print("🔧 BACKUP DEBUG INFO (cache file not found):")
                    for i, info in enumerate(backup_debug, 1):
                        print(f"  {i}. {info}")
                return {"success": False, "error": "Failed to get cache file path for backup"}
            
            # 上传缓存文件作为备份
            backup_debug_log("Step 2: Creating backup file with correct name...")
            backup_debug_log(f"Cache file path: {cache_file_path}")
            backup_debug_log(f"Backup filename: {backup_filename}")
            
            # 创建临时备份文件，使用正确的文件名
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_backup_path = os.path.join(temp_dir, backup_filename)
            backup_debug_log(f"Temp backup path: {temp_backup_path}")
            
            # 复制缓存文件到临时备份文件
            import shutil
            shutil.copy2(cache_file_path, temp_backup_path)
            backup_debug_log(f"Copied cache to temp backup: {cache_file_path} -> {temp_backup_path}")
            
            try:
                # 上传备份文件
                backup_debug_log("Step 3: Uploading backup file...")
                upload_result = self.cmd_upload([temp_backup_path], force=True)
                backup_debug_log(f"Upload result: success={upload_result.get('success')}, error={upload_result.get('error')}")
                backup_debug_log(f"Upload file_moves: {upload_result.get('file_moves', [])}")
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(temp_backup_path):
                        os.unlink(temp_backup_path)
                        backup_debug_log(f"Cleaned up temp backup file: {temp_backup_path}")
                except Exception as cleanup_error:
                    backup_debug_log(f"Failed to cleanup temp backup file: {cleanup_error}")
            
            if upload_result.get("success", False):
                backup_debug_log("Backup creation completed successfully")
                return {"success": True, "message": f"Backup created: {backup_filename}"}
            else:
                if backup_debug:
                    print("🔧 BACKUP DEBUG INFO (upload failed):")
                    for i, info in enumerate(backup_debug, 1):
                        print(f"  {i}. {info}")
                return {"success": False, "error": f"Failed to create backup: {upload_result.get('error')}"}
                
        except KeyboardInterrupt:
            # 用户中断备份过程
            if backup_debug:
                print("\n🔧 BACKUP DEBUG INFO (due to KeyboardInterrupt):")
                for i, info in enumerate(backup_debug, 1):
                    print(f"  {i}. {info}")
            raise
        except Exception as e:
            return {"success": False, "error": f"Backup creation failed: {str(e)}"}

    def cmd_venv(self, *args):
        """
        虚拟环境管理命令
        
        支持的子命令：
        - --create <env_name>: 创建虚拟环境
        - --delete <env_name>: 删除虚拟环境
        - --activate <env_name>: 激活虚拟环境（设置PYTHONPATH）
        - --deactivate: 取消激活虚拟环境（清除PYTHONPATH）
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 操作结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "Usage: venv --create|--delete|--activate|--deactivate|--list [env_name...]"
                }
            
            action = args[0]
            env_names = args[1:] if len(args) > 1 else []
            
            if action == "--create":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_create_batch(env_names)
            elif action == "--delete":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_delete_batch(env_names)
            elif action == "--activate":
                if len(env_names) != 1:
                    return {"success": False, "error": "Please specify exactly one environment name for activation"}
                return self._venv_activate(env_names[0])
            elif action == "--deactivate":
                return self._venv_deactivate()
            elif action == "--list":
                return self._venv_list()
            else:
                return {
                    "success": False,
                    "error": f"Unknown venv command: {action}. Supported commands: --create, --delete, --activate, --deactivate, --list"
                }
                
        except Exception as e:
            return {"success": False, "error": f"venv命令执行失败: {str(e)}"}
    
    def _venv_create(self, env_name):
        """创建虚拟环境"""
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 检查环境是否已存在
            env_path = f"{self.main_instance.REMOTE_ENV}/{env_name}"
            
            # 使用Google Drive API检查文件夹是否存在
            if self.drive_service:
                try:
                    # 列出REMOTE_ENV文件夹下的所有子文件夹
                    folders_result = self.drive_service.list_files(
                        folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID,
                        max_results=100
                    )
                    folders = folders_result.get('files', []) if folders_result.get('success') else []
                    # 过滤出文件夹类型
                    folders = [f for f in folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                    
                    # 检查是否已存在同名环境
                    existing_env = next((f for f in folders if f['name'] == env_name), None)
                    if existing_env:
                        return {
                            "success": False,
                            "error": f"Virtual environment '{env_name}' already exists"
                        }
                        
                except Exception as e:
                    # Silently handle environment existence check errors
                    pass
            
            # 生成创建环境的远程命令（简化版本，避免复杂引号嵌套）
            commands = [
                f"mkdir -p '{env_path}'",
                f"echo '# Virtual environment {env_name} created at {env_path}' > '{env_path}/env_info.txt'",
                f"echo 'Environment: {env_name}' >> '{env_path}/env_info.txt'",
                f"echo 'Created: '\"$(date)\" >> '{env_path}/env_info.txt'",
                f"echo 'Path: {env_path}' >> '{env_path}/env_info.txt'"
            ]
            
            # 使用bash -c执行命令脚本
            command_script = " && ".join(commands)
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command_script])
            
            if result.get("success", False):
                # 检查远程命令的实际执行结果
                exit_code = result.get("exit_code", -1)
                stdout = result.get("stdout", "")
                
                # 远程命令成功执行（exit_code == 0 表示成功，不需要检查特定输出）
                if exit_code == 0:
                    return {
                        "success": True,
                        "message": f"Virtual environment '{env_name}' created successfully",
                        "env_path": env_path,
                        "action": "create",
                        "remote_output": stdout.strip()
                    }
                else:
                    # 获取完整的结果数据用于调试
                    stderr = result.get("stderr", "")
                    
                    # 构建详细的错误信息
                    error_details = []
                    error_details.append(f"remote command failed with exit code {exit_code}")
                    
                    if stdout.strip():
                        error_details.append(f"stdout: {stdout.strip()}")
                    
                    if stderr.strip():
                        error_details.append(f"stderr: {stderr.strip()}")
                    
                    # 检查常见的错误模式并提供建议
                    error_message = f"Failed to create virtual environment: {'; '.join(error_details)}"
                    
                    if "Permission denied" in stdout or "Permission denied" in stderr:
                        error_message += ". Suggestion: Check if you have write permissions to the remote environment directory."
                    elif "No such file or directory" in stdout or "No such file or directory" in stderr:
                        error_message += ". Suggestion: The remote environment path may not exist or be accessible."
                    elif "python" in stdout.lower() or "python" in stderr.lower():
                        error_message += ". Suggestion: Python may not be available or properly configured in the remote environment."
                    
                    return {
                        "success": False,
                        "error": error_message,
                        "remote_output": stdout.strip(),
                        "stderr": stderr.strip(),
                        "exit_code": exit_code
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error creating virtual environment: {str(e)}"}
    
    def _venv_delete(self, env_name):
        """删除虚拟环境"""
        if not env_name:
            return {"success": False, "error": "Please specify the environment name"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 检查环境是否存在
            env_path = f"{self.main_instance.REMOTE_ENV}/{env_name}"
            
            # 使用Google Drive API检查文件夹是否存在
            if self.drive_service:
                try:
                    folders_result = self.drive_service.list_files(
                        folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID,
                        max_results=100
                    )
                    folders = folders_result.get('files', []) if folders_result.get('success') else []
                    folders = [f for f in folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                    
                    existing_env = next((f for f in folders if f['name'] == env_name), None)
                    if not existing_env:
                        return {
                            "success": False,
                            "error": f"Virtual environment '{env_name}' does not exist"
                        }
                        
                except Exception as e:
                    # Silently handle environment existence check errors
                    pass
            
            # 生成删除环境的远程命令，添加执行状态提示
            command = f"rm -rf {env_path}" + ' && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success", False):
                return {
                    "success": True,
                    "message": f"Virtual environment '{env_name}' deleted successfully",
                    "action": "delete"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to delete virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error deleting virtual environment: {str(e)}"}
    
    def _venv_activate(self, env_name):
        """激活虚拟环境（设置PYTHONPATH）"""
        if not env_name:
            return {"success": False, "error": "Please specify the environment name"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 检查环境是否存在
            env_path = f"{self.main_instance.REMOTE_ENV}/{env_name}"
            
            # 使用Google Drive API检查文件夹是否存在
            if self.drive_service:
                try:
                    folders_result = self.drive_service.list_files(
                        folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID,
                        max_results=100
                    )
                    folders = folders_result.get('files', []) if folders_result.get('success') else []
                    folders = [f for f in folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                    
                    existing_env = next((f for f in folders if f['name'] == env_name), None)
                    if not existing_env:
                        return {
                            "success": False,
                            "error": f"Virtual environment '{env_name}' does not exist"
                        }
                        
                except Exception as e:
                    # Silently handle environment existence check errors
                    pass
            
            # 生成激活环境的远程命令（持久化设置PYTHONPATH环境变量并记录当前环境）
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
            current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
            env_file = f"{tmp_dir}/venv_env_{shell_id}.sh"
            
            # 构建命令：创建环境文件并设置PYTHONPATH
            commands = [
                f"mkdir -p {tmp_dir}",
                # 创建环境变量文件，包含PYTHONPATH设置
                f"echo 'export PYTHONPATH=/env/python:{env_path}' > {env_file}",
                # 记录当前激活的虚拟环境名称
                f"echo '{env_name}' > {current_venv_file}",
                # 在当前会话中应用环境变量（用于验证）
                f"source {env_file}",
                # 简单的成功消息
                f"echo 'Virtual environment \"{env_name}\" activated'"
            ]
            # 为了让环境变量在主shell中生效，我们需要让用户在主shell中执行命令
            # 而不是在一个bash -c子shell中执行
            expected_pythonpath = f"/env/python:{env_path}"
            result = self._execute_non_bash_safe_commands(commands, "activate virtual environment", env_name, expected_pythonpath)
            
            if result.get("success", False):
                # 检查远程命令的实际执行结果
                result_data = result.get("data", {})
                exit_code = result_data.get("exit_code", -1)
                stdout = result_data.get("stdout", "")
                
                # 如果有完整的终端输出且包含成功标记，根据输出判断
                if "✅ 执行完成" in stdout:
                    if (exit_code == 0 and f"CURRENT_VENV={env_name}" in stdout and f"/env/python:{env_path}" in stdout):
                        return {
                            "success": True,
                            "message": f"Virtual environment '{env_name}' activated successfully",
                            "env_path": env_path,
                            "pythonpath": env_path,
                            "action": "activate",
                            "note": "PYTHONPATH has been set in the remote environment",
                            "remote_output": stdout.strip()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to activate virtual environment: environment variables not set correctly",
                            "remote_output": stdout.strip()
                        }
                else:
                    # 用户直接提供反馈，检查状态文件来判断是否成功
                    try:
                        current_shell = self.main_instance.get_current_shell()
                        shell_id = current_shell.get("id", "default") if current_shell else "default"
                        tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
                        current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
                        current_env_result = self.main_instance.cmd_cat(current_venv_file)
                        
                        if (current_env_result.get("success") and 
                            current_env_result.get("output", "").strip() == env_name):
                            return {
                                "success": True,
                                "message": f"Virtual environment '{env_name}' activated successfully",
                                "env_path": env_path,
                                "pythonpath": env_path,
                                "action": "activate",
                                "note": "PYTHONPATH has been set in the remote environment (verified via status file)",
                                "remote_output": stdout.strip()
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Failed to activate virtual environment: status file does not contain expected environment name",
                                "remote_output": stdout.strip()
                            }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Failed to verify activation status: {str(e)}",
                            "remote_output": stdout.strip()
                        }
            else:
                return {
                    "success": False,
                    "error": f"Failed to activate virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error activating virtual environment: {str(e)}"}
    
    def _venv_deactivate(self):
        """取消激活虚拟环境（清除PYTHONPATH）"""
        try:
            # 生成取消激活的远程命令（删除环境文件并清除当前环境记录）
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
            current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
            env_file = f"{tmp_dir}/venv_env_{shell_id}.sh"
            
            commands = [
                f"mkdir -p {tmp_dir}",
                # 创建重置环境文件，将PYTHONPATH重置为默认值
                f"echo 'export PYTHONPATH=/env/python' > {env_file}",
                # 删除虚拟环境状态文件
                f"rm -f {current_venv_file}",
                # 在当前会话中应用重置的环境变量
                f"source {env_file}",
                # 简单的成功消息
                "echo 'Virtual environment deactivated'"
            ]
            
            # 使用非bash-safe执行方法，让环境变量在主shell中生效
            expected_pythonpath = "/env/python"
            result = self._execute_non_bash_safe_commands(commands, "deactivate virtual environment", None, expected_pythonpath)
            
            if result.get("success", False):
                # 检查远程命令的实际执行结果
                result_data = result.get("data", {})
                exit_code = result_data.get("exit_code", -1)
                stdout = result_data.get("stdout", "")
                
                # 如果有完整的终端输出且包含成功标记，根据输出判断
                if "✅ 执行完成" in stdout:
                    if (exit_code == 0 and "CURRENT_VENV=none" in stdout and "PYTHONPATH has been reset to: /env/python" in stdout):
                        return {
                            "success": True,
                            "message": "Virtual environment deactivated",
                            "action": "deactivate",
                            "note": "PYTHONPATH has been cleared",
                            "remote_output": stdout.strip()
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to deactivate virtual environment: environment variables not cleared correctly",
                            "remote_output": stdout.strip()
                        }
                else:
                    # 用户直接提供反馈，检查状态文件来判断是否成功
                    try:
                        current_shell = self.main_instance.get_current_shell()
                        shell_id = current_shell.get("id", "default") if current_shell else "default"
                        tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
                        current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
                        current_env_result = self.main_instance.cmd_cat(current_venv_file)
                        
                        # deactivate成功的标志是状态文件不存在或为空
                        if not current_env_result.get("success") or not current_env_result.get("output", "").strip():
                            return {
                                "success": True,
                                "message": "Virtual environment deactivated",
                                "action": "deactivate",
                                "note": "PYTHONPATH has been cleared (verified via status file)",
                                "remote_output": stdout.strip()
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Failed to deactivate virtual environment: status file still contains environment name",
                                "remote_output": stdout.strip()
                            }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Failed to verify deactivation status: {str(e)}",
                            "remote_output": stdout.strip()
                        }
            else:
                return {
                    "success": False,
                    "error": f"Failed to deactivate virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Failed to deactivate virtual environment: {str(e)}"}

    def _venv_list(self):
        """列出所有虚拟环境"""
        try:
            # 使用Google Drive API列出REMOTE_ENV文件夹下的所有子文件夹
            if self.drive_service:
                try:
                    folders_result = self.drive_service.list_files(
                        folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID,
                        max_results=100
                    )
                    folders = folders_result.get('files', []) if folders_result.get('success') else []
                    folders = [f for f in folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                    
                    # 提取环境名称，过滤掉以.开头的文件夹（如.tmp）
                    env_names = [f['name'] for f in folders if not f['name'].startswith('.')]
                    
                except Exception as e:
                    print(f"Warning: Failed to check environments via API: {e}")
                    env_names = []
            else:
                env_names = []
            
            # 检查当前shell的激活环境（通过读取远程状态文件）
            current_env = None
            try:
                current_shell = self.main_instance.get_current_shell()
                shell_id = current_shell.get("id", "default") if current_shell else "default"
                # 确保.tmp目录存在
                tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
                current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
                
                # 尝试读取当前环境状态文件
                current_env_result = self.main_instance.cmd_cat(current_venv_file)
                if current_env_result.get("success") and current_env_result.get("output"):
                    current_env = current_env_result["output"].strip()
            except Exception as e:
                print(f"Warning: Failed to check current environment: {e}")
                current_env = None
            
            if not env_names:
                return {
                    "success": True,
                    "message": "No virtual environments found",
                    "environments": [],
                    "count": 0
                }
            
            # 格式化输出
            env_list = []
            for env_name in sorted(env_names):
                if env_name == current_env:
                    env_list.append(f"* {env_name}")
                else:
                    env_list.append(f"  {env_name}")
            
            return {
                "success": True,
                "message": f"Virtual environments ({len(env_names)} total):",
                "environments": env_list,
                "count": len(env_names),
                "current": current_env
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to list virtual environments: {str(e)}"}

    def _venv_create_batch(self, env_names):
        """批量创建虚拟环境（优化版：一个远程命令创建多个环境）"""
        import time
        
        # 过滤掉无效的环境名
        valid_env_names = []
        invalid_names = []
        
        for env_name in env_names:
            if env_name.startswith('.'):
                invalid_names.append(env_name)
            else:
                valid_env_names.append(env_name)
        
        if invalid_names:
            print(f"⚠️  Skipped {len(invalid_names)} invalid environment name(s): {', '.join(invalid_names)} (cannot start with '.')")
        
        if not valid_env_names:
            return {
                "success": False,
                "message": "No valid environments to create",
                "skipped": invalid_names
            }
        
        print(f"Creating {len(valid_env_names)} virtual environment(s): {', '.join(valid_env_names)}")
        
        # 生成单个远程命令来创建多个环境
        create_commands = []
        for env_name in valid_env_names:
            env_path = f"{self.main_instance.REMOTE_ENV}/{env_name}"
            create_commands.append(f'mkdir -p "{env_path}"')
        
        # 合并为一个命令
        combined_command = " && ".join(create_commands)
        full_command = f'{combined_command} && echo "Batch create completed: {len(valid_env_names)} environments created"'
        
        # 执行远程命令
        result = self.main_instance.execute_generic_remote_command("bash", ["-c", full_command])
        
        if not result.get("success"):
            return {
                "success": False,
                "error": f"Failed to create environments: {result.get('error', 'Unknown error')}",
                "attempted": valid_env_names,
                "skipped": invalid_names
            }
        
        # 异步验证所有环境是否创建成功
        print("⏳ Validating environment creation: ", end="", flush=True)
        
        # 只在真正的调试模式下输出详细信息
        debug_mode = os.environ.get('GDS_DEBUG', '').lower() in ('1', 'true', 'yes')
        if debug_mode:
            debug_print(f"Starting validation for {len(valid_env_names)} environments: {valid_env_names}")
        
        max_attempts = 60
        verified_envs = set()
        
        for attempt in range(max_attempts):
            if debug_mode:
                debug_print(f"Validation attempt {attempt + 1}/{max_attempts}")
            
            # 检查每个环境是否存在
            try:
                if self.drive_service:
                    if debug_mode:
                        debug_print("Calling Google Drive API list_files...")
                    folders_result = self.drive_service.list_files(
                        folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID,
                        max_results=100
                    )
                    if debug_mode:
                        debug_print(f"API call completed, success: {folders_result.get('success', False)}")
                    
                    folders = folders_result.get('files', []) if folders_result.get('success') else []
                    if debug_mode:
                        debug_print(f"Found {len(folders)} total items")
                    
                    env_folders = [f for f in folders if f.get('mimeType') == 'application/vnd.google-apps.folder' and not f['name'].startswith('.')]
                    if debug_mode:
                        debug_print(f"Found {len(env_folders)} environment folders")
                    
                    existing_envs = {f['name'] for f in env_folders}
                    if debug_mode:
                        debug_print(f"Existing environment names: {list(existing_envs)}")
                    
                    # 检查新验证的环境
                    newly_verified = []
                    for env_name in valid_env_names:
                        if env_name not in verified_envs and env_name in existing_envs:
                            verified_envs.add(env_name)
                            newly_verified.append(env_name)
                            if debug_mode:
                                debug_print(f"Newly verified: {env_name}")
                    
                    # 输出新验证的环境
                    for env_name in newly_verified:
                        print(f"{env_name} √; ", end="", flush=True)
                    
                    if debug_mode:
                        debug_print(f"Total verified: {len(verified_envs)}/{len(valid_env_names)}")
                    
                    # 如果所有环境都验证了，完成
                    if len(verified_envs) == len(valid_env_names):
                        print()  # 换行
                        return {
                            "success": True,
                            "message": f"Successfully created {len(valid_env_names)} environments",
                            "created": list(verified_envs),
                            "skipped": invalid_names,
                            "total_requested": len(env_names),
                            "total_created": len(verified_envs),
                            "total_skipped": len(invalid_names)
                        }
                else:
                    if debug_mode:
                        debug_print("No drive_service available")
                
                # 如果还没全部验证，继续等待
                if debug_mode:
                    debug_print("Waiting 1 second before next attempt...")
                time.sleep(1)
                print(".", end="", flush=True)
                
            except Exception as e:
                debug_print(f"Exception during verification: {type(e).__name__}: {str(e)}")
                print(f"\n⚠️ Error during verification: {str(e)[:50]}")
                break
        
        # 超时处理
        print(f"\n💡 Verification timeout after {max_attempts}s")
        return {
            "success": len(verified_envs) > 0,
            "message": f"Created {len(verified_envs)}/{len(valid_env_names)} environments (verification timeout)",
            "created": list(verified_envs),
            "unverified": [name for name in valid_env_names if name not in verified_envs],
            "skipped": invalid_names,
            "total_requested": len(env_names),
            "total_created": len(verified_envs),
            "total_skipped": len(invalid_names),
            "verification_timeout": True
        }

    def _venv_delete_batch(self, env_names):
        """批量删除虚拟环境（优化版：一个远程命令完成检查和删除）"""
        debug_mode = os.environ.get('GDS_DEBUG', '').lower() in ('1', 'true', 'yes')
        if debug_mode:
            debug_print(f"Starting _venv_delete_batch")
            debug_print(f"Input env_names: {env_names}")
        
        # 不再预先检查，直接在远程命令中进行所有检查和删除
        # 分类处理环境名（只做基本的保护检查）
        protected_envs = {"GaussianObject"}
        candidate_envs = []
        skipped_protected = []
        
        for env_name in env_names:
            if env_name in protected_envs:
                skipped_protected.append(env_name)
            else:
                candidate_envs.append(env_name)
        
        if skipped_protected:
            print(f"⚠️  Skipped {len(skipped_protected)} protected environment(s): {', '.join(skipped_protected)}")
        
        if not candidate_envs:
            return {
                "success": False,
                "message": "No valid environments to delete",
                "skipped": {"protected": skipped_protected}
            }
        
        print(f"Deleting {len(candidate_envs)} virtual environment(s): {', '.join(candidate_envs)}")
        
        # 生成智能删除命令：在远程端进行所有检查
        current_shell = self.main_instance.get_current_shell()
        shell_id = current_shell.get("id", "default") if current_shell else "default"
        tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
        current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
        
        # 构建智能删除脚本
        delete_script_parts = [
            # 开始提示
            'echo -n "Removing virtual environments ... "',
            
            # 获取当前激活的环境
            f'CURRENT_ENV=$(cat "{current_venv_file}" 2>/dev/null || echo "none")'
        ]
        
        # 为每个候选环境添加检查和删除逻辑
        for env_name in candidate_envs:
            env_path = f"{self.main_instance.REMOTE_ENV}/{env_name}"
            # 构建单个环境的处理脚本
            env_script = f'''
if [ "$CURRENT_ENV" = "{env_name}" ]; then
  echo -n "⚠"
elif [ -d "{env_path}" ]; then
  rm -rf "{env_path}"
  echo -n "√"
else
  echo -n "?"
fi
'''
            delete_script_parts.append(env_script.strip())
        
        # 最终报告 - 不在远程统计，改为在Python中统计
        delete_script_parts.append('echo ""')  # 换行
        
        # 合并为一个命令，使用分号分隔不同的脚本块
        full_command = "; ".join(delete_script_parts)
        if debug_mode:
            debug_print(f"Generated smart delete command (first 200 chars): {full_command[:200]}...")
        
        # 执行单个远程命令
        if debug_mode:
            debug_print("About to call execute_generic_remote_command for SMART_DELETE")
        result = self.main_instance.execute_generic_remote_command("bash", ["-c", full_command])
        if debug_mode:
            debug_print(f"execute_generic_remote_command for SMART_DELETE returned: success={result.get('success')}")
        
        if result.get("success"):
            # 解析远程输出，统计删除结果
            stdout = result.get("stdout", "")
            if debug_mode:
                debug_print(f"Remote stdout: {stdout}")
            
            # 统计符号
            deleted_count = stdout.count("√")  # 成功删除的环境
            skipped_active_count = stdout.count("⚠")  # 跳过的激活环境
            skipped_nonexistent_count = stdout.count("?")  # 不存在的环境
            total_skipped = skipped_active_count + skipped_nonexistent_count + len(skipped_protected)
            
            # 生成详细的结果消息
            if deleted_count > 0:
                message = f"Successfully deleted {deleted_count} environment(s)"
            else:
                message = "No environments were deleted"
            
            if total_skipped > 0:
                skip_details = []
                if len(skipped_protected) > 0:
                    skip_details.append(f"{len(skipped_protected)} protected")
                if skipped_active_count > 0:
                    skip_details.append(f"{skipped_active_count} active")
                if skipped_nonexistent_count > 0:
                    skip_details.append(f"{skipped_nonexistent_count} non-existent")
                message += f", skipped {total_skipped} ({', '.join(skip_details)})"
            
            return {
                "success": True,
                "message": message,
                "attempted": candidate_envs,
                "deleted_count": deleted_count,
                "skipped_count": total_skipped,
                "skipped_details": {
                    "protected": skipped_protected,
                    "active_count": skipped_active_count,
                    "nonexistent_count": skipped_nonexistent_count
                },
                "total_requested": len(env_names),
                "stdout": stdout
            }
        else:
            return {
                "success": False,
                "error": f"Failed to delete environments: {result.get('error', 'Unknown error')}",
                "attempted": candidate_envs,
                "skipped": {"protected": skipped_protected}
            }


    def cmd_pip(self, *args):
        """
        pip命令，自动根据当前激活的虚拟环境设置--target参数
        
        Args:
            *args: pip命令参数
            
        Returns:
            dict: 执行结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "Usage: pip <command> [options] [packages...]"
                }
            
            # 检查当前shell的激活环境
            current_env = None
            try:
                current_shell = self.main_instance.get_current_shell()
                shell_id = current_shell.get("id", "default") if current_shell else "default"
                tmp_dir = f"{self.main_instance.REMOTE_ENV}/.tmp"
                current_venv_file = f"{tmp_dir}/current_venv_{shell_id}.txt"
                current_env_result = self.main_instance.cmd_cat(current_venv_file)
                if current_env_result.get("success") and current_env_result.get("output"):
                    current_env = current_env_result["output"].strip()
            except Exception:
                current_env = None
            
            # 构建pip命令
            pip_args = list(args)
            
            if current_env:
                # 有激活的虚拟环境，添加--target参数
                env_path = f"{self.main_instance.REMOTE_ENV}/{current_env}"
                
                # 检查是否是install命令，如果是则添加--target参数
                if len(pip_args) > 0 and pip_args[0] == 'install':
                    # 检查是否已经有--target参数
                    has_target = any(arg.startswith('--target') for arg in pip_args)
                    if not has_target:
                        pip_args.insert(1, f'--target={env_path}')
                
                target_info = f"in environment '{current_env}'"
            else:
                # 没有激活虚拟环境，使用系统pip（不添加--target）
                target_info = "in system environment"
            
            # 使用强化的pip执行机制，支持错误处理和结果验证
            pip_command = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in pip_args)
            result = self._execute_pip_command_enhanced(pip_command, current_env, target_info)
            
            if result.get("success", False):
                response = {
                    "success": True,
                    "message": "",  # 不显示额外的成功消息，保持原生pip体验
                    "environment": current_env or "system"
                }
                if current_env:
                    response["target_path"] = f"{self.main_instance.REMOTE_ENV}/{current_env}"
                return response
            else:
                return {
                    "success": False,
                    "error": f"pip command failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"pip command execution failed: {str(e)}"}

    def _execute_pip_command_enhanced(self, pip_command, current_env, target_info):
        """
        强化的pip命令执行，支持错误处理和结果验证
        """
        try:
            import time
            import random
            
            # 生成唯一的结果文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            result_filename = f"pip_result_{timestamp}_{random_id}.json"
            result_file_path = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/{result_filename}"
            
            # 使用Python subprocess包装pip执行，确保正确捕获所有输出和错误
            python_script = f'''
import subprocess
import json
import sys
from datetime import datetime

print("Starting pip {pip_command}...")

# 执行pip命令并捕获所有输出
try:
    result = subprocess.run(
        ["pip"] + "{pip_command}".split(),
        capture_output=True,
        text=True
    )
    
    # 显示pip的完整输出
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    # 检查是否有严重ERROR关键字（排除依赖冲突警告）
    has_error = False
    if result.returncode != 0:  # 只有在退出码非0时才检查错误
        has_error = "ERROR:" in result.stderr or "ERROR:" in result.stdout
    
    print(f"Pip command completed with exit code: {{result.returncode}}")
    if has_error:
        print("⚠️  Detected ERROR messages in pip output")
    
    # 生成结果JSON
    result_data = {{
        "success": result.returncode == 0 and not has_error,
        "pip_command": "{pip_command}",
        "exit_code": result.returncode,
        "environment": "{current_env or 'system'}",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "has_error": has_error,
        "timestamp": datetime.now().isoformat()
    }}
    
    with open("{result_file_path}", "w") as f:
        json.dump(result_data, f, indent=2)
    
    # 显示最终状态
    if result.returncode == 0 and not has_error:
        print("pip command completed successfully")
    else:
        print(f"pip command failed (exit_code: {{result.returncode}}, has_error: {{has_error}})")

except subprocess.TimeoutExpired:
    print("❌ Pip command timed out after 5 minutes")
    result_data = {{
        "success": False,
        "pip_command": "{pip_command}",
        "exit_code": -1,
        "environment": "{current_env or 'system'}",
        "error": "Command timed out",
        "timestamp": datetime.now().isoformat()
    }}
    with open("{result_file_path}", "w") as f:
        json.dump(result_data, f, indent=2)

except Exception as e:
    print(f"❌ Error executing pip command: {{e}}")
    result_data = {{
        "success": False,
        "pip_command": "{pip_command}",
        "exit_code": -1,
        "environment": "{current_env or 'system'}",
        "error": str(e),
        "timestamp": datetime.now().isoformat()
    }}
    with open("{result_file_path}", "w") as f:
        json.dump(result_data, f, indent=2)
'''
            
            commands = [
                "mkdir -p /content/drive/MyDrive/REMOTE_ROOT/tmp",  # 确保远程tmp目录存在
                f"python3 -c '{python_script}'"
            ]
            
            full_command = " && ".join(commands)
            
            # 使用统一的tkinter窗口界面（与activate/deactivate保持一致）
            window_title = f"Execute command to run pip {pip_command} {target_info}"
            
            # 调用统一的远程命令窗口
            try:
                result = self.main_instance.remote_commands._show_generic_command_window(
                    "pip",  # cmd
                    pip_command.split(),  # args
                    full_command,  # remote_command
                    window_title  # debug_info
                )
                
                if result.get("action") == "failed":
                    return {
                        "success": False, 
                        "error": result.get("message", "User reported execution failed"),
                        "source": "user_reported_failure"
                    }
                elif result.get("action") == "direct_feedback":
                    # 用户提供了直接反馈，跳过文件检测
                    return {
                        "success": True,
                        "message": result.get("message", "Pip command executed successfully"),
                        "source": "direct_feedback"
                    }
            except Exception as e:
                # 如果tkinter窗口失败，回退到简单终端提示
                return {
                    "success": False,
                    "error": f"Failed to show command window: {str(e)}"
                }
            
            # 等待并检测结果文件
            remote_file_path = f"~/tmp/{result_filename}"
            
            print("⏳ Validating results ...", end="", flush=True)
            max_attempts = 60
            
            for attempt in range(max_attempts):
                try:
                    # 检查远程文件是否存在
                    check_result = self.main_instance.remote_commands._check_remote_file_exists_absolute(result_file_path)
                    
                    if check_result.get("exists"):
                        # 文件存在，读取内容
                        print("√")  # 成功标记
                        read_result = self.main_instance.remote_commands._read_result_file_via_gds(result_filename)
                        
                        if read_result.get("success"):
                            try:
                                result_data = read_result.get("data", {})
                                
                                # 验证pip命令结果
                                command_success = result_data.get("success", False)
                                exit_code = result_data.get("exit_code", -1)
                                has_error = result_data.get("has_error", False)
                                stdout = result_data.get("stdout", "")
                                stderr = result_data.get("stderr", "")
                                
                                # 显示pip命令的实际输出（简洁格式）
                                if stdout.strip():
                                    print(stdout.strip())
                                
                                if stderr.strip() and not command_success:
                                    print(f"⚠️  {stderr.strip()}")
                                
                                if command_success:
                                    return {
                                        "success": True,
                                        "message": "",  # 不显示额外的成功消息，保持原生pip体验
                                        "stdout": stdout,
                                        "stderr": stderr,
                                        "data": result_data
                                    }
                                else:
                                    return {
                                        "success": False,
                                        "error": f"Pip command failed (exit_code: {exit_code}): {stderr}",
                                        "stdout": stdout,
                                        "stderr": stderr,
                                        "data": result_data
                                    }
                            except Exception as e:
                                return {
                                    "success": False,
                                    "error": f"Failed to parse pip result: {str(e)}"
                                }
                        else:
                            return {
                                "success": False,
                                "error": f"Failed to read pip result file: {read_result.get('error', 'Unknown error')}"
                            }
                    
                    # 文件不存在，等待一下再检查
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        print(".", end="", flush=True)
                    
                except Exception as e:
                    if attempt < max_attempts - 1:
                        time.sleep(1)
                        print(".", end="", flush=True)
                    else:
                        return {
                            "success": False,
                            "error": f"Error checking pip result file: {str(e)}"
                        }
            
            # 超时
            print()  # 换行
            return {
                "success": False,
                "error": f"Timeout waiting for pip result file after {max_attempts} seconds"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error executing pip command: {str(e)}"}
