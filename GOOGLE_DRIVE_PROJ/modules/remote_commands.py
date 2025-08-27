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
    

    
    def generate_remote_commands(self, file_moves, target_path, folder_upload_info=None):
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
            base_command = self._generate_multi_file_remote_commands(all_file_moves)
            
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
                    timeout=0.1  # 0.1秒超时
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
            

            # 输出等待指示器
            print("⏳ Waiting for result ...", end="", flush=True)
            
            # 等待文件出现，最多60秒
            max_wait_time = 60
            for i in range(max_wait_time):
                # 检查文件是否存在
                check_result = self._check_remote_file_exists(remote_file_path)
                
                if check_result.get("exists"):
                    # 文件存在，读取内容
                    print("√")
                    return self._read_result_file_via_gds(result_filename)
                
                # 文件不存在，等待1秒并输出进度点
                time.sleep(1)
                print(".", end="", flush=True)
            
            # 超时，提供用户输入fallback
            print()  # 换行
            print(f"Waiting for result file: {remote_file_path} timed out")
            print("This may be because:")
            print("  1. The command is running in the background (e.g. http-server service)")
            print("  2. The command execution time exceeds 60 seconds")
            print("  3. The remote encountered an unexpected error")
            print()
            print("Please provide the execution result:")
            print("- Enter multiple lines to describe the command execution")
            print("- Press Ctrl+D to end input")
            print("- Or press Enter directly to skip")
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
                    print(f"\n[TIMEOUT] 输入超时 ({timeout_seconds}秒)")
                    break
        except KeyboardInterrupt:
            # Ctrl+C，询问是否取消
            print("\n是否取消输入？(y/N): ", end="", flush=True)
            try:
                response = input().strip().lower()
                if response in ['y', 'yes']:
                    return ""
                else:
                    print("继续输入 (按 Ctrl+D 结束):")
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
                    "error": f"远端结果文件不存在: {remote_file_path}"
                }
            
            # 使用cat命令读取文件内容
            cat_result = self.main_instance.cmd_cat(remote_file_path)
            
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"读取文件内容失败: {cat_result.get('error', 'unknown error')}"
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
                        "stderr": f"JSON解析失败: {str(e)}",
                        "raw_content": content
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"读取结果文件时出错: {str(e)}"
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
                return {"exists": False, "error": f"无法访问目录: {dir_path}"}
            
            # 检查文件和文件夹是否在列表中
            files = ls_result.get("files", [])
            folders = ls_result.get("folders", [])
            all_items = files + folders
            
            # 检查文件或文件夹是否存在
            file_exists = any(f.get("name") == filename for f in all_items)
            
            return {"exists": file_exists}
                
        except Exception as e:
            return {"exists": False, "error": f"检查文件存在性时出错: {str(e)}"}

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

    def show_remote_command_window(self, remote_command, command_type="upload", debug_info=None):
        """
        显示远端命令的 tkinter 窗口（统一版本，使用_show_generic_command_window）
        
        Args:
            remote_command (str): 要显示的远端命令
            command_type (str): 命令类型，默认为 "upload"
            debug_info (str): debug信息，仅在直接反馈时输出
            
        Returns:
            dict: 用户操作结果，包含 action 和相关信息
        """
        try:
            # 调用统一的通用窗口
            debug_info = debug_capture.get_debug_info()
            window_result = self._show_generic_command_window(command_type, [], remote_command, debug_info)
            
            # 适配返回格式以保持向后兼容
            if window_result.get("action") == "success":
                return {"success": True, "action": "success", "error_info": None}
            elif window_result.get("action") == "direct_feedback":
                # 处理直接反馈，保持direct_feedback action类型，跳过验证
                data = window_result.get("data", {})
                exit_code = data.get("exit_code", 0)
                return {
                    "success": exit_code == 0, 
                    "action": "direct_feedback", 
                    "exit_code": exit_code,
                    "stdout": data.get("stdout", ""),
                    "stderr": data.get("stderr", ""),
                    "source": "direct_feedback"
                }
            else:
                return {"success": False, "action": "cancel", "error_info": "Operation cancelled"}
            
        except ImportError:
            # tkinter 不可用，回退到终端显示
            print("=" * 80)
            print("🚀 Google Drive Upload - Remote Terminal Command")
            print("=" * 80)
            print()
            print("请在远端终端执行以下命令：")
            print()
            print(remote_command)
            print()
            print("=" * 80)
            
            try:
                while True:
                    user_choice = self.get_multiline_input_safe("命令执行结果 [s=成功/f=失败/c=取消]: ", single_line=True)
                    if user_choice is None:
                        return {"success": False, "action": "cancelled", "error_info": "用户取消操作"}
                    user_choice = user_choice.lower()
                    if user_choice in ['s', 'success', '成功']:
                        return {"success": True, "action": "success", "error_info": None}
                    elif user_choice in ['f', 'failed', '失败']:
                        error_info = self.get_multiline_input_safe("请描述失败的原因: ", single_line=False)
                        return {
                            "success": False, 
                            "action": "failed", 
                            "error_info": error_info or "用户未提供具体错误信息"
                        }
                    elif user_choice in ['c', 'cancel', '取消']:
                        return {"success": False, "action": "cancelled", "error_info": "用户取消操作"}
                    else:
                        print("❌ 无效选择，请输入 s/f/c")
                        
            except KeyboardInterrupt:
                print("\n❌ 上传已取消")
                return {"success": False, "action": "cancelled", "error_info": "用户中断操作"}
                
        except Exception as e:
            print(f"❌ 显示远端命令窗口时出错: {e}")
            return {"success": False, "action": "error", "error_info": f"窗口显示错误: {e}"}

    def _generate_multi_file_remote_commands(self, all_file_moves):
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
        echo "❌ 错误：{filename} 移动失败，重试60次后仍然失败" >&2
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
echo "✅ 执行完成"'''
            
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
            
            print(f"⏳ Validating {file_display} ...", end="", flush=True)
            
            found_files = []
            missing_files = []
            
            # 序列化验证每个文件
            for i, expected_file in enumerate(expected_files):

                # 对每个文件最多重试60次
                for attempt in range(1, 61):
                    # 使用ls命令检查文件是否存在
                    validation_result = self.main_instance.validation.verify_upload_success_by_ls(
                        expected_files=[expected_file],
                        target_path=target_path,
                        current_shell=current_shell
                    )
                    
                    if validation_result["success"] and len(validation_result.get("found_files", [])) > 0:
                        print("√", end="", flush=True)
                        found_files.append(expected_file)
                        break
                    elif attempt == 60:
                        print("✗", end="", flush=True)
                        missing_files.append(expected_file)
                        break
                    else:
                        print(".", end="", flush=True)
                        time.sleep(1)
            print()
            
            # 输出最终结果
            all_found = len(missing_files) == 0
            return {
                "success": all_found,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_found": len(found_files),
                "total_expected": len(expected_files),
                "search_path": target_path
            }
            
        except Exception as e:
            print(" ❌")
            debug_print(f"Validation error: {e}")
            return {
                "success": False,
                "error": str(e),
                "found_files": [],
                "missing_files": expected_files,
                "total_found": 0,
                "total_expected": len(expected_files)
            }

    def _generate_multi_mv_remote_commands(self, file_pairs, current_shell):
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
    echo "✅ 所有文件移动完成"
else
    echo "⚠️  部分文件移动完成: ${{success_count:-0}}/${{total_files:-0}} 成功, ${{fail_count:-0}} 失败"
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
            print(f"❌ 生成mkdir命令时出错: {e}")
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
                print("(多行输入，按 Ctrl+D 结束):")
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
            print("\n输入已取消")
            return None
        except Exception as e:
            print(f"\n输入错误: {e}")
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
                return self._handle_mkdir_success(context_info)
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
                    "message": "远端命令执行完成"
                }
                
        except Exception as e:
            return {
                "success": False,
                "post_processing_error": True,
                "error": str(e),
                "message": f"成功后处理错误: {e}"
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
            
            # 添加延迟检测机制，参考mkdir的检测逻辑
            print("⏳ Validating touch file creation", end="", flush=True)
            
            max_attempts = 60
            for attempt in range(max_attempts):
                try:
                    # 检查文件是否存在
                    check_result = self._check_remote_file_exists(absolute_path)
                    
                    if check_result.get("exists"):
                        print("√")  # 成功标记
                        return {
                            "success": True,
                            "user_confirmed": True,
                            "command_type": "touch",
                            "message": f"File '{filename}' created and verified successfully",
                            "filename": filename,
                            "absolute_path": absolute_path
                        }
                    
                    # 文件不存在，等待1秒并输出进度点
                    time.sleep(1)
                    print(".", end="", flush=True)
                    
                except Exception as e:
                    print(f"\n⚠️ Error checking file: {str(e)[:50]}")
                    # 检测失败，但不影响整体结果
                    break
            
            # 超时或检测失败，但仍然返回成功（用户已确认执行）
            print(f"\n💡 File creation completed (validation timeout after {max_attempts}s)")
            return {
                "success": True,
                "user_confirmed": True,
                "command_type": "touch",
                "message": f"File '{filename}' creation completed",
                "filename": filename,
                "absolute_path": absolute_path,
                "validation_timeout": True
            }
            
        except Exception as e:
            # 验证过程出错，但不影响touch的成功状态
            return {
                "success": True,
                "user_confirmed": True,
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

    def _handle_mkdir_success(self, context_info):
        """处理mkdir命令成功后的逻辑，包含延迟检测机制"""
        try:
            import time
            
            target_path = context_info.get("target_path", "")
            absolute_path = context_info.get("absolute_path", "")
            
            if not target_path:
                return {
                    "success": True,
                    "user_confirmed": True,
                    "command_type": "mkdir",
                    "message": "Mkdir command executed successfully"
                }
            
            # 添加延迟检测机制，参考echo > file的检测逻辑
            print("⏳ Validating directory creation", end="", flush=True)
            
            max_attempts = 60
            for attempt in range(max_attempts):
                try:
                    # 检查目录是否存在
                    check_result = self._check_remote_file_exists(absolute_path)
                    
                    if check_result.get("exists"):
                        print("√")  # 成功标记
                        return {
                            "success": True,
                            "user_confirmed": True,
                            "command_type": "mkdir",
                            "message": f"Directory '{target_path}' created and verified successfully",
                            "path": target_path,
                            "absolute_path": absolute_path
                        }
                    
                    # 目录不存在，等待1秒并输出进度点
                    time.sleep(1)
                    print(".", end="", flush=True)
                    
                except Exception as e:
                    print(f"\n⚠️ Error checking directory: {str(e)[:50]}")
                    # 检测失败，但不影响整体结果
                    break
            
            # 超时或检测失败，但仍然返回成功（用户已确认执行）
            print(f"\n💡 Directory creation completed (validation timeout after {max_attempts}s)")
            return {
                "success": True,
                "user_confirmed": True,
                "command_type": "mkdir",
                "message": f"Directory '{target_path}' creation completed",
                "path": target_path,
                "absolute_path": absolute_path,
                "validation_timeout": True
            }
            
        except Exception as e:
            # 验证过程出错，但不影响mkdir的成功状态
            return {
                "success": True,
                "user_confirmed": True,
                "command_type": "mkdir",
                "message": f"Directory created successfully (validation error: {str(e)[:50]})",
                "validation_error": str(e)
            }

    def execute_generic_remote_command(self, cmd, args):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            
        Returns:
            dict: 执行结果，包含stdout、stderr、path等字段
        """
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
                remote_command_info = self._generate_remote_command(cmd, args, current_shell)
                remote_command, result_filename = remote_command_info
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
            result = self._execute_with_result_capture(remote_command_info, cmd, args)
            
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

    def _generate_remote_command(self, cmd, args, current_shell):
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
            
            # 为echo显示创建安全版本，避免特殊字符破坏bash语法
            display_command = self._escape_for_display(full_command)
            
            # 检查命令是否包含重定向符号
            has_redirect = any(op in args for op in ['>', '>>', '<', '|'])
            
            if has_redirect:
                # 命令本身包含重定向，不要添加额外的输出捕获
                remote_command = (
                    f'cd "{remote_path}" && {{\n'
                    f'    # 确保tmp目录存在\n'
                    f'    mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"\n'
                    f'    \n'

                    f'    \n'
                    f'    # 执行命令（包含重定向）\n'
                    f'    EXITCODE_FILE="{self.main_instance.REMOTE_ROOT}/tmp/cmd_exitcode_{timestamp}_{cmd_hash}"\n'
                    f'    \n'
                    f'    # 直接执行命令，不捕获输出（因为命令本身有重定向）\n'
                    f'    set +e  # 允许命令失败\n'
                    f'    {bash_safe_command} && clear && echo "✅ 执行完成" || echo "❌ 执行失败"\n'
                    f'    EXIT_CODE=$?\n'
                    f'    echo "$EXIT_CODE" > "$EXITCODE_FILE"\n'
                    f'    set -e\n'
                    f'    \n'
                )
            else:
                # 普通命令，使用标准的输出捕获
                remote_command = (
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
                    f'    # 显示stdout内容\n'
                    f'    if [ -s "$OUTPUT_FILE" ]; then\n'
                    f'        cat "$OUTPUT_FILE"\n'
                    f'    fi\n'
                    f'    \n'
                    f'    # 显示stderr内容（如果有）\n'
                    f'    if [ -s "$ERROR_FILE" ]; then\n'
                    f'        cat "$ERROR_FILE" >&2\n'
                    f'    fi\n'
                    f'    \n'
                    f'    # 统一的执行完成提示\n'
                    f'    if [ "$EXIT_CODE" -eq 0 ]; then\n'
                    f'        clear && echo "✅ 执行完成"\n'
                    f'    else\n'
                    f'        echo "❌ 执行失败 (退出码: $EXIT_CODE)"\n'
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
                # f'    print("DEBUG: stdout文件不存在！", file=sys.stderr)\n'
                f'\n'
                # f'print(f"DEBUG: 检查stderr文件: {{stderr_file}}", file=sys.stderr)\n'
                # f'print(f"DEBUG: stderr文件存在: {{os.path.exists(stderr_file)}}", file=sys.stderr)\n'
                f'if os.path.exists(stderr_file):\n'
                f'    stderr_size = os.path.getsize(stderr_file)\n'
                # f'    print(f"DEBUG: stderr文件大小: {{stderr_size}} bytes", file=sys.stderr)\n'
                f'else:\n'
                f'    pass\n'
                # f'    print("DEBUG: stderr文件不存在！", file=sys.stderr)\n'
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
                # f'    print("DEBUG: stdout文件不存在，无法读取内容", file=sys.stderr)\n'
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
                # f'    print("DEBUG: stderr文件不存在（正常情况）", file=sys.stderr)\n'
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
                f'}}'
            )
            
            # 在返回前进行语法检查
            # print(f"🔍 [DEBUG] 开始语法检查，命令长度: {len(remote_command)} 字符")
            syntax_check = self.validate_bash_syntax_fast(remote_command)
            # print(f"🔍 [DEBUG] 语法检查结果: {syntax_check}")
            if not syntax_check["success"]:
                print(f"❌ [DEBUG] 语法检查失败，抛出异常")
                raise Exception(f"生成的bash命令语法错误: {syntax_check['error']}")
            else:
                pass
                # print(f"✅ [DEBUG] 语法检查通过")
            
            return remote_command, result_filename
            
        except Exception as e:
            raise Exception(f"生成远端命令失败: {str(e)}")

    def _execute_with_result_capture(self, remote_command_info, cmd, args):
        """
        执行远端命令并捕获结果
        
        Args:
            remote_command_info (tuple): (远端命令, 结果文件名)
            cmd (str): 原始命令名
            args (list): 原始命令参数
            
        Returns:
            dict: 执行结果
        """
        try:
            remote_command, result_filename = remote_command_info
            
            # 在显示命令窗口前进行语法检查
            syntax_check = self.validate_bash_syntax_fast(remote_command)
            if not syntax_check["success"]:
                return {
                    "success": False,
                    "error": f"命令语法错误: {syntax_check.get('error')}",
                    "cmd": cmd,
                    "args": args,
                    "syntax_error": syntax_check.get("error")
                }
            
            # 通过tkinter显示命令并获取用户反馈
            debug_info = debug_capture.get_debug_info()
            debug_capture.start_capture()  # 启动debug捕获，避免窗口期间的debug输出
            debug_print("_execute_with_result_capture: 即将调用_show_generic_command_window")
            debug_print(f"cmd: {cmd}, args: {args}")
            window_result = self._show_generic_command_window(cmd, args, remote_command, debug_info)
            debug_print(f"_show_generic_command_window返回结果: {window_result}")
            
            if window_result.get("action") == "direct_feedback":
                # 直接反馈已经在_show_generic_command_window中处理完毕，直接返回结果
                debug_print("_execute_with_result_capture: 检测到direct_feedback，直接返回window_result")
                debug_print(f"window_result: {window_result}")
                debug_capture.stop_capture()  # 在返回前停止debug捕获
                return window_result
            elif window_result.get("action") != "success":
                debug_print("_execute_with_result_capture: window_result.action != 'success'")
                debug_print(f"实际的window_result.action: {window_result.get('action')}")
                debug_print(f"完整window_result: {window_result}")
                debug_capture.stop_capture()  # 在返回前停止debug捕获
                return {
                    "success": False,
                    "error": f"User operation: Timeout or cancelled",
                    "user_feedback": window_result
                }
            
            debug_capture.stop_capture()  # 成功路径的debug捕获停止
            
            # 等待远端文件出现，最多等待60秒
            result_data = self._wait_and_read_result_file(result_filename)
            
            if not result_data.get("success"):
                return {
                    "success": False,
                    "error": "读取结果文件失败",
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
                "path": f"tmp/{result_filename}"  # 远端结果文件路径
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"执行结果捕获失败: {str(e)}"
            }

    def _show_generic_command_window(self, cmd, args, remote_command, debug_info=None):
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
            
            # 使用subprocess方法显示窗口
            result = self.show_command_window_subprocess(
                title=title,
                command_text=remote_command,
                instruction_text=instruction,
                timeout_seconds=300
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
                debug_print("检测到direct_feedback action，即将调用direct_feedback方法")
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
        debug_print("进入direct_feedback方法")
        
        # 先输出debug信息（如果有的话）
        if debug_info:
            print("Debug information:")
            print(debug_info)
            print("=" * 20)  # 20个等号分割线
        
        # 然后粘贴生成的远端指令
        print("Generated remote command:")
        print(remote_command)
        print("=" * 20)  # 50个等号分割线
        
        print("Please provide command execution result (multi-line input, press Ctrl+D to finish):")
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
    
    def show_command_window_subprocess(self, title, command_text, instruction_text="", timeout_seconds=300):
        """
        在subprocess中显示命令窗口，完全抑制所有系统输出
        恢复原来GDS的窗口设计：500x50，三按钮，自动复制
        
        Args:
            title (str): 窗口标题
            command_text (str): 要显示的命令文本
            instruction_text (str): 指令说明文本（可选）
            timeout_seconds (int): 超时时间（秒）
        
        Returns:
            dict: 用户操作结果 {"action": "copy/direct_feedback/success/timeout", "data": ...}
        """
        import subprocess
        import sys
        import json
        
        # 转义字符串以防止注入 - 使用base64编码避免复杂转义问题
        import base64
        title_escaped = title.replace('"', '\\"').replace("'", "\\'")
        # 使用base64编码来避免复杂的字符串转义问题
        command_b64 = base64.b64encode(command_text.encode('utf-8')).decode('ascii')
        
        # 获取音频文件路径
        import os
        current_dir = os.path.dirname(__file__)
        audio_file_path = os.path.join(os.path.dirname(current_dir), "tkinter_bell.mp3")
        
        # 创建子进程脚本 - 恢复原来的500x60窄窗口设计
        subprocess_script = f'''
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
    
    result = {{"action": "timeout"}}
    result_queue = queue.Queue()
    
    # 解码base64命令
    command_text = base64.b64decode("{command_b64}").decode('utf-8')
    
    root = tk.Tk()
    root.title("Google Drive Shell")
    root.geometry("500x60")
    root.resizable(False, False)
    
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
                    copy_btn.config(text="✅ 复制成功", bg="#4CAF50")
                else:
                    # 复制不完整，重试一次
                    root.clipboard_clear()
                    root.clipboard_append(command_text)
                    copy_btn.config(text="⚠️ 已重试", bg="#FF9800")
            except Exception as verify_error:
                # 验证失败但复制可能成功，显示已复制
                copy_btn.config(text="✅ 已复制", bg="#4CAF50")
            
            root.after(1500, lambda: copy_btn.config(text="📋 复制指令", bg="#2196F3"))
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
        result_queue.put({{"action": "success", "message": "用户确认执行完成"}})
        result["action"] = "success"
        root.destroy()
    
    def direct_feedback():
        """直接反馈功能"""
        global button_clicked
        button_clicked = True
        result_queue.put({{"action": "direct_feedback", "message": "启动直接反馈模式"}})
        result["action"] = "direct_feedback"
        root.destroy()
    
    # 复制指令按钮
    copy_btn = tk.Button(
        button_frame, 
        text="📋 复制指令", 
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
        text="✅ 执行完成", 
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
        # Command+C (Mac) 或 Ctrl+C (Windows/Linux) - 复制指令
        if ((event.state & 0x8) and event.keysym == 'c') or ((event.state & 0x4) and event.keysym == 'c'):
            button_clicked = True
            copy_command()
            return "break"  # 阻止默认行为
        # Ctrl+D - 直接反馈
        elif (event.state & 0x4) and event.keysym == 'd':
            button_clicked = True
            direct_feedback()
            return "break"
        # Command+Enter (Mac) - 执行完成
        elif (event.state & 0x8) and event.keysym == 'Return':
            button_clicked = True
            execution_completed()
            return "break"
    
    # 绑定键盘事件到窗口
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
    root.after({timeout_seconds * 1000}, lambda: (result.update({{"action": "timeout"}}), root.destroy()))
    
    # 运行窗口
    root.mainloop()
    
    # 输出结果
    print(json.dumps(result))
    
except Exception as e:
    print(json.dumps({{"action": "error", "error": str(e)}}))
'''
        
        try:
            # 在子进程中运行tkinter窗口，抑制所有输出
            result = subprocess.run(
                [sys.executable, '-c', subprocess_script],
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 10  # 给子进程额外时间
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
                return {"action": "error", "error": "Subprocess failed"}
                
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

# 全局常量（从core_utils迁移）
HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
HOME_FOLDER_ID = "root"  # Google Drive中My Drive的文件夹ID
REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"  # REMOTE_ROOT文件夹ID

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
    help_text = """GOOGLE_DRIVE - Google Drive access tool with GDS (Google Drive Shell)

Usage: GOOGLE_DRIVE [url] [options]

Arguments:
  url                  Custom Google Drive URL (default: https://drive.google.com/)

Options:
  -my                  Open My Drive (https://drive.google.com/drive/u/0/my-drive)
  --console-setup      Start Google Drive API setup wizard with GUI assistance
  --shell [COMMAND]    Enter interactive shell mode or execute shell command (alias: GDS)
  --upload FILE [PATH] Upload a file to Google Drive via local sync (PATH defaults to REMOTE_ROOT)
  --create-remote-shell        Create a new remote shell session
  --list-remote-shell          List all remote shell sessions
  --checkout-remote-shell ID   Switch to a specific remote shell
  --terminate-remote-shell ID  Terminate a remote shell session
  --desktop --status           Check Google Drive Desktop application status
  --desktop --shutdown         Shutdown Google Drive Desktop application
  --desktop --launch           Launch Google Drive Desktop application
  --desktop --restart          Restart Google Drive Desktop application
  --desktop --set-local-sync-dir    Set local sync directory path
  --desktop --set-global-sync-dir   Set global sync directory (Drive folder)
  --help, -h           Show this help message

GDS (Google Drive Shell) Commands:
  When using --shell or in interactive mode, the following commands are available:

  Navigation:
    pwd                         - show current directory path
    ls [path] [--detailed] [-R] - list directory contents (recursive with -R)
    cd <path>                   - change directory (supports ~, .., relative paths)

  File Operations:
    mkdir [-p] <dir>            - create directory (recursive with -p)
    rm <file>                   - remove file
    rm -rf <dir>                - remove directory recursively
    mv <source> <dest>          - move/rename file or folder
    cat <file>                  - display file contents
    read <file> [start end]     - read file content with line numbers

  Upload/Download:
    upload [--target-dir TARGET] <files...> - upload files to Google Drive (default: current directory)
    upload-folder [--keep-zip] <folder> [target] - upload folder (zip->upload->unzip->cleanup)
    download [--force] <file> [path] - download file with caching

  Text Operations:
    echo <text>                 - display text
    echo <text> > <file>        - create file with text
    grep <pattern> <file>       - search for pattern in file
    edit [--preview] [--backup] <file> '<spec>' - edit file with multi-segment replacement

  Remote Execution:
    python <file>               - execute python file remotely
    python -c '<code>'          - execute python code remotely

  Package Management:
    pip install <package>       - install Python packages
    pip list                    - list installed packages  
    pip show <package>          - show package information
    deps <package> [options]    - analyze package dependencies
      --depth=N                 - set analysis depth (default: 2)
      --analysis-type=TYPE      - use 'smart' or 'depth' analysis

  Search:
    find [path] -name [pattern] - search for files matching pattern

  Help:
    help                        - show available commands
    exit                        - exit shell mode

Advanced Features:
  - Multi-file operations: upload [[src1, dst1], [src2, dst2], ...]
  - Command chaining: cmd1 && cmd2 && cmd3
  - Path resolution: supports ~, .., relative and absolute paths
  - File caching: automatic download caching with cache management
  - Remote execution: run Python code on remote Google Drive environment

Examples:
  GOOGLE_DRIVE                                    # Open main Google Drive
  GOOGLE_DRIVE -my                                # Open My Drive folder
  GOOGLE_DRIVE https://drive.google.com/drive/my-drive  # Open specific folder
  GOOGLE_DRIVE --console-setup                    # Start API setup wizard
  GOOGLE_DRIVE --shell                            # Enter interactive shell mode
  GOOGLE_DRIVE --shell pwd                        # Show current path
  GOOGLE_DRIVE --shell ls                         # List directory contents
  GOOGLE_DRIVE --shell mkdir test                 # Create directory
  GOOGLE_DRIVE --shell cd hello                   # Change directory
  GOOGLE_DRIVE --shell rm file.txt               # Remove file
  GOOGLE_DRIVE --shell rm -rf folder              # Remove directory
  GOOGLE_DRIVE --shell upload file1.txt file2.txt    # Upload multiple files to current directory
  GOOGLE_DRIVE --shell upload --target-dir docs file.txt  # Upload file to docs directory
  GOOGLE_DRIVE --shell "ls && cd test && pwd"     # Chain commands
  GOOGLE_DRIVE --upload file.txt                 # Upload file to REMOTE_ROOT
  GOOGLE_DRIVE --upload file.txt subfolder       # Upload file to REMOTE_ROOT/subfolder
  GDS pwd                                         # Using alias (same as above)
  GOOGLE_DRIVE --create-remote-shell              # Create remote shell
  GOOGLE_DRIVE --list-remote-shell                # List remote shells
  GOOGLE_DRIVE --checkout-remote-shell abc123     # Switch to shell
  GOOGLE_DRIVE --terminate-remote-shell abc123    # Terminate shell
  GOOGLE_DRIVE --desktop --status                 # Check Desktop app status
  GOOGLE_DRIVE --desktop --shutdown               # Shutdown Desktop app
  GOOGLE_DRIVE --desktop --launch                 # Launch Desktop app
  GOOGLE_DRIVE --desktop --restart                # Restart Desktop app
  GOOGLE_DRIVE --desktop --set-local-sync-dir     # Set local sync directory
  GOOGLE_DRIVE --desktop --set-global-sync-dir    # Set global sync directory
  GOOGLE_DRIVE --setup-hf                         # Setup HuggingFace credentials on remote
  GOOGLE_DRIVE --test-hf                          # Test HuggingFace configuration on remote
  GOOGLE_DRIVE --help                             # Show help"""
    
    print(help_text)

def main():
    """主函数"""
    import sys
    
    # 从其他模块直接导入需要的函数
    try:
        from .remote_shell_manager import list_remote_shells, create_remote_shell, checkout_remote_shell, terminate_remote_shell, enter_shell_mode
        from .drive_api_service import open_google_drive
        from .sync_config_manager import set_local_sync_dir, set_global_sync_dir
    except ImportError:
        try:
            from modules.remote_shell_manager import list_remote_shells, create_remote_shell, checkout_remote_shell, terminate_remote_shell, enter_shell_mode
            from modules.drive_api_service import open_google_drive
            from modules.sync_config_manager import set_local_sync_dir, set_global_sync_dir
        except ImportError:
            # 如果导入失败，尝试从全局命名空间获取
            list_remote_shells = globals().get('list_remote_shells')
            create_remote_shell = globals().get('create_remote_shell')
            checkout_remote_shell = globals().get('checkout_remote_shell')
            terminate_remote_shell = globals().get('terminate_remote_shell')
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
        return create_remote_shell(None, None, command_identifier) if create_remote_shell else 1
    elif args[0] == '--list-remote-shell':
        return list_remote_shells(command_identifier) if list_remote_shells else 1
    elif args[0] == '--checkout-remote-shell':
        if len(args) < 2:
            print("❌ 错误: 需要指定shell ID")
            return 1
        shell_id = args[1]
        return checkout_remote_shell(shell_id, command_identifier) if checkout_remote_shell else 1
    elif args[0] == '--terminate-remote-shell':
        if len(args) < 2:
            print("❌ 错误: 需要指定shell ID")
            return 1
        shell_id = args[1]
        return terminate_remote_shell(shell_id, command_identifier) if terminate_remote_shell else 1
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
                    print("❌ GoogleDriveShell缺少execute_shell_command方法")
                    return 1
            except Exception as e:
                error_msg = f"❌ 执行shell命令时出错: {e}"
                print(error_msg)
                return 1
    elif args[0] == '--desktop':
        if len(args) < 2:
            print("❌ 错误: --desktop需要指定操作类型")
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
                        print("❌ 无法找到 get_google_drive_status 函数")
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
                        print("❌ 无法找到 shutdown_google_drive 函数")
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
                        print("❌ 无法找到 launch_google_drive 函数")
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
                        print("❌ 无法找到 restart_google_drive 函数")
                        return 1
        elif desktop_action == '--set-local-sync-dir':
            return set_local_sync_dir(command_identifier) if set_local_sync_dir else 1
        elif desktop_action == '--set-global-sync-dir':
            return set_global_sync_dir(command_identifier) if set_global_sync_dir else 1
        else:
            print(f"❌ 错误: 未知的desktop操作: {desktop_action}")
            return 1
    elif args[0] == '--upload':
        # 上传文件：GOOGLE_DRIVE --upload file_path [remote_path] 或 GOOGLE_DRIVE --upload "[[src1, dst1], [src2, dst2], ...]"
        if len(args) < 2:
            print("❌ 错误: 需要指定要上传的文件")
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
                    print(f"❌ {result.get('error', 'Upload failed')}")
            
            return 0 if result["success"] else 1
            
        except Exception as e:
            error_msg = f"❌ 执行upload命令时出错: {e}"
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