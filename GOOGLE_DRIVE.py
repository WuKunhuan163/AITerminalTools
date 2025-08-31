#!/usr/bin/env python3
"""
Google Drive Main Management (Refactored with Delegation Pattern)
Google Drive主管理系统 - 使用委托模式重构版本
模仿google_drive_shell.py的委托模式架构
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

# 设置模块搜索路径
current_dir = Path(__file__).parent
google_drive_proj_dir = current_dir / "GOOGLE_DRIVE_PROJ"
google_drive_data_dir = current_dir / "GOOGLE_DRIVE_DATA"

# 确保数据目录存在
google_drive_data_dir.mkdir(exist_ok=True)
(google_drive_data_dir / "remote_files").mkdir(exist_ok=True)

if str(google_drive_proj_dir) not in sys.path:
    sys.path.insert(0, str(google_drive_proj_dir))

# 导入重构后的管理器模块
try:
    from modules import (
        CoreUtils,
        DriveProcessManager,
        SyncConfigManager,
        SetupWizard,
        RemoteShellManager,
        DriveApiService,
        ShellCommands,
        HfCredentialsManager,
    )
except ImportError as e:
    print(f"❌ Manager module import failed: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")
    sys.exit(1)

# 全局常量
HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
HOME_FOLDER_ID = "root"  # Google Drive中My Drive的文件夹ID
REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"  # REMOTE_ROOT文件夹ID

class GoogleDriveMain:
    """Google Drive主管理类 (委托模式重构版本)"""
    
    def __init__(self):
        """初始化Google Drive主管理器"""
        # 从配置文件加载常量
        try:
            sys.path.insert(0, str(google_drive_proj_dir))
            from modules.config_loader import get_config
            config = get_config()
            self.HOME_URL = config.HOME_URL
            self.HOME_FOLDER_ID = config.HOME_FOLDER_ID
            self.REMOTE_ROOT_FOLDER_ID = config.REMOTE_ROOT_FOLDER_ID
            self.REMOTE_ROOT = config.REMOTE_ROOT
        except ImportError:
            # 降级使用硬编码常量
            self.HOME_URL = HOME_URL
            self.HOME_FOLDER_ID = HOME_FOLDER_ID
            self.REMOTE_ROOT_FOLDER_ID = REMOTE_ROOT_FOLDER_ID
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        
        # 初始化管理器
        self._initialize_managers()
    
    def _initialize_managers(self):
        """初始化各个管理器"""
        self.core_utils = CoreUtils(None, self)
        self.drive_process_manager = DriveProcessManager(None, self)
        self.sync_config_manager = SyncConfigManager(None, self)
        self.remote_shell_manager = RemoteShellManager(None, self)
        self.drive_api_service = DriveApiService(None, self)
        self.shell_commands = ShellCommands(None, self)
        self.hf_credentials_manager = HfCredentialsManager(None, self)
    
    # 委托方法 - Core Utils
    def get_multiline_input_safe(self, *args, **kwargs):
        """委托到core_utils管理器"""
        return self.core_utils.get_multiline_input_safe(*args, **kwargs)
    
    def is_run_environment(self, *args, **kwargs):
        """委托到core_utils管理器"""
        return self.core_utils.is_run_environment(*args, **kwargs)
    
    def write_to_json_output(self, *args, **kwargs):
        """委托到core_utils管理器"""
        return self.core_utils.write_to_json_output(*args, **kwargs)
    
    def copy_to_clipboard(self, *args, **kwargs):
        """委托到core_utils管理器"""
        return self.core_utils.copy_to_clipboard(*args, **kwargs)
    
    def show_help(self, *args, **kwargs):
        """委托到core_utils管理器"""
        return self.core_utils.show_help(*args, **kwargs)
    
    def main(self, *args, **kwargs):
        """委托到core_utils管理器"""
        return self.core_utils.main(*args, **kwargs)
    
    # 委托方法 - Drive Process Manager
    def is_google_drive_running(self, *args, **kwargs):
        """委托到drive_process_manager管理器"""
        return self.drive_process_manager.is_google_drive_running(*args, **kwargs)
    
    def get_google_drive_processes(self, *args, **kwargs):
        """委托到drive_process_manager管理器"""
        return self.drive_process_manager.get_google_drive_processes(*args, **kwargs)
    
    def shutdown_google_drive(self, *args, **kwargs):
        """委托到drive_process_manager管理器"""
        return self.drive_process_manager.shutdown_google_drive(*args, **kwargs)
    
    def launch_google_drive(self, *args, **kwargs):
        """委托到drive_process_manager管理器"""
        return self.drive_process_manager.launch_google_drive(*args, **kwargs)
    
    def restart_google_drive(self, *args, **kwargs):
        """委托到drive_process_manager管理器"""
        return self.drive_process_manager.restart_google_drive(*args, **kwargs)
    
    # 委托方法 - Sync Config Manager  
    def get_sync_config_file(self, *args, **kwargs):
        """委托到sync_config_manager管理器"""
        return self.sync_config_manager.get_sync_config_file(*args, **kwargs)
    
    def load_sync_config(self, *args, **kwargs):
        """委托到sync_config_manager管理器"""
        return self.sync_config_manager.load_sync_config(*args, **kwargs)
    
    def save_sync_config(self, *args, **kwargs):
        """委托到sync_config_manager管理器"""
        return self.sync_config_manager.save_sync_config(*args, **kwargs)
    
    def set_local_sync_dir(self, *args, **kwargs):
        """委托到sync_config_manager管理器"""
        return self.sync_config_manager.set_local_sync_dir(*args, **kwargs)
    
    def set_global_sync_dir(self, *args, **kwargs):
        """委托到sync_config_manager管理器"""
        return self.sync_config_manager.set_global_sync_dir(*args, **kwargs)
    
    def get_google_drive_status(self, *args, **kwargs):
        """委托到sync_config_manager管理器"""
        return self.sync_config_manager.get_google_drive_status(*args, **kwargs)
    
    # 委托方法 - Remote Shell Manager
    def create_remote_shell(self, *args, **kwargs):
        """委托到remote_shell_manager管理器"""
        return self.remote_shell_manager.create_remote_shell(*args, **kwargs)
    
    def list_remote_shells(self, *args, **kwargs):
        """委托到remote_shell_manager管理器"""
        return self.remote_shell_manager.list_remote_shells(*args, **kwargs)
    
    def checkout_remote_shell(self, *args, **kwargs):
        """委托到remote_shell_manager管理器"""
        return self.remote_shell_manager.checkout_remote_shell(*args, **kwargs)
    
    def terminate_remote_shell(self, *args, **kwargs):
        """委托到remote_shell_manager管理器"""
        return self.remote_shell_manager.terminate_remote_shell(*args, **kwargs)
    
    def enter_shell_mode(self, *args, **kwargs):
        """委托到remote_shell_manager管理器"""
        return self.remote_shell_manager.enter_shell_mode(*args, **kwargs)
    
    # 委托方法 - Drive API Service
    def open_google_drive(self, *args, **kwargs):
        """委托到drive_api_service管理器"""
        return self.drive_api_service.open_google_drive(*args, **kwargs)
    
    def test_api_connection(self, *args, **kwargs):
        """委托到drive_api_service管理器"""
        return self.drive_api_service.test_api_connection(*args, **kwargs)
    
    def list_drive_files(self, *args, **kwargs):
        """委托到drive_api_service管理器"""
        return self.drive_api_service.list_drive_files(*args, **kwargs)
    
    def shell_cd(self, *args, **kwargs):
        """委托到shell_commands管理器"""
        return self.shell_commands.shell_cd(*args, **kwargs)
    
    def shell_mkdir(self, *args, **kwargs):
        """委托到shell_commands管理器"""
        return self.shell_commands.shell_mkdir(*args, **kwargs)
    
    def shell_pwd(self, *args, **kwargs):
        """委托到shell_commands管理器"""
        return self.shell_commands.shell_pwd(*args, **kwargs)
    
    def handle_shell_command(self, *args, **kwargs):
        """委托到shell_commands管理器"""
        return self.shell_commands.handle_shell_command(*args, **kwargs)
    
    # 委托方法 - HF Credentials Manager
    def setup_remote_hf_credentials(self, *args, **kwargs):
        """委托到hf_credentials_manager管理器"""
        return self.hf_credentials_manager.setup_remote_hf_credentials(*args, **kwargs)
    
    def test_remote_hf_setup(self, *args, **kwargs):
        """委托到hf_credentials_manager管理器"""
        return self.hf_credentials_manager.test_remote_hf_setup(*args, **kwargs)

# 创建全局实例
google_drive_main = GoogleDriveMain()

# 将所有委托方法暴露为模块级函数，保持原有API兼容性
def get_multiline_input_safe(*args, **kwargs):
    return google_drive_main.get_multiline_input_safe(*args, **kwargs)

def is_run_environment(*args, **kwargs):
    return google_drive_main.is_run_environment(*args, **kwargs)

def write_to_json_output(*args, **kwargs):
    return google_drive_main.write_to_json_output(*args, **kwargs)

def copy_to_clipboard(*args, **kwargs):
    return google_drive_main.copy_to_clipboard(*args, **kwargs)

def show_help(*args, **kwargs):
    return google_drive_main.show_help(*args, **kwargs)

def main(*args, **kwargs):
    return google_drive_main.main(*args, **kwargs)

def is_google_drive_running(*args, **kwargs):
    return google_drive_main.is_google_drive_running(*args, **kwargs)

def get_google_drive_processes(*args, **kwargs):
    return google_drive_main.get_google_drive_processes(*args, **kwargs)

def shutdown_google_drive(*args, **kwargs):
    return google_drive_main.shutdown_google_drive(*args, **kwargs)

def launch_google_drive(*args, **kwargs):
    return google_drive_main.launch_google_drive(*args, **kwargs)

def restart_google_drive(*args, **kwargs):
    return google_drive_main.restart_google_drive(*args, **kwargs)

def get_google_drive_status(*args, **kwargs):
    return google_drive_main.get_google_drive_status(*args, **kwargs)

def open_google_drive(*args, **kwargs):
    return google_drive_main.open_google_drive(*args, **kwargs)

def handle_shell_command(*args, **kwargs):
    return google_drive_main.handle_shell_command(*args, **kwargs)

# 保持原有的main函数调用结构
if __name__ == "__main__":
    import sys
    sys.exit(main()) 