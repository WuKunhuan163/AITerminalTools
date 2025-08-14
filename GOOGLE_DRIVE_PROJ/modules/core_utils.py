#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive - Core Utils Module
从GOOGLE_DRIVE.py重构而来的core_utils模块
"""

import os
import sys
import json
import webbrowser
import hashlib
import subprocess
import time
import uuid
import warnings
from pathlib import Path

from GOOGLE_DRIVE_PROJ.modules.remote_commands import debug_print
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
from dotenv import load_dotenv
load_dotenv()

# 导入Google Drive Shell管理类 - 注释掉避免循环导入
# from .google_drive_shell import GoogleDriveShell

def show_command_window_subprocess(title, command_text, instruction_text="", timeout_seconds=300):
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
    
    # 设置窗口置顶
    root.attributes('-topmost', True)
    
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
    
    def execution_completed():
        result_queue.put({{"action": "success", "message": "用户确认执行完成"}})
        result["action"] = "success"
        root.destroy()
    
    def direct_feedback():
        """直接反馈功能"""
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
    
    # 自动复制命令到剪贴板
    copy_command()
    
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
        
        # 解析结果
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"action": "error", "error": "Failed to parse result"}
        else:
            return {"action": "error", "error": "Subprocess failed"}
            
    except subprocess.TimeoutExpired:
        return {"action": "timeout", "error": "Window timeout"}
    except Exception as e:
        return {"action": "error", "error": str(e)}

def get_multiline_input_safe(prompt_text="请输入内容", single_line=True):
    """
    安全的输入处理函数，支持多行输入和Ctrl+D结束输入
    采用和USERINPUT相同的signal超时机制和readline缓冲区捕获
    
    Args:
        prompt_text (str): 提示文本
        single_line (bool): 是否为单行输入模式，True表示使用标准input()，False表示多行输入
    
    Returns:
        str: 用户输入的内容，如果取消返回None
    """
    if single_line:
        # 单行输入模式，使用标准input()但添加异常处理
        try:
            # 确保readline正确初始化
            import readline
            
            # 设置readline配置以支持中文字符
            try:
                # 设置输入编码
                readline.set_startup_hook(None)
                # 启用历史记录
                readline.clear_history()
            except:
                pass  # 如果配置失败，继续使用默认设置
                
            return input(prompt_text).strip()
        except EOFError:
            # Ctrl+D被按下，在单行模式下返回空字符串
            print("\n输入已结束")
            return ""
        except KeyboardInterrupt:
            # Ctrl+C被按下
            print("\n输入已取消")
            return None
    else:
        # 多行输入模式，采用和USERINPUT相同的实现方式
        import signal
        import readline
        
        # 确保readline正确配置
        try:
            # 设置readline配置以支持中文字符
            readline.set_startup_hook(None)
            # 启用历史记录
            readline.clear_history()
            
            # 设置编辑模式为emacs（支持更好的中文编辑）
            readline.parse_and_bind("set editing-mode emacs")
            # 启用UTF-8支持
            readline.parse_and_bind("set input-meta on")
            readline.parse_and_bind("set output-meta on")
            readline.parse_and_bind("set convert-meta off")
        except Exception:
            pass  # 如果配置失败，继续使用默认设置
        
        print(f"{prompt_text}")
        print("多行输入模式：输入完成后按 Ctrl+D (EOF) 结束输入")
        print("输入内容: ", end="", flush=True)
        
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
            # Ctrl+C 被按下
            print("\n输入已取消")
            return None
        finally:
            # 清理超时设置
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original_handler)
        
        # 组合所有行为最终输入
        full_input = '\n'.join(lines).strip()
        return full_input if full_input else ""

# 全局常量
HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
HOME_FOLDER_ID = "root"  # Google Drive中My Drive的文件夹ID
REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"  # REMOTE_ROOT文件夹ID

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

def copy_to_clipboard(text):
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
        # handle_shell_command = globals().get('handle_shell_command')  # 移除，改用GoogleDriveShell
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
            # 不要用空格连接参数，这会破坏引号结构
            # 而是重新构建带引号的命令字符串
            import shlex
            shell_cmd_parts = args[1:]
            
            # 对于包含空格的参数，需要重新加上引号
            quoted_parts = []
            for part in shell_cmd_parts:
                if ' ' in part or '"' in part or "'" in part:
                    # 如果参数包含空格或引号，用shlex.quote重新引用
                    quoted_parts.append(shlex.quote(part))
                else:
                    quoted_parts.append(part)
            
            shell_cmd = ' '.join(quoted_parts)
            debug_print(f"DEBUG: args[1:] = {args[1:]}")
            debug_print(f"DEBUG: shell_cmd_parts = {shell_cmd_parts}")
            debug_print(f"DEBUG: quoted_parts = {quoted_parts}")
            debug_print(f"DEBUG: final shell_cmd = {repr(shell_cmd)}")
            
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
