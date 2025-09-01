#!/usr/bin/env python3
"""
Progress Manager - 管理GDS远程窗口的进度显示
使用简单的ANSI转义序列实现进度显示和擦除功能
基于test_progress_display.py的成功实现
"""

import sys
import threading
import time
from typing import Optional, List


class ProgressDisplay:
    """进度显示管理器，使用ANSI转义序列实现进度显示"""
    
    def __init__(self):
        self.is_active = False
        self.lock = threading.Lock()
        self.current_message = ""
        self.has_progress_line = False

    def start_progress(self, message: str = "⏳ Waiting for result ..."):
        """开始显示进度"""
        with self.lock:
            if not self.is_active:
                self.is_active = True
                self.current_message = message
                self.has_progress_line = True
                
                # 输出初始进度信息，不换行
                print(message, end='', flush=True)
    
    def update_progress(self, addition: str = "."):
        """更新进度信息（添加内容）"""
        with self.lock:
            if self.is_active and self.has_progress_line:
                # 添加进度指示符（如点）
                print(addition, end='', flush=True)
    
    def stop_progress(self):
        """停止进度显示并清除"""
        with self.lock:
            if self.is_active and self.has_progress_line:
                # 使用ANSI转义序列清除当前行
                print('\r\033[K', end='', flush=True)
                self.is_active = False
                self.has_progress_line = False
                self.current_message = ""
    
    def add_success_mark(self):
        """在进度行添加成功标记√"""
        with self.lock:
            if self.is_active and self.has_progress_line:
                print("√", end='', flush=True)
    
    def print_result(self, message: str, success: bool = True):
        """显示最终结果（替换进度显示）"""
        with self.lock:
            # 先清除进度显示（包括√）
            if self.is_active and self.has_progress_line:
                print('\r\033[K', end='', flush=True)
                self.is_active = False
                self.has_progress_line = False
            
            # 显示最终结果（不带√前缀）
            print(message)
    
    def print_normal(self, message: str):
        """正常输出（不影响进度显示）"""
        print(message)


# 全局进度显示实例
_global_progress_display = ProgressDisplay()

# 导出的函数接口
def start_progress_buffering(message: str = "⏳ Waiting for result ..."):
    """开始进度显示"""
    _global_progress_display.start_progress(message)

def stop_progress_buffering():
    """停止进度显示"""
    _global_progress_display.stop_progress()

def progress_print(message: str, end: str = "\n", flush: bool = False):
    """更新进度信息（添加点或其他内容）"""
    if end == "" or end == "\n":
        # 如果是添加点的情况
        addition = message.strip()
        if addition in [".", "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]:
            _global_progress_display.update_progress(addition)
        else:
            # 如果是更新整个进度信息，先清除再重新开始
            _global_progress_display.stop_progress()
            _global_progress_display.start_progress(message)
    else:
        _global_progress_display.update_progress(message)

def normal_print(message: str, end: str = "\n", flush: bool = False):
    """输出正常信息（不影响进度显示）"""
    _global_progress_display.print_normal(message)

def add_success_mark():
    """在进度行添加成功标记√"""
    _global_progress_display.add_success_mark()

def result_print(message: str, success: bool = True):
    """显示最终结果（替换进度显示）"""
    _global_progress_display.print_result(message, success)

def is_progress_active() -> bool:
    """检查是否在进度显示模式"""
    return _global_progress_display.is_active