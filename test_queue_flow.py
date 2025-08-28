#!/usr/bin/env python3
"""
测试队列管理流程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GOOGLE_DRIVE_PROJ'))

from modules.remote_window_queue import request_window_slot, release_window_slot, get_queue_status
from modules.remote_commands import RemoteCommands
import time

def test_queue_flow():
    print("🧪 开始测试队列管理流程...")
    
    # 1. 检查初始状态
    print("1️⃣ 检查初始队列状态:")
    status = get_queue_status()
    print(f"   初始状态: {status}")
    
    # 2. 请求窗口槽位
    window_id = "test_window_123"
    print(f"2️⃣ 请求窗口槽位: {window_id}")
    success = request_window_slot(window_id, timeout_seconds=10)
    print(f"   请求结果: {success}")
    
    if success:
        # 3. 检查获得槽位后的状态
        print("3️⃣ 检查获得槽位后的状态:")
        status = get_queue_status()
        print(f"   当前状态: {status}")
        
        # 4. 模拟窗口显示
        print("4️⃣ 模拟窗口显示...")
        try:
            remote_commands = RemoteCommands(None)
            result = remote_commands.show_command_window_subprocess(
                title="Queue Test Window",
                command_text="echo 'Queue test command'",
                timeout_seconds=10
            )
            print(f"   窗口显示结果: {result}")
        except Exception as e:
            print(f"   窗口显示失败: {e}")
        
        # 5. 释放槽位
        print("5️⃣ 释放窗口槽位...")
        release_window_slot(window_id)
        
        # 6. 检查释放后的状态
        print("6️⃣ 检查释放后的状态:")
        status = get_queue_status()
        print(f"   最终状态: {status}")
        
    else:
        print("❌ 无法获得窗口槽位")

if __name__ == "__main__":
    test_queue_flow()
