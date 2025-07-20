#!/usr/bin/env python3
"""
GOOGLE_DRIVE.py - Google Drive access tool
Opens Google Drive in browser with RUN environment detection
"""

import os
import sys
import json
import webbrowser
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

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
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
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def open_google_drive(url=None, command_identifier=None):
    """打开Google Drive"""
    
    # 默认URL
    if url is None:
        url = "https://drive.google.com/"
    
    try:
        # 打开浏览器
        success = webbrowser.open(url)
        
        if success:
            success_data = {
                "success": True,
                "message": "Google Drive opened successfully",
                "url": url,
                "action": "browser_opened"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(success_data, command_identifier)
            else:
                print(f"🚀 Opening Google Drive: {url}")
                print("✅ Google Drive opened successfully in browser")
            return 0
        else:
            error_data = {
                "success": False,
                "error": "Failed to open browser",
                "url": url
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"❌ Error: Failed to open browser for {url}")
            return 1
    
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"Error opening Google Drive: {str(e)}",
            "url": url
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"❌ Error opening Google Drive: {e}")
        return 1

def show_help():
    """显示帮助信息"""
    help_text = """GOOGLE_DRIVE - Google Drive access tool

Usage: GOOGLE_DRIVE [url] [options]

Arguments:
  url                  Custom Google Drive URL (default: https://drive.google.com/)

Options:
  -my                  Open My Drive (https://drive.google.com/drive/u/0/my-drive)
  --help, -h           Show this help message

Examples:
  GOOGLE_DRIVE                                    # Open main Google Drive
  GOOGLE_DRIVE -my                                # Open My Drive folder
  GOOGLE_DRIVE https://drive.google.com/drive/my-drive  # Open specific folder
  GOOGLE_DRIVE --help                             # Show help"""
    
    print(help_text)

def main():
    """主函数"""
    # 获取执行上下文和command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    url = None
    
    # 处理参数
    if len(args) == 0:
        # 没有参数，使用默认URL
        url = None
    elif len(args) == 1:
        if args[0] in ['--help', '-h']:
            if is_run_environment(command_identifier):
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": "GOOGLE_DRIVE - Google Drive access tool"
                }
                write_to_json_output(help_data, command_identifier)
            else:
                show_help()
            return 0
        elif args[0] == '-my':
            # My Drive URL
            url = "https://drive.google.com/drive/u/0/my-drive"
        else:
            # 假设是URL
            url = args[0]
    else:
        # 多个参数，检查是否有帮助选项
        if '--help' in args or '-h' in args:
            if is_run_environment(command_identifier):
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": "GOOGLE_DRIVE - Google Drive access tool"
                }
                write_to_json_output(help_data, command_identifier)
            else:
                show_help()
            return 0
        elif '-my' in args:
            # My Drive URL
            url = "https://drive.google.com/drive/u/0/my-drive"
        else:
            error_msg = "❌ Error: Too many arguments. Use --help for usage information."
            if is_run_environment(command_identifier):
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, command_identifier)
            else:
                print(error_msg)
            return 1
    
    # 打开Google Drive
    return open_google_drive(url, command_identifier)

if __name__ == "__main__":
    sys.exit(main()) 