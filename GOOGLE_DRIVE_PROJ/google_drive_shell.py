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
        
        # 确保所有必要的属性都存在
        if not hasattr(self, 'REMOTE_ROOT'):
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        if not hasattr(self, 'REMOTE_ROOT_FOLDER_ID'):
            self.REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"
        
        # 添加虚拟环境管理相关属性
        if not hasattr(self, 'REMOTE_ENV'):
            self.REMOTE_ENV = "/content/drive/MyDrive/REMOTE_ENV"
        if not hasattr(self, 'REMOTE_ENV_FOLDER_ID'):
            self.REMOTE_ENV_FOLDER_ID = "1ZmgwWWIl7qYnGLE66P3kx02M0jxE8D0h"
        
        # 尝试加载Google Drive API服务
        self.drive_service = self._load_drive_service_direct()

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
            print(f"❌ Failed to load shell config: {e}")
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
            print(f"⚠️ Failed to load cache config: {e}")
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
            print(f"⚠️ Failed to load deletion cache: {e}")
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
            print(f"⚠️ Failed to load Google Drive API service: {e}")
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
    
    def cmd_linter(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_linter(*args, **kwargs)
    
    def cmd_pip(self, *args, **kwargs):
        """委托到file_operations管理器"""
        return self.file_operations.cmd_pip(*args, **kwargs)
    
    def create_shell(self, *args, **kwargs):
        """委托到shell_management管理器"""
        return self.shell_management.create_shell(*args, **kwargs)
    
    def execute_generic_remote_command(self, *args, **kwargs):
        """委托到remote_commands管理器"""
        return self.remote_commands.execute_generic_remote_command(*args, **kwargs)
    

    
    def _handle_unified_echo_command(self, args):
        """统一的echo命令处理逻辑 - 简化版本，使用通用的远程命令执行"""
        # 空echo命令
        if not args:
            print("")
            return 0
        
        # 使用通用的远程命令执行机制
        result = self.execute_generic_remote_command('echo', args)
        
        if result.get("success", False):
            # 直接显示远程执行的输出
            stdout = result.get("stdout", "").strip()
            stderr = result.get("stderr", "").strip()
            if stdout:
                print(stdout)
            if stderr:
                print(stderr, file=sys.stderr)
            return 0
        else:
            error_msg = result.get("error", "Echo command failed")
            print(error_msg)
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
    
    def _resolve_absolute_mkdir_path(self, *args, **kwargs):
        """委托到path_resolver管理器"""
        return self.path_resolver._resolve_absolute_mkdir_path(*args, **kwargs)
    
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
    
    def wait_for_file_sync(self, *args, **kwargs):
        """委托到sync_manager管理器"""
        return self.sync_manager.wait_for_file_sync(*args, **kwargs)
    
    def execute_shell_command(self, shell_cmd, command_identifier=None):
        """执行shell命令 - 新的架构入口点"""
        try:
            # 保存原始命令信息，用于检测引号包围的命令
            original_shell_cmd = shell_cmd
            
            # 检测引号命令标记
            is_quoted_command = shell_cmd.startswith("__QUOTED_COMMAND__")
            if is_quoted_command:
                shell_cmd = shell_cmd[len("__QUOTED_COMMAND__"):]  # 移除标记
            # 显示命令分割线
            print("=" * 13)
            # 在banner中将换行符替换为空格，以便单行显示
            display_cmd = shell_cmd.replace('\n', ' ')
            print(f"GDS {display_cmd}")
            print("=" * 13)
            
            # 首先检测引号包围的完整命令（在命令解析之前）
            shell_cmd_clean = shell_cmd.strip()
            if ((shell_cmd_clean.startswith("'") and shell_cmd_clean.endswith("'")) or 
                (shell_cmd_clean.startswith('"') and shell_cmd_clean.endswith('"'))):
                # 去除外层引号，这是一个完整的远程命令
                shell_cmd_clean = shell_cmd_clean[1:-1]
                shell_cmd = shell_cmd_clean  # 更新shell_cmd以便后续使用
                is_quoted_command = True  # 设置引号命令标记

            # 解析命令 - 对edit命令特殊处理
            if shell_cmd_clean.strip().startswith('edit '):
                # edit命令特殊处理：使用正则表达式提取JSON部分，直接调用处理
                import re
                match = re.match(r'^(edit)\s+((?:--\w+\s+)*)([\w.]+)\s+(.+)$', shell_cmd_clean.strip())
                if match:
                    flags_str = match.group(2).strip()
                    filename = match.group(3)
                    json_spec = match.group(4)
                    
                    # 移除JSON参数外层的引号（如果存在）
                    json_spec = json_spec.strip()
                    if ((json_spec.startswith("'") and json_spec.endswith("'")) or 
                        (json_spec.startswith('"') and json_spec.endswith('"'))):
                        json_spec = json_spec[1:-1]
                    
                    # 解析选项参数
                    preview = '--preview' in flags_str
                    backup = '--backup' in flags_str
                    
                    # 直接调用edit命令，避免参数重新处理
                    try:
                        result = self.cmd_edit(filename, json_spec, preview=preview, backup=backup)
                    except KeyboardInterrupt:
                        result = {"success": False, "error": "Operation interrupted by user"}
                    
                    if result.get("success", False):
                        # 显示diff比较（预览模式和正常模式都显示）
                        diff_output = result.get("diff_output", "")
                        
                        if diff_output and diff_output != "No changes detected":
                            print(f"\nEdit comparison: {filename}")
                            print("=" * 50)
                            print(diff_output)
                            print("=" * 50)
                        
                        # 对于正常模式，显示成功信息
                        if result.get("mode") != "preview":
                            print(result.get("message", "\nFile edited successfully"))
                        return 0
                    else:
                        print(result.get("error", "Failed to edit file"))
                        return 1
                else:
                    # 回退到简单分割
                    cmd_parts = shell_cmd_clean.strip().split()
                    cmd = cmd_parts[0] if cmd_parts else ''
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else []
            else:
                # 使用shlex进行智能分割，保留引号内的换行符
                import shlex
                try:
                    cmd_parts = shlex.split(shell_cmd_clean)
                    if not cmd_parts:
                        return 1
                    cmd = cmd_parts[0]
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                except ValueError as e:
                    # 如果shlex解析失败，回退到简单分割
                    print(f"⚠️ Shell command parsing failed with shlex: {e}")
                    print("⚠️ Falling back to simple space splitting")
                    cmd_parts = shell_cmd_clean.split()
                    if not cmd_parts:
                        return 1
                    cmd = cmd_parts[0]
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else []
            
            # 对所有命令应用通用引号和转义处理
            if args:
                args = self._normalize_quotes_and_escapes(args)
            
            # 检查是否包含多命令组合（&& 或 ||）
            if ' && ' in shell_cmd or ' || ' in shell_cmd:
                # 导入shell_commands模块中的具体函数
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from shell_commands import handle_multiple_commands
                return handle_multiple_commands(shell_cmd, command_identifier)
            
            # 路由到具体的命令处理函数
            if cmd == 'pwd':
                # 导入shell_commands模块中的具体函数
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from shell_commands import shell_pwd
                return shell_pwd(command_identifier)
            elif cmd == 'ls':
                # 导入shell_commands模块中的具体函数
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from shell_commands import shell_ls
                path = args[0] if args else None
                return shell_ls(path, command_identifier)
            elif cmd == 'cd':
                if not args:
                    print("❌ cd command needs a path")
                    return 1
                # 使用file_operations中的cmd_cd方法
                path = args[0]
                result = self.cmd_cd(path)
                if result.get("success"):
                    # cd命令成功时不显示输出（像bash一样）
                    return 0
                else:
                    print(result.get("error", "❌ cd命令执行失败"))
                    return 1
            elif cmd == 'mkdir':
                if not args:
                    print("❌ mkdir command needs a directory name")
                    return 1
                # 导入shell_commands模块中的具体函数
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                # 使用file_operations中的cmd_mkdir方法（通过远程命令执行）
                recursive = '-p' in args
                dir_name = [arg for arg in args if arg != '-p'][-1] if args else None
                if not dir_name:
                    print("❌ mkdir command needs a directory name")
                    return 1
                
                # 调用cmd_mkdir方法
                result = self.cmd_mkdir(dir_name, recursive)
                if result.get("success"):
                    return 0
                else:
                    print(result.get("error", "❌ mkdir命令执行失败"))
                    return 1
            elif cmd == 'touch':
                if not args:
                    print("❌ touch command needs a filename")
                    return 1
                
                filename = args[0]
                
                # 调用cmd_touch方法
                result = self.cmd_touch(filename)
                if result.get("success"):
                    return 0
                else:
                    print(result.get("error", "❌ touch命令执行失败"))
                    return 1
            elif cmd == 'rm':
                if not args:
                    print("❌ rm command needs a file or directory")
                    return 1
                # 导入shell_commands模块中的具体函数
                current_dir = os.path.dirname(__file__)
                modules_dir = os.path.join(current_dir, 'modules')
                if modules_dir not in sys.path:
                    sys.path.append(modules_dir)
                
                from modules.shell_commands import shell_rm
                recursive = '-rf' in ' '.join(args) or '-r' in args
                target = [arg for arg in args if not arg.startswith('-')][-1] if args else None
                if not target:
                    print("❌ rm command needs a file or directory")
                    return 1
                return shell_rm(target, recursive, command_identifier)
            elif cmd == 'echo':
                # 简化的echo处理：直接使用统一的echo命令处理
                return self._handle_unified_echo_command(args)
            elif cmd == 'help':
                # 导入shell_commands模块中的具体函数
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
                    print(result.get("message", "Virtual environment operation completed"))
                    # 如果是--list命令，还要打印环境列表
                    if args and args[0] == '--list' and result.get("environments"):
                        for env in result.get("environments", []):
                            print(env)
                    return 0
                else:
                    error_message = result.get("error", "Virtual environment operation failed")
                    print(error_message)
                    
                    # 显示stderr如果存在
                    stderr = result.get("stderr", "")
                    if stderr.strip():
                        print(f"\n❌ STDERR内容:\n{stderr.strip()}")
                    
                    # 显示用户错误信息（如果有）
                    user_error = result.get("user_error_info", "")
                    if user_error:
                        print(f"\n👤 用户提供的错误信息:\n{user_error}")
                    
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
            elif cmd == 'cat':
                # 使用委托方法处理cat命令
                if not args:
                    print("❌ cat command needs a file name")
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
                    print("❌ edit command needs a file name and edit specification")
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
                    print("❌ edit command needs a file name and edit specification")
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
                        print("=" * 50)
                        
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
                        print("=" * 50)
                    elif diff_output == "No changes detected":
                        print("No changes detected")
                    
                    # 对于正常模式，显示成功信息
                    if result.get("mode") != "preview":
                        print(result.get("message", "\nFile edited successfully"))
                    return 0
                else:
                    print(result.get("error", "Failed to edit file"))
                    return 1
            elif cmd == 'read':
                # 使用委托方法处理read命令
                if not args:
                    print("❌ read command needs a file name")
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
                    print("❌ read command needs a file name")
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
                    print("❌ python command needs a file name or code")
                    return 1
                if args[0] == '-c':
                    # 执行Python代码
                    if len(args) < 2:
                        print("❌ python -c needs code")
                        return 1
                    # 过滤掉命令行选项参数，只保留Python代码
                    code_args = []
                    for arg in args[1:]:
                        if not arg.startswith('--'):
                            code_args.append(arg)
                    
                    # 统一处理已经在execute_shell_command中完成
                    code = ' '.join(code_args)
                    
                    # 移除外层引号
                    if code.startswith('"') and code.endswith('"'):
                        code = code[1:-1]
                    elif code.startswith("'") and code.endswith("'"):
                        code = code[1:-1]
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
                        # 显示stdout输出
                        stdout = result.get("stdout", "")
                        if stdout:
                            print(stdout, end="")
                        
                        # 显示stderr输出
                        stderr = result.get("stderr", "")
                        if stderr:
                            print(stderr, end="", file=sys.stderr)
                    
                    # 返回Python脚本的退出码
                    return result.get("returncode", 0)
                else:
                    print(result.get("error", "Python execution failed"))
                    return 1
            elif cmd == 'upload':
                # 使用委托方法处理upload命令
                if not args:
                    print("❌ upload command needs a file name")
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
                            print("❌ --target-dir option requires a directory path")
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
                    print("❌ No source files specified for upload")
                    return 1
                
                result = self.cmd_upload(source_files, target_path, force=force, remove_local=remove_local)
                if result.get("success", False):
                    print(result.get("message", "Upload completed"))
                    return 0
                else:
                    print(result.get("error", "Upload failed"))
                    return 1
            elif cmd == 'upload-folder':
                # 使用委托方法处理upload-folder命令
                if not args:
                    print("❌ upload-folder command needs a folder path")
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
                    print("❌ upload-folder command needs a folder path")
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
                    print("❌ download command needs a file name")
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
                    print("❌ mv command needs a source file and target file")
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
            elif cmd == 'grep':
                # 使用委托方法处理grep命令
                if len(args) < 2:
                    print("❌ grep command needs a pattern and file name")
                    return 1
                # 统一转义处理已经在execute_shell_command中完成
                pattern = args[0]
                # 移除pattern的外层引号
                if pattern.startswith('"') and pattern.endswith('"'):
                    pattern = pattern[1:-1]
                elif pattern.startswith("'") and pattern.endswith("'"):
                    pattern = pattern[1:-1]
                filenames = args[1:]
                result = self.cmd_grep(pattern, *filenames)
                if result.get("success", False):
                    # 格式化输出grep结果
                    result_data = result.get("result", {})
                    for filename, file_result in result_data.items():
                        if "error" in file_result:
                            print(f"{filename}: {file_result['error']}")
                        else:
                            occurrences = file_result.get("occurrences", {})
                            if occurrences:
                                # 获取文件内容用于显示匹配行
                                cat_result = self.cmd_cat(filename)
                                if cat_result.get("success"):
                                    lines = cat_result["output"].split('\n')
                                    for line_num, positions in occurrences.items():
                                        # 确保line_num是整数类型
                                        line_index = int(line_num) - 1
                                        if 0 <= line_index < len(lines):
                                            line_content = lines[line_index]
                                            print(f"{filename}:{line_num}:{line_content}")
                                else:
                                    # 如果无法读取文件内容，只显示匹配位置
                                    for line_num, positions in occurrences.items():
                                        print(f"{filename}:{line_num}: (unable to read content)")
                            # 没有匹配时不输出（符合grep行为）
                    return 0
                else:
                    print(result.get("error", "Grep failed"))
                    return 1
            else:
                print(f"Unknown command: {cmd}")
                return 1
                
        except Exception as e:
            error_msg = f"❌ Error executing shell command: {e}"
            print(error_msg)
            return 1
    