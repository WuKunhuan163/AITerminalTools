#!/usr/bin/env python3
"""
Google Drive Shell Management (Refactored)
Google Drive远程Shell管理系统 - 重构版本
"""

import os
import sys
import json
import time
import hashlib
import warnings
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
import platform
import psutil
from typing import Dict
from google_drive_api import GoogleDriveService

# 导入重构后的模块
from .modules import (
    ShellManagement,
    FileOperations,
    CacheManager,
    RemoteCommands,
    PathResolver,
    SyncManager,
    FileUtils,
    Validation,
    Verification,
)

class GoogleDriveShell:
    """Google Drive Shell管理类 (重构版本)"""
    
    def __init__(self):
        """初始化Google Drive Shell"""
        self.shells_file = Path(__file__).parent / "shells.json"
        self.config_file = Path(__file__).parent / "cache_config.json"
        self.deletion_cache_file = Path(__file__).parent / "deletion_cache.json"  # 新增删除时间缓存文件
        
        # 初始化shell配置
        self.shells_data = self.load_shells()
        
        # 加载缓存配置
        self.load_cache_config()
        
        # 初始化删除时间缓存
        self.deletion_cache = self.load_deletion_cache()
        
        # 设置常量
        self.HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
        
        # 设置路径
        if self.cache_config_loaded:
            try:
                config = self.cache_config
                self.LOCAL_EQUIVALENT = config.get("local_equivalent", "/Users/wukunhuan/Applications/Google Drive")
                self.DRIVE_EQUIVALENT = config.get("drive_equivalent", "/content/drive/Othercomputers/我的 MacBook Air/Google Drive")
                self.DRIVE_EQUIVALENT_FOLDER_ID = config.get("drive_equivalent_folder_id", "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
                os.makedirs(self.LOCAL_EQUIVALENT, exist_ok=True)
                
                # 静默加载同步配置，不显示详细信息
                pass
            except Exception:
                raise Exception("配置加载失败")
        else:
            raise Exception("配置加载失败")
        
        # 确保所有必要的属性都存在
        if not hasattr(self, 'REMOTE_ROOT'):
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        if not hasattr(self, 'REMOTE_ROOT_FOLDER_ID'):
            self.REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"
        
        # 尝试加载Google Drive API服务
        self.drive_service = self.load_drive_service()

        # 初始化管理器
        self._initialize_managers()

    def _initialize_managers(self):
        """初始化各个管理器"""
        self.shell_management = ShellManagement(self.drive_service, self)
        self.file_operations = FileOperations(self.drive_service, self)
        self.cache_manager = CacheManager(self.drive_service, self)
        self.remote_commands = RemoteCommands(self.drive_service, self)
        self.path_resolver = PathResolver(self.drive_service, self)
        self.sync_manager = SyncManager(self.drive_service, self)
        self.file_utils = FileUtils(self.drive_service, self)
        self.validation = Validation(self.drive_service, self)
        self.verification = Verification(self.drive_service, self)
    
    def calculate_timeout_from_file_sizes(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.calculate_timeout_from_file_sizes(*args, **kwargs)
    
    def check_network_connection(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.check_network_connection(*args, **kwargs)
    
    def checkout_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.checkout_shell(*args, **kwargs)
    
    def cmd_cat(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_cat(*args, **kwargs)
    
    def cmd_cd(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_cd(*args, **kwargs)
    
    def cmd_download(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_download(*args, **kwargs)
    
    def cmd_echo(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_echo(*args, **kwargs)
    
    def cmd_edit(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_edit(*args, **kwargs)
    
    def cmd_find(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_find(*args, **kwargs)
    
    def cmd_grep(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_grep(*args, **kwargs)
    
    def cmd_ls(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_ls(*args, **kwargs)
    
    def cmd_mkdir(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_mkdir(*args, **kwargs)
    
    def cmd_mkdir_remote(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_mkdir_remote(*args, **kwargs)
    
    def cmd_mv(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_mv(*args, **kwargs)
    
    def cmd_mv_multi(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_mv_multi(*args, **kwargs)
    
    def cmd_pwd(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_pwd(*args, **kwargs)
    
    def cmd_python(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_python(*args, **kwargs)
    
    def cmd_read(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_read(*args, **kwargs)
    
    def cmd_rm(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_rm(*args, **kwargs)
    
    def cmd_upload(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_upload(*args, **kwargs)
    
    def cmd_upload_folder(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_upload_folder(*args, **kwargs)
    
    def cmd_upload_multi(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_upload_multi(*args, **kwargs)
    
    def create_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.create_shell(*args, **kwargs)
    
    def execute_generic_remote_command(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.execute_generic_remote_command(*args, **kwargs)
    
    def execute_remote_command_interface(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.execute_remote_command_interface(*args, **kwargs)
    
    def exit_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.exit_shell(*args, **kwargs)
    
    def generate_mkdir_commands(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.generate_mkdir_commands(*args, **kwargs)
    
    def generate_remote_commands(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.generate_remote_commands(*args, **kwargs)
    
    def generate_shell_id(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.generate_shell_id(*args, **kwargs)
    
    def get_current_folder_id(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.get_current_folder_id(*args, **kwargs)
    
    def get_current_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.get_current_shell(*args, **kwargs)
    
    def get_remote_file_modification_time(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.get_remote_file_modification_time(*args, **kwargs)
    
    def is_cached_file_up_to_date(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.is_cached_file_up_to_date(*args, **kwargs)
    
    def is_remote_file_cached(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.is_remote_file_cached(*args, **kwargs)
    
    def list_shells(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.list_shells(*args, **kwargs)
    
    def load_cache_config(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.load_cache_config(*args, **kwargs)
    
    def load_deletion_cache(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.load_deletion_cache(*args, **kwargs)
    
    def load_shells(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.load_shells(*args, **kwargs)
    
    def move_to_local_equivalent(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.move_to_local_equivalent(*args, **kwargs)
    
    def resolve_path(self, *args, **kwargs):
        """委托到path_resolver管理器"""
        return self.path_resolver.resolve_path(*args, **kwargs)
    
    def resolve_remote_absolute_path(self, *args, **kwargs):
        """委托到path_resolver管理器"""
        return self.path_resolver.resolve_remote_absolute_path(*args, **kwargs)
    
    def save_deletion_cache(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.save_deletion_cache(*args, **kwargs)
    
    def save_shells(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.save_shells(*args, **kwargs)
    
    def show_remote_command_window(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.show_remote_command_window(*args, **kwargs)
    
    def terminate_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.terminate_shell(*args, **kwargs)
    
    def verify_upload_success(self, *args, **kwargs):
        """委托到validation管理器"""
        return self.validation.verify_upload_success(*args, **kwargs)
    
    def wait_for_file_sync(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.wait_for_file_sync(*args, **kwargs)
    