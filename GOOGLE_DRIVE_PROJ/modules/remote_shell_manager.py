#!/usr/bin/env python3
"""
Google Drive - Remote Shell Manager Module
从GOOGLE_DRIVE.py重构而来的remote_shell_manager模块
"""

import os
import json
import hashlib
import time
import uuid
import warnings
from pathlib import Path
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
from dotenv import load_dotenv
load_dotenv()



# 添加缺失的工具函数
def get_multiline_input_safe(prompt, single_line=False):
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
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"写入JSON输出文件失败: {e}")
        return False

# 全局常量
HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
HOME_FOLDER_ID = "root"  # Google Drive中My Drive的文件夹ID
REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"  # REMOTE_ROOT文件夹ID

def get_shells_file():
    """获取远程shell配置文件路径"""
    # 获取bin目录路径（从modules向上两级：modules -> GOOGLE_DRIVE_PROJ -> bin）
    bin_dir = Path(__file__).parent.parent.parent
    data_dir = bin_dir / "GOOGLE_DRIVE_DATA"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "remote_shells.json"

def load_shells():
    """加载远程shell配置"""
    shells_file = get_shells_file()
    if shells_file.exists():
        try:
            with open(shells_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"shells": {}, "active_shell": None}

def save_shells(shells_data):
    """保存远程shell配置"""
    shells_file = get_shells_file()
    try:
        with open(shells_file, 'w', encoding='utf-8') as f:
            json.dump(shells_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ 保存远程shell配置失败: {e}")
        return False

def generate_shell_id():
    """生成shell标识符"""
    # 使用时间戳和随机UUID生成哈希
    timestamp = str(int(time.time()))
    random_uuid = str(uuid.uuid4())
    combined = f"{timestamp}_{random_uuid}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def create_shell(name=None, folder_id=None, command_identifier=None):
    """创建远程shell"""
    try:
        # 生成shell ID
        shell_id = generate_shell_id()
        
        # 获取当前时间
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 如果没有提供名称，使用默认名称
        if not name:
            name = f"shell_{shell_id[:8]}"
        
        # 创建shell配置
        shell_config = {
            "id": shell_id,
            "name": name,
            "folder_id": folder_id or REMOTE_ROOT_FOLDER_ID,  # 默认使用REMOTE_ROOT作为根目录
            "current_path": "~",  # 当前逻辑路径，初始为~（指向REMOTE_ROOT）
            "current_folder_id": REMOTE_ROOT_FOLDER_ID,  # 当前所在的Google Drive文件夹ID
            "created_time": created_time,
            "last_accessed": created_time,
            "status": "active"
        }
        
        # 加载现有shells
        shells_data = load_shells()
        
        # 添加新shell
        shells_data["shells"][shell_id] = shell_config
        
        # 如果这是第一个shell，设为活跃shell
        if not shells_data["active_shell"]:
            shells_data["active_shell"] = shell_id
        
        # 保存配置
        if save_shells(shells_data):
            success_msg = f"✅ 远程shell创建成功"
            result_data = {
                "success": True,
                "message": success_msg,
                "shell_id": shell_id,
                "shell_name": name,
                "folder_id": folder_id,
                "created_time": created_time
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
                print(f"🆔 Shell ID: {shell_id}")
                print(f"📛 Shell名称: {name}")
                print(f"📁 文件夹ID: {folder_id or 'root'}")
                print(f"🕐 创建时间: {created_time}")
            return 0
        else:
            error_msg = "❌ 保存远程shell配置失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 创建远程shell时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def list_shells(command_identifier=None):
    """列出所有远程shell"""
    try:
        shells_data = load_shells()
        shells = shells_data["shells"]
        active_shell = shells_data["active_shell"]
        
        if not shells:
            no_shells_msg = "📭 没有找到远程shell"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": no_shells_msg,
                    "shells": [],
                    "count": 0,
                    "active_shell": None
                }, command_identifier)
            else:
                print(no_shells_msg)
            return 0
        
        if is_run_environment(command_identifier):
            write_to_json_output({
                "success": True,
                "message": f"找到 {len(shells)} 个远程shell",
                "shells": list(shells.values()),
                "count": len(shells),
                "active_shell": active_shell
            }, command_identifier)
        else:
            print(f"Total {len(shells)} shells:")
            for shell_id, shell_config in shells.items():
                is_active = "*" if shell_id == active_shell else " "
                print(f"{is_active} {shell_config['name']} (ID: {shell_id})")
        
        return 0
        
    except Exception as e:
        error_msg = f"Error listing remote shells: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def checkout_shell(shell_id, command_identifier=None):
    """切换到指定的远程shell"""
    try:
        # from GOOGLE_DRIVE_PROJ.google_drive_shell import GoogleDriveShell
        
        # shell = GoogleDriveShell()
        # result = shell.checkout_shell(shell_id)
        
        # if is_run_environment(command_identifier):
        #     write_to_json_output(result, command_identifier)
        # else:
        #     if result["success"]:
        #         print(result["message"])
        #         if "current_path" in result:
        #             print(f"📍 当前路径: {result['current_path']}")
        #     else:
        #         print(f"❌ {result['error']}")
        
        # return 0 if result["success"] else 1
        pass # Placeholder for actual shell checkout logic
            
    except Exception as e:
        error_msg = f"❌ 切换远程shell时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def terminate_shell(shell_id, command_identifier=None):
    """终止指定的远程shell"""
    try:
        shells_data = load_shells()
        
        if shell_id not in shells_data["shells"]:
            error_msg = f"Cannot find shell ID: {shell_id}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        shell_config = shells_data["shells"][shell_id]
        shell_name = shell_config['name']
        
        # 删除shell
        del shells_data["shells"][shell_id]
        
        # 如果删除的是活跃shell，需要选择新的活跃shell
        if shells_data["active_shell"] == shell_id:
            if shells_data["shells"]:
                # 选择最新的shell作为活跃shell
                latest_shell = max(shells_data["shells"].items(), 
                                 key=lambda x: x[1]["last_accessed"])
                shells_data["active_shell"] = latest_shell[0]
            else:
                shells_data["active_shell"] = None
        
        # 保存配置
        if save_shells(shells_data):
            result_data = {
                "success": True,
                "terminated_shell_id": shell_id,
                "terminated_shell_name": shell_name,
                "new_active_shell": shells_data["active_shell"],
                "remaining_shells": len(shells_data["shells"])
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(f"Shell ID deleted: {shell_id}")
            return 0
        else:
            error_msg = "Failed to save shell configuration"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error terminating remote shell: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def exit_shell(command_identifier=None):
    """退出当前的远程shell"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 清除活跃shell
        shells_data = load_shells()
        shells_data["active_shell"] = None
        
        if save_shells(shells_data):
            success_msg = f"✅ 已退出远程shell: {current_shell['name']}"
            result_data = {
                "success": True,
                "message": success_msg,
                "exited_shell": current_shell['name'],
                "shell_id": current_shell['id']
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
            return 0
        else:
            error_msg = "❌ 保存shell状态失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行exit-remote-shell命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def get_current_shell():
    """获取当前活跃的shell"""
    shells_data = load_shells()
    active_shell_id = shells_data.get("active_shell")
    
    if not active_shell_id or active_shell_id not in shells_data["shells"]:
        return None
    
    return shells_data["shells"][active_shell_id]

def enter_shell_mode(command_identifier=None):
    """进入交互式shell模式"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            # 如果没有活跃shell，创建一个默认的
            print("🚀 No active remote shell, creating default shell...")
            create_result = create_shell("default_shell", None, None)
            if create_result != 0:
                error_msg = "❌ Failed to create default shell"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
            current_shell = get_current_shell()
        
        if is_run_environment(command_identifier):
            # 在RUN环境下，返回shell信息
            result_data = {
                "success": True,
                "message": "Shell mode started",
                "shell_info": current_shell,
                "current_path": current_shell.get("current_path", "~"),
                "available_commands": ["pwd", "ls", "mkdir", "cd", "rm", "help", "exit"]
            }
            write_to_json_output(result_data, command_identifier)
            return 0
        else:
            # 在直接执行模式下，启动交互式shell
            print(f"🌟 Google Drive Shell (GDS) - {current_shell['name']}")
            print(f"📍 Current path: {current_shell.get('current_path', '~')}")
            print("💡 Enter 'help' to view available commands, enter 'exit' to exit")
            print()
            
            while True:
                try:
                    # 显示提示符
                    current_path = current_shell.get("current_path", "~")
                    prompt = f"GDS:{current_path}$ "
                    
                    user_input = get_multiline_input_safe(prompt, single_line=True)
                    
                    if not user_input:
                        continue
                    
                    # 解析命令
                    parts = user_input.split()
                    cmd = parts[0].lower()
                    
                    if cmd == "exit":
                        print("👋 Exit Google Drive Shell")
                        break
                    elif cmd == "pwd":
                        shell_pwd()
                    elif cmd == "ls":
                        # 使用GoogleDriveShell实例执行ls命令
                        try:
                            import sys
                            import os
                            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                            from google_drive_shell import GoogleDriveShell
                            shell_instance = GoogleDriveShell()
                            result = shell_instance.cmd_ls(path=None, detailed=False, recursive=False, show_hidden=False)
                            if result.get("success"):
                                files = result.get("files", [])
                                folders = result.get("folders", [])
                                all_items = folders + files
                                if all_items:
                                    sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                                    sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                                    all_sorted_items = sorted_folders + sorted_files
                                    for item in all_sorted_items:
                                        name = item.get('name', 'Unknown')
                                        if item.get('mimeType') == 'application/vnd.google-apps.folder':
                                            print(f"{name}/")
                                        else:
                                            print(name)
                            else:
                                print(result.get('error', 'ls command failed'))
                        except Exception as e:
                            print(f"Error executing ls command: {e}")
                    elif cmd.startswith("mkdir "):
                        path = cmd[6:].strip()
                        shell_mkdir(path)
                    elif cmd.startswith("cd "):
                        path = cmd[3:].strip()
                        # 使用GoogleDriveShell实例执行cd命令
                        try:
                            import sys
                            import os
                            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                            from google_drive_shell import GoogleDriveShell
                            shell_instance = GoogleDriveShell()
                            result = shell_instance.cmd_cd(path)
                            if result.get("success"):
                                print(result.get("message", f"Switched to directory: {result.get('new_path', path)}"))
                            else:
                                print(result.get("error", "cd command failed"))
                        except Exception as e:
                            print(f"Error executing cd command: {e}")
                    elif cmd == "cd":
                        # cd到根目录
                        try:
                            import sys
                            import os
                            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                            from google_drive_shell import GoogleDriveShell
                            shell_instance = GoogleDriveShell()
                            result = shell_instance.cmd_cd("~")
                            if result.get("success"):
                                print(result.get("message", f"Switched to directory: {result.get('new_path', '~')}"))
                            else:
                                print(result.get("error", "cd command failed"))
                        except Exception as e:
                            print(f"Error executing cd command: {e}")
                    elif cmd.startswith("rm -rf "):
                        path = cmd[7:].strip()
                        shell_rm(path, True)
                    elif cmd.startswith("rm "):
                        path = cmd[3:].strip()
                        shell_rm(path, False)
                    elif cmd == "help":
                        try:
                            from .help_system import show_unified_help
                            show_unified_help(context="shell")
                        except ImportError:
                            try:
                                from help_system import show_unified_help
                                show_unified_help(context="shell")
                            except ImportError:
                                # Fallback to basic help
                                print("📋 Available commands:")
                                print("  pwd           - Show current remote logical address")
                                print("  ls            - List current directory content")
                                print("  mkdir <dir>   - Create directory")
                                print("  cd <path>     - Switch directory")
                                print("  rm <file>     - Delete file")
                                print("  rm -rf <dir>  - Recursively delete directory")
                                print("  help          - Show help information")
                                print("  exit          - Exit shell mode")
                                print()
                    elif cmd == "read":
                        if not args:
                            result = {"success": False, "error": "Usage: read <filename> [start end] or read <filename> [[start1, end1], [start2, end2], ...]"}
                        else:
                            filename = args[0]
                            range_args = args[1:] if len(args) > 1 else []
                            result = shell.cmd_read(filename, *range_args)
                    elif cmd == "find":
                        if not args:
                            result = {"success": False, "error": "Usage: find [path] -name [pattern] or find [path] -type [f|d] -name [pattern]"}
                        else:
                            result = shell.cmd_find(*args)
                    else:
                        print(f"Unknown command: {cmd}")
                        print("💡 Enter 'help' to view available commands")
                        print()
                    
                except KeyboardInterrupt:
                    print("\n👋 Exited Google Drive Shell")
                    break
                except EOFError:
                    print("\n👋 Exited Google Drive Shell")
                    break
            
            return 0
        
    except Exception as e:
        error_msg = f"❌ Error starting shell mode: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1
