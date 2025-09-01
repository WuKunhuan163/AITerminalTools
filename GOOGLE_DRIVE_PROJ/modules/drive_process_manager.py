#!/usr/bin/env python3
"""
Google Drive - Drive Process Manager Module
从GOOGLE_DRIVE.py重构而来的drive_process_manager模块
"""

import os
import sys
import json
import webbrowser
import hashlib
import subprocess
import time
import uuid
import warnings
from pathlib import Path
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
from dotenv import load_dotenv
load_dotenv()

# 添加缺失的工具函数
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
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# 导入Google Drive Shell管理类 - 注释掉避免循环导入
# try:
#     from google_drive_shell import GoogleDriveShell
# except ImportError as e:
#     print(f"Error: Load Google Drive Shell failed: {e}")
#     GoogleDriveShell = None

# 全局常量

def is_google_drive_running():
    """检查Google Drive Desktop是否正在运行"""
    try:
        result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                              capture_output=True, text=True)
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False

def get_google_drive_processes():
    """获取Google Drive进程信息"""
    try:
        result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return [pid for pid in pids if pid]
        return []
    except Exception:
        return []

def shutdown_google_drive(command_identifier=None):
    """关闭Google Drive Desktop"""
    try:
        if not is_google_drive_running():
            result_data = {
                "success": True,
                "message": "Google Drive is already stopped",
                "action": "shutdown",
                "was_running": False
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(result_data["message"])
            return 0
        
        # 尝试优雅关闭
        result = subprocess.run(['killall', 'Google Drive'], 
                              capture_output=True, text=True)
        
        # 等待一下让进程完全关闭
        time.sleep(2)
        
        # 检查是否成功关闭
        if not is_google_drive_running():
            result_data = {
                "success": True,
                "message": "Google Drive has been closed",
                "action": "shutdown",
                "was_running": True
            }
        else:
            pids = get_google_drive_processes()
            for pid in pids:
                subprocess.run(['kill', '-9', pid], capture_output=True)
            
            time.sleep(1)
            
            if not is_google_drive_running():
                result_data = {
                    "success": True,
                    "message": "Google Drive has been closed",
                    "action": "shutdown",
                    "was_running": True,
                    "forced": True
                }
            else:
                result_data = {
                    "success": False,
                    "error": "Cannot close Google Drive",
                    "action": "shutdown"
                }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(result_data.get("message", result_data.get("error")))
        
        return 0 if result_data["success"] else 1
                
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"关闭 Google Drive 时出错: {e}",
            "action": "shutdown"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(error_data["error_info"])
        return 1

def launch_google_drive(command_identifier=None):
    """启动Google Drive Desktop"""
    try:
        if is_google_drive_running():
            result_data = {
                "success": True,
                "message": "Google Drive 已经在运行",
                "action": "launch",
                "was_running": True
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(result_data["message"])
            return 0
        
        if not is_run_environment(command_identifier):
            print(f"Launching Google Drive...")
        
        # 启动Google Drive
        result = subprocess.run(['open', '-a', 'Google Drive'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            result_data = {
                "success": False,
                "error": f"Failed to launch Google Drive: {result.stderr}",
                "action": "launch"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(result_data["error_info"])
            return 1
        
        # 等待启动
        max_wait = 10  # 最多等待10秒
        for i in range(max_wait):
            time.sleep(1)
            if is_google_drive_running():
                result_data = {
                    "success": True,
                    "message": f"Google Drive has been launched (startup time {i+1} seconds)",
                    "action": "launch",
                    "was_running": False,
                    "startup_time": i+1
                }
                
                if is_run_environment(command_identifier):
                    write_to_json_output(result_data, command_identifier)
                else:
                    print(result_data["message"])
                return 0
        
        # 超时但可能已启动
        if is_google_drive_running():
            result_data = {
                "success": True,
                "message": "Google Drive has been launched (startup time longer)",
                "action": "launch",
                "was_running": False,
                "startup_time": max_wait
            }
        else:
            result_data = {
                "success": False,
                "error": "Google Drive startup timeout",
                "action": "launch"
            }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(result_data.get("message", result_data.get("error")))
        
        return 0 if result_data["success"] else 1
            
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"启动 Google Drive 时出错: {e}",
            "action": "launch"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(error_data["error_info"])
        return 1

def restart_google_drive(command_identifier=None):
    """重启Google Drive Desktop"""
    try:
        if not is_run_environment(command_identifier):
            print(f"Restarting Google Drive...")
        
        # 先关闭
        shutdown_result = shutdown_google_drive(command_identifier)
        if shutdown_result != 0:
            error_data = {
                "success": False,
                "error": "Restart failed - shutdown phase failed",
                "action": "restart"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(error_data["error_info"])
            return 1
        
        # 等待一下确保完全关闭
        time.sleep(3)
        
        # 再启动
        launch_result = launch_google_drive(command_identifier)
        if launch_result != 0:
            error_data = {
                "success": False,
                "error": "Restart failed - launch phase failed",
                "action": "restart"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(error_data["error_info"])
            return 1
        
        result_data = {
            "success": True,
            "message": "Google Drive has been restarted",
            "action": "restart"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(result_data["message"])
        return 0
        
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"Restart Google Drive failed: {e}",
            "action": "restart"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(error_data["error_info"])
        return 1
