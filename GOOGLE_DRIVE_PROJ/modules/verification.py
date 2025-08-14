#!/usr/bin/env python3
"""
Google Drive Shell - Verification Module
从google_drive_shell.py重构而来的verification模块
"""

class Verification:
    """Google Drive Shell Verification"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def _verify_mkdir_result(self, path, current_shell):
        """验证mkdir创建结果"""
        try:

            # 使用GDS ls命令验证
            if "/" in path:
                # 如果是多级路径，检查父目录
                parent_path = "/".join(path.split("/")[:-1])
                dir_name = path.split("/")[-1]
                
                # 先切换到父目录
                parent_id, _ = self.main_instance.resolve_path(parent_path, current_shell)
                if parent_id:
                    # 列出父目录内容
                    ls_result = self._ls_single(parent_id, parent_path, detailed=False)
                    if ls_result["success"]:
                        # 检查目标目录是否存在
                        all_folders = ls_result.get("folders", [])
                        for folder in all_folders:
                            if folder["name"] == dir_name:
                                return {
                                    "success": True,
                                    "message": f"✅ Validation successful, directory created: {dir_name}",
                                    "folder_id": folder["id"]
                                }
                        return {
                            "success": False,
                            "error": f"Validation failed, directory not found: {dir_name}"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Validation failed, cannot list parent directory: {ls_result.get('error', 'Unknown error')}"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Validation failed, parent directory does not exist: {parent_path}"
                    }
            else:
                # 单级目录，在当前目录下检查
                current_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                current_path = current_shell.get("current_path", "~")
                
                ls_result = self._ls_single(current_folder_id, current_path, detailed=False)
                if ls_result["success"]:
                    all_folders = ls_result.get("folders", [])
                    for folder in all_folders:
                        if folder["name"] == path:
                            return {
                                "success": True,
                                "message": f"✅ Validation successful, directory created: {path}",
                                "folder_id": folder["id"]
                            }
                    return {
                        "success": False,
                        "error": f"Validation failed, directory not found: {path}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Validation failed, cannot list current directory: {ls_result.get('error', 'Unknown error')}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Error verifying mkdir result: {e}"
            }

    def _verify_mkdir_with_ls(self, path, current_shell):
        """使用GDS ls验证单层目录创建，带重试机制"""
        import time
        
        try:
            print(f"🔍 验证目录创建: {path}")
            
            # 重试机制，最多尝试3次
            for attempt in range(3):
                if attempt > 0:
                    print(f"⏳ 等待Google Drive同步... (尝试 {attempt + 1}/3)")
                    time.sleep(2)  # 等待2秒让Google Drive同步
                
                # 在当前目录执行ls命令
                ls_result = self.main_instance.cmd_ls(None, detailed=False, recursive=False)
                if ls_result["success"]:
                    folders = ls_result.get("folders", [])
                    
                    for folder in folders:
                        if folder["name"] == path:
                            return {
                                "success": True,
                                "message": f"Validation successful, directory created: {path}",
                                "folder_id": folder["id"]
                            }
                    
                    if attempt == 0:
                        print(f"📂 Current directory contains: {[f['name'] for f in folders]}")
                        print(f"🔍 Target directory '{path}' not found, possible sync delay")
                else:
                    return {
                        "success": False,
                        "error": f"Validation failed, cannot execute ls command: {ls_result.get('error', 'Unknown error')}"
                    }
            
            # 所有重试都失败了
            print(f"❌ Validation failed, directory not found after 3 attempts: {path}")
            return {
                "success": False,
                "error": f"Validation failed, directory may have been created but Google Drive sync delay: {path}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification process error: {e}"
            }

    def _verify_mkdir_with_ls_recursive(self, path, current_shell):
        """使用GDS ls -R验证多层目录创建"""
        try:
            # 使用递归ls命令验证
            ls_result = self.main_instance.cmd_ls(None, detailed=False, recursive=True)
            if ls_result["success"]:
                # 检查目标路径是否存在
                target_parts = path.split("/")
                target_name = target_parts[-1]
                
                # 在递归结果中查找目标目录
                all_items = ls_result.get("all_items", [])
                for item in all_items:
                    if (item["name"] == target_name and 
                        item["mimeType"] == "application/vnd.google-apps.folder"):
                        # 检查路径是否匹配
                        item_path = item.get("path", "")
                        expected_parent_path = "/".join(target_parts[:-1])
                        
                        # 简化路径匹配逻辑
                        if expected_parent_path in item_path or item_path.endswith(expected_parent_path):
                            return {
                                "success": True,
                                "message": f"Validation successful, multi-level directory created: {path}",
                                "folder_id": item["id"],
                                "full_path": item_path
                            }
                
                return {
                    "success": False,
                    "error": f"Validation failed, multi-level directory not found: {path}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Validation failed, cannot execute ls -R command: {ls_result.get('error', 'Unknown error')}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Recursive verification process error: {e}"
            }

    def _verify_mv_with_ls(self, source, destination, current_shell, max_retries=3, delay_seconds=2):
        """验证mv操作是否成功，通过ls检查文件是否在新位置"""
        import time
        
        for attempt in range(max_retries):
            try:
                # 检查源文件是否还存在（应该不存在）
                source_still_exists = self._find_file(source, current_shell) is not None
                
                # 检查目标位置是否有文件
                if '/' in destination:
                    # 目标包含路径
                    dest_parent = '/'.join(destination.split('/')[:-1])
                    dest_name = destination.split('/')[-1]
                    
                    # 切换到目标目录检查
                    dest_folder_id, _ = self.main_instance.resolve_path(dest_parent, current_shell)
                    if dest_folder_id:
                        temp_shell = current_shell.copy()
                        temp_shell["current_folder_id"] = dest_folder_id
                        destination_exists = self._find_file(dest_name, temp_shell) is not None
                    else:
                        destination_exists = False
                else:
                    # 在当前目录重命名
                    destination_exists = self._find_file(destination, current_shell) is not None
                
                # 如果源文件不存在且目标文件存在，则移动成功
                if not source_still_exists and destination_exists:
                    return {"success": True, "message": "mv validation successful"}
                
                # 如果还没成功，等待一下再试（Google Drive API延迟）
                if attempt < max_retries - 1:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay_seconds)
                else:
                    return {"success": False, "error": f"Error verifying mv operation: {e}"}
        
        return {"success": False, "error": f"mv validation failed: after {max_retries} attempts, file move status unclear"}

    def _update_cache_after_mv(self, source, destination, current_shell):
        """在mv命令成功后更新缓存路径映射"""
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if not cache_manager_path.exists():
                return {"success": False, "error": "Cache manager not found"}
            
            sys.path.insert(0, str(Path(__file__).parent))
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            # 构建原始和新的远端绝对路径
            old_remote_path = self.resolve_remote_absolute_path(source, current_shell)
            new_remote_path = self.resolve_remote_absolute_path(destination, current_shell)
            
            # 检查是否有缓存需要更新
            if cache_manager.is_file_cached(old_remote_path):
                # 更新缓存路径映射
                move_result = cache_manager.move_cached_file(old_remote_path, new_remote_path)
                if move_result["success"]:
                    return {
                        "success": True,
                        "message": f"✅ Cache path mapping updated: {old_remote_path} -> {new_remote_path}",
                        "old_path": old_remote_path,
                        "new_path": new_remote_path,
                        "cache_file": move_result["cache_file"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to update cache path mapping: {move_result.get('error')}"
                    }
            else:
                return {
                    "success": True,
                    "message": "No cache update needed (file not cached)",
                    "old_path": old_remote_path,
                    "new_path": new_remote_path
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error updating cache mapping: {e}"}

    def _verify_rm_with_find(self, path, current_shell, max_retries=60):
        """
        使用find命令验证文件是否被成功删除
        
        Args:
            path (str): 原始路径
            current_shell (dict): 当前shell信息
            max_retries (int): 最大重试次数
            
        Returns:
            dict: 验证结果
        """
        try:
            import time
            
            for attempt in range(max_retries):
                # 使用find命令查找文件
                find_result = self.cmd_find(path, name_pattern=None, recursive=False)
                
                if find_result["success"] and not find_result.get("files"):
                    # 没有找到文件，删除成功
                    return {"success": True, "message": "Files successfully deleted"}
                
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
            
            # 所有重试都失败
            return {"success": False, "error": "Files still exist after deletion"}
            
        except Exception as e:
            return {"success": False, "error": f"Verification error: {e}"}
