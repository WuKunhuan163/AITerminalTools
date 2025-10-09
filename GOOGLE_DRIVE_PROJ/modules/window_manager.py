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
import psutil
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
        self.lock_file_path = Path("/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA/window_lock.lock")
        self.pid_file_path = Path("/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA/window_lock.pid")
        self.current_lock_fd = None  # 当前持有的锁文件描述符
        
        # 设置进程清理处理器
        self._setup_cleanup_handlers()
        
        # 清理可能存在的无效锁
        self._cleanup_stale_locks()
        
        # 跨进程窗口管理，不需要线程队列
    
    def _setup_cleanup_handlers(self):
        """设置进程清理处理器"""
        def cleanup_handler(signum=None, frame=None):
            self._debug_log(f"🧹 DEBUG: [CLEANUP_HANDLER] 进程清理处理器触发，信号: {signum}")
            self._cleanup_all_processes()
            self._release_lock()
        
        def emergency_cleanup_handler(signum=None, frame=None):
            """紧急清理处理器 - 用于强制退出信号"""
            self._debug_log(f"🚨 DEBUG: [EMERGENCY_CLEANUP] 紧急清理处理器触发，信号: {signum}")
            self._force_cleanup_all_processes()
            self._release_lock()
            # 对于SIGKILL等信号，立即退出
            if signum in (signal.SIGKILL, signal.SIGQUIT):
                os._exit(1)
        
        # 注册常规信号处理器
        signal.signal(signal.SIGTERM, cleanup_handler)
        signal.signal(signal.SIGINT, cleanup_handler)
        
        # 注册紧急信号处理器
        try:
            signal.signal(signal.SIGQUIT, emergency_cleanup_handler)  # Ctrl+\
            if hasattr(signal, 'SIGHUP'):
                signal.signal(signal.SIGHUP, cleanup_handler)  # 挂起信号
        except (OSError, ValueError):
            # 某些信号在某些系统上可能不可用
            pass
        
        # 注册退出处理器
        atexit.register(cleanup_handler)
        
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
                self._debug_log(f"Error: DEBUG: [CLEANUP_ERROR] 清理进程失败: {e}")
            
            # 从活跃进程列表中移除
            self.active_processes.pop(window_id, None)
        
        if cleanup_count > 0:
            self._debug_log(f"🧹 DEBUG: [CLEANUP_COMPLETE] 清理了 {cleanup_count} 个子进程")
    
    def _force_cleanup_all_processes(self):
        """强制清理所有活跃的子进程 - 用于紧急情况"""
        if not hasattr(self, 'active_processes'):
            return
            
        cleanup_count = 0
        for window_id, process in list(self.active_processes.items()):
            try:
                if process.poll() is None:  # 进程还在运行
                    self._debug_log(f"🚨 DEBUG: [FORCE_CLEANUP_PROCESS] 强制清理子进程: PID={process.pid}, window_id: {window_id}")
                    
                    # 立即杀死进程，不等待
                    process.kill()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        # 如果1秒内还没死，就忽略
                        pass
                    cleanup_count += 1
            except Exception as e:
                self._debug_log(f"Error: DEBUG: [FORCE_CLEANUP_ERROR] 强制清理进程失败: {e}")
            
            # 从活跃进程列表中移除
            self.active_processes.pop(window_id, None)
        
        # 额外的系统级清理：查找并杀死所有可能的tkinter窗口进程
        try:
            import psutil
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    cmdline_str = ' '.join(cmdline)
                    
                    # 检测可能的GDS tkinter窗口进程
                    if ('python' in cmdline_str.lower() and 
                        ('-c' in cmdline_str or 'tkinter' in cmdline_str.lower()) and
                        ('Google Drive Shell' in cmdline_str or 'root.title' in cmdline_str)):
                        
                        self._debug_log(f"🚨 DEBUG: [SYSTEM_CLEANUP] 发现并清理tkinter进程: PID={proc.info['pid']}")
                        proc.kill()
                        killed_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if killed_count > 0:
                self._debug_log(f"🚨 DEBUG: [SYSTEM_CLEANUP_COMPLETE] 系统级清理了 {killed_count} 个tkinter进程")
                
        except Exception as e:
            self._debug_log(f"Error: DEBUG: [SYSTEM_CLEANUP_ERROR] 系统级清理失败: {e}")
        
        if cleanup_count > 0:
            self._debug_log(f"🚨 DEBUG: [FORCE_CLEANUP_COMPLETE] 强制清理了 {cleanup_count} 个子进程")
    
    def _cleanup_stale_locks(self):
        """清理过期的锁文件"""
        try:
            if self.pid_file_path.exists():
                with open(self.pid_file_path, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # 检查进程是否还存在
                try:
                    old_process = psutil.Process(old_pid)
                    # 检查是否是GDS相关进程
                    cmdline = ' '.join(old_process.cmdline())
                    if 'GOOGLE_DRIVE.py' not in cmdline and 'python' not in cmdline.lower():
                        # 不是GDS进程，清理锁
                        self._force_cleanup_lock()
                        self._debug_log(f"🧹 DEBUG: [STALE_LOCK_CLEANUP] 清理了非GDS进程的锁: PID={old_pid}")
                except psutil.NoSuchProcess:
                    # 进程不存在，清理锁
                    self._force_cleanup_lock()
                    self._debug_log(f"🧹 DEBUG: [STALE_LOCK_CLEANUP] 清理了不存在进程的锁: PID={old_pid}")
                    
        except Exception as e:
            self._debug_log(f"⚠️ DEBUG: [STALE_LOCK_CLEANUP_ERROR] 清理过期锁失败: {e}")
    
    def _force_cleanup_lock(self):
        """强制清理锁文件"""
        try:
            if self.lock_file_path.exists():
                self.lock_file_path.unlink()
            if self.pid_file_path.exists():
                self.pid_file_path.unlink()
        except Exception as e:
            self._debug_log(f"Error: DEBUG: [FORCE_CLEANUP_ERROR] 强制清理锁失败: {e}")
    
    def _acquire_lock(self, request_id, timeout_seconds=30):
        """
        获取跨进程锁
        
        Args:
            request_id (str): 请求ID
            timeout_seconds (int): 超时时间
            
        Returns:
            bool: 是否成功获取锁
        """
        current_pid = os.getpid()
        start_time = time.time()
        
        self._debug_log(f"🔒 DEBUG: [LOCK_REQUEST] 进程 {current_pid} 请求窗口锁: {request_id}")
        
        while time.time() - start_time < timeout_seconds:
            try:
                # 尝试创建PID文件（原子操作）
                if not self.pid_file_path.exists():
                    # PID文件不存在，尝试创建
                    with open(self.pid_file_path, 'x') as f:  # 'x' 模式确保原子性创建
                        f.write(str(current_pid))
                        f.flush()
                        os.fsync(f.fileno())  # 强制写入磁盘
                    
                    # 再次验证PID文件内容（防止竞态条件）
                    time.sleep(0.01)  # 短暂等待
                    with open(self.pid_file_path, 'r') as f:
                        stored_pid = int(f.read().strip())
                    
                    if stored_pid == current_pid:
                        # 成功获取锁，现在获取文件锁作为双重保险
                        try:
                            self.current_lock_fd = open(self.lock_file_path, 'w')
                            fcntl.flock(self.current_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                            self._debug_log(f"🔓 DEBUG: [LOCK_ACQUIRED] 进程 {current_pid} 成功获得窗口锁: {request_id}")
                            return True
                        except (IOError, OSError):
                            # 文件锁获取失败，清理PID文件
                            self._force_cleanup_lock()
                            continue
                    else:
                        # PID文件被其他进程修改，继续等待
                        continue
                else:
                    # PID文件存在，检查持有锁的进程是否还活着
                    try:
                        with open(self.pid_file_path, 'r') as f:
                            lock_holder_pid = int(f.read().strip())
                        
                        try:
                            lock_process = psutil.Process(lock_holder_pid)
                            # 进程存在，检查是否是GDS进程
                            cmdline = ' '.join(lock_process.cmdline())
                            if 'GOOGLE_DRIVE.py' in cmdline or 'python' in cmdline.lower():
                                # 是有效的GDS进程，等待
                                self._debug_log(f"⏳ DEBUG: [LOCK_WAITING] 进程 {current_pid} 等待锁释放，当前持有者: PID={lock_holder_pid}")
                                time.sleep(0.5)
                                continue
                            else:
                                # 不是GDS进程，清理锁
                                self._force_cleanup_lock()
                                continue
                        except psutil.NoSuchProcess:
                            # 持有锁的进程已不存在，清理锁
                            self._force_cleanup_lock()
                            self._debug_log(f"🧹 DEBUG: [DEAD_LOCK_CLEANUP] 清理了死进程的锁: PID={lock_holder_pid}")
                            continue
                            
                    except (ValueError, FileNotFoundError):
                        # PID文件损坏，清理
                        self._force_cleanup_lock()
                        continue
                        
            except FileExistsError:
                # PID文件已存在，等待
                time.sleep(0.1)
                continue
            except Exception as e:
                self._debug_log(f"Error: DEBUG: [LOCK_ERROR] 获取锁时出错: {e}")
                time.sleep(0.5)
                continue
        
        # 超时
        self._debug_log(f"⏰ DEBUG: [LOCK_TIMEOUT] 进程 {current_pid} 获取锁超时: {request_id}")
        return False
    
    def _release_lock(self):
        """释放跨进程锁"""
        try:
            current_pid = os.getpid()
            
            # 检查是否是当前进程持有的锁
            if self.pid_file_path.exists():
                with open(self.pid_file_path, 'r') as f:
                    lock_holder_pid = int(f.read().strip())
                
                if lock_holder_pid == current_pid:
                    # 释放文件锁
                    if self.current_lock_fd:
                        try:
                            fcntl.flock(self.current_lock_fd.fileno(), fcntl.LOCK_UN)
                            self.current_lock_fd.close()
                            self.current_lock_fd = None
                        except Exception as e:
                            self._debug_log(f"⚠️ DEBUG: [FILE_LOCK_RELEASE_ERROR] 释放文件锁失败: {e}")
                    
                    # 清理锁文件
                    self._force_cleanup_lock()
                    self._debug_log(f"🔓 DEBUG: [LOCK_RELEASED] 进程 {current_pid} 释放了窗口锁")
                else:
                    self._debug_log(f"⚠️ DEBUG: [LOCK_RELEASE_WARNING] 进程 {current_pid} 尝试释放不属于自己的锁")
            
        except Exception as e:
            self._debug_log(f"Error: DEBUG: [LOCK_RELEASE_ERROR] 释放锁时出错: {e}")
    
    def start_manager(self):
        """跨进程窗口管理器，无需启动线程"""
        self._debug_log("🏗️ DEBUG: [CROSS_PROCESS_WINDOW_MANAGER] 跨进程窗口管理器启动成功")
    
    def request_window(self, title, command_text, timeout_seconds=3600):
        """
        请求显示窗口 - 改进的跨进程锁管理
        
        Args:
            title (str): 窗口标题
            command_text (str): 命令文本
            timeout_seconds (int): 超时时间
            
        Returns:
            dict: 用户操作结果
        """
        request_id = f"req_{int(time.time() * 1000)}_{os.getpid()}_{threading.get_ident()}"
        
        # 尝试获取改进的跨进程锁
        if not self._acquire_lock(request_id):
            return {
                "action": "error", 
                "message": "无法获取窗口锁，可能有其他窗口正在显示"
            }
        
        try:
            # 创建窗口请求
            window_request = {
                'request_id': request_id,
                'title': title,
                'command_text': command_text,
                'timeout_seconds': timeout_seconds,
                'process_id': os.getpid(),
                'thread_id': threading.get_ident()
            }
            
            # 创建和显示窗口
            result = self._create_and_show_window(window_request)
            self._debug_log(f"DEBUG: [WINDOW_COMPLETED] 进程 {os.getpid()} 窗口完成: {request_id}, action: {result.get('action')}")
            
            return result
            
        except Exception as e:
            error_msg = f"窗口创建失败: {str(e)}"
            self._debug_log(f"Error: DEBUG: [WINDOW_ERROR] 进程 {os.getpid()} 窗口错误: {request_id}, error: {str(e)}")
            return {"action": "error", "message": error_msg}
        finally:
            # 确保释放锁
            self._release_lock()
    
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
    
    # 获取父进程PID（由父进程传入）
    parent_pid = PARENT_PID_PLACEHOLDER
    
    
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
            f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_CREATED] 窗口创建成功 - WINDOW_ID_PLACEHOLDER (PID={}, 父进程PID={})\\n".format(timestamp, os.getpid(), parent_pid))
            f.flush()
    except:
        pass
    
    # 父进程监控函数
    def check_parent_alive():
        try:
            import psutil
            # 检查父进程是否还存活
            if not psutil.pid_exists(parent_pid):
                try:
                    with open(debug_file, "a", encoding="utf-8") as f:
                        timestamp = time.time() - 1757413752.714440
                        f.write("🪟 DEBUG: [{:.3f}s] [TKINTER_WINDOW_DESTROYED] 窗口销毁 - 父进程被kill - WINDOW_ID_PLACEHOLDER\\n".format(timestamp))
                        f.flush()
                except:
                    pass
                result.update({"action": "parent_killed"})
                root.destroy()
                return
            # 每1秒检查一次
            root.after(1000, check_parent_alive)
        except Exception as e:
            # 出错时继续监控
            root.after(1000, check_parent_alive)
    
    # 启动父进程监控
    root.after(1000, check_parent_alive)
    
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
            else:
        except Exception as e:
    
    # 带focus计数的聚焦函数
    def force_focus_with_count(play_sound=True):
        global focus_count, button_clicked
        
        focus_count += 1
        force_focus()
        
        # 只有在需要时才播放音效
        if play_sound:
            try:
                import threading
                threading.Thread(target=play_bell_in_subprocess, daemon=True).start()
                root.after(100, lambda: trigger_copy_button())
            except Exception:
                pass
        else:
            # 不播放音效时，仍然触发复制按钮
            try:
                root.after(100, lambda: trigger_copy_button())
            except Exception:
                pass
    
    # 设置窗口置顶并初始聚焦（第1次，播放音效）
    root.attributes('-topmost', True)
    force_focus_with_count(play_sound=True)
    
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
    
    #复制指令按钮
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
    
    # 直接反馈按钮（第二个位置）- 初始禁用状态
    feedback_btn = tk.Button(
        button_frame, 
        text="⏳等待激活", 
        command=direct_feedback,
        font=("Arial", 9),
        bg="#CCCCCC",  # 灰色表示禁用
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2,
        state=tk.DISABLED  # 初始禁用
    )
    feedback_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 执行完成按钮（最右边）- 初始禁用状态
    complete_btn = tk.Button(
        button_frame, 
        text="⏳等待激活", 
        command=execution_completed,
        font=("Arial", 9, "bold"),
        bg="#CCCCCC",  # 灰色表示禁用
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2,
        state=tk.DISABLED  # 初始禁用
    )
    complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 设置焦点到完成按钮
    complete_btn.focus_set()
    
    # 按钮激活状态标志
    buttons_activated = False
    
    # 统一的按钮激活函数
    def activate_buttons(activation_source, play_sound=True):
        """激活按钮的统一函数"""
        global buttons_activated
        
        if buttons_activated:
            return  # 已经激活过了
            
        buttons_activated = True
        
        
        # 启用直接反馈按钮
        feedback_btn.config(
            text="💬直接反馈",
            bg="#FF9800",
            fg="white",
            state=tk.NORMAL
        )
        
        # 启用执行完成按钮
        complete_btn.config(
            text="✅执行完成",
            bg="#4CAF50",
            fg="white",
            state=tk.NORMAL
        )
        
        # 播放音效（如果需要）
        if play_sound:
            try:
                import threading
                threading.Thread(target=play_bell_in_subprocess, daemon=True).start()
            except Exception:
                pass
        
        
        # 记录到debug文件
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                import time
                timestamp = time.time() - 1757413752.714440
                f.write("🎯 DEBUG: [{:.3f}s] [BUTTON_ACTIVATION] 按钮激活 - 来源: {} - WINDOW_ID_PLACEHOLDER\\n".format(timestamp, activation_source))
                f.flush()
        except:
            pass
    
    # 全局按键监听器
    global_listener = None
    
    # 启动pynput全局监听器
    def start_global_listener():
        """启动pynput全局按键监听器"""
        global global_listener, buttons_activated
        
        try:
            from pynput import keyboard
            
            def on_press(key):
                """全局按键按下回调"""
                try:
                    if buttons_activated:
                        return  # 已经激活了，不需要继续监听
                    
                    # 检查是否是Command键
                    key_name = getattr(key, 'name', str(key))
                    
                    # macOS Command键检测
                    if key_name in ['cmd', 'cmd_l', 'cmd_r'] or (hasattr(key, 'vk') and key.vk in [55, 54]):
                        activate_buttons("全局Command键", play_sound=False)  # 不播放音效
                        
                    # Windows/Linux Control键检测
                    elif key_name in ['ctrl', 'ctrl_l', 'ctrl_r']:
                        activate_buttons("全局Control键", play_sound=False)  # 不播放音效
                        
                except Exception as e:
            
            # 创建监听器
            global_listener = keyboard.Listener(on_press=on_press)
            global_listener.start()
            
            
        except Exception as e:
    
    # 启动全局监听器
    start_global_listener()
    
    # Command键检测功能（窗口焦点方案）
    def on_key_press(event):
        """处理按键按下事件"""
        global buttons_activated
        
        if buttons_activated:
            return  # 已经激活了
        
        # 记录按键事件到debug
        key_info = f"keysym='{event.keysym}', keycode={event.keycode}, state={event.state}"
        
        try:
            with open(debug_file, "a", encoding="utf-8") as f:
                import time
                timestamp = time.time() - 1757413752.714440
                f.write("⌨️ DEBUG: [{:.3f}s] [KEY_PRESS] 按键检测: {} - WINDOW_ID_PLACEHOLDER\\n".format(timestamp, key_info))
                f.flush()
        except:
            pass
        
        # 检查是否是Command键（Meta键）- macOS
        if event.keysym in ['Meta_L', 'Meta_R', 'Cmd_L', 'Cmd_R']:
            activate_buttons("Command键按下", play_sound=False)  # 不播放音效
            return
            
        # 检查是否是Control键 - Windows/Linux备用
        if event.keysym in ['Control_L', 'Control_R']:
            activate_buttons("Control键按下", play_sound=False)  # 不播放音效
            return
            
        # 检查修饰键状态位
        if event.state & 0x8:  # Command/Meta键状态位 (macOS)
            activate_buttons("Command键状态位", play_sound=False)  # 不播放音效
            return
            
        if event.state & 0x4:  # Control键状态位 (Windows/Linux)
            activate_buttons("Control键状态位", play_sound=False)  # 不播放音效
            return
        
        # 手动激活快捷键：空格键或Enter键
        if event.keysym in ['space', 'Return']:
            activate_buttons(f"手动激活({event.keysym})", play_sound=True)
            return
    
    # 组合键检测功能
    def on_combination_key(event):
        """处理组合键事件"""
        global buttons_activated
        
        if buttons_activated:
            return  # 已经激活了
        
        
        # 检查是否是Command+任意键或Ctrl+任意键
        if hasattr(event, 'state'):
            if event.state & 0x8:  # Command/Meta键
                activate_buttons("Command组合键", play_sound=False)  # 不播放音效
                return
            elif event.state & 0x4:  # Control键
                activate_buttons("Control组合键", play_sound=False)  # 不播放音效
                return
    
    def on_key_release(event):
        """处理按键释放事件"""
        # 记录按键释放事件
        key_info = f"keysym='{event.keysym}', keycode={event.keycode}"
    
    # 10秒自动激活功能（保底方案）
    def auto_activate_buttons():
        """10秒后自动激活按钮（静默激活，无音效）"""
        global buttons_activated
        
        if buttons_activated:
            return  # 已经激活过了
            
        activate_buttons("10秒自动激活", play_sound=False)
    
    # 设置10秒定时器
    root.after(10000, auto_activate_buttons)
    
    # 绑定键盘事件（窗口焦点方案）
    
    # 绑定窗口按键事件（需要焦点）
    root.bind('<KeyPress>', on_key_press)
    root.bind('<KeyRelease>', on_key_release)
    
    # 绑定Command键的各种可能事件（macOS）
    root.bind('<Meta_L>', lambda e: on_key_press(e))
    root.bind('<Meta_R>', lambda e: on_key_press(e))
    root.bind('<KeyPress-Meta_L>', lambda e: on_key_press(e))
    root.bind('<KeyPress-Meta_R>', lambda e: on_key_press(e))
    
    # 绑定Control键（Windows/Linux备用）
    root.bind('<Control_L>', lambda e: on_key_press(e))
    root.bind('<Control_R>', lambda e: on_key_press(e))
    root.bind('<KeyPress-Control_L>', lambda e: on_key_press(e))
    root.bind('<KeyPress-Control_R>', lambda e: on_key_press(e))
    
    # 绑定组合键（Command+任意键，Ctrl+任意键）
    combination_keys = [
        '<Command-v>', '<Command-V>', '<Command-c>', '<Command-C>',  # Command组合键
        '<Control-v>', '<Control-V>', '<Control-c>', '<Control-C>',  # Ctrl组合键
        '<Meta-v>', '<Meta-V>', '<Meta-c>', '<Meta-C>',              # Meta组合键
        '<Command-Key>', '<Control-Key>', '<Meta-Key>'               # 通用组合键
    ]
    
    for combo in combination_keys:
        try:
            root.bind(combo, on_combination_key)
        except Exception as e:
    
    # 定期强制获取焦点（每5秒一次）
    def periodic_focus():
        """定期强制获取焦点"""
        global buttons_activated
        if not buttons_activated:  # 只有在按钮未激活时才尝试获取焦点
            try:
                root.focus_force()
                root.lift()
            except Exception as e:
                pass
        
        # 5秒后再次执行
        root.after(5000, periodic_focus)
    
    # 确保窗口能接收键盘事件
    root.focus_set()
    
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
    
    # 清理函数
    def cleanup_resources():
        """清理资源"""
        global global_listener
        try:
            if global_listener:
                global_listener.stop()
        except Exception as e:
    
    # 绑定窗口关闭事件
    def on_window_closing():
        cleanup_resources()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_window_closing)
    
    # 运行窗口
    try:
        root.mainloop()
    finally:
        cleanup_resources()
    
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
        subprocess_script = subprocess_script.replace("PARENT_PID_PLACEHOLDER", str(os.getpid()))
        
        # 使用Popen来获得更好的进程控制
        try:
            # 启动子进程，创建新的进程组便于管理
            process = subprocess.Popen(
                ['python', '-c', subprocess_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Unix系统创建新进程组
            )
            
            self._debug_log(f"🪟 DEBUG: [SUBPROCESS_STARTED] 启动窗口子进程: PID={process.pid}, window_id: {window_id}")
            
            # 将进程添加到活跃进程列表
            self.active_processes[window_id] = process
            
            # 统计当前tkinter窗口数量
            time.sleep(0.5)  # 等待窗口进程启动
            window_count = self._count_tkinter_windows()
            self._debug_log(f"📊 DEBUG: [WINDOW_COUNT_AFTER_CREATE] 窗口创建后，当前远端指令tkinter窗口总数: {window_count}")
            
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
                    self._debug_log(f"Error: DEBUG: [SUBPROCESS_CLEANUP_ERROR] 清理子进程失败: {cleanup_error}")
                
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
    
    def _count_tkinter_windows(self):
        """统计当前GDS tkinter窗口数量"""
        count = 0
        try:
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                    cmdline_str = ' '.join(cmdline)
                    # 检测GDS相关的tkinter窗口进程
                    if ('python' in cmdline_str.lower() and 
                        ('-c' in cmdline_str or 'tkinter' in cmdline_str.lower()) and
                        ('Google Drive Shell' in cmdline_str or 'root.title' in cmdline_str)):
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return count
    
    def cleanup_windows(self, force=False):
        """
        手动清理窗口 - 支持跨进程清理
        
        Args:
            force (bool): 是否使用强制清理模式
        """
        if force:
            self._debug_log("🚨 DEBUG: [MANUAL_FORCE_CLEANUP] 手动强制清理所有窗口")
            self._force_cleanup_all_processes()
        else:
            self._debug_log("🧹 DEBUG: [MANUAL_CLEANUP] 手动清理所有窗口")
            self._cleanup_all_processes()
        
        # 额外执行跨进程清理
        self._cross_process_cleanup(force=force)
        
        self._release_lock()
    
    def _cross_process_cleanup(self, force=False):
        """跨进程清理 - 清理所有GDS相关的tkinter窗口"""
        try:
            import psutil
            cleaned_count = 0
            
            self._debug_log(f"🌐 DEBUG: [CROSS_PROCESS_CLEANUP] 开始跨进程清理，force={force}")
            
            for proc in psutil.process_iter(['pid', 'cmdline', 'ppid']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    cmdline_str = ' '.join(cmdline)
                    
                    # 检测GDS相关的tkinter窗口进程
                    if ('python' in cmdline_str.lower() and 
                        ('-c' in cmdline_str or 'tkinter' in cmdline_str.lower()) and
                        ('Google Drive Shell' in cmdline_str or 'root.title' in cmdline_str or 
                         'tkinter' in cmdline_str)):
                        
                        self._debug_log(f"🌐 DEBUG: [CROSS_PROCESS_FOUND] 发现tkinter进程: PID={proc.info['pid']}")
                        
                        if force:
                            # 强制清理：立即杀死
                            proc.kill()
                            self._debug_log(f"🚨 DEBUG: [CROSS_PROCESS_KILLED] 强制杀死进程: PID={proc.info['pid']}")
                        else:
                            # 温和清理：先尝试terminate
                            proc.terminate()
                            self._debug_log(f"🧹 DEBUG: [CROSS_PROCESS_TERMINATED] 温和终止进程: PID={proc.info['pid']}")
                        
                        cleaned_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    self._debug_log(f"Error: DEBUG: [CROSS_PROCESS_ERROR] 清理进程失败: {e}")
            
            if cleaned_count > 0:
                self._debug_log(f"🌐 DEBUG: [CROSS_PROCESS_COMPLETE] 跨进程清理了 {cleaned_count} 个tkinter进程")
            else:
                self._debug_log("🌐 DEBUG: [CROSS_PROCESS_NONE] 没有找到需要清理的tkinter进程")
                
        except Exception as e:
            self._debug_log(f"Error: DEBUG: [CROSS_PROCESS_CLEANUP_ERROR] 跨进程清理失败: {e}")
    
    def get_active_windows_count(self):
        """获取当前活跃窗口数量 - 跨进程统计"""
        # 本进程的窗口数量
        local_count = 0
        if hasattr(self, 'active_processes'):
            for window_id, process in list(self.active_processes.items()):
                try:
                    if process.poll() is None:  # 进程还在运行
                        local_count += 1
                    else:
                        # 进程已结束，从列表中移除
                        self.active_processes.pop(window_id, None)
                except Exception:
                    # 进程可能已经不存在，移除它
                    self.active_processes.pop(window_id, None)
        
        # 跨进程统计所有GDS tkinter窗口
        system_count = 0
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    cmdline_str = ' '.join(cmdline)
                    
                    # 检测GDS相关的tkinter窗口进程
                    if ('python' in cmdline_str.lower() and 
                        ('-c' in cmdline_str or 'tkinter' in cmdline_str.lower()) and
                        ('Google Drive Shell' in cmdline_str or 'root.title' in cmdline_str or 
                         'tkinter' in cmdline_str)):
                        system_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        
        # 返回系统级统计（更准确）
        return system_count
    
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
