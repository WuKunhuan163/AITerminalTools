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
                
                # 按路径顺序显示
                sorted_paths = sorted(path_groups.keys())
                for i, path in enumerate(sorted_paths):
                    if i > 0:
                        print()  # 空行分隔不同目录
                    
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
                print("递归列表结果（详细模式）:")
                print(f"路径: {result.get('path', 'unknown')}")
                print(f"总计: {result.get('count', 0)} 项")
                
        except Exception as e:
            print(f"❌ 显示递归ls结果时出错: {e}")
    

    
    def _handle_unified_echo_command(self, args):
        """统一的echo命令处理逻辑 - 支持长内容的base64编码"""
        # 空echo命令
        if not args:
            print("")
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
                    error_msg = result.get("error", "文件创建失败")
                    print(error_msg)
                    return 1
        
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
    
    def _handle_quoted_echo_redirect(self, shell_cmd_clean):
        """处理引号包围的echo重定向命令，使用base64编码"""
        try:
            # 解析echo命令：echo "content" > filename
            import re
            
            # 使用正则表达式提取内容和文件名
            # 匹配格式：echo "content" > filename 或 echo 'content' > filename
            match = re.match(r'^echo\s+(["\'])(.*?)\1\s*>\s*(.+)$', shell_cmd_clean.strip(), re.DOTALL)
            
            if not match:
                print("❌ 无法解析echo重定向命令格式")
                return 1
            
            quote_char = match.group(1)
            content = match.group(2)
            target_file = match.group(3).strip()
        
            # 使用base64编码的文件创建方法
            result = self.file_operations._create_text_file(target_file, content)
            if result.get("success", False):
                return 0
            else:
                error_msg = result.get("error", "文件创建失败")
                print(error_msg)
                return 1
                
        except Exception as e:
            print(f"❌ 处理引号echo命令时出错: {e}")
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
    
    def execute_shell_command(self, shell_cmd, command_identifier=None):
        """执行shell命令 - 新的架构入口点"""
        try:
            # 保存原始命令信息，用于检测引号包围的命令
            original_shell_cmd = shell_cmd
            
            # 检测引号命令标记
            is_quoted_command = shell_cmd.startswith("__QUOTED_COMMAND__")
            if is_quoted_command:
                shell_cmd = shell_cmd[len("__QUOTED_COMMAND__"):]  # 移除标记
            # 显示命令
            # print("=" * 13)
            # display_cmd = shell_cmd.replace('\n', ' ')
            import os
            # local_home = os.path.expanduser("~")
            # if local_home in display_cmd:
            #     display_cmd = display_cmd.replace(local_home, "~")
            # print(f"GDS {display_cmd}")
            # print("=" * 13)
            
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
                    # 使用shlex进行智能分割，保留引号内的换行符
                    import shlex
                    try:
                        # 在shlex.split之前保护~路径，防止本地路径展开
                        protected_cmd = shell_cmd_clean.replace('~/', '__TILDE_SLASH__').replace(' ~', ' __TILDE__')
                        
                        cmd_parts = shlex.split(protected_cmd)
                        
                        # 恢复~路径
                        cmd_parts = [part.replace('__TILDE_SLASH__', '~/').replace('__TILDE__', '~') for part in cmd_parts]
                        
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
            
            # 检查是否包含多命令组合（&&、||或|）
            if ' && ' in shell_cmd or ' || ' in shell_cmd or ' | ' in shell_cmd:
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
                
                # 解析ls命令的参数
                recursive = False
                detailed = False
                path = None
                
                for arg in args:
                    if arg == '-R':
                        recursive = True
                    elif arg == '--detailed':
                        detailed = True
                    elif not arg.startswith('-'):
                        path = arg
                
                # 修复shell展开的家目录路径问题
                if path and path.startswith('/Users/'):
                    import os
                    local_home = os.path.expanduser("~")
                    if path.startswith(local_home):
                        # 将本地家目录路径转换为远程路径格式
                        relative_path = path[len(local_home):].lstrip('/')
                        if relative_path:
                            path = f"~/{relative_path}"
                        else:
                            path = "~"
                
                if recursive:
                    # 使用远端ls -R命令，提高效率
                    if path:
                        cmd_args = ["-R", path]
                    else:
                        cmd_args = ["-R"]
                    
                    # 直接调用远程命令处理，绕过特殊命令检查
                    try:
                        current_shell = self.get_current_shell()
                        if not current_shell:
                            print("❌ 没有活跃的shell会话")
                            return 1
                        
                        # 生成远程命令
                        remote_command_info = self.remote_commands._generate_remote_command("ls", cmd_args, current_shell)
                        remote_command, result_filename = remote_command_info
                        
                        # 显示远程命令窗口
                        title = f"GDS Remote Command: ls -R"
                        instruction = f"Command: ls -R {path if path else ''}\n\nPlease execute the following command in your remote environment:"
                        
                        result = self.remote_commands.show_command_window_subprocess(
                            title=title,
                            command_text=remote_command,
                            timeout_seconds=300
                        )
                        
                        # 处理结果，模拟execute_generic_remote_command的逻辑
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
                                print(result_data.get("error", "❌ 读取结果失败"))
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
                                    print(feedback_result.get("error", "❌ 处理直接反馈失败"))
                                    return 1
                            except Exception as e:
                                print(f"❌ 处理直接反馈时出错: {e}")
                                return 1
                        else:
                            print(result.get("error", "❌ ls -R命令执行失败"))
                            return 1
                    except Exception as e:
                        print(f"❌ ls -R命令执行失败: {e}")
                        import traceback
                        traceback.print_exc()
                        return 1
                else:
                    # 直接使用cmd_ls
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
                dir_names = [arg for arg in args if arg != '-p']
                if not dir_names:
                    print("❌ mkdir command needs directory name(s)")
                    return 1
                
                # 支持多个目录创建 - 使用单个远端命令提高效率
                if len(dir_names) == 1:
                    # 单个目录，直接调用
                    result = self.cmd_mkdir(dir_names[0], recursive)
                    if result.get("success"):
                        return 0
                    else:
                        error_msg = result.get("error", "❌ mkdir命令执行失败")
                        print(error_msg)
                        return 1
                else:
                    # 多个目录，合并为单个远端命令
                    current_shell = self.get_current_shell()
                    if not current_shell:
                        print("❌ 没有活跃的远程shell")
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
                    result = self.execute_generic_remote_command("bash", ["-c", combined_command])
                    
                    if result.get("success"):
                        # 验证所有目录都被创建了
                        all_verified = True
                        for dir_name in dir_names:
                            verification_result = self.verify_creation_with_ls(
                                dir_name, current_shell, creation_type="dir", max_attempts=60
                            )
                            if not verification_result.get("success", False):
                                print(f"❌ 目录 {dir_name} 验证失败")
                                all_verified = False
                        
                        return 0 if all_verified else 1
                    else:
                        error_msg = result.get("error", "多目录创建失败")
                        print(f"❌ {error_msg}")
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
                    # venv命令成功后，同步更新本地shell状态
                    self._sync_venv_state_to_local_shell(args)
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
                    
                    # 显示linter结果（如果有）
                    if result.get("has_linter_issues"):
                        print("=" * 50)
                        linter_output = result.get("linter_output", "")
                        total_issues = linter_output.count("ERROR:") + linter_output.count("WARNING:")
                        print(f"{total_issues} linter warnings or errors found:")
                        print(linter_output)
                        print("=" * 50)
                    elif result.get("linter_error"):
                        print("=" * 50)
                        print(f"Linter check failed: {result.get('linter_error')}")
                        print("=" * 50)
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
                        # 显示stdout输出
                        stdout = result.get("stdout", "")
                        if stdout:
                            print(stdout, end="")
                        
                        # 显示stderr输出
                        stderr = result.get("stderr", "")
                        if stderr:
                            print(stderr, end="", file=sys.stderr)
                    
                    # 返回Python脚本的实际退出码（可能是非零）
                    return result.get("return_code", result.get("returncode", 0))
                else:
                    # 远程执行本身失败（不是Python脚本失败）
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
            elif cmd == 'rm':
                # 使用委托方法处理rm命令
                if not args:
                    print("❌ rm command needs a file or directory name")
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
                    print("❌ rm command needs at least one file or directory to delete")
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
                    print("❌ grep command needs at least a file name")
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
                            print(f"❌ 无法读取文件: {filename}")
                    return 0
                
                # 有模式的grep，只显示匹配行
                result = self.cmd_grep(pattern, *filenames)
                if result.get("success", False):
                    result_data = result.get("result", {})
                    has_matches = False
                    
                    has_file_errors = False
                    for filename, file_result in result_data.items():
                        if "error" in file_result:
                            print(f"❌ {filename}: {file_result['error']}")
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
                                    print(f"❌ 无法读取文件内容: {filename}")
                    
                    # 按照bash grep的标准行为返回退出码
                    if has_file_errors:
                        return 2  # 文件错误（如文件不存在）
                    elif not has_matches:
                        return 1  # 没有匹配项
                    else:
                        return 0  # 有匹配项
                else:
                    print(result.get("error", "❌ Grep命令执行失败"))
                    return 1
            else:
                # 尝试通过通用远程命令执行
                result = self.execute_generic_remote_command(cmd, args)
                if result.get("success", False):
                    stdout = result.get("stdout", "").strip()
                    stderr = result.get("stderr", "").strip()
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
            error_msg = f"❌ Error executing shell command: {e}"
            print(error_msg)
            return 1
    