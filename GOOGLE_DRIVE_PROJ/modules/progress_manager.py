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
                print(f"√", end='', flush=True)
    
    def print_result(self, message: str, success: bool = True):
        """显示最终结果（替换进度显示）"""
        with self.lock:
            # 先清除进度显示（包括√）
            if self.is_active and self.has_progress_line:
                print('\r\033[K', end='', flush=True)
                self.is_active = False
                self.has_progress_line = False
            
            # 显示最终结果（不带√前缀）
            print(message, flush=True)
    
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

def clear_progress():
    """清除进度显示"""
    _global_progress_display.stop_progress()

def result_print(message: str, success: bool = True):
    """显示最终结果（替换进度显示）"""
    _global_progress_display.print_result(message, success)

def is_progress_active() -> bool:
    """检查是否在进度显示模式"""
    return _global_progress_display.is_active


def validate_creation(validation_func, item_name, max_attempts=60, validation_type="file"):
    """
    统一的文件/目录验证接口，集成进度显示
    
    Args:
        validation_func: 验证函数，返回True表示成功，False表示需要重试
        item_name: 验证的项目名称（文件名或目录名）
        max_attempts: 最大重试次数
        validation_type: 验证类型 ("file", "dir", "upload")
        
    Returns:
        dict: {"success": bool, "message": str, "attempts": int}
    """
    import time
    
    # DEBUG: 记录验证开始（已注释以保持输出干净）
    # print(f"DEBUG: Starting validation for {validation_type} '{item_name}' (max_attempts={max_attempts})", flush=True)
    
    # 开始进度显示
    if validation_type == "file":
        start_progress_buffering(f"⏳ Validating file creation ...")
    elif validation_type == "dir":
        start_progress_buffering(f"⏳ Validating directory creation ...")
    elif validation_type == "upload":
        start_progress_buffering(f"⏳ Validating {item_name} ...")
    else:
        start_progress_buffering(f"⏳ Validating {validation_type} ...")
    
    # 执行验证循环
    for attempt in range(max_attempts):
        if attempt > 0:
            time.sleep(1)
            progress_print(f".")
        
        try:
            validation_result = validation_func()
            # print(f"DEBUG: Attempt {attempt + 1}: validation_func returned {validation_result}", flush=True)
            
            if validation_result:
                # 验证成功
                # print(f"DEBUG: Validation successful after {attempt + 1} attempts", flush=True)
                add_success_mark()
                
                # 清除进度显示（不显示额外消息）
                clear_progress()
                
                # 生成成功消息（仅用于返回值）
                if validation_type == "file":
                    success_msg = f"File {item_name} created successfully"
                elif validation_type == "dir":
                    success_msg = f"Directory {item_name} created successfully"
                elif validation_type == "upload":
                    success_msg = f"{item_name} uploaded successfully"
                else:
                    success_msg = f"{item_name} {validation_type} completed"
                return {
                    "success": True,
                    "message": success_msg,
                    "attempts": attempt + 1
                }
        except Exception as e:
            # 验证函数异常，继续重试
            pass
    
    # 所有重试都失败了
    fail_msg = f"Failed to validate {item_name} after {max_attempts} attempts"
    result_print(fail_msg)
    return {
        "success": False,
        "message": fail_msg,
        "attempts": max_attempts
    }