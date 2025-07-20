#!/usr/bin/env python3
"""
USERINPUT.py - User Input Script for Cursor AI
Specialized script for getting user feedback in Cursor AI workflows
Can be used as both a standalone script and as an interface with unique identifiers
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False


def get_project_name():
    """获取项目名称"""
    try:
        # 从当前工作目录获取项目名称
        current_dir = Path.cwd()
        # 尝试找到项目根目录
        project_dir = current_dir
        while project_dir.parent != project_dir:
            if (project_dir / '.git').exists():
                break
            project_dir = project_dir.parent
        return project_dir.name, current_dir, project_dir
    except Exception as e:
        return "Agent Project", Path.cwd(), Path.cwd()

def show_project_info(current_dir, project_dir):
    """显示项目信息"""
    print(f"current_dir: {current_dir}")
    print(f"project_dir: {project_dir}")
    print(f"project_dir.name: {project_dir.name}")
    if is_run_environment():
        run_identifier = os.environ.get('RUN_IDENTIFIER')
        output_file = os.environ.get('RUN_DATA_FILE')
        if run_identifier:
            print(f"RUN identifier: {run_identifier}")
        if output_file:
            print(f"Output file: {output_file}")

def show_prompt_header(project_name):
    """显示提示头部信息"""
    if is_run_environment():
        run_identifier = os.environ.get('RUN_IDENTIFIER', '')
        title = f"{project_name} - Agent Mode (RUN: {run_identifier[:8]}...)"
    else:
        title = f"{project_name} - Agent Mode"
    
    separator = "=" * len(title)
    
    print(f"\n{separator}")
    print(f"{title}")
    print(f"{separator}")
    print("\nEnter your next prompt. Press Ctrl+D (EOF) when done.")
    print("Prompt: ", end="", flush=True)

def show_dummy_ui(project_name):
    """显示极简的dummy UI，只有一个Proceed按钮"""
    try:
        import tkinter as tk
        
        root = tk.Tk()
        title = f"{project_name} - Agent Mode"
        
        root.title(title)
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
    
    # 读取多行输入直到EOF (Ctrl+D)
    lines = []
    try:
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                # Ctrl+D 被按下，结束输入
                break
    except KeyboardInterrupt:
        # Ctrl+C 被按下
        return "stop"
    
    # 组合所有行为最终输入
    full_input = '\n'.join(lines).strip()
    
    # 清理屏幕
    if not is_run_environment():
        print("\n" + "="*50)
    return full_input or "stop"  # 空输入转为stop

def write_to_json_output(user_input, command_identifier=None):
    """将用户输入写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 准备 JSON 数据
        data = {
            'success': True,
            'type': 'user_input',
            'user_input': user_input,
            'message': 'User input received successfully'
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def main():
    """主函数，支持命令行参数"""
    # 获取command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    
    # 解析命令行参数
    if len(args) > 0:
        if args[0] in ['--help', '-h']:
            # 显示帮助信息
            print("""USERINPUT - User Input Script for Cursor AI

Usage:
  USERINPUT                    Get user input interactively
  USERINPUT --help             Show this help message

Description:
  This tool is used to get user feedback in Cursor AI workflows.
  It can work both standalone and within the RUN environment.
""")
            return
    
    # 获取项目信息
    project_name, current_dir, project_dir = get_project_name()
    
    # 尝试显示极简UI（仅在非RUN环境中）
    if not is_run_environment(command_identifier):
        show_dummy_ui(project_name)
        show_project_info(current_dir, project_dir)
        show_prompt_header(project_name)
    
    user_input = get_user_input_via_terminal(project_name)
    
    if is_run_environment(command_identifier):
        if not write_to_json_output(user_input, command_identifier):
            print("Failed to write user input to JSON file.")
            print(user_input)
    else:
        # 不在 RUN 环境中，直接输出到 stdout（保持原有行为）
        os.system("clear") if os.name == "posix" else os.system("cls")
        if user_input != "stop":
            user_input += "\n\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如遇异常情况（如程序停止），重复执行 `USERINPUT` 直到获得自然语言反馈。执行过程中遇到不确定的情况，请使用 `USERINPUT` 确认，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
        print(user_input)

if __name__ == "__main__":
    main() 