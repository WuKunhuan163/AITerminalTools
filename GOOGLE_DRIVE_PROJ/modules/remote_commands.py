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
    print(f"DEBUG: 具体文件存在: {fingerprint_file}")
    sys.exit(0)  # 文件存在
else:
    print(f"DEBUG: 具体文件不存在: {fingerprint_file}")
    
    # 检查目录是否存在
    dir_path = os.path.dirname("{fingerprint_file}")
    print(f"DEBUG: 目录存在: {{os.path.exists(dir_path)}} - {{dir_path}}")
    
    # 列出所有指纹文件
    pattern = "{fingerprint_file}".rsplit("_", 1)[0] + "_*"
    matching_files = glob.glob(pattern)
    print(f"DEBUG: 匹配的指纹文件: {{matching_files}}")
    
    sys.exit(1)  # 文件不存在
'''
            
            result = subprocess.run(
                ['python3', '-c', python_check_script],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            # 如果有debug输出，显示它
            if result.stdout:
                print(f"DEBUG subprocess stdout: {result.stdout.strip()}")
            if result.stderr:
                print(f"DEBUG subprocess stderr: {result.stderr.strip()}")
            
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
                        
                        # 先在进度行显示√标记，然后清除进度显示
                        from .progress_manager import add_success_mark, clear_progress
                        add_success_mark()
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
                print("Operation cancelled by Ctrl+C during waiting for result from remote. ")
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
            print(f"等待结果超时 ({max_wait_time}秒)。可能的原因：")
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
                print(f"🤖 后台模式检测：自动返回超时错误")
                return {
                    "success": False,
                    "error": f"Result file timeout after 60 seconds: {remote_file_path}",
                    "timeout": True,
                    "background_mode": True
                }
            
            print(f"This may be because:")
            print(f"  1. The command is running in the background (e.g. http-server service)")
            print(f"  2. The command execution time exceeds 60 seconds")
            print(f"  3. The remote encountered an unexpected error")
            print()
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
        echo "❌ Error: {filename} move failed, still failed after 60 retries" >&2
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
            return f'echo "❌ 生成命令失败: {e}"'
    
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
            
            # 使用统一的验证接口
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
                echo "❌ (已重试60次失败)"
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
            return f"echo '❌ 生成多文件mv命令失败: {e}'"

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
                
                from .progress_manager import validate_creation
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
            
            from .progress_manager import validate_creation
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



    def execute_generic_command(self, cmd, args, _skip_queue_management=False):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            _skip_queue_management (bool): 是否跳过队列管理（避免双重管理）
            
        Returns:
            dict: 执行结果，包含stdout、stderr、path等字段
        """
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
                remote_command_info = self._generate_command(cmd, args, current_shell)
                remote_command, result_filename = remote_command_info
                
                # DEBUG: 显示生成的远端命令
                # print(f"DEBUG: Generated remote command for '{cmd} {' '.join(args)}':")
                # print(f"=" * 60)
                # print(remote_command)
                # print(f"=" * 60)
                # print(f"DEBUG: Expected result filename: {result_filename}")
                # print(f"=" * 60)
                
            except Exception as e:
                # 如果语法检查失败，直接返回错误，不弹出窗口
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
            result = self._execute_with_result_capture(remote_command_info, cmd, args, window_id, get_relative_timestamp, debug_log)
            debug_log(f"📋 DEBUG: [{get_relative_timestamp()}] [RESULT] 远端命令执行完成 - window_id: {window_id}, success: {result.get('success', False)}")
            
            # WindowManager自动管理窗口生命周期，无需手动释放
            
            # 如果命令执行成功且包含重定向，则验证文件创建
            if result.get("success", False) and self._is_redirect_command(cmd, args):
                redirect_file = self._extract_redirect_target(args)
                if redirect_file:
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
        """检测命令是否包含重定向操作"""
        # 检查参数中是否包含重定向符号
        return '>' in args
    
    def _extract_redirect_target(self, args):
        """从参数中提取重定向目标文件"""
        try:
            if '>' in args:
                redirect_index = args.index('>')
                if redirect_index + 1 < len(args):
                    return args[redirect_index + 1]
            return None
        except (ValueError, IndexError):
            return None

    def _generate_command(self, cmd, args, current_shell):
        """
        生成远端执行命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            current_shell (dict): 当前shell信息
            
        Returns:
            tuple: (远端命令字符串, 结果文件名)
        """
        try:
            # 获取当前路径
            current_path = current_shell.get("current_path", "~")
            
            # 解析远端绝对路径
            if current_path == "~":
                remote_path = self.main_instance.REMOTE_ROOT
            elif current_path.startswith("~/"):
                remote_path = f"{self.main_instance.REMOTE_ROOT}/{current_path[2:]}"
            else:
                remote_path = current_path
            
            # 构建基础命令 - 避免双重转义
            import shlex
            import json
            import time
            import hashlib
            
            # 重新构建命令，避免双重转义问题
            if args:
                # 正确处理命令参数，特别是bash -c的情况
                if cmd == "bash" and len(args) >= 2 and args[0] == "-c":
                    # 对于bash -c命令，第二个参数需要用引号包围
                    script_content = args[1]
                    full_command = f'bash -c "{script_content}"'
                elif cmd == "sh" and len(args) >= 2 and args[0] == "-c":
                    # 对于sh -c命令，第二个参数需要用引号包围
                    script_content = args[1]
                    full_command = f'sh -c "{script_content}"'
                else:
                    # 检查是否包含重定向符号
                    if '>' in args:
                        # 处理重定向：将参数分为命令部分和重定向部分
                        redirect_index = args.index('>')
                        cmd_args = args[:redirect_index]
                        target_file = args[redirect_index + 1] if redirect_index + 1 < len(args) else None
                        
                        if target_file:
                            # 构建重定向命令
                            if cmd_args:
                                full_command = f"{cmd} {' '.join(cmd_args)} > {target_file}"
                            else:
                                full_command = f"{cmd} > {target_file}"
                        else:
                            # 没有目标文件，回退到普通拼接
                            full_command = f"{cmd} {' '.join(args)}"
                    else:
                        # 其他命令直接拼接，但需要处理~路径展开
                        processed_args = []
                        for arg in args:
                            if arg == "~":
                                # 将~替换为远程根目录路径
                                processed_args.append(f'"{self.main_instance.REMOTE_ROOT}"')
                            elif arg.startswith("~/"):
                                # 将~/path替换为远程路径
                                processed_args.append(f'"{self.main_instance.REMOTE_ROOT}/{arg[2:]}"')
                            else:
                                processed_args.append(arg)
                        full_command = f"{cmd} {' '.join(processed_args)}"
            else:
                full_command = cmd
            
            # 将args转换为JSON格式
            args_json = json.dumps(args)
            
            # 生成结果文件名：时间戳+哈希，存储在REMOTE_ROOT/tmp目录
            timestamp = str(int(time.time()))
            cmd_hash = hashlib.md5(f"{cmd}_{' '.join(args)}_{timestamp}".encode()).hexdigest()[:8]
            result_filename = f"cmd_{timestamp}_{cmd_hash}.json"
            result_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
            
            # 正确处理命令转义：分别转义命令和参数，然后重新组合
            if args:
                # 特殊处理python -c命令，避免内部引号转义问题
                if cmd == "python" and len(args) >= 2 and args[0] == "-c":
                    # 对于python -c命令，将整个python代码作为一个参数进行转义
                    python_code = args[1]
                    # 使用双引号包围python代码，并转义内部的双引号、反斜杠和美元符号
                    escaped_python_code = (python_code.replace('\\', '\\\\')
                                                     .replace('"', '\\"')
                                                     .replace('$', '\\$'))
                    bash_safe_command = f'python -c "{escaped_python_code}"'
                    # 对于python -c命令，也需要更新显示命令
                    full_command = bash_safe_command
                elif cmd in ("bash", "sh") and len(args) >= 2 and args[0] == "-c":
                    # 对于bash/sh -c命令，分离进度显示和工作脚本
                    script_content = args[1]
                    
                    import base64
                    # 统一使用base64编码处理所有复杂脚本，简化逻辑
                    # 确保base64编码不包含换行符和空格
                    encoded_script = base64.b64encode(script_content.encode('utf-8')).decode('ascii').replace('\n', '').replace('\r', '').replace(' ', '')
                    

                    bash_safe_command = f'echo "{encoded_script}" | base64 -d | {cmd}'
                else:
                    # 分别转义命令和每个参数，但特殊处理重定向符号和~路径
                    escaped_cmd = shlex.quote(cmd)
                    escaped_args = []
                    for arg in args:
                        # 重定向符号不需要引号转义
                        if arg in ['>', '>>', '<', '|', '&&', '||']:
                            escaped_args.append(arg)
                        elif arg == "~":
                            # 将~替换为远程根目录路径（已带引号）
                            escaped_args.append(f'"{self.main_instance.REMOTE_ROOT}"')
                        elif arg.startswith("~/"):
                            # 将~/path替换为远程路径（已带引号）
                            escaped_args.append(f'"{self.main_instance.REMOTE_ROOT}/{arg[2:]}"')
                        else:
                            escaped_args.append(shlex.quote(arg))
                    bash_safe_command = f"{escaped_cmd} {' '.join(escaped_args)}"
            else:
                bash_safe_command = shlex.quote(cmd)
            # 普通命令，使用标准的输出捕获
            remote_command = (
                f'# 首先检查挂载是否成功（使用Python避免直接崩溃）\n'
                f'python3 -c "\n'
                f'import os\n'
                f'import glob\n'
                f'import sys\n'
                f'try:\n'
                f'    fingerprint_files = glob.glob(\\"{self.main_instance.REMOTE_ROOT}/.gds_mount_fingerprint_*\\")\n'
                f'    if not fingerprint_files:\n'
                f'        sys.exit(1)\n'
                f'except Exception:\n'
                f'    sys.exit(1)\n'
                f'"\n'
                f'if [ $? -ne 0 ]; then\n'
                f'    clear\n'
                f'    echo "当前session的GDS无法访问Google Drive文件结构。请使用GOOGLE_DRIVE --remount指令重新挂载，然后执行GDS的其他命令"\n'
                f'else\n'
                f'    # 确保工作目录存在\n'
                f'mkdir -p "{remote_path}"\n'
                f'cd "{remote_path}" && {{\n'
                f'    # 确保tmp目录存在\n'
                f'    mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"\n'
                f'    \n'

                f'    \n'
                f'    # 执行命令并捕获输出\n'
                f'    OUTPUT_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_stdout_{timestamp}_{cmd_hash}"\n'
                f'    ERROR_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_stderr_{timestamp}_{cmd_hash}"\n'
                f'    EXITCODE_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_{timestamp}_{cmd_hash}"\n'
                f'    \n'
                f'    # 直接执行命令，捕获输出和错误\n'
                f'    set +e  # 允许命令失败\n'
                f'    {bash_safe_command} > "$OUTPUT_FILE" 2> "$ERROR_FILE"\n'
                f'    EXIT_CODE=$?\n'
                f'    echo "$EXIT_CODE" > "$EXITCODE_FILE"\n'
                f'    set -e\n'
                f'    \n'
                f'    # stdout内容将通过JSON结果文件传递，不在这里显示\n'
                f'    # 这样避免重复输出问题\n'
                f'    \n'
                f'    # 显示stderr内容（如果有）\n'
                f'    if [ -s "$ERROR_FILE" ]; then\n'
                f'        cat "$ERROR_FILE" >&2\n'
                f'    fi\n'
                f'    \n'
                f'    # 统一的执行完成提示（无论成功失败都显示完成）\n'
                f'    if [ "$EXIT_CODE" -eq 0 ]; then\n'
                f'        clear && echo "✅执行完成"\n'
                f'    else\n'
                f'        clear && echo "✅执行完成"\n'
                f'    fi\n'
                f'    \n'
            )
            
            # 添加JSON结果文件生成部分（对于所有命令）
            remote_command += (
                f'    # 设置环境变量并生成JSON结果文件\n'
                f'    export EXIT_CODE=$EXIT_CODE\n'
                f'    PYTHON_SCRIPT="{self.main_instance.REMOTE_ROOT}/tmp/json_generator_{timestamp}_{cmd_hash}.py"\n'
                f'    cat > "$PYTHON_SCRIPT" << \'SCRIPT_END\'\n'
                f'import json\n'
                f'import os\n'
                f'import sys\n'
                f'from datetime import datetime\n'
                f'\n'
                f'# 读取输出文件\n'
                f'stdout_content = ""\n'
                f'stderr_content = ""\n'
                f'raw_stdout = ""\n'
                f'raw_stderr = ""\n'
                f'\n'
                f'# 文件路径\n'
                f'stdout_file = "{self.main_instance.REMOTE_ROOT}/tmp/cmd_stdout_{timestamp}_{cmd_hash}"\n'
                f'stderr_file = "{self.main_instance.REMOTE_ROOT}/tmp/cmd_stderr_{timestamp}_{cmd_hash}"\n'
                f'exitcode_file = "{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_{timestamp}_{cmd_hash}"\n'
                f'\n'
                f'# 调试信息\n'
                # f'print(f"DEBUG: 检查stdout文件: {{stdout_file}}", file=sys.stderr)\n'
                # f'print(f"DEBUG: stdout文件存在: {{os.path.exists(stdout_file)}}", file=sys.stderr)\n'
                f'if os.path.exists(stdout_file):\n'
                f'    stdout_size = os.path.getsize(stdout_file)\n'
                # f'    print(f"DEBUG: stdout文件大小: {{stdout_size}} bytes", file=sys.stderr)\n'
                f'else:\n'
                f'    pass\n'
                # f'    print(f"DEBUG: stdout文件不存在！", file=sys.stderr)\n'
                f'\n'
                # f'print(f"DEBUG: 检查stderr文件: {{stderr_file}}", file=sys.stderr)\n'
                # f'print(f"DEBUG: stderr文件存在: {{os.path.exists(stderr_file)}}", file=sys.stderr)\n'
                f'if os.path.exists(stderr_file):\n'
                f'    stderr_size = os.path.getsize(stderr_file)\n'
                # f'    print(f"DEBUG: stderr文件大小: {{stderr_size}} bytes", file=sys.stderr)\n'
                f'else:\n'
                f'    pass\n'
                # f'    print(f"DEBUG: stderr文件不存在！", file=sys.stderr)\n'
                f'\n'
                f'# 读取stdout文件\n'
                f'if os.path.exists(stdout_file):\n'
                f'    try:\n'
                f'        with open(stdout_file, "r", encoding="utf-8", errors="ignore") as f:\n'
                f'            raw_stdout = f.read()\n'
                f'        stdout_content = raw_stdout.strip()\n'
                # f'        print(f"DEBUG: 成功读取stdout，长度: {{len(raw_stdout)}}", file=sys.stderr)\n'
                f'    except Exception as e:\n'
                # f'        print(f"DEBUG: 读取stdout失败: {{e}}", file=sys.stderr)\n'
                f'        raw_stdout = f"ERROR: 无法读取stdout文件: {{e}}"\n'
                f'        stdout_content = raw_stdout\n'
                f'else:\n'
                f'    raw_stdout = "ERROR: stdout文件不存在"\n'
                f'    stdout_content = ""\n'
                # f'    print(f"DEBUG: stdout文件不存在，无法读取内容", file=sys.stderr)\n'
                f'\n'
                f'# 读取stderr文件\n'
                f'if os.path.exists(stderr_file):\n'
                f'    try:\n'
                f'        with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:\n'
                f'            raw_stderr = f.read()\n'
                f'        stderr_content = raw_stderr.strip()\n'
                # f'        print(f"DEBUG: 成功读取stderr，长度: {{len(raw_stderr)}}", file=sys.stderr)\n'
                f'    except Exception as e:\n'
                # f'        print(f"DEBUG: 读取stderr失败: {{e}}", file=sys.stderr)\n'
                f'        raw_stderr = f"ERROR: 无法读取stderr文件: {{e}}"\n'
                f'        stderr_content = raw_stderr\n'
                f'else:\n'
                f'    raw_stderr = ""\n'
                f'    stderr_content = ""\n'
                # f'    print(f"DEBUG: stderr文件不存在（正常情况）", file=sys.stderr)\n'
                f'\n'
                f'# 读取退出码\n'
                f'exit_code = 0\n'
                f'if os.path.exists(exitcode_file):\n'
                f'    try:\n'
                f'        with open(exitcode_file, "r") as f:\n'
                f'            exit_code = int(f.read().strip())\n'
                f'    except:\n'
                f'        exit_code = -1\n'
                f'\n'
                f'# 构建结果JSON\n'
                f'result = {{\n'
                f'    "cmd": "{cmd}",\n'
                f'    "args": {args_json},\n'
                f'    "working_dir": os.getcwd(),\n'
                f'    "timestamp": datetime.now().isoformat(),\n'
                f'    "exit_code": exit_code,\n'
                f'    "stdout": stdout_content,\n'
                f'    "stderr": stderr_content,\n'
                f'    "raw_output": raw_stdout,\n'
                f'    "raw_error": raw_stderr,\n'
                f'    "debug_info": {{\n'
                f'        "stdout_file_exists": os.path.exists(stdout_file),\n'
                f'        "stderr_file_exists": os.path.exists(stderr_file),\n'
                f'        "stdout_file_size": os.path.getsize(stdout_file) if os.path.exists(stdout_file) else 0,\n'
                f'        "stderr_file_size": os.path.getsize(stderr_file) if os.path.exists(stderr_file) else 0\n'
                f'    }}\n'
                f'}}\n'
                f'\n'
                f'print(json.dumps(result, indent=2, ensure_ascii=False))\n'
                f'SCRIPT_END\n'
                f'    python3 "$PYTHON_SCRIPT" > "{result_path}"\n'
                f'    rm -f "$PYTHON_SCRIPT"\n'
                f'    \n'
                f'    # 清理临时文件（在JSON生成之后）\n'
                f'    rm -f "$OUTPUT_FILE" "$ERROR_FILE" "$EXITCODE_FILE"\n'
                f'    }}\n'
                f'fi'
            )
            
            # 在返回前进行语法检查
            return remote_command, result_filename
            
        except Exception as e:
            raise Exception(f"Generate remote command failed: {str(e)}")

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
            
            # 在显示命令窗口前，先输出命令到command文件供检查
            try:
                import os
                command_file_path = "/Users/wukunhuan/.local/bin/command"
                with open(command_file_path, 'w', encoding='utf-8') as f:
                    f.write(remote_command)
                debug_log_func(f"📝 DEBUG: [{get_timestamp_func()}] [COMMAND_FILE] 已输出命令到 {command_file_path}")
            except Exception as e:
                debug_log_func(f"⚠️ DEBUG: [{get_timestamp_func()}] [COMMAND_FILE_ERROR] 输出command文件失败: {e}")
            
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
            window_result = self._show_command_window(cmd, args, final_remote_command)
            debug_print(f"_show_command_window返回结果: {window_result}")
            
            # 检查用户窗口操作结果，并在适当时机释放槽位
            user_completed_window = False
            
            if window_result.get("action") == "direct_feedback":
                # 直接反馈已经在_show_command_window中处理完毕，直接返回结果
                debug_print(f"_execute_with_result_capture: 检测到direct_feedback，直接返回window_result")
                debug_print(f"window_result: {window_result}")
                user_completed_window = True  # 用户完成了窗口操作
                debug_log_func(f"👤 DEBUG: [{get_timestamp_func()}] [USER_COMPLETED] 设置user_completed_window=True (direct_feedback) - window_id: {window_id}")
                debug_capture.stop_capture()  # 在返回前停止debug捕获
                
                # WindowManager自动处理窗口生命周期
                debug_log_func(f"🏗️ DEBUG: [{get_timestamp_func()}] [USER_FEEDBACK] 用户完成直接反馈 - window_id: {window_id}")
                
                return window_result
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
                    "error": f"User operation: Timeout or cancelled",
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
                "stdout": result_data["data"].get("stdout", "") + "\n" if result_data["data"].get("stdout", "").strip() else "",
                "stderr": result_data["data"].get("stderr", "") + "\n" if result_data["data"].get("stderr", "").strip() else "",
                "working_dir": result_data["data"].get("working_dir", ""),
                "timestamp": result_data["data"].get("timestamp", ""),
                "path": f"tmp/{result_filename}",  # 远端结果文件路径
            }
            
        except Exception as e:
            debug_log_func(f"❌ DEBUG: [{get_timestamp_func()}] [CAPTURE_ERROR] _execute_with_result_capture 异常 - window_id: {window_id}, error: {str(e)}")
            return {
                "success": False,
                "error": f"执行结果捕获失败: {str(e)}"
            }
        finally:
            # 停止进度缓冲
            stop_progress_buffering()
            
            # 单窗口锁机制下不需要心跳线程
            debug_log_func(f"🏁 DEBUG: [{get_timestamp_func()}] [CLEANUP] 清理完成 - window_id: {window_id}")
            
            # print(f"DEBUG: [{get_timestamp_func()}] [CAPTURE_EXIT] _execute_with_result_capture 结束 - window_id: {window_id}")
        # 注意：窗口槽位的释放由execute_generic_command的finally块统一处理

    def _show_command_window(self, cmd, args, remote_command, debug_info=None):
        """
        显示远端命令的窗口（使用subprocess方法，完全抑制IMK信息）
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            remote_command (str): 远端命令内容
            debug_info (str): debug信息，仅在直接反馈时输出
        
        Returns:
            dict: 用户操作结果
        """
        try:
            
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
                    feedback_result = self.direct_feedback(remote_command, debug_info)
                    return {
                        "success": feedback_result.get("success", False),
                        "action": "direct_feedback",
                        "data": feedback_result.get("data", {}),
                        "source": "direct_feedback"
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
            copy_btn.config(text="❌ 复制失败", bg="#f44336")
    
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
                # 正常的多参数命令，直接组合，不进行额外的引号转义
                # 因为参数已经由shell正确解析过了
                shell_cmd = ' '.join(shell_cmd_parts)
                quoted_parts = shell_cmd_parts  # 为调试信息设置
            debug_capture.start_capture()
            debug_print(f"DEBUG: args[1:] = {args[1:]}")
            debug_print(f"DEBUG: shell_cmd_parts = {shell_cmd_parts}")
            debug_print(f"DEBUG: quoted_parts = {quoted_parts}")
            debug_print(f"DEBUG: final shell_cmd = {repr(shell_cmd)}")
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
                error_msg = f"❌ Execute shell command failed: {e}"
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
            else:
                if result["success"]:
                    print(result["message"])
                    if result.get("uploaded_files"):
                        print(f"Successfully uploaded:")
                        for file in result["uploaded_files"]:
                            if file.get('url') and file['url'] != 'unavailable':
                                print(f"  - {file['name']} (ID: {file.get('id', 'unknown')}, URL: {file['url']})")
                            else:
                                print(f"  - {file['name']} (ID: {file.get('id', 'unknown')})")
                    if result.get("failed_files"):
                        print(f"Failed to upload:")
                        for file in result["failed_files"]:
                            print(f"  - {file}")
                else:
                    print(f"Error: {result.get('error', 'Upload failed')}")
            
            return 0 if result["success"] else 1
            
        except Exception as e:
            error_msg = f"❌ Execute upload command failed: {e}"
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
        print(f"❌ 重新挂载命令失败: {e}")
        return 1