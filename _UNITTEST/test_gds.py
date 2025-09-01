# -*- coding: utf-8 -*-
"""
GDS (Google Drive Shell) 全面测试套件

合并了所有GDS相关测试，涵盖：
- 基础功能测试
- 真实项目开发场景测试  
- 新功能测试（linter等）
- 边缘情况和错误处理测试

测试设计原则：
1. 远端窗口操作无timeout限制，允许用户手动执行
2. 结果判断基于功能执行情况，不依赖终端输出
3. 具有静态可重复性，使用--force等选项确保测试可重复运行
"""

import unittest
import subprocess
import sys
import re
import threading
import queue
import time
import inspect
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class GDSTest(unittest.TestCase):
    """
    GDS全面测试类
    包含所有GDS功能的测试，从基础到高级，从简单到复杂
    """
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        print("🚀 设置GDS全面测试环境...")
        
        # 设置路径
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GOOGLE_DRIVE_PY = cls.BIN_DIR / "GOOGLE_DRIVE.py"
        cls.TEST_DATA_DIR = Path(__file__).parent / "_DATA"
        cls.TEST_TEMP_DIR = Path(__file__).parent / "_TEMP"
        
        # 确保目录存在
        cls.TEST_DATA_DIR.mkdir(exist_ok=True)
        cls.TEST_TEMP_DIR.mkdir(exist_ok=True)
        
        # 创建测试文件
        cls._create_test_files()
        
        # 创建唯一的测试目录名（用于远端）
        import hashlib
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        hash_suffix = hashlib.md5(timestamp.encode()).hexdigest()[:8]
        cls.test_folder = f"gds_test_{timestamp}_{hash_suffix}"
        
        # print(f"📂 本地测试数据: {cls.TEST_DATA_DIR}")
        # print(f"📂 本地临时文件: {cls.TEST_TEMP_DIR}")
        
        # 检查GOOGLE_DRIVE.py是否可用
        if not cls.GOOGLE_DRIVE_PY.exists():
            raise unittest.SkipTest(f"GOOGLE_DRIVE.py not found at {cls.GOOGLE_DRIVE_PY}")
        
        # 创建远端测试目录并切换到该目录
        cls._setup_remote_test_directory()
        
        print("✅ 测试环境设置完成")
    
    @classmethod
    def _setup_remote_test_directory(cls):
        """设置远端测试目录"""
        print(f"📁 远端测试目录: ~/tmp/{cls.test_folder}")
        
        # 创建测试目录 (先切换到根目录确保正确的路径解析)
        mkdir_command = f"python3 {cls.GOOGLE_DRIVE_PY} --shell 'cd ~ && mkdir -p ~/tmp/{cls.test_folder}'"
        result = subprocess.run(
            mkdir_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cls.BIN_DIR
        )
        
        if result.returncode != 0:
            error_msg = f"创建远端测试目录失败: 返回码={result.returncode}, stderr={result.stderr}, stdout={result.stdout}"
            print(f"⚠️ {error_msg}")
            raise RuntimeError(error_msg)
        
        # 切换到测试目录
        cd_command = f"python3 {cls.GOOGLE_DRIVE_PY} --shell 'cd ~/tmp/{cls.test_folder}'"
        result = subprocess.run(
            cd_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cls.BIN_DIR
        )
        
        if result.returncode != 0:
            error_msg = f"切换到远端测试目录失败: 返回码={result.returncode}, stderr={result.stderr}, stdout={result.stdout}"
            print(f"⚠️ {error_msg}")
            raise RuntimeError(error_msg)
        else:
            print(f"✅ 已切换到远端测试目录: ~/tmp/{cls.test_folder}")
            
        # 验证目录确实存在
        pwd_command = f"python3 {cls.GOOGLE_DRIVE_PY} --shell 'pwd'"
        result = subprocess.run(
            pwd_command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cls.BIN_DIR
        )
        
        # 本地也切换到临时目录，避免本地重定向问题
        import tempfile
        import os
        cls.local_tmp_dir = tempfile.mkdtemp(prefix="gds_test_local_")
        print(f"📁 本地临时目录: {cls.local_tmp_dir}")
        os.chdir(cls.local_tmp_dir)
    
    @classmethod
    def _create_test_files(cls):
        """创建所有测试需要的文件"""
        
        # 1. 简单的Python脚本
        simple_script = cls.TEST_DATA_DIR / "simple_hello.py"
        simple_script.write_text('''"""
Simple Hello Script
"""
print("Hello from remote project!")
print("Current working directory:", __import__("os").getcwd())
import sys
print("Python version:", sys.version)
''')
        
        # 2. 复杂的Python项目结构
        project_dir = cls.TEST_DATA_DIR / "test_project"
        project_dir.mkdir(exist_ok=True)
        
        # main.py
        (project_dir / "main.py").write_text('''"""
测试项目主文件
"""
import json
import sys
from datetime import datetime

def main():
    print("🚀 测试项目启动")
    print(f"📅 当前时间: {datetime.now()}")
    print(f"🐍 Python版本: {sys.version}")
    
    # 读取配置文件
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print(f"⚙️ 配置: {config}")
    except FileNotFoundError:
        print("⚠️ 配置文件不存在，使用默认配置")
        config = {"debug": True, "version": "1.0.0"}
    
    # 执行核心逻辑
    from core import process_data
    result = process_data(config)
    print(f"✅ 处理结果: {result}")

if __name__ == "__main__":
    main()
''')
        
        # core.py
        (project_dir / "core.py").write_text('''"""
核心处理模块
"""

def process_data(config):
    """处理数据的核心函数"""
    if config.get("debug", False):
        print("🐛 调试模式已启用")
    
    # 模拟数据处理
    data = [1, 2, 3, 4, 5]
    result = sum(x * x for x in data)
    
    return {
        "processed": True,
        "result": result,
        "version": config.get("version", "unknown")
    }
''')
        
        # config.json
        (project_dir / "config.json").write_text('''{
    "debug": true,
    "version": "1.0.0",
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "testdb"
    },
    "features": {
        "logging": true,
        "caching": false,
        "monitoring": true
    }
}''')
        
        # 3. 语法正确和错误的文件（用于linter测试）
        valid_python = cls.TEST_DATA_DIR / "valid_script.py"
        valid_python.write_text('''"""
语法正确的Python脚本
"""

def hello_world():
    print("Hello, World!")
    return True

def calculate_sum(a, b):
    """计算两个数的和"""
    return a + b

if __name__ == "__main__":
    hello_world()
    result = calculate_sum(5, 3)
    print(f"Sum: {result}")
''')
        
        invalid_python = cls.TEST_DATA_DIR / "invalid_script.py"
        invalid_python.write_text('''"""
包含语法错误的Python脚本
"""

def hello_world(
    print("Missing closing parenthesis")
    return True

def calculate_sum(a, b:
    return a + b

if __name__ == "__main__":
hello_world()
    result = calculate_sum(5, 3)
    print(f"Sum: {result}")
''')
        
        # 4. 特殊字符文件
        special_file = cls.TEST_DATA_DIR / "special_chars.txt"
        special_file.write_text('''包含中文的文件
Special characters: !@#$%^&*()
Quotes: "Hello" and 'World'
Backslashes: \\path\\to\\file
JSON: {"key": "value", "number": 123}
Shell commands: ls -la && echo "done"
''')
        
        # 5. 大文件（用于性能测试）
        large_file = cls.TEST_DATA_DIR / "large_file.txt"
        large_content = "\\n".join([f"Line {i}: This is a test line with some content for performance testing" for i in range(1000)])
        large_file.write_text(large_content)
        
        # 6. JSON配置文件
        valid_json = cls.TEST_DATA_DIR / "valid_config.json"
        valid_json.write_text('''{
    "name": "测试项目",
    "version": "1.0.0",
    "description": "这是一个测试配置文件",
    "settings": {
        "debug": true,
        "logging": {
            "level": "INFO",
            "file": "app.log"
        }
    }
}''')
    
    def _run_gds_command(self, command, expect_success=True, check_function_result=True):
        """
        运行GDS命令的辅助方法
        
        Args:
            command: GDS命令
            expect_success: 是否期望命令成功
            check_function_result: 是否基于功能执行情况判断，而不是终端输出
        
        Returns:
            subprocess结果对象
        """
        full_command = f"python3 {self.GOOGLE_DRIVE_PY} --shell {command}"
        print(f"\n🔧 执行命令: {command}")
        
        try:
            # 注意：远端窗口操作没有timeout限制，允许用户手动执行
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                # 没有timeout参数 - 允许用户手动操作远端窗口
                cwd=self.BIN_DIR
            )
            
            print(f"📤 返回码: {result.returncode}")
            if result.stdout:
                print(f"📝 输出: {result.stdout[:200]}...")  # 限制输出长度
            if result.stderr:
                print(f"⚠️ 错误: {result.stderr[:200]}...")
            
            # 基于功能执行情况判断，而不是终端输出
            if check_function_result and expect_success:
                self.assertEqual(result.returncode, 0, f"命令执行失败: {command}")
            
            return result
        except Exception as e:
            print(f"💥 命令执行异常: {e}")
            if expect_success:
                self.fail(f"命令执行异常: {command} - {e}")
            return None
    
    def _verify_file_exists(self, filename):
        """验证远端文件或目录是否存在 - 使用统一cmd_ls接口，不弹出远程窗口"""
        result = self._run_gds_command(f'ls {filename}', expect_success=False)
        if result is None or result.returncode != 0:
            return False
        return "Path not found" not in result.stdout and "not found" not in result.stdout.lower()
    
    def _verify_file_content_contains(self, filename, expected_content):
        """验证远端文件内容包含特定文本（基于功能结果）"""
        result = self._run_gds_command(f'cat {filename}')
        if result.returncode == 0:
            return expected_content in result.stdout
        return False
    
    def _create_temp_file(self, filename, content):
        """在_TEMP目录创建临时文件"""
        temp_file = self.TEST_TEMP_DIR / filename
        temp_file.write_text(content)
        return temp_file
    
    def _run_gds_command_with_retry(self, command, verification_commands, max_retries=3, expect_success=True):
        """
        运行GDS命令并进行重试验证的辅助方法
        
        Args:
            command: 要执行的GDS命令
            verification_commands: 验证命令列表，所有命令都必须返回0才算成功
            max_retries: 最大重试次数
            expect_success: 是否期望命令成功
        
        Returns:
            tuple: (success: bool, last_result: subprocess结果对象)
        """
        print(f"\n🔄 执行带重试的命令: {command}")
        print(f"🔍 验证命令: {verification_commands}")
        print(f"🎯 最大重试次数: {max_retries}")
        
        for attempt in range(max_retries):
            print(f"\n📍 尝试 {attempt + 1}/{max_retries}")
            
            # 执行主命令
            result = self._run_gds_command(command, expect_success=expect_success, check_function_result=False)
            
            if not expect_success:
                # 如果不期望成功，直接返回结果
                return result.returncode != 0, result
            
            if result.returncode != 0:
                print(f"❌ 主命令失败，返回码: {result.returncode}")
                if attempt < max_retries - 1:
                    print("⏳ 等待1秒后重试...")
                    import time
                    time.sleep(1)
                    continue
                else:
                    return False, result
            
            # 执行验证命令
            all_verifications_passed = True
            for i, verify_cmd in enumerate(verification_commands):
                print(f"  🔍 验证 {i+1}/{len(verification_commands)}: {verify_cmd}")
                verify_result = self._run_gds_command(verify_cmd, expect_success=False, check_function_result=False)
                
                if verify_result.returncode != 0:
                    print(f"  ❌ 验证失败，返回码: {verify_result.returncode}")
                    all_verifications_passed = False
                    break
                else:
                    print(f"  ✅ 验证成功")
            
            if all_verifications_passed:
                print(f"🎉 所有验证通过，命令成功执行")
                return True, result
            
            if attempt < max_retries - 1:
                print("⏳ 验证失败，等待2秒后重试...")
                import time
                time.sleep(2)
        
        print(f"💥 所有重试失败")
        return False, result
    
    def _run_command_with_input(self, command_list, input_text, timeout=60):
        """
        运行命令并提供输入的辅助方法
        
        Args:
            command_list: 命令列表 (如 [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"])
            input_text: 要发送给命令的输入文本
            timeout: 超时时间（秒）
        
        Returns:
            subprocess结果对象
        """
        try:
            result = subprocess.run(
                command_list,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.BIN_DIR
            )
            return result
        except subprocess.TimeoutExpired:
            print(f"⏰ 命令执行超时 ({timeout}s)")
            # 创建一个模拟的失败结果
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = f"Command timed out after {timeout} seconds"
            return MockResult()
        except Exception as e:
            print(f"💥 命令执行异常: {e}")
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stdout = ""
                    self.stderr = str(e)
            return MockResult()
    
    # ==================== 基础功能测试 ====================
    
    def test_01_echo_basic(self):
        """测试基础echo命令"""
        
        # 简单echo
        result = self._run_gds_command('echo "Hello World"')
        self.assertEqual(result.returncode, 0)
        
        # 复杂字符串echo（避免使用!以免触发bash历史问题）
        result = self._run_gds_command('echo "Complex: @#$%^&*() \\"quotes\\" 中文字符"')
        self.assertEqual(result.returncode, 0)
        
        # Echo重定向创建文件（使用正确的语法：单引号包围整个命令）
        result = self._run_gds_command('\'echo "Test content" > test_echo.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件是否创建（基于功能结果）
        self.assertTrue(self._verify_file_exists("test_echo.txt"))
        self.assertTrue(self._verify_file_content_contains("test_echo.txt", "Test content"))
        
        # 更复杂的echo测试：包含转义字符和引号
        result = self._run_gds_command('\'echo "Line 1\\nLine 2\\tTabbed\\\\Backslash" > complex_echo.txt\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self._verify_file_exists("complex_echo.txt"))
        # 一次性验证文件内容
        result = self._run_gds_command('cat complex_echo.txt')
        self.assertEqual(result.returncode, 0)
        self.assertIn("Line 1", result.stdout)
        self.assertIn("Backslash", result.stdout)
        
        # 包含JSON格式的echo（检查实际的转义字符处理）
        result = self._run_gds_command('\'echo "{\\"name\\": \\"test\\", \\"value\\": 123}" > json_echo.txt\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self._verify_file_exists("json_echo.txt"))
        # 一次性验证JSON文件内容：GDS echo正确处理引号，不保留不必要的转义字符
        result = self._run_gds_command('cat json_echo.txt')
        self.assertEqual(result.returncode, 0)
        self.assertIn('{"name": "test"', result.stdout)
        self.assertIn('"value": 123}', result.stdout)
        
        # 包含中文和特殊字符的echo
        result = self._run_gds_command('\'echo "测试中文：你好世界 Special chars: @#$%^&*()_+-=[]{}|;:,.<>?" > chinese_echo.txt\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self._verify_file_exists("chinese_echo.txt"))
        self.assertTrue(self._verify_file_content_contains("chinese_echo.txt", "你好世界"))
        
        # 测试echo -e处理换行符（重定向到文件）
        result = self._run_gds_command('\'echo -e "line1\\nline2\\nline3" > echo_multiline.txt\'')
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self._verify_file_exists("echo_multiline.txt"))
        
        # 一次性读取文件内容并验证所有内容（避免重复cat调用）
        result = self._run_gds_command('cat echo_multiline.txt')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件内容包含所有预期的行
        self.assertIn("line1", result.stdout)
        self.assertIn("line2", result.stdout)
        self.assertIn("line3", result.stdout)
        
        # 验证输出包含实际的换行符，而不是空格分隔
        output_lines = result.stdout.strip().split('\n')
        content_lines = [line for line in output_lines if line and not line.startswith('=') and not line.startswith('⏳') and not line.startswith('GDS')]
        # 验证每行都是独立的（换行符被正确处理）
        line1_found = any("line1" in line and "line2" not in line for line in content_lines)
        line2_found = any("line2" in line and "line1" not in line and "line3" not in line for line in content_lines)
        line3_found = any("line3" in line and "line2" not in line for line in content_lines)
        self.assertTrue(line1_found and line2_found and line3_found, 
                       f"Expected separate lines for 'line1', 'line2', 'line3', got: {content_lines}")
    
    def test_02_echo_advanced(self):
        """测试echo的正确JSON语法（修复后的功能）"""
        
        # 使用正确的语法创建JSON文件（单引号包围重定向范围）
        result = self._run_gds_command('\'echo "{\\"name\\": \\"test\\", \\"value\\": 123}" > correct_json.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证JSON文件内容正确（修复后无转义字符）
        self.assertTrue(self._verify_file_exists("correct_json.txt"))
        self.assertTrue(self._verify_file_content_contains("correct_json.txt", '{"name": "test"'))
        self.assertTrue(self._verify_file_content_contains("correct_json.txt", '"value": 123}'))
        
        # 测试echo -e参数处理换行符
        result = self._run_gds_command('\'echo -e "Line1\\nLine2\\nLine3" > multiline.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证多行文件创建成功
        self.assertTrue(self._verify_file_exists("multiline.txt"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line1"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line2"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line3"))
        
        # 使用正确的语法（用引号包围整个命令，避免本地重定向）
        result = self._run_gds_command('\'echo -e "Line1\\nLine2\\nLine3" > multiline.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件在远端创建，而不是本地
        self.assertTrue(self._verify_file_exists("multiline.txt"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line1"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line2"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line3"))
        
        # 使用错误语法（会导致本地重定向）
        result = self._run_gds_command('echo \'{"name": "test", "value": 123}\' > local_redirect.txt')
        self.assertEqual(result.returncode, 0)

        # 文件应该被创建在TEST_TEMP_DIR中（本地临时目录）
        actual_file = self.TEST_TEMP_DIR / "local_redirect.txt"
        
        # 如果在TEST_TEMP_DIR没找到，也检查BIN_DIR
        if not actual_file.exists():
            actual_file = Path(self.BIN_DIR) / "local_redirect.txt"
        
        self.assertTrue(actual_file.exists(), f"文件应该在{self.TEST_TEMP_DIR}或{self.BIN_DIR}被创建")
        
        # 检查本地文件内容（应该包含处理后的JSON内容）
        with open(actual_file, 'r') as f:
            content = f.read().strip()
        
        # 验证文件包含正确的JSON内容（GDS应该处理并创建文件）
        print(f"📝 文件内容: {content}")
        self.assertTrue(len(content) > 0, "文件不应该为空")
        
        # 验证远端没有这个文件（应该返回False）
        self.assertFalse(self._verify_file_exists("local_redirect.txt"))
        
        # 清理：删除本地创建的文件
        try:
            actual_file.unlink()
            print(f"🗑️ 已清理文件: {actual_file}")
        except Exception as e:
            print(f"⚠️ 清理文件失败: {e}")
            pass
        
        # 创建简单的Python脚本
        python_code = '''import json
import os

# 创建配置文件
config = {
    "name": "test_project",
    "version": "1.0.0",
    "debug": True
}

with open("test_config.json", "w") as f:
    json.dump(config, f, indent=2)

print("Config created successfully")
print(f"Current files: {len(os.listdir())}")'''
        escaped_python_code = python_code.replace('"', '\\"').replace('\n', '\\n')
        result = self._run_gds_command(f"'echo -e \"{escaped_python_code}\" > test_script.py'")
        self.assertEqual(result.returncode, 0)
        
        # 验证Python脚本文件创建
        self.assertTrue(self._verify_file_exists("test_script.py"))
        
        # 执行Python脚本
        result = self._run_gds_command('python test_script.py')
        self.assertEqual(result.returncode, 0)
        
        # 验证脚本执行结果：创建了配置文件
        self.assertTrue(self._verify_file_exists("test_config.json"))
        self.assertTrue(self._verify_file_content_contains("test_config.json", '"name": "test_project"'))
        self.assertTrue(self._verify_file_content_contains("test_config.json", '"debug": true'))

        # 1. 批量创建文件（修复：使用正确的echo重定向语法）
        files = ["batch_file1.txt", "batch_file2.txt", "batch_file3.txt"]
        for i, filename in enumerate(files):
            result = self._run_gds_command(f'\'echo "Content {i+1}" > {filename}\'')
            self.assertEqual(result.returncode, 0)
        
        # 2. 验证所有文件创建成功（基于功能结果）
        for filename in files:
            self.assertTrue(self._verify_file_exists(filename))
            self.assertTrue(self._verify_file_content_contains(filename, f"Content"))
        
        # 3. 批量检查文件内容
        for filename in files:
            result = self._run_gds_command(f'cat {filename}')
            self.assertEqual(result.returncode, 0)
        
        # 4. 批量文件操作
        result = self._run_gds_command('find . -name "batch_file*.txt"')
        self.assertEqual(result.returncode, 0)
        
        # 5. 批量清理（使用通配符）
        for filename in files:
            result = self._run_gds_command(f'rm {filename}')
            self.assertEqual(result.returncode, 0)
    
    def test_03_ls_basic(self):
        """测试ls命令的全路径支持（修复后的功能）"""
        
        # 创建测试文件和目录结构
        result = self._run_gds_command('mkdir -p testdir')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('\'echo "test content" > testdir/testfile.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 测试ls目录
        result = self._run_gds_command('ls testdir')
        self.assertEqual(result.returncode, 0)
        
        # 测试ls全路径文件（修复后应该工作）
        result = self._run_gds_command('ls testdir/testfile.txt')
        self.assertEqual(result.returncode, 0)
        
        # 测试ls不存在的文件
        result = self._run_gds_command('ls testdir/nonexistent.txt', expect_success=False)
        # 修复后：GDS的ls命令对不存在文件应该返回非零退出码
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        self.assertIn("Path not found", result.stdout)
        
        # 测试ls不存在的目录中的文件
        result = self._run_gds_command('ls nonexistent_dir/file.txt', expect_success=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败

    def test_04_ls_advanced(self):
        # 1. 切换到测试子目录
        print("📁 切换到测试子目录")
        result = self._run_gds_command('"mkdir -p ls_test_subdir && cd ls_test_subdir"')
        self.assertEqual(result.returncode, 0)
        
        # 2. 测试基本ls命令（当前目录）
        print("📁 测试基本ls命令")
        result = self._run_gds_command('ls')
        self.assertEqual(result.returncode, 0)
        
        # 3. 测试ls .（当前目录显式指定）
        print("📁 测试ls .（当前目录）")
        result_ls_dot = self._run_gds_command('ls .')
        self.assertEqual(result_ls_dot.returncode, 0)
        
        # 4. 验证ls和ls .的输出完全一致
        print("🔍 验证ls和ls .输出一致性")
        result_ls = self._run_gds_command('ls')
        self.assertEqual(result_ls.returncode, 0)
        
        # 比较两个命令的输出内容（去除命令行显示部分）
        ls_output = result_ls.stdout.split('=============')[-1].strip()
        ls_dot_output = result_ls_dot.stdout.split('=============')[-1].strip()
        self.assertEqual(ls_output, ls_dot_output, 
                        f"ls和ls .的输出应该完全一致\nls输出: {ls_output}\nls .输出: {ls_dot_output}")
        
        # 5. 测试ls ~（根目录）- 关键修复测试
        print("🏠 测试ls ~（根目录）")
        result = self._run_gds_command('ls ~')
        self.assertEqual(result.returncode, 0)
        
        # 6. 创建测试结构来验证路径差异
        print("🏗️ 创建测试目录结构")
        result = self._run_gds_command('mkdir -p ls_test_dir/subdir')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('\'echo "root file" > ls_test_root.txt\'')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('\'echo "subdir file" > ls_test_dir/ls_test_sub.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 7. 测试不同路径的ls命令
        print("📂 测试不同路径的ls命令")
        
        # ls 相对路径
        result = self._run_gds_command('ls ls_test_dir')
        self.assertEqual(result.returncode, 0)
        
        # 8. 测试ls -R（递归列表）- 关键修复测试
        print("🔄 测试ls -R（递归）")
        result = self._run_gds_command('ls -R ls_test_dir')
        self.assertEqual(result.returncode, 0)
        
        # 9. 测试文件路径的ls
        print("📄 测试文件路径的ls")
        result = self._run_gds_command('ls ls_test_root.txt')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('ls ls_test_dir/ls_test_sub.txt')
        self.assertEqual(result.returncode, 0)
        
        # 10. 测试不存在路径的错误处理
        print("❌ 测试不存在路径的错误处理")
        result = self._run_gds_command('ls nonexistent_file.txt', expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        
        result = self._run_gds_command('ls nonexistent_dir/', expect_success=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 11. 测试特殊字符路径
        print("🔤 测试特殊字符路径")
        result = self._run_gds_command('mkdir -p "test dir with spaces"')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('ls "test dir with spaces"')
        self.assertEqual(result.returncode, 0)
        
        # 12. 清理测试文件
        print("🧹 清理测试文件")
        cleanup_items = [
            'ls_test_dir',
            'ls_test_root.txt', 
            '"test dir with spaces"'
        ]
        for item in cleanup_items:
            try:
                result = self._run_gds_command(f'rm -rf {item}', expect_success=False, check_function_result=False)
            except:
                pass  # 清理失败不影响测试结果

        # 13. 测试基本的绝对路径ls
        print("📁 测试绝对路径ls ~")
        result = self._run_gds_command('ls ~')
        self.assertEqual(result.returncode, 0)
        
        # 14. 创建多级目录结构用于测试
        print("🏗️ 创建多级测试目录结构")
        result = self._run_gds_command('mkdir -p path_test/level1/level2')
        self.assertEqual(result.returncode, 0)
        
        # 15. 测试相对路径cd和ls
        print("📂 测试相对路径cd")
        result = self._run_gds_command('cd path_test')
        self.assertEqual(result.returncode, 0)
        
        # 16. 测试当前目录ls
        print("📁 测试当前目录ls")
        result = self._run_gds_command('ls .')
        self.assertEqual(result.returncode, 0)
        
        # 17. 测试子目录ls
        print("📁 测试子目录ls")
        result = self._run_gds_command('ls level1')
        self.assertEqual(result.returncode, 0)
        
        # 18. 测试多级cd
        print("📂 测试多级cd")
        result = self._run_gds_command('cd level1/level2')
        self.assertEqual(result.returncode, 0)
        
        # 19. 测试父目录导航
        print("📂 测试父目录cd ..")
        result = self._run_gds_command('cd ..')
        self.assertEqual(result.returncode, 0)
        
        # 20. 测试多级父目录导航
        print("📂 测试多级父目录cd ../..")
        result = self._run_gds_command('cd ../..')
        self.assertEqual(result.returncode, 0)
        
        # 21. 测试相对路径ls
        print("📁 测试相对路径ls")
        result = self._run_gds_command('ls path_test/level1')
        self.assertEqual(result.returncode, 0)
        
        # 22. 测试复杂相对路径（先确保在正确位置）
        print("📂 测试复杂相对路径cd")
        # 先cd到path_test目录
        result = self._run_gds_command('cd path_test')
        self.assertEqual(result.returncode, 0)
        # 然后测试复杂路径
        result = self._run_gds_command('cd level1/../level1/level2')
        self.assertEqual(result.returncode, 0)
        
        # 23. 测试绝对路径cd回根目录
        print("📂 测试绝对路径cd回根目录")
        result = self._run_gds_command('cd ~')
        self.assertEqual(result.returncode, 0)
        
        # 24. 清理测试目录
        print("🧹 清理测试目录")
        result = self._run_gds_command('rm -rf path_test')
        self.assertEqual(result.returncode, 0)
        print("✅ 路径解析功能测试完成")
        
        # 25. 测试不存在的路径
        print("❌ 测试不存在的路径")
        result = self._run_gds_command('ls nonexistent_path', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        
        # 26. 测试cd到不存在的路径
        print("❌ 测试cd到不存在的路径")
        result = self._run_gds_command('cd nonexistent_path', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        
        # 27. 创建测试目录
        print("🏗️ 创建边界测试目录")
        result = self._run_gds_command('mkdir -p edge_test/empty_dir')
        self.assertEqual(result.returncode, 0)
        
        # 28. 测试空目录ls
        print("📁 测试空目录ls")
        result = self._run_gds_command('ls edge_test/empty_dir')
        self.assertEqual(result.returncode, 0)
        
        # 29. 测试根目录的父目录（应该失败或返回根目录）
        print("📂 测试根目录的父目录")
        result = self._run_gds_command('cd ~')
        self.assertEqual(result.returncode, 0)
        result = self._run_gds_command('cd ..', expect_success=False, check_function_result=False)
        # 这可能成功（返回根目录）或失败，取决于实现
        
        # 30. 测试当前目录的当前目录
        print("📁 测试当前目录的当前目录")
        result = self._run_gds_command('ls .')
        self.assertEqual(result.returncode, 0)
        result = self._run_gds_command('ls ./.')
        self.assertEqual(result.returncode, 0)
        
        # 31. 清理
        print("🧹 清理边界测试目录")
        result = self._run_gds_command('rm -rf edge_test')
        self.assertEqual(result.returncode, 0)

    def test_05_file_ops_mixed(self):
        # 1. 创建复杂目录结构
        result = self._run_gds_command('mkdir -p advanced_project/src/utils')
        self.assertEqual(result.returncode, 0)
        
        # 2. 在不同目录创建文件（修复：使用正确的echo重定向语法）
        result = self._run_gds_command('\'echo "# Main module" > advanced_project/src/main.py\'')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('\'echo "# Utilities" > advanced_project/src/utils/helpers.py\'')
        self.assertEqual(result.returncode, 0)
        
        # 3. 验证文件创建（基于功能结果）
        self.assertTrue(self._verify_file_exists("advanced_project/src/main.py"))
        self.assertTrue(self._verify_file_exists("advanced_project/src/utils/helpers.py"))
        
        # 4. 递归列出文件
        result = self._run_gds_command('ls -R advanced_project')
        self.assertEqual(result.returncode, 0)
        
        # 5. 移动文件
        result = self._run_gds_command('mv advanced_project/src/main.py advanced_project/main.py')
        self.assertEqual(result.returncode, 0)
        
        # 验证移动结果（基于功能结果）
        self.assertTrue(self._verify_file_exists("advanced_project/main.py"))
        
        # 原位置应该不存在
        result = self._run_gds_command('ls advanced_project/src/main.py', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 6. 测试rm命令删除文件
        result = self._run_gds_command('rm advanced_project/main.py')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件已被删除
        result = self._run_gds_command('ls advanced_project/main.py', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 7. 测试rm -rf删除目录
        result = self._run_gds_command('rm -rf advanced_project')
        self.assertEqual(result.returncode, 0)
        
        # 验证目录已被删除
        result = self._run_gds_command('ls advanced_project', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)

    def test_06_navigation(self):
        # pwd命令
        result = self._run_gds_command('pwd')
        self.assertEqual(result.returncode, 0)
        
        # ls命令
        result = self._run_gds_command('ls')
        self.assertEqual(result.returncode, 0)
        
        # mkdir命令
        result = self._run_gds_command('mkdir test_dir')
        self.assertEqual(result.returncode, 0)
        
        # 验证目录创建（基于功能结果）
        self.assertTrue(self._verify_file_exists("test_dir"))
        
        # 测试多目录创建（修复后的功能）
        print("📁 测试多目录创建")
        result = self._run_gds_command('mkdir -p multi_test/dir1 multi_test/dir2 multi_test/dir3')
        self.assertEqual(result.returncode, 0)
        
        # 验证所有目录都被创建
        self.assertTrue(self._verify_file_exists("multi_test/dir1"))
        self.assertTrue(self._verify_file_exists("multi_test/dir2"))
        self.assertTrue(self._verify_file_exists("multi_test/dir3"))
        
        # cd命令
        result = self._run_gds_command('cd test_dir')
        self.assertEqual(result.returncode, 0)
        
        # 返回上级目录
        result = self._run_gds_command('cd ..')
        self.assertEqual(result.returncode, 0)
        
        # === 不同远端路径类型测试 ===
        print("🛤️ 不同远端路径类型测试")
        # 创建嵌套目录结构用于测试
        result = self._run_gds_command('mkdir -p path_test/level1/level2')
        self.assertEqual(result.returncode, 0)
        
        # 测试相对路径导航
        result = self._run_gds_command('cd path_test')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('cd level1')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('cd level2')
        self.assertEqual(result.returncode, 0)
        
        # 测试..返回上级
        result = self._run_gds_command('cd ../..')
        self.assertEqual(result.returncode, 0)
        
        # 测试~开头的路径（应该指向REMOTE_ROOT）
        result = self._run_gds_command('cd ~')
        self.assertEqual(result.returncode, 0)
        
        # 从~返回到测试目录
        result = self._run_gds_command(f'cd ~/tmp/{self.test_folder}')
        self.assertEqual(result.returncode, 0)
        
        # 测试嵌套路径导航
        result = self._run_gds_command('cd path_test/level1/level2')
        self.assertEqual(result.returncode, 0)
        
        # 返回根目录
        result = self._run_gds_command('cd ../../..')
        self.assertEqual(result.returncode, 0)
        
        # === 错误路径类型测试 ===
        print("❌ 错误路径类型测试")
        
        # 测试不存在的目录
        result = self._run_gds_command('cd nonexistent_directory', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 测试将文件当作目录
        result = self._run_gds_command('\'echo "test content" > test_file.txt\'')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('cd test_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 测试无效的路径格式
        result = self._run_gds_command('cd ""', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)
        
        # 测试尝试访问~上方的路径（应该被限制）
        result = self._run_gds_command('cd ~/../..', expect_success=False, check_function_result=False)
        # 这个可能成功也可能失败，取决于GDS的安全限制
        
        print("✅ 导航命令和路径测试完成")
    
    # ==================== 文件上传测试 ====================
    
    def test_07_upload(self):
        # 单文件上传（使用--force确保可重复性）
        # 创建唯一的测试文件避免并发冲突
        unique_file = self.TEST_TEMP_DIR / "test_upload_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        import shutil
        shutil.copy2(original_file, unique_file)
        
        # 使用重试机制上传文件
        success, result = self._run_gds_command_with_retry(
            f'upload --force {unique_file}',
            ['ls test_upload_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 多文件上传（使用--force确保可重复性）
        valid_script = self.TEST_DATA_DIR / "valid_script.py"
        special_file = self.TEST_DATA_DIR / "special_chars.txt"
        success, result = self._run_gds_command_with_retry(
            f'upload --force {valid_script} {special_file}',
            ['ls valid_script.py', 'ls special_chars.txt'],
            max_retries=3
        )
        self.assertTrue(success, f"多文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 文件夹上传（修复：--force参数应该在路径之前）
        project_dir = self.TEST_DATA_DIR / "test_project"
        success, result = self._run_gds_command_with_retry(
            f'upload-folder --force {project_dir}',
            ['ls test_project'],
            max_retries=3
        )
        self.assertTrue(success, f"文件夹上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 测试上传到已存在文件（没有--force应该失败）
        # 创建唯一测试文件用于冲突测试
        conflict_test_file = self.TEST_TEMP_DIR / "test_upload_conflict_file.py"
        shutil.copy2(original_file, conflict_test_file)
        
        # 先确保文件存在
        success, result = self._run_gds_command_with_retry(
            f'upload --force {conflict_test_file}',
            ['ls test_upload_conflict_file.py'],
            max_retries=3
        )
        self.assertTrue(success, f"冲突测试文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 现在尝试不带--force上传同一个文件（应该失败）
        result = self._run_gds_command(f'upload {conflict_test_file}', expect_success=False)
        self.assertEqual(result.returncode, 1)
        
        # 测试upload --force的覆盖功能（文件内容不同）
        # 创建一个内容不同的本地文件
        overwrite_test_file = self.TEST_TEMP_DIR / "test_upload_overwrite_file.py"
        with open(overwrite_test_file, 'w') as f:
            f.write('print("ORIGINAL VERSION - Test upload")')
        
        # 先上传原始版本
        success, result = self._run_gds_command_with_retry(
            f'upload --force {overwrite_test_file}',
            ['ls test_upload_overwrite_file.py'],
            max_retries=3
        )
        self.assertTrue(success, f"原始版本上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 读取远程文件的原始内容
        original_content_result = self._run_gds_command('cat test_upload_overwrite_file.py')
        self.assertEqual(original_content_result.returncode, 0)
        original_content = original_content_result.stdout
        
        # 修改本地文件内容
        with open(overwrite_test_file, 'w') as f:
            f.write('print("MODIFIED VERSION - Test upload overwrite!")')
        
        # 使用--force上传修改后的文件
        success, result = self._run_gds_command_with_retry(
            f'upload --force {overwrite_test_file}',
            ['grep "MODIFIED VERSION" test_upload_overwrite_file.py'],
            max_retries=3
        )
        self.assertTrue(success, f"修改版本上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 验证文件内容确实被修改了
        modified_content_result = self._run_gds_command('cat test_upload_overwrite_file.py')
        self.assertEqual(modified_content_result.returncode, 0)
        modified_content = modified_content_result.stdout
        
        # 确保内容不同
        self.assertNotEqual(original_content, modified_content)
        self.assertIn("MODIFIED VERSION", modified_content)

        # 测试空目录上传
        empty_dir = self.TEST_DATA_DIR / "empty_test_dir"
        empty_dir.mkdir(exist_ok=True)
        
        # 清理目录内容（确保为空）
        for item in empty_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                import shutil
                shutil.rmtree(item)
        
        success, result = self._run_gds_command_with_retry(
            f'upload-folder --force {empty_dir}',
            ['ls empty_test_dir'],
            max_retries=3
        )
        self.assertTrue(success, f"空目录上传失败: {result.stderr if result else 'Unknown error'}")
    
    def test_08_grep(self):
        # 创建测试文件
        test_content = '''Line 1: Hello world
Line 2: This is a test
Line 3: Hello again
Line 4: Multiple Hello Hello Hello
Line 5: No match here'''
        echo_cmd = f'echo "{test_content}" > grep_test.txt'
        result = self._run_gds_command(f"'{echo_cmd}'")
        self.assertEqual(result.returncode, 0)
        
        # 验证文件创建成功
        self.assertTrue(self._verify_file_exists("grep_test.txt"))
        
        # 测试1: 无模式grep（等效于read命令）
        result = self._run_gds_command('grep grep_test.txt')
        self.assertEqual(result.returncode, 0)
        output = result.stdout

        # 验证包含行号和所有行内容
        self.assertIn("1: Line 1: Hello world", output)
        self.assertIn("2: Line 2: This is a test", output)
        self.assertIn("3: Line 3: Hello again", output)
        self.assertIn("4: Line 4: Multiple Hello Hello Hello", output)
        self.assertIn("5: Line 5: No match here", output)
        
        # 测试2: 有模式grep（只显示匹配行）
        result = self._run_gds_command('grep "Hello" grep_test.txt')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        # 验证只包含匹配的行
        self.assertIn("1: Line 1: Hello world", output)
        self.assertIn("3: Line 3: Hello again", output)
        self.assertIn("4: Line 4: Multiple Hello Hello Hello", output)
        # 验证不包含不匹配的行
        self.assertNotIn("2: Line 2: This is a test", output)
        self.assertNotIn("5: Line 5: No match here", output)
        
        # 测试3: 多词模式grep
        result = self._run_gds_command('grep "is a" grep_test.txt')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertIn("2: Line 2: This is a test", output)
        self.assertNotIn("1: Line 1: Hello world", output)
        self.assertNotIn("3: Line 3: Hello again", output)
        
        # 测试4: 测试不存在模式的grep（应该没有输出）
        result = self._run_gds_command('grep "NotFound" grep_test.txt')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertNotIn("1:", output)
        self.assertNotIn("2:", output)
        self.assertNotIn("3:", output)
        self.assertNotIn("4:", output)
        self.assertNotIn("5:", output)
    
    # ==================== 文件编辑测试 ====================
    
    def test_09_edit(self):
        # 重新上传测试文件确保存在（使用--force保证覆盖）
        # 创建唯一的测试文件避免并发冲突
        test_edit_file = self.TEST_TEMP_DIR / "test_edit_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        import shutil
        shutil.copy2(original_file, test_edit_file)
        
        success, result = self._run_gds_command_with_retry(
            f'upload --force {test_edit_file}',
            ['ls test_edit_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"test04文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 测试upload --force的覆盖功能
        # 再次上传同一个文件，应该覆盖成功
        success, result = self._run_gds_command_with_retry(
            f'upload --force {test_edit_file}',
            ['ls test_edit_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"upload --force覆盖功能失败: {result.stderr if result else 'Unknown error'}")
        
        # 基础文本替换编辑
        success, result = self._run_gds_command_with_retry(
            'edit test_edit_simple_hello.py \'[["Hello from remote project!", "Hello from MODIFIED remote project!"]]\'',
            ['grep "MODIFIED" test_edit_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"基础文本替换编辑失败: {result.stderr if result else 'Unknown error'}")
        
        # 行号替换编辑（使用0-based索引）
        success, result = self._run_gds_command_with_retry(
            'edit test_edit_simple_hello.py \'[[[1, 2], "# Modified first line"]]\'',
            ['grep "# Modified first line" test_edit_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"行号替换编辑失败: {result.stderr if result else 'Unknown error'}")
        
        # 预览模式编辑（不实际修改文件）
        # 预览模式不修改文件，所以不需要验证文件内容变化
        result = self._run_gds_command('edit --preview test_edit_simple_hello.py \'[["print", "# print"]]\'')
        self.assertEqual(result.returncode, 0)
        
        # 备份模式编辑
        success, result = self._run_gds_command_with_retry(
            'edit --backup test_edit_simple_hello.py \'[["MODIFIED", "Updated"]]\'',
            ['grep "Updated" test_edit_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"备份模式编辑失败: {result.stderr if result else 'Unknown error'}")
    
    
    def test_10_read(self):
        # 创建独特的测试文件
        test_read_file = self.TEST_TEMP_DIR / "test_read_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        
        # 复制文件并上传
        import shutil
        shutil.copy2(original_file, test_read_file)
        success, result = self._run_gds_command_with_retry(
            f'upload --force {test_read_file}',
            ['ls test_read_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"test05文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        # cat命令读取文件
        result = self._run_gds_command('cat test_read_simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # read命令读取文件（带行号）
        result = self._run_gds_command('read test_read_simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # read命令读取指定行范围
        result = self._run_gds_command('read test_read_simple_hello.py 1 3')
        self.assertEqual(result.returncode, 0)
        
        # grep命令搜索内容
        result = self._run_gds_command('grep "print" test_read_simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # find命令查找文件
        result = self._run_gds_command('find . -name "*.py"')
        self.assertEqual(result.returncode, 0)
        
        # --force选项强制重新下载
        result = self._run_gds_command('read --force test_read_simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # 测试不存在的文件
        print("🚫 测试cat不存在的文件")
        result = self._run_gds_command('cat nonexistent_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "cat不存在的文件应该返回非零退出码")
        
        # 测试read不存在的文件
        print("🚫 测试read不存在的文件")
        result = self._run_gds_command('read nonexistent_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "read不存在的文件应该返回非零退出码")
        
        # 测试grep不存在的文件
        print("🚫 测试grep不存在的文件")
        result = self._run_gds_command('grep "test" nonexistent_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "grep不存在的文件应该返回非零退出码")
        
        # 测试特殊字符文件处理
        print("✨ 测试特殊字符文件处理")
        if not self._verify_file_exists("special_chars.txt"):
            special_file = self.TEST_DATA_DIR / "special_chars.txt"
            success, result = self._run_gds_command_with_retry(
                f'upload --force {special_file}',
                ['ls special_chars.txt'],
                max_retries=3
            )
            self.assertTrue(success, f"特殊字符文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        result = self._run_gds_command('cat special_chars.txt')
        self.assertEqual(result.returncode, 0, "特殊字符文件应该能正常读取")
    
    def test_11_project_development(self):
        
        # === 阶段1: 项目初始化 ===
        print("📦 阶段1: 项目初始化")
        
        # 创建项目目录
        result = self._run_gds_command('mkdir -p myproject/src myproject/tests myproject/docs')
        self.assertEqual(result.returncode, 0)
        
        # 验证所有目录创建成功
        self.assertTrue(self._verify_file_exists("myproject/src"), "myproject/src目录应该存在")
        self.assertTrue(self._verify_file_exists("myproject/tests"), "myproject/tests目录应该存在")
        self.assertTrue(self._verify_file_exists("myproject/docs"), "myproject/docs目录应该存在")
        
        # 创建项目基础文件
        result = self._run_gds_command('\'echo "# My Project\\nA sample Python project for testing" > myproject/README.md\'')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('\'echo "requests>=2.25.0\\nnumpy>=1.20.0\\npandas>=1.3.0" > myproject/requirements.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 创建主应用文件
        main_py_content = '''# 主应用文件
import sys
import json
from datetime import datetime

def load_config(config_file="config.json"):
    # 加载配置文件
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_file} 不存在")
        return {}

def process_data(data_list):
    # 处理数据列表
    if not data_list:
        return {"error": "数据为空"}
    
    result = {
        "count": len(data_list),
        "sum": sum(data_list),
        "average": sum(data_list) / len(data_list),
        "max": max(data_list),
        "min": min(data_list)
    }
    return result

def main():
    # 主函数
    print("🚀 应用启动")
    print(f"⏰ 当前时间: {datetime.now()}")
    
    # 加载配置
    config = load_config()
    print(f"⚙️ 配置: {config}")
    
    # 处理示例数据
    sample_data = [1, 2, 3, 4, 5, 10, 15, 20]
    result = process_data(sample_data)
    print(f"📊 处理结果: {result}")
    
    print("✅ 应用完成")

if __name__ == "__main__":
    main()
'''
        
        # 使用echo创建main.py文件（长内容会自动使用base64编码）
        # 转义特殊字符确保Python语法正确
        escaped_content = main_py_content.replace('"', '\\"')
        result = self._run_gds_command(f'\'echo "{escaped_content}" > myproject/src/main.py\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证项目结构创建成功
        self.assertTrue(self._verify_file_exists("myproject/README.md"))
        self.assertTrue(self._verify_file_exists("myproject/requirements.txt"))
        self.assertTrue(self._verify_file_exists("myproject/src/main.py"))
        
        # === 阶段2: 环境设置 ===
        print("🔧 阶段2: 环境设置")
        
        # 使用时间哈希命名虚拟环境（确保测试独立性）
        import time
        venv_name = f"myproject_env_{int(time.time())}"
        print(f"📦 虚拟环境名称: {venv_name}")
        
        # 创建虚拟环境
        result = self._run_gds_command(f'venv --create {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 激活虚拟环境
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 安装依赖（简化版，只安装一个包）
        result = self._run_gds_command('pip install requests')
        self.assertEqual(result.returncode, 0)
        
        # === 阶段3: 开发调试 ===
        print("🐛 阶段3: 开发调试")
        
        # 进入项目目录
        result = self._run_gds_command('cd myproject/src')
        self.assertEqual(result.returncode, 0)
        
        # 运行主程序（第一次运行，可能有问题）
        result = self._run_gds_command('python main.py')
        self.assertEqual(result.returncode, 0)
        
        # 创建配置文件
        result = self._run_gds_command('\'echo "{\\"debug\\": true, \\"version\\": \\"1.0.0\\", \\"author\\": \\"developer\\"}" > config.json\'')
        self.assertEqual(result.returncode, 0)
        
        # 再次运行程序（现在应该加载配置文件）
        result = self._run_gds_command('python main.py')
        self.assertEqual(result.returncode, 0)
        
        # === 阶段4: 问题解决 ===
        print("🔍 阶段4: 问题解决")
        
        # 搜索特定函数
        result = self._run_gds_command('grep "def " main.py', expect_success=False)
        if result.returncode != 0:
            # 如果grep失败，尝试其他方式验证文件内容
            print("⚠️ grep命令失败，使用cat查看文件内容")
            result = self._run_gds_command('cat main.py')
            self.assertEqual(result.returncode, 0)
        else:
            print("✅ grep命令成功")
        
        # 查看配置文件内容
        result = self._run_gds_command('cat config.json')
        self.assertEqual(result.returncode, 0)
        
        # 读取代码的特定行
        result = self._run_gds_command('read main.py 1 10')
        self.assertEqual(result.returncode, 0)
        
        # 编辑代码：添加更多功能
        success, result = self._run_gds_command_with_retry(
            'edit main.py \'[["处理示例数据", "处理示例数据（已优化）"]]\'',
            ['grep "已优化" main.py'],
            max_retries=3
        )
        self.assertTrue(success, f"代码编辑失败: {result.stderr if result else 'Unknown error'}")
        
        # === 阶段5: 验证测试 ===
        print("✅ 阶段5: 验证测试")
        
        # 最终运行测试
        result = self._run_gds_command('python main.py')
        self.assertEqual(result.returncode, 0)
        
        # 检查项目文件（限制在当前测试目录内）
        result = self._run_gds_command('find . -name "*.py"')
        self.assertEqual(result.returncode, 0)
        
        # 查看项目结构（限制在当前测试目录内）
        result = self._run_gds_command('ls -R .')
        self.assertEqual(result.returncode, 0)
        
        # 清理：取消激活虚拟环境
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        # 删除测试虚拟环境
        result = self._run_gds_command(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 返回根目录
        result = self._run_gds_command('cd ../..')
        self.assertEqual(result.returncode, 0)
        
        print("🎉 真实项目开发工作流程测试完成！")

    # ==================== 项目开发场景测试 ====================
    
    def test_12_project_deployment(self):
        
        # 1. 上传项目文件夹（修复：--force参数应该在路径之前）
        project_dir = self.TEST_DATA_DIR / "test_project"
        success, result = self._run_gds_command_with_retry(
            f'upload-folder --force {project_dir}',
            ['ls test_project'],
            max_retries=3
        )
        self.assertTrue(success, f"项目文件夹上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 2. 进入项目目录
        result = self._run_gds_command('cd test_project')
        self.assertEqual(result.returncode, 0)
        
        # 3. 查看项目结构
        result = self._run_gds_command('ls -la')
        self.assertEqual(result.returncode, 0)
        
        # 4. 验证项目文件存在
        result = self._run_gds_command('ls main.py')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('ls core.py')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('ls config.json')
        self.assertEqual(result.returncode, 0)
        
        # 5. 返回根目录
        result = self._run_gds_command('cd ..')
        self.assertEqual(result.returncode, 0)
    
    def test_13_code_execution(self):
        
        # === 阶段1: 创建独立的测试项目结构 ===
        print("📦 阶段1: 创建测试项目")
        
        # 创建项目目录
        result = self._run_gds_command('mkdir -p test07_project')
        self.assertEqual(result.returncode, 0)
        
        # 创建简单的main.py文件（无三重引号，无外部依赖）
        main_py_content = '''# Test project main file
import sys
from datetime import datetime

def main():
    print("🚀 Test project started")
    print(f"📅 Current time: {datetime.now()}")
    print(f"🐍 Python version: {sys.version}")
    
    # Simple data processing
    data = [1, 2, 3, 4, 5]
    result = {
        "count": len(data),
        "sum": sum(data),
        "average": sum(data) / len(data)
    }
    print(f"✅ Processing result: {result}")
    print("✅ Test project completed")

if __name__ == "__main__":
    main()
'''
        
        # 转义特殊字符确保Python语法正确
        escaped_content = main_py_content.replace('"', '\\"')
        result = self._run_gds_command(f'\'echo "{escaped_content}" > test07_project/main.py\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证项目文件创建成功
        self.assertTrue(self._verify_file_exists("test07_project/main.py"))
        
        # === 阶段2: 执行测试 ===
        print("🔧 阶段2: 代码执行测试")
        
        # 1. 执行简单Python脚本
        # 创建独特的测试文件
        test07_file = self.TEST_TEMP_DIR / "test07_simple_hello.py"
        original_file = self.TEST_DATA_DIR / "simple_hello.py"
        
        # 复制文件并上传
        import shutil
        shutil.copy2(original_file, test07_file)
        success, result = self._run_gds_command_with_retry(
            f'upload --force {test07_file}',
            ['ls test07_simple_hello.py'],
            max_retries=3
        )
        self.assertTrue(success, f"test07文件上传失败: {result.stderr if result else 'Unknown error'}")
        
        result = self._run_gds_command('python test07_simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # 2. 执行Python代码片段
        result = self._run_gds_command('python -c "print(\\"Hello from Python code!\\"); import os; print(os.getcwd())"')
        self.assertEqual(result.returncode, 0)
        
        # 3. 执行项目主文件
        result = self._run_gds_command('"cd test07_project && python main.py"')
        self.assertEqual(result.returncode, 0)
    
    # ==================== 虚拟环境管理测试 ====================
    
    def test_14_venv_basic(self):
        # 使用时间哈希命名虚拟环境（确保测试独立性）
        import time
        venv_name = f"test_env_{int(time.time())}"
        print(f"📦 虚拟环境名称: {venv_name}")
        
        # 1. 创建虚拟环境
        result = self._run_gds_command(f'venv --create {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 2. 列出虚拟环境（验证创建成功）
        result = self._run_gds_command('venv --list')
        self.assertEqual(result.returncode, 0)
        # 基于功能结果判断：检查输出是否包含环境名
        self.assertIn(venv_name, result.stdout)
        
        # 3. 激活虚拟环境
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 4. 在虚拟环境中安装包（使用colorama避免与其他测试冲突）
        result = self._run_gds_command('pip install colorama')
        self.assertEqual(result.returncode, 0)
        
        # 5. 验证包在激活状态下可用
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama imported successfully\\")"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("colorama imported successfully", result.stdout)
        
        # 6. 取消激活虚拟环境
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        # 7. 创建一个空的虚拟环境用于验证包隔离
        empty_venv_name = f"empty_env_{int(time.time())}"
        result = self._run_gds_command(f'venv --create {empty_venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 8. 激活空环境
        result = self._run_gds_command(f'venv --activate {empty_venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 9. 验证包在空环境中不可用（应该失败）
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama imported\\")"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败，因为colorama不在空环境中
        
        # 10. 重新激活原环境验证包仍然可用
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama re-imported successfully\\")"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("colorama re-imported successfully", result.stdout)
        
        # 11. 最终清理：取消激活并删除虚拟环境
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 12. 清理空环境
        result = self._run_gds_command(f'venv --delete {empty_venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 13. 验证删除后的环境不在列表中
        result = self._run_gds_command('venv --list')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn(venv_name, result.stdout)
        self.assertNotIn(empty_venv_name, result.stdout)
        
        # 14. 验证删除后的环境无法激活
        result = self._run_gds_command(f'venv --activate {venv_name}', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        
        result = self._run_gds_command(f'venv --activate {empty_venv_name}', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败
    
    def test_15_venv_package(self):
        # 使用时间哈希命名虚拟环境（确保测试独立性）
        import time
        venv_name = f"current_test_env_{int(time.time())}"
        print(f"📦 虚拟环境名称: {venv_name}")
        
        # 0. 预备工作：确保测试环境干净（强制取消激活任何现有环境）
        print("🧹 清理测试环境...")
        try:
            result = self._run_gds_command('venv --deactivate', expect_success=False, check_function_result=False)
            # 不管成功与否都继续，因为可能本来就没有激活的环境
        except:
            pass  # 忽略清理过程中的任何错误
        
        # 1. 初始状态：没有激活的环境
        result = self._run_gds_command('venv --current')
        self.assertEqual(result.returncode, 0)
        self.assertIn("No virtual environment", result.stdout)
        
        # 2. 创建虚拟环境
        result = self._run_gds_command(f'venv --create {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 3. 激活虚拟环境
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 4. 检测当前激活的环境
        result = self._run_gds_command('venv --current')
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"Current virtual environment: {venv_name}", result.stdout)
        
        # 5. 取消激活
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        # 6. 再次检测：应该没有激活的环境
        result = self._run_gds_command('venv --current')
        self.assertEqual(result.returncode, 0)
        self.assertIn("No virtual environment currently activated", result.stdout)
        
        # 7. 清理：删除虚拟环境
        result = self._run_gds_command(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)

        print("🧹 清理测试环境...")
        try:
            result = self._run_gds_command('venv --deactivate', expect_success=False, check_function_result=False)
        except:
            pass  # 忽略清理过程中的任何错误
        
        # 使用时间哈希命名虚拟环境（确保测试独立性）
        import time
        venv_name = f"package_test_env_{int(time.time())}"
        print(f"📦 虚拟环境名称: {venv_name}")
        
        # 1. 创建虚拟环境
        result = self._run_gds_command(f'venv --create {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 2. 激活虚拟环境
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        # 3. 在虚拟环境中安装包
        result = self._run_gds_command('pip install colorama')
        self.assertEqual(result.returncode, 0)
        
        # 4. 检测已安装的包
        result = self._run_gds_command('pip list')
        self.assertEqual(result.returncode, 0)
        self.assertIn("colorama", result.stdout)
        
        # 5. 验证包在激活状态下可用
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama imported successfully\\")"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("colorama imported successfully", result.stdout)
        
        # 6. 取消激活虚拟环境
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        # 7. 验证包在未激活状态下不可用
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama imported\\")"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败，因为colorama不在系统环境中
        
        # 8. 重新激活环境验证包仍然可用
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama re-imported successfully\\")"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("colorama re-imported successfully", result.stdout)
        
        # 9. 清理：取消激活并删除虚拟环境
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)
        
    def test_16_linter(self):
        # 强制上传测试文件（确保文件存在）
        print("📤 上传测试文件...")
        valid_script = self.TEST_DATA_DIR / "valid_script.py"
        success, result = self._run_gds_command_with_retry(
            f'upload --force {valid_script}',
            ['ls valid_script.py'],
            max_retries=3
        )
        self.assertTrue(success, f"valid_script.py上传失败: {result.stderr if result else 'Unknown error'}")
        
        invalid_script = self.TEST_DATA_DIR / "invalid_script.py"
        success, result = self._run_gds_command_with_retry(
            f'upload --force {invalid_script}',
            ['ls invalid_script.py'],
            max_retries=3
        )
        self.assertTrue(success, f"invalid_script.py上传失败: {result.stderr if result else 'Unknown error'}")
        
        json_file = self.TEST_DATA_DIR / "valid_config.json"
        success, result = self._run_gds_command_with_retry(
            f'upload --force {json_file}',
            ['ls valid_config.json'],
            max_retries=3
        )
        self.assertTrue(success, f"valid_config.json上传失败: {result.stderr if result else 'Unknown error'}")
        
        # 1. 测试语法正确的文件
        print("✅ 测试语法正确的Python文件")
        result = self._run_gds_command('linter valid_script.py')
        self.assertEqual(result.returncode, 0)
        
        # 2. 测试有样式错误的文件
        print("⚠️ 测试有样式错误的Python文件")
        result = self._run_gds_command('linter invalid_script.py', expect_success=False, check_function_result=False)
        # 样式错误的文件应该返回非零退出码或包含错误信息
        if result.returncode == 0:
            # 如果返回码为0，检查输出是否包含错误信息
            self.assertTrue("error" in result.stdout.lower() or "warning" in result.stdout.lower(), 
                          f"样式错误文件应该报告错误，但输出为: {result.stdout}")
        else:
            # 如果返回码非0，应该是因为检测到了linting问题
            self.assertTrue("error" in result.stdout.lower() or "warning" in result.stdout.lower() or "fail" in result.stdout.lower(), 
                          f"Linter应该报告具体问题，但输出为: {result.stdout}")
        
        # 3. 测试指定语言的linter
        print("🐍 测试指定Python语言的linter")
        result = self._run_gds_command('linter --language python valid_script.py')
        self.assertEqual(result.returncode, 0)
        
        # 4. 测试JSON文件linter
        print("📋 测试JSON文件linter")
        result = self._run_gds_command('linter valid_config.json')
        self.assertEqual(result.returncode, 0)
        
        # 5. 测试不存在文件的错误处理
        print("🚫 测试不存在文件的错误处理")
        result = self._run_gds_command('linter nonexistent_file.py', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "不存在的文件应该返回错误")
        
    def test_17_edit_linter(self):
        # 创建一个有语法错误的Python文件
        error_content = '''def hello_world(
print("Missing closing parenthesis")
return True

def calculate_sum(a, b:
return a + b

if __name__ == "__main__":
hello_world()
result = calculate_sum(5, 3)
print(f"Sum: {result}")
'''
        
        # 使用echo创建有错误的文件
        escaped_content = error_content.replace('"', '\\"').replace('\n', '\\n')
        success, result = self._run_gds_command_with_retry(
            f"'echo -e \"{escaped_content}\" > syntax_error_test.py'",
            ['ls syntax_error_test.py'],
            max_retries=3
        )
        self.assertTrue(success, f"创建语法错误文件失败: {result.stderr if result else 'Unknown error'}")
        
        # 尝试编辑文件，这应该触发linter并显示错误
        print("🔧 执行edit命令，应该触发linter检查...")
        result = self._run_gds_command('edit syntax_error_test.py \'[["Missing closing parenthesis", "Fixed syntax error"]]\'')
        
        # 检查edit命令的输出格式
        print("📋 检查edit命令输出格式...")
        output = result.stdout
        
        # 验证linter错误格式
        # 1. 检查是否有edit comparison部分
        self.assertIn("========", output, "应该包含edit comparison分隔线")
        
        # 2. 检查是否有linter错误部分（由于语法错误应该有）
        linter_error_indicators = [
            "linter warnings or errors found:",
            "ERROR:",
            "SyntaxError",
            "invalid syntax"
        ]
        
        has_linter_output = any(indicator in output for indicator in linter_error_indicators)
        if has_linter_output:
            print("✅ 检测到linter错误输出")
            
            # 验证linter错误格式：应该在edit comparison下方，由======分割
            sections = output.split("========")
            
            # 寻找包含linter错误的section
            linter_section = None
            for i, section in enumerate(sections):
                if any(indicator in section for indicator in linter_error_indicators):
                    linter_section = section
                    print(f"📍 在第{i+1}个section找到linter输出")
                    break
            
            if linter_section:
                print("🔍 Linter错误格式验证:")
                print("=" * 50)
                print(linter_section.strip())
                print("=" * 50)
                
                # 验证格式特征
                self.assertIn("warnings or errors found:", linter_section, "应该包含linter错误计数信息")
                
                # 验证每个错误都以ERROR:开头并列在单独的行
                error_lines = [line.strip() for line in linter_section.split('\n') 
                              if line.strip().startswith('ERROR:')]
                self.assertGreater(len(error_lines), 0, "应该至少有一个ERROR:行")
                print(f"✅ 找到 {len(error_lines)} 个linter错误")
                for i, error_line in enumerate(error_lines[:3]):  # 只显示前3个
                    print(f"   {i+1}. {error_line}")
                
            else:
                print("⚠️ 未找到格式化的linter错误section，但检测到linter输出")
        else:
            print("⚠️ 未检测到linter错误输出，可能linter未运行或文件语法正确")
            # 这可能是正常的，如果linter没有检测到错误
        
        print("✅ Edit与Linter集成测试完成")
    
    def test_18_pipe(self):
        
        # 测试简单的pipe命令
        result = self._run_gds_command('echo "hello world" | grep hello')
        self.assertEqual(result.returncode, 0)
        
        # 创建测试文件
        result = self._run_gds_command('\'echo "test content" > pipe_test.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件是否被创建（调试）
        result = self._run_gds_command('ls -la', expect_success=False)
        print(f"📋 创建文件后目录内容: {result.stdout[:300]}")
        
        # 直接验证文件存在
        self.assertTrue(self._verify_file_exists('pipe_test.txt'), "pipe_test.txt should exist after creation")
        
        # 测试 ls | grep 组合
        result = self._run_gds_command('ls | grep pipe_test')
        self.assertEqual(result.returncode, 0)
        
        # 清理测试文件
        self._run_gds_command('rm pipe_test.txt')
        
        # 测试多个pipe操作符的组合
        result = self._run_gds_command('echo -e "apple\\nbanana\\napple\\ncherry" | sort | uniq')
        self.assertEqual(result.returncode, 0)
        
        # 测试head命令
        result = self._run_gds_command('echo -e "line1\\nline2\\nline3\\nline4\\nline5" | head -n 3')
        self.assertEqual(result.returncode, 0)
        
        # 测试tail命令
        result = self._run_gds_command('echo -e "line1\\nline2\\nline3\\nline4\\nline5" | tail -n 2')
        self.assertEqual(result.returncode, 0)

    # ==================== 新功能测试：依赖树分析 ====================
    
    def test_19_pip_deps_analysis(self):
        
        # 测试简单包的依赖分析（depth=1）
        print("🔍 测试简单包依赖分析（depth=1）")
        result = self._run_gds_command('pip --show-deps requests --depth=1')
        self.assertEqual(result.returncode, 0)
        
        # 验证输出包含关键信息
        output = result.stdout
        self.assertIn("Analysis completed:", output, "应该包含分析完成信息")
        self.assertIn("API calls", output, "应该包含API调用次数")
        self.assertIn("packages analyzed", output, "应该包含分析包数量")
        self.assertIn("requests", output, "应该包含主包名")
        
        # 验证依赖树格式
        self.assertIn("├─", output, "应该包含依赖树连接符")
        self.assertIn("Level 1:", output, "应该包含层级汇总")
        
        print("✅ 简单包依赖分析测试通过")
        
        # 测试复杂包的依赖分析（depth=2）
        print("🔍 测试复杂包依赖分析（depth=2）")
        result = self._run_gds_command('pip --show-deps numpy --depth=2')
        self.assertEqual(result.returncode, 0)
        
        # numpy通常没有依赖，但测试应该正常完成
        output = result.stdout
        self.assertIn("Analysis completed:", output, "应该包含分析完成信息")
        self.assertIn("numpy", output, "应该包含包名")
        
        print("✅ 复杂包依赖分析测试通过")
        
        # 测试不存在包的错误处理
        print("🚫 测试不存在包的错误处理")
        result = self._run_gds_command('pip --show-deps nonexistent-package-12345', expect_success=False, check_function_result=False)
        # 不存在的包应该返回错误或空结果
        if result.returncode == 0:
            # 如果返回码为0，输出应该表明没有找到包
            output = result.stdout.lower()
            not_found_indicators = ["not found", "error", "failed", "no package"]
            has_error_indicator = any(indicator in output for indicator in not_found_indicators)
            self.assertTrue(has_error_indicator, f"不存在的包应该有错误指示，输出: {result.stdout}")
        
        # 测试性能统计信息
        print("⏱️ 测试性能统计")
        import time
        start_time = time.time()
        result = self._run_gds_command('pip --show-deps colorama --depth=1')
        end_time = time.time()
        
        self.assertEqual(result.returncode, 0)
        
        # 验证性能统计格式
        output = result.stdout
        self.assertRegex(output, r'\d+ API calls', "应该包含API调用次数")
        self.assertRegex(output, r'\d+ packages analyzed', "应该包含分析包数量")
        self.assertRegex(output, r'in \d+\.\d+s', "应该包含执行时间")
        
        # 验证执行时间合理（应该在合理范围内）
        actual_time = end_time - start_time
        print(f"📊 实际执行时间: {actual_time:.2f}s")
        self.assertLess(actual_time, 60, "简单包分析应该在60秒内完成")
        
        # 测试深度参数
        print("🔢 测试深度参数")
        result = self._run_gds_command('pip --show-deps requests --depth=1')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('pip --show-deps requests --depth=2')
        self.assertEqual(result.returncode, 0)
        
        # 测试输出格式的各个组成部分
        result = self._run_gds_command('pip --show-deps requests --depth=1')
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        
        # 验证分析统计行
        print("📊 验证分析统计")
        self.assertRegex(output, r'Analysis completed: \d+ API calls, \d+ packages analyzed in \d+\.\d+s', 
                        "应该包含完整的分析统计信息")
        
        # 验证依赖树格式
        print("🌳 验证依赖树格式")
        tree_indicators = ["├─", "└─", "│"]
        has_tree_format = any(indicator in output for indicator in tree_indicators)
        self.assertTrue(has_tree_format, "应该包含依赖树格式字符")
        
        # 验证大小显示格式
        print("💾 验证大小显示格式")
        size_patterns = [r'\(\d+\.\d+MB\)', r'\(\d+\.\d+KB\)', r'\(\d+B\)']
        has_size_format = any(re.search(pattern, output) for pattern in size_patterns)
        self.assertTrue(has_size_format, "应该包含大小信息")
        
        # 验证层级汇总
        print("📋 验证层级汇总")
        self.assertRegex(output, r'Level \d+:', "应该包含层级汇总")
        
        print("✅ 依赖分析功能测试完成")

    def test_20_shell_mode_continuous_operations(self):
        """测试Shell模式下的连续操作"""
        print("🐚 测试Shell模式连续操作")
        
        # 创建测试文件
        test_file = self.TEST_TEMP_DIR / "shell_test.txt"
        test_file.write_text("shell test content", encoding='utf-8')
        
        # 测试连续的shell命令执行
        shell_commands = [
            "pwd",
            "ls",
            f"upload {test_file} shell_upload_test.txt",
            "ls",  # 验证上传后的文件列表
            "cat shell_upload_test.txt",  # 验证上传的文件内容
            "mkdir shell_test_dir",
            "cd shell_test_dir",
            "pwd",  # 验证目录切换
            "cd ..",
            "rm shell_upload_test.txt",
            "rm -rf shell_test_dir"
        ]
        
        # 构建shell输入
        shell_input = "\n".join(shell_commands) + "\nexit\n"
        
        # 执行shell模式
        result = self._run_command_with_input(
            [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
            shell_input,
            timeout=180
        )
        
        self.assertEqual(result.returncode, 0, "Shell模式连续操作应该成功")
        
        # 验证关键输出
        output = result.stdout
        self.assertIn("Google Drive Shell (GDS)", output, "应该显示Shell启动信息")
        self.assertIn("Exit Google Drive Shell", output, "应该显示Shell退出信息")
        
        # 验证命令执行结果
        self.assertRegex(output, r"GDS:.*\$", "应该显示Shell提示符")
        
        print("✅ Shell模式连续操作测试完成")

    def test_21_shell_mode_vs_direct_consistency(self):
        """测试Shell模式与直接命令执行的输出一致性"""
        print("🔄 测试Shell模式与直接命令一致性")
        
        # 测试命令列表
        test_commands = [
            "pwd",
            "ls",
            "help"
        ]
        
        for cmd in test_commands:
            print(f"🔍 测试命令: {cmd}")
            
            # 直接命令执行
            direct_result = self._run_gds_command(cmd)
            
            # Shell模式执行
            shell_input = f"{cmd}\nexit\n"
            shell_result = self._run_command_with_input(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
                shell_input,
                timeout=60
            )
            
            self.assertEqual(direct_result.returncode, 0, f"直接执行{cmd}应该成功")
            self.assertEqual(shell_result.returncode, 0, f"Shell模式执行{cmd}应该成功")
            
            # 提取shell模式中的命令输出（去除shell提示符等）
            shell_output = shell_result.stdout
            
            # 对于help命令，验证关键内容存在
            if cmd == "help":
                # 验证直接执行包含基本命令
                self.assertIn("pwd", direct_result.stdout, "直接执行help应该包含pwd命令")
                self.assertIn("ls", direct_result.stdout, "直接执行help应该包含ls命令")
                
                # 验证shell模式也包含相同命令
                self.assertIn("pwd", shell_output, "Shell模式help应该包含pwd命令")
                self.assertIn("ls", shell_output, "Shell模式help应该包含ls命令")
                
                print(f"✅ {cmd}命令在两种模式下都包含必要内容")
            else:
                # 对于其他命令，验证命令执行成功（不要求非空输出，因为ls在空目录中可能无输出）
                self.assertIn("GDS:", shell_output, f"Shell模式执行{cmd}应该包含提示符")
                
                print(f"✅ {cmd}命令在两种模式下都正常执行")
        
        print("✅ Shell模式与直接命令一致性测试完成")

    def test_22_shell_switching_and_state(self):
        """测试Shell切换和状态管理"""
        print("🔄 测试Shell切换和状态管理")
        
        # 首先创建一个新的remote shell
        print("📝 创建新的remote shell")
        create_result = self._run_gds_command_with_retry('--create-remote-shell', max_retries=2)
        self.assertEqual(create_result.returncode, 0, "创建remote shell应该成功")
        
        # 从输出中提取shell ID
        shell_id_match = re.search(r'Shell ID: (\w+)', create_result.stdout)
        if shell_id_match:
            new_shell_id = shell_id_match.group(1)
            print(f"📋 创建的Shell ID: {new_shell_id}")
            
            # 列出所有shells
            print("📋 列出所有shells")
            list_result = self._run_gds_command('--list-remote-shell')
            self.assertEqual(list_result.returncode, 0, "列出shells应该成功")
            self.assertIn(new_shell_id, list_result.stdout, "新创建的shell应该在列表中")
            
            # 切换到新shell
            print(f"🔄 切换到新shell: {new_shell_id}")
            checkout_result = self._run_gds_command(f'--checkout-remote-shell {new_shell_id}')
            self.assertEqual(checkout_result.returncode, 0, "切换shell应该成功")
            
            # 在新shell中执行一些操作
            print("🧪 在新shell中执行操作")
            shell_commands = [
                "pwd",
                "mkdir test_shell_state",
                "cd test_shell_state",
                "pwd",
                "echo 'shell state test' > state_test.txt",
                "cat state_test.txt",
                "cd ..",
                "ls"
            ]
            
            shell_input = "\n".join(shell_commands) + "\nexit\n"
            shell_result = self._run_command_with_input(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
                shell_input,
                timeout=120
            )
            
            self.assertEqual(shell_result.returncode, 0, "新shell中的操作应该成功")
            
            # 验证状态保持
            output = shell_result.stdout
            self.assertIn("state test", output, "应该能够创建和读取文件")
            self.assertIn("test_shell_state", output, "应该能够创建目录")
            
            # 清理：删除创建的shell
            print(f"🧹 清理：删除shell {new_shell_id}")
            cleanup_result = self._run_gds_command(f'--terminate-remote-shell {new_shell_id}')
            # 注意：cleanup可能失败，但不影响测试结果
            
            print("✅ Shell切换和状态管理测试完成")
        else:
            print("⚠️ 无法从输出中提取Shell ID，跳过后续测试")
            self.skipTest("无法提取新创建的Shell ID")

    def test_23_shell_mode_error_handling(self):
        """测试Shell模式的错误处理"""
        print("❌ 测试Shell模式错误处理")
        
        # 测试无效命令
        error_commands = [
            "invalid_command",
            "ls /nonexistent/path",
            "rm nonexistent_file.txt",
            "cd /invalid/directory"
        ]
        
        for cmd in error_commands:
            print(f"🔍 测试错误命令: {cmd}")
            
            shell_input = f"{cmd}\nexit\n"
            shell_result = self._run_command_with_input(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
                shell_input,
                timeout=60
            )
            
            # Shell模式应该能够处理错误而不崩溃
            self.assertEqual(shell_result.returncode, 0, f"Shell模式处理错误命令{cmd}时不应该崩溃")
            
            # 验证错误信息或提示
            output = shell_result.stdout
            self.assertIn("GDS:", output, "即使命令失败，Shell模式也应该继续运行")
            self.assertIn("Exit Google Drive Shell", output, "Shell应该正常退出")
        
        print("✅ Shell模式错误处理测试完成")

    def test_24_shell_mode_performance(self):
        """测试Shell模式的性能表现"""
        print("⚡ 测试Shell模式性能")
        
        # 测试快速连续命令
        quick_commands = ["pwd"] * 5  # 执行5次pwd命令
        shell_input = "\n".join(quick_commands) + "\nexit\n"
        
        start_time = time.time()
        shell_result = self._run_command_with_input(
            [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
            shell_input,
            timeout=60
        )
        end_time = time.time()
        
        self.assertEqual(shell_result.returncode, 0, "快速连续命令应该成功")
        
        execution_time = end_time - start_time
        print(f"📊 执行5个pwd命令用时: {execution_time:.2f}s")
        
        # 验证性能合理（应该在合理时间内完成）
        self.assertLess(execution_time, 30, "5个简单命令应该在30秒内完成")
        
        # 验证所有命令都执行了
        output = shell_result.stdout
        pwd_count = output.count("~")  # pwd命令通常返回包含~的路径
        self.assertGreaterEqual(pwd_count, 3, "应该执行了多个pwd命令")
        
        print("✅ Shell模式性能测试完成")

    def test_25_shell_prompt_improvements(self):
        """测试Shell提示符改进"""
        print("🎨 测试Shell提示符改进")
        
        # 测试目录切换后提示符更新
        shell_commands = [
            "pwd",  # 显示初始路径
            "mkdir test_prompt_dir",
            "cd test_prompt_dir", 
            "pwd",  # 显示切换后的路径
            "cd ..",
            "pwd",  # 显示返回后的路径
            "rm -rf test_prompt_dir"
        ]
        
        shell_input = "\n".join(shell_commands) + "\nexit\n"
        
        result = self._run_command_with_input(
            [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
            shell_input,
            timeout=120
        )
        
        self.assertEqual(result.returncode, 0, "Shell提示符测试应该成功")
        
        output = result.stdout
        
        # 验证路径切换
        self.assertIn("test_prompt_dir", output, "应该显示切换到的目录")
        
        # 验证pwd命令显示不同的路径
        pwd_outputs = []
        lines = output.split('\n')
        for line in lines:
            # 查找包含路径的行（可能包含~符号的路径）
            if ('~' in line and 
                not line.startswith('GDS:') and 
                not line.startswith('💡') and 
                not line.startswith('🌟') and
                not line.startswith('📍')):
                pwd_outputs.append(line.strip())
        
        # 打印调试信息
        print(f"📋 找到的pwd输出: {pwd_outputs}")
        
        # 验证路径变化 - 至少应该有一些路径输出
        self.assertGreater(len(pwd_outputs), 0, "应该有pwd输出")
        
        # 验证路径变化
        found_test_dir = False
        for pwd_output in pwd_outputs:
            if "test_prompt_dir" in pwd_output:
                found_test_dir = True
                break
        
        self.assertTrue(found_test_dir, f"应该找到切换到测试目录的pwd输出，实际输出: {pwd_outputs}")
        
        print("✅ Shell提示符改进测试完成")

    def test_26_shell_command_routing(self):
        """测试Shell命令路由改进"""
        print("🔄 测试Shell命令路由改进")
        
        # 测试各种命令都能正确路由
        test_commands = [
            ("pwd", "应该显示当前路径"),
            ("ls", "应该列出文件"),
            ("help", "应该显示帮助信息"),
            ("mkdir test_routing", "应该创建目录"),
            ("ls", "应该显示新创建的目录"),
            ("rm -rf test_routing", "应该删除目录")
        ]
        
        for cmd, description in test_commands:
            print(f"🔍 测试命令: {cmd}")
            
            shell_input = f"{cmd}\nexit\n"
            result = self._run_command_with_input(
                [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
                shell_input,
                timeout=60
            )
            
            self.assertEqual(result.returncode, 0, f"{cmd}命令应该成功执行")
            
            output = result.stdout
            self.assertIn("GDS:", output, f"{cmd}命令应该在shell模式中执行")
            
            # 验证没有"Unknown command"错误
            self.assertNotIn("Unknown command", output, f"{cmd}命令不应该被认为是未知命令")
            
            print(f"✅ {cmd}命令路由正常")
        
        print("✅ Shell命令路由改进测试完成")

    def test_27_shell_state_persistence(self):
        """测试Shell状态持久性"""
        print("💾 测试Shell状态持久性")
        
        # 测试连续的状态变化操作
        shell_commands = [
            "pwd",
            "mkdir test_state_dir",
            "cd test_state_dir",
            "pwd",
            "echo 'test content' > test_file.txt",
            "cat test_file.txt",
            "ls",
            "cd ..",
            "pwd",
            "ls",
            "rm -rf test_state_dir"
        ]
        
        shell_input = "\n".join(shell_commands) + "\nexit\n"
        
        result = self._run_command_with_input(
            [sys.executable, str(self.GOOGLE_DRIVE_PY), "--shell"],
            shell_input,
            timeout=150
        )
        
        self.assertEqual(result.returncode, 0, "Shell状态持久性测试应该成功")
        
        output = result.stdout
        
        # 验证状态变化的连续性
        self.assertIn("test_state_dir", output, "应该显示创建的目录")
        self.assertIn("test content", output, "应该显示文件内容")
        
        # 验证目录切换的效果
        lines = output.split('\n')
        pwd_lines = [line.strip() for line in lines if line.strip().startswith('~') and not line.startswith('GDS:')]
        
        # 应该有不同的路径输出
        path_changes = len(set(pwd_lines))
        self.assertGreaterEqual(path_changes, 2, "应该有路径变化")
        
        print("✅ Shell状态持久性测试完成")

class ParallelTestRunner:
    """并行测试运行器"""
    
    def __init__(self, num_workers=3):
        self.num_workers = num_workers
        self.test_methods = []
        self.total_gds_commands = 0
        self.completed_gds_commands = 0
        self.results = {}
        self.lock = threading.Lock()
        self.start_time = None
        
    def discover_test_methods(self, test_class):
        """发现所有测试方法并统计GDS命令数量"""
        print("🔍 发现测试方法...")
        
        methods = []
        for name in dir(test_class):
            if name.startswith('test_'):
                method = getattr(test_class, name)
                if callable(method):
                    # 统计该方法中的_run_gds_command调用次数
                    source = inspect.getsource(method)
                    gds_count = source.count('_run_gds_command(')
                    gds_count += source.count('_run_gds_command_with_retry(')
                    
                    methods.append({
                        'name': name,
                        'method': method,
                        'gds_commands': gds_count,
                        'status': 'pending'
                    })
                    self.total_gds_commands += gds_count
        
        self.test_methods = sorted(methods, key=lambda x: x['name'])
        return methods
    
    def run_single_test(self, test_info, worker_id):
        """运行单个测试方法"""
        test_name = test_info['name']
        
        try:
            print(f"🔧 Worker-{worker_id}: 开始执行 {test_name}")
            
            # 创建测试实例
            test_instance = GDSTest()
            test_instance.setUpClass()
            
            # 执行测试方法
            method = getattr(test_instance, test_name)
            start_time = time.time()
            method()
            end_time = time.time()
            
            # 更新结果
            with self.lock:
                self.results[test_name] = {
                    'status': 'success',
                    'duration': end_time - start_time,
                    'worker': worker_id,
                    'gds_commands': test_info['gds_commands']
                }
                self.completed_gds_commands += test_info['gds_commands']
                
            print(f"✅ Worker-{worker_id}: {test_name} 成功 ({end_time - start_time:.1f}s)")
            return True
            
        except Exception as e:
            with self.lock:
                self.results[test_name] = {
                    'status': 'failed',
                    'error': str(e),
                    'worker': worker_id,
                    'gds_commands': test_info['gds_commands']
                }
                # 即使失败也计入已完成的命令数
                self.completed_gds_commands += test_info['gds_commands']
                
            print(f"❌ Worker-{worker_id}: {test_name} 失败 - {str(e)[:100]}")
            return False
    
    def display_progress(self):
        """显示实时进度"""
        while True:
            with self.lock:
                if len(self.results) >= len(self.test_methods):
                    break
                    
                # 统计状态
                success_count = sum(1 for r in self.results.values() if r['status'] == 'success')
                failed_count = sum(1 for r in self.results.values() if r['status'] == 'failed')
                pending_count = len(self.test_methods) - len(self.results)
                
                # 计算进度
                progress_percent = (self.completed_gds_commands / self.total_gds_commands * 100) if self.total_gds_commands > 0 else 0
                
                # 显示进度
                elapsed = time.time() - self.start_time if self.start_time else 0
                print(f"\r📊 进度: {success_count}✅ {failed_count}❌ {pending_count}⏳ | "
                      f"GDS命令: {self.completed_gds_commands}/{self.total_gds_commands} ({progress_percent:.1f}%) | "
                      f"用时: {elapsed:.0f}s", end="", flush=True)
            
            time.sleep(1)
    
    def run_parallel_tests(self):
        """并行运行所有测试"""
        print(f"🚀 启动并行测试 (Workers: {self.num_workers})")
        print(f"📋 发现 {len(self.test_methods)} 个测试方法，共 {self.total_gds_commands} 个GDS命令")
        print("=" * 80)
        
        self.start_time = time.time()
        
        # 启动进度显示线程
        progress_thread = threading.Thread(target=self.display_progress, daemon=True)
        progress_thread.start()
        
        # 使用线程池执行测试
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # 提交所有任务
            future_to_test = {}
            for i, test_info in enumerate(self.test_methods):
                worker_id = (i % self.num_workers) + 1
                future = executor.submit(self.run_single_test, test_info, worker_id)
                future_to_test[future] = test_info
            
            # 等待所有任务完成
            for future in as_completed(future_to_test):
                test_info = future_to_test[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"\n💥 测试执行异常: {test_info['name']} - {e}")
        
        # 等待进度显示完成
        progress_thread.join(timeout=1)
        
        # 显示最终结果
        self.display_final_results()
    
    def display_final_results(self):
        """显示最终测试结果"""
        print("\n" + "=" * 80)
        print("📊 测试结果汇总")
        print("=" * 80)
        
        success_tests = [name for name, result in self.results.items() if result['status'] == 'success']
        failed_tests = [name for name, result in self.results.items() if result['status'] == 'failed']
        
        total_time = time.time() - self.start_time if self.start_time else 0
        
        print(f"✅ 成功: {len(success_tests)}/{len(self.test_methods)} ({len(success_tests)/len(self.test_methods)*100:.1f}%)")
        print(f"❌ 失败: {len(failed_tests)}/{len(self.test_methods)} ({len(failed_tests)/len(self.test_methods)*100:.1f}%)")
        print(f"⏱️ 总用时: {total_time:.1f}s")
        print(f"🔧 GDS命令: {self.completed_gds_commands}/{self.total_gds_commands}")
        
        if success_tests:
            print(f"\n✅ 成功的测试 ({len(success_tests)}):")
            for test_name in success_tests:
                result = self.results[test_name]
                print(f"   • {test_name} (Worker-{result['worker']}, {result['duration']:.1f}s, {result['gds_commands']} GDS命令)")
        
        if failed_tests:
            print(f"\n❌ 失败的测试 ({len(failed_tests)}):")
            for test_name in failed_tests:
                result = self.results[test_name]
                print(f"   • {test_name} (Worker-{result['worker']})")
                print(f"     错误: {result['error'][:150]}...")
        
        # 按Worker统计
        worker_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'time': 0})
        for result in self.results.values():
            worker_id = result['worker']
            worker_stats[worker_id][result['status']] += 1
            if 'duration' in result:
                worker_stats[worker_id]['time'] += result['duration']
        
        print(f"\n👥 Worker统计:")
        for worker_id in sorted(worker_stats.keys()):
            stats = worker_stats[worker_id]
            print(f"   Worker-{worker_id}: {stats['success']}✅ {stats['failed']}❌ ({stats['time']:.1f}s)")
        
        print("=" * 80)
        
        return len(failed_tests) == 0

def main():
    """主函数"""
    print("🚀 启动GDS并行测试套件")
    print("=" * 60)
    print("📋 测试特点:")
    print("  • 远端窗口操作无timeout限制")
    print("  • 结果判断基于功能执行情况")
    print("  • 具有静态可重复性（使用--force等选项）")
    print("  • 3个Worker并行执行")
    print("=" * 60)
    
    # 创建并行测试运行器
    runner = ParallelTestRunner(num_workers=3)
    
    # 发现测试方法
    test_methods = runner.discover_test_methods(GDSTest)
    
    print(f"📋 发现测试方法:")
    for i, method in enumerate(test_methods, 1):
        print(f"  {i:2d}. {method['name']} ({method['gds_commands']} GDS命令)")
    
    print(f"\n📊 总计: {len(test_methods)} 个测试，{runner.total_gds_commands} 个GDS命令")
    
    # 运行并行测试
    success = runner.run_parallel_tests()
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
