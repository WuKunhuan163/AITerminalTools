
class PythonExecution:
    """
    Python code execution (local and remote)
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance

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
            # 构建命令，确保Python脚本的退出码被正确捕获
            command = f'''
            mkdir -p {self.main_instance.REMOTE_ROOT}/tmp && \\
            echo "{code_base64}" > "{temp_file_path}" && \\
            source {env_file} 2>/dev/null || true
            
            # 执行Python代码并捕获退出码
            python3 -c "import base64; exec(base64.b64decode(open(\\"{temp_file_path}\\").read().strip()).decode(\\"utf-8\\"))"
            PYTHON_EXIT_CODE=$?
            
            # 清理临时文件
            rm -f "{temp_file_path}"
            
            # 返回Python脚本的退出码
            exit $PYTHON_EXIT_CODE
            '''.strip()
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success"):
                return {
                    "success": True,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "return_code": result.get("exit_code", 0),
                    "source": result.get("source", "")
                }
            else:
                return {
                    "success": False,
                    "error": f"User direct feedback is as above. ",
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
            python_cmd_parts = ['python3', filename]
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
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success"):
                return {
                    "success": True,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "return_code": result.get("exit_code", 0)
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

    def _execute_non_bash_safe_commands(self, commands, action_description, context_name=None, expected_pythonpath=None):
        """
        生成非bash-safe命令供用户在远端主shell中执行，并自动验证结果
        """
        try:
            import time
            import random
            import json
            import os
            
            # 生成唯一的结果文件名
            timestamp = int(time.time())
            random_id = f"{random.randint(1000, 9999):04x}"
            result_filename = f"venv_result_{timestamp}_{random_id}.json"
            # 生成远程和本地文件路径
            import os
            bin_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            local_result_file = f"{bin_dir}/GOOGLE_DRIVE_DATA/remote_files/{result_filename}"
            # 使用远程路径而不是本地路径
            remote_result_file = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/{result_filename}"
            
            # 生成包含验证的完整命令
            original_command = " && ".join(commands)
            full_commands = [
                f"mkdir -p {self.main_instance.REMOTE_ROOT}/tmp",  # 确保远程tmp目录存在
                original_command,
                # 验证PYTHONPATH并输出到远程JSON文件
                f'echo "{{" > {remote_result_file}',
                f'echo "  \\"success\\": true," >> {remote_result_file}',
                f'echo "  \\"action\\": \\"{action_description}\\"," >> {remote_result_file}',
                f'echo "  \\"pythonpath\\": \\"$PYTHONPATH\\"," >> {remote_result_file}',
                f'echo "  \\"timestamp\\": \\"$(date)\\"" >> {remote_result_file}',
                f'echo "}}" >> {remote_result_file}'
            ]
            
            full_command_with_verification = " && ".join(full_commands)
            
            # 使用统一的tkinter窗口界面
            context_str = f" '{context_name}'" if context_name else ""
            window_title = f"Execute command to {action_description}{context_str}"
            
            # 调用统一的远程命令窗口
            try:
                result = self.main_instance.remote_commands._show_generic_command_window(
                    action_description,  # cmd
                    [context_name] if context_name else [],  # args
                    full_command_with_verification,  # remote_command
                    window_title  # debug_info
                )
                
                if result.get("action") == "failed":
                    return {
                        "success": False, 
                        "error": result.get("message", "User reported execution failed"),
                        "source": "user_reported_failure"
                    }
                elif result.get("action") == "direct_feedback":
                    # 用户提供了直接反馈，跳过文件检测
                    print ()
                    return {
                        "success": True,
                        "message": result.get("message", "Command executed successfully"),
                        "source": "direct_feedback"
                    }
            except Exception as e:
                # 如果tkinter窗口失败，回退到终端提示
                print(f"\n🔧 Execute the following command in remote main shell to {action_description}{context_str}:")
                print(f"Command: {full_command_with_verification}")
                print("💡 Copy and execute the above command, then press Ctrl+D")
            
            # 如果使用了tkinter窗口，等待文件检测
            remote_file_path = f"~/tmp/{result_filename}"
            
            # 等待并检测结果文件
            print("⏳ Validating results ...", end="", flush=True)
            max_attempts = 60
            
            for attempt in range(max_attempts):
                try:
                    # 检查远程文件是否存在
                    check_result = self.main_instance.remote_commands._check_remote_file_exists(remote_result_file)
                    
                    if check_result.get("exists"):
                        # 文件存在，读取内容
                        print("√")  # 成功标记
                        read_result = self.main_instance.remote_commands._read_result_file_via_gds(result_filename)
                        
                        if read_result.get("success"):
                            result_data = read_result.get("data", {})
                            
                            # 验证结果（PYTHONPATH验证或其他验证）
                            if expected_pythonpath:
                                # PYTHONPATH验证模式（用于虚拟环境）
                                actual_pythonpath = result_data.get("pythonpath", "")
                                
                                if expected_pythonpath in actual_pythonpath:
                                    return {
                                        "success": True,
                                        "message": f"{action_description.capitalize()}{context_str} completed and verified",
                                        "pythonpath": actual_pythonpath,
                                        "result_data": result_data
                                    }
                                else:
                                    return {
                                        "success": False,
                                        "error": f"PYTHONPATH verification failed: expected {expected_pythonpath}, got {actual_pythonpath}",
                                        "result_data": result_data
                                    }
                            else:
                                # 通用验证模式（用于pip等命令）
                                return {
                                    "success": True,
                                    "message": f"{action_description.capitalize()}{context_str} completed successfully",
                                    "result_data": result_data
                                }
                        else:
                            return {"success": False, "error": f"Error reading result: {read_result.get('error')}"}
                    
                    # 文件不存在，等待1秒并输出进度点
                    time.sleep(1)
                    print(".", end="", flush=True)
                    
                except Exception as e:
                    print(f"\n❌ Error checking result file: {str(e)[:100]}")
                    return {"success": False, "error": f"Error checking result: {e}"}
            
            print(f"\n❌ Timeout: No result file found after {max_attempts} seconds")
            return {"success": False, "error": "Execution timeout - no result file found"}
            
        except Exception as e:
            print(f"Error: {e}")
            return {"success": False, "error": f"Error generating command: {e}"}

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
            commands = [
                # source环境文件，如果失败则忽略
                f"source {env_file} 2>/dev/null || true",
                f'python3 -c "{escaped_code}"'
            ]
            command = " && ".join(commands)
            
            # 执行远程命令
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            if result.get("success"):
                return {
                    "success": True,
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "return_code": result.get("exit_code", 0),
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

    def _execute_python_code_local(self, code, save_output=False, filename=None):
        """在本地执行Python代码"""
        try:
            import subprocess
            import tempfile
            import os
            
            # 创建临时Python文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # 执行Python代码
                result = subprocess.run(
                    ['/usr/bin/python3', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30秒超时
                )
                
                # 清理临时文件
                os.unlink(temp_file_path)
                
                # 准备结果
                execution_result = {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "filename": filename
                }
                
                # 如果需要保存输出到Drive
                if save_output and (result.stdout or result.stderr):
                    output_filename = f"{filename}_output.txt" if filename else "python_output.txt"
                    output_content = f"=== Python Execution Result ===\n"
                    output_content += f"Return code: {result.returncode}\n\n"
                    
                    if result.stdout:
                        output_content += f"=== STDOUT ===\n{result.stdout}\n"
                    
                    if result.stderr:
                        output_content += f"=== STDERR ===\n{result.stderr}\n"
                    
                    # 尝试保存到Drive（如果失败也不影响主要功能）
                    try:
                        save_result = self._create_text_file(output_filename, output_content)
                        if save_result["success"]:
                            execution_result["output_saved"] = output_filename
                    except:
                        pass  # 保存失败不影响主要功能
                
                return execution_result
                
            except subprocess.TimeoutExpired:
                os.unlink(temp_file_path)
                return {"success": False, "error": "Python代码执行超时（30秒）"}
            except Exception as e:
                os.unlink(temp_file_path)
                return {"success": False, "error": f"执行Python代码时出错: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"准备Python执行环境时出错: {e}"}

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

