#!/usr/bin/env python3
"""
Google Drive Modules
重构后的模块导入 - 委托模式版本
"""

# 导入所有模块的函数（保持向后兼容）
# core_utils已合并到remote_commands中
from .drive_process_manager import *
from .sync_config_manager import *
from .remote_shell_manager import *
from .drive_api_service import *
from .shell_commands import *
from .hf_credentials_manager import *

# 导入原有的Google Drive Shell系统类
try:
    from .shell_management import ShellManagement
    from .file_operations import FileOperations
    from .cache_manager import CacheManager
    from .remote_commands import RemoteCommands
    from .path_resolver import PathResolver
    from .sync_manager import SyncManager
    from .file_utils import FileUtils
    from .validation import Validation
    from .verification import Verification
    from .constants import *
except ImportError as e:
    print(f"Warning: Import Google Drive Shell system class failed: {e}")

# 导入管理器类（委托模式）
class CoreUtils:
    """核心工具管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def get_multiline_input_safe(self, *args, **kwargs):
        return get_multiline_input_safe(*args, **kwargs)
    
    def is_run_environment(self, *args, **kwargs):
        from .remote_commands import is_run_environment
        return is_run_environment(*args, **kwargs)
    
    def write_to_json_output(self, *args, **kwargs):
        from .remote_commands import write_to_json_output
        return write_to_json_output(*args, **kwargs)
    
    def copy_to_clipboard(self, *args, **kwargs):
        # copy_to_clipboard现在是RemoteCommands类的方法，需要创建实例
        from .remote_commands import RemoteCommands
        remote_cmd_instance = RemoteCommands(None, None)
        return remote_cmd_instance.copy_to_clipboard(*args, **kwargs)
    
    def show_help(self, *args, **kwargs):
        from .remote_commands import show_help
        return show_help(*args, **kwargs)
    
    def main(self, *args, **kwargs):
        # 临时绕过remote_commands导入问题
        try:
            from .remote_commands import main
            return main(*args, **kwargs)
        except ImportError:
            # 使用简化的main实现
            return self._simplified_main(*args, **kwargs)
    
    def _simplified_main(self, *args, **kwargs):
        """简化的main实现"""
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == '--help':
            print("GOOGLE_DRIVE - Google Drive Remote Control Tool")
            print("Use 'GOOGLE_DRIVE --shell <command>' to execute commands")
            return 0
        
        # 委托给GoogleDriveShell
        try:
            import os
            current_dir = os.path.dirname(os.path.dirname(__file__))
            sys.path.insert(0, current_dir)
            from google_drive_shell import GoogleDriveShell
            
            shell = GoogleDriveShell()
            args = sys.argv[1:]
            
            if not args:
                print("Use --help for usage information")
                return 0
            
            if args[0] == '--shell':
                if len(args) == 1:
                    print("Interactive mode not implemented")
                    return 0
                else:
                    # 直接传递参数列表，避免双重解析
                    return shell.execute_shell_command_with_args(args[1:])
            elif args[0] == '--list-remote-shell':
                return shell.list_shells()
            elif args[0] == '--create-remote-shell':
                return shell.create_shell()
            elif args[0].startswith('--'):
                # 处理未知的--参数，提供错误信息
                print(f"Error: Unknown option '{args[0]}'")
                print("Available options:")
                print("  --shell <command>        Execute shell command")
                print("  --list-remote-shell      List remote shells")
                print("  --create-remote-shell    Create remote shell")
                print("  --help                   Show help")
                print("")
                print("For background tasks, use:")
                print("  --shell \"--bg <command>\"  Run command in background")
                print("")
                print("Examples:")
                print("  GOOGLE_DRIVE --shell \"echo hello\"")
                print("  GOOGLE_DRIVE --shell \"--bg echo hello\"")
                return 1
            else:
                command = ' '.join(args)
                return shell.execute_shell_command(command)
                
        except Exception as e:
            print(f"Error: {e}")
            return 1
    
    def _verify_mkdir_with_ls(self, *args, **kwargs):
        from .verification import VerificationMixin
        return VerificationMixin._verify_mkdir_with_ls(self, *args, **kwargs)

class DriveProcessManager:
    """驱动进程管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def is_google_drive_running(self, *args, **kwargs):
        return is_google_drive_running(*args, **kwargs)
    
    def get_google_drive_processes(self, *args, **kwargs):
        return get_google_drive_processes(*args, **kwargs)
    
    def shutdown_google_drive(self, *args, **kwargs):
        return shutdown_google_drive(*args, **kwargs)
    
    def launch_google_drive(self, *args, **kwargs):
        return launch_google_drive(*args, **kwargs)
    
    def restart_google_drive(self, *args, **kwargs):
        return restart_google_drive(*args, **kwargs)

class SyncConfigManager:
    """同步配置管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def get_sync_config_file(self, *args, **kwargs):
        return get_sync_config_file(*args, **kwargs)
    
    def load_sync_config(self, *args, **kwargs):
        return load_sync_config(*args, **kwargs)
    
    def save_sync_config(self, *args, **kwargs):
        return save_sync_config(*args, **kwargs)
    
    def set_local_sync_dir(self, *args, **kwargs):
        return set_local_sync_dir(*args, **kwargs)
    
    def set_global_sync_dir(self, *args, **kwargs):
        return set_global_sync_dir(*args, **kwargs)
    
    def get_google_drive_status(self, *args, **kwargs):
        return get_google_drive_status(*args, **kwargs)

class SetupWizard:
    """设置向导管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def show_setup_step_1(self, *args, **kwargs):
        return show_setup_step_1(*args, **kwargs)
    
    def show_setup_step_2(self, *args, **kwargs):
        return show_setup_step_2(*args, **kwargs)
    
    def show_setup_step_3(self, *args, **kwargs):
        return show_setup_step_3(*args, **kwargs)
    
    def show_setup_step_4(self, *args, **kwargs):
        return show_setup_step_4(*args, **kwargs)
    
    def console_setup_interactive(self, *args, **kwargs):
        return console_setup_interactive(*args, **kwargs)

class RemoteShellManager:
    """远程Shell管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def create_shell(self, *args, **kwargs):
        return create_shell(*args, **kwargs)
    
    def list_shells(self, *args, **kwargs):
        return list_shells(*args, **kwargs)
    
    def checkout_shell(self, *args, **kwargs):
        return checkout_shell(*args, **kwargs)
    
    def terminate_shell(self, *args, **kwargs):
        return terminate_shell(*args, **kwargs)
    
    def enter_shell_mode(self, *args, **kwargs):
        return enter_shell_mode(*args, **kwargs)

class DriveApiService:
    """Drive API服务管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def open_google_drive(self, *args, **kwargs):
        return open_google_drive(*args, **kwargs)
    
    def test_api_connection(self, *args, **kwargs):
        return test_api_connection(*args, **kwargs)
    
    def list_drive_files(self, *args, **kwargs):
        return list_drive_files(*args, **kwargs)
    
    def upload_file_to_drive(self, *args, **kwargs):
        return upload_file_to_drive(*args, **kwargs)

class ShellCommands:
    """Shell命令管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    

    
    def shell_cd(self, *args, **kwargs):
        # 使用main_instance的cmd_cd方法
        if args:
            path = args[0]
            result = self.main_instance.cmd_cd(path)
            if result.get("success"):
                return 0
            else:
                print(result.get("error", "cd command failed"))
                return 1
        else:
            print(f"Error:  cd command needs a path")
            return 1
    
    def shell_mkdir(self, *args, **kwargs):
        return shell_mkdir(*args, **kwargs)
    
    def shell_pwd(self, *args, **kwargs):
        return shell_pwd(*args, **kwargs)
    
    def handle_shell_command(self, *args, **kwargs):
        return handle_shell_command(*args, **kwargs)

class HfCredentialsManager:
    """HuggingFace凭据管理器"""
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def setup_remote_hf_credentials(self, *args, **kwargs):
        return setup_remote_hf_credentials(*args, **kwargs)
    
    def test_remote_hf_setup(self, *args, **kwargs):
        return test_remote_hf_setup(*args, **kwargs)

# 将所有函数添加到当前模块的全局命名空间
import sys
current_module = sys.modules[__name__]

# 从各个子模块导入函数并添加到当前模块
from . import drive_process_manager, sync_config_manager  # core_utils已合并到remote_commands中
from . import remote_shell_manager, drive_api_service, shell_commands, hf_credentials_manager

# 收集所有子模块的函数
all_modules = [
    drive_process_manager, sync_config_manager,  # core_utils已移除
    remote_shell_manager, drive_api_service, shell_commands, hf_credentials_manager
]

# 将所有函数添加到当前模块的命名空间
for module in all_modules:
    for attr_name in dir(module):
        if not attr_name.startswith('_') and callable(getattr(module, attr_name)):
            setattr(current_module, attr_name, getattr(module, attr_name))

# 导出所有函数和管理器类
__all__ = [
    # Google Drive Shell系统类
    "ShellManagement",
    "FileOperations", 
    "CacheManager",
    "RemoteCommands",
    "PathResolver",
    "SyncManager",
    "FileUtils",
    "Validation",
    "Verification",
    # 委托模式管理器类
    "CoreUtils",
    "DriveProcessManager", 
    "SyncConfigManager",
    "SetupWizard",
    "RemoteShellManager",
    "DriveApiService",
    "ShellCommands",
    "HfCredentialsManager",
    # 函数（向后兼容）
    "checkout_shell",
    "console_setup_interactive",
    "console_setup_step2",
    "console_setup_step3",
    "console_setup_step4",
    "console_setup_step5",
    "console_setup_step6",
    "console_setup_step7",
    "copy_to_clipboard",
    "create_shell",
    "delete_drive_file",
    "download_file_from_drive",
    "enter_shell_mode",
    "exit_shell",
    "extract_folder_id_from_url",
    "generate_shell_id",
    "get_current_shell",
    "get_folder_path_from_api",
    "get_google_drive_processes",
    "get_google_drive_status",
    "get_local_hf_token",
    "get_multiline_input_safe",
    "get_project_id_from_user",
    "get_shells_file",
    "get_setup_config_file",
    "get_sync_config_file",
    "handle_multiple_commands",
    "handle_shell_command",
    "is_google_drive_running",
    "is_run_environment",
    "launch_google_drive",
    "list_drive_files",
    "list_shells",
    "load_shells",
    "load_setup_config",
    "load_sync_config",
    "main",
    "open_dir",
    "open_google_drive",
    "resolve_parent_directory",
    "resolve_path",
    "resolve_relative_path",
    "restart_google_drive",
    "save_shells",
    "save_setup_config",
    "save_sync_config",
    "set_global_sync_dir",
    "set_local_sync_dir",
    "setup_remote_hf_credentials",
    "shell_cd",
    "shell_ls_with_id",
    "shell_mkdir",
    "shell_pwd",
    "shell_rm",
    "show_help",
    "show_setup_step_1",
    "show_setup_step_2",
    "show_setup_step_3",
    "show_setup_step_4",
    "shutdown_google_drive",
    "terminate_shell",
    "test_api_connection",
    "test_drive_folder_access",
    "test_drive_service",
    "test_remote_hf_setup",
    "test_upload_workflow",
    "upload_file_to_drive",
    "url_to_logical_path",
    "write_to_json_output",
]