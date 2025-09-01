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

# 导入shell命令函数
try:
    from .shell_commands import shell_pwd, shell_rm
except ImportError:
    try:
        from shell_commands import shell_pwd, shell_rm
    except ImportError:
        # 如果导入失败，定义简单的fallback函数
        def shell_pwd():
            print("~/")
        def shell_rm(path, recursive=False):
            print(f"rm: {path}")

# 定义缺失的shell命令函数
def shell_mkdir(path):
    """创建目录的简化实现"""
    try:
        # 使用GoogleDriveShell实例执行mkdir命令
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from google_drive_shell import GoogleDriveShell
        
        shell = GoogleDriveShell()
        result = shell.cmd_mkdir(path)
        if not result.get("success", False):
            print(result.get("error", f"Failed to create directory: {path}"))
    except Exception as e:
        print(f"mkdir: {path}: {e}")


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
        
        if single_line:
            # 单行输入 - 使用input(prompt)确保提示符不被删除键影响
            try:
                return input(prompt)
            except EOFError:
                return None
        else:
            # 多行输入，直到Ctrl+D
            lines = []
            print(f"{prompt}(多行输入，按 Ctrl+D 结束):")
            try:
                while True:
                    line = input("  ")  # 使用缩进提示符
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
    """获取远程shell配置文件路径 - 与GoogleDriveShell保持一致"""
    # 获取bin目录路径（从modules向上两级：modules -> GOOGLE_DRIVE_PROJ -> bin）
    bin_dir = Path(__file__).parent.parent.parent
    data_dir = bin_dir / "GOOGLE_DRIVE_DATA"
    data_dir.mkdir(exist_ok=True)
    # 使用与GoogleDriveShell相同的文件名
    return data_dir / "shells.json"

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
        print(f"Warning: Save remote shell config failed: {e}")
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
        
        # 改进的shell配置，简化结构并添加虚拟环境支持
        shell_config = {
            "id": shell_id,
            "name": name,
            "current_path": "~",  # 当前逻辑路径
            "current_folder_id": REMOTE_ROOT_FOLDER_ID,  # 当前所在的Google Drive文件夹ID
            "created_time": created_time,
            "last_accessed": created_time,
            "venv_state": {
                "active_env": None,  # 当前激活的虚拟环境名称
                "pythonpath": "/env/python"  # 当前PYTHONPATH
            }
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
            success_msg = f"Remote shell created successfully"
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
                print(f"📛 Shell name: {name}")
                print(f"Folder ID: {folder_id or 'root'}")
                print(f"🕐 Created time: {created_time}")
            return 0
        else:
            error_msg = "❌ Save remote shell config failed"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ Create remote shell failed: {e}"
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
            no_shells_msg = "📭 No remote shells found"
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
                "message": f"Found {len(shells)} remote shells",
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
        #         print(f"Error: {result['error']}")
        
        # return 0 if result["success"] else 1
        pass # Placeholder for actual shell checkout logic
            
    except Exception as e:
        error_msg = f"❌ Switch remote shell failed: {e} (shell_id: {shell_id})"
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
            error_msg = "❌ No active remote shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 清除活跃shell
        shells_data = load_shells()
        shells_data["active_shell"] = None
        
        if save_shells(shells_data):
            success_msg = f"Exited remote shell: {current_shell['name']}"
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
            error_msg = "❌ Save shell state failed"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ Execute exit-remote-shell command failed: {e}"
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

def _detect_active_venv():
    """使用统一的venv --current接口检测当前激活的虚拟环境"""
    try:
        import sys
        import os
        import subprocess
        
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        # 使用统一的venv --current接口
        from pathlib import Path
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "GOOGLE_DRIVE.py"), 
             "--shell", "venv --current"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout
            # 解析输出中的环境名称
            for line in output.split('\n'):
                if line.startswith("Current virtual environment:"):
                    env_name = line.split(":")[1].strip()
                    return env_name if env_name != "None" else None
        
        return None
    except Exception:
        return None

def _update_shell_venv_state(current_shell, active_env):
    """更新shell状态中的虚拟环境信息"""
    try:
        shells_data = load_shells()
        shell_id = current_shell['id']
        
        if shell_id in shells_data["shells"]:
            # 确保venv_state字段存在
            if "venv_state" not in shells_data["shells"][shell_id]:
                shells_data["shells"][shell_id]["venv_state"] = {}
            
            shells_data["shells"][shell_id]["venv_state"]["active_env"] = active_env
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            save_shells(shells_data)
    except Exception:
        pass  # 如果更新失败，不影响shell正常运行

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
            print("Enter 'help' to view available commands, enter 'exit' to exit")
            
            while True:
                try:
                    # 获取当前shell状态（可能在循环中被更新）
                    current_shell = get_current_shell()
                    
                    # 显示提示符，包括虚拟环境和当前路径
                    current_path = current_shell.get("current_path", "~")
                    
                    # 检查是否有激活的虚拟环境
                    venv_prefix = ""
                    try:
                        # 首先尝试从shell配置中获取虚拟环境信息
                        venv_state = current_shell.get("venv_state", {})
                        active_env = venv_state.get("active_env")
                        
                        # 如果shell配置中没有venv信息，进行一次检测并缓存
                        if not active_env:
                            active_env = _detect_active_venv()
                            if active_env:
                                _update_shell_venv_state(current_shell, active_env)
                                # 更新当前shell对象，避免下次循环重复检测
                                current_shell["venv_state"] = {"active_env": active_env}
                        
                        if active_env:
                            venv_prefix = f"({active_env}) "
                    except Exception as e:
                        # 如果检测失败，继续使用默认提示符
                        pass
                    
                    # 简化路径显示：类似bash只显示最后一个部分
                    if current_path == "~":
                        display_path = "~"
                    else:
                        # 显示最后一个路径部分，类似bash的行为
                        path_parts = current_path.split('/')
                        display_path = path_parts[-1] if path_parts[-1] else path_parts[-2]
                    
                    prompt = f"\n{venv_prefix}GDS:{display_path}$ "
                    user_input = get_multiline_input_safe(prompt, single_line=True)
                    if not user_input:
                        continue
                    
                    # 解析命令
                    parts = user_input.split()
                    cmd = parts[0].lower()
                    
                    if cmd == "exit":
                        # print("👋 Exit Google Drive Shell")
                        break
                    else:
                        # 使用GoogleDriveShell的execute_shell_command方法处理所有命令
                        try:
                            import sys
                            import os
                            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                            from google_drive_shell import GoogleDriveShell
                            shell_instance = GoogleDriveShell()
                            
                            # 执行完整的shell命令
                            result_code = shell_instance.execute_shell_command(user_input)
                            
                            # 如果命令执行失败，显示帮助提示
                            if result_code != 0:
                                print("💡 Enter 'help' to view available commands")
                        except Exception as e:
                            print(f"Error executing command '{cmd}': {e}")
                            print("💡 Enter 'help' to view available commands")
                    
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
