#!/usr/bin/env python3
"""
测试subprocess中的tkinter键盘事件绑定 - 更接近GDS窗口
"""

import subprocess
import sys
import json

def test_subprocess_keyboard():
    # 创建更接近GDS窗口的subprocess脚本
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
    root.title("GDS-like Keyboard Test")
    root.geometry("500x100")
    root.resizable(False, False)
    
    # 居中窗口
    root.eval('tk::PlaceWindow . center')
    
    # 状态变量
    paste_detected = False
    button_clicked = False
    
    # 自动复制命令到剪切板
    command_text = "echo 'test command'"
    root.clipboard_clear()
    root.clipboard_append(command_text)
    
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
    
    def copy_command():
        global button_clicked
        button_clicked = True
        try:
            root.clipboard_clear()
            root.clipboard_append(command_text)
            copy_btn.config(text="✅复制成功", bg="#4CAF50")
            root.after(1500, lambda: copy_btn.config(text="📋复制指令", bg="#2196F3"))
        except Exception as e:
            copy_btn.config(text="Error: 复制失败", bg="#f44336")
    
    def test_activation():
        global paste_detected
        if not paste_detected:
            paste_detected = True
            test_btn.config(text="✅已激活", bg="#4CAF50")
            # 启用直接反馈按钮
            feedback_btn.config(
                text="💬直接反馈",
                bg="#FF9800",
                fg="white",
                state=tk.NORMAL
            )
            # 启用执行完成按钮
            complete_btn.config(
                text="✅执行完成",
                bg="#4CAF50",
                fg="white",
                state=tk.NORMAL
            )
    
    def direct_feedback():
        global button_clicked
        button_clicked = True
        result["action"] = "direct_feedback"
        result["message"] = "Direct feedback selected"
        root.destroy()
    
    def execution_completed():
        global button_clicked
        button_clicked = True
        result["action"] = "success"
        result["message"] = "Execution completed"
        root.destroy()
    
    def on_key_press(event):
        global button_clicked, paste_detected
        
        # 详细的debug输出
        print(f"DEBUG: KeyPress event - keysym: {event.keysym}, state: {event.state}, keycode: {event.keycode}, char: {repr(event.char)}", file=sys.stderr)
        
        # Command+C (Mac) 或 Ctrl+C (Windows/Linux) -复制指令
        if ((event.state & 0x8) and event.keysym == 'c') or ((event.state & 0x4) and event.keysym == 'c'):
            print(f"DEBUG: Copy shortcut detected!", file=sys.stderr)
            button_clicked = True
            copy_command()
            return "break"
        
        # Command+V (Mac) 或 Ctrl+V (Windows/Linux) - 检测粘贴操作
        if ((event.state & 0x8) and event.keysym == 'v') or ((event.state & 0x4) and event.keysym == 'v'):
            print(f"DEBUG: Paste shortcut detected!", file=sys.stderr)
            test_activation()
            return "break"
        
        # Enter键
        if event.keysym == 'Return':
            print(f"DEBUG: Return key detected!", file=sys.stderr)
            test_activation()
            return "break"
    
    # 复制指令按钮
    copy_btn = tk.Button(
        button_frame, 
        text="📋复制指令", 
        command=copy_command,
        font=("Arial", 9),
        bg="#2196F3",
        fg="white",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    copy_btn.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=True)
    
    # 测试按钮
    test_btn = tk.Button(
        button_frame,
        text="🧪测试激活",
        command=test_activation,
        font=("Arial", 8),
        bg="#9C27B0",
        fg="white",
        padx=5,
        pady=5,
        relief=tk.RAISED,
        bd=2
    )
    test_btn.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=False)
    
    # 直接反馈按钮 - 默认禁用
    feedback_btn = tk.Button(
        button_frame, 
        text="⏳等待粘贴", 
        command=direct_feedback,
        font=("Arial", 9),
        bg="#CCCCCC",
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2,
        state=tk.DISABLED
    )
    feedback_btn.pack(side=tk.LEFT, padx=(0, 2), fill=tk.X, expand=True)
    
    # 执行完成按钮 - 默认禁用
    complete_btn = tk.Button(
        button_frame, 
        text="⏳等待粘贴", 
        command=execution_completed,
        font=("Arial", 9, "bold"),
        bg="#CCCCCC",
        fg="#666666",
        padx=10,
        pady=5,
        relief=tk.RAISED,
        bd=2,
        state=tk.DISABLED
    )
    complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 设置焦点到完成按钮
    complete_btn.focus_set()
    
    # 绑定键盘事件
    root.bind('<Key>', on_key_press)
    
    # 确保窗口获得焦点
    root.focus_force()
    root.lift()
    root.attributes('-topmost', True)
    root.focus_set()
    
    print("DEBUG: GDS-like keyboard test window started", file=sys.stderr)
    
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
        
        print("GDS-like keyboard test started. Please try pressing Cmd+V in the window.")
        
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
