#!/usr/bin/env python3
"""
直接测试窗口显示功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'GOOGLE_DRIVE_PROJ'))

from modules.remote_commands import RemoteCommands

def test_window_direct():
    print("🧪 开始直接测试窗口显示功能...")
    
    # 创建RemoteCommands实例
    remote_commands = RemoteCommands(None)  # 传入None作为main_instance
    
    # 测试简单的窗口显示
    try:
        print("🖥️ 测试窗口显示...")
        result = remote_commands.show_command_window_subprocess(
            title="Test Window",
            command_text="echo 'Hello, this is a test command'"
        )
        
        print(f"✅ 窗口显示结果: {result}")
        
    except Exception as e:
        print(f"❌ 窗口显示失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_window_direct()
