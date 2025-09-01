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
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
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
                print(f"Updated: {config_file}")
            else:
                print(f"Error: Failed to update {config_file}: {result.stderr}")
        except Exception as e:
            print(f"Error: Error updating {config_file}: {e}")
    
    if success_count > 0:
        print(f"🎉 Successfully updated {success_count} configuration files!")
        print("💡 Changes should now be active in your current shell.")
    else:
        print("Error:  Failed to update any configuration files.")
    
    return success_count > 0

def copy_to_clipboard(text):
    """将文本复制到剪贴板"""
    try:
        # macOS
        if sys.platform == "darwin":
            result = subprocess.run(["pbcopy"], input=text.encode(), check=True, capture_output=True)
            return True
        # Linux
        elif sys.platform == "linux":
            result = subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True, capture_output=True)
            return True
        # Windows
        elif sys.platform == "win32":
            result = subprocess.run(["clip"], input=text.encode(), check=True, shell=True, capture_output=True)
            return True
        return False
    except subprocess.CalledProcessError as e:
        # 调试信息（可以注释掉）
        # print(f"Debug: pbcopy failed with return code {e.returncode}")
        # print(f"Debug: stderr: {e.stderr}")
        return False
    except Exception as e:
        # print(f"Debug: Exception in copy_to_clipboard: {e}")
        return False

def copy_source_commands_to_clipboard(updated_files):
    """生成source命令并复制到剪贴板"""
    if not updated_files:
        return
    
    # 过滤出shell配置文件
    shell_config_files = []
    for file_path in updated_files:
        file_name = os.path.basename(file_path)
        if file_name in ['.bash_profile', '.bashrc', '.zshrc']:
            shell_config_files.append(file_path)
    
    if not shell_config_files:
        return
    
    # 生成source命令，用&&连接
    source_commands = []
    for config_file in shell_config_files:
        source_commands.append(f"source {config_file}")
    
    source_command_line = " && ".join(source_commands)
    
    # 尝试复制到剪贴板
    if copy_to_clipboard(source_command_line):
        print(f"📋 Source command copied to clipboard:")
        print(f"   {source_command_line}")
        print("💡 Paste and execute to take effect immediately in the current session")
    else:
        print(f"Warning: Cannot copy to clipboard, please execute manually:")
        print(f"   {source_command_line}")

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
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 检查是否是要移除的export语句的开始
        if (stripped.startswith(f'export {var_name}=') or 
            stripped.startswith(f'export {var_name} =') or
            stripped == f'export {var_name}'):
            
            # 如果使用了 $'...' 格式，需要找到匹配的结束引号
            if f"export {var_name}=$'" in line:
                # 多行 $'...' 格式，需要找到结束的单引号
                while i < len(lines):
                    current_line = lines[i]
                    # 检查是否找到了结束的单引号（不被转义的）
                    if current_line.rstrip().endswith("'") and not current_line.rstrip().endswith("\\'"):
                        i += 1  # 跳过这一行
                        break
                    i += 1
                continue
            else:
                # 单行格式，直接跳过
                i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    return new_lines

def add_export_statement(lines: List[str], var_name: str, var_value: str) -> List[str]:
    """添加export语句到配置文件"""
    # 移除已存在的export语句
    lines = remove_existing_export(lines, var_name)
    
    # 检查是否是多行值（包含换行符）
    if '\n' in var_value:
        # 对于多行值，使用 $'...' 格式来正确处理换行符
        # 将换行符转换为 \n 转义序列
        escaped_value = var_value.replace('\\', '\\\\').replace('\n', '\\n').replace("'", "\\'")
        export_line = f"export {var_name}=$'{escaped_value}'\n"
    else:
        # 对于单行值，使用标准双引号格式
        export_line = f'export {var_name}="{var_value}"\n'
    
    # 如果文件不为空且最后一行不是空行，添加一个空行
    if lines and not lines[-1].endswith('\n'):
        lines.append('\n')
    
    lines.append(export_line)
    return lines

def remove_variable(var_name: str, command_identifier=None):
    """移除环境变量并从配置文件中删除"""
    
    # 验证变量名
    if not var_name or not var_name.replace('_', '').isalnum():
        error_data = {
            "success": False,
            "error": f"Invalid variable name: {var_name}",
            "variable": var_name
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: Invalid variable name: {var_name}")
        return 1
    
    # 获取配置文件
    config_files = get_shell_config_files()
    
    # 从当前环境中移除变量
    if var_name in os.environ:
        del os.environ[var_name]
    
    updated_files = []
    failed_files = []
    
    # 从每个配置文件中移除export语句
    for config_file in config_files:
        try:
            # 备份文件
            if not backup_config_file(config_file):
                failed_files.append(str(config_file))
                continue
            
            # 读取现有内容
            lines = read_config_file(config_file)
            
            # 移除export语句
            new_lines = remove_export_statement(lines, var_name)
            
            # 写入文件
            if write_config_file(config_file, new_lines):
                updated_files.append(str(config_file))
            else:
                failed_files.append(str(config_file))
                
        except Exception as e:
            failed_files.append(str(config_file))
            if not is_run_environment(command_identifier):
                print(f"Error: Error updating {config_file}: {e}")
    
    # 准备结果
    result_data = {
        "success": len(failed_files) == 0,
        "variable": var_name,
        "updated_files": updated_files,
        "failed_files": failed_files,
        "message": f"Removed {var_name} from {len(updated_files)} files" if len(failed_files) == 0 else f"Failed to remove from {len(failed_files)} files"
    }
    
    if is_run_environment(command_identifier):
        write_to_json_output(result_data, command_identifier)
    else:
        if len(failed_files) == 0:
            print(f"Successfully removed {var_name} from {len(updated_files)} configuration files!")
            for file in updated_files:
                print(f"   📝 {file}")
        else:
            print(f"Warning: Partially successful: removed from {len(updated_files)} files, failed on {len(failed_files)} files")
            for file in failed_files:
                print(f"   ❌ {file}")
    
    return 0 if len(failed_files) == 0 else 1

def remove_export_statement(lines: List[str], var_name: str) -> List[str]:
    """从配置行中移除指定的export语句"""
    new_lines = []
    
    for line in lines:
        # 检查是否是要移除的export语句
        stripped = line.strip()
        if (stripped.startswith(f'export {var_name}=') or 
            stripped.startswith(f'export {var_name} =') or
            stripped == f'export {var_name}'):
            # 跳过这一行（不添加到new_lines中）
            continue
        else:
            new_lines.append(line)
    
    return new_lines

def export_variable(var_name: str, var_value: str, command_identifier=None):
    """导出环境变量并写入配置文件"""
    
    # 验证变量名
    if not var_name or not var_name.replace('_', '').isalnum():
        error_data = {
            "success": False,
            "error": f"Invalid variable name: {var_name}",
            "variable": var_name
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: Invalid variable name: {var_name}")
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
        
        if is_run_environment(command_identifier):
            write_to_json_output(success_data, command_identifier)
        else:
            print(f"Successfully exported {var_name}='{var_value}'")
            print(f"Updated files: {', '.join(updated_files)}")
            if failed_files:
                print(f"Error: Failed files: {', '.join(failed_files)}")
            
            # 自动在当前shell中设置环境变量
            os.environ[var_name] = var_value
            print("🔄 Environment variable set in current session")
            print("💡 Note: Changes will persist in new terminal sessions")
            
            # 生成source命令并复制到剪贴板
            copy_source_commands_to_clipboard(updated_files)
        return 0
    else:
        error_data = {
            "success": False,
            "error": "Failed to update any configuration files",
            "variable": var_name,
            "failed_files": failed_files
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: Failed to update any configuration files")
            print(f"Failed files: {', '.join(failed_files)}")
        return 1

def show_help():
    """显示帮助信息"""
    help_text = """EXPORT - Environment Variable Export Tool

Usage: EXPORT <variable_name> <value>
       EXPORT --remove <variable_name>
       EXPORT --update

Arguments:
  variable_name        Name of the environment variable to export
  value               Value to assign to the variable

Options:
  --help, -h          Show this help message
  --remove, --undo, -r Remove an existing environment variable
  --update            Update shell configuration files (source all config files)

Examples:
  EXPORT OPENROUTER_API_KEY "sk-or-v1-..."
  EXPORT PATH "/usr/local/bin:$PATH"
  EXPORT MY_VAR "some value"
  EXPORT --remove MY_VAR
  EXPORT --undo OPENROUTER_API_KEY
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
    # 获取执行上下文和command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    
    if len(args) == 0:
        if is_run_environment(command_identifier):
            error_data = {
                "success": False,
                "error": "No arguments provided. Usage: EXPORT <variable_name> <value>"
            }
            write_to_json_output(error_data, command_identifier)
        else:
            print("Error: No arguments provided")
            print("Usage: EXPORT <variable_name> <value>")
            print("Use --help for more information")
        return 1
    
    if len(args) == 1:
        if args[0] in ['--help', '-h']:
            if is_run_environment(command_identifier):
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": "EXPORT - Environment Variable Export Tool"
                }
                write_to_json_output(help_data, command_identifier)
            else:
                show_help()
            return 0
        elif args[0] == '--update':
            if is_run_environment(command_identifier):
                success = update_shell_configs()
                output_data = {
                    "success": success,
                    "message": "Configuration files updated" if success else "Failed to update configuration files"
                }
                write_to_json_output(output_data, command_identifier)
                return 0 if success else 1
            else:
                print("Updating shell configuration files...")
                success = update_shell_configs()
                return 0 if success else 1
        else:
            if is_run_environment(command_identifier):
                error_data = {
                    "success": False,
                    "error": "Missing value. Usage: EXPORT <variable_name> <value> or EXPORT --remove <variable_name>"
                }
                write_to_json_output(error_data, command_identifier)
            else:
                print("Error: Missing value")
                print("Usage: EXPORT <variable_name> <value>")
                print("       EXPORT --remove <variable_name>")
                print("       EXPORT --undo <variable_name>")
            return 1
    
    if len(args) == 2:
        if args[0] in ['--remove', '--undo', '-r']:
            var_name = args[1]
            return remove_variable(var_name, command_identifier)
    
    if len(args) >= 2:
        var_name = args[0]
        var_value = args[1]
        
        # 如果有多个参数，将它们连接起来（用空格分隔）
        if len(args) > 2:
            var_value = ' '.join(args[1:])
        
        return export_variable(var_name, var_value, command_identifier)
    
    return 1

if __name__ == "__main__":
    sys.exit(main()) 