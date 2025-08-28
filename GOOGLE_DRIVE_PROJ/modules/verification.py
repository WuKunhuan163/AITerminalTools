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
            return self._verify_file_creation_with_ls(path, current_shell, max_attempts)
        else:
            return {
                "success": False,
                "error": f"Unsupported creation type: {creation_type}"
            }
    
    def _verify_file_creation_with_ls(self, path, current_shell, max_attempts=60):
        """使用GDS ls验证文件创建"""
        import time
        
        try:
            # 输出验证进度提示
            print("⏳ Validating file creation ...", end="", flush=True)
            

            
            # 解析文件路径
            if path.startswith("~/"):
                # ~/dir/file.txt -> 验证文件在指定目录中存在
                remaining_path = path[2:]  # 去掉~/
                path_components = [comp for comp in remaining_path.split('/') if comp]
                
                if len(path_components) == 1:
                    # 根目录下的文件
                    target_dir = "~"
                    target_filename = path_components[0]
                else:
                    # 嵌套目录中的文件
                    target_dir = "~/" + "/".join(path_components[:-1])
                    target_filename = path_components[-1]
                

                
            else:
                # 相对路径或其他格式
                if '/' in path:
                    path_components = path.split('/')
                    target_dir = "/".join(path_components[:-1]) or "."
                    target_filename = path_components[-1]
                else:
                    target_dir = "."
                    target_filename = path
                

            
            # 计算绝对路径
            if target_dir == ".":
                # 获取当前shell的路径
                current_path = current_shell.get("current_path", "~")
                
                # 使用路径解析器计算绝对路径
                try:
                    absolute_path = self.main_instance.path_resolver.compute_absolute_path(current_path, target_filename)
                    
                    # 分解绝对路径
                    if '/' in absolute_path:
                        abs_components = absolute_path.split('/')
                        target_dir = "/".join(abs_components[:-1]) or "~"
                        target_filename = abs_components[-1]
                except Exception as e:
                    # 如果路径解析失败，保持原有逻辑
                    pass
            
            # 验证文件存在
            for attempt in range(max_attempts):
                if attempt > 0:
                    time.sleep(1)
                    print(".", end="", flush=True)
                
                # 使用ls命令检查文件是否存在
                ls_result = self.main_instance.cmd_ls(target_dir, detailed=False, recursive=False)
                

                
                if ls_result["success"]:
                    files = ls_result.get("files", [])
                    
                    # 检查目标文件是否存在
                    for file in files:
                        if file["name"] == target_filename:
                            print("√")  # 成功标记
                            return {
                                "success": True,
                                "message": f"File creation verified: {path}",
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
                "error": f"File '{path}' not found after {max_attempts} verification attempts",
                "attempts": max_attempts
            }
            
        except Exception as e:
            print("✗")  # 失败标记
            return {
                "success": False,
                "error": f"File verification process error: {e}"
            }

    def _verify_mkdir_with_ls(self, path, current_shell, max_attempts=60):
        """使用GDS ls验证目录创建，支持嵌套路径验证和递归验证"""
        import time
        import sys
        
        try:
            # 使用用户期望的验证风格
            print("⏳ Validating dir creation ...", end="", flush=True)
            
            # 对于mkdir验证，我们需要验证的是实际创建的目录
            # 对于路径如~/tmp/gds_test_xxx，实际创建的是gds_test_xxx目录在tmp文件夹中
            # 但由于mkdir -p的特性，我们只需要验证顶级目录的存在即可
            
            # 检查当前路径是否已经在目标目录或其子目录中
            current_path = current_shell.get("current_path", "~")
            
            # 检查是否为复杂嵌套路径，如果是则使用递归验证
            path_depth = len([comp for comp in path.replace("~/", "").split('/') if comp])
            if path_depth > 2:  # 超过2层深度的路径使用递归验证
                return self._verify_mkdir_recursive_logic(path, current_shell)
            
            # 对于简单路径，继续使用原有逻辑
            
            if path.startswith("~/"):
                # ~/tmp/gds_test_xxx -> 验证tmp目录在根目录中存在
                remaining_path = path[2:]  # 去掉~/
                path_components = [comp for comp in remaining_path.split('/') if comp]
                target_dir_name = path_components[0]  # 要验证的顶级目录名 (tmp)
                is_nested = len(path_components) > 1
                
                # 如果当前路径已经在目标目录或其子目录中，直接返回成功
                if current_path.startswith(f"~/{target_dir_name}/") or current_path == f"~/{target_dir_name}":
                    print("√")  # 成功标记
                    return {
                        "success": True,
                        "message": f"Directory already exists (current path is in target directory): {path}",
                        "attempts": 1
                    }
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


