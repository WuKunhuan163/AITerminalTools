import sys
import os
from pathlib import Path

def get_project_name():
    """获取项目名称"""
    try:
        script_path = Path(__file__).resolve()
        project_path = script_path.parent.parent
        return project_path.name
    except Exception as e:
        return "Agent Project"

def show_dummy_ui(project_name):
    """显示极简的dummy UI，只有一个Proceed按钮"""
    try:
        import tkinter as tk
        
        root = tk.Tk()
        root.title(f"{project_name} - Agent Mode")
        root.geometry("200x40")
        root.attributes('-topmost', True)
        
        # 唯一按钮
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
        
        root.mainloop()
        return True
    
    except Exception:
        return False

def get_user_input_via_terminal(project_name):
    """直接在终端中获取用户输入"""
    title = f"{project_name} - Agent Mode"
    separator = "=" * len(title)
    
    # 显示标题和提示
    print(f"{separator}\n{title}\n{separator}\n")
    print("Enter your next prompt and press Ctrl+D when done.\nPrompt: ", end = "")
    
    # 直接读取整个输入直到EOF
    try:
        input_lines = sys.stdin.read().splitlines()
    except KeyboardInterrupt:  # 处理Ctrl+C
        return "stop"
    
    # 组合所有行为最终输入
    full_input = '\n'.join(input_lines).strip()
    
    # 清理提示行并返回用户输入
    os.system('clear') if os.name == 'posix' else os.system('cls')
    return full_input or "stop"  # 空输入转为stop

if __name__ == "__main__":
    project_name = get_project_name()
    
    # 尝试显示极简UI
    ui_shown = show_dummy_ui(project_name)
    
    # 无论是UI显示成功还是失败，都进入终端输入模式
    user_input = get_user_input_via_terminal(project_name)
    if user_input != "stop":
        user_input += "\n\n上述任务完成之后，接着执行user rule：python others/cursor_userinput.py。等待执行结束，你就能读取终端输出，获得我的反馈。如果你看到python程序停止等异常情况，就再执行一次python others/cursor_userinput.py，直到得到自然语言的反馈。"
    
    # 最终只输出用户的实际输入
    print(user_input)