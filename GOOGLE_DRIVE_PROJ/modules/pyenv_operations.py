import os
import json
import subprocess

class PyenvOperations:
    """
    Python version management (similar to pyenv)
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
        
    def cmd_pyenv(self, *args):
        """
        Python版本管理命令
        
        支持的子命令：
        - --install <version>: 安装指定Python版本
        - --uninstall <version>: 卸载指定Python版本
        - --list: 列出所有已安装的Python版本
        - --list-available: 列出可下载的Python版本
        - --global <version>: 设置全局默认Python版本
        - --local <version>: 设置当前shell的Python版本
        - --version: 显示当前使用的Python版本
        - --versions: 显示所有已安装版本及当前版本标记
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 操作结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "Usage: pyenv --install|--uninstall|--list|--list-available|--global|--local|--version|--versions [version]"
                }
            
            action = args[0]
            version = args[1] if len(args) > 1 else None
            
            if action == "--install":
                if not version:
                    return {"success": False, "error": "Please specify a Python version to install"}
                return self._pyenv_install(version)
            elif action == "--uninstall":
                if not version:
                    return {"success": False, "error": "Please specify a Python version to uninstall"}
                return self._pyenv_uninstall(version)
            elif action == "--list":
                return {
                    "success": False,
                    "error": "pyenv: no such command `list'. Use 'pyenv --versions' to list installed versions."
                }
            elif action == "--list-available":
                return self._pyenv_list_available()
            elif action == "--update-cache":
                return self._pyenv_update_cache()
            elif action == "--global":
                if not version:
                    return self._pyenv_global_get()
                return self._pyenv_global_set(version)
            elif action == "--local":
                if not version:
                    return self._pyenv_local_get()
                return self._pyenv_local_set(version)
            elif action == "--version":
                return self._pyenv_version()
            elif action == "--versions":
                return self._pyenv_versions()
            else:
                return {
                    "success": False,
                    "error": f"Unknown pyenv command: {action}. Supported commands: --install, --uninstall, --list-available, --update-cache, --global, --local, --version, --versions"
                }
                
        except Exception as e:
            return {"success": False, "error": f"pyenv命令执行失败: {str(e)}"}
    
    def _get_python_base_path(self):
        """获取Python版本基础路径"""
        return f"{self.main_instance.REMOTE_ENV}/python"
    
    def _get_python_state_file_path(self):
        """获取Python版本状态文件路径"""
        return f"{self._get_python_base_path()}/python_states.json"
    
    def _pyenv_install(self, version):
        """安装指定Python版本"""
        if not self._validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        try:
            # 检查版本是否已安装
            if self._is_version_installed(version):
                return {
                    "success": False,
                    "error": f"Python {version} is already installed"
                }
            
            # 构建安装路径
            install_path = f"{self._get_python_base_path()}/{version}"
            
            print(f"Installing Python {version}...")
            print(f"This may take several minutes...")
            
            # 构建远程安装命令
            # 使用pyenv-like installation method via source compilation
            install_command = f'''
# 创建安装目录
mkdir -p "{install_path}"

# 设置临时构建目录
BUILD_DIR="/tmp/python_build_{version}"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 下载Python源码
echo "Downloading Python {version} source code..."
wget -q https://www.python.org/ftp/python/{version}/Python-{version}.tgz

if [ $? -ne 0 ]; then
    echo "Failed to download Python {version}"
    exit 1
fi

# 解压源码
tar -xzf Python-{version}.tgz
cd Python-{version}

# 配置编译选项
echo "Configuring Python {version}..."
./configure --prefix="{install_path}" --enable-optimizations --with-ensurepip=install

if [ $? -ne 0 ]; then
    echo "Failed to configure Python {version}"
    exit 1
fi

# 编译和安装
echo "Compiling Python {version}..."
make -j$(nproc)

if [ $? -ne 0 ]; then
    echo "Failed to compile Python {version}"
    exit 1
fi

echo "Installing Python {version}..."
make install

if [ $? -ne 0 ]; then
    echo "Failed to install Python {version}"
    exit 1
fi

# 清理构建目录
cd /
rm -rf "$BUILD_DIR"

# 设置执行权限
echo "Setting executable permissions..."
chmod -R 755 "{install_path}/bin/"

# 验证安装
if [ -f "{install_path}/bin/python3" ]; then
    echo "Python {version} installed successfully"
    echo "Location: {install_path}"
    {install_path}/bin/python3 --version
else
    echo "Installation verification failed"
    exit 1
fi
'''
            
            # 执行远程安装命令
            result = self.main_instance.execute_command_interface("bash", ["-c", install_command])
            
            if result.get("success") and result.get("exit_code") == 0:
                # 更新状态文件
                self._add_installed_version(version)
                
                return {
                    "success": True,
                    "message": f"Python {version} installed successfully",
                    "version": version,
                    "install_path": install_path
                }
            else:
                stderr = result.get("stderr", "")
                stdout = result.get("stdout", "")
                print(f"Debug: Installation failed - stdout: {stdout[:200]}, stderr: {stderr[:200]}")
                error_msg = f"Failed to install Python {version}"
                if stderr:
                    error_msg += f": {stderr}"
                elif stdout:
                    error_msg += f": {stdout}"
                
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            return {"success": False, "error": f"Error installing Python {version}: {str(e)}"}
    
    def _pyenv_uninstall(self, version):
        """卸载指定Python版本"""
        if not self._validate_version(version):
            return {"success": False, "error": f"Invalid Python version format: {version}"}
        
        try:
            # 检查版本是否已安装
            if not self._is_version_installed(version):
                return {
                    "success": False,
                    "error": f"Python {version} is not installed"
                }
            
            # 检查是否为当前使用的版本
            current_version = self._get_current_python_version()
            if current_version == version:
                return {
                    "success": False,
                    "error": f"Cannot uninstall Python {version} because it is currently in use. Please switch to another version first."
                }
            
            # 构建卸载路径
            install_path = f"{self._get_python_base_path()}/{version}"
            
            print(f"Uninstalling Python {version}...")
            
            # 构建远程卸载命令
            uninstall_command = f'''
if [ -d "{install_path}" ]; then
    rm -rf "{install_path}"
    echo "Python {version} uninstalled successfully"
else
    echo "Python {version} directory not found"
    exit 1
fi
'''
            
            # 执行远程卸载命令
            result = self.main_instance.execute_command_interface("bash", ["-c", uninstall_command])
            
            if result.get("success") and result.get("exit_code") == 0:
                # 更新状态文件
                self._remove_installed_version(version)
                
                return {
                    "success": True,
                    "message": f"Python {version} uninstalled successfully",
                    "version": version
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to uninstall Python {version}: {result.get('error', 'Unknown error')}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error uninstalling Python {version}: {str(e)}"}
    
    def _pyenv_list(self):
        """列出所有已安装的Python版本"""
        try:
            # 使用单个远程命令同时获取已安装版本和当前版本信息
            installed_versions, current_version, _ = self._get_versions_and_current_unified()
            
            if not installed_versions:
                print("No Python versions installed")
                return {
                    "success": True,
                    "message": "No Python versions installed",
                    "versions": [],
                    "count": 0
                }
            
            # 格式化输出
            version_list = []
            print(f"Installed Python versions ({len(installed_versions)} total):")
            for version in sorted(installed_versions):
                if version == current_version:
                    version_list.append(f"* {version}")
                    print(f"* {version}")
                else:
                    version_list.append(f"  {version}")
                    print(f"  {version}")
            
            return {
                "success": True,
                "message": f"Installed Python versions ({len(installed_versions)} total):",
                "versions": version_list,
                "count": len(installed_versions),
                "current": current_version
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error listing Python versions: {str(e)}"}
    
    def _get_versions_and_current_unified(self):
        """使用单个远程命令同时获取已安装版本、当前版本和版本来源信息"""
        try:
            # 构建统一的远程命令，同时获取版本列表和状态文件
            python_base_path = self._get_python_base_path()
            state_file = self._get_python_state_file_path()
            
            unified_command = f'''
# 获取已安装版本
export INSTALLED_VERSIONS=$(ls -1 "{python_base_path}" 2>/dev/null | grep -E "^[0-9]+\.[0-9]+\.[0-9]+$" || echo "")

# 获取状态文件内容
export STATE_CONTENT=$(cat "{state_file}" 2>/dev/null || echo "{{}}")

# 输出结果（JSON格式）
python3 -c "
import json
import sys
import os

# 解析已安装版本
versions_str = os.environ.get('INSTALLED_VERSIONS', '')
installed_versions = [v.strip() for v in versions_str.split('\\n') if v.strip()]

# 解析状态文件
try:
    states = json.loads(os.environ.get('STATE_CONTENT', '{{}}'))
except:
    states = {{}}

# 获取当前shell ID（简化）
shell_id = 'default_shell'

# 确定当前版本和来源（优先级：local > global > None）
current_version = None
version_source = 'system'
local_key = f'shell_{{shell_id}}'
if local_key in states:
    current_version = states[local_key]
    version_source = f'local (shell {{shell_id}})'
elif 'global' in states:
    current_version = states['global']
    version_source = 'global'

# 输出结果
result = {{
    'installed_versions': installed_versions,
    'current_version': current_version,
    'version_source': version_source
}}
print(json.dumps(result))
"
'''
            
            result = self.main_instance.execute_command_interface("bash", ["-c", unified_command])
            
            if result.get("success") and result.get("stdout"):
                try:
                    data = json.loads(result["stdout"])
                    installed_versions = data.get("installed_versions", [])
                    current_version = data.get("current_version")
                    version_source = data.get("version_source", "system")
                    return installed_versions, current_version, version_source
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse unified command result: {e}")
                    return [], None, "system"
            else:
                print(f"Warning: Unified command failed: {result.get('error', 'Unknown error')}")
                return [], None, "system"
                
        except Exception as e:
            print(f"Warning: Error in unified version query: {e}")
            return [], None, "system"
    
    def _pyenv_list_available(self):
        """列出可下载的Python版本"""
        try:
            # 获取缓存的可用版本列表
            available_versions = self._get_cached_available_versions()
            
            # 只显示验证成功的版本
            verified_versions = [v for v in available_versions if v.get("status") == "verified"]
            
            if not verified_versions:
                print("No verified Python versions available for installation.")
                print("Run with --update-cache to refresh the version list.")
                return {
                    "success": True,
                    "message": "No verified versions available",
                    "versions": []
                }
            
            print("Available Python versions for installation:")
            for version_info in verified_versions:
                version = version_info["version"]
                print(f"  {version}")
            
            print(f"\nShowing {len(verified_versions)} verified versions out of {len(available_versions)} tested.")
            
            return {
                "success": True,
                "message": f"Available Python versions ({len(verified_versions)} verified):",
                "versions": [v["version"] for v in verified_versions],
                "count": len(verified_versions)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error listing available Python versions: {str(e)}"}
    
    def _pyenv_update_cache(self):
        """更新Python版本缓存"""
        try:
            print("Updating Python versions cache...")
            print("This may take several minutes as we test each version...")
            
            # 强制重新生成缓存
            verified_versions = self._generate_available_versions_cache()
            
            verified_count = len([v for v in verified_versions if v.get("status") == "verified"])
            total_count = len(verified_versions)
            
            print(f"\nCache update completed!")
            print(f"Tested {total_count} versions, {verified_count} verified as working.")
            
            return {
                "success": True,
                "message": f"Cache updated: {verified_count}/{total_count} versions verified",
                "verified_count": verified_count,
                "total_count": total_count
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error updating cache: {str(e)}"}
    
    def _pyenv_global_set(self, version):
        """设置全局默认Python版本"""
        if not self._validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        # 对于特殊版本（如system），不需要检查是否已安装
        if version not in ["system", "global"] and not self._is_version_installed(version):
            return {"success": False, "error": f"Python {version} is not installed. Use 'pyenv --install {version}' first."}
        
        try:
            # 更新全局Python版本设置
            self._update_python_state("global", version)
            
            print(f"Global Python version set to {version}")
            return {
                "success": True,
                "message": f"Global Python version set to {version}",
                "version": version,
                "scope": "global"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error setting global Python version: {str(e)}"}
    
    def _pyenv_global_get(self):
        """获取全局默认Python版本"""
        try:
            global_version = self._get_python_state("global")
            
            if global_version:
                print(f"Global Python version: {global_version}")
                return {
                    "success": True,
                    "version": global_version,
                    "scope": "global"
                }
            else:
                print("No global Python version set")
                return {
                    "success": True,
                    "version": None,
                    "scope": "global"
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error getting global Python version: {str(e)}"}
    
    def _pyenv_local_set(self, version):
        """设置当前shell的Python版本"""
        if not self._validate_version(version):
            return {
                "success": False, 
                "error": f"Invalid Python version format: '{version}'. Expected format: x.y.z (e.g., 3.9.18) or special identifiers like 'system'"
            }
        
        # 对于特殊版本（如system），不需要检查是否已安装
        if version not in ["system", "global"] and not self._is_version_installed(version):
            return {"success": False, "error": f"Python {version} is not installed. Use 'pyenv --install {version}' first."}
        
        try:
            # 获取当前shell ID
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 更新shell级别的Python版本设置
            self._update_python_state(f"shell_{shell_id}", version)
            
            print(f"Local Python version set to {version} for shell {shell_id}")
            return {
                "success": True,
                "message": f"Local Python version set to {version}",
                "version": version,
                "scope": "local",
                "shell_id": shell_id
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error setting local Python version: {str(e)}"}
    
    def _pyenv_local_get(self):
        """获取当前shell的Python版本"""
        try:
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            local_version = self._get_python_state(f"shell_{shell_id}")
            
            if local_version:
                print(f"Local Python version: {local_version}")
                return {
                    "success": True,
                    "version": local_version,
                    "scope": "local",
                    "shell_id": shell_id
                }
            else:
                print("No local Python version set")
                return {
                    "success": True,
                    "version": None,
                    "scope": "local",
                    "shell_id": shell_id
                }
                
        except Exception as e:
            return {"success": False, "error": f"Error getting local Python version: {str(e)}"}
    
    def _pyenv_version(self):
        """显示当前使用的Python版本"""
        try:
            # 一次性读取状态文件，避免多次远程调用
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 构建一个命令来一次性获取所有需要的信息
            check_command = f'''
            STATE_FILE="{self._get_python_state_file_path()}"
            if [ -f "$STATE_FILE" ]; then
                python3 -c "
import json
try:
    with open('$STATE_FILE', 'r') as f:
        states = json.load(f)
    
    shell_key = 'shell_{shell_id}'
    local_version = states.get(shell_key, '')
    global_version = states.get('global', '')
    
    if local_version:
        print(f'{{local_version}}|local')
    elif global_version:
        print(f'{{global_version}}|global')
    else:
        print('|system')
except:
    print('|system')
"
            else
                echo "|system"
            fi
            '''
            
            result = self.main_instance.execute_command_interface("bash", ["-c", check_command])
            
            if result.get("success") and result.get("stdout"):
                version_info = result["stdout"].strip()
                if "|" in version_info:
                    version, source = version_info.split("|", 1)
                    
                    if version and source != "system":
                        if source == "local":
                            source = f"local (shell {shell_id})"
                        print(f"Current Python version: {version} ({source})")
                        return {
                            "success": True,
                            "version": version,
                            "source": source
                        }
            
            # 如果没有配置或出错，返回系统默认
            print("No Python version configured (using system default)")
            return {
                "success": True,
                "version": "system",
                "source": "system"
            }
                
        except Exception as e:
            return {"success": False, "error": f"Error getting current Python version: {str(e)}"}
    
    def _pyenv_versions(self):
        """显示所有已安装版本及当前版本标记"""
        try:
            # 使用单个远程命令同时获取已安装版本、当前版本和版本来源信息
            installed_versions, current_version, version_source = self._get_versions_and_current_unified()
            
            if not installed_versions:
                print("No Python versions installed")
                return {
                    "success": True,
                    "message": "No Python versions installed",
                    "versions": []
                }
            
            print(f"Installed Python versions ({len(installed_versions)} total):")
            for version in sorted(installed_versions):
                if version == current_version:
                    print(f"* {version}")  # 标记当前版本
                else:
                    print(f"  {version}")
            
            # 显示版本来源信息（已从统一命令获取）
            if version_source and current_version:
                print(f"Current: {current_version} ({version_source})")
            
            return {
                "success": True,
                "message": f"Listed {len(installed_versions)} installed Python versions",
                "versions": installed_versions,
                "current_version": current_version,
                "version_source": version_source
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error listing Python versions: {str(e)}"}
    
    def _get_version_source(self):
        """获取当前Python版本的来源（local/global/system）"""
        try:
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 检查local版本
            local_version = self._get_python_state(f"shell_{shell_id}")
            if local_version:
                return f"local (shell {shell_id})"
            
            # 检查global版本
            global_version = self._get_python_state("global")
            if global_version:
                return "global"
            
            # 默认为system
            return "system"
            
        except Exception:
            return "unknown"
    
    def get_python_executable_path(self, version=None):
        """获取指定版本的Python可执行文件路径"""
        if not version:
            version = self._get_current_python_version()
        
        if not version or version == "system":
            return "python3"  # 使用系统默认Python
        
        # 为了避免多次远程调用，直接构造路径并让远程命令处理fallback
        # 这样只需要一次远程调用，在实际执行时检查文件是否存在
        return f"{self._get_python_base_path()}/{version}/bin/python3"
    
    # 辅助方法
    def _validate_version(self, version):
        """验证Python版本格式"""
        import re
        
        # 特殊版本标识符
        special_versions = ["system", "global"]
        if version in special_versions:
            return True
        
        # 标准版本格式：x.y.z 或 x.y
        pattern = r'^\d+\.\d+(\.\d+)?$'  # 匹配 x.y.z 或 x.y 格式
        return bool(re.match(pattern, version))
    
    def _is_version_installed(self, version):
        """检查指定版本是否已安装"""
        try:
            installed_versions = self._get_installed_versions()
            return version in installed_versions
        except:
            return False
    
    def _get_installed_versions(self):
        """获取所有已安装的Python版本"""
        try:
            # 通过远程命令列出python目录下的版本
            list_command = f'ls -1 "{self._get_python_base_path()}" 2>/dev/null | grep -E "^[0-9]+\.[0-9]+\.[0-9]+$" || echo ""'
            result = self.main_instance.execute_command_interface("bash", ["-c", list_command])
            
            if result.get("success") and result.get("stdout"):
                versions = [v.strip() for v in result["stdout"].split('\n') if v.strip()]
                return versions
            else:
                return []
                
        except Exception as e:
            print(f"Warning: Error getting installed versions: {e}")
            return []
    
    def _get_current_python_version(self):
        """获取当前使用的Python版本"""
        try:
            # 优先级：local > global > system
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
            # 检查local版本
            local_version = self._get_python_state(f"shell_{shell_id}")
            if local_version:
                return local_version
            
            # 检查global版本
            global_version = self._get_python_state("global")
            if global_version:
                return global_version
            
            # 返回None表示使用系统默认
            return None
            
        except Exception as e:
            print(f"Warning: Error getting current Python version: {e}")
            return None
    
    def _get_python_state(self, key):
        """从状态文件获取Python版本信息"""
        try:
            # 通过远程命令读取状态文件
            state_file = self._get_python_state_file_path()
            read_command = f'cat "{state_file}" 2>/dev/null || echo "{{}}"'
            result = self.main_instance.execute_command_interface("bash", ["-c", read_command])
            
            if result.get("success") and result.get("stdout"):
                try:
                    states = json.loads(result["stdout"])
                    return states.get(key)
                except json.JSONDecodeError:
                    return None
            else:
                return None
                
        except Exception as e:
            print(f"Warning: Error reading Python state: {e}")
            return None
    
    def _update_python_state(self, key, value):
        """更新状态文件中的Python版本信息"""
        try:
            state_file = self._get_python_state_file_path()
            
            # 构建更新状态的远程命令
            update_command = f'''
# 确保目录存在
mkdir -p "{self._get_python_base_path()}"

# 更新状态
python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('{state_file}', 'r') as f:
        states = json.load(f)
except:
    states = {{}}

states['{key}'] = '{value}'
states['{key}_updated_at'] = datetime.now().isoformat()

with open('{state_file}', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('State updated successfully')
"
'''
            
            result = self.main_instance.execute_command_interface("bash", ["-c", update_command])
            
            if not (result.get("success") and result.get("exit_code") == 0):
                raise Exception(f"Failed to update Python state: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            raise Exception(f"Error updating Python state: {str(e)}")
    
    def _get_cached_available_versions(self):
        """获取缓存的可用Python版本列表"""
        cache_file = self._get_available_versions_cache_file()
        
        try:
            import json
            import os
            from datetime import datetime, timedelta
            
            # 检查缓存文件是否存在且未过期（7天）
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # 检查缓存是否过期
                cache_time = datetime.fromisoformat(cache_data.get("updated_at", "1970-01-01"))
                if datetime.now() - cache_time < timedelta(days=7):
                    return cache_data.get("versions", [])
            
            # 缓存不存在或已过期，生成新的缓存
            return self._generate_available_versions_cache()
            
        except Exception as e:
            print(f"Warning: Failed to load version cache: {e}")
            # 返回默认版本列表
            return [
                {"version": "3.8.10", "status": "unknown"},
                {"version": "3.8.18", "status": "unknown"},
                {"version": "3.9.18", "status": "unknown"},
                {"version": "3.9.19", "status": "unknown"},
                {"version": "3.10.12", "status": "unknown"},
                {"version": "3.10.13", "status": "unknown"},
                {"version": "3.11.7", "status": "unknown"},
                {"version": "3.11.8", "status": "unknown"},
                {"version": "3.12.1", "status": "unknown"},
                {"version": "3.12.2", "status": "unknown"}
            ]
    
    def _get_available_versions_cache_file(self):
        """获取可用版本缓存文件路径"""
        import os
        cache_dir = os.path.expanduser("~/.local/bin/GOOGLE_DRIVE_DATA")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "python_available_versions.json")
    
    def _generate_available_versions_cache(self):
        """生成可用Python版本缓存（并发验证）"""
        import json
        from datetime import datetime
        import concurrent.futures
        import threading
        
        print("Updating Python versions cache...")
        
        # 生成更全面的Python版本候选列表
        candidate_versions = self._generate_python_version_candidates()
        
        verified_versions = []
        completed_count = 0
        total_count = len(candidate_versions)
        
        # 线程安全的进度更新
        progress_lock = threading.Lock()
        
        def verify_version_with_progress(version):
            nonlocal completed_count
            status = self._verify_python_version_availability(version)
            
            with progress_lock:
                completed_count += 1
                print(f"[{completed_count}/{total_count}] Python {version}: {status}")
            
            return {
                "version": version,
                "status": status,
                "tested_at": datetime.now().isoformat()
            }
        
        print(f"Testing {total_count} Python versions concurrently...")
        
        # 使用线程池并发验证（限制并发数避免过载）
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_version = {
                executor.submit(verify_version_with_progress, version): version 
                for version in candidate_versions
            }
            
            for future in concurrent.futures.as_completed(future_to_version):
                try:
                    result = future.result()
                    verified_versions.append(result)
                except Exception as e:
                    version = future_to_version[future]
                    print(f"Error testing {version}: {e}")
                    verified_versions.append({
                        "version": version,
                        "status": "failed",
                        "tested_at": datetime.now().isoformat()
                    })
        
        # 保存缓存
        cache_data = {
            "versions": verified_versions,
            "updated_at": datetime.now().isoformat()
        }
        
        cache_file = self._get_available_versions_cache_file()
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Cache updated: {cache_file}")
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
        
        return verified_versions
    
    def _generate_python_version_candidates(self):
        """生成Python版本候选列表"""
        candidates = []
        
        # Python 2.x 系列 (常用的后期版本)
        for minor in [6, 7]:
            for patch in range(15, 19):  # 2.6.15-2.6.18, 2.7.15-2.7.18
                candidates.append(f"2.{minor}.{patch}")
        
        # Python 3.0-3.6 系列 (部分版本)
        for minor in range(0, 7):  # 3.0 到 3.6
            for patch in range(0, 3):  # 每个系列测试前几个版本
                candidates.append(f"3.{minor}.{patch}")
        
        # Python 3.7 系列
        for patch in range(0, 18):  # 3.7.0 到 3.7.17
            candidates.append(f"3.7.{patch}")
        
        # Python 3.8 系列 (全面覆盖)
        for patch in range(0, 21):  # 3.8.0 到 3.8.20
            candidates.append(f"3.8.{patch}")
        
        # Python 3.9 系列 (全面覆盖)
        for patch in range(0, 21):  # 3.9.0 到 3.9.20
            candidates.append(f"3.9.{patch}")
        
        # Python 3.10 系列 (全面覆盖)
        for patch in range(0, 16):  # 3.10.0 到 3.10.15
            candidates.append(f"3.10.{patch}")
        
        # Python 3.11 系列 (全面覆盖)
        for patch in range(0, 13):  # 3.11.0 到 3.11.12
            candidates.append(f"3.11.{patch}")
        
        # Python 3.12 系列 (全面覆盖)
        for patch in range(0, 15):  # 3.12.0 到 3.12.14
            candidates.append(f"3.12.{patch}")
        
        # Python 3.13 系列 (全面覆盖)
        for patch in range(0, 10):  # 3.13.0 到 3.13.9
            candidates.append(f"3.13.{patch}")
        
        # Python 3.14-3.20 系列 (未来版本，最多就是下载失败)
        for minor in range(14, 21):  # 3.14 到 3.20
            for patch in range(0, 5):  # 每个系列测试前5个版本
                candidates.append(f"3.{minor}.{patch}")
        
        print(f"Generated {len(candidates)} Python version candidates for testing")
        return candidates
    
    def _verify_python_version_availability(self, version):
        """验证Python版本是否可用（通过下载和测试执行，自动清理临时文件）"""
        import subprocess
        import tempfile
        import os
        import zipfile
        import shutil
        
        temp_dir = None
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix=f"python_test_{version}_")
            
            # 尝试多种下载URL（包含Python 2.x和3.x）
            download_urls = []
            
            # Python 2.x 使用不同的URL模式
            if version.startswith('2.'):
                download_urls = [
                    f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                    f"https://github.com/python/cpython/archive/v{version}.tar.gz"
                ]
            else:
                # Python 3.x 使用标准URL
                download_urls = [
                    f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip",
                    f"https://www.python.org/ftp/python/{version}/Python-{version}.tgz",
                    f"https://github.com/python/cpython/archive/v{version}.tar.gz",
                    f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe"
                ]
            
            for download_url in download_urls:
                try:
                    # 根据URL确定文件名
                    if download_url.endswith('.zip'):
                        file_name = f"python-{version}.zip"
                    elif download_url.endswith('.tgz'):
                        file_name = f"Python-{version}.tgz"
                    elif download_url.endswith('.exe'):
                        file_name = f"python-{version}.exe"
                    else:
                        file_name = f"python-{version}.tar.gz"
                    
                    file_path = os.path.join(temp_dir, file_name)
                    
                    # 尝试下载（减少超时时间提高并发效率）
                    download_success = False
                    try:
                        result = subprocess.run(
                            ["curl", "-s", "-L", "-o", file_path, download_url],
                            capture_output=True,
                            timeout=15  # 减少超时时间
                        )
                        if result.returncode == 0 and os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
                            download_success = True
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
                    
                    if not download_success:
                        continue
                    
                    # 如果是embed版本的zip文件，尝试解压并执行
                    if file_name.endswith('.zip') and 'embed' in download_url:
                        try:
                            extract_dir = os.path.join(temp_dir, f"python-{version}")
                            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                                zip_ref.extractall(extract_dir)
                            
                            # 查找python.exe
                            python_exe = os.path.join(extract_dir, "python.exe")
                            if not os.path.exists(python_exe):
                                # 在Windows embed版本中，可能是python.exe
                                for file in os.listdir(extract_dir):
                                    if file.startswith("python") and file.endswith(".exe"):
                                        python_exe = os.path.join(extract_dir, file)
                                        break
                            
                            if os.path.exists(python_exe):
                                # 尝试执行python --version
                                try:
                                    result = subprocess.run(
                                        [python_exe, "--version"],
                                        capture_output=True,
                                        timeout=5,  # 减少执行超时
                                        text=True
                                    )
                                    if result.returncode == 0 and version in result.stdout:
                                        return "verified"
                                except:
                                    pass
                        except:
                            pass
                    
                    # 如果下载成功，至少标记为可用（即使无法执行测试）
                    return "verified"
                    
                except Exception:
                    continue
            
            # 所有URL都失败
            return "failed"
            
        except Exception as e:
            return "failed"
        finally:
            # 确保清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass  # 忽略清理错误
    
    def _add_installed_version(self, version):
        """添加已安装版本到状态文件"""
        try:
            installed_versions = self._get_installed_versions()
            if version not in installed_versions:
                installed_versions.append(version)
            
            self._update_python_state("installed_versions", json.dumps(sorted(installed_versions)))
            
        except Exception as e:
            print(f"Warning: Failed to update installed versions: {e}")
    
    def _remove_installed_version(self, version):
        """从状态文件移除已安装版本"""
        try:
            installed_versions = self._get_installed_versions()
            if version in installed_versions:
                installed_versions.remove(version)
            
            self._update_python_state("installed_versions", json.dumps(sorted(installed_versions)))
            
        except Exception as e:
            print(f"Warning: Failed to update installed versions: {e}")

