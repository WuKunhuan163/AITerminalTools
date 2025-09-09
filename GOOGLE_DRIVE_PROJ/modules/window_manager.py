"""
GDS窗口管理器 - 统一管理所有tkinter窗口
解决多线程窗口创建和队列管理的复杂性问题
支持跨进程队列管理，确保多个GDS进程只能有一个窗口
"""

import threading
import queue
import time
import os
import fcntl
import json
import signal
import atexit
import subprocess
from pathlib import Path

class WindowManager:
    """
    统一窗口管理器
    
    设计原则：
    1. 单例模式：整个系统只有一个WindowManager实例
    2. 队列化处理：所有窗口请求进入队列，按顺序处理
    3. 接口化设计：线程通过简单接口提交命令和获取结果
    4. 生命周期管理：Manager负责窗口的完整生命周期
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化窗口管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.window_counter = 0  # 窗口计数器
        self.active_processes = {}  # 活跃的子进程 {window_id: process}
        
        # 设置进程清理处理器
        self._setup_cleanup_handlers()
        
        # 跨进程窗口管理，不需要线程队列
    
    def _setup_cleanup_handlers(self):
        """设置进程清理处理器"""
        def cleanup_handler(signum=None, frame=None):
            self._debug_log(f"🧹 DEBUG: [CLEANUP_HANDLER] 进程清理处理器触发，信号: {signum}")
            self._cleanup_all_processes()
        
        # 注册信号处理器
        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)
        
        # 注册退出处理器
        atexit.register(self._cleanup_all_processes)
        
        self._debug_log("🛡️ DEBUG: [CLEANUP_SETUP] 进程清理处理器已设置")
    
    def _cleanup_all_processes(self):
        """清理所有活跃的子进程"""
        if not hasattr(self, 'active_processes'):
            return
            
        cleanup_count = 0
        for window_id, process in list(self.active_processes.items()):
            try:
                if process.poll() is None:  # 进程还在运行
                    self._debug_log(f"🧹 DEBUG: [CLEANUP_PROCESS] 清理子进程: PID={process.pid}, window_id: {window_id}")
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
                    cleanup_count += 1
            except Exception as e:
                self._debug_log(f"❌ DEBUG: [CLEANUP_ERROR] 清理进程失败: {e}")
            
            # 从活跃进程列表中移除
            self.active_processes.pop(window_id, None)
        
        if cleanup_count > 0:
            self._debug_log(f"🧹 DEBUG: [CLEANUP_COMPLETE] 清理了 {cleanup_count} 个子进程")
    
    def start_manager(self):
        """跨进程窗口管理器，无需启动线程"""
        self._debug_log("🏗️ DEBUG: [CROSS_PROCESS_WINDOW_MANAGER] 跨进程窗口管理器启动成功")
    
    def request_window(self, title, command_text, timeout_seconds=3600):
        """
        请求显示窗口 - 跨进程队列管理
        
        Args:
            title (str): 窗口标题
            command_text (str): 命令文本
            timeout_seconds (int): 超时时间
            
        Returns:
            dict: 用户操作结果
        """
        request_id = f"req_{int(time.time() * 1000)}_{os.getpid()}_{threading.get_ident()}"
        
        # 使用跨进程文件锁确保只有一个窗口
        lock_file = Path("/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA/window_lock.lock")
        lock_file.parent.mkdir(exist_ok=True)
        
        self._debug_log(f"🔒 DEBUG: [CROSS_PROCESS_LOCK] 进程 {os.getpid()} 请求窗口锁: {request_id}")
        
        try:
            with open(lock_file, 'w') as f:
                # 获取排他锁，阻塞等待直到获得锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                self._debug_log(f"🔓 DEBUG: [LOCK_ACQUIRED] 进程 {os.getpid()} 获得窗口锁: {request_id}")
                
                # 现在只有这个进程可以创建窗口
                window_request = {
                    'request_id': request_id,
                    'title': title,
                    'command_text': command_text,
                    'timeout_seconds': timeout_seconds,
                    'process_id': os.getpid(),
                    'thread_id': threading.get_ident()
                }
                
                # 直接创建窗口（因为已经获得了跨进程锁）
                result = self._create_and_show_window(window_request)
                self._debug_log(f"✅ DEBUG: [CROSS_PROCESS_WINDOW] 进程 {os.getpid()} 窗口完成: {request_id}, action: {result.get('action')}")
                
                return result
                
        except Exception as e:
            error_msg = f"跨进程窗口创建失败: {str(e)}"
            self._debug_log(f"❌ DEBUG: [CROSS_PROCESS_ERROR] 进程 {os.getpid()} 窗口错误: {request_id}, error: {str(e)}")
            return {"action": "error", "message": error_msg}
        # fcntl.flock会在文件关闭时自动释放锁
    
    def _create_and_show_window(self, request):
        """创建和显示tkinter窗口"""
        import subprocess
        import json
        import base64
        
        self.window_counter += 1
        window_id = f"win_{self.window_counter}_{request['request_id']}"
        
        self._debug_log(f"🪟 DEBUG: [TKINTER_WINDOW_CREATE] 创建窗口: {window_id}")
        
        # 使用subprocess创建窗口（避免主线程阻塞）
        title_escaped = request['title'].replace('"', '\\"').replace("'", "\\'")
        command_b64 = base64.b64encode(request['command_text'].encode('utf-8')).decode('ascii')
        
        # 获取音频文件路径
        current_dir = os.path.dirname(__file__)
        audio_file_path = os.path.join(os.path.dirname(current_dir), "tkinter_bell.mp3")
        
        # 创建子进程脚本
        # 准备模板变量
        timeout_ms = request['timeout_seconds'] * 1000
        
        subprocess_script_template = '''
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
    command_text = base64.b64decode("COMMAND_B64_PLACEHOLDER").decode('utf-8')
    
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
            f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_CREATED] 窗口创建成功 - WINDOW_ID_PLACEHOLDER\\n".format(timestamp))
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
            audio_path = "AUDIO_FILE_PATH_PLACEHOLDER"
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
        result_queue.put({"action": "success", "message": "用户确认执行完成"})
        result["action"] = "success"
        # 记录窗口销毁
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                import time
                timestamp = time.time() - 1757413752.714440
                f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 用户点击成功 - WINDOW_ID_PLACEHOLDER\\n".format(timestamp))
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
                import time
                timestamp = time.time() - 1757413752.714440
                f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 用户点击反馈 - WINDOW_ID_PLACEHOLDER\\n".format(timestamp))
                f.flush()
        except:
            pass
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
    
    # 绑定键盘事件到窗口（仅保留复制功能）
    root.bind('<Key>', on_key_press)
    root.focus_set()  # 确保窗口能接收键盘事件
    
    # 设置超时定时器
    def timeout_destroy():
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                import time
                timestamp = time.time() - 1757413752.714440
                f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 超时 - WINDOW_ID_PLACEHOLDER\\n".format(timestamp))
                f.flush()
        except:
            pass
        result.update({"action": "timeout"})
        root.destroy()
    
    root.after(TIMEOUT_MS_PLACEHOLDER, timeout_destroy)
    
    # 运行窗口
    root.mainloop()
    
    # 输出结果
    print(json.dumps(result))

except Exception as e:
    print(json.dumps({"action": "error", "message": str(e)}))
'''
        
        # 替换模板占位符
        subprocess_script = subprocess_script_template.replace("COMMAND_B64_PLACEHOLDER", command_b64)
        subprocess_script = subprocess_script.replace("TITLE_PLACEHOLDER", title_escaped)
        subprocess_script = subprocess_script.replace("WINDOW_ID_PLACEHOLDER", window_id)
        subprocess_script = subprocess_script.replace("TIMEOUT_MS_PLACEHOLDER", str(timeout_ms))
        subprocess_script = subprocess_script.replace("AUDIO_FILE_PATH_PLACEHOLDER", audio_file_path)
        
        # 使用Popen来获得更好的进程控制
        try:
            # 启动子进程
            process = subprocess.Popen(
                ['python', '-c', subprocess_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self._debug_log(f"🪟 DEBUG: [SUBPROCESS_STARTED] 启动窗口子进程: PID={process.pid}, window_id: {window_id}")
            
            # 将进程添加到活跃进程列表
            self.active_processes[window_id] = process
            
            try:
                # 等待进程完成，带超时
                stdout, stderr = process.communicate(timeout=request['timeout_seconds'] + 10)
                
                # 进程正常完成，从活跃列表中移除
                self.active_processes.pop(window_id, None)
                
                if process.returncode == 0 and stdout.strip():
                    try:
                        window_result = json.loads(stdout.strip())
                        self._debug_log(f"🪟 DEBUG: [TKINTER_WINDOW_RESULT] 窗口结果: {window_id}, action: {window_result.get('action')}")
                        return window_result
                    except json.JSONDecodeError as e:
                        return {"action": "error", "message": f"窗口结果解析失败: {e}"}
                else:
                    return {"action": "error", "message": f"窗口进程失败: returncode={process.returncode}, stderr={stderr}"}
                    
            except subprocess.TimeoutExpired:
                # 超时时强制终止子进程
                self._debug_log(f"⏰ DEBUG: [SUBPROCESS_TIMEOUT] 窗口子进程超时，强制终止: PID={process.pid}, window_id: {window_id}")
                
                try:
                    # 尝试温和终止
                    process.terminate()
                    process.wait(timeout=3)
                    self._debug_log(f"🔄 DEBUG: [SUBPROCESS_TERMINATED] 窗口子进程已终止: PID={process.pid}")
                except subprocess.TimeoutExpired:
                    # 强制杀死
                    process.kill()
                    process.wait(timeout=3)
                    self._debug_log(f"💀 DEBUG: [SUBPROCESS_KILLED] 窗口子进程已强制杀死: PID={process.pid}")
                except Exception as cleanup_error:
                    self._debug_log(f"❌ DEBUG: [SUBPROCESS_CLEANUP_ERROR] 清理子进程失败: {cleanup_error}")
                
                # 从活跃进程列表中移除
                self.active_processes.pop(window_id, None)
                
                return {"action": "timeout", "message": "窗口超时，子进程已清理"}
                
        except Exception as e:
            return {"action": "error", "message": f"窗口创建失败: {e}"}
    
    def _debug_log(self, message):
        """写入debug日志"""
        try:
            debug_file = Path("/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA/window_queue_debug.log")
            debug_file.parent.mkdir(exist_ok=True)
            
            with open(debug_file, "a", encoding="utf-8") as f:
                timestamp = time.time() - 1757413752.714440
                current_time = time.strftime("[%H:%M:%S]")
                f.write(f"{current_time} {message}\n")
                f.flush()
        except Exception:
            pass  # 忽略日志错误
    
    def stop_manager(self):
        """停止跨进程窗口管理器"""
        self._debug_log("🛑 DEBUG: [CROSS_PROCESS_WINDOW_MANAGER] 跨进程窗口管理器已停止")

# 全局窗口管理器实例
_window_manager = None

def get_window_manager():
    """获取全局窗口管理器实例"""
    global _window_manager
    if _window_manager is None:
        _window_manager = WindowManager()
    return _window_manager
