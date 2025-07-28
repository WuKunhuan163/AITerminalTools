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
import subprocess
import time
import uuid
import warnings
from pathlib import Path

# 抑制urllib3的SSL警告
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 导入Google Drive Shell管理类
try:
    sys.path.insert(0, str(Path(__file__).parent / "GOOGLE_DRIVE_PROJ"))
    from google_drive_shell import GoogleDriveShell
except ImportError as e:
    print(f"❌ 导入Google Drive Shell失败: {e}")
    GoogleDriveShell = None

def get_multiline_input_safe(prompt_text="请输入内容", single_line=True):
    """
    安全的输入处理函数，支持多行输入和Ctrl+D结束输入
    参考USERINPUT.py的实现，避免Ctrl+D导致Cursor terminal停止的问题
    
    Args:
        prompt_text (str): 提示文本
        single_line (bool): 是否为单行输入模式，True表示使用标准input()，False表示多行输入
    
    Returns:
        str: 用户输入的内容，如果取消返回None
    """
    if single_line:
        # 单行输入模式，使用标准input()但添加异常处理
        try:
            return input(prompt_text).strip()
        except EOFError:
            # Ctrl+D被按下，在单行模式下返回空字符串
            print("\n输入已结束")
            return ""
        except KeyboardInterrupt:
            # Ctrl+C被按下
            print("\n输入已取消")
            return None
    else:
        # 多行输入模式，类似USERINPUT.py的处理方式
        print(f"{prompt_text}")
        print("多行输入模式：输入完成后按 Ctrl+D (EOF) 结束输入")
        print("输入内容: ", end="", flush=True)
        
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
            print("\n输入已取消")
            return None
        
        # 组合所有行为最终输入
        full_input = '\n'.join(lines).strip()
        return full_input if full_input else ""

# 全局常量
HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
HOME_FOLDER_ID = "root"  # Google Drive中My Drive的文件夹ID
REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"  # REMOTE_ROOT文件夹ID

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

def copy_to_clipboard(text):
    """将文本复制到剪贴板"""
    try:
        # macOS
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        # Linux
        elif sys.platform == "linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
        # Windows
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode(), check=True, shell=True)
        return True
    except:
        return False

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
                "message": "Google Drive 已经停止运行",
                "action": "shutdown",
                "was_running": False
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(result_data["message"])
            return 0
        
        if not is_run_environment(command_identifier):
            print("🔄 正在关闭 Google Drive...")
        
        # 尝试优雅关闭
        result = subprocess.run(['killall', 'Google Drive'], 
                              capture_output=True, text=True)
        
        # 等待一下让进程完全关闭
        time.sleep(2)
        
        # 检查是否成功关闭
        if not is_google_drive_running():
            result_data = {
                "success": True,
                "message": "✅ Google Drive 已成功关闭",
                "action": "shutdown",
                "was_running": True
            }
        else:
            # 如果优雅关闭失败，使用强制关闭
            if not is_run_environment(command_identifier):
                print("🔧 尝试强制关闭...")
            pids = get_google_drive_processes()
            for pid in pids:
                subprocess.run(['kill', '-9', pid], capture_output=True)
            
            time.sleep(1)
            
            if not is_google_drive_running():
                result_data = {
                    "success": True,
                    "message": "✅ Google Drive 已强制关闭",
                    "action": "shutdown",
                    "was_running": True,
                    "forced": True
                }
            else:
                result_data = {
                    "success": False,
                    "error": "❌ 无法关闭 Google Drive",
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
            print(error_data["error"])
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
            print("🚀 正在启动 Google Drive...")
        
        # 启动Google Drive
        result = subprocess.run(['open', '-a', 'Google Drive'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            result_data = {
                "success": False,
                "error": f"❌ 启动 Google Drive 失败: {result.stderr}",
                "action": "launch"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(result_data["error"])
            return 1
        
        # 等待启动
        max_wait = 10  # 最多等待10秒
        for i in range(max_wait):
            time.sleep(1)
            if is_google_drive_running():
                result_data = {
                    "success": True,
                    "message": f"✅ Google Drive 已成功启动 (耗时 {i+1} 秒)",
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
                "message": "✅ Google Drive 已启动 (启动时间较长)",
                "action": "launch",
                "was_running": False,
                "startup_time": max_wait
            }
        else:
            result_data = {
                "success": False,
                "error": "❌ Google Drive 启动超时",
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
            print(error_data["error"])
        return 1

def restart_google_drive(command_identifier=None):
    """重启Google Drive Desktop"""
    try:
        if not is_run_environment(command_identifier):
            print("🔄 正在重启 Google Drive...")
        
        # 先关闭
        shutdown_result = shutdown_google_drive(command_identifier)
        if shutdown_result != 0:
            error_data = {
                "success": False,
                "error": "重启失败 - 关闭阶段失败",
                "action": "restart"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(error_data["error"])
            return 1
        
        # 等待一下确保完全关闭
        time.sleep(3)
        
        # 再启动
        launch_result = launch_google_drive(command_identifier)
        if launch_result != 0:
            error_data = {
                "success": False,
                "error": "重启失败 - 启动阶段失败",
                "action": "restart"
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(error_data["error"])
            return 1
        
        result_data = {
            "success": True,
            "message": "✅ Google Drive 已成功重启",
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
            "error": f"重启 Google Drive 时出错: {e}",
            "action": "restart"
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(error_data["error"])
        return 1

def get_sync_config_file():
    """获取同步配置文件路径"""
    data_dir = Path(__file__).parent / "GOOGLE_DRIVE_DATA"
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

def extract_folder_id_from_url(url):
    """从Google Drive文件夹URL中提取文件夹ID"""
    try:
        import re
        
        # 匹配各种可能的Google Drive文件夹URL格式
        patterns = [
            r'/folders/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)',
            r'folders/([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
        
    except Exception as e:
        print(f"提取文件夹ID时出错: {e}")
        return None

def test_drive_folder_access(folder_id):
    """测试是否可以访问Google Drive文件夹"""
    try:
        # 临时更新GoogleDriveShell配置以使用新的folder_id
        shell = GoogleDriveShell()
        if not shell.drive_service:
            return False
        
        # 直接测试API访问
        result = shell.drive_service.list_files(folder_id=folder_id, max_results=5)
        return result.get('success', False)
        
    except Exception as e:
        print(f"测试文件夹访问时出错: {e}")
        return False

def test_upload_workflow(drive_equivalent_path, drive_equivalent_folder_id, command_identifier=None):
    """测试上传工作流程"""
    try:
        print("🧪 测试上传工作流程...")
        
        # 创建测试文件
        import tempfile
        test_content = f"Upload test at {time.strftime('%Y-%m-%d %H:%M:%S')}\nDrive equivalent: {drive_equivalent_path}"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='upload_test_') as f:
            f.write(test_content)
            test_file_path = f.name
        
        test_filename = os.path.basename(test_file_path)
        
        try:
            # 临时更新shell配置
            shell = GoogleDriveShell()
            original_drive_equivalent = shell.DRIVE_EQUIVALENT
            original_drive_equivalent_folder_id = shell.DRIVE_EQUIVALENT_FOLDER_ID
            
            # 更新配置
            shell.DRIVE_EQUIVALENT = drive_equivalent_path
            shell.DRIVE_EQUIVALENT_FOLDER_ID = drive_equivalent_folder_id
            
            print(f"📤 上传测试文件: {test_filename}")
            
            # 使用shell的upload命令测试上传到.upload-test目录
            upload_result = shell.cmd_upload([test_file_path], ".upload-test")
            
            # 恢复原配置
            shell.DRIVE_EQUIVALENT = original_drive_equivalent
            shell.DRIVE_EQUIVALENT_FOLDER_ID = original_drive_equivalent_folder_id
            
            # 清理本地测试文件
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
            
            if upload_result.get("success", False):
                print("✅ 上传测试成功")
                return {
                    "success": True,
                    "message": "上传工作流程测试通过",
                    "test_file": test_filename,
                    "upload_details": upload_result
                }
            else:
                print(f"❌ 上传测试失败: {upload_result.get('error', '未知错误')}")
                return {
                    "success": False,
                    "error": f"上传测试失败: {upload_result.get('error', '未知错误')}",
                    "upload_details": upload_result
                }
                
        except Exception as e:
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)
            return {
                "success": False,
                "error": f"上传测试出错: {e}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"准备上传测试时出错: {e}"
        }

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
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(error_data["error"])
        return 1

def show_setup_step_1():
    """显示设置步骤1：创建Google Cloud项目"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.title("Google Drive API 设置 - 步骤 1/7")
        root.geometry("500x300")
        root.resizable(False, False)
        
        # 居中窗口
        root.eval('tk::PlaceWindow . center')
        
        # 设置窗口置顶
        root.attributes('-topmost', True)
        
        # 主框架
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            main_frame, 
            text="🚀 Google Drive API 设置向导", 
            font=("Arial", 16, "bold"),
            fg="#1a73e8"
        )
        title_label.pack(pady=(0, 20))
        
        # 步骤说明
        step_label = tk.Label(
            main_frame, 
            text="步骤 1: 创建 Google Cloud 项目", 
            font=("Arial", 14, "bold")
        )
        step_label.pack(pady=(0, 10))
        
        # 详细说明
        instruction_text = """即将打开 Google Cloud Console 创建项目页面。

请按以下步骤操作：
1. 点击下方 "Proceed" 按钮
2. 浏览器将自动打开 Google Cloud Console
3. 项目名称 "my-drive-remote-control" 已复制到剪贴板
4. 在页面中粘贴项目名称并点击 "CREATE"
5. 等待项目创建完成后，关闭此窗口继续下一步"""
        
        instruction_label = tk.Label(
            main_frame, 
            text=instruction_text,
            font=("Arial", 11),
            justify=tk.LEFT,
            wraplength=450
        )
        instruction_label.pack(pady=(0, 20))
        
        def on_proceed():
            # 复制项目名称到剪贴板
            project_name = "my-drive-remote-control"
            if copy_to_clipboard(project_name):
                messagebox.showinfo("✅ 成功", f"项目名称 '{project_name}' 已复制到剪贴板！")
            else:
                messagebox.showwarning("⚠️ 提醒", f"请手动复制项目名称: {project_name}")
            
            # 打开Google Cloud Console创建项目页面
            url = "https://console.cloud.google.com/projectcreate"
            webbrowser.open(url)
            
            # 显示下一步提示
            messagebox.showinfo(
                "下一步", 
                "项目创建完成后，请运行下一步：\nGOOGLE_DRIVE --console-setup-step2"
            )
            
            root.destroy()
        
        # Proceed按钮
        proceed_btn = tk.Button(
            main_frame, 
            text="Proceed", 
            command=on_proceed,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=30,
            pady=10,
            relief=tk.RAISED,
            bd=2
        )
        proceed_btn.pack(pady=20)
        
        # 取消按钮
        cancel_btn = tk.Button(
            main_frame, 
            text="取消", 
            command=root.destroy,
            font=("Arial", 10),
            padx=20,
            pady=5
        )
        cancel_btn.pack()
        
        root.mainloop()
        return True
        
    except ImportError:
        print("❌ tkinter不可用，请手动执行以下步骤：")
        print("1. 访问: https://console.cloud.google.com/projectcreate")
        print("2. 项目名称: my-drive-remote-control")
        print("3. 点击 CREATE")
        return False
    except Exception as e:
        print(f"❌ 显示设置窗口时出错: {e}")
        return False

def show_setup_step_2():
    """显示设置步骤2：启用Google Drive API"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.title("Google Drive API 设置 - 步骤 2/7")
        root.geometry("500x350")
        root.resizable(False, False)
        root.eval('tk::PlaceWindow . center')
        root.attributes('-topmost', True)
        
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            main_frame, 
            text="🔌 Google Drive API 设置向导", 
            font=("Arial", 16, "bold"),
            fg="#1a73e8"
        )
        title_label.pack(pady=(0, 20))
        
        # 步骤说明
        step_label = tk.Label(
            main_frame, 
            text="步骤 2: 启用 Google Drive API", 
            font=("Arial", 14, "bold")
        )
        step_label.pack(pady=(0, 10))
        
        # 详细说明
        instruction_text = """现在需要在您的项目中启用 Google Drive API。

请按以下步骤操作：
1. 点击下方 "Proceed" 按钮
2. 浏览器将打开 API Library 页面
3. 搜索 "Google Drive API"
4. 点击 "Google Drive API" 结果
5. 点击 "ENABLE" 按钮
6. 等待API启用完成后，关闭此窗口继续下一步

注意：确保您已选择正确的项目 (my-drive-remote-control)"""
        
        instruction_label = tk.Label(
            main_frame, 
            text=instruction_text,
            font=("Arial", 11),
            justify=tk.LEFT,
            wraplength=450
        )
        instruction_label.pack(pady=(0, 20))
        
        def on_proceed():
            # 打开API Library页面
            url = "https://console.cloud.google.com/apis/library"
            webbrowser.open(url)
            
            # 显示下一步提示
            messagebox.showinfo(
                "下一步", 
                "API启用完成后，请运行下一步：\nGOOGLE_DRIVE --console-setup-step3"
            )
            
            root.destroy()
        
        # Proceed按钮
        proceed_btn = tk.Button(
            main_frame, 
            text="Proceed", 
            command=on_proceed,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=30,
            pady=10,
            relief=tk.RAISED,
            bd=2
        )
        proceed_btn.pack(pady=20)
        
        # 取消按钮
        cancel_btn = tk.Button(
            main_frame, 
            text="取消", 
            command=root.destroy,
            font=("Arial", 10),
            padx=20,
            pady=5
        )
        cancel_btn.pack()
        
        root.mainloop()
        return True
        
    except ImportError:
        print("❌ tkinter不可用，请手动执行以下步骤：")
        print("1. 访问: https://console.cloud.google.com/apis/library")
        print("2. 搜索: Google Drive API")
        print("3. 点击 ENABLE")
        return False
    except Exception as e:
        print(f"❌ 显示设置窗口时出错: {e}")
        return False

def show_setup_step_3():
    """显示设置步骤3：创建OAuth凭据"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.title("Google Drive API 设置 - 步骤 3/7")
        root.geometry("500x400")
        root.resizable(False, False)
        root.eval('tk::PlaceWindow . center')
        root.attributes('-topmost', True)
        
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            main_frame, 
            text="🔐 Google Drive API 设置向导", 
            font=("Arial", 16, "bold"),
            fg="#1a73e8"
        )
        title_label.pack(pady=(0, 20))
        
        # 步骤说明
        step_label = tk.Label(
            main_frame, 
            text="步骤 3: 创建 OAuth 凭据", 
            font=("Arial", 14, "bold")
        )
        step_label.pack(pady=(0, 10))
        
        # 详细说明
        instruction_text = """现在需要创建OAuth凭据以访问Google Drive API。

请按以下步骤操作：
1. 点击下方 "Proceed" 按钮
2. 浏览器将打开凭据创建页面
3. 点击 "+ CREATE CREDENTIALS"
4. 选择 "OAuth client ID"
5. 如果提示配置同意屏幕，请先配置：
   - 选择 "External" 用户类型
   - 应用名称: Drive Remote Control
   - 用户支持邮箱: 您的邮箱
   - 开发者联系信息: 您的邮箱
6. 应用类型选择 "Desktop application"
7. 名称: Drive Remote Client
8. 点击 "CREATE"
9. 下载JSON文件并重命名为 credentials.json"""
        
        instruction_label = tk.Label(
            main_frame, 
            text=instruction_text,
            font=("Arial", 11),
            justify=tk.LEFT,
            wraplength=450
        )
        instruction_label.pack(pady=(0, 20))
        
        def on_proceed():
            # 打开凭据页面
            url = "https://console.cloud.google.com/apis/credentials"
            webbrowser.open(url)
            
            # 显示下一步提示
            messagebox.showinfo(
                "下一步", 
                "凭据创建并下载完成后，请运行下一步：\nGOOGLE_DRIVE --console-setup-step4"
            )
            
            root.destroy()
        
        # Proceed按钮
        proceed_btn = tk.Button(
            main_frame, 
            text="Proceed", 
            command=on_proceed,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=30,
            pady=10,
            relief=tk.RAISED,
            bd=2
        )
        proceed_btn.pack(pady=20)
        
        # 取消按钮
        cancel_btn = tk.Button(
            main_frame, 
            text="取消", 
            command=root.destroy,
            font=("Arial", 10),
            padx=20,
            pady=5
        )
        cancel_btn.pack()
        
        root.mainloop()
        return True
        
    except ImportError:
        print("❌ tkinter不可用，请手动执行以下步骤：")
        print("1. 访问: https://console.cloud.google.com/apis/credentials")
        print("2. 创建OAuth client ID凭据")
        print("3. 下载JSON文件")
        return False
    except Exception as e:
        print(f"❌ 显示设置窗口时出错: {e}")
        return False

def show_setup_step_4():
    """显示设置步骤4：安装依赖和保存API密钥"""
    try:
        import tkinter as tk
        from tkinter import messagebox, filedialog
        
        root = tk.Tk()
        root.title("Google Drive API 设置 - 步骤 4/7")
        root.geometry("500x450")
        root.resizable(False, False)
        root.eval('tk::PlaceWindow . center')
        root.attributes('-topmost', True)
        
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            main_frame, 
            text="📦 Google Drive API 设置向导", 
            font=("Arial", 16, "bold"),
            fg="#1a73e8"
        )
        title_label.pack(pady=(0, 20))
        
        # 步骤说明
        step_label = tk.Label(
            main_frame, 
            text="步骤 4: 安装依赖和配置凭据", 
            font=("Arial", 14, "bold")
        )
        step_label.pack(pady=(0, 10))
        
        # 详细说明
        instruction_text = """现在需要安装Python依赖包并配置API凭据。

请按以下步骤操作：
1. 点击 "安装依赖" 按钮安装必要的Python包
2. 点击 "选择凭据文件" 选择刚才下载的JSON文件
3. 系统将自动保存凭据路径到环境变量
4. 完成后点击 "继续下一步"

注意：请确保已下载credentials.json文件"""
        
        instruction_label = tk.Label(
            main_frame, 
            text=instruction_text,
            font=("Arial", 11),
            justify=tk.LEFT,
            wraplength=450
        )
        instruction_label.pack(pady=(0, 20))
        
        # 状态显示
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        deps_status = tk.Label(status_frame, text="📦 依赖包: 未安装", font=("Arial", 10))
        deps_status.pack(anchor=tk.W)
        
        creds_status = tk.Label(status_frame, text="🔐 凭据文件: 未选择", font=("Arial", 10))
        creds_status.pack(anchor=tk.W)
        
        def install_dependencies():
            try:
                import subprocess
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", 
                    "google-api-python-client", "google-auth-oauthlib", "google-auth-httplib2"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    deps_status.config(text="📦 依赖包: ✅ 已安装", fg="green")
                    messagebox.showinfo("成功", "依赖包安装完成！")
                else:
                    messagebox.showerror("错误", f"依赖包安装失败:\n{result.stderr}")
            except Exception as e:
                messagebox.showerror("错误", f"安装依赖时出错: {e}")
        
        def select_credentials_file():
            file_path = filedialog.askopenfilename(
                title="选择Google API凭据文件",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if file_path:
                # 使用EXPORT工具保存凭据路径
                try:
                    result = subprocess.run([
                        sys.executable, "EXPORT.py", 
                        "GOOGLE_DRIVE_CREDENTIALS", file_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        creds_status.config(text="🔐 凭据文件: ✅ 已保存", fg="green")
                        messagebox.showinfo("成功", f"凭据文件路径已保存到环境变量:\n{file_path}")
                    else:
                        messagebox.showerror("错误", f"保存凭据路径失败:\n{result.stderr}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存凭据时出错: {e}")
        
        def continue_next_step():
            # 检查状态
            if "✅" not in deps_status.cget("text"):
                messagebox.showwarning("提醒", "请先安装依赖包！")
                return
            if "✅" not in creds_status.cget("text"):
                messagebox.showwarning("提醒", "请先选择凭据文件！")
                return
            
            messagebox.showinfo(
                "下一步", 
                "配置完成！请运行下一步：\nGOOGLE_DRIVE --console-setup-step5"
            )
            root.destroy()
        
        # 按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 安装依赖按钮
        install_btn = tk.Button(
            button_frame, 
            text="安装依赖", 
            command=install_dependencies,
            font=("Arial", 10),
            bg="#2196F3",
            fg="white",
            padx=20,
            pady=5
        )
        install_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 选择凭据文件按钮
        select_btn = tk.Button(
            button_frame, 
            text="选择凭据文件", 
            command=select_credentials_file,
            font=("Arial", 10),
            bg="#FF9800",
            fg="white",
            padx=20,
            pady=5
        )
        select_btn.pack(side=tk.LEFT)
        
        # 继续按钮
        continue_btn = tk.Button(
            main_frame, 
            text="继续下一步", 
            command=continue_next_step,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=30,
            pady=10,
            relief=tk.RAISED,
            bd=2
        )
        continue_btn.pack(pady=20)
        
        # 取消按钮
        cancel_btn = tk.Button(
            main_frame, 
            text="取消", 
            command=root.destroy,
            font=("Arial", 10),
            padx=20,
            pady=5
        )
        cancel_btn.pack()
        
        root.mainloop()
        return True
        
    except ImportError:
        print("❌ tkinter不可用，请手动执行以下步骤：")
        print("1. pip install google-api-python-client google-auth-oauthlib")
        print("2. 将credentials.json文件路径保存到环境变量")
        return False
    except Exception as e:
        print(f"❌ 显示设置窗口时出错: {e}")
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
    help_text = """GOOGLE_DRIVE - Google Drive access tool with GDS (Google Drive Shell)

Usage: GOOGLE_DRIVE [url] [options]

Arguments:
  url                  Custom Google Drive URL (default: https://drive.google.com/)

Options:
  -my                  Open My Drive (https://drive.google.com/drive/u/0/my-drive)
  --console-setup      Start Google Drive API setup wizard with GUI assistance
  --shell [COMMAND]    Enter interactive shell mode or execute shell command (alias: GDS)
  --upload FILE [PATH] Upload a file to Google Drive via local sync (PATH defaults to REMOTE_ROOT)
  --create-remote-shell        Create a new remote shell session
  --list-remote-shell          List all remote shell sessions
  --checkout-remote-shell ID   Switch to a specific remote shell
  --terminate-remote-shell ID  Terminate a remote shell session
  --desktop --status           Check Google Drive Desktop application status
  --desktop --shutdown         Shutdown Google Drive Desktop application
  --desktop --launch           Launch Google Drive Desktop application
  --desktop --restart          Restart Google Drive Desktop application
  --desktop --set-local-sync-dir    Set local sync directory path
  --desktop --set-global-sync-dir   Set global sync directory (Drive folder)
  --help, -h           Show this help message

GDS (Google Drive Shell) Commands:
  When using --shell or in interactive mode, the following commands are available:

  Navigation:
    pwd                         - show current directory path
    ls [path] [--detailed] [-R] - list directory contents (recursive with -R)
    cd <path>                   - change directory (supports ~, .., relative paths)

  File Operations:
    mkdir [-p] <dir>            - create directory (recursive with -p)
    rm <file>                   - remove file
    rm -rf <dir>                - remove directory recursively
    mv <source> <dest>          - move/rename file or folder
    cat <file>                  - display file contents
    read <file> [start end]     - read file content with line numbers

  Upload/Download:
    upload <files...> [target]  - upload files to Google Drive
    upload-folder [--keep-zip] <folder> [target] - upload folder (zip->upload->unzip->cleanup)
    download [--force] <file> [path] - download file with caching

  Text Operations:
    echo <text>                 - display text
    echo <text> > <file>        - create file with text
    grep <pattern> <file>       - search for pattern in file
    edit [--preview] [--backup] <file> '<spec>' - edit file with multi-segment replacement

  Remote Execution:
    python <file>               - execute python file remotely
    python -c '<code>'          - execute python code remotely

  Search:
    find [path] -name [pattern] - search for files matching pattern

  Help:
    help                        - show available commands
    exit                        - exit shell mode

Advanced Features:
  - Multi-file operations: upload [[src1, dst1], [src2, dst2], ...]
  - Command chaining: cmd1 && cmd2 && cmd3
  - Path resolution: supports ~, .., relative and absolute paths
  - File caching: automatic download caching with cache management
  - Remote execution: run Python code on remote Google Drive environment

Examples:
  GOOGLE_DRIVE                                    # Open main Google Drive
  GOOGLE_DRIVE -my                                # Open My Drive folder
  GOOGLE_DRIVE https://drive.google.com/drive/my-drive  # Open specific folder
  GOOGLE_DRIVE --console-setup                    # Start API setup wizard
  GOOGLE_DRIVE --shell                            # Enter interactive shell mode
  GOOGLE_DRIVE --shell pwd                        # Show current path
  GOOGLE_DRIVE --shell ls                         # List directory contents
  GOOGLE_DRIVE --shell mkdir test                 # Create directory
  GOOGLE_DRIVE --shell cd hello                   # Change directory
  GOOGLE_DRIVE --shell rm file.txt               # Remove file
  GOOGLE_DRIVE --shell rm -rf folder              # Remove directory
  GOOGLE_DRIVE --shell upload file.txt           # Upload file to current directory
  GOOGLE_DRIVE --shell "ls && cd test && pwd"     # Chain commands
  GOOGLE_DRIVE --upload file.txt                 # Upload file to REMOTE_ROOT
  GOOGLE_DRIVE --upload file.txt subfolder       # Upload file to REMOTE_ROOT/subfolder
  GDS pwd                                         # Using alias (same as above)
  GOOGLE_DRIVE --create-remote-shell              # Create remote shell
  GOOGLE_DRIVE --list-remote-shell                # List remote shells
  GOOGLE_DRIVE --checkout-remote-shell abc123     # Switch to shell
  GOOGLE_DRIVE --terminate-remote-shell abc123    # Terminate shell
  GOOGLE_DRIVE --desktop --status                 # Check Desktop app status
  GOOGLE_DRIVE --desktop --shutdown               # Shutdown Desktop app
  GOOGLE_DRIVE --desktop --launch                 # Launch Desktop app
  GOOGLE_DRIVE --desktop --restart                # Restart Desktop app
  GOOGLE_DRIVE --desktop --set-local-sync-dir     # Set local sync directory
  GOOGLE_DRIVE --desktop --set-global-sync-dir    # Set global sync directory
  GOOGLE_DRIVE --setup-hf                         # Setup HuggingFace credentials on remote
  GOOGLE_DRIVE --test-hf                          # Test HuggingFace configuration on remote
  GOOGLE_DRIVE --help                             # Show help"""
    
    print(help_text)

def get_setup_config_file():
    """获取设置配置文件路径"""
    data_dir = Path(__file__).parent / "GOOGLE_DRIVE_DATA"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "setup_config.json"

def get_remote_shells_file():
    """获取远程shell配置文件路径"""
    data_dir = Path(__file__).parent / "GOOGLE_DRIVE_DATA"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "remote_shells.json"

def load_remote_shells():
    """加载远程shell配置"""
    shells_file = get_remote_shells_file()
    if shells_file.exists():
        try:
            with open(shells_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"shells": {}, "active_shell": None}

def save_remote_shells(shells_data):
    """保存远程shell配置"""
    shells_file = get_remote_shells_file()
    try:
        with open(shells_file, 'w', encoding='utf-8') as f:
            json.dump(shells_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ 保存远程shell配置失败: {e}")
        return False

def generate_shell_id():
    """生成shell标识符"""
    # 使用时间戳和随机UUID生成哈希
    timestamp = str(int(time.time()))
    random_uuid = str(uuid.uuid4())
    combined = f"{timestamp}_{random_uuid}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def create_remote_shell(name=None, folder_id=None, command_identifier=None):
    """创建远程shell"""
    try:
        # 生成shell ID
        shell_id = generate_shell_id()
        
        # 获取当前时间
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 如果没有提供名称，使用默认名称
        if not name:
            name = f"shell_{shell_id[:8]}"
        
        # 创建shell配置
        shell_config = {
            "id": shell_id,
            "name": name,
            "folder_id": folder_id or REMOTE_ROOT_FOLDER_ID,  # 默认使用REMOTE_ROOT作为根目录
            "current_path": "~",  # 当前逻辑路径，初始为~（指向REMOTE_ROOT）
            "current_folder_id": REMOTE_ROOT_FOLDER_ID,  # 当前所在的Google Drive文件夹ID
            "created_time": created_time,
            "last_accessed": created_time,
            "status": "active"
        }
        
        # 加载现有shells
        shells_data = load_remote_shells()
        
        # 添加新shell
        shells_data["shells"][shell_id] = shell_config
        
        # 如果这是第一个shell，设为活跃shell
        if not shells_data["active_shell"]:
            shells_data["active_shell"] = shell_id
        
        # 保存配置
        if save_remote_shells(shells_data):
            success_msg = f"✅ 远程shell创建成功"
            result_data = {
                "success": True,
                "message": success_msg,
                "shell_id": shell_id,
                "shell_name": name,
                "folder_id": folder_id,
                "created_time": created_time
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
                print(f"🆔 Shell ID: {shell_id}")
                print(f"📛 Shell名称: {name}")
                print(f"📁 文件夹ID: {folder_id or 'root'}")
                print(f"🕐 创建时间: {created_time}")
            return 0
        else:
            error_msg = "❌ 保存远程shell配置失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 创建远程shell时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def list_remote_shells(command_identifier=None):
    """列出所有远程shell"""
    try:
        shells_data = load_remote_shells()
        shells = shells_data["shells"]
        active_shell = shells_data["active_shell"]
        
        if not shells:
            no_shells_msg = "📭 没有找到远程shell"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": no_shells_msg,
                    "shells": [],
                    "count": 0,
                    "active_shell": None
                }, command_identifier)
            else:
                print(no_shells_msg)
            return 0
        
        if is_run_environment(command_identifier):
            write_to_json_output({
                "success": True,
                "message": f"找到 {len(shells)} 个远程shell",
                "shells": list(shells.values()),
                "count": len(shells),
                "active_shell": active_shell
            }, command_identifier)
        else:
            print(f"📋 远程Shell列表 (共{len(shells)}个):")
            print("-" * 60)
            for shell_id, shell_config in shells.items():
                is_active = "🟢" if shell_id == active_shell else "⚪"
                print(f"{is_active} {shell_config['name']}")
                print(f"   ID: {shell_id}")
                print(f"   文件夹: {shell_config['folder_id'] or 'root'}")
                print(f"   创建时间: {shell_config['created_time']}")
                print(f"   最后访问: {shell_config['last_accessed']}")
                print(f"   状态: {shell_config['status']}")
                print()
        
        return 0
        
    except Exception as e:
        error_msg = f"❌ 列出远程shell时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def checkout_remote_shell(shell_id, command_identifier=None):
    """切换到指定的远程shell"""
    try:
        from GOOGLE_DRIVE_PROJ.google_drive_shell import GoogleDriveShell
        
        shell = GoogleDriveShell()
        result = shell.checkout_shell(shell_id)
        
        if is_run_environment(command_identifier):
            write_to_json_output(result, command_identifier)
        else:
            if result["success"]:
                print(result["message"])
                if "current_path" in result:
                    print(f"📍 当前路径: {result['current_path']}")
            else:
                print(f"❌ {result['error']}")
        
        return 0 if result["success"] else 1
            
    except Exception as e:
        error_msg = f"❌ 切换远程shell时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def terminate_remote_shell(shell_id, command_identifier=None):
    """终止指定的远程shell"""
    try:
        shells_data = load_remote_shells()
        
        if shell_id not in shells_data["shells"]:
            error_msg = f"❌ 找不到Shell ID: {shell_id}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        shell_config = shells_data["shells"][shell_id]
        shell_name = shell_config['name']
        
        # 删除shell
        del shells_data["shells"][shell_id]
        
        # 如果删除的是活跃shell，需要选择新的活跃shell
        if shells_data["active_shell"] == shell_id:
            if shells_data["shells"]:
                # 选择最新的shell作为活跃shell
                latest_shell = max(shells_data["shells"].items(), 
                                 key=lambda x: x[1]["last_accessed"])
                shells_data["active_shell"] = latest_shell[0]
            else:
                shells_data["active_shell"] = None
        
        # 保存配置
        if save_remote_shells(shells_data):
            success_msg = f"✅ 远程shell '{shell_name}' 已终止"
            result_data = {
                "success": True,
                "message": success_msg,
                "terminated_shell_id": shell_id,
                "terminated_shell_name": shell_name,
                "new_active_shell": shells_data["active_shell"],
                "remaining_shells": len(shells_data["shells"])
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
                print(f"🗑️ 已删除Shell ID: {shell_id}")
                if shells_data["active_shell"]:
                    new_active_name = shells_data["shells"][shells_data["active_shell"]]["name"]
                    print(f"🔄 新的活跃shell: {new_active_name}")
                else:
                    print("📭 没有剩余的远程shell")
            return 0
        else:
            error_msg = "❌ 保存shell配置失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 终止远程shell时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def load_setup_config():
    """加载设置配置"""
    config_file = get_setup_config_file()
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_setup_config(config):
    """保存设置配置"""
    config_file = get_setup_config_file()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ 保存配置失败: {e}")
        return False

def get_project_id_from_user():
    """从用户获取项目ID"""
    config = load_setup_config()
    default_project_id = config.get("project_id", "")
    
    print("📋 请输入创建的项目ID：")
    print("   (项目创建完成后，您应该能在页面上看到类似 'console-control-466711' 的项目ID)")
    print()
    
    while True:
        if default_project_id:
            prompt = f"项目ID [默认: {default_project_id}]: "
        else:
            prompt = "项目ID: "
        
        try:
            user_input = get_multiline_input_safe(prompt, single_line=True)
            
            if not user_input and default_project_id:
                # 用户直接回车，使用默认值
                return default_project_id
            elif user_input:
                # 用户输入了新值
                return user_input
            else:
                # 用户直接回车但没有默认值
                print("❌ 项目ID不能为空，请重新输入")
                continue
                
        except KeyboardInterrupt:
            print("\n❌ 输入已取消")
            return None

def console_setup_step2(project_id):
    """步骤2：启用Google Drive API"""
    print("📋 步骤 2/7: 启用 Google Drive API")
    print("-" * 40)
    print()
    print("现在我们需要为您的项目启用 Google Drive API。")
    print()
    
    # 构建API启用URL
    api_url = f"https://console.cloud.google.com/apis/library/drive.googleapis.com?project={project_id}"
    
    try:
        webbrowser.open(api_url)
        print(f"🌐 已自动打开浏览器: Google Drive API 页面")
    except Exception as e:
        print(f"❌ 无法自动打开浏览器: {e}")
        print(f"请手动访问: {api_url}")
    print()
    
    print("请按照以下步骤操作：")
    print("1. 在打开的页面中，点击 '启用' (ENABLE) 按钮")
    print("2. 等待 API 启用完成")
    print()
    
    try:
        get_multiline_input_safe("✋ 完成上述步骤后，按 Enter 键继续...", single_line=True)
        print()
        print("✅ 第二步完成！")
        print("🎉 Google Drive API 已启用！")
        print()
        
        # 保存进度
        save_setup_config({"project_id": project_id, "step": 2})
        
        # 直接继续下一步
        console_setup_step3(project_id)
        
    except KeyboardInterrupt:
        print("\n❌ 设置已取消")
        return False
    
    return True

def console_setup_step3(project_id):
    """步骤3：创建服务账户"""
    print("📋 步骤 3/7: 创建服务账户")
    print("-" * 40)
    print()
    print("为了实现远程控制Google Drive，我们需要创建服务账户而非OAuth凭据。")
    print("服务账户可以在无用户交互的情况下访问API，适合自动化和远程控制。")
    print()
    
    # 构建服务账户创建URL
    service_account_url = f"https://console.cloud.google.com/iam-admin/serviceaccounts?project={project_id}"
    
    try:
        webbrowser.open(service_account_url)
        print(f"🌐 已自动打开浏览器: 服务账户管理页面")
    except Exception as e:
        print(f"❌ 无法自动打开浏览器: {e}")
        print(f"请手动访问: {service_account_url}")
    print()
    
    print("请按照以下步骤操作：")
    print("1. 点击 '+ 创建服务账户' (CREATE SERVICE ACCOUNT)")
    print("2. 服务账户名称: drive-remote-controller")
    print("3. 服务账户ID: drive-remote-controller (自动生成)")
    print("4. 描述: Google Drive remote control service account")
    print("5. 点击 '创建并继续'")
    print("6. 角色选择: 编辑者 (Editor) 或 所有者 (Owner)")
    print("7. 点击 '继续' 然后 '完成'")
    print()
    
    try:
        get_multiline_input_safe("✋ 完成上述步骤后，按 Enter 键继续...", single_line=True)
        print()
        print("✅ 第三步完成！")
        print("🎉 服务账户已创建！")
        print()
        
        # 保存进度
        save_setup_config({"project_id": project_id, "step": 3})
        
        # 直接继续下一步
        console_setup_step4(project_id)
        
    except KeyboardInterrupt:
        print("\n❌ 设置已取消")
        return False
    
    return True

def console_setup_step4(project_id):
    """步骤4：创建服务账户密钥"""
    print("📋 步骤 4/7: 创建服务账户密钥")
    print("-" * 40)
    print()
    print("现在我们需要为服务账户创建JSON密钥文件。")
    print("这个密钥文件将用于API认证。")
    print()
    
    # 构建服务账户管理URL
    service_account_url = f"https://console.cloud.google.com/iam-admin/serviceaccounts?project={project_id}"
    
    try:
        webbrowser.open(service_account_url)
        print(f"🌐 已自动打开浏览器: 服务账户管理页面")
    except Exception as e:
        print(f"❌ 无法自动打开浏览器: {e}")
        print(f"请手动访问: {service_account_url}")
    print()
    
    print("请按照以下步骤操作：")
    print("1. 找到刚创建的 'drive-remote-controller' 服务账户")
    print("2. 点击服务账户邮箱地址进入详情页")
    print("3. 切换到 '密钥' (KEYS) 标签页")
    print("4. 点击 '添加密钥' (ADD KEY) -> '创建新密钥' (Create new key)")
    print("5. 选择 'JSON' 格式")
    print("6. 点击 '创建' (CREATE)")
    print("7. JSON文件将自动下载，请保存到安全位置")
    print()
    
    try:
        get_multiline_input_safe("✋ 完成上述步骤后，按 Enter 键继续...", single_line=True)
        print()
        print("✅ 第四步完成！")
        print("🎉 服务账户密钥已创建！")
        print()
        
        # 保存进度
        save_setup_config({"project_id": project_id, "step": 4})
        
        # 直接继续下一步
        console_setup_step5(project_id)
        
    except KeyboardInterrupt:
        print("\n❌ 设置已取消")
        return False
    
    return True

def console_setup_step5(project_id):
    """步骤5：配置服务密钥和安装依赖"""
    print("📋 步骤 5/7: 配置服务密钥和安装依赖")
    print("-" * 40)
    print()
    print("现在我们需要配置刚才下载的服务账户密钥文件，并安装必要的依赖。")
    print()
    
    # 获取用户下载的密钥文件路径
    print("📂 请输入刚才下载的JSON密钥文件的完整路径：")
    print("   (例如: /Users/username/Downloads/console-control-466711-xxxxx.json)")
    print()
    
    try:
        while True:
            key_file_path = get_multiline_input_safe("密钥文件路径: ", single_line=True)
            
            if not key_file_path:
                print("❌ 路径不能为空，请重新输入")
                continue
            
            # 检查文件是否存在
            if not os.path.exists(key_file_path):
                print(f"❌ 文件不存在: {key_file_path}")
                print("请检查路径是否正确")
                continue
            
            # 检查是否为JSON文件
            if not key_file_path.lower().endswith('.json'):
                print("❌ 请确保选择的是JSON格式的密钥文件")
                continue
            
            # 尝试验证JSON文件内容
            try:
                with open(key_file_path, 'r') as f:
                    key_data = json.load(f)
                    if 'type' in key_data and key_data['type'] == 'service_account':
                        print(f"✅ 密钥文件验证成功: {key_file_path}")
                        break
                    else:
                        print("❌ 这不是有效的服务账户密钥文件")
                        continue
            except json.JSONDecodeError:
                print("❌ 无法解析JSON文件，请确保文件完整且格式正确")
                continue
            except Exception as e:
                print(f"❌ 读取文件时出错: {e}")
                continue
        
        print()
        print("📦 正在安装Google API客户端库...")
        
        # 安装依赖
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "google-api-python-client", "google-auth", "google-auth-oauthlib", "google-auth-httplib2"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 依赖安装成功！")
            else:
                print(f"❌ 依赖安装失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 安装依赖时出错: {e}")
            return False
        
        print()
        print("🔐 正在提取和配置服务账户信息...")
        
        # 读取并提取JSON密钥文件中的关键字段
        try:
            with open(key_file_path, 'r', encoding='utf-8') as f:
                key_data = json.load(f)
            
            # 提取需要的字段
            required_fields = {
                'GOOGLE_DRIVE_SERVICE_TYPE': key_data.get('type'),
                'GOOGLE_DRIVE_PROJECT_ID': key_data.get('project_id'),
                'GOOGLE_DRIVE_PRIVATE_KEY_ID': key_data.get('private_key_id'),
                'GOOGLE_DRIVE_PRIVATE_KEY': key_data.get('private_key'),
                'GOOGLE_DRIVE_CLIENT_EMAIL': key_data.get('client_email'),
                'GOOGLE_DRIVE_CLIENT_ID': key_data.get('client_id'),
                'GOOGLE_DRIVE_AUTH_URI': key_data.get('auth_uri'),
                'GOOGLE_DRIVE_TOKEN_URI': key_data.get('token_uri'),
                'GOOGLE_DRIVE_AUTH_PROVIDER_CERT_URL': key_data.get('auth_provider_x509_cert_url'),
                'GOOGLE_DRIVE_CLIENT_CERT_URL': key_data.get('client_x509_cert_url'),
                'GOOGLE_DRIVE_UNIVERSE_DOMAIN': key_data.get('universe_domain')
            }
            
            # 检查EXPORT工具是否存在
            export_tool_path = Path(__file__).parent / "EXPORT.py"
            if export_tool_path.exists():
                export_success_count = 0
                export_total_count = 0
                
                print("📤 正在导出服务账户字段到环境变量...")
                
                for env_var, value in required_fields.items():
                    if value is not None:
                        export_total_count += 1
                        try:
                            result = subprocess.run([
                                sys.executable, str(export_tool_path), 
                                env_var, str(value)
                            ], capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                export_success_count += 1
                                print(f"  ✅ {env_var}")
                            else:
                                print(f"  ❌ {env_var}: {result.stderr}")
                        except Exception as e:
                            print(f"  ❌ {env_var}: {e}")
                
                if export_success_count == export_total_count:
                    print(f"✅ 成功导出 {export_success_count}/{export_total_count} 个环境变量！")
                    print("🎉 现在即使删除JSON文件，系统也能正常工作！")
                else:
                    print(f"⚠️ 部分导出成功: {export_success_count}/{export_total_count}")
                    print("💾 建议保留JSON文件作为备份")
                    
                # 仍然保存文件路径作为备用
                result = subprocess.run([
                    sys.executable, str(export_tool_path), 
                    "GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY", key_file_path
                ], capture_output=True, text=True)
                    
            else:
                print(f"⚠️ EXPORT工具未找到，请手动设置环境变量:")
                print(f"export GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY='{key_file_path}'")
                
        except Exception as e:
            print(f"⚠️ 读取密钥文件时出错: {e}")
            print(f"回退到文件路径模式: export GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY='{key_file_path}'")
        
        print()
        print("✅ 第五步完成！")
        print("🎉 服务密钥配置完成！")
        print()
        
        # 保存进度和密钥路径
        save_setup_config({
            "project_id": project_id, 
            "step": 5,
            "service_account_key": key_file_path
        })
        
        # 直接继续下一步
        console_setup_step6(project_id)
        
    except KeyboardInterrupt:
        print("\n❌ 设置已取消")
        return False
    
    return True

def console_setup_step6(project_id):
    """步骤6：创建API服务和测试连接"""
    print("📋 步骤 6/7: 创建API服务和测试连接")
    print("-" * 40)
    print()
    print("现在我们将创建Google Drive API服务类，并测试连接。")
    print()
    
    # 创建API服务文件
    api_service_code = '''#!/usr/bin/env python3
"""
Google Drive API Service
远程控制Google Drive的API服务类
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io

class GoogleDriveService:
    """Google Drive API服务类"""
    
    def __init__(self, service_account_key_path=None):
        """
        初始化Google Drive服务
        
        Args:
            service_account_key_path (str): 服务账户密钥文件路径
        """
        self.service = None
        self.credentials = None
        
        # 获取密钥文件路径
        if service_account_key_path:
            self.key_path = service_account_key_path
        else:
            self.key_path = os.environ.get('GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY')
        
        if not self.key_path:
            raise ValueError("未找到服务账户密钥文件路径")
        
        if not os.path.exists(self.key_path):
            raise FileNotFoundError(f"服务账户密钥文件不存在: {self.key_path}")
        
        self._authenticate()
    
    def _authenticate(self):
        """认证并创建服务对象"""
        try:
            # 定义需要的权限范围
            SCOPES = [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
            
            # 从服务账户密钥文件创建凭据
            self.credentials = service_account.Credentials.from_service_account_file(
                self.key_path, scopes=SCOPES
            )
            
            # 创建Drive API服务对象
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            raise Exception(f"Google Drive API认证失败: {e}")
    
    def test_connection(self):
        """测试API连接"""
        try:
            # 获取用户信息
            about = self.service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            
            return {
                "success": True,
                "message": "Google Drive API连接成功",
                "user_email": user_info.get('emailAddress', 'Unknown'),
                "user_name": user_info.get('displayName', 'Unknown')
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"连接测试失败: {e}"
            }
    
    def list_files(self, folder_id=None, max_results=10):
        """
        列出文件
        
        Args:
            folder_id (str): 文件夹ID，None表示根目录
            max_results (int): 最大结果数
            
        Returns:
            dict: 文件列表
        """
        try:
            query = ""
            if folder_id:
                query = f"'{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)"
            ).execute()
            
            items = results.get('files', [])
            
            return {
                "success": True,
                "files": items,
                "count": len(items)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"列出文件失败: {e}"
            }
    
    def create_folder(self, name, parent_id=None):
        """
        创建文件夹
        
        Args:
            name (str): 文件夹名称
            parent_id (str): 父文件夹ID，None表示根目录
            
        Returns:
            dict: 创建结果
        """
        try:
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name'
            ).execute()
            
            return {
                "success": True,
                "folder_id": folder.get('id'),
                "folder_name": folder.get('name')
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"创建文件夹失败: {e}"
            }
    
    def upload_file(self, local_file_path, drive_folder_id=None, drive_filename=None):
        """
        上传文件到Google Drive
        
        Args:
            local_file_path (str): 本地文件路径
            drive_folder_id (str): Drive文件夹ID，None表示根目录
            drive_filename (str): Drive中的文件名，None使用本地文件名
            
        Returns:
            dict: 上传结果
        """
        try:
            if not os.path.exists(local_file_path):
                return {
                    "success": False,
                    "error": f"本地文件不存在: {local_file_path}"
                }
            
            # 确定文件名
            if not drive_filename:
                drive_filename = os.path.basename(local_file_path)
            
            # 文件元数据
            file_metadata = {'name': drive_filename}
            if drive_folder_id:
                file_metadata['parents'] = [drive_folder_id]
            
            # 上传文件
            media = MediaFileUpload(local_file_path)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size'
            ).execute()
            
            return {
                "success": True,
                "file_id": file.get('id'),
                "file_name": file.get('name'),
                "file_size": file.get('size')
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"上传文件失败: {e}"
            }
    
    def download_file(self, file_id, local_save_path):
        """
        从Google Drive下载文件
        
        Args:
            file_id (str): Drive文件ID
            local_save_path (str): 本地保存路径
            
        Returns:
            dict: 下载结果
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # 保存文件
            with open(local_save_path, 'wb') as f:
                f.write(fh.getvalue())
            
            return {
                "success": True,
                "local_path": local_save_path,
                "message": "文件下载成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"{e}"
            }
    
    def delete_file(self, file_id):
        """
        删除文件
        
        Args:
            file_id (str): 文件ID
            
        Returns:
            dict: 删除结果
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            return {
                "success": True,
                "message": "文件删除成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"删除文件失败: {e}"
            }
    
    def share_file(self, file_id, email_address, role='reader'):
        """
        分享文件给指定邮箱
        
        Args:
            file_id (str): 文件ID
            email_address (str): 邮箱地址
            role (str): 权限角色 (reader, writer, owner)
            
        Returns:
            dict: 分享结果
        """
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email_address
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=True
            ).execute()
            
            return {
                "success": True,
                "message": f"文件已分享给 {email_address}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"分享文件失败: {e}"
            }

# 测试函数
def test_drive_service():
    """测试Google Drive服务"""
    try:
        print("🧪 正在测试Google Drive API连接...")
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 测试连接
        result = drive_service.test_connection()
        
        if result['success']:
            print("✅ API连接测试成功！")
            print(f"📧 服务账户邮箱: {result.get('user_email', 'Unknown')}")
            print(f"👤 用户名: {result.get('user_name', 'Unknown')}")
            
            # 测试列出文件
            print("\\n📂 正在测试文件列表功能...")
            files_result = drive_service.list_files(max_results=5)
            
            if files_result['success']:
                print(f"✅ 文件列表获取成功！找到 {files_result['count']} 个文件")
                for file in files_result['files'][:3]:  # 显示前3个文件
                    print(f"   📄 {file['name']} ({file['mimeType']})")
            else:
                print(f"❌ 文件列表获取失败: {files_result['error']}")
            
            return True
        else:
            print(f"❌ API连接测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    test_drive_service()
'''
    
    # 创建API服务文件
    api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
    
    # 确保目录存在
    api_service_path.parent.mkdir(exist_ok=True)
    
    try:
        with open(api_service_path, 'w', encoding='utf-8') as f:
            f.write(api_service_code)
        print(f"✅ API服务文件已创建: {api_service_path}")
    except Exception as e:
        print(f"❌ 创建API服务文件失败: {e}")
        return False
    
    print()
    print("🧪 正在测试API连接...")
    
    # 运行测试
    try:
        result = subprocess.run([
            sys.executable, str(api_service_path)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ API测试成功！")
            print(result.stdout)
        else:
            print("❌ API测试失败:")
            print(result.stderr)
            print("可能的原因:")
            print("1. 服务账户密钥文件路径不正确")
            print("2. 服务账户权限不足")
            print("3. API未正确启用")
            return False
    except subprocess.TimeoutExpired:
        print("⚠️ API测试超时，可能需要更多时间进行认证")
    except Exception as e:
        print(f"❌ 运行API测试时出错: {e}")
        return False
    
    print()
    print("✅ 第六步完成！")
    print("🎉 API服务创建完成！")
    print()
    
    # 保存进度
    save_setup_config({
        "project_id": project_id, 
        "step": 6,
        "api_service_path": str(api_service_path)
    })
    
    # 直接继续下一步
    console_setup_step7(project_id)
    
    return True

def console_setup_step7(project_id):
    """步骤8：完成设置和提供使用指南"""
    print("📋 步骤 8/7: 完成设置")
    print("-" * 40)
    print()
    print("🎉 恭喜！Google Drive远程控制API设置已完成！")
    print()
    
    # 获取配置信息
    config = load_setup_config()
    
    print("📋 设置摘要:")
    print(f"  🏗️  项目ID: {project_id}")
    print(f"  🔐 服务账户密钥: {config.get('service_account_key', '未配置')}")
    print(f"  🔧 API服务文件: GOOGLE_DRIVE_PROJ/google_drive_api.py")
    print(f"  🔬 Colab集成文件: GOOGLE_DRIVE_PROJ/google_drive_colab.py")
    print()
    
    print("🚀 使用方法:")
    print()
    print("1. 本地使用:")
    print("   python GOOGLE_DRIVE_PROJ/google_drive_api.py  # 测试连接")
    print("   # 或在Python中:")
    print("   from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService")
    print("   drive = GoogleDriveService()")
    print("   drive.list_files()")
    print()
    
    print("2. Google Colab使用:")
    print("   a. 将服务账户密钥文件上传到Google Drive")
    print("   b. 在Colab中复制运行GOOGLE_DRIVE_PROJ/google_drive_colab.py中的代码")
    print("   c. 使用drive_service对象进行操作")
    print()
    
    print("3. 主要功能:")
    print("   📂 列出文件: list_files()")
    print("   📁 创建文件夹: create_folder()")
    print("   ⬆️  上传文件: upload_file()")
    print("   ⬇️  下载文件: download_file()")
    print("   🗑️  删除文件: delete_file()")
    print("   📤 分享文件: share_file()")
    print()
    
    print("🔧 GOOGLE_DRIVE工具更新:")
    print("   GOOGLE_DRIVE --api-test        # 测试API连接")
    print("   GOOGLE_DRIVE --api-list        # 列出Drive文件")
    print("   GOOGLE_DRIVE --api-upload FILE # 上传文件")
    print()
    
    print("💡 提示:")
    print("- 服务账户只能访问与其共享的文件和文件夹")
    print("- 如需访问个人Drive文件，请在Drive中将文件夹分享给服务账户邮箱")
    print("- 在Colab中可以结合Drive挂载和API服务实现完整的远程控制")
    print()
    
    # 保存最终配置
    final_config = {
        "project_id": project_id,
        "step": 8,
        "setup_completed": True,
        "completion_time": str(Path(__file__).stat().st_mtime)
    }
    final_config.update(config)
    save_setup_config(final_config)
    
    print("✅ 第八步完成！")
    print("🎊 Google Drive远程控制API设置完成！")
    print()
    print("现在您可以使用API进行远程Drive操作了！")
    
    return True

def get_folder_path_from_api(folder_id):
    """使用API获取文件夹的完整路径"""
    try:
        # 动态导入API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            return None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 构建路径
        path_parts = []
        current_id = folder_id
        
        while current_id and current_id != HOME_FOLDER_ID:
            try:
                # 获取文件夹信息
                folder_info = drive_service.service.files().get(
                    fileId=current_id,
                    fields="name, parents"
                ).execute()
                
                folder_name = folder_info.get('name')
                parents = folder_info.get('parents', [])
                
                if folder_name:
                    path_parts.insert(0, folder_name)
                
                # 移动到父文件夹
                if parents:
                    current_id = parents[0]
                else:
                    break
                    
            except Exception as e:
                print(f"⚠️ 获取文件夹信息时出错: {e}")
                break
        
        if path_parts:
            # 移除"My Drive"如果它是第一个部分
            if path_parts and path_parts[0] == "My Drive":
                path_parts = path_parts[1:]
            
            if path_parts:
                return "~/" + "/".join(path_parts)
            else:
                return "~"
        else:
            return "~"
            
    except Exception as e:
        print(f"❌ 获取文件夹路径时出错: {e}")
        return None

def url_to_logical_path(url):
    """将Google Drive URL转换为逻辑路径"""
    try:
        # 如果是My Drive的URL，直接返回~
        if "my-drive" in url.lower() or url == HOME_URL:
            return "~"
        
        # 提取文件夹ID
        folder_id = extract_folder_id_from_url(url)
        if not folder_id:
            return None
        
        # 使用API获取路径
        return get_folder_path_from_api(folder_id)
        
    except Exception as e:
        print(f"❌ URL转换为路径时出错: {e}")
        return None

def shell_ls(path=None, command_identifier=None):
    """列出指定路径或当前路径的文件和文件夹"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell，请先创建或切换到一个shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 确定要列出的文件夹ID
        if path is None or path == "." or path == "~":
            # 列出当前目录或根目录
            target_folder_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
            display_path = current_shell.get("current_path", "~")
        else:
            # 实现基本路径解析
            try:
                # 使用shell的路径解析功能
                target_folder_id, display_path = shell.resolve_path(path)
                if not target_folder_id:
                    error_msg = f"❌ 路径不存在: {path}"
                    if is_run_environment(command_identifier):
                        write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                    else:
                        print(error_msg)
                    return 1
            except Exception as e:
                error_msg = f"❌ 路径解析失败: {path} ({e})"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        
        # 使用API列出文件
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 列出文件
        result = drive_service.list_files(folder_id=target_folder_id, max_results=50)
        
        if result['success']:
            files = result['files']
            
            if is_run_environment(command_identifier):
                # RUN环境下返回JSON
                write_to_json_output({
                    "success": True,
                    "path": display_path,
                    "folder_id": target_folder_id,
                    "files": files,
                    "count": len(files)
                }, command_identifier)
            else:
                # 直接执行时显示bash风格的列表
                if not files:
                    # 目录为空时不显示任何内容，就像bash一样
                    pass
                else:
                    # 按名称排序，文件夹优先
                    folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                    other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                       key=lambda x: x['name'].lower())
                    
                    # 合并列表，文件夹在前
                    all_items = folders + other_files
                    
                    # 简单的列表格式，类似bash ls
                    for item in all_items:
                        name = item['name']
                        if item['mimeType'] == 'application/vnd.google-apps.folder':
                            # 文件夹用不同颜色或标记（这里用简单文本）
                            print(f"{name}/")
                        else:
                            print(name)
            
            return 0
        else:
            error_msg = f"❌ 列出文件失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行ls命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def resolve_path(path, current_shell):
    """解析路径，返回对应的Google Drive文件夹ID和逻辑路径"""
    try:
        if not current_shell:
            return None, None
        
        current_path = current_shell.get("current_path", "~")
        current_folder_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
        
        # 处理绝对路径
        if path.startswith("~"):
            if path == "~":
                return REMOTE_ROOT_FOLDER_ID, "~"
            elif path.startswith("~/"):
                # 从根目录开始解析
                relative_path = path[2:]  # 去掉 ~/
                return resolve_relative_path(relative_path, REMOTE_ROOT_FOLDER_ID, "~")
            else:
                return None, None
        
        # 处理相对路径
        elif path.startswith("./"):
            # 当前目录的相对路径
            relative_path = path[2:]
            return resolve_relative_path(relative_path, current_folder_id, current_path)
        
        elif path == ".":
            # 当前目录
            return current_folder_id, current_path
        
        elif path == "..":
            # 父目录
            return resolve_parent_directory(current_folder_id, current_path)
        
        elif path.startswith("../"):
            # 父目录的相对路径
            parent_id, parent_path = resolve_parent_directory(current_folder_id, current_path)
            if parent_id:
                relative_path = path[3:]  # 去掉 ../
                return resolve_relative_path(relative_path, parent_id, parent_path)
            return None, None
        
        else:
            # 相对于当前目录的路径
            return resolve_relative_path(path, current_folder_id, current_path)
            
    except Exception as e:
        print(f"❌ 解析路径时出错: {e}")
        return None, None

def resolve_relative_path(relative_path, base_folder_id, base_path):
    """解析相对路径"""
    try:
        if not relative_path:
            return base_folder_id, base_path
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            return None, None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 分割路径
        path_parts = relative_path.split("/")
        current_id = base_folder_id
        current_logical_path = base_path
        
        for part in path_parts:
            if not part:  # 跳过空部分
                continue
            
            # 在当前目录中查找这个名称的文件夹
            files_result = drive_service.list_files(folder_id=current_id, max_results=100)
            if not files_result['success']:
                return None, None
            
            # 查找匹配的文件夹
            found_folder = None
            for file in files_result['files']:
                if file['name'] == part and file['mimeType'] == 'application/vnd.google-apps.folder':
                    found_folder = file
                    break
            
            if not found_folder:
                return None, None  # 路径不存在
            
            # 更新当前位置
            current_id = found_folder['id']
            if current_logical_path == "~":
                current_logical_path = f"~/{part}"
            else:
                current_logical_path = f"{current_logical_path}/{part}"
        
        return current_id, current_logical_path
        
    except Exception as e:
        print(f"❌ 解析相对路径时出错: {e}")
        return None, None

def resolve_parent_directory(folder_id, current_path):
    """解析父目录"""
    try:
        if current_path == "~":
            return None, None  # 已经在根目录
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            return None, None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 获取当前文件夹的父目录
        folder_info = drive_service.service.files().get(
            fileId=folder_id,
            fields="parents"
        ).execute()
        
        parents = folder_info.get('parents', [])
        if not parents:
            return None, None
        
        parent_id = parents[0]
        
        # 计算父目录的逻辑路径
        if current_path.count('/') == 1:  # ~/folder -> ~
            parent_path = "~"
        else:
            parent_path = '/'.join(current_path.split('/')[:-1])
        
        return parent_id, parent_path
        
    except Exception as e:
        print(f"❌ 解析父目录时出错: {e}")
        return None, None

def shell_mkdir(path, command_identifier=None):
    """创建目录"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell，请先创建或切换到一个shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        if not path:
            error_msg = "❌ 请指定要创建的目录名称"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 解析路径
        if "/" in path:
            # 复杂路径，需要解析父目录
            parent_path = "/".join(path.split("/")[:-1])
            dir_name = path.split("/")[-1]
            
            parent_id, _ = resolve_path(parent_path, current_shell)
            if not parent_id:
                error_msg = f"❌ 父目录不存在: {parent_path}"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        else:
            # 简单目录名，在当前目录创建
            parent_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
            dir_name = path
        
        # 使用API创建目录
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        result = drive_service.create_folder(dir_name, parent_id)
        
        if result['success']:
            success_msg = f"✅ 目录创建成功: {dir_name}"
            result_data = {
                "success": True,
                "message": success_msg,
                "folder_name": result['folder_name'],
                "folder_id": result['folder_id']
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
            return 0
        else:
            error_msg = f"❌ 创建目录失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行mkdir命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def shell_cd(path, command_identifier=None):
    """切换目录"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell，请先创建或切换到一个shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        if not path:
            # cd 不带参数，回到根目录
            path = "~"
        
        # 解析目标路径
        target_id, target_path = resolve_path(path, current_shell)
        
        if not target_id:
            error_msg = f"❌ 目录不存在: {path}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 更新shell的当前位置
        shells_data = load_remote_shells()
        shell_id = current_shell['id']
        
        shells_data["shells"][shell_id]["current_path"] = target_path
        shells_data["shells"][shell_id]["current_folder_id"] = target_id
        shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if save_remote_shells(shells_data):
            success_msg = f"✅ 已切换到目录: {target_path}"
            result_data = {
                "success": True,
                "message": success_msg,
                "new_path": target_path,
                "folder_id": target_id
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
            return 0
        else:
            error_msg = "❌ 保存shell状态失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行cd命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def shell_rm(path, recursive=False, command_identifier=None):
    """删除文件或目录"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell，请先创建或切换到一个shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        if not path:
            error_msg = "❌ 请指定要删除的文件或目录"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 解析路径以找到要删除的文件/目录
        if "/" in path:
            # 复杂路径
            parent_path = "/".join(path.split("/")[:-1])
            item_name = path.split("/")[-1]
            
            parent_id, _ = resolve_path(parent_path, current_shell)
            if not parent_id:
                error_msg = f"❌ 父目录不存在: {parent_path}"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        else:
            # 简单名称，在当前目录查找
            parent_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
            item_name = path
        
        # 使用API查找要删除的项目
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 列出父目录内容查找目标项目
        files_result = drive_service.list_files(folder_id=parent_id, max_results=100)
        if not files_result['success']:
            error_msg = f"❌ 无法访问目录: {files_result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 查找要删除的项目
        target_item = None
        for file in files_result['files']:
            if file['name'] == item_name:
                target_item = file
                break
        
        if not target_item:
            error_msg = f"❌ 文件或目录不存在: {item_name}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 检查是否为目录且没有使用递归标志
        is_folder = target_item['mimeType'] == 'application/vnd.google-apps.folder'
        if is_folder and not recursive:
            error_msg = f"❌ 无法删除目录 '{item_name}': 请使用 rm -rf"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 删除项目
        result = drive_service.delete_file(target_item['id'])
        
        if result['success']:
            item_type = "目录" if is_folder else "文件"
            success_msg = f"✅ {item_type}删除成功: {item_name}"
            result_data = {
                "success": True,
                "message": success_msg,
                "deleted_item": item_name,
                "item_type": item_type,
                "item_id": target_item['id']
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
            return 0
        else:
            error_msg = f"❌ 删除失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行rm命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def open_dir(path, command_identifier=None):
    """打开目录 - 相当于创建shell + cd"""
    try:
        current_shell = get_current_shell()
        
        # 如果已经有活跃shell，直接cd
        if current_shell:
            return shell_cd(path, command_identifier)
        
        # 没有活跃shell，先创建一个
        import time
        shell_id = generate_shell_id()
        shell_name = f"shell_{shell_id[:8]}"
        created_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 解析目标路径
        temp_shell = {
            "current_path": "~",
            "current_folder_id": REMOTE_ROOT_FOLDER_ID
        }
        
        target_id, target_path = resolve_path(path, temp_shell)
        if not target_id:
            error_msg = f"❌ 目录不存在: {path}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 创建shell配置，直接定位到目标目录
        shell_config = {
            "id": shell_id,
            "name": shell_name,
            "folder_id": REMOTE_ROOT_FOLDER_ID,  # 根目录ID
            "current_path": target_path,  # 当前逻辑路径设为目标路径
            "current_folder_id": target_id,  # 当前所在的Google Drive文件夹ID
            "created_time": created_time,
            "last_accessed": created_time,
            "status": "active"
        }
        
        # 保存shell
        shells_data = load_remote_shells()
        shells_data["shells"][shell_id] = shell_config
        shells_data["active_shell"] = shell_id
        
        if save_remote_shells(shells_data):
            success_msg = f"✅ 已创建shell并打开目录: {target_path}"
            result_data = {
                "success": True,
                "message": success_msg,
                "shell_id": shell_id,
                "shell_name": shell_name,
                "path": target_path,
                "folder_id": target_id
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
                print(f"🆔 Shell ID: {shell_id}")
            return 0
        else:
            error_msg = "❌ 保存shell配置失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行open-dir命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def exit_remote_shell(command_identifier=None):
    """退出当前的远程shell"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 清除活跃shell
        shells_data = load_remote_shells()
        shells_data["active_shell"] = None
        
        if save_remote_shells(shells_data):
            success_msg = f"✅ 已退出远程shell: {current_shell['name']}"
            result_data = {
                "success": True,
                "message": success_msg,
                "exited_shell": current_shell['name'],
                "shell_id": current_shell['id']
            }
            
            if is_run_environment(command_identifier):
                write_to_json_output(result_data, command_identifier)
            else:
                print(success_msg)
            return 0
        else:
            error_msg = "❌ 保存shell状态失败"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行exit-remote-shell命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def get_current_shell():
    """获取当前活跃的shell"""
    shells_data = load_remote_shells()
    active_shell_id = shells_data.get("active_shell")
    
    if not active_shell_id or active_shell_id not in shells_data["shells"]:
        return None
    
    return shells_data["shells"][active_shell_id]

def shell_pwd(command_identifier=None):
    """显示当前远程逻辑地址"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "❌ 没有活跃的远程shell，请先创建或切换到一个shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        current_path = current_shell.get("current_path", "~")
        
        result_data = {
            "success": True,
            "current_path": current_path,
            "shell_id": current_shell["id"],
            "shell_name": current_shell["name"],
            "home_url": HOME_URL
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(result_data, command_identifier)
        else:
            print(f"📍 当前路径: {current_path}")
            print(f"🏠 Home URL: {HOME_URL}")
            print(f"🆔 Shell: {current_shell['name']} ({current_shell['id']})")
        
        return 0
        
    except Exception as e:
        error_msg = f"❌ 获取当前路径时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def enter_shell_mode(command_identifier=None):
    """进入交互式shell模式"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            # 如果没有活跃shell，创建一个默认的
            print("🚀 没有活跃的远程shell，正在创建默认shell...")
            create_result = create_remote_shell("default_shell", None, None)
            if create_result != 0:
                error_msg = "❌ 无法创建默认shell"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
            current_shell = get_current_shell()
        
        if is_run_environment(command_identifier):
            # 在RUN环境下，返回shell信息
            result_data = {
                "success": True,
                "message": "Shell模式已启动",
                "shell_info": current_shell,
                "current_path": current_shell.get("current_path", "~"),
                "available_commands": ["pwd", "ls", "mkdir", "cd", "rm", "help", "exit"]
            }
            write_to_json_output(result_data, command_identifier)
            return 0
        else:
            # 在直接执行模式下，启动交互式shell
            print(f"🌟 Google Drive Shell (GDS) - {current_shell['name']}")
            print(f"📍 当前路径: {current_shell.get('current_path', '~')}")
            print("💡 输入 'help' 查看可用命令，输入 'exit' 退出")
            print()
            
            while True:
                try:
                    # 显示提示符
                    current_path = current_shell.get("current_path", "~")
                    prompt = f"GDS:{current_path}$ "
                    
                    user_input = get_multiline_input_safe(prompt, single_line=True)
                    
                    if not user_input:
                        continue
                    
                    # 解析命令
                    parts = user_input.split()
                    cmd = parts[0].lower()
                    
                    if cmd == "exit":
                        print("👋 退出Google Drive Shell")
                        break
                    elif cmd == "pwd":
                        shell_pwd()
                    elif cmd == "ls":
                        shell_ls()
                    elif cmd.startswith("mkdir "):
                        path = cmd[6:].strip()
                        shell_mkdir(path)
                    elif cmd.startswith("cd "):
                        path = cmd[3:].strip()
                        shell_cd(path)
                    elif cmd == "cd":
                        shell_cd("~")
                    elif cmd.startswith("rm -rf "):
                        path = cmd[7:].strip()
                        shell_rm(path, True)
                    elif cmd.startswith("rm "):
                        path = cmd[3:].strip()
                        shell_rm(path, False)
                    elif cmd == "help":
                        print("📋 可用命令:")
                        print("  pwd           - 显示当前远程逻辑地址")
                        print("  ls            - 列出当前目录内容")
                        print("  mkdir <dir>   - 创建目录")
                        print("  cd <path>     - 切换目录")
                        print("  rm <file>     - 删除文件")
                        print("  rm -rf <dir>  - 递归删除目录")
                        print("  help          - 显示帮助信息")
                        print("  exit          - 退出shell模式")
                        print()
                    elif cmd == "read":
                        if not args:
                            result = {"success": False, "error": "用法: read <filename> [start end] 或 read <filename> [[start1, end1], [start2, end2], ...]"}
                        else:
                            filename = args[0]
                            range_args = args[1:] if len(args) > 1 else []
                            result = shell.cmd_read(filename, *range_args)
                    elif cmd == "find":
                        if not args:
                            result = {"success": False, "error": "用法: find [path] -name [pattern] 或 find [path] -type [f|d] -name [pattern]"}
                        else:
                            result = shell.cmd_find(*args)
                    else:
                        print(f"❌ 未知命令: {cmd}")
                        print("💡 输入 'help' 查看可用命令")
                        print()
                    
                except KeyboardInterrupt:
                    print("\n👋 退出Google Drive Shell")
                    break
                except EOFError:
                    print("\n👋 退出Google Drive Shell")
                    break
            
            return 0
        
    except Exception as e:
        error_msg = f"❌ 启动shell模式时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def console_setup_interactive():
    """终端交互式 Google Drive API 设置向导"""
    print("=" * 60)
    print("🚀 Google Drive API 设置向导 (终端交互版)")
    print("=" * 60)
    print()
    print("这个向导将指导您完成 Google Drive API 的完整配置过程。")
    print("我们将分步骤进行，每一步都会有详细的说明。")
    print()
    
    # 步骤 1: 创建 Google Cloud 项目
    print("📋 步骤 1/7: 创建 Google Cloud 项目")
    print("-" * 40)
    print()
    print("首先，我们需要在 Google Cloud Console 中创建一个新项目。")
    print()
    
    # 复制项目名称到剪贴板
    project_name = "console-control"
    if copy_to_clipboard(project_name):
        print(f"✅ 项目名称 '{project_name}' 已复制到剪贴板")
    else:
        print(f"📋 请手动复制项目名称: {project_name}")
    print()
    
    # 打开浏览器
    url = "https://console.cloud.google.com/projectcreate"
    try:
        webbrowser.open(url)
        print(f"🌐 已自动打开浏览器: {url}")
    except Exception as e:
        print(f"❌ 无法自动打开浏览器: {e}")
        print(f"请手动访问: {url}")
    print()
    
    print("请按照以下步骤操作：")
    print("1. 在打开的页面中，项目名称字段粘贴 'console-control'")
    print("2. 点击 '建立' (CREATE) 按钮")
    print("3. 等待项目创建完成")
    print()
    
    # 等待用户确认
    try:
        get_multiline_input_safe("✋ 完成上述步骤后，按 Enter 键继续...", single_line=True)
        print()
        print("✅ 第一步完成！")
        print()
        
        # 收集项目ID
        project_id = get_project_id_from_user()
        if not project_id:
            print("❌ 未获取到项目ID，设置已取消")
            return False
        
        # 保存项目ID到配置文件
        save_setup_config({"project_id": project_id, "step": 1})
        
        print()
        print("🎉 Google Cloud 项目创建成功！")
        print(f"📋 项目ID: {project_id}")
        print()
        
        # 直接继续下一步
        console_setup_step2(project_id)
        
    except KeyboardInterrupt:
        print("\n❌ 设置已取消")
        return False
    
    return True

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
    
    # 处理shell命令（优先处理）
    if len(args) > 0 and args[0] == '--shell':
        if len(args) > 1:
            # 检查是否有--return标志
            return_command_only = False
            shell_args = args[1:]
            
            # 检查最后一个参数是否为--return
            if shell_args and shell_args[-1] == '--return':
                return_command_only = True
                shell_args = shell_args[:-1]  # 移除--return标志
            
            if shell_args:
                # 执行指定的shell命令
                shell_cmd = ' '.join(shell_args)
                return handle_shell_command(shell_cmd, command_identifier, return_command_only)
            else:
                # 如果只有--return标志，没有实际命令
                error_msg = "用法: GOOGLE_DRIVE --shell <command> [--return]"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        else:
            # 进入交互式shell
            return enter_shell_mode(command_identifier)
    
    # 处理--return-command选项
    if len(args) > 0 and args[0] == '--return-command':
        if len(args) > 1:
            # 执行指定的shell命令，但只返回生成的远程命令
            shell_cmd = ' '.join(args[1:])
            return handle_shell_command(shell_cmd, command_identifier, return_command_only=True)
        else:
            error_msg = "用法: GOOGLE_DRIVE --return-command <shell_command>"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
    
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
        elif args[0] == '--console-setup':
            # 开始Google Drive API设置向导（终端交互版本）
            if is_run_environment(command_identifier):
                setup_data = {
                    "success": True,
                    "message": "Console setup wizard started",
                    "action": "console_setup_interactive"
                }
                write_to_json_output(setup_data, command_identifier)
            else:
                console_setup_interactive()
            return 0
        elif args[0] == '--console-setup-step2':
            # 设置步骤2：启用API
            if is_run_environment(command_identifier):
                setup_data = {
                    "success": True,
                    "message": "Setup step 2 started",
                    "action": "console_setup_step2"
                }
                write_to_json_output(setup_data, command_identifier)
            else:
                print("🔌 Google Drive API 设置 - 步骤 2")
                show_setup_step_2()
            return 0
        elif args[0] == '--console-setup-step3':
            # 设置步骤3：创建凭据
            if is_run_environment(command_identifier):
                setup_data = {
                    "success": True,
                    "message": "Setup step 3 started",
                    "action": "console_setup_step3"
                }
                write_to_json_output(setup_data, command_identifier)
            else:
                print("🔐 Google Drive API 设置 - 步骤 3")
                show_setup_step_3()
            return 0
        elif args[0] == '--console-setup-step4':
            # 设置步骤4：安装依赖和配置
            if is_run_environment(command_identifier):
                setup_data = {
                    "success": True,
                    "message": "Setup step 4 started",
                    "action": "console_setup_step4"
                }
                write_to_json_output(setup_data, command_identifier)
            else:
                print("📦 Google Drive API 设置 - 步骤 4")
                show_setup_step_4()
            return 0

        elif args[0] == '--pwd':
            # 显示当前路径（shell命令）
            return shell_pwd(command_identifier)
        elif args[0] == '--ls':
            # 处理多参数的ls命令（如--ls --shell-id xxx --detailed）
            shell_id = None
            detailed = False
            
            # 解析参数
            i = 1
            while i < len(args):
                if args[i] == '--shell-id' and i + 1 < len(args):
                    shell_id = args[i + 1]
                    i += 2
                elif args[i] == '--detailed':
                    detailed = True
                    i += 1
                else:
                    i += 1
            
            if shell_id:
                return shell_ls_with_id(shell_id, detailed, command_identifier)
            else:
                return shell_ls(None, command_identifier)
        elif args[0] == '--cd':
            # 切换目录到根目录（不带参数）
            return shell_cd("~", command_identifier)
        elif args[0] == '--url-to-path':
            # 测试URL转路径功能
            if len(args) > 1:
                url = args[1]
            else:
                url = get_multiline_input_safe("请输入Google Drive URL: ", single_line=True)
            
            logical_path = url_to_logical_path(url)
            if logical_path:
                result_data = {
                    "success": True,
                    "url": url,
                    "logical_path": logical_path
                }
                if is_run_environment(command_identifier):
                    write_to_json_output(result_data, command_identifier)
                else:
                    print(f"📍 URL: {url}")
                    print(f"🗂️ 逻辑路径: {logical_path}")
                return 0
            else:
                error_msg = "❌ 无法解析URL或获取路径"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg, "url": url}, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif args[0] == '--create-remote-shell':
            # 创建远程shell
            return create_remote_shell(command_identifier=command_identifier)
        elif args[0] == '--list-remote-shell':
            # 列出远程shell
            return list_remote_shells(command_identifier)
        elif args[0] == '-my':
            # My Drive URL
            url = "https://drive.google.com/drive/u/0/my-drive"
        elif args[0] == '--setup-hf':
            # 设置远端HuggingFace认证配置
            result = setup_remote_hf_credentials(command_identifier)
            if is_run_environment(command_identifier):
                write_to_json_output(result, command_identifier)
            return 0 if result["success"] else 1
        elif args[0] == '--test-hf':
            # 测试远端HuggingFace配置
            result = test_remote_hf_setup(command_identifier)
            if is_run_environment(command_identifier):
                write_to_json_output(result, command_identifier)
            return 0 if result["success"] else 1
        else:
            # 假设是URL
            url = args[0]
    elif len(args) == 2:
        if args[0] == '--checkout-remote-shell':
            # 切换远程shell
            return checkout_remote_shell(args[1], command_identifier)
        elif args[0] == '--terminate-remote-shell':
            # 终止远程shell
            return terminate_remote_shell(args[1], command_identifier)
        elif args[0] == '--mkdir':
            # 创建目录
            return shell_mkdir(args[1], command_identifier)
        elif args[0] == '--cd':
            # 切换目录
            return shell_cd(args[1], command_identifier)
        elif args[0] == '--rm':
            # 删除文件
            return shell_rm(args[1], False, command_identifier)
        elif args[0] == '--rm-rf':
            # 递归删除目录
            return shell_rm(args[1], True, command_identifier)
        elif args[0] == '--open-dir':
            # 打开目录
            return open_dir(args[1], command_identifier)
        elif args[0] == '--desktop':
            # Google Drive Desktop控制
            if len(args) < 2:
                error_msg = "请指定desktop操作: --status, --shutdown, --launch, --restart, --set-local-sync-dir, --set-global-sync-dir"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(f"❌ {error_msg}")
                return 1
            
            desktop_action = args[1]
            if desktop_action == '--status':
                return get_google_drive_status(command_identifier)
            elif desktop_action == '--shutdown':
                return shutdown_google_drive(command_identifier)
            elif desktop_action == '--launch':
                return launch_google_drive(command_identifier)
            elif desktop_action == '--restart':
                return restart_google_drive(command_identifier)
            elif desktop_action == '--set-local-sync-dir':
                return set_local_sync_dir(command_identifier)
            elif desktop_action == '--set-global-sync-dir':
                return set_global_sync_dir(command_identifier)
            else:
                error_msg = f"未知的desktop操作: {desktop_action}"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(f"❌ {error_msg}")
                return 1
        elif args[0] == '--upload':
            # 上传文件：GOOGLE_DRIVE --upload file_path [remote_path] 或 GOOGLE_DRIVE --upload "[[src1, dst1], [src2, dst2], ...]"
            if not GoogleDriveShell:
                error_msg = "❌ Google Drive Shell未初始化"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
            
            shell = GoogleDriveShell()
            
            # 检查是否为多文件语法
            if len(args) == 2 and args[1].startswith('[[') and args[1].endswith(']]'):
                try:
                    import ast
                    file_pairs = ast.literal_eval(args[1])
                    result = shell.cmd_upload_multi(file_pairs)
                except:
                    result = {"success": False, "error": "多文件语法格式错误，应为: [[src1, dst1], [src2, dst2], ...]"}
            else:
                # 原有的单文件或多文件到单目标语法
                target_path = "." if len(args) == 2 else args[2]
                result = shell.cmd_upload([args[1]], target_path)
            
            if is_run_environment(command_identifier):
                write_to_json_output(result, command_identifier)
            else:
                if result["success"]:
                    print(result["message"])
                    if result.get("uploaded_files"):
                        print(f"Successfully uploaded:")
                        for file in result["uploaded_files"]:
                            if file.get('url') and file['url'] != 'unavailable':
                                print(f"  - {file['name']} (ID: {file.get('id', 'unknown')}, URL: {file['url']})")
                            else:
                                print(f"  - {file['name']} (ID: {file.get('id', 'unknown')})")
                    if result.get("failed_files"):
                        print(f"Failed to upload:")
                        for file in result["failed_files"]:
                            print(f"  - {file}")
                else:
                    print(f"❌ {result.get('error', 'Upload failed')}")
            
            return 0 if result["success"] else 1

        else:
            # 检查是否有帮助选项
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
                error_msg = "❌ Error: Invalid arguments. Use --help for usage information."
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
    else:
        # 多个参数，检查是否有帮助选项或特殊命令
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
        elif args[0] == '--ls':
            # 处理多参数的ls命令（如--ls --shell-id xxx --detailed）
            shell_id = None
            detailed = False
            
            # 解析参数
            i = 1
            while i < len(args):
                if args[i] == '--shell-id' and i + 1 < len(args):
                    shell_id = args[i + 1]
                    i += 2
                elif args[i] == '--detailed':
                    detailed = True
                    i += 1
                else:
                    i += 1
            
            if shell_id:
                return shell_ls_with_id(shell_id, detailed, command_identifier)
            else:
                return shell_ls(None, command_identifier)
        elif args[0] == '--shell-id' and len(args) >= 2:
            # 处理--shell-id xxx --ls格式
            shell_id = args[1]
            detailed = False
            
            # 检查后续参数
            if len(args) > 2:
                if '--ls' in args[2:]:
                    if '--detailed' in args[2:]:
                        detailed = True
                    return shell_ls_with_id(shell_id, detailed, command_identifier)
                else:
                    # 其他shell-id相关命令可以在这里添加
                    error_msg = f"❌ Unsupported command with --shell-id: {' '.join(args[2:])}"
                    if is_run_environment(command_identifier):
                        write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                    else:
                        print(error_msg)
                    return 1
            else:
                error_msg = "❌ --shell-id requires additional command (e.g., --ls)"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif args[0] == '--upload' and len(args) == 3:
            # 上传文件到指定远程路径：GOOGLE_DRIVE --upload file_path remote_path
            if not GoogleDriveShell:
                error_msg = "❌ Google Drive Shell未初始化"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
            
            shell = GoogleDriveShell()
            result = shell.cmd_upload([args[1]], args[2])
            
            if is_run_environment(command_identifier):
                write_to_json_output(result, command_identifier)
            else:
                if result["success"]:
                    print(result["message"])
                    if result.get("uploaded_files"):
                        print(f"Successfully uploaded:")
                        for file in result["uploaded_files"]:
                            if file.get('url') and file['url'] != 'unavailable':
                                print(f"  - {file['name']} (ID: {file.get('id', 'unknown')}, URL: {file['url']})")
                            else:
                                print(f"  - {file['name']} (ID: {file.get('id', 'unknown')})")
                    if result.get("failed_files"):
                        print(f"Failed to upload:")
                        for file in result["failed_files"]:
                            print(f"  - {file}")
                else:
                    print(f"❌ {result.get('error', 'Upload failed')}")
            
            return 0 if result["success"] else 1
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

def test_api_connection(command_identifier=None):
    """测试Google Drive API连接"""
    try:
        # 导入API服务
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 运行API测试
        result = subprocess.run([
            sys.executable, str(api_service_path)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            success_msg = "✅ Google Drive API连接测试成功！"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": success_msg,
                    "output": result.stdout
                }, command_identifier)
            else:
                print(success_msg)
                print(result.stdout)
            return 0
        else:
            error_msg = f"❌ API连接测试失败: {result.stderr}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except subprocess.TimeoutExpired:
        timeout_msg = "⚠️ API测试超时"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": timeout_msg}, command_identifier)
        else:
            print(timeout_msg)
        return 1
    except Exception as e:
        error_msg = f"❌ 测试API连接时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def list_drive_files(command_identifier=None, max_results=10):
    """列出Google Drive文件"""
    try:
        # 导入并使用API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 动态导入API服务
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 列出文件
        result = drive_service.list_files(max_results=max_results)
        
        if result['success']:
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": f"找到 {result['count']} 个文件",
                    "files": result['files'],
                    "count": result['count']
                }, command_identifier)
            else:
                print(f"📂 Google Drive 文件列表 (前{max_results}个):")
                print("-" * 50)
                for file in result['files']:
                    file_type = "📁" if file['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                    print(f"{file_type} {file['name']}")
                    print(f"   ID: {file['id']}")
                    print(f"   类型: {file['mimeType']}")
                    if 'size' in file:
                        print(f"   大小: {file['size']} bytes")
                    print()
            return 0
        else:
            error_msg = f"❌ 列出文件失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 列出Drive文件时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def upload_file_to_drive(file_path, command_identifier=None):
    """上传文件到Google Drive"""
    try:
        if not os.path.exists(file_path):
            error_msg = f"❌ 文件不存在: {file_path}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 导入并使用API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 动态导入API服务
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 上传文件
        result = drive_service.upload_file(file_path)
        
        if result['success']:
            success_msg = f"✅ 文件上传成功: {result['file_name']}"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": success_msg,
                    "file_id": result['file_id'],
                    "file_name": result['file_name'],
                    "file_size": result.get('file_size')
                }, command_identifier)
            else:
                print(success_msg)
                print(f"📄 文件名: {result['file_name']}")
                print(f"🆔 文件ID: {result['file_id']}")
                if 'file_size' in result:
                    print(f"📏 文件大小: {result['file_size']} bytes")
            return 0
        else:
            error_msg = f"❌ 文件上传失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 上传文件时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def download_file_from_drive(file_id, command_identifier=None):
    """从Google Drive下载文件"""
    try:
        # 导入并使用API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 动态导入API服务
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 获取文件信息
        try:
            file_info = drive_service.service.files().get(fileId=file_id, fields="name").execute()
            file_name = file_info['name']
        except:
            file_name = f"downloaded_file_{file_id}"
        
        # 设置下载路径
        download_path = f"./{file_name}"
        
        # 下载文件
        result = drive_service.download_file(file_id, download_path)
        
        if result['success']:
            success_msg = f"✅ 文件下载成功: {result['local_path']}"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": success_msg,
                    "local_path": result['local_path'],
                    "file_id": file_id
                }, command_identifier)
            else:
                print(success_msg)
                print(f"📁 本地路径: {result['local_path']}")
            return 0
        else:
            error_msg = f"❌ 文件下载失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 下载文件时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def delete_drive_file(file_id, command_identifier=None):
    """删除Google Drive文件"""
    try:
        # 导入并使用API服务
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 动态导入API服务
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 删除文件
        result = drive_service.delete_file(file_id)
        
        if result['success']:
            success_msg = f"✅ 文件删除成功"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": success_msg,
                    "file_id": file_id
                }, command_identifier)
            else:
                print(success_msg)
                print(f"🗑️ 已删除文件ID: {file_id}")
            return 0
        else:
            error_msg = f"❌ 文件删除失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 删除文件时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def handle_multiple_commands(shell_cmd, command_identifier=None):
    """处理多个用&&连接的shell命令"""
    try:
        commands = shell_cmd.split(" && ")
        results = []
        
        for i, cmd in enumerate(commands):
            cmd = cmd.strip()
            if not cmd:
                continue
                
            # print(f"🔄 执行命令 {i+1}/{len(commands)}: {cmd}")
            
            # 递归调用单个命令处理
            result_code = handle_shell_command(cmd, command_identifier)
            
            # 如果任何一个命令失败，停止执行后续命令
            if result_code != 0:
                if not is_run_environment(command_identifier):
                    print(f"❌ 命令失败，停止执行后续命令")
                return result_code
            
            results.append(result_code)
        
        # 所有命令都成功
        if not is_run_environment(command_identifier):
            pass
            # print(f"✅ 所有 {len(commands)} 个命令执行成功")
        
        return 0
        
    except Exception as e:
        error_msg = f"执行多命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"❌ {error_msg}")
        return 1

def handle_shell_command(shell_cmd, command_identifier=None, return_command_only=False):
    """处理shell命令"""
    try:
        if not GoogleDriveShell:
            error_msg = "❌ Google Drive Shell未初始化"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        shell = GoogleDriveShell()
        
        # 检查是否包含多命令组合（&&）
        # 对于包含 || 或 | 的命令，应该作为单个bash命令处理
        has_multi_commands = ' && ' in shell_cmd
        if has_multi_commands:
            if return_command_only:
                # 对于多命令组合，尝试直接处理而不是拒绝
                try:
                    # 将整个多命令组合作为单个bash命令处理
                    result = shell.execute_generic_remote_command("bash", ["-c", shell_cmd], return_command_only)
                    return result
                except Exception as e:
                    error_msg = f"多命令组合处理失败: {str(e)}"
                    if is_run_environment(command_identifier):
                        write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                    else:
                        print(error_msg)
                    return 1
            return handle_multiple_commands(shell_cmd, command_identifier)
        
        # 对于包含 || 或 | 的命令，直接作为bash命令处理
        if ' || ' in shell_cmd or ' | ' in shell_cmd:
            try:
                result = shell.execute_generic_remote_command("bash", ["-c", shell_cmd], return_command_only)
                if return_command_only:
                    return result
                
                # 处理执行结果
                if result.get("success", False):
                    return 0
                else:
                    error_msg = result.get("error", "命令执行失败")
                    if is_run_environment(command_identifier):
                        write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                    else:
                        print(f"❌ {error_msg}")
                    return 1
                    
            except Exception as e:
                error_msg = f"bash命令执行失败: {str(e)}"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        
        # 解析shell命令 - 使用shlex来正确处理带引号和空格的参数
        import shlex
        
        try:
            cmd_parts = shlex.split(shell_cmd)
        except ValueError:
            # 如果shlex解析失败，回退到简单分割
            cmd_parts = shell_cmd.split()
        
        cmd = cmd_parts[0]
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        # 特殊处理：检测python -c命令的参数丢失引号问题
        if cmd == "python" and len(args) >= 1 and (args[0] == "-c" or "-c" in shell_cmd):
            # 重新组装python代码参数 - 直接从原始命令中提取，避免shlex分割问题
            import re
            # 从原始命令中提取 -c 后面的所有内容，支持多行
            match = re.search(r'python\s+-c\s+(.+)', shell_cmd, re.DOTALL)
            if match:
                python_code = match.group(1).strip()
                # 处理不同类型的引号包围
                if python_code.startswith('"""') and python_code.endswith('"""'):
                    # 三重双引号
                    python_code = python_code[3:-3]
                elif python_code.startswith("'''") and python_code.endswith("'''"):
                    # 三重单引号
                    python_code = python_code[3:-3]
                elif (python_code.startswith('"') and python_code.endswith('"')) or \
                     (python_code.startswith("'") and python_code.endswith("'")):
                    # 单重引号
                    python_code = python_code[1:-1]
                args = ["-c", python_code]
            else:
                # 回退到原来的方法
                if len(args) >= 2 and args[0] == "-c":
                    python_code = " ".join(args[1:])
                    args = ["-c", python_code]
        
        # 通用路径转换函数：将shell展开的本地路径转换回远程逻辑路径
        def convert_local_path_to_remote(path):
            """将shell展开的本地路径转换回远程逻辑路径"""
            if not path:
                return path
                
            # 获取用户主目录
            home_path = os.path.expanduser("~")
            
            # 如果路径是用户主目录，转换为~
            if path == home_path:
                return "~"
            # 如果是主目录下的子路径，转换为~/相对路径
            elif path.startswith(home_path + "/"):
                relative_part = path[len(home_path) + 1:]
                return f"~/{relative_part}"
            # 其他情况保持原样
            else:
                return path

        # 执行对应命令
        if cmd == "pwd":
            result = shell.cmd_pwd()
        elif cmd == "ls":
            detailed = False
            recursive = False
            show_hidden = False
            long_format = False  # New flag for -l option
            path = None
            
            # Parse arguments, including combined flags like -la, -lr, etc.
            for arg in args:
                if arg == "--detailed":
                    detailed = True
                elif arg == "-R":
                    recursive = True
                elif arg.startswith("-") and len(arg) > 1:
                    # Handle combined flags like -la, -lr, -al, etc.
                    for flag in arg[1:]:  # Skip the first '-'
                        if flag == "a":
                            show_hidden = True
                        elif flag == "l":
                            long_format = True
                        elif flag == "R":
                            recursive = True
                        # Add more flags as needed
                else:
                    path = arg
            
            # Convert local path to remote logical path
            path = convert_local_path_to_remote(path)
            
            result = shell.cmd_ls(path, detailed, recursive, show_hidden)
            
            # Pass the long_format flag to the result for proper formatting
            if result.get("success"):
                result["long_format"] = long_format
            
            # Ensure show_hidden info is passed to result processing
            if 'args' not in locals():
                args = []
            if show_hidden and '-a' not in args:
                args.append('-a')
            if long_format and '-l' not in args:
                args.append('-l')
        elif cmd == "cd":
            path = args[0] if args else "~"
            # 转换本地路径为远程逻辑路径
            path = convert_local_path_to_remote(path)
            result = shell.cmd_cd(path)
        elif cmd == "mkdir":
            if not args:
                result = {"success": False, "error": "请指定要创建的目录名称"}
            else:
                recursive = False
                path = None
                
                # 解析参数
                for arg in args:
                    if arg == "-p":
                        recursive = True
                    else:
                        path = arg
                
                if not path:
                    result = {"success": False, "error": "请指定要创建的目录名称"}
                else:
                    # 转换本地路径为远程逻辑路径
                    path = convert_local_path_to_remote(path)
                    result = shell.cmd_mkdir(path, recursive)
        elif cmd == "rm":
            if not args:
                result = {"success": False, "error": "Please specify file or directory to delete"}
            else:
                # Parse flags bash-style: -r, -f, -rf, -fr, etc.
                recursive = False
                force = False
                paths = []
                
                for arg in args:
                    if arg.startswith("-"):
                        # Parse combined flags like -rf, -fr, -r, -f
                        if "r" in arg:
                            recursive = True
                        if "f" in arg:
                            force = True
                    else:
                        paths.append(arg)
                
                if not paths:
                    result = {"success": False, "error": "Please specify file or directory to delete"}
                else:
                    # Handle multiple paths - process each path separately
                    all_results = []
                    overall_success = True
                    
                    for path in paths:
                        # 转换本地路径为远程逻辑路径
                        converted_path = convert_local_path_to_remote(path)
                        path_result = shell.cmd_rm(converted_path, recursive=recursive, force=force)
                        all_results.append({
                            "path": path,
                            "result": path_result
                        })
                        if not path_result.get("success", False):
                            overall_success = False
                    
                    # Combine results
                    if overall_success:
                        result = {
                            "success": True,
                            "message": f"Successfully deleted {len(paths)} items",
                            "details": all_results
                        }
                    else:
                        failed_paths = [item["path"] for item in all_results if not item["result"].get("success", False)]
                        result = {
                            "success": False,
                            "error": f"Failed to delete some items: {', '.join(failed_paths)}",
                            "details": all_results
                        }

        elif cmd == "echo":
            if not args:
                result = {"success": True, "output": ""}
            elif len(args) >= 3 and args[-2] == ">":
                # echo "text" > file
                text = " ".join(args[:-2])
                output_file = args[-1]
                result = shell.cmd_echo(text, output_file)
            else:
                # echo "text"
                text = " ".join(args)
                result = shell.cmd_echo(text)
        elif cmd == "cat":
            if not args:
                result = {"success": False, "error": "请指定要查看的文件"}
            else:
                # 转换本地路径为远程逻辑路径
                filename = convert_local_path_to_remote(args[0])
                result = shell.cmd_cat(filename)
        elif cmd == "grep":
            if len(args) < 2:
                result = {"success": False, "error": "用法: grep <pattern> <file1> [file2] ..."}
            else:
                pattern = args[0]
                files = [convert_local_path_to_remote(f) for f in args[1:]]
                result = shell.cmd_grep(pattern, *files)
        elif cmd == "python":
            if not args:
                result = {"success": False, "error": "用法: python <file> 或 python -c '<code>'"}
            else:
                # 使用统一的远端命令执行接口处理python命令
                result = shell.execute_generic_remote_command(cmd, args, return_command_only)
        elif cmd == "download":
            if not args:
                result = {"success": False, "error": "用法: download [--force] <filename> [local_path]"}
            else:
                # 检查是否有--force选项
                force_download = False
                download_args = args.copy()
                
                if "--force" in download_args:
                    force_download = True
                    download_args.remove("--force")
                
                if len(download_args) == 0:
                    result = {"success": False, "error": "用法: download [--force] <filename> [local_path]"}
                elif len(download_args) == 1:
                    result = shell.cmd_download(download_args[0], force=force_download)
                else:
                    result = shell.cmd_download(download_args[0], download_args[1], force=force_download)
        elif cmd == "read":
            if not args:
                result = {"success": False, "error": "用法: read <filename> [start end] 或 read <filename> [[start1, end1], [start2, end2], ...]"}
            else:
                # 转换本地路径为远程逻辑路径
                filename = convert_local_path_to_remote(args[0])
                range_args = args[1:] if len(args) > 1 else []
                result = shell.cmd_read(filename, *range_args)
        elif cmd == "find":
            if not args:
                result = {"success": False, "error": "用法: find [path] -name [pattern] 或 find [path] -type [f|d] -name [pattern]"}
            else:
                # 转换路径参数（通常是第一个参数，如果不是选项的话）
                converted_args = []
                for i, arg in enumerate(args):
                    if i == 0 and not arg.startswith('-'):
                        # 第一个参数如果不是选项，则是路径
                        converted_args.append(convert_local_path_to_remote(arg))
                    else:
                        converted_args.append(arg)
                result = shell.cmd_find(*converted_args)
        elif cmd == "mv":
            if not args:
                result = {"success": False, "error": "用法: mv <source> <destination> 或 mv [[src1, dst1], [src2, dst2], ...]"}
            elif len(args) == 1 and args[0].startswith('[[') and args[0].endswith(']]'):
                # 新的多文件语法
                try:
                    import ast
                    file_pairs = ast.literal_eval(args[0])
                    result = shell.cmd_mv_multi(file_pairs)
                except:
                    result = {"success": False, "error": "多文件语法格式错误，应为: [[src1, dst1], [src2, dst2], ...]"}
            elif len(args) == 2:
                # 原有的单文件语法
                # 转换本地路径为远程逻辑路径
                src = convert_local_path_to_remote(args[0])
                dst = convert_local_path_to_remote(args[1])
                result = shell.cmd_mv(src, dst)
            else:
                result = {"success": False, "error": "用法: mv <source> <destination> 或 mv [[src1, dst1], [src2, dst2], ...]"}
        elif cmd == "edit":
            if not args:
                result = {"success": False, "error": "用法: edit [--preview] [--backup] <filename> '<replacement_spec>'"}
            else:
                # 解析选项
                preview_mode = False
                backup_mode = False
                edit_args = args.copy()
                
                if "--preview" in edit_args:
                    preview_mode = True
                    edit_args.remove("--preview")
                
                if "--backup" in edit_args:
                    backup_mode = True
                    edit_args.remove("--backup")
                
                if len(edit_args) < 2:
                    result = {"success": False, "error": "用法: edit [--preview] [--backup] <filename> '<replacement_spec>'"}
                else:
                    filename = edit_args[0]
                    # 转换本地路径为远程逻辑路径
                    filename = convert_local_path_to_remote(filename)
                    # 修复：重新从原始shell_cmd中提取JSON参数，避免shlex分割问题
                    # 找到文件名后的JSON部分
                    import re
                    # 匹配 filename 后面的 JSON 部分（可能包含选项）
                    pattern = r'edit\s+(?:--\w+\s+)*' + re.escape(edit_args[0]) + r'\s+(.*)'  # 使用原始文件名匹配
                    match = re.search(pattern, shell_cmd)
                    if match:
                        replacement_spec = match.group(1).strip()
                    else:
                        # 回退到原来的方法
                        replacement_spec = " ".join(edit_args[1:])
                    result = shell.cmd_edit(filename, replacement_spec, preview=preview_mode, backup=backup_mode)
        elif cmd == "upload":
            if not args:
                result = {"success": False, "error": "用法: upload [--force] [--remove-local] <file1> [file2] ... [target_path] 或 upload [--force] [--remove-local] [[src1, dst1], [src2, dst2], ...]"}
            else:
                # 解析选项
                force = False
                remove_local = False
                upload_args = []
                
                for arg in args:
                    if arg == '--force':
                        force = True
                    elif arg == '--remove-local':
                        remove_local = True
                    else:
                        upload_args.append(arg)
                
                if not upload_args:
                    result = {"success": False, "error": "Please specify file to upload"}
                else:
                    # 检查是否为新的多文件语法 [[src, dst], ...]
                    if len(upload_args) == 1 and upload_args[0].startswith('[[') and upload_args[0].endswith(']]'):
                        try:
                            import ast
                            file_pairs = ast.literal_eval(upload_args[0])
                            result = shell.cmd_upload_multi(file_pairs, force=force, remove_local=remove_local)
                        except:
                            result = {"success": False, "error": "多文件语法格式错误，应为: [[src1, dst1], [src2, dst2], ...]"}
                    else:
                        # 原有的单目标路径语法
                        if len(upload_args) >= 2 and not os.path.exists(upload_args[-1]):
                            source_files = upload_args[:-1]
                            target_path = convert_local_path_to_remote(upload_args[-1])
                        else:
                            source_files = upload_args
                            target_path = "."
                        
                        # 检查是否有文件夹需要上传，如果是单个文件夹则使用cmd_upload_folder
                        if len(source_files) == 1 and os.path.isdir(source_files[0]):
                            result = shell.cmd_upload_folder(source_files[0], target_path, keep_zip=False)
                        else:
                            result = shell.cmd_upload(source_files, target_path, force=force, remove_local=remove_local)
        elif cmd == "upload-folder":
            if not args:
                result = {"success": False, "error": "用法: upload-folder [--keep-zip] <folder_path> [target_path]"}
            else:
                # 解析参数
                keep_zip = False
                folder_args = []
                
                for arg in args:
                    if arg == '--keep-zip':
                        keep_zip = True
                    else:
                        folder_args.append(arg)
                
                if not folder_args:
                    result = {"success": False, "error": "请指定要上传的文件夹"}
                else:
                    folder_path = folder_args[0]
                    target_path = folder_args[1] if len(folder_args) > 1 else "."
                    result = shell.cmd_upload_folder(folder_path, target_path, keep_zip=keep_zip)
        elif cmd == "help":
            result = {
                "success": True,
                "commands": [
                    "pwd                         - show current directory", 
                    "ls [path] [--detailed] [-R] - list directory contents (recursive with -R)", 
                    "mkdir [-p] <dir>             - create directory (recursive with -p)",
                    "cd <path>                    - change directory",
                    "rm <file>                    - remove file",
                    "rm -rf <dir>                 - remove directory recursively",
                    "echo <text>                  - display text",
                    "echo <text> > <file>         - create file with text",
                    "cat <file>                   - display file contents",
                    "grep <pattern> <file>        - search for pattern in file",
                    "python <file>                - execute python file",
                    "python -c '<code>'           - execute python code",
                    "download [--force] <file> [path] - download file with caching",
                    "read <file> [start end]      - read file content with line numbers",
                    "find [path] -name [pattern]  - search for files matching pattern",
                    "mv <source> <dest>           - move/rename file or folder",
                    "edit [--preview] [--backup] <file> '<spec>' - edit file with multi-segment replacement",
                    "upload <files...> [target]   - upload files to Google Drive",
                    "upload-folder [--keep-zip] <folder> [target] - upload folder (zip->upload->unzip->cleanup)"
                ]
            }
        else:
            # 使用统一的远端命令执行接口处理未知命令
            result = shell.execute_generic_remote_command(cmd, args, return_command_only)
        
        # 输出结果
        # 处理--return-command选项：直接返回结果，不管是否在RUN环境
        if return_command_only and result.get("action") == "return_command_only":
            return result
            
        if is_run_environment(command_identifier):
            write_to_json_output(result, command_identifier)
        else:
            
            if result["success"]:
                if cmd == "pwd":
                    # bash风格：只输出路径
                    print(result['current_path'])
                elif cmd == "ls":
                    # Check for long format (-l) or extended mode
                    if result.get("long_format"):
                        # Long format mode (-l): bash-like detailed listing
                        folders = result.get("folders", [])
                        files = result.get("files", [])
                        
                        def format_size(size_str):
                            """Format file size in a readable way"""
                            if not size_str:
                                return "0"
                            try:
                                size = int(size_str)
                                if size < 1024:
                                    return f"{size}"
                                elif size < 1024*1024:
                                    return f"{size//1024}K"
                                elif size < 1024*1024*1024:
                                    return f"{size//(1024*1024)}M"
                                else:
                                    return f"{size//(1024*1024*1024)}G"
                            except:
                                return "0"
                        
                        def format_time(time_str):
                            """Format modification time in bash ls -l style"""
                            if not time_str:
                                return "Jan  1 00:00"
                            try:
                                from datetime import datetime
                                # Parse Google Drive time format
                                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                                return dt.strftime("%b %d %H:%M")
                            except:
                                return "Jan  1 00:00"
                        
                        # Display folders first
                        for folder in folders:
                            name = folder['name']
                            time_str = format_time(folder.get('modifiedTime'))
                            url = folder.get('url', 'N/A')
                            print(f"drwxr-xr-x    - {time_str} {name}/")
                            print(f"    URL: {url}")
                            print()  # 添加空行分割
                        
                        # Display files
                        for file in files:
                            name = file['name']
                            size_str = format_size(file.get('size'))
                            time_str = format_time(file.get('modifiedTime'))
                            url = file.get('url', 'N/A')
                            print(f"-rw-r--r-- {size_str:>8} {time_str} {name}")
                            print(f"    URL: {url}")
                            print()  # 添加空行分割
                            
                    elif result.get("mode") == "extended":
                        # Legacy extended mode - keeping for backward compatibility
                        folders = result.get("folders", [])
                        files = result.get("files", [])
                        
                        print(f"Directory: {result.get('path', '.')}")
                        print(f"Total: {result.get('count', 0)} items")
                        print()
                        
                        # Display folders
                        if folders:
                            print("Folders:")
                            for folder in folders:
                                print(f"  {folder['name']}/")
                                print(f"    URL: {folder.get('url', 'N/A')}")
                                if 'modifiedTime' in folder:
                                    print(f"    Modified: {folder['modifiedTime']}")
                                print()
                        
                        # Display files
                        if files:
                            print("Files:")
                            for file in files:
                                print(f"  {file['name']}")
                                print(f"    URL: {file.get('url', 'N/A')}")
                                if 'modifiedTime' in file:
                                    print(f"    Modified: {file['modifiedTime']}")
                                if 'size' in file:
                                    # Format file size
                                    size = int(file['size'])
                                    if size < 1024:
                                        size_str = f"{size} B"
                                    elif size < 1024*1024:
                                        size_str = f"{size/1024:.1f} KB"
                                    elif size < 1024*1024*1024:
                                        size_str = f"{size/(1024*1024):.1f} MB"
                                    else:
                                        size_str = f"{size/(1024*1024*1024):.1f} GB"
                                    print(f"    Size: {size_str}")
                                print()
                    elif result.get("mode") in ["detailed", "recursive_detailed"]:
                        # 详细模式：直接输出JSON
                        import json
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                    elif result.get("mode") == "recursive_bash":
                        # 递归bash模式：按路径分组显示
                        if result.get("all_items"):
                            current_path = None
                            for item in result["all_items"]:
                                if item["path"] != current_path:
                                    current_path = item["path"]
                                    print(f"\n{current_path}:")
                                
                                # 显示项目名称，文件夹加/后缀
                                if item["mimeType"] == "application/vnd.google-apps.folder":
                                    print(f"  {item['name']}/")
                                else:
                                    # 跳过隐藏文件
                                    if not item['name'].startswith('.'):
                                        print(f"  {item['name']}")
                    else:
                        # bash style: only show file names
                        if result.get("files") is not None:
                            folders = result.get("folders", [])
                            files = result.get("files", [])  # files field now only contains non-folder files
                            all_items = []
                            
                            # Use set to avoid duplicates
                            seen_names = set()
                            
                            # Add directories (with / suffix)
                            for folder in folders:
                                # Check if hidden file should be shown
                                show_hidden = "-a" in args if 'args' in locals() else False
                                if folder['name'].startswith('.') and not show_hidden:
                                    continue
                                    
                                folder_name = f"{folder['name']}/"
                                if folder_name not in seen_names:
                                    all_items.append(folder_name)
                                    seen_names.add(folder_name)
                            
                            # Add files (exclude hidden files unless -a flag is specified)
                            # Check if -a parameter exists (show hidden files)
                            show_hidden = "-a" in args if 'args' in locals() else False
                            
                            for file in files:
                                # Skip hidden files starting with . (unless -a flag is present)
                                if file['name'].startswith('.') and not show_hidden:
                                    continue
                                if file['name'] not in seen_names:
                                    all_items.append(file['name'])
                                    seen_names.add(file['name'])
                            
                            # Display in lines with appropriate spacing
                            if all_items:
                                # Calculate terminal width, default 80 characters
                                import shutil
                                try:
                                    terminal_width = shutil.get_terminal_size().columns
                                except:
                                    terminal_width = 80
                                
                                # If filenames are long, use vertical layout
                                max_item_length = max(len(item) for item in all_items) if all_items else 0
                                
                                if max_item_length > 30 or len(all_items) <= 3:
                                    # Long filenames or few files, one per line
                                    for item in all_items:
                                        print(item)
                                else:
                                    # Short filenames, use column layout
                                    # Calculate appropriate column width, at least 15 characters, max 30 characters
                                    col_width = min(max(15, max_item_length + 2), 30)
                                    items_per_line = max(1, terminal_width // col_width)
                                    
                                    # Display by lines
                                    for i in range(0, len(all_items), items_per_line):
                                        line_items = all_items[i:i + items_per_line]
                                        formatted_line = []
                                        
                                        for item in line_items:
                                            if len(item) <= col_width - 2:
                                                # Normal display
                                                formatted_line.append(f"{item:<{col_width}}")
                                            else:
                                                # Truncate long filenames
                                                truncated = f"{item[:col_width-5]}..."
                                                formatted_line.append(f"{truncated:<{col_width}}")
                                        
                                        print("".join(formatted_line).rstrip())
                            else:
                                # Empty directory - bash style: don't display anything
                                pass
                elif cmd == "help":
                    # 保持help的详细输出
                    for command_help in result["commands"]:
                        print(command_help)
                elif cmd == "echo":
                    # echo命令输出文本（如果有输出）
                    if "output" in result:
                        print(result["output"])
                    elif not result["success"] and "info" in result:
                        # 文件创建失败时的友好提示
                        print(f"echo: {result['error']}")
                        if not is_run_environment(command_identifier):
                            print("\n💡 替代方案:")
                            for alt in result["info"]["alternatives"]:
                                print(f"   • {alt}")
                            print("\n✅ 可用功能:")
                            for feature in result["info"]["working_features"]:
                                print(f"   {feature}")
                elif cmd == "cat":
                    # cat命令输出文件内容
                    if "output" in result:
                        print(result["output"])
                elif cmd == "read":
                    # read命令输出文件内容（带行号）
                    if "output" in result:
                        print(result["output"])
                elif cmd == "find":
                    # find命令输出搜索结果
                    if "output" in result:
                        print(result["output"])
                    if result.get("success") and "count" in result:
                        print("\nFound", result.get("count", 0), "matches.")
                elif cmd == "grep":
                    # grep命令输出匹配行
                    if "output" in result:
                        print(result["output"])
                elif cmd == "python":
                    # python命令现在使用远端执行接口，由通用处理逻辑处理
                    if "path" in result and "stdout" in result and "stderr" in result:
                        # 远端命令执行结果
                        if result.get("stdout"):
                            print(result["stdout"], end="")
                        if result.get("stderr"):
                            print(result["stderr"], file=sys.stderr, end="")
                    else:
                        # 兼容旧格式
                        if "stdout" in result:
                            if result["stdout"]:
                                print(result["stdout"])
                            if result["stderr"]:
                                print(result["stderr"], file=sys.stderr)
                elif cmd == "download":
                    # download命令输出缓存下载信息
                    if "message" in result:
                        print(result["message"])
                elif cmd == "edit":
                    # edit命令输出编辑结果
                    if result.get("mode") == "preview":
                        # 预览模式
                        print(f"📝 预览模式 - 文件: {result.get('filename')}")
                        print(f"原始行数: {result.get('original_lines')}, 修改后行数: {result.get('modified_lines')}")
                        print(f"应用替换: {result.get('replacements_applied')} 个")
                        
                        if result.get("diff", {}).get("summary"):
                            print("\n🔄 修改摘要:")
                            for summary in result["diff"]["summary"]:
                                print(f"  • {summary}")
                        
                        print(f"\n📄 修改后内容预览:")
                        print("=" * 50)
                        print(result.get("preview_content", ""))
                        print("=" * 50)
                    else:
                        # 正常编辑模式
                        if "message" in result:
                            print(result["message"])
                        
                        if result.get("diff", {}).get("summary"):
                            print("\n🔄 修改摘要:")
                            for summary in result["diff"]["summary"]:
                                print(f"  • {summary}")
                        
                        if result.get("backup_created"):
                            print(f"💾 备份文件已创建: {result.get('backup_filename')}")
                        elif result.get("backup_error"):
                            print(f"⚠️  备份创建失败: {result.get('backup_error')}")
                elif cmd == "upload":
                    # bash风格简洁输出
                    if result.get("uploaded_files"):
                        for file in result["uploaded_files"]:
                            # 获取目标文件夹路径
                            target_folder = result.get("target_path", "remote folder")
                            if not target_folder or target_folder == "remote folder":
                                # 尝试从当前shell获取路径
                                if hasattr(shell, 'get_current_shell'):
                                    current_shell = shell.get_current_shell()
                                    if current_shell:
                                        target_folder = current_shell.get("current_path", "~")
                                else:
                                    target_folder = "~"
                            
                            # 简洁的成功输出
                            print(f"File {file['name']} uploaded successfully to {target_folder}")
                    
                    if result.get("failed_files"):
                        for file_info in result["failed_files"]:
                            if isinstance(file_info, dict):
                                file_name = file_info.get('name', 'unknown')
                                error_msg = file_info.get('error', 'unknown error')
                            else:
                                file_name = str(file_info)
                                error_msg = "upload failed"
                            print(f"File {file_name} failed to upload: {error_msg}")
                elif cmd in ["mkdir", "cd", "rm", "mv"]:
                    # bash风格：成功的命令不输出任何内容
                    pass
                else:
                    # 检查是否为远端命令执行结果
                    if "path" in result and "stdout" in result and "stderr" in result:
                        # 远端命令执行结果的特殊输出格式
                        if result.get("stdout"):
                            print(result["stdout"], end="")
                        if result.get("stderr"):
                            print(result["stderr"], file=sys.stderr, end="")
                        
                        # 在RUN环境下输出完整JSON，包含所有字段
                        if is_run_environment(command_identifier):
                            # 确保包含所有必要字段
                            run_result = {
                                "success": result.get("success", True),
                                "cmd": result.get("cmd"),
                                "args": result.get("args", []),
                                "exit_code": result.get("exit_code", 0),
                                "stdout": result.get("stdout", ""),
                                "stderr": result.get("stderr", ""),
                                "working_dir": result.get("working_dir", ""),
                                "timestamp": result.get("timestamp", ""),
                                "path": result.get("path", "")  # 本地结果文件路径
                            }
                            write_to_json_output(run_result, command_identifier)
                    else:
                        # 其他命令保持简洁输出
                        if "message" in result:
                            print(result["message"])
            else:
                # bash风格错误输出：command: error message
                # 对于有用户输入的命令，使用统一接口处理错误信息
                if cmd in ["upload", "mv", "rm"] and hasattr(shell, '_format_tkinter_result_message'):
                    formatted_msg = shell._format_tkinter_result_message(result, "操作成功", "操作失败")
                    print(f"{cmd}: {formatted_msg}")
                else:
                    error_msg = result.get("error", "Command failed")
                    # 移除中文前缀，使用英文格式
                    if "目录不存在" in error_msg:
                        print(f"{cmd}: no such file or directory: {args[0] if args else ''}")
                    elif "文件或目录不存在" in error_msg:
                        print(f"{cmd}: {args[0] if args else 'file'}: No such file or directory")
                    elif "请指定" in error_msg:
                        print(f"{cmd}: missing operand")
                    else:
                        print(f"{cmd}: {error_msg}")
                return 1
        
        return 0 if result["success"] else 1
        
    except Exception as e:
        error_msg = f"❌ 执行shell命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def shell_ls_with_id(folder_id, detailed=False, command_identifier=None):
    """列出指定文件夹ID的文件和文件夹"""
    try:
        # 使用API列出文件
        import sys
        api_service_path = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "❌ API服务文件不存在，请先运行 GOOGLE_DRIVE --console-setup"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 列出文件
        result = drive_service.list_files(folder_id=folder_id, max_results=50)
        
        if result['success']:
            files = result['files']
            
            if detailed:
                # 详细模式：返回JSON格式
                result_data = {
                    "success": True,
                    "folder_id": folder_id,
                    "files": files,
                    "mode": "detailed"
                }
                
                if is_run_environment(command_identifier):
                    write_to_json_output(result_data, command_identifier)
                else:
                    import json
                    print(json.dumps(result_data, indent=2, ensure_ascii=False))
            else:
                # 简洁模式：bash风格输出
                if is_run_environment(command_identifier):
                    result_data = {
                        "success": True,
                        "folder_id": folder_id,
                        "files": files,
                        "mode": "bash"
                    }
                    write_to_json_output(result_data, command_identifier)
                else:
                    # 分离文件夹和文件
                    folders = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder']
                    non_folders = [f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder']
                    
                    all_items = []
                    
                    # 添加目录（带/后缀）
                    for folder in folders:
                        all_items.append(f"{folder['name']}/")
                    
                    # 添加文件
                    for file in non_folders:
                        # 跳过隐藏文件
                        if not file['name'].startswith('.'):
                            all_items.append(file['name'])
                    
                    # 输出
                    if all_items:
                        # 计算终端宽度，默认80字符
                        import shutil
                        try:
                            terminal_width = shutil.get_terminal_size().columns
                        except:
                            terminal_width = 80
                        
                        # 如果文件名很长，使用垂直布局
                        max_item_length = max(len(item) for item in all_items) if all_items else 0
                        
                        if max_item_length > 30 or len(all_items) <= 3:
                            # 长文件名或文件数量少时，每行一个
                            for item in all_items:
                                print(item)
                        else:
                            # 短文件名时，使用列布局
                            col_width = min(max(15, max_item_length + 2), 30)
                            items_per_line = max(1, terminal_width // col_width)
                            
                            # 按行显示
                            for i in range(0, len(all_items), items_per_line):
                                line_items = all_items[i:i + items_per_line]
                                formatted_line = []
                                
                                for item in line_items:
                                    if len(item) <= col_width - 2:
                                        formatted_line.append(f"{item:<{col_width}}")
                                    else:
                                        truncated = f"{item[:col_width-5]}..."
                                        formatted_line.append(f"{truncated:<{col_width}}")
                                
                                print("".join(formatted_line).rstrip())
            
            return 0
        else:
            error_msg = f"❌ 列出文件失败: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"❌ 执行ls命令时出错: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def get_local_hf_token():
    """
    获取本地HuggingFace token
    
    Returns:
        dict: 包含token信息或错误信息
    """
    try:
        # 检查HUGGINGFACE工具是否可用
        import subprocess
        result = subprocess.run(['HUGGINGFACE', '--status'], capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": "HUGGINGFACE tool not available or not authenticated"}
        
        # 直接读取token文件
        import os
        from pathlib import Path
        
        hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        token_path = Path(hf_home) / "token"
        
        if not token_path.exists():
            return {"success": False, "error": "HuggingFace token file not found"}
        
        try:
            with open(token_path, 'r') as f:
                token = f.read().strip()
            
            if not token:
                return {"success": False, "error": "HuggingFace token file is empty"}
            
            return {
                "success": True,
                "token": token,
                "token_path": str(token_path),
                "token_length": len(token)
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read token file: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"Failed to get local HF token: {str(e)}"}

def setup_remote_hf_credentials(command_identifier=None):
    """
    设置远端HuggingFace认证配置
    
    Args:
        command_identifier (str): 命令标识符
        
    Returns:
        dict: 操作结果
    """
    try:
        # 1. 获取本地HF token
        token_result = get_local_hf_token()
        if not token_result["success"]:
            return {
                "success": False,
                "error": f"Failed to get local HF token: {token_result['error']}"
            }
        
        token = token_result["token"]
        
        # 2. 生成远端设置命令
        remote_setup_commands = f"""
# HuggingFace Credentials Setup
export HF_TOKEN="{token}"
export HUGGINGFACE_HUB_TOKEN="{token}"

# Create HF cache directory
mkdir -p ~/.cache/huggingface

# Write token to standard location
echo "{token}" > ~/.cache/huggingface/token
chmod 600 ~/.cache/huggingface/token

# Verify setup
if [ -f ~/.cache/huggingface/token ]; then
    echo "✅ HuggingFace token configured successfully"
    echo "Token length: {len(token)}"
    echo "Token prefix: {token[:8]}..."
else
    echo "❌ Failed to configure HuggingFace token"
    exit 1
fi

# Test HuggingFace authentication (if python and pip are available)
if command -v python3 >/dev/null 2>&1; then
    echo "🧪 Testing HuggingFace authentication..."
    python3 -c "
import sys
import subprocess

try:
    # Try to install huggingface_hub if not available
    try:
        import huggingface_hub
    except ImportError:
        print('📦 Installing huggingface_hub...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'huggingface_hub', '--quiet'])
        import huggingface_hub
    
    # Test authentication
    from huggingface_hub import HfApi
    api = HfApi()
    user_info = api.whoami()
    username = user_info.get('name', 'Unknown')
    email = user_info.get('email', 'Unknown')
    
    print('✅ HuggingFace authentication successful!')
    print(f'   Username: {{username}}')
    print(f'   Email: {{email}}')
    
    # Test model access
    try:
        model_info = api.model_info('bert-base-uncased')
        print('✅ Model access verified (can access public models)')
    except Exception as model_error:
        print(f'⚠️  Model access test failed: {{model_error}}')
    
    # Final success indicator
    print('🎉 HuggingFace setup completed successfully!')
    exit(0)
    
except Exception as e:
    print(f'❌ HuggingFace authentication failed: {{e}}')
    print('💡 Please check your token and try again')
    exit(1)
"
    
    # Check the exit code from Python script
    if [ $? -eq 0 ]; then
        clear
        echo "✅ 设置完成"
    else
        echo "❌ 设置失败"
        exit 1
    fi
else
    echo "⚠️  Python not available, skipping authentication test"
    echo "🎉 Token configured, but manual verification needed"
fi
"""
        
        # 3. 通过tkinter显示远端命令供用户执行
        if is_run_environment(command_identifier):
            return {
                "success": True,
                "message": "HuggingFace remote setup command generated",
                "remote_command": remote_setup_commands.strip(),
                "token_configured": True,
                "instructions": "Execute the remote_command in your remote terminal to set up HuggingFace credentials"
            }
        else:
            # 非RUN环境，显示tkinter窗口 - 参考_show_generic_command_window风格
            import tkinter as tk
            import queue
            
            result_queue = queue.Queue()
            
            def show_hf_setup_window():
                root = tk.Tk()
                root.title("🤗 HuggingFace 远程设置")
                root.geometry("400x60")
                root.resizable(False, False)
                
                # 居中窗口
                root.eval('tk::PlaceWindow . center')
                
                # 设置窗口置顶
                root.attributes('-topmost', True)
                
                # 自动复制命令到剪切板
                root.clipboard_clear()
                root.clipboard_append(remote_setup_commands.strip())
                
                # 主框架
                main_frame = tk.Frame(root, padx=10, pady=10)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # 按钮框架
                button_frame = tk.Frame(main_frame)
                button_frame.pack(fill=tk.X, expand=True)
                
                def copy_command():
                    try:
                        # 使用更可靠的复制方法
                        root.clipboard_clear()
                        root.clipboard_append(remote_setup_commands.strip())
                        
                        # 验证复制是否成功
                        try:
                            clipboard_content = root.clipboard_get()
                            if clipboard_content == remote_setup_commands.strip():
                                copy_btn.config(text="✅ 复制成功", bg="#4CAF50")
                            else:
                                # 复制不完整，重试一次
                                root.clipboard_clear()
                                root.clipboard_append(remote_setup_commands.strip())
                                copy_btn.config(text="⚠️ 已重试", bg="#FF9800")
                        except Exception:
                            # 验证失败但复制可能成功，显示已复制
                            copy_btn.config(text="✅ 已复制", bg="#4CAF50")
                        
                        root.after(1500, lambda: copy_btn.config(text="📋 复制指令", bg="#2196F3"))
                    except Exception as e:
                        print(f"复制到剪贴板失败: {e}")
                        copy_btn.config(text="❌ 复制失败", bg="#f44336")
                
                def setup_completed():
                    result_queue.put({"action": "success", "message": "用户确认设置完成"})
                    root.destroy()
                
                def direct_feedback():
                    """直接反馈功能 - 让用户提供设置执行结果"""
                    # 关闭主窗口
                    root.destroy()
                    
                    # 使用命令行输入获取用户反馈
                    print("\n" + "="*60)
                    print("🔄 HuggingFace 设置反馈")
                    print("="*60)
                    print("请提供远程HuggingFace设置的执行结果 (多行输入，按 Ctrl+D 结束):")
                    print("💡 提示: 直接粘贴命令的完整输出即可")
                    print()
                    
                    # 获取统一的命令输出
                    try:
                        output_lines = []
                        while True:
                            try:
                                line = input()
                                output_lines.append(line)
                            except EOFError:
                                break
                        full_output = '\n'.join(output_lines)
                    except KeyboardInterrupt:
                        print("\n用户取消输入")
                        full_output = ""
                    
                    # 分析输出判断是否成功
                    success_indicators = ['HuggingFace setup completed successfully', '✅', 'All tests passed']
                    error_indicators = ['❌', 'failed', 'error', 'Error', 'ERROR', 'exception']
                    
                    has_success = any(indicator in full_output for indicator in success_indicators)
                    has_error = any(indicator in full_output for indicator in error_indicators)
                    
                    if has_success and not has_error:
                        print()
                        print("="*60)
                        print("✅ HuggingFace 设置成功！")
                        print("="*60)
                        success = True
                    elif has_error:
                        print()
                        print("="*60)
                        print("❌ HuggingFace 设置失败")
                        print("="*60)
                        success = False
                    else:
                        print()
                        print("="*60)
                        print("⚠️  设置状态不明确，请手动验证")
                        print("="*60)
                        success = None
                    
                    # 构建反馈结果
                    feedback_result = {
                        "action": "direct_feedback",
                        "success": success,
                        "output": full_output,
                        "message": "HuggingFace设置反馈已收集"
                    }
                    result_queue.put(feedback_result)
                
                # 复制指令按钮
                copy_btn = tk.Button(
                    button_frame, 
                    text="📋 复制指令", 
                    command=copy_command,
                    font=("Arial", 9),
                    bg="#2196F3",
                    fg="white",
                    padx=10,
                    pady=5,
                    relief=tk.RAISED,
                    bd=2
                )
                copy_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
                
                # 直接反馈按钮
                feedback_btn = tk.Button(
                    button_frame, 
                    text="💬 直接反馈", 
                    command=direct_feedback,
                    font=("Arial", 9),
                    bg="#FF9800",
                    fg="white",
                    padx=10,
                    pady=5,
                    relief=tk.RAISED,
                    bd=2
                )
                feedback_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
                
                # 设置完成按钮
                complete_btn = tk.Button(
                    button_frame, 
                    text="✅ 设置完成", 
                    command=setup_completed,
                    font=("Arial", 9, "bold"),
                    bg="#4CAF50",
                    fg="white",
                    padx=10,
                    pady=5,
                    relief=tk.RAISED,
                    bd=2
                )
                complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # 设置焦点到完成按钮
                complete_btn.focus_set()
                
                # 自动复制命令到剪贴板
                copy_command()
                
                root.mainloop()
            
            # 显示窗口
            show_hf_setup_window()
            
            # 获取结果
            try:
                result = result_queue.get_nowait()
                return {
                    "success": True,
                    "message": "HuggingFace remote setup completed",
                    "token_configured": True,
                    "user_action": result
                }
            except queue.Empty:
                return {
                    "success": True,
                    "message": "HuggingFace remote setup window closed",
                    "token_configured": True
                }
            
    except Exception as e:
        return {"success": False, "error": f"Failed to setup remote HF credentials: {str(e)}"}

def test_remote_hf_setup(command_identifier=None):
    """
    测试远端HuggingFace配置
    
    Args:
        command_identifier (str): 命令标识符
        
    Returns:
        dict: 测试结果
    """
    try:
        # 生成远端测试命令
        test_command = """
# Test HuggingFace Configuration
echo "🧪 Testing HuggingFace Configuration..."

# Check environment variables
echo "Environment Variables:"
echo "  HF_TOKEN: ${HF_TOKEN:0:8}..."
echo "  HUGGINGFACE_HUB_TOKEN: ${HUGGINGFACE_HUB_TOKEN:0:8}..."

# Check token file
if [ -f ~/.cache/huggingface/token ]; then
    token_content=$(cat ~/.cache/huggingface/token)
    echo "  Token file: ✅ Exists (${#token_content} chars)"
else
    echo "  Token file: ❌ Missing"
fi

# Test Python integration
if command -v python3 >/dev/null 2>&1; then
    echo "Python HuggingFace Test:"
    python3 -c "
try:
    import huggingface_hub
    from huggingface_hub import HfApi
    
    api = HfApi()
    user_info = api.whoami()
    print(f'  Authentication: ✅ Success')
    print(f'  Username: {user_info.get(\"name\", \"Unknown\")}')
    print(f'  Email: {user_info.get(\"email\", \"Unknown\")}')
    
    # Test model access
    model_info = api.model_info('bert-base-uncased')
    print(f'  Model Access: ✅ Can access public models')
    
except ImportError:
    print('  HuggingFace Hub: ❌ Not installed')
    print('  Run: pip install huggingface_hub')
except Exception as e:
    print(f'  Authentication: ❌ Failed - {e}')
"
else
    echo "Python: ❌ Not available"
fi

echo "🏁 HuggingFace configuration test completed"
"""
        
        if is_run_environment(command_identifier):
            return {
                "success": True,
                "message": "HuggingFace test command generated",
                "test_command": test_command.strip(),
                "instructions": "Execute the test_command in your remote terminal to verify HuggingFace setup"
            }
        else:
            # 使用GDS执行测试命令
            result = handle_shell_command(f'bash -c "{test_command}"', command_identifier)
            return result
            
    except Exception as e:
        return {"success": False, "error": f"Failed to test remote HF setup: {str(e)}"}

if __name__ == "__main__":
    sys.exit(main()) 