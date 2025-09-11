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
                return self._pyenv_list()
            elif action == "--list-available":
                return self._pyenv_list_available()
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
                    "error": f"Unknown pyenv command: {action}. Supported commands: --install, --uninstall, --list, --list-available, --global, --local, --version, --versions"
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
        print(f"Debug: Starting Python {version} installation process")
        
        if not self._validate_version(version):
            print(f"Debug: Version validation failed for {version}")
            return {"success": False, "error": f"Invalid Python version format: {version}"}
        
        try:
            # 检查版本是否已安装
            if self._is_version_installed(version):
                print(f"Debug: Python {version} is already installed")
                return {
                    "success": False,
                    "error": f"Python {version} is already installed"
                }
            
            # 构建安装路径
            install_path = f"{self._get_python_base_path()}/{version}"
            print(f"Debug: Installation path: {install_path}")
            
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
            print(f"Debug: Executing remote installation command for Python {version}")
            result = self.main_instance.execute_generic_command("bash", ["-c", install_command])
            print(f"Debug: Remote command result - success: {result.get('success')}, exit_code: {result.get('exit_code')}")
            
            if result.get("success") and result.get("exit_code") == 0:
                # 更新状态文件
                print(f"Debug: Installation successful, updating state file")
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
            result = self.main_instance.execute_generic_command("bash", ["-c", uninstall_command])
            
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
            installed_versions = self._get_installed_versions()
            current_version = self._get_current_python_version()
            
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
    
    def _pyenv_list_available(self):
        """列出可下载的Python版本"""
        try:
            # 获取可用的Python版本列表
            # 这里简化处理，提供常用版本
            available_versions = [
                "3.8.10", "3.8.18",
                "3.9.18", "3.9.19",
                "3.10.12", "3.10.13",
                "3.11.7", "3.11.8",
                "3.12.1", "3.12.2"
            ]
            
            print("Available Python versions for installation:")
            for version in available_versions:
                print(f"  {version}")
            
            return {
                "success": True,
                "message": f"Available Python versions ({len(available_versions)} total):",
                "versions": available_versions,
                "count": len(available_versions)
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error listing available Python versions: {str(e)}"}
    
    def _pyenv_global_set(self, version):
        """设置全局默认Python版本"""
        if not self._validate_version(version):
            return {"success": False, "error": f"Invalid Python version format: {version}"}
        
        if not self._is_version_installed(version):
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
            return {"success": False, "error": f"Invalid Python version format: {version}"}
        
        if not self._is_version_installed(version):
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
            current_version = self._get_current_python_version()
            
            if current_version:
                # 获取版本来源（local或global）
                current_shell = self.main_instance.get_current_shell()
                shell_id = current_shell.get("id", "default") if current_shell else "default"
                
                local_version = self._get_python_state(f"shell_{shell_id}")
                if local_version == current_version:
                    source = f"local (shell {shell_id})"
                else:
                    source = "global"
                
                print(f"Current Python version: {current_version} ({source})")
                return {
                    "success": True,
                    "version": current_version,
                    "source": source
                }
            else:
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
        # 这个方法与_pyenv_list相同，保持兼容性
        return self._pyenv_list()
    
    def get_python_executable_path(self, version=None):
        """获取指定版本的Python可执行文件路径"""
        if not version:
            version = self._get_current_python_version()
        
        if not version or version == "system":
            return "python3"  # 使用系统默认Python
        
        if self._is_version_installed(version):
            return f"{self._get_python_base_path()}/{version}/bin/python3"
        else:
            return "python3"  # 回退到系统Python
    
    # 辅助方法
    def _validate_version(self, version):
        """验证Python版本格式"""
        import re
        pattern = r'^\d+\.\d+\.\d+$'  # 匹配 x.y.z 格式
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
            result = self.main_instance.execute_generic_command("bash", ["-c", list_command])
            
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
            result = self.main_instance.execute_generic_command("bash", ["-c", read_command])
            
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

# 读取现有状态
if [ -f "{state_file}" ]; then
    STATES=$(cat "{state_file}")
else
    STATES="{{}}"
fi

# 更新状态
python3 -c "
import json
import sys
from datetime import datetime

try:
    states = json.loads('$STATES')
except:
    states = {{}}

states['{key}'] = '{value}'
states['{key}_updated_at'] = datetime.now().isoformat()

with open('{state_file}', 'w') as f:
    json.dump(states, f, indent=2, ensure_ascii=False)

print('State updated successfully')
"
'''
            
            result = self.main_instance.execute_generic_command("bash", ["-c", update_command])
            
            if not (result.get("success") and result.get("exit_code") == 0):
                raise Exception(f"Failed to update Python state: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            raise Exception(f"Error updating Python state: {str(e)}")
    
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

