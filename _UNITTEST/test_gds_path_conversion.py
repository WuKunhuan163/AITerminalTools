#!/usr/bin/env python3
"""
测试GDS路径转换功能
验证shell展开的本地路径能正确转换为远程逻辑路径
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入被测试的模块
import GOOGLE_DRIVE

class TestGDSPathConversion(unittest.TestCase):
    """测试GDS路径转换功能"""
    
    def setUp(self):
        """测试前准备"""
        self.original_home = os.path.expanduser("~")
        
        # Mock GoogleDriveShell
        self.mock_shell = Mock()
        self.mock_shell.cmd_ls.return_value = {"success": True, "files": []}
        self.mock_shell.cmd_cd.return_value = {"success": True, "path": "~"}
        self.mock_shell.cmd_cat.return_value = {"success": True, "content": "test"}
        self.mock_shell.cmd_mkdir.return_value = {"success": True, "path": "test"}
        self.mock_shell.cmd_rm.return_value = {"success": True, "deleted": ["test"]}
        self.mock_shell.cmd_read.return_value = {"success": True, "content": "test"}
        self.mock_shell.cmd_find.return_value = {"success": True, "results": []}
        self.mock_shell.cmd_mv.return_value = {"success": True, "moved": "test"}
        self.mock_shell.cmd_edit.return_value = {"success": True, "edited": "test"}
        self.mock_shell.cmd_grep.return_value = {"success": True, "matches": []}
        
    def test_convert_local_path_to_remote_function(self):
        """测试路径转换函数本身"""
        # 模拟handle_shell_command函数中的convert_local_path_to_remote函数
        def convert_local_path_to_remote(path):
            """将shell展开的本地路径转换回远程逻辑路径"""
            if not path:
                return path
                
            # 获取用户主目录
            home_path = os.path.expanduser("~")
            
            # 如果路径是用户主目录，转换为~
            if path == home_path:
                return "~"
            # 如果是主目录下的子路径，转换为~/相对路径
            elif path.startswith(home_path + "/"):
                relative_part = path[len(home_path) + 1:]
                return f"~/{relative_part}"
            # 其他情况保持原样
            else:
                return path
        
        # 测试用例
        home_path = self.original_home
        
        # 测试主目录转换
        self.assertEqual(convert_local_path_to_remote(home_path), "~")
        
        # 测试主目录下的子路径转换
        self.assertEqual(convert_local_path_to_remote(f"{home_path}/Documents"), "~/Documents")
        self.assertEqual(convert_local_path_to_remote(f"{home_path}/Desktop/test"), "~/Desktop/test")
        
        # 测试非主目录路径保持不变
        self.assertEqual(convert_local_path_to_remote("/usr/local/bin"), "/usr/local/bin")
        self.assertEqual(convert_local_path_to_remote("relative/path"), "relative/path")
        
        # 测试空路径和None
        self.assertEqual(convert_local_path_to_remote(""), "")
        self.assertEqual(convert_local_path_to_remote(None), None)
        
        # 测试边界情况
        self.assertEqual(convert_local_path_to_remote(f"{home_path}extra"), f"{home_path}extra")  # 不是真正的子路径
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_ls_command_path_conversion(self, mock_shell_class):
        """测试ls命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        expanded_path = f"{home_path}/Documents"
        
        # 测试ls命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'ls', expanded_path]):
            GOOGLE_DRIVE.handle_shell_command(f'ls {expanded_path}')
        
        # 验证传递给cmd_ls的路径已被转换
        self.mock_shell.cmd_ls.assert_called_once_with("~/Documents", False, False)
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_cd_command_path_conversion(self, mock_shell_class):
        """测试cd命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        
        # 测试cd到主目录
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'cd', home_path]):
            GOOGLE_DRIVE.handle_shell_command(f'cd {home_path}')
        
        # 验证传递给cmd_cd的路径已被转换
        self.mock_shell.cmd_cd.assert_called_once_with("~")
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_mkdir_command_path_conversion(self, mock_shell_class):
        """测试mkdir命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        expanded_path = f"{home_path}/NewFolder"
        
        # 测试mkdir命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'mkdir', expanded_path]):
            GOOGLE_DRIVE.handle_shell_command(f'mkdir {expanded_path}')
        
        # 验证传递给cmd_mkdir的路径已被转换
        self.mock_shell.cmd_mkdir.assert_called_once_with("~/NewFolder", False)
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_cat_command_path_conversion(self, mock_shell_class):
        """测试cat命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        expanded_path = f"{home_path}/test.txt"
        
        # 测试cat命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'cat', expanded_path]):
            GOOGLE_DRIVE.handle_shell_command(f'cat {expanded_path}')
        
        # 验证传递给cmd_cat的路径已被转换
        self.mock_shell.cmd_cat.assert_called_once_with("~/test.txt")
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_rm_command_path_conversion(self, mock_shell_class):
        """测试rm命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        expanded_path = f"{home_path}/test.txt"
        
        # 测试rm命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'rm', expanded_path]):
            GOOGLE_DRIVE.handle_shell_command(f'rm {expanded_path}')
        
        # 验证传递给cmd_rm的路径已被转换
        self.mock_shell.cmd_rm.assert_called_once_with("~/test.txt", recursive=False, force=False)
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_find_command_path_conversion(self, mock_shell_class):
        """测试find命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        expanded_path = f"{home_path}/Documents"
        
        # 测试find命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'find', expanded_path, '-name', '*.txt']):
            GOOGLE_DRIVE.handle_shell_command(f'find {expanded_path} -name *.txt')
        
        # 验证传递给cmd_find的路径已被转换
        self.mock_shell.cmd_find.assert_called_once_with("~/Documents", "-name", "*.txt")
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_mv_command_path_conversion(self, mock_shell_class):
        """测试mv命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        src_path = f"{home_path}/old.txt"
        dst_path = f"{home_path}/new.txt"
        
        # 测试mv命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'mv', src_path, dst_path]):
            GOOGLE_DRIVE.handle_shell_command(f'mv {src_path} {dst_path}')
        
        # 验证传递给cmd_mv的路径已被转换
        self.mock_shell.cmd_mv.assert_called_once_with("~/old.txt", "~/new.txt")
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_grep_command_path_conversion(self, mock_shell_class):
        """测试grep命令的路径转换"""
        mock_shell_class.return_value = self.mock_shell
        
        # 模拟shell展开的路径
        home_path = self.original_home
        file1_path = f"{home_path}/file1.txt"
        file2_path = f"{home_path}/file2.txt"
        
        # 测试grep命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'grep', 'pattern', file1_path, file2_path]):
            GOOGLE_DRIVE.handle_shell_command(f'grep pattern {file1_path} {file2_path}')
        
        # 验证传递给cmd_grep的路径已被转换
        self.mock_shell.cmd_grep.assert_called_once_with("pattern", "~/file1.txt", "~/file2.txt")
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_non_home_paths_unchanged(self, mock_shell_class):
        """测试非主目录路径保持不变"""
        mock_shell_class.return_value = self.mock_shell
        
        # 测试非主目录的绝对路径
        abs_path = "/usr/local/bin/test"
        
        # 测试ls命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'ls', abs_path]):
            GOOGLE_DRIVE.handle_shell_command(f'ls {abs_path}')
        
        # 验证路径保持不变
        self.mock_shell.cmd_ls.assert_called_once_with(abs_path, False, False)
    
    @patch('GOOGLE_DRIVE.GoogleDriveShell')
    def test_relative_paths_unchanged(self, mock_shell_class):
        """测试相对路径保持不变"""
        mock_shell_class.return_value = self.mock_shell
        
        # 测试相对路径
        rel_path = "Documents/test.txt"
        
        # 测试cat命令
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--shell', 'cat', rel_path]):
            GOOGLE_DRIVE.handle_shell_command(f'cat {rel_path}')
        
        # 验证路径保持不变
        self.mock_shell.cmd_cat.assert_called_once_with(rel_path)

def run_tests():
    """运行测试"""
    unittest.main(verbosity=2)

if __name__ == "__main__":
    run_tests() 