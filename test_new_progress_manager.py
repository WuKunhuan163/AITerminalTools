#!/usr/bin/env python3
"""
测试新的progress_manager模块
验证其是否按照期望的方式工作
"""

import sys
import time
import os

# 添加路径以便导入模块
sys.path.insert(0, os.path.dirname(__file__))

from GOOGLE_DRIVE_PROJ.modules.progress_manager import (
    start_progress_buffering, 
    stop_progress_buffering, 
    progress_print, 
    result_print,
    normal_print
)

def test_new_progress_manager():
    """测试新的progress_manager功能"""
    
    # (1) 输出模拟指令
    normal_print("$ echo 'Hello World'")
    
    # (2) 开始进度显示
    start_progress_buffering("⏳ Waiting for result ...")
    
    # 每秒添加一个点，持续5秒（缩短测试时间）
    for i in range(5):
        time.sleep(1)
        progress_print(".")
    
    # (3) 显示最终结果（会自动擦除进度）
    result_print("Hello World")
    
    # 测试正常输出
    normal_print("Test completed successfully!")

if __name__ == "__main__":
    test_new_progress_manager()
