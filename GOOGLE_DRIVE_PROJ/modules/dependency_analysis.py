
class DependencyAnalysis:
    """
    Package dependency analysis and visualization
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance
        self._pypi_client = None
    
    def cmd_deps(self, *args, **kwargs):
        """独立的依赖分析命令"""
        try:
            if not args:
                return {"success": False, "error": "Usage: GDS deps <package1> [package2] [...] [--depth=N] [--analysis-type=smart|depth]"}
            
            # 解析参数
            packages = []
            max_depth = 2
            
            i = 0
            while i < len(args):
                arg = args[i]
                if arg.startswith('--depth='):
                    max_depth = int(arg.split('=')[1])
                elif arg == '--depth' and i + 1 < len(args):
                    max_depth = int(args[i + 1])
                    i += 1
                elif arg.startswith('--analysis-type='):
                    analysis_type = arg.split('=')[1]
                elif arg == '--analysis-type' and i + 1 < len(args):
                    analysis_type = args[i + 1]
                    i += 1
                elif arg == '-r' or arg == '--requirement':
                    # 处理requirements.txt文件
                    if i + 1 < len(args):
                        requirements_file = args[i + 1]
                        packages_from_file = self._parse_requirements_file(requirements_file)
                        packages.extend(packages_from_file)
                        i += 1
                elif arg.startswith('-r'):
                    # 处理 -rrequirements.txt 格式
                    requirements_file = arg[2:]
                    packages_from_file = self._parse_requirements_file(requirements_file)
                    packages.extend(packages_from_file)
                elif arg.endswith('.txt') and ('requirements' in arg.lower() or 'req' in arg.lower()):
                    # 直接指定requirements文件
                    packages_from_file = self._parse_requirements_file(arg)
                    packages.extend(packages_from_file)
                elif not arg.startswith('-'):
                    packages.append(arg)
                i += 1
            
            if not packages:
                return {"success": False, "error": "No packages specified for dependency analysis"}
            
            print(f"Analyzing dependencies for: {', '.join(packages)}")
            print(f"Analysis depth: {max_depth}")
            
            # 获取当前环境的已安装包信息
            installed_packages = self._detect_current_environment_packages()
            
            # 根据分析类型选择不同的分析方法
            if analysis_type == "smart":
                analysis_result = self._smart_dependency_analysis(
                    packages, 
                    max_calls=10, 
                    interface_mode=False, 
                    installed_packages=installed_packages
                )
            elif analysis_type == "depth":
                analysis_result = self._depth_based_dependency_analysis(
                    packages, 
                    max_depth=max_depth, 
                    interface_mode=False, 
                    installed_packages=installed_packages
                )
            else:
                return {"success": False, "error": f"Unknown analysis type: {analysis_type}. Use 'smart' or 'depth'"}
            
            # 显示分析结果
            total_calls = analysis_result.get('total_calls', 0)
            analyzed_packages = analysis_result.get('analyzed_packages', 0)
            total_time = analysis_result.get('total_time', 0)
            
            if total_time:
                print(f"Analysis completed: {total_calls} API calls, {analyzed_packages} packages analyzed in {total_time:.2f}s\n")
            else:
                print(f"Analysis completed: {total_calls} API calls, {analyzed_packages} packages analyzed\n")
            
            # 显示依赖树
            self._display_smart_dependency_tree(analysis_result, installed_packages)
            
            return {
                "success": True,
                "message": f"Dependency analysis completed for {len(packages)} package(s)",
                "analysis_result": analysis_result
            }
            
        except Exception as e:
            return {"success": False, "error": f"Dependency analysis failed: {str(e)}"}
    
    def _parse_requirements_file(self, requirements_file):
        """解析requirements.txt文件"""
        packages = []
        try:
            # 这里可以添加远程文件读取逻辑
            # 目前简化处理，返回空列表
            print(f"Note: Requirements file parsing not yet implemented for remote files: {requirements_file}")
            return packages
        except Exception as e:
            print(f"Error parsing requirements file: {e}")
            return packages
    
    def _detect_current_environment_packages(self):
        """检测当前环境的已安装包"""
        try:
            # 获取当前shell信息
            current_shell = self.main_instance.get_current_shell()
            shell_id = current_shell.get("id", "default_shell") if current_shell else "default_shell"
            
            # 检查是否有激活的虚拟环境
            try:
                from .venv_operations import VenvOperations
                venv_ops = VenvOperations(self.drive_service, self.main_instance)
                all_states = venv_ops._load_all_venv_states()
                
                current_venv = None
                if shell_id in all_states and all_states[shell_id].get("current_venv"):
                    current_venv = all_states[shell_id]["current_venv"]
                
                if current_venv:
                    # 从JSON获取虚拟环境的包信息
                    if 'environments' in all_states and current_venv in all_states['environments']:
                        env_data = all_states['environments'][current_venv]
                        return env_data.get('packages', {})
                else:
                    # 系统环境的基础包
                    return {
                        'pip': '23.0.0',
                        'setuptools': '65.0.0'
                    }
            except Exception:
                # 如果获取失败，返回基础包
                return {
                    'pip': '23.0.0',
                    'setuptools': '65.0.0'
                }
            
            return {}
        except Exception as e:
            return {}
        
    def _get_pypi_client(self):
        """Get or create PyPI client instance"""
        if self._pypi_client is None:
            try:
                import sys
                import os
                bin_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                sys.path.insert(0, bin_path)
                from PYPI import PyPIClient
                self._pypi_client = PyPIClient()
            except ImportError:
                print("Warning: PYPI tool not available, falling back to direct API calls")
                self._pypi_client = None
        return self._pypi_client

    def _ensure_pipdeptree_available(self):
        """检查pipdeptree命令是否可用"""
        try:
            # Checking if pipdeptree command is available
            import subprocess
            # 直接测试命令是否可用，而不是import
            result = subprocess.run(['pipdeptree', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # pipdeptree command is available
                return True
            else:
                # pipdeptree command failed
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            # pipdeptree command not found
            print("💡 Please install pipdeptree with: pip install pipdeptree")
            return False

    def _get_package_dependencies_with_pipdeptree(self, package_name, installed_packages=None):
        """使用pipdeptree获取单个包的依赖信息"""
        try:
            # Getting dependencies for package
            
            # 首先检查包是否在已安装包列表中
            if installed_packages:
                # 标准化包名进行比较
                pkg_variants = [package_name, package_name.replace('-', '_'), package_name.replace('_', '-')]
                found_in_installed = False
                actual_pkg_name = package_name
                
                for variant in pkg_variants:
                    if variant.lower() in [pkg.lower() for pkg in installed_packages.keys()]:
                        found_in_installed = True
                        # 找到实际的包名（保持原始大小写）
                        for installed_pkg in installed_packages.keys():
                            if installed_pkg.lower() == variant.lower():
                                actual_pkg_name = installed_pkg
                                break
                        break
                
                if not found_in_installed:
                    # Package not found in installed packages
                    return None
                
                # Package found in installed packages
            
            # 方法1：尝试本地pipdeptree (可能不会找到远程包，但值得一试)
            try:
                import subprocess
                import json
                
                cmd = ['pipdeptree', '-p', package_name, '--json', '--warn', 'silence']
                # Running local command
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                # Local command completed
                
                if result.returncode == 0 and result.stdout.strip():
                    dep_data = json.loads(result.stdout)
                    # Local pipdeptree found packages
                    
                    for pkg_info in dep_data:
                        pkg_name_in_data = pkg_info['package']['package_name']
                        if pkg_name_in_data.lower() == package_name.lower():
                            # Found matching package locally
                            dependencies = []
                            for dep in pkg_info.get('dependencies', []):
                                dependencies.append(dep['package_name'])
                            # Local dependencies found
                            return dependencies
                
                # Package not found in local pipdeptree, trying fallback
                
            except Exception as e:
                # Local pipdeptree failed
                
                # 方法2：使用远程pip show命令获取依赖信息
                return self._get_dependencies_via_remote_pip_show(package_name)
                
        except Exception as e:
            # Error getting dependencies
            import traceback
            traceback.print_exc()
            return None

    def _get_dependencies_via_remote_pip_show(self, package_name):
        """通过远程pip show命令获取包依赖信息"""
        try:
            # Using remote pip show for package
            
            # 构建远程pip show命令
            pip_show_cmd = f"pip show {package_name}"
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", pip_show_cmd])
            
            if not result.get("success"):
                # Remote pip show failed
                return []
            
            output = result.get("stdout", "")
            # pip show output received
            
            # 解析pip show输出中的Requires字段
            dependencies = []
            for line in output.split('\n'):
                if line.startswith('Requires:'):
                    requires_text = line.replace('Requires:', '').strip()
                    if requires_text and requires_text != 'None':
                        # 解析依赖，处理版本约束
                        for dep in requires_text.split(','):
                            dep = dep.strip()
                            if dep:
                                # 移除版本约束，只保留包名
                                dep_name = dep.split('>=')[0].split('<=')[0].split('==')[0].split('>')[0].split('<')[0].split('!=')[0].split('~=')[0].strip()
                                if dep_name:
                                    dependencies.append(dep_name)
                    break
            
            # Remote pip show dependencies found
            return dependencies
            
        except Exception as e:
            # Remote pip show error
            return []

    def _get_pypi_dependencies_with_all_sizes(self, package_name):
        """
        从PyPI JSON API获取包的直接依赖信息，同时获取每个依赖的大小
        这算作一次完整的API调用
        
        Args:
            package_name: 包名
            
        Returns:
            tuple: (依赖列表, 包大小, 依赖大小字典)
                   如果失败返回(None, 0, {})
        """
        try:
            pypi_client = self._get_pypi_client()
            if pypi_client:
                # Use PYPI tool
                dependencies, package_size = pypi_client.get_package_dependencies_with_size(package_name)
                return dependencies, package_size, {}  # 返回空的dependency_sizes
            else:
                # Fallback to direct API calls
                import requests
                
                # 首先获取主包信息
                api_url = f"https://pypi.org/pypi/{package_name}/json"
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Get package size from latest release
                package_size = 0
                releases = data.get("releases", {})
                info = data.get("info", {})
                
                # Try to get size from the latest version
                latest_version = info.get("version", "")
                if latest_version and latest_version in releases:
                    files = releases[latest_version]
                    if files:
                        package_size = max((f.get("size", 0) for f in files), default=0)
                
                # Get dependencies
                requires_dist = data.get("info", {}).get("requires_dist")
                
                if requires_dist is None:
                    return [], package_size, {}
                
                # 解析依赖规格，提取包名
                dependencies = []
                for dep_spec in requires_dist:
                    dep_spec = dep_spec.split(';')[0].strip()
                    import re
                    match = re.match(r'^([a-zA-Z0-9_-]+)', dep_spec)
                    if match:
                        dep_name = match.group(1)
                        dependencies.append(dep_name)
                
                # 不获取依赖的大小，只返回依赖列表和主包大小
                # 依赖的大小将在后续分析时获取
                return dependencies, package_size, {}
            
        except Exception as e:
            return None, 0, {}

    def _get_pypi_dependencies_with_size(self, package_name):
        """
        从PyPI JSON API获取包的直接依赖信息和包大小
        
        Args:
            package_name: 包名
            
        Returns:
            tuple: (依赖包名列表, 包大小(bytes))，如果失败返回(None, 0)
        """
        try:
            pypi_client = self._get_pypi_client()
            if pypi_client:
                # Use PYPI tool
                return pypi_client.get_package_dependencies_with_size(package_name)
            else:
                # Fallback to direct API calls
                import requests
                
                # Getting PyPI dependencies and size
                api_url = f"https://pypi.org/pypi/{package_name}/json"
                
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Get package size from latest release
                package_size = 0
                releases = data.get("releases", {})
                info = data.get("info", {})
                
                # Try to get size from the latest version
                latest_version = info.get("version", "")
                if latest_version and latest_version in releases:
                    files = releases[latest_version]
                    if files:
                        # Get the largest file size (usually the wheel or tar.gz)
                        package_size = max((f.get("size", 0) for f in files), default=0)
                
                # Get dependencies
                requires_dist = data.get("info", {}).get("requires_dist")
                
                if requires_dist is None:
                    # No requires_dist found
                    return [], package_size
                
                # 解析依赖规格，提取包名
                dependencies = []
                for dep_spec in requires_dist:
                    # 处理依赖规格，如 "numpy>=1.0.0" -> "numpy"
                    # 也处理条件依赖，如 "pytest; extra == 'test'" -> "pytest"
                    dep_spec = dep_spec.split(';')[0].strip()  # 移除条件部分
                    
                    # 提取包名（移除版本约束）
                    import re
                    match = re.match(r'^([a-zA-Z0-9_-]+)', dep_spec)
                    if match:
                        dep_name = match.group(1)
                        dependencies.append(dep_name)
                
                # PyPI dependencies and size found
                return dependencies, package_size
            
        except Exception as e:
            # Error getting PyPI data
            return None, 0

    def _smart_dependency_analysis(self, packages, max_calls=10, interface_mode=False, installed_packages=None):
        """
        智能依赖分析策略，限制API调用次数，基于包大小优化队列
        
        Args:
            packages: 要分析的包列表
            max_calls: 最大API调用次数 (n)
            interface_mode: 接口模式，返回每层需要下载的包
            installed_packages: 已安装包的字典 {package_name: version}
            
        Returns:
            dict: 分析结果，包含依赖树和层级信息
        """
        try:
            import heapq
            from collections import defaultdict
            
            # 初始化数据结构
            D = {}  # package name -> dependencies mapping  
            Q = []  # priority queue: (-size, package_name) for max-heap behavior
            package_sizes = {}  # package -> size mapping
            layers = defaultdict(set)  # layer -> set of packages
            
            # 将初始包加入Layer 0
            current_packages = [pkg.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0] for pkg in packages]
            layers[0].update(current_packages)
            
            # 将初始包加入队列，优先级最高
            for pkg in current_packages:
                heapq.heappush(Q, (-float('inf'), pkg))
                
            i = 0  # 当前API调用次数
            
            while Q and i < max_calls:
                l = max_calls - i  # 队列剩余容量
                
                # 取出优先级最高的包
                neg_size, current_pkg = heapq.heappop(Q)
                
                if current_pkg in D:
                    continue  # 已经分析过了
                    
                # 调用新的API获取依赖和所有大小信息
                deps, pkg_size, dep_sizes = self._get_pypi_dependencies_with_all_sizes(current_pkg)
                i += 1
                
                # 更新数据结构
                package_sizes[current_pkg] = pkg_size
                package_sizes.update(dep_sizes)  # 更新所有依赖的大小
                
                if deps is not None:
                    D[current_pkg] = deps
                    
                    # 处理新发现的依赖S
                    S = deps
                    for dep in S:
                        if dep not in D and dep not in [item[1] for item in Q]:
                            # 检查是否应该加入队列Q
                            # 规则：(1)不存在D中 (2)不存在Q中 (3)比Q的第l个元素大
                            l = max_calls - i  # 更新l值
                            if l > 0:
                                dep_size = dep_sizes.get(dep, 0)
                                if len(Q) < l:
                                    # 队列未满，直接加入
                                    heapq.heappush(Q, (-dep_size, dep))
                                elif Q:
                                    # 队列已满，检查是否比最小的大
                                    min_size = -Q[0][0] if Q else 0
                                    if dep_size > min_size:
                                        heapq.heappop(Q)  # 移除最小的
                                        heapq.heappush(Q, (-dep_size, dep))
                                
                                # 维护队列大小为l
                                while len(Q) > l:
                                    heapq.heappop(Q)
                else:
                    # API失败，尝试fallback
                    fallback_deps = self._get_package_dependencies_with_pipdeptree(current_pkg, installed_packages)
                    if fallback_deps:
                        D[current_pkg] = fallback_deps
                    else:
                        D[current_pkg] = []
            
            # 生成依赖树和层级信息
            decomposed = set()
            
            def build_tree_and_layers(pkg, current_layer=0, visited=None):
                if visited is None:
                    visited = set()
                    
                if pkg in visited:
                    return {}  # 避免循环依赖
                    
                visited.add(pkg)
                
                if pkg in D and pkg not in decomposed:
                    decomposed.add(pkg)
                    deps = D[pkg]
                    
                    # 将依赖添加到下一层
                    if deps:
                        next_layer = current_layer + 1
                        layers[next_layer].update(deps)
                        
                    result = {
                        'dependencies': deps,
                        'size': package_sizes.get(pkg, 0),
                        'children': {}
                    }
                    
                    for dep in deps:
                        result['children'][dep] = build_tree_and_layers(dep, current_layer + 1, visited.copy())
                    
                    return result
                else:
                    return {
                        'dependencies': [],
                        'size': package_sizes.get(pkg, 0),
                        'children': {}
                    }
            
            # 为每个初始包构建树
            result = {
                'trees': {},
                'layers': {},
                'package_sizes': package_sizes,
                'total_calls': i,
                'analyzed_packages': len(D),
                'D': D,  # 调试用
                'Q': [(size, pkg) for size, pkg in Q]  # 调试用
            }
            
            for pkg in current_packages:
                result['trees'][pkg] = build_tree_and_layers(pkg)
            
            # 转换layers为list并去重
            for layer_num in layers:
                result['layers'][layer_num] = list(layers[layer_num])
            
            if interface_mode:
                # 接口模式：返回每层需要下载的包
                result['download_layers'] = result['layers'].copy()
                    
            return result
            
        except Exception as e:
            # Smart analysis failed, fallback to simple analysis
            return {
                'trees': {},
                'layers': {0: current_packages},
                'package_sizes': {},
                'total_calls': 0,
                'analyzed_packages': 0,
                'error': str(e)
            }

    def _depth_based_dependency_analysis(self, packages, max_depth=1, interface_mode=False, installed_packages=None):
        """
        基于深度和包数量限制的依赖分析策略
        
        Args:
            packages: 要分析的包列表
            max_depth: 最大分析深度
            interface_mode: 接口模式，返回每层需要下载的包
            installed_packages: 已安装包的字典 {package_name: version}
            
        Returns:
            dict: 分析结果，包含依赖树和层级信息
        """
        try:
            import concurrent.futures
            from collections import defaultdict
            import time
            
            # 初始化数据结构
            # Q: {package_name: {'physical_size': int, 'logical_size': None, 'dependencies': []}}
            Q = {}
            R = []  # 待分析的包列表
            layers = defaultdict(set)  # layer -> set of packages
            
            # 清理包名并初始化
            current_packages = [pkg.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0] for pkg in packages]
            layers[0].update(current_packages)
            
            # 初始化Q和R
            for pkg in current_packages:
                Q[pkg] = {
                    'physical_size': None,
                    'logical_size': None, 
                    'dependencies': []
                }
                R.append(pkg)
            
            total_calls = 0
            current_depth = 0
            analysis_start_time = time.time()
            
            # 主分析循环
            while R and len(Q) < 1000 and current_depth <= max_depth:
                # print(f"Analyzing depth {current_depth}: {len(R)} packages to analyze...")
                
                # 准备这一轮要分析的包（最多40个）
                batch_size = min(40, len(R))
                current_batch = R[:batch_size]
                R = R[batch_size:]  # 移除已处理的包
                
                # 过滤掉已经分析过依赖的包（dependencies不为空的包）
                packages_to_analyze = []
                for pkg in current_batch:
                    if pkg not in Q:
                        packages_to_analyze.append(pkg)
                    elif len(Q[pkg]['dependencies']) == 0:  # dependencies为空，表示尚未分析依赖
                        packages_to_analyze.append(pkg)
                
                if not packages_to_analyze:
                    if not R:  # R空了，进入下一层
                        current_depth += 1
                        if current_depth <= max_depth:
                            # 收集下一层的包
                            R_prime = []
                            for pkg_name, pkg_data in Q.items():
                                if pkg_data['dependencies']:
                                    for dep in pkg_data['dependencies']:
                                        if dep not in Q and dep not in R_prime:
                                            R_prime.append(dep)
                            
                            R = R_prime
                            if R:
                                layers[current_depth].update(R)
                    continue
                
                # 并行分析当前批次
                batch_start_time = time.time()
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(40, len(packages_to_analyze))) as executor:
                    future_to_package = {
                        executor.submit(self._get_pypi_dependencies_with_all_sizes, pkg): pkg 
                        for pkg in packages_to_analyze
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_package):
                        package_name = future_to_package[future]
                        try:
                            deps, pkg_size, dep_sizes = future.result()
                            total_calls += 1
                            
                            # 更新Q
                            if package_name not in Q:
                                Q[package_name] = {
                                    'physical_size': pkg_size,
                                    'logical_size': None,
                                    'dependencies': deps or []
                                }
                            else:
                                Q[package_name]['physical_size'] = pkg_size
                                Q[package_name]['dependencies'] = deps or []
                            
                            # 将新发现的依赖加入Q（如果还有空间），但不设置dependencies
                            # 这样它们在下一层仍然可以被分析
                            if deps:
                                for dep in deps:
                                    if dep not in Q and len(Q) < 1000:
                                        Q[dep] = {
                                            'physical_size': None,  # 依赖的大小未知，需要后续分析
                                            'logical_size': None,
                                            'dependencies': []  # 空列表，表示尚未分析依赖
                                        }
                            
                        except Exception as e:
                            print(f"Error analyzing {package_name}: {e}")
                            if package_name not in Q:
                                Q[package_name] = {
                                    'physical_size': 0,
                                    'logical_size': None,
                                    'dependencies': []
                                }
                
                batch_duration = time.time() - batch_start_time
                print(f"    Processed {len(packages_to_analyze)} packages in {batch_duration:.2f}s")
                
                # 如果这批处理时间少于1秒，等待到1秒
                if batch_duration < 1.0:
                    time.sleep(1.0 - batch_duration)
                
                # 检查是否需要进入下一层
                if not R and current_depth < max_depth:
                    current_depth += 1
                    # 收集下一层的包：从当前层的包中找出它们的依赖
                    R_prime = []
                    current_layer_packages = layers.get(current_depth - 1, [])
                    
                    for pkg_name in current_layer_packages:
                        if pkg_name in Q and Q[pkg_name]['dependencies']:
                            for dep in Q[pkg_name]['dependencies']:
                                # 只添加尚未分析过依赖的包（dependencies为空且不在R_prime中）
                                if dep in Q and len(Q[dep]['dependencies']) == 0 and dep not in R_prime:
                                    R_prime.append(dep)
                                elif dep not in Q:
                                    R_prime.append(dep)
                                    # 确保在Q中有条目
                                    Q[dep] = {
                                        'physical_size': None,
                                        'logical_size': None,
                                        'dependencies': []
                                    }
                    
                    R = R_prime
                    if R:
                        layers[current_depth].update(R)
                        print(f"Moving to depth {current_depth} with {len(R)} new packages: {R[:5]}{'...' if len(R) > 5 else ''}")
            
            analysis_end_time = time.time()
            total_analysis_time = analysis_end_time - analysis_start_time
            
            # 计算逻辑大小
            def calculate_logical_size(pkg_name, visited=None):
                if visited is None:
                    visited = set()
                
                if pkg_name in visited or pkg_name not in Q:
                    return 0
                
                visited.add(pkg_name)
                pkg_data = Q[pkg_name]
                
                if pkg_data['logical_size'] is not None:
                    return pkg_data['logical_size']
                
                # 计算逻辑大小 = 物理大小 + 所有子包的逻辑大小
                logical_size = pkg_data['physical_size'] if pkg_data['physical_size'] is not None else 0
                
                for dep in pkg_data['dependencies']:
                    if dep in Q:
                        logical_size += calculate_logical_size(dep, visited.copy())
                    # 如果依赖不在Q中（由于限制），使用其物理大小
                
                pkg_data['logical_size'] = logical_size
                return logical_size
            
            # 为所有包计算逻辑大小
            for pkg_name in current_packages:
                calculate_logical_size(pkg_name)
            
            # 构建结果
            result = {
                'trees': {},
                'layers': {},
                'package_sizes': {pkg: (data['physical_size'] if data['physical_size'] is not None else 0) for pkg, data in Q.items()},
                'logical_sizes': {pkg: (data['logical_size'] if data['logical_size'] is not None else 0) for pkg, data in Q.items()},
                'total_calls': total_calls,
                'analyzed_packages': len(Q),
                'total_time': total_analysis_time,
                'Q': Q  # 调试用
            }
            
            # 构建依赖树
            def build_tree(pkg_name, visited=None, max_tree_depth=3):
                if visited is None:
                    visited = set()
                
                if pkg_name in visited or pkg_name not in Q:
                    return {}
                
                visited.add(pkg_name)
                pkg_data = Q[pkg_name]
                
                result_tree = {
                    'dependencies': pkg_data['dependencies'],
                    'size': pkg_data['physical_size'] if pkg_data['physical_size'] is not None else 0,
                    'logical_size': pkg_data['logical_size'] if pkg_data['logical_size'] is not None else 0,
                    'children': {}
                }
                
                if len(visited) < max_tree_depth:
                    for dep in pkg_data['dependencies']:
                        result_tree['children'][dep] = build_tree(dep, visited.copy(), max_tree_depth)
                
                return result_tree
            
            for pkg in current_packages:
                result['trees'][pkg] = build_tree(pkg)
            
            # 转换layers为list
            for layer_num in layers:
                result['layers'][layer_num] = list(layers[layer_num])
            
            if interface_mode:
                result['download_layers'] = result['layers'].copy()
                    
            return result
            
        except Exception as e:
            # Analysis failed, fallback to simple analysis
            return {
                'trees': {},
                'layers': {0: current_packages},
                'package_sizes': {},
                'logical_sizes': {},
                'total_calls': 0,
                'analyzed_packages': 0,
                'error': str(e)
            }

    def _get_pypi_dependencies(self, package_name):
        """
        从PyPI JSON API获取包的直接依赖信息
        
        Args:
            package_name: 包名
            
        Returns:
            list: 依赖包名列表，如果失败返回None
        """
        try:
            import requests
            
            # Getting PyPI dependencies
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            requires_dist = data.get("info", {}).get("requires_dist")
            
            if requires_dist is None:
                # No requires_dist found
                return []
            
            # 解析依赖规格，提取包名
            dependencies = []
            for dep_spec in requires_dist:
                # 处理依赖规格，如 "numpy>=1.0.0" -> "numpy"
                # 也处理条件依赖，如 "pytest; extra == 'test'" -> "pytest"
                dep_spec = dep_spec.split(';')[0].strip()  # 移除条件部分
                
                # 提取包名（移除版本约束）
                import re
                match = re.match(r'^([a-zA-Z0-9_-]+)', dep_spec)
                if match:
                    dep_name = match.group(1)
                    dependencies.append(dep_name)
            
            # PyPI dependencies found
            return dependencies
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Package not found on PyPI
                return None
            else:
                # HTTP error for package
                return None
        except Exception as e:
            # Error getting PyPI dependencies
            return None

    def _analyze_dependencies_recursive(self, packages, max_depth=2, installed_packages=None):
        """
        递归分析包依赖关系（使用PyPI API + 并行处理）
        
        Args:
            packages: 要分析的包列表
            max_depth: 最大递归深度
            installed_packages: 已安装包的字典 {package_name: version}
            
        Returns:
            dict: 递归依赖分析结果
        """
        try:
            import concurrent.futures
            import threading
            from collections import defaultdict, deque
            
            # Starting recursive dependency analysis
            
            # 用于存储所有依赖关系
            all_dependencies = {}  # {package: [direct_deps]}
            dependencies_by_level = defaultdict(lambda: defaultdict(list))  # {package: {level: [deps]}}
            processed_packages = set()
            lock = threading.Lock()
            
            def process_package_batch(package_list, current_level):
                """并行处理一批包"""
                if current_level > max_depth:
                    return []
                
                # Processing dependency level
                
                next_level_packages = []
                
                # 使用线程池并行获取依赖
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    # 提交所有任务
                    future_to_package = {
                        executor.submit(self._get_pypi_dependencies, pkg): pkg 
                        for pkg in package_list
                    }
                    
                    # 收集结果
                    for future in concurrent.futures.as_completed(future_to_package):
                        pkg = future_to_package[future]
                        try:
                            deps = future.result()
                            
                            with lock:
                                if deps is not None:
                                    all_dependencies[pkg] = deps
                                    dependencies_by_level[pkg][current_level] = deps
                                    
                                    # 添加到下一层处理队列
                                    for dep in deps:
                                        if dep not in processed_packages:
                                            next_level_packages.append(dep)
                                            processed_packages.add(dep)
                                else:
                                    # PyPI查询失败，尝试fallback方法
                                    # PyPI failed, trying fallback
                                    fallback_deps = self._get_package_dependencies_with_pipdeptree(pkg, installed_packages)
                                    if fallback_deps:
                                        all_dependencies[pkg] = fallback_deps
                                        dependencies_by_level[pkg][current_level] = fallback_deps
                                        for dep in fallback_deps:
                                            if dep not in processed_packages:
                                                next_level_packages.append(dep)
                                                processed_packages.add(dep)
                                    else:
                                        all_dependencies[pkg] = []
                                        dependencies_by_level[pkg][current_level] = []
                                
                                processed_packages.add(pkg)
                                
                        except Exception as e:
                            # Error processing package
                            with lock:
                                all_dependencies[pkg] = []
                                dependencies_by_level[pkg][current_level] = []
                
                return next_level_packages
            
            # 开始递归处理
            current_level = 0
            current_packages = [pkg.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0] for pkg in packages]
            
            while current_packages and current_level <= max_depth:
                current_packages = process_package_batch(current_packages, current_level)
                current_level += 1
            
            # 统计结果
            all_deps = set()
            dependency_count = defaultdict(int)
            
            for pkg_deps in all_dependencies.values():
                for dep in pkg_deps:
                    all_deps.add(dep)
                    dependency_count[dep] += 1
            
            # 计算共享依赖
            shared_deps = [(dep, count) for dep, count in dependency_count.items() if count > 1]
            shared_deps.sort(key=lambda x: x[1], reverse=True)
            
            result = {
                "dependencies": all_dependencies,
                "dependencies_by_level": dict(dependencies_by_level),
                "total_unique_deps": len(all_deps),
                "shared_dependencies": shared_deps,
                "dependency_count": dict(dependency_count)
            }
            
            # Recursive analysis complete
            
            return result
            
        except Exception as e:
            # Recursive dependency analysis failed
            import traceback
            traceback.print_exc()
            return self._fallback_dependency_analysis(packages)

    def _analyze_package_dependencies(self, packages, max_depth=2, installed_packages=None):
        """
        分析包依赖关系（优先使用PyPI API，pipdeptree作为fallback）
        
        Args:
            packages: 要分析的包列表
            max_depth: 分析深度
            installed_packages: 已安装包的字典 {package_name: version}
            
        Returns:
            dict: 依赖分析结果
        """
        try:
            # Dependency analysis starting (debug output removed)
            
            # 使用新的递归分析方法
            return self._analyze_dependencies_recursive(packages, max_depth, installed_packages)
            
        except Exception as e:
            # Dependency analysis failed
            import traceback
            traceback.print_exc()
            return self._fallback_dependency_analysis(packages)

    def _fallback_dependency_analysis(self, packages):
        """回退的依赖分析（当pipdeptree不可用时）"""
        print("Using fallback dependency analysis")
        dependencies = {}
        dependencies_by_level = {}
        
        for package in packages:
            dependencies[package] = []
            dependencies_by_level[package] = {0: []}
        
        return {
            "dependencies": dependencies,
            "dependencies_by_level": dependencies_by_level,
            "total_unique_deps": 0,
            "shared_dependencies": [],
            "dependency_count": {}
        }

    def _normalize_package_name(self, package_name):
        """
        标准化包名进行比较
        将下划线转换为连字符，并转换为小写
        """
        if not package_name:
            return ""
        # 移除版本信息
        base_name = package_name.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
        # 将下划线转换为连字符，转换为小写
        normalized = base_name.replace('_', '-').lower().strip()
        return normalized

    def _show_dependency_tree(self, packages_args, installed_packages=None):
        """
        显示包的依赖树结构
        
        Args:
            packages_args: pip install的参数列表（包括--show-deps选项）
            installed_packages: 已安装包的字典，如果提供则不重新扫描
            
        Returns:
            dict: 依赖树显示结果
        """
        try:
            # 过滤出实际的包名（排除选项）或处理requirements.txt
            packages = []
            max_depth = 2  # 默认显示2层
            
            i = 0
            while i < len(packages_args):
                arg = packages_args[i]
                if arg == '--show-deps':
                    i += 1
                    continue
                elif arg.startswith('--depth='):
                    max_depth = int(arg.split('=')[1])
                    i += 1
                    continue
                elif arg == '-r' or arg == '--requirement':
                    # 处理requirements.txt文件
                    if i + 1 < len(packages_args):
                        requirements_file = packages_args[i + 1]
                        packages_from_file = self._parse_requirements_file(requirements_file)
                        packages.extend(packages_from_file)
                        i += 2
                    else:
                        i += 1
                elif arg.startswith('-r'):
                    # 处理 -rrequirements.txt 格式
                    requirements_file = arg[2:]  # 去掉-r
                    packages_from_file = self._parse_requirements_file(requirements_file)
                    packages.extend(packages_from_file)
                    i += 1
                elif arg.endswith('.txt') and ('requirements' in arg.lower() or 'req' in arg.lower()):
                    # 直接指定requirements文件
                    packages_from_file = self._parse_requirements_file(arg)
                    packages.extend(packages_from_file)
                    i += 1
                elif arg.startswith('-'):
                    # 跳过其他选项
                    if arg in ['--target', '--index-url', '--extra-index-url', '--find-links']:
                        i += 2
                    else:
                        i += 1
                else:
                    packages.append(arg)
                    i += 1
            
            if not packages:
                return {
                    "success": False,
                    "error": "No packages specified for dependency tree analysis"
                }
            
            # 解析--depth选项，默认为1
            max_depth = 1  # 默认值
            for i, arg in enumerate(packages_args):
                if arg.startswith('--depth='):
                    max_depth = int(arg.split('=')[1])
                    packages_args.pop(i)
                    break
                elif arg == '--depth' and i + 1 < len(packages_args):
                    max_depth = int(packages_args[i + 1])
                    packages_args.pop(i + 1)
                    packages_args.pop(i)
                    break
            
            # 重新解析包列表（移除了--depth选项后）
            packages = []
            i = 0
            while i < len(packages_args):
                arg = packages_args[i]
                if arg == '--show-deps':
                    i += 1
                    continue
                elif arg.startswith('--depth='):
                    i += 1
                    continue
                elif arg == '-r' or arg == '--requirement':
                    if i + 1 < len(packages_args):
                        requirements_file = packages_args[i + 1]
                        packages_from_file = self._parse_requirements_file(requirements_file)
                        packages.extend(packages_from_file)
                        i += 2
                    else:
                        i += 1
                elif arg.startswith('-r'):
                    requirements_file = arg[2:]
                    packages_from_file = self._parse_requirements_file(requirements_file)
                    packages.extend(packages_from_file)
                    i += 1
                elif arg.endswith('.txt') and ('requirements' in arg.lower() or 'req' in arg.lower()):
                    packages_from_file = self._parse_requirements_file(arg)
                    packages.extend(packages_from_file)
                    i += 1
                elif arg.startswith('-'):
                    if arg in ['--target', '--index-url', '--extra-index-url', '--find-links']:
                        i += 2
                    else:
                        i += 1
                else:
                    packages.append(arg)
                    i += 1
            
            print(f"Analyzing dependency tree (max depth {max_depth})...")
            
            # 获取已安装包的信息（优先使用提供的包信息，避免重复扫描）
            if installed_packages is None:
                installed_packages = self._detect_current_environment_packages(None)
            
            # 使用基于深度的依赖分析
            smart_analysis = self._depth_based_dependency_analysis(
                packages, 
                max_depth=max_depth, 
                interface_mode=False, 
                installed_packages=installed_packages
            )
            
            # 显示分析统计
            total_calls = smart_analysis.get('total_calls', 0)
            analyzed_packages = smart_analysis.get('analyzed_packages', 0)
            total_time = smart_analysis.get('total_time', 0)
            print(f"Analysis completed: {total_calls} API calls, {analyzed_packages} packages analyzed in {total_time:.2f}s\n")
            
            # 显示智能依赖树
            self._display_smart_dependency_tree(smart_analysis, installed_packages)
            
            return {
                "success": True,
                "message": f"Smart dependency tree analysis completed for {len(packages)} package(s)",
                "smart_analysis": smart_analysis
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Dependency tree analysis failed: {str(e)}"
            }
    
    def _display_smart_dependency_tree(self, smart_analysis, installed_packages=None):
        """
        显示智能依赖分析结果，包含包大小和层级信息
        
        Args:
            smart_analysis: 智能分析结果
            installed_packages: 已安装包的字典 {package_name: version}
        """
        def format_size(size_bytes):
            """格式化包大小显示"""
            if size_bytes == 0:
                return ""
            elif size_bytes < 1024:
                return f" ({size_bytes}B)"
            elif size_bytes < 1024 * 1024:
                return f" ({size_bytes/1024:.1f}KB)"
            else:
                return f" ({size_bytes/(1024*1024):.1f}MB)"
        
        def format_logical_size(physical_size, logical_size):
            """格式化逻辑大小显示（物理大小→逻辑大小）"""
            if logical_size and logical_size != physical_size and logical_size > physical_size:
                if logical_size < 1024*1024:
                    return f" ({physical_size/1024:.1f}KB→{logical_size/1024:.1f}KB)"
                else:
                    return f" ({physical_size/(1024*1024):.1f}MB→{logical_size/(1024*1024):.1f}MB)"
            else:
                return format_size(physical_size)
        
        def is_package_installed(pkg_name):
            """检查包是否已安装"""
            if not installed_packages:
                return False
            normalized_name = self._normalize_package_name(pkg_name)
            normalized_installed = {self._normalize_package_name(pkg): pkg for pkg in installed_packages.keys()}
            return normalized_name in normalized_installed
        
        trees = smart_analysis.get('trees', {})
        package_sizes = smart_analysis.get('package_sizes', {})
        logical_sizes = smart_analysis.get('logical_sizes', {})
        layers = smart_analysis.get('layers', {})
        
        # 显示每个主包的依赖树
        for package, tree_data in trees.items():
            installed_mark = " [√]" if is_package_installed(package) else ""
            physical_size = package_sizes.get(package, 0)
            logical_size = logical_sizes.get(package, 0)
            size_info = format_logical_size(physical_size, logical_size)
            print(f"{package}{installed_mark}{size_info}")
            
            # 显示直接依赖
            deps = tree_data.get('dependencies', [])
            if deps:
                for i, dep in enumerate(deps):
                    is_last = (i == len(deps) - 1)
                    connector = "└─" if is_last else "├─"
                    dep_installed = " [√]" if is_package_installed(dep) else ""
                    dep_physical = package_sizes.get(dep, 0)
                    dep_logical = logical_sizes.get(dep, 0)
                    dep_size = format_logical_size(dep_physical, dep_logical)
                    print(f"{connector} {dep}{dep_installed}{dep_size}")
                    
                    # 显示二级依赖 (Level 2) - 4个空格缩进
                    child_data = tree_data.get('children', {}).get(dep, {})
                    child_deps = child_data.get('dependencies', [])
                    if child_deps:
                        for j, child_dep in enumerate(child_deps):
                            is_last_child = (j == len(child_deps) - 1)
                            if is_last:
                                # 父级是最后一个，使用空格
                                child_connector = "    └─" if is_last_child else "    ├─"
                            else:
                                # 父级不是最后一个，使用竖线连接
                                child_connector = "│   └─" if is_last_child else "│   ├─"
                            child_installed = " [√]" if is_package_installed(child_dep) else ""
                            child_physical = package_sizes.get(child_dep, 0)
                            child_logical = logical_sizes.get(child_dep, 0)
                            child_size = format_logical_size(child_physical, child_logical)
                            print(f"{child_connector} {child_dep}{child_installed}{child_size}")
            
        # 显示层级汇总（从Level 1开始）
        print()
        for layer_num in sorted(layers.keys()):
            if layer_num == 0:
                continue  # 跳过主包层
            pkgs = layers[layer_num]
            if pkgs:
                # 去重并按大小排序
                unique_pkgs = list(set(pkgs))
                pkg_with_sizes = [(pkg, package_sizes.get(pkg, 0)) for pkg in unique_pkgs]
                pkg_with_sizes.sort(key=lambda x: x[1], reverse=True)
                
                print(f"\nLevel {layer_num}: {', '.join([f'{pkg}{format_size(size)}' for pkg, size in pkg_with_sizes])}")
    
    def _get_package_sizes_for_layers(self, download_layers):
        """获取各层包的大小信息"""
        package_sizes = {}
        
        for layer_packages in download_layers.values():
            for package in layer_packages:
                if package not in package_sizes:
                    # 尝试获取包大小
                    try:
                        _, size = self._get_pypi_dependencies_with_size(package)
                        package_sizes[package] = size
                    except Exception:
                        package_sizes[package] = 0
        
        return package_sizes
    
    def _display_package_dependency_tree(self, package, dependency_analysis, max_depth, installed_packages=None):
        """
        显示单个包的2层依赖树
        
        Args:
            package: 包名
            dependency_analysis: 依赖分析结果
            max_depth: 最大深度
            installed_packages: 已安装包的字典 {package_name: version}
        """
        base_name = package.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
        
        # 检查主包是否已安装
        normalized_base_name = self._normalize_package_name(base_name)
        is_installed = False
        if installed_packages:
            # 创建标准化的已安装包字典
            normalized_installed = {self._normalize_package_name(pkg): pkg for pkg in installed_packages.keys()}
            is_installed = normalized_base_name in normalized_installed
        
        main_package_status = " [√]" if is_installed else ""
        print(f"{package}{main_package_status}")
        
        # 获取依赖关系
        dependencies = dependency_analysis.get("dependencies", {})
        dependencies_by_level = dependency_analysis.get("dependencies_by_level", {})
        
        if package in dependencies:
            all_deps = dependencies[package]
            if all_deps and package in dependencies_by_level:
                level_deps = dependencies_by_level[package]
                
                # 获取直接依赖（Level 0）
                direct_deps = level_deps.get(0, [])
                if direct_deps:
                    # 我们需要从递归分析结果中获取每个依赖的子依赖
                    # 使用原始的dependencies字典来获取每个包的依赖
                    for i, direct_dep in enumerate(direct_deps):
                        is_last_direct = (i == len(direct_deps) - 1)
                        direct_connector = "└─" if is_last_direct else "├─"
                        
                        # 检查直接依赖是否已安装
                        direct_dep_base = direct_dep.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
                        normalized_direct_name = self._normalize_package_name(direct_dep_base)
                        direct_is_installed = False
                        if installed_packages:
                            direct_is_installed = normalized_direct_name in normalized_installed
                        direct_status = " [√]" if direct_is_installed else ""
                        
                        print(f"   {direct_connector} {direct_dep}{direct_status}")
                        
                        # 获取这个直接依赖的子依赖
                        sub_deps = dependencies.get(direct_dep_base, [])
                        if sub_deps:
                            prefix = "              " if is_last_direct else "   │          "
                            
                            # 限制显示数量，避免过长
                            display_sub_deps = sub_deps[:4]  # 最多显示4个子依赖
                            
                            for j, sub_dep in enumerate(display_sub_deps):
                                sub_is_last = (j == len(display_sub_deps) - 1) and len(sub_deps) <= 4
                                sub_connector = "└─" if sub_is_last else "├─"
                                
                                # 检查子依赖是否已安装
                                sub_dep_base = sub_dep.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].split('!=')[0]
                                normalized_sub_name = self._normalize_package_name(sub_dep_base)
                                sub_is_installed = False
                                if installed_packages:
                                    sub_is_installed = normalized_sub_name in normalized_installed
                                sub_status = " [√]" if sub_is_installed else ""
                                
                                print(f"{prefix}{sub_connector} {sub_dep}{sub_status}")
                            
                            # 如果有更多子依赖，显示省略号
                            if len(sub_deps) > 4:
                                ellipsis_prefix = "              " if is_last_direct else "   │          "
                                print(f"{ellipsis_prefix}└─ ... ({len(sub_deps) - 4} more)")
            else:
                print("   └─ No dependencies")
        else:
            print("   └─ Package not in known dependencies database")
