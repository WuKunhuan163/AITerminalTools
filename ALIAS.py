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

def generate_run_identifier():
    """生成一个基于时间和随机数的唯一标识符"""
    import time
    import random
    
    timestamp = str(time.time())
    random_num = str(random.randint(100000, 999999))
    combined = f"{timestamp}_{random_num}_{os.getpid()}"
    
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def get_run_context():
    """获取 RUN 执行上下文信息"""
    run_identifier = os.environ.get('RUN_IDENTIFIER')
    output_file = os.environ.get('RUN_OUTPUT_FILE')
    
    if run_identifier:
        if not output_file:
            output_file = f"RUN_output/run_{run_identifier}.json"
        return {
            'in_run_context': True,
            'identifier': run_identifier,
            'output_file': output_file
        }
    elif output_file:
        try:
            filename = Path(output_file).stem
            if filename.startswith('run_'):
                identifier = filename[4:]
            else:
                identifier = generate_run_identifier()
        except:
            identifier = generate_run_identifier()
        
        return {
            'in_run_context': True,
            'identifier': identifier,
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
        
        # 添加RUN相关信息
        data['run_identifier'] = run_context['identifier']
        
        with open(run_context['output_file'], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

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

def get_config_files() -> List[Path]:
    """获取shell配置文件列表"""
    home = Path.home()
    config_files = [
        home / ".bash_profile",
        home / ".bashrc", 
        home / ".zshrc"
    ]
    return config_files

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
        alias_line = f"alias {alias_name}='{alias_command}'\n"
        with open(config_file, 'a', encoding='utf-8') as f:
            f.write(alias_line)
        
        return True
    except Exception as e:
        print(f"Error adding alias to {config_file}: {e}")
        return False

def create_alias(alias_name: str, alias_command: str, run_context) -> int:
    """创建别名"""
    
    # 验证别名名称
    valid, error_msg = validate_alias_name(alias_name)
    if not valid:
        error_data = {
            "success": False,
            "error": f"Invalid alias name: {error_msg}",
            "alias_name": alias_name
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
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
    if run_context['in_run_context']:
        output_data = {
            "success": success_count > 0,
            "message": f"Alias '{alias_name}' created successfully" if success_count > 0 else "Failed to create alias",
            "alias_name": alias_name,
            "alias_command": alias_command,
            "files_processed": len(config_files),
            "files_updated": success_count,
            "results": results
        }
        write_to_json_output(output_data, run_context)
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
            print("💡 To use the alias immediately, run one of these commands:")
            print("   source ~/.bash_profile")
            print("   source ~/.bashrc")
            print("   source ~/.zshrc")
            print()
            print("Or restart your terminal.")
        else:
            print("❌ Failed to create alias in any configuration file")
    
    return 0 if success_count > 0 else 1

def show_help():
    """显示帮助信息"""
    help_text = """ALIAS - Permanent Shell Alias Creation Tool

Usage: ALIAS <alias_name> <alias_command>

Arguments:
  alias_name      The short name for the alias (cannot be 'ALIAS')
  alias_command   The command that the alias will execute

Options:
  --help, -h      Show this help message

Examples:
  ALIAS ll "ls -la"                    # Create alias for detailed listing
  ALIAS gs "git status"                # Create alias for git status
  ALIAS python python3                 # Create alias for python3
  ALIAS mydir "cd ~/my-project"        # Create alias for changing directory
  ALIAS serve "python -m http.server"  # Create alias for local server

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
    # 获取执行上下文
    run_context = get_run_context()
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    if len(args) == 0:
        if run_context['in_run_context']:
            error_data = {
                "success": False,
                "error": "No arguments provided. Usage: ALIAS <alias_name> <alias_command>"
            }
            write_to_json_output(error_data, run_context)
        else:
            print("❌ Error: No arguments provided")
            print("Usage: ALIAS <alias_name> <alias_command>")
            print("Use --help for more information")
        return 1
    
    if args[0] in ['--help', '-h']:
        if run_context['in_run_context']:
            help_data = {
                "success": True,
                "message": "Help information",
                "help": "ALIAS - Permanent Shell Alias Creation Tool"
            }
            write_to_json_output(help_data, run_context)
        else:
            show_help()
        return 0
    
    if len(args) != 2:
        error_msg = "Error: Exactly two arguments required: alias_name and alias_command"
        if run_context['in_run_context']:
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ {error_msg}")
            print("Usage: ALIAS <alias_name> <alias_command>")
            print("Use --help for more information")
        return 1
    
    alias_name = args[0]
    alias_command = args[1]
    
    return create_alias(alias_name, alias_command, run_context)

if __name__ == "__main__":
    sys.exit(main()) 