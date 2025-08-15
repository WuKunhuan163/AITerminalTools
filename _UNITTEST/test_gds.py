#!/usr/bin/env python3
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
from pathlib import Path
from datetime import datetime

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
        
        print(f"📁 远端测试目录: ~/tmp/{cls.test_folder}")
        print(f"📂 本地测试数据: {cls.TEST_DATA_DIR}")
        print(f"📂 本地临时文件: {cls.TEST_TEMP_DIR}")
        
        # 检查GOOGLE_DRIVE.py是否可用
        if not cls.GOOGLE_DRIVE_PY.exists():
            raise unittest.SkipTest(f"GOOGLE_DRIVE.py not found at {cls.GOOGLE_DRIVE_PY}")
        
        # 创建远端测试目录并切换到该目录
        cls._setup_remote_test_directory()
        
        print("✅ 测试环境设置完成")
    
    @classmethod
    def _setup_remote_test_directory(cls):
        """设置远端测试目录"""
        print(f"📁 创建远端测试目录: ~/tmp/{cls.test_folder}")
        
        # 创建测试目录
        result = subprocess.run(
            f"python3 {cls.GOOGLE_DRIVE_PY} --shell 'mkdir -p ~/tmp/{cls.test_folder}'",
            shell=True,
            capture_output=True,
            text=True,
            cwd=cls.BIN_DIR
        )
        
        if result.returncode != 0:
            print(f"⚠️ 创建远端测试目录失败: {result.stderr}")
        
        # 切换到测试目录
        result = subprocess.run(
            f"python3 {cls.GOOGLE_DRIVE_PY} --shell 'cd ~/tmp/{cls.test_folder}'",
            shell=True,
            capture_output=True,
            text=True,
            cwd=cls.BIN_DIR
        )
        
        if result.returncode != 0:
            print(f"⚠️ 切换到远端测试目录失败: {result.stderr}")
        else:
            print(f"✅ 已切换到远端测试目录: ~/tmp/{cls.test_folder}")
        
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
        simple_script.write_text('''#!/usr/bin/env python3
print("Hello from remote project!")
print("Current working directory:", __import__("os").getcwd())
import sys
print("Python version:", sys.version)
''')
        
        # 2. 复杂的Python项目结构
        project_dir = cls.TEST_DATA_DIR / "test_project"
        project_dir.mkdir(exist_ok=True)
        
        # main.py
        (project_dir / "main.py").write_text('''#!/usr/bin/env python3
"""
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
        valid_python.write_text('''#!/usr/bin/env python3
"""
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
        invalid_python.write_text('''#!/usr/bin/env python3
"""
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
        
        print(f"📁 创建了测试文件在 {cls.TEST_DATA_DIR}")
    
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
        """验证远端文件是否存在（基于功能结果，不是输出）"""
        result = self._run_gds_command(f'ls {filename}')
        return result.returncode == 0
    
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
    
    # ==================== 基础功能测试 ====================
    
    def test_01_basic_echo_commands(self):
        """测试基础echo命令"""
        print("\n🧪 测试01: 基础echo命令")
        
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
    
    def test_01b_echo_correct_json_syntax(self):
        """测试echo的正确JSON语法（修复后的功能）"""
        print("\n🧪 测试01b: Echo正确JSON语法")
        
        # 使用正确的语法创建JSON文件（单引号包围重定向范围）
        result = self._run_gds_command('\'echo "{\\"name\\": \\"test\\", \\"value\\": 123}" > correct_json.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证JSON文件内容正确（修复后无转义字符）
        self.assertTrue(self._verify_file_exists("correct_json.txt"))
        self.assertTrue(self._verify_file_content_contains("correct_json.txt", '{"name": "test"'))
        self.assertTrue(self._verify_file_content_contains("correct_json.txt", '"value": 123}'))
        
        # 测试echo -e参数处理换行符
        result = self._run_gds_command('echo -e \'Line1\\nLine2\\nLine3\' > multiline.txt')
        self.assertEqual(result.returncode, 0)
        
        # 验证多行文件创建成功
        self.assertTrue(self._verify_file_exists("multiline.txt"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line1"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line2"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line3"))
    
    def test_01b2_echo_quote_parsing_fix(self):
        """测试echo的引号解析修复"""
        print("\n🧪 测试01b2: Echo引号解析修复")
        
        # 测试简单的echo命令，不应该有多重引号
        result = self._run_gds_command('"echo \'test\'"')
        self.assertEqual(result.returncode, 0)
        
        # 验证生成的命令不包含过多引号层级
        # 这个测试主要是检查命令能正常执行，不会因为引号问题而失败
        
    def test_01b3_echo_local_redirect_fix(self):
        """测试echo的本地重定向修复"""
        print("\n🧪 测试01b3: Echo本地重定向修复")
        
        # 使用正确的语法（用引号包围整个命令，避免本地重定向）
        result = self._run_gds_command('\'echo -e "Line1\\nLine2\\nLine3" > multiline.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件在远端创建，而不是本地
        self.assertTrue(self._verify_file_exists("multiline.txt"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line1"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line2"))
        self.assertTrue(self._verify_file_content_contains("multiline.txt", "Line3"))
        
    def test_01b4_echo_local_redirect_test(self):
        """测试echo的本地重定向行为（错误语法示例）"""
        print("\n🧪 测试01b4: Echo本地重定向行为")
        
        # 由于我们现在在本地临时目录中，本地重定向不会污染原始目录
        # 使用错误语法（会导致本地重定向）
        result = self._run_gds_command('echo \'{"name": "test", "value": 123}\' > local_redirect.txt')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件被创建在本地目录（而不是远端）
        local_file = Path("local_redirect.txt")
        self.assertTrue(local_file.exists(), "文件应该在本地被创建")
        
        # 检查本地文件内容
        with open(local_file, 'r') as f:
            content = f.read().strip()
        self.assertEqual(content, '{"name": "test", "value": 123}', "本地文件内容应该正确")
        
        # 验证远端没有这个文件（应该返回False）
        self.assertFalse(self._verify_file_exists("local_redirect.txt"))
    
    def test_01c_echo_create_python_script(self):
        """测试echo创建Python脚本并执行"""
        print("\n🧪 测试01c: Echo创建Python脚本并执行")
        
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
        
        # 修复：使用单引号包围整个命令避免本地重定向
        result = self._run_gds_command(f'\'echo -e "{python_code}" > test_script.py\'')
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
    
    def test_01d_ls_full_path_support(self):
        """测试ls命令的全路径支持（修复后的功能）"""
        print("\n🧪 测试01d: LS全路径支持")
        
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
        result = self._run_gds_command('ls testdir/nonexistent.txt')
        self.assertNotEqual(result.returncode, 0)  # 应该失败
        
        # 测试ls不存在的目录中的文件
        result = self._run_gds_command('ls nonexistent_dir/file.txt')
        self.assertNotEqual(result.returncode, 0)  # 应该失败

    def test_01e_advanced_file_operations(self):
        """测试高级文件操作（从测试10合并）"""
        print("\n🧪 测试01e: 高级文件操作")
        
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
        
        print("✅ 高级文件操作测试完成")

    def test_02_basic_navigation_commands(self):
        """测试基础导航命令和不同路径类型"""
        print("\n🧪 测试02: 基础导航命令和路径类型测试")
        
        # === 基础导航命令 ===
        print("📁 基础导航命令测试")
        
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
    
    def test_03_file_upload_operations(self):
        """测试文件上传操作"""
        print("\n🧪 测试03: 文件上传操作")
        
        # 单文件上传（使用--force确保可重复性）
        simple_script = self.TEST_DATA_DIR / "simple_hello.py"
        result = self._run_gds_command(f'upload --force {simple_script}')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件上传成功（基于功能结果）
        self.assertTrue(self._verify_file_exists("simple_hello.py"))
        
        # 多文件上传（使用--force确保可重复性）
        valid_script = self.TEST_DATA_DIR / "valid_script.py"
        special_file = self.TEST_DATA_DIR / "special_chars.txt"
        result = self._run_gds_command(f'upload --force {valid_script} {special_file}')
        self.assertEqual(result.returncode, 0)
        
        # 验证多文件上传成功
        self.assertTrue(self._verify_file_exists("valid_script.py"))
        self.assertTrue(self._verify_file_exists("special_chars.txt"))
        
        # 文件夹上传（修复：--force参数应该在路径之前）
        project_dir = self.TEST_DATA_DIR / "test_project"
        result = self._run_gds_command(f'upload-folder --force {project_dir}')
        self.assertEqual(result.returncode, 0)
        
        # 验证文件夹上传成功
        self.assertTrue(self._verify_file_exists("test_project"))
    
    def test_03b_large_file_upload_and_performance(self):
        """测试大文件上传和性能（从测试11合并）"""
        print("\n🧪 测试03b: 大文件上传和性能测试")
        
        # 1. 上传大文件（使用--force确保可重复性）
        large_file = self.TEST_DATA_DIR / "large_file.txt"
        result = self._run_gds_command(f'upload --force {large_file}')
        self.assertEqual(result.returncode, 0)
        
        # 验证大文件上传成功（基于功能结果）
        self.assertTrue(self._verify_file_exists("large_file.txt"))
        
        # 2. 读取大文件的部分内容
        result = self._run_gds_command('read large_file.txt 1 10')
        self.assertEqual(result.returncode, 0)
        
        # 3. 在大文件中搜索
        result = self._run_gds_command('grep "Line 500" large_file.txt')
        self.assertEqual(result.returncode, 0)
        
        # 4. 测试缓存机制（第二次读取应该使用缓存）
        import time
        start_time = time.time()
        result1 = self._run_gds_command('read large_file.txt 1 5')
        first_time = time.time() - start_time
        
        start_time = time.time()
        result2 = self._run_gds_command('read large_file.txt 1 5')
        second_time = time.time() - start_time
        
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)
        print(f"📊 首次读取: {first_time:.2f}s, 缓存读取: {second_time:.2f}s")
        
        print("✅ 大文件上传和性能测试完成")
    
    # ==================== 文件编辑测试 ====================
    
    def test_04_file_editing_operations(self):
        """测试文件编辑操作"""
        print("\n🧪 测试04: 文件编辑操作")
        
        # 确保测试文件存在
        if not self._verify_file_exists("simple_hello.py"):
            simple_script = self.TEST_DATA_DIR / "simple_hello.py"
            self._run_gds_command(f'upload --force {simple_script}')
        
        # 基础文本替换编辑
        result = self._run_gds_command('edit simple_hello.py \'[["Hello from remote project!", "Hello from MODIFIED remote project!"]]\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证编辑结果（基于功能结果）
        self.assertTrue(self._verify_file_content_contains("simple_hello.py", "MODIFIED"))
        
        # 行号替换编辑（使用0-based索引）
        result = self._run_gds_command('edit simple_hello.py \'[[[1, 2], "# Modified first line"]]\'')
        self.assertEqual(result.returncode, 0)
        
        # 预览模式编辑（不实际修改文件）
        result = self._run_gds_command('edit --preview simple_hello.py \'[["print", "# print"]]\'')
        self.assertEqual(result.returncode, 0)
        
        # 备份模式编辑
        result = self._run_gds_command('edit --backup simple_hello.py \'[["Modified", "Updated"]]\'')
        self.assertEqual(result.returncode, 0)
    
    # ==================== 文件读取和搜索测试 ====================
    
    def test_05_file_reading_and_search(self):
        """测试文件读取和搜索操作"""
        print("\n🧪 测试05: 文件读取和搜索操作")
        
        # 确保测试文件存在
        if not self._verify_file_exists("simple_hello.py"):
            simple_script = self.TEST_DATA_DIR / "simple_hello.py"
            self._run_gds_command(f'upload --force {simple_script}')
        
        # cat命令读取文件
        result = self._run_gds_command('cat simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # read命令读取文件（带行号）
        result = self._run_gds_command('read simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # read命令读取指定行范围
        result = self._run_gds_command('read simple_hello.py 1 3')
        self.assertEqual(result.returncode, 0)
        
        # grep命令搜索内容
        result = self._run_gds_command('grep "print" simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # find命令查找文件
        result = self._run_gds_command('find . -name "*.py"')
        self.assertEqual(result.returncode, 0)
        
        # --force选项强制重新下载
        result = self._run_gds_command('read --force simple_hello.py')
        self.assertEqual(result.returncode, 0)
    
    def test_05b_file_error_handling(self):
        """测试文件操作错误处理（从测试12合并）"""
        print("\n🧪 测试05b: 文件操作错误处理")
        
        # 1. 测试不存在的文件
        print("🚫 测试cat不存在的文件")
        result = self._run_gds_command('cat nonexistent_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "cat不存在的文件应该返回非零退出码")
        
        # 2. 测试read不存在的文件
        print("🚫 测试read不存在的文件")
        result = self._run_gds_command('read nonexistent_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "read不存在的文件应该返回非零退出码")
        
        # 3. 测试grep不存在的文件
        print("🚫 测试grep不存在的文件")
        result = self._run_gds_command('grep "test" nonexistent_file.txt', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0, "grep不存在的文件应该返回非零退出码")
        
        # 4. 测试特殊字符文件处理
        print("✨ 测试特殊字符文件处理")
        if not self._verify_file_exists("special_chars.txt"):
            special_file = self.TEST_DATA_DIR / "special_chars.txt"
            self._run_gds_command(f'upload --force {special_file}')
        
        result = self._run_gds_command('cat special_chars.txt')
        self.assertEqual(result.returncode, 0, "特殊字符文件应该能正常读取")
        
        print("✅ 文件操作错误处理测试完成")
    
    # ==================== 真实远端项目开发场景测试 ====================
    
    def test_05_real_world_development_workflow(self):
        """测试真实的远端项目开发工作流程"""
        print("\n🧪 测试05: 真实远端项目开发工作流程")
        
        # === 阶段1: 项目初始化 ===
        print("📦 阶段1: 项目初始化")
        
        # 创建项目目录
        result = self._run_gds_command('mkdir -p myproject/src myproject/tests myproject/docs')
        self.assertEqual(result.returncode, 0)
        
        # 创建项目基础文件
        result = self._run_gds_command('\'echo "# My Project\\nA sample Python project for testing" > myproject/README.md\'')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('\'echo "requests>=2.25.0\\nnumpy>=1.20.0\\npandas>=1.3.0" > myproject/requirements.txt\'')
        self.assertEqual(result.returncode, 0)
        
        # 创建主应用文件
        main_py_content = '''#!/usr/bin/env python3
"""
主应用文件
"""
import sys
import json
from datetime import datetime

def load_config(config_file="config.json"):
    """加载配置文件"""
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_file} 不存在")
        return {}

def process_data(data_list):
    """处理数据列表"""
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
    """主函数"""
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
        
        result = self._run_gds_command(f'\'echo "{main_py_content}" > myproject/src/main.py\'')
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
        result = self._run_gds_command('grep "def " main.py')
        self.assertEqual(result.returncode, 0)
        
        # 查看配置文件内容
        result = self._run_gds_command('cat config.json')
        self.assertEqual(result.returncode, 0)
        
        # 读取代码的特定行
        result = self._run_gds_command('read main.py 1 10')
        self.assertEqual(result.returncode, 0)
        
        # 编辑代码：添加更多功能
        result = self._run_gds_command('edit main.py \'[["处理示例数据", "处理示例数据（已优化）"]]\'')
        self.assertEqual(result.returncode, 0)
        
        # 验证编辑结果
        self.assertTrue(self._verify_file_content_contains("main.py", "已优化"))
        
        # === 阶段5: 验证测试 ===
        print("✅ 阶段5: 验证测试")
        
        # 最终运行测试
        result = self._run_gds_command('python main.py')
        self.assertEqual(result.returncode, 0)
        
        # 检查项目文件
        result = self._run_gds_command('find ../.. -name "*.py"')
        self.assertEqual(result.returncode, 0)
        
        # 查看项目结构
        result = self._run_gds_command('ls -R ../..')
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
    
    def test_06_project_deployment_scenario(self):
        """测试完整项目部署场景"""
        print("\n🧪 测试06: 项目部署场景")
        
        # 1. 上传项目文件夹（修复：--force参数应该在路径之前）
        project_dir = self.TEST_DATA_DIR / "test_project"
        result = self._run_gds_command(f'upload-folder --force {project_dir}')
        self.assertEqual(result.returncode, 0)
        
        # 验证项目上传成功（基于功能结果）
        self.assertTrue(self._verify_file_exists("test_project"))
        
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
    
    def test_07_code_execution_scenario(self):
        """测试代码执行场景"""
        print("\n🧪 测试07: 代码执行场景")
        
        # 确保项目文件存在（修复：--force参数应该在路径之前）
        if not self._verify_file_exists("test_project"):
            project_dir = self.TEST_DATA_DIR / "test_project"
            self._run_gds_command(f'upload-folder --force {project_dir}')
        
        # 1. 执行简单Python脚本
        if not self._verify_file_exists("simple_hello.py"):
            simple_script = self.TEST_DATA_DIR / "simple_hello.py"
            self._run_gds_command(f'upload --force {simple_script}')
        
        result = self._run_gds_command('python simple_hello.py')
        self.assertEqual(result.returncode, 0)
        
        # 2. 执行Python代码片段
        result = self._run_gds_command('python -c "print(\\"Hello from Python code!\\"); import os; print(os.getcwd())"')
        self.assertEqual(result.returncode, 0)
        
        # 3. 执行项目主文件
        result = self._run_gds_command('cd test_project && python main.py')
        self.assertEqual(result.returncode, 0)
    
    # ==================== 虚拟环境管理测试 ====================
    
    def test_08_virtual_environment_workflow(self):
        """测试虚拟环境工作流程和功能验证"""
        print("\n🧪 测试08: 虚拟环境工作流程和功能验证")
        
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
        
        # 7. 验证包在未激活状态下不可用（应该失败）
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama imported\\")"', expect_success=False, check_function_result=False)
        self.assertNotEqual(result.returncode, 0)  # 应该失败，因为colorama不在系统环境中
        
        # 8. 重新激活环境验证包仍然可用
        result = self._run_gds_command(f'venv --activate {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command('python -c "import colorama; print(\\"colorama re-imported successfully\\")"')
        self.assertEqual(result.returncode, 0)
        self.assertIn("colorama re-imported successfully", result.stdout)
        
        # 9. 最终清理：取消激活并删除虚拟环境
        result = self._run_gds_command('venv --deactivate')
        self.assertEqual(result.returncode, 0)
        
        result = self._run_gds_command(f'venv --delete {venv_name}')
        self.assertEqual(result.returncode, 0)
        
        print("✅ 虚拟环境功能验证完成")
    
    # ==================== Linter功能测试 ====================
    
    def test_09_linter_functionality(self):
        """测试Linter语法检查功能"""
        print("\n🧪 测试09: Linter功能测试")
        
        # 强制上传测试文件（确保文件存在）
        print("📤 上传测试文件...")
        valid_script = self.TEST_DATA_DIR / "valid_script.py"
        result = self._run_gds_command(f'upload --force {valid_script}')
        self.assertEqual(result.returncode, 0, "valid_script.py上传失败")
        
        invalid_script = self.TEST_DATA_DIR / "invalid_script.py"
        result = self._run_gds_command(f'upload --force {invalid_script}')
        self.assertEqual(result.returncode, 0, "invalid_script.py上传失败")
        
        json_file = self.TEST_DATA_DIR / "valid_config.json"
        result = self._run_gds_command(f'upload --force {json_file}')
        self.assertEqual(result.returncode, 0, "valid_config.json上传失败")
        
        # 验证文件上传成功
        self.assertTrue(self._verify_file_exists("valid_script.py"), "valid_script.py文件不存在")
        self.assertTrue(self._verify_file_exists("invalid_script.py"), "invalid_script.py文件不存在")
        self.assertTrue(self._verify_file_exists("valid_config.json"), "valid_config.json文件不存在")
        
        # 1. 测试语法正确的文件
        print("✅ 测试语法正确的Python文件")
        result = self._run_gds_command('linter valid_script.py')
        self.assertEqual(result.returncode, 0)
        
        # 2. 测试语法错误的文件
        print("❌ 测试语法错误的Python文件")
        result = self._run_gds_command('linter invalid_script.py', expect_success=False, check_function_result=False)
        # 语法错误的文件应该返回非零退出码或包含错误信息
        if result.returncode == 0:
            # 如果返回码为0，检查输出是否包含错误信息
            self.assertTrue("error" in result.stdout.lower() or "syntax" in result.stdout.lower(), 
                          f"语法错误文件应该报告错误，但输出为: {result.stdout}")
        
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
        
        print("✅ Linter功能测试完成")
    
    # ==================== 边缘情况和错误处理测试 ====================
    
    def test_12_empty_directory_upload(self):
        """测试空目录上传（保留的边缘情况测试）"""
        print("\n🧪 测试12: 空目录上传测试")
        
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
        
        result = self._run_gds_command(f'upload-folder --force {empty_dir}')
        self.assertEqual(result.returncode, 0)
        
        # 验证空目录上传成功
        self.assertTrue(self._verify_file_exists("empty_test_dir"))
        
        print("✅ 空目录上传测试完成")
    
    # ==================== 并发和批量操作测试 ====================
    
    def test_13_concurrent_and_batch_operations(self):
        """测试并发和批量操作"""
        print("\n🧪 测试13: 并发和批量操作")
        
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
    
    # ==================== 清理测试 ====================
    
    def test_99_cleanup_test_environment(self):
        """清理测试环境"""
        print("\n🧹 清理测试环境...")
        
        # 清理远端测试文件和目录
        cleanup_items = [
            "test_echo.txt", "complex_echo.txt", "json_echo.txt", "chinese_echo.txt", "echo_multiline.txt",
            "correct_json.txt", "multiline.txt", "test_script.py", "test_config.json",
            "testdir", "testfile.txt",  # ls全路径测试文件
            "advanced_project",  # 高级文件操作测试目录
            "path_test",  # 导航测试目录
            "test_file.txt",  # 导航测试文件
            "test_dir", "simple_hello.py", "valid_script.py", 
            "invalid_script.py", "special_chars.txt", "test_project", 
            "large_file.txt", "valid_config.json", "empty_test_dir",
            "batch_file1.txt", "batch_file2.txt", "batch_file3.txt",
            "myproject"  # 真实开发场景创建的项目目录
        ]
        
        for item in cleanup_items:
            try:
                result = self._run_gds_command(f'rm -rf {item}', expect_success=False, check_function_result=False)
                # 清理命令可能部分失败，这是正常的
            except:
                pass  # 忽略清理错误
        
        # 清理本地临时文件
        temp_files = list(self.TEST_TEMP_DIR.glob("*"))
        for temp_file in temp_files:
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                elif temp_file.is_dir():
                    import shutil
                    shutil.rmtree(temp_file)
            except:
                pass  # 忽略清理错误
        
        print("✅ 测试环境清理完成")

def main():
    """主函数"""
    print("🚀 启动GDS全面测试套件")
    print("=" * 60)
    print("📋 测试特点:")
    print("  • 远端窗口操作无timeout限制")
    print("  • 结果判断基于功能执行情况")
    print("  • 具有静态可重复性（使用--force等选项）")
    print("=" * 60)
    
    # 运行测试
    unittest.main(verbosity=2)

if __name__ == "__main__":
    main()
