"""
远程命令窗口队列管理器
实现全局锁机制，确保一次只产生一个remote window，避免多个测试同时运行时的冲突
"""

import json
import time
import threading
import os
from pathlib import Path

class RemoteWindowQueue:
    """远程命令窗口队列管理器"""
    
    def __init__(self, lock_file_path=None):
        if lock_file_path is None:
            # 默认锁文件路径在GOOGLE_DRIVE_PROJ目录下
            current_dir = Path(__file__).parent.parent
            lock_file_path = current_dir / "remote_window_queue.json"
        
        self.lock_file_path = Path(lock_file_path)
        self.local_lock = threading.Lock()  # 本地线程锁
        self.timeout_hours = 0.01  # 36秒超时（用于测试）
    
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
                self._cleanup_expired_windows(queue_data)
                
                # 检查是否可以立即获得槽位
                if queue_data["current_window"] is None:
                    # 可以立即获得槽位
                    queue_data["current_window"] = {
                        "id": window_id,
                        "start_time": time.time(),
                        "thread_id": threading.get_ident()
                    }
                    self._write_queue_file(queue_data)
                    # print(f"🚀 获得窗口槽位: {window_id}")
                    return True
                
                # 检查是否已经在队列中（避免重复请求）
                if not any(w["id"] == window_id for w in queue_data["waiting_queue"]):
                    # 添加到等待队列
                    queue_data["waiting_queue"].append({
                        "id": window_id,
                        "request_time": time.time(),
                        "thread_id": threading.get_ident()
                    })
                    self._write_queue_file(queue_data)
                    print(f"⏳ 加入等待队列: {window_id} (位置: {len(queue_data['waiting_queue'])})")
            
            # 等待一段时间后重试
            time.sleep(1)
        
        print(f"⏰ 等待超时: {window_id}")
        return False
    
    def release_window_slot(self, window_id):
        """
        释放窗口槽位
        
        Args:
            window_id (str): 窗口唯一标识符
        """
        with self.local_lock:
            queue_data = self._read_queue_file()
            # 自动清理死线程和超时窗口
            self._cleanup_expired_windows(queue_data)
            
            # 检查是否是当前窗口
            if (queue_data["current_window"] and 
                queue_data["current_window"]["id"] == window_id):
                # print(f"✅ 释放窗口槽位: {window_id}")
                queue_data["current_window"] = None
                # 增加完成计数器
                queue_data["completed_windows_count"] = queue_data.get("completed_windows_count", 0) + 1
                print(f"📊 DEBUG: 窗口完成计数: {queue_data['completed_windows_count']} - window_id: {window_id}")
                
                # 如果有等待的窗口，将下一个设为当前窗口
                if queue_data["waiting_queue"]:
                    next_window = queue_data["waiting_queue"].pop(0)
                    queue_data["current_window"] = {
                        "id": next_window["id"],
                        "start_time": time.time(),
                        "thread_id": next_window["thread_id"]
                    }
                    print(f"🔄 下一个窗口获得槽位: {next_window['id']}")
                
                self._write_queue_file(queue_data)
            else:
                # 从等待队列中移除
                original_count = len(queue_data["waiting_queue"])
                queue_data["waiting_queue"] = [
                    w for w in queue_data["waiting_queue"] 
                    if w["id"] != window_id
                ]
                if len(queue_data["waiting_queue"]) < original_count:
                    print(f"🚫 从等待队列移除: {window_id}")
                    self._write_queue_file(queue_data)
    
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

def get_queue_status():
    """获取队列状态的便捷函数"""
    return get_global_queue().get_queue_status()

def reset_queue():
    """重置队列的便捷函数"""
    return get_global_queue().reset_queue()
