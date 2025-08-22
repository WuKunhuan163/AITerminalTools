#!/usr/bin/env python3
"""
Google Drive Shell - Virtual environment management
Refactored from file_operations.py
"""

import os
import time
import subprocess
from pathlib import Path
import platform
from typing import Dict
from .linter import GDSLinter

try:
    from ..google_drive_api import GoogleDriveService
except ImportError:
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService

# 导入debug捕获系统


class FileOperationsBase:
    """Base class for file operations modules"""
    
    def __init__(self, drive_service, main_instance=None):
        self.drive_service = drive_service
        self.main_instance = main_instance
        # Add other common initialization as needed
        
    def check_network_connection(self):
        """Check network connection - placeholder"""
        return True
        
    def generate_remote_commands(self, *args, **kwargs):
        """Generate remote commands - placeholder"""
        return self.main_instance.generate_remote_commands(*args, **kwargs) if self.main_instance else None

class VenvApiManager:
    """虚拟环境API管理器 - 统一处理所有虚拟环境相关的API操作"""
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def get_venv_base_path(self):
        """获取虚拟环境基础路径"""
        return f"{self.main_instance.REMOTE_ENV}/venv"
    
    def get_venv_state_file_path(self):
        """获取虚拟环境状态文件路径"""
        return f"{self.get_venv_base_path()}/venv_states.json"
    
    def read_venv_states(self):
        """读取虚拟环境状态文件"""
        try:
            import json
            
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
            
            # 构建文件路径：REMOTE_ENV/venv/venv_states.json
            venv_states_filename = "venv_states.json"
            
            # 首先需要找到REMOTE_ENV/venv文件夹
            try:
                # 列出REMOTE_ENV文件夹的内容，寻找venv子文件夹
                env_files_result = self.drive_service.list_files(
                    folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID, 
                    max_results=100
                )
                
                if not env_files_result['success']:
                    return {"success": False, "error": "无法列出REMOTE_ENV目录内容"}
                
                # 寻找venv文件夹
                venv_folder_id = None
                for file in env_files_result['files']:
                    if file['name'] == 'venv' and file['mimeType'] == 'application/vnd.google-apps.folder':
                        venv_folder_id = file['id']
                        break
                
                if not venv_folder_id:
                    # venv文件夹不存在，返回空状态
                    return {"success": True, "data": {}, "note": "venv文件夹不存在"}
                
                # 在venv文件夹中寻找venv_states.json文件
                venv_files_result = self.drive_service.list_files(
                    folder_id=venv_folder_id, 
                    max_results=100
                )
                
                if not venv_files_result['success']:
                    return {"success": False, "error": "无法列出venv目录内容"}
                
                # 寻找venv_states.json文件
                states_file_id = None
                for file in venv_files_result['files']:
                    if file['name'] == venv_states_filename:
                        states_file_id = file['id']
                        break
                
                if not states_file_id:
                    # 文件不存在，返回空状态
                    return {"success": True, "data": {}, "note": "venv_states.json文件不存在"}
                
                # 读取文件内容
                try:
                    import io
                    from googleapiclient.http import MediaIoBaseDownload
                    
                    request = self.drive_service.service.files().get_media(fileId=states_file_id)
                    fh = io.BytesIO()
                    downloader = MediaIoBaseDownload(fh, request)
                    
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    content = fh.getvalue().decode('utf-8', errors='replace')
                    
                    # 解析JSON内容
                    try:
                        states_data = json.loads(content)
                        return {"success": True, "data": states_data if isinstance(states_data, dict) else {}}
                    except json.JSONDecodeError as e:
                        return {"success": False, "error": f"JSON解析失败: {e}"}
                        
                except Exception as e:
                    return {"success": False, "error": f"读取文件内容失败: {e}"}
                    
            except Exception as e:
                return {"success": False, "error": f"查找文件失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"API读取venv状态失败: {e}"}
    
    def list_venv_environments(self):
        """列出所有虚拟环境"""
        try:
            if not self.drive_service:
                return []
            
            # 首先需要找到REMOTE_ENV/venv文件夹
            try:
                # 列出REMOTE_ENV文件夹的内容，寻找venv子文件夹
                env_files_result = self.drive_service.list_files(
                    folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID, 
                    max_results=100
                )
                
                if not env_files_result['success']:
                    return []
                
                # 寻找venv文件夹
                venv_folder_id = None
                for file in env_files_result['files']:
                    if file['name'] == 'venv' and file['mimeType'] == 'application/vnd.google-apps.folder':
                        venv_folder_id = file['id']
                        break
                
                if not venv_folder_id:
                    # venv文件夹不存在
                    return []
                
                # 在venv文件夹中列出所有文件夹（虚拟环境）
                venv_files_result = self.drive_service.list_files(
                    folder_id=venv_folder_id, 
                    max_results=100
                )
                
                if not venv_files_result['success']:
                    return []
                
                # 过滤出文件夹（虚拟环境），排除venv_states.json等文件
                env_names = []
                for file in venv_files_result['files']:
                    if (file['mimeType'] == 'application/vnd.google-apps.folder' and 
                        not file['name'].startswith('.') and 
                        file['name'] != 'venv_states.json'):
                        env_names.append(file['name'])
                
                return env_names
                    
            except Exception as e:
                return []
                
        except Exception as e:
            return []


    def _initialize_venv_state(self, env_name):
        """为新创建的虚拟环境初始化状态条目"""
        return self._initialize_venv_state_simple(env_name)

    def _initialize_venv_state_simple(self, env_name):
        """简化的状态初始化方法"""
        try:
            # 读取所有状态
            all_states = self._load_all_venv_states()
            
            # 确保environments字段存在
            if 'environments' not in all_states:
                all_states['environments'] = {}
            
            # 检查特定环境是否存在
            if env_name not in all_states['environments']:
                all_states['environments'][env_name] = {
                    'created_at': self._get_current_timestamp(),
                    'packages': {},
                    'last_updated': self._get_current_timestamp()
                }
                
                # 保存更新后的状态
                self._save_all_venv_states(all_states)
                print(f"Initialized state for environment '{env_name}'")
                return True
            else:
                print(f"Environment '{env_name}' already has state entry")
                return True
                
        except Exception as e:
            print(f"Failed to initialize venv state for '{env_name}': {str(e)}")
            return False

    def _initialize_venv_states_batch(self, env_names):
        """批量初始化虚拟环境状态条目（状态已在远程命令中初始化）"""
        # 状态已经在远程命令中初始化，这里只需要记录日志
        print(f"Initialized state for {len(env_names)} environment(s): {', '.join(env_names)}")
        return True

    def _ensure_environment_state_exists(self, env_name):
        """确保环境状态存在（向后兼容）"""
        try:
            all_states = self._load_all_venv_states()
            
            # 检查environments字段是否存在
            if 'environments' not in all_states:
                all_states['environments'] = {}
            
            # 检查特定环境是否存在
            if env_name not in all_states['environments']:
                print(f"Environment '{env_name}' not found in state, creating entry...")
                all_states['environments'][env_name] = {
                    'created_at': self._get_current_timestamp(),
                    'packages': {},
                    'last_updated': self._get_current_timestamp()
                }
                
                # 保存更新后的状态
                self._save_all_venv_states(all_states)
                print(f"Created state entry for environment '{env_name}'")
            
            return True
            
        except Exception as e:
            print(f"Failed to ensure environment state exists: {str(e)}")
            return False

    def _get_current_timestamp(self):
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()

    def _save_all_venv_states(self, all_states):
        """保存完整的虚拟环境状态"""
        try:
            import json
            
            # 构建保存状态的远程命令
            state_file_path = self._get_venv_state_file_path()
            json_content = json.dumps(all_states, indent=2, ensure_ascii=False)
            
            # 转义JSON内容以便在bash中使用
            escaped_json = json_content.replace("'", "'\"'\"'")
            
            remote_command = f'''
    def _get_venv_api_manager(self):
        """获取虚拟环境API管理器"""
        if not hasattr(self, '_venv_api_manager'):
            self._venv_api_manager = VenvApiManager(self.drive_service, self.main_instance)
        return self._venv_api_manager
    
    def _load_all_venv_states(self):
        """从统一的JSON文件加载所有虚拟环境状态（优先使用API，回退到远程命令）"""
        try:
            import json
            
            # 首先尝试通过API读取
            try:
                api_result = self._read_venv_states_via_api()
                if api_result.get("success"):
                    return api_result.get("data", {})
            except Exception as api_error:
                print(f"API call failed: {api_error}")
            
            # 回退到远程命令
            state_file = self._get_venv_state_file_path()
            check_command = f'cat "{state_file}" 2>/dev/null || echo "{{}}"'
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", check_command])
            if result.get("success") and result.get("stdout"):
                stdout_content = result["stdout"].strip()
                try:
                    state_data = json.loads(stdout_content)
                    return state_data if isinstance(state_data, dict) else {}
                except json.JSONDecodeError as e:
                    return {}
            else:
                self._create_initial_venv_states_file()
                return {}
            
        except Exception: 
            import traceback
            traceback.print_exc()
            return {}
    
    def _create_initial_venv_states_file(self):
        """创建初始的虚拟环境状态文件"""
        try:
            import json
            state_file = self._get_venv_state_file_path()
            
            # 创建基本的JSON结构
            initial_structure = {
                "environments": {},
                "created_at": self._get_current_timestamp(),
                "version": "1.0"
            }
            
            # 确保目录存在
            venv_dir = f"{self._get_venv_base_path()}"
            mkdir_command = f'mkdir -p "{venv_dir}"'
            mkdir_result = self.main_instance.execute_generic_remote_command("bash", ["-c", mkdir_command])
            print(f"📁 创建目录结果: {mkdir_result}")
            
            # 写入初始JSON文件
            json_content = json.dumps(initial_structure, indent=2, ensure_ascii=False)
            create_command = f'cat > "{state_file}" << \'EOF\'\n{json_content}\nEOF'
            create_result = self.main_instance.execute_generic_remote_command("bash", ["-c", create_command])
            print(f"📄 创建JSON文件结果: {create_result}")
            
            if create_result.get("success"):
                print(f"✅ 成功创建初始状态文件: {state_file}")
                return True
            else:
                print(f"❌ 创建状态文件失败: {create_result.get('error')}")
                return False
            
        except Exception as e:
            print(f"❌ 创建初始状态文件失败: {e}")
            return False

    def _update_environment_packages_in_json(self, env_name, packages_dict):
        """更新JSON文件中指定环境的包信息"""
        try:
            import datetime
            
            # 加载现有状态
            all_states = self._load_all_venv_states()
            
            # 确保环境存在
            if "environments" not in all_states:
                all_states["environments"] = {}
            
            if env_name not in all_states["environments"]:
                all_states["environments"][env_name] = {
                    "created_at": datetime.datetime.now().isoformat(),
                    "packages": {},
                    "last_updated": datetime.datetime.now().isoformat()
                }
            
            # 更新包信息
            all_states["environments"][env_name]["packages"] = packages_dict
            all_states["environments"][env_name]["last_updated"] = datetime.datetime.now().isoformat()
            
            # 保存更新后的状态
            self._save_all_venv_states(all_states)
            
        except Exception as e:
            print(f"❌ 更新环境包信息失败: {e}")
    
    def _clear_venv_state(self, shell_id):
        """清除指定shell的虚拟环境状态"""
        try:
            # 读取现有的状态文件
            existing_states = self._load_all_venv_states()
            
            # 移除指定shell的状态
            if shell_id in existing_states:
                del existing_states[shell_id]
            
            # 保存更新后的状态
            state_file = self._get_venv_state_file_path()
            import json
            json_content = json.dumps(existing_states, indent=2, ensure_ascii=False)
            
            commands = [
                f"mkdir -p '{self._get_venv_base_path()}'",
                f"cat > '{state_file}' << 'EOF'\n{json_content}\nEOF"
            ]
            
            command_script = " && ".join(commands)
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command_script])
            
            return result.get("success", False)
            
        except Exception as e:
            print(f"⚠️ 清除虚拟环境状态失败: {e}")
            return False

    def _get_current_venv(self):
        """获取当前激活的虚拟环境名称"""
        try:
            current_shell = self.main_instance.get_current_shell()
            
            if not current_shell:
                return None
            
            shell_id = current_shell.get("id", "default")
            
            # 尝试从JSON状态文件加载
            state_data = self._load_venv_state(shell_id)
            
            if state_data and state_data.get("current_venv"):
                return state_data["current_venv"]
            
            # 回退到旧的txt文件格式
            current_venv_file = f"{self._get_venv_base_path()}/current_venv_{shell_id}.txt"
            
            # 通过远程命令检查虚拟环境状态文件
            check_command = f'cat "{current_venv_file}" 2>/dev/null || echo "none"'
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", check_command])
            
            if result.get("success") and result.get("stdout"):
                venv_name = result["stdout"].strip()
                return venv_name if venv_name != "none" else None
            
            return None
            
        except Exception as e:
            print(f"⚠️ 获取当前虚拟环境失败: {e}")
            return None

    def _get_environment_json_path(self, is_remote=True):
        """
        获取环境JSON文件的路径
        
        Args:
            is_remote: 是否为远端路径
            
        Returns:
            str: JSON文件路径
        """
        if is_remote:
            return "/content/drive/MyDrive/REMOTE_ROOT/environments.json"
        else:
            return os.path.join(self.main_instance.REMOTE_ENV or ".", "environments_local.json")
    
