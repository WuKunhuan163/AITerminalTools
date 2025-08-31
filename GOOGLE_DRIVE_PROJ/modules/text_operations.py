
class TextOperations:
    """
    Text file editing and content operations
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def cmd_download(self, *args, **kwargs):
        """Delegate to file_core for download operations"""
        # Import FileCore for download operations
        from .file_core import FileCore
        file_core = FileCore(self.drive_service, self.main_instance)
        return file_core.cmd_download(*args, **kwargs)
    
    def cmd_upload(self, *args, **kwargs):
        """Delegate to file_core for upload operations"""
        # Import FileCore for upload operations
        from .file_core import FileCore
        file_core = FileCore(self.drive_service, self.main_instance)
        return file_core.cmd_upload(*args, **kwargs)

    def _find_folder(self, folder_name, parent_id):
        """在指定父目录中查找文件夹"""
        try:
            files_result = self.drive_service.list_files(folder_id=parent_id, max_results=100)
            if not files_result['success']:
                return None
            
            for file in files_result['files']:
                if (file['name'] == folder_name and 
                    file['mimeType'] == 'application/vnd.google-apps.folder'):
                    return file
            
            return None
            
        except Exception:
            return None

    def _create_text_file(self, filename, content):
        """通过远程命令创建文本文件"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远程echo命令
            remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
            
            # 使用base64编码来完全避免引号和特殊字符问题
            import base64
            content_bytes = content.encode('utf-8')
            content_base64 = base64.b64encode(content_bytes).decode('ascii')
            
            # 构建远程命令 - 使用base64解码避免所有引号问题
            remote_command = f'echo "{content_base64}" | base64 -d > "{remote_absolute_path}"'
            
            # 使用远程命令执行接口
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if result.get("success"):
                # 验证文件是否真的被创建了
                verification_result = self.main_instance.verify_creation_with_ls(
                    filename, current_shell, creation_type="file", max_attempts=60
                )
                
                if verification_result.get("success", False):
                    return {
                        "success": True,
                        "filename": filename,
                        "message": f"✅ 文件已创建: {filename}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"文件创建命令成功但验证失败: {verification_result.get('error', 'Unknown verification error')}"
                    }
            else:
                # 优先使用用户提供的错误信息
                error_msg = result.get('error_info') or result.get('error') or 'Unknown error'
                return {
                    "success": False,
                    "error": f"创建文件失败: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"创建文件时出错: {e}"}

    def cmd_cat(self, filename):
        """cat命令 - 显示文件内容"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not filename:
                return {"success": False, "error": "请指定要查看的文件"}
            
            # 查找文件
            file_info = self._find_file(filename, current_shell)
            if not file_info:
                return {"success": False, "error": f"File or directory does not exist"}
            
            # 检查是否为文件
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"cat: {filename}: Is a directory"}
            
            # 下载并读取文件内容
            try:
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                request = self.drive_service.service.files().get_media(fileId=file_info['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8', errors='replace')
                return {"success": True, "output": content, "filename": filename}
                
            except Exception as e:
                return {"success": False, "error": f"无法读取文件内容: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cat命令时出错: {e}"}

    def cmd_grep(self, pattern, *filenames):
        """grep命令 - 在文件中搜索模式，支持多文件和regex"""
        import re
        
        try:
            if not pattern:
                return {"success": False, "error": "请指定搜索模式"}
            
            if not filenames:
                return {"success": False, "error": "请指定要搜索的文件"}
            
            # 编译正则表达式
            try:
                regex = re.compile(pattern)
            except re.error as e:
                return {"success": False, "error": f"无效的正则表达式: {e}"}
            
            result = {}
            
            for filename in filenames:
                # 获取文件内容
                cat_result = self.cmd_cat(filename)
                if not cat_result["success"]:
                    result[filename] = {
                        "local_file": None,
                        "occurrences": [],
                        "error": cat_result["error"]
                    }
                    continue
                
                content = cat_result["output"]
                lines = content.split('\n')
                
                # 搜索匹配的位置
                occurrences = {}
                for line_num, line in enumerate(lines, 1):
                    line_matches = []
                    for match in regex.finditer(line):
                        line_matches.append(match.start())
                    if line_matches:
                        occurrences[line_num] = line_matches
                
                # 转换为所需格式: {line_num: [positions]}
                formatted_occurrences = occurrences
                
                # 获取本地缓存文件路径
                local_file = self.main_instance.cache_manager._get_local_cache_path(filename)
                
                result[filename] = {
                    "local_file": local_file,
                    "occurrences": formatted_occurrences
                }
            
            return {"success": True, "result": result}
                
        except Exception as e:
            return {"success": False, "error": f"Grep command failed: {str(e)}"}

    def _find_file(self, filepath, current_shell):
        """查找文件，支持路径解析"""
        try:
            # 如果包含路径分隔符，需要解析路径
            if '/' in filepath:
                # 分离目录和文件名
                dir_path, filename = filepath.rsplit('/', 1)
                
                # 解析目录路径
                target_folder_id, _ = self.main_instance.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    return None
            else:
                # 在当前目录查找
                filename = filepath
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            
            # 列出目标目录内容
            files_result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not files_result['success']:
                return None
            
            # 查找匹配的文件
            for file in files_result['files']:
                if file['name'] == filename:
                    return file
            
            return None
            
        except Exception:
            return None

    def _download_and_get_content(self, filename, remote_absolute_path, force=False):
        """
        下载文件并获取内容（用于read命令）
        
        Args:
            filename (str): 文件名
            remote_absolute_path (str): 远程绝对路径
            force (bool): 是否强制下载并更新缓存
        """
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 解析路径以获取目标文件夹和文件名
            path_parts = remote_absolute_path.strip('/').split('/')
            actual_filename = path_parts[-1]
            
            # 对于绝对路径，需要特殊处理
            if remote_absolute_path.startswith('/content/drive/MyDrive/REMOTE_ROOT/'):
                # 移除前缀，获取相对于REMOTE_ROOT的路径
                relative_path = remote_absolute_path.replace('/content/drive/MyDrive/REMOTE_ROOT/', '')
                relative_parts = relative_path.split('/')
                actual_filename = relative_parts[-1]
                parent_relative_path = '/'.join(relative_parts[:-1]) if len(relative_parts) > 1 else ''
                
                if parent_relative_path:
                    # 转换为~路径格式
                    parent_logical_path = '~/' + parent_relative_path
                    resolve_result = self.main_instance.path_resolver.resolve_path(parent_logical_path, current_shell)
                    if isinstance(resolve_result, tuple) and len(resolve_result) >= 2:
                        target_folder_id, _ = resolve_result
                        if not target_folder_id:
                            return {"success": False, "error": f"无法解析目标路径: {parent_logical_path}"}
                    else:
                        return {"success": False, "error": f"路径解析返回格式错误: {parent_logical_path}"}
                else:
                    # 文件在REMOTE_ROOT根目录
                    target_folder_id = self.main_instance.REMOTE_ROOT_FOLDER_ID
            else:
                # 使用当前shell的文件夹ID
                target_folder_id = current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
            
            # 在目标文件夹中查找文件
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not result['success']:
                return {"success": False, "error": f"无法列出文件夹内容: {result.get('error', '未知错误')}"}
            
            file_info = None
            files = result['files']
            for file in files:
                if file['name'] == actual_filename:
                    file_info = file
                    break
            
            if not file_info:
                return {"success": False, "error": f"File does not exist: {actual_filename}"}
            
            # 检查是否为文件（不是文件夹）
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"{actual_filename} 是一个目录，无法读取"}
            
            # 使用Google Drive API下载文件内容
            try:
                file_id = file_info['id']
                request = self.drive_service.service.files().get_media(fileId=file_id)
                content = request.execute()
                
                # 将字节内容转换为字符串
                if isinstance(content, bytes):
                    try:
                        content_str = content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            content_str = content.decode('gbk')
                        except UnicodeDecodeError:
                            content_str = content.decode('utf-8', errors='replace')
                else:
                    content_str = str(content)
                

                
                return {
                    "success": True,
                    "content": content_str,
                    "file_info": file_info
                }
                
            except Exception as e:
                return {"success": False, "error": f"下载文件内容失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"下载和获取内容时出错: {e}"}

    def _format_read_output(self, selected_lines):
        """
        格式化读取输出
        
        Args:
            selected_lines: 包含(line_number, line_content)元组的列表
            
        Returns:
            str: 格式化后的输出字符串
        """
        if not selected_lines:
            return ""
        
        # 格式化每行，显示行号和内容
        formatted_lines = ["line_num: line_content"]
        for line_num, line_content in selected_lines:
            # 行号从0开始, 0-indexed
            formatted_lines.append(f"{line_num:4d}: {line_content}")
        
        return "\n".join(formatted_lines)

    def _parse_find_args(self, args):
        """解析find命令参数"""
        try:
            args_list = list(args)
            
            # 默认值
            path = "."
            pattern = "*"
            case_sensitive = True
            file_type = None  # None=both, "f"=files, "d"=directories
            
            i = 0
            while i < len(args_list):
                arg = args_list[i]
                
                if arg == "-name" and i + 1 < len(args_list):
                    pattern = args_list[i + 1]
                    case_sensitive = True
                    i += 2
                elif arg == "-iname" and i + 1 < len(args_list):
                    pattern = args_list[i + 1]
                    case_sensitive = False
                    i += 2
                elif arg == "-type" and i + 1 < len(args_list):
                    file_type = args_list[i + 1]
                    if file_type not in ["f", "d"]:
                        return {"success": False, "error": "无效的文件类型，使用 'f' (文件) 或 'd' (目录)"}
                    i += 2
                elif not arg.startswith("-"):
                    # 这是路径参数
                    path = arg
                    i += 1
                else:
                    i += 1
            
            return {
                "success": True,
                "path": path,
                "pattern": pattern,
                "case_sensitive": case_sensitive,
                "file_type": file_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"参数解析错误: {e}"}

    def _recursive_find(self, search_path, pattern, case_sensitive=True, file_type=None):
        """
        递归查找匹配的文件和目录
        
        Args:
            search_path: 搜索路径
            pattern: 搜索模式（支持通配符）
            case_sensitive: 是否大小写敏感
            file_type: 文件类型过滤 ("f" for files, "d" for directories, None for both)
        
        Returns:
            dict: {"success": bool, "files": list, "error": str}
        """
        try:
            import fnmatch
            
            # 解析搜索路径
            if search_path == ".":
                # 使用当前shell路径
                current_shell = self.main_instance.get_current_shell()
                if current_shell:
                    search_path = current_shell.get("current_path", "~")
            
            # 将~转换为实际的REMOTE_ROOT路径
            if search_path.startswith("~"):
                search_path = search_path.replace("~", "/content/drive/MyDrive/REMOTE_ROOT", 1)
            
            # 生成远程find命令
            find_cmd_parts = ["find", f'"{search_path}"']
            
            # 添加文件类型过滤
            if file_type == "f":
                find_cmd_parts.append("-type f")
            elif file_type == "d":
                find_cmd_parts.append("-type d")
            
            # 添加名称模式
            if case_sensitive:
                find_cmd_parts.append(f'-name "{pattern}"')
            else:
                find_cmd_parts.append(f'-iname "{pattern}"')
            
            find_command = " ".join(find_cmd_parts)
            
            # 执行远程find命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", find_command])
            
            if result.get("success"):
                stdout = result.get("stdout", "").strip()
                if stdout:
                    # 分割输出为文件路径列表
                    files = [line.strip() for line in stdout.split("\n") if line.strip()]
                    return {
                        "success": True,
                        "files": files
                    }
                else:
                    return {
                        "success": True,
                        "files": []
                    }
            else:
                return {
                    "success": False,
                    "error": f"Remote find command failed: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error executing find: {e}"
            }

    def cmd_find(self, *args):
        """
        GDS find命令实现，类似bash find
        
        用法:
            find [path] -name [pattern]
            find [path] -iname [pattern]  # 大小写不敏感
            find [path] -type f -name [pattern]  # 只查找文件
            find [path] -type d -name [pattern]  # 只查找目录
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 查找结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "用法: find [path] -name [pattern] 或 find [path] -type [f|d] -name [pattern]"
                }
            
            # 解析参数
            parsed_args = self._parse_find_args(args)
            if not parsed_args["success"]:
                return parsed_args
            
            search_path = parsed_args["path"]
            pattern = parsed_args["pattern"]
            case_sensitive = parsed_args["case_sensitive"]
            file_type = parsed_args["file_type"]  # "f" for files, "d" for directories, None for both
            
            # 递归搜索文件
            results = self._recursive_find(search_path, pattern, case_sensitive, file_type)
            
            if results["success"]:
                found_files = results["files"]
                
                # 格式化输出
                output_lines = []
                for file_path in sorted(found_files):
                    output_lines.append(file_path)
                
                return {
                    "success": True,
                    "files": found_files,
                    "count": len(found_files),
                    "output": "\n".join(output_lines) if output_lines else "No files found matching the pattern."
                }
            else:
                return results
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Find command error: {e}"
            }

    def _generate_edit_diff(self, original_lines, modified_lines, parsed_replacements):
        """
        生成编辑差异信息
        
        Args:
            original_lines: 原始文件行列表
            modified_lines: 修改后文件行列表
            parsed_replacements: 解析后的替换操作列表
            
        Returns:
            dict: 差异信息
        """
        try:
            import difflib
            
            # 生成unified diff
            diff = list(difflib.unified_diff(
                original_lines,
                modified_lines,
                fromfile='original',
                tofile='modified',
                lineterm=''
            ))
            
            # 统计变更信息
            lines_added = len(modified_lines) - len(original_lines)
            changes_count = len(parsed_replacements)
            
            # 生成简化的变更摘要
            changes_summary = []
            for replacement in parsed_replacements:
                if replacement["type"] == "line_range":
                    changes_summary.append(f"Lines {replacement['start_line']}-{replacement['end_line']}: range replacement")
                elif replacement["type"] == "line_insert":
                    changes_summary.append(f"Line {replacement['insert_line']}: content insertion")
                elif replacement["type"] == "text_search":
                    changes_summary.append(f"Text search: '{replacement['old_text'][:50]}...' -> '{replacement['new_text'][:50]}...'")
            
            return {
                "diff_lines": diff,
                "lines_added": lines_added,
                "changes_count": changes_count,
                "changes_summary": changes_summary,
                "original_line_count": len(original_lines),
                "modified_line_count": len(modified_lines)
            }
            
        except Exception as e:
            return {
                "error": f"Failed to generate diff: {e}",
                "diff_lines": [],
                "lines_added": 0,
                "changes_count": 0,
                "changes_summary": []
            }

    def _generate_local_diff_preview(self, filename, original_lines, modified_lines, parsed_replacements):
        """
        生成本地diff预览，只显示修改的部分
        
        Args:
            filename (str): 文件名
            original_lines (list): 原始文件行
            modified_lines (list): 修改后文件行
            parsed_replacements (list): 解析后的替换操作
            
        Returns:
            dict: 包含diff输出和变更摘要
        """
        try:
            import tempfile
            import os
            import subprocess
            import hashlib
            import time
            
            # 创建临时目录
            temp_base_dir = os.path.join(os.path.expanduser("~"), ".local", "bin", "GOOGLE_DRIVE_DATA", "tmp")
            os.makedirs(temp_base_dir, exist_ok=True)
            
            # 生成带时间戳的哈希文件名
            timestamp = str(int(time.time() * 1000))
            content_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
            
            original_filename = f"{content_hash}_{timestamp}_original.tmp"
            modified_filename = f"{content_hash}_{timestamp}_modified.tmp"
            
            original_path = os.path.join(temp_base_dir, original_filename)
            modified_path = os.path.join(temp_base_dir, modified_filename)
            
            try:
                # 写入原始文件
                with open(original_path, 'w', encoding='utf-8') as f:
                    f.writelines(original_lines)
                
                # 写入修改后文件
                with open(modified_path, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
                
                # 执行diff命令
                diff_cmd = ['diff', '-u', original_path, modified_path]
                result = subprocess.run(diff_cmd, capture_output=True, text=True, encoding='utf-8')
                
                # diff命令返回码：0=无差异，1=有差异，2=错误
                if result.returncode == 0:
                    diff_output = "No changes detected"
                elif result.returncode == 1:
                    # 有差异，处理输出
                    diff_lines = result.stdout.splitlines()
                    # 移除文件路径行，只保留差异内容
                    filtered_lines = []
                    for line in diff_lines:
                        if line.startswith('---') or line.startswith('+++'):
                            # 替换临时文件路径为实际文件名
                            if line.startswith('---'):
                                filtered_lines.append(f"--- {filename} (original)")
                            elif line.startswith('+++'):
                                filtered_lines.append(f"+++ {filename} (modified)")
                        else:
                            filtered_lines.append(line)
                    diff_output = '\n'.join(filtered_lines)
                else:
                    diff_output = f"Diff command error: {result.stderr}"
                
                # 生成变更摘要
                changes_summary = []
                for replacement in parsed_replacements:
                    if replacement["type"] == "line_range":
                        changes_summary.append(f"Lines {replacement['start_line']}-{replacement['end_line']}: range replacement")
                    elif replacement["type"] == "line_insert":
                        changes_summary.append(f"Line {replacement['insert_line']}: content insertion")
                    elif replacement["type"] == "text_search":
                        changes_summary.append(f"Text search: '{replacement['old_text'][:50]}...' -> '{replacement['new_text'][:50]}...'")
                
                return {
                    "diff_output": diff_output,
                    "changes_summary": changes_summary,
                    "temp_files_created": [original_path, modified_path]
                }
                
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(original_path):
                        os.unlink(original_path)
                    if os.path.exists(modified_path):
                        os.unlink(modified_path)
                except Exception as cleanup_error:
                    # 清理失败不影响主要功能
                    pass
                    
        except Exception as e:
            return {
                "diff_output": f"Failed to generate diff preview: {str(e)}",
                "changes_summary": [],
                "temp_files_created": []
            }

    def cmd_edit(self, filename, replacement_spec, preview=False, backup=False):
        """
        GDS edit命令 - 支持多段文本同步替换的文件编辑功能
        
        Args:
            filename (str): 要编辑的文件名
            replacement_spec (str): 替换规范，支持多种格式
            preview (bool): 预览模式，只显示修改结果不实际保存
            backup (bool): 是否创建备份文件
            
        Returns:
            dict: 编辑结果
            
        支持的替换格式:
        1. 行号替换: '[[[1, 2], "new content"], [[5, 7], "another content"]]'
        2. 行号插入: '[[[1, null], "content to insert"], [[5, null], "another insert"]]'
        3. 文本搜索替换: '[["old text", "new text"], ["another old", "another new"]]'
        4. 混合模式: '[[[1, 1], "line replacement"], [[3, null], "insertion"], ["text", "replace"]]'
        """
        # Debug信息收集器
        debug_info = []
        # 初始化变量以避免作用域问题
        files_to_upload = []
        
        def debug_log(message):
            debug_info.append(message)
        
        try:
            
            import json
            import re
            import tempfile
            import shutil
            import os
            from datetime import datetime
            
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent.parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "Cache manager not found"}
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 1. 解析替换规范
            try:
                replacements = json.loads(replacement_spec)
                if not isinstance(replacements, list):
                    return {"success": False, "error": "Replacement specification must be an array"}
            except json.JSONDecodeError as e:
                # 提供更有建设性的错误信息
                error_msg = f"JSON parsing failed: {e}\n\n"
                error_msg += "Common issues:\n"
                error_msg += "1. Missing quotes around strings\n"
                error_msg += "2. Unescaped quotes inside strings (use \\\" instead of \")\n" 
                error_msg += "3. Missing commas between array elements\n"
                error_msg += "4. Shell quote conflicts. Try using single quotes around JSON\n\n"
                error_msg += f"Your input: {repr(replacement_spec)}\n"
                error_msg += "Correct format examples:\n"
                error_msg += "  Text replacement: '[[\"old\", \"new\"]]'\n"
                error_msg += "  Line replacement: '[[[1, 3], \"new content\"]]'\n"
                error_msg += "  Mixed: '[[[1, 2], \"line\"], [\"old\", \"new\"]]'"
                return {"success": False, "error": error_msg}
            
            # 2. 下载文件到缓存
            download_result = self.cmd_download(filename, force=True)  # 强制重新下载确保最新内容
            if not download_result["success"]:
                return {"success": False, "error": f"{download_result.get('error')}"}  #TODO
            
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            if not cache_file_path or not os.path.exists(cache_file_path):
                return {"success": False, "error": "Failed to get cache file path"}
            
            # 3. 读取文件内容
            try:
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    original_lines = f.readlines()
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(cache_file_path, 'r', encoding='gbk') as f:
                        original_lines = f.readlines()
                except:
                    return {"success": False, "error": "Unsupported file encoding, please ensure the file is UTF-8 or GBK encoded"}
            except Exception as e:
                return {"success": False, "error": f"Failed to read file: {e}"}
            
            # 4. 解析和验证替换操作
            parsed_replacements = []
            for i, replacement in enumerate(replacements):
                if not isinstance(replacement, list) or len(replacement) != 2:
                    return {"success": False, "error": f"Replacement specification item {i+1} has incorrect format, should be [source, target] format"}
                
                source, target = replacement
                
                if isinstance(source, list) and len(source) == 2:
                    start_line, end_line = source
                    
                    # 检查插入模式：[a, null] 或 [a, ""] 或 [a, None]
                    if end_line is None or end_line == "" or end_line == "null":
                        # 插入模式: [[line_number, null], "content_to_insert"]
                        if not isinstance(start_line, int):
                            return {"success": False, "error": f"Insert mode requires integer line number, got: {start_line}"}
                        
                        if start_line < 0 or start_line > len(original_lines):
                            return {"success": False, "error": f"Insert line number error: {start_line} (valid range: 0-{len(original_lines)}, 0-based index)"}
                        
                        parsed_replacements.append({
                            "type": "line_insert",
                            "insert_after_idx": start_line,
                            "insert_line": start_line,
                            "new_content": target,
                            "original_content": ""  # 插入模式没有原始内容
                        })
                        
                    elif isinstance(start_line, int) and isinstance(end_line, int):
                        # 替换模式: [[start_line, end_line], "new_content"] (0-based, [a, b] 包含语法)
                        # 使用0-based索引，[a, b] 包含语法，与read命令保持一致
                        start_idx = start_line
                        end_idx = end_line  # end_line是inclusive的
                        
                        if start_idx < 0 or start_idx >= len(original_lines) or end_line >= len(original_lines) or start_idx > end_idx:
                            return {"success": False, "error": f"Line number range error: [{start_line}, {end_line}] in file with {len(original_lines)} lines (0-based index)"}
                        
                        parsed_replacements.append({
                            "type": "line_range",
                            "start_idx": start_idx,
                            "end_idx": end_idx,
                            "start_line": start_line,
                            "end_line": end_line,
                            "new_content": target,
                            "original_content": "".join(original_lines[start_idx:end_line + 1]).rstrip()
                        })
                    else:
                        return {"success": False, "error": f"Invalid line specification: [{start_line}, {end_line}]. Use [start, end] for replacement or [line, null] for insertion."}
                    
                elif isinstance(source, str):
                    # 文本搜索替换模式: ["old_text", "new_text"]
                    if source not in "".join(original_lines):
                        return {"success": False, "error": f"Text not found to replace: {source[:50]}..."}
                    
                    parsed_replacements.append({
                        "type": "text_search",
                        "old_text": source,
                        "new_text": target
                    })
                else:
                    return {"success": False, "error": f"Source format for replacement specification item {i+1} is not supported, should be line number array [start, end] or text string"}
            
            # 5. 执行替换和插入操作
            modified_lines = original_lines.copy()
            
            # 先处理插入操作（按行号倒序，避免行号变化影响后续插入）
            line_insertions = [r for r in parsed_replacements if r["type"] == "line_insert"]
            line_insertions.sort(key=lambda x: x["insert_after_idx"], reverse=True)
            
            for insertion in line_insertions:
                insert_after_idx = insertion["insert_after_idx"]
                new_content = insertion["new_content"]
                
                # 将新内容按换行符拆分成行列表，正确处理\n
                if new_content:
                    # 处理换行符，将\n转换为实际换行
                    processed_content = new_content.replace('\\n', '\n')
                    # 处理空格占位符，支持多种格式
                    processed_content = processed_content.replace('_SPACE_', ' ')  # 单个空格
                    processed_content = processed_content.replace('_SP_', ' ')     # 简写形式
                    processed_content = processed_content.replace('_4SP_', '    ') # 4个空格（常用缩进）
                    processed_content = processed_content.replace('_TAB_', '\t')   # 制表符
                    new_lines = processed_content.split('\n')
                    
                    # 确保每行都以换行符结尾
                    formatted_new_lines = []
                    for i, line in enumerate(new_lines):
                        if i < len(new_lines) - 1:  # 不是最后一行
                            formatted_new_lines.append(line + '\n')
                        else:  # 最后一行
                            formatted_new_lines.append(line + '\n')  # 插入的内容总是添加换行符
                    
                    # 在指定行之后插入内容
                    # insert_after_idx = 0 表示在第0行后插入（即第1行之前）
                    # insert_after_idx = len(lines) 表示在文件末尾插入
                    insert_position = insert_after_idx + 1 if insert_after_idx < len(modified_lines) else len(modified_lines)
                    modified_lines[insert_position:insert_position] = formatted_new_lines
            
            # 然后按行号倒序处理行替换，避免行号变化影响后续替换
            line_replacements = [r for r in parsed_replacements if r["type"] == "line_range"]
            line_replacements.sort(key=lambda x: x["start_idx"], reverse=True)
            
            for replacement in line_replacements:
                start_idx = replacement["start_idx"]
                end_idx = replacement["end_idx"]
                new_content = replacement["new_content"]
                
                # 将新内容按换行符拆分成行列表，正确处理\n
                if new_content:
                    # 处理换行符，将\n转换为实际换行
                    processed_content = new_content.replace('\\n', '\n')
                    # 处理空格占位符，支持多种格式
                    processed_content = processed_content.replace('_SPACE_', ' ')  # 单个空格
                    processed_content = processed_content.replace('_SP_', ' ')     # 简写形式
                    processed_content = processed_content.replace('_4SP_', '    ') # 4个空格（常用缩进）
                    processed_content = processed_content.replace('_TAB_', '\t')   # 制表符
                    new_lines = processed_content.split('\n')
                    
                    # 确保每行都以换行符结尾（除了最后一行）
                    formatted_new_lines = []
                    for i, line in enumerate(new_lines):
                        if i < len(new_lines) - 1:  # 不是最后一行
                            formatted_new_lines.append(line + '\n')
                        else:  # 最后一行
                            # 根据原文件的最后一行是否有换行符来决定
                            if end_idx == len(original_lines) and original_lines and not original_lines[-1].endswith('\n'):
                                formatted_new_lines.append(line)  # 不添加换行符
                            else:
                                formatted_new_lines.append(line + '\n')  # 添加换行符
                    
                    # 替换行范围 (使用[a, b]包含语法)
                    modified_lines[start_idx:end_idx + 1] = formatted_new_lines
                else:
                    # 空内容，删除行范围
                    modified_lines[start_idx:end_idx + 1] = []
            
            # 处理文本搜索替换
            text_replacements = [r for r in parsed_replacements if r["type"] == "text_search"]
            if text_replacements:
                file_content = "".join(modified_lines)
                for replacement in text_replacements:
                    file_content = file_content.replace(replacement["old_text"], replacement["new_text"])
                modified_lines = file_content.splitlines(keepends=True)
            
            # 6. 生成结果预览
            diff_info = self._generate_edit_diff(original_lines, modified_lines, parsed_replacements)
            
            if preview:
                # 预览模式：使用diff显示修改内容，不保存文件
                diff_result = self._generate_local_diff_preview(filename, original_lines, modified_lines, parsed_replacements)
                return {
                    "success": True,
                    "mode": "preview",
                    "filename": filename,
                    "original_lines": len(original_lines),
                    "modified_lines": len(modified_lines),
                    "replacements_applied": len(parsed_replacements),
                    "diff_output": diff_result.get("diff_output", ""),
                    "changes_summary": diff_result.get("changes_summary", []),
                    "message": f"📝 预览模式 - 文件: {filename}\n原始行数: {len(original_lines)}, 修改后行数: {len(modified_lines)}\n应用替换: {len(parsed_replacements)} 个"
                }
            
            # 7. 准备临时目录和文件上传列表
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            
            # 从完整路径中提取文件名，保持原始文件名用于替换
            actual_filename = os.path.basename(filename)
            # 使用原始文件名，不添加时间戳，这样upload时会直接替换
            temp_file_path = os.path.join(temp_dir, actual_filename)
            
            files_to_upload = []
            backup_info = {}
            
            if backup:
                # 使用更精确的时间戳避免冲突，包含毫秒
                import time
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') + f"_{int(time.time() * 1000) % 10000:04d}"
                backup_filename = f"{filename}.backup.{timestamp}"
                
                debug_log("Creating backup file for batch upload...")
                # 下载原文件到缓存
                download_result = self.cmd_download(filename, force=True)
                if download_result["success"]:
                    cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
                    if cache_file_path and os.path.exists(cache_file_path):
                        # 创建临时备份文件
                        temp_backup_path = os.path.join(temp_dir, backup_filename)
                        import shutil
                        shutil.copy2(cache_file_path, temp_backup_path)
                        files_to_upload.append(temp_backup_path)
                        debug_log(f"Backup file prepared: {temp_backup_path}")
                        
                        backup_info = {
                            "backup_created": True,
                            "backup_filename": backup_filename,
                            "backup_temp_path": temp_backup_path
                        }
                    else:
                        backup_info = {
                            "backup_created": False,
                            "backup_error": "Failed to get cache file for backup"
                        }
                else:
                    backup_info = {
                        "backup_created": False,
                        "backup_error": f"Failed to download original file for backup: {download_result.get('error')}"
                    }
            
            # 添加修改后的文件到上传列表
            files_to_upload.append(temp_file_path)
            debug_log(f"Files to upload: {files_to_upload}")
            
            # 8. 保存修改后的文件到临时位置，使用原始文件名
            debug_log(f"Using temp_file_path='{temp_file_path}' for original filename='{actual_filename}'")
            
            with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
                temp_file.writelines(modified_lines)
            
            try:
                # 9. 更新缓存
                remote_absolute_path = self.main_instance.resolve_remote_absolute_path(filename, current_shell)
                cache_result = cache_manager.cache_file(remote_absolute_path, temp_file_path)
                
                if not cache_result["success"]:
                    return {"success": False, "error": f"Failed to update cache: {cache_result.get('error')}"}
                
                # 10. 上传修改后的文件，确保缓存状态正确更新
                debug_log(f"About to upload edited file - temp_file_path='{temp_file_path}', filename='{filename}'")
                debug_log(f"temp_file exists: {os.path.exists(temp_file_path)}")
                if os.path.exists(temp_file_path):
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        content_preview = f.read()[:200]
                    debug_log(f"temp_file content preview: {content_preview}...")
                
                # 批量上传所有文件（备份文件+修改后的文件）
                debug_log("Starting batch upload...")
                upload_result = self.cmd_upload(files_to_upload, force=True)
                debug_log(f"Batch upload result: {upload_result}")
                
                if upload_result["success"]:
                    # 生成diff预览用于显示
                    diff_result = self._generate_local_diff_preview(filename, original_lines, modified_lines, parsed_replacements)
                    
                    result = {
                        "success": True,
                        "filename": filename,
                        "original_lines": len(original_lines),
                        "modified_lines": len(modified_lines),
                        "replacements_applied": len(parsed_replacements),
                        "diff": diff_info,
                        "diff_output": diff_result.get("diff_output", ""),
                        "cache_updated": True,
                        "uploaded": True,
                        "message": f"File {filename} edited successfully, applied {len(parsed_replacements)} replacements"
                    }
                    result.update(backup_info)
                    
                    # 如果有备份文件，添加成功信息
                    if backup_info.get("backup_created"):
                        result["message"] += f"\n📋 Backup created: {backup_info['backup_filename']}"
                    
                    # 在编辑完成后运行linter检查
                    try:
                        linter_result = self._run_linter_on_content(''.join(modified_lines), filename)
                        if linter_result.get("has_issues"):
                            result["linter_output"] = linter_result.get("formatted_output", "")
                            result["has_linter_issues"] = True
                        else:
                            result["has_linter_issues"] = False
                    except Exception as e:
                        # Linter failure shouldn't break the edit operation
                        result["linter_error"] = f"Linter check failed: {str(e)}"
                    
                    return result
                else:
                    return {
                        "success": False,
                        "error": f"Failed to upload files: {upload_result.get('error')}",
                        "cache_updated": True,
                        "diff": diff_info,
                        "backup_info": backup_info
                    }
                    
            finally:
                # 清理所有临时文件
                for temp_path in files_to_upload:
                    try:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                            debug_log(f"Cleaned up temp file: {temp_path}")
                    except Exception as cleanup_error:
                        debug_log(f"Failed to cleanup temp file {temp_path}: {cleanup_error}")
            
        except KeyboardInterrupt:
            # 用户中断，输出debug信息
            if debug_info:
                print("\n🔧 DEBUG INFO (due to KeyboardInterrupt):")
                for i, info in enumerate(debug_info, 1):
                    print(f"  {i}. {info}")
            raise  # 重新抛出KeyboardInterrupt
        except Exception as e:
            # 输出debug信息用于异常诊断
            if debug_info:
                print("🔧 DEBUG INFO (due to exception):")
                for i, info in enumerate(debug_info, 1):
                    print(f"  {i}. {info}")
            return {"success": False, "error": f"Edit operation failed: {str(e)}"}

    def _create_backup(self, filename, backup_filename):
        """
        创建文件的备份副本
        
        Args:
            filename (str): 原文件名
            backup_filename (str): 备份文件名
            
        Returns:
            dict: 备份结果
        """
        # 备份debug信息收集器
        backup_debug = []
        
        def backup_debug_log(message):
            backup_debug.append(message)
        
        try:
            backup_debug_log(f"Starting backup: {filename} -> {backup_filename}")
            
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                backup_debug_log("ERROR: No active remote shell")
                return {"success": False, "error": "No active remote shell"}
            
            backup_debug_log(f"Current shell: {current_shell.get('id', 'unknown')}")
            
            # 下载原文件到缓存
            backup_debug_log("Step 1: Downloading original file to cache...")
            download_result = self.cmd_download(filename, force=True)
            backup_debug_log(f"Download result: success={download_result.get('success')}, error={download_result.get('error')}")
            
            if not download_result["success"]:
                if backup_debug:
                    print("🔧 BACKUP DEBUG INFO (download failed):")
                    for i, info in enumerate(backup_debug, 1):
                        print(f"  {i}. {info}")
                return {"success": False, "error": f"Failed to download original file for backup: {download_result.get('error')}"}
            
            import os
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            backup_debug_log(f"Cache file path: {cache_file_path}")
            backup_debug_log(f"Cache file exists: {os.path.exists(cache_file_path) if cache_file_path else False}")
            
            if not cache_file_path or not os.path.exists(cache_file_path):
                if backup_debug:
                    print("🔧 BACKUP DEBUG INFO (cache file not found):")
                    for i, info in enumerate(backup_debug, 1):
                        print(f"  {i}. {info}")
                return {"success": False, "error": "Failed to get cache file path for backup"}
            
            # 上传缓存文件作为备份
            backup_debug_log("Step 2: Creating backup file with correct name...")
            backup_debug_log(f"Cache file path: {cache_file_path}")
            backup_debug_log(f"Backup filename: {backup_filename}")
            
            # 创建临时备份文件，使用正确的文件名
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_backup_path = os.path.join(temp_dir, backup_filename)
            backup_debug_log(f"Temp backup path: {temp_backup_path}")
            
            # 复制缓存文件到临时备份文件
            import shutil
            shutil.copy2(cache_file_path, temp_backup_path)
            backup_debug_log(f"Copied cache to temp backup: {cache_file_path} -> {temp_backup_path}")
            
            try:
                # 上传备份文件
                backup_debug_log("Step 3: Uploading backup file...")
                upload_result = self.cmd_upload([temp_backup_path], force=True)
                backup_debug_log(f"Upload result: success={upload_result.get('success')}, error={upload_result.get('error')}")
                backup_debug_log(f"Upload file_moves: {upload_result.get('file_moves', [])}")
            finally:
                # 清理临时文件
                try:
                    if os.path.exists(temp_backup_path):
                        os.unlink(temp_backup_path)
                        backup_debug_log(f"Cleaned up temp backup file: {temp_backup_path}")
                except Exception as cleanup_error:
                    backup_debug_log(f"Failed to cleanup temp backup file: {cleanup_error}")
            
            if upload_result.get("success", False):
                backup_debug_log("Backup creation completed successfully")
                return {"success": True, "message": f"Backup created: {backup_filename}"}
            else:
                if backup_debug:
                    print("🔧 BACKUP DEBUG INFO (upload failed):")
                    for i, info in enumerate(backup_debug, 1):
                        print(f"  {i}. {info}")
                return {"success": False, "error": f"Failed to create backup: {upload_result.get('error')}"}
                
        except KeyboardInterrupt:
            # 用户中断备份过程
            if backup_debug:
                print("\n🔧 BACKUP DEBUG INFO (due to KeyboardInterrupt):")
                for i, info in enumerate(backup_debug, 1):
                    print(f"  {i}. {info}")
            raise
        except Exception as e:
            return {"success": False, "error": f"Backup creation failed: {str(e)}"}

