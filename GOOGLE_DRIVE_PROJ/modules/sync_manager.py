#!/usr/bin/env python3
"""
Google Drive Shell - Sync Manager Module
从google_drive_shell.py重构而来的sync_manager模块
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

class SyncManager:
    """Google Drive Shell Sync Manager"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def move_to_local_equivalent(self, file_path):
        """
        将文件移动到 LOCAL_EQUIVALENT 目录，如果有同名文件则重命名
        
        Args:
            file_path (str): 要移动的文件路径
            
        Returns:
            dict: 包含成功状态和移动后文件路径的字典
        """
        try:
            # 确保 LOCAL_EQUIVALENT 目录存在
            local_equiv_path = Path(self.main_instance.LOCAL_EQUIVALENT)
            if not local_equiv_path.exists():
                return self._create_error_result(f"LOCAL_EQUIVALENT 目录不存在: {self.main_instance.LOCAL_EQUIVALENT}")
            
            source_path = Path(file_path)
            if not source_path.exists():
                return self._create_error_result(f"源文件不存在: {file_path}")
            
            # 获取文件名和扩展名
            filename = source_path.name
            name_part = source_path.stem
            ext_part = source_path.suffix
            
            # 检查目标目录中是否已存在同名文件
            target_path = local_equiv_path / filename
            final_filename = filename
            renamed = False
            
            if target_path.exists():
                # 如果远端也有同名文件，使用重命名策略
                print(f"🔄 LOCAL_EQUIVALENT中发现同名文件，检查远端是否也存在: {filename}")
                
                # 检查远端是否有同名文件
                remote_has_same_file = self._check_remote_file_exists(filename)
                
                # 检查是否在删除时间缓存中（5分钟内删除过）
                cache_suggests_rename = self.should_rename_file(filename)
                
                if remote_has_same_file or cache_suggests_rename:
                    # 远端有同名文件或缓存建议重命名，使用重命名策略
                    counter = 1
                    while target_path.exists():
                        # 生成新的文件名：name_1.ext, name_2.ext, ...
                        new_filename = f"{name_part}_{counter}{ext_part}"
                        target_path = local_equiv_path / new_filename
                        counter += 1
                    
                    final_filename = target_path.name
                    renamed = True
                    
                    if cache_suggests_rename:
                        print(f"🏷️  基于删除缓存重命名文件: {filename} -> {final_filename}")
                    else:
                        print(f"🏷️  重命名文件以避免冲突: {filename} -> {final_filename}")
                else:
                    # 远端没有同名文件且缓存无风险，删除本地旧文件并记录删除
                    try:
                        target_path.unlink()
                        print(f"🗑️  删除LOCAL_EQUIVALENT中的旧文件: {filename}")
                        
                        # 记录删除到缓存
                        self.add_deletion_record(filename)
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"删除旧文件失败: {e}"
                        }
            
            # 复制文件而不是移动（保留原文件）
            shutil.copy2(str(source_path), str(target_path))
            
            return {
                "success": True,
                "original_path": str(source_path),
                "new_path": str(target_path),
                "filename": final_filename,
                "original_filename": filename,
                "renamed": renamed
            }
            
        except Exception as e:
            return self._handle_exception(e, "移动文件")

    def check_network_connection(self):
        """
        检测网络连接状态
        
        Returns:
            dict: 网络连接状态
        """
        try:
            # 如果有可用的API服务，直接测试API连接
            if self.drive_service:
                try:
                    # 尝试一个简单的API调用
                    result = self.drive_service.test_connection()
                    if result.get('success'):
                        return self._create_success_result("Google Drive API连接正常")
                    else:
                        return {"success": False, "error": f"Google Drive API连接失败: {result.get('error', '未知错误')}"}
                except Exception as e:
                    # API测试失败，继续尝试ping
                    pass
            
            # 回退到ping测试（更宽松的参数）
            import platform
            if platform.system() == "Darwin":  # macOS
                ping_cmd = ["ping", "-c", "1", "-W", "3000", "8.8.8.8"]  # 使用Google DNS
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "3", "8.8.8.8"]
            
            result = subprocess.run(
                ping_cmd, 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                return self._create_success_result("网络连接正常")
            else:
                # 网络测试失败但不影响功能
                return {"success": True, "message": "网络状态未知，但将继续执行"}
                
        except subprocess.TimeoutExpired:
            return {"success": True, "message": "网络检测超时，但将继续执行"}
        except Exception as e:
            return {"success": True, "message": f"网络检测失败，但将继续执行: {e}"}

    def calculate_timeout_from_file_sizes(self, file_moves):
        """
        根据文件大小计算超时时间
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            int: 超时时间（秒）
        """
        try:
            total_size_mb = 0
            for file_info in file_moves:
                file_path = file_info["new_path"]
                if os.path.exists(file_path):
                    size_bytes = os.path.getsize(file_path)
                    size_mb = size_bytes / (1024 * 1024)  # 转换为MB
                    total_size_mb += size_mb
            
            # 基础检测时间30秒 + 按照100KB/s的速度计算文件传输时间
            # 100KB/s = 0.1MB/s，所以每MB需要10秒
            base_time = 30  # 基础检测时间（从10秒增加到30秒）
            transfer_time = max(30, int(total_size_mb * 10))  # 按100KB/s计算，最少30秒（从10秒增加到30秒）
            timeout = base_time + transfer_time
            
            return timeout
            
        except Exception as e:
            print(f"计算超时时间时出错: {e}")
            return 60  # 默认60秒（10秒基础 + 50秒传输）

    def wait_for_file_sync(self, expected_files, file_moves):
        """
        等待文件同步到 DRIVE_EQUIVALENT 目录，使用GDS ls命令检测
        
        Args:
            expected_files (list): 期望同步的文件名列表
            file_moves (list): 文件移动信息列表（用于计算超时时间）
            
        Returns:
            dict: 同步状态
        """
        try:
            # 根据文件大小计算超时时间
            timeout = self.calculate_timeout_from_file_sizes(file_moves)
            
            start_time = time.time()
            synced_files = []
            check_count = 0
            next_check_delay = 1.0  # 第一次检测等待1秒
            
            # 只显示一行简洁的开始信息
            print(f"⏳", end="", flush=True)
            
            while time.time() - start_time < timeout:
                check_count += 1
                elapsed_time = time.time() - start_time
                
                # 直接使用 ls_with_folder_id 检查 DRIVE_EQUIVALENT 目录
                try:
                    # 使用内部API直接检查DRIVE_EQUIVALENT目录
                    ls_result = self.ls_with_folder_id(self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, detailed=False)
                    
                    if ls_result.get("success"):
                        files = ls_result.get("files", [])
                        current_synced = []
                        
                        for filename in expected_files:
                            # 检查文件名是否在DRIVE_EQUIVALENT中
                            file_found = any(f.get("name") == filename for f in files)
                            if file_found:
                                current_synced.append(filename)
                        
                        # 如果所有文件都已同步，返回成功
                        if len(current_synced) == len(expected_files):
                            print(f" ({elapsed_time:.1f}s)")
                            return {
                                "success": True,
                                "synced_files": current_synced,
                                "sync_time": elapsed_time,
                                "base_sync_time": elapsed_time  # 保存基础同步时间用于计算额外等待
                            }
                        
                        # 更新已同步文件列表
                        synced_files = current_synced
                        
                except Exception as e: 
                    pass  # 静默处理错误
                
                # 显示一个点表示检测进行中
                print(".", end="", flush=True)
                
                # 使用对数规律增加等待时间：每次 * √2，最多等待16秒
                time.sleep(min(next_check_delay, 16))
                next_check_delay *= 1.414  # √2 ≈ 1.414
            
            # 超时，返回当前状态
            missing_files = [f for f in expected_files if f not in synced_files]
            print(f" ⏰ 超时 ({timeout}s)")
            
            return {
                "success": len(synced_files) > 0,
                "error": "文件同步超时，但部分文件可能已同步",
                "synced_files": synced_files,
                "missing_files": missing_files,
                "sync_time": timeout
            }
            
        except Exception as e:
            print(f" ❌ 检测失败: {e}")
            return {"success": False, "error": f"文件同步检测失败: {e}"}

    def _wait_for_zip_sync(self, zip_filename, timeout=60):
        """
        等待zip文件同步到远程目录
        
        Args:
            zip_filename (str): 要等待的zip文件名
            timeout (int): 超时时间（秒）
            
        Returns:
            dict: 等待结果
        """
        try:
            import time
            
            print(f"⏳ 等待zip文件同步: {zip_filename}")
            
            start_time = time.time()
            check_count = 0
            next_check_delay = 1.0  # 第一次检测等待1秒
            
            # 只显示一行简洁的开始信息
            print(f"⏳", end="", flush=True)
            
            while time.time() - start_time < timeout:
                check_count += 1
                elapsed_time = time.time() - start_time
                
                # 使用 ls 命令检查文件是否存在
                try:
                    check_result = self.main_instance.cmd_ls(".")
                    if check_result.get("success"):
                        files = check_result.get("files", [])
                        zip_exists = any(f.get("name") == zip_filename for f in files)
                        
                        if zip_exists:
                            print(f" ({elapsed_time:.1f}s)")
                            return {
                                "success": True,
                                "message": f"zip文件同步完成: {zip_filename}",
                                "sync_time": elapsed_time
                            }
                        
                except Exception as e:
                    pass  # 静默处理检查错误
                
                # 显示一个点表示检测进行中
                print(".", end="", flush=True)
                
                # 使用对数规律增加等待时间：每次 * √2，最多等待8秒
                time.sleep(min(next_check_delay, 8))
                next_check_delay *= 1.414  # √2 ≈ 1.414
            
            # 超时，返回失败
            print(f" ⏰ 超时 ({timeout}s)")
            return {
                "success": False,
                "error": f"zip文件同步超时: {zip_filename}",
                "sync_time": timeout
            }
            
        except Exception as e:
            print(f" ❌ 检测失败: {e}")
            return {"success": False, "error": f"zip文件同步检测失败: {e}"}

    def _wait_for_file_sync_with_timeout(self, expected_files, file_moves, custom_timeout):
        """
        等待文件同步到 DRIVE_EQUIVALENT 目录，使用自定义超时时间
        
        Args:
            expected_files (list): 期望同步的文件名列表
            file_moves (list): 文件移动信息列表
            custom_timeout (int): 自定义超时时间（秒）
            
        Returns:
            dict: 同步状态
        """
        try:
            start_time = time.time()
            synced_files = []
            check_count = 0
            next_check_delay = 1.0  # 第一次检测等待1秒
            
            # 只显示一行简洁的开始信息
            print(f"⏳", end="", flush=True)
            
            while time.time() - start_time < custom_timeout:
                check_count += 1
                elapsed_time = time.time() - start_time
                
                # 使用 GDS ls 命令检查 DRIVE_EQUIVALENT 目录
                try:
                    import subprocess
                    import sys
                    
                    # 执行 GDS ls 命令
                    result = subprocess.run([
                        sys.executable, "GOOGLE_DRIVE.py", "--shell", "ls"
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        # 解析输出，查找期望的文件
                        output_lines = result.stdout.strip().split('\n')
                        current_synced = []
                        
                        for filename in expected_files:
                            # 检查文件名是否在输出中
                            for line in output_lines:
                                if filename in line:
                                    current_synced.append(filename)
                                    break
                        
                        # 如果所有文件都已同步，返回成功
                        if len(current_synced) == len(expected_files):
                            print(f" ({elapsed_time:.1f}s)")
                            return {
                                "success": True,
                                "synced_files": current_synced,
                                "sync_time": elapsed_time,
                                "base_sync_time": elapsed_time  # 保存基础同步时间用于计算额外等待
                            }
                        
                        # 更新已同步文件列表
                        synced_files = current_synced
                        
                except subprocess.TimeoutExpired:
                    pass  # 静默处理超时
                except Exception:
                    pass  # 静默处理错误
                
                # 显示一个点表示检测进行中
                print(".", end="", flush=True)
                
                # 使用对数规律增加等待时间：每次 * √2，最多等待16秒
                time.sleep(min(next_check_delay, 16))
                next_check_delay *= 1.414  # √2 ≈ 1.414
            
            # 超时，返回当前状态
            missing_files = [f for f in expected_files if f not in synced_files]
            print(f" ⏰ 重试超时 ({custom_timeout}s)")
            
            return {
                "success": len(synced_files) > 0,
                "error": "文件同步重试超时，但部分文件可能已同步",
                "synced_files": synced_files,
                "missing_files": missing_files,
                "sync_time": custom_timeout
            }
            
        except Exception as e:
            print(f" ❌ 重试检测失败: {e}")
            return {"success": False, "error": f"文件同步重试检测失败: {e}"}

    def _restart_google_drive_desktop(self):
        """
        重启Google Drive Desktop应用
        
        Returns:
            bool: 重启是否成功
        """
        try:
            import subprocess
            import sys
            
            print("🔄 正在重启Google Drive Desktop...")
            
            # 调用主GOOGLE_DRIVE.py的重启功能
            result = subprocess.run([
                sys.executable, "GOOGLE_DRIVE.py", "--desktop", "--restart"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # print("✅ Google Drive Desktop重启成功")
                return True
            else:
                # print(f"❌ Google Drive Desktop重启失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Google Drive Desktop重启超时")
            return False
        except Exception as e:
            print(f"❌ 重启Google Drive Desktop时出错: {e}")
            return False

    def _wait_for_drive_equivalent_file_deletion(self, filename, timeout=60):
        """
        等待DRIVE_EQUIVALENT中的文件被删除，使用内部ls_with_folder_id接口
        
        Args:
            filename (str): 要等待删除的文件名
            timeout (int): 超时时间（秒）
            
        Returns:
            dict: 等待结果
        """
        try:
            import time
            
            print(f"⏳ 等待DRIVE_EQUIVALENT中的文件删除: {filename}")
            print(f"🔍 检查远端目录ID: {self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID}")
            
            start_time = time.time()
            
            # 60秒检测机制，每秒检查一次
            for attempt in range(timeout):
                try:
                    # 使用内部ls_with_folder_id接口检查DRIVE_EQUIVALENT目录
                    ls_result = self.ls_with_folder_id(self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, detailed=False)
                    
                    if ls_result.get("success"):
                        files = ls_result.get("files", [])
                        file_found = any(f.get("name") == filename for f in files)
                        
                        if not file_found:
                            print(f"✅ DRIVE_EQUIVALENT中的文件已删除: {filename}")
                            return {"success": True, "message": f"File {filename} deleted from DRIVE_EQUIVALENT"}
                    else:
                        print(f"⚠️ ls检查失败: {ls_result.get('error')}")
                
                except Exception as check_error:
                    print(f"⚠️ 检查文件时出错: {check_error}")
                
                # 显示进度点，类似上传时的显示
                if attempt % 5 == 0 and attempt > 0:
                    elapsed = time.time() - start_time
                    print(f"⏳ 等待删除中... ({elapsed:.0f}s)")
                else:
                    print(".", end="", flush=True)
                
                time.sleep(1)
            
            # 超时
            print(f"\n⏰ 删除等待超时 ({timeout}s): {filename}")
            print(f"⚠️ 警告: DRIVE_EQUIVALENT中的文件删除检测超时，但将继续上传")
            return {
                "success": False, 
                "error": f"Timeout waiting for {filename} deletion in DRIVE_EQUIVALENT"
            }
            
        except Exception as e:
            print(f"⚠️ 删除等待过程中出错: {e}")
            return {"success": False, "error": f"Error waiting for file deletion: {e}"}

    def _wait_and_read_result_file(self, result_filename):
        """
        等待并读取远端结果文件，最多等待60秒
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            
        Returns:
            dict: 读取结果
        """
        try:
            import sys
            
            # 远端文件路径（在REMOTE_ROOT/tmp目录中）
            remote_file_path = f"~/tmp/{result_filename}"
            
            # 输出等待指示器
            print("⏳", end="", flush=True)
            
            # 等待文件出现，最多60秒
            max_wait_time = 60
            for wait_count in range(max_wait_time):
                # 检查文件是否存在
                check_result = self._check_remote_file_exists_absolute(remote_file_path)
                
                if check_result.get("exists"):
                    # 文件存在，读取内容
                    print()  # 换行
                    return self._read_result_file_via_gds(result_filename)
                
                # 文件不存在，等待1秒并输出进度点
                time.sleep(1)
                print(".", end="", flush=True)
            
            # 超时，提供用户输入fallback
            print()  # 换行
            print(f"⚠️  等待远端结果文件超时（60秒）: {remote_file_path}")
            print("这可能是因为:")
            print("  1. 命令正在后台运行（如http-server等服务）")
            print("  2. 命令执行时间超过60秒")
            print("  3. 远端出现意外错误")
            print()
            print("请手动提供执行结果:")
            print("- 输入多行内容描述命令执行情况")
            print("- 按 Ctrl+D 结束输入")
            print("- 或直接按 Enter 跳过")
            print()
            
            # 获取用户手动输入
            user_feedback = self._get_multiline_user_input()
            
            if user_feedback.strip():
                # 用户提供了反馈
                return {
                    "success": True,
                    "data": {
                        "cmd": "unknown",
                        "args": [],
                        "working_dir": "unknown", 
                        "timestamp": "unknown",
                        "exit_code": 0,  # 假设成功
                        "stdout": user_feedback,
                        "stderr": "",
                        "source": "user_input",  # 标记来源
                        "note": "用户手动输入的执行结果"
                    }
                }
            else:
                # 用户跳过了输入
                return {
                    "success": False,
                    "error": f"等待远端结果文件超时（60秒），用户未提供反馈: {remote_file_path}"
                }
            
        except Exception as e:
            print()  # 换行
            return {
                "success": False,
                "error": f"等待结果文件时出错: {str(e)}"
            }
