#!/usr/bin/env python3
"""
Google Drive - Drive Api Service Module
从GOOGLE_DRIVE.py重构而来的drive_api_service模块
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

# 导入Google Drive Shell管理类
try:
    # from google_drive_shell import GoogleDriveShell
    pass
except ImportError as e:
    print(f"Error: Import Google Drive Shell failed: {e}")
    GoogleDriveShell = None

# 导入is_run_environment函数
try:
    # is_run_environment现在在remote_commands中，但这里我们直接实现一个简单版本
    def is_run_environment(command_identifier=None):
        """Check if running in RUN environment by checking environment variables"""
        if command_identifier:
            return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
        return False
except ImportError:
    try:
        from core_utils import is_run_environment
    except ImportError:
        def is_run_environment(command_identifier=None):
            """Fallback is_run_environment function"""
            return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True' if command_identifier else False

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
        print(f"Extract folder ID failed: {e}")
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
        print(f"Test folder access failed: {e}")
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
                print(f"Error: Failed to open browser for {url}")
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
            print(f"Error: Error opening Google Drive: {e}")
        return 1

def test_drive_service():
    """测试Google Drive服务"""
    try:
        print(f"Testing Google Drive API连接...")
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 测试连接
        result = drive_service.test_connection()
        
        if result['success']:
            print(f"API connection test successful")
            print(f"Service account email: {result.get('user_email', 'Unknown')}")
            print(f"User name: {result.get('user_name', 'Unknown')}")
            
            # 测试列出文件
            print(f"\nTesting file list function...")
            files_result = drive_service.list_files(max_results=5)
            
            if files_result['success']:
                print(f"File list get successful! Found {files_result['count']} files")
                for file in files_result['files'][:3]:  # 显示前3个文件
                    print(f"{file['name']} ({file['mimeType']})")
            else:
                print(f"Error: File list get failed: {files_result['error']}")
            
            return True
        else:
            print(f"Error: API connection test failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"Error: Error during test: {e}")
        return False

def get_folder_path_from_api(folder_id):
    """使用API获取文件夹的完整路径"""
    try:
        # 动态导入API服务
        import sys
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
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
                print(f"Warning: Get folder info failed: {e}")
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
        print(f"Error: Error getting folder path: {e}")
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
        print(f"Error: Error converting URL to path: {e}")
        return None

def test_api_connection(command_identifier=None):
    """测试Google Drive API连接"""
    try:
        # 导入API服务
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "Error: API service file not found, please run GOOGLE_DRIVE --console-setup"
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
            success_msg = "Google Drive API connection test successful"
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
            error_msg = f"Error: API connection test failed: {result.stderr}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except subprocess.TimeoutExpired:
        timeout_msg = "⚠️ API test timeout"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": timeout_msg}, command_identifier)
        else:
            print(timeout_msg)
        return 1
    except Exception as e:
        error_msg = f"Error: Error testing API connection: {e}"
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
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "Error: API service file not found, please run GOOGLE_DRIVE --console-setup"
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
                    "message": f"Found {result['count']} files",
                    "files": result['files'],
                    "count": result['count']
                }, command_identifier)
            else:
                print(f"Google Drive file list (first {max_results} files):")
                print(f"-" * 50)
                for file in result['files']:
                    file_type = "📁" if file['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                    print(f"{file_type} {file['name']}")
                    print(f"ID: {file['id']}")
                    print(f"Type: {file['mimeType']}")
                    if 'size' in file:
                        print(f"Size: {file['size']} bytes")
                    print()
            return 0
        else:
            error_msg = f"Error: Listing files failed: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error: Error listing Drive files: {e}"
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
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "Error: API service file not found, please run GOOGLE_DRIVE --console-setup"
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
            success_msg = f"File download successful: {result['local_path']}"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": success_msg,
                    "local_path": result['local_path'],
                    "file_id": file_id
                }, command_identifier)
            else:
                print(success_msg)
                print(f"Local path: {result['local_path']}")
            return 0
        else:
            error_msg = f"Error: File download failed: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error: Error downloading file: {e}"
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
        api_service_path = Path(__file__).parent.parent / "google_drive_api.py"
        if not api_service_path.exists():
            error_msg = "Error: API service file not found, please run GOOGLE_DRIVE --console-setup"
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
            success_msg = f"File delete successful"
            if is_run_environment(command_identifier):
                write_to_json_output({
                    "success": True,
                    "message": success_msg,
                    "file_id": file_id
                }, command_identifier)
            else:
                print(success_msg)
                print(f"Deleted file ID: {file_id}")
            return 0
        else:
            error_msg = f"Error: File delete failed: {result['error']}"
            if is_run_environment(command_identifier):
                write_to_json_output({"success": False, "error": error_msg}, command_identifier)
            else:
                print(error_msg)
            return 1
            
    except Exception as e:
        error_msg = f"Error: Error deleting file: {e}"
        if is_run_environment(command_identifier):
            write_to_json_output({"success": False, "error": error_msg}, command_identifier)
        else:
            print(error_msg)
        return 1
