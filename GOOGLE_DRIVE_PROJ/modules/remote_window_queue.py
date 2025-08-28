"""
远程命令窗口队列管理器
实现全局锁机制，确保一次只产生一个remote window，避免多个测试同时运行时的冲突
"""

import json
import time
import threading
import os
import fcntl
import errno
from pathlib import Path

# 全局时间戳基准点
_debug_start_time = None

def get_global_timestamp():
    """获取相对于调试开始时间的时间戳"""
    global _debug_start_time
    if _debug_start_time is None:
        _debug_start_time = time.time()
    return f"{time.time() - _debug_start_time:.3f}s"

def debug_log(message):
    """写入调试信息到文件"""
    try:
        # 写入到tmp文件夹中的调试文件
        current_dir = Path(__file__).parent.parent.parent
        debug_file = current_dir / "tmp" / "queue_debug_new.txt"
        debug_file.parent.mkdir(exist_ok=True)
        
        with open(debug_file, 'a', encoding='utf-8') as f:
            timestamp = time.strftime('%H:%M:%S.%f')[:-3]  # 精确到毫秒
            f.write(f"[{timestamp}] {message}\n")
        
        # 同时输出到控制台（可选）
        print(message)
    except Exception as e:
        print(f"Debug logging error: {e}")

class RemoteWindowQueue:
    """远程命令窗口队列管理器"""
    
    def __init__(self, lock_file_path=None):
        if lock_file_path is None:
            # 默认锁文件路径在GOOGLE_DRIVE_DATA目录下
            current_dir = Path(__file__).parent.parent
            lock_file_path = current_dir / ".." / "GOOGLE_DRIVE_DATA" / "remote_window_queue.json"
        
        self.lock_file_path = Path(lock_file_path)
        self.file_lock_path = self.lock_file_path.with_suffix('.lock')  # 文件锁
        self.local_lock = threading.Lock()  # 本地线程锁
        self.timeout_hours = 1  # 1小时超时（作为后备机制）
        self._lock_file_handle = None
    
    def _acquire_file_lock(self, timeout=30):
        """获取文件锁（跨进程）"""
        try:
            # 确保锁文件目录存在
            self.file_lock_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 打开锁文件
            self._lock_file_handle = open(self.file_lock_path, 'w')
            
            # 尝试获取排他锁，带超时
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    debug_log(f"🔒 DEBUG: [{get_global_timestamp()}] [FILE_LOCK] 成功获取文件锁: {self.file_lock_path}")
                    return True
                except (IOError, OSError) as e:
                    if e.errno == errno.EAGAIN or e.errno == errno.EACCES:
                        # 锁被其他进程占用，等待后重试
                        time.sleep(0.1)
                        continue
                    else:
                        raise
            
            # 超时未获取到锁
            debug_log(f"⏰ DEBUG: [{get_global_timestamp()}] [FILE_LOCK_TIMEOUT] 获取文件锁超时: {timeout}s")
            self._release_file_lock()
            return False
            
        except Exception as e:
            debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [FILE_LOCK_ERROR] 获取文件锁失败: {e}")
            self._release_file_lock()
            return False
    
    def _release_file_lock(self):
        """释放文件锁"""
        try:
            if self._lock_file_handle:
                fcntl.flock(self._lock_file_handle.fileno(), fcntl.LOCK_UN)
                self._lock_file_handle.close()
                self._lock_file_handle = None
                debug_log(f"🔓 DEBUG: [{get_global_timestamp()}] [FILE_LOCK] 释放文件锁: {self.file_lock_path}")
        except Exception as e:
            debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [FILE_LOCK_RELEASE_ERROR] 释放文件锁失败: {e}")
            if self._lock_file_handle:
                try:
                    self._lock_file_handle.close()
                except:
                    pass
                self._lock_file_handle = None
    
    def _read_queue_file(self):
        """读取队列文件"""
        try:
            if self.lock_file_path.exists():
                with open(self.lock_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "window_queue": [],  # 统一队列：第一个元素是current window，其余是waiting
                    "last_update": time.time(),
                    "completed_windows_count": 0,
                    "last_window_open_time": 0,  # 追踪上次窗口开启时间
                    "description": "远程窗口队列状态文件 - 统一队列设计"
                }
        except (json.JSONDecodeError, IOError):
            # 文件损坏或读取失败，返回默认状态
            return {
                "window_queue": [],  # 统一队列：第一个元素是current window，其余是waiting
                "last_update": time.time(),
                "completed_windows_count": 0,
                "last_window_open_time": 0,  # 追踪上次窗口开启时间
                "description": "远程窗口队列状态文件 - 统一队列设计"
            }
    
    def _write_queue_file(self, queue_data):
        """写入队列文件"""
        try:
            queue_data["last_update"] = time.time()
            # 确保目录存在
            self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.lock_file_path, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"⚠️ 警告：无法写入队列文件: {e}")
    
    def _is_thread_alive(self, thread_id):
        """检查线程是否还存活"""
        try:
            import threading
            # 获取所有活跃线程
            active_threads = threading.enumerate()
            for thread in active_threads:
                if hasattr(thread, 'ident') and thread.ident == thread_id:
                    return thread.is_alive()
            return False
        except Exception:
            # 如果无法检查，保守地认为线程还存活
            return True
    
    def _cleanup_expired_windows(self, queue_data):
        """清理超时和死线程的窗口 - 适配统一队列结构"""
        current_time = time.time()
        timeout_seconds = self.timeout_hours * 3600
        cleaned_any = False
        
        window_queue = queue_data.get("window_queue", [])
        if not window_queue:
            return cleaned_any
            
        original_count = len(window_queue)
        cleaned_queue = []
        
        for i, window in enumerate(window_queue):
            window_id = window.get("id", "unknown")
            thread_id = window.get("thread_id")
            is_current = (i == 0)  # 第一个元素是当前窗口
            
            # 对于当前窗口，检查start_time；对于等待窗口，检查request_time
            if is_current:
                check_time = window.get("start_time", window.get("request_time", 0))
                time_label = "当前窗口"
            else:
                check_time = window.get("request_time", 0)
                time_label = "等待队列"
            
            # 检查超时
            if current_time - check_time > timeout_seconds:
                print(f"🕐 {time_label}中超时请求，移除: {window_id}")
                cleaned_any = True
                continue
            
            # 检查线程是否还存活
            if thread_id and not self._is_thread_alive(thread_id):
                print(f"💀 {time_label}中死线程，移除: {window_id} (thread_id: {thread_id})")
                cleaned_any = True
                continue
                
            # 线程还存活且未超时，保留
            cleaned_queue.append(window)
        
        queue_data["window_queue"] = cleaned_queue
        
        cleaned_count = original_count - len(cleaned_queue)
        if cleaned_count > 0:
            print(f"🧹 清理了 {cleaned_count} 个无效的窗口请求")
            
        return cleaned_any
    
    def _get_current_window(self, queue_data):
        """
        获取当前窗口（队列的第一个元素）
        
        Args:
            queue_data (dict): 队列数据
            
        Returns:
            dict or None: 当前窗口信息，如果队列为空则返回None
        """
        window_queue = queue_data.get("window_queue", [])
        return window_queue[0] if window_queue else None
    
    def _get_waiting_windows(self, queue_data):
        """
        获取等待中的窗口（队列的第二个及后续元素）
        
        Args:
            queue_data (dict): 队列数据
            
        Returns:
            list: 等待中的窗口列表
        """
        window_queue = queue_data.get("window_queue", [])
        return window_queue[1:] if len(window_queue) > 1 else []
    
    def _add_window_to_queue(self, queue_data, window_info):
        """
        将窗口添加到队列末尾
        
        Args:
            queue_data (dict): 队列数据
            window_info (dict): 窗口信息
        """
        if "window_queue" not in queue_data:
            queue_data["window_queue"] = []
        queue_data["window_queue"].append(window_info)
    
    def _remove_current_window(self, queue_data):
        """
        移除当前窗口（队列的第一个元素）
        
        Args:
            queue_data (dict): 队列数据
            
        Returns:
            dict or None: 被移除的窗口信息
        """
        window_queue = queue_data.get("window_queue", [])
        if window_queue:
            return queue_data["window_queue"].pop(0)
        return None
    
    def _is_next_in_queue(self, window_id):
        """
        检查指定的窗口是否是队列中的下一个（第二个元素，因为第一个是current window）
        
        Args:
            window_id (str): 窗口ID
            
        Returns:
            bool: True如果是队列中的下一个窗口
        """
        try:
            queue_data = self._read_queue_file()
            window_queue = queue_data.get("window_queue", [])
            
            if len(window_queue) >= 2:
                next_window_id = window_queue[1].get("id")  # 第二个元素是下一个等待的窗口
                is_next = (next_window_id == window_id)
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [NEXT_CHECK] 检查是否为下一个窗口: {window_id} == {next_window_id} -> {is_next}")
                return is_next
            else:
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [NEXT_CHECK] 队列长度不足，无下一个窗口 (长度: {len(window_queue)})")
                return False
        except Exception as e:
            debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [NEXT_CHECK_ERROR] 检查下一个窗口失败: {e}")
            return False
    
    def request_window_slot(self, window_id, timeout_seconds=3600):
        """
        请求窗口槽位
        
        Args:
            window_id (str): 窗口唯一标识符
            timeout_seconds (int): 最大等待时间（秒）
            
        Returns:
            bool: 是否获得了窗口槽位
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            # 使用文件锁确保跨进程同步
            if not self._acquire_file_lock(timeout=10):
                debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [FILE_LOCK_FAILED] 无法获取文件锁，等待重试: {window_id}")
                time.sleep(0.5)
                continue
            
            try:
                queue_data = self._read_queue_file()
                self._cleanup_expired_windows(queue_data)
                
                # 检查是否可以立即获得槽位（使用统一队列）
                current_window = self._get_current_window(queue_data)
                debug_log(f"🔍 DEBUG: [{get_global_timestamp()}] [SLOT_CHECK] 检查槽位可用性 - current_window: {current_window is not None}, status: {current_window.get('status') if current_window else 'None'}")
                
                # 自动清理已完成的窗口
                if current_window and current_window.get("status") == "completed":
                    debug_log(f"🧹 DEBUG: [{get_global_timestamp()}] [AUTO_CLEANUP] 自动移除已完成的窗口: {current_window['id']}")
                    self._remove_current_window(queue_data)
                    queue_data["completed_windows_count"] = queue_data.get("completed_windows_count", 0) + 1
                    current_window = self._get_current_window(queue_data)  # 重新获取当前窗口
                    debug_log(f"🔄 DEBUG: [{get_global_timestamp()}] [AUTO_PROMOTE] 队列自动推进，新的当前窗口: {current_window['id'] if current_window else 'None'}")
                
                # 检查请求的窗口是否已经是队列中的第一个（当前窗口）
                if current_window and current_window.get("id") == window_id:
                    # 如果请求的窗口已经是当前窗口，检查状态
                    if current_window.get("status") == "waiting":
                        # 将状态从waiting改为active，并记录开始时间
                        debug_log(f"🔄 DEBUG: [{get_global_timestamp()}] [PROMOTE_TO_ACTIVE] 窗口从等待状态提升为活跃: {window_id}")
                        
                        # 强制执行5秒最小间隔约束
                        last_window_time = queue_data.get("last_window_open_time", 0)
                        current_time = time.time()
                        time_since_last = current_time - last_window_time
                        
                        if time_since_last < 5.0 and last_window_time > 0:
                            debug_log(f"⏰ DEBUG: [{get_global_timestamp()}] [MIN_5SEC_INTERVAL] 强制5秒间隔：距上次窗口 {time_since_last:.2f}s < 5.0s，继续等待...")
                            # 不激活，继续等待
                            pass
                        else:
                            # 激活当前窗口
                            queue_data["window_queue"][0]["status"] = "active"
                            queue_data["window_queue"][0]["start_time"] = current_time
                            queue_data["window_queue"][0]["heartbeat"] = False  # 初始化布尔心跳
                            queue_data["last_window_open_time"] = current_time
                            self._write_queue_file(queue_data)
                            debug_log(f"🚀 DEBUG: [{get_global_timestamp()}] [QUEUE_ACQUIRED] 窗口激活为当前槽位: {window_id}, thread: {threading.get_ident()}, 距上次: {time_since_last:.2f}s")
                            
                            # 启动心跳更新线程
                            self.start_heartbeat_updater(window_id)
                            return True
                    elif current_window.get("status") == "active":
                        # 已经是活跃状态，直接返回成功
                        debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [ALREADY_ACTIVE] 窗口已经是活跃状态: {window_id}")
                        return True
                
                # 检查是否队列中第一个窗口是waiting状态但不是当前请求的窗口
                # 这种情况下，第一个窗口应该被自动激活
                elif current_window and current_window.get("status") == "waiting":
                    # 强制执行5秒最小间隔约束
                    last_window_time = queue_data.get("last_window_open_time", 0)
                    current_time = time.time()
                    time_since_last = current_time - last_window_time
                    
                    if time_since_last >= 5.0 or last_window_time == 0:
                        # 自动激活队列中的第一个等待窗口
                        debug_log(f"🔄 DEBUG: [{get_global_timestamp()}] [AUTO_ACTIVATE_FIRST] 自动激活队列首位等待窗口: {current_window['id']}")
                        current_window["status"] = "active"
                        current_window["start_time"] = current_time
                        current_window["heartbeat"] = False  # 初始化布尔心跳
                        queue_data["last_window_open_time"] = current_time
                        self._write_queue_file(queue_data)
                        
                        # 启动心跳更新线程
                        self.start_heartbeat_updater(current_window['id'])
                        debug_log(f"🚀 DEBUG: [{get_global_timestamp()}] [FIRST_ACTIVATED] 队列首位窗口已激活: {current_window['id']}")
                        
                        # 如果刚好激活的就是请求的窗口，直接返回成功
                        if current_window['id'] == window_id:
                            return True
                
                elif current_window is None:
                    # 队列为空，可以立即获得槽位
                    current_time = time.time()
                    last_window_time = queue_data.get("last_window_open_time", 0)
                    time_since_last = current_time - last_window_time
                    
                    if time_since_last < 5.0 and last_window_time > 0:
                        debug_log(f"⏰ DEBUG: [{get_global_timestamp()}] [MIN_5SEC_INTERVAL] 强制5秒间隔：距上次窗口 {time_since_last:.2f}s < 5.0s，继续等待...")
                        # 不获得槽位，继续等待
                        pass
                    else:
                        # 创建新的窗口信息并添加到队列首位
                        new_window = {
                        "id": window_id,
                            "start_time": current_time,
                            "thread_id": threading.get_ident(),
                            "status": "active",
                            "heartbeat": False  # 初始化布尔心跳
                                                }
                        queue_data["window_queue"] = [new_window]
                        queue_data["last_window_open_time"] = current_time
                        self._write_queue_file(queue_data)
                        debug_log(f"🚀 DEBUG: [{get_global_timestamp()}] [QUEUE_ACQUIRED] 立即获得窗口槽位（空队列）: {window_id}, thread: {threading.get_ident()}, 距上次: {time_since_last:.2f}s")
                        
                        # 启动心跳更新线程
                        self.start_heartbeat_updater(window_id)
                        return True
                else:
                    debug_log(f"⏳ DEBUG: [{get_global_timestamp()}] [SLOT_BUSY] 槽位忙碌 - current_window: {current_window['id']}, status: {current_window.get('status')}, start_time: {current_window.get('start_time')}")
                
                # 检查是否已经在队列中（避免重复请求）
                window_queue = queue_data.get("window_queue", [])
                is_already_waiting = any(w["id"] == window_id for w in window_queue)
                if not is_already_waiting:
                    # 添加到等待队列（队列末尾）
                    new_waiting_window = {
                        "id": window_id,
                        "request_time": time.time(),
                        "thread_id": threading.get_ident(),
                        "status": "waiting",
                        "heartbeat": False  # 初始化布尔心跳
                    }
                    self._add_window_to_queue(queue_data, new_waiting_window)
                    self._write_queue_file(queue_data)
                    debug_log(f"⏳ DEBUG: [{get_global_timestamp()}] [QUEUE_WAITING] 加入等待队列: {window_id}, 位置: {len(queue_data.get('window_queue', []))}, thread: {threading.get_ident()}")
                    
                    # 启动心跳检查线程（等待窗口检查当前窗口的心跳）
                    self.start_heartbeat_checker(window_id)
                    
                    # 等待窗口也需要更新自己的心跳，以便后续窗口检测
                    self.start_heartbeat_updater(window_id)
                
                # 心跳通过自动线程管理
                    
            finally:
                # 确保释放文件锁
                self._release_file_lock()
            
            # 心跳检查通过自动线程管理
            
            # 等待一段时间后重试（减少等待时间以更快响应）
            time.sleep(0.5)  # 更快响应 
        
        debug_log(f"⏰ DEBUG: [{get_global_timestamp()}] [QUEUE_TIMEOUT] 等待超时: {window_id}, thread: {threading.get_ident()}")
        return False
    
    def release_window_slot(self, window_id):
        """
        释放窗口槽位
        
        Args:
            window_id (str): 窗口唯一标识符
        """
        # 使用文件锁确保跨进程同步
        if not self._acquire_file_lock(timeout=10):
            debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [FILE_LOCK_FAILED] 释放窗口槽位时无法获取文件锁: {window_id}")
            return
            
        try:
            queue_data = self._read_queue_file()
            # 注意：不依赖超时机制，直接处理窗口完成
            # self._cleanup_expired_windows(queue_data)  # 注释掉自动清理，避免干扰
            
            # 检查是否是当前窗口（队列第一个元素）
            current_window = self._get_current_window(queue_data)
            if (current_window and current_window["id"] == window_id):
                debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [QUEUE_RELEASE] 释放当前窗口槽位: {window_id}, thread: {threading.get_ident()}")
                
                # 移除当前窗口
                self._remove_current_window(queue_data)
                
                # 增加完成计数器
                queue_data["completed_windows_count"] = queue_data.get("completed_windows_count", 0) + 1
                debug_log(f"📊 DEBUG: [{get_global_timestamp()}] [COUNTER] 窗口完成计数: {queue_data['completed_windows_count']} - window_id: {window_id}")
                
                # 检查是否有等待的窗口需要激活
                next_window = self._get_current_window(queue_data)
                if next_window and next_window.get("status") == "waiting":
                    next_window["status"] = "active"
                    next_window["start_time"] = time.time()
                    if "heartbeat" not in next_window:
                        next_window["heartbeat"] = False
                    debug_log(f"🔄 DEBUG: [{get_global_timestamp()}] [QUEUE_NEXT] 下一个窗口获得槽位: {next_window['id']}, thread: {next_window['thread_id']}")
                    
                    # 启动心跳更新线程
                    self.start_heartbeat_updater(next_window['id'])
                
                self._write_queue_file(queue_data)
                debug_log(f"🎯 DEBUG: [{get_global_timestamp()}] [IMMEDIATE_RELEASE] 窗口槽位立即释放完成 - window_id: {window_id}")
            else:
                # 从队列中移除（不是当前窗口）
                window_queue = queue_data.get("window_queue", [])
                original_count = len(window_queue)
                queue_data["window_queue"] = [
                    w for w in window_queue 
                    if w["id"] != window_id
                ]
                if len(queue_data["window_queue"]) < original_count:
                    debug_log(f"🚫 DEBUG: [{get_global_timestamp()}] [QUEUE_REMOVE] 从队列移除: {window_id}, thread: {threading.get_ident()}")
                    self._write_queue_file(queue_data)
                else:
                    debug_log(f"⚠️ DEBUG: [{get_global_timestamp()}] [QUEUE_NOT_FOUND] 窗口未在队列中找到: {window_id}, thread: {threading.get_ident()}")
        finally:
            # 确保释放文件锁
            self._release_file_lock()
    
    def mark_window_completed(self, window_id):
        """
        标记窗口为已完成，并自动激活下一个等待的窗口
        
        Args:
            window_id (str): 窗口唯一标识符
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            current_window = self._get_current_window(queue_data)
            
            debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [MARK_ATTEMPT] 尝试标记窗口完成: {window_id}")
            debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [MARK_CURRENT] 当前窗口: {current_window['id'] if current_window else 'None'}")
            
            # 检查是否是当前窗口（队列第一个元素）
            if (current_window and current_window["id"] == window_id):
                old_status = current_window.get("status", "unknown")
                # 直接修改队列中的第一个元素
                queue_data["window_queue"][0]["status"] = "completed"
                
                # 增加完成计数器
                queue_data["completed_windows_count"] = queue_data.get("completed_windows_count", 0) + 1
                
                self._write_queue_file(queue_data)
                debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [MARK_COMPLETED] 窗口标记为已完成: {window_id} (状态: {old_status} -> completed), 完成计数: {queue_data['completed_windows_count']}")
                
                # 自动处理队列进展
                self._process_queue_progression(queue_data)
                return True
            else:
                current_id = current_window["id"] if current_window else "None"
                debug_log(f"⚠️ DEBUG: [{get_global_timestamp()}] [MARK_FAILED] 无法标记窗口完成，非当前窗口: {window_id} (当前: {current_id})")
                return False
    
    def _process_queue_progression(self, queue_data):
        """
        处理队列自动进展：移除已完成的窗口，激活下一个等待的窗口
        
        Args:
            queue_data (dict): 队列数据（调用者已持有锁）
        """
        current_window = self._get_current_window(queue_data)
        
        if current_window and current_window.get("status") == "completed":
            debug_log(f"🔄 DEBUG: [{get_global_timestamp()}] [QUEUE_PROGRESSION] 检测到已完成窗口，开始队列进展")
            
            # 移除已完成的窗口
            completed_window = self._remove_current_window(queue_data)
            debug_log(f"🗑️ DEBUG: [{get_global_timestamp()}] [REMOVE_COMPLETED] 移除已完成窗口: {completed_window['id'] if completed_window else 'None'}")
            
            # 检查是否有等待的窗口
            waiting_windows = self._get_waiting_windows(queue_data)
            if waiting_windows:
                # 激活下一个等待的窗口（现在它变成了队列的第一个元素）
                next_window = self._get_current_window(queue_data)
                if next_window and next_window.get("status") == "waiting":
                    next_window["status"] = "active"
                    next_window["start_time"] = time.time()  # 更新开始时间
                    
                    # 初始化心跳
                    if "heartbeat" not in next_window:
                        next_window["heartbeat"] = False
                    
                    debug_log(f"🚀 DEBUG: [{get_global_timestamp()}] [ACTIVATE_NEXT] 激活下一个窗口: {next_window['id']} (waiting -> active)")
                    
                    # 更新窗口开启时间
                    queue_data["last_window_open_time"] = time.time()
                    
                    self._write_queue_file(queue_data)
                    debug_log(f"🎯 DEBUG: [{get_global_timestamp()}] [PROGRESSION_COMPLETE] 队列进展完成，新活跃窗口: {next_window['id']}")
                    
                    # 启动新活跃窗口的心跳更新线程
                    self.start_heartbeat_updater(next_window['id'])
            else:
                debug_log(f"📝 DEBUG: [{get_global_timestamp()}] [NO_WAITING] 没有等待的窗口，队列现在为空")
                self._write_queue_file(queue_data)
    
    # 旧的手动心跳注册方法已删除 - 现在使用自动心跳线程
    
    def update_heartbeat(self, window_id):
        """
        更新心跳（当前窗口调用，设置自己的心跳为true）- 新的布尔心跳设计
        
        Args:
            window_id (str): 当前窗口ID
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            current_window = self._get_current_window(queue_data)
            
            if (current_window and current_window["id"] == window_id):
                old_heartbeat = current_window.get("heartbeat", False)
                current_window["heartbeat"] = True  # 设置为布尔值true
                
                self._write_queue_file(queue_data)
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_UPDATE] 窗口 {window_id} 更新心跳: {old_heartbeat} -> True")
                return True
            else:
                current_id = current_window["id"] if current_window else "None"
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_UPDATE_FAIL] 无法更新心跳 - window_id: {window_id}, current: {current_id}")
            return False
    
    def check_heartbeat_timeout(self, watcher_id):
        """
        检查心跳超时（只有下一个等待窗口检查当前窗口的心跳）- 新的布尔心跳设计
        
        Args:
            watcher_id (str): 监视器窗口ID
            
        Returns:
            bool: True如果当前窗口已经超时（应该被清除）
        """
        # 只有下一个等待的窗口才能检查当前窗口的心跳
        if not self._is_next_in_queue(watcher_id):
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NOT_NEXT] 窗口 {watcher_id} 不是下一个等待窗口，跳过心跳检查")
            return False
            
        with self.local_lock:
            queue_data = self._read_queue_file()
            current_window = self._get_current_window(queue_data)
            
            if current_window:
                current_heartbeat = current_window.get("heartbeat", False)
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECK] 下一个窗口 {watcher_id} 检查当前窗口 {current_window['id']} 心跳: {current_heartbeat}")
                
                # 检查失败次数
                failure_key = f"heartbeat_failures"
                failure_count = current_window.get(failure_key, 0)
                
                if current_heartbeat == True:
                    # 心跳正常，重置为false并清除失败计数
                    current_window["heartbeat"] = False
                    if failure_key in current_window:
                        del current_window[failure_key]
                    self._write_queue_file(queue_data)
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_ALIVE] 心跳正常，重置为False，清除失败计数")
                    return False
                else:
                    # 心跳为false，增加失败计数
                    failure_count += 1
                    current_window[failure_key] = failure_count
                    
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_FAIL_COUNT] 心跳失败次数: {failure_count}/2 - 当前窗口: {current_window['id']}")
                    
                    if failure_count >= 2:  # 连续两次检测失败才清除窗口
                        # 心跳超时，清除当前窗口
                        current_window_id = current_window["id"]
                        debug_log(f"💀 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_TIMEOUT] 连续心跳失败，清除窗口: {current_window_id} (失败次数: {failure_count})")
                        self._remove_current_window(queue_data)
                        self._write_queue_file(queue_data)
                        return True
                    else:
                        # 第一次失败，记录但不清除
                        self._write_queue_file(queue_data)
                        return False
            else:
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NO_CURRENT_CHECK] 没有当前窗口进行心跳检查")
            return False
    
    def start_heartbeat_updater(self, window_id):
        """
        启动心跳更新线程（当前窗口每0.1秒更新心跳为true）
        
        Args:
            window_id (str): 窗口ID
        """
        import threading
        import time
        
        def update_heartbeat_loop():
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_THREAD_START] 启动心跳更新线程: {window_id}")
            while True:
                try:
                    # 检查窗口是否仍然是当前活跃窗口
                    with self.local_lock:
                        queue_data = self._read_queue_file()
                        current_window = self._get_current_window(queue_data)
                        
                        if not current_window or current_window["id"] != window_id:
                            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_THREAD_EXIT] 心跳线程退出，窗口不再活跃: {window_id}")
                            break
                            
                        if current_window.get("status") == "completed":
                            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_THREAD_COMPLETED] 心跳线程退出，窗口已完成: {window_id}")
                            break
                    
                    # 更新心跳
                    success = self.update_heartbeat(window_id)
                    if not success:
                        debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_UPDATE_FAILED] 心跳更新失败，退出线程: {window_id}")
                        break
                    
                    # 等待0.1秒
                    time.sleep(0.1)
                    
                except Exception as e:
                    debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [HEARTBEAT_THREAD_ERROR] 心跳线程异常: {window_id}, 错误: {e}")
                    break
        
        # 启动守护线程
        heartbeat_thread = threading.Thread(target=update_heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_THREAD_CREATED] 心跳线程已创建: {window_id}")
    
    def start_heartbeat_checker(self, watcher_id):
        """
        启动心跳检查线程（等待窗口每0.5秒检查当前窗口心跳）
        
        Args:
            watcher_id (str): 监视器窗口ID
        """
        import threading
        import time
        
        def check_heartbeat_loop():
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_START] 启动心跳检查线程: {watcher_id}")
            while True:
                try:
                    # 检查是否仍在等待队列中
                    with self.local_lock:
                        queue_data = self._read_queue_file()
                        current_window = self._get_current_window(queue_data)
                        
                        # 如果没有当前窗口，退出检查
                        if not current_window:
                            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_NO_CURRENT] 心跳检查线程退出，没有当前窗口: {watcher_id}")
                            break
                        
                        # 如果自己变成了当前窗口，退出检查线程
                        if current_window["id"] == watcher_id:
                            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_ACTIVE] 心跳检查线程退出，自己变成活跃窗口: {watcher_id}")
                            break
                        
                        # 检查是否还在等待队列中
                        waiting_windows = self._get_waiting_windows(queue_data)
                        if not any(w["id"] == watcher_id for w in waiting_windows):
                            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_NOT_WAITING] 心跳检查线程退出，不在等待队列: {watcher_id}")
                            break
                    
                    # 执行心跳检查
                    timeout_detected = self.check_heartbeat_timeout(watcher_id)
                    if timeout_detected:
                        debug_log(f"💀 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_TIMEOUT] 检测到心跳超时，当前窗口已清除: {watcher_id}")
                        # 超时后继续检查，可能有新的当前窗口
                    
                    # 等待0.5秒
                    time.sleep(0.5)
                    
                except Exception as e:
                    debug_log(f"❌ DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_ERROR] 心跳检查线程异常: {watcher_id}, 错误: {e}")
                    break
        
        # 启动守护线程
        checker_thread = threading.Thread(target=check_heartbeat_loop, daemon=True)
        checker_thread.start()
        debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECKER_CREATED] 心跳检查线程已创建: {watcher_id}")
    
    def get_queue_status(self):
        """获取队列状态 - 适配统一队列结构"""
        with self.local_lock:
            queue_data = self._read_queue_file()
            self._cleanup_expired_windows(queue_data)
            
            current_window = self._get_current_window(queue_data)
            waiting_windows = self._get_waiting_windows(queue_data)
            
            return {
                "current_window": current_window,
                "waiting_count": len(waiting_windows),
                "waiting_queue": waiting_windows,
                "completed_windows_count": queue_data.get("completed_windows_count", 0),
                "window_queue": queue_data.get("window_queue", [])  # 添加统一队列信息
            }
    
    def reset_queue(self):
        """重置队列到默认状态，清除所有等待和活跃的窗口"""
        import os
        
        with self.local_lock:
            # 尝试从默认文件读取
            default_file = os.path.join(os.path.dirname(str(self.lock_file_path)), "remote_window_queue_default.json")
            
            if os.path.exists(default_file):
                try:
                    with open(default_file, 'r') as f:
                        default_data = json.load(f)
                    
                    # 更新时间戳 - 适配统一队列结构
                    reset_data = {
                        "window_queue": [],
                        "last_update": time.time(),
                        "completed_windows_count": 0,
                        "last_window_open_time": 0,
                        "description": "远程窗口队列状态文件 - 统一队列设计"
                    }
                    
                    self._write_queue_file(reset_data)
                    print("🔄 队列已重置为默认状态")
                    return True
                except Exception as e:
                    print(f"❌ 读取默认配置失败: {e}")
                    # 如果读取默认文件失败，直接重置
                    self._reset_queue_file()
                    print("🔄 队列已强制重置")
                    return True
            else:
                # 如果没有默认文件，直接重置
                self._reset_queue_file()
                print("🔄 队列已重置（未找到默认配置文件）")
                return True

# 全局队列管理器实例
_global_queue = None

def get_global_queue():
    """获取全局队列管理器实例"""
    global _global_queue
    if _global_queue is None:
        _global_queue = RemoteWindowQueue()
    return _global_queue

def request_window_slot(window_id, timeout_seconds=3600):
    """请求窗口槽位的便捷函数"""
    return get_global_queue().request_window_slot(window_id, timeout_seconds)

def release_window_slot(window_id):
    """释放窗口槽位的便捷函数"""
    return get_global_queue().release_window_slot(window_id)

def mark_window_completed(window_id):
    """标记窗口完成的便捷函数"""
    return get_global_queue().mark_window_completed(window_id)

def update_heartbeat(window_id):
    """更新心跳的便捷函数"""
    return get_global_queue().update_heartbeat(window_id)

def get_queue_status():
    """获取队列状态的便捷函数"""
    return get_global_queue().get_queue_status()

def reset_queue():
    """重置队列的便捷函数"""
    return get_global_queue().reset_queue()
