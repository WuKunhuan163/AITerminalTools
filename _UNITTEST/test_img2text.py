#!/usr/bin/env python3
"""
Unit tests for IMG2TEXT tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

IMG2TEXT_PATH = str(Path(__file__).parent.parent / 'IMG2TEXT')
IMG2TEXT_PY = str(Path(__file__).parent.parent / 'IMG2TEXT.py')
TEST_DATA_DIR = Path(__file__).parent / '_DATA'

class TestImg2Text(unittest.TestCase):
    """Test cases for IMG2TEXT tool"""

    def setUp(self):
        """Set up test environment"""
        self.test_formula = TEST_DATA_DIR / 'test_formula.png'
        self.test_table = TEST_DATA_DIR / 'test_table.png'
        self.test_academic_image = TEST_DATA_DIR / 'test_academic_image.png'
        self.test_img = TEST_DATA_DIR / 'test_img.png'

    def test_no_api_key(self):
        """Test error when no API key is set"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "", "GOOGLE_API_KEY_PAID": ""}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, 'not_exist.png', '--mode', 'academic'
            ], capture_output=True, text=True, timeout=20)
            self.assertIn('API调用错误', result.stdout)

    def test_image_path_not_exist(self):
        """Test error when image path does not exist"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "fake", "GOOGLE_API_KEY_PAID": "fake"}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, 'not_exist.png', '--mode', 'academic'
            ], capture_output=True, text=True, timeout=20)
            self.assertIn('图片路径不存在', result.stdout)

    def test_run_show_json_output(self):
        """Test RUN --show compatibility (JSON output) when API key missing"""
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY_FREE": "", "GOOGLE_API_KEY_PAID": "",
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_img2text_run.json"
        }):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, 'not_exist.png', '--mode', 'academic'
            ], capture_output=True, text=True, timeout=20)
            # 检查JSON文件内容
            with open('/tmp/test_img2text_run.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertFalse(data['success'])
            self.assertIn('API调用错误', data['reason'])

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, IMG2TEXT_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertIn('图片转文字描述工具', result.stdout)

    def test_formula_image_processing(self):
        """Test formula image processing with test_formula.png"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # 由于API密钥问题，我们预期会失败，但检查错误处理
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "fake", "GOOGLE_API_KEY_PAID": "fake"}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, str(self.test_formula), '--mode', 'academic'
            ], capture_output=True, text=True, timeout=30)
            # 检查是否正确处理了API错误
            self.assertIn('API调用错误', result.stdout)

    def test_table_image_processing(self):
        """Test table image processing with test_table.png"""
        if not self.test_table.exists():
            self.skipTest(f"Test image {self.test_table} not found")
        
        # 由于API密钥问题，我们预期会失败，但检查错误处理
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "fake", "GOOGLE_API_KEY_PAID": "fake"}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, str(self.test_table), '--mode', 'academic'
            ], capture_output=True, text=True, timeout=30)
            # 检查是否正确处理了API错误
            self.assertIn('API调用错误', result.stdout)

    def test_academic_image_processing(self):
        """Test academic image processing with test_academic_image.png"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        # 由于API密钥问题，我们预期会失败，但检查错误处理
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "fake", "GOOGLE_API_KEY_PAID": "fake"}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, str(self.test_academic_image), '--mode', 'academic'
            ], capture_output=True, text=True, timeout=30)
            # 检查是否正确处理了API错误
            self.assertIn('API调用错误', result.stdout)

    def test_run_show_json_output_with_new_images(self):
        """Test RUN --show compatibility (JSON output) with new test images"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY_FREE": "fake", "GOOGLE_API_KEY_PAID": "fake",
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_img2text_new_run.json"
        }):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, str(self.test_academic_image), '--mode', 'academic'
            ], capture_output=True, text=True, timeout=30)
            
            # 检查JSON文件内容
            if os.path.exists('/tmp/test_img2text_new_run.json'):
                with open('/tmp/test_img2text_new_run.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.assertFalse(data['success'])
                self.assertIn('API调用错误', data['reason'])

if __name__ == '__main__':
    unittest.main() 