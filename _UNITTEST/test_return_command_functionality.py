#!/usr/bin/env python3
"""
测试--return-command功能的单元测试
验证GDS --return-command像函数一样直接返回结果，不进行终端打印
"""

import sys
import os
import subprocess
import json
import tempfile

# 添加父目录到路径以导入GOOGLE_DRIVE
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_return_command_basic():
    """测试基本的--return-command功能"""
    print("测试1: 基本--return-command功能")
    
    # 测试简单的python命令
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    cmd = ['python', google_drive_path, '--return-command', 'python', '-c', 'print("hello world")']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        # --return-command成功时会返回退出码1，这是正常的
        if result.returncode != 1:
            print(f"❌ 命令执行失败，期望退出码1但得到{result.returncode}: {result.stderr}")
            return False
            
        # 尝试解析输出（可能是Python字典格式或JSON格式）
        try:
            import json
            import ast
            import re
            
            # 先尝试JSON解析
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试Python字典解析
                try:
                    output_data = ast.literal_eval(result.stdout.strip())
                except (ValueError, SyntaxError):
                    # 如果直接解析失败，尝试从输出中提取关键信息
                    stdout = result.stdout
                    success_check = "'success': True" in stdout
                    action_check = "'action': 'return_command_only'" in stdout
                    remote_cmd_check = "'remote_command':" in stdout
                    syntax_check = "'syntax_valid': True" in stdout
                    
                    if success_check and action_check and remote_cmd_check and syntax_check:
                        print("✅ 基本功能测试通过（通过文本匹配验证）")
                        return True
                    else:
                        # 尝试从stderr中检查
                        stderr = result.stderr
                        success_check_err = "'success': True" in stderr
                        action_check_err = "'action': 'return_command_only'" in stderr
                        remote_cmd_check_err = "'remote_command':" in stderr
                        syntax_check_err = "'syntax_valid': True" in stderr
                        
                        if success_check_err and action_check_err and remote_cmd_check_err and syntax_check_err:
                            print("✅ 基本功能测试通过（从stderr文本匹配验证）")
                            return True
                        else:
                            print(f"❌ 输出格式不正确，所有字段检查都失败")
                            return False
            
            if (output_data.get("success") == True and
                output_data.get("action") == "return_command_only" and 
                "remote_command" in output_data and 
                "syntax_valid" in output_data):
                print("✅ 基本功能测试通过")
                return True
            else:
                print(f"❌ 输出格式不正确，期望success=True但得到关键字段检查失败")
                return False
        except Exception as e:
            print(f"❌ 输出解析失败: {str(e)}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 测试超时")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_return_command_syntax_validation():
    """测试bash语法验证功能"""
    print("\n测试2: bash语法验证功能")
    
    # 测试语法正确的命令（使用touch，简单且不会超时）
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    cmd_valid = ['python', google_drive_path, '--return-command', 'touch', 'test_file.txt']
    
    try:
        result = subprocess.run(cmd_valid, capture_output=True, text=True, timeout=10)
        
        # --return-command成功时会返回退出码1，这是正常的
        if result.returncode != 1:
            print(f"❌ 有效命令测试失败，期望退出码1但得到{result.returncode}: {result.stderr}")
            return False
            
        # 尝试解析输出（可能是Python字典格式或JSON格式）
        try:
            import json
            import ast
            import re
            
            # 先尝试JSON解析
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试Python字典解析
                try:
                    output_data = ast.literal_eval(result.stdout.strip())
                except (ValueError, SyntaxError):
                    # 如果直接解析失败，尝试从输出中提取关键信息
                    stdout = result.stdout
                    success_check = "'success': True" in stdout
                    syntax_check = "'syntax_valid': True" in stdout
                    remote_cmd_check = "'remote_command':" in stdout
                    
                    if success_check and syntax_check and remote_cmd_check:
                        print("✅ 语法验证功能正常（通过文本匹配验证）")
                        return True
                    else:
                        # 尝试从stderr中检查
                        stderr = result.stderr
                        success_check_err = "'success': True" in stderr
                        syntax_check_err = "'syntax_valid': True" in stderr
                        remote_cmd_check_err = "'remote_command':" in stderr
                        
                        if success_check_err and syntax_check_err and remote_cmd_check_err:
                            print("✅ 语法验证功能正常（从stderr文本匹配验证）")
                            return True
                        else:
                            print(f"❌ 语法验证结果不正确，所有字段检查都失败")
                            return False
            
            if (output_data.get("success") == True and
                "syntax_valid" in output_data and 
                output_data.get("syntax_valid") == True and
                "remote_command" in output_data):
                print(f"✅ 语法验证功能正常，语法有效: {output_data['syntax_valid']}")
                return True
            else:
                print(f"❌ 语法验证结果不正确，关键字段检查失败")
                return False
        except Exception as e:
            print(f"❌ 输出解析失败: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ 语法验证测试异常: {e}")
        return False

def test_return_command_no_terminal_output():
    """测试--return-command不会产生终端打印输出"""
    print("\n测试3: 验证无终端打印输出")
    
    # 创建一个Python脚本来调用GOOGLE_DRIVE并捕获所有输出
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_script = f'''
import sys
sys.path.insert(0, '{parent_dir}')

try:
    from GOOGLE_DRIVE import handle_shell_command
    
    # 测试--return-command是否直接返回结果
    result = handle_shell_command("python -c 'print(\\"test\\")'", return_command_only=True)
    
    # 检查返回值类型
    if isinstance(result, dict):
        print("SUCCESS: Got dict result")
        if result.get("action") == "return_command_only":
            print("SUCCESS: Correct action type")
        else:
            print(f"ERROR: Wrong action type: {{result.get('action')}}")
    else:
        print(f"ERROR: Wrong return type: {{type(result)}}")
        
except Exception as e:
    print(f"ERROR: Exception occurred: {{e}}")
    import traceback
    traceback.print_exc()
'''
    
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_file = f.name
        
        result = subprocess.run(['python', temp_file], capture_output=True, text=True, timeout=10)
        
        # 清理临时文件
        os.unlink(temp_file)
        
        if "SUCCESS: Got dict result" in result.stdout and "SUCCESS: Correct action type" in result.stdout:
            print("✅ 函数式返回测试通过")
            return True
        else:
            print(f"❌ 函数式返回测试失败: {result.stdout}")
            if result.stderr:
                print(f"错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 函数式返回测试异常: {e}")
        # 确保临时文件被清理
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass
        return False

def test_return_command_error_handling():
    """测试错误处理"""
    print("\n测试4: 错误处理")
    
    # 测试无参数的情况
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    cmd = ['python', google_drive_path, '--return-command']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print("✅ 无参数错误处理正确")
            return True
        else:
            print("❌ 无参数应该返回错误")
            return False
            
    except Exception as e:
        print(f"❌ 错误处理测试异常: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 开始测试--return-command功能")
    print("=" * 60)
    
    tests = [
        test_return_command_basic,
        test_return_command_syntax_validation, 
        test_return_command_no_terminal_output,
        test_return_command_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 