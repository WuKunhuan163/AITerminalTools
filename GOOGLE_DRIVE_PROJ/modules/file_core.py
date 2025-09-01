
import time
import os
from pathlib import Path

# 导入debug捕获系统
from .remote_commands import debug_capture, debug_print

class FileCore:
    """
    Core file operations (upload, download, navigation)
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance

    def _verify_files_available(self, file_moves):
        """委托到file_utils的文件可用性验证"""
        return self.main_instance.file_utils._verify_files_available(file_moves)
    
    def _cleanup_local_equivalent_files(self, file_moves):
        """委托到cache_manager的本地等效文件清理"""
        return self.main_instance.cache_manager._cleanup_local_equivalent_files(file_moves)
    
    def _check_large_files(self, source_files):
        """检查大文件并分离处理（大于1G的文件）"""
        normal_files = []
        large_files = []
        
        for file_path in source_files:
            try:
                file_size = os.path.getsize(file_path)
                # 1G = 1024 * 1024 * 1024 bytes
                if file_size > 1024 * 1024 * 1024:
                    large_files.append({
                        "path": file_path,
                        "size": file_size,
                        "name": os.path.basename(file_path)
                    })
                else:
                    normal_files.append(file_path)
            except OSError:
                # 文件不存在或无法访问，加入normal_files让后续处理报错
                normal_files.append(file_path)
        
        return normal_files, large_files
    
    def _handle_large_files(self, large_files, target_path, current_shell):
        """处理大文件上传"""
        print(f"\n📁 Detected {len(large_files)} large files (>1GB):")
        for file_info in large_files:
            size_gb = file_info["size"] / (1024 * 1024 * 1024)
            print(f"  - {file_info['name']} ({size_gb:.1f} GB)")
        
        print(f"\n💡 Large files need to be manually uploaded to Google Drive:")
        print(f"  1. Open Google Drive web version")
        print(f"  2. Manually drag and drop these large files")
        print(f"  3. Wait for upload to complete")
        
        return {"success": True, "message": "Large files detected, manual upload required"}
    
    def wait_for_file_sync(self, file_names, file_moves):
        """等待文件同步完成"""
        return self.main_instance.sync_manager.wait_for_file_sync(file_names, file_moves)
    

    
    def _check_target_file_conflicts_before_move(self, file_moves, force=False):
        """检查目标文件冲突"""
        # 简化实现，如果force=True直接返回成功
        if force:
            return {"success": True, "conflicts": []}
        
        # 否则检查文件是否已存在（简化版本）
        conflicts = []
        for move in file_moves:
            target_path = move.get("new_path", "")
            if os.path.exists(target_path):
                conflicts.append({
                    "file": move.get("source", ""),
                    "target": target_path,
                    "reason": "File already exists"
                })
        
        if conflicts:
            return {
                "success": False,
                "conflicts": conflicts,
                "error": f"Found {len(conflicts)} file conflicts"
            }
        
        return {"success": True, "conflicts": []}
    
    def _check_remote_file_conflicts(self, source_files, target_path):
        """检查远程文件是否已存在（用于非force模式）"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            conflicts = []
            
            # 获取目标目录中的文件列表
            ls_result = self.main_instance.cmd_ls(target_path, detailed=False, recursive=False)
            if not ls_result.get("success"):
                # 如果无法列出文件（可能是目录不存在），则认为没有冲突
                return {"success": True, "conflicts": []}
            
            # 获取远程文件名列表
            remote_files = set()
            if ls_result.get("files"):
                for file_info in ls_result["files"]:
                    remote_files.add(file_info["name"])
            
            # 检查每个源文件是否在远程已存在
            for source_file in source_files:
                if not os.path.exists(source_file):
                    continue
                
                filename = os.path.basename(source_file)
                if filename in remote_files:
                    conflicts.append({
                        "local_file": source_file,
                        "remote_file": filename,
                        "reason": "File already exists in remote directory"
                    })
            
            if conflicts:
                conflict_files = [c["remote_file"] for c in conflicts]
                return {
                    "success": False,
                    "conflicts": conflicts,
                    "error": f"\nFile exists: {', '.join(conflict_files)}. Use --force to override."
                }
            
            return {"success": True, "conflicts": []}
            
        except Exception as e:
            # 如果检查过程出错，允许继续上传（保守处理）
            debug_print(f"Remote file conflict check failed: {e}")
            return {"success": True, "conflicts": []}

    def cmd_upload_folder(self, folder_path, target_path=".", keep_zip=False, force=False):
        """
        上传文件夹到Google Drive
        
        流程：打包 -> 上传zip文件（作为普通文件）
        
        Args:
            folder_path (str): 要上传的文件夹路径
            target_path (str): 目标路径（相对于当前shell路径）
            keep_zip (bool): 是否保留本地zip文件（远端总是保留zip文件）
            force (bool): 是否强制覆盖现有文件
            
        Returns:
            dict: 上传结果
        """
        try:
            folder_name = Path(folder_path).name
            print(f"Packing {folder_name} ...", end="", flush=True)
            
            # 步骤1: 打包文件夹
            zip_result = self.main_instance.file_utils._zip_folder(folder_path)
            if not zip_result["success"]:
                print(f" ✗")
                return {"success": False, "error": f"打包失败: {zip_result['error']}"}
            else: 
                print(f" √")
            
            zip_path = zip_result["zip_path"]
            zip_filename = Path(zip_path).name
            
            try:
                # 步骤2: 上传zip文件并自动解压
                # 传递文件夹上传的特殊参数
                upload_result = self.cmd_upload([zip_path], target_path, force=force, 
                                              folder_upload_info={
                                                  "is_folder_upload": True,
                                                  "zip_filename": zip_filename,
                                                  "keep_zip": keep_zip
                                              })
                if not upload_result["success"]:
                    print(f" ✗")
                    return {"success": False, "error": f"上传失败: {upload_result['error']}"}
                
                # 成功完成
                print(f" √")
                return {
                    "success": True,
                    "message": f"Uploaded folder: {folder_name}",
                    "original_folder": folder_path,
                    "zip_uploaded": zip_filename,
                    "zip_kept": keep_zip,
                    "target_path": target_path,
                    "zip_size": zip_result.get("zip_size", 0),
                    "method": "zip_upload_and_extract",
                    "upload_details": upload_result
                }
                
            finally:
                # 根据keep_zip参数决定是否清理本地临时zip文件
                if not keep_zip:
                    try:
                        if Path(zip_path).exists():
                            Path(zip_path).unlink()
                            print(f"Cleaned up local temporary file: {zip_filename}")
                    except Exception as e:
                        print(f"Warning: Failed to clean up temporary file: {e}")
                else:
                    print(f"Saved local zip file: {zip_path}")
                    
        except Exception as e:
            # 如果出错，也要清理临时文件
            try:
                if 'zip_path' in locals() and Path(zip_path).exists():
                    Path(zip_path).unlink()
                    print(f"🧹 已清理本地临时文件: {zip_path}")
            except:
                pass
            return {"success": False, "error": f"文件夹上传过程出错: {e}"}

    def cmd_upload(self, source_files, target_path=".", force=False, folder_upload_info=None, remove_local=False):
        """
        GDS UPLOAD 命令实现
        
        Args:
            source_files (list): 要上传的源文件路径列表
            target_path (str): 目标路径（相对于当前 shell 路径）
            force (bool): 是否强制覆盖现有文件
            
        Returns:
            dict: 上传结果
        """
        try:
            # 立即显示进度消息
            print("⏳ Waiting for upload ...", end="", flush=True)
            debug_capture.start_capture()
            
            # 延迟启动debug信息捕获，让重命名信息能够显示
            debug_print(f"cmd_upload called with source_files={source_files}, target_path='{target_path}', force={force}")
            
            # 0. 检查Google Drive Desktop是否运行
            if not self.main_instance.file_operations.ensure_google_drive_desktop_running():
                return {"success": False, "error": "用户取消上传操作"}
            
            # 1. 验证输入参数
            if not source_files:
                return {"success": False, "error": "请指定要上传的文件"}
            
            if isinstance(source_files, str):
                source_files = [source_files]
            
            # 1.5. 检查大文件并分离处理
            normal_files, large_files = self._check_large_files(source_files)
            
            # 处理大文件
            if large_files:
                large_file_result = self._handle_large_files(large_files, target_path, current_shell)
                if not large_file_result["success"]:
                    return large_file_result
            
            # 如果没有正常大小的文件需要处理，但有大文件，需要等待手动上传完成
            if not normal_files:
                if large_files:
                    # 等待大文件手动上传完成
                    large_file_names = [Path(f["path"]).name for f in large_files]
                    print(f"\n⏳ Waiting for large files manual upload ...")
                    
                    # 创建虚拟file_moves用于计算超时时间
                    virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                    sync_result = self.wait_for_file_sync(large_file_names, virtual_file_moves)
                    
                    if sync_result["success"]:
                        return {
                            "success": True,
                            "message": f"\nLarge files manual upload completed: {len(large_files)} files",
                            "large_files_handled": True,
                            "sync_time": sync_result.get("sync_time", 0)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Manual upload failed: {sync_result.get('error', 'Unknown error')}",
                            "large_files_handled": True
                        }
                else:
                    return {"success": False, "error": "Cannot find valid files"}
            
            # 继续处理正常大小的文件
            source_files = normal_files
            
            # 2. 获取当前 shell
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            # 3. 解析目标路径
            debug_print(f"Before _resolve_target_path_for_upload - target_path='{target_path}'")
            debug_print(f"current_shell={current_shell}")
            target_folder_id, target_display_path = self.main_instance.path_resolver._resolve_target_path_for_upload(target_path, current_shell)
            debug_print(f"After _resolve_target_path_for_upload - target_folder_id='{target_folder_id}', target_display_path='{target_display_path}'")
            if target_folder_id is None and self.drive_service:
                # 目标路径不存在，但这是正常的，我们会在远端创建它
                # 静默处理目标路径创建
                target_folder_id = None  # 标记为需要创建
                target_display_path = target_path
            elif not self.drive_service:
                print("⚠️ 警告: Google Drive API 服务未初始化，将使用模拟模式")
            
            # 3.5. 检查目标文件是否已存在，避免冲突（除非使用--force）
            overridden_files = []
            if not force:
                # 检查远程文件是否已存在
                conflict_check_result = self._check_remote_file_conflicts(source_files, target_path)
                if not conflict_check_result["success"]:
                    return conflict_check_result
            else:
                # Force模式：检查哪些文件会被覆盖，记录警告
                override_check_result = self.main_instance.file_utils._check_files_to_override(source_files, target_path)
                if override_check_result["success"] and override_check_result.get("overridden_files"):
                    overridden_files = override_check_result["overridden_files"]
                    for file_path in overridden_files:
                        print(f"Warning: Overriding remote file {file_path}")
            
            # 4. 检查是否有文件夹，提示正确语法
            for source_file in source_files:
                if Path(source_file).is_dir():
                    print(f"\nError: '{source_file}' is a directory")
                    print(f"To upload folders, use: GDS upload-folder {source_file}")
                    print(f"   Options: --keep-zip to preserve local zip file")
                    return {"success": False, "error": f""}
            
            # 5. 移动文件到 LOCAL_EQUIVALENT
            file_moves = []
            failed_moves = []
            
            for source_file in source_files:
                debug_print(f"Processing file: {source_file}")
                move_result = self.main_instance.sync_manager.move_to_local_equivalent(source_file)
                debug_print(f"Move result: {move_result}")
                
                if move_result["success"]:
                    file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "original_filename": move_result["original_filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"]
                    })
                    
                    # 记录重命名信息到debug（不显示给用户）
                    if move_result["renamed"]:
                        debug_print(f"🏷️  File renamed: {move_result['original_filename']} -> {move_result['filename']}")
                    else:
                        debug_print(f"File processed without renaming: {move_result['filename']}")
                else:
                    failed_moves.append({
                        "file": source_file,
                        "error": move_result.get("error", "Unknown error")
                    })
                    print(f"\n✗ {move_result['error']}")
            
            if not file_moves:
                return {
                    "success": False,
                    "error": "所有文件移动失败",
                    "failed_moves": failed_moves
                }
            
            # 5. 检测网络连接
            network_result = self.main_instance.file_operations.check_network_connection()
            if not network_result:
                print("⚠️ 网络连接检测失败")
                print("📱 将继续执行，但请确保网络连接正常")
            else:
                # 静默处理网络检查
                pass
            
            # 6. 等待文件同步到 DRIVE_EQUIVALENT
            # 对于同步检测，使用重命名后的文件名（在DRIVE_EQUIVALENT中的实际文件名）
            expected_filenames = [fm["filename"] for fm in file_moves]
            
            sync_result = self.wait_for_file_sync(expected_filenames, file_moves)
            
            if not sync_result["success"]:
                # 同步检测失败，但继续执行
                print(f"Warning: File sync check failed: {sync_result.get('error', 'Unknown error')}")
                print("📱 Upload may have succeeded, please manually verify files have been uploaded")
                print("💡 You can retry upload if needed")
                
                # 返回失败结果，让用户决定是否重试
                return {
                    "success": False,
                    "error": f"Upload sync verification failed: {sync_result.get('error', 'Unknown error')}",
                    "file_moves": file_moves,
                    "sync_time": sync_result.get("sync_time", 0),
                    "suggestion": "Files may have been uploaded successfully. Please check manually and retry if needed."
                }
            else:
                base_time = sync_result.get("base_sync_time", sync_result.get("sync_time", 0))
                sync_result["sync_time"] = base_time
            
            # 7. 静默验证文件同步状态
            self._verify_files_available(file_moves)
            
            # 8. 静默生成远端命令
            debug_print(f"Before generate_remote_commands - file_moves={file_moves}")
            debug_print(f"Before generate_remote_commands - target_path='{target_path}'")
            remote_command = self.main_instance.remote_commands.generate_remote_commands(file_moves, target_path, folder_upload_info)
            debug_print(f"After generate_remote_commands - remote_command preview: {remote_command[:200]}...")
            
            # 7.5. 远端目录创建已经集成到generate_remote_commands中，无需额外处理
            
            # 8. 使用统一的远端命令执行接口
            # 对于文件夹上传，跳过文件验证因为验证的是zip文件而不是解压后的内容
            if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
                # 文件夹上传：跳过文件验证，信任远程命令执行结果
                context_info = {
                    "expected_filenames": None,  # 跳过验证
                    "sync_filenames": expected_filenames,
                    "target_folder_id": target_folder_id,
                    "target_path": target_path,
                    "file_moves": file_moves,
                    "is_folder_upload": True
                }
            else:
                # 普通文件上传：正常验证
                context_info = {
                    "expected_filenames": [fm.get("original_filename", fm["filename"]) for fm in file_moves],  # 验证阶段用原始文件名
                    "sync_filenames": expected_filenames,  # 同步阶段用重命名后的文件名
                    "target_folder_id": target_folder_id,
                    "target_path": target_path,
                    "file_moves": file_moves
                }
            
            execution_result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            # 如果执行失败，直接返回错误
            if not execution_result["success"]:
                return {
                    "success": False,
                    "error": execution_result.get("error", execution_result.get("data", {}).get("error", "Unknown error")),
                    "remote_command": remote_command,
                    "execution_result": execution_result
                }
            
            if folder_upload_info and folder_upload_info.get("is_folder_upload", False):
                # 文件夹上传：跳过文件验证，信任远程命令执行结果
                debug_print(f"Folder upload detected, skipping file verification")
                verify_result = {
                    "success": True,
                    "found_files": [],
                    "missing_files": [],
                    "total_expected": len(expected_filenames),
                    "total_found": 0,
                    "skip_verification": True
                }
            else:
                # 普通文件上传：使用ls-based验证
                expected_for_verification = [fm.get("original_filename", fm["filename"]) for fm in file_moves]

                # 使用带进度的验证机制
                verify_result = self.main_instance.remote_commands._verify_upload_with_progress(
                    expected_for_verification, 
                    target_path, 
                    current_shell
                )

                debug_capture.start_capture()
                debug_print(f"Verification completed: {verify_result}")
            
            # 9. 上传和远端命令执行完成后，清理LOCAL_EQUIVALENT中的文件
            if verify_result["success"]:
                self._cleanup_local_equivalent_files(file_moves)
                
                # 添加删除记录到缓存（记录原始文件名和临时文件名的使用）
                for file_info in file_moves:
                    original_filename = file_info["original_filename"]
                    temp_filename = file_info["filename"]
                    
                    # 记录原始文件名的使用
                    self.main_instance.cache_manager.add_deletion_record(original_filename)
                    debug_print(f"Added deletion record for original: {original_filename}")
                    
                    # 如果文件被重命名，也记录临时文件名的使用
                    if file_info["renamed"] and temp_filename != original_filename:
                        self.main_instance.cache_manager.add_deletion_record(temp_filename)
                        debug_print(f"Added deletion record for temp: {temp_filename}")
                
                # 如果指定了 --remove-local 选项，删除本地源文件
                if remove_local:
                    removed_files = []
                    failed_removals = []
                    for source_file in source_files:
                        try:
                            if os.path.exists(source_file):
                                os.unlink(source_file)
                                removed_files.append(source_file)
                        except Exception as e:
                            failed_removals.append({"file": source_file, "error": str(e)})
            
            result = {
                "success": verify_result["success"],
                "uploaded_files": verify_result.get("found_files", []),
                "failed_files": verify_result.get("missing_files", []) + [fm["file"] for fm in failed_moves],
                "target_path": target_display_path,
                "target_folder_id": target_folder_id,
                "total_attempted": len(file_moves) + len(failed_moves),
                "total_succeeded": len(verify_result.get("found_files", [])),
                "remote_command": remote_command,
                "file_moves": file_moves,
                "failed_moves": failed_moves,
                "sync_time": sync_result.get("sync_time", 0),
                "message": f"Upload completed: {len(verify_result.get('found_files', []))}/{len(file_moves)} files" if verify_result["success"] else f" ✗\n⚠️ Partially uploaded: {len(verify_result.get('found_files', []))}/{len(file_moves)} files",
                "api_available": self.drive_service is not None
            }
            
            # Add debug information for all uploads to diagnose verification issues
            used_direct_feedback = verify_result.get("source") == "direct_feedback"
            upload_failed = not verify_result["success"]
            
            # Always show debug information to diagnose verification problems
            if used_direct_feedback:
                debug_print("User used direct feedback, showing debug information:")
            elif upload_failed:
                debug_print("Upload failed, showing debug information:")
            else:
                debug_print("Upload completed, showing verification debug information:")
            
            debug_print(f"verify_result={verify_result}")
            debug_print(f"sync_result={sync_result}")
            debug_print(f"target_folder_id='{target_folder_id}'")
            debug_print(f"target_display_path='{target_display_path}'")
            
            # 停止debug信息捕获
            debug_capture.stop_capture()
            
            # Always print debug capture buffer
            captured_debug = debug_capture.get_debug_info()
            if captured_debug:
                debug_print("Captured debug output:")
                debug_print(captured_debug)
            
            # 添加本地文件删除信息
            if remove_local and verify_result["success"]:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            # 停止debug信息捕获
            debug_capture.stop_capture()
            return result
            
        except Exception as e:
            # 停止debug信息捕获
            debug_capture.stop_capture()
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"Upload error: {str(e)}"
            }

    def cmd_pwd(self):
        """显示当前路径"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            return {
                "success": True,
                "current_path": current_shell.get("current_path", "~"),
                "home_url": self.main_instance.HOME_URL,
                "shell_id": current_shell["id"],
                "shell_name": current_shell["name"]
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取当前路径时出错: {e}"}

    def cmd_ls(self, path=None, detailed=False, recursive=False, show_hidden=False):
        """列出目录内容，支持递归、详细模式和扩展信息模式，支持文件路径"""
        try:
            # Debug: print(f"🔍 DEBUG: cmd_ls called with path='{path}', detailed={detailed}, recursive={recursive}")
            
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            # Debug: print(f"🔍 DEBUG: current_shell info - current_path='{current_shell.get('current_path', 'UNKNOWN')}', current_folder_id='{current_shell.get('current_folder_id', 'UNKNOWN')}'")
            
            if path is None or path == ".":
                # 当前目录
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                display_path = current_shell.get("current_path", "~")
                # Debug: print(f"🔍 DEBUG: Using current directory - target_folder_id='{target_folder_id}', display_path='{display_path}'")
            elif path == "~":
                # 根目录
                target_folder_id = self.main_instance.REMOTE_ROOT_FOLDER_ID
                display_path = "~"
                # Debug: print(f"🔍 DEBUG: Using root directory - target_folder_id='{target_folder_id}'")
            else:
                # Debug: print(f"🔍 DEBUG: Processing custom path '{path}'")
                # 首先尝试作为目录解析
                # Debug: print(f"🔍 DEBUG: Step 1 - Trying to resolve '{path}' as directory")
                target_folder_id, display_path = self.main_instance.resolve_path(path, current_shell)
                # Debug: print(f"🔍 DEBUG: resolve_path result - target_folder_id='{target_folder_id}', display_path='{display_path}'")
                
                if not target_folder_id:
                    # Debug: print(f"🔍 DEBUG: Step 2 - Directory resolution failed, trying as file path")
                    # 如果作为目录解析失败，尝试作为文件路径解析
                    file_result = self._resolve_file_path(path, current_shell)
                    # Debug: print(f"🔍 DEBUG: _resolve_file_path result: {file_result is not None}")
                    if file_result:
                        # 这是一个文件路径，返回单个文件信息
                        # Debug: print(f"🔍 DEBUG: ✅ Found as file, returning single file info")
                        # 内联_ls_single_file的逻辑
                        return {
                            "success": True,
                            "path": path,
                            "files": [file_result],
                            "folders": [],
                            "count": 1,
                            "mode": "single_file"
                        }
                    else:
                        # Debug: print(f"🔍 DEBUG: ❌ Neither directory nor file found for path '{path}'")
                        return {"success": False, "error": f"Path not found: {path}"}
            
            if recursive:
                return self._ls_recursive(target_folder_id, display_path, detailed, show_hidden)
            else:
                # 内联_ls_single的逻辑
                result = self.drive_service.list_files(folder_id=target_folder_id, max_results=50)
                
                if result['success']:
                    files = result['files']
                    
                    # 添加网页链接到每个文件
                    for file in files:
                        file['url'] = self._generate_web_url(file)
                    
                    # 按名称排序，文件夹优先
                    folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                    other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                       key=lambda x: x['name'].lower())
                    
                    # 去重处理
                    seen_names = set()
                    clean_folders = []
                    clean_files = []
                    
                    # 处理文件夹
                    for folder in folders:
                        if folder["name"] not in seen_names:
                            clean_folders.append(folder)
                            seen_names.add(folder["name"])
                    
                    # 处理文件
                    for file in other_files:
                        if file["name"] not in seen_names:
                            clean_files.append(file)
                            seen_names.add(file["name"])
                    
                    if detailed:
                        # 详细模式：返回完整JSON
                        return {
                            "success": True,
                            "path": display_path,
                            "folder_id": target_folder_id,
                            "folder_url": self._generate_folder_url(target_folder_id),
                            "files": clean_files,  # 只有非文件夹文件
                            "folders": clean_folders,  # 只有文件夹
                            "count": len(clean_folders) + len(clean_files),
                            "mode": "detailed"
                        }
                    else:
                        # bash风格：只返回文件名列表
                        return {
                            "success": True,
                            "path": display_path,
                            "folder_id": target_folder_id,
                            "files": clean_files,  # 只有非文件夹文件
                            "folders": clean_folders,  # 只有文件夹
                            "count": len(clean_folders) + len(clean_files),
                            "mode": "bash"
                        }
                else:
                    return {"success": False, "error": f"列出文件失败: {result['error']}"}
                
        except Exception as e:

            return {"success": False, "error": f"执行ls命令时出错: {e}"}

    def _ls_recursive(self, root_folder_id, root_path, detailed, show_hidden=False, max_depth=5):
        """递归列出目录内容"""
        try:
            all_items = []
            visited_folders = set()  # 防止循环引用
            
            def scan_folder(folder_id, folder_path, depth=0):
                # 深度限制
                if depth > max_depth:
                    return
                
                # 循环检测
                if folder_id in visited_folders:
                    return
                visited_folders.add(folder_id)
                
                result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
                if not result['success']:
                    visited_folders.discard(folder_id)  # 失败时移除，允许重试
                    return
                
                files = result['files']
                
                # 添加网页链接
                for file in files:
                    file['url'] = self._generate_web_url(file)
                    file['path'] = folder_path
                    file['depth'] = depth
                    all_items.append(file)
                    
                    # 如果是文件夹，递归扫描
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        sub_path = f"{folder_path}/{file['name']}" if folder_path != "~" else f"~/{file['name']}"
                        scan_folder(file['id'], sub_path, depth + 1)
                
                visited_folders.discard(folder_id)  # 扫描完成后移除，允许在其他路径中再次访问
            
            # 开始递归扫描
            scan_folder(root_folder_id, root_path)
            
            # 按路径和名称排序
            all_items.sort(key=lambda x: (x['path'], x['name'].lower()))
            
            # 分离文件夹和文件
            folders = [f for f in all_items if f['mimeType'] == 'application/vnd.google-apps.folder']
            other_files = [f for f in all_items if f['mimeType'] != 'application/vnd.google-apps.folder']
            
            if detailed:
                # 详细模式：返回嵌套的树形结构
                nested_structure = self._build_nested_structure(all_items, root_path)
                
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "folder_url": self._generate_folder_url(root_folder_id),
                    "files": nested_structure["files"],
                    "folders": nested_structure["folders"],  # 每个文件夹包含自己的files和folders
                    "count": len(all_items),
                    "mode": "recursive_detailed"
                }
            else:
                # 简单模式：只返回基本信息
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "files": other_files,
                    "folders": folders,
                    "all_items": all_items,
                    "count": len(all_items),
                    "mode": "recursive_bash"
                }
                
        except Exception as e:
            return {"success": False, "error": f"递归列出目录时出错: {e}"}

    def _build_nested_structure(self, all_items, root_path):
        """构建嵌套的文件夹结构，每个文件夹包含自己的files和folders"""
        try:
            # 按路径分组所有项目
            path_groups = {}
            
            for item in all_items:
                path = item['path']
                if path not in path_groups:
                    path_groups[path] = {'files': [], 'folders': []}
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    path_groups[path]['folders'].append(item)
                else:
                    path_groups[path]['files'].append(item)
            
            # 构建嵌套结构
            def build_folder_content(folder_path):
                content = path_groups.get(folder_path, {'files': [], 'folders': []})
                
                # 为每个子文件夹递归构建内容
                enriched_folders = []
                for folder in content['folders']:
                    folder_copy = folder.copy()
                    sub_path = f"{folder_path}/{folder['name']}" if folder_path != "~" else f"~/{folder['name']}"
                    sub_content = build_folder_content(sub_path)
                    
                    # 将子内容添加到文件夹中
                    folder_copy['files'] = sub_content['files']
                    folder_copy['folders'] = sub_content['folders']
                    enriched_folders.append(folder_copy)
                
                return {
                    'files': content['files'],
                    'folders': enriched_folders
                }
            
            # 从根路径开始构建
            return build_folder_content(root_path)
            
        except Exception as e:
            return {'files': [], 'folders': [], 'error': str(e)}

    def _build_folder_tree(self, folders):
        """构建文件夹树结构，便于显示层次关系"""
        try:
            tree = {}
            
            for folder in folders:
                path_parts = folder['path'].split('/')
                current_level = tree
                
                for i, part in enumerate(path_parts):
                    if part not in current_level:
                        current_level[part] = {
                            'folders': {},
                            'info': None
                        }
                    current_level = current_level[part]['folders']
                
                # 在最终位置添加当前文件夹信息
                current_level[folder['name']] = {
                    'folders': {},
                    'info': {
                        'id': folder['id'],
                        'url': folder['url'],
                        'name': folder['name'],
                        'path': folder['path'],
                        'depth': folder['depth']
                    }
                }
            
            return tree
            
        except Exception as e:
            print(f"构建文件夹树时出错: {e}")
            return {}

    def _generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return f"https://drive.google.com/drive/folders/{folder_id}"

    def _generate_web_url(self, file):
        """为文件生成网页链接"""
        file_id = file['id']
        mime_type = file['mimeType']
        
        if mime_type == 'application/vnd.google.colaboratory':
            # Colab文件
            return f"https://colab.research.google.com/drive/{file_id}"
        elif mime_type == 'application/vnd.google-apps.document':
            # Google文档
            return f"https://docs.google.com/document/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google表格
            return f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.presentation':
            # Google幻灯片
            return f"https://docs.google.com/presentation/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.folder':
            # 文件夹
            return f"https://drive.google.com/drive/folders/{file_id}"
        else:
            # 其他文件（预览或下载）
            return f"https://drive.google.com/file/d/{file_id}/view"

    def cmd_cd(self, path):
        """切换目录"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                path = "~"
            
            # 转换bash扩展的本地路径为远程路径格式
            path = self.main_instance.path_resolver._convert_local_path_to_remote(path)
            
            # 使用新的路径解析器计算绝对路径
            current_shell_path = current_shell.get("current_path", "~")
            absolute_path = self.main_instance.path_resolver.compute_absolute_path(current_shell_path, path)
            
            # 使用cmd_ls验证路径是否存在（与mkdir验证保持一致）
            try:
                # 使用统一的cmd_ls接口检测目录是否存在
                ls_result = self.main_instance.cmd_ls(absolute_path)
                
                if not ls_result.get('success'):
                    return {"success": False, "error": f"Directory does not exist: {path}"}
                
                # 如果ls成功，说明目录存在，使用resolve_path获取目标ID和路径
                target_id, target_path = self.main_instance.resolve_path(path, current_shell)
                
                if not target_id:
                    return {"success": False, "error": f"Directory does not exist: {path}"}
                
            except Exception as e:
                # 如果cmd_ls失败，回退到旧方法
                target_id, target_path = self.main_instance.resolve_path(path, current_shell)
                
                if not target_id:
                    return {"success": False, "error": f"Directory does not exist: {path}"}
            
            # 更新shell状态
            shells_data = self.main_instance.load_shells()
            shell_id = current_shell['id']
            
            shells_data["shells"][shell_id]["current_path"] = target_path
            shells_data["shells"][shell_id]["current_folder_id"] = target_id
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.main_instance.save_shells(shells_data):
                return {
                    "success": True,
                    "new_path": target_path,
                    "folder_id": target_id,
                    "message": f"Switched to directory: {target_path}"
                }
            else:
                return {"success": False, "error": "Save shell state failed"}
                
        except Exception as e:
            return {"success": False, "error": f"Execute cd command failed: {e}"}

    def cmd_mkdir_remote(self, target_path, recursive=False):
        """
        通过远端命令创建目录的接口（使用统一接口）
        
        Args:
            target_path (str): 目标路径
            recursive (bool): 是否递归创建
            
        Returns:
            dict: 创建结果
        """
        try:
            # 获取当前shell以解析相对路径
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 解析绝对路径
            absolute_path = self.main_instance.resolve_remote_absolute_path(target_path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {target_path}"}
            
            # 生成远端mkdir命令，添加清屏和成功/失败提示（总是使用-p确保父目录存在）
            remote_command = f'mkdir -p "{absolute_path}"'
            
            # 准备上下文信息
            context_info = {
                "target_path": target_path,
                "absolute_path": absolute_path,
                "recursive": recursive
            }
            
            # 使用统一接口执行远端命令
            execution_result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if execution_result["success"]:
                # 执行成功后，进行验证以确保目录真正创建（最多60次重试）
                verification_result = self.main_instance.verify_creation_with_ls(target_path, current_shell, creation_type="dir", max_attempts=60)
                
                if verification_result["success"]:
                    # 验证成功，简洁返回，像bash shell一样成功时不显示任何信息
                    return {
                        "success": True,
                        "path": target_path,
                        "absolute_path": absolute_path,
                        "remote_command": remote_command,
                        "message": "",  # 空消息，不显示任何内容
                        "verification": verification_result
                    }
                else:
                    # 验证失败
                    return {
                        "success": False,
                        "error": f"Directory creation may have failed, verification timeout: {target_path}",
                        "verification": verification_result,
                        "remote_command": remote_command
                    }
            else:
                # 执行失败
                return {
                    "success": False,
                    "error": f"mkdir command execution failed: {execution_result.get('error', 'Unknown error')}",
                    "remote_command": remote_command
                }
                
        except Exception as e:
            return {"success": False, "error": f"Execute mkdir command failed: {e}"}

    def cmd_mkdir(self, path, recursive=False):
        """创建目录，通过远程命令界面执行以确保由用户账户创建"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            if not path:
                return {"success": False, "error": "Please specify the directory name to create"}
            
            # 调用统一的mkdir_remote方法
            return self.cmd_mkdir_remote(path, recursive)
                
        except Exception as e:
            return {"success": False, "error": f"Execute mkdir command failed: {e}"}





    def _generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return f"https://drive.google.com/drive/folders/{folder_id}"

    def _generate_web_url(self, file):
        """为文件生成网页链接"""
        file_id = file['id']
        mime_type = file['mimeType']
        
        if mime_type == 'application/vnd.google.colaboratory':
            # Colab文件
            return f"https://colab.research.google.com/drive/{file_id}"
        elif mime_type == 'application/vnd.google-apps.document':
            # Google文档
            return f"https://docs.google.com/document/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google表格
            return f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.presentation':
            # Google幻灯片
            return f"https://docs.google.com/presentation/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.folder':
            # 文件夹
            return f"https://drive.google.com/drive/folders/{file_id}"
        else:
            # 其他文件（预览或下载）
            return f"https://drive.google.com/file/d/{file_id}/view"

    def cmd_touch(self, filename):
        """创建空文件，通过远程命令界面执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            if not filename:
                return {"success": False, "error": "Please specify the file name to create"}
            
            # 解析绝对路径
            current_path = current_shell.get("current_path", "~")
            if filename.startswith("/"):
                # 绝对路径
                absolute_path = filename.replace("~", "/content/drive/MyDrive/REMOTE_ROOT", 1)
            else:
                # 相对路径
                if current_path == "~":
                    current_path = "/content/drive/MyDrive/REMOTE_ROOT"
                else:
                    current_path = current_path.replace("~", "/content/drive/MyDrive/REMOTE_ROOT", 1)
                absolute_path = f"{current_path}/{filename}"
            
            # 生成远端touch命令（创建空文件）
            remote_command = f'touch "{absolute_path}"'
            
            # 准备上下文信息
            context_info = {
                "filename": filename,
                "absolute_path": absolute_path
            }
            
            # 使用统一接口执行远端命令
            execution_result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if execution_result["success"]:
                # 简洁返回，像bash shell一样成功时不显示任何信息
                return {
                    "success": True,
                    "filename": filename,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，不显示任何内容
                    "verification": {"success": True}
                }
            else:
                return execution_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Remote touch command generation failed: {e}"
            }

    def cmd_rm(self, path, recursive=False, force=False):
        """删除文件或目录，通过远程rm命令执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
            
            if not path:
                return {"success": False, "error": "Please specify file or directory to delete"}
            
            # 解析远程绝对路径
            absolute_path = self.main_instance.resolve_remote_absolute_path(path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {path}"}
            
            # 构建rm命令
            rm_flags = ""
            if recursive:
                rm_flags += "r"
            if force:
                rm_flags += "f"
            
            if rm_flags:
                remote_command = f'rm -{rm_flags} "{absolute_path}"'
            else:
                remote_command = f'rm "{absolute_path}"'
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if result["success"]:
                # 简化验证逻辑：如果远程命令执行完成，就认为删除成功
                # 避免复杂的验证逻辑导致误报
                return {
                    "success": True,
                    "path": path,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，像bash shell一样
                }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Error executing rm command: {e}"}

    def cmd_download(self, filename, local_path=None, force=False):
        """
        download命令 - 从Google Drive下载文件并缓存
        用法：
        - download A: 下载到缓存目录，显示哈希文件名
        - download A B: 下载到缓存目录，然后复制到指定位置（类似cp操作）
        - download --force A: 强制重新下载，替换缓存
        """
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent.parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "缓存管理器未找到"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 构建远端绝对路径
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 检查是否已经缓存（如果force=True则跳过缓存检查）
            if not force and cache_manager.is_file_cached(remote_absolute_path):
                cached_info = cache_manager.get_cached_file(remote_absolute_path)
                cached_path = cache_manager.get_cached_file_path(remote_absolute_path)
                
                if local_path:
                    # 如果指定了本地目标，复制缓存文件到目标位置（cp操作）
                    import shutil
                    if os.path.isdir(local_path):
                        # 从原始filename中提取实际文件名（不包含路径部分）
                        actual_filename = os.path.basename(filename)
                        target_path = os.path.join(local_path, actual_filename)
                    else:
                        target_path = local_path
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                    shutil.copy2(cached_path, target_path)
                    
                    return {
                        "success": True,
                        "message": f"Using cached file: {target_path}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "local_path": target_path,
                        "cache_status": cached_info["status"]
                    }
                else:
                    # 只显示缓存信息
                    return {
                        "success": True,
                        "message": f"Using cached file: {cached_info['cache_file']}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "cached_path": cached_path,
                        "cache_status": cached_info["status"]
                    }
            
            # 文件未缓存或强制重新下载
            # 如果是强制模式且文件已缓存，先删除旧缓存
            if force and cache_manager.is_file_cached(remote_absolute_path):
                old_cached_info = cache_manager.get_cached_file(remote_absolute_path)
                old_cache_file = old_cached_info.get("cache_file")
                
                # 删除旧的缓存文件
                cleanup_result = cache_manager.cleanup_cache(remote_absolute_path)
                force_info = {
                    "force_mode": True,
                    "removed_old_cache": cleanup_result.get("success", False),
                    "old_cache_file": old_cache_file
                }
            else:
                force_info = {"force_mode": False}
            
            # 解析路径以获取目标文件夹和文件名
            file_info = None
            target_folder_id = None
            actual_filename = None
            
            # 分析路径：分离目录路径和文件名
            if '/' in filename:
                # 包含路径分隔符，需要解析路径
                path_parts = filename.rsplit('/', 1)  # 从右边分割，只分割一次
                dir_path = path_parts[0] if path_parts[0] else '/'
                actual_filename = path_parts[1]
                
                # 解析目录路径
                target_folder_id, resolved_path = self.main_instance.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    return {"success": False, "error": f"Download failed: directory not found: {dir_path}"}
            else:
                # 没有路径分隔符，在当前目录查找
                target_folder_id = current_shell.get("current_folder_id")
                actual_filename = filename
            
            # 在目标文件夹中查找文件
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if result['success']:
                files = result['files']
                for file in files:
                    if file['name'] == actual_filename:
                        file_info = file
                        break
            
            if not file_info:
                return {"success": False, "error": f"Download failed: file not found: {actual_filename}"}
            
            # 检查是否为文件（不是文件夹）
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"download: {actual_filename}: is a directory, cannot download"}
            
            # 使用Google Drive API直接下载文件
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{actual_filename}") as temp_file:
                temp_path = temp_file.name
            
            try:
                # 使用Google Drive API下载文件内容
                file_id = file_info['id']
                request = self.drive_service.service.files().get_media(fileId=file_id)
                content = request.execute()
                
                # 将内容写入临时文件
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                # 下载成功，缓存文件
                cache_result = cache_manager.cache_file(
                    remote_path=remote_absolute_path,
                    temp_file_path=temp_path
                )
                
                if cache_result["success"]:
                    if local_path:
                        # 如果指定了本地目标，也复制到目标位置（cp操作）
                        import shutil
                        if os.path.isdir(local_path):
                            target_path = os.path.join(local_path, actual_filename)
                        else:
                            target_path = local_path
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                        shutil.copy2(temp_path, target_path)
                        
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {target_path}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"],
                            "local_path": target_path
                        }
                        result.update(force_info)
                        return result
                    else:
                        # 只显示缓存信息
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {cache_result['cache_file']}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"]
                        }
                        result.update(force_info)
                        return result
                else:
                    return {"success": False, "error": f"Download failed: {cache_result.get('error')}"}
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            return {"success": False, "error": f"Download file failed: {e}"}

    def cmd_mv(self, source, destination, force=False):
        """mv命令 - 移动/重命名文件或文件夹（使用远端指令执行）"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            if not source or not destination:
                return {"success": False, "error": "Usage: mv <source> <destination>"}
            
            # 简化版本：不进行复杂的冲突检查
            
            # 构建远端mv命令 - 需要计算绝对路径
            source_absolute_path = self.main_instance.resolve_remote_absolute_path(source, current_shell)
            destination_absolute_path = self.main_instance.resolve_remote_absolute_path(destination, current_shell)
            
            # 构建增强的远端命令，包含成功/失败提示
            base_command = f"mv {source_absolute_path} {destination_absolute_path}"
            remote_command = f"({base_command})"
            
            # 使用远端指令执行接口
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if result.get("success"):
                # 验证文件是否真的被移动了
                verification_result = self.main_instance.verify_creation_with_ls(
                    destination, current_shell, creation_type="file", max_attempts=30
                )
                
                if verification_result.get("success", False):
                    return {
                        "success": True,
                        "source": source,
                        "destination": destination,
                        "message": f""
                    }
                else:
                    return {
                        "success": False,
                        "error": f"mv command execution succeeded but verification failed: {verification_result.get('error', 'Unknown verification error')}"
                    }
            else:
                # 优先使用用户提供的错误信息
                error_msg = result.get('error_info') or result.get('error') or 'Unknown error'
                return {
                    "success": False,
                    "error": f"Remote mv command execution failed: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Execute mv command failed: {e}"}

    def _resolve_file_path(self, file_path, current_shell):
        """解析文件路径，返回文件信息（如果存在）"""
        try:
            # Debug: print(f"🔍 DEBUG: _resolve_file_path called with file_path='{file_path}'")
            # Debug: print(f"🔍 DEBUG: current_shell current_path='{current_shell.get('current_path', 'UNKNOWN')}'")
            # Debug: print(f"🔍 DEBUG: current_shell current_folder_id='{current_shell.get('current_folder_id', 'UNKNOWN')}'")
            
            # 分离目录和文件名
            if "/" in file_path:
                dir_path = "/".join(file_path.split("/")[:-1])
                filename = file_path.split("/")[-1]
                # Debug: print(f"🔍 DEBUG: Path with directory - dir_path='{dir_path}', filename='{filename}'")
            else:
                # 相对于当前目录
                dir_path = "."
                filename = file_path
                # Debug: print(f"🔍 DEBUG: Path without directory - dir_path='{dir_path}', filename='{filename}'")
            
            # 解析目录路径
            if dir_path == ".":
                parent_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
                # Debug: print(f"🔍 DEBUG: Using current directory folder_id='{parent_folder_id}'")
            else:
                parent_folder_id, _ = self.main_instance.resolve_path(dir_path, current_shell)
                # Debug: print(f"🔍 DEBUG: Resolved directory path '{dir_path}' to folder_id='{parent_folder_id}'")
                if not parent_folder_id:
                    # Debug: print(f"🔍 DEBUG: Failed to resolve directory path '{dir_path}'")
                    return None
            
            # 在父目录中查找文件
            # Debug: print(f"🔍 DEBUG: Listing files in folder_id='{parent_folder_id}' looking for filename='{filename}'")
            result = self.drive_service.list_files(folder_id=parent_folder_id, max_results=100)
            # Debug: print(f"🔍 DEBUG: list_files result success={result.get('success')}")
            
            if not result['success']:
                # Debug: print(f"🔍 DEBUG: list_files failed with error: {result.get('error', 'Unknown error')}")
                return None
            
            files = result.get('files', [])
            # Debug: print(f"🔍 DEBUG: Found {len(files)} files in directory")
            for i, file in enumerate(files):
                file_name = file.get('name', 'UNKNOWN')
                # Debug: print(f"🔍 DEBUG: File {i+1}: '{file_name}' (type: {file.get('mimeType', 'UNKNOWN')})")
                if file_name == filename:
                    # Debug: print(f"🔍 DEBUG: ✅ MATCH FOUND! File '{filename}' exists")
                    file['url'] = self._generate_web_url(file)
                    return file
            
            # Debug: print(f"🔍 DEBUG: ❌ File '{filename}' NOT FOUND in {len(files)} files")
            return None
            
        except Exception as e:
            return None

