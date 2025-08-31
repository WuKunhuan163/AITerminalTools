#!/usr/bin/env python3
"""
Google Drive - Sync Config Manager Module
从GOOGLE_DRIVE.py重构而来的sync_config_manager模块
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

# 导入Google Drive Shell管理类 - 注释掉避免循环导入
# try:
#     from google_drive_shell import GoogleDriveShell
# except ImportError as e:
#     print(f"❌ 导入Google Drive Shell失败: {e}")
#     GoogleDriveShell = None

# 添加缺失的工具函数
def get_multiline_input_safe(prompt, single_line=False):
    """
    安全的多行输入函数，支持Ctrl+D结束输入
    
    Args:
        prompt (str): 输入提示
        single_line (bool): 是否只接受单行输入
        
    Returns:
        str: 用户输入的内容，如果用户取消则返回None
    """
    try:
        # 配置readline以支持中文字符
        import readline
        try:
            readline.set_startup_hook(None)
            readline.clear_history()
            
            # 设置编辑模式为emacs（支持更好的中文编辑）
            readline.parse_and_bind("set editing-mode emacs")
            # 启用UTF-8支持
            readline.parse_and_bind("set input-meta on")
            readline.parse_and_bind("set output-meta on")
            readline.parse_and_bind("set convert-meta off")
            # 启用中文字符显示
            readline.parse_and_bind("set print-completions-horizontally off")
            readline.parse_and_bind("set skip-completed-text on")
            # 确保正确处理宽字符
            readline.parse_and_bind("set enable-bracketed-paste on")
        except Exception:
            pass  # 如果配置失败，继续使用默认设置
        
        print(prompt, end="", flush=True)
        
        if single_line:
            # 单行输入
            try:
                return input()
            except EOFError:
                return None
        else:
            # 多行输入，直到Ctrl+D
            lines = []
            print("(多行输入，按 Ctrl+D 结束):")
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                # Ctrl+D被按下，结束输入
                pass
            
            return '\n'.join(lines) if lines else None
            
    except KeyboardInterrupt:
        # Ctrl+C被按下
        print("\n输入已取消")
        return None
    except Exception as e:
        print(f"\n输入错误: {e}")
        return None

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
    except Exception as e:
        print(f"写入JSON输出文件失败: {e}")
        return False

# 全局常量

def get_sync_config_file():
    """获取同步配置文件路径"""
    # 从modules目录向上两级到bin目录，然后进入GOOGLE_DRIVE_DATA
    data_dir = Path(__file__).parent.parent.parent / "GOOGLE_DRIVE_DATA"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "sync_config.json"

def load_sync_config():
    """加载同步配置"""
    try:
        config_file = get_sync_config_file()
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 返回默认配置
            return {
                "local_equivalent": "/Users/wukunhuan/Applications/Google Drive",
                "drive_equivalent": "/content/drive/Othercomputers/我的 MacBook Air/Google Drive",
                "drive_equivalent_folder_id": "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
            }
    except Exception as e:
        print(f"加载同步配置失败: {e}")
        return {
            "local_equivalent": "/Users/wukunhuan/Applications/Google Drive",
            "drive_equivalent": "/content/drive/Othercomputers/我的 MacBook Air/Google Drive", 
            "drive_equivalent_folder_id": "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
        }

def save_sync_config(config):
    """保存同步配置"""
    try:
        config_file = get_sync_config_file()
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存同步配置失败: {e}")
        return False

def set_local_sync_dir(command_identifier=None):
    """设置本地同步目录"""
    try:
        # 加载当前配置
        config = load_sync_config()
        current_local = config.get("local_equivalent", "未设置")
        
        if is_run_environment(command_identifier):
            # RUN环境下返回交互式设置信息
            write_to_json_output({
                "success": True,
                "action": "interactive_setup",
                "current_local_equivalent": current_local,
                "instructions": "请在终端中运行: GOOGLE_DRIVE --desktop --set-local-sync-dir"
            }, command_identifier)
            return 0
        
        print("🔧 设置本地同步目录")
        print("=" * 50)
        print(f"当前设置: {current_local}")
        print()
        
        new_path = get_multiline_input_safe("请输入新的本地同步目录路径 (直接回车保持不变): ", single_line=True)
        
        if not new_path:
            print("✅ 保持当前设置不变")
            return 0
        
        # 展开路径
        expanded_path = os.path.expanduser(os.path.expandvars(new_path))
        
        # 检查路径是否存在
        if not os.path.exists(expanded_path):
            print(f"❌ 错误: 路径不存在: {expanded_path}")
            print("请确认路径正确后重试")
            return 1
        
        if not os.path.isdir(expanded_path):
            print(f"❌ 错误: 路径不是目录: {expanded_path}")
            return 1
        
        # 更新配置
        config["local_equivalent"] = expanded_path
        
        if save_sync_config(config):
            print(f"✅ 本地同步目录已更新: {expanded_path}")
            return 0
        else:
            print("❌ 保存配置失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ 操作已取消")
        return 1
    except Exception as e:
        error_msg = f"设置本地同步目录时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"❌ {error_msg}")
        return 1

def set_global_sync_dir(command_identifier=None):
    """设置全局同步目录"""
    try:
        # 加载当前配置
        config = load_sync_config()
        current_drive = config.get("drive_equivalent", "未设置")
        current_folder_id = config.get("drive_equivalent_folder_id", "未设置")
        
        if is_run_environment(command_identifier):
            # RUN环境下返回交互式设置信息
            write_to_json_output({
                "success": True,
                "action": "interactive_setup",
                "current_drive_equivalent": current_drive,
                "current_folder_id": current_folder_id,
                "instructions": "请在终端中运行: GOOGLE_DRIVE --desktop --set-global-sync-dir"
            }, command_identifier)
            return 0
        
        print("🔧 设置全局同步目录")
        print("=" * 50)
        print(f"当前设置:")
        print(f"  逻辑路径: {current_drive}")
        print(f"  文件夹ID: {current_folder_id}")
        print()
        
        # 获取文件夹URL
        folder_url = get_multiline_input_safe("请输入Google Drive文件夹链接 (直接回车保持不变): ", single_line=True)
        
        if not folder_url:
            print("✅ 保持当前设置不变")
            return 0
        
        # 提取文件夹ID
        folder_id = extract_folder_id_from_url(folder_url)
        if not folder_id:
            print("❌ 错误: 无法从URL中提取文件夹ID")
            print("请确认URL格式正确，例如: https://drive.google.com/drive/u/0/folders/1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
            return 1
        
        print(f"📁 提取到文件夹ID: {folder_id}")
        
        # 测试文件夹访问
        print("🔍 测试文件夹访问权限...")
        if not test_drive_folder_access(folder_id):
            print("❌ 错误: 无法访问该文件夹")
            print("请确认:")
            print("  1. 文件夹ID正确")
            print("  2. 服务账户有访问权限")
            print("  3. 网络连接正常")
            return 1
        
        print("✅ 文件夹访问测试通过")
        
        # 获取逻辑路径
        logical_path = get_multiline_input_safe("请输入该文件夹对应的逻辑路径 (例如: /content/drive/Othercomputers/我的 MacBook Air/Google Drive): ", single_line=True)
        
        if not logical_path:
            print("❌ 错误: 逻辑路径不能为空")
            return 1
        
        # 测试上传工作流程
        print("🧪 测试上传工作流程...")
        test_result = test_upload_workflow(logical_path, folder_id, command_identifier)
        
        if not test_result["success"]:
            print(f"❌ 上传工作流程测试失败: {test_result['error']}")
            print("请检查逻辑路径是否正确")
            print("注意: REMOTE_ROOT的逻辑路径应为 /content/drive/MyDrive/REMOTE_ROOT")
            return 1
        
        print("✅ 上传工作流程测试通过")
        
        # 更新配置
        config["drive_equivalent"] = logical_path
        config["drive_equivalent_folder_id"] = folder_id
        
        if save_sync_config(config):
            print("✅ 全局同步目录配置已更新:")
            print(f"  文件夹ID: {folder_id}")
            print(f"  逻辑路径: {logical_path}")
            
            # 更新GoogleDriveShell实例的配置
            try:
                shell = GoogleDriveShell()
                shell.DRIVE_EQUIVALENT = logical_path
                shell.DRIVE_EQUIVALENT_FOLDER_ID = folder_id
                print("✅ 运行时配置也已同步更新")
            except:
                pass  # 如果更新失败也不影响主要功能
            
            return 0
        else:
            print("❌ 保存配置失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n❌ 操作已取消")
        return 1
    except Exception as e:
        error_msg = f"设置全局同步目录时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"❌ {error_msg}")
        return 1

def get_google_drive_status(command_identifier=None):
    """获取Google Drive Desktop状态信息"""
    try:
        # 导入需要的函数（延迟导入避免循环依赖）
        import sys
        current_module = sys.modules[__name__]
        parent_module = sys.modules.get('modules')
        
        if parent_module:
            is_google_drive_running = getattr(parent_module, 'is_google_drive_running', None)
            get_google_drive_processes = getattr(parent_module, 'get_google_drive_processes', None)
            is_run_environment = getattr(parent_module, 'is_run_environment', None)
            write_to_json_output = getattr(parent_module, 'write_to_json_output', None)
        else:
            # 回退到全局命名空间查找
            is_google_drive_running = globals().get('is_google_drive_running')
            get_google_drive_processes = globals().get('get_google_drive_processes')
            is_run_environment = globals().get('is_run_environment') 
            write_to_json_output = globals().get('write_to_json_output')
        
        if not all([is_google_drive_running, get_google_drive_processes, is_run_environment, write_to_json_output]):
            raise ImportError("Required functions not available")
            
        running = is_google_drive_running()
        processes = get_google_drive_processes()
        
        result_data = {
            "success": True,
            "running": running,
            "process_count": len(processes),
            "processes": processes,
            "message": f"Google Drive {'正在运行' if running else '未运行'} ({len(processes)} 个进程)"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(result_data["message"])
            if running and processes:
                print(f"进程ID: {', '.join(processes)}")
        return 0
        
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"获取状态时出错: {e}"
        }
        
        # 尝试输出错误
        try:
            if 'is_run_environment' in locals() and 'write_to_json_output' in locals():
                if is_run_environment(command_identifier):
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_data["error"])
            else:
                print(error_data["error"])
        except:
            print(f"获取状态时出错: {e}")
        return 1
