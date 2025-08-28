class PipOperations:
    """
    Pip package management and scanning
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance

    def cmd_pip(self, *args, **kwargs):
        """执行pip命令（增强版 - 自动处理虚拟环境、包状态显示）"""
        try:
            if not args:
                return {"success": False, "error": "pip命令需要参数"}
            
            # 构建pip命令
            pip_args = list(args)
            pip_command = " ".join(pip_args)
            
            # 获取当前激活的虚拟环境
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
            
            # 检查是否有激活的虚拟环境
            all_states = self._load_all_venv_states()
            current_venv = None
            env_path = None
            if shell_id in all_states and all_states[shell_id].get("current_venv"):
                current_venv = all_states[shell_id]["current_venv"]
                env_path = f"{self._get_venv_base_path()}/{current_venv}"
            
            # 特殊处理不同的pip命令
            if pip_args[0] == "--show-deps":
                # 直接处理 --show-deps，不需要远程执行，静默获取包信息
                current_packages = self._get_packages_from_json(current_venv) if current_venv else {}
                return self._show_dependency_tree(pip_args, current_packages)
            
            # 检测当前环境中的包（用于显示[√]标记）
            current_packages = self._detect_current_environment_packages(current_venv)
            
            if pip_args[0] == "install":
                return self._handle_pip_install(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "uninstall":
                return self._handle_pip_uninstall(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "list":
                return self._handle_pip_list(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "show":
                return self._handle_pip_show(pip_args[1:], current_venv, env_path, current_packages)
            else:
                # 其他pip命令，使用增强版执行器
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self._execute_pip_command(pip_command, current_venv, target_info)
                
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}

    def _handle_pip_install(self, packages_args, current_venv, env_path, current_packages):
        """处理pip install命令"""
        try:
            if not packages_args:
                return {"success": False, "error": "pip install需要指定包名"}
            
            # 检查是否有 --show-deps 选项 - 现在重定向到独立的依赖分析命令
            if '--show-deps' in packages_args:
                return {"success": False, "error": "Please use 'GDS deps' command for dependency analysis instead of 'pip install --show-deps'"}
            
            # 解析选项
            force_install = '--force' in packages_args
            
            # 过滤选项，获取实际的包列表
            packages_to_install = [pkg for pkg in packages_args if not pkg.startswith('--')]
            
            # 检查已安装包（简化版本，不进行依赖分析）
            if not force_install:
                all_installed = True
                for package in packages_to_install:
                    pkg_name = package.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
                    if pkg_name not in current_packages:
                        all_installed = False
                        break
                
                if all_installed:
                    return {
                        "success": True,
                        "message": "All target packages are already installed.",
                        "installed_packages": packages_to_install
                    }
            
            # 标准安装流程
            install_command = f"install {' '.join(packages_to_install)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            return self._execute_pip_command(install_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip install时出错: {str(e)}"}



    def _handle_pip_list(self, list_args, current_venv, env_path, current_packages):
        """处理pip list命令 - 显示增强的包列表信息"""
        try:
            # 检查是否有--refresh-list选项
            force_refresh = "--refresh-list" in list_args
            if force_refresh:
                list_args = [arg for arg in list_args if arg != "--refresh-list"]
                # 重新获取包信息（强制刷新）
                if current_venv:
                    current_packages = self._get_packages_from_json(current_venv, force_refresh=True)
            
            env_info = f"环境: {current_venv}" if current_venv else "环境: system"
            print(f"Total {len(current_packages)} packages")
            
            if current_packages:
                for pkg_name, version in sorted(current_packages.items()):
                    print(f"  {pkg_name} == {version}")
            
            # 如果有额外的list参数，执行原始pip list命令
            if list_args:
                list_command = f"list {' '.join(list_args)}"
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self._execute_pip_command(list_command, current_venv, target_info)
            
            return {
                "success": True,
                "packages": current_packages,
                "environment": current_venv or "system"
            }
            
        except Exception as e:
            return {"success": False, "error": f"处理pip list时出错: {str(e)}"}

    def _handle_pip_uninstall(self, uninstall_args, current_venv, env_path, current_packages):
        """处理pip uninstall命令"""
        try:
            if not uninstall_args:
                return {"success": False, "error": "pip uninstall需要指定包名"}
            
            # 构建uninstall命令（添加-y自动确认）
            uninstall_command = f"uninstall -y {' '.join(uninstall_args)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            
            print(f"Uninstalling packages: {', '.join(uninstall_args)}")
            
            return self._execute_pip_command(uninstall_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip uninstall时出错: {str(e)}"}

    def _handle_pip_show(self, show_args, current_venv, env_path, current_packages):
        """处理pip show命令 - 显示包的详细信息"""
        try:
            if not show_args:
                return {"success": False, "error": "pip show需要指定包名"}
            
            show_command = f"show {' '.join(show_args)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            return self._execute_pip_command(show_command, current_venv, target_info)
            
        except Exception as e:
                        return {"success": False, "error": f"处理pip show时出错: {str(e)}"}

    # Placeholder methods that need to be implemented or imported from other modules
    def _load_all_venv_states(self):
        """Load venv states using VenvApiManager"""
        try:
            try:
                from .venv_manager import VenvApiManager
            except ImportError:
                from venv_manager import VenvApiManager
            
            api_manager = VenvApiManager(self.drive_service, self.main_instance)
            result = api_manager.read_venv_states()
            if result.get('success') and 'data' in result:
                return result['data']
            return {}
        except Exception as e:
            return {}

    def _get_venv_base_path(self):
        """Get venv base path - should be implemented or imported"""
        try:
            try:
                from .venv_operations import VenvOperations
            except ImportError:
                from venv_operations import VenvOperations
            venv_ops = VenvOperations(self.drive_service, self.main_instance)
            return venv_ops._get_venv_base_path()
        except Exception:
            return "/content/drive/MyDrive/REMOTE_ENV/venv"

    def _get_packages_from_json(self, venv_name, force_refresh=False):
        """Get packages from JSON with directory scanning fallback"""
        try:
            # 如果强制刷新或JSON中没有数据，进行目录扫描
            if force_refresh:
                print("Refreshing package list from directory scan...")
                scanned_packages = self._scan_environment_directory(venv_name)
                if scanned_packages:
                    # 更新JSON文件
                    self._remote_update_json_packages(venv_name, scanned_packages, action="replace")
                    return scanned_packages
            
            # 获取JSON中的包信息
            all_states = self._load_all_venv_states()
            packages_from_json = {}
            
            if all_states and 'environments' in all_states and venv_name in all_states['environments']:
                env_data = all_states['environments'][venv_name]
                packages_from_json = env_data.get('packages', {})
            
            # 如果JSON中没有包信息，进行目录扫描
            if not packages_from_json:
                scanned_packages = self._scan_environment_directory(venv_name)
                if scanned_packages:
                    # 更新JSON文件
                    self._remote_update_json_packages(venv_name, scanned_packages, action="replace")
                    return scanned_packages
            
            return packages_from_json
        except Exception as e:
            return {}

    def _scan_environment_directory(self, env_name):
        """Scan virtual environment directory for installed packages"""
        try:
            env_path = f"{self._get_venv_base_path()}/{env_name}"
            
            # 构建扫描命令，类似备份文件中的实现
            scan_command = f"""
find '{env_path}' -maxdepth 1 -name '*.dist-info' -type d 2>/dev/null | sed 's|.*/||' | head -50 && \\
find '{env_path}' -maxdepth 1 -name '*.egg-info' -type d 2>/dev/null | sed 's|.*/||' | head -50
""".strip()
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", scan_command])
            
            if result.get("success"):
                output = result.get("stdout", "")
                # 解析输出获取包信息
                packages = self._parse_package_scan_output(output)
                return packages
            else:
                return {}
                
        except Exception as e:
            return {}

    def _parse_package_scan_output(self, output):
        """Parse package scan output to extract package names and versions"""
        packages = {}
        try:
            lines = output.strip().split('\n')
            for line in lines:
                line = line.strip()
                # 查找 .dist-info 目录
                if line.endswith('.dist-info'):
                    # 格式通常是 package_name-version.dist-info
                    parts = line.replace('.dist-info', '').split('-')
                    if len(parts) >= 2:
                        package_name = '-'.join(parts[:-1])  # 包名可能包含连字符
                        version = parts[-1]
                        packages[package_name] = version
                # 查找 .egg-info 目录
                elif line.endswith('.egg-info'):
                    parts = line.replace('.egg-info', '').split('-')
                    if len(parts) >= 2:
                        package_name = '-'.join(parts[:-1])
                        version = parts[-1]
                        packages[package_name] = version
        except Exception as e:
            pass
        
        return packages

    def _update_environment_packages_in_json(self, env_name, packages):
        """Update environment packages in JSON file"""
        try:
            # 这里应该调用VenvOperations的更新方法
            # 为简化，我们先记录日志，具体实现可以后续完善
            try:
                from .venv_operations import VenvOperations
            except ImportError:
                from venv_operations import VenvOperations
            venv_ops = VenvOperations(self.drive_service, self.main_instance)
            
            # 通过API管理器更新状态
            api_manager = venv_ops._get_venv_api_manager()
            
            # 构建更新命令（这里需要实现具体的JSON更新逻辑）
            # 实际的JSON更新逻辑需要后续完善
            
        except Exception as e:
            pass

    def _update_json_after_pip_install(self, env_name, pip_command, pip_output):
        """Update JSON file after pip install by parsing pip output"""
        try:
            # 解析pip输出，提取安装的包信息
            installed_packages = self._parse_pip_install_output(pip_output)
            if installed_packages:
                print(f"Updating JSON with {len(installed_packages)} newly installed packages...")
                # 生成JSON更新脚本，但不执行（由主命令合并执行）
                update_script = self._remote_update_json_packages(env_name, installed_packages, action="add")
                return update_script
        except Exception as e:
            print(f"Warning: Failed to update JSON after pip install: {e}")
        return None

    def _parse_pip_install_output(self, pip_output):
        """Parse pip install output to extract installed package information"""
        packages = {}
        try:
            # 查找 "Successfully installed" 行
            lines = pip_output.split('\n')
            for line in lines:
                if 'Successfully installed' in line:
                    # 格式：Successfully installed package1-version1 package2-version2 ...
                    parts = line.replace('Successfully installed', '').strip().split()
                    for part in parts:
                        if '-' in part:
                            # 分离包名和版本，处理包名中可能包含连字符的情况
                            pkg_parts = part.rsplit('-', 1)  # 从右边分割，只分割一次
                            if len(pkg_parts) == 2:
                                package_name, version = pkg_parts
                                packages[package_name] = version
        except Exception as e:
            print(f"Error parsing pip output: {e}")
        
        return packages

    def _remote_update_json_packages(self, env_name, packages, action="add"):
        """Update venv_states.json remotely with new package information"""
        try:
            # 构建Python脚本来更新JSON文件
            packages_json = str(packages).replace("'", '"')  # 转换为JSON格式
            
            python_script = f'''
import json
import os

venv_states_file = "/content/drive/MyDrive/REMOTE_ENV/venv/venv_states.json"
env_name = "{env_name}"
new_packages = {packages_json}
action = "{action}"

# 读取现有状态
states = {{}}
if os.path.exists(venv_states_file):
    try:
        with open(venv_states_file, 'r') as f:
            states = json.load(f)
    except:
        states = {{}}

# 确保environments字段存在
if 'environments' not in states:
    states['environments'] = {{}}

# 确保环境存在
if env_name not in states['environments']:
    states['environments'][env_name] = {{"packages": {{}}}}

# 确保packages字段存在
if 'packages' not in states['environments'][env_name]:
    states['environments'][env_name]['packages'] = {{}}

# 更新包信息
if action == "add":
    states['environments'][env_name]['packages'].update(new_packages)
    print(f"Added {{len(new_packages)}} packages to {{env_name}}")
elif action == "remove":
    for pkg in new_packages:
        if pkg in states['environments'][env_name]['packages']:
            del states['environments'][env_name]['packages'][pkg]
    print(f"Removed {{len(new_packages)}} packages from {{env_name}}")
elif action == "replace":
    states['environments'][env_name]['packages'] = new_packages
    print(f"Replaced package list with {{len(new_packages)}} packages for {{env_name}}")

# 写回文件
with open(venv_states_file, 'w') as f:
    json.dump(states, f, indent=2)

print(f"JSON file updated successfully")
'''
            
            return python_script  # 返回脚本，由调用者合并到主命令中
                
        except Exception as e:
            print(f"Error updating JSON remotely: {e}")

    def _detect_current_environment_packages(self, venv_name):
        """Detect current environment packages with JSON and directory scanning"""
        try:
            if venv_name:
                # 直接从JSON读取，不进行扫描（避免弹窗）
                all_states = self._load_all_venv_states()
                if all_states and 'environments' in all_states and venv_name in all_states['environments']:
                    env_data = all_states['environments'][venv_name]
                    return env_data.get('packages', {})
                else:
                    # 如果JSON中没有数据，返回空字典（用户可以手动--refresh-list）
                    return {}
            else:
                # 对于系统环境，返回基础包
                return {
                    'pip': '23.0.0',
                    'setuptools': '65.0.0'
                }
        except Exception as e:
            return {}



    def _execute_pip_command(self, pip_command, current_env, target_info):
        """强化的pip命令执行，支持错误处理和结果验证"""
        try:
            import time
            import random
            
            # 生成唯一的结果文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            result_filename = f"pip_result_{timestamp}_{random_id}.json"
            result_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}"
            
            # 构建环境设置命令
            pip_target_option = ""
            if current_env:
                env_path = f"{self.main_instance.REMOTE_ENV}/venv/{current_env}"
                # 不设置PYTHONPATH，因为使用统一的远程Python
                # 只添加pip安装目标目录（不使用引号，避免双重引号问题）
                pip_target_option = f" --target {env_path}"
                

            
            # 使用Python subprocess包装pip执行，确保正确捕获所有输出和错误
            python_script = f'''
import subprocess
import json
import sys
from datetime import datetime

print("Starting pip {pip_command}...")
start_time = datetime.now()

# 执行pip命令并捕获所有输出
try:
    pip_cmd_parts = ["pip"] + "{pip_command}".split()
    # 添加虚拟环境目标目录（如果有的话）
    pip_target = "{pip_target_option}"
    if pip_target.strip():
        pip_cmd_parts.extend(pip_target.strip().split())
    
    print(f"Full pip command: {{pip_cmd_parts}}")
    
    # 执行pip命令并捕获输出
    result = subprocess.run(
        pip_cmd_parts,
        capture_output=True,
        text=True
    )
    
    # 显示pip的完整输出
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    # 检查是否有严重ERROR关键字（排除依赖冲突警告）
    has_error = False
    if result.returncode != 0:  # 只有在退出码非0时才检查错误
        has_error = "ERROR:" in result.stderr or "ERROR:" in result.stdout
    
    # 计算执行时间
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"Pip command completed with exit code: {{result.returncode}}")
    if has_error:
        print("⚠️  Detected ERROR messages in pip output")
    
    # 生成结果JSON
    result_data = {{
        "success": result.returncode == 0 and not has_error,
        "pip_command": "{pip_command}",
        "exit_code": result.returncode,
        "environment": "{current_env or 'system'}",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "has_error": has_error,
        "timestamp": datetime.now().isoformat(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration.total_seconds()
    }}
    
    with open("{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}", "w") as f:
        json.dump(result_data, f, indent=2)
    
    # 显示最终状态
    if result.returncode == 0 and not has_error:
        print("pip command completed successfully")
        
        # 如果是install/uninstall命令且成功，更新JSON文件
        if ("{pip_command}".startswith("install") or "{pip_command}".startswith("uninstall")) and "{current_env}":
            try:
                import json
                import os
                
                venv_states_file = "/content/drive/MyDrive/REMOTE_ENV/venv/venv_states.json"
                env_name = "{current_env}"
                
                if "{pip_command}".startswith("install"):
                    # 解析Successfully installed行获取包信息
                    installed_packages = {{}}
                    for line in result.stdout.split('\\n'):
                        if 'Successfully installed' in line:
                            parts = line.replace('Successfully installed', '').strip().split()
                            for part in parts:
                                if '-' in part:
                                    pkg_parts = part.rsplit('-', 1)
                                    if len(pkg_parts) == 2:
                                        package_name, version = pkg_parts
                                        installed_packages[package_name] = version
                    
                    if installed_packages:
                        # 读取现有状态
                        states = {{}}
                        if os.path.exists(venv_states_file):
                            try:
                                with open(venv_states_file, 'r') as f:
                                    states = json.load(f)
                            except:
                                states = {{}}
                        
                        # 确保结构存在
                        if 'environments' not in states:
                            states['environments'] = {{}}
                        if env_name not in states['environments']:
                            states['environments'][env_name] = {{"packages": {{}}}}
                        if 'packages' not in states['environments'][env_name]:
                            states['environments'][env_name]['packages'] = {{}}
                        
                        # 更新包信息
                        states['environments'][env_name]['packages'].update(installed_packages)
                        
                        # 写回文件
                        with open(venv_states_file, 'w') as f:
                            json.dump(states, f, indent=2)
                        
                        print(f"Updated JSON with {{len(installed_packages)}} newly installed packages")
                        
                elif "{pip_command}".startswith("uninstall"):
                    # 解析Successfully uninstalled行获取包信息
                    uninstalled_packages = []
                    for line in result.stdout.split('\\n'):
                        if 'Successfully uninstalled' in line:
                            parts = line.replace('Successfully uninstalled', '').strip().split()
                            for part in parts:
                                if '-' in part:
                                    pkg_parts = part.rsplit('-', 1)
                                    if len(pkg_parts) == 2:
                                        package_name, version = pkg_parts
                                        uninstalled_packages.append(package_name)
                    
                    if uninstalled_packages:
                        # 读取现有状态
                        states = {{}}
                        if os.path.exists(venv_states_file):
                            try:
                                with open(venv_states_file, 'r') as f:
                                    states = json.load(f)
                            except:
                                states = {{}}
                        
                        # 确保结构存在
                        if 'environments' not in states:
                            states['environments'] = {{}}
                        if env_name not in states['environments']:
                            states['environments'][env_name] = {{"packages": {{}}}}
                        if 'packages' not in states['environments'][env_name]:
                            states['environments'][env_name]['packages'] = {{}}
                        
                        # 移除包信息
                        for pkg in uninstalled_packages:
                            if pkg in states['environments'][env_name]['packages']:
                                del states['environments'][env_name]['packages'][pkg]
                        
                        # 写回文件
                        with open(venv_states_file, 'w') as f:
                            json.dump(states, f, indent=2)
                        
                        print(f"Removed {{len(uninstalled_packages)}} packages from JSON")
            except Exception as e:
                print(f"Warning: Failed to update JSON: {{e}}")
    else:
        print(f"pip command failed (exit_code: {{result.returncode}}, has_error: {{has_error}})")

except Exception as e:
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"❌ Error executing pip command: {{e}}")
    result_data = {{
        "success": False,
        "pip_command": "{pip_command}",
        "exit_code": -1,
        "environment": "{current_env or 'system'}",
        "error": str(e),
        "timestamp": datetime.now().isoformat(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration.total_seconds()
    }}
    with open("{self.main_instance.REMOTE_ROOT}/tmp/{result_filename}", "w") as f:
        json.dump(result_data, f, indent=2)
'''
            
            # 构建完整的远程命令
            commands = [
                f'cd "{self.main_instance.REMOTE_ROOT}"',
                "mkdir -p tmp",  # 确保远程tmp目录存在
                f'python3 -c "{python_script.replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34))}"'
            ]
            
            # 过滤空命令（env_setup现在总是空的）
            commands = [cmd for cmd in commands if cmd.strip()]
            full_command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", full_command])
            
            # Debug info removed - pip functionality working correctly
            
            if result.get("success"):
                # 显示远程pip的完整输出
                remote_output = result.get("stdout", "")
                if remote_output:
                    print("Remote pip output:")
                    print(remote_output)
                
                # JSON更新已合并到pip命令中，无需额外处理
                
                return {
                    "success": True,
                    "output": remote_output,
                    "environment": current_env or "system"
                }
            else:
                error_output = result.get("stderr", "")
                if error_output:
                    print("Remote pip error:")
                    print(error_output)
                
                return {
                    "success": False,
                    "error": result.get("error", f"Pip {pip_command} execution failed"),
                    "stderr": error_output
                }
            
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}