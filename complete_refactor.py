#!/usr/bin/env python3
"""
Complete File Operations Refactor
Aggressive refactoring with duplicate removal, merging, and proper modularization
"""

import os
import re
import shutil
from typing import Dict, List, Set

class CompleteRefactor:
    def __init__(self):
        self.source_file = "GOOGLE_DRIVE_PROJ/modules/file_operations.py"
        self.modules_dir = "GOOGLE_DRIVE_PROJ/modules"
        
        # Methods to delete (unused or redundant)
        self.methods_to_delete = {
            "_display_dependency_summary_old",  # Unused old function
            "_execute_python_code_remote_unified",  # Merge into _execute_python_code_remote
            "_execute_python_file_remote",  # Merge into _execute_python_file
        }
        
        # Duplicate methods to investigate and potentially merge
        self.duplicate_methods = {
            "_check_pip_version_conflicts",  # Found twice
            "_execute_pip_command_enhanced",  # Found twice
        }
        
        # Module structure - much more focused
        self.modules = {
            "venv_operations": {
                "file": "venv_operations.py",
                "description": "Virtual environment state management",
                "classes": ["VenvApiManager"],
                "methods": [
                    # VenvApiManager methods
                    "get_venv_base_path", "get_venv_state_file_path", "read_venv_states", "list_venv_environments",
                    # Venv state methods
                    "_get_venv_api_manager", "_get_current_venv", "_initialize_venv_state", "_initialize_venv_state_simple",
                    "_initialize_venv_states_batch", "_save_all_venv_states", "_load_all_venv_states", 
                    "_create_initial_venv_states_file", "_ensure_environment_state_exists", "_clear_venv_state",
                    "_get_environment_json_path", "_get_current_timestamp", "_update_environment_packages_in_json"
                ]
            },
            
            "pip_operations": {
                "file": "pip_operations.py",
                "description": "Pip package management and scanning",
                "classes": [],
                "methods": [
                    "cmd_pip", "_detect_current_environment_packages", "_handle_pip_install", "_handle_pip_list", 
                    "_handle_pip_show", "_validate_pip_install_packages", "_check_local_package_installability",
                    "_smart_pip_install", "_execute_pip_command_enhanced", "_get_packages_from_json",
                    "_parse_improved_package_scan_output", "_scan_environment_packages_real", "_scan_environment_via_api",
                    "_packages_differ", "_update_package_in_environment_json"
                ]
            },
            
            "dependency_analysis": {
                "file": "dependency_analysis.py", 
                "description": "Package dependency analysis and visualization",
                "classes": [],
                "methods": [
                    "_normalize_package_name", "_analyze_dependencies_recursive", "_analyze_package_dependencies",
                    "_ensure_pipdeptree_available", "_get_package_dependencies_with_pipdeptree", 
                    "_get_dependencies_via_remote_pip_show", "_get_pypi_dependencies", "_fallback_dependency_analysis",
                    "_show_dependency_tree", "_display_package_dependency_tree", "_display_simple_level_summary"
                ]
            },
            
            "python_execution": {
                "file": "python_execution.py",
                "description": "Python code execution (local and remote)",
                "classes": [],
                "methods": [
                    "cmd_python", "_execute_python_code", "_execute_python_code_local", "_execute_python_code_remote",
                    "_execute_python_file", "_execute_individual_fallback", "_execute_non_bash_safe_commands"
                ]
            },
            
            "file_operations": {
                "file": "file_core.py",
                "description": "Core file operations (upload, download, navigation)",
                "classes": [],
                "methods": [
                    "cmd_upload_folder", "cmd_upload", "cmd_download", "cmd_pwd", "cmd_ls", "_ls_recursive",
                    "_build_nested_structure", "_build_folder_tree", "_generate_folder_url", "_generate_web_url",
                    "cmd_cd", "cmd_mkdir", "cmd_touch", "cmd_rm", "cmd_cp", "cmd_mv", "_check_large_files",
                    "_handle_large_files", "wait_for_file_sync", "_check_target_file_conflicts_before_move",
                    "_check_remote_file_conflicts", "_verify_files_available", "_cleanup_local_equivalent_files"
                ]
            },
            
            "text_operations": {
                "file": "text_operations.py",
                "description": "Text file editing and content operations",
                "classes": [],
                "methods": [
                    "cmd_edit", "cmd_nano", "cmd_vim", "cmd_cat", "cmd_head", "cmd_tail", "cmd_grep", "cmd_find", 
                    "cmd_wc", "_create_text_file", "_download_and_get_content", "_format_read_output",
                    "_generate_edit_diff", "_generate_local_diff_preview", "_find_file", "_find_folder", "_create_backup"
                ]
            }
        }
    
    def read_file_content(self) -> str:
        """Read the source file content"""
        with open(self.source_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def find_method_boundaries(self, content: str, method_name: str) -> List[tuple]:
        """Find all occurrences of a method and their boundaries"""
        lines = content.split('\n')
        methods = []
        
        for i, line in enumerate(lines):
            if re.match(rf'^\s{{4}}def\s+{re.escape(method_name)}\s*\(', line):
                # Found method start, now find end
                start_line = i
                method_indent = len(line) - len(line.lstrip())
                
                # Find end of method
                end_line = len(lines)
                for j in range(i + 1, len(lines)):
                    next_line = lines[j]
                    if next_line.strip() == '':
                        continue
                    
                    current_indent = len(next_line) - len(next_line.lstrip())
                    
                    # If we hit a line with same or less indentation that's not empty, method ends
                    if current_indent <= method_indent and next_line.strip():
                        end_line = j
                        break
                
                methods.append((start_line, end_line, '\n'.join(lines[start_line:end_line])))
        
        return methods
    
    def remove_duplicate_methods(self, content: str) -> str:
        """Remove duplicate methods, keeping the first occurrence"""
        lines = content.split('\n')
        
        for method_name in self.duplicate_methods:
            method_occurrences = self.find_method_boundaries(content, method_name)
            
            if len(method_occurrences) > 1:
                print(f"🔍 Found {len(method_occurrences)} occurrences of {method_name}")
                
                # Keep the first, remove the rest
                for i in range(len(method_occurrences) - 1, 0, -1):  # Remove from end to start
                    start_line, end_line, _ = method_occurrences[i]
                    print(f"  ❌ Removing duplicate {method_name} at lines {start_line}-{end_line}")
                    del lines[start_line:end_line]
                    
                # Update content for next iteration
                content = '\n'.join(lines)
                lines = content.split('\n')
        
        return '\n'.join(lines)
    
    def remove_unused_methods(self, content: str) -> str:
        """Remove unused methods"""
        for method_name in self.methods_to_delete:
            method_occurrences = self.find_method_boundaries(content, method_name)
            
            if method_occurrences:
                print(f"🗑️ Removing unused method: {method_name}")
                lines = content.split('\n')
                
                for start_line, end_line, _ in reversed(method_occurrences):
                    del lines[start_line:end_line]
                
                content = '\n'.join(lines)
        
        return content
    
    def extract_class_and_methods(self, content: str, target_classes: List[str], target_methods: List[str]) -> str:
        """Extract specific classes and methods"""
        lines = content.split('\n')
        extracted_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for target classes
            class_match = re.match(r'^class\s+(\w+)', line)
            if class_match and class_match.group(1) in target_classes:
                # Extract entire class
                class_start = i
                class_indent = len(line) - len(line.lstrip())
                
                # Find class end
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.strip() == '':
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= class_indent and next_line.strip():
                        break
                    j += 1
                
                extracted_lines.extend(lines[class_start:j])
                i = j
                continue
            
            # Check for target methods
            method_match = re.match(r'^(\s{4})def\s+(\w+)\s*\(', line)
            if method_match and method_match.group(2) in target_methods:
                # Extract entire method
                method_start = i
                method_indent = len(method_match.group(1))
                
                # Find method end
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    if next_line.strip() == '':
                        j += 1
                        continue
                    
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= method_indent and next_line.strip():
                        break
                    j += 1
                
                extracted_lines.extend(lines[method_start:j])
                i = j
                continue
            
            i += 1
        
        return '\n'.join(extracted_lines)
    
    def create_module_file(self, module_name: str, module_info: Dict, content: str) -> str:
        """Create a module file"""
        
        # Extract the relevant content
        extracted_content = self.extract_class_and_methods(
            content, 
            module_info["classes"], 
            module_info["methods"]
        )
        
        # Create module header
        header = f'''
class {module_name.title().replace('_', '')}:
    """
    {module_info["description"]}
    """
    
    def __init__(self, drive_service, main_instance):
        self.drive_service = drive_service
        self.main_instance = main_instance

{extracted_content}
'''
        
        return header
    
    def create_main_coordinator(self, content: str) -> str:
        """Create the main FileOperations coordinator class"""
        # Import all modules
        module_imports = []
        for module_name, module_info in self.modules.items():
            class_name = module_name.title().replace('_', '')
            module_imports.append(f"from .{module_info['file'][:-3]} import {class_name}")
        imports_section = '\n'.join(module_imports)
        
        # Create coordinator class
        coordinator = f'''
{imports_section}

class FileOperations:
    """
    Main file operations coordinator - delegates to specialized modules
    """
    
    def __init__(self, drive_service, main_instance=None):
        """Initialize all specialized modules"""
        self.drive_service = drive_service
        self.main_instance = main_instance
        
        # Initialize specialized modules
'''
        
        # Add module initializations
        for module_name, module_info in self.modules.items():
            class_name = module_name.title().replace('_', '')
            var_name = module_name.lower()
            coordinator += f"        self.{var_name} = {class_name}(drive_service, main_instance)\n"
        
        coordinator += '\n'
        
        # Add delegation methods
        for module_name, module_info in self.modules.items():
            var_name = module_name.lower()
            for method in module_info["methods"]:
                if not method.startswith('_'):  # Only delegate public methods
                    coordinator += f'''    def {method}(self, *args, **kwargs):
        """Delegate to {var_name}"""
        return self.{var_name}.{method}(*args, **kwargs)
    
'''
        
        # Add basic utility methods that should stay in main class
        coordinator += '''    def check_network_connection(self):
        """Check network connection"""
        try:
            import urllib.request
            urllib.request.urlopen('http://www.google.com', timeout=1)
            return True
        except:
            return False
    
    def ensure_google_drive_desktop_running(self):
        """Ensure Google Drive Desktop is running"""
        try:
            import subprocess
            import platform
            import time
            
            # Check if running
            result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and bool(result.stdout.strip()):
                return True
            
            # Try to start
            print("🚀 Starting Google Drive Desktop...")
            if platform.system() == "Darwin":
                subprocess.run(['open', '-a', 'Google Drive'], check=False)
            elif platform.system() == "Linux":
                subprocess.run(['google-drive'], check=False)
            elif platform.system() == "Windows":
                subprocess.run(['start', 'GoogleDrive'], shell=True, check=False)
            
            # Wait for startup
            for i in range(10):
                time.sleep(1)
                result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and bool(result.stdout.strip()):
                    print("✅ Google Drive Desktop started successfully")
                    return True
            
            print("⚠️ Could not confirm Google Drive Desktop startup")
            return False
            
        except Exception as e:
            print(f"❌ Error managing Google Drive Desktop: {e}")
            return False
'''
        
        return coordinator
    
    def run_complete_refactor(self):
        """Execute the complete refactor"""
        print("🚀 Starting complete file_operations.py refactor...")
        
        # Read original content
        content = self.read_file_content()
        original_lines = len(content.split('\n'))
        print(f"📊 Original file: {original_lines} lines")
        
        # Step 1: Remove duplicates and unused methods
        print("\n🧹 Cleaning up duplicates and unused methods...")
        content = self.remove_duplicate_methods(content)
        content = self.remove_unused_methods(content)
        
        cleaned_lines = len(content.split('\n'))
        print(f"📊 After cleanup: {cleaned_lines} lines (removed {original_lines - cleaned_lines} lines)")
        
        # Step 2: Create specialized modules
        print(f"\n📦 Creating {len(self.modules)} specialized modules...")
        
        for module_name, module_info in self.modules.items():
            module_file = os.path.join(self.modules_dir, module_info["file"])
            module_content = self.create_module_file(module_name, module_info, content)
            
            with open(module_file, 'w', encoding='utf-8') as f:
                f.write(module_content)
            
            lines = len(module_content.split('\n'))
            print(f"  ✅ {module_info['file']}: {lines} lines - {module_info['description']}")
        
        # Step 3: Create main coordinator
        print("\n🎯 Creating main coordinator...")
        coordinator_content = self.create_main_coordinator(content)
        
        with open(self.source_file, 'w', encoding='utf-8') as f:
            f.write(coordinator_content)
        
        coordinator_lines = len(coordinator_content.split('\n'))
        print(f"  ✅ file_operations.py: {coordinator_lines} lines - Main coordinator")
        
        # Summary
        total_new_lines = coordinator_lines + sum(len(self.create_module_file(name, info, content).split('\n')) 
                                                 for name, info in self.modules.items())
        
        print(f"\n🎉 Complete refactor finished!")
        print(f"📊 Summary:")
        print(f"  • Original: {original_lines} lines in 1 file")
        print(f"  • New: {total_new_lines} lines across {len(self.modules) + 1} files")
        print(f"  • Reduction: {original_lines - total_new_lines} lines removed")
        print(f"  • Modules created: {len(self.modules)}")

if __name__ == "__main__":
    refactor = CompleteRefactor()
    refactor.run_complete_refactor()
