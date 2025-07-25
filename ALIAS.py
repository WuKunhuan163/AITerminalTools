#!/usr/bin/env python3
"""
ALIAS.py - Permanent Shell Alias Creation Tool
Creates permanent aliases in shell configuration files
Python version with RUN environment detection
"""

import os
import sys
import json
import hashlib
import re
from pathlib import Path
from typing import List, Optional

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
    config_files = get_config_files()
    
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


def get_config_files() -> List[Path]:
    """获取shell配置文件路径"""
    home = Path.home()
    return [
        home / ".bash_profile",
        home / ".bashrc", 
        home / ".zshrc"
    ]


def validate_alias_name(alias_name: str) -> tuple[bool, str]:
    """验证别名名称是否有效"""
    if not alias_name:
        return False, "Alias name cannot be empty"
    
    if alias_name == "ALIAS":
        return False, "Alias name cannot be 'ALIAS'"
    
    if re.search(r'\s', alias_name):
        return False, "Alias name cannot contain spaces"
    
    # 检查是否包含特殊字符
    if re.search(r'[;&|<>(){}[\]$`"\'\\]', alias_name):
        return False, "Alias name contains invalid characters"
    
    return True, ""

def check_existing_alias(alias_name: str, config_file: Path) -> bool:
    """检查别名是否已存在于配置文件中"""
    if not config_file.exists():
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找现有的别名定义
        pattern = rf'^alias\s+{re.escape(alias_name)}\s*='
        return bool(re.search(pattern, content, re.MULTILINE))
    except Exception:
        return False

def remove_existing_alias(alias_name: str, config_file: Path) -> bool:
    """从配置文件中移除现有的别名"""
    if not config_file.exists():
        return True
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 过滤掉现有的别名行
        pattern = rf'^alias\s+{re.escape(alias_name)}\s*='
        new_lines = [line for line in lines if not re.match(pattern, line)]
        
        with open(config_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        return True
    except Exception as e:
        print(f"Error removing existing alias from {config_file}: {e}")
        return False

def add_alias_to_file(alias_name: str, alias_command: str, config_file: Path) -> bool:
    """向配置文件添加别名"""
    try:
        # 如果文件不存在，创建它
        if not config_file.exists():
            config_file.touch()
        
        # 移除现有的别名（如果存在）
        if check_existing_alias(alias_name, config_file):
            remove_existing_alias(alias_name, config_file)
        
        # 添加新的别名
        # 根据命令内容选择合适的引号
        if "'" in alias_command:
            alias_line = f'alias {alias_name}="{alias_command}"\n'
        else:
            alias_line = f"alias {alias_name}='{alias_command}'\n"
        
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(alias_line)
        
        return True
    except Exception as e:
        print(f"Error adding alias to {config_file}: {e}")
        return False

def create_alias(alias_name: str, alias_command: str, command_identifier=None) -> int:
    """创建别名"""
    
    # 验证别名名称
    valid, error_msg = validate_alias_name(alias_name)
    if not valid:
        error_data = {
            "success": False,
            "error": f"Invalid alias name: {error_msg}",
            "alias_name": alias_name
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"❌ Error: {error_msg}")
        
        return 1
    
    # 获取配置文件
    config_files = get_config_files()
    
    # 处理结果
    results = []
    success_count = 0
    
    for config_file in config_files:
        file_existed = config_file.exists()
        had_existing_alias = check_existing_alias(alias_name, config_file)
        
        if add_alias_to_file(alias_name, alias_command, config_file):
            success_count += 1
            results.append({
                "file": str(config_file),
                "success": True,
                "created_file": not file_existed,
                "updated_existing": had_existing_alias
            })
        else:
            results.append({
                "file": str(config_file),
                "success": False,
                "error": "Failed to add alias"
            })
    
    # 准备输出数据
    if is_run_environment(command_identifier):
        output_data = {
            "success": success_count > 0,
            "message": f"Alias '{alias_name}' created successfully" if success_count > 0 else "Failed to create alias",
            "alias_name": alias_name,
            "alias_command": alias_command,
            "files_processed": len(config_files),
            "files_updated": success_count,
            "results": results
        }
        write_to_json_output(output_data, command_identifier)
    else:
        print(f"Creating alias: {alias_name} -> {alias_command}")
        print()
        
        for result in results:
            if result["success"]:
                status = "✅"
                if result.get("created_file"):
                    status += f" Created file and added alias: {result['file']}"
                elif result.get("updated_existing"):
                    status += f" Updated existing alias in: {result['file']}"
                else:
                    status += f" Added alias to: {result['file']}"
                print(status)
            else:
                print(f"❌ Failed to update: {result['file']}")
        
        print()
        if success_count > 0:
            print("🎉 Alias created successfully!")
            print("🔄 Alias will be available in new terminal sessions")
            print("💡 Note: Current session may need manual source or restart for aliases")
        else:
            print("❌ Failed to create alias in any configuration file")
    
    return 0 if success_count > 0 else 1

def remove_alias_from_all_files(alias_name: str, command_identifier=None) -> int:
    """从所有配置文件中移除别名"""
    config_files = get_config_files()
    removed_count = 0
    results = []

    for config_file in config_files:
        if remove_existing_alias(alias_name, config_file):
            removed_count += 1
            results.append({
                "file": str(config_file),
                "success": True,
                "alias_name": alias_name
            })
        else:
            results.append({
                "file": str(config_file),
                "success": False,
                "error": "Failed to remove alias"
            })

    if is_run_environment(command_identifier):
        output_data = {
            "success": removed_count > 0,
            "message": f"Alias '{alias_name}' removed successfully" if removed_count > 0 else "Failed to remove alias",
            "alias_name": alias_name,
            "files_processed": len(config_files),
            "files_removed": removed_count,
            "results": results
        }
        write_to_json_output(output_data, command_identifier)
    else:
        print(f"Removing alias: {alias_name}")
        print()
        for result in results:
            if result["success"]:
                print(f"✅ Removed alias '{alias_name}' from {result['file']}")
            else:
                print(f"❌ Failed to remove alias '{alias_name}' from {result['file']}: {result['error']}")
        print()
        if removed_count > 0:
            print("🎉 Alias removed successfully!")
        else:
            print("❌ Alias not found in any configuration file.")
    
    return 0 if removed_count > 0 else 1

def show_help():
    """显示帮助信息"""
    help_text = """ALIAS - Permanent Shell Alias Creation Tool

Usage: ALIAS <alias_name> <alias_command>

Arguments:
  alias_name      The short name for the alias (cannot be 'ALIAS')
  alias_command   The command that the alias will execute

Options:
  --help, -h      Show this help message
  --remove, --undo, -r  Remove an existing alias
  --update        Update shell configuration files (source all config files)

Examples:
  ALIAS ll "ls -la"                    # Create alias for detailed listing
  ALIAS gs "git status"                # Create alias for git status
  ALIAS python python3                 # Create alias for python3
  ALIAS mydir "cd ~/my-project"        # Create alias for changing directory
  ALIAS serve "python -m http.server"  # Create alias for local server
  ALIAS --remove ll                     # Remove the 'll' alias
  ALIAS --undo gs                       # Remove the 'gs' alias
  ALIAS --update                        # Update shell configuration files

Notes:
  - Alias names cannot contain spaces or special characters
  - Alias commands with spaces should be quoted
  - Aliases are added to ~/.bash_profile, ~/.bashrc, and ~/.zshrc
  - Existing aliases with the same name will be updated
  - Use 'source ~/.bashrc' (or similar) to activate aliases immediately

This tool will:
1. Validate the alias name
2. Add the alias to shell configuration files
3. Handle existing aliases by updating them
4. Provide instructions for immediate activation"""
    
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
                "error": "No arguments provided. Usage: ALIAS <alias_name> <alias_command>"
            }
            write_to_json_output(error_data, command_identifier)
        else:
            print("❌ Error: No arguments provided")
            print("Usage: ALIAS <alias_name> <alias_command>")
            print("Use --help for more information")
        return 1
    
    if args[0] in ['--help', '-h']:
        if is_run_environment(command_identifier):
            help_data = {
                "success": True,
                "message": "Help information",
                "help": "ALIAS - Permanent Shell Alias Creation Tool"
            }
            write_to_json_output(help_data, command_identifier)
        else:
            show_help()
        return 0
    
    # 处理移除别名
    if args[0] in ['--remove', '--undo', '-r']:
        if len(args) != 2:
            error_msg = "Error: --remove/--undo requires exactly one argument: alias_name"
            if is_run_environment(command_identifier):
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"❌ {error_msg}")
                print("Usage: ALIAS --remove <alias_name>")
                print("       ALIAS --undo <alias_name>")
            return 1
        
        alias_name = args[1]
        return remove_alias_from_all_files(alias_name, command_identifier)
    
    # 处理更新配置文件
    if args[0] == '--update':
        if len(args) != 1:
            error_msg = "Error: --update does not take any arguments"
            if is_run_environment(command_identifier):
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"❌ {error_msg}")
                print("Usage: ALIAS --update")
            return 1
        
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
    
    if len(args) != 2:
        error_msg = "Error: Exactly two arguments required: alias_name and alias_command"
        if is_run_environment(command_identifier):
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"❌ {error_msg}")
            print("Usage: ALIAS <alias_name> <alias_command>")
            print("Use --help for more information")
        return 1
    
    alias_name = args[0]
    alias_command = args[1]
    
    return create_alias(alias_name, alias_command, command_identifier)

if __name__ == "__main__":
    sys.exit(main()) 