#!/usr/bin/env python3
"""
BACKGROUND_CMD - 安全的后台进程管理工具
支持创建、监控和管理后台进程，防止系统资源耗尽
"""

import os
import sys
import json
import time
import shlex
import signal
import psutil
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ProcessManager:
    """后台进程管理器"""
    
    def __init__(self, max_processes: int = 1000, log_dir: str = "~/tmp/background_cmd_logs"):
        self.max_processes = max_processes
        self.log_dir = Path(os.path.expanduser(log_dir))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 进程状态文件
        self.state_file = self.log_dir / "processes.json"
        self.processes: Dict[str, Dict] = {}
        
        # 加载现有进程状态
        self._load_state()
        
        # 清理已死亡的进程
        self._cleanup_dead_processes()
    
    def _load_state(self):
        """从文件加载进程状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.processes = data.get('processes', {})
            except (json.JSONDecodeError, FileNotFoundError):
                self.processes = {}
    
    def _save_state(self):
        """保存进程状态到文件"""
        data = {
            'processes': self.processes,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _cleanup_dead_processes(self):
        """清理已死亡的进程"""
        dead_pids = []
        for pid_str, proc_info in self.processes.items():
            try:
                pid = int(pid_str)
                # 检查进程是否还存在且创建时间匹配
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    if abs(proc.create_time() - proc_info['start_time']) < 1.0:
                        continue  # 进程仍然有效
                
                # 进程已死亡或PID被重用
                dead_pids.append(pid_str)
                
                # 清理日志文件（可选）
                log_file = Path(proc_info.get('log_file', ''))
                if log_file.exists() and log_file.stat().st_size == 0:
                    log_file.unlink(missing_ok=True)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                dead_pids.append(pid_str)
        
        # 移除死亡进程
        for pid_str in dead_pids:
            del self.processes[pid_str]
        
        if dead_pids:
            self._save_state()
    
    def _resolve_shell_aliases(self, command: str, shell: str) -> str:
        """解析shell别名"""
        if shell == 'zsh':
            # 使用交互式zsh来解析别名
            resolve_cmd = f'zsh -i -c "which {shlex.split(command)[0]} 2>/dev/null || echo {shlex.split(command)[0]}"'
        elif shell == 'bash':
            # 使用交互式bash来解析别名
            resolve_cmd = f'bash -i -c "which {shlex.split(command)[0]} 2>/dev/null || echo {shlex.split(command)[0]}"'
        else:
            return command
        
        try:
            result = subprocess.run(resolve_cmd, shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                resolved_cmd = result.stdout.strip()
                # 替换命令的第一部分
                cmd_parts = shlex.split(command)
                cmd_parts[0] = resolved_cmd
                return ' '.join(shlex.quote(part) for part in cmd_parts)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        return command
    
    def create_process(self, command: str, shell: str = 'zsh', 
                      resolve_aliases: bool = True) -> Optional[Tuple[int, str]]:
        """创建后台进程"""
        
        # 检查进程数量限制
        if len(self.processes) >= self.max_processes:
            print(f"Error: Maximum process limit reached ({self.max_processes})")
            return None
        
        # 清理死亡进程
        self._cleanup_dead_processes()
        
        # 解析别名
        if resolve_aliases:
            command = self._resolve_shell_aliases(command, shell)
        
        # 创建日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        log_filename = f"bg_cmd_{timestamp}.log"
        log_file = self.log_dir / log_filename
        
        try:
            # 根据shell类型创建进程
            if shell == 'zsh':
                shell_cmd = ['zsh', '-c', command]
            elif shell == 'bash':
                shell_cmd = ['bash', '-c', command]
            else:
                print(f"Error: Unsupported shell type: {shell}")
                return None
            
            # 创建新会话组，避免信号传播
            with open(log_file, 'w') as log_f:
                process = subprocess.Popen(
                    shell_cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid,  # 创建新会话组
                    cwd=os.getcwd(),
                    env=os.environ.copy()
                )
            
            # 获取进程信息
            psutil_proc = psutil.Process(process.pid)
            start_time = psutil_proc.create_time()
            
            # 记录进程信息
            self.processes[str(process.pid)] = {
                'command': command,
                'shell': shell,
                'start_time': start_time,
                'log_file': str(log_file),
                'cwd': os.getcwd(),
                'created_at': datetime.now().isoformat()
            }
            
            # 保存状态
            self._save_state()
            
            print(f"Process started: PID {process.pid}, Log: {log_file}")
            
            return process.pid, str(log_file)
            
        except Exception as e:
            print(f"Error: Failed to create process - {e}")
            # 清理可能创建的空日志文件
            if log_file.exists() and log_file.stat().st_size == 0:
                log_file.unlink(missing_ok=True)
            return None
    
    def list_processes(self) -> List[Dict]:
        """列出所有活跃进程"""
        self._cleanup_dead_processes()
        
        active_processes = []
        for pid_str, proc_info in self.processes.items():
            try:
                pid = int(pid_str)
                proc = psutil.Process(pid)
                
                # 获取当前状态
                status = proc.status()
                cpu_percent = proc.cpu_percent()
                memory_mb = proc.memory_info().rss / (1024 * 1024)
                
                # 计算运行时间
                start_time = datetime.fromtimestamp(proc_info['start_time'])
                runtime = datetime.now() - start_time
                
                active_processes.append({
                    'pid': pid,
                    'command': proc_info['command'],
                    'shell': proc_info['shell'],
                    'status': status,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'runtime': str(runtime).split('.')[0],  # 去掉微秒
                    'log_file': proc_info['log_file'],
                    'cwd': proc_info['cwd']
                })
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue
        
        return active_processes
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """终止指定进程"""
        pid_str = str(pid)
        
        if pid_str not in self.processes:
            print(f"Error: Process {pid} not in managed list")
            return False
        
        try:
            proc = psutil.Process(pid)
            
            if force:
                proc.kill()  # SIGKILL
                signal_type = "SIGKILL"
            else:
                proc.terminate()  # SIGTERM
                signal_type = "SIGTERM"
            
            print(f"Sent {signal_type} to process {pid}")
            
            # 等待进程结束
            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                if not force:
                    print(f"Process {pid} not responding to SIGTERM, trying SIGKILL...")
                    proc.kill()
                    proc.wait(timeout=3)
            
            # 从管理列表中移除
            del self.processes[pid_str]
            self._save_state()
            
            print(f"Process {pid} terminated")
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Error: Cannot terminate process {pid} - {e}")
            # 从管理列表中移除（进程可能已经死亡）
            if pid_str in self.processes:
                del self.processes[pid_str]
                self._save_state()
            return False
    
    def cleanup_all(self) -> int:
        """清理所有管理的进程"""
        count = 0
        pids = list(self.processes.keys())
        
        for pid_str in pids:
            if self.kill_process(int(pid_str)):
                count += 1
        
        return count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='BACKGROUND_CMD - 安全的后台进程管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  BACKGROUND_CMD "sleep 60"                    # 使用默认zsh运行命令
  BACKGROUND_CMD "ls -la" --shell bash         # 使用bash运行命令
  BACKGROUND_CMD --list                        # 列出所有活跃进程
  BACKGROUND_CMD --kill 12345                  # 终止指定进程
  BACKGROUND_CMD --cleanup                     # 清理所有进程
  BACKGROUND_CMD --max-processes 500           # 设置最大进程数
        """
    )
    
    # 位置参数 - 使用REMAINDER来捕获所有剩余参数
    parser.add_argument('command_args', nargs=argparse.REMAINDER, help='要在后台执行的命令')
    
    # 可选参数
    parser.add_argument('--shell', choices=['zsh', 'bash'], default='zsh',
                       help='使用的shell类型 (默认: zsh)')
    parser.add_argument('--max-processes', type=int, default=1000,
                       help='最大同时运行进程数 (默认: 1000)')
    parser.add_argument('--log-dir', default='~/tmp/background_cmd_logs',
                       help='日志文件目录 (默认: ~/tmp/background_cmd_logs)')
    parser.add_argument('--no-alias', action='store_true',
                       help='不解析shell别名')
    
    # 操作参数
    parser.add_argument('--list', action='store_true',
                       help='列出所有活跃的后台进程')
    parser.add_argument('--kill', type=int, metavar='PID',
                       help='终止指定PID的进程')
    parser.add_argument('--force-kill', type=int, metavar='PID',
                       help='强制终止指定PID的进程')
    parser.add_argument('--cleanup', action='store_true',
                       help='清理所有管理的后台进程')
    
    # JSON输出
    parser.add_argument('--json', action='store_true',
                       help='以JSON格式输出结果')
    
    args, unknown_args = parser.parse_known_args()
    
    # 创建进程管理器
    manager = ProcessManager(
        max_processes=args.max_processes,
        log_dir=args.log_dir
    )
    
    try:
        # 处理各种操作
        if args.list:
            processes = manager.list_processes()
            if args.json:
                print(json.dumps({
                    'success': True,
                    'processes': processes,
                    'total_count': len(processes)
                }, indent=2))
            else:
                if processes:
                    print(f"\nActive processes ({len(processes)}):")
                    print(f"-" * 80)
                    for proc in processes:
                        print(f"PID: {proc['pid']:<8} | "
                              f"Status: {proc['status']:<10} | "
                              f"CPU: {proc['cpu_percent']:>5.1f}% | "
                              f"Memory: {proc['memory_mb']:>6.1f}MB | "
                              f"Runtime: {proc['runtime']}")
                        print(f"Command: {proc['command']}")
                        print(f"Log: {proc['log_file']}")
                        print(f"-" * 80)
                else:
                    print(f"No active processes")
        
        elif args.kill is not None:
            success = manager.kill_process(args.kill)
            if args.json:
                print(json.dumps({'success': success, 'action': 'kill', 'pid': args.kill}))
        
        elif args.force_kill is not None:
            success = manager.kill_process(args.force_kill, force=True)
            if args.json:
                print(json.dumps({'success': success, 'action': 'force_kill', 'pid': args.force_kill}))
        
        elif args.cleanup:
            count = manager.cleanup_all()
            if args.json:
                print(json.dumps({'success': True, 'action': 'cleanup', 'killed_count': count}))
            else:
                print(f"Cleaned up {count} processes")
        
        elif args.command_args or unknown_args:
            # 合并command_args和unknown_args
            all_args = (args.command_args or []) + (unknown_args or [])
            if all_args:
                full_command = ' '.join(all_args)
            else:
                parser.print_help()
                return
                
            result = manager.create_process(
                full_command,
                shell=args.shell,
                resolve_aliases=not args.no_alias
            )
            
            if args.json:
                if result:
                    pid, log_file = result
                    print(json.dumps({
                        'success': True,
                        'action': 'create',
                        'pid': pid,
                        'log_file': log_file,
                        'command': full_command,
                        'shell': args.shell
                    }))
                else:
                    print(json.dumps({'success': False, 'action': 'create', 'error': 'Failed to create process'}))
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print(f"\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        if args.json:
            print(json.dumps({'success': False, 'error': str(e)}))
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
