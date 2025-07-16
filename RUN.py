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

def generate_run_identifier(*args):
    """生成一个基于命令、时间戳和随机数的唯一标识符"""
    cmd_string = ' '.join(str(arg) for arg in args)
    timestamp = str(time.time_ns())
    random_num = str(random.randint(100000, 999999))
    pid = str(os.getpid())
    combined = f"{cmd_string}_{timestamp}_{random_num}_{pid}"
    
    # 使用 SHA256 生成哈希并截取前16位
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def get_script_dir():
    """获取脚本所在目录"""
    return Path(__file__).parent.absolute()

def generate_output_file(identifier):
    """基于标识符生成输出文件路径"""
    script_dir = get_script_dir()
    output_dir = script_dir / "RUN_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir / f"run_{identifier}.json"

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
    
    # 构建完整的命令路径
    full_command = script_dir / command
    
    # 检查命令是否存在
    if not full_command.exists():
        data = {
            'success': False,
            'error': f'Command not found: {full_command}',
            'command': command,
            'args': list(args),
            'run_identifier': run_identifier,
            'output_file': str(output_file)
        }
        write_json_output(data, output_file)
        return str(output_file), 1
    
    # 记录开始时间
    start_time = time.time()
    
    # 设置环境变量
    env = os.environ.copy()
    env['RUN_IDENTIFIER'] = run_identifier
    env['RUN_OUTPUT_FILE'] = str(output_file)
    env['RUN_COMMAND'] = command
    env['RUN_ARGS'] = ' '.join(args)
    
    try:
        # 执行命令
        result = subprocess.run(
            [str(full_command)] + list(args),
            env=env,
            capture_output=False,  # 让输出直接显示到终端
            text=True
        )
        exit_code = result.returncode
    except Exception as e:
        exit_code = 1
        data = {
            'success': False,
            'error': f'Command execution failed: {str(e)}',
            'command': command,
            'args': list(args),
            'run_identifier': run_identifier,
            'output_file': str(output_file)
        }
        write_json_output(data, output_file)
        return str(output_file), exit_code
    
    # 计算执行时间
    end_time = time.time()
    duration = int(end_time - start_time)
    
    # 检查被调用的命令是否已经创建了输出文件
    if not output_file.exists():
        # 如果命令没有创建输出文件，创建一个默认的
        if exit_code == 0:
            data = {
                'success': True,
                'message': 'Command executed successfully (no explicit output)',
                'command': command,
                'args': list(args),
                'run_identifier': run_identifier,
                'exit_code': exit_code,
                'duration': duration,
                'output_file': str(output_file)
            }
        else:
            data = {
                'success': False,
                'error': 'Command execution failed',
                'command': command,
                'args': list(args),
                'run_identifier': run_identifier,
                'exit_code': exit_code,
                'duration': duration,
                'output_file': str(output_file)
            }
        write_json_output(data, output_file)
    else:
        # 如果命令已经创建了输出文件，添加包装器信息
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {}
        
        # 添加包装器信息
        data.update({
            'command': command,
            'args': list(args),
            'run_identifier': run_identifier,
            'output_file': str(output_file),
            'duration': duration
        })
        
        write_json_output(data, output_file)
    
    return str(output_file), exit_code

def show_usage():
    """显示使用说明"""
    print("""Usage: RUN.py [--show] <command> [args...]

Options:
  --show    Display JSON output in terminal (also clears screen first)

Examples:
  RUN.py OVERLEAF document.tex
  RUN.py SEARCH_PAPER "3DGS" --max-results 3
  RUN.py --show SEARCH_PAPER "3DGS" --max-results 3
  RUN.py LEARN "python basics"
  RUN.py ALIAS ll "ls -la"
  RUN.py USERINPUT

The command returns a JSON file path containing the execution results.
Commands can write to the JSON output file via the RUN_OUTPUT_FILE environment variable.
Each execution gets a unique RUN_IDENTIFIER for isolation.
With --show flag, JSON results are also displayed in terminal.

Functions available for import:
  - generate_run_identifier(*args): Generate unique identifier
  - wrap_command(command, *args): Execute command with wrapper
""", file=sys.stderr)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_usage()
        return 1
    
    args = sys.argv[1:]
    show_output = False
    
    # 解析 --show 参数
    if args and args[0] == '--show':
        show_output = True
        args = args[1:]
    
    if not args:
        show_usage()
        return 1
    
    command = args[0]
    command_args = args[1:]
    
    # 执行命令
    output_file, exit_code = wrap_command(command, *command_args)
    
    # 如果使用了 --show 参数，显示JSON输出
    if show_output:
        # 清屏
        os.system('clear' if os.name == 'posix' else 'cls')
        
        # 显示JSON内容
        if Path(output_file).exists():
            print("=== RUN Command JSON Output ===")
            print(f"Command: {command} {' '.join(command_args)}")
            print(f"Output File: {output_file}")
            print("===============================")
            print()
            
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print(f"Error reading output file: {e}")
        else:
            print(f"Error: Output file not found: {output_file}")
    
    # 始终返回输出文件路径
    print(output_file)
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 