#!/usr/bin/env python3
"""
EXPORT.py - Environment Variable Export Tool
Exports environment variables and writes to multiple shell configuration files
Python version with RUN environment detection
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any



def get_run_context():
    """获取 RUN 执行上下文信息"""
    run_identifier = os.environ.get('RUN_IDENTIFIER')
    output_file = os.environ.get('RUN_DATA_FILE')
    
    if run_identifier and output_file:
        return {
            'in_run_context': True,
            'identifier': run_identifier,
            'output_file': output_file
        }
    else:
        return {
            'in_run_context': False,
            'identifier': None,
            'output_file': None
        }

def write_to_json_output(data, run_context):
    """将结果写入到指定的 JSON 输出文件中"""
    if not run_context['in_run_context'] or not run_context['output_file']:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(run_context['output_file'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 不再添加冗余的RUN相关信息
        
        with open(run_context['output_file'], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def update_shell_configs():
    """更新shell配置文件（source所有配置文件）"""
    config_files = get_shell_config_files()
    
    success_count = 0
    for config_file in config_files:
        try:
            import subprocess
            result = subprocess.run(
                ["bash", "-c", f"source {str(config_file)}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                success_count += 1
                print(f"✅ Updated: {config_file}")
            else:
                print(f"❌ Failed to update {config_file}: {result.stderr}")
        except Exception as e:
            print(f"❌ Error updating {config_file}: {e}")
    
    if success_count > 0:
        print(f"🎉 Successfully updated {success_count} configuration files!")
        print("💡 Changes should now be active in your current shell.")
    else:
        print("❌ Failed to update any configuration files.")
    
    return success_count > 0


def get_shell_config_files():
    """获取shell配置文件路径"""
    home = Path.home()
    config_files = [
        home / ".bash_profile",
        home / ".bashrc",
        home / ".zshrc"
    ]
    return config_files

def backup_config_file(config_file: Path):
    """备份配置文件"""
    if config_file.exists():
        backup_file = config_file.with_suffix(config_file.suffix + '.backup')
        try:
            import shutil
            shutil.copy2(config_file, backup_file)
            return True
        except Exception:
            return False
    return True

def read_config_file(config_file: Path) -> List[str]:
    """读取配置文件内容"""
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return f.readlines()
        except Exception:
            return []
    return []

def write_config_file(config_file: Path, lines: List[str]):
    """写入配置文件"""
    try:
        # 确保目录存在
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error writing to {config_file}: {e}")
        return False

def remove_existing_export(lines: List[str], var_name: str) -> List[str]:
    """从配置文件中移除已存在的export语句"""
    new_lines = []
    for line in lines:
        stripped = line.strip()
        # 检查是否是要移除的export语句
        if (stripped.startswith(f'export {var_name}=') or 
            stripped.startswith(f'export {var_name} =') or
            stripped == f'export {var_name}'):
            continue
        new_lines.append(line)
    return new_lines

def add_export_statement(lines: List[str], var_name: str, var_value: str) -> List[str]:
    """添加export语句到配置文件"""
    # 移除已存在的export语句
    lines = remove_existing_export(lines, var_name)
    
    # 添加新的export语句
    export_line = f'export {var_name}="{var_value}"\n'
    
    # 如果文件不为空且最后一行不是空行，添加一个空行
    if lines and not lines[-1].endswith('\n'):
        lines.append('\n')
    
    lines.append(export_line)
    return lines

def export_variable(var_name: str, var_value: str, run_context):
    """导出环境变量并写入配置文件"""
    
    # 验证变量名
    if not var_name or not var_name.replace('_', '').isalnum():
        error_data = {
            "success": False,
            "error": f"Invalid variable name: {var_name}",
            "variable": var_name
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ Error: Invalid variable name: {var_name}")
        return 1
    
    # 获取配置文件
    config_files = get_shell_config_files()
    
    # 设置当前环境变量
    os.environ[var_name] = var_value
    
    updated_files = []
    failed_files = []
    
    # 更新每个配置文件
    for config_file in config_files:
        try:
            # 备份文件
            if not backup_config_file(config_file):
                failed_files.append(str(config_file))
                continue
            
            # 读取现有内容
            lines = read_config_file(config_file)
            
            # 添加export语句
            new_lines = add_export_statement(lines, var_name, var_value)
            
            # 写入文件
            if write_config_file(config_file, new_lines):
                updated_files.append(str(config_file))
            else:
                failed_files.append(str(config_file))
                
        except Exception as e:
            failed_files.append(f"{config_file} ({str(e)})")
    
    # 创建结果
    if updated_files:
        success_data = {
            "success": True,
            "message": f"Environment variable {var_name} exported successfully",
            "variable": var_name,
            "value": var_value,
            "updated_files": updated_files,
            "failed_files": failed_files if failed_files else None
        }
        
        if run_context['in_run_context']:
            write_to_json_output(success_data, run_context)
        else:
            print(f"✅ Successfully exported {var_name}='{var_value}'")
            print(f"📝 Updated files: {', '.join(updated_files)}")
            if failed_files:
                print(f"❌ Failed files: {', '.join(failed_files)}")
            print("💡 Note: Run 'source ~/.bash_profile' or restart your terminal to apply changes")
        return 0
    else:
        error_data = {
            "success": False,
            "error": "Failed to update any configuration files",
            "variable": var_name,
            "failed_files": failed_files
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ Error: Failed to update any configuration files")
            print(f"Failed files: {', '.join(failed_files)}")
        return 1

def show_help():
    """显示帮助信息"""
    help_text = """EXPORT - Environment Variable Export Tool

Usage: EXPORT <variable_name> <value>
       EXPORT --update

Arguments:
  variable_name        Name of the environment variable to export
  value               Value to assign to the variable

Options:
  --help, -h          Show this help message
  --update            Update shell configuration files (source all config files)

Examples:
  EXPORT OPENROUTER_API_KEY "sk-or-v1-..."
  EXPORT PATH "/usr/local/bin:$PATH"
  EXPORT MY_VAR "some value"
  EXPORT --update

This tool will:
1. Set the environment variable in the current session
2. Add/update the export statement in ~/.bash_profile, ~/.bashrc, and ~/.zshrc
3. Create backups of configuration files before modifying them

Note: You may need to restart your terminal or run 'source ~/.bash_profile' 
to apply changes in new sessions. Use --update to apply changes immediately."""
    
    print(help_text)

def main():
    """主函数"""
    # 获取执行上下文
    run_context = get_run_context()
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    if len(args) == 0:
        if run_context['in_run_context']:
            error_data = {
                "success": False,
                "error": "No arguments provided. Usage: EXPORT <variable_name> <value>"
            }
            write_to_json_output(error_data, run_context)
        else:
            print("❌ Error: No arguments provided")
            print("Usage: EXPORT <variable_name> <value>")
            print("Use --help for more information")
        return 1
    
    if len(args) == 1:
        if args[0] in ['--help', '-h']:
            if run_context['in_run_context']:
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": "EXPORT - Environment Variable Export Tool"
                }
                write_to_json_output(help_data, run_context)
            else:
                show_help()
            return 0
        elif args[0] == '--update':
            if run_context['in_run_context']:
                success = update_shell_configs()
                output_data = {
                    "success": success,
                    "message": "Configuration files updated" if success else "Failed to update configuration files"
                }
                write_to_json_output(output_data, run_context)
                return 0 if success else 1
            else:
                print("Updating shell configuration files...")
                success = update_shell_configs()
                return 0 if success else 1
        else:
            if run_context['in_run_context']:
                error_data = {
                    "success": False,
                    "error": "Missing value. Usage: EXPORT <variable_name> <value>"
                }
                write_to_json_output(error_data, run_context)
            else:
                print("❌ Error: Missing value")
                print("Usage: EXPORT <variable_name> <value>")
            return 1
    
    if len(args) >= 2:
        var_name = args[0]
        var_value = args[1]
        
        # 如果有多个参数，将它们连接起来（用空格分隔）
        if len(args) > 2:
            var_value = ' '.join(args[1:])
        
        return export_variable(var_name, var_value, run_context)
    
    return 1

if __name__ == "__main__":
    sys.exit(main()) 