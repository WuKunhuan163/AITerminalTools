#!/usr/bin/env python3
"""
Google Drive Shell - Cache Manager Module
从google_drive_shell.py重构而来的cache_manager模块
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

class CacheManager:
    """Google Drive Shell Cache Manager"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def _get_local_cache_path(self, remote_path):
        """获取远程文件对应的本地缓存路径"""
        try:
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            # 获取文件的哈希值作为本地文件名
            file_hash = hashlib.md5(remote_path.encode()).hexdigest()[:16]
            local_path = cache_manager.remote_files_dir / file_hash
            
            if local_path.exists():
                return str(local_path)
            else:
                return file_hash  # 返回哈希文件名
        except Exception:
            # 如果无法获取缓存路径，返回简化的文件名
            return remote_path.split('/')[-1] if '/' in remote_path else remote_path

    def _cleanup_local_equivalent_files(self, file_moves):
        """
        清理LOCAL_EQUIVALENT中的文件（上传完成后）
        
        Args:
            file_moves (list): 文件移动信息列表
        """
        try:
            cleaned_files = []
            failed_cleanups = []
            
            for file_info in file_moves:
                filename = file_info["filename"]  # 实际的文件名（可能已重命名）
                file_path = Path(file_info["new_path"])
                
                try:
                    if file_path.exists():
                        file_path.unlink()
                        cleaned_files.append(filename)
                        # print(f"🧹 清理LOCAL_EQUIVALENT文件: {filename}")
                        
                        # 记录删除到缓存（使用原始文件名）
                        original_filename = file_info.get("original_filename", filename)
                        self.add_deletion_record(original_filename)
                    else:
                        print(f"File already deleted: {filename} (skipped)")
                except Exception as e:
                    failed_cleanups.append({"file": filename, "error": str(e)})
                    print(f"Failed to clean file: {filename} - {e}")
            
            if cleaned_files:
                pass
            
            if failed_cleanups:
                pass
                
        except Exception as e:
            print(f"Error cleaning LOCAL_EQUIVALENT files: {e}")

    def load_deletion_cache(self):
        """
        加载删除时间缓存
        
        Returns:
            list: 删除记录栈（按时间排序）
        """
        try:
            if self.main_instance.deletion_cache_file.exists():
                with open(self.main_instance.deletion_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return cache_data.get("deletion_records", [])
            else:
                return []
        except Exception as e:
            print(f"⚠️ 加载删除缓存失败: {e}")
            return []

    def save_deletion_cache(self, deletion_records):
        """
        保存删除时间缓存
        
        Args:
            deletion_records (list): 删除记录栈
        """
        try:
            cache_data = {
                "deletion_records": deletion_records,
                "last_updated": time.time()
            }
            with open(self.main_instance.deletion_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存删除缓存失败: {e}")
    
    def should_rename_file(self, filename):
        """
        检查是否应该重命名文件（基于删除缓存）
        
        Args:
            filename (str): 文件名
            
        Returns:
            bool: 是否应该重命名
        """
        try:
            deletion_records = self.load_deletion_cache()
            current_time = time.time()
            
            # 检查5分钟内是否删除过同名文件
            for record in deletion_records:
                if (record.get("filename") == filename and 
                    current_time - record.get("timestamp", 0) < 300):  # 5分钟 = 300秒
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️ 检查文件重命名建议时出错: {e}")
            return False
    
    def add_deletion_record(self, filename):
        """
        添加文件删除记录
        
        Args:
            filename (str): 被删除的文件名
        """
        try:
            deletion_records = self.load_deletion_cache()
            
            # 添加新的删除记录
            deletion_records.append({
                "filename": filename,
                "timestamp": time.time()
            })
            
            # 清理5分钟以前的记录
            current_time = time.time()
            deletion_records = [
                record for record in deletion_records
                if current_time - record.get("timestamp", 0) < 300
            ]
            
            # 保存更新的缓存
            self.save_deletion_cache(deletion_records)
        except Exception as e:
            print(f"⚠️ 添加删除记录时出错: {e}")

    def load_cache_config(self):
        """加载缓存配置"""
        try:
            if self.main_instance.config_file.exists():
                with open(self.main_instance.config_file, 'r', encoding='utf-8') as f:
                    self.cache_config = json.load(f)
                    self.cache_config_loaded = True
            else:
                self.cache_config = {}
                self.cache_config_loaded = False
        except Exception as e:
            print(f"⚠️ 加载缓存配置失败: {e}")
            self.cache_config = {}
            self.cache_config_loaded = False

    def is_remote_file_cached(self, remote_path: str) -> Dict:
        """检查远端文件是否在本地有缓存"""
        try:
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            cache_config = cache_manager.cache_config
            files = cache_config.get("files", {})
            
            if remote_path in files:
                file_info = files[remote_path]
                cache_file_path = file_info.get("cache_path")
                
                if cache_file_path and Path(cache_file_path).exists():
                    return {
                        "success": True,
                        "is_cached": True,
                        "cache_file_path": cache_file_path,
                        "cache_info": file_info
                    }
                else:
                    return {
                        "success": True,
                        "is_cached": False,
                        "reason": "cache_file_not_found"
                    }
            else:
                return {
                    "success": True,
                    "is_cached": False,
                    "reason": "not_in_cache_config"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"检查缓存时出错: {e}"
            }

    def get_remote_file_modification_time(self, remote_path: str) -> Dict:
        """获取远端文件的修改时间"""
        try:
            # 如果remote_path看起来像文件名（不包含路径分隔符），在当前目录中查找
            if '/' not in remote_path and not remote_path.startswith('~'):
                # 列出当前目录的所有文件
                result = self.main_instance.cmd_ls('', detailed=True)
                
                if result["success"] and result["files"]:
                    # 在文件列表中查找指定文件
                    for file_info in result["files"]:
                        if file_info.get("name") == remote_path:
                            modified_time = file_info.get("modifiedTime")
                            
                            if modified_time:
                                return {
                                    "success": True,
                                    "modified_time": modified_time,
                                    "file_info": file_info
                                }
                            else:
                                return {
                                    "success": False,
                                    "error": "无法获取文件修改时间"
                                }
                    
                    # 文件未找到
                    return {
                        "success": False,
                        "error": f"文件不存在或无法访问: {remote_path}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"无法列出目录内容: {result.get('error', 'unknown error')}"
                    }
            else:
                # 原来的逻辑，处理路径格式的文件
                result = self.main_instance.cmd_ls(remote_path, detailed=True)
                
                if result["success"] and result["files"]:
                    file_info = result["files"][0]
                    modified_time = file_info.get("modifiedTime")
                    
                    if modified_time:
                        return {
                            "success": True,
                            "modified_time": modified_time,
                            "file_info": file_info
                        }
                    else:
                        return {
                            "success": False,
                            "error": "无法获取文件修改时间"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"文件不存在或无法访问: {remote_path}"
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"获取文件修改时间时出错: {e}"
            }

    def is_cached_file_up_to_date(self, remote_path: str) -> Dict:
        """检查缓存文件是否为最新版本"""
        try:
            cache_result = self.is_remote_file_cached(remote_path)
            if not cache_result["success"]:
                return cache_result
            
            if not cache_result["is_cached"]:
                return {
                    "success": True,
                    "is_cached": False,
                    "is_up_to_date": False,
                    "reason": "no_cache"
                }
            
            cache_info = cache_result["cache_info"]
            cached_modified_time = cache_info.get("remote_modified_time")
            
            if not cached_modified_time:
                return {
                    "success": True,
                    "is_cached": True,
                    "is_up_to_date": False,
                    "reason": "no_cached_modified_time"
                }
            
            import os
            filename = os.path.basename(remote_path)
            remote_time_result = self.get_remote_file_modification_time(filename)
            if not remote_time_result["success"]:
                return {
                    "success": False,
                    "error": f"无法获取远端修改时间: {remote_time_result.get('error', '未知错误')}"
                }
            
            current_modified_time = remote_time_result["modified_time"]
            is_up_to_date = cached_modified_time == current_modified_time
            
            return {
                "success": True,
                "is_cached": True,
                "is_up_to_date": is_up_to_date,
                "cached_modified_time": cached_modified_time,
                "current_modified_time": current_modified_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"检查缓存新旧时出错: {e}"
            }

    def _update_uploaded_files_cache(self, found_files, context_info):
        """
        更新上传文件的缓存信息，记录最新的远端修改时间
        
        Args:
            found_files (list): 验证成功的文件列表，包含文件信息
            context_info (dict): 上下文信息，包含file_moves等
        """
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if not cache_manager_path.exists():
                return  # 缓存管理器不存在，静默返回
                
            sys.path.insert(0, str(Path(__file__).parent))
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            file_moves = context_info.get("file_moves", [])
            target_path = context_info.get("target_path", ".")
            
            # 为每个成功上传的文件更新缓存
            for found_file in found_files:
                file_name = found_file.get("name")
                if not file_name:
                    continue
                    
                # 构建远端绝对路径
                if target_path == ".":
                    # 当前目录
                    current_shell = self.main_instance.get_current_shell()
                    if current_shell:
                        current_path = current_shell.get("current_path", "~")
                        if current_path == "~":
                            remote_absolute_path = f"{self.main_instance.REMOTE_ROOT}/{file_name}"
                        else:
                            remote_absolute_path = f"{current_path}/{file_name}"
                    else:
                        remote_absolute_path = f"{self.main_instance.REMOTE_ROOT}/{file_name}"
                else:
                    # 指定目标路径
                    if target_path.startswith("/"):
                        remote_absolute_path = f"{target_path}/{file_name}"
                    else:
                        current_shell = self.main_instance.get_current_shell()
                        if current_shell:
                            current_path = current_shell.get("current_path", "~")
                            if current_path == "~":
                                remote_absolute_path = f"{self.main_instance.REMOTE_ROOT}/{target_path}/{file_name}"
                            else:
                                remote_absolute_path = f"{current_path}/{target_path}/{file_name}"
                        else:
                            remote_absolute_path = f"{self.main_instance.REMOTE_ROOT}/{target_path}/{file_name}"
                
                # 获取远端修改时间
                remote_modified_time = found_file.get("modified")
                if remote_modified_time:
                    # 检查是否已经有缓存
                    if cache_manager.is_file_cached(remote_absolute_path):
                        # 更新现有缓存的远端修改时间
                        cache_manager._update_cached_file_modified_time(remote_absolute_path, remote_modified_time)
                        print(f"✅ 已更新缓存文件时间: {file_name} -> {remote_modified_time}")
                    else:
                        # 文件还没有缓存，存储修改时间以备后用
                        cache_manager.store_pending_modified_time(remote_absolute_path, remote_modified_time)
                        print(f"📝 记录上传文件修改时间: {file_name} -> {remote_modified_time}")
                        
        except Exception as e:
            # 静默处理错误，不影响主流程
            print(f"⚠️ 更新缓存时间时出错: {e}")
