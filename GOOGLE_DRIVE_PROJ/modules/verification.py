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



    def verify_creation_with_ls(self, path, current_shell, creation_type="dir", max_attempts=60):
        """
        通用的创建验证接口，支持目录和文件验证
        
        Args:
            path (str): 要验证的路径
            current_shell (dict): 当前shell信息
            creation_type (str): 创建类型，"dir"或"file"
            max_attempts (int): 最大重试次数
            
        Returns:
            dict: 验证结果
        """
        if creation_type == "dir":
            return self._verify_mkdir_with_ls(path, current_shell, max_attempts)
        elif creation_type == "file":
            return self._verify_creation_with_ls(path, current_shell, max_attempts, creation_type="file")
        else:
            return {
                "success": False,
                "error": f"Unsupported creation type: {creation_type}"
            }
    
    def _verify_creation_with_ls(self, path, current_shell, max_attempts=60, creation_type="file"):
        """使用GDS ls统一验证文件或目录创建"""
        import time
        
        try:
            # 输出验证进度提示
            if creation_type == "dir":
                print("⏳ Validating dir creation ...", end="", flush=True)
            else:
                print("⏳ Validating file creation ...", end="", flush=True)
            
            # 简化验证逻辑：直接使用FileCore的cmd_ls验证路径是否存在
            for attempt in range(max_attempts):
                if attempt > 0:
                    time.sleep(1)
                    print(".", end="", flush=True)
                
                # 使用FileCore的cmd_ls直接检查路径是否存在
                # cmd_ls有统一的路径解析功能，不需要手动解析
                ls_result = self.main_instance.cmd_ls(path, detailed=False, recursive=False)
                
                if ls_result["success"]:
                    # 如果ls成功，说明路径存在
                    print("√")  # 成功标记
                    return {
                        "success": True,
                        "message": f"Creation verified: {path}",
                        "attempts": attempt + 1
                    }
                # 如果ls失败，继续重试
            
            # 所有重试都失败了
            print("✗")  # 失败标记
            return {
                "success": False,
                "error": f"Path '{path}' not found after {max_attempts} verification attempts",
                "attempts": max_attempts
            }
            
        except Exception as e:
            print("✗")  # 失败标记
            return {
                "success": False,
                "error": f"Verification process error: {e}"
            }

    def _verify_mkdir_with_ls(self, path, current_shell, max_attempts=60):
        """使用统一验证函数验证目录创建"""
        return self._verify_creation_with_ls(path, current_shell, max_attempts, creation_type="dir")
    
    def _verify_mkdir_recursive_logic(self, path, current_shell):
        """递归验证复杂嵌套路径的目录创建"""
        try:
            # 优化验证逻辑：直接尝试解析目标路径而不是使用递归ls
            # 这避免了遍历整个目录树的开销
            try:
                target_folder_id, display_path = self.main_instance.resolve_path(path, current_shell)
                
                if target_folder_id:
                    # 路径解析成功，说明目录存在
                    print("√")
                    return {
                        "success": True,
                        "message": f"Validation successful, directory created: {path}",
                        "folder_id": target_folder_id,
                        "full_path": display_path,
                        "attempts": 1
                    }
                else:
                    print("✗")
                    return {
                        "success": False,
                        "error": f"Validation failed, directory not found: {path}"
                    }
            except Exception as resolve_error:
                print("✗")
                return {
                    "success": False,
                    "error": f"Validation failed, path resolution error: {resolve_error}"
                }
                
        except Exception as e:
            print("✗")
            return {
                "success": False,
                "error": f"Recursive verification error: {e}"
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
                        "message": f"Cache path mapping updated: {old_remote_path} -> {new_remote_path}",
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


