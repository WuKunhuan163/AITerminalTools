#!/usr/bin/env python3
"""
Unit tests for LEARN tool
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from _UNITTEST.base_test import BaseTest, APITest


class TestLearn(BaseTest):
    """Test cases for LEARN tool"""

    def setUp(self):
        super().setUp()
        self.learn_script = self.get_bin_path('LEARN')
        self.learn_py = self.get_python_path('LEARN.py')

    def test_learn_script_exists(self):
        """Test that LEARN script exists"""
        self.assertTrue(self.learn_script.exists())

    def test_learn_py_exists(self):
        """Test that LEARN.py exists"""
        self.assertTrue(self.learn_py.exists())

    def test_learn_direct_mode_missing_output_dir(self):
        """Test LEARN direct mode requires output directory"""
        result = self.assertCommandFail([
            sys.executable, str(self.learn_py), 
            "Python编程", "--mode", "Advanced", "--style", "Witty"
        ])
        self.assertIn('required', result.stderr)

    def test_learn_help_output(self):
        """Test LEARN help output"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.learn_py), "--help"
        ])
        self.assertIn('LEARN', result.stderr)


class TestLearnAPI(APITest):
    """API tests for LEARN tool that require longer timeouts"""

    def setUp(self):
        super().setUp()
        self.learn_py = self.get_python_path('LEARN.py')

    def test_learn_direct_mode_with_output_dir(self):
        """Test LEARN direct mode with output directory"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.learn_py), 
            "Python编程", "--mode", "Advanced", "--style", "Witty", 
            "--output-dir", "/tmp/test-learn"
        ])
        self.assertIn('正在生成学习内容结构', result.stdout)

    def test_learn_basic_functionality(self):
        """Test basic LEARN functionality"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.learn_py),
            "测试主题", "--mode", "Beginner", "--output-dir", "/tmp/test"
        ])
        self.assertIn('正在生成学习内容结构', result.stdout)

    def test_learn_paper_mode(self):
        """Test LEARN paper mode"""
        # Create a dummy PDF file
        dummy_pdf = "/tmp/test_paper.pdf"
        with open(dummy_pdf, 'w') as f:
            f.write("dummy pdf content")
        
        try:
            result = self.assertCommandSuccess([
                sys.executable, str(self.learn_py),
                dummy_pdf, "--mode", "Beginner", "--output-dir", "/tmp/test"
            ])
            self.assertIn('正在生成学习内容结构', result.stdout)
        finally:
            # Clean up
            if os.path.exists(dummy_pdf):
                os.remove(dummy_pdf)

    def test_learn_pdf_mode(self):
        """Test LEARN --pdf mode"""
        # Create a dummy PDF file
        dummy_pdf = "/tmp/test_paper.pdf"
        with open(dummy_pdf, 'w') as f:
            f.write("dummy pdf content")
        
        try:
            result = self.run_subprocess([
                sys.executable, str(self.learn_py),
                "--pdf", dummy_pdf, "--output", "/tmp/test", "测试PDF处理"
            ])
            # Should attempt to process PDF (may fail due to dummy content, but should try)
            self.assertIn('直接处理PDF文件', result.stdout)
        finally:
            # Clean up
            if os.path.exists(dummy_pdf):
                os.remove(dummy_pdf)

    def test_learn_gen_command(self):
        """Test LEARN --gen-command feature"""
        result = self.run_subprocess([
            sys.executable, str(self.learn_py),
            "--gen-command", "我想学习深度学习基础"
        ])
        # Should generate a LEARN command
        self.assertIn('LEARN', result.stdout)

    def test_learn_file_reference_parsing(self):
        """Test file reference parsing functionality"""
        # This test checks if the file reference parsing logic exists
        # We can't easily test the full functionality without actual files
        try:
            import LEARN
            # Check if the file reference functions exist
            self.assertTrue(hasattr(LEARN, 'expand_file_references') or 
                          'expand_file_references' in dir(LEARN))
        except ImportError:
            self.skipTest("LEARN module not available for direct import")


if __name__ == '__main__':
    import unittest
    unittest.main() 