#!/usr/bin/env python3
"""
简化的USERINPUT测试版本，用于诊断tkinter窗口问题
"""

import subprocess
import sys
import os

def show_simple_tkinter_window(project_name, timeout_seconds):
    """显示简化的tkinter窗口"""
    
    # 创建简化的子进程脚本
    subprocess_script = f'''
import sys
import os
import warnings

# 抑制所有警告
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

try:
    import tkinter as tk
    
    root = tk.Tk()
    root.title("{project_name} - Agent Mode")
    root.geometry("300x80")
    root.attributes('-topmost', True)
    
    # 简单的聚焦函数
    def force_focus():
        try:
            root.focus_force()
            root.lift()
            root.attributes('-topmost', True)
        except:
            pass
    
    # 初始聚焦
    force_focus()
    
    # 创建按钮
    btn = tk.Button(
        root, 
        text="Click to Enter Prompt", 
        command=root.destroy,
        padx=20,
        pady=10,
        bg="#4CAF50",
        fg="white",
        font=("Arial", 10, "bold")
    )
    btn.pack(expand=True)
    
    # 设置自动关闭定时器
    root.after({timeout_seconds * 1000}, root.destroy)
    
    print("Starting tkinter window...")
    # 运行窗口
    root.mainloop()
    
    # 输出结果
    print("clicked")
    
except Exception as e:
    print(f"error: {{e}}")
'''
    
    try:
        print("Starting subprocess...")
        result = subprocess.run(
            [sys.executable, '-c', subprocess_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds + 5
        )
        
        print(f"Subprocess completed with return code: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        
        # 检查结果
        if result.returncode == 0 and "clicked" in result.stdout:
            return True
        else:
            return False
            
    except subprocess.TimeoutExpired:
        print("Subprocess timed out")
        return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("Testing simple tkinter window...")
    result = show_simple_tkinter_window("Test Project", 8)
    print(f"Final result: {result}")
