#!/usr/bin/env python3
"""
测试tkinter键盘事件绑定
用于理解键盘事件的工作机制
"""

import tkinter as tk
import sys

def test_keyboard_events():
    root = tk.Tk()
    root.title("Keyboard Event Test")
    root.geometry("500x300")
    
    # 状态变量
    paste_detected = False
    
    # 创建显示区域
    info_frame = tk.Frame(root)
    info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 事件显示文本框
    event_text = tk.Text(info_frame, height=10, width=60)
    event_text.pack(fill=tk.BOTH, expand=True)
    
    # 按钮框架
    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=5)
    
    # 测试按钮
    test_btn = tk.Button(
        button_frame,
        text="⏳等待粘贴",
        font=("Arial", 10),
        bg="#CCCCCC",
        fg="#666666",
        state=tk.DISABLED
    )
    test_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    def log_event(message):
        event_text.insert(tk.END, message + "\n")
        event_text.see(tk.END)
        print(message, file=sys.stderr)
    
    def activate_button():
        nonlocal paste_detected
        if not paste_detected:
            paste_detected = True
            test_btn.config(
                text="✅已激活",
                bg="#4CAF50",
                fg="white",
                state=tk.NORMAL
            )
            log_event("按钮已激活！")
    
    def on_key_press(event):
        log_event(f"KeyPress: keysym={event.keysym}, state={event.state}, keycode={event.keycode}, char={repr(event.char)}")
        
        # 检测Cmd+C (复制)
        if ((event.state & 0x8) and event.keysym == 'c') or ((event.state & 0x4) and event.keysym == 'c'):
            log_event("检测到复制快捷键 (Cmd+C 或 Ctrl+C)")
            return "break"
        
        # 检测Cmd+V (粘贴)
        if ((event.state & 0x8) and event.keysym == 'v') or ((event.state & 0x4) and event.keysym == 'v'):
            log_event("检测到粘贴快捷键 (Cmd+V 或 Ctrl+V)")
            activate_button()
            return "break"
        
        # 检测Enter键
        if event.keysym == 'Return':
            log_event("检测到Enter键")
            activate_button()
            return "break"
    
    def on_key_release(event):
        log_event(f"KeyRelease: keysym={event.keysym}, state={event.state}")
    
    # 绑定键盘事件
    root.bind('<KeyPress>', on_key_press)
    root.bind('<KeyRelease>', on_key_release)
    root.bind('<Key>', on_key_press)
    
    # 尝试特定绑定
    root.bind('<Control-v>', lambda e: (log_event("特定绑定: Control-v"), activate_button()))
    root.bind('<Command-v>', lambda e: (log_event("特定绑定: Command-v"), activate_button()))
    root.bind('<Meta-v>', lambda e: (log_event("特定绑定: Meta-v"), activate_button()))
    root.bind('<Return>', lambda e: (log_event("特定绑定: Return"), activate_button()))
    
    # 确保窗口获得焦点
    root.focus_force()
    root.lift()
    root.attributes('-topmost', True)
    root.focus_set()
    
    log_event("键盘事件测试窗口已启动")
    log_event("请尝试按下以下键：")
    log_event("- Cmd+V 或 Ctrl+V (粘贴)")
    log_event("- Cmd+C 或 Ctrl+C (复制)")
    log_event("- Enter键")
    log_event("- 任何其他键")
    
    root.mainloop()

if __name__ == "__main__":
    test_keyboard_events()
