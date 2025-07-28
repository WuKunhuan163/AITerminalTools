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
from ..google_drive_api import GoogleDriveService

class RemoteCommands:
    """Google Drive Shell Remote Commands"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

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
                remote_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 验证结果 ===" && ls -la && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'''
            else:
                # 默认版本：解压后删除zip文件
                remote_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "=== 验证结果 ===" && ls -la && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'''
            
            print(f"🔧 生成的远程解压命令: {remote_command}")
            
            # 使用tkinter窗口显示命令并等待用户反馈
            try:
                import tkinter as tk
                from tkinter import messagebox, scrolledtext
                import threading
                import queue
                
                # 创建结果队列
                result_queue = queue.Queue()
                
                def show_command_window():
                    """显示远程解压命令窗口"""
                    root = tk.Tk()
                    root.title("远程文件夹解压命令 - Google Drive")
                    root.geometry("800x600")
                    
                    # 标题
                    title_label = tk.Label(root, text=f"远程文件夹解压: {zip_filename}", 
                                         font=("Arial", 14, "bold"))
                    title_label.pack(pady=10)
                    
                    # 说明文字
                    action_text = "解压并删除zip文件" if not keep_zip else "解压但保留zip文件"
                    instruction_text = f"""
请在远程终端执行以下命令来完成文件夹解压：

操作: {action_text}
目标路径: {remote_target_path}

1. 复制下面的命令到剪切板
2. 在远程终端粘贴并执行
3. 根据执行结果选择相应按钮
"""
                    instruction_label = tk.Label(root, text=instruction_text, 
                                               justify=tk.LEFT, wraplength=750)
                    instruction_label.pack(pady=10)
                    
                    # 命令文本框
                    command_frame = tk.Frame(root)
                    command_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
                    
                    command_text = scrolledtext.ScrolledText(command_frame, height=8, 
                                                           font=("Consolas", 10))
                    command_text.pack(fill=tk.BOTH, expand=True)
                    command_text.insert(tk.END, remote_command)
                    command_text.config(state=tk.DISABLED)
                    
                    # 复制按钮
                    def copy_command():
                        root.clipboard_clear()
                        root.clipboard_append(remote_command)
                        messagebox.showinfo("已复制", "命令已复制到剪切板")
                    
                    copy_btn = tk.Button(root, text="📋 复制命令到剪切板", 
                                       command=copy_command, font=("Arial", 12))
                    copy_btn.pack(pady=10)
                    
                    # 结果按钮框架
                    result_frame = tk.Frame(root)
                    result_frame.pack(pady=20)
                    
                    # 结果按钮
                    def on_success():
                        result_queue.put({"success": True, "message": "用户确认解压成功"})
                        root.destroy()
                    
                    def on_failure():
                        result_queue.put({"success": False, "error": "用户报告解压失败"})
                        root.destroy()
                    
                    def on_cancel():
                        result_queue.put({"success": False, "error": "用户取消操作"})
                        root.destroy()
                    
                    success_btn = tk.Button(result_frame, text="✅ 执行成功", 
                                          command=on_success, bg="lightgreen",
                                          font=("Arial", 12), width=12)
                    success_btn.pack(side=tk.LEFT, padx=10)
                    
                    failure_btn = tk.Button(result_frame, text="❌ 执行失败", 
                                          command=on_failure, bg="lightcoral",
                                          font=("Arial", 12), width=12)
                    failure_btn.pack(side=tk.LEFT, padx=10)
                    
                    cancel_btn = tk.Button(result_frame, text="🚫 取消操作", 
                                         command=on_cancel, bg="lightgray",
                                         font=("Arial", 12), width=12)
                    cancel_btn.pack(side=tk.LEFT, padx=10)
                    
                    # 居中显示窗口
                    root.update_idletasks()
                    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
                    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
                    root.geometry(f"+{x}+{y}")
                    
                    root.mainloop()
                
                # 在单独线程中显示窗口
                window_thread = threading.Thread(target=show_command_window)
                window_thread.start()
                window_thread.join()
                
                # 获取用户反馈结果
                try:
                    user_result = result_queue.get_nowait()
                    if user_result["success"]:
                        return {
                            "success": True,
                            "message": f"成功解压 {zip_filename}",
                            "zip_deleted": not keep_zip,
                            "method": "manual_execution",
                            "command": remote_command
                        }
                    else:
                        return {
                            "success": False,
                            "error": user_result["error"],
                            "method": "manual_execution",
                            "command": remote_command
                        }
                except queue.Empty:
                    return {
                        "success": False,
                        "error": "用户未提供反馈",
                        "method": "manual_execution",
                        "command": remote_command
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"显示命令窗口失败: {e}",
                    "command": remote_command
                }
                
        except Exception as e:
            return {"success": False, "error": f"生成远程解压命令失败: {e}"}
    
    def show_remote_command_window(self, remote_command, command_type="upload"):
        """
        显示远端命令的 tkinter 窗口（简化版本，只有按钮）
        
        Args:
            remote_command (str): 要显示的远端命令
            command_type (str): 命令类型，用于设置窗口标题
            
        Returns:
            dict: 包含用户选择和可能的错误信息的字典
        """
        try:
            import tkinter as tk
            from tkinter import messagebox
            import webbrowser
            
            result = {"success": False, "action": None, "error_info": None}
            
            # 创建窗口
            root = tk.Tk()
            window_title = f"Google Drive - {command_type} Command"
            root.title(window_title)
            root.geometry("500x60")
            root.resizable(False, False)
            
            # 居中窗口
            root.eval('tk::PlaceWindow . center')
            
            # 设置窗口置顶
            root.attributes('-topmost', True)
            
            # 主框架
            main_frame = tk.Frame(root, padx=10, pady=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 按钮框架
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, expand=True)
            
            def copy_command():
                try:
                    root.clipboard_clear()
                    root.clipboard_append(remote_command)
                    copy_btn.config(text="✅ 已复制", bg="#4CAF50")
                    root.after(1500, lambda: copy_btn.config(text="📋 复制命令", bg="#2196F3"))
                except Exception as e:
                    print(f"复制到剪贴板失败: {e}")
            
            def execution_success():
                result["success"] = True
                result["action"] = "success"
                root.destroy()
            
            def execution_failed():
                result["success"] = False
                result["action"] = "failed"
                root.destroy()
            
            # 复制命令按钮
            copy_btn = tk.Button(
                button_frame, 
                text="📋 复制命令", 
                command=copy_command,
                font=("Arial", 10),
                bg="#2196F3",
                fg="white",
                padx=15,
                pady=5,
                relief=tk.RAISED,
                bd=2
            )
            copy_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
            
            # 执行成功按钮
            success_btn = tk.Button(
                button_frame, 
                text="✅ 执行成功", 
                command=execution_success,
                font=("Arial", 10, "bold"),
                bg="#4CAF50",
                fg="white",
                padx=15,
                pady=5,
                relief=tk.RAISED,
                bd=2
            )
            success_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
            
            # 执行失败按钮
            failed_btn = tk.Button(
                button_frame, 
                text="❌ 执行失败", 
                command=execution_failed,
                font=("Arial", 10),
                bg="#f44336",
                fg="white",
                padx=15,
                pady=5,
                relief=tk.RAISED,
                bd=2
            )
            failed_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 只自动复制到剪贴板，不再自动打开Drive链接
            copy_command()
            
            # 运行窗口
            root.mainloop()
            
            # 如果用户选择了执行失败，进行交互式错误收集
            if result["action"] == "failed":
                print("\n" + "=" * 60)
                print("🚨 远端命令执行失败")
                print("=" * 60)
                print(f"命令: {remote_command}")
                print()
                
                try:
                    error_description = get_multiline_input_safe("请描述失败的原因或错误信息: ", single_line=False)
                    if error_description:
                        result["error_info"] = error_description
                        print(f"✅ 已记录错误信息: {error_description}")
                    else:
                        result["error_info"] = "用户未提供具体错误信息"
                        print("⚠️ 未提供具体错误信息")
                except KeyboardInterrupt:
                    print("\n❌ 错误信息收集已取消")
                    result["error_info"] = "用户取消了错误信息输入"
                print("=" * 60)
            
            return result
            
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
                    user_choice = get_multiline_input_safe("命令执行结果 [s=成功/f=失败/c=取消]: ", single_line=True)
                    if user_choice is None:
                        return {"success": False, "action": "cancelled", "error_info": "用户取消操作"}
                    user_choice = user_choice.lower()
                    if user_choice in ['s', 'success', '成功']:
                        return {"success": True, "action": "success", "error_info": None}
                    elif user_choice in ['f', 'failed', '失败']:
                        error_info = get_multiline_input_safe("请描述失败的原因: ", single_line=False)
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
                filename = file_info["filename"]
                target_path = file_info["target_path"]
                
                # 计算目标绝对路径
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
                    dest_absolute = f"{target_absolute.rstrip('/')}/{filename}"
                elif target_path.startswith("/"):
                    # 绝对路径
                    target_absolute = f"{self.main_instance.REMOTE_ROOT}{target_path}"
                    dest_absolute = f"{target_absolute.rstrip('/')}/{filename}"
                else:
                    # 相对路径，需要判断是文件名还是目录名
                    last_part = target_path.split('/')[-1]
                    is_file = '.' in last_part and last_part != '.' and last_part != '..'
                    
                    if is_file:
                        # target_path 是文件名，直接使用
                        current_shell = self.main_instance.get_current_shell()
                        current_path = current_shell.get("current_path", "~") if current_shell else "~"
                        if current_path == "~":
                            dest_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path}"
                        else:
                            dest_absolute = f"{self.main_instance.REMOTE_ROOT}/{current_path[2:]}/{target_path}" if current_path.startswith("~/") else f"{self.main_instance.REMOTE_ROOT}/{target_path}"
                    else:
                        # target_path 是目录名，在后面添加文件名
                        target_absolute = f"{self.main_instance.REMOTE_ROOT}/{target_path.lstrip('/')}"
                        dest_absolute = f"{target_absolute.rstrip('/')}/{filename}"
                
                source_absolute = f"{self.main_instance.DRIVE_EQUIVALENT}/{filename}"
                
                file_info_list.append({
                    'filename': filename,
                    'source': source_absolute,
                    'dest': dest_absolute,
                    'index': i
                })
            
            # 生成分布式移动脚本
            full_command = f'''
# 初始化完成状态数组
declare -a completed
total_files={len(file_info_list)}
completed_count=0

# 为每个文件启动独立的移动进程
'''
            
            for file_info in file_info_list:
                full_command += f'''
(
    echo -n "⏳ {file_info['filename']}: "
    for attempt in {{1..60}}; do
        if mv "{file_info['source']}" "{file_info['dest']}" 2>/dev/null; then
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
    clear && echo "✅ 执行成功"
else
    echo "⚠️  部分文件处理完成: $success_count/$total_files 成功, $fail_count 失败"
fi
'''
            
            return full_command
            
        except Exception as e:
            return f"echo '❌ 生成多文件命令失败: {e}'"

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
    echo -n "⏳ {file_info['source_name']} -> {file_info['dest_name']}: "
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
    clear && echo "✅ 执行成功"
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
            mkdir_command = f'mkdir -p "{full_target_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
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
            # 显示远端命令（用于调试和协作）
            print(f"   {remote_command}")
            
            # 显示tkinter窗口获取用户确认
            window_result = self.show_remote_command_window(remote_command, command_type)
            os.system("clear") if os.name == "posix" else os.system("cls")
            
            # 统一处理用户确认结果
            if window_result["action"] == "cancel":
                return {
                    "success": False,
                    "cancelled": True,
                    "message": "Operation cancelled. "
                }
            elif window_result["action"] == "failed":
                return {
                    "success": False,
                    "user_reported_failure": True,
                    "error_info": window_result.get('error_info'),
                    "message": "User reported failure: " + window_result.get('error_info')
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
            elif command_type == "move":
                return self._handle_move_success(context_info)
            else:
                # 通用成功处理
                return {
                    "success": True,
                    "user_confirmed": True,
                    "command_type": command_type,
                    "message": "远端命令执行成功"
                }
                
        except Exception as e:
            return {
                "success": False,
                "post_processing_error": True,
                "error": str(e),
                "message": f"成功后处理错误: {e}"
            }

    def execute_generic_remote_command(self, cmd, args, return_command_only=False):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            return_command_only (bool): 如果为True，只返回生成的命令而不执行
            
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
            
            # 如果只需要返回命令，进行语法检查并返回
            if return_command_only:
                # 验证bash语法
                syntax_check = self.validate_bash_syntax_fast(remote_command)
                
                return {
                    "success": True,
                    "cmd": cmd,
                    "args": args,
                    "remote_command": remote_command,
                    "result_filename": result_filename,
                    "syntax_valid": syntax_check["success"],
                    "syntax_error": syntax_check.get("error") if not syntax_check["success"] else None,
                    "action": "return_command_only"
                }
            
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
                # 直接重建完整命令，不进行预转义
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
                    # 使用双引号包围python代码，并转义内部的双引号和反斜杠
                    escaped_python_code = python_code.replace('\\', '\\\\').replace('"', '\\"')
                    bash_safe_command = f'python -c "{escaped_python_code}"'
                    # 对于python -c命令，也需要更新显示命令
                    full_command = bash_safe_command
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
            window_result = self._show_generic_command_window(remote_command, cmd, args)
            
            if window_result.get("action") == "direct_feedback":
                # 用户选择了直接反馈，直接返回用户提供的数据
                user_data = window_result.get("data", {})
                return {
                    "success": True,
                    "cmd": cmd,
                    "args": args,
                    "exit_code": user_data.get("exit_code", 0),
                    "stdout": user_data.get("stdout", ""),
                    "stderr": user_data.get("stderr", ""),
                    "working_dir": user_data.get("working_dir", "user_provided"),
                    "timestamp": user_data.get("timestamp", "user_provided"),
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

    def _show_generic_command_window(self, remote_command, cmd, args):
        """
        显示简化的命令执行窗口
        
        Args:
            remote_command (str): 远端命令
            cmd (str): 原始命令名
            args (list): 原始命令参数
            
        Returns:
            dict: 用户操作结果
        """
        try:
            import tkinter as tk
            from tkinter import messagebox
            import queue
            
            result_queue = queue.Queue()
            
            def show_command_window():
                root = tk.Tk()
                root.title("Google Drive Shell")
                root.geometry("400x60")
                root.resizable(False, False)
                
                # 居中窗口
                root.eval('tk::PlaceWindow . center')
                
                # 设置窗口置顶
                root.attributes('-topmost', True)
                
                # 自动复制命令到剪切板
                root.clipboard_clear()
                root.clipboard_append(remote_command)
                
                # 主框架
                main_frame = tk.Frame(root, padx=10, pady=10)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # 按钮框架
                button_frame = tk.Frame(main_frame)
                button_frame.pack(fill=tk.X, expand=True)
                
                def copy_command():
                    try:
                        # 使用更可靠的复制方法 - 一次性复制完整命令
                        root.clipboard_clear()
                        root.clipboard_append(remote_command)
                        
                        # 验证复制是否成功
                        try:
                            clipboard_content = root.clipboard_get()
                            if clipboard_content == remote_command:
                                copy_btn.config(text="✅ 复制成功", bg="#4CAF50")
                            else:
                                # 复制不完整，重试一次
                                root.clipboard_clear()
                                root.clipboard_append(remote_command)
                                copy_btn.config(text="⚠️ 已重试", bg="#FF9800")
                                print(f"复制验证: 原始{len(remote_command)}字符，剪切板{len(clipboard_content)}字符")
                        except Exception as verify_error:
                            # 验证失败但复制可能成功，显示已复制
                            copy_btn.config(text="✅ 已复制", bg="#4CAF50")
                            print(f"复制验证失败但命令已复制: {verify_error}")
                        
                        root.after(1500, lambda: copy_btn.config(text="📋 复制指令", bg="#2196F3"))
                    except Exception as e:
                        print(f"复制到剪贴板失败: {e}")
                        copy_btn.config(text="❌ 复制失败", bg="#f44336")
                
                def execution_completed():
                    result_queue.put({"action": "success", "message": "用户确认执行完成"})
                    root.destroy()
                
                def direct_feedback():
                    """直接反馈功能 - 使用命令行输入让用户提供命令执行结果"""
                    # 关闭主窗口
                    root.destroy()
                    
                    # 使用命令行输入获取用户反馈
                    print(f"命令: {cmd} {' '.join(args)}")
                    print("请提供命令执行结果 (多行输入，按 Ctrl+D 结束):")
                    print()
                    
                    # 获取统一的命令输出
                    try:
                        output_lines = []
                        while True:
                            try:
                                line = input()
                                output_lines.append(line)
                            except EOFError:
                                break
                        full_output = '\n'.join(output_lines)
                    except KeyboardInterrupt:
                        print("\n用户取消输入")
                        full_output = ""
                    
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
                        "action": "direct_feedback",
                        "data": {
                            "cmd": cmd,
                            "args": args,
                            "working_dir": "user_provided",
                            "timestamp": "user_provided", 
                            "exit_code": exit_code,
                            "stdout": stdout_content,
                            "stderr": stderr_content,
                            "source": "direct_feedback"
                        }
                    }
                    result_queue.put(feedback_result)
                
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
                
                # 直接反馈按钮
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
                
                # 执行完成按钮
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
                
                # 自动复制命令到剪贴板
                copy_command()
                
                root.mainloop()
            
            # 直接在主线程中显示窗口，避免tkinter线程问题
            show_command_window()
            
            # 获取结果
            try:
                return result_queue.get_nowait()
            except queue.Empty:
                return {"action": "error", "error_info": "窗口关闭但未获取到用户操作"}
                
        except Exception as e:
            return {"action": "error", "error_info": f"显示命令窗口失败: {str(e)}"}

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
