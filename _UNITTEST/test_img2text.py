#!/usr/bin/env python3
"""
Unit tests for IMG2TEXT tool
"""

import unittest
import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

IMG2TEXT_PATH = str(Path(__file__).parent.parent / 'IMG2TEXT')
IMG2TEXT_PY = str(Path(__file__).parent.parent / 'IMG2TEXT.py')
TEST_DATA_DIR = Path(__file__).parent / '_DATA'

class TestImg2Text(unittest.TestCase):
    """Test cases for IMG2TEXT tool"""

    def setUp(self):
        """Set up test environment"""
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

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, IMG2TEXT_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('图片转文字描述工具', result.stdout)
        self.assertIn('--output-dir', result.stdout)

    def test_connection_test_no_api_key(self):
        """Test --test-connection with no API key"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "", "GOOGLE_API_KEY_PAID": ""}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, '--test-connection'
            ], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0)
            self.assertIn('❌ 连接测试失败：未设置API密钥', result.stdout)

    def test_connection_test_with_fake_key(self):
        """Test --test-connection with fake API key"""
        with patch.dict(os.environ, {"GOOGLE_API_KEY_FREE": "fake_key", "GOOGLE_API_KEY_PAID": ""}):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, '--test-connection'
            ], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0)
            self.assertIn('🔍 API连接测试结果:', result.stdout)
            self.assertIn('FREE 密钥:', result.stdout)

    def test_connection_test_with_custom_key(self):
        """Test --test-connection with custom key parameter"""
        result = subprocess.run([
            sys.executable, IMG2TEXT_PY, '--test-connection', '--key', 'custom_fake_key'
        ], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertIn('🔍 API连接测试结果:', result.stdout)
        self.assertIn('USER 密钥:', result.stdout)

    def test_connection_test_run_mode(self):
        """Test --test-connection in RUN mode"""
        run_script = str(Path(__file__).parent.parent / 'RUN')
        result = subprocess.run([
            run_script, '--show', 'IMG2TEXT', '--test-connection'
        ], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        
        # Should return valid JSON
        try:
            json_result = json.loads(result.stdout)
            self.assertIn('success', json_result)
            self.assertIn('output', json_result)
            self.assertIn('🔍 API连接测试结果:', json_result['output'])
        except json.JSONDecodeError:
            self.fail(f"RUN mode should return valid JSON, got: {result.stdout}")

    def test_help_includes_test_connection(self):
        """Test that help output includes --test-connection option"""
        result = subprocess.run([
            sys.executable, IMG2TEXT_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--test-connection', result.stdout)
        self.assertIn('测试API连接状态', result.stdout)

    def test_run_show_json_output(self):
        """Test RUN --show compatibility (JSON output) when API key missing"""
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY_FREE": "", "GOOGLE_API_KEY_PAID": "",
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_img2text_run.json"
        }):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, 'test_run', 'not_exist.png'
            ], capture_output=True, text=True, timeout=20)
            
            # Should output JSON format
            try:
                output_json = json.loads(result.stdout)
                self.assertFalse(output_json['success'])
                self.assertIn('API调用错误', output_json['reason'])
            except json.JSONDecodeError:
                self.fail(f"Output is not valid JSON: {result.stdout}")

    def test_general_image_processing(self):
        """Test general image processing with test image - check for dice colors"""
        if not self.test_img.exists():
            self.skipTest(f"Test image {self.test_img} not found")
        
        # Use --prompt to ask specifically about objects and colors in the image
        prompt = "What objects are in this image and what colors are they? Please be specific about the colors you see."
        
        result = subprocess.run([
            sys.executable, IMG2TEXT_PY, str(self.test_img), 
            '--prompt', prompt
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Success case - check for specific content
            output = result.stdout.lower()
            required_terms = ['dice', 'red', 'yellow', 'green', 'blue']
            missing_terms = [term for term in required_terms if term not in output]
            
            if missing_terms:
                self.fail(f"Missing required terms in output: {missing_terms}. Output was: {result.stdout[:300]}...")
            else:
                print(f"✅ General image test passed - found all required terms: {required_terms}")
        else:
            # API failure case - check error handling
            self.assertTrue(
                'API调用错误' in result.stdout or 'API调用失败' in result.stdout,
                f"Expected API error message, got: {result.stdout[:200]}..."
            )

    def test_academic_image_processing(self):
        """Test academic image processing with test_academic_image.png - check LoRA training flow"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        # Use --prompt to ask specifically about the fire symbol and LoRA training flow
        prompt = "详细地描述🔥标志所代表的中心所涉及的LoRA训练流程。请包含训练过程中的关键概念和组件。"
        
        result = subprocess.run([
            sys.executable, IMG2TEXT_PY, str(self.test_academic_image),
            '--prompt', prompt
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Success case - check for specific LoRA training flow terms
            output = result.stdout.lower()
            
            # Define required terms with flexible matching
            required_checks = [
                ('gaussian', lambda text: 'gaussian' in text),
                ('operation/flow', lambda text: 'operation' in text or 'flow' in text),
                ('gradient', lambda text: 'gradient' in text),
                ('stable diffusion', lambda text: 'stable diffusion' in text),
                ('controlnet', lambda text: 'controlnet' in text),
                ('bulldozer/tractor', lambda text: 'bulldozer' in text or 'tractor' in text),
                ('model', lambda text: 'model' in text),
                ('prediction', lambda text: 'prediction' in text or 'predict' in text),
                ('training', lambda text: 'training' in text or 'train' in text)
            ]
            
            missing_terms = [name for name, check_func in required_checks if not check_func(output)]
            
            if missing_terms:
                self.fail(f"Missing required LoRA training terms in output: {missing_terms}. Output was: {result.stdout[:500]}...")
            else:
                found_terms = [name for name, check_func in required_checks if check_func(output)]
                print(f"✅ Academic image test passed - found all required LoRA training terms: {found_terms}")
        else:
            # API failure case - check error handling
            self.assertTrue(
                'API调用错误' in result.stdout or 'API调用失败' in result.stdout,
                f"Expected API error message, got: {result.stdout[:200]}..."
            )

    def test_output_dir_functionality(self):
        """Test --output-dir functionality with /tmp directory"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        # Use /tmp as output directory
        output_dir = "/tmp/img2text_test"
        
        try:
            # Clean up any existing test directory
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            
            # Test with fake API keys to ensure predictable behavior
            with patch.dict(os.environ, {
                "GOOGLE_API_KEY_FREE": "fake_key_for_testing", 
                "GOOGLE_API_KEY_PAID": "fake_key_for_testing"
            }, clear=False):
                result = subprocess.run([
                    sys.executable, IMG2TEXT_PY, str(self.test_academic_image), 
                    '--mode', 'academic', '--output-dir', output_dir
                ], capture_output=True, text=True, timeout=30)
                
                # Check that --output-dir option is recognized (should not fail due to argument error)
                self.assertNotIn('unrecognized arguments', result.stderr)
                
                # Either succeeds (if real API keys work) or fails with API error
                if result.returncode == 0:
                    # Success case - check that file was saved to correct directory
                    self.assertIn('分析结果已保存到:', result.stdout)
                    self.assertIn(output_dir, result.stdout)
                else:
                    # Failure case - should show API error
                    self.assertTrue(
                        'API调用错误' in result.stdout or 'API调用失败' in result.stdout,
                        f"Expected API error message, got: {result.stdout[:200]}..."
                    )
                
        finally:
            # Clean up test directory
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)

    def test_run_show_json_output_with_academic_image(self):
        """Test RUN --show compatibility (JSON output) with academic test image"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        with patch.dict(os.environ, {
            "GOOGLE_API_KEY_FREE": "fake", "GOOGLE_API_KEY_PAID": "fake",
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_img2text_academic_run.json"
        }):
            result = subprocess.run([
                sys.executable, IMG2TEXT_PY, 'test_run', str(self.test_academic_image)
            ], capture_output=True, text=True, timeout=30)
            
            # Should output JSON format
            try:
                output_json = json.loads(result.stdout)
                self.assertFalse(output_json['success'])
                self.assertTrue(
                    'API调用失败' in output_json['reason'] or 'API调用错误' in output_json['reason'] or 
                    '所有配置的API密钥都无法成功获取回复' in output_json['reason'],
                    f"Expected API error in reason, got: {output_json['reason'][:100]}..."
                )
                self.assertEqual(output_json['image_path'], str(self.test_academic_image))
            except json.JSONDecodeError:
                self.fail(f"Output is not valid JSON: {result.stdout}")

if __name__ == '__main__':
    unittest.main() 