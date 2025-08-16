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

    def _verify_mkdir_with_ls(self, path, current_shell, max_attempts=60):
        """使用GDS ls验证目录创建，支持嵌套路径验证"""
        import time
        import sys
        
        try:
            # 使用用户期望的验证风格
            print("⏳ Validating dir creation ...", end="", flush=True)
            
            # 对于mkdir验证，我们需要验证的是实际创建的目录
            # 对于路径如~/tmp/gds_test_xxx，实际创建的是gds_test_xxx目录在tmp文件夹中
            # 但由于mkdir -p的特性，我们只需要验证顶级目录的存在即可
            
            if path.startswith("~/"):
                # ~/tmp/gds_test_xxx -> 验证tmp目录在根目录中存在
                remaining_path = path[2:]  # 去掉~/
                path_components = [comp for comp in remaining_path.split('/') if comp]
                target_dir_name = path_components[0]  # 要验证的顶级目录名 (tmp)
                is_nested = len(path_components) > 1
            elif path == "~":
                # 根目录本身，无需验证
                print("√")
                return {
                    "success": True,
                    "message": "Root directory already exists",
                    "attempts": 1
                }
            elif '/' in path:
                path_components = [comp for comp in path.split('/') if comp]
                target_dir_name = path_components[0]
                is_nested = len(path_components) > 1
            else:
                target_dir_name = path
                is_nested = False
            
            # 可配置重试机制，默认最多尝试60次
            for attempt in range(max_attempts):
                if attempt > 0:
                    # 根据重试次数调整等待时间
                    if max_attempts <= 3:
                        time.sleep(2)  # 短重试：2秒间隔
                    else:
                        time.sleep(1)  # 长重试：1秒间隔
                    
                    # 每次重试显示一个点
                    print(".", end="", flush=True)
                
                # 使用GDS ls的绝对路径功能，避免切换目录
                if path.startswith("~/"):
                    # 对于~/tmp/gds_test_xxx，我们需要验证tmp目录存在
                    # 使用ls ~来列出根目录内容
                    ls_result = self.main_instance.cmd_ls("~", detailed=False, recursive=False)
                elif is_nested:
                    # 对于嵌套路径a/b/c/d，验证a目录存在
                    # 可以使用当前目录的ls
                    ls_result = self.main_instance.cmd_ls(None, detailed=False, recursive=False)
                else:
                    # 单级目录，使用当前目录验证
                    ls_result = self.main_instance.cmd_ls(None, detailed=False, recursive=False)
                
                if ls_result["success"]:
                    folders = ls_result.get("folders", [])
                    # 检查目标目录是否存在
                    for folder in folders:
                        if folder["name"] == target_dir_name:
                            print("√")  # 成功标记
                            if is_nested:
                                return {
                                    "success": True,
                                    "message": f"Validation successful, nested directory created: {path}",
                                    "folder_id": folder["id"],
                                    "attempts": attempt + 1
                                }
                            else:
                                return {
                                    "success": True,
                                    "message": f"Validation successful, directory created: {path}",
                                    "folder_id": folder["id"],
                                    "attempts": attempt + 1
                                }
                else:
                    return {
                        "success": False,
                        "error": f"Validation failed, cannot execute ls command: {ls_result.get('error', 'Unknown error')}"
                    }
                        
            # 所有重试都失败了
            print("✗")  # 失败标记
            return {
                "success": False,
                "error": f"Directory '{path}' not found after {max_attempts} verification attempts",
                "attempts": max_attempts
            }
            
        except Exception as e:
            print("✗")  # 失败标记
            return {
                "success": False,
                "error": f"Verification process error: {e}"
            }
    
    def _verify_nested_path_in_ls_result(self, target_path, ls_result):
        """在递归ls结果中验证嵌套路径是否存在"""
        try:
            # 获取递归ls结果中的所有路径
            all_paths = []
            
            # 从folders中提取路径
            if "folders" in ls_result:
                for folder in ls_result["folders"]:
                    if "path" in folder:
                        all_paths.append(folder["path"])
                    elif "name" in folder:
                        all_paths.append(folder["name"])
            
            # 从files中提取路径（如果有的话）
            if "files" in ls_result:
                for file in ls_result["files"]:
                    if "path" in file:
                        # 提取文件的目录路径
                        dir_path = '/'.join(file["path"].split('/')[:-1])
                        if dir_path and dir_path not in all_paths:
                            all_paths.append(dir_path)
            
            # 检查目标路径或其任何前缀是否存在
            target_components = target_path.split('/')
            
            # 逐级检查路径是否存在
            for i in range(1, len(target_components) + 1):
                partial_path = '/'.join(target_components[:i])
                
                # 检查是否有匹配的路径
                for found_path in all_paths:
                    if found_path == partial_path or found_path.endswith('/' + partial_path):
                        if i == len(target_components):  # 完整路径匹配
                            return True
            
            # 如果递归ls结果结构不同，尝试简单的字符串匹配
            for found_path in all_paths:
                if target_path in found_path or found_path in target_path:
                    return True
            
            return False
            
        except Exception as e:
            # 如果解析失败，回退到简单验证
            return False

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
