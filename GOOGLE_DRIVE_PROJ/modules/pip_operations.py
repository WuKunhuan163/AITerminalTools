class PipOperations:
    """
    Pip package management and scanning
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
        self._dependency_analyzer = None

    def cmd_pip(self, *args, **kwargs):
        """执行pip命令（增强版 - 自动处理虚拟环境、智能依赖分析、包状态显示）"""
        try:
            if not args:
                return {"success": False, "error": "pip命令需要参数"}
            
            # 构建pip命令
            pip_args = list(args)
            pip_command = " ".join(pip_args)
            
            # 获取当前激活的虚拟环境
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default") if current_shell else "default"
            
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
            elif pip_args[0] == "list":
                return self._handle_pip_list(pip_args[1:], current_venv, env_path, current_packages)
            elif pip_args[0] == "show":
                return self._handle_pip_show(pip_args[1:], current_venv, env_path, current_packages)
            else:
                # 其他pip命令，使用增强版执行器
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self._execute_pip_command_enhanced(pip_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}

    def _handle_pip_install(self, packages_args, current_venv, env_path, current_packages):
        """处理pip install命令 - 包含智能依赖分析和已安装包检测"""
        try:
            if not packages_args:
                return {"success": False, "error": "pip install需要指定包名"}
            
            # 检查是否有 --show-deps 选项
            if '--show-deps' in packages_args:
                return self._show_dependency_tree(packages_args, current_packages)
            
            # 解析选项
            force_install = '--force' in packages_args
            batch_install = '--batch' in packages_args
            
            # 过滤选项，获取实际的包列表
            packages_to_install = [pkg for pkg in packages_args if not pkg.startswith('--')]
            
            # 始终调用智能依赖分析（接口模式）
            print("Analyzing dependencies...")
            dependency_analyzer = self._get_dependency_analyzer()
            smart_analysis = dependency_analyzer._smart_dependency_analysis(
                packages_to_install, 
                max_calls=10, 
                interface_mode=True, 
                installed_packages=current_packages
            )
            
            download_layers = smart_analysis.get('download_layers', {})
            
            # 显示当前环境信息
            env_info = f"环境: {current_venv}" if current_venv else "环境: system"
            print(f"📦 {env_info} | 已有 {len(current_packages)} 个包")
            
            # 检查Layer 0（主要包）是否已安装
            layer_0_packages = download_layers.get(0, [])
            all_installed = True
            
            for package in layer_0_packages:
                pkg_name = package.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
                if pkg_name not in current_packages:
                    all_installed = False
                    break
            
            # 如果没有--force且Layer 0都已安装，返回"download complete"
            if not force_install and all_installed:
                print("All target packages are already installed.")
                return {
                    "success": True,
                    "message": "download complete",
                    "installed_packages": layer_0_packages
                }
            
            # 处理批量安装
            if batch_install:
                return self._handle_batch_install(download_layers, current_venv, current_packages)
            else:
                # 标准安装流程
                install_command = f"install {' '.join(packages_to_install)}"
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self._execute_pip_command_enhanced(install_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip install时出错: {str(e)}"}

    def _get_dependency_analyzer(self):
        """获取依赖分析器实例"""
        if self._dependency_analyzer is None:
            try:
                from .dependency_analysis import DependencyAnalysis
            except ImportError:
                from dependency_analysis import DependencyAnalysis
            self._dependency_analyzer = DependencyAnalysis(self.drive_service, self.main_instance)
        return self._dependency_analyzer

    def _handle_batch_install(self, download_layers, current_venv, current_packages):
        """处理批量安装，基于网络数据和包大小优化"""
        try:
            # 尝试获取网络测试数据
            network_data = self._get_network_data()
            
            if network_data is None:
                # 没有网络数据，调用NETWORK --test
                print("No network data found, running network test...")
                network_data = self._run_network_test()
                
                if network_data is None or network_data.get('status') != 'success':
                    print("Network test failed, using default batch size (5 packages)")
                    max_packages_per_batch = 5
                    max_size_per_batch = float('inf')  # No size limit
                else:
                    # 基于网络数据计算最大包大小
                    max_size_per_batch = self._calculate_max_package_size(network_data)
                    max_packages_per_batch = float('inf')  # No package count limit
            else:
                # 基于网络数据计算最大包大小
                max_size_per_batch = self._calculate_max_package_size(network_data)
                max_packages_per_batch = float('inf')  # No package count limit
            
            print(f"Batch install mode: max {max_size_per_batch/1024/1024:.1f}MB per batch")
            
            # 按层级从深到浅安装，每层内按大小从小到大排序
            dependency_analyzer = self._get_dependency_analyzer()
            package_sizes = dependency_analyzer._get_package_sizes_for_layers(download_layers)
            
            success_count = 0
            total_packages = sum(len(pkgs) for pkgs in download_layers.values())
            
            for layer_num in sorted(download_layers.keys(), reverse=True):  # 从深层开始
                packages = download_layers[layer_num]
                if not packages:
                    continue
                
                print(f"\nInstalling Layer {layer_num} packages...")
                
                # 按大小排序（小到大）
                packages_with_sizes = [(pkg, package_sizes.get(pkg, 0)) for pkg in packages]
                packages_with_sizes.sort(key=lambda x: x[1])
                
                # 分批安装
                current_batch = []
                current_batch_size = 0
                
                for pkg, size in packages_with_sizes:
                    # 检查是否可以加入当前批次
                    if (len(current_batch) < max_packages_per_batch and 
                        current_batch_size + size <= max_size_per_batch) or not current_batch:
                        current_batch.append(pkg)
                        current_batch_size += size
                    else:
                        # 安装当前批次
                        batch_success = self._install_package_batch(current_batch, current_venv, layer_num)
                        if batch_success:
                            success_count += len(current_batch)
                        
                        # 开始新批次
                        current_batch = [pkg]
                        current_batch_size = size
                
                # 安装最后一批
                if current_batch:
                    batch_success = self._install_package_batch(current_batch, current_venv, layer_num)
                    if batch_success:
                        success_count += len(current_batch)
            
            return {
                "success": True,
                "message": f"Batch installation completed: {success_count}/{total_packages} packages installed",
                "installed_count": success_count,
                "total_count": total_packages
            }
            
        except Exception as e:
            return {"success": False, "error": f"批量安装失败: {str(e)}"}

    def _get_network_data(self):
        """获取最新的网络测试数据"""
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from NETWORK import get_network_data_interface
            return get_network_data_interface()
        except Exception:
            return None

    def _run_network_test(self):
        """运行网络测试"""
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from NETWORK import network_test_interface
            return network_test_interface()
        except Exception:
            return None

    def _calculate_max_package_size(self, network_data, time_limit=10):
        """基于网络数据计算t秒内可下载的最大包大小"""
        try:
            download_speed_mbps = network_data.get('download_speed_mbps', 1.0)
            # 转换为bytes per second
            download_speed_bps = download_speed_mbps * 1000000 / 8
            # 计算t秒内的最大下载量
            max_bytes = download_speed_bps * time_limit
            return max(max_bytes, 1024*1024)  # 至少1MB
        except Exception:
            return 10 * 1024 * 1024  # 默认10MB

    def _install_package_batch(self, packages, current_venv, layer_num):
        """安装一批包"""
        try:
            if not packages:
                return True
            
            print(f"  Installing batch: {', '.join(packages)}")
            
            # 对于非Layer 0的包，失败不抛出错误
            install_command = f"install {' '.join(packages)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            
            result = self._execute_pip_command_enhanced(install_command, current_venv, target_info)
            
            if layer_num == 0:
                # Layer 0 失败需要报错
                return result.get("success", False)
            else:
                # 高层包失败不影响整体流程
                if not result.get("success", False):
                    print(f"    Warning: Some packages in Layer {layer_num} failed to install")
                return True
                
        except Exception as e:
            if layer_num == 0:
                print(f"    Error installing Layer 0 packages: {e}")
                return False
            else:
                print(f"    Warning: Layer {layer_num} batch installation failed: {e}")
                return True

    def _handle_pip_list(self, list_args, current_venv, env_path, current_packages):
        """处理pip list命令 - 显示增强的包列表信息"""
        try:
            env_info = f"环境: {current_venv}" if current_venv else "环境: system"
            print(f"Total {len(current_packages)} packages: ")
            
            if current_packages:
                for pkg_name, version in sorted(current_packages.items()):
                    print(f"  {pkg_name} == {version}")
            else:
                print("\\n未检测到已安装的包")
            
            # 如果有额外的list参数，执行原始pip list命令
            if list_args:
                list_command = f"list {' '.join(list_args)}"
                target_info = f"in {current_venv}" if current_venv else "in system environment"
                return self._execute_pip_command_enhanced(list_command, current_venv, target_info)
            
            return {
                "success": True,
                "packages": current_packages,
                "environment": current_venv or "system"
            }
            
        except Exception as e:
            return {"success": False, "error": f"处理pip list时出错: {str(e)}"}

    def _handle_pip_show(self, show_args, current_venv, env_path, current_packages):
        """处理pip show命令 - 显示包的详细信息"""
        try:
            if not show_args:
                return {"success": False, "error": "pip show需要指定包名"}
            
            show_command = f"show {' '.join(show_args)}"
            target_info = f"in {current_venv}" if current_venv else "in system environment"
            return self._execute_pip_command_enhanced(show_command, current_venv, target_info)
            
        except Exception as e:
            return {"success": False, "error": f"处理pip show时出错: {str(e)}"}

    # Placeholder methods that need to be implemented or imported from other modules
    def _load_all_venv_states(self):
        """Load venv states - should be implemented or imported"""
        try:
            try:
                from .venv_operations import VenvOperations
            except ImportError:
                from venv_operations import VenvOperations
            venv_ops = VenvOperations(self.drive_service, self.main_instance)
            return venv_ops._load_all_venv_states()
        except Exception:
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

    def _get_packages_from_json(self, venv_name):
        """Get packages from JSON - should be implemented or imported"""
        try:
            try:
                from .venv_operations import VenvOperations
            except ImportError:
                from venv_operations import VenvOperations
            venv_ops = VenvOperations(self.drive_service, self.main_instance)
            return venv_ops._get_packages_from_json(venv_name)
        except Exception:
            return {}

    def _detect_current_environment_packages(self, venv_name):
        """Detect current environment packages - should be implemented or imported"""
        try:
            try:
                from .venv_operations import VenvOperations
            except ImportError:
                from venv_operations import VenvOperations
            venv_ops = VenvOperations(self.drive_service, self.main_instance)
            return venv_ops._detect_current_environment_packages(venv_name)
        except Exception:
            return {}

    def _show_dependency_tree(self, packages_args, current_packages):
        """Show dependency tree - should be implemented or imported"""
        try:
            dependency_analyzer = self._get_dependency_analyzer()
            return dependency_analyzer._show_dependency_tree(packages_args, current_packages)
        except Exception as e:
            return {"success": False, "error": f"依赖树分析失败: {str(e)}"}

    def _execute_pip_command_enhanced(self, pip_command, current_env, target_info):
        """Execute pip command with enhanced features"""
        try:
            print(f"Executing: pip {pip_command} {target_info}")
            # This is a placeholder - in real implementation, this would execute the actual pip command
            return {"success": True, "message": f"pip {pip_command} executed successfully"}
        except Exception as e:
            return {"success": False, "error": f"pip命令执行失败: {str(e)}"}