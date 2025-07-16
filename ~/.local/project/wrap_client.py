#!/usr/bin/env python3
"""
WRAP Client - Python接口用于调用WRAP命令
提供简单的Python接口来调用包装的命令并获取JSON结果
"""

import subprocess
import json
import os
import sys
from pathlib import Path

class WrapClient:
    def __init__(self):
        self.wrap_command = os.path.expanduser("~/.local/bin/WRAP")
        
    def execute(self, command, *args):
        """
        执行包装的命令并返回JSON结果
        
        Args:
            command (str): 要执行的命令名称
            *args: 命令参数
            
        Returns:
            dict: 包含执行结果的JSON对象
        """
        try:
            # 构建命令
            cmd = [self.wrap_command, command] + list(args)
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            # 获取输出文件路径
            output_file_path = result.stdout.strip()
            
            if not output_file_path or not os.path.exists(output_file_path):
                return {
                    "success": False,
                    "error": f"Output file not found: {output_file_path}",
                    "command": command,
                    "args": list(args),
                    "stderr": result.stderr
                }
            
            # 读取JSON结果
            try:
                with open(output_file_path, 'r', encoding='utf-8') as f:
                    json_result = json.load(f)
                return json_result
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON in output file: {str(e)}",
                    "command": command,
                    "args": list(args),
                    "output_file": output_file_path
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error reading output file: {str(e)}",
                    "command": command,
                    "args": list(args),
                    "output_file": output_file_path
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command execution timeout (10 minutes)",
                "command": command,
                "args": list(args)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "command": command,
                "args": list(args)
            }
    
    def overleaf(self, tex_file=None):
        """编译LaTeX文件"""
        if tex_file:
            return self.execute("OVERLEAF", tex_file)
        else:
            return self.execute("OVERLEAF")
    
    def paper_search(self, query):
        """搜索论文"""
        return self.execute("PAPER_SEARCH", query)
    
    def learn(self, topic):
        """学习主题"""
        return self.execute("LEARN", topic)
    
    def alias(self, name, command):
        """创建别名"""
        return self.execute("ALIAS", name, command)

def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("Usage: wrap_client.py <command> [args...]", file=sys.stderr)
        print("Commands: OVERLEAF, PAPER_SEARCH, LEARN, ALIAS", file=sys.stderr)
        sys.exit(1)
    
    client = WrapClient()
    command = sys.argv[1]
    args = sys.argv[2:]
    
    result = client.execute(command, *args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    sys.exit(0 if result.get("success", False) else 1)

if __name__ == "__main__":
    main() 