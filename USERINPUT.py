#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT.py - User Input Script for Cursor AI

获取用户输入的脚本，支持多行输入和超时控制
"""

import os
import sys
import json
import signal
import time
import threading
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 音频播放相关
import subprocess
import platform

# 全局focus计数器和音频播放功能 - 每3次focus播放一次音效
_focus_count = 0
_audio_file_path = Path(__file__).parent / "USERINPUT_PROJ" / "tkinter_bell.mp3"

# 已移除should_play_audio()函数，因为音效播放逻辑已完全移至Tkinter subprocess中
# 这样可以避免主进程和subprocess的双重音效播放问题
# def should_play_audio():
#     """检查是否应该播放音效（第1、4、7...次focus）"""
#     global _focus_count
#     _focus_count += 1
#     # 第1次、第4次、第7次... (即 count % 3 == 1)
#     return _focus_count % 3 == 1

# 已移除主进程中的音效播放函数，因为音效播放逻辑已完全移至Tkinter subprocess中
# 这样可以避免主进程和subprocess的双重音效播放问题

# def play_bell_sound():
#     """播放提示音"""
#     try:
#         if not _audio_file_path.exists():
#             return False
#             
#         system = platform.system()
#         if system == "Darwin":  # macOS
#             subprocess.run(["afplay", str(_audio_file_path)], 
#                          capture_output=True, timeout=2)
#         elif system == "Linux":
#             # 尝试多个Linux音频播放器
#             players = ["paplay", "aplay", "mpg123", "mpv", "vlc"]
#             for player in players:
#                 try:
#                     subprocess.run([player, str(_audio_file_path)], 
#                                  capture_output=True, timeout=2, check=True)
#                     break
#                 except (subprocess.CalledProcessError, FileNotFoundError):
#                     continue
#         elif system == "Windows":
#             # Windows可以使用winsound模块或powershell
#             try:
#                 subprocess.run(["powershell", "-c", 
#                               f"(New-Object Media.SoundPlayer '{_audio_file_path}').PlaySync()"], 
#                              capture_output=True, timeout=2)
#             except:
#                 pass
#         return True
#     except Exception:
#         return False

# def increment_focus_and_play():
#     """增加focus计数，每3次播放一次音频"""
#     global _focus_count
#     _focus_count += 1
#     if _focus_count % 3 == 1:
#         # 在后台线程中播放音频，避免阻塞
#         threading.Thread(target=play_bell_sound, daemon=True).start()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False


def get_project_name():
    """获取项目名称"""
    try:
        # 从当前工作目录获取项目名称
        current_dir = Path.cwd()
        # 尝试找到项目根目录
        project_dir = current_dir
        while project_dir.parent != project_dir:
            if (project_dir / '.git').exists():
                break
            project_dir = project_dir.parent
        return project_dir.name, current_dir, project_dir
    except Exception as e:
        return "Agent Project", Path.cwd(), Path.cwd()

def show_project_info(current_dir, project_dir):
    """显示项目信息"""
    # print(f"current_dir: {current_dir}")
    # print(f"project_dir: {project_dir}")
    # print(f"project_dir.name: {project_dir.name}")
    if is_run_environment():
        run_identifier = os.environ.get('RUN_IDENTIFIER')
        output_file = os.environ.get('RUN_DATA_FILE')
        if run_identifier:
            print(f"RUN identifier: {run_identifier}")
        if output_file:
            print(f"Output file: {output_file}")

def show_prompt_header(project_name, hint_text=None):
    """显示提示头部信息"""
    # 移除主进程中的音效播放逻辑，只在Tkinter subprocess中播放音效
    # 这样可以避免双重音效播放和按钮点击时的音效问题
    
    if project_name: 
        project_name = project_name + " - "
    if is_run_environment():
        run_identifier = os.environ.get('RUN_IDENTIFIER', '')
        title = f"{project_name}Agent Mode (RUN: {run_identifier[:8]}...)"
    else:
        title = f"{project_name}Agent Mode"
    
    separator = "=" * len(title)
    
    print(f"{separator}")
    print(f"{title}")
    print(f"{separator}")
    
    if hint_text:
        print(f"\nHint provided: {hint_text}")
    
    print(f"\nEnter your next prompt. Press Ctrl+D (EOF) when done.")

def show_tkinter_window_in_subprocess(project_name, timeout_seconds):
    """在子进程中显示tkinter窗口，抑制所有stdout/stderr输出"""
    import subprocess
    import sys
    import os
    
    # 获取音频文件路径并传递给子进程
    current_dir = os.path.dirname(__file__)
    audio_file_path = os.path.join(current_dir, "USERINPUT_PROJ", "tkinter_bell.mp3")
    
    # 创建子进程脚本
    subprocess_script = f'''
import sys
import os
import time

# 抑制所有警告
import warnings
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

try:
    import tkinter as tk
    
    root = tk.Tk()
    root.title("{project_name} - Agent Mode")
    root.geometry("200x40")
    root.attributes('-topmost', True)
    
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
    
    # 全局focus计数器和状态标志
    focus_count = 0
    button_clicked = False
    
    # 带focus计数的聚焦函数
    def force_focus_with_count():
        global focus_count, button_clicked
        # 如果按钮已被点击，不再播放音效
        if button_clicked:
            return
            
        focus_count += 1
        force_focus()
        
        try:
            import threading
            threading.Thread(target=play_bell_in_subprocess, daemon=True).start()
        except Exception as e:
            pass
    
    # 按钮点击处理函数
    def on_button_click():
        global button_clicked
        button_clicked = True  # 标记按钮已被点击
        root.destroy()
    
    # 初始聚焦（第1次，会播放音效）
    force_focus_with_count()
    
    # 创建按钮
    btn = tk.Button(
        root, 
        text="Click to Enter Prompt", 
        command=on_button_click,  # 使用自定义的点击处理函数
        padx=20,
        pady=10,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 10, "bold")
    )
    btn.pack(expand=True)
    
    # 回车键快捷键已删除，用户需要点击按钮
    
    # 键盘事件绑定已移除
    
    # 定期重新获取焦点的函数 - 暂时注释掉5秒refocus机制
    def refocus_window():
        try:
            # 使用带focus计数的聚焦函数
            force_focus_with_count()
            
            # 每30秒重新获取焦点并播放音效
            root.after(30000, refocus_window)
        except Exception as e:
            pass  # 如果窗口已关闭，忽略错误
    
    # 开始定期重新获取焦点
    root.after(30000, refocus_window)
    
    # 设置自动关闭定时器
    def auto_close():
        if not button_clicked:
            root.destroy()
    
    root.after({timeout_seconds} * 1000, auto_close)
    
    # 运行窗口
    root.mainloop()
    
    # 输出结果（用户是否点击了按钮）
    print(f"clicked")
    
except Exception as e:
    print(f"error")
'''
    
    try:
        # 在子进程中运行tkinter窗口，允许debug输出
        result = subprocess.run(
            [sys.executable, '-c', subprocess_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 将stderr重定向到stdout以便看到debug输出
            text=True,
            timeout=timeout_seconds + 5  # 给子进程额外5秒时间
        )
        
        # 检查结果
        if result.returncode == 0 and "clicked" in result.stdout:
            return True  # 用户点击了按钮
        else:
            return False  # 超时或其他情况
            
    except subprocess.TimeoutExpired:
        return False  # 超时
    except Exception:
        return False  # 其他错误

def show_dummy_ui(project_name):
    """显示极简的dummy UI，使用全局超时管理"""
    global _global_timeout_manager
    
    # 检查是否设置了跳过GUI的环境变量
    if os.environ.get('USERINPUT_NO_GUI', '').lower() in ('1', 'true', 'yes'):
        # 直接返回True，跳过GUI，使用终端输入
        return True
    
    # 检查全局超时是否已经过期
    if _global_timeout_manager and _global_timeout_manager.is_timeout_expired():
        return False
    
    # 获取剩余时间
    if _global_timeout_manager:
        remaining_time = int(_global_timeout_manager.get_remaining_time())
    else:
        # 如果没有全局超时管理器，使用默认值
        default_timeout = int(os.environ.get('USERINPUT_TIMEOUT', '300'))
        remaining_time = getattr(get_user_input_via_terminal, '_timeout_override', default_timeout)
    
    # 如果剩余时间<=0，直接返回
    if remaining_time <= 0:
        return False
    
    # 使用子进程方式显示tkinter窗口
    return show_tkinter_window_in_subprocess(project_name, remaining_time)

class TimeoutException(Exception):
    """Timeout exception for input operations"""
    pass

class GlobalTimeoutManager:
    """管理全局超时，确保tkinter窗口和终端输入的总时间不超过设定值"""
    def __init__(self, timeout_seconds):
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()
        self.is_expired = False
        self.lock = threading.Lock()
    
    def get_remaining_time(self):
        """获取剩余时间（秒）"""
        with self.lock:
            if self.is_expired:
                return 0
            elapsed = time.time() - self.start_time
            remaining = max(0, self.timeout_seconds - elapsed)
            if remaining <= 0:
                self.is_expired = True
            return remaining
    
    def is_timeout_expired(self):
        """检查是否已超时"""
        return self.get_remaining_time() <= 0
    
    def mark_expired(self):
        """手动标记为已超时"""
        with self.lock:
            self.is_expired = True

# 全局超时管理器实例
_global_timeout_manager = None

def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutException("Input timeout")

def _read_input_with_signal(lines, timeout_seconds):
    """使用信号的传统方法，简化输入处理"""
    import readline
    
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                # Ctrl+D 结束输入
                try:
                    current_line = readline.get_line_buffer()
                    if current_line.strip():
                        lines.append(current_line.strip())
                except:
                    pass
                return False
            except KeyboardInterrupt:
                # Ctrl+C 处理
                try:
                    current_line = readline.get_line_buffer()
                    if current_line.strip():
                        stripped_line = current_line.strip()
                        if not lines or lines[-1] != stripped_line:
                            lines.append(stripped_line)
                except Exception:
                    pass
                return "partial_input" if lines else "no_input"
            except TimeoutException:
                # 超时处理
                try:
                    current_line = readline.get_line_buffer()
                    if current_line.strip():
                        stripped_line = current_line.strip()
                        # 避免重复添加已经存在的行
                        if not lines or lines[-1] != stripped_line:
                            lines.append(stripped_line)
                except Exception:
                    pass
                return True
    finally:
        # 清理超时设置
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

def get_user_input_via_terminal(project_name, timeout_hint=""):
    """直接在终端中获取用户输入，带有超时功能"""
    global _global_timeout_manager

    # 获取剩余超时时间
    if _global_timeout_manager:
        remaining_time = _global_timeout_manager.get_remaining_time()
        if remaining_time <= 0:
            return timeout_hint if timeout_hint else "输入超时"
        TIMEOUT_SECONDS = max(1, int(remaining_time))
    else:
        default_timeout = int(os.environ.get('USERINPUT_TIMEOUT', '300'))
        TIMEOUT_SECONDS = int(getattr(get_user_input_via_terminal, '_timeout_override', default_timeout))
    
    # 读取多行输入
    lines = []
    timeout_occurred = False
    
    try:
        result = _read_input_with_signal(lines, TIMEOUT_SECONDS)
        if result == "partial_input" or result == False:
            timeout_occurred = False
        else:
            timeout_occurred = result  # True for timeout
    except KeyboardInterrupt:
        pass  # 忽略KeyboardInterrupt，继续处理
    
    # 组合输入
    full_input = '\n'.join(lines).strip()
    
    # 如果发生超时，添加超时提示
    if timeout_occurred or (_global_timeout_manager and _global_timeout_manager.is_timeout_expired()):
        if timeout_hint:
            full_input = f"{full_input}\n{timeout_hint}" if full_input else timeout_hint
    
    # 清理屏幕
    if not is_run_environment():
        print(f"\n" + "="*50)
    
    return full_input or "用户暂无输入"

def write_to_json_output(user_input, command_identifier=None):
    """将用户输入写入到指定的 JSON 输出文件中"""
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
        
        # 准备 JSON 数据
        data = {
            'success': True,
            'type': 'user_input',
            'user_input': user_input,
            'message': 'User input received successfully'
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def show_help():
    """显示帮助信息"""
    print(f"""USERINPUT - User Input Script for Cursor AI

Usage:
  USERINPUT                    Get user input interactively (3-minute timeout)
  USERINPUT --timeout SECONDS Get user input with custom timeout
  USERINPUT --help             Show this help message

Options:
  --timeout SECONDS    Set custom timeout (default: 180 seconds)
  --help, -h           Show this help message

Environment Variables:
  USERINPUT_TIMEOUT            Timeout in seconds (default: 180)
  USERINPUT_NO_GUI             Skip GUI window to avoid IMK messages (1/true/yes)

Examples:
  USERINPUT                    # 3-minute timeout (default)
  USERINPUT --timeout 20       # 20-second timeout (testing)
  USERINPUT --timeout 300      # 5-minute timeout
  USERINPUT_NO_GUI=1 USERINPUT # Skip GUI, avoid macOS IMK messages

Features:
- Multi-line input support (press Ctrl+D to finish)
- Automatic timeout with graceful handling
- GUI window for better user experience (can be disabled)
- JSON output support for programmatic usage
- Timeout guidance for repeated USERINPUT calls
- Complete tkinter warning suppression

GUI Notes:
- On macOS, tkinter windows may show IMK (Input Method) messages
- Use USERINPUT_NO_GUI=1 to completely avoid GUI and IMK messages
- Terminal-only mode provides identical functionality

Environment Variables:
  USERINPUT_TIMEOUT            Timeout in seconds (default: 180)
  USERINPUT_NO_GUI             Skip GUI window to avoid IMK messages (1/true/yes)
""")
    return True

def main():
    """主函数，支持命令行参数"""
    
    # 获取command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    
    # 解析命令行参数
    timeout_override = None
    hint_text = None
    remaining_args = []
    
    i = 0
    while i < len(args):
        if args[i] in ['--help', '-h']:
            # 显示帮助信息
            show_help()
            return
        elif args[i] == '--timeout':
            if i + 1 < len(args):
                try:
                    timeout_override = int(args[i + 1])
                    i += 2  # Skip both --timeout and its value
                except ValueError:
                    print(f"Error: --timeout requires a numeric value")
                    return
            else:
                print(f"Error: --timeout requires a value")
                return
        elif args[i] == '--hint':
            if i + 1 < len(args):
                hint_text = args[i + 1]
                i += 2  # Skip both --hint and its value
            else:
                print(f"Error: --hint requires a value")
                return
        else:
            remaining_args.append(args[i])
            i += 1
    
    # 更新剩余参数
    args = remaining_args
    
    # 获取项目信息
    project_name, current_dir, project_dir = get_project_name()
    
    # IGNOREEOF 现在由 USERINPUT shell 脚本自动设置
    # 设置超时覆盖（如果有的话）
    timeout_hint = "\n用户还在测试代码，或者准备给你的反馈。如果你没有得到指导你下一步工作的信息，请通过再次执行USERINPUT等待用户，不要直接结束。"
    end_hint = "\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如果程序停止，重复执行 `USERINPUT` 直到获得自然语言反馈。编程遇到不确定的情况或者Keyboard Interrupt时，请执行 `USERINPUT`，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
    if timeout_override is not None:
        get_user_input_via_terminal._timeout_override = timeout_override
    
    # 初始化全局超时管理器
    global _global_timeout_manager
    default_timeout = int(os.environ.get('USERINPUT_TIMEOUT', '180'))
    final_timeout = timeout_override if timeout_override is not None else default_timeout
    _global_timeout_manager = GlobalTimeoutManager(final_timeout)
    timeout = False
    
    # 尝试显示极简UI（仅在非RUN环境中）
    if not is_run_environment(command_identifier):
        ui_result = show_dummy_ui(project_name)
        
        # 如果UI因超时关闭，直接返回超时结果
        if (not ui_result and _global_timeout_manager.is_timeout_expired()) or \
            _global_timeout_manager.is_timeout_expired():
            timeout = True
            user_input = f"输入超时 ({final_timeout}秒)。{timeout_hint}"
        else:
            show_project_info(current_dir, project_dir)
            show_prompt_header(project_name, hint_text)
            user_input = get_user_input_via_terminal(project_name, timeout_hint)
    else:
        user_input = get_user_input_via_terminal(project_name, timeout_hint)
    
    if is_run_environment(command_identifier):
        if not write_to_json_output(user_input, command_identifier):
            print(f"Failed to write user input to JSON file.")
            print(user_input)
    else:
        # 不在 RUN 环境中，直接输出到 stdout（保持原有行为）
        os.system("clear") if os.name == "posix" else os.system("cls")
        if not timeout:
            user_input += end_hint
        print(user_input)

if __name__ == "__main__":
    main() 