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
                
                # 确保清除当前行并从行首开始输出进度信息
                print(f'\r\033[K{message}', end='', flush=True)
    
    def update_progress(self, addition: str = "."):
        """更新进度信息（添加内容）"""
        with self.lock:
            if self.is_active and self.has_progress_line:
                # 添加进度指示符（如点）
                print(addition, end='', flush=True)
    
    def stop_progress(self):
        """停止进度显示并清除"""
        with self.lock:
            # 强制清除当前行，无论状态如何
            print('\r\033[K', end='', flush=True)
            self.is_active = False
            self.has_progress_line = False
            self.current_message = ""
    
    def add_success_mark(self):
        """在进度行添加成功标记√"""
        with self.lock:
            if self.is_active and self.has_progress_line:
                # 不立即flush，让后续的clear_progress统一处理
                print(f"√", end='', flush=False)
    
    def print_result(self, message: str, success: bool = True):
        """显示最终结果（替换进度显示）"""
        with self.lock:
            # 先清除进度显示（包括√）
            # 强制清除，无论状态如何
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


def interruptible_progress_loop(progress_message, loop_func, check_interval=1.0, max_attempts=None):
    """
    统一的可中断进度循环接口
    
    Args:
        progress_message (str): 进度显示消息
        loop_func (callable): 循环检查函数，返回True表示完成，False表示继续，None表示失败
        check_interval (float): 检查间隔（秒）
        max_attempts (int): 最大尝试次数，None表示无限制
        
    Returns:
        dict: {"success": bool, "cancelled": bool, "message": str, "attempts": int}
    """
    import time
    import signal
    import sys
    
    # 开始进度显示
    if is_progress_active():
        clear_progress()
    start_progress_buffering(progress_message)
    
    # 设置中断标志
    interrupted = False
    
    def signal_handler(signum, frame):
        nonlocal interrupted
        interrupted = True
    
    # 保存原有的信号处理器
    old_handler = signal.signal(signal.SIGINT, signal_handler)
    
    try:
        attempt = 0
        while max_attempts is None or attempt < max_attempts:
            attempt += 1
            
            # 检查中断标志
            if interrupted:
                raise KeyboardInterrupt()
            
            # 执行检查函数
            try:
                result = loop_func()
                if result is True:
                    # 成功完成
                    clear_progress()
                    return {
                        "success": True,
                        "cancelled": False,
                        "message": "Operation completed successfully",
                        "attempts": attempt
                    }
                elif result is None:
                    # 失败，退出循环
                    break
                # result is False: 继续循环
            except Exception as e:
                # 循环函数异常，继续重试
                pass
            
            # 等待下一次检查，支持中断
            if check_interval > 0:
                sleep_time = 0
                while sleep_time < check_interval:
                    if interrupted:
                        raise KeyboardInterrupt()
                    time.sleep(0.1)
                    sleep_time += 0.1
                    
                # 显示进度点
                progress_print(".")
                
    except KeyboardInterrupt:
        # 用户中断
        clear_progress()
        return {
            "success": False,
            "cancelled": True,
            "message": "Operation cancelled by user",
            "attempts": attempt
        }
    finally:
        # 恢复原有的信号处理器
        try:
            signal.signal(signal.SIGINT, old_handler)
        except:
            pass
    
    # 超时或失败
    clear_progress()
    return {
        "success": False,
        "cancelled": False,
        "message": f"Operation failed after {attempt} attempts",
        "attempts": attempt
    }


def validate_creation(validation_func, item_name, max_attempts=60, validation_type="file"):
    """
    统一的文件/目录验证接口，集成进度显示
    使用统一的可中断进度循环接口
    
    Args:
        validation_func: 验证函数，返回True表示成功，False表示需要重试
        item_name: 验证的项目名称（文件名或目录名）
        max_attempts: 最大重试次数
        validation_type: 验证类型 ("file", "dir", "upload")
        
    Returns:
        dict: {"success": bool, "message": str, "attempts": int, "cancelled": bool}
    """
    # 确定进度消息
    if validation_type == "file":
        progress_message = f"⏳ Validating file creation ..."
        success_msg = f"File {item_name} created successfully"
    elif validation_type == "dir":
        progress_message = f"⏳ Validating directory creation ..."
        success_msg = f"Directory {item_name} created successfully"
    elif validation_type == "upload":
        progress_message = f"⏳ Validating {item_name} ..."
        success_msg = f"{item_name} uploaded successfully"
    else:
        progress_message = f"⏳ Validating {validation_type} ..."
        success_msg = f"{item_name} {validation_type} completed"
    
    # 使用统一的可中断进度循环
    result = interruptible_progress_loop(
        progress_message=progress_message,
        loop_func=validation_func,
        check_interval=1.0,
        max_attempts=max_attempts
    )
    
    # 转换结果格式
    if result["success"]:
        result["message"] = success_msg
    elif result["cancelled"]:
        result["message"] = f"Validation of {item_name} cancelled by user"
    else:
        result["message"] = f"Validation of {item_name} failed after {result['attempts']} attempts"
    
    return result