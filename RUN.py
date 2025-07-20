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
    
    # 构建完整的命令路径
    full_command = script_dir / command
    
    # 检查命令是否存在
    if not full_command.exists():
        data = {
            'success': False,
            'error': f'Command not found: {full_command}'
        }
        write_json_output(data, output_file)
        return str(output_file), 1
    
    # 记录开始时间
    start_time = time.time()
    
    # 设置环境变量
    env = os.environ.copy()
    env[f'RUN_IDENTIFIER_{run_identifier}'] = 'True'
    env[f'RUN_DATA_FILE_{run_identifier}'] = str(output_file)
    env['RUN_DATA_FILE'] = str(output_file)  # 保持向后兼容
    
    try:
        # 执行命令，传递identifier作为第一个参数
        cmd_args = [str(full_command), run_identifier] + list(args)
        result = subprocess.run(
            cmd_args,
            env=env,
            capture_output=True,  # 捕获输出
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
        return {'help': False, 'show': show_output, 'command': None, 'args': []}
    
    command = args[0]
    command_args = args[1:]
    
    return {
        'help': False,
        'show': show_output,
        'command': command,
        'args': command_args
    }

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
Commands can write to the JSON output file via the RUN_DATA_FILE environment variable.
Each execution gets a unique RUN_IDENTIFIER for isolation.
With --show flag, JSON results are also displayed in terminal.

Functions available for import:
  - generate_run_identifier(*args): Generate unique identifier
  - wrap_command(command, *args): Execute command with wrapper
""")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_usage()
        return 1
    
    args = sys.argv[1:]
    show_output = False
    
    # 检查 --help 参数
    if args and args[0] in ['--help', '-h']:
        show_usage()
        return 0
    
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
    
    # 如果使用了 --show 参数，显示JSON输出并包含文件路径
    if show_output:
        # 不清屏，避免输出被截断
        # os.system('clear' if os.name == 'posix' else 'cls')
        
        # 显示JSON内容
        if Path(output_file).exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 将输出文件路径添加到JSON数据中
                data['_RUN_DATA_file'] = output_file
                
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                error_data = {
                    "success": False,
                    "error": f"Error reading output file: {e}",
                    "RUN_DATA_file": output_file
                }
                print(json.dumps(error_data, indent=2, ensure_ascii=False))
        else:
            error_data = {
                "success": False,
                "error": f"Output file not found: {output_file}",
                "RUN_DATA_file": output_file
            }
            print(json.dumps(error_data, indent=2, ensure_ascii=False))
    else:
        # 非show模式下，仍然输出文件路径（保持向后兼容）
        print(output_file)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main()) 