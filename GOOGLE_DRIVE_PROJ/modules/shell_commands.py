#!/usr/bin/env python3
"""
Google Drive - Shell Commands Module
从GOOGLE_DRIVE.py重构而来的shell_commands模块
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

# GoogleDriveShell will be imported when needed to avoid circular import

# 导入需要的函数
try:
    from .remote_commands import HOME_URL
except ImportError:
    HOME_URL = "https://drive.google.com/drive/u/0/my-drive"

# 使用统一的shell管理系统
def get_current_shell():
    """获取当前shell，使用统一的GoogleDriveShell实例"""
    try:
        # 动态导入避免循环导入
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from google_drive_shell import GoogleDriveShell
        
        shell = GoogleDriveShell()
        return shell.get_current_shell()
    except Exception as e:
        print(f"Failed to get current shell: {e}")
        return None

# 导入Google Drive Shell管理类 - 注释掉避免循环导入
# try:
#     from google_drive_shell import GoogleDriveShell
# except ImportError as e:
#     print(f"Failed to import Google Drive Shell: {e}")
#     GoogleDriveShell = None

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
    except Exception as e:
        print(f"写入JSON输出文件失败: {e}")
        return False

# 全局常量
HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
HOME_FOLDER_ID = "root"  # Google Drive中My Drive的文件夹ID
REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"  # REMOTE_ROOT文件夹ID

def shell_ls(path=None, command_identifier=None):
    """列出指定路径或当前路径的文件和文件夹"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "No active remote shell, please create or switch to a shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 确定要列出的文件夹ID
        if path is None or path == ".":
            # 列出当前目录
            target_folder_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
            display_path = current_shell.get("current_path", "~")
        elif path == "~":
            # 列出根目录
            target_folder_id = REMOTE_ROOT_FOLDER_ID
            display_path = "~"
        else:
            # 实现基本路径解析，支持文件路径
            try:
                # 首先尝试作为目录解析
                target_folder_id, display_path = resolve_path(path, current_shell)
                
                if not target_folder_id:
                    # 如果作为目录解析失败，尝试作为文件路径解析
                    file_info = resolve_file_path(path, current_shell)
                    if file_info:
                        # 这是一个文件路径，直接显示文件信息
                        if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                            print(f"{file_info['name']}/")
                        else:
                            print(f"{file_info['name']}")
                        
                        if is_run_environment(command_identifier):
                            write_to_json_output({
                                "success": True,
                                "path": path,
                                "files": [file_info] if file_info['mimeType'] != 'application/vnd.google-apps.folder' else [],
                                "folders": [file_info] if file_info['mimeType'] == 'application/vnd.google-apps.folder' else [],
                                "count": 1
                            }, command_identifier)
                        return 0
                    else:
                        error_msg = f"Path not found: {path}"
                        if is_run_environment(command_identifier):
                            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                        else:
                            print(error_msg)
                        return 1
            except Exception as e:
                error_msg = f"Path resolution failed: {path} ({e})"
                if is_run_environment(command_identifier):
                    write_to_json_output({"success": False, "error": error_msg}, command_identifier)
                else:
                    print(error_msg)
                return 1
        
        # 使用API列出文件
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "API service file not found, please run GOOGLE_DRIVE --console-setup"
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
            error_msg = f"Failed to list files: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing ls command: {e}"
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
        print(f"Error resolving path: {e}")
        return None, None

def resolve_relative_path(relative_path, base_folder_id, base_path):
    """解析相对路径"""
    try:
        if not relative_path:
            return base_folder_id, base_path
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
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
        print(f"Error resolving relative path: {e}")
        return None, None

def resolve_file_path(file_path, current_shell):
    """解析文件路径，返回文件信息（如果存在）"""
    try:
        # 分离目录和文件名
        if "/" in file_path:
            dir_path = "/".join(file_path.split("/")[:-1])
            filename = file_path.split("/")[-1]
        else:
            # 相对于当前目录
            dir_path = "."
            filename = file_path
        
        # 解析目录路径
        if dir_path == ".":
            parent_folder_id = current_shell.get("current_folder_id", REMOTE_ROOT_FOLDER_ID)
        else:
            parent_folder_id, _ = resolve_path(dir_path, current_shell)
            if not parent_folder_id:
                return None
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            return None
        
        sys.path.insert(0, str(api_service_path.parent))
        from google_drive_api import GoogleDriveService #type: ignore
        
        drive_service = GoogleDriveService()
        
        # 在父目录中查找文件
        result = drive_service.list_files(folder_id=parent_folder_id, max_results=100)
        if not result['success']:
            return None
        
        for file in result['files']:
            if file['name'] == filename:
                return file
        
        return None
        
    except Exception as e:
        print(f"Error resolving file path: {e}")
        return None
        
def resolve_parent_directory(folder_id, current_path):
    """解析父目录"""
    try:
        if current_path == "~":
            return None, None  # 已经在根目录
        
        # 导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
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
        print(f"Error resolving parent directory: {e}")
        return None, None



def shell_cd(path, command_identifier=None):
    """切换目录"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "No active remote shell, please create or switch to a shell"
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
            error_msg = f"Directory not found: {path}"
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
            success_msg = f"Switched to directory: {target_path}"
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
            error_msg = "Failed to save shell state"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing cd command: {e}"
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
            error_msg = "No active remote shell, please create or switch to a shell"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        if not path:
            error_msg = "Please specify the file or directory to delete"
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
                error_msg = f"Parent directory not found: {parent_path}"
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
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "API service file not found, please run GOOGLE_DRIVE --console-setup"
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
            error_msg = f"Failed to access directory: {files_result['error']}"
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
            error_msg = f"File or directory does not exist"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 检查是否为目录且没有使用递归标志
        is_folder = target_item['mimeType'] == 'application/vnd.google-apps.folder'
        if is_folder and not recursive:
            error_msg = f"Cannot delete directory '{item_name}': use rm -rf"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 删除项目
        result = drive_service.delete_file(target_item['id'])
        
        if result['success']:
            item_type = "directory" if is_folder else "file"
            success_msg = f"\nSuccessfully deleted {item_type}: {item_name}"
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
            error_msg = f"Failed to delete: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing rm command: {e}"
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
            error_msg = f"Directory not found: {path}"
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
            success_msg = f"Created shell and opened directory: {target_path}"
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
            error_msg = "Failed to save shell configuration"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing open-dir command: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def shell_pwd(command_identifier=None):
    """显示当前远程逻辑地址"""
    try:
        current_shell = get_current_shell()
        
        if not current_shell:
            error_msg = "No active remote shell, please create or switch to a shell"
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
            print(current_path)
        
        return 0
        
    except Exception as e:
        error_msg = f"Error getting current path: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1

def shell_help(command_identifier=None):
    """显示帮助信息"""
    help_text = """pwd                         - show current directory
ls [path] [--detailed] [-R] - list directory contents (recursive with -R)
mkdir [-p] <dir>             - create directory (recursive with -p)
touch <file>                 - create empty file
cd <path>                    - change directory
rm <file>                    - remove file
rm -rf <dir>                 - remove directory recursively
echo <text>                  - display text
echo <text> > <file>         - create file with text
cat <file>                   - display file contents
grep <pattern> <file>        - search for pattern in file
python <file>                - execute python file
python -c '<code>'           - execute python code
download [--force] <file> [path] - download file with caching
read <file> [start end]      - read file content with line numbers
find [path] -name [pattern]  - search for files matching pattern
mv <source> <dest>           - move/rename file or folder
edit [--preview] [--backup] <file> '<spec>' - edit file with multi-segment replacement
upload [--target-dir TARGET] <files...> - upload files to Google Drive (default: current directory)
upload-folder [--keep-zip] <folder> [target] - upload folder (zip->upload->unzip->cleanup)
venv --create <env_name...>  - create virtual environment(s) (supports multiple names)
venv --delete <env_name...>  - delete virtual environment(s) (supports multiple names, protects GaussianObject)
venv --activate <env_name>   - activate virtual environment (set PYTHONPATH)
venv --deactivate           - deactivate virtual environment (clear PYTHONPATH)
venv --list                 - list all virtual environments
pip <command> [options]      - pip package manager (auto-targets active venv)"""
    
    if is_run_environment(command_identifier):
        write_to_json_output({"success": True, "help": help_text}, command_identifier)
    else:
        print(help_text)
    
    return 0

def handle_pipe_commands(shell_cmd, command_identifier=None):
    """处理用|连接的pipe命令"""
    try:
        # 解析pipe命令：支持 | 操作符
        pipe_parts = shell_cmd.split(' | ')
        if len(pipe_parts) < 2:
            # 不是pipe命令，不应该到这里
            return handle_single_command(shell_cmd, command_identifier)
        
        # 获取GoogleDriveShell实例来执行命令
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
        except Exception as e:
            error_msg = f"Failed to get GoogleDriveShell instance: {e}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 执行pipe命令链
        if not is_run_environment(command_identifier):
            print(f"Executing pipe command chain: {shell_cmd}")
        
        previous_output = ""
        final_result = 0
        
        for i, cmd_part in enumerate(pipe_parts):
            cmd_part = cmd_part.strip()
            
            if not is_run_environment(command_identifier):
                print(f"\n- Executing command {i+1}/{len(pipe_parts)}: {cmd_part}")
            
            # 如果不是第一个命令，将上一个命令的输出作为输入
            if i > 0:
                # 对于pipe命令，我们需要特殊处理
                # 这里简化实现：将前一个命令的输出作为当前命令的输入参数
                if cmd_part.startswith('grep ') or cmd_part.startswith('head ') or cmd_part.startswith('tail ') or cmd_part.startswith('sort') or cmd_part.startswith('uniq'):
                    # 对于这些常见的pipe命令，我们模拟其行为
                    final_result = _execute_pipe_command(cmd_part, previous_output, shell, command_identifier)
                    if final_result != 0:
                        break
                else:
                    # 对于其他命令，直接执行
                    final_result = shell.execute_shell_command(cmd_part, command_identifier)
                    if final_result != 0:
                        break
            else:
                # 第一个命令，正常执行并捕获输出
                import io
                import contextlib
                from contextlib import redirect_stdout
                
                # 捕获第一个命令的输出
                output_buffer = io.StringIO()
                try:
                    with redirect_stdout(output_buffer):
                        final_result = shell.execute_shell_command(cmd_part, command_identifier)
                    previous_output = output_buffer.getvalue()
                except Exception as e:
                    if not is_run_environment(command_identifier):
                        print(f"Error capturing output from command '{cmd_part}': {e}")
                    final_result = 1
                    break
        
        return final_result
        
    except Exception as e:
        error_msg = f"Error executing pipe commands: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"{error_msg}")
        return 1

def _execute_pipe_command(cmd, input_text, shell, command_identifier=None):
    """执行pipe命令的具体实现"""
    try:
        cmd_parts = cmd.split()
        if not cmd_parts:
            return 1
            
        cmd_name = cmd_parts[0]
        
        if cmd_name == 'grep':
            # 实现简单的grep功能
            if len(cmd_parts) < 2:
                if not is_run_environment(command_identifier):
                    print("grep: missing pattern")
                return 1
            
            pattern = cmd_parts[1]
            lines = input_text.split('\n')
            matched_lines = [line for line in lines if pattern in line]
            
            if not is_run_environment(command_identifier):
                for line in matched_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'head':
            # 实现简单的head功能
            n_lines = 10  # 默认显示10行
            if len(cmd_parts) >= 3 and cmd_parts[1] == '-n':
                try:
                    n_lines = int(cmd_parts[2])
                except ValueError:
                    n_lines = 10
            elif len(cmd_parts) >= 2 and cmd_parts[1].startswith('-'):
                try:
                    n_lines = int(cmd_parts[1][1:])
                except ValueError:
                    n_lines = 10
            
            lines = input_text.split('\n')
            head_lines = lines[:n_lines]
            
            if not is_run_environment(command_identifier):
                for line in head_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'tail':
            # 实现简单的tail功能
            n_lines = 10  # 默认显示10行
            if len(cmd_parts) >= 3 and cmd_parts[1] == '-n':
                try:
                    n_lines = int(cmd_parts[2])
                except ValueError:
                    n_lines = 10
            elif len(cmd_parts) >= 2 and cmd_parts[1].startswith('-'):
                try:
                    n_lines = int(cmd_parts[1][1:])
                except ValueError:
                    n_lines = 10
            
            lines = input_text.split('\n')
            tail_lines = lines[-n_lines:] if len(lines) >= n_lines else lines
            
            if not is_run_environment(command_identifier):
                for line in tail_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'sort':
            # 实现简单的sort功能
            lines = input_text.split('\n')
            sorted_lines = sorted(lines)
            
            if not is_run_environment(command_identifier):
                for line in sorted_lines:
                    print(line)
            return 0
            
        elif cmd_name == 'uniq':
            # 实现简单的uniq功能
            lines = input_text.split('\n')
            unique_lines = []
            for line in lines:
                if not unique_lines or unique_lines[-1] != line:
                    unique_lines.append(line)
            
            if not is_run_environment(command_identifier):
                for line in unique_lines:
                    print(line)
            return 0
        else:
            # 不支持的pipe命令
            if not is_run_environment(command_identifier):
                print(f"Pipe command '{cmd_name}' not supported")
            return 1
            
    except Exception as e:
        if not is_run_environment(command_identifier):
            print(f"Error executing pipe command '{cmd}': {e}")
        return 1

def handle_single_command(shell_cmd, command_identifier=None):
    """处理单个命令"""
    try:
        # 获取GoogleDriveShell实例来执行命令
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
        except Exception as e:
            error_msg = f"Failed to get GoogleDriveShell instance: {e}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        return shell.execute_shell_command(shell_cmd, command_identifier)
        
    except Exception as e:
        error_msg = f"Error executing command: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"{error_msg}")
        return 1

def handle_multiple_commands(shell_cmd, command_identifier=None):
    """处理多个用&&、||或|连接的shell命令"""
    try:
        # 首先检查是否包含pipe操作符
        if ' | ' in shell_cmd:
            return handle_pipe_commands(shell_cmd, command_identifier)
        
        # 解析命令：支持 && 和 || 操作符
        commands_with_operators = []
        
        # 先按 || 分割，然后再按 && 分割
        if ' || ' in shell_cmd:
            # 包含 || 操作符
            or_parts = shell_cmd.split(' || ')
            for i, part in enumerate(or_parts):
                if ' && ' in part:
                    # 这部分包含 && 操作符
                    and_parts = part.split(' && ')
                    for j, and_part in enumerate(and_parts):
                        operator = '&&' if j > 0 else ('||' if i > 0 else None)
                        commands_with_operators.append((and_part.strip(), operator))
                else:
                    operator = '||' if i > 0 else None
                    commands_with_operators.append((part.strip(), operator))
        elif ' && ' in shell_cmd:
            # 只包含 && 操作符
            and_parts = shell_cmd.split(' && ')
            for i, part in enumerate(and_parts):
                operator = '&&' if i > 0 else None
                commands_with_operators.append((part.strip(), operator))
        else:
            # 单个命令，不应该到这里，但为了安全起见
            commands_with_operators.append((shell_cmd.strip(), None))
        
        # 获取GoogleDriveShell实例来执行命令
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
        except Exception as e:
            error_msg = f"Failed to get GoogleDriveShell instance: {e}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
        
        # 执行命令
        results = []
        last_result = 0
        
        for i, (cmd, operator) in enumerate(commands_with_operators):
            if not cmd:
                continue
            
            # 根据操作符决定是否执行当前命令
            should_execute = True
            
            if operator == '&&':
                # && 操作符：只有前一个命令成功才执行
                should_execute = (last_result == 0)
            elif operator == '||':
                # || 操作符：只有前一个命令失败才执行
                should_execute = (last_result != 0)
            
            if should_execute:
                if not is_run_environment(command_identifier):
                    print(f"\n- Executing command {i+1}/{len(commands_with_operators)}: {cmd}")
                
                # 通过GoogleDriveShell执行单个命令
                try:
                    result = shell.execute_shell_command(cmd, command_identifier)
                    
                    # 处理返回结果
                    if isinstance(result, dict):
                        if result.get("success", True):
                            last_result = 0
                        else:
                            last_result = 1
                    elif isinstance(result, int):
                        last_result = result
                    else:
                        # 默认认为成功
                        last_result = 0
                        
                except Exception as e:
                    if not is_run_environment(command_identifier):
                        print(f"Error executing command: {e}")
                    last_result = 1
            else:
                # 跳过命令
                if not is_run_environment(command_identifier):
                    if operator == '&&':
                        print(f"\n- Skipped command {i+1}/{len(commands_with_operators)} (previous command failed): {cmd}")
                    elif operator == '||':
                        print(f"\n- Skipped command {i+1}/{len(commands_with_operators)} (previous command succeeded): {cmd}")
            
            results.append(last_result)
        
        # 返回最后一个命令的结果
        final_result = last_result if results else 0
        return final_result
        
    except Exception as e:
        error_msg = f"Error executing multiple commands: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(f"{error_msg}")
        return 1

def shell_ls_with_id(folder_id, detailed=False, command_identifier=None):
    """列出指定文件夹ID的文件和文件夹"""
    try:
        # 使用API列出文件
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "API service file not found, please run GOOGLE_DRIVE --console-setup"
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
            error_msg = f"Failed to list files: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error executing ls command: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1
