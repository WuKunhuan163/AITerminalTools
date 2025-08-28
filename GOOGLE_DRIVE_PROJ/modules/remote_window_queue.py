"""
远程命令窗口队列管理器
实现全局锁机制，确保一次只产生一个remote window，避免多个测试同时运行时的冲突
"""

import json
import time
import threading
import os
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
        import os
        log_file = os.path.join(os.path.dirname(__file__), "..", "..", "tmp", "debug_heartbeat.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
            f.flush()
    except Exception as e:
        print(f"DEBUG_LOG_ERROR: {e}")
    # 同时也输出到终端
    print(message)

class RemoteWindowQueue:
    """远程命令窗口队列管理器"""
    
    def __init__(self, lock_file_path=None):
        if lock_file_path is None:
            # 默认锁文件路径在GOOGLE_DRIVE_DATA目录下
            current_dir = Path(__file__).parent.parent
            lock_file_path = current_dir / ".." / "GOOGLE_DRIVE_DATA" / "remote_window_queue.json"
        
        self.lock_file_path = Path(lock_file_path)
        self.local_lock = threading.Lock()  # 本地线程锁
        self.timeout_hours = 1  # 1小时超时（作为后备机制）
    
    def _read_queue_file(self):
        """读取队列文件"""
        try:
            if self.lock_file_path.exists():
                with open(self.lock_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "current_window": None,
                    "waiting_queue": [],
                    "last_update": time.time(),
                    "completed_windows_count": 0
                }
        except (json.JSONDecodeError, IOError):
            # 文件损坏或读取失败，返回默认状态
            return {
                "current_window": None,
                "waiting_queue": [],
                "last_update": time.time(),
                "completed_windows_count": 0
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
        """清理超时和死线程的窗口"""
        current_time = time.time()
        timeout_seconds = self.timeout_hours * 3600
        cleaned_any = False
        
        # 检查当前窗口是否超时或线程已死
        if queue_data["current_window"]:
            window_start_time = queue_data["current_window"].get("start_time", 0)
            thread_id = queue_data["current_window"].get("thread_id")
            window_id = queue_data["current_window"].get("id", "unknown")
            
            # 检查超时
            if current_time - window_start_time > timeout_seconds:
                print(f"🕐 当前窗口超时，释放锁: {window_id}")
                queue_data["current_window"] = None
                cleaned_any = True
            # 检查线程是否还存活
            elif thread_id and not self._is_thread_alive(thread_id):
                print(f"💀 当前窗口线程已死，释放锁: {window_id} (thread_id: {thread_id})")
                queue_data["current_window"] = None
                cleaned_any = True
        
        # 清理等待队列中超时或死线程的请求
        original_count = len(queue_data["waiting_queue"])
        cleaned_queue = []
        
        for window in queue_data["waiting_queue"]:
            request_time = window.get("request_time", 0)
            thread_id = window.get("thread_id")
            window_id = window.get("id", "unknown")
            
            # 检查超时
            if current_time - request_time > timeout_seconds:
                print(f"🕐 等待队列中超时请求，移除: {window_id}")
                continue
            
            # 检查线程是否还存活
            if thread_id and not self._is_thread_alive(thread_id):
                print(f"💀 等待队列中死线程，移除: {window_id} (thread_id: {thread_id})")
                continue
                
            # 线程还存活且未超时，保留
            cleaned_queue.append(window)
        
        queue_data["waiting_queue"] = cleaned_queue
        
        cleaned_count = original_count - len(cleaned_queue)
        if cleaned_count > 0:
            print(f"🧹 清理了 {cleaned_count} 个无效的等待请求")
            cleaned_any = True
            
        return cleaned_any
    
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
            with self.local_lock:
                queue_data = self._read_queue_file()
                # 只在真正需要时进行清理（比如等待了一段时间后）
                if time.time() - start_time > 5:  # 等待5秒后才开始清理检查
                    self._cleanup_expired_windows(queue_data)
                
                # 检查是否可以立即获得槽位
                if (queue_data["current_window"] is None or 
                    queue_data["current_window"].get("status") == "completed"):
                    # 可以立即获得槽位（可能是新槽位或者前一个窗口已完成）
                    if queue_data["current_window"] and queue_data["current_window"].get("status") == "completed":
                        # 增加完成计数器（前一个窗口）
                        queue_data["completed_windows_count"] = queue_data.get("completed_windows_count", 0) + 1
                        debug_log(f"📊 DEBUG: [{get_global_timestamp()}] [COUNTER] 检测到完成窗口，计数: {queue_data['completed_windows_count']}")
                    
                    queue_data["current_window"] = {
                        "id": window_id,
                        "start_time": time.time(),
                        "thread_id": threading.get_ident(),
                        "status": "active",  # 状态字段：active, completed
                        "heartbeat": {}  # 心跳字段：{window_id: "true"/"false"}
                    }
                    self._write_queue_file(queue_data)
                    debug_log(f"🚀 DEBUG: [{get_global_timestamp()}] [QUEUE_ACQUIRED] 立即获得窗口槽位: {window_id}, thread: {threading.get_ident()}")
                    return True
                
                # 检查是否已经在队列中（避免重复请求）
                is_already_waiting = any(w["id"] == window_id for w in queue_data["waiting_queue"])
                if not is_already_waiting:
                    # 添加到等待队列
                    queue_data["waiting_queue"].append({
                        "id": window_id,
                        "request_time": time.time(),
                        "thread_id": threading.get_ident()
                    })
                    self._write_queue_file(queue_data)
                    debug_log(f"⏳ DEBUG: [{get_global_timestamp()}] [QUEUE_WAITING] 加入等待队列: {window_id}, 位置: {len(queue_data['waiting_queue'])}, thread: {threading.get_ident()}")
                
                # 每次循环都尝试注册心跳监视器（确保注册成功）
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECK_CURRENT] 检查当前窗口状态: {queue_data['current_window'] is not None}")
                if queue_data["current_window"]:
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_TRY] 尝试注册心跳监视器: {window_id} -> 当前窗口: {queue_data['current_window']['id']}")
                    result = self._register_heartbeat_watcher_internal(queue_data, window_id)
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_TRY_RESULT] 注册心跳监视器结果: {result}")
                else:
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NO_CURRENT] 没有当前窗口，无法注册心跳: {window_id}")
            
            # 每次循环检查心跳超时（等待1秒后开始检查）
            if time.time() - start_time > 1:
                if self.check_heartbeat_timeout(window_id):
                    debug_log(f"💀 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CLEAR] 心跳检测清除了卡住的窗口，重试获取槽位")
                    continue  # 重新尝试获取槽位
            
            # 等待一段时间后重试（减少等待时间以更快响应）
            time.sleep(0.1)  # 更快响应 
        
        debug_log(f"⏰ DEBUG: [{get_global_timestamp()}] [QUEUE_TIMEOUT] 等待超时: {window_id}, thread: {threading.get_ident()}")
        return False
    
    def release_window_slot(self, window_id):
        """
        释放窗口槽位
        
        Args:
            window_id (str): 窗口唯一标识符
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            # 注意：不依赖超时机制，直接处理窗口完成
            # self._cleanup_expired_windows(queue_data)  # 注释掉自动清理，避免干扰
            
            # 检查是否是当前窗口
            if (queue_data["current_window"] and 
                queue_data["current_window"]["id"] == window_id):
                debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [QUEUE_RELEASE] 释放当前窗口槽位: {window_id}, thread: {threading.get_ident()}")
                queue_data["current_window"] = None
                # 增加完成计数器
                queue_data["completed_windows_count"] = queue_data.get("completed_windows_count", 0) + 1
                debug_log(f"📊 DEBUG: [{get_global_timestamp()}] [COUNTER] 窗口完成计数: {queue_data['completed_windows_count']} - window_id: {window_id}")
                
                # 如果有等待的窗口，将下一个设为当前窗口
                if queue_data["waiting_queue"]:
                    next_window = queue_data["waiting_queue"].pop(0)
                    queue_data["current_window"] = {
                        "id": next_window["id"],
                        "start_time": time.time(),
                        "thread_id": next_window["thread_id"],
                        "status": "active",  # 新窗口开始时状态为active
                        "heartbeat": {}  # 心跳字段：{window_id: "true"/"false"}
                    }
                    debug_log(f"🔄 DEBUG: [{get_global_timestamp()}] [QUEUE_NEXT] 下一个窗口获得槽位: {next_window['id']}, thread: {next_window['thread_id']}")
                
                self._write_queue_file(queue_data)
                debug_log(f"🎯 DEBUG: [{get_global_timestamp()}] [IMMEDIATE_RELEASE] 窗口槽位立即释放完成 - window_id: {window_id}")
            else:
                # 从等待队列中移除
                original_count = len(queue_data["waiting_queue"])
                queue_data["waiting_queue"] = [
                    w for w in queue_data["waiting_queue"] 
                    if w["id"] != window_id
                ]
                if len(queue_data["waiting_queue"]) < original_count:
                    debug_log(f"🚫 DEBUG: [{get_global_timestamp()}] [QUEUE_REMOVE] 从等待队列移除: {window_id}, thread: {threading.get_ident()}")
                    self._write_queue_file(queue_data)
                else:
                    debug_log(f"⚠️ DEBUG: [{get_global_timestamp()}] [QUEUE_NOT_FOUND] 窗口未在队列中找到: {window_id}, thread: {threading.get_ident()}")
    
    def mark_window_completed(self, window_id):
        """
        标记窗口为已完成状态，但不释放槽位（等待下次检查时自动处理）
        
        Args:
            window_id (str): 窗口唯一标识符
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            
            # 检查是否是当前窗口
            if (queue_data["current_window"] and 
                queue_data["current_window"]["id"] == window_id):
                queue_data["current_window"]["status"] = "completed"
                self._write_queue_file(queue_data)
                debug_log(f"✅ DEBUG: [{get_global_timestamp()}] [MARK_COMPLETED] 窗口标记为已完成: {window_id}")
                return True
            else:
                debug_log(f"⚠️ DEBUG: [{get_global_timestamp()}] [MARK_FAILED] 无法标记窗口完成，非当前窗口: {window_id}")
                return False
    
    def _register_heartbeat_watcher_internal(self, queue_data, watcher_id):
        """
        内部心跳注册函数（调用者已持有锁）
        
        Args:
            queue_data (dict): 队列数据
            watcher_id (str): 监视器窗口ID
        """
        debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_ENTER_INTERNAL] 进入内部心跳注册函数: {watcher_id}")
        
        if queue_data["current_window"]:
            if "heartbeat" not in queue_data["current_window"]:
                queue_data["current_window"]["heartbeat"] = {}
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_INIT] 初始化心跳字段")
            
            current_heartbeat = queue_data["current_window"]["heartbeat"]
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_BEFORE] 注册前心跳状态: {current_heartbeat}")
            
            queue_data["current_window"]["heartbeat"][watcher_id] = "false"
            self._write_queue_file(queue_data)
            
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_REG] 注册心跳监视器: {watcher_id}")
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_AFTER] 注册后心跳状态: {queue_data['current_window']['heartbeat']}")
            return True
        else:
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NO_CURRENT] 没有当前窗口，无法注册心跳监视器: {watcher_id}")
        return False
    
    def register_heartbeat_watcher(self, watcher_id):
        """
        注册心跳监视器（等待的窗口注册自己）
        
        Args:
            watcher_id (str): 监视器窗口ID
        """
        debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_ENTER] 进入register_heartbeat_watcher函数: {watcher_id}")
        with self.local_lock:
            queue_data = self._read_queue_file()
            debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_READ] 读取队列数据完成，current_window存在: {queue_data.get('current_window') is not None}")
            
            if queue_data["current_window"]:
                if "heartbeat" not in queue_data["current_window"]:
                    queue_data["current_window"]["heartbeat"] = {}
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_INIT] 初始化心跳字段")
                
                current_heartbeat = queue_data["current_window"]["heartbeat"]
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_BEFORE] 注册前心跳状态: {current_heartbeat}")
                
                queue_data["current_window"]["heartbeat"][watcher_id] = "false"
                self._write_queue_file(queue_data)
                
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_REG] 注册心跳监视器: {watcher_id}")
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_AFTER] 注册后心跳状态: {queue_data['current_window']['heartbeat']}")
                return True
            else:
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NO_CURRENT] 没有当前窗口，无法注册心跳监视器: {watcher_id}")
            return False
    
    def update_heartbeat(self, window_id):
        """
        更新心跳（当前窗口调用，将所有监视器设置为true）
        
        Args:
            window_id (str): 当前窗口ID
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            
            if (queue_data["current_window"] and 
                queue_data["current_window"]["id"] == window_id):
                heartbeat = queue_data["current_window"].get("heartbeat", {})
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_UPDATE_BEFORE] 更新前心跳状态: {heartbeat}")
                
                for watcher_id in heartbeat:
                    heartbeat[watcher_id] = "true"
                
                self._write_queue_file(queue_data)
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_UPDATE_AFTER] 更新后心跳状态: {heartbeat}")
                return len(heartbeat)  # 返回更新的监视器数量
            else:
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_UPDATE_FAIL] 无法更新心跳 - window_id: {window_id}, current: {queue_data.get('current_window', {}).get('id', 'None')}")
            return 0
    
    def check_heartbeat_timeout(self, watcher_id):
        """
        检查心跳超时（等待的窗口检查自己的心跳状态）
        
        Args:
            watcher_id (str): 监视器窗口ID
            
        Returns:
            bool: True如果当前窗口已经超时（应该被清除）
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            
            if queue_data["current_window"]:
                heartbeat = queue_data["current_window"].get("heartbeat", {})
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_CHECK] 检查心跳超时 - watcher: {watcher_id}, heartbeat: {heartbeat}")
                
                if watcher_id in heartbeat:
                    if heartbeat[watcher_id] == "false":
                        # 心跳超时，清除当前窗口
                        current_window_id = queue_data["current_window"]["id"]
                        debug_log(f"💀 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_TIMEOUT] 心跳超时，清除窗口: {current_window_id}")
                        queue_data["current_window"] = None
                        self._write_queue_file(queue_data)
                        return True
                    else:
                        debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_ALIVE] 心跳正常 - watcher: {watcher_id}")
                        # 重置心跳为false，准备下次检查
                        heartbeat[watcher_id] = "false"
                        self._write_queue_file(queue_data)
                else:
                    debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NOT_FOUND] 心跳中未找到监视器: {watcher_id}")
            else:
                debug_log(f"💓 DEBUG: [{get_global_timestamp()}] [HEARTBEAT_NO_CURRENT_CHECK] 没有当前窗口进行心跳检查")
            return False
    
    def get_queue_status(self):
        """获取队列状态"""
        with self.local_lock:
            queue_data = self._read_queue_file()
            self._cleanup_expired_windows(queue_data)
            return {
                "current_window": queue_data["current_window"],
                "waiting_count": len(queue_data["waiting_queue"]),
                "waiting_queue": queue_data["waiting_queue"],
                "completed_windows_count": queue_data.get("completed_windows_count", 0)
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
                    
                    # 更新时间戳
                    reset_data = {
                        "current_window": None,
                        "waiting_queue": [],
                        "last_update": time.time()
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
