
class PythonExecution:
    """
    Python code execution (local and remote)
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
        
    def _get_python_executable(self):
        """获取当前应该使用的Python可执行文件路径 - 已废弃，Python版本选择在远程进行"""
        # 这个方法已经不再使用，Python版本选择逻辑已移到远程命令中
        # 保留这个方法以保持兼容性，但总是返回默认值
        return "python3"

    def cmd_python(self, code=None, filename=None, python_args=None, save_output=False):
        """python命令 - 执行Python代码"""
        try:
            if filename:
                # 执行Drive中的Python文件
                return self._execute_python_file(filename, save_output, python_args)
            elif code:
                # 执行直接提供的Python代码
                return self._execute_python_code(code, save_output)
            else:
                return {"success": False, "error": "请提供Python代码或文件名"}
                
        except Exception as e:
            return {"success": False, "error": f"执行Python命令时出错: {e}"}

    def _execute_python_file(self, filename, save_output=False, python_args=None):
        """执行Google Drive中的Python文件"""
        try:
            # 直接在远端执行Python文件，不需要先读取文件内容
            return self._execute_python_file_remote(filename, save_output, python_args)
            
        except Exception as e:
            return {"success": False, "error": f"执行Python文件时出错: {e}"}
    
    def _execute_python_code(self, code, save_output=False, filename=None):
        """执行Python代码并返回结果"""
        try:
            # 直接尝试远程执行，在远程命令中检查和应用虚拟环境
            return self._execute_python_code_remote_unified(code, save_output, filename)
                
        except Exception as e:
            return {"success": False, "error": f"执行Python代码时出错: {e}"}

    def _execute_python_code_remote_unified(self, code, save_output=False, filename=None):
        """统一的远程Python执行方法，在一个命令中检查虚拟环境并执行代码"""
        try:
            import base64
            import time
            import random
            
            # 使用base64编码避免所有bash转义问题
            code_bytes = code.encode('utf-8')
            code_base64 = base64.b64encode(code_bytes).decode('ascii')
            
            # 生成唯一的临时文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            temp_filename = f"python_code_{timestamp}_{random_id}.b64"
            
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            temp_file_path = f"{self.main_instance.REMOTE_ROOT}/tmp/{temp_filename}"
            
            # 构建统一的远程命令：
            # 1. 确保tmp目录存在
            # 2. 将base64字符串写入临时文件
            # 3. source环境文件
            # 4. 从临时文件读取base64并解码执行
            # 5. 清理临时文件
            # 构建命令，在远程环境中智能选择Python可执行文件
            # 所有的Python版本选择逻辑都在远程执行，避免多次窗口调用
            command = f'''
            mkdir -p {self.main_instance.REMOTE_ROOT}/tmp && \\
            echo "{code_base64}" > "{temp_file_path}" && \\
            source {env_file} 2>/dev/null || true
            
            # 在远程环境中智能选择Python可执行文件
            # 1. 检查是否有pyenv设置的Python版本
            PYTHON_EXEC="python3"  # 默认
            PYTHON_BASE_PATH="{self.main_instance.REMOTE_ENV}/python"
            STATE_FILE="$PYTHON_BASE_PATH/python_states.json"
            
            # 获取当前shell ID (简化版本)
            SHELL_ID="default"
            
            # 如果状态文件存在，尝试读取Python版本设置
            if [ -f "$STATE_FILE" ]; then
                # 优先检查local版本
                LOCAL_VERSION=$(python3 -c "
import json, sys
try:
    with open('$STATE_FILE', 'r') as f:
        states = json.load(f)
    print(states.get('shell_${{SHELL_ID}}', ''))
except:
    pass
" 2>/dev/null || echo "")
                
                # 如果没有local版本，检查global版本
                if [ -z "$LOCAL_VERSION" ]; then
                    GLOBAL_VERSION=$(python3 -c "
import json, sys
try:
    with open('$STATE_FILE', 'r') as f:
        states = json.load(f)
    print(states.get('global', ''))
except:
    pass
" 2>/dev/null || echo "")
                    CURRENT_VERSION="$GLOBAL_VERSION"
                else
                    CURRENT_VERSION="$LOCAL_VERSION"
                fi
                
                # 如果找到了版本设置，检查对应的Python是否存在
                if [ -n "$CURRENT_VERSION" ] && [ "$CURRENT_VERSION" != "system" ]; then
                    PYENV_PYTHON="$PYTHON_BASE_PATH/$CURRENT_VERSION/bin/python3"
                    if [ -f "$PYENV_PYTHON" ] && [ -x "$PYENV_PYTHON" ]; then
                        PYTHON_EXEC="$PYENV_PYTHON"
                    fi
                fi
            fi
            
            # 执行Python代码 (修复版本：避免exec嵌套)
            # 直接从base64文件解码并作为脚本执行，而不是通过exec
            base64 -d "{temp_file_path}" | $PYTHON_EXEC
            PYTHON_EXIT_CODE=$?
            
            # 清理临时文件
            rm -f "{temp_file_path}"
            
            # 返回Python脚本的退出码
            exit $PYTHON_EXIT_CODE
            '''.strip()
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", command])
            
            if result.get("success"):
                # 处理新的返回结构：result.data 包含实际的命令执行结果
                data = result.get("data", {})
                return {
                    "success": True,
                    "stdout": data.get("stdout", result.get("stdout", "")),
                    "stderr": data.get("stderr", result.get("stderr", "")),
                    "return_code": data.get("exit_code", result.get("exit_code", 0)),
                    "source": result.get("source", ""),
                    "output_displayed": result.get("output_displayed", False)  # 传递输出显示标记
                }
            else:
                return {
                    "success": False,
                    "error": f"User direct feedback is as above. If there is no feedback, it may indicate the operation is cancelled.",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python执行时出错: {e}"}

    def _execute_python_file_remote(self, filename, save_output=False, python_args=None):
        """远程执行Python文件"""
        try:
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            
            # 构建Python命令，包含文件名和参数
            python_executable = self._get_python_executable()
            python_cmd_parts = [python_executable, filename]
            if python_args:
                python_cmd_parts.extend(python_args)
            python_cmd = ' '.join(python_cmd_parts)
            
            # 构建远程命令：检查并应用虚拟环境，然后执行Python文件
            commands = [
                # source环境文件，如果失败则忽略（会使用默认的PYTHONPATH）
                f"source {env_file} 2>/dev/null || true",

                python_cmd
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", command])
            
            if result.get("success"):
                # 处理新的返回结构：result.data 包含实际的命令执行结果
                data = result.get("data", {})
                return {
                    "success": True,
                    "stdout": data.get("stdout", result.get("stdout", "")),
                    "stderr": data.get("stderr", result.get("stderr", "")),
                    "return_code": data.get("exit_code", result.get("exit_code", 0)),
                    "output_displayed": result.get("output_displayed", False)  # 传递输出显示标记
                }
            else:
                return {
                    "success": False,
                    "error": f"Remote Python file execution failed: {result.get('error', '')}",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python文件执行时出错: {e}"}

    def _execute_python_code_remote(self, code, venv_name, save_output=False, filename=None):
        """在远程虚拟环境中执行Python代码"""
        try:
            # 转义Python代码中的引号和反斜杠
            escaped_code = code.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
            
            # 获取环境文件路径
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            env_file = f"{self.main_instance.REMOTE_ENV}/venv/venv_pythonpath.sh"
            
            # 构建远程命令：source环境文件并执行Python代码
            python_executable = self._get_python_executable()
            commands = [
                # source环境文件，如果失败则忽略
                f"source {env_file} 2>/dev/null || true",
                f'{python_executable} -c "{escaped_code}"'
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_command_interface("bash", ["-c", command])
            
            if result.get("success"):
                # 处理新的返回结构：result.data 包含实际的命令执行结果
                data = result.get("data", {})
                return {
                    "success": True,
                    "stdout": data.get("stdout", result.get("stdout", "")),
                    "stderr": data.get("stderr", result.get("stderr", "")),
                    "return_code": data.get("exit_code", result.get("exit_code", 0)),
                    "environment": venv_name
                }
            else:
                return {
                    "success": False,
                    "error": f"User directed feedback is as above. ",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")
                }
                
        except Exception as e:
            return {"success": False, "error": f"远程Python执行时出错: {e}"}

    def _execute_individual_fallback(self, packages, base_command, options):
        """
        批量安装失败时的逐个安装回退机制
        
        Args:
            packages: 要逐个安装的包列表
            base_command: 基础命令（pip install）
            options: 安装选项
            
        Returns:
            list: 逐个安装的结果列表
        """
        results = []
        
        for package in packages:
            print(f"Individual installation of {package}")
            individual_command = f"{base_command} {' '.join(options)} {package}"
            individual_args = individual_command.split()[2:]  # 去掉 'pip install'
            
            try:
                individual_result = self._execute_standard_pip_install(individual_args)
                individual_success = individual_result.get("success", False)
                
                # 使用GDS ls类似的判定机制验证安装结果
                verification_result = self._verify_package_installation(package)
                final_success = individual_success and verification_result
                
                results.append({
                    "success": final_success,
                    "packages": [package],
                    "batch_size": 1,
                    "method": "individual_fallback",
                    "verification": verification_result
                })
                
                if final_success:
                    print(f"Individual installation of {package} successful")
                else:
                    print(f"Individual installation of {package} failed")
                    
            except Exception as e:
                print(f"Individual installation of {package} error: {str(e)}")
                results.append({
                    "success": False,
                    "packages": [package],
                    "batch_size": 1,
                    "method": "individual_fallback",
                    "error": str(e)
                })
        
        return results

