#!/usr/bin/env python3
"""
GDS bash命令生成测试
测试--return-command生成的bash命令语法正确性
排除特殊命令，避免本地路径解析问题
"""

import sys
import os
import subprocess
import json
import tempfile

# 添加父目录到路径以导入GOOGLE_DRIVE
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from GOOGLE_DRIVE import handle_shell_command

def get_test_commands():
    """
    获取测试命令列表 - 包含复杂引号转义和特殊字符的测试用例
    排除特殊命令: ls, cd, pwd, mkdir, rm, mv, cat, echo, grep, upload, download, edit, read, find, help, exit, quit
    重点测试引号转义、括号、方括号等容易出错的情况
    """
    
    # 特殊命令列表（需要排除）
    special_commands = {
        'ls', 'cd', 'pwd', 'mkdir', 'rm', 'mv', 'cat', 'echo', 'grep', 
        'upload', 'download', 'edit', 'read', 'find', 'help', 'exit', 'quit'
    }
    
    return [
        # 基础引号转义测试 (1-10)
        'python -c "print(\'Hello World\')"',
        'python -c "print(\"Hello World\")"',
        'python -c "import sys; print(f\"Python version: {sys.version}\")"',
        'python -c "data = {\'key\': \'value\'}; print(data)"',
        'python -c "import json; print(json.dumps({\'test\': True}))"',
        
        # 复杂引号嵌套测试 (11-15) - 这些是问题的根源
        'python -c "import subprocess; result = subprocess.run([\'ls\', \'-la\'], capture_output=True, text=True); print(result.stdout)"',
        'python -c "import subprocess; result = subprocess.run([\'python\', \'-c\', \'print(\\\"nested\\\")\'], capture_output=True, text=True); print(result.stdout)"',
        'python -c "print([1, 2, 3]); print({\'a\': [4, 5, 6]})"',
        'python -c "import os; print(f\'Current dir: {os.getcwd()}\')"',
        'python -c "text = \'String with \"quotes\" inside\'; print(text)"',
        
        # 括号和方括号测试 (16-20)
        'python -c "result = (1 + 2) * 3; print(f\'Result: {result}\')"',
        'python -c "data = [1, 2, 3]; print(data[0])"',
        'python -c "import sys; print(sys.argv[0] if len(sys.argv) > 0 else \'no args\')"',
        'python -c "func = lambda x: x * 2; print([func(i) for i in range(3)])"',
        'python -c "import re; match = re.search(r\'\\\\d+\', \'abc123def\'); print(match.group() if match else \'no match\')"',
        
        # 特殊字符和转义测试 (21-25)
        'python -c "print(\'Line 1\\\\nLine 2\\\\nLine 3\')"',
        'python -c "print(\'Tab\\\\tSeparated\\\\tValues\')"',
        'python -c "print(\'Path: /usr/bin/python3\')"',
        'python -c "import os; print(os.environ.get(\'HOME\', \'unknown\'))"',
        'python -c "import os; print(\'$HOME is:\', os.environ.get(\'HOME\', \'not set\'))"',
        
        # 复杂subprocess调用测试 (26-30) - 重点测试区域
        'python -c "import subprocess; proc = subprocess.run([\'echo\', \'hello\'], capture_output=True, text=True); print(\'Output:\', proc.stdout.strip())"',
        'python -c "import subprocess; proc = subprocess.run([\'date\', \'+%Y-%m-%d\'], capture_output=True, text=True); print(proc.stdout.strip())"',
        'python -c "import subprocess; proc = subprocess.run([\'whoami\'], capture_output=True, text=True); print(\'User:\', proc.stdout.strip())"',
        'python -c "import subprocess; proc = subprocess.run([\'pwd\'], capture_output=True, text=True); print(\'Dir:\', proc.stdout.strip())"',
        'python -c "import subprocess; proc = subprocess.run([\'python3\', \'-c\', \'print(\\\\\"nested command\\\\\")\'], capture_output=True, text=True); print(proc.stdout.strip())"',
        
        # JSON和数据结构测试 (31-35)
        'python -c "import json; data = {\'users\': [{\'name\': \'Alice\', \'age\': 30}, {\'name\': \'Bob\', \'age\': 25}]}; print(json.dumps(data, indent=2))"',
        'python -c "data = {\'nested\': {\'array\': [1, 2, {\'key\': \'value\'}]}}; print(data[\'nested\'][\'array\'][2][\'key\'])"',
        'python -c "import json; text = \'{\\\\\"test\\\\\\": \\\\\\"value with quotes\\\\\\"}\'; data = json.loads(text); print(data)"',
        'python -c "items = [\'item1\', \'item2\', \'item3\']; result = \', \'.join(f\'[{i}] {item}\' for i, item in enumerate(items)); print(result)"',
        'python -c "matrix = [[1, 2], [3, 4]]; print(\'Matrix:\'); [print(row) for row in matrix]"',
        
        # 文件操作模拟测试 (36-40)
        'python -c "import tempfile; import os; f = tempfile.NamedTemporaryFile(mode=\'w\', delete=False); f.write(\'test content\'); f.close(); print(f\'Created: {f.name}\'); os.unlink(f.name)"',
        'python -c "import io; buffer = io.StringIO(\'line1\\\\nline2\\\\nline3\'); lines = buffer.readlines(); print(f\'Read {len(lines)} lines\')"',
        'python -c "content = \'Hello\\\\nWorld\\\\n\'; lines = content.strip().split(\'\\\\n\'); print(f\'Lines: {lines}\')"',
        'python -c "import csv; import io; data = \'name,age\\\\nAlice,30\\\\nBob,25\'; reader = csv.DictReader(io.StringIO(data)); rows = list(reader); print(rows)"',
        'python -c "import hashlib; text = \'test string\'; hash_obj = hashlib.md5(text.encode()); print(f\'MD5: {hash_obj.hexdigest()}\')"',
        
        # 错误处理和异常测试 (41-45)
        'python -c "try: result = 1/0; except ZeroDivisionError as e: print(f\'Caught error: {e}\')"',
        'python -c "try: import nonexistent_module; except ImportError: print(\'Module not found\')"',
        'python -c "data = [1, 2, 3]; try: print(data[10]); except IndexError: print(\'Index out of range\')"',
        'python -c "try: result = int(\'not_a_number\'); except ValueError as e: print(f\'Conversion error: {e}\')"',
        'python -c "import sys; print(f\'Python {sys.version_info.major}.{sys.version_info.minor}\')"',
        
        # 复杂格式化和字符串操作 (46-50)
        'python -c "text = \'The quick brown fox jumps over the lazy dog\'; words = text.split(); print(f\'Words: {len(words)}, First: {words[0]}, Last: {words[-1]}\')"',
        'python -c "import datetime; now = datetime.datetime.now(); print(f\'Current time: {now.strftime(\\\\\"%Y-%m-%d %H:%M:%S\\\\\")}\')"',
        'python -c "data = {\'a\': 1, \'b\': 2, \'c\': 3}; result = [(k, v*2) for k, v in data.items()]; print(dict(result))"',
        'python -c "text = \'Hello, World!\'; encoded = text.encode(\'utf-8\'); decoded = encoded.decode(\'utf-8\'); print(f\'Original: {text}, Encoded bytes: {len(encoded)}, Decoded: {decoded}\')"',
        'python -c "import re; text = \'Contact: john@example.com and mary@test.org\'; emails = re.findall(r\'\\\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\\\.[A-Z|a-z]{2,}\\\\b\', text); print(f\'Found emails: {emails}\')"',
        
        # 特殊回归测试用例 (51-60) - 针对最近修复的问题
        # 这些测试用例专门测试在echo显示中容易出错的字符组合
        'python -c "import subprocess; result = subprocess.run([\'HUGGINGFACE\', \'--status\'], capture_output=True, text=True); print(\'Status:\', result.stdout.strip())"',
        'python -c "import subprocess; result = subprocess.run([\'echo\', \'(test)\'], capture_output=True, text=True); print(\'Result:\', result.stdout.strip())"',
        'python -c "import subprocess; result = subprocess.run([\'echo\', \'[array]\'], capture_output=True, text=True); print(\'Result:\', result.stdout.strip())"',
        'python -c "import subprocess; result = subprocess.run([\'echo\', \'{object}\'], capture_output=True, text=True); print(\'Result:\', result.stdout.strip())"',
        'python -c "data = {\'test\': [1, 2, (3, 4)]}; print(f\'Complex structure: {data}\')"',
        'python -c "import subprocess; result = subprocess.run([\'python\', \'-c\', \'print(\\\"(nested)[brackets]{braces}\\\")\'], capture_output=True, text=True); print(result.stdout.strip())"',
        'python -c "pattern = r\'\\\\([^)]+\\\\)\'; import re; matches = re.findall(pattern, \'test (match) string\'); print(matches)"',
        'python -c "import subprocess; cmd = [\'bash\', \'-c\', \'echo \\\"$((2+3))\\\"\']; result = subprocess.run(cmd, capture_output=True, text=True); print(result.stdout.strip())"',
        'python -c "nested = [[{\'key\': (1, 2)}], [{\'key\': [3, 4]}]]; print(f\'Nested: {nested[0][0][\\\"key\\\"]}\')"',
        'python -c "import subprocess; result = subprocess.run([\'echo\', \'Test with (parentheses) and [brackets] and {braces}\'], capture_output=True, text=True); print(result.stdout.strip())"',
    ]

def validate_bash_syntax_fast(command):
    """
    快速验证bash命令语法
    
    Args:
        command (str): 要验证的bash命令
        
    Returns:
        dict: 验证结果，包含success和error字段
    """
    try:
        # 创建临时文件存储命令
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\n')
            f.write(command)
            temp_file = f.name
        
        try:
            # 使用bash -n检查语法
            result = subprocess.run(
                ['bash', '-n', temp_file], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "Bash syntax is valid"}
            else:
                return {
                    "success": False, 
                    "error": f"Bash syntax error: {result.stderr.strip()}"
                }
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Bash syntax check timed out"}
    except Exception as e:
        return {"success": False, "error": f"Failed to validate bash syntax: {str(e)}"}

def run_gds_bash_test():
    """
    运行GDS bash命令生成测试
    重点测试引号转义和特殊字符处理
    """
    print("=" * 80)
    print("🧪 GDS Bash Command Generation Test")
    print("=" * 80)
    print("测试--return-command生成的bash命令语法正确性")
    print("重点关注引号转义、括号、方括号等特殊字符处理")
    print()
    
    test_commands = get_test_commands()
    total_tests = len(test_commands)
    passed_tests = 0
    failed_tests = []
    
    print(f"📋 总测试用例数: {total_tests}")
    print()
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"🔍 测试 {i:2d}/{total_tests}: {cmd[:60]}{'...' if len(cmd) > 60 else ''}")
        
        try:
            # 调用GDS获取生成的bash命令
            result = handle_shell_command(cmd, return_command_only=True)
            
            if not result.get("success", False):
                print(f"   ❌ GDS调用失败: {result.get('error', 'Unknown error')}")
                failed_tests.append({
                    "test_id": i,
                    "command": cmd,
                    "error_type": "GDS_CALL_FAILED",
                    "error": result.get("error", "Unknown error")
                })
                continue
            
            # 获取生成的远程命令
            remote_command = result.get("remote_command", "")
            if not remote_command:
                print(f"   ❌ 未获取到远程命令")
                failed_tests.append({
                    "test_id": i,
                    "command": cmd,
                    "error_type": "NO_REMOTE_COMMAND",
                    "error": "未获取到远程命令"
                })
                continue
            
            # 验证bash语法
            syntax_result = validate_bash_syntax_fast(remote_command)
            
            if syntax_result["success"]:
                print(f"   ✅ Bash语法正确")
                passed_tests += 1
            else:
                print(f"   ❌ Bash语法错误: {syntax_result['error']}")
                failed_tests.append({
                    "test_id": i,
                    "command": cmd,
                    "error_type": "BASH_SYNTAX_ERROR",
                    "error": syntax_result["error"],
                    "remote_command": remote_command[:200] + "..." if len(remote_command) > 200 else remote_command
                })
                
        except Exception as e:
            print(f"   ❌ 测试异常: {str(e)}")
            failed_tests.append({
                "test_id": i,
                "command": cmd,
                "error_type": "TEST_EXCEPTION",
                "error": str(e)
            })
    
    # 输出测试结果总结
    print()
    print("=" * 80)
    print("📊 测试结果总结")
    print("=" * 80)
    print(f"✅ 通过: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"❌ 失败: {len(failed_tests)}/{total_tests} ({len(failed_tests)/total_tests*100:.1f}%)")
    
    if failed_tests:
        print()
        print("🔍 失败用例详情:")
        print("-" * 80)
        
        # 按错误类型分组
        error_groups = {}
        for test in failed_tests:
            error_type = test["error_type"]
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(test)
        
        for error_type, tests in error_groups.items():
            print(f"\n📋 {error_type} ({len(tests)} 个用例):")
            for test in tests[:3]:  # 只显示前3个用例，避免输出过长
                print(f"   测试 {test['test_id']}: {test['command'][:50]}...")
                print(f"   错误: {test['error']}")
                if 'remote_command' in test:
                    print(f"   生成的命令: {test['remote_command'][:100]}...")
                print()
            
            if len(tests) > 3:
                print(f"   ... 还有 {len(tests) - 3} 个类似错误")
                print()
    
    # 返回测试结果
    return {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": len(failed_tests),
        "pass_rate": passed_tests / total_tests * 100,
        "failed_details": failed_tests
    }

if __name__ == "__main__":
    result = run_gds_bash_test()
    
    # 如果有失败的测试，以非零退出码退出
    if result["failed_tests"] > 0:
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过！")
        sys.exit(0) 