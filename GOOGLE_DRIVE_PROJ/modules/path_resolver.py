#!/usr/bin/env python3
"""
Google Drive Shell - Path Resolver Module
从google_drive_shell.py重构而来的path_resolver模块
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
try:
    from ..google_drive_api import GoogleDriveService
except ImportError:
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService

class PathResolver:
    """Google Drive Shell Path Resolver"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def _setup_environment_paths(self):
        """根据运行环境设置路径配置"""
        import os
        import platform
        import json
        
        # 尝试从配置文件加载设置
        try:
            config_file = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA" / "sync_config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                self.main_instance.LOCAL_EQUIVALENT = config.get("local_equivalent", "/Users/wukunhuan/Applications/Google Drive")
                self.main_instance.DRIVE_EQUIVALENT = config.get("drive_equivalent", "/content/drive/Othercomputers/我的 MacBook Air/Google Drive")
                self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID = config.get("drive_equivalent_folder_id", "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
                pass
            else:
                self._setup_default_paths()
        except Exception as e:
            print(f"⚠️ 加载同步配置失败，使用默认配置: {e}")
            self._setup_default_paths()
        
        if platform.system() == "Darwin":  # macOS
            self.environment = "macos"
            self.main_instance.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        else: 
            #TODO
            raise Exception("Unsupported environment")
        
        # 确保目录存在
        os.makedirs(self.main_instance.LOCAL_EQUIVALENT, exist_ok=True)
        # 只在Colab环境下创建DRIVE_REMOTE_ROOT目录
        if self.environment == "colab":
            os.makedirs(self.main_instance.REMOTE_ROOT, exist_ok=True)

    def _setup_default_paths(self):
        """设置默认路径配置"""
        import platform
        
        if platform.system() == "Darwin":  # macOS
            self.main_instance.LOCAL_EQUIVALENT = "/Users/wukunhuan/Applications/Google Drive"
            self.main_instance.DRIVE_EQUIVALENT = "/content/drive/Othercomputers/我的 MacBook Air/Google Drive"
        else:
            raise Exception("Not Implemented Yet")
        
        # 默认的DRIVE_EQUIVALENT_FOLDER_ID
        self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID = "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"

    def _expand_path(self, path):
        """展开路径，处理~等特殊字符"""
        try:
            import os
            return os.path.expanduser(os.path.expandvars(path))
        except Exception as e:
            print(f"路径展开失败: {e}")
            return path

    def _resolve_target_path_for_upload(self, target_path, current_shell=None):
        """
        解析上传目标路径的通用方法
        
        Args:
            target_path (str): 目标路径
            current_shell (dict, optional): 当前shell信息
            
        Returns:
            tuple: (target_folder_id, target_display_path) 或 (None, None) 如果解析失败
        """
        if current_shell is None:
            current_shell = self.main_instance.get_current_shell()
        
        if not current_shell:
            return None, None
            
        if self.drive_service:
            if target_path == ".":
                target_folder_id = self.main_instance.get_current_folder_id(current_shell)
                target_display_path = current_shell.get("current_path", "~")
            else:
                target_folder_id, target_display_path = self.main_instance.resolve_path(target_path, current_shell)
                if not target_folder_id:
                    return None, None
        else:
            # 没有API服务时的默认处理
            target_folder_id = self.main_instance.REMOTE_ROOT_FOLDER_ID
            target_display_path = target_path if target_path != "." else "~"
            
        return target_folder_id, target_display_path

    def resolve_path(self, path, current_shell=None):
        """解析路径，返回对应的Google Drive文件夹ID和逻辑路径"""
        if not self.drive_service:
            return None, None
        
        # 处理bash shell自动扩展的本地路径
        path = self._convert_local_path_to_remote(path)
            
        if not current_shell:
            current_shell = self.main_instance.get_current_shell()
            
        if not current_shell:
            return None, None
        
        try:
            current_path = current_shell.get("current_path", "~")
            current_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            
            # 处理特殊路径：DRIVE_EQUIVALENT
            if path == "@drive_equivalent" or path.startswith("@drive_equivalent/"):
                if path == "@drive_equivalent":
                    return self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, "@drive_equivalent"
                else:
                    # 处理@drive_equivalent下的子路径
                    relative_path = path[len("@drive_equivalent/"):]
                    return self._resolve_relative_path(relative_path, self.main_instance.DRIVE_EQUIVALENT_FOLDER_ID, "@drive_equivalent")
            
            # 处理绝对路径（基于REMOTE_ROOT）
            if path == "~":
                return self.main_instance.REMOTE_ROOT_FOLDER_ID, "~"
            elif path.startswith("~/"):
                relative_path = path[2:]
                return self._resolve_relative_path(relative_path, self.main_instance.REMOTE_ROOT_FOLDER_ID, "~")
            
            # 处理完整的绝对路径（如 /content/drive/MyDrive/REMOTE_ROOT/...）
            elif path.startswith("/content/drive/MyDrive/REMOTE_ROOT"):
                if path == "/content/drive/MyDrive/REMOTE_ROOT":
                    return self.main_instance.REMOTE_ROOT_FOLDER_ID, "~"
                elif path.startswith("/content/drive/MyDrive/REMOTE_ROOT/"):
                    relative_path = path[len("/content/drive/MyDrive/REMOTE_ROOT/"):]
                    return self._resolve_relative_path(relative_path, self.main_instance.REMOTE_ROOT_FOLDER_ID, "~")
                else:
                    return None, None
            
            # 处理REMOTE_ENV的绝对路径
            elif path.startswith("/content/drive/MyDrive/REMOTE_ENV"):
                if path == "/content/drive/MyDrive/REMOTE_ENV":
                    return self.main_instance.REMOTE_ENV_FOLDER_ID, "/content/drive/MyDrive/REMOTE_ENV"
                elif path.startswith("/content/drive/MyDrive/REMOTE_ENV/"):
                    relative_path = path[len("/content/drive/MyDrive/REMOTE_ENV/"):]
                    return self._resolve_relative_path(relative_path, self.main_instance.REMOTE_ENV_FOLDER_ID, "/content/drive/MyDrive/REMOTE_ENV")
                else:
                    return None, None
            
            # 处理相对路径
            elif path.startswith("./"):
                relative_path = path[2:]
                return self._resolve_relative_path(relative_path, current_folder_id, current_path)
            
            elif path == ".":
                return current_folder_id, current_path
            
            elif path == "..":
                return self._resolve_parent_directory(current_folder_id, current_path)
            
            elif path.startswith("../"):
                parent_id, parent_path = self._resolve_parent_directory(current_folder_id, current_path)
                if parent_id:
                    relative_path = path[3:]
                    return self._resolve_relative_path(relative_path, parent_id, parent_path)
                return None, None
            
            else:
                return self._resolve_relative_path(path, current_folder_id, current_path)
                
        except Exception as e:
            print(f"❌ 解析路径时出错: {e}")
            return None, None

    def _resolve_relative_path(self, relative_path, base_folder_id, base_path):
        """解析相对路径"""
        if not relative_path:
            return base_folder_id, base_path
        
        try:
            path_parts = relative_path.split("/")
            current_id = base_folder_id
            current_logical_path = base_path
            
            for part in path_parts:
                if not part:
                    continue
                
                files_result = self.drive_service.list_files(folder_id=current_id, max_results=100)
                if not files_result['success']:
                    return None, None
                
                found_folder = None
                for file in files_result['files']:
                    if file['name'] == part and file['mimeType'] == 'application/vnd.google-apps.folder':
                        found_folder = file
                        break
                
                if not found_folder:
                    return None, None
                
                current_id = found_folder['id']
                if current_logical_path == "~":
                    current_logical_path = f"~/{part}"
                else:
                    current_logical_path = f"{current_logical_path}/{part}"
            
            return current_id, current_logical_path
            
        except Exception as e:
            print(f"❌ 解析相对路径时出错: {e}")
            return None, None

    def _resolve_parent_directory(self, folder_id, current_path):
        """解析父目录"""
        if current_path == "~":
            return None, None
        
        try:
            folder_info = self.drive_service.service.files().get(
                fileId=folder_id,
                fields="parents"
            ).execute()
            
            parents = folder_info.get('parents', [])
            if not parents:
                return None, None
            
            parent_id = parents[0]
            
            if current_path.count('/') == 1:
                parent_path = "~"
            else:
                parent_path = '/'.join(current_path.split('/')[:-1])
            
            return parent_id, parent_path
            
        except Exception as e:
            print(f"❌ 解析父目录时出错: {e}")
            return None, None
    
    # Shell命令实现

    def _resolve_absolute_mkdir_path(self, path, current_shell, recursive=False):
        """解析mkdir路径为绝对路径"""
        try:
            # 获取当前路径
            current_path = current_shell.get("current_path", "~")
            
            if path.startswith("~"):
                # 以~开头，相对于REMOTE_ROOT
                if path == "~":
                    return self.main_instance.REMOTE_ROOT
                elif path.startswith("~/"):
                    return f"{self.main_instance.REMOTE_ROOT}/{path[2:]}"
                else:
                    return None
            elif path.startswith("/"):
                # 绝对路径
                return path
            elif path.startswith("./"):
                # 相对于当前目录
                if current_path == "~":
                    return f"{self.main_instance.REMOTE_ROOT}/{path[2:]}"
                else:
                    # 将当前GDS路径转换为绝对路径
                    abs_current = self._gds_path_to_absolute(current_path)
                    return f"{abs_current}/{path[2:]}"
            else:
                # 相对路径
                if current_path == "~":
                    return f"{self.main_instance.REMOTE_ROOT}/{path}"
                else:
                    # 将当前GDS路径转换为绝对路径
                    abs_current = self._gds_path_to_absolute(current_path)
                    return f"{abs_current}/{path}"
                    
        except Exception as e:
            print(f"❌ 解析mkdir路径时出错: {e}")
            return None

    def _gds_path_to_absolute(self, gds_path):
        """将GDS路径转换为绝对路径"""
        try:
            if gds_path == "~":
                return self.main_instance.REMOTE_ROOT
            elif gds_path.startswith("~/"):
                return f"{self.main_instance.REMOTE_ROOT}/{gds_path[2:]}"
            else:
                return gds_path
        except Exception as e:
            print(f"❌ 转换GDS路径时出错: {e}")
            return gds_path

    def _convert_local_path_to_remote(self, path):
        """
        将bash shell扩展的本地路径转换回远程路径格式
        
        当用户输入 'GDS cd ~/tmp/test' 时，bash会将 ~/tmp/test 扩展为 /Users/username/tmp/test
        这个函数将其转换回 ~/tmp/test 格式，以便正确解析为远程路径
        """
        try:
            import os
            
            # 获取用户的home目录
            home_dir = os.path.expanduser("~")
            
            # 如果路径以用户home目录开头，将其转换为~/格式
            if path.startswith(home_dir + "/"):
                relative_path = path[len(home_dir + "/"):]
                return f"~/{relative_path}"
            elif path == home_dir:
                return "~"
            else:
                # 不是home目录下的路径，保持原样
                # 这包括：相对路径、绝对的远程路径（如/content/drive/...）等
                return path
        except Exception as e:
            # 如果转换失败，返回原路径，避免破坏用户输入
            return path

    def resolve_remote_absolute_path(self, path, current_shell=None):
        """
        通用路径解析接口：将相对路径解析为远端绝对路径
        
        Args:
            path (str): 要解析的路径
            current_shell (dict): 当前shell状态，如果为None则自动获取
            
        Returns:
            str: 解析后的远端绝对路径
        """
        try:
            if not current_shell:
                current_shell = self.main_instance.get_current_shell()
                if not current_shell:
                    return path  # 如果没有shell，返回原路径
            
            # 如果已经是绝对路径（以/开头），直接返回
            if path.startswith("/"):
                return path
            
            # 获取当前路径和REMOTE_ROOT路径
            current_path = current_shell.get("current_path", "~")
            remote_root_path = self.main_instance.REMOTE_ROOT
            
            # 处理特殊路径
            if path == "~":
                return remote_root_path
            elif path.startswith("~/"):
                # ~/xxx 形式的绝对路径
                relative_part = path[2:]
                return f"{remote_root_path}/{relative_part}"
            elif path == ".":
                # 当前目录
                if current_path == "~":
                    return remote_root_path
                else:
                    current_relative = current_path[2:] if current_path.startswith("~/") else current_path
                    return f"{remote_root_path}/{current_relative}"
            else:
                # 相对路径，基于当前目录
                if current_path == "~":
                    return f"{remote_root_path}/{path}"
                else:
                    current_relative = current_path[2:] if current_path.startswith("~/") else current_path
                    return f"{remote_root_path}/{current_relative}/{path}"
            
        except Exception as e:
            # 如果解析失败，返回原路径
            return path
