
import os

class VenvOperations:
    """
    Virtual environment state management
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
    
    def cmd_venv(self, *args):
        """
        虚拟环境管理命令
        
        支持的子命令：
        - --create <env_name>: 创建虚拟环境
        - --delete <env_name>: 删除虚拟环境
        - --activate <env_name>: 激活虚拟环境（设置PYTHONPATH）
        - --deactivate: 取消激活虚拟环境（清除PYTHONPATH）
        - --list: 列出所有虚拟环境
        - --current: 显示当前激活的虚拟环境
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 操作结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "Usage: venv --create|--delete|--activate|--deactivate|--list|--current [env_name...]"
                }
            
            action = args[0]
            env_names = args[1:] if len(args) > 1 else []
            
            if action == "--create":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_create_batch(env_names)
            elif action == "--delete":
                if not env_names:
                    return {"success": False, "error": "Please specify at least one environment name"}
                return self._venv_delete_batch(env_names)
            elif action == "--activate":
                if len(env_names) != 1:
                    return {"success": False, "error": "Please specify exactly one environment name for activation"}
                return self._venv_activate(env_names[0])
            elif action == "--deactivate":
                return self._venv_deactivate()
            elif action == "--list":
                return self._venv_list()
            elif action == "--current":
                return self._venv_current()
            else:
                return {
                    "success": False,
                    "error": f"Unknown venv command: {action}. Supported commands: --create, --delete, --activate, --deactivate, --list, --current"
                }
                
        except Exception as e:
            return {"success": False, "error": f"venv命令执行失败: {str(e)}"}
    
    def _venv_create_batch(self, env_names):
        """批量创建虚拟环境"""
        results = []
        for env_name in env_names:
            result = self._venv_create(env_name)
            results.append(result)
        
        # 返回综合结果
        all_success = all(r.get("success", False) for r in results)
        if all_success:
            return {"success": True, "message": f"Created {len(env_names)} virtual environment(s)"}
        else:
            failed = [r.get("error", "Unknown error") for r in results if not r.get("success", False)]
            return {"success": False, "error": failed}
    
    def _get_venv_base_path(self):
        """获取虚拟环境基础路径"""
        return f"{self.main_instance.REMOTE_ENV}/venv"
    
    def _get_venv_api_manager(self):
        """获取虚拟环境API管理器"""
        if not hasattr(self, '_venv_api_manager'):
            try:
                from .venv_manager import VenvApiManager
            except ImportError:
                from venv_manager import VenvApiManager
            self._venv_api_manager = VenvApiManager(self.drive_service, self.main_instance)
        return self._venv_api_manager
    
    def _get_venv_state_file_path(self):
        """获取虚拟环境状态文件路径（统一的JSON格式）"""
        return f"{self._get_venv_base_path()}/venv_states.json"
    
    def _venv_create(self, env_name):
        """创建虚拟环境"""
        if not env_name:
            return {"success": False, "error": "Environment name required"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 使用正确的路径：REMOTE_ENV/venv
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            
            # 使用API管理器检查环境是否已存在
            try:
                api_manager = self._get_venv_api_manager()
                existing_envs = api_manager.list_venv_environments()
                
                if env_name in existing_envs:
                    return {
                        "success": False,
                        "error": f"Virtual environment '{env_name}' already exists"
                    }
                        
            except Exception as e:
                # Silently handle environment existence check errors
                pass
            
            # 使用远程命令创建目录和文件（正确的方式）
            commands = [
                f"mkdir -p '{env_path}'"
            ]
            
            # 使用bash -c执行命令脚本
            command_script = " && ".join(commands)
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command_script])
            
            if result.get("success", False):
                # 检查远程命令的实际执行结果
                exit_code = result.get("exit_code", -1)
                stdout = result.get("stdout", "")
                
                # 远程命令成功执行（exit_code == 0 表示成功）
                if exit_code == 0:
                    print(f"Virtual environment '{env_name}' created successfully")
                    print(f"Environment path: {env_path}")
                    return {"success": True, "message": f"Virtual environment '{env_name}' created successfully"}
                else:
                    # 获取完整的结果数据用于调试
                    stderr = result.get("stderr", "")
                    error_details = []
                    error_details.append(f"remote command failed with exit code {exit_code}")
                    
                    if stdout.strip():
                        error_details.append(f"stdout: {stdout.strip()}")
                    
                    if stderr.strip():
                        error_details.append(f"stderr: {stderr.strip()}")
                    
                    error_message = f"Failed to create virtual environment: {'; '.join(error_details)}"
                    return {"success": False, "error": error_message}
            else:
                return {"success": False, "error": f"Failed to create virtual environment: {result.get('error', 'Unknown error')}"}
                
        except Exception as e:
            return {"success": False, "error": f"Error creating environment '{env_name}': {str(e)}"}
    

    
    def _get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _venv_delete(self, env_name):
        """删除虚拟环境"""
        if not env_name:
            return {"success": False, "error": "Please specify the environment name"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 检查是否为当前激活的环境
            current_status = self._venv_current()
            if current_status.get("success") and current_status.get("current") == env_name:
                return {
                    "success": False, 
                    "error": f"Cannot delete '{env_name}' because it is currently activated. Please deactivate it first."
                }
            
            # 检查环境是否存在
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            
            # 使用Google Drive API检查文件夹是否存在
            if self.main_instance.drive_service:
                try:
                    folders_result = self.main_instance.drive_service.list_files(
                        folder_id=self.main_instance.REMOTE_ENV_FOLDER_ID,
                        max_results=100
                    )
                    folders = folders_result.get('files', []) if folders_result.get('success') else []
                    folders = [f for f in folders if f.get('mimeType') == 'application/vnd.google-apps.folder']
                    
                    existing_env = next((f for f in folders if f['name'] == env_name), None)
                    if not existing_env:
                        return {
                            "success": False,
                            "error": f"Virtual environment '{env_name}' does not exist"
                        }
                        
                except Exception as e:
                    # Silently handle environment existence check errors
                    pass
            
            # 生成删除环境的远程命令，添加执行状态提示
            command = f"rm -rf {env_path}"
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success", False):
                print(f"Virtual environment '{env_name}' deleted successfully")
                return {
                    "success": True,
                    "message": f"Virtual environment '{env_name}' deleted successfully",
                    "action": "delete"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to delete virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error deleting virtual environment: {str(e)}"}
    
    def _venv_delete_batch(self, env_names):
        """批量删除虚拟环境（优化版：一个远程命令完成检查和删除）"""
        # 分类处理环境名（只做基本的保护检查）
        protected_envs = {"GaussianObject"}
        candidate_envs = []
        skipped_protected = []
        
        for env_name in env_names:
            if env_name in protected_envs:
                skipped_protected.append(env_name)
            else:
                candidate_envs.append(env_name)
        
        if skipped_protected:
            print(f"⚠️  Skipped {len(skipped_protected)} protected environment(s): {', '.join(skipped_protected)}")
        
        if not candidate_envs:
            return {
                "success": False,
                "message": "No valid environments to delete",
                "skipped": {"protected": skipped_protected}
            }
        
        print(f"Deleting {len(candidate_envs)} virtual environment(s): {', '.join(candidate_envs)}")
        
        # 生成智能删除命令：在远程端进行所有检查
        current_shell = self.main_instance.get_current_shell()
        shell_id = current_shell.get("id", "default") if current_shell else "default"
        # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
        current_venv_file = f"{self.main_instance.REMOTE_ENV}/current_venv_{shell_id}.txt"
        
        # 构建智能删除脚本
        delete_script_parts = [
            # 获取当前激活的环境
            f'CURRENT_ENV=$(cat "{current_venv_file}" 2>/dev/null || echo "none")'
        ]
        
        # 为每个候选环境添加检查和删除逻辑
        for env_name in candidate_envs:
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            # 构建单个环境的处理脚本
            env_script = f'''
if [ "$CURRENT_ENV" != "{env_name}" ] && [ -d "{env_path}" ]; then
  rm -rf "{env_path}"
fi
'''
            delete_script_parts.append(env_script.strip())
        
        # 最终报告 - 不在远程统计，改为在Python中统计
        
        # 合并为一个命令，使用分号分隔不同的脚本块
        full_command = "; ".join(delete_script_parts)
        
        # 执行单个远程命令
        result = self.main_instance.execute_generic_remote_command("bash", ["-c", full_command])
        
        if result.get("success"):
            # 解析远程输出，统计删除结果
            stdout = result.get("stdout", "")
            
            # 统计符号
            deleted_count = stdout.count("√")  # 成功删除的环境
            skipped_active_count = stdout.count("⚠")  # 跳过的激活环境
            skipped_nonexistent_count = stdout.count("?")  # 不存在的环境
            total_skipped = skipped_active_count + skipped_nonexistent_count + len(skipped_protected)
            
            # 生成详细的结果消息
            if deleted_count > 0:
                message = f"Successfully deleted {deleted_count} environment(s)"
            else:
                message = "No environments were deleted"
            
            if total_skipped > 0:
                skip_details = []
                if len(skipped_protected) > 0:
                    skip_details.append(f"{len(skipped_protected)} protected")
                if skipped_active_count > 0:
                    skip_details.append(f"{skipped_active_count} active")
                if skipped_nonexistent_count > 0:
                    skip_details.append(f"{skipped_nonexistent_count} non-existent")
                message += f" (skipped {total_skipped}: {', '.join(skip_details)})"
            
            return {
                "success": True,
                "message": message,
                "deleted": deleted_count,
                "skipped": {
                    "protected": skipped_protected,
                    "active": skipped_active_count,
                    "non_existent": skipped_nonexistent_count
                }
            }
        else:
            return {
                "success": False,
                "error": f"Failed to execute delete operation: {result.get('error', 'Unknown error')}"
            }
    
    def _venv_activate(self, env_name):
        """激活虚拟环境（设置PYTHONPATH）"""
        if not env_name:
            return {"success": False, "error": "Please specify the environment name"}
        
        if env_name.startswith('.'):
            return {"success": False, "error": "Environment name cannot start with '.'"}
        
        try:
            # 构建远程命令来激活虚拟环境
            venv_states_file = f"{self._get_venv_base_path()}/venv_states.json"
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            
            remote_env_path = self.main_instance.REMOTE_ENV
            remote_command = f'''
# 获取当前shell ID
SHELL_ID="${{GDS_SHELL_ID:-default_shell}}"

# 检查环境是否存在
ENV_PATH="{env_path}"
if [ ! -d "$ENV_PATH" ]; then
    exit 1  # Virtual environment does not exist
fi

# 检查是否已经激活
VENV_STATES_FILE="{venv_states_file}"
if [ -f "$VENV_STATES_FILE" ]; then
    CURRENT_VENV=$(cat "$VENV_STATES_FILE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    shell_id = '$SHELL_ID'
    if shell_id in data and data[shell_id].get('current_venv') == '{env_name}':
        print('already_active')
    else:
        print('not_active')
except:
    print('not_active')
")
else
    CURRENT_VENV="not_active"
fi

if [ "$CURRENT_VENV" = "already_active" ]; then
    echo "Virtual environment '{env_name}' is already active"
    exit 0
fi

# 保存新的状态到JSON文件
mkdir -p "{self._get_venv_base_path()}"
python3 -c "
import json
import os
from datetime import datetime

# 读取现有状态
states = {{}}
if os.path.exists('$VENV_STATES_FILE'):
    try:
        with open('$VENV_STATES_FILE', 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

# 更新当前shell的状态
states['$SHELL_ID'] = {{
    'current_venv': '{env_name}',
    'env_path': '$ENV_PATH',
    'activated_at': datetime.now().isoformat(),
    'shell_id': '$SHELL_ID'
}}

# 保存状态
with open('$VENV_STATES_FILE', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('Virtual environment \\'{env_name}\\' activated successfully')
"

# 创建虚拟环境的shell文件
mkdir -p "{remote_env_path}/venv"
cat > "{remote_env_path}/venv/venv_pythonpath.sh" << 'EOF'
# Virtual environment activation script for {env_name}
export PYTHONPATH="{env_path}:$PYTHONPATH"
EOF

# 验证保存是否成功
sleep 1
VERIFICATION_RESULT=$(cat "$VENV_STATES_FILE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    shell_id = '$SHELL_ID'
    if shell_id in data and data[shell_id].get('current_venv') == '{env_name}':
        print('VERIFICATION_SUCCESS')
    else:
        print('VERIFICATION_FAILED')
except:
    print('VERIFICATION_FAILED')
")

if [ "$VERIFICATION_RESULT" != "VERIFICATION_SUCCESS" ]; then
    exit 1  # Activation verification failed
fi
'''
            
            # 执行远程命令（这会显示远端窗口）
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if result.get("success"):
                output = result.get("stdout", "").strip()
                
                # 检查是否已经激活
                if "already active" in output:
                    print("💡 Virtual environment already activated!")
                    return {
                        "success": True,
                        "message": f"Virtual environment '{env_name}' is already active",
                        "environment": env_name,
                        "skipped": True
                    }
                
                # 检查是否成功激活
                if "activated successfully" in output:
                    # 添加额外的提示信息
                    print("Virtual environment activated successfully")
                    return {
                        "success": True,
                        "message": f"Virtual environment '{env_name}' activated successfully",
                        "env_path": env_path,
                        "pythonpath": env_path,
                        "action": "activate"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Virtual environment activation failed: {output}"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Failed to activate virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error activating virtual environment: {str(e)}"}
    
    def _venv_deactivate(self):
        """取消激活虚拟环境（清除PYTHONPATH）"""
        try:
            # 构建单个远程命令来取消激活虚拟环境（包含验证）
            # 这个命令会：1) 获取当前shell ID，2) 从JSON文件中移除该shell的状态，3) 验证移除成功
            venv_states_file = self._get_venv_state_file_path()
            
            remote_command = f'''
# 获取当前shell ID
SHELL_ID="${{GDS_SHELL_ID:-default_shell}}"

# 从JSON文件中移除当前shell的状态
VENV_STATES_FILE="{venv_states_file}"
if [ -f "$VENV_STATES_FILE" ]; then
    python3 -c "
import json
import os

# 读取现有状态
states = {{}}
if os.path.exists('$VENV_STATES_FILE'):
    try:
        with open('$VENV_STATES_FILE', 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

# 移除当前shell的状态
if '$SHELL_ID' in states:
    del states['$SHELL_ID']

# 保存状态
with open('$VENV_STATES_FILE', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('Virtual environment deactivated successfully')
"
fi

# 删除或重置虚拟环境的shell文件
rm -f "{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"

# 验证移除是否成功
sleep 1
if [ -f "$VENV_STATES_FILE" ]; then
    VERIFICATION_RESULT=$(cat "$VENV_STATES_FILE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    shell_id = '$SHELL_ID'
    if shell_id in data:
        print('VERIFICATION_FAILED')
    else:
        print('VERIFICATION_SUCCESS')
except:
    print('VERIFICATION_SUCCESS')
")
else
    VERIFICATION_RESULT="VERIFICATION_SUCCESS"
fi

if [ "$VERIFICATION_RESULT" != "VERIFICATION_SUCCESS" ]; then
    exit 1  # Deactivation verification failed
fi
'''
            
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", remote_command])
            
            if result.get("success", False):
                # 添加额外的提示信息
                print("Virtual environment deactivated successfully")
                return {
                    "success": True,
                    "message": "Virtual environment deactivated successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to deactivate virtual environment: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error deactivating virtual environment: {str(e)}"}
    
    def _venv_list(self):
        """列出所有虚拟环境（显示当前激活环境的*标记）"""
        try:
            # 使用API管理器列出虚拟环境
            api_manager = self._get_venv_api_manager()
            env_names = api_manager.list_venv_environments()
            
            # 获取当前激活的环境
            current_env = None
            try:
                states = api_manager.read_venv_states()
                if states.get("success"):
                    current_shell = self.main_instance.get_current_shell()
                    shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
                    
                    shell_states = states.get("data", {})
                    if shell_id in shell_states:
                        current_env = shell_states[shell_id].get("current_venv")
            except Exception as e:
                # Silently handle current environment check errors
                current_env = None
            
            if not env_names:
                print("No virtual environments found")
                return {
                    "success": True,
                    "message": "No virtual environments found",
                    "environments": [],
                    "count": 0
                }
            
            # 格式化输出
            env_list = []
            print(f"Virtual environments ({len(env_names)} total):")
            for env_name in sorted(env_names):
                if env_name == current_env:
                    env_list.append(f"* {env_name}")
                    print(f"* {env_name}")
                else:
                    env_list.append(f"  {env_name}")
                    print(f"  {env_name}")
                
            return {
                "success": True,
                "message": f"Virtual environments ({len(env_names)} total):",
                "environments": env_list,
                "count": len(env_names),
                "current": current_env
            }
                
        except Exception as e:
            return {"success": False, "error": f"Error listing environments: {str(e)}"}
    
    def _venv_current(self):
        """显示当前激活的虚拟环境"""
        try:
            # 使用API管理器获取当前状态
            api_manager = self._get_venv_api_manager()
            states = api_manager.read_venv_states()
            
            if states.get("success"):
                # 获取当前shell ID
                current_shell = self.main_instance.get_current_shell()
                shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
                
                # 检查当前shell的状态
                shell_states = states.get("data", {})
                if shell_id in shell_states:
                    current_venv = shell_states[shell_id].get("current_venv")
                    if current_venv:
                        env_path = shell_states[shell_id].get("env_path")
                        activated_at = shell_states[shell_id].get("activated_at")
                        
                        print(f"Current virtual environment: {current_venv}")
                        if env_path:
                            print(f"Environment path: {env_path}")
                        if activated_at:
                            print(f"Activated at: {activated_at}")
                        
                        return {
                            "success": True, 
                            "current": current_venv,
                            "env_path": env_path,
                            "activated_at": activated_at
                        }
                
                # 没有激活的环境
                print("No virtual environment currently activated")
                return {"success": True, "current": None}
            else:
                print("No virtual environment currently activated")
                return {"success": True, "current": None}
                
        except Exception as e:
            print("No virtual environment currently activated")
            return {"success": True, "current": None, "error": str(e)}

