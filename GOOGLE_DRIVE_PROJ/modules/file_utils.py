#!/usr/bin/env python3
"""
Google Drive Shell - File Utils Module
从google_drive_shell.py重构而来的file_utils模块
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

class FileUtils:
    """Google Drive Shell File Utils"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance
    
  # 引用主实例以访问其他属性

    def _zip_folder(self, folder_path, zip_path=None):
        """
        将文件夹打包成zip文件
        
        Args:
            folder_path (str): 要打包的文件夹路径
            zip_path (str): zip文件保存路径，如果为None则自动生成
            
        Returns:
            dict: 打包结果 {"success": bool, "zip_path": str, "error": str}
        """
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                return {"success": False, "error": f"文件夹不存在: {folder_path}"}
            
            if not folder_path.is_dir():
                return {"success": False, "error": f"路径不是文件夹: {folder_path}"}
            
            # 生成zip文件路径
            if zip_path is None:
                # 在临时目录中创建zip文件
                temp_dir = Path(tempfile.gettempdir())
                zip_filename = f"{folder_path.name}.zip"
                zip_path = temp_dir / zip_filename
            else:
                zip_path = Path(zip_path)
            
            # 创建zip文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历文件夹中的所有文件和目录
                files_added = 0
                dirs_added = 0
                
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        # 计算相对路径，使用文件夹名作为根目录
                        arcname = file_path.relative_to(folder_path.parent)
                        zipf.write(file_path, arcname)
                        files_added += 1
                    elif file_path.is_dir():
                        # 添加空目录到zip文件
                        arcname = file_path.relative_to(folder_path.parent)
                        # 确保目录名以/结尾
                        dir_arcname = str(arcname) + '/'
                        zipf.writestr(dir_arcname, '')
                        dirs_added += 1
                
                # 如果文件夹完全为空，至少添加根目录本身
                if files_added == 0 and dirs_added == 0:
                    root_dir_name = folder_path.name + '/'
                    zipf.writestr(root_dir_name, '')
                    dirs_added = 1
                        
            # 检查zip文件是否创建成功
            if zip_path.exists():
                file_size = zip_path.stat().st_size
                return {
                    "success": True,
                    "zip_path": str(zip_path),
                    "original_folder": str(folder_path),
                    "zip_size": file_size
                }
            else:
                return {"success": False, "error": "zip文件创建失败"}
                
        except Exception as e:
            return {"success": False, "error": f"打包过程出错: {e}"}

    def _unzip_remote_file(self, zip_filename, target_dir=".", delete_zip=True, remote_path=None):
        """
        生成包含两个同步检测的远程解压命令并通过tkinter窗口提供给用户执行
        
        Args:
            zip_filename (str): 要解压的zip文件名
            target_dir (str): 解压目标目录
            delete_zip (bool): 解压后是否删除zip文件
            remote_path (str): 远程目标路径
            
        Returns:
            dict: 解压结果
        """
        try:
            print(f"📂 生成包含双重同步检测的远程解压命令: {zip_filename}")
            
            # 构建远程路径
            if remote_path is None:
                remote_target_path = f'"{self.main_instance.REMOTE_ROOT}"'
            else:
                if remote_path.startswith('/'):
                    remote_target_path = f'"{remote_path}"'
                else:
                    # 解析相对路径，处理~和..
                    import os.path
                    if remote_path.startswith('~'):
                        # 将~替换为REMOTE_ROOT
                        resolved_path = remote_path.replace('~', self.main_instance.REMOTE_ROOT, 1)
                    else:
                        resolved_path = f"{self.main_instance.REMOTE_ROOT}/{remote_path}"
                    
                    # 规范化路径，处理..
                    normalized_path = os.path.normpath(resolved_path)
                    remote_target_path = f'"{normalized_path}"'
            
            # 构建源文件路径（Google Drive Desktop同步路径）
            source_path = f'"/content/drive/Othercomputers/我的 MacBook Air/Google Drive/{zip_filename}"'
            target_zip_path = f'{remote_target_path}/{zip_filename}'
            
            # 生成解压命令部分 - 使用统一函数
            # generate_unzip_command现在在remote_commands中，需要通过main_instance访问
            unzip_part = self.main_instance.remote_commands.generate_unzip_command(
                remote_target_path, 
                zip_filename, 
                delete_zip=delete_zip,
                handle_empty_zip=True
            )
            
            # 生成包含两个同步检测的远程命令
            sync_and_move_part = f"""(mkdir -p {remote_target_path} && echo -n "⏳"; for i in $(seq 1 60); do     if mv {source_path} {target_zip_path} 2>/dev/null; then         echo "";         break;     else         if [ "$i" -eq 60 ]; then             echo " ❌ (已重试60次失败)";             exit 1;         else             echo -n ".";             sleep 1;         fi;     fi; done) && (cd {remote_target_path} && echo -n "⏳"; for i in $(seq 1 30); do     if [ -f "{zip_filename}" ]; then         echo "";         break;     else         if [ "$i" -eq 30 ]; then             echo " ❌ (zip文件检测失败)";             exit 1;         else             echo -n ".";             sleep 1;         fi;     fi; done)"""
            
            # 组合完整命令
            remote_command = f"""{sync_and_move_part} && ({unzip_part})"""
            
            print(f"🔧 生成的远程命令（包含双重同步检测）: {remote_command}")
            
            # 使用subprocess方法显示命令窗口
            try:
                # show_command_window_subprocess现在在remote_commands中，需要通过main_instance访问
                
                title = f"远程文件夹上传: {zip_filename}"
                instruction = f"""请在远程环境中执行以下命令来完成文件夹上传和解压：

1. 该命令会自动等待文件同步完成
2. 然后解压文件到目标目录
3. 最后验证解压结果

目标路径: {remote_target_path}
"""
                
                # 使用subprocess方法显示窗口
                result = self.main_instance.remote_commands.show_command_window_subprocess(
                    title=title,
                    command_text=remote_command,
                    timeout_seconds=300
                )
                
                # 转换结果格式
                if result["action"] == "success":
                    return {"success": True, "message": f"文件夹 {folder_path} 上传并解压完成"}
                elif result["action"] == "copy":
                    return {"success": True, "message": "命令已复制到剪切板，请手动执行"}
                else:
                    return {"success": False, "message": f"操作取消或失败: {result.get('error', 'Unknown error')}"}
                    
            except Exception as e:
                return {"success": False, "message": f"显示命令窗口失败: {str(e)}"}
                
        except Exception as e:
            return {"success": False, "error": f"生成远程解压命令失败: {e}"}
    
    def _check_local_files(self, expected_files):
        """检查本地文件系统中的文件"""
        try:
            drive_equiv_path = Path(self.main_instance.DRIVE_EQUIVALENT)
            if not drive_equiv_path.exists():
                return {
                    "success": False,
                    "error": f"DRIVE_EQUIVALENT 目录不存在: {self.main_instance.DRIVE_EQUIVALENT}"
                }
            
            synced_files = []
            missing_files = []
            
            for filename in expected_files:
                file_path = drive_equiv_path / filename
                if file_path.exists():
                    synced_files.append(filename)
                else:
                    missing_files.append(filename)
            
            return {
                "success": len(synced_files) == len(expected_files),
                "synced_files": synced_files,
                "missing_files": missing_files,
                "sync_time": 0  # 本地检查是即时的
            }
            
        except Exception as e:
            return {"success": False, "error": f"本地文件检查失败: {e}"}

    def _verify_files_available(self, file_moves):
        """
        验证文件是否在同步目录中可用
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            bool: 所有文件都可用返回True，否则返回False
        """
        try:
            import os
            for file_info in file_moves:
                filename = file_info["filename"]
                file_path = os.path.join(self.main_instance.LOCAL_EQUIVALENT, filename)
                if not os.path.exists(file_path):
                    return False
            return True
        except Exception as e:
            return False

    def _check_large_files(self, source_files):
        """
        检查大文件（>1GB）并提供手动上传方案
        
        Args:
            source_files (list): 源文件路径列表
            
        Returns:
            tuple: (normal_files, large_files) - 正常文件和大文件列表
        """
        try:
            normal_files = []
            large_files = []
            GB_SIZE = 1024 * 1024 * 1024  # 1GB in bytes
            
            for file_path in source_files:
                expanded_path = self._expand_path(file_path)
                if os.path.exists(expanded_path):
                    file_size = os.path.getsize(expanded_path)
                    if file_size > GB_SIZE:
                        large_files.append({
                            "path": expanded_path,
                            "original_path": file_path,
                            "size_gb": file_size / GB_SIZE
                        })
                    else:
                        normal_files.append(expanded_path)
                else:
                    print(f"File does not exist: {file_path}")
            
            return normal_files, large_files
            
        except Exception as e:
            print(f"检查大文件时出错: {e}")
            return source_files, []

    def _handle_large_files(self, large_files, target_path=".", current_shell=None):
        """处理大文件的手动上传，支持逐一跟进"""
        try:
            if not large_files:
                return {"success": True, "message": "没有大文件需要手动处理"}
            
            print(f"\n📁 发现 {len(large_files)} 个大文件（>1GB），将逐一处理:")
            
            successful_uploads = []
            failed_uploads = []
            
            for i, file_info in enumerate(large_files, 1):
                print(f"\n{'='*60}")
                print(f"🔄 处理第 {i}/{len(large_files)} 个大文件")
                print(f"📄 文件: {file_info['original_path']} ({file_info['size_gb']:.2f} GB)")
                print(f"{'='*60}")
                
                # 为单个文件创建临时上传目录
                single_upload_dir = Path(os.getcwd()) / f"_MANUAL_UPLOAD_{i}"
                single_upload_dir.mkdir(exist_ok=True)
                
                file_path = Path(file_info["path"])
                link_path = single_upload_dir / file_path.name
                
                # 删除已存在的链接
                if link_path.exists():
                    link_path.unlink()
                
                # 创建符号链接
                try:
                    link_path.symlink_to(file_path)
                    print(f"✅ 已准备文件: {file_path.name}")
                except Exception as e:
                    print(f"❌ 创建链接失败: {file_path.name} - {e}")
                    failed_uploads.append({
                        "file": file_info["original_path"],
                        "error": f"创建链接失败: {e}"
                    })
                    continue
                
                # 确定目标文件夹URL
                target_folder_id = None
                target_url = None
                
                if current_shell and self.drive_service:
                    try:
                        # 尝试解析目标路径
                        if target_path == ".":
                            target_folder_id = self.get_current_folder_id(current_shell)
                        else:
                            target_folder_id, _ = self.main_instance.resolve_path(target_path, current_shell)
                        
                        if target_folder_id:
                            target_url = f"https://drive.google.com/drive/folders/{target_folder_id}"
                        else:
                            target_url = f"https://drive.google.com/drive/folders/{self.main_instance.REMOTE_ROOT_FOLDER_ID}"
                    except:
                        target_url = f"https://drive.google.com/drive/folders/{self.main_instance.REMOTE_ROOT_FOLDER_ID}"
                else:
                    target_url = f"https://drive.google.com/drive/folders/{self.main_instance.REMOTE_ROOT_FOLDER_ID}"
                
                # 打开文件夹和目标位置
                try:
                    import subprocess
                    import webbrowser
                    
                    # 打开本地文件夹
                    if platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", str(single_upload_dir)])
                    elif platform.system() == "Windows":
                        os.startfile(str(single_upload_dir))
                    else:  # Linux
                        subprocess.run(["xdg-open", str(single_upload_dir)])
                    
                    # 打开目标Google Drive文件夹（不是DRIVE_EQUIVALENT）
                    webbrowser.open(target_url)
                    
                    print(f"🚀 已打开本地文件夹: {single_upload_dir}")
                    print(f"🌐 已打开目标Google Drive文件夹")
                    print(f"📋 请将文件拖拽到Google Drive目标文件夹中")
                    
                except Exception as e:
                    print(f"⚠️ 打开文件夹失败: {e}")
                
                # 等待用户确认
                try:
                    print(f"\n⏳ 请完成文件上传后按回车继续...")
                    get_multiline_input_safe("按Enter键继续...", single_line=True)  # 等待用户确认
                    
                    # 清理临时目录
                    try:
                        if link_path.exists():
                            link_path.unlink()
                        single_upload_dir.rmdir()
                    except:
                        pass
                    
                    successful_uploads.append({
                        "file": file_info["original_path"],
                        "size_gb": file_info["size_gb"]
                    })
                    
                    print(f"✅ 文件 {i}/{len(large_files)} 处理完成")
                    
                except KeyboardInterrupt:
                    print(f"\n❌ 用户中断了大文件上传过程")
                    # 清理临时目录
                    try:
                        if link_path.exists():
                            link_path.unlink()
                        single_upload_dir.rmdir()
                    except:
                        pass
                    break
                except Exception as e:
                    print(f"❌ 处理文件时出错: {e}")
                    failed_uploads.append({
                        "file": file_info["original_path"],
                        "error": str(e)
                    })
            
            print(f"\n{'='*60}")
            print(f"📊 大文件处理完成:")
            print(f"✅ 成功: {len(successful_uploads)} 个文件")
            print(f"❌ 失败: {len(failed_uploads)} 个文件")
            print(f"{'='*60}")
            
            return {
                "success": len(successful_uploads) > 0,
                "large_files_count": len(large_files),
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "message": f"大文件处理完成: {len(successful_uploads)}/{len(large_files)} 个文件成功"
            }
            
        except Exception as e:
            return {"success": False, "error": f"处理大文件时出错: {e}"}

    def _check_target_file_conflicts_before_move(self, source_files, target_path):
        """在移动文件之前检查目标位置是否已存在同名文件，避免上传冲突"""
        try:
            # 计算每个文件的远端绝对路径
            current_shell = self.main_instance.get_current_shell()
            
            for source_file in source_files:
                filename = Path(source_file).name
                
                # 计算远端绝对路径
                if target_path == "." or target_path == "":
                    # 当前shell位置
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:]
                            remote_file_path = f"~/{relative_path}/{filename}" if relative_path else f"~/{filename}"
                        else:
                            remote_file_path = f"~/{filename}"
                    else:
                        remote_file_path = f"~/{filename}"
                elif target_path.startswith("/"):
                    # 绝对路径
                    remote_file_path = f"{target_path.rstrip('/')}/{filename}"
                else:
                    # 相对路径
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            base_path = current_path[2:] if len(current_path) > 2 else ""
                            if base_path:
                                remote_file_path = f"~/{base_path}/{target_path.strip('/')}/{filename}"
                            else:
                                remote_file_path = f"~/{target_path.strip('/')}/{filename}"
                        else:
                            remote_file_path = f"~/{target_path.strip('/')}/{filename}"
                    else:
                        remote_file_path = f"~/{target_path.strip('/')}/{filename}"
                
                # 使用ls命令检查文件是否存在
                # 获取目录路径和文件名
                if remote_file_path.count('/') > 0:
                    dir_path = '/'.join(remote_file_path.split('/')[:-1])
                    file_name = remote_file_path.split('/')[-1]
                else:
                    dir_path = "~"
                    file_name = remote_file_path
                
                # 列出目录内容
                ls_result = self.main_instance.cmd_ls(dir_path, detailed=False, recursive=False)
                if ls_result["success"] and "files" in ls_result:
                    existing_files = [f["name"] for f in ls_result["files"]]
                    if file_name in existing_files:
                        # 文件存在，返回简洁错误信息
                        return {
                            "success": False,
                            "error": f"File exists: {remote_file_path}"
                        }
            
            return {"success": True}
            
        except Exception as e:
            # 如果检查过程出错，为了安全起见，允许继续上传
            print(f"⚠️ 文件冲突检查出错: {e}")
            return {"success": True}

    def _check_mv_destination_conflict(self, destination, current_shell):
        """检查mv命令的目标是否已存在"""
        try:
            # 计算目标的远端绝对路径
            if destination.startswith("/"):
                # 绝对路径
                remote_destination_path = destination
            else:
                # 相对路径，基于当前shell位置
                if current_shell and current_shell.get("current_path") != "~":
                    current_path = current_shell.get("current_path", "~")
                    if current_path.startswith("~/"):
                        relative_path = current_path[2:] if len(current_path) > 2 else ""
                        if relative_path:
                            remote_destination_path = f"~/{relative_path}/{destination}"
                        else:
                            remote_destination_path = f"~/{destination}"
                    else:
                        remote_destination_path = f"~/{destination}"
                else:
                    remote_destination_path = f"~/{destination}"
            
            # 使用ls命令检查目标是否存在
            # 获取目录路径和文件名
            if remote_destination_path.count('/') > 0:
                dir_path = '/'.join(remote_destination_path.split('/')[:-1])
                file_name = remote_destination_path.split('/')[-1]
            else:
                dir_path = "~"
                file_name = remote_destination_path
            
            # 列出目录内容
            ls_result = self.main_instance.cmd_ls(dir_path, detailed=False, recursive=False)
            if ls_result["success"] and "files" in ls_result:
                existing_files = [f["name"] for f in ls_result["files"]]
                if file_name in existing_files:
                    # 目标已存在，返回简洁错误信息
                    return {
                        "success": False,
                        "error": f"File exists: {remote_destination_path}"
                    }
            
            return {"success": True}
            
        except Exception as e:
            # 如果检查过程出错，为了安全起见，允许继续操作
            print(f"⚠️ mv目标冲突检查出错: {e}")
            return {"success": True}

    def _check_target_file_conflicts(self, file_moves, target_path):
        """检查目标位置是否已存在同名文件，避免上传冲突"""
        try:
            # 计算目标路径
            if target_path == "." or target_path == "":
                current_shell = self.main_instance.get_current_shell()
                if current_shell and current_shell.get("current_path") != "~":
                    current_path = current_shell.get("current_path", "~")
                    if current_path.startswith("~/"):
                        check_path = current_path[2:] if len(current_path) > 2 else None
                    else:
                        check_path = None
                else:
                    check_path = None
            else:
                check_path = target_path
            
            # 使用ls命令检查目标路径
            ls_result = self.main_instance.cmd_ls(check_path, detailed=False, recursive=False)
            if not ls_result["success"]:
                # 如果ls失败，可能是路径不存在，这是正常的
                return {"success": True}
            
            # 检查每个要上传的文件是否与现有文件冲突
            existing_files = []
            if "files" in ls_result:
                existing_files = [f["name"] for f in ls_result["files"]]
            elif "output" in ls_result and ls_result["output"]:
                # 解析简单的ls输出
                lines = ls_result["output"].strip().split('\n')
                for line in lines:
                    if line.strip():
                        # 简单解析文件名（去掉可能的权限、大小等信息）
                        parts = line.strip().split()
                        if parts:
                            existing_files.append(parts[-1])  # 通常文件名是最后一部分
            
            # 检查冲突
            conflicting_files = []
            for file_info in file_moves:
                filename = file_info["filename"]
                if filename in existing_files:
                    conflicting_files.append(filename)
            
            if conflicting_files:
                return {
                    "success": False,
                    "error": f"目标位置已存在文件: {', '.join(conflicting_files)}",
                    "conflicting_files": conflicting_files,
                    "target_path": target_path,
                    "suggestion": "请使用不同的文件名或先删除现有文件"
                }
            
            return {"success": True}
            
        except Exception as e:
            # 如果检查过程出错，为了安全起见，允许继续上传
            print(f"⚠️ 文件冲突检查出错: {e}")
            return {"success": True}

    def _create_text_file(self, filename, content):
        """创建文本文件"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 尝试使用共享驱动器解决方案
            try:
                # 加载共享驱动器配置
                data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
                config_file = data_dir / "shared_drive_config.json"
                
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    drive_id = config["shared_drive_id"]
                    
                    # 在共享驱动器中创建文件
                    result = self._create_file_in_shared_drive(content, filename, drive_id)
                    if result["success"]:
                        return result
                    else:
                        print(f"共享驱动器创建失败: {result['error']}")
                
            except Exception as e:
                print(f"共享驱动器方法出错: {e}")
            
            # 服务账户无法创建文件，返回友好提示
            return {
                "success": False,
                "error": "文件创建功能暂不可用",
                "info": {
                    "reason": "服务账户无法在Google Drive中创建文件（存储配额限制）",
                    "setup_instructions": "运行: cd GOOGLE_DRIVE_PROJ && python setup_shared_drive.py",
                    "alternatives": [
                        "创建共享驱动器并与服务账户分享",
                        "使用 python -c 'code' 直接执行Python代码",
                        "手动在Google Drive中创建文件后使用 cat filename 查看"
                    ],
                    "working_features": [
                        "✅ 读取现有文件 (cat)",
                        "✅ 执行Python代码 (python -c)",
                        "✅ 目录导航 (cd, ls, pwd)",
                        "✅ 文本搜索 (grep)",
                        "✅ 目录管理 (mkdir, rm)"
                    ]
                }
            }
                
        except Exception as e:
            return {"success": False, "error": f"创建文件时出错: {e}"}

    def _create_file_in_shared_drive(self, content, filename, drive_id):
        """在共享驱动器中创建文件"""
        try:
            import tempfile
            import os
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # 文件元数据
                file_metadata = {
                    'name': filename,
                    'parents': [drive_id]  # 共享驱动器ID作为父级
                }
                
                # 使用MediaFileUpload
                from googleapiclient.http import MediaFileUpload
                media = MediaFileUpload(temp_file_path, mimetype='text/plain')
                
                # 创建文件，使用supportsAllDrives=True
                result = self.drive_service.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True,  # 关键：支持共享驱动器
                    fields='id,name,size,webViewLink'
                ).execute()
                
                # 清理临时文件
                os.unlink(temp_file_path)
                
                return {
                    "success": True,
                    "file_id": result['id'],
                    "file_name": result['name'],
                    "file_size": result.get('size', 0),
                    "web_link": result.get('webViewLink'),
                    "message": f"✅ 文件创建成功: {filename}"
                }
                
            except Exception as e:
                # 确保清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                return {"success": False, "error": f"共享驱动器文件创建失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"准备共享驱动器文件时出错: {e}"}

    def _check_files_to_override(self, source_files, target_path):
        """
        检查哪些文件会被覆盖（用于--force模式）
        
        Args:
            source_files (list): 源文件列表
            target_path (str): 目标路径
            
        Returns:
            dict: 检查结果，包含会被覆盖的文件列表
        """
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            overridden_files = []
            
            for source_file in source_files:
                if not os.path.exists(source_file):
                    continue
                    
                filename = os.path.basename(source_file)
                
                # 计算目标远程路径
                if target_path == ".":
                    if current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            target_remote_path = f"{current_path}/{filename}"
                        else:
                            target_remote_path = f"~/{filename}"
                    else:
                        target_remote_path = f"~/{filename}"
                else:
                    if current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            base_path = current_path[2:] if len(current_path) > 2 else ""
                            if base_path:
                                target_remote_path = f"~/{base_path}/{target_path.strip('/')}/{filename}"
                            else:
                                target_remote_path = f"~/{target_path.strip('/')}/{filename}"
                        else:
                            target_remote_path = f"~/{target_path.strip('/')}/{filename}"
                    else:
                        target_remote_path = f"~/{target_path.strip('/')}/{filename}"
                
                # 检查目标文件是否存在
                check_result = self._check_single_target_file_conflict(filename, target_path)
                if not check_result["success"] and "File exists" in check_result.get("error", ""):
                    overridden_files.append(target_remote_path)
            
            return {
                "success": True,
                "overridden_files": overridden_files
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error checking files to override: {e}"}
