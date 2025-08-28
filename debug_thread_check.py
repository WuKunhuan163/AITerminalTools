#!/usr/bin/env python3
"""
调试线程检查逻辑
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GOOGLE_DRIVE_PROJ'))

from modules.remote_window_queue import get_global_queue
import threading
import json

def debug_thread_check():
    print("🔍 调试线程检查逻辑...")
    
    queue = get_global_queue()
    
    # 读取当前队列状态
    queue_data = queue._read_queue_file()
    print(f"📋 当前队列状态: {json.dumps(queue_data, indent=2, ensure_ascii=False)}")
    
    # 获取当前所有活跃线程
    active_threads = threading.enumerate()
    print(f"📊 当前活跃线程数量: {len(active_threads)}")
    
    for i, thread in enumerate(active_threads):
        print(f"   线程 {i+1}: ident={getattr(thread, 'ident', None)}, name={thread.name}, alive={thread.is_alive()}")
    
    # 检查当前窗口的线程状态
    current_window = queue_data.get("current_window")
    if current_window:
        thread_id = current_window.get("thread_id")
        print(f"🔍 检查当前窗口线程: {thread_id}")
        
        # 手动检查线程是否存活
        is_alive = queue._is_thread_alive(thread_id)
        print(f"   线程存活检查结果: {is_alive}")
        
        # 查找匹配的线程
        matching_thread = None
        for thread in active_threads:
            if hasattr(thread, 'ident') and thread.ident == thread_id:
                matching_thread = thread
                break
        
        if matching_thread:
            print(f"   找到匹配线程: {matching_thread.name}, alive={matching_thread.is_alive()}")
        else:
            print(f"   ❌ 未找到匹配线程，应该清理此窗口")
    
    # 测试清理逻辑
    print("🧹 测试清理逻辑...")
    cleaned = queue._cleanup_expired_windows(queue_data)
    print(f"   清理结果: {cleaned}")
    
    if cleaned:
        print(f"✅ 清理后状态: {json.dumps(queue_data, indent=2, ensure_ascii=False)}")
        queue._write_queue_file(queue_data)
    else:
        print("   无需清理")

if __name__ == "__main__":
    debug_thread_check()
