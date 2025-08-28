#!/usr/bin/env python3
"""
强制清理队列，清除所有死线程和超时窗口
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GOOGLE_DRIVE_PROJ'))

from modules.remote_window_queue import get_global_queue
import threading

def force_clean_queue():
    print("🧹 开始强制清理队列...")
    
    queue = get_global_queue()
    
    # 获取当前所有活跃线程ID
    active_thread_ids = set()
    for thread in threading.enumerate():
        if hasattr(thread, 'ident') and thread.ident:
            active_thread_ids.add(thread.ident)
    
    print(f"📊 当前活跃线程ID: {active_thread_ids}")
    
    with queue.local_lock:
        queue_data = queue._read_queue_file()
        print(f"🔍 清理前状态: {queue_data}")
        
        # 强制清理当前窗口
        current_window = queue_data.get("current_window")
        if current_window:
            thread_id = current_window.get("thread_id")
            if thread_id not in active_thread_ids:
                print(f"💀 强制清理当前窗口 (死线程): {current_window['id']} (thread_id: {thread_id})")
                queue_data["current_window"] = None
        
        # 强制清理等待队列
        original_count = len(queue_data["waiting_queue"])
        cleaned_queue = []
        
        for window in queue_data["waiting_queue"]:
            thread_id = window.get("thread_id")
            if thread_id in active_thread_ids:
                cleaned_queue.append(window)
            else:
                print(f"💀 强制清理等待队列窗口 (死线程): {window['id']} (thread_id: {thread_id})")
        
        queue_data["waiting_queue"] = cleaned_queue
        
        print(f"🧹 清理完成: 移除了 {original_count - len(cleaned_queue)} 个死线程窗口")
        
        # 如果有等待的窗口，将第一个设为当前窗口
        if not queue_data["current_window"] and queue_data["waiting_queue"]:
            next_window = queue_data["waiting_queue"].pop(0)
            queue_data["current_window"] = {
                "id": next_window["id"],
                "start_time": __import__("time").time(),
                "thread_id": next_window["thread_id"]
            }
            print(f"🔄 提升等待队列中的窗口为当前窗口: {next_window['id']}")
        
        queue._write_queue_file(queue_data)
        print(f"✅ 清理后状态: {queue_data}")

if __name__ == "__main__":
    force_clean_queue()
