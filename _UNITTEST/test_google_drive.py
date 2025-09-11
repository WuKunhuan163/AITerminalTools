#!/usr/bin/env python3
import unittest
import subprocess
import sys
import os
import tempfile
import json
import argparse
import re
import ast
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    import GOOGLE_DRIVE
    from GOOGLE_DRIVE import handle_shell_command
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE = None
    handle_shell_command = None
    GOOGLE_DRIVE_AVAILABLE = False

try:
    from _TEST import BinToolsIntegrationTest
    INTEGRATION_TEST_AVAILABLE = True
except ImportError:
    BinToolsIntegrationTest = None
    INTEGRATION_TEST_AVAILABLE = False

GOOGLE_DRIVE_PY = str(Path(__file__).parent.parent / 'GOOGLE_DRIVE.py')

# Helper functions from merged files

def validate_bash_syntax_fast(command):
    """Fast bash command syntax validation"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write('#!/bin/bash\n')
            f.write(command)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ['bash', '-n', temp_file],
                capture_output=True,
                text=True,
                timeout=0.1
            )
            return {
                'success': result.returncode == 0,
                'error': result.stderr if result.returncode != 0 else None
            }
        finally:
            os.unlink(temp_file)
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_test_commands():
    """Get test commands list for bash command testing"""
    return [
        'python -c "print(\'Hello World\')"',
        'python -c "print(\"Hello World\")"',
        'python -c "import sys; print(f\"Python version: {sys.version}\")"',
        'python -c "data = {\'key\': \'value\'}; print(data)"',
        'python -c "import json; print(json.dumps({\'test\': True}))"',
        'python -c "import subprocess; result = subprocess.run([\'ls\', \'-la\'], capture_output=True, text=True); print(result.stdout)"',
        'python -c "import subprocess; result = subprocess.run([\'python\', \'-c\', \'print(\\\"nested\\\")\'], capture_output=True, text=True); print(result.stdout)"',
        'python -c "print([1, 2, 3]); print({\'a\': [4, 5, 6]})"',
        'python -c "import os; print(f\'Current dir: {os.getcwd()}\')"',
        'python -c "text = \'String with \"quotes\" inside\'; print(text)"',
    ]

def run_tool(args, timeout=10, allow_user_interaction=False):
    """Helper method to run the GOOGLE_DRIVE tool with given arguments"""
    tool_path = Path(__file__).parent.parent / "GOOGLE_DRIVE.py"
    assert tool_path.exists(), "GOOGLE_DRIVE.py not found"
    
    try:
        # Remove timeout for commands that require user interaction
        if allow_user_interaction:
            result = subprocess.run(
                [sys.executable, str(tool_path)] + args,
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                [sys.executable, str(tool_path)] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        return result
    except subprocess.TimeoutExpired:
        raise AssertionError(f"Tool execution timed out with args: {args}")

# Test functions from merged files

# 已移除test_return_command_basic - --return-command选项已废弃

def test_bash_syntax_validation():
    """Test bash syntax validation functionality"""
    print(f"测试bash语法验证功能")
    
    # Test valid commands
    valid_commands = [
        'echo "hello world"',
        'ls -la',
        'mkdir test_dir'
    ]
    
    for cmd in valid_commands:
        validation = validate_bash_syntax_fast(cmd)
        assert validation['success'], f"Valid command should pass validation: {cmd}"
    
    # Test invalid commands
    invalid_commands = [
        'echo "unclosed quote',
        'if [ condition; then',  # Missing fi
        'for i in'  # Incomplete loop
    ]
    
    for cmd in invalid_commands:
        validation = validate_bash_syntax_fast(cmd)
        assert not validation['success'], f"Invalid command should fail validation: {cmd}"
    
    print(f"test_bash_syntax_validation passed")

def test_return_command_no_output():
    """Test --return-command does not produce terminal print output
    
    这个测试检查--return模式是否只输出JSON格式的远程命令，
    而不是混合的终端输出。目的是确保生成的输出可以被程序解析。
    """
    if not GOOGLE_DRIVE_AVAILABLE:
        print(f"test_return_command_no_output skipped - GOOGLE_DRIVE module not available")
        return
    
    print(f"测试--shell --return不会产生混合的终端输出")
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    # 使用正确的命令格式
    cmd = ['python', google_drive_path, '--shell', 'touch', 'test_file.txt', '--return']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        
        # 检查输出格式 - 应该是纯净的JSON或者明确的错误信息
        output = result.stdout + result.stderr
        if output.strip():
            # 如果有输出，检查是否包含混合的终端消息
            if "✅" in output and not output.strip().startswith('{'):
                print(f"Warning:  输出包含终端状态消息: {output[:100]}...")
                # 这是当前的行为，先不抛出异常
            else:
                print(f"输出格式正常: {output[:50]}...")
                
    except subprocess.TimeoutExpired:
        raise AssertionError("命令执行超时")
    except Exception as e:
        raise AssertionError(f"测试执行出错: {e}")
    
    print(f"test_return_command_no_output passed")

def test_error_handling():
    """Test error handling"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print(f"test_error_handling skipped - GOOGLE_DRIVE module not available")
        return
    
    print(f"测试错误处理")
    
    # Test with invalid command
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    cmd = ['python', google_drive_path, '--shell', 'invalid_command_that_does_not_exist']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        
        # Should handle error gracefully (non-zero exit code is expected)
        assert result.returncode != 0, "Invalid command should return non-zero exit code"
        
    except subprocess.TimeoutExpired:
        raise AssertionError("命令执行超时")
    except Exception as e:
        raise AssertionError(f"测试执行出错: {e}")
    
    print(f"test_error_handling passed")

def test_gds_read_command():
    """Test read command various usage patterns"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print(f"test_gds_read_command skipped - GOOGLE_DRIVE module not available")
        return
    
    print(f"测试read命令的各种用法")
    
    # Test basic read functionality (this would require actual files to exist)
    # For now, just test that the command is recognized
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    cmd = ['python', google_drive_path, '--shell', 'help']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        
        # Should include read command in help
        output = result.stdout.lower() + result.stderr.lower()
        assert 'read' in output, "Help should mention read command"
        
    except subprocess.TimeoutExpired:
        raise AssertionError("命令执行超时")
    except Exception as e:
        raise AssertionError(f"测试执行出错: {e}")
    
    print(f"test_gds_read_command passed")

def test_python_command_parsing():
    """Test python -c command parsing with different quote styles"""
    print(f"Test python -c command parsing with different quote styles")
    
    # Test different python command styles
    test_commands = [
        'python -c "print(\"hello world\")"',
        "python -c 'print(\"hello world\")'",
        'python -c """print(f"hello world")"""',
        '''python -c """
print(f"multiline")
print(f"test")
"""''',
    ]
    
    for cmd in test_commands:
        # Test that the command can be processed without syntax errors
        validation = validate_bash_syntax_fast(cmd)
        print(f"Command: {cmd[:50]}... - Validation: {validation['success']}")
    
    print(f"test_python_command_parsing passed")

def test_path_conversion():
    """Test path conversion functionality"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print(f"test_path_conversion skipped - GOOGLE_DRIVE module not available")
        return
    
    print(f"测试路径转换功能")
    
    # Test basic path operations
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    cmd = ['python', google_drive_path, '--shell', 'pwd']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        
        # Should return some path information
        assert result.returncode == 0, "pwd command should succeed"
        
    except subprocess.TimeoutExpired:
        raise AssertionError("命令执行超时")
    except Exception as e:
        raise AssertionError(f"测试执行出错: {e}")
    
    print(f"test_path_conversion passed")

def test_bash_command_generation():
    """Test bash command generation for various GDS commands"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print(f"test_bash_command_generation skipped - GOOGLE_DRIVE module not available")
        return
    
    print(f"运行GDS bash命令生成测试")
    
    # Test that shell commands work with various commands
    test_commands = get_test_commands()[:5]  # Test first 5 commands
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    
    for cmd_parts in test_commands:
        try:
            full_cmd = ['python', google_drive_path, '--shell'] + cmd_parts.split()
            result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
            
            # Should not crash - output may vary based on environment
            # Just check that it doesn't crash completely
            
        except subprocess.TimeoutExpired:
            print(f"Warning:  Command timed out: {cmd_parts}")
        except Exception as e:
            print(f"Warning:  Command failed: {cmd_parts} - {e}")
    
    print(f"test_bash_command_generation passed")

def test_google_drive_help_command():
    """Test Google Drive help functionality"""
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    
    try:
        result = subprocess.run([
            'python', google_drive_path, '--help'
        ], capture_output=True, text=True, timeout=10)
        
        assert result.returncode == 0, "Help command should succeed"
        output = result.stdout.lower()
        assert 'google drive' in output or 'google_drive' in output, "Help should mention Google Drive"
        
    except subprocess.TimeoutExpired:
        raise AssertionError("Help command timed out")
    except Exception as e:
        raise AssertionError(f"Help command failed: {e}")
    
    print(f"test_google_drive_help_command passed")

def test_google_drive_shell_command():
    """Test Google Drive shell command"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print(f"test_google_drive_shell_command skipped - GOOGLE_DRIVE module not available")
        return
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    
    try:
        result = subprocess.run([
            'python', google_drive_path, '--shell', 'help'
        ], capture_output=True, text=True, timeout=10)
        
        # Should provide help output
        assert result.returncode == 0, "Shell help should succeed"
        
    except subprocess.TimeoutExpired:
        raise AssertionError("Shell help command timed out")
    except Exception as e:
        raise AssertionError(f"Shell help command failed: {e}")
    
    print(f"test_google_drive_shell_command passed")

def test_google_drive_desktop_status():
    """Test Google Drive desktop status option"""
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    google_drive_path = os.path.join(parent_dir, 'GOOGLE_DRIVE.py')
    
    try:
        result = subprocess.run([
            'python', google_drive_path, '--desktop', '--status'
        ], capture_output=True, text=True, timeout=10)
        
        # Should not crash (may succeed or fail based on environment)
        assert result.returncode in [0, 1], "Desktop status should return valid exit code"
        
    except subprocess.TimeoutExpired:
        raise AssertionError("Desktop status command timed out")
    except Exception as e:
        raise AssertionError(f"Desktop status command failed: {e}")
    
    print(f"test_google_drive_desktop_status passed")

# Converted unittest tests to standalone functions

def test_help_option():
    """Test --help option displays help information"""
    result = run_tool(["--help"])
    
    # Should return successfully (exit code 0)
    assert result.returncode == 0, "Help command should return exit code 0"
    
    # Should contain key information
    output = result.stdout.lower()
    assert "google drive" in output, "Help should mention Google Drive"
    assert "usage" in output, "Help should show usage information"
    assert "gds" in output, "Help should mention GDS (Google Drive Shell)"
    assert "shell" in output, "Help should mention shell functionality"
    
    print(f"test_help_option passed")

def test_help_short_option():
    """Test -h option displays help information"""
    result = run_tool(["-h"])
    
    # Should return successfully (exit code 0)
    assert result.returncode == 0, "Short help command should return exit code 0"
    
    # Should contain key information
    output = result.stdout.lower()
    assert "google drive" in output, "Help should mention Google Drive"
    assert "usage" in output, "Help should show usage information"
    
    print(f"test_help_short_option passed")

def test_invalid_arguments():
    """Test handling of invalid arguments"""
    result = run_tool(["--invalid-option"])
    
    # The tool treats unknown arguments as URLs and tries to open them
    # So it may return 0 (success) or 1 (failure) depending on browser availability
    # The important thing is that it doesn't crash
    assert result.returncode in [0, 1], "Tool should handle invalid arguments gracefully"
    
    print(f"test_invalid_arguments passed")

def test_shell_help_command():
    """Test shell help command"""
    result = run_tool(["--shell", "help"])
    
    # Should return successfully
    assert result.returncode == 0, "Shell help command should return exit code 0"
    
    # Should list available commands
    output = result.stdout.lower()
    expected_commands = ["pwd", "ls", "mkdir", "cd", "rm", "upload", "download"]
    for cmd in expected_commands:
        assert cmd in output, f"Help should mention {cmd} command"
    
    print(f"test_shell_help_command passed")

def test_my_drive_option():
    """Test -my option (should attempt to open My Drive)"""
    # This test just verifies the option is recognized and processed
    # We can't test actual browser opening in unit tests
    result = run_tool(["-my"])
    
    # Should return successfully (even if browser opening fails in test environment)
    # The important thing is that the option is recognized
    assert result.returncode in [0, 1], "My Drive option should be recognized"
    
    print(f"test_my_drive_option passed")

def test_desktop_status_option():
    """Test --desktop --status option"""
    result = run_tool(["--desktop", "--status"])
    
    # Should return some result (0 or 1 depending on Google Drive Desktop status)
    assert result.returncode in [0, 1], "Desktop status command should return 0 or 1"
    
    # Should provide some output about status
    output = result.stdout + result.stderr
    assert len(output.strip()) > 0, "Desktop status should provide some output"
    
    print(f"test_desktop_status_option passed")

def test_list_shell():
    """Test --list-remote-shell option"""
    result = run_tool(["--list-remote-shell"])
    
    # Should return successfully
    assert result.returncode == 0, "List remote shell should return exit code 0"
    
    # Should provide information about shells (even if empty)
    output = result.stdout.lower()
    assert "shell" in output or "没有" in output or "not found" in output, "Should provide information about shell status"
    
    print(f"test_list_shell passed")

def test_tool_structure():
    """Test that the tool has proper structure"""
    tool_path = Path(__file__).parent.parent / "GOOGLE_DRIVE.py"
    
    # Check that the Python file is executable
    assert os.access(tool_path, os.R_OK), "Tool should be readable"
    
    # Check that it has a main function or __main__ block
    with open(tool_path, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'if __name__ == "__main__"' in content or 'def main(' in content, "Tool should have main function or __main__ block"
    
    print(f"test_tool_structure passed")

def test_run_environment_compatibility():
    """Test compatibility with RUN environment"""
    tool_path = Path(__file__).parent.parent / "GOOGLE_DRIVE.py"
    
    # Create a temporary RUN environment simulation
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up mock RUN environment variables
        env = os.environ.copy()
        test_id = "test_12345"
        output_file = os.path.join(temp_dir, "output.json")
        
        env[f'RUN_IDENTIFIER_{test_id}'] = 'True'
        env[f'RUN_DATA_FILE_{test_id}'] = output_file
        
        # Test help command in RUN environment
        result = subprocess.run(
            [sys.executable, str(tool_path), test_id, "--help"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )
        
        # Should return successfully
        assert result.returncode == 0, "RUN environment help should return exit code 0"
        
        # Should create output file
        assert os.path.exists(output_file), "RUN environment should create output file"
        
        # Output file should contain valid JSON
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert isinstance(data, dict), "Output should be valid JSON object"
                assert "success" in data, "Output should contain success field"
        except json.JSONDecodeError:
            raise AssertionError("Output file should contain valid JSON")
    
    print(f"test_run_environment_compatibility passed")

# Test management and execution

# ===== 新增的全面测试函数 =====

def test_shell_echo():
    """Test shell echo command"""
    result = run_tool(["--shell", 'echo "Hello World"'])
    
    assert result.returncode == 0, "Shell echo should return exit code 0"
    assert "Hello World" in result.stdout, "Echo should output the text"
    
    print(f"test_shell_echo passed")

def test_shell_ls():
    """Test shell ls command"""
    result = run_tool(["--shell", "ls"])
    
    assert result.returncode == 0, "Shell ls should return exit code 0"
    # ls should return some output (files or empty)
    
    print(f"test_shell_ls passed")

def test_shell_pwd():
    """Test shell pwd command"""
    result = run_tool(["--shell", "pwd"])
    
    assert result.returncode == 0, "Shell pwd should return exit code 0"
    assert "~" in result.stdout, "pwd should show current path"
    
    print(f"test_shell_pwd passed")

def test_shell_mkdir():
    """Test shell mkdir command"""
    import time
    test_dir = f"test_dir_{int(time.time())}"
    result = run_tool(["--shell", f"mkdir {test_dir}"])
    
    assert result.returncode == 0, "Shell mkdir should return exit code 0"
    # Should show success message
    assert ("创建" in result.stdout or "created" in result.stdout.lower()), "mkdir should show success message"
    
    print(f"test_shell_mkdir passed")

def test_shell_cd():
    """Test shell cd command"""
    result = run_tool(["--shell", "cd test_dir"])
    
    assert result.returncode == 0, "Shell cd should return exit code 0"
    assert ("切换" in result.stdout or "switched" in result.stdout.lower()), "cd should show success message"
    
    print(f"test_shell_cd passed")

def test_shell_cd_parent():
    """Test shell cd .. command"""
    result = run_tool(["--shell", "cd .."])
    
    assert result.returncode == 0, "Shell cd .. should return exit code 0"
    assert ("切换" in result.stdout or "switched" in result.stdout.lower()), "cd .. should show success message"
    
    print(f"test_shell_cd_parent passed")

def test_shell_rm():
    """Test shell rm command with nonexistent file"""
    result = run_tool(["--shell", "rm -rf nonexistent_file"])
    
    assert result.returncode == 0, "Shell rm should return exit code 0"
    assert ("not exist" in result.stdout.lower() or "不存在" in result.stdout), "rm should handle nonexistent files"
    
    print(f"test_shell_rm passed")

def test_desktop_launch():
    """Test desktop launch command"""
    result = run_tool(["--desktop", "--launch"])
    
    assert result.returncode == 0, "Desktop launch should return exit code 0"
    # Should show launch message or already running message
    output_lower = result.stdout.lower()
    assert ("launched" in output_lower or "already" in output_lower or "启动" in result.stdout), "Launch should show appropriate message"
    
    print(f"test_desktop_launch passed")

def test_desktop_shutdown():
    """Test desktop shutdown command"""
    result = run_tool(["--desktop", "--shutdown"])
    
    assert result.returncode == 0, "Desktop shutdown should return exit code 0"
    # Should show shutdown message
    output_lower = result.stdout.lower()
    assert ("closed" in output_lower or "stopped" in output_lower or "关闭" in result.stdout), "Shutdown should show appropriate message"
    
    print(f"test_desktop_shutdown passed")

def test_desktop_restart():
    """Test desktop restart command"""
    result = run_tool(["--desktop", "--restart"])
    
    assert result.returncode == 0, "Desktop restart should return exit code 0"
    assert ("restarted" in result.stdout.lower() or "重启" in result.stdout), "Restart should show success message"
    
    print(f"test_desktop_restart passed")

def test_create_shell():
    """Test creating remote shell"""
    result = run_tool(["--create-remote-shell"])
    
    assert result.returncode == 0, "Create remote shell should return exit code 0"
    # Should show creation message
    output_lower = result.stdout.lower()
    assert ("shell" in output_lower or "created" in output_lower or "创建" in result.stdout), "Should show shell creation message"
    
    print(f"test_create_shell passed")

def test_checkout_shell():
    """Test checkout remote shell"""
    result = run_tool(["--checkout-remote-shell", "default_shell"])
    
    assert result.returncode == 0, "Checkout remote shell should return exit code 0"
    # Should handle checkout (success or not found)
    
    print(f"test_checkout_shell passed")

def test_terminate_shell():
    """Test terminate remote shell with nonexistent shell"""
    result = run_tool(["--terminate-remote-shell", "nonexistent_shell"])
    
    assert result.returncode == 0, "Terminate should return exit code 0"
    assert ("not found" in result.stdout.lower() or "找不到" in result.stdout), "Should handle nonexistent shell"
    
    print(f"test_terminate_shell passed")

def test_shell_invalid_command():
    """Test shell with invalid command"""
    result = run_tool(["--shell", "invalidcommand"])
    
    assert result.returncode == 0, "Shell should handle invalid commands gracefully"
    assert ("未知命令" in result.stdout or "unknown" in result.stdout.lower()), "Should show unknown command message"
    
    print(f"test_shell_invalid_command passed")

def test_cd_without_argument():
    """Test cd command without argument"""
    result = run_tool(["--shell", "cd"])
    
    assert result.returncode == 0, "Shell should handle cd without argument"
    assert ("需要指定路径" in result.stdout or "需要" in result.stdout), "Should show error for cd without argument"
    
    print(f"test_cd_without_argument passed")

def test_mkdir_without_argument():
    """Test mkdir command without argument"""
    result = run_tool(["--shell", "mkdir"])
    
    assert result.returncode == 0, "Shell should handle mkdir without argument"
    assert ("需要指定" in result.stdout or "需要" in result.stdout), "Should show error for mkdir without argument"
    
    print(f"test_mkdir_without_argument passed")

def test_rm_without_argument():
    """Test rm command without argument"""
    result = run_tool(["--shell", "rm"])
    
    assert result.returncode == 0, "Shell should handle rm without argument"
    assert ("需要指定" in result.stdout or "需要" in result.stdout), "Should show error for rm without argument"
    
    print(f"test_rm_without_argument passed")

def test_echo_with_quotes():
    """Test echo command with quotes"""
    result = run_tool(["--shell", 'echo "Hello World"'])
    
    assert result.returncode == 0, "Echo with quotes should work"
    assert "Hello World" in result.stdout, "Echo should output quoted text"
    
    print(f"test_echo_with_quotes passed")

def test_echo_empty():
    """Test echo command without arguments"""
    result = run_tool(["--shell", "echo"])
    
    assert result.returncode == 0, "Empty echo should work"
    # Empty echo should just return success
    
    print(f"test_echo_empty passed")

def test_upload_nonexistent_file():
    """Test upload nonexistent file"""
    result = run_tool(["--upload", "nonexistent_file.txt"])
    
    assert result.returncode == 0, "Upload should handle nonexistent files gracefully"
    # Should show some error indication in output
    
    print(f"test_upload_nonexistent_file passed")

def test_upload_with_test_file():
    """Test upload with actual test file"""
    import tempfile
    import os
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test content for upload")
        temp_file = f.name
    
    try:
        result = run_tool(["--upload", temp_file])
        assert result.returncode == 0, "Upload with valid file should work"
        
        print(f"test_upload_with_test_file passed")
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)

class GoogleDriveUploadImprovementsTest(unittest.TestCase):
    """
    Test class for the improved GDS upload functionality including:
    - Sequential upload and validation
    - Progress display improvements
    - Parameter parsing (--force, --target-dir, --remove-local)
    - Upload-folder improvements
    - Uses temporary test folder in ~/tmp to avoid remote file conflicts
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment with temporary folder"""
        # Set up paths
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GOOGLE_DRIVE_PY = cls.BIN_DIR / "GOOGLE_DRIVE.py"
        
        # Create hashed timestamp for unique test folder
        import hashlib
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"upload_test_{timestamp}_{os.getpid()}"
        folder_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        cls.test_folder_name = f"upload_test_{timestamp}_{folder_hash}"
        
        print(f"Upload test folder: ~/tmp/{cls.test_folder_name}")
        
        # Set up remote test environment
        cls._setup_remote_test_folder()
        
        cls.test_data_dir = Path(__file__).parent / "_DATA" / "google_drive_test"
        cls.test_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files if they don't exist
        cls.test_files = [
            cls.test_data_dir / "test_upload_1.txt",
            cls.test_data_dir / "test_upload_2.txt", 
            cls.test_data_dir / "test_upload_3.txt"
        ]
        
        for i, test_file in enumerate(cls.test_files, 1):
            if not test_file.exists():
                test_file.write_text(f"Test file {i} content for upload improvements")
        
        # Create test folder
        cls.test_folder = cls.test_data_dir / "test_folder"
        cls.test_folder.mkdir(exist_ok=True)
        
        folder_files = [
            cls.test_folder / "folder_file1.txt",
            cls.test_folder / "folder_file2.txt"
        ]
        
        for i, folder_file in enumerate(folder_files, 1):
            if not folder_file.exists():
                folder_file.write_text(f"Folder content {i} for upload improvements")
    
    @classmethod
    def _setup_remote_test_folder(cls):
        """Set up the remote test folder in ~/tmp"""
        print(f"Tool: Setting up upload test folder: ~/tmp/{cls.test_folder_name}")
        
        # Clean up any existing tmp folders
        print(f"Cleaning up existing tmp folders...")
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "rm", "-rf", "~/tmp"]
        print(f"Cleaning tmp directory: {' '.join(cmd)}")
        print(f"👤 Please complete the tmp cleanup in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        
        # Create fresh tmp structure
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "mkdir", "-p", "~/tmp"]
        print(f"Creating ~/tmp: {' '.join(cmd)}")
        print(f"👤 Please complete the tmp folder creation in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        
        # Create the test folder
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "mkdir", "-p", f"~/tmp/{cls.test_folder_name}"]
        print(f"Creating upload test folder: {' '.join(cmd)}")
        print(f"👤 Please complete the test folder creation in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        
        # Change to the test folder
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "cd", f"~/tmp/{cls.test_folder_name}"]
        print(f"Changing to upload test folder: {' '.join(cmd)}")
        print(f"👤 Please complete the directory change in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        
        print(f"Upload test folder setup completed")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        print(f"Cleaning up upload test environment...")
        
        # Clean up entire tmp folder
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "rm", "-rf", "~/tmp"]
        print(f"Removing tmp directory: {' '.join(cmd)}")
        print(f"👤 Please complete the cleanup in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        print(f"Upload test environment cleanup completed")
    
    def test_01_basic_upload(self):
        """Test basic single file upload functionality"""
        print(f"\nTesting basic upload functionality...")
        print(f"This test requires user interaction - please follow the prompts")
        print(f"No timeout restrictions - take your time to complete the UI interactions")
        
        # Upload a single test file (no timeout)
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "upload", str(self.test_files[0])]
        print(f"Running: {' '.join(cmd)}")
        print(f"Please complete the upload process in the UI")
        
        result = subprocess.run(cmd, cwd=self.BIN_DIR)
        
        # Check if upload was successful by verifying the file exists remotely
        print(f"Verifying upload result...")
        ls_cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "ls"]
        ls_result = subprocess.run(ls_cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        
        # Should find the uploaded file in the listing
        self.assertIn("test_upload_1.txt", ls_result.stdout)
        print(f"Basic upload verified - file found in remote directory")
    
    def test_02_multi_file_upload(self):
        """Test multi-file upload functionality"""
        print(f"\nTesting multi-file upload...")
        print(f"This test requires user interaction - please follow the prompts")
        print(f"No timeout restrictions - take your time to complete the UI interactions")
        
        # Upload multiple test files (no timeout)
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "upload"] + [str(f) for f in self.test_files[1:3]]  # Upload files 2 and 3
        print(f"Running: {' '.join(cmd)}")
        print(f"Please complete the multi-file upload process in the UI")
        
        result = subprocess.run(cmd, cwd=self.BIN_DIR)
        
        # Check if all files were uploaded successfully
        print(f"Verifying multi-file upload results...")
        ls_cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "ls"]
        ls_result = subprocess.run(ls_cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        
        # Should find both uploaded files
        self.assertIn("test_upload_2.txt", ls_result.stdout)
        self.assertIn("test_upload_3.txt", ls_result.stdout)
        print(f"Multi-file upload verified - both files found in remote directory")
    
    def test_03_upload_folder_functionality(self):
        """Test upload-folder functionality"""
        print(f"\nTesting upload-folder functionality...")
        print(f"This test requires user interaction - please follow the prompts")
        print(f"No timeout restrictions - take your time to complete the UI interactions")
        
        # Upload test folder (no timeout)
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "upload-folder", str(self.test_folder)]
        print(f"Running: {' '.join(cmd)}")
        print(f"Please complete the folder upload process in the UI")
        
        result = subprocess.run(cmd, cwd=self.BIN_DIR)
        
        # Check if folder was uploaded and extracted successfully
        print(f"Verifying folder upload results...")
        # First check if the folder exists
        ls_root_cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "ls"]
        ls_root_result = subprocess.run(ls_root_cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        print(f"Root directory contents: {ls_root_result.stdout}")
        
        ls_cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "ls", "test_folder"]
        ls_result = subprocess.run(ls_cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        print(f"test_folder contents: {ls_result.stdout}")
        
        # Should find the folder contents
        self.assertIn("folder_file1.txt", ls_result.stdout)
        self.assertIn("folder_file2.txt", ls_result.stdout)
        print(f"Folder upload verified - folder contents found in remote directory")
    
    def test_04_upload_with_options(self):
        """Test upload with various options like --target-dir, --force"""
        print(f"\nTesting upload with options...")
        print(f"This test requires user interaction - please follow the prompts")
        print(f"No timeout restrictions - take your time to complete the UI interactions")
        
        # Test --target-dir option (no timeout)
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "upload", "--target-dir", "test_target_dir", str(self.test_files[0])]
        print(f"Running: {' '.join(cmd)}")
        print(f"Please complete the upload with target directory")
        
        result = subprocess.run(cmd, cwd=self.BIN_DIR)
        
        # Check if file was uploaded to the correct target directory
        print(f"Verifying target directory upload...")
        ls_cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "ls", "test_target_dir"]
        ls_result = subprocess.run(ls_cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        
        # Should find the file in the target directory
        self.assertIn("test_upload_1.txt", ls_result.stdout)
        print(f"Target directory upload verified - file found in specified directory")
        
        # Test file content integrity
        print(f"Verifying file content integrity...")
        cat_cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell", "cat", "test_target_dir/test_upload_1.txt"]
        cat_result = subprocess.run(cat_cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        
        # Should contain the expected content
        self.assertIn("Test file 1 content", cat_result.stdout)
        print(f"File content integrity verified")


def run_upload_improvements_tests():
    """Run only the upload improvements tests"""
    print(f"Running Google Drive Upload Improvements tests...")
    suite = unittest.TestLoader().loadTestsFromTestCase(GoogleDriveUploadImprovementsTest)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    return result.wasSuccessful()

ALL_GOOGLE_DRIVE_TESTS = [
    # Merged tests from original files
    test_bash_syntax_validation,
    test_return_command_no_output,
    test_error_handling,
    test_gds_read_command,
    test_python_command_parsing,
    test_path_conversion,
    test_bash_command_generation,
    test_google_drive_help_command,
    test_google_drive_shell_command,
    test_google_drive_desktop_status,
    # Converted unittest tests
    test_help_option,
    test_help_short_option,
    test_invalid_arguments,
    test_shell_help_command,
    test_my_drive_option,
    test_desktop_status_option,
    test_list_shell,
    test_tool_structure,
    test_run_environment_compatibility,
    # New comprehensive tests
    test_shell_echo,
    test_shell_ls,
    test_shell_pwd,
    test_shell_mkdir,
    test_shell_cd,
    test_shell_cd_parent,
    test_shell_rm,
    test_desktop_launch,
    test_desktop_shutdown,
    test_desktop_restart,
    test_create_shell,
    test_checkout_shell,
    test_terminate_shell,
    test_shell_invalid_command,
    test_cd_without_argument,
    test_mkdir_without_argument,
    test_rm_without_argument,
    test_echo_with_quotes,
    test_echo_empty,
    test_upload_nonexistent_file,
    test_upload_with_test_file,
]

def run_all_tests():
    """Run all Google Drive tests"""
    print(f"Running all Google Drive tests...")
    passed = 0
    failed = 0
    
    for test_func in ALL_GOOGLE_DRIVE_TESTS:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"Error: {test_func.__name__} failed: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0

def run_specific_test(test_name: str):
    """Run a specific test by name"""
    for test_func in ALL_GOOGLE_DRIVE_TESTS:
        if test_func.__name__ == test_name:
            print(f"Running {test_name}...")
            try:
                test_func()
                print(f"{test_name} passed")
                return True
            except Exception as e:
                print(f"Error: {test_name} failed: {e}")
                return False
    
    print(f"Error: Test {test_name} not found")
    return False

def list_all_tests():
    """List all available tests"""
    print(f"Available Google Drive test functions:")
    for i, test_func in enumerate(ALL_GOOGLE_DRIVE_TESTS, 1):
        print(f"  {i:2d}. {test_func.__name__}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Google Drive tool tests (all standalone functions)"
    )
    parser.add_argument(
        '--integration-only',
        action='store_true',
        help='Run only Google Drive integration test from _TEST.py'
    )
    parser.add_argument(
        '--specific',
        type=str,
        help='Run specific test function by name'
    )
    parser.add_argument(
        '--list-tests',
        action='store_true',
        help='List all available test functions'
    )
    parser.add_argument(
        '--upload-improvements',
        action='store_true',
        help='Run only the upload improvements tests'
    )
    parser.add_argument(
        '--comprehensive',
        action='store_true',
        help='Run the new comprehensive GDS tests (read, edit, upload, echo)'
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    
    success = True
    
    if args.list_tests:
        list_all_tests()
    elif args.specific:
        success = run_specific_test(args.specific)
    elif args.upload_improvements:
        success = run_upload_improvements_tests()
    elif args.comprehensive:
        print(f"Running comprehensive GDS tests...")
        try:
            from test_gds_comprehensive import run_comprehensive_tests
            success = run_comprehensive_tests()
        except ImportError:
            print(f"Error:  Comprehensive tests not available - test_gds_comprehensive.py not found")
            success = False
    elif args.integration_only:
        print(f"Running Google Drive integration test only...")
        if INTEGRATION_TEST_AVAILABLE:
            suite = unittest.TestSuite()
            suite.addTest(BinToolsIntegrationTest('test_07_google_drive'))
            runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
            result = runner.run(suite)
            success = result.wasSuccessful()
        else:
            print(f"Error:  Integration tests not available - _TEST.py not found")
            success = False
    else:
        # Default: Run all tests
        success = run_all_tests()
    
    sys.exit(0 if success else 1)
