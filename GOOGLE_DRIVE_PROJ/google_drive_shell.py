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
try:
    from .google_drive_api import GoogleDriveService
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
except ImportError:
    # 当作为独立模块导入时使用绝对导入
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService
    from GOOGLE_DRIVE_PROJ.modules import (
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
        # 更新数据文件路径到GOOGLE_DRIVE_DATA
        data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
        self.shells_file = data_dir / "shells.json"
        self.config_file = data_dir / "cache_config.json"
        self.deletion_cache_file = data_dir / "deletion_cache.json"  # 新增删除时间缓存文件
        
        # 确保数据目录存在
        data_dir.mkdir(exist_ok=True)
        (data_dir / "remote_files").mkdir(exist_ok=True)
        
        # 直接初始化shell配置（不通过委托）
        self.shells_data = self._load_shells_direct()
        
        # 直接加载缓存配置（不通过委托）
        self._load_cache_config_direct()
        
        # 直接初始化删除时间缓存（不通过委托）
        self.deletion_cache = self._load_deletion_cache_direct()
        
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
        
        # 从config.json动态加载REMOTE_ROOT和REMOTE_ENV
        self._load_paths_from_config()
        
        # 确保所有必要的属性都存在（回退值）
        if not hasattr(self, 'REMOTE_ROOT'):
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        if not hasattr(self, 'REMOTE_ROOT_FOLDER_ID'):
            self.REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"
        
        # 添加虚拟环境管理相关属性
        if not hasattr(self, 'REMOTE_ENV'):
            self.REMOTE_ENV = "/content/drive/MyDrive/REMOTE_ENV"
        if not hasattr(self, 'REMOTE_ENV_FOLDER_ID'):
            self.REMOTE_ENV_FOLDER_ID = "1ZmgwWWIl7qYnGLE66P3kx02M0jxE8D0h"
        
        # 动态挂载点管理：检查是否需要使用动态挂载
        self.current_mount_point = None
        self.dynamic_mode = False
        
        # 先初始化Google Drive API服务
        self.drive_service = self._load_drive_service_direct()
        
        # 然后检查挂载点（需要drive_service进行指纹验证）
        self._check_and_setup_mount_point()

        # 初始化管理器
        self._initialize_managers()

    def _load_shells_direct(self):
        """直接加载远程shell配置（不通过委托）"""
        try:
            if self.shells_file.exists():
                with open(self.shells_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"shells": {}, "active_shell": None}
        except Exception as e:
            print(f"Error: Failed to load shell config: {e}")
            return {"shells": {}, "active_shell": None}

    def _load_cache_config_direct(self):
        """直接加载缓存配置（不通过委托）"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.cache_config = json.load(f)
                    self.cache_config_loaded = True
            else:
                self.cache_config = {}
                self.cache_config_loaded = False
        except Exception as e:
            print(f"Warning: Failed to load cache config: {e}")
            self.cache_config = {}
            self.cache_config_loaded = False

    def _load_deletion_cache_direct(self):
        """直接加载删除时间缓存（不通过委托）"""
        try:
            if self.deletion_cache_file.exists():
                with open(self.deletion_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return cache_data.get("deletion_records", [])
            else:
                return []
        except Exception as e:
            print(f"Warning: Failed to load deletion cache: {e}")
            return []

    def _load_drive_service_direct(self):
        """直接加载Google Drive API服务（不通过委托）"""
        try:
            import sys
            from pathlib import Path
            
            # 添加GOOGLE_DRIVE_PROJ到Python路径
            api_service_path = Path(__file__).parent / "google_drive_api.py"
            if api_service_path.exists():
                sys.path.insert(0, str(api_service_path.parent))
                from google_drive_api import GoogleDriveService
                return GoogleDriveService()
            else:
                return None
        except Exception as e:
            print(f"Warning: Failed to load Google Drive API service: {e}")
            return None

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
    
    def cmd_deps(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_deps(*args, **kwargs)
    
    def cmd_download(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_download(*args, **kwargs)
    
    # cmd_echo 已删除 - 统一使用内置echo处理逻辑
    
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
    
    def cmd_touch(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_touch(*args, **kwargs)
    
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
    
    def cmd_python_code(self, code, save_output=False):
        """执行Python代码 - 委托到file_operations管理器"""
        return self.file_operations.cmd_python(code=code, save_output=save_output)
    
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
    
    def cmd_venv(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_venv(*args, **kwargs)
    
    def cmd_pyenv(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_pyenv(*args, **kwargs)
    
    def cmd_linter(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_linter(*args, **kwargs)
    
    def cmd_pip(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_pip(*args, **kwargs)
    
    def create_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.create_shell(*args, **kwargs)
    
    def execute_generic_command(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        # 检查是否已经在execute_shell_command的队列管理中
        kwargs['_skip_queue_management'] = kwargs.get('_skip_queue_management', False)
        return self.remote_commands.execute_generic_command(*args, **kwargs)
    
    def _verify_mkdir_with_ls(self, *args, **kwargs):
        """委托到verification管理器"""
        return self.verification._verify_mkdir_with_ls(*args, **kwargs)
    
    def verify_creation_with_ls(self, *args, **kwargs):
        """委托到verification管理器"""
        return self.verification.verify_creation_with_ls(*args, **kwargs)
    
    def _display_recursive_ls_result(self, result):
        """显示递归ls命令的结果"""
        try:
            if result.get("mode") == "recursive_bash":
                # 简单模式：类似bash ls -R的输出
                all_items = result.get("all_items", [])
                if not all_items:
                    return
                
                # 按路径分组
                path_groups = {}
                for item in all_items:
                    path = item['path']
                    if path not in path_groups:
                        path_groups[path] = []
                    path_groups[path].append(item)
                
                # Display paths in order
                sorted_paths = sorted(path_groups.keys())
                for i, path in enumerate(sorted_paths):
                    if i > 0:
                        print()  # Empty line to separate different directories
                    
                    print(f"{path}:")
                    items = path_groups[path]
                    
                    # 按名称排序，文件夹优先
                    folders = sorted([f for f in items if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                    other_files = sorted([f for f in items if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                       key=lambda x: x['name'].lower())
                    
                    all_dir_items = folders + other_files
                    
                    for item in all_dir_items:
                        name = item['name']
                        if item['mimeType'] == 'application/vnd.google-apps.folder':
                            print(f"{name}/")
                        else:
                            print(name)
            else:
                # 其他模式的显示逻辑可以在这里添加
                print(f"Recursive ls results (detailed mode):")
                print(f"Path: {result.get('path', 'unknown')}")
                print(f"Total: {result.get('count', 0)} items")
                
        except Exception as e:
            print(f"Error: Error displaying recursive ls results: {e}")
    

    
    def _handle_unified_echo_command(self, args):
        """统一的echo命令处理逻辑 - 支持长内容的base64编码"""
        # 空echo命令
        if not args:
            print(f"")
            return 0
        
        # 检测是否为重定向命令，如果是则统一使用base64编码
        if '>' in args:
            # 计算内容总长度
            content_parts = []
            redirect_found = False
            target_file = None
            
            for i, arg in enumerate(args):
                if arg == '>':
                    redirect_found = True
                    if i + 1 < len(args):
                        target_file = args[i + 1]
                    break
                content_parts.append(arg)
            
            if redirect_found and content_parts and target_file:
                # 检查是否有-e选项并处理转义序列
                enable_escapes = False
                filtered_content_parts = []
                
                for part in content_parts:
                    if part == '-e':
                        enable_escapes = True
                    else:
                        filtered_content_parts.append(part)
                
                # 重组内容
                content = ' '.join(filtered_content_parts)
                
                # 如果启用了转义序列，处理常见的转义字符
                if enable_escapes:
                    content = content.replace('\\n', '\n')
                    content = content.replace('\\t', '\t')
                    content = content.replace('\\r', '\r')
                    content = content.replace('\\\\', '\\')
                
                # 统一使用base64编码的文件创建方法
                result = self.file_operations._create_text_file(target_file, content)
                if result.get("success", False):
                    return 0
                else:
                    error_msg = result.get("error", "File creation failed")
                    print(error_msg)
                    return 1
        
        # 使用通用的远程命令执行机制
        result = self.execute_generic_command('echo', args)
        
        if result.get("success", False):
            # 统一在命令处理结束后打印输出
            stdout = result.get("stdout", "").strip()
            if stdout:
                print(stdout)
            stderr = result.get("stderr", "").strip()
            if stderr:
                print(stderr, file=sys.stderr)
            return 0
        else:
            error_msg = result.get("error", "Echo command failed")
            print(error_msg)
            return 1
    
    def _handle_quoted_echo_redirect(self, shell_cmd_clean):
        """处理引号包围的echo重定向命令，使用base64编码"""
        try:
            # 解析echo命令：echo "content" > filename
            import re
            
            # 使用正则表达式提取内容和文件名
            # 匹配格式：echo "content" > filename 或 echo 'content' > filename
            match = re.match(r'^echo\s+(["\'])(.*?)\1\s*>\s*(.+)$', shell_cmd_clean.strip(), re.DOTALL)
            
            if not match:
                print(f"Error: Unable to parse echo redirect command format")
                return 1
            
            content = match.group(2)
            target_file = match.group(3).strip()
        
            # 使用base64编码的文件创建方法
            result = self.file_operations._create_text_file(target_file, content)
            if result.get("success", False):
                return 0
            else:
                error_msg = result.get("error", "File creation failed")
                print(error_msg)
                return 1
                
        except Exception as e:
            print(f"Error: Error processing quoted echo command: {e}")
            return 1
    
    def _normalize_quotes_and_escapes(self, args):
        """通用引号和转义处理：重组被分割的参数并统一处理转义字符"""
        if not args:
            return args
        
        # 重组参数：将被shell分割的引号包围的字符串重新组合
        reconstructed = []
        temp_parts = []
        in_quoted_string = False
        quote_char = None
        
        for arg in args:
            # 检查是否开始一个引号包围的字符串
            if not in_quoted_string and (arg.startswith('"') or arg.startswith("'")):
                quote_char = arg[0]
                in_quoted_string = True
                temp_parts = [arg]
                
                # 检查是否在同一个参数中结束
                if len(arg) > 1 and arg.endswith(quote_char):
                    # 单个参数完成
                    reconstructed.append(self._process_quoted_string(arg))
                    in_quoted_string = False
                    temp_parts = []
                    quote_char = None
            elif in_quoted_string and arg.endswith(quote_char):
                # 结束引号包围的字符串
                temp_parts.append(arg)
                # 重组完整的字符串
                full_string = ' '.join(temp_parts)
                reconstructed.append(self._process_quoted_string(full_string))
                
                temp_parts = []
                in_quoted_string = False
                quote_char = None
            elif in_quoted_string:
                # 引号字符串中间部分
                temp_parts.append(arg)
            else:
                # 普通参数
                reconstructed.append(arg)
        
        # 如果还有未完成的引号字符串（异常情况）
        if temp_parts:
            reconstructed.extend(temp_parts)
        
        return reconstructed
    
    def _process_quoted_string(self, quoted_string):
        """处理引号包围的字符串：保留外层引号，统一处理转义字符"""
        if not quoted_string:
            return quoted_string
        
        # 保留原始的外层引号（不额外嵌套）
        if ((quoted_string.startswith('"') and quoted_string.endswith('"')) or 
            (quoted_string.startswith("'") and quoted_string.endswith("'"))):
            
            quote_char = quoted_string[0]
            content = quoted_string[1:-1]  # 提取内容
            
            # 统一处理转义字符：将 \\ 变成 \
            # 注意：对于echo命令，我们需要保留\n、\t等转义序列，不要在这里处理它们
            content = content.replace('\\\\', '\\')
            content = content.replace('\\"', '"')
            content = content.replace("\\'", "'")
            
            result = f"{quote_char}{content}{quote_char}"
            return result
        
        return quoted_string
    


    def exit_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.exit_shell(*args, **kwargs)
    
    def generate_mkdir_commands(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.generate_mkdir_commands(*args, **kwargs)
    
    def generate_commands(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.generate_commands(*args, **kwargs)
    
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
    
    def _resolve_absolute_mkdir_path(self, *args, **kwargs):
        """委托到path_resolver管理器"""
        return self.path_resolver._resolve_absolute_mkdir_path(*args, **kwargs)
    
    def save_deletion_cache(self, *args, **kwargs):
        """委托到cache_manager管理器"""
        return self.cache_manager.save_deletion_cache(*args, **kwargs)
    
    def save_shells(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.save_shells(*args, **kwargs)

    def terminate_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.terminate_shell(*args, **kwargs)
    
    def wait_for_file_sync(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.wait_for_file_sync(*args, **kwargs)
    
    def _handle_wildcard_ls(self, wildcard_path):
        """处理包含通配符的ls命令"""
        import fnmatch
        import os.path
        
        try:
            # 分离目录路径和文件名模式
            if '/' in wildcard_path:
                dir_path, pattern = wildcard_path.rsplit('/', 1)
            else:
                dir_path = "."
                pattern = wildcard_path
            
            # 解析目录路径
            current_shell = self.get_current_shell()
            if not current_shell:
                print("Error: 没有活跃的shell会话")
                return 1
            
            if dir_path == ".":
                target_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                display_path = current_shell.get("current_path", "~")
            else:
                target_folder_id, display_path = self.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    print(f"Path not found: {dir_path}")
                    return 1
            
            # 直接使用Google Drive API获取目录内容，避免可能的远程命令调用
            if dir_path == ".":
                folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
            else:
                folder_id, _ = self.resolve_path(dir_path, current_shell)
                if not folder_id:
                    print(f"Path not found: {dir_path}")
                    return 1
            
            # 直接调用Google Drive API
            api_result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
            if not api_result.get('success'):
                print(f"Error: Failed to list directory: {api_result.get('error', 'Unknown error')}")
                return 1
            
            result = {
                "success": True,
                "files": api_result.get('files', []),
                "folders": []  # list_files已经包含了所有类型的项目
            }
            
            if not result.get("success"):
                print(result.get("error", "Error: Failed to list directory"))
                return 1
            
            # 获取所有项目（files字段包含文件和文件夹）
            all_items = result.get("files", [])
            
            # 使用fnmatch进行通配符匹配
            matched_items = []
            for item in all_items:
                item_name = item.get('name', '')
                if fnmatch.fnmatch(item_name, pattern):
                    matched_items.append(item)
            
            # 显示匹配的项目
            if matched_items:
                # 按名称排序，文件夹优先
                folders = [item for item in matched_items if item.get('mimeType') == 'application/vnd.google-apps.folder']
                files = [item for item in matched_items if item.get('mimeType') != 'application/vnd.google-apps.folder']
                
                sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                
                all_sorted_items = sorted_folders + sorted_files
                
                for item in all_sorted_items:
                    name = item.get('name', 'Unknown')
                    if item.get('mimeType') == 'application/vnd.google-apps.folder':
                        print(f"{name}/")
                    else:
                        print(name)
            
            return 0
            
        except Exception as e:
            print(f"Error: Wildcard matching failed: {e}")
            return 1

    def _sync_venv_state_to_local_shell(self, venv_args):
        """同步虚拟环境状态到本地shell配置"""
        try:
            import time
            
            # 检查是否是会改变venv状态的命令
            if not venv_args or venv_args[0] not in ['--activate', '--deactivate']:
                return
            
            # 获取当前shell
            current_shell = self.get_current_shell()
            if not current_shell:
                return
            
            # 使用统一的venv --current接口获取最新状态
            current_result = self.cmd_venv("--current")
            
            if current_result.get("success"):
                # 解析当前激活的环境 - 适配实际的返回格式
                current_env = current_result.get("current")
                # 如果current字段为空或"None"，设置为None
                if current_env == "None" or not current_env:
                    current_env = None
                
                # 更新本地shell状态
                shells_data = self.load_shells()
                shell_id = current_shell['id']
                
                if shell_id in shells_data["shells"]:
                    # 确保venv_state字段存在
                    if "venv_state" not in shells_data["shells"][shell_id]:
                        shells_data["shells"][shell_id]["venv_state"] = {}
                    
                    # 更新虚拟环境状态
                    shells_data["shells"][shell_id]["venv_state"]["active_env"] = current_env
                    shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 保存到本地
                    self.save_shells(shells_data)
                    
        except Exception as e:
            # 如果同步失败，不影响venv命令的正常执行
            pass
    
    def _execute_background_command(self, shell_cmd, command_identifier=None):
        """执行background命令 - 使用echo命令构建，完全避免f-string嵌套引号"""
        import time
        import random
        import base64
        from datetime import datetime
        from modules.constants import get_bg_status_file, get_bg_script_file, get_bg_log_file, get_bg_result_file
        
        # 开始调试后台任务创建
        
        try:
            # 获取当前shell
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 简单的语法检查
            try:
                import subprocess
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
                    temp_file.write(f"#!/bin/bash\n{shell_cmd}")
                    temp_file_path = temp_file.name
                
                result = subprocess.run(['bash', '-n', temp_file_path], capture_output=True, text=True, timeout=5)
                import os
                os.unlink(temp_file_path)
                
                if result.returncode != 0:
                    print(f"Error: Bash syntax error in command: {shell_cmd}")
                    print(f"Error: {result.stderr.strip()}")
                    return 1
            except Exception as e:
                print(f"Warning: Could not check syntax: {e}")
            
            # 生成background PID
            bg_pid = f"{int(time.time())}_{random.randint(1000, 9999)}"
            start_time = datetime.now().isoformat()
            
            # 获取路径信息
            tmp_path = f"{self.REMOTE_ROOT}/tmp"
            
            # 使用常量构建文件名
            status_file = get_bg_status_file(bg_pid)
            script_file = get_bg_script_file(bg_pid)
            log_file = get_bg_log_file(bg_pid)
            result_file = get_bg_result_file(bg_pid)
            
            # 使用base64编码来安全传递命令，避免引号问题
            cmd_b64 = base64.b64encode(shell_cmd.encode('utf-8')).decode('ascii')
            
            # 构建命令使用简单字符串拼接 - 完全避免f-string嵌套引号
            cmd_parts = []
            
            # Part 1: Setup
            cmd_parts.append("# Final solution - NO quote escaping issues")
            cmd_parts.append(f"mkdir -p {tmp_path}")
            cmd_parts.append("")
            
            # Part 2: Create status helper script using simple echo commands
            cmd_parts.append("# Create status helper script using echo (no heredoc)")
            cmd_parts.append(f"echo 'import json, base64, sys' > {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'cmd = base64.b64decode(sys.argv[1]).decode(\"utf-8\")' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'pid = sys.argv[2]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'status_type = sys.argv[3]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'start_time = sys.argv[4]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'status_file = sys.argv[5]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'if status_type == \"starting\":' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    data = {{\"pid\": pid, \"command\": cmd, \"status\": \"starting\", \"start_time\": start_time, \"result_file\": None}}' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'elif status_type == \"running\":' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    real_pid = int(sys.argv[6])' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    result_file = sys.argv[7]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    data = {{\"pid\": pid, \"real_pid\": real_pid, \"command\": cmd, \"status\": \"running\", \"start_time\": start_time, \"result_file\": result_file}}' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'elif status_type == \"completed\":' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    end_time = sys.argv[6]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    exit_code = int(sys.argv[7])' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    result_file = sys.argv[8]' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    data = {{\"pid\": pid, \"command\": cmd, \"status\": \"completed\", \"start_time\": start_time, \"end_time\": end_time, \"exit_code\": exit_code, \"result_file\": result_file}}' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo 'with open(status_file, \"w\") as f:' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append(f"echo '    json.dump(data, f, ensure_ascii=False)' >> {tmp_path}/status_helper_{bg_pid}.py")
            cmd_parts.append("")
            
            # Part 3: Create initial status
            cmd_parts.append("# Create initial status")
            cmd_parts.append(f"python3 {tmp_path}/status_helper_{bg_pid}.py {cmd_b64} {bg_pid} starting {start_time} {tmp_path}/{status_file}")
            cmd_parts.append("")
            
            # Part 4: Create execution script using echo commands
            cmd_parts.append("# Create execution script using echo (no heredoc)")
            cmd_parts.append(f"echo '#!/bin/bash' > {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'set -e' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'echo {cmd_b64} | base64 -d > /tmp/bg_cmd_{bg_pid}.sh' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'chmod +x /tmp/bg_cmd_{bg_pid}.sh' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'bash /tmp/bg_cmd_{bg_pid}.sh > /tmp/bg_stdout_{bg_pid} 2> /tmp/bg_stderr_{bg_pid}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'EXIT_CODE=$?' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'rm -f /tmp/bg_cmd_{bg_pid}.sh' >> {tmp_path}/{script_file}")
            
            # Add result generation using a separate Python script to avoid quote escaping
            cmd_parts.append(f"echo 'cat > {tmp_path}/create_result_{bg_pid}.py << \"RESULT_PYTHON_EOF\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'import json, os, sys' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'from datetime import datetime' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'exit_code = int(sys.argv[1])' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stdout_file = \"/tmp/bg_stdout_{bg_pid}\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stderr_file = \"/tmp/bg_stderr_{bg_pid}\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stdout_content = \"\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'stderr_content = \"\"' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'if os.path.exists(stdout_file):' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    with open(stdout_file, \"r\") as f:' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        stdout_content = f.read()' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'if os.path.exists(stderr_file):' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    with open(stderr_file, \"r\") as f:' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        stderr_content = f.read()' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'result = {{' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    \"success\": exit_code == 0,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    \"data\": {{' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"exit_code\": exit_code,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"stdout\": stdout_content,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"stderr\": stderr_content,' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"working_dir\": os.getcwd(),' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '        \"timestamp\": datetime.now().isoformat()' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    }}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '}}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'with open(\"{tmp_path}/{result_file}\", \"w\") as f:' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo '    json.dump(result, f, indent=2, ensure_ascii=False)' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'RESULT_PYTHON_EOF' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'python3 {tmp_path}/create_result_{bg_pid}.py $EXIT_CODE' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'rm -f {tmp_path}/create_result_{bg_pid}.py' >> {tmp_path}/{script_file}")
            
            # Clean up and update status
            cmd_parts.append(f"echo 'rm -f /tmp/bg_stdout_{bg_pid} /tmp/bg_stderr_{bg_pid}' >> {tmp_path}/{script_file}")
            cmd_parts.append(f"echo 'python3 {tmp_path}/status_helper_{bg_pid}.py {cmd_b64} {bg_pid} completed {start_time} {tmp_path}/{status_file} \"$(date -Iseconds 2>/dev/null || date)\" $EXIT_CODE {result_file}' >> {tmp_path}/{script_file}")
            cmd_parts.append("")
            
            # Part 5: Execute
            cmd_parts.append("# Execute background task")
            cmd_parts.append(f"chmod +x {tmp_path}/{script_file}")
            cmd_parts.append(f"({tmp_path}/{script_file} > {tmp_path}/{log_file} 2>&1) &")
            cmd_parts.append("REAL_PID=$!")
            cmd_parts.append("")
            
            # Part 6: Update status with real PID
            cmd_parts.append("# Update status with real PID")
            cmd_parts.append(f"python3 {tmp_path}/status_helper_{bg_pid}.py {cmd_b64} {bg_pid} running {start_time} {tmp_path}/{status_file} $REAL_PID {result_file}")
            cmd_parts.append("")
            
            # Part 7: Clean up
            cmd_parts.append("# Clean up helper script")
            cmd_parts.append(f"rm -f {tmp_path}/status_helper_{bg_pid}.py")
            
            bg_create_cmd = '\n'.join(cmd_parts)
            
            # 显示生成的命令
            
            # 设置后台模式标志
            current_shell_copy = current_shell.copy()
            current_shell_copy["_background_mode"] = True
            current_shell_copy["_background_pid"] = bg_pid
            current_shell_copy["_background_original_cmd"] = shell_cmd
            
            # 使用统一的命令执行接口
            # 执行背景命令
            result = self.remote_commands.execute_unified_command(
                user_command=bg_create_cmd,
                result_filename=None,
                current_shell=current_shell_copy,
                skip_quote_escaping=True
            )
            
            # 显示执行结果
            
            # 处理统一接口的结果
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                
                # 显示后台任务信息
                print(f"Background task started with ID: {bg_pid}")
                print(f"Command: {shell_cmd}")
                print("")
                print("Run the following commands to track the background task status:")
                print(f"  GDS --bg --status {bg_pid}    # Check task status")
                print(f"  GDS --bg --result {bg_pid}    # View task result")
                print(f"  GDS --bg --log {bg_pid}       # View task log")
                print(f"  GDS --bg --cleanup {bg_pid}   # Clean up task files")
                
                return 0
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"Error: Failed to create background task: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error executing background command: {e}")
            return 1

    def execute_shell_command_with_args(self, args, command_identifier=None):
        """执行shell命令 - 直接使用参数列表，避免双重解析"""
        if not args:
            return 0
        
        cmd = args[0]
        cmd_args = args[1:]
        
        # 直接处理命令，跳过字符串解析
        if cmd == 'ls':
            # 解析ls命令的参数
            recursive = False
            detailed = False
            force_mode = False  # -f选项
            directory_mode = False  # -d选项：显示目录本身而不是内容
            paths = []  # 支持多个路径
            
            for arg in cmd_args:
                if arg == '-R':
                    recursive = True
                elif arg == '--detailed':
                    detailed = True
                elif arg == '-f':
                    force_mode = True
                elif arg == '-d':
                    directory_mode = True
                elif not arg.startswith('-'):
                    paths.append(arg)
            
            # 单个路径或无路径的情况，直接使用cmd_ls
            if len(paths) <= 1 and not recursive and not force_mode and not directory_mode:
                path = paths[0] if paths else None
                result = self.cmd_ls(path=path, detailed=detailed, recursive=recursive, show_hidden=False)
                
                if result.get("success"):
                    files = result.get("files", [])
                    folders = result.get("folders", [])
                    all_items = folders + files
                    
                    if all_items:
                        # 按名称排序，文件夹优先
                        sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                        sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                        
                        # 合并列表，文件夹在前
                        all_sorted_items = sorted_folders + sorted_files
                        
                        # 简单的列表格式，类似bash ls
                        for item in all_sorted_items:
                            name = item.get('name', 'Unknown')
                            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                                print(f"{name}/")
                            else:
                                print(name)
                    
                    return 0
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"Failed to list files: {error_msg}")
                    return 1
            else:
                # 多路径或特殊选项，回退到字符串命令
                shell_cmd = cmd + ' ' + ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd_args)
                return self.execute_shell_command(shell_cmd, command_identifier)
        else:
            # 其他命令，回退到字符串命令
            shell_cmd = cmd + ' ' + ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd_args)
            return self.execute_shell_command(shell_cmd, command_identifier)

    def execute_shell_command(self, shell_cmd, command_identifier=None):
        """执行shell命令 - 使用WindowManager的新架构入口点"""
        
        # 保存原始用户命令，用于后续的文件验证分析
        self._original_user_command = shell_cmd.strip()
        try:
            is_quoted_command = shell_cmd.startswith("__QUOTED_COMMAND__")
            if is_quoted_command:
                shell_cmd = shell_cmd[len("__QUOTED_COMMAND__"):]
            
            # 首先检测引号包围的完整命令（在命令解析之前）
            shell_cmd_clean = shell_cmd.strip()
            if ((shell_cmd_clean.startswith("'") and shell_cmd_clean.endswith("'")) or 
                (shell_cmd_clean.startswith('"') and shell_cmd_clean.endswith('"'))):
                # 去除外层引号，这是一个完整的远程命令
                shell_cmd_clean = shell_cmd_clean[1:-1]
                shell_cmd = shell_cmd_clean  # 更新shell_cmd以便后续使用
                is_quoted_command = True  # 设置引号命令标记
                
                # 特殊处理：引号包围的echo重定向命令
                if shell_cmd_clean.strip().startswith('echo ') and '>' in shell_cmd_clean:
                    return self._handle_quoted_echo_redirect(shell_cmd_clean)

            # 首先检查特殊命令（不需要远程执行）
            if shell_cmd_clean in ['--help', '-h', 'help']:
                # 显示本地帮助信息，不触发远程窗口
                try:
                    from modules.help_system import show_unified_help
                    return show_unified_help(context="shell", command_identifier=command_identifier)
                except ImportError:
                    # 回退到基本帮助
                    help_text = """GDS (Google Drive Shell) - Available Commands:

Navigation:
  pwd                         - Show current directory
  ls [path] [--detailed] [-R] - List directory contents
  cd <path>                   - Change directory

File Operations:
  mkdir [-p] <dir>            - Create directory
  rm <file>                   - Remove file
  rm -rf <dir>                - Remove directory recursively
  cp <src> <dst>              - Copy file/directory
  mv <src> <dst>              - Move/rename file/directory

Text Operations:
  cat <file>                  - Display file contents
  echo <text>                 - Display text
  edit <file> [options]       - Edit file content

Background Tasks:
  --bg <command>              - Run command in background
  --status [task_id]          - Show task status
  --log <task_id>             - Show task log
  --result <task_id>          - Show task result

Other:
  help, --help, -h            - Show this help
  exit                        - Exit shell mode

For more information, visit: https://github.com/your-repo/gds"""
                    print(help_text)
                    return 0
            

            # 检查background选项
            background_mode = False
            background_options = ['--background', '--bg', '--async']
            for bg_option in background_options:
                if shell_cmd_clean.startswith(bg_option + ' ') or shell_cmd_clean == bg_option:
                    background_mode = True
                    remaining_cmd = shell_cmd_clean[len(bg_option):].strip()
                    
                    # 处理--bg的子命令
                    if remaining_cmd.startswith('--status'):
                        # GDS --bg --status [task_id]
                        status_args = remaining_cmd[8:].strip()  # 移除--status
                        if status_args:
                            return self._show_background_status(status_args, command_identifier)
                        else:
                            return self._show_all_background_status(command_identifier)
                    elif remaining_cmd.startswith('--log '):
                        # GDS --bg --log <task_id>
                        task_id = remaining_cmd[6:].strip()  # 移除--log 
                        return self._show_background_log(task_id, command_identifier)
                    elif remaining_cmd.startswith('--result '):
                        # GDS --bg --result <task_id>
                        task_id = remaining_cmd[9:].strip()  # 移除--result 
                        return self._show_background_result(task_id, command_identifier)
                    elif remaining_cmd.startswith('--cleanup'):
                        # GDS --bg --cleanup [task_id]
                        cleanup_args = remaining_cmd[9:].strip()  # 移除--cleanup
                        if cleanup_args:
                            return self._cleanup_background_task(cleanup_args, command_identifier)
                        else:
                            return self._cleanup_background_tasks(command_identifier)
                    elif remaining_cmd.startswith('--wait '):
                        # GDS --bg --wait <task_id>
                        task_id = remaining_cmd[7:].strip()  # 移除--wait 
                        return self._wait_background_task(task_id, command_identifier)
                    elif remaining_cmd == '':
                        # 只有--bg，显示帮助
                        print("GDS Background Commands:")
                        print("  --bg <command>           # Run command in background")
                        print("  --bg --status [task_id]  # Show task status")
                        print("  --bg --log <task_id>     # Show task log")
                        print("  --bg --result <task_id>  # Show task result")
                        print("  --bg --wait <task_id>    # Wait for task")
                        print("  --bg --cleanup [task_id] # Clean up tasks")
                        print("")
                        print("Alternative short forms:")
                        print("  --status [task_id]       # Show task status")
                        print("  --log <task_id>          # Show task log")
                        print("  --result <task_id>       # Show task result")
                        print("  --wait <task_id>         # Wait for task")
                        print("  --cleanup [task_id]      # Clean up tasks")
                        return 0
                    else:
                        # 执行background命令
                        return self._execute_background_command(remaining_cmd, command_identifier)
                    break
            
            # 解析命令 - 对edit命令特殊处理
            if shell_cmd_clean.strip().startswith('edit '):
                # 使用新的用户友好的edit命令解析器
                return self._handle_edit_command(shell_cmd_clean.strip())
            else:
                # 特殊处理python -c命令，避免shlex破坏Python代码中的引号
                if shell_cmd_clean.strip().startswith('python -c '):
                    # 对于python -c命令，手动分割以保护Python代码中的引号
                    cmd = 'python'
                    # 提取-c后面的所有内容作为Python代码
                    python_code = shell_cmd_clean.strip()[len('python -c '):].strip()
                    
                    # 去掉外层的引号（如果存在）
                    if python_code.startswith('"') and python_code.endswith('"'):
                        python_code = python_code[1:-1]
                    elif python_code.startswith("'") and python_code.endswith("'"):
                        python_code = python_code[1:-1]
                    
                    args = ['-c', python_code]

                else:
                    # 使用接口化的命令解析
                    parse_result = self._parse_shell_command(shell_cmd_clean)
                    if not parse_result["success"]:
                        print(f"Error: {parse_result['error']}")
                        return 1
                    cmd = parse_result["cmd"]
                    args = parse_result["args"]
                    
                    # 显示警告信息（如果有）
                    if "warning" in parse_result:
                        print(f"Warning: {parse_result['warning']}")
            
            # 对所有命令应用通用引号和转义处理
            if args:
                args = self._normalize_quotes_and_escapes(args)
            
            # 特殊处理BACKGROUND_CMD命令
            if cmd == "BACKGROUND_CMD":
                # 将BACKGROUND_CMD转换为GDS的--bg格式，自动引号包围
                if args:
                    # 自动将所有参数合并并引号包围
                    bg_command = ' '.join(str(arg) for arg in args)
                    # 如果命令包含特殊字符，确保正确处理
                    return self.execute_shell_command(f"--bg {bg_command}", command_identifier)
                else:
                    print("Usage: BACKGROUND_CMD <command>")
                    print("Example: BACKGROUND_CMD echo hello world")
                    print("Note: No need to add quotes around the command")
                    return 1
            
            # 检查是否包含多命令组合（&&、||或|），但要避免引号内的操作符
            has_multiple_ops = False
            for op in [' && ', ' || ', ' | ']:
                if op in shell_cmd:
                    # 检查操作符是否在引号外
                    if self._is_operator_outside_quotes(shell_cmd, op):
                        has_multiple_ops = True
                        break
            
            if has_multiple_ops:
                # 导入shell_commands模块中的具体函数
                import os
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from shell_commands import handle_multiple_commands
                return handle_multiple_commands(shell_cmd, command_identifier)
            
            # 如果不是多命令，继续执行原来的单命令逻辑
            # 这里应该继续原来execute_shell_command的逻辑
            if cmd == 'pwd':
                # 导入shell_commands模块中的具体函数
                import os
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from shell_commands import shell_pwd
                return shell_pwd(command_identifier)
            elif cmd == 'ls':
                
                # 解析ls命令的参数
                recursive = False
                detailed = False
                force_mode = False  # -f选项
                directory_mode = False  # -d选项：显示目录本身而不是内容
                paths = []  # 支持多个路径
                
                for arg in args:
                    if arg == '-R':
                        recursive = True
                    elif arg == '--detailed':
                        detailed = True
                    elif arg == '-f':
                        force_mode = True
                    elif arg == '-d':
                        directory_mode = True
                    elif not arg.startswith('-'):
                        paths.append(arg)
                
                # 修复shell展开的家目录路径问题
                import os
                local_home = os.path.expanduser("~")
                fixed_paths = []
                for path in paths:
                    if path and path.startswith('/Users/') and path.startswith(local_home):
                        # 将本地家目录路径转换为远程路径格式
                        relative_path = path[len(local_home):].lstrip('/')
                        if relative_path:
                            fixed_paths.append(f"~/{relative_path}")
                        else:
                            fixed_paths.append("~")
                    else:
                        fixed_paths.append(path)
                paths = fixed_paths
                
                # 检查是否有通配符模式
                has_wildcards = any('*' in path or '?' in path or '[' in path or ']' in path for path in paths)
                
                # 如果有通配符，使用本地匹配而不是远程命令（避免后台模式问题）
                if has_wildcards and len(paths) == 1 and not recursive and not force_mode and not directory_mode:
                    # 处理单个通配符路径
                    wildcard_path = paths[0]
                    return self._handle_wildcard_ls(wildcard_path)
                
                # 如果有多个路径、使用了-R/-f/-d选项，使用远端命令执行
                if len(paths) > 1 or recursive or force_mode or directory_mode:
                    # 构建ls命令参数
                    cmd_args = []
                    if recursive:
                        cmd_args.append("-R")
                    if force_mode:
                        cmd_args.append("-f")
                    if directory_mode:
                        cmd_args.append("-d")
                    cmd_args.extend(paths)
                    
                    # 直接调用远程命令处理，绕过特殊命令检查
                    try:
                        current_shell = self.get_current_shell()
                        if not current_shell:
                            print(f"Error: 没有活跃的shell会话")
                            return 1
                        
                        # 生成远程命令
                        remote_command_info = self.remote_commands._generate_command("ls", cmd_args, current_shell)
                        remote_command, result_filename = remote_command_info
                        
                        # 显示远程命令窗口
                        options_str = " ".join(opt for opt in ["-R" if recursive else "", "-f" if force_mode else "", "-d" if directory_mode else ""] if opt)
                        paths_str = " ".join(paths) if paths else ""
                        title = f"GDS Remote Command: ls {options_str} {paths_str}".strip()
                        instruction = f"Command: ls {options_str} {paths_str}\n\nPlease execute the following command in your remote environment:"
                        
                        result = self.remote_commands.show_command_window_subprocess(  # WARNING: BYPASSING QUEUE SYSTEM
                            title=title,
                            command_text=remote_command,
                            timeout_seconds=300
                        )
                        
                        # 处理结果，模拟execute_generic_command的逻辑
                        if result["action"] == "success":
                            # 等待并读取结果文件
                            result_data = self.remote_commands._wait_and_read_result_file(result_filename)
                            if result_data.get("success"):
                                # 显示stdout内容（ls -R的输出）
                                stdout_content = result_data.get("data", {}).get("stdout", "")
                                if stdout_content:
                                    print(stdout_content)
                                return 0
                            else:
                                print(result_data.get("error", "Error: 读取结果失败"))
                                return 1
                        elif result["action"] == "direct_feedback":
                            # 处理直接反馈
                            print()  # shift a newline since ctrl+D
                            debug_info = {
                                "cmd": "ls",
                                "args": cmd_args,
                                "result_filename": result_filename
                            }
                            try:
                                feedback_result = self.remote_commands.direct_feedback(remote_command, debug_info)
                                if feedback_result.get("success", False):
                                    return 0
                                else:
                                    print(feedback_result.get("error", "Error: 处理直接反馈失败"))
                                    return 1
                            except Exception as e:
                                print(f"Error: 处理直接反馈时出错: {e}")
                                return 1
                        else:
                            print(result.get("error", "Error: ls -R command execution failed"))
                            return 1
                    except Exception as e:
                        print(f"Error: ls -R command execution failed: {e}")
                        import traceback
                        traceback.print_exc()
                        return 1
                else:
                    # 单个路径或无路径的情况，直接使用cmd_ls
                    path = paths[0] if paths else None
                    result = self.cmd_ls(path=path, detailed=detailed, recursive=recursive, show_hidden=False)
                    
                    if result.get("success"):
                        files = result.get("files", [])
                        folders = result.get("folders", [])
                        all_items = folders + files
                        
                        if all_items:
                            # 按名称排序，文件夹优先
                            sorted_folders = sorted(folders, key=lambda x: x.get('name', '').lower())
                            sorted_files = sorted(files, key=lambda x: x.get('name', '').lower())
                            
                            # 合并列表，文件夹在前
                            all_sorted_items = sorted_folders + sorted_files
                            
                            # 简单的列表格式，类似bash ls
                            for item in all_sorted_items:
                                name = item.get('name', 'Unknown')
                                if item.get('mimeType') == 'application/vnd.google-apps.folder':
                                    print(f"{name}/")
                                else:
                                    print(name)
                        
                        return 0
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        print(f"Failed to list files: {error_msg}")
                        return 1
            elif cmd == 'cd':
                if not args:
                    print(f"Error: cd command needs a path")
                    return 1
                # 使用file_operations中的cmd_cd方法
                path = args[0]
                result = self.cmd_cd(path)
                if result.get("success"):
                    # cd命令成功时不显示输出（像bash一样）
                    return 0
                else:
                    print(result.get("error", "Error: cd command execution failed"))
                    return 1
            elif cmd == 'mkdir':
                if not args:
                    print(f"Error: mkdir command needs a directory name")
                    return 1
                # 导入shell_commands模块中的具体函数
                import os
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                # 使用file_operations中的cmd_mkdir方法（通过远程命令执行）
                recursive = '-p' in args
                dir_names = [arg for arg in args if arg != '-p']
                if not dir_names:
                    print(f"Error: mkdir command needs directory name(s)")
                    return 1
                
                # 支持多个目录创建 - 使用单个远端命令提高效率
                if len(dir_names) == 1:
                    # 单个目录，直接调用
                    result = self.cmd_mkdir(dir_names[0], recursive)
                    if result.get("success"):
                        return 0
                    else:
                        error_msg = result.get("error", "Error: mkdir command execution failed")
                        print(error_msg)
                        return 1
                else:
                    # 多个目录，合并为单个远端命令
                    current_shell = self.get_current_shell()
                    if not current_shell:
                        print(f"Error: no active remote shell")
                        return 1
                    
                    # 构建合并的mkdir命令
                    mkdir_prefix = "mkdir -p" if recursive else "mkdir"
                    absolute_paths = []
                    for dir_name in dir_names:
                        abs_path = self.resolve_remote_absolute_path(dir_name, current_shell)
                        absolute_paths.append(abs_path)
                    
                    # 使用&&连接多个mkdir命令
                    combined_command = " && ".join([f'{mkdir_prefix} "{path}"' for path in absolute_paths])
                    
                    # 执行合并的命令
                    result = self.execute_generic_command("bash", ["-c", combined_command])
                    
                    if result.get("success"):
                        # 验证所有目录都被创建了
                        all_verified = True
                        for dir_name in dir_names:
                            verification_result = self.verify_creation_with_ls(
                                dir_name, current_shell, creation_type="dir", max_attempts=60
                            )
                            if not verification_result.get("success", False):
                                print(f"Error: Directory {dir_name} verification failed")
                                all_verified = False
                        
                        return 0 if all_verified else 1
                    else:
                        error_msg = result.get("error", "Multiple directory creation failed")
                        print(f"Error: {error_msg}")
                        return 1
            elif cmd == 'touch':
                if not args:
                    print(f"Error: touch command needs a filename")
                    return 1
                
                filename = args[0]
                
                # 调用cmd_touch方法
                result = self.cmd_touch(filename)
                if result.get("success"):
                    return 0
                else:
                    print(result.get("error", "Error: touch command execution failed"))
                    return 1

            elif cmd == 'echo':
                # 简化的echo处理：直接使用统一的echo命令处理
                return self._handle_unified_echo_command(args)
            elif cmd == 'help':
                # 导入shell_commands模块中的具体函数
                import os
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from modules.shell_commands import shell_help
                return shell_help(command_identifier)
            elif cmd == 'venv':
                # 使用委托方法处理venv命令
                result = self.cmd_venv(*args)
                if result.get("success", False):
                    # venv命令成功后，同步更新本地shell状态
                    self._sync_venv_state_to_local_shell(args)
                    return 0
                else:
                    error_message = result.get("error", "Virtual environment operation failed")
                    print(error_message)
            elif cmd == 'pyenv':
                # 使用委托方法处理pyenv命令
                result = self.cmd_pyenv(*args)
                if result.get("success", False):
                    return 0
                else:
                    error_message = result.get("error", "Python version management operation failed")
                    print(error_message)
            elif cmd == 'cleanup-windows':
                # 手动清理窗口命令
                force = '--force' in args
                try:
                    from modules.window_manager import get_window_manager
                    manager = get_window_manager()
                    
                    # 获取清理前的窗口数量
                    before_count = manager.get_active_windows_count()
                    print(f"清理前活跃窗口数量: {before_count}")
                    
                    # 执行清理
                    manager.cleanup_windows(force=force)
                    
                    # 等待一下再检查
                    import time
                    time.sleep(1)
                    after_count = manager.get_active_windows_count()
                    print(f"清理后活跃窗口数量: {after_count}")
                    
                    if before_count > 0 and after_count == 0:
                        print("窗口清理成功")
                    elif before_count == 0:
                        print("ℹ️ 没有需要清理的窗口")
                    elif after_count < before_count:
                        print(f"部分窗口清理成功 (清理了 {before_count - after_count} 个窗口)")
                    else:
                        print("⚠️ 窗口清理可能未完全成功")
                    
                    return 0
                except Exception as e:
                    print(f"Error: 窗口清理失败: {e}")
                    return 1
                    
                    # 显示stderr如果存在
                    stderr = result.get("stderr", "")
                    if stderr.strip():
                        print(f"\nError: STDERR content:\n{stderr.strip()}")
                    
                    # 显示用户错误信息（如果有）
                    user_error = result.get("user_error_info", "")
                    if user_error:
                        print(f"\nError: User provided content:\n{user_error}")
                    
                    return 1
            elif cmd == 'linter':
                # 使用委托方法处理linter命令
                result = self.cmd_linter(*args)
                if result.get("success", False):
                    print(result.get("output", "Linting completed"))
                    return 0 if not result.get("has_errors", False) else 1
                else:
                    error_message = result.get("error", "Linter operation failed")
                    print(error_message)
                    return 1
            elif cmd == 'pip':
                # 使用委托方法处理pip命令
                result = self.cmd_pip(*args)
                if result.get("success", False):
                    message = result.get("message", "")
                    if message.strip():  # 只有当message不为空时才打印
                        print(message)
                    return 0
                else:
                    print(result.get("error", "Pip operation failed"))
                    return 1
            elif cmd == 'deps':
                # 使用委托方法处理依赖分析命令
                result = self.cmd_deps(*args)
                if result.get("success", False):
                    message = result.get("message", "")
                    if message.strip():  # 只有当message不为空时才打印
                        print(message)
                    return 0
                else:
                    print(result.get("error", "Dependency analysis failed"))
                    return 1
            elif cmd == 'cat':
                # 使用委托方法处理cat命令
                if not args:
                    print(f"Error: cat command needs a file name")
                    return 1
                result = self.cmd_cat(args[0])
                if result.get("success", False):
                    if not result.get("direct_feedback", False):
                        print(result.get("output", ""))
                    return 0
                else:
                    print(result.get("error", "Failed to read file"))
                    return 1
            elif cmd == 'edit':
                # 使用委托方法处理edit命令
                if len(args) < 2:
                    print(f"Error: edit command needs a file name and edit specification")
                    return 1
                
                # 解析选项参数
                preview = False
                backup = False
                remaining_args = []
                
                for arg in args:
                    if arg == '--preview':
                        preview = True
                    elif arg == '--backup':
                        backup = True
                    else:
                        remaining_args.append(arg)
                
                if len(remaining_args) < 2:
                    print(f"Error: edit command needs a file name and edit specification")
                    return 1
                    
                filename = remaining_args[0]
                # 对于edit命令，JSON参数不能用空格连接，需要从原始命令中提取
                # 使用正则表达式从原始shell_cmd中提取JSON部分
                import re
                # 构建选项字符串用于匹配
                options_pattern = ""
                if preview:
                    options_pattern += r"(?:--preview\s+)?"
                if backup:
                    options_pattern += r"(?:--backup\s+)?"
                
                # 匹配命令：edit [options] filename JSON_spec
                pattern = rf'^edit\s+{options_pattern}(\S+)\s+(.+)$'
                match = re.search(pattern, shell_cmd)
                if match:
                    edit_spec = match.group(2)  # 直接提取JSON部分，不做空格连接
                else:
                    # 回退方案：如果只有一个JSON参数，直接使用
                    if len(remaining_args) == 2:
                        edit_spec = remaining_args[1]
                    else:
                        # 多个参数时，可能是引号被分割了，尝试重新组合
                        edit_spec = ' '.join(remaining_args[1:])
                
                try:
                    result = self.cmd_edit(filename, edit_spec, preview=preview, backup=backup)
                except KeyboardInterrupt:
                    result = {"success": False, "error": "Operation interrupted by user"}
                
                if result.get("success", False):
                    # 显示diff比较（预览模式和正常模式都显示）
                    diff_output = result.get("diff_output", "")
                    
                    if diff_output and diff_output != "No changes detected":
                        print(f"\nEdit comparison: {filename}")
                        print(f"=" * 50)
                        
                        # 过滤diff输出，移除文件头和行号信息
                        diff_lines = diff_output.splitlines()
                        filtered_lines = []
                        for line in diff_lines:
                            # 跳过文件头行（--- 和 +++）
                            if line.startswith('---') or line.startswith('+++'):
                                continue
                            # 跳过行号信息行（@@）
                            if line.startswith('@@'):
                                continue
                            filtered_lines.append(line)
                        
                        # 显示过滤后的diff内容
                        if filtered_lines:
                            print('\n'.join(filtered_lines))
                        print(f"=" * 50)
                    elif diff_output == "No changes detected":
                        print(f"No changes detected")
                    
                    # 对于正常模式，显示成功信息
                    if result.get("mode") != "preview":
                        print(result.get("message", "\nFile edited successfully"))
                    
                    # 显示linter结果（如果有）
                    if result.get("has_linter_issues"):
                        print(f"=" * 50)
                        linter_output = result.get("linter_output", "")
                        total_issues = linter_output.count("ERROR:") + linter_output.count("WARNING:")
                        print(f"{total_issues} linter warnings or errors found:")
                        print(linter_output)
                        print(f"=" * 50)
                    elif result.get("linter_error"):
                        print(f"=" * 50)
                        print(f"Linter check failed: {result.get('linter_error')}")
                        print(f"=" * 50)
                    elif result.get("has_linter_issues") == False:
                        # Only show "no issues" message if linter actually ran
                        pass  # No need to show anything for clean files
                    
                    return 0
                else:
                    print(result.get("error", "Failed to edit file"))
                    return 1
            elif cmd == 'read':
                # 使用委托方法处理read命令
                if not args:
                    print(f"Error: read command needs a file name")
                    return 1
                
                # 解析--force标志
                force = False
                remaining_args = []
                
                for arg in args:
                    if arg == '--force':
                        force = True
                    else:
                        remaining_args.append(arg)
                
                if not remaining_args:
                    print(f"Error: read command needs a file name")
                    return 1
                
                filename = remaining_args[0]
                # Pass all arguments after filename to cmd_read for proper parsing
                read_args = remaining_args[1:] if len(remaining_args) > 1 else []
                result = self.cmd_read(filename, *read_args, force=force)
                if result.get("success", False):
                    if not result.get("direct_feedback", False):
                        print(result.get("output", ""))
                    return 0
                else:
                    print(result.get("error", "Failed to read file"))
                    return 1
            elif cmd == 'python':
                # 使用委托方法处理python命令
                if not args:
                    print(f"Error: python command needs a file name or code")
                    return 1
                if args[0] == '-c':
                    # 执行Python代码
                    if len(args) < 2:
                        print(f"Error: python -c needs code")
                        return 1
                    # 过滤掉命令行选项参数，只保留Python代码
                    code_args = []
                    for arg in args[1:]:
                        if not arg.startswith('--'):
                            code_args.append(arg)
                    
                    # 统一处理已经在execute_shell_command中完成
                    code = ' '.join(code_args)
                    
                    # 不要移除Python代码的引号，因为shlex.split已经正确处理了shell引号
                    # Python代码中的引号是语法的一部分，不应该被移除
                    result = self.cmd_python_code(code)
                else:
                    # 执行Python文件
                    filename = args[0]
                    # 传递额外的命令行参数
                    python_args = args[1:] if len(args) > 1 else []
                    result = self.cmd_python(filename=filename, python_args=python_args)
                
                if result.get("success", False):
                    # 检查是否来自direct_feedback，如果是则不重复打印
                    if result.get("source") != "direct_feedback":
                        # 按正确顺序显示输出：先stdout，后stderr，并确保立即刷新
                        stdout = result.get("stdout", "")
                        stderr = result.get("stderr", "")
                        
                        if stdout:
                            print(stdout, end="", flush=True)
                        if stderr:
                            print(stderr, end="", file=sys.stderr, flush=True)
                    
                    # 返回Python脚本的实际退出码（可能是非零）
                    return_code = result.get("return_code", result.get("returncode", 0))
                    
                    return return_code
                else:
                    # 远程执行本身失败（不是Python脚本失败）
                    print(result.get("error", "Python execution failed"))
                    # 也显示stderr（如果有）
                    stderr = result.get("stderr", "")
                    if stderr:
                        print(stderr, end="", file=sys.stderr)
                    return 1
            elif cmd == 'upload':
                # 使用委托方法处理upload命令
                if not args:
                    print(f"Error: upload command needs a file name")
                    return 1
                
                # 参数解析规则：
                # 格式: upload [--target-dir TARGET] [--force] [--remove-local] file1 file2 file3 ...
                # 或者: upload file1 file2 file3 ... [--force] [--remove-local]
                
                target_path = "."  # 默认上传到当前目录
                source_files = []
                force = False
                remove_local = False
                
                i = 0
                while i < len(args):
                    if args[i] == '--target-dir':
                        if i + 1 < len(args):
                            target_path = args[i + 1]
                            i += 2  # 跳过--target-dir和其值
                        else:
                            print(f"Error: --target-dir option requires a directory path")
                            return 1
                    elif args[i] == '--force':
                        force = True
                        i += 1
                    elif args[i] == '--remove-local':
                        remove_local = True
                        i += 1
                    else:
                        source_files.append(args[i])
                        i += 1
                
                if not source_files:
                    print(f"Error: No source files specified for upload")
                    return 1
                
                    from GOOGLE_DRIVE_PROJ.modules.progress_manager import result_print
                if result.get("cancelled"):
                    result_print(result.get("error", "Upload cancelled by user"), success=False)
                    return 130  # 标准的Ctrl+C退出码
                elif result.get("success", False):
                    result_print(result.get("message", "Upload completed"), success=True)
                    return 0
                else:
                    result_print(result.get("error", "Upload failed"), success=False)
                    return 1
            elif cmd == 'upload-folder':
                # 使用委托方法处理upload-folder命令
                if not args:
                    print(f"Error: upload-folder command needs a folder path")
                    return 1
                
                # 解析参数: upload-folder [--keep-zip] [--force] <folder> [target]
                # 或者: upload-folder <folder> [target] [--keep-zip] [--force]
                folder_path = None
                target_path = "."
                keep_zip = False
                force = False
                
                i = 0
                while i < len(args):
                    if args[i] == '--keep-zip':
                        keep_zip = True
                        i += 1
                    elif args[i] == '--force':
                        force = True
                        i += 1
                    elif folder_path is None:
                        folder_path = args[i]
                        i += 1
                    else:
                        target_path = args[i]
                        i += 1
                
                if folder_path is None:
                    print(f"Error: upload-folder command needs a folder path")
                    return 1
                
                result = self.cmd_upload_folder(folder_path, target_path, keep_zip, force)
                if result.get("success", False):
                    print(result.get("message", "Folder upload completed"))
                    return 0
                else:
                    print(result.get("error", "Folder upload failed"))
                    return 1
            elif cmd == 'download':
                # 使用委托方法处理download命令
                if not args:
                    print(f"Error: download command needs a file name")
                    return 1
                result = self.cmd_download(*args)
                if result.get("success", False):
                    print(result.get("message", "Download completed"))
                    return 0
                else:
                    print(result.get("error", "Download failed"))
                    return 1
            elif cmd == 'mv':
                # 使用委托方法处理mv命令
                if len(args) < 2:
                    print(f"Error: mv command needs a source file and target file")
                    return 1
                result = self.cmd_mv(args[0], args[1])
                if result.get("success", False):
                    print(result.get("message", "Move completed"))
                    return 0
                else:
                    print(result.get("error", "Move failed"))
                    return 1
            elif cmd == 'find':
                # 使用委托方法处理find命令
                result = self.cmd_find(*args)
                if result.get("success", False):
                    if not result.get("direct_feedback", False):
                        print(result.get("output", ""))
                    return 0
                else:
                    print(result.get("error", "Find failed"))
                    return 1
            elif cmd == 'rm':
                # 使用委托方法处理rm命令
                if not args:
                    print(f"Error: rm command needs a file or directory name")
                    return 1
                
                # 解析rm选项
                recursive = False
                force = False
                paths = []
                
                for arg in args:
                    if arg == '-r' or arg == '-rf' or arg == '-fr':
                        recursive = True
                        if 'f' in arg:
                            force = True
                    elif arg == '-f':
                        force = True
                    elif not arg.startswith('-'):
                        paths.append(arg)
                
                if not paths:
                    print(f"Error: rm command needs at least one file or directory to delete")
                    return 1
                
                # 处理每个路径
                success_count = 0
                for path in paths:
                    result = self.cmd_rm(path, recursive=recursive, force=force)
                    if result.get("success", False):
                        success_count += 1
                        # rm命令成功时通常不显示消息，像bash一样
                    else:
                        print(result.get("error", f"Failed to delete {path}"))
                
                return 0 if success_count == len(paths) else 1
            elif cmd == 'grep':
                # 使用委托方法处理grep命令
                if len(args) < 1:
                    print(f"Error: grep command needs at least a file name")
                    return 1
                
                # 处理参数解析
                if len(args) == 1:
                    # 只有一个参数，视为文件名，模式为空（等效于read）
                    pattern = ""
                    filenames = args
                elif '.' in args[-1] and not args[-1].startswith('.'):
                    # 最后一个参数很可能是文件名，前面的是模式
                    filenames = [args[-1]]
                    pattern_parts = args[:-1]
                    pattern = ' '.join(pattern_parts)
                else:
                    # 传统处理：第一个参数是模式，其余是文件名
                    pattern = args[0]
                    filenames = args[1:]
                
                # 移除pattern的外层引号（如果存在）
                if pattern.startswith('"') and pattern.endswith('"'):
                    pattern = pattern[1:-1]
                elif pattern.startswith("'") and pattern.endswith("'"):
                    pattern = pattern[1:-1]
                    
                # 检查是否为无模式的grep（等效于read）
                if not pattern or pattern.strip() == "":
                    # 无模式grep，等效于read命令
                    for filename in filenames:
                        cat_result = self.cmd_cat(filename)
                        if cat_result.get("success"):
                            content = cat_result["output"]
                            # 修复换行显示问题，并添加行号
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                print(f"{i:3}: {line}")
                        else:
                            print(f"Error: 无法读取文件: {filename}")
                    return 0
                
                # 有模式的grep，只显示匹配行
                result = self.cmd_grep(pattern, *filenames)
                if result.get("success", False):
                    result_data = result.get("result", {})
                    has_matches = False
                    
                    has_file_errors = False
                    for filename, file_result in result_data.items():
                        if "error" in file_result:
                            print(f"Error: {filename}: {file_result['error']}")
                            has_file_errors = True
                        else:
                            occurrences = file_result.get("occurrences", {})
                            if occurrences:
                                has_matches = True
                                # 获取文件内容用于显示匹配行
                                cat_result = self.cmd_cat(filename)
                                if cat_result.get("success"):
                                    lines = cat_result["output"].split('\n')
                                    # 按行号排序显示匹配行
                                    sorted_line_nums = sorted([int(line_num) for line_num in occurrences.keys()])
                                    for line_num in sorted_line_nums:
                                        line_index = line_num - 1
                                        if 0 <= line_index < len(lines):
                                            line_content = lines[line_index]
                                            print(f"{line_num:3}: {line_content}")
                                else:
                                    print(f"Error: 无法读取文件内容: {filename}")
                    
                    # 按照bash grep的标准行为返回退出码
                    if has_file_errors:
                        return 2  # 文件错误（如文件不存在）
                    elif not has_matches:
                        return 1  # 没有匹配项
                    else:
                        return 0  # 有匹配项
                else:
                    print(result.get("error", "Error: Grep命令执行失败"))
                    return 1
            else:
                # 尝试通过通用远程命令执行
                result = self.execute_generic_command(cmd, args)
                if result.get("success", False):
                    stdout = result.get("stdout", "").strip()
                    stderr = result.get("stderr", "").strip()
                    # 统一在命令处理结束后打印输出
                    if stdout:
                        print(stdout)
                    if stderr:
                        print(stderr, file=sys.stderr)
                    return 0
                else:
                    error_msg = result.get("error", f"Command '{cmd}' failed")
                    print(error_msg)
                    return 1
                
        except Exception as e:
            error_msg = f"Error: Error executing shell command: {e}"
            print(error_msg)
            return 1
        finally:
            # ============ 简化架构：无需手动释放槽位 ============
            # 槽位释放由execute_generic_command统一处理
            # 调试日志已禁用
            # ========== 简化架构结束 ==========
            pass

    def _show_background_status(self, bg_pid, command_identifier=None):
        """显示background任务状态 - 使用统一接口"""
        try:
            # 使用通用的文件读取接口读取状态
            status_result = self._read_background_file(bg_pid, 'status', command_identifier)
            
            if not status_result.get("success", False):
                error_msg = status_result.get("error", "Failed to read status file")
                print(f"Error: Background task {bg_pid} not found")
                return 1
            
            # 获取状态文件内容
            status_data = status_result.get("data", {})
            status_content = status_data.get("stdout", "").strip()
            
            # 同时获取日志大小
            log_result = self._read_background_file(bg_pid, 'log', command_identifier)
            log_size = 0
            if log_result.get("success", False):
                log_data = log_result.get("data", {})
                log_content = log_data.get("stdout", "")
                log_size = len(log_content.encode('utf-8'))
            
            result = {"success": True, "data": {"stdout": f"{status_content}\nLOG_SIZE_SEPARATOR\n{log_size}", "stderr": ""}}
            
            if not result.get("success", False):
                error_msg = result.get("error", "Failed to read status file")
                print(f"Error: Background task {bg_pid} not found")
                return 1
            
            # 解析合并的输出：status JSON + 分隔符 + 日志大小
            data = result.get("data", {})
            stdout = data.get("stdout", "").strip()
            
            if not stdout:
                print(f"Error: Background task {bg_pid} status file is empty")
                return 1
            
            # 分离status内容和日志大小
            log_size = 0
            status_content = stdout
            
            if "LOG_SIZE_SEPARATOR" in stdout:
                parts = stdout.split("LOG_SIZE_SEPARATOR")
                if len(parts) >= 2:
                    status_content = parts[0].strip()
                    log_size_str = parts[1].strip()
                    try:
                        log_size = int(log_size_str)
                    except ValueError:
                        log_size = 0
            
            try:
                import json
                status_data = json.loads(status_content)
                
                # 提取状态信息
                status = status_data.get("status", "unknown")
                command = status_data.get("command", "N/A")
                start_time = status_data.get("start_time", "N/A")
                end_time = status_data.get("end_time", "")
                real_pid = status_data.get("real_pid", None)
                
                # 显示状态信息 - 直接信任远程状态文件
                print(f"Status: {status}")
                if real_pid:
                    if status == "running":
                        print(f"PID: {real_pid}")
                    else:
                        print(f"PID: {real_pid} (finished)")
                
                print(f"Command: {command}")
                print(f"Start time: {start_time}")
                
                if end_time:
                    print(f"End time: {end_time}")
                
                # 显示日志大小信息（已在合并命令中获取）
                print(f"Log size: {log_size} bytes")
                
                return 0
                
            except json.JSONDecodeError as e:
                print(f"Error: Invalid status file format for task {bg_pid}")
                print(f"JSON parse error: {e}")
                return 1
                
        except Exception as e:
            print(f"Error: Failed to check status: {e}")
            return 1

    def _show_all_background_status(self, command_identifier=None):
        """显示所有background任务状态"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 构建查询所有状态的远程命令
            status_cmd = '''
if [ ! -d ~/tmp ]; then
    echo "No background tasks found"
    exit 0
fi

FOUND_TASKS=0
for status_file in ~/tmp/cmd_bg_*.status; do
    if [ -f "$status_file" ]; then
        FOUND_TASKS=1
        BG_PID=$(basename "$status_file" .status | sed 's/cmd_bg_//')
        STATUS_DATA=$(cat "$status_file")
        REAL_PID=$(echo "$STATUS_DATA" | grep -o '"real_pid":[0-9]*' | cut -d':' -f2)
        
        echo "========================"
        echo "Task ID: $BG_PID"
        echo "Command: $(echo "$STATUS_DATA" | grep -o '"command":"[^"]*' | cut -d':' -f2- | sed 's/^"//')"
        
        if [ -n "$REAL_PID" ] && ps -p $REAL_PID > /dev/null 2>&1; then
            echo "Status: running"
            echo "PID: $REAL_PID"
        else
            echo "Status: completed"
            if [ -n "$REAL_PID" ]; then
                echo "PID: $REAL_PID (finished)"
            fi
        fi
        
        echo "Start time: $(echo "$STATUS_DATA" | grep -o '"start_time":"[^"]*' | cut -d':' -f2- | sed 's/^"//')"
        
        if [ -f ~/tmp/cmd_bg_${BG_PID}.log ]; then
            LOG_SIZE=$(wc -c < ~/tmp/cmd_bg_${BG_PID}.log)
            echo "Log size: $LOG_SIZE bytes"
        fi
    fi
done

if [ $FOUND_TASKS -eq 0 ]; then
    echo "No background tasks found"
fi
'''
            
            # 执行状态查询 - 使用与普通命令相同的_show_command_window方法
            remote_command_info = self.remote_commands._generate_command("bash", ["-c", status_cmd], current_shell)
            remote_command, result_filename = remote_command_info
            
            result = self.remote_commands._show_command_window("bash", ["-c", status_cmd], remote_command)
            
            # 处理结果 - 使用与普通命令相同的统一结果格式
            if result.get("success", False):
                # 成功情况：显示结果数据
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                    return 0
                else:
                    # 失败情况：显示错误信息
                    if result.get("action") == "direct_feedback_error":
                        data = result.get("data", {})
                        error_msg = data.get("error", "All background status check failed via direct feedback")
                        print(f"Error: {error_msg}")
            else:
                error_msg = result.get("error", "Failed to check status")
                print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Status check failed: {e}")
            return 1

    def _show_background_log(self, bg_pid, command_identifier=None):
        """显示background任务日志 - 使用统一接口"""
        try:
            # 使用通用的文件读取接口
            result = self._read_background_file(bg_pid, 'log', command_identifier)
            
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    print(stdout)
                elif stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                else:
                    print(f"Log file for task {bg_pid} is empty or task hasn't started producing output yet.")
                
                return 0
            else:
                error_msg = result.get("error", "Log view failed")
                if "does not exist" in error_msg.lower():
                    print(f"Log file for task {bg_pid} not found. Task may not have started producing output yet.")
                    print(f"Use 'GDS --bg --status {bg_pid}' to check if the task is running.")
                else:
                    print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Log view failed: {e}")
            return 1

    def _wait_background_task(self, bg_pid, command_identifier=None):
        """等待background任务完成"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 构建等待任务的远程命令
            wait_cmd = f'''
if [ ! -f ~/tmp/cmd_bg_{bg_pid}.status ]; then
    echo "Error: Background task {bg_pid} not found"
    exit 1
fi

echo "Waiting for task {bg_pid} to complete..."

while true; do
    STATUS_DATA=$(cat ~/tmp/cmd_bg_{bg_pid}.status)
    REAL_PID=$(echo "$STATUS_DATA" | grep -o '"real_pid":[0-9]*' | cut -d':' -f2)
    
    if [ -n "$REAL_PID" ] && ps -p $REAL_PID > /dev/null 2>&1; then
        echo "Task still running (PID: $REAL_PID)..."
        sleep 5
    else
        echo "Task {bg_pid} completed!"
        
        # 显示最后的日志
        if [ -f ~/tmp/cmd_bg_{bg_pid}.log ]; then
            echo ""
            echo "=== Final Output ==="
            tail -20 ~/tmp/cmd_bg_{bg_pid}.log
        fi
        break
    fi
done
'''
            
            # 执行等待
            remote_command_info = self.remote_commands._generate_command("bash", ["-c", wait_cmd], current_shell)
            remote_command, result_filename = remote_command_info
            
            result = self.remote_commands.show_command_window_subprocess(
                title=f"GDS Wait Task: {bg_pid}",
                command_text=remote_command,
                timeout_seconds=3600  # 1小时超时
            )
            
            if result["action"] == "success":
                result_data = self.remote_commands._wait_and_read_result_file(result_filename)
                if result_data.get("success"):
                    stdout_content = result_data.get("data", {}).get("stdout", "")
                    if stdout_content:
                        print(stdout_content)
                    return 0
                else:
                    print(f"Error: {result_data.get('error', 'Wait failed')}")
                    return 1
            else:
                print(f"Error: Failed to wait for task: {result.get('error', 'Unknown error')}")
                return 1
                
        except Exception as e:
            print(f"Error: Wait failed: {e}")
            return 1

    def _is_operator_outside_quotes(self, shell_cmd, operator):
        """
        检查操作符是否在引号外
        
        Args:
            shell_cmd (str): shell命令
            operator (str): 要检查的操作符
            
        Returns:
            bool: True如果操作符在引号外
        """
        in_single_quote = False
        in_double_quote = False
        i = 0
        
        while i < len(shell_cmd):
            char = shell_cmd[i]
            
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                # 检查是否匹配操作符
                if shell_cmd[i:i+len(operator)] == operator:
                    return True
            
            i += 1
        
        return False

    def _parse_shell_command(self, shell_cmd):
        """
        接口化的shell命令解析方法
        
        Args:
            shell_cmd (str): 要解析的shell命令
            
        Returns:
            dict: 解析结果
                - success (bool): 是否解析成功
                - cmd (str): 命令名称
                - args (list): 命令参数
                - error (str): 错误信息（如果失败）
        """
        import shlex
        
        try:
            # 在shlex.split之前保护~路径，防止本地路径展开
            protected_cmd = shell_cmd.replace('~/', '__TILDE_SLASH__').replace(' ~', ' __TILDE__')
            
            cmd_parts = shlex.split(protected_cmd)
            
            # 恢复~路径
            cmd_parts = [part.replace('__TILDE_SLASH__', '~/').replace('__TILDE__', '~') for part in cmd_parts]
            
            if not cmd_parts:
                return {
                    "success": False,
                    "error": "Empty command"
                }
            
            return {
                "success": True,
                "cmd": cmd_parts[0],
                "args": cmd_parts[1:] if len(cmd_parts) > 1 else []
            }
            
        except ValueError as e:
            # 如果shlex解析失败，尝试简单分割作为fallback
            try:
                cmd_parts = shell_cmd.split()
                if not cmd_parts:
                    return {
                        "success": False,
                        "error": f"Command parsing failed: {e}"
                    }
                
                return {
                    "success": True,
                    "cmd": cmd_parts[0],
                    "args": cmd_parts[1:] if len(cmd_parts) > 1 else [],
                    "warning": f"Used simple parsing due to shlex error: {e}"
                }
            except Exception as fallback_error:
                return {
                    "success": False,
                    "error": f"Command parsing failed: {e}. Fallback also failed: {fallback_error}"
                }

    def _handle_edit_command(self, shell_cmd):
        """
        处理edit命令的用户友好接口
        支持多种参数格式，避免复杂的JSON和引号嵌套
        """
        import shlex
        import json
        
        try:
            # 使用统一的命令解析接口
            parse_result = self._parse_shell_command(shell_cmd)
            if not parse_result["success"]:
                print(f"Error: {parse_result['error']}")
                return 1
            
            parts = [parse_result["cmd"]] + parse_result["args"]
            if len(parts) < 2:
                print("Error: edit command requires a filename")
                return 1
                
            cmd = parts[0]  # 'edit'
            filename = None
            preview = False
            backup = False
            replacements = []
            content_mode = False
            content = None
            
            i = 1
            while i < len(parts):
                arg = parts[i]
                
                if arg == '--preview':
                    preview = True
                elif arg == '--backup':
                    backup = True
                elif arg in ['--content', '-c']:
                    if i + 1 >= len(parts):
                        print("Error: --content requires a value")
                        return 1
                    content_mode = True
                    # 处理转义字符，特别是\n
                    content = parts[i + 1].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                    i += 1
                elif arg in ['--replace', '-r']:
                    if i + 2 >= len(parts):
                        print("Error: --replace requires old and new values")
                        return 1
                    old_text = parts[i + 1].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                    new_text = parts[i + 2].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                    replacements.append([old_text, new_text])
                    i += 2
                elif arg in ['--line', '-l']:
                    if i + 2 >= len(parts):
                        print("Error: --line requires line number and content")
                        return 1
                    try:
                        line_spec = parts[i + 1]
                        line_content = parts[i + 2].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                        
                        # 支持行号范围：5-10 或单个行号：5
                        if '-' in line_spec and line_spec.count('-') == 1:
                            # 行号范围模式
                            start_str, end_str = line_spec.split('-', 1)
                            start_line = int(start_str.strip())
                            end_line = int(end_str.strip())
                            if start_line > end_line:
                                print(f"Error: Invalid line range: {line_spec}. Start line must be <= end line.")
                                return 1
                            replacements.append([[start_line, end_line], line_content])
                        else:
                            # 单个行号模式
                            line_num = int(line_spec)
                            replacements.append([[line_num, line_num], line_content])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid line number or range: {parts[i + 1]}")
                        return 1
                elif arg in ['--insert', '-i']:
                    if i + 2 >= len(parts):
                        print("Error: --insert requires line number and content")
                        return 1
                    try:
                        line_num = int(parts[i + 1])
                        line_content = parts[i + 2].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                        replacements.append([[line_num, None], line_content])
                        i += 2
                    except ValueError:
                        print(f"Error: Invalid line number: {parts[i + 1]}")
                        return 1
                elif not arg.startswith('-'):
                    if filename is None:
                        filename = arg
                    else:
                        print(f"Error: Unrecognized argument: {arg}")
                        print("Use --content, --replace, --line, or --insert")
                        return 1
                else:
                    print(f"Error: Unknown option: {arg}")
                    return 1
                    
                i += 1
            
            if filename is None:
                print("Error: No filename specified")
                return 1
            
            # 构建替换规范
            if content_mode:
                # 内容模式：使用行号范围替换整个文件内容
                try:
                    read_result = self.cmd_read(filename)
                    if read_result.get("success"):
                        current_content = read_result.get("output", "")
                        if current_content.strip():  # 文件有内容
                            # 计算总行数
                            lines = current_content.splitlines()
                            total_lines = len(lines)
                            if total_lines > 0:
                                # 使用行号范围替换：替换从第0行到最后一行（包含）
                                json_spec = json.dumps([[[0, total_lines - 1], content]])
                            else:
                                # 空文件，使用插入模式
                                json_spec = json.dumps([[[0, None], content]])
                        else:
                            # 空文件，使用插入模式
                            json_spec = json.dumps([[[0, None], content]])
                    else:
                        # 文件不存在，使用插入模式创建新文件
                        json_spec = json.dumps([[[0, None], content]])
                except Exception:
                    # 出错时回退到插入模式
                    json_spec = json.dumps([[[0, None], content]])
            elif replacements:
                # 替换模式：使用收集的替换规则
                json_spec = json.dumps(replacements)
            else:
                print("Error: No edit operations specified")
                print("Use --content, --replace, --line, or --insert")
                return 1
            
            # 调用原有的edit方法
            try:
                result = self.cmd_edit(filename, json_spec, preview=preview, backup=backup)
            except KeyboardInterrupt:
                result = {"success": False, "error": "Operation interrupted by user"}
            
            if result.get("success", False):
                # 显示diff比较（预览模式和正常模式都显示）
                diff_output = result.get("diff_output", "")
                
                if diff_output and diff_output != "No changes detected":
                    print(f"\nEdit comparison: {filename}")
                    print(f"=" * 50)
                    print(diff_output)
                    print(f"=" * 50)
                
                # 对于正常模式，显示成功信息
                if result.get("mode") != "preview":
                    print(result.get("message", "\nFile edited successfully"))
                return 0
            else:
                print(result.get("error", "Edit failed"))
                return 1
                
        except Exception as e:
            print(f"Error parsing edit command: {e}")
            return 1

    def _cleanup_background_tasks(self, command_identifier=None):
        """清理所有已完成的background任务"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 构建清理命令
            cleanup_cmd = '''
if [ ! -d ~/tmp ]; then
    echo "No background tasks to clean up"
    exit 0
fi

CLEANED=0
for status_file in ~/tmp/cmd_bg_*.status; do
    if [ -f "$status_file" ]; then
        BG_PID=$(basename "$status_file" .status | sed 's/cmd_bg_//')
        STATUS_DATA=$(cat "$status_file")
        REAL_PID=$(echo "$STATUS_DATA" | grep -o '"real_pid":[0-9]*' | cut -d':' -f2)
        
        # 检查进程是否还在运行
        if [ -n "$REAL_PID" ] && ps -p $REAL_PID > /dev/null 2>&1; then
            echo "Skipping running task: $BG_PID (PID: $REAL_PID)"
        else
            echo "Cleaning up completed task: $BG_PID"
            rm -f ~/tmp/cmd_bg_${BG_PID}.*
            CLEANED=$((CLEANED + 1))
        fi
    fi
done

echo "Cleaned up $CLEANED completed background tasks"
'''
            
            # 执行清理
            remote_command_info = self.remote_commands._generate_command("bash", ["-c", cleanup_cmd], current_shell)
            remote_command, result_filename = remote_command_info
            
            result = self.remote_commands.show_command_window_subprocess(
                title="GDS Cleanup Background Tasks",
                command_text=remote_command,
                timeout_seconds=86400  # 24小时，实际上就是无timeout
            )
            
            if result["action"] == "success":
                result_data = self.remote_commands._wait_and_read_result_file(result_filename)
                if result_data.get("success"):
                    stdout_content = result_data.get("data", {}).get("stdout", "")
                    if stdout_content:
                        print(stdout_content)
                    return 0
                else:
                    print(f"Error: {result_data.get('error', 'Cleanup failed')}")
                    return 1
            else:
                print(f"Error: Failed to cleanup: {result.get('error', 'Unknown error')}")
                return 1
                
        except Exception as e:
            print(f"Error: Cleanup failed: {e}")
            return 1

    def _cleanup_background_task(self, bg_pid, command_identifier=None):
        """清理特定的background任务"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                print(f"Error: 没有活跃的shell会话")
                return 1
            
            # 获取REMOTE_ROOT路径
            tmp_path = f"{self.REMOTE_ROOT}/tmp"
            
            # 构建清理特定任务的命令
            cleanup_cmd = f'''
if [ ! -f "{tmp_path}/cmd_bg_{bg_pid}.status" ]; then
    echo "Error: Background task {bg_pid} not found"
    exit 1
fi

STATUS_DATA=$(cat "{tmp_path}/cmd_bg_{bg_pid}.status")
REAL_PID=$(echo "$STATUS_DATA" | grep -o '"real_pid": *[0-9]*' | grep -o '[0-9]*')

# 检查进程是否还在运行
if [ -n "$REAL_PID" ] && ps -p $REAL_PID > /dev/null 2>&1; then
    echo "Error: Cannot cleanup running task {bg_pid} (PID: $REAL_PID)"
    echo "Use 'kill $REAL_PID' to stop it first, or wait for it to complete"
    exit 1
else
    echo "Cleaning up task: {bg_pid}"
    rm -f "{tmp_path}/cmd_bg_{bg_pid}.*"
    echo "Task {bg_pid} cleaned up successfully"
fi
'''
            
            # 使用统一的命令执行接口
            result = self.remote_commands.execute_unified_command(
                user_command=cleanup_cmd,
                current_shell=current_shell
            )
            
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    print(stdout)
                if stderr:
                    import sys
                    print(stderr, file=sys.stderr)
                
                    return 0
                else:
                    error_msg = result.get("error", "Cleanup failed")
                    print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Cleanup failed: {e}")
            return 1

    def _read_background_file(self, bg_pid, file_type, command_identifier=None):
        """通用的后台任务文件读取接口
        
        Args:
            bg_pid: 后台任务ID
            file_type: 文件类型 ('status', 'result', 'log')
            command_identifier: 命令标识符
            
        Returns:
            dict: 包含文件内容的结果字典
        """
        try:
            # 获取REMOTE_ROOT路径
            tmp_path = f"{self.REMOTE_ROOT}/tmp"
            
            # 根据文件类型选择相应的文件
            if file_type == 'status':
                from modules.constants import get_bg_status_file
                target_file = get_bg_status_file(bg_pid)
            elif file_type == 'result':
                from modules.constants import get_bg_result_file
                target_file = get_bg_result_file(bg_pid)
            elif file_type == 'log':
                from modules.constants import get_bg_log_file
                target_file = get_bg_log_file(bg_pid)
            else:
                return {"success": False, "error": f"Unknown file type: {file_type}"}
            
            file_path = f"{tmp_path}/{target_file}"
            
            # 使用cmd_cat直接读取文件，避免弹窗
            result = self.cmd_cat(file_path)
            
            if result.get("success", False):
                # 将cmd_cat的结果转换为统一格式
                content = result.get("output", "")
                return {
                    "success": True,
                    "data": {
                        "stdout": content,
                        "stderr": ""
                    }
                }
            else:
                return {"success": False, "error": result.get("error", "Failed to read file")}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _show_background_result(self, bg_pid, command_identifier=None):
        """显示background任务的最终结果 - 先检查状态，再读取结果"""
        try:
            # 先检查任务状态
            status_result = self._read_background_file(bg_pid, 'status', command_identifier)
            
            if status_result.get("success", False):
                status_data = status_result.get("data", {})
                status_content = status_data.get("stdout", "").strip()
                
                if status_content:
                    try:
                        import json
                        status_json = json.loads(status_content)
                        task_status = status_json.get("status", "unknown")
                        
                        # 如果任务还在运行，提示用户
                        if task_status in ["running", "starting"]:
                            print(f"Task {bg_pid} is still {task_status}.")
                            print(f"Use 'GDS --bg --status {bg_pid}' to check current status")
                            if task_status == "running":
                                print(f"Use 'GDS --bg --log {bg_pid}' to view current output")
                            return 1
                        elif task_status != "completed":
                            print(f"Task {bg_pid} has status: {task_status}")
                            return 1
                    except json.JSONDecodeError:
                        pass  # Continue to try reading result file
            
            # 如果状态是 completed，读取结果文件
            result = self._read_background_file(bg_pid, 'result', command_identifier)
            
            # 处理统一接口的结果
            if result.get("success", False):
                data = result.get("data", {})
                stdout = data.get("stdout", "").strip()
                stderr = data.get("stderr", "").strip()
                
                if stdout:
                    try:
                        import json
                        # 解析后台任务的JSON结果
                        bg_data = json.loads(stdout, strict=False)
                        
                        # 获取后台任务的实际输出
                        task_data = bg_data.get("data", {})
                        stdout_content = task_data.get("stdout", "")
                        stderr_content = task_data.get("stderr", "")
                        exit_code = task_data.get("exit_code", 0)
                        
                        # 显示后台任务的输出
                        if stdout_content:
                            # 使用end=""避免额外的换行符，因为stdout_content可能已经包含换行符
                            print(stdout_content, end="")
                        
                        if stderr_content:
                            import sys
                            print(stderr_content, file=sys.stderr, end="")
                        
                        return exit_code
                        
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON in result file: {e}")
                        return 1
                else:
                    # 检查stderr中是否有"No such file"错误
                    if "no such file" in stderr.lower() or "not found" in stderr.lower():
                        print(f"Error: Background task {bg_pid} result file not found")
                        print(f"This usually means the task failed to complete or the result file was not created")
                        print(f"Use 'GDS --bg --status {bg_pid}' to check task status")
                        print(f"Use 'GDS --bg --log {bg_pid}' to check task logs")
                    else:
                        print(f"Error: Empty result file for task {bg_pid}")
                    return 1
                    
            else:
                # 检查stderr中是否有"No such file"错误
                data = result.get("data", {})
                stderr = data.get("stderr", "")
                if "no such file" in stderr.lower() or "not found" in stderr.lower():
                    print(f"Error: Background task {bg_pid} result file not found")
                    print(f"This usually means the task failed to complete or the result file was not created")
                    print(f"Use 'GDS --bg --status {bg_pid}' to check task status")
                    print(f"Use 'GDS --bg --log {bg_pid}' to check task logs")
                else:
                    error_msg = result.get("error", "Failed to read result file")
                    print(f"Error: {error_msg}")
                return 1
                
        except Exception as e:
            print(f"Error: Result view failed: {e}")
            return 1
    
    def _check_and_setup_mount_point(self):
        """检查并设置动态挂载点"""
        import os
        import tempfile
        
        # 使用临时文件存储当前session的挂载点信息
        self.mount_info_file = os.path.join(tempfile.gettempdir(), "gds_current_mount.txt")
        
        # 检查是否有现有的挂载点
        if os.path.exists(self.mount_info_file):
            try:
                with open(self.mount_info_file, 'r') as f:
                    stored_mount_point = f.read().strip()
                if stored_mount_point:
                    # 验证挂载点的指纹文件（静默模式，不输出调试信息）
                    if self._verify_mount_fingerprint(stored_mount_point, silent=True):
                        self.current_mount_point = stored_mount_point
                        self._update_paths_for_dynamic_mount(stored_mount_point)
                        return
            except Exception as e:
                print(f"Warning: 读取挂载点信息失败: {e}")
        
        # 如果检测到需要动态挂载（比如传统挂载失败），启用动态模式
        try:
            # 简单的启发式：如果REMOTE_ROOT包含默认路径，可能需要动态挂载
            if self.REMOTE_ROOT == "/content/drive/MyDrive/REMOTE_ROOT":
                self.dynamic_mode = True
            else:
                self.dynamic_mode = False
                
        except Exception as e:
            self.dynamic_mode = False
    
    def _update_paths_for_dynamic_mount(self, mount_point):
        """更新路径以使用动态挂载点"""
        self.current_mount_point = mount_point
        self.REMOTE_ROOT = f"{mount_point}/MyDrive/REMOTE_ROOT"
        self.REMOTE_ENV = f"{mount_point}/MyDrive/REMOTE_ENV"
        self.dynamic_mode = True
        
        # 保存挂载点信息到临时文件
        try:
            import os
            import tempfile
            mount_info_file = os.path.join(tempfile.gettempdir(), "gds_current_mount.txt")
            with open(mount_info_file, 'w') as f:
                f.write(mount_point)
        except Exception as e:
            print(f"Warning: 保存挂载点信息失败: {e}")
    
    def _verify_mount_fingerprint(self, mount_point, silent=False):
        """验证挂载点的指纹文件（通过Google Drive API）"""
        import json
        
        try:
            # 首先确保我们有Google Drive API服务
            if not self.drive_service:
                if not silent:
                    print(f"🔍 Google Drive API服务未初始化，无法验证指纹")
                return False
            
            # 获取REMOTE_ROOT文件夹ID
            if not hasattr(self, 'REMOTE_ROOT_FOLDER_ID'):
                if not silent:
                    print(f"🔍 REMOTE_ROOT_FOLDER_ID未设置，无法验证指纹")
                return False
            
            # 首先获取tmp文件夹ID
            tmp_folder_result = self.drive_service.list_files(
                folder_id=self.REMOTE_ROOT_FOLDER_ID, 
                query="name='tmp' and mimeType='application/vnd.google-apps.folder'",
                max_results=1
            )
            
            if not tmp_folder_result.get('success') or not tmp_folder_result.get('files'):
                if not silent:
                    print(f"🔍 tmp文件夹不存在，无法验证指纹")
                return False
            
            tmp_folder_id = tmp_folder_result['files'][0]['id']
            
            # 列出tmp文件夹中的所有文件
            result = self.drive_service.list_files(folder_id=tmp_folder_id, max_results=100)
            
            if not result.get('success'):
                if not silent:
                    print(f"Error: 无法访问tmp文件夹: {result.get('error', '未知错误')}")
                return False
            
            files = result.get('files', [])
            
            # 查找指纹文件
            fingerprint_files = [f for f in files if f['name'].startswith('.gds_mount_fingerprint_')]
            
            if not fingerprint_files:
                if not silent:
                    print(f"🔍 在REMOTE_ROOT中未找到指纹文件")
                return False
            
            # 使用最新的指纹文件（按名称排序，最新的在最后）
            latest_fingerprint = max(fingerprint_files, key=lambda x: x['name'])
            
            # 下载并读取指纹文件内容（使用临时文件）
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                download_result = self.drive_service.download_file(latest_fingerprint['id'], temp_path)
                if not download_result.get('success'):
                    if not silent:
                        print(f"Error: 无法下载指纹文件: {download_result.get('error', '未知错误')}")
                    return False
                
                # 读取临时文件内容
                with open(temp_path, 'r', encoding='utf-8') as f:
                    fingerprint_content = f.read()
                
                # 解析指纹文件内容
                try:
                    fingerprint_data = json.loads(fingerprint_content)
                except json.JSONDecodeError as e:
                    if not silent:
                        print(f"Error: 指纹文件JSON格式错误: {e}")
                    return False
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            # 验证指纹数据的基本结构
            required_fields = ["mount_point", "timestamp", "hash", "signature", "type"]
            for field in required_fields:
                if field not in fingerprint_data:
                    if not silent:
                        print(f"Error: 指纹文件缺少必需字段: {field}")
                    return False
            
            # 验证挂载点匹配
            if fingerprint_data.get("mount_point") != mount_point:
                if not silent:
                    print(f"Error: 挂载点不匹配: 期望 {mount_point}, 实际 {fingerprint_data.get('mount_point')}")
                return False
            
            # 验证文件类型
            if fingerprint_data.get("type") != "mount_fingerprint":
                if not silent:
                    print(f"Error: 指纹文件类型不正确: {fingerprint_data.get('type')}")
                return False
            
            # 验证签名格式（基本验证）
            signature = fingerprint_data.get("signature", "")
            expected_prefix = f"{fingerprint_data.get('timestamp')}_{fingerprint_data.get('hash')}_"
            if not signature.startswith(expected_prefix):
                if not silent:
                    print(f"Error: 指纹签名格式不正确")
                return False
            
            # 验证通过，更新本地配置中的文件夹ID
            remote_root_id = fingerprint_data.get("remote_root_id")
            remote_env_id = fingerprint_data.get("remote_env_id")
            
            if remote_root_id:
                self.REMOTE_ROOT_FOLDER_ID = remote_root_id
            
            if remote_env_id:
                self.REMOTE_ENV_FOLDER_ID = remote_env_id
            
            return True
            
        except Exception as e:
            if not silent:
                print(f"Error: 指纹验证失败: {e}")
            return False
        
    
    def _generate_dynamic_mount_point(self):
        """生成动态挂载点，避免挂载冲突"""
        import os
        import time
        
        # 基础挂载目录
        base_mount_dir = "/content"
        
        # 首先尝试传统的挂载点
        traditional_mount = "/content/drive"
        if not os.path.exists(traditional_mount) or not os.listdir(traditional_mount):
            return traditional_mount
        
        # 如果传统挂载点有文件，使用动态挂载点
        timestamp = int(time.time())
        dynamic_mount = f"/content/drive_{timestamp}"
        
        # 确保动态挂载点不存在
        counter = 0
        while os.path.exists(dynamic_mount):
            counter += 1
            dynamic_mount = f"/content/drive_{timestamp}_{counter}"
            
        return dynamic_mount
    
    def _handle_remount_command(self, command_identifier):
        """处理GOOGLE_DRIVE --remount命令"""
        import time
        import hashlib
        import random
        
        # 首先检查当前是否已有有效的指纹文件
        current_mount_point = getattr(self, 'current_mount_point', None) or "/content/drive"
        if self._verify_mount_fingerprint(current_mount_point, silent=True):
            print("当前挂载已有效，无需重新挂载")
            return 0
        
        # 生成动态挂载点（避免挂载点冲突）
        mount_point = self._generate_dynamic_mount_point()
        
        # 需要重新挂载
        timestamp = str(int(time.time()))
        random_hash = hashlib.md5(f"{timestamp}_{random.randint(1000, 9999)}".encode()).hexdigest()[:8]
        
        # 生成指纹文件名（以.开头，保存在tmp文件夹内）
        fingerprint_filename = f".gds_mount_fingerprint_{random_hash}"
        fingerprint_path = f"{mount_point}/MyDrive/REMOTE_ROOT/tmp/{fingerprint_filename}"
        
        # 生成结果文件
        result_filename = f"remount_result_{timestamp}_{random_hash}.json"
        result_path = f"{mount_point}/MyDrive/REMOTE_ROOT/tmp/{result_filename}"
        
        # 生成全Python挂载脚本
        python_remount_script = self._generate_python_remount_script(
            mount_point, fingerprint_path, result_path, timestamp, random_hash
        )
        
        # 复制到剪切板（静默）
        try:
            import subprocess
            subprocess.run(['pbcopy'], input=python_remount_script.encode('utf-8'), 
                          capture_output=True)
        except Exception as e:
            pass
        
        # 显示tkinter窗口（使用subprocess压制IMK信息）
        success = self._show_remount_window_subprocess(python_remount_script, mount_point, result_path)
        
        if success:
            # 更新挂载点信息
            self._update_paths_for_dynamic_mount(mount_point)
            
            # 保存挂载配置到config.json
            config_saved = self._save_mount_config_to_json(mount_point, timestamp, random_hash)
            
            return 0
        else:
            return 1
    
    def _generate_python_remount_script(self, mount_point, fingerprint_path, result_path, timestamp, random_hash):
        """生成全Python重新挂载脚本"""
        
        # 检查当前挂载点信息
        current_mount = getattr(self, 'current_mount_point', None)
        current_fingerprint = None
        if current_mount:
            current_fingerprint = f"{current_mount}/REMOTE_ROOT/tmp/.gds_mount_fingerprint_*"
        
        script = f'''# GDS 动态挂载脚本
import os
import json
from datetime import datetime

print("挂载点: {mount_point}")

# Google Drive挂载
try:
    from google.colab import drive
    drive.mount("{mount_point}", force_remount=True)
    mount_result = "挂载成功"
except Exception as e:
    mount_result = str(e)
    if "Drive already mounted" not in str(e):
        raise

print(f"挂载结果: {{mount_result}}")

# 验证并创建必要目录
remote_root_path = "{mount_point}/MyDrive/REMOTE_ROOT"
remote_env_path = "{mount_point}/MyDrive/REMOTE_ENV"

# 确保目录存在
os.makedirs(remote_root_path, exist_ok=True)
os.makedirs(f"{{remote_root_path}}/tmp", exist_ok=True)
os.makedirs(remote_env_path, exist_ok=True)

# 尝试获取文件夹ID（使用kora库）
remote_root_id = None
remote_env_id = None
remote_root_status = "失败"
remote_env_status = "失败"

try:
    try: 
        import kora  
    except:   
        # 安装并导入kora库
        import subprocess
        subprocess.run(['pip', 'install', 'kora'], check=True, capture_output=True)
    from kora.xattr import get_id
    
    # 获取REMOTE_ROOT文件夹ID
    if os.path.exists(remote_root_path):
        try:
            remote_root_id = get_id(remote_root_path)
            remote_root_status = f"成功（ID: {{remote_root_id}}）"
        except Exception:
            remote_root_status = "失败"
    
    # 获取REMOTE_ENV文件夹ID
    if os.path.exists(remote_env_path):
        try:
            remote_env_id = get_id(remote_env_path)
            remote_env_status = f"成功（ID: {{remote_env_id}}）"
        except Exception:
            remote_env_status = "失败"
            
except Exception:
    remote_root_status = "失败（kora库问题）"
    remote_env_status = "失败（kora库问题）"

print(f"访问REMOTE_ROOT: {{remote_root_status}}")
print(f"访问REMOTE_ENV: {{remote_env_status}}")

# 创建指纹文件（包含挂载签名信息）
fingerprint_data = {{
    "mount_point": "{mount_point}",
    "timestamp": "{timestamp}",
    "hash": "{random_hash}",
    "remote_root_id": remote_root_id,
    "remote_env_id": remote_env_id,
    "signature": f"{timestamp}_{random_hash}_{{remote_root_id or 'unknown'}}_{{remote_env_id or 'unknown'}}",
    "created": datetime.now().isoformat(),
    "type": "mount_fingerprint"
}}

fingerprint_file = "{fingerprint_path}"
try:
    with open(fingerprint_file, 'w') as f:
        json.dump(fingerprint_data, f, indent=2)
    print(f"指纹文件已创建: {{fingerprint_file}}")
except Exception as e:
    print(f"指纹文件创建失败: {{e}}")

# 创建结果文件（包含文件夹ID）
result_file = "{result_path}"
try:
    with open(result_file, 'w') as f:
        result_data = {{
            "success": True,
            "mount_point": "{mount_point}",
            "timestamp": "{timestamp}",
            "remote_root": remote_root_path,
            "remote_env": remote_env_path,
            "remote_root_id": remote_root_id,
            "remote_env_id": remote_env_id,
            "fingerprint_signature": fingerprint_data.get("signature"),
            "completed": datetime.now().isoformat(),
            "type": "remount",
            "note": "Dynamic remount with kora folder ID detection and fingerprint"
        }}
        json.dump(result_data, f, indent=2)
    print(f"结果文件已创建: {{result_file}}")
    print("重新挂载流程完成！现在可以使用GDS命令访问Google Drive了！")
    print("✅执行完成")
except Exception as e:
    print(f"结果文件创建失败: {{e}}")

'''
        return script
    
    def _show_remount_window(self, python_script, mount_point, result_path):
        """显示重新挂载窗口"""
        try:
            import tkinter as tk
            from tkinter import messagebox, scrolledtext
            import subprocess
            import time
            import json
            
            # 创建窗口（使用远端指令窗口风格）
            window = tk.Tk()
            window.title("GDS 重新挂载")
            window.geometry("500x60")  # 与普通指令窗口完全一致
            window.resizable(False, False)
            window.attributes('-topmost', True)  # 置顶显示
            
            # 结果变量
            remount_success = False
            
            def copy_script():
                """复制脚本到剪切板"""
                try:
                    subprocess.run(['pbcopy'], input=python_script.encode('utf-8'), 
                                  capture_output=True)
                except Exception as e:
                    pass
            
            def execution_completed():
                """用户确认执行完成"""
                nonlocal remount_success
                
                try:
                        remount_success = True
                        
                        # 保存挂载信息到GOOGLE_DRIVE_DATA（简化版）
                        try:
                            mount_info = {
                                "mount_point": mount_point,
                                "timestamp": int(time.time()),
                                "type": "dynamic_mount"
                            }
                        except Exception as e:
                            pass
                        
                        window.quit()
                        
                except Exception as e:
                    pass
            
            def cancel_remount():
                """取消重新挂载"""
                nonlocal remount_success
                remount_success = False
                window.quit()
            
            # 自动复制脚本到剪切板（静默）
            try:
                subprocess.run(['pbcopy'], input=python_script.encode('utf-8'), 
                              capture_output=True)
            except Exception as e:
                pass  # 静默处理复制失败
            
            # 创建主框架（类似远端指令窗口布局）
            main_frame = tk.Frame(window, padx=10, pady=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 按钮框架（类似远端指令窗口的按钮布局）
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, expand=True)
            
            # 复制Python代码按钮（使用与远端指令窗口一致的风格）
            copy_btn = tk.Button(button_frame, text="📋复制指令", command=copy_script,
                               bg="#2196F3", fg="white", font=("Arial", 9), 
                               padx=10, pady=5, relief=tk.RAISED, bd=2)
            copy_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
            
            # 执行完成按钮（使用与远端指令窗口一致的风格）
            complete_btn = tk.Button(button_frame, text="✅执行完成", command=execution_completed,
                                   bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), 
                                   padx=10, pady=5, relief=tk.RAISED, bd=2)
            complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 运行窗口
            try:
                window.mainloop()
            finally:
                try:
                    window.destroy()
                except:
                    pass  # 忽略destroy错误
            
            return remount_success
            
        except Exception as e:
            print(f"Error: 显示重新挂载窗口失败: {e}")
            return False
    
    def _show_remount_window_subprocess(self, python_script, mount_point, result_path):
        """使用subprocess显示重新挂载窗口，压制IMK信息"""
        import subprocess
        import sys
        import base64
        
        try:
            # 将脚本编码为base64以避免shell转义问题
            script_b64 = base64.b64encode(python_script.encode('utf-8')).decode('ascii')
            
            # 创建subprocess脚本
            subprocess_script = f'''
import sys
import os
import base64
import time

# 抑制所有警告和IMK信息
import warnings
warnings.filterwarnings("ignore")

# 设置环境变量抑制tkinter警告
os.environ["TK_SILENCE_DEPRECATION"] = "1"

try:
    import tkinter as tk
    from tkinter import messagebox
    import subprocess
    
    result = False
    
    # 解码脚本
    python_script = base64.b64decode("{script_b64}").decode('utf-8')
    
    root = tk.Tk()
    root.title("GDS Remount")
    root.geometry("500x60")
    root.resizable(False, False)
    root.attributes('-topmost', True)
    
    # 居中窗口
    root.eval('tk::PlaceWindow . center')
    
    # 音频文件路径
    audio_file_path = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_PROJ/tkinter_bell.mp3"
    
    # 定义统一的聚焦函数
    def force_focus():
        try:
            root.focus_force()
            root.lift()
            root.attributes('-topmost', True)
            
            # macOS特定的焦点获取方法
            import platform
            if platform.system() == 'Darwin':
                import subprocess
                try:
                    # 尝试多个可能的应用程序名称
                    app_names = ['Python', 'python3', 'tkinter', 'Tk']
                    for app_name in app_names:
                        try:
                            subprocess.run(['osascript', '-e', 'tell application "' + app_name + '" to activate'], 
                                          timeout=0.5, capture_output=True)
                            break
                        except:
                            continue
                    
                    # 尝试使用系统事件来强制获取焦点
                    applescript_code = "tell application \\"System Events\\"\\n    set frontmost of first process whose name contains \\"Python\\" to true\\nend tell"
                    subprocess.run(['osascript', '-e', applescript_code], timeout=0.5, capture_output=True)
                except:
                    pass  # 如果失败就忽略
        except:
            pass
    
    # 全局focus计数器和按钮点击标志
    focus_count = 0
    button_clicked = False
    
    # 定义音频播放函数
    def play_bell_in_subprocess():
        try:
            audio_path = audio_file_path
            if os.path.exists(audio_path):
                import platform
                import subprocess
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["afplay", audio_path], 
                                 capture_output=True, timeout=2)
                elif system == "Linux":
                    # 尝试多个Linux音频播放器
                    players = ["paplay", "aplay", "mpg123", "mpv", "vlc"]
                    for player in players:
                        try:
                            subprocess.run([player, audio_path], 
                                         capture_output=True, timeout=2, check=True)
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                elif system == "Windows":
                    # Windows可以使用winsound模块或powershell
                    try:
                        subprocess.run(["powershell", "-c", 
                                      "(New-Object Media.SoundPlayer '" + audio_path + "').PlaySync()"], 
                                     capture_output=True, timeout=2)
                    except:
                        pass
        except Exception:
            pass  # 如果播放失败，忽略错误
    
    # 带focus计数的聚焦函数
    def force_focus_with_count():
        global focus_count, button_clicked
        
        focus_count += 1
        force_focus()
        
        try:
            import threading
            threading.Thread(target=play_bell_in_subprocess, daemon=True).start()
            root.after(100, lambda: trigger_copy_button())
        except Exception:
            pass
    
    # 设置窗口置顶并初始聚焦（第1次，会播放音效）
    root.attributes('-topmost', True)
    force_focus_with_count()
    
    # 自动复制脚本到剪切板
    try:
        root.clipboard_clear()
        root.clipboard_append(python_script)
    except:
        pass
    
    def copy_script():
        global button_clicked
        button_clicked = True
        try:
            subprocess.run(['pbcopy'], input=python_script.encode('utf-8'), 
                          capture_output=True)
            
            # 验证复制是否成功
            try:
                clipboard_content = root.clipboard_get()
                if clipboard_content == python_script:
                    copy_btn.config(text="✅复制成功", bg="#4CAF50")
                else:
                    # 复制不完整，重试一次
                    root.clipboard_clear()
                    root.clipboard_append(python_script)
                    copy_btn.config(text="🔄重新复制", bg="#FF9800")
            except Exception as verify_error:
                # 验证失败但复制可能成功，显示已复制
                copy_btn.config(text="已复制", bg="#4CAF50")
            
            root.after(1500, lambda: copy_btn.config(text="📋 复制指令", bg="#2196F3"))
        except Exception as e:
            copy_btn.config(text="Error: 复制失败", bg="#f44336")
    
    def trigger_copy_button():
        """触发复制按钮的点击效果（用于音效播放时自动触发）"""
        try:
            # 模拟按钮点击效果
            copy_btn.config(relief='sunken')
            root.after(50, lambda: copy_btn.config(relief='raised'))
            # 执行复制功能
            copy_script()
        except Exception:
            pass
    
    def execution_completed():
        global result, button_clicked
        button_clicked = True
        result = True
        root.quit()
    
    # 定期重新获取焦点的函数
    def refocus_window():
        global button_clicked
        if not button_clicked:  # 只有在用户未点击按钮时才重新获取焦点
            try:
                # 使用带focus计数的聚焦函数
                force_focus_with_count()
                # 每30秒重新获取焦点并播放音效
                root.after(30000, refocus_window)
            except:
                pass  # 如果窗口已关闭，忽略错误
    
    # 开始定期重新获取焦点 - 每30秒播放音效
    root.after(30000, refocus_window)
    
    # 主框架
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 按钮框架
    button_frame = tk.Frame(main_frame)
    button_frame.pack(fill=tk.X, expand=True)
    
    # 复制Python代码按钮（使用与远端指令窗口一致的风格）
    copy_btn = tk.Button(button_frame, text="📋 复制指令", command=copy_script,
                       bg="#2196F3", fg="white", font=("Arial", 9), 
                       padx=10, pady=5, relief=tk.RAISED, bd=2)
    copy_btn.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
    
    # 执行完成按钮（使用与远端指令窗口一致的风格）
    complete_btn = tk.Button(button_frame, text="✅执行完成", command=execution_completed,
                           bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), 
                           padx=10, pady=5, relief=tk.RAISED, bd=2)
    complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    # 设置自动关闭定时器（5分钟）
    def timeout_destroy():
        global result
        result = False
        root.destroy()
    
    root.after(300000, timeout_destroy)  # 5分钟超时
    
    # 运行窗口
    root.mainloop()
    
    # 返回结果
    print("success" if result else "cancelled")
    
except Exception as e:
    print("error")
'''
            
            # 运行subprocess窗口，压制所有输出
            result = subprocess.run(
                [sys.executable, '-c', subprocess_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # 完全抑制stderr（包括IMK信息）
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 检查结果
            window_success = result.returncode == 0 and "success" in result.stdout
            
            # 如果用户点击了"✅执行完成"，尝试下载并显示执行结果
            if window_success:
                self._download_and_display_remount_result(result_path)
            
            return window_success
            
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            return False
    
    def _download_and_display_remount_result(self, result_path):
        """下载并显示remount执行结果"""
        try:
            import time
            import json
            
            # 从result_path推断结果文件名
            import os
            result_filename = os.path.basename(result_path)
            
            # 使用统一的等待和读取接口
            file_result = self.remote_commands._wait_and_read_result_file(result_filename)
            
            if file_result.get("success"):
                content = file_result.get("content", "")
                
                # 尝试解析JSON并提取有用信息
                try:
                    result_data = json.loads(content)
                    
                    # 显示关键信息
                    if result_data.get("success"):
                        print(f"挂载点: {result_data.get('mount_point', 'unknown')}")
                        print(f"REMOTE_ROOT ID: {result_data.get('remote_root_id', 'unknown')}")
                        print(f"REMOTE_ENV ID: {result_data.get('remote_env_id', 'unknown')}")
                        print(f"指纹签名: {result_data.get('fingerprint_signature', 'unknown')}")
                        print(f"完成时间: {result_data.get('completed', 'unknown')}")
                        print("重新挂载流程完成！")
                    else:
                        print("挂载失败")
                        if "error" in result_data:
                            print(f"错误: {result_data['error']}")
                    
                except json.JSONDecodeError:
                    lines = content.split('\n')
                    filtered_lines = [line for line in lines if "✅执行完成" not in line and line.strip()]
                    if filtered_lines:
                        for line in filtered_lines:
                            print(line)
                
                return True
            else:
                # 统一接口已经处理了超时和错误信息
                return False
            
        except Exception as e:
            print(f"下载执行结果时出错: {e}")
            return False
    
    def _save_mount_config_to_json(self, mount_point, timestamp, random_hash):
        """保存挂载配置到GOOGLE_DRIVE_DATA/config.json"""
        try:
            import json
            import os
            
            # GOOGLE_DRIVE_DATA路径
            config_dir = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA"
            config_file = os.path.join(config_dir, "config.json")
            
            # 读取现有配置
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {"version": "1.0.0", "description": "Google Drive Shell 配置文件"}
            
            # 计算动态路径
            dynamic_remote_root = f"{mount_point}/MyDrive/REMOTE_ROOT"
            dynamic_remote_env = f"{mount_point}/MyDrive/REMOTE_ENV"
            
            # 更新配置中的动态挂载信息
            if "constants" not in config:
                config["constants"] = {}
            
            # 保存动态挂载配置
            config["constants"].update({
                "REMOTE_ROOT": dynamic_remote_root,
                "REMOTE_ENV": dynamic_remote_env,
                "CURRENT_MOUNT_POINT": mount_point,
                "MOUNT_TIMESTAMP": timestamp,
                "MOUNT_HASH": random_hash,
                "MOUNT_TYPE": "dynamic"
            })
            
            # 尝试从挂载结果文件中读取kora获取的文件夹ID
            remote_root_id = None
            remote_env_id = None
            
            try:
                # 先尝试从挂载结果文件读取（kora方法）
                result_file = f"{mount_point}/MyDrive/REMOTE_ROOT/tmp/remount_{timestamp}.json"
                if os.path.exists(result_file):
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                        remote_root_id = result_data.get('remote_root_id')
                        remote_env_id = result_data.get('remote_env_id')
                        if remote_root_id or remote_env_id:
                            print(f"从挂载结果读取到kora文件夹ID")
                else:
                    # 静默处理：kora方法的结果文件不存在时，不显示警告
                    pass
                    
                # 如果kora方法失败，回退到API方法（静默模式）
                if not remote_root_id:
                    remote_root_id = self._get_folder_id_by_path("REMOTE_ROOT", mount_point, silent=True)
                if not remote_env_id:
                    remote_env_id = self._get_folder_id_by_path("REMOTE_ENV", mount_point, silent=True)
                
                # 保存文件夹ID到配置
                if remote_root_id:
                    config["constants"]["REMOTE_ROOT_FOLDER_ID"] = remote_root_id
                    print(f"REMOTE_ROOT文件夹ID: {remote_root_id}")
                
                if remote_env_id:
                    config["constants"]["REMOTE_ENV_FOLDER_ID"] = remote_env_id
                    print(f"📁 REMOTE_ENV文件夹ID: {remote_env_id}")
                    
            except Exception as e:
                print(f"Warning: 获取文件夹ID失败: {e}")
            
            # 添加动态挂载历史记录
            if "mount_history" not in config:
                config["mount_history"] = []
            
            mount_record = {
                "mount_point": mount_point,
                "timestamp": timestamp,
                "hash": random_hash,
                "remote_root": dynamic_remote_root,
                "remote_env": dynamic_remote_env,
                "created": timestamp
            }
            
            # 保留最近10个挂载记录
            config["mount_history"].insert(0, mount_record)
            config["mount_history"] = config["mount_history"][:10]
            
            # 保存配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"挂载配置已保存到: {config_file}")
            print(f"   REMOTE_ROOT: {dynamic_remote_root}")
            print(f"   REMOTE_ENV: {dynamic_remote_env}")
            print(f"   挂载点: {mount_point}")
            
            return True
            
        except Exception as e:
            print(f"ERROR: 保存挂载配置失败: {e}")
            return False
    
    def _get_folder_id_by_path(self, folder_name, mount_point, silent=False):
        """通过Google Drive API获取文件夹ID"""
        try:
            if not hasattr(self, 'drive_service') or not self.drive_service:
                if not silent:
                    print(f"Warning: drive_service不可用，无法获取{folder_name}文件夹ID")
                return None
            
            # 使用GoogleDriveService的正确API
            # 首先获取MyDrive文件夹的ID
            mydrive_folder_id = self.drive_service._find_folder_by_name("root", "My Drive")
            if not mydrive_folder_id:
                # 如果找不到"My Drive"，尝试直接在root下搜索
                mydrive_folder_id = "root"
            
            # 在MyDrive中搜索目标文件夹
            folder_id = self.drive_service._find_folder_by_name(mydrive_folder_id, folder_name)
            
            if folder_id:
                if not silent:
                    print(f"找到{folder_name}文件夹ID: {folder_id}")
                return folder_id
            else:
                if not silent:
                    print(f"Warning: 未找到{folder_name}文件夹")
                return None
                
        except Exception as e:
            if not silent:
                print(f"ERROR: 获取{folder_name}文件夹ID失败: {e}")
            return None
    
    def _load_paths_from_config(self):
        """从config.json动态加载REMOTE_ROOT和REMOTE_ENV路径"""
        try:
            import json
            import os
            
            # GOOGLE_DRIVE_DATA路径
            config_dir = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_DATA"
            config_file = os.path.join(config_dir, "config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 从配置中读取路径
                constants = config.get('constants', {})
                
                # 如果配置中有动态路径，使用它们
                if 'REMOTE_ROOT' in constants:
                    self.REMOTE_ROOT = constants['REMOTE_ROOT']
                
                if 'REMOTE_ENV' in constants:
                    self.REMOTE_ENV = constants['REMOTE_ENV']
                
                if 'REMOTE_ROOT_FOLDER_ID' in constants:
                    self.REMOTE_ROOT_FOLDER_ID = constants['REMOTE_ROOT_FOLDER_ID']
                
                if 'REMOTE_ENV_FOLDER_ID' in constants:
                    self.REMOTE_ENV_FOLDER_ID = constants['REMOTE_ENV_FOLDER_ID']
                
                # 如果有当前挂载点信息，更新它
                if 'CURRENT_MOUNT_POINT' in constants:
                    self.current_mount_point = constants['CURRENT_MOUNT_POINT']
                    self.dynamic_mode = constants.get('MOUNT_TYPE') == 'dynamic'
                
                # 加载挂载哈希值
                if 'MOUNT_HASH' in constants:
                    self.MOUNT_HASH = constants['MOUNT_HASH']
                
                # 加载挂载时间戳
                if 'MOUNT_TIMESTAMP' in constants:
                    self.MOUNT_TIMESTAMP = constants['MOUNT_TIMESTAMP']
                
            else:
                print("Warning: config.json不存在，使用默认路径")
                
        except Exception as e:
            print(f"ERROR: 从config.json加载路径失败: {e}")
            print("使用默认路径")
    