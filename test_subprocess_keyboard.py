#!/usr/bin/env python3
"""
测试subprocess中的tkinter键盘事件绑定
模拟GDS窗口的subprocess环境
"""

import subprocess
import sys
import json

def test_subprocess_keyboard():
    # 创建与GDS窗口相似的subprocess脚本
    subprocess_script = '''
import sys
import os
import json
import warnings
import tkinter as tk

# 抑制所有警告
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

try:
    result = {"action": "timeout"}
    
    root = tk.Tk()
    root.title("Subprocess Keyboard Test")
    root.geometry("500x100")
    root.resizable(False, False)
    
    # 居中窗口
    root.eval('tk::PlaceWindow . center')
    
    # 状态变量
    paste_detected = False
    button_clicked = False
    
    # 主框架
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 测试输入框
    test_entry = tk.Entry(main_frame, width=30)
    test_entry.pack(fill=tk.X, pady=(0, 5))
    test_entry.insert(0, "Test focus here - press Cmd+V")
    
    # 按钮框架
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, expand=True)
    
    def on_key_press(event):
        global button_clicked, paste_detected
        
        # 详细的debug输出
        print(f"DEBUG: KeyPress event - keysym: {event.keysym}, state: {event.state}, keycode: {event.keycode}, char: {repr(event.char)}", file=sys.stderr)
        
        # Command+V (Mac) 或 Ctrl+V (Windows/Linux) - 检测粘贴操作
        if ((event.state & 0x8) and event.keysym == 'v') or ((event.state & 0x4) and event.keysym == 'v'):
            print(f"DEBUG: Paste shortcut detected!", file=sys.stderr)
            if not paste_detected:
                paste_detected = True
                print(f"DEBUG: Activating test button!", file=sys.stderr)
                test_btn.config(
                    text="✅已激活",
                    bg="#4CAF50",
                    fg="white"
                )
        
        # Enter键
        if event.keysym == 'Return':
            print(f"DEBUG: Return key detected!", file=sys.stderr)
            if not paste_detected:
                paste_detected = True
                test_btn.config(
                    text="✅已激活",
                    bg="#4CAF50",
                    fg="white"
                )
    
    def test_complete():
        global button_clicked
        button_clicked = True
        result["action"] = "success"
        result["message"] = "Test completed successfully"
        root.destroy()
    
    # 测试按钮
    test_btn = tk.Button(
        button_frame,
        text="⏳等待粘贴",
        command=test_complete,
        font=("Arial", 10),
        bg="#CCCCCC",
        fg="#666666"
    )
    test_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 绑定键盘事件
    root.bind('<Key>', on_key_press)
    
    # 确保窗口获得焦点
    root.focus_force()
    root.lift()
    root.attributes('-topmost', True)
    root.focus_set()
    
    print("DEBUG: Subprocess keyboard test window started", file=sys.stderr)
    
    # 设置超时
    def timeout_destroy():
        result.update({"action": "timeout", "message": "Test timed out"})
        root.destroy()
    
    root.after(30000, timeout_destroy)  # 30秒超时
    
    # 运行窗口
    root.mainloop()
    
    # 输出结果
    print(json.dumps(result))

except Exception as e:
    print(json.dumps({"action": "error", "message": str(e)}))
'''
    
    try:
        # 启动子进程
        process = subprocess.Popen(
            ['python', '-c', subprocess_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("Subprocess keyboard test started. Please try pressing Cmd+V in the window.")
        
        # 等待进程完成
        stdout, stderr = process.communicate(timeout=35)
        
        # 输出stderr以便看到debug信息
        if stderr.strip():
            print(f"SUBPROCESS STDERR:\n{stderr}")
        
        # 解析结果
        if process.returncode == 0 and stdout.strip():
            try:
                result = json.loads(stdout.strip())
                print(f"Test result: {result}")
                return result
            except json.JSONDecodeError as e:
                print(f"Failed to parse result: {e}")
                return {"action": "error", "message": f"Result parsing failed: {e}"}
        else:
            return {"action": "error", "message": f"Process failed: returncode={process.returncode}"}
            
    except subprocess.TimeoutExpired:
        process.kill()
        return {"action": "timeout", "message": "Test timed out"}
    except Exception as e:
        return {"action": "error", "message": f"Test failed: {e}"}

if __name__ == "__main__":
    result = test_subprocess_keyboard()
    print(f"Final result: {result}")
