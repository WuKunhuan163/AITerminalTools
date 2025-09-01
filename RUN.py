#!/usr/bin/env python3
"""
RUN.py - 通用命令包装器，支持JSON返回值和唯一标识符系统
Python版本的RUN脚本，提供更好的跨平台兼容性和代码重用
"""

import os
import sys
import json
import time
import random
import hashlib
import subprocess
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def generate_run_identifier(*args):
    """生成一个基于时间戳+短hash的唯一标识符"""
    cmd_string = ' '.join(str(arg) for arg in args)
    timestamp = str(time.time_ns())
    random_num = str(random.randint(100000, 999999))
    pid = str(os.getpid())
    combined = f"{cmd_string}_{timestamp}_{random_num}_{pid}"
    
    # 生成时间戳部分（格式：YYYYMMDD_HHMMSS）
    import datetime
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    
    # 使用 SHA256 生成哈希并截取前8位
    hash_part = hashlib.sha256(combined.encode()).hexdigest()[:8]
    
    return f"{timestamp_str}_{hash_part}"

def get_script_dir():
    """获取脚本所在目录"""
    return Path(__file__).parent.absolute()

def generate_output_file(identifier):
    """基于标识符生成输出文件路径"""
    script_dir = get_script_dir()
    output_dir = script_dir / "RUN_DATA"
    output_dir.mkdir(exist_ok=True)
    return output_dir / f"run_{identifier}.json"

def get_output_file_path(identifier):
    """获取输出文件路径（别名函数，用于测试兼容性）"""
    return str(generate_output_file(identifier))

def create_json_output(success=True, message="", command="", output="", error="", run_identifier=""):
    """创建标准的JSON输出格式"""
    import datetime
    return {
        'success': success,
        'message': message,
        'command': command,
        'output': output,
        'error': error,
        'run_identifier': run_identifier,
        'timestamp': datetime.datetime.now().isoformat()
    }

def write_json_output(data, output_file):
    """写入JSON数据到输出文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing JSON output: {e}", file=sys.stderr)
        return False

def wrap_command(command, *args):
    """包装命令执行"""
    script_dir = get_script_dir()
    
    # 生成唯一标识符和输出文件
    run_identifier = generate_run_identifier(command, *args)
    output_file = generate_output_file(run_identifier)
    
    # 设置环境变量
    env = os.environ.copy()
    env[f'RUN_IDENTIFIER_{run_identifier}'] = 'True'
    env[f'RUN_DATA_FILE_{run_identifier}'] = str(output_file)
    env['RUN_DATA_FILE'] = str(output_file)  # 保持向后兼容
    
    # 构建完整的命令路径
    full_command = script_dir / command
    
    # 首先检查是否是别名 - 需要加载shell配置
    # 尝试多种方式检查别名
    shell_configs = [
        'source ~/.bashrc 2>/dev/null || true; source ~/.bash_profile 2>/dev/null || true; source ~/.profile 2>/dev/null || true',
        'source ~/.zshrc 2>/dev/null || true'
    ]
    
    is_alias = False
    actual_command = None
    
    # 使用交互式bash检查别名
    alias_check = subprocess.run(
        ['bash', '-i', '-c', f'type {command} 2>/dev/null'],
        capture_output=True,
        text=True,
        env=env
    )
    
    if alias_check.returncode == 0 and 'aliased to' in alias_check.stdout:
        is_alias = True
        # 获取别名的实际命令
        alias_cmd = subprocess.run(
            ['bash', '-i', '-c', f'alias {command} 2>/dev/null'],
            capture_output=True,
            text=True,
            env=env
        )
        
        if alias_cmd.returncode == 0 and '=' in alias_cmd.stdout:
            actual_command = alias_cmd.stdout.strip().split('=', 1)[1].strip("'\"")
        else:
            # 从type输出中解析
            # 输出格式：GDS is aliased to `GOOGLE_DRIVE --shell'
            if 'aliased to' in alias_check.stdout:
                parts = alias_check.stdout.split('aliased to')
                if len(parts) > 1:
                    actual_command = parts[1].strip().strip('`\'\"')
    
    # 检查命令是否存在（文件或别名）
    if not full_command.exists() and not is_alias:
        data = {
            'success': False,
            'error': f'Command not found: {full_command}'
        }
        write_json_output(data, output_file)
        return str(output_file), 1
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        if is_alias:
            # 如果是别名，使用shell执行
            if actual_command:
                # 对于别名命令，不传递run_identifier作为参数
                # 而是通过环境变量传递
                if args:
                    full_shell_cmd = f"{actual_command} {' '.join(args)}"
                else:
                    full_shell_cmd = actual_command
                
                # 使用shell执行别名命令
                result = subprocess.run(
                    full_shell_cmd,
                    shell=True,
                    env=env,
                    capture_output=True,
                    text=True
                )
            else:
                # 如果解析失败，回退到直接执行
                cmd_args = [str(full_command), run_identifier] + list(args)
                result = subprocess.run(
                    cmd_args,
                    env=env,
                    capture_output=True,
                    text=True
                )
        else:
            # 不是别名，直接执行
            cmd_args = [str(full_command), run_identifier] + list(args)
            result = subprocess.run(
                cmd_args,
                env=env,
                capture_output=True,
                text=True
            )
        
        exit_code = result.returncode
        stdout_output = result.stdout.strip()
        stderr_output = result.stderr.strip()
        
        # 如果有stderr输出，打印到终端
        if stderr_output:
            print(stderr_output, file=sys.stderr)
            
    except Exception as e:
        exit_code = 1
        data = {
            'success': False,
            'error': f'Command execution failed: {str(e)}'
        }
        write_json_output(data, output_file)
        return str(output_file), exit_code

    # 计算执行时间
    end_time = time.time()
    duration = int(end_time - start_time)
    
    # 检查被调用的命令是否已经创建了输出文件
    if not output_file.exists():
        # 如果命令没有创建输出文件，尝试解析stdout作为JSON
        if stdout_output:
            try:
                # 尝试解析stdout为JSON
                data = json.loads(stdout_output)
            except json.JSONDecodeError:
                # 如果不是JSON，创建一个包含输出的结构
                if exit_code == 0:
                    data = {
                        'success': True,
                        'message': 'Command executed successfully',
                        'output': stdout_output
                    }
                else:
                    data = {
                        'success': False,
                        'error': 'Command execution failed',
                        'output': stdout_output
                    }
        else:
            # 如果没有stdout输出，创建默认结果
            if exit_code == 0:
                data = {
                    'success': True,
                    'message': 'Command executed successfully'
                }
            else:
                data = {
                    'success': False,
                    'error': 'Command execution failed'
                }
        write_json_output(data, output_file)
    else:
        # 如果命令已经创建了输出文件，保持原样
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {'success': False, 'error': 'Failed to read command output'}
        
        write_json_output(data, output_file)
    
    # 清除运行标识符
    try:
        if f'RUN_IDENTIFIER_{run_identifier}' in os.environ:
            del os.environ[f'RUN_IDENTIFIER_{run_identifier}']
    except:
        pass  # 忽略清除失败
    
    return str(output_file), exit_code

def parse_arguments(args_list):
    """解析命令行参数"""
    show_output = False
    args = args_list[:]
    
    # 检查 --help 参数
    if args and args[0] in ['--help', '-h']:
        return {'help': True, 'show': False, 'command': None, 'args': []}
    
    # 解析 --show 参数
    if args and args[0] == '--show':
        show_output = True
        args = args[1:]
    
    if not args:
        return {'help': True, 'show': show_output, 'command': None, 'args': []}
    
    command = args[0]
    command_args = args[1:] if len(args) > 1 else []
    
    return {
        'help': False,
        'show': show_output,
        'command': command,
        'args': command_args
    }

def show_help():
    """显示帮助信息"""
    print(f"""
RUN - Universal Command Wrapper

Usage:
    RUN [--show] <command> [args...]
    RUN --help

Options:
    --show      Show JSON output directly to terminal
    --help      Show this help message

Examples:
    RUN OVERLEAF document.tex
    RUN --show SEARCH_PAPER "machine learning"
    RUN GOOGLE_DRIVE --shell ls

Description:
    RUN executes bin tools and captures their output in JSON format.
    Each execution generates a unique identifier and stores results
    in the RUN_DATA directory.
    """)

def main():
    """主函数"""
    args = sys.argv[1:]
    
    # 解析参数
    parsed = parse_arguments(args)
    
    if parsed['help']:
        show_help()
        return 0
    
    command = parsed['command']
    command_args = parsed['args']
    show_output = parsed['show']
    
    try:
        # 执行命令
        output_file, exit_code = wrap_command(command, *command_args)
        
        if show_output:
            # 读取并显示JSON输出
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"Error reading output file: {e}", file=sys.stderr)
                return 1
        
        return exit_code
        
    except KeyboardInterrupt:
        print(f"\nOperation cancelled", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"RUN error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main()) 