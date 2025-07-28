#!/usr/bin/env python3
"""
Google Drive Shell Refactor Helper
用于安全地将google_drive_shell.py重构为多个模块的辅助脚本
"""

import ast
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass

@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    start_line: int
    end_line: int
    content: str
    dependencies: Set[str]  # 依赖的其他方法
    category: str  # 功能分类

class GoogleDriveShellRefactor:
    """Google Drive Shell重构助手"""
    
    def __init__(self, source_file: str = "google_drive_shell.py"):
        self.source_file = Path(source_file)
        self.source_content = ""
        self.functions = {}  # Dict[str, FunctionInfo]
        self.imports = []
        self.class_init_content = ""  # 存储原始__init__方法内容
        self.module_categories = {
            'shell_management': [
                'load_shells', 'save_shells', 'generate_shell_id', 'get_current_shell',
                'create_shell', 'list_shells', 'checkout_shell', 'terminate_shell', 
                'exit_shell', '_create_default_shell', 'get_current_folder_id'
            ],
            'file_operations': [
                'cmd_upload', 'cmd_upload_multi', 'cmd_upload_folder', 'cmd_download',
                'cmd_mv', 'cmd_mv_multi', 'cmd_rm', 'cmd_mkdir', 'cmd_mkdir_remote',
                'cmd_ls', 'cmd_cd', 'cmd_pwd', 'cmd_find', 'cmd_cat', 'cmd_grep', 
                'cmd_echo', 'cmd_python', '_execute_python_file', '_execute_python_code',
                '_ls_single', '_ls_recursive', '_build_nested_structure', '_build_folder_tree',
                '_generate_folder_url', '_generate_web_url', '_find_folder', '_find_file',
                'cmd_read', 'cmd_edit'
            ],
            'cache_manager': [
                'load_cache_config', 'load_deletion_cache', 'save_deletion_cache',
                'is_remote_file_cached', 'get_remote_file_modification_time',
                'is_cached_file_up_to_date', '_get_local_cache_path',
                '_update_uploaded_files_cache', '_cleanup_local_equivalent_files'
            ],
            'remote_commands': [
                'generate_remote_commands', '_generate_multi_file_remote_commands',
                'execute_remote_command_interface', 'execute_generic_remote_command',
                '_generate_remote_command', 'show_remote_command_window',
                '_show_generic_command_window', '_execute_with_result_capture',
                '_generate_unzip_and_delete_command', 'generate_mkdir_commands',
                '_generate_multi_mv_remote_commands', '_cleanup_remote_result_file'
            ],
            'path_resolver': [
                'resolve_path', 'resolve_remote_absolute_path', '_resolve_relative_path',
                '_resolve_parent_directory', '_resolve_target_path_for_upload',
                '_resolve_absolute_mkdir_path', '_gds_path_to_absolute', '_expand_path',
                '_setup_environment_paths', '_setup_default_paths'
            ],
            'sync_manager': [
                'wait_for_file_sync', '_wait_for_file_sync_with_timeout', '_wait_for_zip_sync',
                '_wait_for_drive_equivalent_file_deletion', 'check_network_connection',
                'calculate_timeout_from_file_sizes', 'move_to_local_equivalent',
                '_restart_google_drive_desktop', '_wait_and_read_result_file'
            ],
            'file_utils': [
                '_check_large_files', '_handle_large_files', '_zip_folder', '_unzip_remote_file',
                '_check_local_files', '_verify_files_available', '_check_files_to_override',
                '_check_target_file_conflicts', '_check_target_file_conflicts_before_move',
                '_check_mv_destination_conflict', '_create_text_file', '_create_file_in_shared_drive'
            ],
            'validation': [
                '_create_error_result', '_create_success_result', '_handle_exception',
                '_format_tkinter_result_message', '_check_remote_file_exists',
                '_check_remote_file_exists_absolute', 'verify_upload_success'
            ],
            'verification': [
                '_verify_mkdir_result', '_verify_mkdir_with_ls', '_verify_mkdir_with_ls_recursive',
                '_verify_mv_with_ls', '_verify_rm_with_find', '_update_cache_after_mv'
            ]
        }
    
    def load_source_file(self):
        """加载源文件内容"""
        print(f"Loading source file: {self.source_file}")
        with open(self.source_file, 'r', encoding='utf-8') as f:
            self.source_content = f.read()
        print(f"Source file loaded: {len(self.source_content)} characters")
    
    def parse_functions(self):
        """解析所有函数定义，使用更精确的方法"""
        print("Parsing function definitions...")
        lines = self.source_content.split('\n')
        
        current_function = None
        function_start = 0
        in_function = False
        in_class = False
        brace_count = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            original_line = line
            
            # 检测类开始
            if stripped.startswith('class GoogleDriveShell'):
                in_class = True
                continue
                
            if not in_class:
                continue
            
            # 检测函数定义（必须在类内部，4空格缩进）
            if re.match(r'^    def\s+\w+\s*\(', original_line):
                # 如果有之前的函数，先保存
                if current_function and in_function:
                    self._save_function_precise(current_function, function_start, i-1, lines)
                
                # 开始新函数
                func_match = re.match(r'^    def\s+(\w+)\s*\(', original_line)
                if func_match:
                    current_function = func_match.group(1)
                    function_start = i
                    in_function = True
                    brace_count = 0
            
            # 检测函数结束
            elif in_function and current_function:
                # 如果遇到同级别或更高级别的定义，函数结束
                if (re.match(r'^    def\s+\w+\s*\(', original_line) or  # 下一个函数
                    re.match(r'^class\s+\w+', original_line) or  # 类定义
                    (original_line and not original_line.startswith(' '))):  # 文件级别的代码
                    # 保存当前函数
                    self._save_function_precise(current_function, function_start, i-1, lines)
                    current_function = None
                    in_function = False
        
        # 保存最后一个函数
        if current_function and in_function:
            self._save_function_precise(current_function, function_start, len(lines), lines)
        
        print(f"Found {len(self.functions)} functions")
        
    def _save_function_precise(self, func_name: str, start_line: int, end_line: int, lines: List[str]):
        """精确保存函数信息"""
        # 获取函数内容，包括完整的缩进
        content_lines = lines[start_line-1:end_line]
        
        # 清理内容 - 移除多余的空行
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        
        content = '\n'.join(content_lines)
        
        # 分析依赖
        dependencies = self._analyze_dependencies(content)
        
        # 确定分类
        category = self._categorize_function(func_name)
        
        self.functions[func_name] = FunctionInfo(
            name=func_name,
            start_line=start_line,
            end_line=end_line,
            content=content,
            dependencies=dependencies,
            category=category
        )
        
        # 特殊处理__init__方法
        if func_name == '__init__':
            self.class_init_content = content
    
    def _analyze_dependencies(self, content: str) -> Set[str]:
        """分析函数依赖的其他方法"""
        dependencies = set()
        
        # 查找self.方法调用
        self_calls = re.findall(r'self\.(\w+)\s*\(', content)
        dependencies.update(self_calls)
        
        return dependencies
    
    def _categorize_function(self, func_name: str) -> str:
        """确定函数所属分类"""
        for category, functions in self.module_categories.items():
            if func_name in functions:
                return category
        
        # 默认分类逻辑
        if func_name.startswith('cmd_'):
            return 'file_operations'
        elif 'cache' in func_name.lower():
            return 'cache_manager'
        elif 'remote' in func_name.lower():
            return 'remote_commands'
        elif 'path' in func_name.lower() or 'resolve' in func_name.lower():
            return 'path_resolver'
        elif 'sync' in func_name.lower() or 'wait' in func_name.lower():
            return 'sync_manager'
        elif func_name.startswith('_check') or func_name.startswith('_verify'):
            return 'validation'
        else:
            return 'utils'
    
    def extract_imports(self):
        """提取导入语句"""
        print("Extracting imports...")
        lines = self.source_content.split('\n')
        
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith('import ') or 
                stripped.startswith('from ')) and 'google_drive_api' in stripped:
                self.imports.append(line)
            elif stripped.startswith('import ') or stripped.startswith('from '):
                self.imports.append(line)
            elif stripped.startswith('class GoogleDriveShell'):
                break
        
        # 去重并过滤
        seen = set()
        filtered_imports = []
        for imp in self.imports:
            if imp.strip() and imp not in seen:
                seen.add(imp)
                filtered_imports.append(imp)
        
        self.imports = filtered_imports
        print(f"Found {len(self.imports)} import lines")
    
    def generate_module_files(self):
        """生成模块文件"""
        print("Generating module files...")
        
        # 创建modules目录
        modules_dir = self.source_file.parent / "modules"
        modules_dir.mkdir(exist_ok=True)
        
        # 为每个分类生成模块文件
        for category in self.module_categories.keys():
            self._generate_module_file(category, modules_dir)
        
        # 生成__init__.py
        self._generate_init_file(modules_dir)
        
        print("Module files generated successfully")
    
    def _generate_module_file(self, category: str, modules_dir: Path):
        """生成单个模块文件"""
        module_file = modules_dir / f"{category}.py"
        
        # 收集该分类的所有函数
        category_functions = []
        for func_name, func_info in self.functions.items():
            if func_info.category == category:
                category_functions.append(func_info)
        
        if not category_functions:
            print(f"No functions found for category: {category}")
            return
        
        print(f"Generating {module_file.name} with {len(category_functions)} functions")
        
        # 生成模块内容
        content = self._generate_module_content(category, category_functions)
        
        with open(module_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_module_content(self, category: str, functions: List[FunctionInfo]) -> str:
        """生成模块内容"""
        lines = []
        
        # 添加文件头
        lines.append(f'#!/usr/bin/env python3')
        lines.append(f'"""')
        lines.append(f'Google Drive Shell - {category.replace("_", " ").title()} Module')
        lines.append(f'从google_drive_shell.py重构而来的{category}模块')
        lines.append(f'"""')
        lines.append('')
        
        # 添加必要的导入（去重）
        for imp in self.imports:
            lines.append(imp)
        lines.append('')
        
        # 添加类定义
        class_name = ''.join(word.capitalize() for word in category.split('_'))
        lines.append(f'class {class_name}:')
        lines.append(f'    """Google Drive Shell {category.replace("_", " ").title()}"""')
        lines.append('')
        lines.append('    def __init__(self, drive_service, main_instance=None):')
        lines.append('        """初始化管理器"""')
        lines.append('        self.drive_service = drive_service')
        lines.append('        self.main_instance = main_instance  # 引用主实例以访问其他属性')
        lines.append('')
        
        # 添加所有函数
        for func in sorted(functions, key=lambda x: x.start_line):
            # 保持原始函数内容，只调整缩进
            modified_content = self._adjust_function_indentation(func.content)
            lines.append(modified_content)
            lines.append('')
        
        return '\n'.join(lines)
    
    def _adjust_function_indentation(self, content: str) -> str:
        """调整函数缩进以适应类结构"""
        lines = content.split('\n')
        if not lines:
            return content
        
        # 保持原有的相对缩进结构
        return content  # 原始内容已经有正确的缩进
    
    def _generate_init_file(self, modules_dir: Path):
        """生成__init__.py文件"""
        init_file = modules_dir / "__init__.py"
        
        lines = [
            '#!/usr/bin/env python3',
            '"""',
            'Google Drive Shell Modules',
            '重构后的模块导入',
            '"""',
            ''
        ]
        
        # 导入所有模块
        for category in self.module_categories.keys():
            class_name = ''.join(word.capitalize() for word in category.split('_'))
            lines.append(f'from .{category} import {class_name}')
        
        lines.append('')
        lines.append('__all__ = [')
        for category in self.module_categories.keys():
            class_name = ''.join(word.capitalize() for word in category.split('_'))
            lines.append(f'    "{class_name}",')
        lines.append(']')
        
        with open(init_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def generate_refactored_main_class(self):
        """生成重构后的主类"""
        print("Generating refactored main class...")
        
        main_file = self.source_file.parent / "google_drive_shell_refactored.py"
        
        lines = []
        
        # 文件头
        lines.extend([
            '#!/usr/bin/env python3',
            '"""',
            'Google Drive Shell Management (Refactored)',
            'Google Drive远程Shell管理系统 - 重构版本',
            '"""',
            ''
        ])
        
        # 导入
        for imp in self.imports:
            lines.append(imp)
        
        lines.extend([
            '',
            '# 导入重构后的模块',
            'from .modules import (',
        ])
        
        for category in self.module_categories.keys():
            class_name = ''.join(word.capitalize() for word in category.split('_'))
            lines.append(f'    {class_name},')
        
        lines.extend([
            ')',
            ''
        ])
        
        # 主类定义
        lines.extend([
            'class GoogleDriveShell:',
            '    """Google Drive Shell管理类 (重构版本)"""',
            '    ',
        ])
        
        # 添加原始__init__方法
        if self.class_init_content:
            lines.append(self.class_init_content)
            lines.append('')
            lines.append('        # 初始化管理器')
            lines.append('        self._initialize_managers()')
            lines.append('')
        else:
            lines.extend([
                '    def __init__(self):',
                '        """初始化Google Drive Shell"""',
                '        # TODO: 从原始__init__方法复制初始化代码',
                '        self._initialize_managers()',
                '    '
            ])
        
        lines.extend([
            '    def _initialize_managers(self):',
            '        """初始化各个管理器"""',
        ])
        
        # 初始化管理器
        for category in self.module_categories.keys():
            class_name = ''.join(word.capitalize() for word in category.split('_'))
            var_name = category
            lines.append(f'        self.{var_name} = {class_name}(self.drive_service, self)')
        
        lines.append('    ')
        
        # 生成委托方法
        public_methods = []
        for func_name, func_info in self.functions.items():
            if (not func_name.startswith('_') and 
                func_info.category != 'utils' and 
                func_name != '__init__'):
                public_methods.append((func_name, func_info))
        
        for func_name, func_info in sorted(public_methods, key=lambda x: x[0]):
            manager_name = func_info.category
            lines.extend([
                f'    def {func_name}(self, *args, **kwargs):',
                f'        """委托到{manager_name}管理器"""',
                f'        return self.{manager_name}.{func_name}(*args, **kwargs)',
                '    '
            ])
        
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Refactored main class saved to: {main_file}")
    
    def generate_summary_report(self):
        """生成重构摘要报告"""
        report_file = self.source_file.parent / "refactor_report.md"
        
        lines = [
            '# Google Drive Shell 重构报告',
            '',
            f'## 源文件分析',
            f'- 源文件: {self.source_file}',
            f'- 总行数: {len(self.source_content.split())}',
            f'- 总函数数: {len(self.functions)}',
            '',
            '## 模块分布',
            ''
        ]
        
        for category, func_names in self.module_categories.items():
            actual_functions = [f for f in self.functions.keys() if self.functions[f].category == category]
            lines.extend([
                f'### {category}',
                f'- 计划函数数: {len(func_names)}',
                f'- 实际函数数: {len(actual_functions)}',
                f'- 函数列表: {", ".join(actual_functions)}',
                ''
            ])
        
        lines.extend([
            '## 未分类函数',
            ''
        ])
        
        uncategorized = [f for f in self.functions.keys() if self.functions[f].category == 'utils']
        for func in uncategorized:
            lines.append(f'- {func}')
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Summary report saved to: {report_file}")
    
    def run_refactor(self):
        """执行完整的重构过程"""
        print("Starting Google Drive Shell refactoring...")
        
        try:
            self.load_source_file()
            self.extract_imports()
            self.parse_functions()
            self.generate_module_files()
            self.generate_refactored_main_class()
            self.generate_summary_report()
            
            print("\n✅ Refactoring completed successfully!")
            print(f"Generated files:")
            print(f"  - modules/ directory with {len(self.module_categories)} module files")
            print(f"  - google_drive_shell_refactored.py (new main class)")
            print(f"  - refactor_report.md (summary report)")
            
        except Exception as e:
            print(f"\n❌ Refactoring failed: {e}")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Google Drive Shell Refactor Helper")
    parser.add_argument("--source", "-s", default="google_drive_shell.py", 
                       help="Source file to refactor")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="Dry run - only analyze, don't generate files")
    
    args = parser.parse_args()
    
    refactor = GoogleDriveShellRefactor(args.source)
    
    if args.dry_run:
        print("Dry run mode - analyzing only...")
        refactor.load_source_file()
        refactor.extract_imports()
        refactor.parse_functions()
        refactor.generate_summary_report()
    else:
        refactor.run_refactor()

if __name__ == "__main__":
    main() 