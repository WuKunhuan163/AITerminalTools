#!/usr/bin/env python3
"""
Unit tests for UNIMERNET tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

UNIMERNET_PATH = str(Path(__file__).parent.parent / 'UNIMERNET')
UNIMERNET_PY = str(Path(__file__).parent.parent / 'UNIMERNET.py')
TEST_DATA_DIR = Path(__file__).parent / '_DATA'

class TestUnimernet(unittest.TestCase):
    """Test cases for UNIMERNET tool"""

    def setUp(self):
        """Set up test environment"""
        self.test_formula = TEST_DATA_DIR / 'test_formula.png'
        self.test_table = TEST_DATA_DIR / 'test_table.png'
        self.test_academic_image = TEST_DATA_DIR / 'test_academic_image.png'

    def test_check_availability(self):
        """Test UNIMERNET availability check"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--check'
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        self.assertIn('✅ UnimerNet is available and ready', result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_formula_recognition(self):
        """Test formula recognition with test_formula.png"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # 检查是否有识别结果
        self.assertIn('Recognition successful', result.stdout)

    def test_table_recognition(self):
        """Test table recognition with test_table.png"""
        if not self.test_table.exists():
            self.skipTest(f"Test image {self.test_table} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_table)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # 检查是否有识别结果
        self.assertIn('Recognition successful', result.stdout)

    def test_academic_image_recognition(self):
        """Test academic image recognition with test_academic_image.png"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_academic_image)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # 检查是否有识别结果
        self.assertIn('Recognition successful', result.stdout)

    def test_run_show_json_output(self):
        """Test RUN --show compatibility (JSON output)"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        with patch.dict(os.environ, {
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_unimernet_run.json"
        }):
            result = subprocess.run([
                sys.executable, UNIMERNET_PY, str(self.test_formula)
            ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
            
            # 检查JSON文件内容
            if os.path.exists('/tmp/test_unimernet_run.json'):
                with open('/tmp/test_unimernet_run.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.assertTrue(data['success'])
                self.assertIn('Recognition successful', data['output'])

    def test_image_path_not_exist(self):
        """Test error when image path does not exist"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, 'not_exist.png'
        ], capture_output=True, text=True, timeout=20)
        self.assertIn('图片路径不存在', result.stdout)

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertIn('UNIMERNET - UnimerNet Formula and Table Recognition Tool', result.stdout)

    def test_cache_functionality(self):
        """Test cache functionality with repeated calls"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # 第一次调用
        result1 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 第二次调用应该从缓存获取
        result2 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 两次调用都应该成功
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)
        
        # 第二次调用应该显示从缓存获取
        self.assertIn('From cache: True', result2.stdout)

if __name__ == '__main__':
    unittest.main() 