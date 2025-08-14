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
        self.debug_buffer = []
        self.capturing = True
    
    def stop_capture(self):
        """停止捕获debug信息"""
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
    
    # 如果正在捕获，只添加到缓存，不输出到控制台
    if debug_capture.capturing:
        debug_capture.add_debug(message)
        # 只显示真正的进度指示器（不是debug信息）给用户
        # 排除所有包含"DEBUG"、"检查"、"发现"等调试关键词的消息
        if (any(indicator in message for indicator in ['⏳', '✅', '❌']) 
            and not any(debug_keyword in message for debug_keyword in ['🔧 DEBUG:', '检查', '发现', '处理'])):
            print(*args, **kwargs)
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
        self.SPECIAL_COMMANDS = {
            'ls', 'cd', 'pwd', 'mkdir', 'rm', 'mv', 'cat', 'echo', 'grep', 
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
                    
                    # 生成解压命令
                    if keep_zip:
                        unzip_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 验证结果 ===" && ls -la'''
                    else:
                        unzip_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "=== 验证结果 ===" && ls -la'''
                    
                    # 将解压命令添加到基础命令之后
                    combined_command = f"{base_command}\n\n# 解压和清理zip文件\n({unzip_command}) && clear && echo \"✅ 执行完成\" || echo \"❌ 执行失败\""
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
            import sys
            import time
            
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

    def _get_multiline_user_input(self):
        """
        获取用户的多行输入，支持Ctrl+D结束
        类似USERINPUT的机制
        
        Returns:
            str: 用户输入的多行内容
        """
        try:
            import sys
            
            lines = []
            print("请输入内容 (按 Ctrl+D 结束):")
            
            try:
                while True:
                    try:
                        line = input()
                        lines.append(line)
                    except KeyboardInterrupt:
                        # Ctrl+C，询问是否取消
                        print("\n是否取消输入？(y/N): ", end="", flush=True)
                        response = input().strip().lower()
                        if response in ['y', 'yes']:
                            return ""
                        else:
                            print("继续输入 (按 Ctrl+D 结束):")
                            continue
            except EOFError:
                # Ctrl+D，正常结束输入
                pass
            
            return "\n".join(lines)
            
        except Exception as e:
            print(f"获取用户输入时出错: {e}")
            return ""

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
            check_result = self._check_remote_file_exists_absolute(remote_file_path)
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

    def _check_remote_file_exists_absolute(self, file_path):
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

    def _generate_unzip_and_delete_command(self, zip_filename, remote_target_path, keep_zip=False):
        """
        生成远程解压和删除zip文件的命令，并通过tkinter窗口提供给用户执行
        
        Args:
            zip_filename (str): zip文件名
            remote_target_path (str): 远程目标路径
            keep_zip (bool): 是否保留zip文件
            
        Returns:
            dict: 命令生成结果
        """
        try:
            print(f"📂 生成远程解压和删除命令: {zip_filename}")
            
            # 构建远程命令
            if keep_zip:
                # 保留zip文件的版本：只解压，不删除
                remote_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 验证结果 ===" && ls -la && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'''
            else:
                # 默认版本：解压后删除zip文件
                remote_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "=== 验证结果 ===" && ls -la && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'''
            
            print(f"🔧 生成的远程解压命令: {remote_command}")
            
            # 使用subprocess方法显示命令窗口
            try:
                from .core_utils import show_command_window_subprocess
                
                title = f"远程文件夹解压: {zip_filename}"
                instruction = f"""请在远程环境中执行以下命令来解压文件夹：

1. 解压zip文件到指定目录
2. 自动删除zip文件（如果设置了删除选项）
3. 验证解压结果

目标路径: {remote_target_path}
"""
                
                # 使用subprocess方法显示窗口
                result = show_command_window_subprocess(
                    title=title,
                    command_text=remote_command,
                    instruction_text=instruction,
                    timeout_seconds=300
                )
                
                # 转换结果格式
                if result["action"] == "success":
                    return {"success": True, "message": f"文件夹 {zip_filename} 解压完成"}
                elif result["action"] == "copy":
                    return {"success": True, "message": "命令已复制到剪切板，请手动执行"}
                else:
                    return {"success": False, "message": f"操作取消或失败: {result.get('error', 'Unknown error')}"}
                    
            except Exception as e:
                return {"success": False, "message": f"显示命令窗口失败: {str(e)}"}
                
        except Exception as e:
            return {"success": False, "error": f"生成远程解压命令失败: {e}"}
    
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
        """生成多文件分布式远端移动命令，每个文件独立重试60次，直到所有文件完成"""
        try:
            # 生成文件信息数组
            file_info_list = []
            for i, file_info in enumerate(all_file_moves):
                filename = file_info["filename"]  # 重命名后的文件名（在DRIVE_EQUIVALENT中）
                original_filename = file_info.get("original_filename", filename)  # 原始文件名（目标文件名）
                renamed = file_info.get("renamed", False)
                target_path = file_info["target_path"]
                
                # 计算目标绝对路径 - 使用original_filename作为最终文件名
                target_filename = original_filename  # 最终目标文件名应该是原始文件名
                
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
                elif target_path.startswith("/"):
                    # 绝对路径
                    target_absolute = f"{self.main_instance.REMOTE_ROOT}{target_path}"
                    dest_absolute = f"{target_absolute.rstrip('/')}/{target_filename}"
                else:
                    # 相对路径，需要判断是文件名还是目录名
                    last_part = target_path.split('/')[-1]
                    is_file = '.' in last_part and last_part != '.' and last_part != '..'
                    
                    # 获取当前路径信息
                    current_shell = self.main_instance.get_current_shell()
                    current_path = current_shell.get("current_path", "~") if current_shell else "~"
                    
                    if is_file:
                        # target_path 是文件名，直接使用
                        if target_path.startswith("~/"):
                            # target_path是绝对路径（从~开始），直接使用
                            dest_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path[2:]}"
                            debug_print(f"🔧 DEBUG: target_path starts with '~/', dest_absolute='{dest_absolute}'")
                        elif current_path == "~":
                            dest_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path}"
                            debug_print(f"🔧 DEBUG: current_path is '~', dest_absolute='{dest_absolute}'")
                        else:
                            # current_path不是~，需要包含当前路径
                            if current_path.startswith("~/"):
                                # 去掉~/前缀，添加当前路径
                                current_subpath = current_path[2:]  # 去掉~/
                                dest_absolute = f"{self.main_instance.REMOTE_ROOT}/{current_subpath}/{target_path}"
                            else:
                                # 不应该发生，但作为fallback
                                dest_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path}"
                            debug_print(f"🔧 DEBUG: current_path is '{current_path}', dest_absolute='{dest_absolute}'")
                    else:
                        # target_path 是目录名，需要包含当前路径，在后面添加原始文件名
                        if current_path == "~":
                            target_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path.lstrip('/')}"
                        else:
                            # 包含当前路径
                            current_subpath = current_path[2:] if current_path.startswith("~/") else current_path
                            target_absolute = f"{self.main_instance.REMOTE_ROOT}/{current_subpath}/{target_path.lstrip('/')}"
                        
                        dest_absolute = f"{target_absolute.rstrip('/')}/{target_filename}"
                
                # 源文件路径使用重命名后的文件名
                source_absolute = f"{self.main_instance.DRIVE_EQUIVALENT}/{filename}"
                
                debug_print(f"🔧 DEBUG: File {i}: filename='{filename}', original_filename='{original_filename}', renamed={renamed}")
                debug_print(f"🔧 DEBUG: File {i}: source_absolute='{source_absolute}', dest_absolute='{dest_absolute}'")
                
                file_info_list.append({
                    'filename': filename,  # 源文件名（重命名后）
                    'original_filename': original_filename,  # 目标文件名（原始）
                    'renamed': renamed,
                    'source': source_absolute,
                    'dest': dest_absolute,
                    'index': i
                })
            
            # 收集所有需要创建的目录
            target_dirs = set()
            for file_info in file_info_list:
                dest_dir = '/'.join(file_info['dest'].split('/')[:-1])  # 获取目标目录路径
                target_dirs.add(dest_dir)
            
            # 生成分布式移动脚本
            full_command = f'''
# 初始化完成状态数组
declare -a completed
total_files={len(file_info_list)}
completed_count=0

# 确保所有目标目录存在
'''
            
            for target_dir in sorted(target_dirs):
                full_command += f'mkdir -p "{target_dir}"\n'
            
            # 生成文件名列表用于显示
            if len(file_info_list) <= 3:
                file_display = ", ".join([f['original_filename'] for f in file_info_list])
            else:
                first_three = ", ".join([f['original_filename'] for f in file_info_list[:3]])
                file_display = f"{first_three}, ... ({len(file_info_list)} files)"
            
            full_command += f'''
# 显示统一的上传进度
echo -n "⏳ Uploading {file_display}: "

# 按顺序处理每个文件（序列化）
'''
            
            for file_info in file_info_list:
                full_command += f'''
# 处理文件 {file_info['index'] + 1}/{len(file_info_list)}: {file_info['original_filename']}
for attempt in {{1..60}}; do
    if mv "{file_info['source']}" "{file_info['dest']}" 2>/dev/null; then
        echo -n "√"
        completed[{file_info['index']}]=1
        break
    else
        if [ $attempt -eq 60 ]; then
            echo -n "✗"
            completed[{file_info['index']}]=0
            break
        else
            echo -n "."
            sleep 1
        fi
    fi
done
'''
            
            # 检查结果（序列化执行，无需等待）
            full_command += f'''

# 简化结果统计 - 检查目标文件是否存在
success_count=0
fail_count=0
'''
            
            # 为每个文件生成检查命令
            for file_info in file_info_list:
                full_command += f'''
if [ -f "{file_info['dest']}" ]; then
    ((success_count++))
else
    ((fail_count++))
fi
'''
            
            full_command += f'''
# 输出最终结果
total_files={len(file_info_list)}
if [ $fail_count -eq 0 ]; then
    echo " ✅"
    clear && echo "✅ 执行完成"
else
    echo " ❌"
    echo "Partially completed: $success_count/$total_files success, $fail_count failed"
fi
'''
            
            return full_command
            
        except Exception as e:
            return f"echo '❌ 生成多文件命令失败: {e}'"
    
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
                debug_print(f"🔧 DEBUG: Validating file {i+1}/{len(expected_files)}: {expected_file}")
                file_found = False
                
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
                        debug_print(f"🔧 DEBUG: File {expected_file} found on attempt {attempt}")
                        break
                    elif attempt == 60:
                        print("✗", end="", flush=True)
                        missing_files.append(expected_file)
                        debug_print(f"🔧 DEBUG: File {expected_file} not found after 60 attempts")
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
            debug_print(f"🔧 DEBUG: Validation error: {e}")
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
    for attempt in {{1..60}}; do
        if mv {file_info['source_path']} {file_info['dest_path']} 2>/dev/null; then
            echo "✅"
            completed[{file_info['index']}]=1
            break
        else
            if [ $attempt -eq 60 ]; then
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
if [ $fail_count -eq 0 ]; then
    clear && echo "✅ 执行完成"
else
    echo "⚠️  部分文件移动完成: $success_count/$total_files 成功, $fail_count 失败"
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
            mkdir_command = f'mkdir -p "{full_target_path}" && clear && echo "✅ 执行完成" || echo "❌ 执行失败"'
            
            return mkdir_command
            
        except Exception as e:
            print(f"❌ 生成mkdir命令时出错: {e}")
            return ""

    def execute_remote_command_interface(self, remote_command, command_type="upload", context_info=None):
        """
        统一的远端命令执行接口
        
        Args:
            remote_command (str): 要执行的远端命令
            command_type (str): 命令类型 ("upload", "mkdir", "move", etc.)
            context_info (dict): 上下文信息，包含文件名、路径等
            
        Returns:
            dict: 执行结果
        """
        try:
            # 显示远端命令（用于调试和协作） - 根据用户要求移除自动显示
            # print(f"   {remote_command}")
            
            # 显示tkinter窗口获取用户确认
            debug_info = debug_capture.get_debug_info()
            window_result = self.show_remote_command_window(remote_command, command_type, debug_info)
            # os.system("clear") if os.name == "posix" else os.system("cls")  # 注释掉清屏，保留调试信息
            
            # 统一处理用户确认结果
            if window_result["action"] == "cancel":
                return {
                    "success": False,
                    "cancelled": True,
                    "message": "Operation cancelled. "
                }
            elif window_result["action"] == "error":
                return {
                    "success": False,
                    "window_error": True,
                    "error_info": window_result.get('error_info'),
                    "message": f"Window error: {window_result.get('error_info', 'Unknown error')}"
                }
            elif window_result["action"] == "success":
                # 根据命令类型进行相应的后处理
                return self._handle_successful_remote_execution(command_type, context_info)
            elif window_result["action"] == "direct_feedback":
                # 调用相应的后处理逻辑（包括validation）
                result = self._handle_successful_remote_execution(command_type, context_info)
                
                # 添加direct feedback的额外信息
                result.update({
                    "user_confirmed": True,
                    "exit_code": window_result.get("exit_code", 0),
                    "stdout": window_result.get("stdout", ""),
                    "stderr": window_result.get("stderr", ""),
                    "source": "direct_feedback"
                })
                
                return result
            else:
                return {
                    "success": False,
                    "unknown_action": True,
                    "message": f"Unknown user action: {window_result.get('action')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "interface_error": True,
                "error": str(e),
                "message": f"Remote command interface error: {e}"
            }

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
            print("⏳ Validating file creation", end="", flush=True)
            
            max_attempts = 60
            for attempt in range(max_attempts):
                try:
                    # 检查文件是否存在
                    check_result = self._check_remote_file_exists_absolute(absolute_path)
                    
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
                debug_print(f"🔧 DEBUG: target_folder_id is None, re-resolving target_path='{target_path}' after remote execution")
                current_shell = self.main_instance.get_current_shell()
                if current_shell:
                    # 尝试重新解析目标路径（目录现在应该存在了）
                    resolved_folder_id, resolved_display_path = self.main_instance.resolve_path(target_path, current_shell)
                    if resolved_folder_id:
                        target_folder_id = resolved_folder_id
                        debug_print(f"🔧 DEBUG: re-resolved target_folder_id='{target_folder_id}', display_path='{resolved_display_path}'")
                    else:
                        debug_print(f"🔧 DEBUG: failed to re-resolve target_path='{target_path}', will use parent folder for validation")
                        # 如果重新解析失败，使用父目录作为fallback
                        target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                        debug_print(f"🔧 DEBUG: using parent folder_id='{target_folder_id}' as fallback")
            
            # 如果有验证信息，进行文件验证
            debug_print(f"🔧 DEBUG: Validation check - expected_filenames={expected_filenames}, target_path='{target_path}'")
            if expected_filenames and target_path is not None:
                debug_print(f"🔧 DEBUG: Starting ls-based validation with {len(expected_filenames)} files")
                current_shell = self.main_instance.get_current_shell()
                
                # 使用带进度显示的验证逻辑，类似上传过程
                validation_result = self._verify_upload_with_progress(
                    expected_files=expected_filenames,
                    target_path=target_path,
                    current_shell=current_shell
                )
                
                debug_print(f"🔧 DEBUG: Validation completed - validation_result={validation_result}")
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
                    debug_print(f"🔧 DEBUG: Skipping validation for folder upload - trusting remote command execution")
                    return {
                        "success": True,
                        "user_confirmed": True,
                        "command_type": "upload",
                        "message": "Folder upload and extraction completed successfully"
                    }
                else:
                    debug_print(f"🔧 DEBUG: Skipping validation - expected_filenames={expected_filenames}, target_path='{target_path}'")
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
                    check_result = self._check_remote_file_exists_absolute(absolute_path)
                    
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
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"执行远端命令时出错: {str(e)}"
            }

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
                    # 其他命令直接拼接
                    full_command = f"{cmd} {' '.join(args)}"
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
                    # 对于bash/sh -c命令，正确处理脚本内容
                    script_content = args[1]
                    # 转义脚本内容中的双引号和反斜杠
                    escaped_script = script_content.replace('\\', '\\\\').replace('"', '\\"')
                    bash_safe_command = f'{cmd} -c "{escaped_script}"'
                else:
                    # 分别转义命令和每个参数
                    escaped_cmd = shlex.quote(cmd)
                    escaped_args = [shlex.quote(arg) for arg in args]
                    bash_safe_command = f"{escaped_cmd} {' '.join(escaped_args)}"
            else:
                bash_safe_command = shlex.quote(cmd)
            
            # 为echo显示创建安全版本，避免特殊字符破坏bash语法
            display_command = self._escape_for_display(full_command)
            
            remote_command = (
                f'cd "{remote_path}" && {{\n'
                f'    # 确保tmp目录存在\n'
                f'    mkdir -p "{self.main_instance.REMOTE_ROOT}/tmp"\n'
                f'    \n'
                f'    echo "🚀 开始执行命令: {display_command}"\n'
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

                f'    # 设置环境变量并生成JSON结果文件\n'
                f'    export EXIT_CODE=$EXIT_CODE\n'
                f'    python3 << \'EOF\' > "{result_path}"\n'
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
                f'EOF\n'
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
            window_result = self._show_generic_command_window(cmd, args, remote_command, debug_info)
            
            if window_result.get("action") == "direct_feedback":
                # 处理直接反馈，保持direct_feedback action类型，跳过验证
                data = window_result.get("data", {})
                exit_code = data.get("exit_code", 0)
                print () # an empty line
                return {
                    "success": exit_code == 0, 
                    "action": "direct_feedback", 
                    "exit_code": exit_code,
                    "stdout": data.get("stdout", ""),
                    "stderr": data.get("stderr", ""),
                    "source": "direct_feedback"
                }
            elif window_result.get("action") != "success":
                return {
                    "success": False,
                    "error": f"User operation: {'Cancelled' if window_result.get('action', 'unknown') == 'error' else window_result.get('action', 'unknown')}",
                    "user_feedback": window_result
                }
            
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
            from .core_utils import show_command_window_subprocess
            
            title = f"GDS Remote Command: {cmd}"
            instruction = f"Command: {cmd} {' '.join(args)}\n\nPlease execute the following command in your remote environment:"
            
            # 使用subprocess方法显示窗口
            result = show_command_window_subprocess(
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
                try:
                    feedback_result = self.direct_feedback(remote_command, debug_info)
                    return {
                        "success": feedback_result.get("success", False),
                        "action": "direct_feedback",
                        "data": feedback_result.get("data", {}),
                        "source": "direct_feedback"
                    }
                except Exception as e:
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
        基于用户提供的原始逻辑
        """
        # 先输出debug信息（如果有的话）
        if debug_info:
            print("Debug information:")
            print(debug_info)
            print("=" * 20)  # 20个等号分割线
        
        # 然后粘贴生成的远端指令
        print("Generated remote command:")
        print(remote_command)
        print("=" * 20)  # 20个等号分割线
        
        # 使用命令行输入获取用户反馈
        print("Please provide command execution result (multi-line input, press Ctrl+D to finish):")
        print()
        
        # 采用和USERINPUT相同的输入流捕获机制
        import signal
        import readline
        
        # 确保readline正确配置以支持中文全角字符
        try:
            # 设置readline配置以支持中文字符
            readline.set_startup_hook(None)
            # 启用历史记录
            readline.clear_history()
            
            # 设置编辑模式为emacs（支持更好的中文编辑）
            readline.parse_and_bind("set editing-mode emacs")
            
            # 启用UTF-8和中文字符支持
            readline.parse_and_bind("set input-meta on")
            readline.parse_and_bind("set output-meta on")
            readline.parse_and_bind("set convert-meta off")
            
            # 支持中文字符的字符宽度计算
            readline.parse_and_bind("set enable-meta-key on")
            readline.parse_and_bind("set meta-flag on")
            
            # 设置字符编码
            readline.parse_and_bind("set completion-display-width -1")
            
            # 处理中文字符的删除行为 - 按字符而不是字节删除
            readline.parse_and_bind("set bind-tty-special-chars off")
            
            # 设置中文字符的显示宽度处理
            import locale
            try:
                locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
            except:
                try:
                    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                except:
                    pass  # 如果设置locale失败，继续使用默认
                    
        except Exception:
            pass  # 如果配置失败，继续使用默认设置
        
        lines = []
        timeout_seconds = 180  # 3分钟超时，和USERINPUT一致
        
        class TimeoutException(Exception):
            pass
        
        def timeout_handler(signum, frame):
            raise TimeoutException("Input timeout")
        
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
                    # Ctrl+D 被按下，结束输入
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
            print("\nUser cancelled input")
            lines = []
        finally:
            # 清理超时设置
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
        
        # 组合所有行为最终输入
        full_output = '\n'.join(lines).strip()
        
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
