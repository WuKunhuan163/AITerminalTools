#!/usr/bin/env python3
"""
Google Drive Shell - Remote Commands Module
从google_drive_shell.py重构而来的remote_commands模块
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

from .constants import get_bg_status_file, get_bg_script_file, get_bg_log_file, get_bg_result_file

import threading
import time
import json
import subprocess
import os
import sys

class DebugCapture:
    """Debug信息捕获和存储系统"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.debug_buffer = []
                    cls._instance.capturing = False
        return cls._instance
    
    def start_capture(self):
        """开始捕获debug信息"""
        self.capturing = True
    
    def stop_capture(self):
        """停止捕获debug信息"""
        self.debug_buffer = []
        self.capturing = False
    
    def add_debug(self, message):
        """添加debug信息到缓存"""
        if self.capturing:
            self.debug_buffer.append(message)
    
    def get_debug_info(self):
        """获取所有捕获的debug信息"""
        return '\n'.join(self.debug_buffer)
    
    def clear_buffer(self):
        """清空debug缓存"""
        self.debug_buffer = []

# 全局debug捕获实例
debug_capture = DebugCapture()

def debug_print(*args, **kwargs):
    """统一的debug输出函数，捕获时只存储，不捕获时正常输出"""
    # 构建消息字符串
    message = ' '.join(str(arg) for arg in args)
    
    # 如果正在捕获，添加到缓存
    if debug_capture.capturing:
        debug_capture.add_debug(message)
    else:
        # 不在捕获期间，正常输出到控制台
        print(*args, **kwargs)

class RemoteCommands:
    """Google Drive Shell Remote Commands"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance
        
        # 特殊命令列表 - 这些命令在本地处理，不需要远端执行
        # 注意：echo已被移除，现在通过通用远程命令执行
        self.SPECIAL_COMMANDS = {
            'ls', 'cd', 'pwd', 'mkdir', 'mv', 'cat', 'grep', 
            'upload', 'download', 'edit', 'read', 'find', 'help', 'exit', 'quit', 'venv'
        }
    

    
    def generate_commands(self, file_moves, target_path, folder_upload_info=None):
        """
        生成远程命令
        
        Args:
            file_moves (list): 文件移动信息列表
            target_path (str): 目标路径
            folder_upload_info (dict, optional): 文件夹上传信息
            
        Returns:
            str: 生成的远程命令
        """
        try:
            # 准备文件移动信息
            all_file_moves = []
            for file_move in file_moves:
                all_file_moves.append({
                    "filename": file_move["filename"],
                    "original_filename": file_move.get("original_filename", file_move["filename"]),
                    "renamed": file_move.get("renamed", False),
                    "target_path": target_path
                })
            
            # 调用多文件远程命令生成方法
            base_command = self._generate_multi_file_commands(all_file_moves)
            
            # 如果是文件夹上传，需要添加解压和清理命令
            if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
                zip_filename = folder_upload_info.get("zip_filename", "")
                keep_zip = folder_upload_info.get("keep_zip", False)
                
                if zip_filename:
                    # 计算目标路径
                    current_shell = self.main_instance.get_current_shell()
                    if target_path == "." or target_path == "":
                        if current_shell and current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                relative_path = current_path[2:]
                                remote_target_path = f"{self.main_instance.REMOTE_ROOT}/{relative_path}" if relative_path else self.main_instance.REMOTE_ROOT
                            else:
                                remote_target_path = self.main_instance.REMOTE_ROOT
                        else:
                            remote_target_path = self.main_instance.REMOTE_ROOT
                    elif target_path.startswith("/"):
                        remote_target_path = f"{self.main_instance.REMOTE_ROOT}{target_path}"
                    else:
                        remote_target_path = f"{self.main_instance.REMOTE_ROOT}/{target_path}"
                    
                    # 生成解压命令 - 使用统一函数
                    # generate_unzip_command现在是类方法
                    unzip_command = self.generate_unzip_command(
                        remote_target_path, 
                        zip_filename, 
                        delete_zip=not keep_zip,
                        handle_empty_zip=True
                    )
                    
                    # 将解压命令添加到基础命令之后
                    combined_command = f"{base_command}\n\n# 解压和清理zip文件\n({unzip_command})"
                    return combined_command
            
            return base_command
            
        except Exception as e:
            return f"# Error generating remote commands: {e}"

    def _escape_for_display(self, command):
        """
        为在echo中显示创建安全的命令版本
        处理特殊字符，避免破坏bash语法
        
        注意：这个函数的输出将用在双引号包围的echo命令中，
        在双引号内，大多数特殊字符会失去特殊含义，只需要转义少数字符
        """
        display_command = command
        
        # 处理反斜杠 - 必须首先处理，避免重复转义
        display_command = display_command.replace('\\', '\\\\')
        
        # 处理双引号 - 转义为\"
        display_command = display_command.replace('"', '\\"')
        
        # 处理美元符号 - 转义为\$（在双引号中仍有特殊含义）
        display_command = display_command.replace('$', '\\$')
        
        # 处理反引号 - 转义为\`（在双引号中仍有特殊含义）
        display_command = display_command.replace('`', '\\`')
        
        # 处理shell展开的家目录路径：将本地家目录路径转换回~显示
        # 这解决了"GDS cd ~"中~被shell展开为本地路径的显示问题
        import os
        local_home = os.path.expanduser("~")
        if local_home in display_command:
            # 只替换作为独立路径组件的家目录，避免误替换包含家目录路径的其他路径
            # 例如："/Users/username" -> "~", 但 "/Users/username/Documents" -> "~/Documents"
            display_command = display_command.replace(local_home, "~")
        
        # 注意：在双引号内，圆括号()、方括号[]、花括号{}等不需要转义
        # 因为它们在双引号内失去了特殊含义
        # 过度转义会导致显示时出现不必要的反斜杠
        
        return display_command

    def _test_command_in_local_environment(self, remote_command):
        """
        在本地测试环境中实际执行命令以检查是否有执行问题
        
        Args:
            remote_command (str): 要测试的远端命令
            
        Returns:
            dict: 测试结果，包含success和error字段
        """
        try:
            import tempfile
            import subprocess
            import os
            import shutil
            from pathlib import Path
            
            # 创建本地测试环境 ~/tmp/gds_test
            test_dir = Path.home() / "tmp" / "gds_test"
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # 模拟远端环境结构 - 在测试目录中创建，然后用符号链接
            local_mock_root = test_dir / "mock_remote_root"
            local_mock_root.mkdir(parents=True, exist_ok=True)
            
            local_tmp_dir = local_mock_root / "tmp"
            local_tmp_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建模拟的指纹文件以通过挂载检查
            fingerprint_file = local_mock_root / ".gds_mount_fingerprint_test"
            fingerprint_file.write_text("test fingerprint")
            
            # 创建符号链接模拟远端路径（需要sudo权限，所以改用替换策略）
            # 而是在测试脚本中替换路径
            
            # 创建测试脚本，将远端路径替换为本地测试路径
            test_command = remote_command.replace(
                '/content/drive/MyDrive/REMOTE_ROOT', 
                str(local_mock_root)
            )
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, dir=test_dir) as f:
                f.write('#!/bin/bash\n')
                f.write('set -e\n')  # 遇到错误立即退出
                f.write(f'cd "{test_dir}"\n')  # 切换到测试目录
                f.write(test_command)
                test_script = f.name
            
            try:
                # 执行测试脚本，设置较短超时
                result = subprocess.run(
                    ['bash', test_script], 
                    capture_output=True, 
                    text=True, 
                    timeout=10.0,  # 10秒超时
                    cwd=test_dir
                )
                
                if result.returncode == 0:
                    return {"success": True, "message": "命令在本地测试环境执行成功"}
                else:
                    return {
                        "success": False, 
                        "error": f"命令执行失败 (exit code: {result.returncode}): {result.stderr.strip()}"
                    }
            finally:
                # 清理测试文件
                try:
                    os.unlink(test_script)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令执行超时（10秒）"}
        except Exception as e:
            return {"success": False, "error": f"测试执行失败: {str(e)}"}

    def _check_specific_fingerprint_file(self, fingerprint_file):
        """
        检查特定的指纹文件是否存在
        
        Args:
            fingerprint_file (str): 指纹文件的完整路径
            
        Returns:
            dict: 检查结果，包含exists字段
        """
        try:
            import subprocess
            import os
            
            # 使用Python os.path.exists来检查特定文件
            python_check_script = f'''
import os
import sys
import glob

# 检查具体文件
if os.path.exists("{fingerprint_file}"):
    sys.exit(0)  # 文件存在
else:
    # 检查目录是否存在
    dir_path = os.path.dirname("{fingerprint_file}")
    # 列出所有指纹文件
    pattern = "{fingerprint_file}".rsplit("_", 1)[0] + "_*"
    matching_files = glob.glob(pattern)
    sys.exit(1)  # 文件不存在
'''
            
            result = subprocess.run(
                ['python3', '-c', python_check_script],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            return {"exists": result.returncode == 0}
            
        except Exception as e:
            # 如果检查失败，假设挂载无效
            return {"exists": False, "error": str(e)}

    def _check_fingerprint_files_exist(self, fingerprint_pattern):
        """
        检查指纹文件是否存在，用于验证挂载状态
        
        Args:
            fingerprint_pattern (str): 指纹文件匹配模式
            
        Returns:
            dict: 检查结果，包含exists字段
        """
        try:
            import subprocess
            import os
            
            # 使用Python glob来检查指纹文件，避免bash通配符问题
            python_check_script = f'''
import glob
import sys
fingerprint_files = glob.glob("{fingerprint_pattern}")
if fingerprint_files:
    sys.exit(0)  # 找到指纹文件
else:
    sys.exit(1)  # 没有找到指纹文件
'''
            
            result = subprocess.run(
                ['python3', '-c', python_check_script],
                capture_output=True,
                timeout=5
            )
            
            return {"exists": result.returncode == 0}
            
        except Exception as e:
            # 如果检查失败，假设挂载无效
            return {"exists": False, "error": str(e)}

    def validate_bash_syntax_fast(self, command):
        """
        快速验证bash命令语法
        
        Args:
            command (str): 要验证的bash命令
            
        Returns:
            dict: 验证结果，包含success和error字段
        """
        try:
            import tempfile
            import subprocess
            import os
            
            # 创建临时文件存储命令
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                f.write('#!/bin/bash\n')
                f.write(command)
                temp_file = f.name
            
            try:
                # 使用bash -n检查语法，设置短超时
                result = subprocess.run(
                    ['bash', '-n', temp_file], 
                    capture_output=True, 
                    text=True, 
                    timeout=2.0  # 2秒超时，避免并发时的超时问题
                )
                
                if result.returncode == 0:
                    return {"success": True, "message": "Bash syntax is valid"}
                else:
                    return {
                        "success": False, 
                        "error": f"Bash syntax error: {result.stderr.strip()}"
                    }
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return {
                "success": False, 
                "error": "Bash syntax check timeout"
            }
        except Exception as e:
            return {
                "success": False, 
                "error": f"Syntax check failed: {str(e)}"
            }

    def _wait_and_read_result_file(self, result_filename):
        """
        等待并读取远端结果文件，最多等待60秒
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            
        Returns:
            dict: 读取结果
        """
        try:
            import time
            
            # 远端文件路径（在REMOTE_ROOT/tmp目录中）
            remote_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"

            # 使用进度缓冲输出等待指示器
            from .progress_manager import start_progress_buffering
            start_progress_buffering("⏳ Waiting for result ...")
            
            # 等待文件出现，最多30秒，支持Ctrl+C中断
            max_wait_time = 30
            import signal
            import sys
            
            # 设置KeyboardInterrupt标志
            interrupted = False
            
            def signal_handler(signum, frame):
                nonlocal interrupted
                interrupted = True
            
            # 注册信号处理器
            old_handler = signal.signal(signal.SIGINT, signal_handler)
            
            try:
                for i in range(max_wait_time):
                    # 在每次循环开始时检查中断标志
                    if interrupted:
                        raise KeyboardInterrupt()
                    
                    # 检查文件是否存在
                    check_result = self._check_remote_file_exists(remote_file_path)
                    
                    if check_result.get("exists"):
                        # 文件存在，读取内容
                        file_result = self._read_result_file_via_gds(result_filename)
                        
                        # 直接清除进度显示，不添加√标记（与upload validation保持一致）
                        from .progress_manager import clear_progress
                        clear_progress()
                        
                        # 恢复原来的信号处理器
                        signal.signal(signal.SIGINT, old_handler)
                        return file_result
                    
                    # 文件不存在，等待1秒并输出进度点
                    # 使用可中断的等待，每100ms检查一次中断标志
                    for j in range(10):  # 10 * 0.1s = 1s
                        if interrupted:
                            raise KeyboardInterrupt()
                        time.sleep(0.1)
                    
                    from .progress_manager import progress_print
                    progress_print(f".")
                
            except KeyboardInterrupt:
                # 用户按下Ctrl+C，清除进度显示并退出
                from .progress_manager import clear_progress
                clear_progress()
                # 恢复原来的信号处理器
                signal.signal(signal.SIGINT, old_handler)
                return {
                    "success": False,
                    "error": "Operation cancelled by Ctrl+C during waiting for result from remote. ",
                    "cancelled": True
                }
            finally:
                # 确保信号处理器总是被恢复
                try:
                    signal.signal(signal.SIGINT, old_handler)
                except:
                    pass
            
            # 超时处理，恢复信号处理器并显示超时信息
            signal.signal(signal.SIGINT, old_handler)
            print()  # 换行
            print(f"等待结果超时。可能的原因：")
            print(f"  (1) 网络问题导致命令执行缓慢。请检查")
            print(f"  (2) Google Drive挂载失效，需要使用 GOOGLE_DRIVE --remount重新挂载")
            
            # 检查是否在后台模式或无交互环境
            import sys
            import os
            is_background_mode = (
                not sys.stdin.isatty() or  # 非交互式终端
                not sys.stdout.isatty() or  # 输出被重定向
                os.getenv('PYTEST_CURRENT_TEST') is not None or  # pytest环境
                os.getenv('CI') is not None  # CI环境
            )
            
            if is_background_mode:
                print(f"后台模式检测：自动返回超时错误")
                return {
                    "success": False,
                    "error": f"Result file timeout: {remote_file_path}",
                    "timeout": True,
                    "background_mode": True
                }
            print(f"Please provide the execution result:")
            print(f"- Enter multiple lines to describe the command execution")
            print(f"- Press Ctrl+D to end input")
            print(f"- Or press Enter directly to skip")
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

    def _get_multiline_user_input(self):
        """
        获取用户的多行输入，支持Ctrl+D结束
        使用与USERINPUT完全相同的信号超时输入逻辑
        
        Returns:
            str: 用户输入的多行内容
        """
        lines = []
        timeout_seconds = 180  # 3分钟超时，和USERINPUT一致
        
        # 定义超时异常
        class TimeoutException(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutException("Input timeout")
        
        # 使用信号方式进行超时控制，完全复制USERINPUT逻辑
        import signal
        import readline
        
        original_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        
        try:
            while True:
                try:
                    line = input()
                    lines.append(line)
                    # 重置超时计时器，因为用户正在输入
                    signal.alarm(timeout_seconds)
                except EOFError:
                    # Ctrl+D，正常结束输入
                    print()  # 输出一个空行
                    break
                except TimeoutException:
                    # 超时发生 - 尝试捕获当前正在输入的行
                    try:
                        # 获取当前输入缓冲区的内容
                        current_line = readline.get_line_buffer()
                        if current_line.strip():
                            lines.append(current_line.strip())
                    except:
                        pass  # 如果无法获取缓冲区内容，忽略错误
                    print(f"\n[TIMEOUT] Input timeout ({timeout_seconds} seconds)")
                    break
        except KeyboardInterrupt:
            # Ctrl+C，询问是否取消
            print(f"\nCancel input? (y/N): ", end="", flush=True)
            try:
                response = input().strip().lower()
                if response in ['y', 'yes']:
                    return ""
                else:
                    print(f"Continue input (press Ctrl+D to end):")
                    # 重新开始输入循环
                    return self._get_multiline_user_input()
            except (EOFError, KeyboardInterrupt):
                return ""
        finally:
            # 清理超时设置
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
        
        # 组合所有行为最终输入
        return '\n'.join(lines).strip()

    def _read_result_file_via_gds(self, result_filename):
        """
        使用GDS ls和cat机制读取远端结果文件
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            
        Returns:
            dict: 读取结果
        """
        try:
            # 远端文件路径（在REMOTE_ROOT/tmp目录中）
            # 需要先cd到根目录，然后访问tmp目录
            remote_file_path = f"~/tmp/{result_filename}"
            
            # 首先使用ls检查文件是否存在
            check_result = self._check_remote_file_exists(remote_file_path)
            if not check_result.get("exists"):
                return {
                    "success": False,
                    "error": f"Remote result file does not exist: {remote_file_path}"
                }
            
            # 使用cat命令读取文件内容
            cat_result = self.main_instance.cmd_cat(remote_file_path)
            
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"Read file content failed: {cat_result.get('error', 'unknown error')}"
                }
            
            # 获取文件内容
            content = cat_result.get("output", "")
            
            # 尝试解析JSON
            try:
                import json
                # 预处理JSON内容以修复格式问题
                cleaned_content = self._preprocess_json_content(content)
                result_data = json.loads(cleaned_content)
                
                return {
                    "success": True,
                    "data": result_data
                }
            except json.JSONDecodeError as e:
                # 如果JSON解析失败，返回原始内容
                return {
                    "success": True,
                    "data": {
                        "exit_code": -1,
                        "stdout": content,
                        "stderr": f"JSON parse failed: {str(e)}",
                        "raw_content": content
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Read result file failed: {str(e)}"
            }

    def _check_remote_file_exists(self, file_path):
        """
        检查远端文件是否存在（绝对路径）
        
        Args:
            file_path (str): 绝对路径的文件路径（如~/tmp/filename.json）
            
        Returns:
            dict: 检查结果
        """
        try:
            # 解析路径
            if "/" in file_path:
                dir_path, filename = file_path.rsplit("/", 1)
            else:
                dir_path = "~"
                filename = file_path
            
            # 列出目录内容
            ls_result = self.main_instance.cmd_ls(dir_path)
            
            if not ls_result.get("success"):
                return {"exists": False, "error": f"Cannot access directory: {dir_path}"}
            
            # 检查文件和文件夹是否在列表中
            files = ls_result.get("files", [])
            folders = ls_result.get("folders", [])
            all_items = files + folders
            
            # 检查文件或文件夹是否存在
            file_exists = any(f.get("name") == filename for f in all_items)
            
            return {"exists": file_exists}
                
        except Exception as e:
            return {"exists": False, "error": f"Check file existence failed: {str(e)}"}

    def _preprocess_json_content(self, content):
        """
        预处理JSON内容以修复常见格式问题
        
        Args:
            content (str): 原始JSON内容
            
        Returns:
            str: 清理后的JSON内容
        """
        try:
            # 移除首尾空白
            content = content.strip()
            
            # 如果内容为空，返回默认JSON
            if not content:
                return '{"exit_code": -1, "stdout": "", "stderr": "empty content"}'
            
            # 简单的JSON修复：确保以{开头，}结尾
            if not content.startswith('{'):
                content = '{' + content
            if not content.endswith('}'):
                content = content + '}'
            
            return content
            
        except Exception as e:
            # 如果预处理失败，返回包装的原始内容
            return f'{{"exit_code": -1, "stdout": "{content}", "stderr": "preprocess failed: {str(e)}"}}'

    def _generate_multi_file_commands(self, all_file_moves):
        """生成简化的多文件上传远端命令，只显示关键状态信息"""
        try:
            # 生成文件信息数组 - 保留原有的路径解析逻辑
            file_info_list = []
            for i, file_info in enumerate(all_file_moves):
                filename = file_info["filename"]  # 重命名后的文件名（在DRIVE_EQUIVALENT中）
                original_filename = file_info.get("original_filename", filename)  # 原始文件名（目标文件名）
                target_path = file_info["target_path"]
                
                # 计算目标绝对路径 - 使用original_filename作为最终文件名
                target_filename = original_filename
                
                if target_path == "." or target_path == "":
                    # 当前目录
                    current_shell = self.main_instance.get_current_shell()
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:]
                            target_absolute = f"{self.main_instance.REMOTE_ROOT}/{relative_path}" if relative_path else self.main_instance.REMOTE_ROOT
                        else:
                            target_absolute = self.main_instance.REMOTE_ROOT
                    else:
                        target_absolute = self.main_instance.REMOTE_ROOT
                    dest_absolute = f"{target_absolute.rstrip('/')}/{target_filename}"
                else:
                    # 简化路径处理 - 其他情况都当作目录处理
                    current_shell = self.main_instance.get_current_shell()
                    current_path = current_shell.get("current_path", "~") if current_shell else "~"
                    
                    if current_path == "~":
                        target_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path.lstrip('/')}"
                    else:
                        current_subpath = current_path[2:] if current_path.startswith("~/") else current_path
                        target_absolute = f"{self.main_instance.REMOTE_ROOT}/{current_subpath}/{target_path.lstrip('/')}"
                    
                    dest_absolute = f"{target_absolute.rstrip('/')}/{target_filename}"
                
                # 源文件路径使用重命名后的文件名
                source_absolute = f"{self.main_instance.DRIVE_EQUIVALENT}/{filename}"
                
                file_info_list.append({
                    'source': source_absolute,
                    'dest': dest_absolute,
                    'original_filename': original_filename
                })
            
            # 收集所有需要创建的目录
            target_dirs = set()
            for file_info in file_info_list:
                dest_dir = '/'.join(file_info['dest'].split('/')[:-1])
                target_dirs.add(dest_dir)
            
            # 生成简化的命令 - 按照用户要求的格式
            mv_commands = []
            for file_info in file_info_list:
                mv_commands.append(f'mv "{file_info["source"]}" "{file_info["dest"]}"')
            
            # 创建目录命令
            mkdir_commands = [f'mkdir -p "{target_dir}"' for target_dir in sorted(target_dirs)]
            
            # 组合所有命令
            all_commands = mkdir_commands + mv_commands
            command_summary = f"mkdir + mv {len(file_info_list)} files"
            
            # 创建实际命令的显示列表 - 保持引号显示
            actual_commands_display = []
            if mkdir_commands:
                actual_commands_display.extend(mkdir_commands)
            actual_commands_display.extend(mv_commands)
            
            # 生成重试命令
            retry_commands = []
            for cmd in mv_commands:
                # 提取文件名用于显示
                try:
                    filename = cmd.split('"')[3].split('/')[-1] if len(cmd.split('"')) > 3 else 'file'
                except:
                    filename = 'file'
                
                retry_cmd = f'''
for attempt in $(seq 1 60); do
    if {cmd} 2>/dev/null; then
        break
    elif [ "$attempt" -eq 60 ]; then
        echo "Error: Error: {filename} move failed, still failed after 60 retries" >&2
        exit 1
    else
        sleep 1
    fi
done'''
                retry_commands.append(retry_cmd)
            
            # 生成简化的脚本，包含视觉分隔和实际命令显示
            script = f'''

# 创建目录
{chr(10).join(mkdir_commands)}

# 移动文件（带重试机制）
{chr(10).join(retry_commands)}

clear
echo "✅执行完成"'''
            
            return script
            
        except Exception as e:
            return f'echo "Error: 生成命令失败: {e}"'
    
    def _verify_upload_with_progress(self, expected_files, target_path, current_shell):
        """
        带进度显示的验证逻辑，类似上传过程
        对每个文件进行最多60次重试，显示⏳和点的进度
        """
        import time
        
        try:
            # 生成文件名列表用于显示
            if len(expected_files) <= 3:
                file_display = ", ".join(expected_files)
            else:
                first_three = ", ".join(expected_files[:3])
                file_display = f"{first_three}, ... ({len(expected_files)} files)"
            
            # 定义验证函数
            def validate_all_files():
                validation_result = self.main_instance.validation.verify_upload_success_by_ls(
                    expected_files=expected_files,
                    target_path=target_path,
                    current_shell=current_shell
                )
                found_count = len(validation_result.get("found_files", []))
                return found_count == len(expected_files)
            
            # 直接使用统一的验证接口，它会正确处理进度显示的切换
            from .progress_manager import validate_creation
            result = validate_creation(validate_all_files, file_display, 60, "upload")
            
            # 转换返回格式
            all_found = result["success"]
            if all_found:
                found_files = expected_files
                missing_files = []
            else:
                # 如果验证失败，需要重新检查哪些文件缺失
                final_validation = self.main_instance.validation.verify_upload_success_by_ls(
                    expected_files=expected_files,
                    target_path=target_path,
                    current_shell=current_shell
                )
                found_files = final_validation.get("found_files", [])
                missing_files = [f for f in expected_files if f not in found_files]
            
            return {
                "success": all_found,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_found": len(found_files),
                "total_expected": len(expected_files),
                "search_path": target_path
            }
            
        except Exception as e:
            debug_print(f"Validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "found_files": [],
                "missing_files": expected_files,
                "total_found": 0,
                "total_expected": len(expected_files)
            }

    def _generate_multi_mv_commands(self, file_pairs, current_shell):
        """生成多文件mv的分布式远端命令，每个文件独立重试60次"""
        try:
            # 生成文件信息数组
            file_info_list = []
            for i, (source, destination) in enumerate(file_pairs):
                source_absolute_path = self.resolve_remote_absolute_path(source, current_shell)
                destination_absolute_path = self.resolve_remote_absolute_path(destination, current_shell)
                
                file_info_list.append({
                    'source_name': source,
                    'dest_name': destination,
                    'source_path': source_absolute_path,
                    'dest_path': destination_absolute_path,
                    'index': i
                })
            
            # 生成分布式mv脚本
            full_command = f'''
# 初始化完成状态数组
declare -a completed
total_files={len(file_info_list)}

# 为每个文件启动独立的移动进程
'''
            
            for file_info in file_info_list:
                full_command += f'''
(
    echo -n "⏳ Moving {file_info['source_name']} -> {file_info['dest_name']}: "
    for attempt in $(seq 1 60); do
        if mv {file_info['source_path']} {file_info['dest_path']} 2>/dev/null; then
            echo "✅"
            completed[{file_info['index']}]=1
            break
        else
            if [ "$attempt" -eq 60 ]; then
                echo "Error: (已重试60次失败)"
                completed[{file_info['index']}]=0
            else
                echo -n "."
                sleep 1
            fi
        fi
    done
) &
'''
            
            # 等待所有进程完成并检查结果
            full_command += f'''
# 等待所有后台进程完成
wait

# 简化结果统计 - 检查目标文件是否存在
success_count=0
fail_count=0
'''
            
            # 为每个文件生成检查命令
            for file_info in file_info_list:
                full_command += f'''
if [ -f {file_info['dest_path']} ]; then
    ((success_count++))
else
    ((fail_count++))
fi
'''
            
            full_command += f'''
# 输出最终结果
total_files={len(file_info_list)}
if [ "${{fail_count:-0}}" -eq 0 ]; then
    echo "所有文件移动完成"
else
    echo "Warning: 部分文件移动完成: ${{success_count:-0}}/${{total_files:-0}} 成功, ${{fail_count:-0}} 失败"
fi
'''
            
            return full_command
            
        except Exception as e:
            return f"echo 'Error: 生成多文件mv命令失败: {e}'"

    def generate_mkdir_commands(self, target_path):
        """
        生成创建远端目录结构的命令
        
        Args:
            target_path (str): 目标路径
            
        Returns:
            str: mkdir 命令字符串，如果不需要创建目录则返回空字符串
        """
        try:
            # 如果是当前目录或根目录，不需要创建
            if target_path == "." or target_path == "" or target_path == "~":
                return ""
            
            # 计算需要创建的目录路径
            if target_path.startswith("/"):
                # 绝对路径
                full_target_path = target_path
            else:
                # 相对路径，基于 REMOTE_ROOT
                full_target_path = f"{self.main_instance.REMOTE_ROOT}/{target_path.lstrip('/')}"
            
            # 生成 mkdir -p 命令来创建整个目录结构，添加清屏和成功/失败提示
            mkdir_command = f'mkdir -p "{full_target_path}"'
            
            return mkdir_command
            
        except Exception as e:
            print(f"Error: Generate mkdir command failed: {e}")
            return ""



    def get_multiline_input_safe(self, prompt, single_line=False):
        """
        安全的多行输入函数，支持Ctrl+D结束输入
        
        Args:
            prompt (str): 输入提示
            single_line (bool): 是否只接受单行输入
            
        Returns:
            str: 用户输入的内容，如果用户取消则返回None
        """
        try:
            # 配置readline以支持中文字符
            import readline
            try:
                readline.set_startup_hook(None)
                readline.clear_history()
                
                # 设置编辑模式为emacs（支持更好的中文编辑）
                readline.parse_and_bind("set editing-mode emacs")
                # 启用UTF-8支持
                readline.parse_and_bind("set input-meta on")
                readline.parse_and_bind("set output-meta on")
                readline.parse_and_bind("set convert-meta off")
                # 启用中文字符显示
                readline.parse_and_bind("set print-completions-horizontally off")
                readline.parse_and_bind("set skip-completed-text on")
                # 确保正确处理宽字符
                readline.parse_and_bind("set enable-bracketed-paste on")
            except Exception:
                pass  # 如果配置失败，继续使用默认设置
            
            print(prompt, end="", flush=True)
            
            if single_line:
                # 单行输入
                try:
                    return input()
                except EOFError:
                    return None
            else:
                # 多行输入，直到Ctrl+D
                lines = []
                print(f"(多行输入，按 Ctrl+D 结束):")
                try:
                    while True:
                        line = input()
                        lines.append(line)
                except EOFError:
                    # Ctrl+D被按下，结束输入
                    pass
                
                return '\n'.join(lines) if lines else None
                
        except KeyboardInterrupt:
            # Ctrl+C被按下
            print(f"\nInput cancelled")
            return None
        except Exception as e:
            print(f"\nInput error: {e}")
            return None

    def _handle_successful_remote_execution(self, command_type, context_info):
        """
        处理用户确认成功后的逻辑
        
        Args:
            command_type (str): 命令类型
            context_info (dict): 上下文信息
            
        Returns:
            dict: 处理结果
        """
        try:
            if command_type == "upload":
                return self._handle_upload_success(context_info)
            elif command_type == "mkdir":
                # 使用统一的验证接口
                target_path = context_info.get("target_path", "")
                absolute_path = context_info.get("absolute_path", "")
                
                if not target_path:
                    return {
                        "success": True,
                        "user_confirmed": True,
                        "command_type": "mkdir",
                        "message": "Mkdir command executed successfully"
                    }
                
                def validate_mkdir():
                    check_result = self._check_remote_file_exists(absolute_path)
                    return check_result.get("exists")
                
                from .progress_manager import validate_creation, clear_progress, is_progress_active
                if is_progress_active():
                    clear_progress()
                validation_result = validate_creation(validate_mkdir, target_path, 60, "dir")
                
                if validation_result["success"]:
                    return {
                        "success": True,
                        "user_confirmed": True,
                        "command_type": "mkdir",
                        "message": f"Directory '{target_path}' created and verified successfully",
                        "path": target_path,
                        "absolute_path": absolute_path
                    }
                else:
                    return {
                        "success": False,
                        "user_confirmed": False,
                        "command_type": "mkdir",
                        "message": validation_result["message"],
                        "path": target_path,
                        "absolute_path": absolute_path
                    }
            elif command_type == "touch":
                return self._handle_touch_success(context_info)
            elif command_type == "move":
                return self._handle_move_success(context_info)
            else:
                # 通用成功处理
                return {
                    "success": True,
                    "user_confirmed": True,
                    "command_type": command_type,
                    "message": "Remote command execution completed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "post_processing_error": True,
                "error": str(e),
                "message": f"Post-processing error: {e}"
            }

    def _handle_touch_success(self, context_info):
        """处理touch命令成功后的逻辑，包含延迟检测机制"""
        try:
            import time
            
            filename = context_info.get("filename", "")
            absolute_path = context_info.get("absolute_path", "")
            
            if not filename:
                return {
                    "success": True,
                    "user_confirmed": True,
                    "command_type": "touch",
                    "message": "Touch command executed successfully"
                }
            
            # 使用统一的验证接口
            def validate_touch():
                check_result = self._check_remote_file_exists(absolute_path)
                return check_result.get("exists")
            
            from .progress_manager import validate_creation, clear_progress, is_progress_active
            if is_progress_active():
                clear_progress()
            validation_result = validate_creation(validate_touch, filename, 60, "file")
            
            if validation_result["success"]:
                return {
                    "success": True,
                    "user_confirmed": True,
                    "command_type": "touch",
                    "message": f"File '{filename}' created and verified successfully",
                    "filename": filename,
                    "absolute_path": absolute_path
                }
            else:
                return {
                    "success": False,
                    "user_confirmed": False,
                    "command_type": "touch",
                    "message": validation_result["message"],
                    "filename": filename,
                    "absolute_path": absolute_path
                }

        except Exception as e:
            # 验证过程出错，返回失败
            return {
                "success": False,
                "user_confirmed": False,
                "command_type": "touch",
                "message": f"File created successfully (validation error: {str(e)[:50]})",
                "validation_error": str(e)
            }

    def _handle_move_success(self, context_info):
        """处理move命令成功后的逻辑"""
        return {
            "success": True,
            "user_confirmed": True,
            "command_type": "move",
            "message": "Move command executed successfully"
        }

    def _handle_upload_success(self, context_info):
        """处理upload命令成功后的逻辑"""
        try:
            # debug_print is already defined in this module
            
            # 获取期望的文件名列表和目标文件夹信息
            expected_filenames = context_info.get("expected_filenames", [])
            target_folder_id = context_info.get("target_folder_id")
            target_path = context_info.get("target_path")
            
            # 如果target_folder_id为None（目标目录不存在），需要重新解析路径
            if expected_filenames and target_folder_id is None and target_path:
                debug_print(f"target_folder_id is None, re-resolving target_path='{target_path}' after remote execution")
                current_shell = self.main_instance.get_current_shell()
                if current_shell:
                    # 尝试重新解析目标路径（目录现在应该存在了）
                    resolved_folder_id, resolved_display_path = self.main_instance.resolve_path(target_path, current_shell)
                    if resolved_folder_id:
                        target_folder_id = resolved_folder_id
                        debug_print(f"re-resolved target_folder_id='{target_folder_id}', display_path='{resolved_display_path}'")
                    else:
                        debug_print(f"failed to re-resolve target_path='{target_path}', will use parent folder for validation")
                        # 如果重新解析失败，使用父目录作为fallback
                        target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                        debug_print(f"using parent folder_id='{target_folder_id}' as fallback")
            
            # 如果有验证信息，进行文件验证
            debug_print(f"Validation check - expected_filenames={expected_filenames}, target_path='{target_path}'")
            if expected_filenames and target_path is not None:
                debug_print(f"Starting ls-based validation with {len(expected_filenames)} files")
                current_shell = self.main_instance.get_current_shell()
                
                # 使用带进度显示的验证逻辑，类似上传过程
                validation_result = self._verify_upload_with_progress(
                    expected_files=expected_filenames,
                    target_path=target_path,
                    current_shell=current_shell
                )
                
                debug_print(f"Validation completed - validation_result={validation_result}")
                return {
                    "success": validation_result["success"],
                    "user_confirmed": True,
                    "command_type": "upload",
                    "message": "Upload completed successfully" if validation_result["success"] else "Upload command executed but files not found in target location",
                    "found_files": validation_result.get("found_files", []),
                    "missing_files": validation_result.get("missing_files", []),
                    "total_found": validation_result.get("total_found", 0),
                    "total_expected": validation_result.get("total_expected", 0)
                }
            else:
                # 没有验证信息或文件夹上传，返回基本成功状态
                is_folder_upload = context_info.get("is_folder_upload", False)
                if is_folder_upload:
                    debug_print(f"Skipping validation for folder upload - trusting remote command execution")
                    return {
                        "success": True,
                        "user_confirmed": True,
                        "command_type": "upload",
                        "message": "Folder upload and extraction completed successfully"
                    }
                else:
                    debug_print(f"Skipping validation - expected_filenames={expected_filenames}, target_path='{target_path}'")
                    return {
                        "success": True,
                        "user_confirmed": True,
                        "command_type": "upload",
                        "message": "Upload completed successfully"
                    }
                
        except Exception as e:
            # 验证失败，但用户确认成功，记录错误但返回成功
            return {
                "success": True,
                "user_confirmed": True,
                "command_type": "upload",
                "message": f"Upload command executed but verification failed: {str(e)}",
                "found_files": [],
                "verification_error": str(e)
            }



    def _remove_emoji_from_args(self, args):
        """移除参数中的emoji字符，避免远程shell编码问题"""
        def remove_emoji(text):
            if not isinstance(text, str):
                return text
            # 移除emoji字符（Unicode范围）
            import re
            emoji_pattern = re.compile("["
                u"\U0001F600-\U0001F64F"  # emoticons
                u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                u"\U0001F680-\U0001F6FF"  # transport & map symbols
                u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                u"\U00002702-\U000027B0"
                u"\U000024C2-\U0001F251"
                u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                u"\U00002600-\U000026FF"  # Miscellaneous Symbols
                u"\U0000FE00-\U0000FE0F"  # Variation Selectors
                "]+", flags=re.UNICODE)
            return emoji_pattern.sub('', text)
        
        cleaned_args = []
        for arg in args:
            cleaned_args.append(remove_emoji(arg))
        return cleaned_args

    def execute_generic_command(self, cmd, args, _skip_queue_management=False, _original_user_command=None):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            _skip_queue_management (bool): 是否跳过队列管理（避免双重管理）
            
        Returns:
            dict: 执行结果，包含stdout、stderr、path等字段
        """
        # 移除emoji字符避免远程shell编码问题（暂时禁用，测试base64方案）
        # cleaned_args = self._remove_emoji_from_args(args)
        cleaned_args = args  # 使用原始args测试base64编码
        # 保存原始用户命令用于后续分析
        if _original_user_command:
            original_cmd, original_args = _original_user_command
        elif hasattr(self.main_instance, '_original_user_command'):
            # 从主实例获取原始用户命令
            original_user_cmd = self.main_instance._original_user_command
            # 简单解析原始命令
            parts = original_user_cmd.split()
            if parts:
                original_cmd = parts[0]
                original_args = parts[1:] if len(parts) > 1 else []
            else:
                original_cmd = cmd
                original_args = cleaned_args
        else:
            original_cmd = cmd
            original_args = cleaned_args
        
        # 调试日志已禁用
        # 导入正确的远程窗口队列管理器并生成唯一的窗口ID
        import threading
        import time
        import uuid
        
        # 设置时间戳基准点（如果还没有设置的话）
        if not hasattr(self, '_debug_start_time'):
            self._debug_start_time = time.time()
        
        def get_relative_timestamp():
            return f"{time.time() - self._debug_start_time:.3f}s"
        
        def debug_log(message):
            """写入调试信息到文件 - 启用详细调试"""
            try:
                # 写入到GOOGLE_DRIVE_DATA文件夹中的调试文件
                from pathlib import Path
                current_dir = Path(__file__).parent.parent
                debug_file = current_dir / "GOOGLE_DRIVE_DATA" / "remote_commands_debug.log"
                debug_file.parent.mkdir(exist_ok=True)
                
                with open(debug_file, 'a', encoding='utf-8') as f:
                    timestamp = time.strftime('%H:%M:%S.%f')[:-3]  # 精确到毫秒
                    f.write(f"[{timestamp}] {message}\n")
                
                # 调试输出已禁用以减少日志噪音
                pass
            except Exception as e:
                pass  # 调试错误也不输出
        
        # 使用WindowManager替代旧的队列系统
        debug_log(f"🏗️ DEBUG: [{get_relative_timestamp()}] [WINDOW_MANAGER] 使用WindowManager统一管理窗口")
        
        window_id = f"{cmd}_{threading.get_ident()}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        
        # WindowManager自动处理队列，无需手动槽位管理
        debug_log(f"🪟 DEBUG: [{get_relative_timestamp()}] [WINDOW_SHOW] 准备通过WindowManager显示窗口 - window_id: {window_id}, cmd: {cmd}, thread: {threading.get_ident()}")
        
        try:
            # 检查是否为特殊命令
            if cmd in self.SPECIAL_COMMANDS:
                return {
                    "success": False, 
                    "error": f"命令 '{cmd}' 应该通过特殊命令处理，不应调用此接口"
                }
            

            
            # 获取当前shell信息
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的shell会话"}
            
            # 生成远端命令（包含语法检查）
            try:
                remote_command_info = self._generate_command(cmd, cleaned_args, current_shell)
            except Exception as e:
                if "语法错误" in str(e):
                    return {
                        "success": False,
                        "error": f"命令语法错误: {str(e)}",
                        "cmd": cmd,
                        "args": args
                    }
                else:
                    raise e
            
            # 正常执行流程：显示远端命令并通过tkinter获取用户执行结果
            debug_log(f"🖥️ DEBUG: [{get_relative_timestamp()}] [EXEC] 开始执行远端命令 - window_id: {window_id}, cmd: {cmd}")
            debug_log(f"🔧 DEBUG: [{get_relative_timestamp()}] [EXEC_CALL] 调用_execute_with_result_capture - window_id: {window_id}, remote_command_info: {len(remote_command_info) if isinstance(remote_command_info, (list, tuple)) else 'not_list'}")
            result = self._execute_with_result_capture(remote_command_info, cmd, cleaned_args, window_id, get_relative_timestamp, debug_log)
            debug_log(f"📋 DEBUG: [{get_relative_timestamp()}] [RESULT] 远端命令执行完成 - window_id: {window_id}, success: {result.get('success', False)}")
            
            # WindowManager自动管理窗口生命周期，无需手动释放
            
            # 基于原始用户命令判断是否需要文件验证
            # 这里分析的是用户输入的原始命令，而不是生成的远程命令
            should_verify_file_creation = self._should_verify_file_creation(original_cmd, original_args)
            
            
            if result.get("success", False) and should_verify_file_creation:
                redirect_file = self._extract_redirect_target(args)
                if redirect_file and redirect_file.strip():
                    verification_result = self.main_instance.verify_creation_with_ls(
                        redirect_file, current_shell, creation_type="file", max_attempts=30
                    )
                    if not verification_result.get("success", False):
                        # 验证失败，但不影响原始命令的成功状态（因为远程命令已经成功了）
                        result["verification_warning"] = f"文件创建验证失败: {verification_result.get('error', 'Unknown error')}"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"执行远端命令时出错: {str(e)}"
            }
        finally:
            # WindowManager自动管理窗口生命周期
            debug_log(f"🏗️ DEBUG: [{get_relative_timestamp()}] [COMMAND_END] 命令执行流程结束，WindowManager自动管理 - window_id: {window_id}, cmd: {cmd}")
    
    def _is_redirect_command(self, cmd, args):
        """检测命令是否包含文件输出重定向操作"""
        import re
        
        # 检查参数中是否包含文件输出重定向符号
        # 排除stderr重定向（2>/dev/null等）、/dev/null重定向、以及命令替换中的重定向
        if isinstance(args, list):
            for arg in args:
                arg_str = str(arg)
                # 更严格的重定向检测：
                # 1. 排除stderr重定向 (2>)
                # 2. 排除/dev/null重定向
                # 3. 排除命令替换中的重定向 $(...)
                # 4. 排除echo命令中的重定向
                if re.search(r'(?<!2)>\s*(?!/dev/null)(?!\s*\$\()(?!.*echo\s+["\'].*["\'])\S+', arg_str):
                    # 进一步检查：如果包含echo ""或echo "{}"，也排除
                    if 'echo ""' in arg_str or 'echo "{}"' in arg_str:
                        continue
                    return True
        elif isinstance(args, str):
            # 同样的逻辑应用于字符串参数
            if re.search(r'(?<!2)>\s*(?!/dev/null)(?!\s*\$\()(?!.*echo\s+["\'].*["\'])\S+', args):
                if 'echo ""' in args or 'echo "{}"' in args:
                    return False
                return True
        return False
    
    def _should_verify_file_creation(self, cmd, args):
        """
        基于原始用户命令智能判断是否需要文件创建验证
        
        这个方法分析用户输入的原始命令，而不是生成的远程命令
        只有真正会创建用户文件的命令才需要验证
        """
        # 将参数转换为字符串进行分析
        if isinstance(args, list):
            command_str = f"{cmd} {' '.join(str(arg) for arg in args)}"
        else:
            command_str = f"{cmd} {args}" if args else cmd
        
        # 1. 明确的文件创建命令
        file_creation_patterns = [
            r'\btouch\s+\S+',           # touch filename
            r'\bmkdir\s+\S+',           # mkdir dirname  
            r'\bcp\s+\S+\s+\S+',        # cp source dest
            r'\bmv\s+\S+\s+\S+',        # mv source dest
            r'\becho\s+.*>\s*\S+',      # echo content > file
            r'\bcat\s+.*>\s*\S+',       # cat content > file
            r'>\s*[^/\s][^\s]*',        # general redirect to non-absolute path
        ]
        
        import re
        for pattern in file_creation_patterns:
            if re.search(pattern, command_str):
                return True
        
        # 2. 排除不会创建用户文件的命令
        non_file_creation_commands = [
            'ls', 'pwd', 'cd', 'find', 'grep', 'cat', 'head', 'tail',
            'ps', 'top', 'df', 'du', 'whoami', 'date', 'uptime',
            'python', 'python3', 'pip', 'pyenv', 'git status', 'git log',
            'which', 'whereis', 'history', 'env', 'printenv'
        ]
        
        # 检查命令是否在排除列表中
        for excluded_cmd in non_file_creation_commands:
            if command_str.strip().startswith(excluded_cmd):
                return False
        
        # 3. 特殊情况：bash -c 命令需要分析内部命令
        if cmd == 'bash' and isinstance(args, list) and len(args) >= 2 and args[0] == '-c':
            inner_command = args[1]
            # 递归分析bash -c内部的命令
            return self._should_verify_file_creation('bash', inner_command)
        
        # 4. 默认情况：如果不确定，不进行验证（避免误报）
        return False
    
    def _is_pyenv_related_command(self, cmd, args):
        """检测是否是pyenv相关命令"""
        if isinstance(args, list):
            for arg in args:
                arg_str = str(arg)
                # 检查是否包含pyenv相关的路径或操作
                if any(keyword in arg_str for keyword in [
                    'REMOTE_ENV/python',
                    'python_states.json',
                    'INSTALLED_VERSIONS',
                    'STATE_CONTENT',
                    'ls -1 "/content/drive/MyDrive/REMOTE_ENV/python"'
                ]):
                    return True
        elif isinstance(args, str):
            # 同样的逻辑应用于字符串参数
            if any(keyword in args for keyword in [
                'REMOTE_ENV/python',
                'python_states.json', 
                'INSTALLED_VERSIONS',
                'STATE_CONTENT',
                'ls -1 "/content/drive/MyDrive/REMOTE_ENV/python"'
            ]):
                return True
        return False
    
    def _is_internal_redirect_command(self, cmd, args):
        """检测是否是内部方法生成的重定向命令"""
        # 检测由_create_text_file等内部方法生成的base64重定向命令
        if isinstance(args, list):
            for arg in args:
                arg_str = str(arg)
                # 检测base64编码的重定向模式，这通常是内部方法生成的
                if ('base64 -d' in arg_str and '>' in arg_str) or ('| base64 -d >' in arg_str):
                    return True
        elif isinstance(args, str):
            if ('base64 -d' in args and '>' in args) or ('| base64 -d >' in args):
                return True
        return False
    
    def _extract_redirect_target(self, args):
        """从参数中提取重定向目标文件"""
        try:
            if isinstance(args, list):
                # 在列表中查找包含重定向的参数
                for arg in args:
                    if '>' in str(arg):
                        # 解析重定向目标
                        parts = str(arg).split('>')
                        if len(parts) > 1:
                            target = parts[-1].strip().strip('"').strip("'")
                            return target
            elif isinstance(args, str):
                if '>' in args:
                    parts = args.split('>')
                    if len(parts) > 1:
                        target = parts[-1].strip().strip('"').strip("'")
                        return target
            return None
        except (ValueError, IndexError):
            return None

    def _check_bash_syntax(self, script_content):
        """
        检查bash脚本语法
        
        Args:
            script_content (str): 要检查的bash脚本内容
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            import subprocess
            import tempfile
            import os
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_file_path = temp_file.name
            
            try:
                # 使用bash -n检查语法
                result = subprocess.run(
                    ['bash', '-n', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    return True, None
                else:
                    return False, result.stderr.strip()
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            return False, f"Syntax check failed: {str(e)}"

    def _generate_unified_json_command(self, user_command, result_filename=None, current_shell=None, skip_quote_escaping=False):
        """
        统一的JSON结果生成接口 - 为任何用户命令生成包含JSON结果的远程脚本
        
        Args:
            user_command (str): 用户要执行的完整命令
            result_filename (str, optional): 指定的结果文件名，如果不提供则自动生成
            current_shell (dict, optional): 当前shell信息，用于路径解析
            skip_quote_escaping (bool, optional): 跳过引号转义处理，用于已经处理过的命令
            
        Returns:
            tuple: (远端命令字符串, 结果文件名)
        """
        try:
            import time
            import hashlib
            import json
            
            # 生成统一JSON命令
            import shlex
            from datetime import datetime
            
            # 检测和处理感叹号问题（只对简单用户命令进行检测）
            # 如果用户命令很短且包含感叹号，可能是shell历史扩展问题
            if '!' in user_command and len(user_command) < 200 and not user_command.strip().startswith('#'):
                print(f"Warning: Command contains exclamation marks which may cause shell history expansion issues.")
                print(f"Original command: {user_command}")
                # 自动移除感叹号
                cleaned_command = user_command.replace('!', '')
                print(f"Cleaned command: {cleaned_command}")
                print(f"Suggestion: Avoid using '!' in commands to prevent shell history expansion errors.")
                user_command = cleaned_command
            
            # 获取当前路径
            if current_shell:
                current_path = current_shell.get("current_path", "~")
                is_background = current_shell.get("_background_mode", False)
                bg_pid = current_shell.get("_background_pid", "")
                bg_original_cmd = current_shell.get("_background_original_cmd", "")
            else:
                current_path = "~"
                is_background = False
                bg_pid = ""
                bg_original_cmd = ""
            
            # 解析远端绝对路径
            if current_path == "~":
                remote_path = self.main_instance.REMOTE_ROOT
            elif current_path.startswith("~/"):
                remote_path = f"{self.main_instance.REMOTE_ROOT}/{current_path[2:]}"
            else:
                remote_path = current_path
            
            # 生成结果文件名（如果未提供）
            if not result_filename:
                if is_background:
                    # Background模式使用常量定义的结果文件名格式
                    result_filename = get_bg_result_file(bg_pid)
                else:
                    # 普通模式使用统一的结果文件名格式
                    timestamp = str(int(time.time()))
                    cmd_hash = hashlib.md5(f"{user_command}_{timestamp}".encode()).hexdigest()[:8]
                    result_filename = f"cmd_{timestamp}_{cmd_hash}.json"
            
            result_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
            
            # 预计算所有需要的值，避免f-string中的复杂表达式
            timestamp = str(int(time.time()))
            cmd_hash = hashlib.md5(user_command.encode()).hexdigest()[:8]
            
            # 根据是否为background模式生成不同的远程命令脚本
            # 检查是否为背景任务
            if is_background:
                # Background模式：生成后台任务脚本
                import shlex
                quoted_user_cmd = shlex.quote(bg_original_cmd)
                start_time = datetime.now().isoformat()
                
                # 使用常量定义background文件名
                BG_STATUS_FILE = get_bg_status_file(bg_pid)
                BG_SCRIPT_FILE = get_bg_script_file(bg_pid)
                BG_LOG_FILE = get_bg_log_file(bg_pid)
                BG_RESULT_FILE = get_bg_result_file(bg_pid)
                
                # 创建统一的JSON状态生成函数
                def generate_status_json(pid, command, status, start_time, end_time=None, exit_code=None, result_file=None, real_pid=None):
                    """统一的状态JSON生成函数"""
                    status_obj = {
                        "pid": pid,
                        "command": command,
                        "status": status,
                        "start_time": start_time
                    }
                    if end_time:
                        status_obj["end_time"] = end_time
                    if exit_code is not None:
                        status_obj["exit_code"] = exit_code
                    if result_file:
                        status_obj["result_file"] = result_file
                    if real_pid:
                        status_obj["real_pid"] = real_pid
                    return json.dumps(status_obj, ensure_ascii=False)
                
                
                # 为JSON生成正确转义的命令字符串
                escaped_bg_cmd = json.dumps(bg_original_cmd)
                
                # 测试shlex.quote的结果
                quoted_bg_cmd = shlex.quote(bg_original_cmd)
                
                # 测试统一JSON生成函数
                test_json = generate_status_json(bg_pid, bg_original_cmd, "starting", start_time)
                
                # 获取当前挂载的特定指纹文件名
                mount_hash = getattr(self.main_instance, 'MOUNT_HASH', None)
                if mount_hash:
                    fingerprint_file = f"{self.main_instance.REMOTE_ROOT}/tmp/.gds_mount_fingerprint_{mount_hash}"
                else:
                    # 回退到通配符模式
                    fingerprint_file = f"{self.main_instance.REMOTE_ROOT}/tmp/.gds_mount_fingerprint_*"
                
                # 生成各种状态的JSON - 使用python3 -c方式，传递原始命令让python处理转义
                # 为了避免shell转义问题，将命令作为环境变量传递
                starting_json_template = f'$(BG_ORIGINAL_CMD={shlex.quote(bg_original_cmd)} python3 -c "import json, os; print(json.dumps({{\\"pid\\": \\"{bg_pid}\\", \\"command\\": os.environ[\\"BG_ORIGINAL_CMD\\"], \\"status\\": \\"starting\\", \\"start_time\\": \\"{start_time}\\"}}, ensure_ascii=False))")'
                completed_json_template = f'$(BG_ORIGINAL_CMD={shlex.quote(bg_original_cmd)} python3 -c "import json, os; print(json.dumps({{\\"pid\\": \\"{bg_pid}\\", \\"command\\": os.environ[\\"BG_ORIGINAL_CMD\\"], \\"status\\": \\"completed\\", \\"start_time\\": \\"{start_time}\\", \\"end_time\\": \\"$(date -Iseconds 2>/dev/null || date)\\", \\"exit_code\\": $EXIT_CODE, \\"result_file\\": \\"{BG_RESULT_FILE}\\"}}, ensure_ascii=False))")'
                running_json_template = f'$(BG_ORIGINAL_CMD={shlex.quote(bg_original_cmd)} python3 -c "import json, os; print(json.dumps({{\\"pid\\": \\"{bg_pid}\\", \\"command\\": os.environ[\\"BG_ORIGINAL_CMD\\"], \\"status\\": \\"running\\", \\"start_time\\": \\"{start_time}\\", \\"result_file\\": \\"{BG_RESULT_FILE}\\", \\"real_pid\\": $REAL_PID}}, ensure_ascii=False))")'
                
                # 测试模板实际执行结果（模拟）
                import subprocess
                try:
                    test_env = os.environ.copy()
                    test_env['BG_ORIGINAL_CMD'] = bg_original_cmd
                    test_result = subprocess.run([
                        'python3', '-c', 
                        f'import json, os; print(json.dumps({{"pid": "{bg_pid}", "command": os.environ["BG_ORIGINAL_CMD"], "status": "starting", "start_time": "{start_time}"}}, ensure_ascii=False))'
                    ], env=test_env, capture_output=True, text=True)
                    if test_result.stderr:
                        print (test_result.stderr)
                except Exception as e:
                    pass
                
                # 创建后台管理脚本内容
                background_manager_content = f'''#!/bin/bash
# Background Task Manager for {bg_pid}

# 确保工作目录存在并切换到正确的基础目录
mkdir -p "{remote_path}"
cd "{remote_path}"

# 确保tmp目录存在
mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"

# 创建状态文件，表示任务已开始
cat > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_STATUS_FILE}" << STATUS_EOF
{starting_json_template}
STATUS_EOF

# 创建后台执行脚本
cat > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}" << 'SCRIPT_EOF'
#!/bin/bash
set -e

# 执行用户命令
bash -c {bg_original_cmd}
EXIT_CODE=$?

# 生成后台任务的JSON结果文件
python3 << 'PYTHON_EOF'
import json
import os
from datetime import datetime

try:
    exit_code = int(os.environ.get('EXIT_CODE', '0'))
    
    result = {{
        "success": exit_code == 0,
        "data": {{
            "exit_code": exit_code,
            "stdout": "Background task {bg_pid} completed",
            "stderr": "",
            "working_dir": os.getcwd(),
            "timestamp": datetime.now().isoformat()
        }}
    }}
    
    with open("{self.main_instance.REMOTE_ROOT}/tmp/{BG_RESULT_FILE}", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
except Exception as e:
    print(f"ERROR: Failed to generate JSON result: {{e}}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF

# 更新状态文件
cat > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_STATUS_FILE}" << STATUS_FINAL_EOF
{completed_json_template}
STATUS_FINAL_EOF
SCRIPT_EOF

# 给脚本执行权限并启动后台任务
chmod +x "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}"
nohup "{self.main_instance.REMOTE_ROOT}/tmp/{BG_SCRIPT_FILE}" < /dev/null > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_LOG_FILE}" 2>&1 &
REAL_PID=$!

# 更新状态文件包含真实PID
cat > "{self.main_instance.REMOTE_ROOT}/tmp/{BG_STATUS_FILE}" << STATUS_RUNNING_EOF
{running_json_template}
STATUS_RUNNING_EOF

# 验证background任务文件是否被正确创建
sleep 1  # 等待文件系统同步
if [ -f "{self.main_instance.REMOTE_ROOT}/tmp/{BG_STATUS_FILE}" ]; then
    echo "Background task started with ID: {bg_pid}"
    echo "Command: {bg_original_cmd}"
    echo ""
    echo "Run the following commands to track the background task status:"
    echo "  GDS --bg --status {bg_pid}    # Check task status"
    echo "  GDS --bg --result {bg_pid}    # View task result"
    echo "  GDS --bg --log {bg_pid}       # View task log"
    echo "  GDS --bg --cleanup {bg_pid}   # Clean up task files"
else
    echo "Error: Background task creation failed - status file not found"
    exit 1
fi
'''

                # 主程序：创建后台管理进程并立即返回，同时生成主程序的JSON结果
                remote_command = f'''# Background任务启动脚本 - 主程序立即返回
# 确保基础目录存在
mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"

# 创建后台任务管理脚本
cat > "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.sh" << 'MANAGER_EOF'
{background_manager_content}
MANAGER_EOF

# 给管理脚本执行权限
chmod +x "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.sh"

# 启动后台管理进程
nohup "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.sh" > "{self.main_instance.REMOTE_ROOT}/tmp/bg_manager_{bg_pid}.log" 2>&1 &

# 主程序立即返回消息
echo "Background task manager started for ID: {bg_pid}"
echo "Task creation is proceeding in background..."

# 统一的执行完成提示
clear && echo "✅执行完成"

# 立即生成主程序的JSON结果文件（用于本地wait and read）
cd "{self.main_instance.REMOTE_ROOT}"
export TIMESTAMP="{timestamp}"
export HASH="{cmd_hash}"
python3 << 'MAIN_JSON_EOF'
import json
import os
from datetime import datetime

# 构建主程序执行结果
result = {{
    "cmd": "background_task_created",
    "working_dir": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "exit_code": 0,
    "stdout": "Background task manager started for ID: {bg_pid}\\nTask creation is proceeding in background...\\n✅执行完成",
    "stderr": ""
}}

# 写入主程序结果文件（注意：这是主程序的结果文件，不是背景任务的结果文件）
result_file = "{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
result_dir = os.path.dirname(result_file)
if result_dir:
    os.makedirs(result_dir, exist_ok=True)

with open(result_file, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
MAIN_JSON_EOF'''
            else:
                # 普通模式：使用原有的统一JSON生成脚本
                remote_command = f'''
# 统一JSON结果生成脚本
# 首先检查挂载是否成功
python3 -c "
import os
import sys
try:
    mount_hash = '{getattr(self.main_instance, "MOUNT_HASH", "")}'
    if mount_hash:
        fingerprint_file = \\\"{self.main_instance.REMOTE_ROOT}/tmp/.gds_mount_fingerprint_\\\" + mount_hash
        if os.path.exists(fingerprint_file):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
"
if [ $? -ne 0 ]; then
    clear && echo "当前session的GDS无法访问Google Drive文件结构。请使用GOOGLE_DRIVE --remount指令重新挂载，然后执行GDS的其他命令"
else
    # 确保工作目录存在并切换到正确的基础目录
    mkdir -p "{remote_path}"
    cd "{remote_path}" && {{
        # 确保tmp目录存在
        mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"
        
        # 执行用户命令并捕获输出
        TIMESTAMP="{timestamp}"
        HASH="{cmd_hash}"
        OUTPUT_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_stdout_${{TIMESTAMP}}_${{HASH}}"
        ERROR_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_stderr_${{TIMESTAMP}}_${{HASH}}"
        EXITCODE_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_${{TIMESTAMP}}_${{HASH}}"
        
        # 直接执行用户命令，捕获输出和错误
        set +e  # 允许命令失败
        bash -c {shlex.quote(user_command)} > "$OUTPUT_FILE" 2> "$ERROR_FILE"
        EXIT_CODE=$?
        echo "$EXIT_CODE" > "$EXITCODE_FILE"
        set -e
        
        # 显示stderr内容（如果有）
        if [ -s "$ERROR_FILE" ]; then
            cat "$ERROR_FILE" >&2
        fi
        
        # 统一的执行完成提示
        clear && echo "✅执行完成"
        
        # 生成JSON结果文件
        export EXIT_CODE=$EXIT_CODE
        export TIMESTAMP=$TIMESTAMP
        export HASH=$HASH
        python3 << 'JSON_SCRIPT_EOF'
import json
import os
import sys
from datetime import datetime

# 从环境变量获取文件路径参数
timestamp = os.environ.get('TIMESTAMP', '{timestamp}')
hash_val = os.environ.get('HASH', '{cmd_hash}')

# 构建文件路径
stdout_file = f"{self.main_instance.REMOTE_ROOT}/tmp/cmd_stdout_{{timestamp}}_{{hash_val}}"
stderr_file = f"{self.main_instance.REMOTE_ROOT}/tmp/cmd_stderr_{{timestamp}}_{{hash_val}}"
exitcode_file = f"{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_{{timestamp}}_{{hash_val}}"

# 读取输出文件
stdout_content = ""
stderr_content = ""

if os.path.exists(stdout_file):
    try:
        with open(stdout_file, "r", encoding="utf-8", errors="ignore") as f:
            stdout_content = f.read()
    except Exception as e:
        stdout_content = f"ERROR: 无法读取stdout文件: {{e}}"
else:
    stdout_content = ""

if os.path.exists(stderr_file):
    try:
        with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
            stderr_content = f.read()
    except Exception as e:
        stderr_content = f"ERROR: 无法读取stderr文件: {{e}}"
else:
    stderr_content = ""

# 读取退出码
exit_code = int(os.environ.get('EXIT_CODE', '0'))

# 构建统一的结果JSON格式
result = {{
    "cmd": "remote_command_executed",
    "working_dir": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "exit_code": exit_code,
    "stdout": stdout_content,
    "stderr": stderr_content
}}

# 写入结果文件
result_file = "{result_path}"
result_dir = os.path.dirname(result_file)
if result_dir:
    os.makedirs(result_dir, exist_ok=True)

with open(result_file, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

JSON_SCRIPT_EOF
        
        # 清理临时文件
        rm -f "$OUTPUT_FILE" "$ERROR_FILE" "$EXITCODE_FILE"
    }}
fi'''
            
            
            # 检查生成的完整脚本语法（包括wrapper部分）
            is_valid, error_msg = self._check_bash_syntax(remote_command)
            
            if not is_valid:
                print(f"Error: Bash syntax error detected in generated remote script:")
                print(f"Error: {error_msg}")
                print(f"Script content preview:")
                print(remote_command[:500] + "..." if len(remote_command) > 500 else remote_command)
                print(f"Full script length: {len(remote_command)} characters")
                raise Exception(f"Generated remote script has syntax errors: {error_msg}")
            
            # 最终生成的remote_command
            
            return remote_command, result_filename
            
        except Exception as e:
            raise Exception(f"Generate unified JSON command failed: {str(e)}")

    def _generate_command(self, cmd, args, current_shell):
        """
        生成远端执行命令 - 现在使用统一的JSON生成接口
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            current_shell (dict): 当前shell信息
            
        Returns:
            tuple: (远端命令字符串, 结果文件名)
        """
        try:
            # 构建完整的用户命令
            if args:
                # 处理特殊命令格式
                if cmd == "bash" and len(args) >= 2 and args[0] == "-c":
                    user_command = f'bash -c "{args[1]}"'
                elif cmd == "sh" and len(args) >= 2 and args[0] == "-c":
                    user_command = f'sh -c "{args[1]}"'
                elif cmd == "python" and len(args) >= 2 and args[0] == "-c":
                    # 对于python -c命令，需要正确转义
                    python_code = args[1]
                    escaped_python_code = (python_code.replace('\\', '\\\\')
                                                     .replace('"', '\\"')
                                                     .replace('$', '\\$'))
                    user_command = f'python -c "{escaped_python_code}"'
                else:
                    # 处理重定向和其他参数
                    import shlex
                    if '>' in args:
                        # 处理重定向：将参数分为命令部分和重定向部分
                        redirect_index = args.index('>')
                        cmd_args = args[:redirect_index]
                        target_file = args[redirect_index + 1] if redirect_index + 1 < len(args) else None
                        
                        if target_file:
                            if cmd_args:
                                user_command = f"{cmd} {' '.join(cmd_args)} > {target_file}"
                            else:
                                user_command = f"{cmd} > {target_file}"
                        else:
                            user_command = f"{cmd} {' '.join(args)}"
                    else:
                        # 处理~路径展开
                        processed_args = []
                        for arg in args:
                            if arg == "~":
                                processed_args.append(f'"{self.main_instance.REMOTE_ROOT}"')
                            elif arg.startswith("~/"):
                                processed_args.append(f'"{self.main_instance.REMOTE_ROOT}/{arg[2:]}"')
                            else:
                                processed_args.append(arg)
                        user_command = f"{cmd} {' '.join(processed_args)}"
            else:
                user_command = cmd
            
            # 使用统一的JSON生成接口
            return self._generate_unified_json_command(user_command, None, current_shell, False)
            
        except Exception as e:
            raise Exception(f"Generate remote command failed: {str(e)}")

    def execute_unified_command(self, user_command, result_filename=None, current_shell=None, skip_quote_escaping=False):
        """
        统一的命令执行接口 - 支持任何用户命令，自动生成JSON结果
        
        Args:
            user_command (str): 用户要执行的完整命令
            result_filename (str, optional): 指定的结果文件名
            current_shell (dict, optional): 当前shell信息
            skip_quote_escaping (bool, optional): 跳过引号转义处理，用于已经处理过的命令
            
        Returns:
            dict: 执行结果
        """
        try:
            # 使用统一的JSON生成接口（包含语法检查）
            try:
                remote_command, actual_result_filename = self._generate_unified_json_command(
                    user_command, result_filename, current_shell, skip_quote_escaping
                )
            except Exception as e:
                # 如果是语法错误，直接返回错误，不弹出窗口
                if "syntax errors" in str(e).lower():
                    print(f"Error: Bash syntax error detected:")
                    print(f"   {str(e)}")
                    print(f"   Please fix the syntax error in your command and try again.")
                    return {
                        "success": False,
                        "action": "syntax_error",
                        "data": {
                            "error": str(e),
                            "source": "syntax_check"
                        }
                    }
                else:
                    # 其他错误继续抛出
                    raise
            
            # DEBUG: 显示生成的远端指令 (暂时禁用)
            # print(f"DEBUG: Generated remote command for '{user_command}':")
            # print(f"=" * 60)
            # print(remote_command)
            # print(f"=" * 60)
            
            # 显示远程窗口
            title = f"GDS Unified Command: {user_command[:50]}..."
            window_result = self.show_command_window_subprocess(
                title=title,
                command_text=remote_command
            )
            
            # 处理窗口结果
            if window_result["action"] == "success":
                # 用户点击了执行完成，等待并读取结果
                result_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{actual_result_filename}"
                result = self._wait_and_read_result_file(actual_result_filename)
                
                if result.get("success", False):
                    data = result.get("data", {})
                    return {
                        "success": True,
                        "action": "success",
                        "data": data,
                        "source": "unified_command"
                    }
                else:
                    return {
                        "success": False,
                        "action": "execution_failed",
                        "data": {
                            "error": result.get("error", "Command execution failed"),
                            "source": "unified_command"
                        }
                    }
                    
            elif window_result["action"] == "direct_feedback":
                # 用户选择直接反馈，使用direct_feedback_interface
                print()  # 换行
                feedback_result = self.direct_feedback_interface(remote_command, actual_result_filename)
                return feedback_result
                
            elif window_result["action"] == "copy":
                return {
                    "success": True,
                    "action": "copy",
                    "data": {
                        "message": "Command copied to clipboard",
                        "source": "unified_command"
                    }
                }
                
            else:  # timeout, cancel, failure, error
                return {
                    "success": False,
                    "action": window_result["action"],
                    "data": {
                        "error": window_result.get("error", "Operation cancelled or failed"),
                        "source": "unified_command"
                    }
                }
            
        except Exception as e:
            return {
                "success": False,
                "action": "error",
                "data": {
                    "error": f"Unified command execution failed: {str(e)}",
                    "source": "unified_command"
                }
            }

    def _execute_with_result_capture(self, remote_command_info, cmd, args, window_id, get_timestamp_func, debug_log_func):
        """
        执行远端命令并捕获结果
        
        Args:
            remote_command_info (tuple): (远端命令, 结果文件名)
            cmd (str): 原始命令名
            args (list): 原始命令参数
            window_id (str): 窗口唯一标识符
            get_timestamp_func (function): 获取相对时间戳的函数
            debug_log_func (function): 调试日志函数
            
        Returns:
            dict: 执行结果
        """
        debug_log_func(f"🎯 DEBUG: [{get_timestamp_func()}] [CAPTURE_START] _execute_with_result_capture 开始 - window_id: {window_id}, cmd: {cmd}")
        
        # 开始进度缓冲
        from .progress_manager import start_progress_buffering, stop_progress_buffering
        start_progress_buffering()
        
        # WindowManager自动处理窗口生命周期
        debug_log_func(f"🏗️ DEBUG: [{get_timestamp_func()}] [WINDOW_MANAGER] WindowManager自动处理窗口 - window_id: {window_id}")
        try:
            remote_command, result_filename = remote_command_info
            
            # 在显示命令窗口前，先输出命令到临时文件供检查
            try:
                import os
                import tempfile
                # 创建临时文件在GOOGLE_DRIVE_DATA目录中
                google_drive_data = os.path.expanduser("~/.local/bin/GOOGLE_DRIVE_DATA")
                os.makedirs(google_drive_data, exist_ok=True)
                
                # 使用临时文件，执行完成后自动删除
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.sh', 
                    prefix='gds_command_', 
                    dir=google_drive_data, 
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    f.write(remote_command)
                    command_file_path = f.name
                
                debug_log_func(f"📝 DEBUG: [{get_timestamp_func()}] [COMMAND_FILE] 已输出命令到临时文件 {command_file_path}")
                
                # 在函数结束时删除临时文件
                def cleanup_command_file():
                    try:
                        if os.path.exists(command_file_path):
                            os.remove(command_file_path)
                            debug_log_func(f"🗑️ DEBUG: [{get_timestamp_func()}] [COMMAND_FILE_CLEANUP] 已删除临时文件 {command_file_path}")
                    except Exception as cleanup_error:
                        debug_log_func(f"⚠️ DEBUG: [{get_timestamp_func()}] [COMMAND_FILE_CLEANUP_ERROR] 删除临时文件失败: {cleanup_error}")
                
            except Exception as e:
                debug_log_func(f"⚠️ DEBUG: [{get_timestamp_func()}] [COMMAND_FILE_ERROR] 创建临时文件失败: {e}")
                command_file_path = None
                cleanup_command_file = None
            
            # 不进行本地测试，直接显示窗口让用户在远端检测
            
            # 通过tkinter显示命令并获取用户反馈
            debug_log_func(f"🖥️ DEBUG: [{get_timestamp_func()}] [WINDOW_PREP] 准备显示窗口 - window_id: {window_id}, cmd: {cmd}")
            
            # DEBUG: 显示即将调用的窗口信息
            # print(f"\nDEBUG: 即将调用show_command_window")
            # print(f"DEBUG: cmd = {cmd}, args = {args}")
            # print(f"DEBUG: remote_command 长度 = {len(remote_command)} 字符")
            # print(f"DEBUG: window_id = {window_id}")
            
            # 记录窗口打开时间到专用的测试文件
            try:
                debug_log_func(f"📝 DEBUG: [{get_timestamp_func()}] [LOG_TIME] 窗口时间记录成功 - window_id: {window_id}")
            except Exception as e:
                debug_log_func(f"Warning: DEBUG: [{get_timestamp_func()}] [LOG_TIME_ERROR] 窗口时间记录失败: {e} - window_id: {window_id}")
            
            debug_info = debug_capture.get_debug_info()
            debug_capture.start_capture()  # 启动debug捕获，避免窗口期间的debug输出
            debug_log_func(f"🪟 DEBUG: [{get_timestamp_func()}] [WINDOW_CALL] 即将调用_show_command_window - window_id: {window_id}")
            
            # 获取当前shell状态
            current_shell = self.main_instance.get_current_shell()
            
            # 生成最终的远端命令（使用原有的_generate_command方法）
            remote_command_info = self._generate_command(cmd, args, current_shell)
            final_remote_command, result_filename = remote_command_info
            
            # 显示命令窗口
            window_result = self._show_command_window(cmd, args, final_remote_command, result_filename)
            debug_print(f"_show_command_window返回结果: {window_result}")
            
            # 检查用户窗口操作结果，并在适当时机释放槽位
            user_completed_window = False
            
            if window_result.get("action") == "direct_feedback":
                # 用户选择直接反馈，使用direct_feedback_interface（照搬--bg指令的逻辑）
                debug_print(f"_execute_with_result_capture: 检测到direct_feedback，使用direct_feedback_interface")
                debug_print(f"window_result: {window_result}")
                user_completed_window = True  # 用户完成了窗口操作
                debug_log_func(f"👤 DEBUG: [{get_timestamp_func()}] [USER_COMPLETED] 设置user_completed_window=True (direct_feedback) - window_id: {window_id}")
                debug_capture.stop_capture()  # 在返回前停止debug捕获
                
                # WindowManager自动处理窗口生命周期
                debug_log_func(f"🏗️ DEBUG: [{get_timestamp_func()}] [USER_FEEDBACK] 用户完成直接反馈 - window_id: {window_id}")
                
                # 照搬execute_unified_command的逻辑：使用direct_feedback_interface
                print()  # 换行
                feedback_result = self.direct_feedback_interface(remote_command, result_filename)
                return feedback_result
            elif window_result.get("action") == "success":
                # 用户确认执行完成
                user_completed_window = True
                debug_log_func(f"👤 DEBUG: [{get_timestamp_func()}] [USER_COMPLETED] 设置user_completed_window=True (success) - window_id: {window_id}")
                debug_print(f"_execute_with_result_capture: 用户确认执行完成")
            elif window_result.get("action") != "success":
                debug_print(f"_execute_with_result_capture: window_result.action != 'success'")
                debug_print(f"实际的window_result.action: {window_result.get('action')}")
                debug_print(f"完整window_result: {window_result}")
                user_completed_window = True  # 用户取消或超时也算完成窗口操作
                debug_log_func(f"👤 DEBUG: [{get_timestamp_func()}] [USER_COMPLETED] 设置user_completed_window=True (non-success: {window_result.get('action')}) - window_id: {window_id}")
                debug_capture.stop_capture()  # 在返回前停止debug捕获
                
                # WindowManager自动处理窗口生命周期
                debug_log_func(f"🏗️ DEBUG: [{get_timestamp_func()}] [USER_CANCEL] 用户取消/超时 - window_id: {window_id}")
                
                return {
                    "success": False,
                    "error": f"User operation timeout or cancelled",
                    "user_feedback": window_result
                }
            
            debug_capture.stop_capture()  # 成功路径的debug捕获停止
            
            # 等待远端文件出现
            result_data = self._wait_and_read_result_file(result_filename)
            
            if not result_data.get("success"):
                return {
                    "success": False,
                    "error": "",
                    "read_error": result_data.get("error")
                }
            
            # 返回完整结果
            return {
                "success": True,
                "cmd": cmd,
                "args": args,
                "exit_code": result_data["data"].get("exit_code", -1),
                "stdout": result_data["data"].get("stdout", ""),
                "stderr": result_data["data"].get("stderr", ""),
                "working_dir": result_data["data"].get("working_dir", ""),
                "timestamp": result_data["data"].get("timestamp", ""),
                "path": f"tmp/{result_filename}",  # 远端结果文件路径
            }
            
        except Exception as e:
            debug_log_func(f"Error: DEBUG: [{get_timestamp_func()}] [CAPTURE_ERROR] _execute_with_result_capture 异常 - window_id: {window_id}, error: {str(e)}")
            return {
                "success": False,
                "error": f"执行结果捕获失败: {str(e)}"
            }
        finally:
            # 停止进度缓冲
            stop_progress_buffering()
            
            # 清理临时命令文件
            if 'cleanup_command_file' in locals() and cleanup_command_file is not None:
                cleanup_command_file()
            
            # 单窗口锁机制下不需要心跳线程
            debug_log_func(f"🏁 DEBUG: [{get_timestamp_func()}] [CLEANUP] 清理完成 - window_id: {window_id}")
            
            # print(f"DEBUG: [{get_timestamp_func()}] [CAPTURE_EXIT] _execute_with_result_capture 结束 - window_id: {window_id}")
        # 注意：窗口槽位的释放由execute_generic_command的finally块统一处理

    def _show_command_window(self, cmd, args, remote_command, result_filename=None, debug_info=None):
        """
        显示远端命令的窗口（使用subprocess方法，完全抑制IMK信息）
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            remote_command (str): 远端命令内容
            result_filename (str, optional): 结果文件名，用于direct_feedback_interface
            debug_info (str): debug信息，仅在直接反馈时输出
        
        Returns:
            dict: 用户操作结果
        """
        try:
            # 保存远端命令到文件以便调试
            try:
                import os
                import time
                from pathlib import Path
                data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
                cmd_file_path = os.path.join(data_dir, 'remote_window_cmd.sh')
                
                # 创建命令文件内容
                cmd_content = f"#!/bin/bash\n# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n# Command: {cmd} {' '.join(args)}\n\n{remote_command}\n"
                
                with open(cmd_file_path, 'w', encoding='utf-8') as f:
                    f.write(cmd_content)
                
                # 设置执行权限
                os.chmod(cmd_file_path, 0o755)
            except Exception as e:
                print(f"Warning: Failed to save remote command: {e}")
            
            # show_command_window_subprocess现在是类方法
            title = f"GDS Remote Command: {cmd}"
            instruction = f"Command: {cmd} {' '.join(args)}\n\nPlease execute the following command in your remote environment:"
            
            # 使用新的WindowManager显示窗口
            result = self.show_command_window_subprocess(
                title=title,
                command_text=remote_command
            )
            
            # 转换结果格式以保持兼容性
            if result["action"] == "success":
                return {
                    "success": True,
                    "action": "success",
                    "data": {
                        "cmd": cmd,
                        "args": args,
                        "exit_code": 0,
                        "stdout": "Command executed successfully",
                        "stderr": "",
                        "source": "subprocess_window"
                    }
                }
            elif result["action"] == "direct_feedback":
                # 处理直接反馈 - 调用原来的直接反馈逻辑
                print () # shift a newline since ctrl+D
                debug_print(f"检测到direct_feedback action，即将调用direct_feedback方法")
                debug_print(f"remote_command存在: {remote_command is not None}")
                debug_print(f"debug_info存在: {debug_info is not None}")
                try:
                    feedback_result = self.direct_feedback_interface(remote_command, result_filename, debug_info)
                    return {
                        "success": feedback_result.get("success", False),
                        "action": feedback_result.get("action", "direct_feedback"),
                        "data": feedback_result.get("data", {}),
                        "user_feedback": feedback_result.get("user_feedback", {}),
                        "source": feedback_result.get("source", "direct_feedback_interface")
                    }
                except Exception as e:
                    debug_print(f"direct_feedback调用异常: {e}")
                    import traceback
                    debug_print(f"异常traceback: {traceback.format_exc()}")
                    return {
                        "success": False,
                        "action": "direct_feedback_error",
                        "data": {
                            "error": f"Direct feedback failed: {str(e)}",
                            "source": "direct_feedback"
                        }
                    }
            elif result["action"] == "failure":
                return {
                    "success": False,
                    "action": "failure", 
                    "data": {
                        "cmd": cmd,
                        "args": args,
                        "exit_code": 1,
                        "stdout": "",
                        "stderr": "Command execution failed",
                        "source": "subprocess_window"
                    }
                }
            elif result["action"] == "copy":
                return {
                    "success": True,
                    "action": "copy",
                    "data": {
                        "cmd": cmd,
                        "args": args,
                        "message": "Command copied to clipboard",
                        "source": "subprocess_window"
                    }
                }
            else:  # timeout, cancel, error
                return {
                    "success": False,
                    "action": result["action"],
                    "data": {
                        "cmd": cmd,
                        "args": args,
                        "error": result.get("error", "Operation cancelled or timed out"),
                        "source": "subprocess_window"
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "action": "error",
                "data": {
                    "cmd": cmd,
                    "args": args,
                    "error": f"Failed to show command window: {str(e)}",
                    "source": "subprocess_window"
                }
            }

    def _cleanup_remote_result_file(self, result_filename):
        """
        清理远端结果文件
        
        Args:
            result_filename (str): 要清理的远端文件名（在tmp目录中）
        """
        try:
            # 使用rm命令删除远端文件（静默执行）
            remote_file_path = f"tmp/{result_filename}"
            self.cmd_rm(remote_file_path, force=True)
        except:
            # 清理失败不影响主要功能
            pass

    def direct_feedback(self, remote_command, debug_info=None):
        """
        直接反馈功能 - 粘贴远端命令和用户反馈，用=分割
        使用统一的_get_multiline_user_input方法
        """
        debug_print(f"进入direct_feedback方法")
        
        # 先输出debug信息（如果有的话）
        if debug_info:
            print(f"Debug information:")
            print(debug_info)
            print(f"=" * 20)  # 20个等号分割线
        
        # 然后粘贴生成的远端指令
        print(f"Generated remote command:")
        print(remote_command)
        print(f"=" * 20)  # 50个等号分割线
        
        print(f"Please provide command execution result (multi-line input, press Ctrl+D to finish):")
        print()
        
        # 使用统一的多行输入方法
        full_output = self._get_multiline_user_input()
        
        # 简单解析输出：如果包含错误关键词，放到stderr，否则放到stdout
        error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 
                         'traceback', 'Traceback', 'TRACEBACK', 'failed', 'Failed', 'FAILED']
        
        # 检查是否包含错误信息
        has_error = any(keyword in full_output for keyword in error_keywords)
        if has_error:
            stdout_content = ""
            stderr_content = full_output
            exit_code = 1  # 有错误时默认退出码为1
        else:
            stdout_content = full_output
            stderr_content = ""
            exit_code = 0 
        
        # 构建反馈结果
        feedback_result = {
            "success": exit_code == 0,
            "action": "direct_feedback",
            "data": {
                "working_dir": "user_provided",
                "timestamp": "user_provided", 
                "exit_code": exit_code,
                "stdout": stdout_content,
                "stderr": stderr_content,
                "source": "direct_feedback"
            }
        }
        return feedback_result
    
    def direct_feedback_interface(self, remote_command, result_filename=None, debug_info=None):
        """
        增强的直接反馈功能 - 在收集用户反馈后，尝试等待并获取实际的执行结果
        
        Args:
            remote_command (str): 远端命令内容
            result_filename (str): 结果文件名（如果有的话）
            debug_info (str): debug信息，仅在直接反馈时输出
        
        Returns:
            dict: 包含直接反馈和实际结果的综合结果
        """
        feedback_result = self.direct_feedback(remote_command, debug_info)
        
        # 添加分隔符
        print(f"=" * 20)
        
        # 如果提供了result_filename，尝试等待并读取实际的执行结果
        if result_filename:
            try:
                # 等待并读取结果文件
                actual_result = self._wait_and_read_result_file(result_filename)
                
                if actual_result.get("success", False):
                    actual_data = actual_result.get("data", {})
                    actual_stdout = actual_data.get("stdout", "").strip()
                    actual_stderr = actual_data.get("stderr", "").strip()
                    
                    # 不打印actual_stdout，因为用户的直接反馈已经包含了输出
                    # 只在有stderr时打印stderr
                    if actual_stderr:
                        import sys
                        print(actual_stderr, file=sys.stderr)
                    
                    # 返回实际的执行结果，但保留用户反馈信息
                    return {
                        "success": actual_result.get("success", False),
                        "action": "direct_feedback_interface",
                        "data": actual_data,
                        "user_feedback": feedback_result.get("data", {}),
                        "source": "direct_feedback_interface"
                    }
                else:
                    error_msg = actual_result.get("error", "Failed to get actual result")
                    print(f"Could not get actual execution result: {error_msg}")
                    
            except Exception as e:
                print(f"Error waiting for actual result: {e}")
        
        # 如果没有result_filename或获取实际结果失败，返回用户反馈结果
        return feedback_result
    
    def wait_and_read_background_result(self, bg_result_file_path):
        """
        等待并读取后台任务结果文件，使用与普通命令相同的等待逻辑
        
        Args:
            bg_result_file_path (str): 后台任务结果文件的完整路径
            
        Returns:
            dict: 读取结果，格式与_wait_and_read_result_file一致
        """
        try:
            import time
            import os
            
            # 使用进度缓冲输出等待指示器
            from .progress_manager import start_progress_buffering
            start_progress_buffering("⏳ Waiting for background task result ...")
            
            # 等待文件出现，最多60秒，支持Ctrl+C中断
            max_wait_time = 60  # 后台任务可能需要更长时间
            import signal
            import sys
            
            # 设置KeyboardInterrupt标志
            interrupted = False
            
            def signal_handler(signum, frame):
                nonlocal interrupted
                interrupted = True
            
            # 注册信号处理器
            old_handler = signal.signal(signal.SIGINT, signal_handler)
            
            try:
                for i in range(max_wait_time):
                    # 在每次循环开始时检查中断标志
                    if interrupted:
                        raise KeyboardInterrupt()
                    
                    # 检查文件是否存在
                    check_result = self._check_remote_file_exists(bg_result_file_path)
                    
                    if check_result.get("exists"):
                        # 文件存在，读取内容
                        try:
                            # 提取文件名用于_read_result_file_via_gds
                            result_filename = os.path.basename(bg_result_file_path)
                            file_result = self._read_result_file_via_gds(result_filename)
                            
                            # 直接清除进度显示
                            from .progress_manager import clear_progress
                            clear_progress()
                            
                            # 恢复原来的信号处理器
                            signal.signal(signal.SIGINT, old_handler)
                            
                            # 解析后台任务的JSON结果格式
                            if file_result.get("success", False):
                                data = file_result.get("data", {})
                                stdout = data.get("stdout", "").strip()
                                
                                if stdout:
                                    try:
                                        import json
                                        bg_result = json.loads(stdout)
                                        
                                        # 后台任务的JSON格式是 {"success": bool, "data": {...}}
                                        # 直接返回，因为格式已经正确
                                        bg_result["data"]["source"] = "background_task"
                                        return bg_result
                                    except json.JSONDecodeError:
                                        # JSON解析失败，返回原始内容
                                        return {
                                            "success": True,
                                            "data": {
                                                "exit_code": 0,
                                                "stdout": stdout,
                                                "stderr": "",
                                                "source": "background_task_raw"
                                            }
                                        }
                                else:
                                    return {
                                        "success": True,
                                        "data": {
                                            "exit_code": 0,
                                            "stdout": "",
                                            "stderr": "",
                                            "source": "background_task_empty"
                                        }
                                    }
                            else:
                                return file_result
                                
                        except Exception as e:
                            # 清除进度显示
                            from .progress_manager import clear_progress
                            clear_progress()
                            # 恢复信号处理器
                            signal.signal(signal.SIGINT, old_handler)
                            return {
                                "success": False,
                                "error": f"Error reading background result file: {str(e)}"
                            }
                    
                    # 文件不存在，等待1秒并输出进度点
                    # 使用可中断的等待，每100ms检查一次中断标志
                    for j in range(10):  # 10 * 0.1s = 1s
                        if interrupted:
                            raise KeyboardInterrupt()
                        time.sleep(0.1)
                    
                    from .progress_manager import progress_print
                    progress_print(f".")
                
            except KeyboardInterrupt:
                # 用户按下Ctrl+C，清除进度显示并退出
                from .progress_manager import clear_progress
                clear_progress()
                # 恢复原来的信号处理器
                signal.signal(signal.SIGINT, old_handler)
                return {
                    "success": False,
                    "error": "Operation cancelled by Ctrl+C during waiting for background result",
                    "cancelled": True
                }
            finally:
                # 确保信号处理器总是被恢复
                try:
                    signal.signal(signal.SIGINT, old_handler)
                except:
                    pass
            
            # 超时处理
            signal.signal(signal.SIGINT, old_handler)
            from .progress_manager import clear_progress
            clear_progress()
            
            return {
                "success": False,
                "error": f"Background task result not available after {max_wait_time} seconds. Task may still be running.",
                "timeout": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error waiting for background result: {str(e)}"
            }
    
    # ==================== 从core_utils.py迁移的方法 ====================
    
    def generate_unzip_command(self, remote_target_path, zip_filename, delete_zip=True, handle_empty_zip=True):
        """
        统一生成解压命令的工具函数，消除重复代码
        
        Args:
            remote_target_path: 远程目标路径
            zip_filename: zip文件名
            delete_zip: 是否删除zip文件
            handle_empty_zip: 是否处理空zip文件的警告
        
        Returns:
            str: 生成的解压命令
        """
        if handle_empty_zip:
            # 处理空zip文件警告的版本：过滤掉"zipfile is empty"警告，但不影响实际执行结果
            if delete_zip:
                unzip_command = f'''cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && (unzip -o "{zip_filename}" 2>&1 | grep -v "zipfile is empty" || true) && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "Verifying decompression result ..." && ls -la'''
            else:
                unzip_command = f'''cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && (unzip -o "{zip_filename}" 2>&1 | grep -v "zipfile is empty" || true) && echo "Verifying decompression result ..." && ls -la'''
        else:
            # 原始版本（保持向后兼容）
            if delete_zip:
                unzip_command = f'''cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && unzip -o "{zip_filename}" && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "Verifying decompression result ..." && ls -la'''
            else:
                unzip_command = f'''cd "{remote_target_path}" && echo "Start decompressing {zip_filename}" && unzip -o "{zip_filename}" && echo "Verifying decompression result ..." && ls -la'''
        
        return unzip_command
    
    def show_command_window_subprocess(self, title, command_text, timeout_seconds=3600):
        """
        使用WindowManager显示命令窗口
        新架构：统一窗口管理，避免多线程竞态问题
        """
        from .window_manager import get_window_manager
        
        # 获取窗口管理器并请求窗口
        window_manager = get_window_manager()
        result = window_manager.request_window(title, command_text, timeout_seconds)
        
        return result
    
    def show_command_window_subprocess_legacy(self, title, command_text, timeout_seconds=3600):
        """
        在subprocess中显示命令窗口，完全抑制所有系统输出
        恢复原来GDS的窗口设计：500x50，三按钮，自动复制
        
        Args:
            title (str): 窗口标题
            command_text (str): 要显示的命令文本
            timeout_seconds (int): 超时时间（秒）
        
        Returns:
            dict: 用户操作结果 {"action": "copy/direct_feedback/success/timeout", "data": ...}
        """
        # debug_log(f"🪟 DEBUG: [{get_relative_timestamp()}] [SUBPROCESS_WINDOW] 创建子进程窗口 - title: {title}, thread: {threading.get_ident()}")
        import subprocess
        import sys
        import json
        
        # 转义字符串以防止注入 - 使用base64编码避免复杂转义问题
        import base64
        command_b64 = base64.b64encode(command_text.encode('utf-8')).decode('ascii')
        
        # 获取音频文件路径
        import os
        current_dir = os.path.dirname(__file__)
        audio_file_path = os.path.join(os.path.dirname(current_dir), "tkinter_bell.mp3")
        
        # 创建子进程脚本 - 恢复原来的500x60窗口设计
        subprocess_script = '''
import sys
import os
import json
import warnings
import base64

# 抑制所有警告
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

try:
    import tkinter as tk
    import queue
    
    result = {"action": "timeout"}
    result_queue = queue.Queue()
    
    # 解码base64命令
    command_text = base64.b64decode("{command_b64}").decode('utf-8')
    
    root = tk.Tk()
    root.title("Google Drive Shell")
    root.geometry("500x60")
    root.resizable(False, False)
    
    # 窗口计数器 - 记录到debug日志
    import os
    debug_file = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA/window_queue_debug.log"
    try:
        with open(debug_file, "a", encoding="utf-8") as f:
            import time
            timestamp = time.time() - 1757413752.714440  # 相对时间戳
            f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_CREATED] 窗口创建成功\\n".format(timestamp))
            f.flush()
    except:
        pass
    
    # 居中窗口
    root.eval('tk::PlaceWindow . center')
    
    # 定义统一的聚焦函数
    def force_focus():
        try:
            root.focus_force()
            root.lift()
            root.attributes('-topmost', True)
            
            # macOS特定的焦点获取方法
            import platform
            if platform.system() == 'Darwin':
                import subprocess
                try:
                    # 尝试多个可能的应用程序名称
                    app_names = ['Python', 'python3', 'tkinter', 'Tk']
                    for app_name in app_names:
                        try:
                            subprocess.run(['osascript', '-e', 'tell application "' + app_name + '" to activate'], 
                                          timeout=0.5, capture_output=True)
                            break
                        except:
                            continue
                    
                    # 尝试使用系统事件来强制获取焦点
                    applescript_code = "tell application \\"System Events\\"\\n    set frontmost of first process whose name contains \\"Python\\" to true\\nend tell"
                    subprocess.run(['osascript', '-e', applescript_code], timeout=0.5, capture_output=True)
                except:
                    pass  # 如果失败就忽略
        except:
            pass
    
    # 全局focus计数器和按钮点击标志
    focus_count = 0
    button_clicked = False
    
    # 定义音频播放函数
    def play_bell_in_subprocess():
        try:
            audio_path = "{audio_file_path}"
            if os.path.exists(audio_path):
                import platform
                import subprocess
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["afplay", audio_path], 
                                 capture_output=True, timeout=2)
                elif system == "Linux":
                    # 尝试多个Linux音频播放器
                    players = ["paplay", "aplay", "mpg123", "mpv", "vlc"]
                    for player in players:
                        try:
                            subprocess.run([player, audio_path], 
                                         capture_output=True, timeout=2, check=True)
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                elif system == "Windows":
                    # Windows可以使用winsound模块或powershell
                    try:
                        subprocess.run(["powershell", "-c", 
                                      "(New-Object Media.SoundPlayer '" + audio_path + "').PlaySync()"], 
                                     capture_output=True, timeout=2)
                    except:
                        pass
        except Exception:
            pass  # 如果播放失败，忽略错误
    
    # 带focus计数的聚焦函数
    def force_focus_with_count():
        global focus_count, button_clicked
        
        focus_count += 1
        force_focus()
        

        try:
            import threading
            threading.Thread(target=play_bell_in_subprocess, daemon=True).start()
            root.after(100, lambda: trigger_copy_button())
        except Exception:
            pass
    
    # 设置窗口置顶并初始聚焦（第1次，会播放音效）
    root.attributes('-topmost', True)
    force_focus_with_count()
    
    # 自动复制命令到剪切板
    root.clipboard_clear()
    root.clipboard_append(command_text)
    
    # 主框架
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 按钮框架
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, expand=True)
    
    def copy_command():
        global button_clicked
        button_clicked = True
        try:
            # 使用更可靠的复制方法 - 一次性复制完整命令
            root.clipboard_clear()
            root.clipboard_append(command_text)
            
            # 验证复制是否成功
            try:
                clipboard_content = root.clipboard_get()
                if clipboard_content == command_text:
                    copy_btn.config(text="✅复制成功", bg="#4CAF50")
                else:
                    # 复制不完整，重试一次
                    root.clipboard_clear()
                    root.clipboard_append(command_text)
                    copy_btn.config(text="🔄重新复制", bg="#FF9800")
            except Exception as verify_error:
                # 验证失败但复制可能成功，显示已复制
                copy_btn.config(text="已复制", bg="#4CAF50")
            
            root.after(1500, lambda: copy_btn.config(text="📋复制指令", bg="#2196F3"))
        except Exception as e:
            copy_btn.config(text="Error: 复制失败", bg="#f44336")
    
    def trigger_copy_button():
        """触发复制按钮的点击效果（用于音效播放时自动触发）"""
        try:
            # 模拟按钮点击效果
            copy_btn.config(relief='sunken')
            root.after(50, lambda: copy_btn.config(relief='raised'))
            # 执行复制功能
            copy_command()
        except Exception:
            pass
    
    def execution_completed():
        global button_clicked
        button_clicked = True
        result_queue.put({"action": "success", "message": "用户确认执行完成"})
        result["action"] = "success"
        # 记录窗口销毁
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                timestamp = time.time() - 1757413752.714440
                f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 用户点击成功\\n".format(timestamp))
                f.flush()
        except:
            pass
        root.destroy()
    
    def direct_feedback():
        """直接反馈功能"""
        global button_clicked
        button_clicked = True
        result_queue.put({"action": "direct_feedback", "message": "启动直接反馈模式"})
        result["action"] = "direct_feedback"
        # 记录窗口销毁
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                timestamp = time.time() - 1757413752.714440
                f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 用户点击反馈\\n".format(timestamp))
                f.flush()
        except:
            pass
        root.destroy()
    
    # 复制指令按钮
    copy_btn = tk.Button(
        button_frame, 
        text="📋复制指令", 
        command=copy_command,
        font=("Arial", 9),
        bg="#2196F3",
        fg="white",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    copy_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 直接反馈按钮（第二个位置）
    feedback_btn = tk.Button(
        button_frame, 
        text="💬 直接反馈", 
        command=direct_feedback,
        font=("Arial", 9),
        bg="#FF9800",
        fg="white",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    feedback_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 执行完成按钮（最右边）
    complete_btn = tk.Button(
        button_frame, 
        text="✅执行完成", 
        command=execution_completed,
        font=("Arial", 9, "bold"),
        bg="#4CAF50",
        fg="white",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 设置焦点到完成按钮
    complete_btn.focus_set()
    
    # 添加键盘快捷键
    def on_key_press(event):
        global button_clicked
        
        # Command+C (Mac) 或 Ctrl+C (Windows/Linux) -复制指令
        if ((event.state & 0x8) and event.keysym == 'c') or ((event.state & 0x4) and event.keysym == 'c'):
            button_clicked = True
            copy_command()
            return "break"  # 阻止默认行为
    
    # 绑定键盘事件到窗口（仅保留复制功能）
    root.bind('<Key>', on_key_press)
    root.focus_set()  # 确保窗口能接收键盘事件
    
    # 自动复制命令到剪贴板 - 暂时注释掉自动复制功能
    # copy_command()
    
    # 定期重新获取焦点的函数 - 暂时注释掉5秒refocus机制
    def refocus_window():
        try:
            # 使用带focus计数的聚焦函数
            force_focus_with_count()
            # 每30秒重新获取焦点并播放音效（从5秒改为30秒）
            root.after(30000, refocus_window)
        except:
            pass  # 如果窗口已关闭，忽略错误
    
    # 开始定期重新获取焦点 - 每30秒播放音效
    root.after(30000, refocus_window)
    
    # 设置自动关闭定时器
    def timeout_destroy():
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                timestamp = time.time() - 1757413752.714440
                f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 超时\\n".format(timestamp))
                f.flush()
        except:
            pass
        result.update({"action": "timeout"})
        root.destroy()
    
    root.after({timeout_seconds * 1000}, timeout_destroy)
    
    # 运行窗口
    root.mainloop()
    
    # 输出结果
    print(json.dumps(result))
    
except Exception as e:
    print(json.dumps({"action": "error", "error": str(e)}))
'''.format(
    command_b64=command_b64,
    audio_file_path=audio_file_path,
    timeout_seconds=timeout_seconds
)
        
        try:
            # 在子进程中运行tkinter窗口，抑制所有输出
            result = subprocess.run(
                [sys.executable, '-c', subprocess_script],
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    # 尝试解析整个输出
                    parsed_result = json.loads(result.stdout.strip())
                    return parsed_result
                except json.JSONDecodeError as e:
                    # 尝试解析最后一行（可能包含debug信息）
                    lines = result.stdout.strip().split('\n')
                    for line in reversed(lines):
                        line = line.strip()
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                parsed_result = json.loads(line)
                                return parsed_result
                            except json.JSONDecodeError:
                                continue
                    
                    return {"action": "error", "error": "Failed to parse result"}
            else:
                # 添加调试信息
                error_info = f"Subprocess failed - returncode: {result.returncode}, stdout: {result.stdout[:200]}, stderr: {result.stderr[:200]}"
                print(f"[WINDOW_DEBUG] {error_info}")
                return {"action": "error", "error": error_info}
                
        except subprocess.TimeoutExpired:
            return {"action": "timeout", "error": "Window timeout"}
        except Exception as e:
            return {"action": "error", "error": str(e)}
    
    def copy_to_clipboard(self, text):
        """将文本复制到剪贴板"""
        try:
            # macOS
            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
            # Linux
            elif sys.platform == "linux":
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
            # Windows
            elif sys.platform == "win32":
                subprocess.run(["clip"], input=text.encode(), check=True, shell=True)
            return True
        except:
            return False

# 从配置文件加载常量
from .config_loader import get_config

# 全局常量（从配置文件加载）
_config = get_config()
HOME_URL = _config.HOME_URL
HOME_FOLDER_ID = _config.HOME_FOLDER_ID
REMOTE_ROOT_FOLDER_ID = _config.REMOTE_ROOT_FOLDER_ID
REMOTE_ROOT = _config.REMOTE_ROOT

# 从core_utils迁移的工具函数
def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def show_help():
    """显示帮助信息"""
    try:
        from .help_system import show_unified_help
        return show_unified_help(context="command_line")
    except ImportError:
        try:
            from help_system import show_unified_help
            return show_unified_help(context="command_line")
        except ImportError:
            # Fallback to basic help if help_system is not available
            print(f"GOOGLE_DRIVE - Google Drive access tool with GDS (Google Drive Shell)")
            print(f"Use --shell for interactive mode. Type 'help' in shell for commands.")
            return 0

def main():
    """主函数"""
    import sys
    
    # 从其他模块直接导入需要的函数
    try:
        from .remote_shell_manager import list_shells, create_shell, checkout_shell, terminate_shell, enter_shell_mode
        from .drive_api_service import open_google_drive
        from .sync_config_manager import set_local_sync_dir, set_global_sync_dir
    except ImportError:
        try:
            from modules.remote_shell_manager import list_shells, create_shell, checkout_shell, terminate_shell, enter_shell_mode
            from modules.drive_api_service import open_google_drive
            from modules.sync_config_manager import set_local_sync_dir, set_global_sync_dir
        except ImportError:
            # 如果导入失败，尝试从全局命名空间获取
            list_shells = globals().get('list_shells')
            create_shell = globals().get('create_shell')
            checkout_shell = globals().get('checkout_shell')
            terminate_shell = globals().get('terminate_shell')
            enter_shell_mode = globals().get('enter_shell_mode')
            console_setup_interactive = globals().get('console_setup_interactive')
            open_google_drive = globals().get('open_google_drive')
            set_local_sync_dir = globals().get('set_local_sync_dir')
            set_global_sync_dir = globals().get('set_global_sync_dir')
    
    # 检查是否在RUN环境中
    command_identifier = None
    if len(sys.argv) > 1 and (sys.argv[1].startswith('test_') or sys.argv[1].startswith('cmd_')):
        command_identifier = sys.argv[1]
        args = sys.argv[2:]
    else:
        args = sys.argv[1:]
    
    if not args:
        # 没有参数，打开默认Google Drive
        return open_google_drive(None, command_identifier) if open_google_drive else 1
    
    # 处理各种命令行参数
    if args[0] in ['--help', '-h']:
        show_help()
        return 0
    elif args[0] == '--console-setup':
        return console_setup_interactive() if console_setup_interactive else 1
    elif args[0] == '--create-remote-shell':
        return create_shell(None, None, command_identifier) if create_shell else 1
    elif args[0] == '--list-remote-shell':
        return list_shells(command_identifier) if list_shells else 1
    elif args[0] == '--checkout-remote-shell':
        if len(args) < 2:
            print(f"Error:  错误: 需要指定shell ID")
            return 1
        shell_id = args[1]
        return checkout_shell(shell_id, command_identifier) if checkout_shell else 1
    elif args[0] == '--terminate-remote-shell':
        if len(args) < 2:
            print(f"Error:  错误: 需要指定shell ID")
            return 1
        shell_id = args[1]
        return terminate_shell(shell_id, command_identifier) if terminate_shell else 1
    elif args[0] == '--remount':
        # 处理重新挂载命令
        return handle_remount_command(command_identifier)
    elif args[0] == '--shell':
        if len(args) == 1:
            # 进入交互模式
            return enter_shell_mode(command_identifier) if enter_shell_mode else 1
        else:
            # 执行指定的shell命令 - 使用GoogleDriveShell
            # 检测引号包围的完整命令（用于远端重定向等）
            shell_cmd_parts = args[1:]
            
            # 如果只有一个参数且包含空格，可能是引号包围的完整命令
            if len(shell_cmd_parts) == 1 and (' > ' in shell_cmd_parts[0] or ' && ' in shell_cmd_parts[0] or ' || ' in shell_cmd_parts[0] or ' | ' in shell_cmd_parts[0]):
                # 这是一个引号包围的完整命令，直接使用
                shell_cmd = shell_cmd_parts[0]
                quoted_parts = shell_cmd_parts  # 为调试信息设置
                # 添加标记，表示这是引号包围的命令
                shell_cmd = f"__QUOTED_COMMAND__{shell_cmd}"

            else:
                # 正常的多参数命令，需要正确处理带空格的参数
                # 对包含空格的参数添加引号
                shell_cmd_parts_quoted = []
                for part in shell_cmd_parts:
                    if ' ' in part:
                        shell_cmd_parts_quoted.append(f'"{part}"')
                    else:
                        shell_cmd_parts_quoted.append(part)
                shell_cmd = ' '.join(shell_cmd_parts_quoted)
                quoted_parts = shell_cmd_parts  # 为调试信息设置
            debug_capture.start_capture()
            debug_capture.stop_capture()
            
            try:
                # 动态导入GoogleDriveShell避免循环导入
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from google_drive_shell import GoogleDriveShell
                
                shell = GoogleDriveShell()
                # 这里需要GoogleDriveShell提供一个处理shell命令的方法
                if hasattr(shell, 'execute_shell_command'):
                    return shell.execute_shell_command(shell_cmd, command_identifier)
                else:
                    print(f"Error:  GoogleDriveShell missing execute_shell_command method")
                    return 1
            except Exception as e:
                error_msg = f"Error: Execute shell command failed: {e}"
                print(error_msg)
                return 1
    elif args[0] == '--desktop':
        if len(args) < 2:
            print(f"Error: --desktop needs to specify operation type")
            return 1
        
        desktop_action = args[1]
        if desktop_action == '--status':
            try:
                from .sync_config_manager import get_google_drive_status
                return get_google_drive_status(command_identifier)
            except ImportError:
                try:
                    from modules.sync_config_manager import get_google_drive_status
                    return get_google_drive_status(command_identifier)
                except ImportError:
                    global_get_status = globals().get('get_google_drive_status')
                    if global_get_status:
                        return global_get_status(command_identifier)
                    else:
                        print(f"Error:  Unable to find get_google_drive_status function")
                        return 1
        elif desktop_action == '--shutdown':
            try:
                from .drive_process_manager import shutdown_google_drive
                return shutdown_google_drive(command_identifier)
            except ImportError:
                try:
                    from modules.drive_process_manager import shutdown_google_drive
                    return shutdown_google_drive(command_identifier)
                except ImportError:
                    global_shutdown = globals().get('shutdown_google_drive')
                    if global_shutdown:
                        return global_shutdown(command_identifier)
                    else:
                        print(f"Error:  Unable to find shutdown_google_drive function")
                        return 1
        elif desktop_action == '--launch':
            try:
                from .drive_process_manager import launch_google_drive
                return launch_google_drive(command_identifier)
            except ImportError:
                try:
                    from modules.drive_process_manager import launch_google_drive
                    return launch_google_drive(command_identifier)
                except ImportError:
                    global_launch = globals().get('launch_google_drive')
                    if global_launch:
                        return global_launch(command_identifier)
                    else:
                        print(f"Error:  Unable to find launch_google_drive function")
                        return 1
        elif desktop_action == '--restart':
            try:
                from .drive_process_manager import restart_google_drive
                return restart_google_drive(command_identifier)
            except ImportError:
                try:
                    from modules.drive_process_manager import restart_google_drive
                    return restart_google_drive(command_identifier)
                except ImportError:
                    global_restart = globals().get('restart_google_drive')
                    if global_restart:
                        return global_restart(command_identifier)
                    else:
                        print(f"Error:  Unable to find restart_google_drive function")
                        return 1
        elif desktop_action == '--set-local-sync-dir':
            return set_local_sync_dir(command_identifier) if set_local_sync_dir else 1
        elif desktop_action == '--set-global-sync-dir':
            return set_global_sync_dir(command_identifier) if set_global_sync_dir else 1
        else:
            print(f"Error: Unknown desktop operation: {desktop_action}")
            return 1
    elif args[0] == '--upload':
        # 上传文件：GOOGLE_DRIVE --upload file_path [remote_path] 或 GOOGLE_DRIVE --upload "[[src1, dst1], [src2, dst2], ...]"
        if len(args) < 2:
            print(f"Error: Need to specify the file to upload")
            return 1
            
        try:
            # 动态导入GoogleDriveShell避免循环导入
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
            
            # 检查是否为多文件语法
            if len(args) == 2 and args[1].startswith('[[') and args[1].endswith(']]'):
                try:
                    import ast
                    file_pairs = ast.literal_eval(args[1])
                    result = shell.cmd_upload_multi(file_pairs)
                except:
                    result = {"success": False, "error": "多文件语法格式错误，应为: [[src1, dst1], [src2, dst2], ...]"}
            else:
                # 原有的单文件或多文件到单目标语法
                target_path = "." if len(args) == 2 else args[2]
                
                # 修复路径展开问题：如果target_path是本地完整路径，转换为相对路径
                if target_path.startswith(os.path.expanduser("~")):
                    # 将本地完整路径转换回~/相对路径
                    home_path = os.path.expanduser("~")
                    target_path = "~" + target_path[len(home_path):]
                
                result = shell.cmd_upload([args[1]], target_path)
            
            if is_run_environment(command_identifier):
                write_to_json_output(result, command_identifier)
            # 注意：不在这里调用result_print，因为GoogleDriveShell已经处理了输出
            # 避免重复输出导致进度显示问题
            
            return 0 if result["success"] else 1
            
        except Exception as e:
            error_msg = f"Error: Execute upload command failed: {e}"
            print(error_msg)
            return 1
    elif args[0] == '-my':
        # My Drive URL
        my_drive_url = "https://drive.google.com/drive/u/0/my-drive"
        return open_google_drive(my_drive_url, command_identifier) if open_google_drive else 1
    else:
        # 默认作为URL处理
        url = args[0]
        return open_google_drive(url, command_identifier) if open_google_drive else 1


def handle_remount_command(command_identifier):
    """处理GOOGLE_DRIVE --remount命令"""
    try:
        # 导入GoogleDriveShell并调用重新挂载方法
        import sys
        import os
        
        # 添加GOOGLE_DRIVE_PROJ到路径
        current_dir = os.path.dirname(os.path.dirname(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from google_drive_shell import GoogleDriveShell
        
        # 创建GoogleDriveShell实例
        shell = GoogleDriveShell()
        
        # 调用重新挂载方法
        return shell._handle_remount_command(command_identifier)
        
    except Exception as e:
        print(f"Error: 重新挂载命令失败: {e}")
        return 1