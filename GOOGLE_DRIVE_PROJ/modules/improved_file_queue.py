#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的文件队列管理器 - 使用增强的文件锁定机制
解决跨进程队列同步问题
"""

import time
import threading
import os
import json
import fcntl
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from .config_loader import get_config


@dataclass
class WindowInfo:
    """窗口信息结构"""
    id: str
    status: str  # 'active', 'waiting', 'completed'
    thread_id: int
    process_id: int
    start_time: float
    request_time: float
    heartbeat: bool = True
    heartbeat_failures: int = 0
    last_heartbeat_update: float = 0


class ImprovedFileQueue:
    """改进的文件队列管理器 - 使用增强的文件锁定"""
    
    def __init__(self):
        # 从配置文件加载设置
        config = get_config()
        self.timeout_hours = config.timeout_hours
        self.heartbeat_interval = config.heartbeat_interval
        self.heartbeat_check_interval = config.heartbeat_check_interval
        self.lock_timeout = config.lock_timeout
        
        # 队列文件路径
        data_dir = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA"
        self.queue_file = f"{data_dir}/{config.get_file_paths()['remote_window_queue_file']}"
        self.lock_file = f"{data_dir}/{config.get_file_paths()['remote_window_queue_lock']}"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.queue_file), exist_ok=True)
        
        # 本地线程管理
        self._local_threads = {}
        self._shutdown_event = threading.Event()
        
        # 启动定期清理线程
        self._start_periodic_cleanup()
        
        # self.debug_log(f"[INIT] 改进文件队列管理器初始化完成, PID: {os.getpid()}")
    
    def debug_log(self, message: str):
        """调试日志输出"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        elapsed = time.time() - (getattr(self, '_start_time', time.time()))
        print(f"Tool: [{timestamp}] [PID:{os.getpid()}] [+{elapsed:.1f}s] {message}")
        
        # 同时写入调试文件
        try:
            debug_file = "/Users/wukunhuan/.local/bin/tmp/new_queue_debug.txt"
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [PID:{os.getpid()}] [+{elapsed:.1f}s] {message}\n")
        except:
            pass
    
    def _acquire_lock(self, timeout=None):
        """获取文件锁，使用超时机制"""
        if timeout is None:
            timeout = self.lock_timeout
        
        lock_fd = None
        start_time = time.time()
        
        try:
            # 创建锁文件
            lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_TRUNC | os.O_RDWR, 0o644)
            
            # 尝试获取锁
            while time.time() - start_time < timeout:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # self.debug_log(f"[LOCK_ACQUIRED] 成功获取文件锁，耗时: {time.time() - start_time:.3f}s")
                    return lock_fd
                except BlockingIOError:
                    time.sleep(0.01)  # 等待10毫秒再试
            
            # 超时
            os.close(lock_fd)
            # self.debug_log(f"[LOCK_TIMEOUT] 获取文件锁超时: {timeout}s")
            return None
            
        except Exception as e:
            if lock_fd:
                try:
                    os.close(lock_fd)
                except:
                    pass
            # self.debug_log(f"[LOCK_ERROR] 获取文件锁失败: {e}")
            return None
    
    def _release_lock(self, lock_fd):
        """释放文件锁"""
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
                # self.debug_log("[LOCK_RELEASED] 文件锁已释放")
            except Exception as e:
                pass
                # self.debug_log(f"[LOCK_RELEASE_ERROR] 释放文件锁失败: {e}")
    
    def _load_queue(self):
        """加载队列数据"""
        try:
            if os.path.exists(self.queue_file):
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 确保数据结构正确
                    if 'window_queue' not in data:
                        data['window_queue'] = []
                    return data
        except Exception as e:
            pass
            # self.debug_log(f"[LOAD_ERROR] 加载队列文件失败: {e}")
        
        # 返回默认数据结构
        return {
            'window_queue': [],
            'last_update': time.time(),
            'completed_count': 0,
            'last_window_open_time': 0,
            'description': "改进的文件队列管理器"
        }
    
    def _save_queue(self, data):
        """保存队列数据"""
        try:
            data['last_update'] = time.time()
            
            # 使用临时文件确保原子写入
            temp_file = self.queue_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 原子替换
            os.replace(temp_file, self.queue_file)
            return True
            
        except Exception as e:
            # self.debug_log(f"[SAVE_ERROR] 保存队列文件失败: {e}")
            return False
    
    def request_window_slot(self, window_id: str) -> str:
        """请求窗口槽位"""
        current_time = time.time()
        thread_id = threading.get_ident()
        process_id = os.getpid()
        
        if not hasattr(self, '_start_time'):
            self._start_time = current_time
        
        # self.debug_log(f"[SLOT_REQUEST] 请求槽位: {window_id}, thread: {thread_id}")
        
        # 获取文件锁
        lock_fd = self._acquire_lock()
        if not lock_fd:
            # self.debug_log(f"[SLOT_REQUEST_TIMEOUT] 获取锁超时: {window_id}")
            return 'error'
        
        try:
            # 加载队列数据
            queue_data = self._load_queue()
            queue = queue_data['window_queue']
            
            # 清理过期和死进程
            self._cleanup_expired_windows(queue_data)
            queue = queue_data['window_queue']  # 重新获取清理后的队列
            
            # 检查当前队列状态
            if len(queue) == 0:
                # 队列为空，立即获得槽位
                window = WindowInfo(
                    id=window_id,
                    status='active',
                    thread_id=thread_id,
                    process_id=process_id,
                    start_time=current_time,
                    request_time=current_time,
                    heartbeat=True,
                    heartbeat_failures=0,
                    last_heartbeat_update=current_time
                )
                queue.append(asdict(window))
                queue_data['last_window_open_time'] = current_time
                
                # 保存数据
                if self._save_queue(queue_data):
                    # self.debug_log(f"[SLOT_ACQUIRED] 立即获得槽位（空队列）: {window_id}, PID: {process_id}, 状态: active")
                    
                    # 启动心跳更新线程
                    self._start_heartbeat_updater(window_id)
                    return 'active'
                else:
                    # self.debug_log(f"[SLOT_SAVE_ERROR] 保存队列失败: {window_id}")
                    return 'error'
                    
            else:
                # 队列不为空，检查是否已在队列中
                for i, w in enumerate(queue):
                    if w['id'] == window_id:
                        # self.debug_log(f"[SLOT_EXISTS] 窗口已在队列中: {window_id}, 位置: {i}, 状态: {w['status']}")
                        if i == 0 and w['status'] == 'waiting':
                            # 如果是队首且状态为waiting，提升为active
                            w['status'] = 'active'
                            w['start_time'] = current_time
                            queue[i] = w
                            if self._save_queue(queue_data):
                                # self.debug_log(f"[SLOT_PROMOTED] 提升为活动状态: {window_id}")
                                self._start_heartbeat_updater(window_id)
                                return 'active'
                        return w['status']
                
                # 不在队列中，添加到等待队列
                window = WindowInfo(
                    id=window_id,
                    status='waiting',
                    thread_id=thread_id,
                    process_id=process_id,
                    start_time=0,  # 等待时不设置开始时间
                    request_time=current_time,
                    heartbeat=True,
                    heartbeat_failures=0,
                    last_heartbeat_update=current_time
                )
                queue.append(asdict(window))
                position = len(queue)
                
                if self._save_queue(queue_data):
                    # self.debug_log(f"[SLOT_WAITING] 加入等待队列: {window_id}, 位置: {position}")
                    
                    # 启动心跳更新线程（等待中的窗口也需要更新心跳）
                    self._start_heartbeat_updater(window_id)
                    
                    # 如果是队列中的第二个元素，启动心跳检查线程
                    if position == 2:
                        self._start_heartbeat_checker(window_id)
                    
                    return 'waiting'
                else:
                    return 'error'
                    
        finally:
            self._release_lock(lock_fd)
    
    def _start_heartbeat_updater(self, window_id: str):
        """启动心跳更新线程"""
        if window_id in self._local_threads:
            return
        
        def heartbeat_updater():
            # self.debug_log(f"[HEARTBEAT_UPDATER_START] 启动心跳更新线程: {window_id}")
            while not self._shutdown_event.is_set():
                try:
                    lock_fd = self._acquire_lock(timeout=1)  # 心跳使用较短的锁超时
                    if lock_fd:
                        try:
                            queue_data = self._load_queue()
                            queue = queue_data['window_queue']
                            
                            for i, w in enumerate(queue):
                                if w['id'] == window_id:
                                    old_heartbeat = w['heartbeat']
                                    w['heartbeat'] = True
                                    w['last_heartbeat_update'] = time.time()
                                    queue[i] = w
                                    
                                    if self._save_queue(queue_data):
                                        pass
                                        # self.debug_log(f"[HEARTBEAT_UPDATE] 更新心跳: {window_id}, {old_heartbeat} -> True")
                                    else:
                                        pass
                                        # self.debug_log(f"[HEARTBEAT_UPDATE_SAVE_ERROR] 心跳保存失败: {window_id}")
                                    break
                            else:
                                # self.debug_log(f"[HEARTBEAT_UPDATE_FAIL] 窗口不在队列中: {window_id}")
                                break
                                
                        finally:
                            self._release_lock(lock_fd)
                    else:
                        pass
                        # self.debug_log(f"[HEARTBEAT_UPDATE_LOCK_FAIL] 心跳更新获取锁失败: {window_id}")
                        
                except Exception as e:
                    pass
                    # self.debug_log(f"[HEARTBEAT_UPDATE_ERROR] 心跳更新错误: {window_id}, {e}")
                    break
                
                time.sleep(self.heartbeat_interval)
            
            # self.debug_log(f"[HEARTBEAT_UPDATER_END] 心跳更新线程结束: {window_id}")
        
        thread = threading.Thread(target=heartbeat_updater, daemon=True)
        thread.start()
        self._local_threads[window_id] = thread
        # self.debug_log(f"[HEARTBEAT_UPDATER_CREATED] 心跳更新线程已创建: {window_id}")
    
    def _start_heartbeat_checker(self, window_id: str):
        """启动心跳检查线程（仅对等待中的第一个窗口）"""
        def heartbeat_checker():
            # self.debug_log(f"[HEARTBEAT_CHECKER_START] 启动心跳检查线程: {window_id}")
            consecutive_failures = 0
            
            while not self._shutdown_event.is_set():
                try:
                    lock_fd = self._acquire_lock(timeout=2)  # 心跳检查使用稍长的锁超时
                    if lock_fd:
                        try:
                            queue_data = self._load_queue()
                            queue = queue_data['window_queue']
                            
                            if len(queue) < 2:
                                # self.debug_log(f"[HEARTBEAT_CHECKER_EXIT] 队列长度不足: {window_id}")
                                break
                            
                            # 检查当前窗口是否还是第二个
                            if len(queue) < 2 or queue[1]['id'] != window_id:
                                # self.debug_log(f"[HEARTBEAT_CHECKER_NOT_SECOND] 不再是第二个窗口: {window_id}")
                                break
                            
                            # 检查第一个窗口的心跳
                            current_window = queue[0]
                            if current_window['heartbeat']:
                                # 心跳正常，重置并清除失败计数
                                current_window['heartbeat'] = False
                                current_window['heartbeat_failures'] = 0
                                queue[0] = current_window
                                consecutive_failures = 0
                                
                                if self._save_queue(queue_data):
                                    # self.debug_log(f"[HEARTBEAT_ALIVE] 心跳正常，重置失败计数: {current_window['id']}")
                                    pass
                            else:
                                # 心跳失败
                                consecutive_failures += 1
                                current_window['heartbeat_failures'] = consecutive_failures
                                queue[0] = current_window
                                
                                # self.debug_log(f"[HEARTBEAT_FAILURE] 心跳失败 {consecutive_failures}/2: {current_window['id']}")
                                
                                if consecutive_failures >= get_config().heartbeat_failure_threshold:
                                    # 两次连续失败，清除当前窗口
                                    # self.debug_log(f"[HEARTBEAT_TIMEOUT] 心跳超时，清除窗口: {current_window['id']}")
                                    queue.pop(0)
                                    
                                    # 处理队列进程
                                    self._process_queue_after_removal(queue_data)
                                    
                                    if self._save_queue(queue_data):
                                        # self.debug_log(f"[HEARTBEAT_TIMEOUT_PROCESSED] 心跳超时处理完成")
                                        pass
                                    break
                                
                                if self._save_queue(queue_data):
                                    pass  # 保存失败计数更新
                            
                        finally:
                            self._release_lock(lock_fd)
                    else:
                        pass
                        # self.debug_log(f"[HEARTBEAT_CHECKER_LOCK_FAIL] 心跳检查获取锁失败: {window_id}")
                    
                except Exception as e:
                    pass
                    # self.debug_log(f"[HEARTBEAT_CHECKER_ERROR] 心跳检查错误: {window_id}, {e}")
                    break
                
                time.sleep(self.heartbeat_check_interval)
            
            # self.debug_log(f"[HEARTBEAT_CHECKER_END] 心跳检查线程结束: {window_id}")
        
        thread = threading.Thread(target=heartbeat_checker, daemon=True)
        thread.start()
        # self.debug_log(f"[HEARTBEAT_CHECKER_CREATED] 心跳检查线程已创建: {window_id}")
    
    def _process_queue_after_removal(self, queue_data):
        """处理窗口移除后的队列进程"""
        queue = queue_data['window_queue']
        # self.debug_log(f"[QUEUE_AFTER_REMOVAL] 移除后队列长度: {len(queue)}")
        
        if len(queue) > 0:
            # 提升第一个等待窗口为活动状态
            first_window = queue[0]
            # self.debug_log(f"[QUEUE_FIRST_WINDOW] 第一个窗口状态: {first_window['status']}, ID: {first_window['id']}")
            
            if first_window['status'] == 'waiting':
                first_window['status'] = 'active'
                first_window['start_time'] = time.time()
                queue[0] = first_window
                # self.debug_log(f"[QUEUE_PROMOTED] 提升等待窗口为活动: {first_window['id']}, PID: {first_window['process_id']}")
            else:
                pass
                # self.debug_log(f"[QUEUE_NO_PROMOTION] 第一个窗口已经是活动状态: {first_window['id']}")
        else:
            pass
            # self.debug_log(f"[QUEUE_EMPTY] 队列为空，无需处理")
    
    def check_window_status(self, window_id: str) -> str:
        """检查窗口状态
        
        Returns:
            'active' - 窗口是活动状态
            'waiting' - 窗口在等待队列中
            'not_found' - 窗口不在队列中
        """
        lock_fd = self._acquire_lock()
        if lock_fd is None:
            return 'not_found'
            
        try:
            queue_data = self._load_queue()
            if not queue_data:
                return 'not_found'
                
            queue = queue_data.get('window_queue', [])
            
            for window in queue:
                if window['id'] == window_id:
                    status = window.get('status', 'unknown')
                    # self.debug_log(f"[WINDOW_STATUS_CHECK] 窗口状态: {window_id} -> {status}")
                    return status
                    
            # self.debug_log(f"[WINDOW_STATUS_CHECK] 窗口不在队列中: {window_id}")
            return 'not_found'
            
        finally:
            self._release_lock(lock_fd)
    
    def release_window_slot(self, window_id: str):
        """释放窗口槽位"""
        # self.debug_log(f"[SLOT_RELEASE] 释放槽位: {window_id}")
        
        lock_fd = self._acquire_lock()
        if not lock_fd:
            # self.debug_log(f"[SLOT_RELEASE_TIMEOUT] 获取锁超时: {window_id}")
            return
        
        try:
            queue_data = self._load_queue()
            queue = queue_data['window_queue']
            # self.debug_log(f"[SLOT_RELEASE_QUEUE] 当前队列长度: {len(queue)}")
            
            # 查找并移除窗口
            for i, w in enumerate(queue):
                if w['id'] == window_id:
                    # self.debug_log(f"[SLOT_RELEASE_FOUND] 找到窗口: {window_id}, 位置: {i}, 状态: {w['status']}")
                    queue.pop(i)
                    queue_data['completed_count'] += 1
                    
                    # 停止本地线程
                    self._stop_local_thread(window_id)
                    # self.debug_log(f"[SLOT_RELEASE_THREAD_STOPPED] 停止本地线程: {window_id}")
                    
                    # 处理队列进程
                    # self.debug_log(f"[SLOT_RELEASE_PROCESSING] 开始处理队列进程...")
                    self._process_queue_after_removal(queue_data)
                    
                    if self._save_queue(queue_data):
                        # self.debug_log(f"[SLOT_RELEASED] 槽位已释放: {window_id}, 位置: {i}, 新队列长度: {len(queue_data['window_queue'])}")
                        
                        # 显示新的队列状态
                        if len(queue_data['window_queue']) > 0:
                            next_window = queue_data['window_queue'][0]
                            # self.debug_log(f"[SLOT_RELEASE_NEXT] 下一个窗口: {next_window['id']}, 状态: {next_window['status']}, PID: {next_window['process_id']}")
                    return
            
            # self.debug_log(f"[SLOT_RELEASE_FAIL] 窗口不在队列中: {window_id}")
            
        finally:
            self._release_lock(lock_fd)
    
    def mark_window_completed(self, window_id: str):
        """标记窗口完成"""
        # self.debug_log(f"[WINDOW_COMPLETED] 标记窗口完成: {window_id}")
        
        lock_fd = self._acquire_lock()
        if not lock_fd:
            return
        
        try:
            queue_data = self._load_queue()
            queue = queue_data['window_queue']
            
            for i, w in enumerate(queue):
                if w['id'] == window_id:
                    w['status'] = 'completed'
                    queue[i] = w
                    
                    # 处理队列进程（完成的窗口会在下次清理时移除）
                    self._process_queue_after_removal(queue_data)
                    
                    if self._save_queue(queue_data):
                        pass
                        # self.debug_log(f"[WINDOW_MARKED_COMPLETED] 窗口已标记完成: {window_id}")
                    return
                    
        finally:
            self._release_lock(lock_fd)
    
    def _stop_local_thread(self, window_id: str):
        """停止本地线程"""
        if window_id in self._local_threads:
            # self.debug_log(f"[THREAD_STOP] 停止本地线程: {window_id}")
            # 线程会在下次循环时自动退出（因为窗口不在队列中了）
            del self._local_threads[window_id]
    
    def _cleanup_expired_windows(self, queue_data):
        """清理过期和死进程的窗口"""
        current_time = time.time()
        timeout_seconds = self.timeout_hours * 3600
        queue = queue_data['window_queue']
        
        if not queue:
            return
        
        original_count = len(queue)
        cleaned_indices = []
        
        for i in range(len(queue) - 1, -1, -1):  # 倒序遍历以安全删除
            window = queue[i]
            window_id = window['id']
            process_id = window['process_id']
            
            # 检查超时
            check_time = window['start_time'] if window['start_time'] > 0 else window['request_time']
            if current_time - check_time > timeout_seconds:
                # self.debug_log(f"[CLEANUP_TIMEOUT] 超时窗口: {window_id}")
                queue.pop(i)
                cleaned_indices.append(i)
                continue
            
            # 检查进程是否存活
            if not self._is_process_alive(process_id):
                # self.debug_log(f"[CLEANUP_DEAD_PROCESS] 死进程窗口: {window_id}, PID: {process_id}")
                queue.pop(i)
                cleaned_indices.append(i)
                continue
        
        cleaned_count = len(cleaned_indices)
        if cleaned_count > 0:
            pass
            # self.debug_log(f"[CLEANUP_SUMMARY] 清理了 {cleaned_count} 个无效窗口")
    
    def _is_process_alive(self, pid: int) -> bool:
        """检查进程是否存活"""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def _start_periodic_cleanup(self):
        """启动定期清理线程"""
        def cleanup_worker():
            while not self._shutdown_event.wait(30):  # 每30秒清理一次
                try:
                    lock_fd = self._acquire_lock()
                    if not lock_fd:
                        # self.debug_log(f"[PERIODIC_CLEANUP_TIMEOUT] 定期清理获取锁超时")
                        continue
                    
                    try:
                        queue_data = self._load_queue()
                        original_count = len(queue_data['window_queue'])
                        
                        if original_count > 0:
                            self._cleanup_expired_windows(queue_data)
                            new_count = len(queue_data['window_queue'])
                            
                            if new_count < original_count:
                                self._save_queue(queue_data)
                                # self.debug_log(f"[PERIODIC_CLEANUP] 定期清理: {original_count} -> {new_count}")
                        
                    finally:
                        self._release_lock(lock_fd)
                        
                except Exception as e:
                    pass
                    # self.debug_log(f"[PERIODIC_CLEANUP_ERROR] 定期清理错误: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True, name="PeriodicCleanup")
        cleanup_thread.start()
        # self.debug_log(f"[PERIODIC_CLEANUP_STARTED] 定期清理线程已启动")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        lock_fd = self._acquire_lock()
        if not lock_fd:
            return {}
        
        try:
            queue_data = self._load_queue()
            queue = queue_data['window_queue']
            
            current_window = queue[0] if queue else None
            waiting_windows = queue[1:] if len(queue) > 1 else []
            
            status = {
                'current_window': current_window,
                'waiting_queue': waiting_windows,
                'queue_length': len(queue),
                'completed_count': queue_data.get('completed_count', 0),
                'last_update': queue_data.get('last_update', 0)
            }
            
            # self.debug_log(f"[QUEUE_STATUS] 当前: {current_window['id'] if current_window else 'None'}, 等待: {len(waiting_windows)}")
            return status
            
        finally:
            self._release_lock(lock_fd)
    
    def reset_queue(self):
        """重置队列"""
        # self.debug_log("[QUEUE_RESET] 重置队列")
        
        lock_fd = self._acquire_lock()
        if not lock_fd:
            return
        
        try:
            queue_data = {
                'window_queue': [],
                'completed_count': 0,
                'last_update': time.time(),
                'last_window_open_time': 0,
                'description': "改进的文件队列管理器"
            }
            self._save_queue(queue_data)
            
        finally:
            self._release_lock(lock_fd)
        
        # 停止所有本地线程
        self._shutdown_event.set()
        for window_id in list(self._local_threads.keys()):
            self._stop_local_thread(window_id)
        self._shutdown_event.clear()
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_shutdown_event'):
            self._shutdown_event.set()


# 全局单例实例
_improved_file_queue = None

def get_improved_file_queue() -> ImprovedFileQueue:
    """获取改进文件队列管理器单例"""
    global _improved_file_queue
    if _improved_file_queue is None:
        _improved_file_queue = ImprovedFileQueue()
    return _improved_file_queue
