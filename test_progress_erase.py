#!/usr/bin/env python3
"""
测试进度擦除功能
直接调用validate_creation函数，验证擦除是否正常工作
"""

import sys
import os
import time

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(__file__))

def test_direct_validate_creation():
    """直接测试validate_creation函数"""
    
    print("=== 直接测试 validate_creation 函数 ===")
    
    try:
        from GOOGLE_DRIVE_PROJ.modules.progress_manager import validate_creation
        
        # 模拟一个简单的验证函数
        attempt_count = 0
        def mock_validation():
            nonlocal attempt_count
            attempt_count += 1
            print(f"DEBUG: Mock validation called, attempt {attempt_count}")
            if attempt_count >= 3:  # 第3次尝试成功
                return True
            return False
        
        print("开始测试...")
        result = validate_creation(mock_validation, "test_item", 10, "file")
        print(f"结果: {result}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

def test_progress_display_components():
    """测试进度显示的各个组件"""
    
    print("\n=== 测试进度显示组件 ===")
    
    try:
        from GOOGLE_DRIVE_PROJ.modules.progress_manager import (
            start_progress_buffering, 
            progress_print, 
            add_success_mark, 
            result_print,
            stop_progress_buffering
        )
        
        print("1. 测试开始进度显示")
        start_progress_buffering("⏳ Testing progress display ...")
        time.sleep(1)
        
        print("2. 测试添加点")
        progress_print(".")
        time.sleep(1)
        
        print("3. 测试添加成功标记")
        add_success_mark()
        time.sleep(1)
        
        print("4. 测试结果显示（应该擦除进度）")
        result_print("Test completed successfully")
        
        print("5. 测试完成")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

def test_ansi_escape_sequences():
    """测试ANSI转义序列"""
    
    print("\n=== 测试ANSI转义序列 ===")
    
    print("测试1: 显示进度信息", end='', flush=True)
    time.sleep(1)
    print(".", end='', flush=True)
    time.sleep(1)
    print(".", end='', flush=True)
    time.sleep(1)
    print("√", end='', flush=True)
    time.sleep(1)
    
    print("\n测试2: 使用\\r\\033[K清除", end='', flush=True)
    time.sleep(1)
    print('\r\033[K', end='', flush=True)
    print("清除后的新内容")
    
    print("测试3: 显示长内容然后清除")
    print("⏳ 这是一个很长的进度信息，包含很多字符 ..................√", end='', flush=True)
    time.sleep(2)
    print('\r\033[K', end='', flush=True)
    print("完全清除后的最终结果")

if __name__ == "__main__":
    test_ansi_escape_sequences()
    test_progress_display_components()
    test_direct_validate_creation()

