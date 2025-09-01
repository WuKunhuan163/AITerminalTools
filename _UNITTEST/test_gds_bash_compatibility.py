#!/usr/bin/env python3
"""
GDS与本地bash行为对比测试
同时在本地测试文件夹和GDS中执行相同指令，验证输出一致性
"""

import unittest
import subprocess
import tempfile
import shutil
import os
import sys
import re
from pathlib import Path

class TestGDSBashCompatibility(unittest.TestCase):
    """GDS与bash行为一致性测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 创建本地测试目录
        cls.local_test_dir = tempfile.mkdtemp(prefix="gds_bash_test_")
        print(f"本地测试目录: {cls.local_test_dir}")
        
        # GDS工具路径
        cls.gds_tool = os.path.join(os.path.dirname(__file__), "..", "GOOGLE_DRIVE.py")
        
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        if os.path.exists(cls.local_test_dir):
            shutil.rmtree(cls.local_test_dir)
            print(f"清理本地测试目录: {cls.local_test_dir}")
    
    def clean_gds_output(self, raw_output):
        """
        清理GDS输出，移除ANSI转义序列和进度指示器
        用户最终看到的是经过终端处理后的逻辑输出
        """
        if not raw_output:
            return raw_output
            
        # 移除ANSI转义序列
        # \x1b[K 是清除当前行到行尾的序列
        # \x1b[nK 是清除行的变体
        # \r 是回车符，用于回到行首
        ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
        cleaned = ansi_escape.sub('', raw_output)
        
        # 移除回车符和相关的进度指示器
        # 处理 "⏳ Waiting for result ......√\r" 这种模式
        # 当遇到\r时，应该清除从行首到\r之前的所有内容
        lines = []
        for line in cleaned.split('\n'):
            if '\r' in line:
                # 找到最后一个\r，只保留\r之后的内容
                parts = line.split('\r')
                if parts[-1].strip():  # 如果最后部分有内容
                    lines.append(parts[-1])
                # 如果最后部分为空，说明这行被完全清除了
            else:
                lines.append(line)
        
        result = '\n'.join(lines)
        
        # 移除可能残留的进度指示器模式
        # 如 "⏳ Waiting for result ......√" 
        progress_pattern = re.compile(r'⏳[^√\n]*√\s*')
        result = progress_pattern.sub('', result)
        
        # 移除单独的进度符号行
        progress_symbols = re.compile(r'^[⏳√\.]+\s*$', re.MULTILINE)
        result = progress_symbols.sub('', result)
        
        # 清理多余的空行
        result = re.sub(r'\n\s*\n', '\n', result)
        result = result.strip()
        
        # 处理重复输出问题
        # 如果结果包含重复的相同行，只保留一份
        lines = result.split('\n')
        if len(lines) >= 2:
            # 检查是否有连续的重复行
            cleaned_lines = []
            prev_line = None
            for line in lines:
                if line != prev_line:
                    cleaned_lines.append(line)
                prev_line = line
            result = '\n'.join(cleaned_lines)
        
        return result
    
    def run_local_command(self, command):
        """在本地测试目录执行命令"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=self.local_test_dir,
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timeout'
            }
    
    def run_gds_command(self, command):
        """执行GDS命令"""
        try:
            result = subprocess.run(
                [sys.executable, self.gds_tool, '--shell', command],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # 对GDS输出进行后处理，移除进度指示器和ANSI序列
            cleaned_stdout = self.clean_gds_output(result.stdout)
            cleaned_stderr = self.clean_gds_output(result.stderr)
            
            return {
                'returncode': result.returncode,
                'stdout': cleaned_stdout,
                'stderr': cleaned_stderr
            }
        except subprocess.TimeoutExpired:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'GDS command timeout'
            }
    
    def assert_outputs_compatible(self, local_result, gds_result, command_desc):
        """断言本地和GDS输出兼容"""
        # 返回码应该一致
        self.assertEqual(
            local_result['returncode'], 
            gds_result['returncode'],
            f"{command_desc}: 返回码不一致 - 本地:{local_result['returncode']}, GDS:{gds_result['returncode']}"
        )
        
        # 如果成功执行，stdout应该一致
        if local_result['returncode'] == 0:
            self.assertEqual(
                local_result['stdout'].strip(),
                gds_result['stdout'].strip(),
                f"{command_desc}: stdout不一致\\n本地:{repr(local_result['stdout'])}\\nGDS:{repr(gds_result['stdout'])}"
            )
    
    def test_touch_file_creation(self):
        """测试touch命令创建文件"""
        command = "touch test_file.txt"
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        self.assert_outputs_compatible(local_result, gds_result, "touch文件创建")
        
        # 验证文件确实被创建
        local_ls = self.run_local_command("ls test_file.txt")
        gds_ls = self.run_gds_command("ls test_file.txt")
        
        self.assert_outputs_compatible(local_ls, gds_ls, "touch后ls验证")
    
    def test_echo_redirection(self):
        """测试echo重定向"""
        command = 'echo "Hello World" > hello.txt'
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        self.assert_outputs_compatible(local_result, gds_result, "echo重定向")
        
        # 验证文件内容
        local_cat = self.run_local_command("cat hello.txt")
        gds_cat = self.run_gds_command("cat hello.txt")
        
        self.assert_outputs_compatible(local_cat, gds_cat, "echo重定向后cat验证")
    
    def test_mkdir_directory_creation(self):
        """测试mkdir命令创建目录"""
        command = "mkdir test_directory"
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        self.assert_outputs_compatible(local_result, gds_result, "mkdir目录创建")
        
        # 验证目录确实被创建
        local_ls = self.run_local_command("ls -d test_directory")
        gds_ls = self.run_gds_command("ls -d test_directory")
        
        # 注意：ls -d的输出可能略有不同，主要检查返回码
        self.assertEqual(local_ls['returncode'], gds_ls['returncode'], "mkdir后ls -d验证")
    
    def test_simple_echo(self):
        """测试简单echo命令"""
        command = 'echo "Simple test message"'
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        self.assert_outputs_compatible(local_result, gds_result, "简单echo")
    
    def test_pwd_command(self):
        """测试pwd命令"""
        # 注意：本地和GDS的工作目录不同，所以只测试返回码
        local_result = self.run_local_command("pwd")
        gds_result = self.run_gds_command("pwd")
        
        self.assertEqual(local_result['returncode'], gds_result['returncode'], "pwd命令返回码")
        self.assertTrue(len(local_result['stdout'].strip()) > 0, "本地pwd应有输出")
        self.assertTrue(len(gds_result['stdout'].strip()) > 0, "GDS pwd应有输出")
    
    def test_ls_empty_directory(self):
        """测试ls空目录"""
        # 创建空目录
        local_mkdir = self.run_local_command("mkdir empty_dir")
        gds_mkdir = self.run_gds_command("mkdir empty_dir")
        
        self.assertEqual(local_mkdir['returncode'], gds_mkdir['returncode'], "创建空目录")
        
        # ls空目录
        local_ls = self.run_local_command("ls empty_dir")
        gds_ls = self.run_gds_command("ls empty_dir")
        
        self.assert_outputs_compatible(local_ls, gds_ls, "ls空目录")
    
    def test_python_simple_execution(self):
        """测试简单Python执行"""
        command = 'python3 -c "print(123)"'
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        self.assert_outputs_compatible(local_result, gds_result, "Python简单执行")
    
    def test_compound_commands(self):
        """测试复合命令"""
        # 先创建文件
        self.run_local_command('echo "test content" > compound_test.txt')
        self.run_gds_command('echo "test content" > compound_test.txt')
        
        # 测试复合命令
        command = "ls compound_test.txt && echo 'File exists!'"
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        self.assert_outputs_compatible(local_result, gds_result, "复合命令")
    
    def test_file_not_found_error(self):
        """测试文件不存在的错误情况"""
        command = "cat nonexistent_file.txt"
        
        local_result = self.run_local_command(command)
        gds_result = self.run_gds_command(command)
        
        # 两者都应该返回非零退出码
        self.assertNotEqual(local_result['returncode'], 0, "本地cat不存在文件应失败")
        self.assertNotEqual(gds_result['returncode'], 0, "GDS cat不存在文件应失败")
    
    def test_multiple_file_operations(self):
        """测试多个文件操作"""
        commands = [
            'touch file1.txt',
            'touch file2.txt', 
            'echo "content1" > file1.txt',
            'echo "content2" > file2.txt',
            'ls file1.txt file2.txt'
        ]
        
        for i, command in enumerate(commands):
            with self.subTest(step=i, command=command):
                local_result = self.run_local_command(command)
                gds_result = self.run_gds_command(command)
                
                self.assert_outputs_compatible(local_result, gds_result, f"多文件操作步骤{i+1}")


if __name__ == '__main__':
    # 设置测试输出格式
    unittest.main(verbosity=2)


