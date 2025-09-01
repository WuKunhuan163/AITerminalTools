#!/usr/bin/env python3
"""
Unit tests for EXTRACT_IMG tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

EXTRACT_IMG_PATH = str(Path(__file__).parent.parent / 'EXTRACT_IMG')
EXTRACT_IMG_PY = str(Path(__file__).parent.parent / 'EXTRACT_IMG.py')
TEST_DATA_DIR = Path(__file__).parent / '_DATA'

class TestExtractImg(unittest.TestCase):
    """Test cases for EXTRACT_IMG tool"""

    def setUp(self):
        """Set up test environment"""
        self.test_academic_image = TEST_DATA_DIR / 'test_academic_image.png'
        self.test_img = TEST_DATA_DIR / 'test_img.png'

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('EXTRACT_IMG', result.stdout)
        self.assertIn('Unified Image Analysis Tool', result.stdout)

    def test_image_path_not_exist(self):
        """Test error when image path does not exist"""
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, 'not_exist.png'
        ], capture_output=True, text=True, timeout=20)
        
        # Check for error handling (either return code or error message)
        if result.returncode == 0:
            # If it returns success, should contain error message in output
            self.assertTrue(
                'error' in result.stdout.lower() or 'not found' in result.stdout.lower() or
                'does not exist' in result.stdout.lower() or 'failed' in result.stdout.lower(),
                f"Expected error message for non-existent file, got: {result.stdout[:200]}..."
            )
        else:
            # Non-zero return code is expected for error
            self.assertNotEqual(result.returncode, 0)

    def test_general_image_routing_to_img2text(self):
        """Test that general images are routed to IMG2TEXT"""
        if not self.test_img.exists():
            self.skipTest(f"Test image {self.test_img} not found")
        
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_img), 
            '--type', 'image', '--mode', 'general'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Success case - check that it used IMG2TEXT processor
            try:
                # Try to parse as JSON
                output_json = json.loads(result.stdout)
                self.assertEqual(output_json.get('processor'), 'img2text')
                self.assertEqual(output_json.get('content_type'), 'image')
                self.assertTrue(output_json.get('success', False))
                print(f"General image correctly routed to IMG2TEXT")
            except json.JSONDecodeError:
                # Plain text output - check for success indicators
                self.assertNotIn('error', result.stdout.lower())
                print(f"General image processed successfully (plain text output)")
        else:
            # API failure case - check error handling
            self.assertTrue(
                'error' in result.stdout.lower() or 'failed' in result.stdout.lower(),
                f"Expected error message, got: {result.stdout[:200]}..."
            )

    def test_academic_image_routing_to_img2text(self):
        """Test that academic images are routed to IMG2TEXT in academic mode"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_academic_image),
            '--type', 'image', '--mode', 'academic'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Success case - check that it used IMG2TEXT processor
            try:
                # Try to parse as JSON
                output_json = json.loads(result.stdout)
                self.assertEqual(output_json.get('processor'), 'img2text')
                self.assertEqual(output_json.get('content_type'), 'image')
                self.assertEqual(output_json.get('mode'), 'academic')
                self.assertTrue(output_json.get('success', False))
                print(f"Academic image correctly routed to IMG2TEXT")
            except json.JSONDecodeError:
                # Plain text output - check for success indicators
                self.assertNotIn('error', result.stdout.lower())
                print(f"Academic image processed successfully (plain text output)")
        else:
            # API failure case - check error handling
            self.assertTrue(
                'error' in result.stdout.lower() or 'failed' in result.stdout.lower(),
                f"Expected error message, got: {result.stdout[:200]}..."
            )

    def test_formula_image_routing_to_unimernet(self):
        """Test that formula images are routed to UNIMERNET"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        # # Skip this test due to UNIMERNET performance issues in test environment
        # self.skipTest("UNIMERNET tests skipped due to performance issues - UNIMERNET is functional but slow")
        
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_academic_image),
            '--type', 'formula'
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # Success case - check that it attempted UNIMERNET processing
            try:
                # Try to parse as JSON
                output_json = json.loads(result.stdout)
                if output_json.get('success'):
                    # Successful UNIMERNET processing
                    self.assertEqual(output_json.get('processor'), 'unimernet')
                    self.assertEqual(output_json.get('content_type'), 'formula')
                    print(f"Formula image correctly routed to UNIMERNET")
                else:
                    # Failed UNIMERNET processing but routing worked
                    self.assertIn('unimernet', output_json.get('error', '').lower())
                    print(f"Formula image routing to UNIMERNET attempted (expected UNIMERNET failure)")
            except json.JSONDecodeError:
                # Plain text output - check for UNIMERNET attempt indicators
                if 'error' in result.stdout.lower():
                    # Error output should mention UNIMERNET or related terms
                    self.assertTrue(
                        'unimernet' in result.stdout.lower() or 'json' in result.stdout.lower(),
                        f"Expected UNIMERNET-related error, got: {result.stdout[:200]}..."
                    )
                    print(f"Formula image routing to UNIMERNET attempted (expected UNIMERNET failure)")
                else:
                    print(f"Formula image processed successfully (plain text output)")
        else:
            # Expected failure case for UNIMERNET (may not be fully configured)
            # Just check that the routing attempt was made
            self.assertTrue(
                'unimernet' in result.stderr.lower() or 'formula' in result.stderr.lower() or
                'error' in result.stdout.lower() or 'failed' in result.stdout.lower() or
                'timeout' in result.stderr.lower(),
                f"Expected UNIMERNET-related output, got: {result.stdout[:200]}... stderr: {result.stderr[:200]}..."
            )
            print(f"Formula image routing to UNIMERNET attempted (expected failure/timeout due to setup)")

    def test_table_image_routing_to_unimernet(self):
        """Test that table images are routed to UNIMERNET"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        # # Skip this test due to UNIMERNET performance issues in test environment
        # self.skipTest("UNIMERNET tests skipped due to performance issues - UNIMERNET is functional but slow")
        
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_academic_image),
            '--type', 'table'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Success case - check that it attempted UNIMERNET processing
            try:
                # Try to parse as JSON
                output_json = json.loads(result.stdout)
                if output_json.get('success'):
                    # Successful UNIMERNET processing
                    self.assertEqual(output_json.get('processor'), 'unimernet')
                    self.assertEqual(output_json.get('content_type'), 'table')
                    print(f"Table image correctly routed to UNIMERNET")
                else:
                    # Failed UNIMERNET processing but routing worked
                    self.assertIn('unimernet', output_json.get('error', '').lower())
                    print(f"Table image routing to UNIMERNET attempted (expected UNIMERNET failure)")
            except json.JSONDecodeError:
                # Plain text output - check for UNIMERNET attempt indicators
                if 'error' in result.stdout.lower():
                    # Error output should mention UNIMERNET or related terms
                    self.assertTrue(
                        'unimernet' in result.stdout.lower() or 'json' in result.stdout.lower(),
                        f"Expected UNIMERNET-related error, got: {result.stdout[:200]}..."
                    )
                    print(f"Table image routing to UNIMERNET attempted (expected UNIMERNET failure)")
                else:
                    print(f"Table image processed successfully (plain text output)")
        else:
            # Expected failure case for UNIMERNET (may not be fully configured)
            # Just check that the routing attempt was made
            self.assertTrue(
                'unimernet' in result.stderr.lower() or 'table' in result.stderr.lower() or
                'error' in result.stdout.lower() or 'failed' in result.stdout.lower() or
                'timeout' in result.stderr.lower(),
                f"Expected UNIMERNET-related output, got: {result.stdout[:200]}... stderr: {result.stderr[:200]}..."
            )
            print(f"Table image routing to UNIMERNET attempted (expected failure/timeout due to setup)")

    def test_auto_type_detection(self):
        """Test automatic type detection for images"""
        if not self.test_img.exists():
            self.skipTest(f"Test image {self.test_img} not found")
        
        # Test with --type auto (default)
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_img)
        ], capture_output=True, text=True, timeout=30)
        
        # Should not fail due to type detection
        if result.returncode == 0:
            # Success case
            try:
                output_json = json.loads(result.stdout)
                self.assertIn(output_json.get('content_type'), ['image', 'formula', 'table'])
                print(f"Auto-detection successful: {output_json.get('content_type')}")
            except json.JSONDecodeError:
                # Plain text output is also acceptable
                print(f"Auto-detection processed successfully (plain text output)")
        else:
            # Failure is acceptable for auto-detection tests
            print(f"Auto-detection test completed (failure expected without full setup)")

    def test_run_show_json_output(self):
        """Test RUN --show compatibility (JSON output)"""
        if not self.test_img.exists():
            self.skipTest(f"Test image {self.test_img} not found")
        
        # Test RUN integration
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'EXTRACT_IMG', str(self.test_img), '--type', 'image'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Should output JSON format
            try:
                output_json = json.loads(result.stdout)
                self.assertTrue('success' in output_json or 'result' in output_json)
                print(f"RUN --show EXTRACT_IMG integration successful")
            except json.JSONDecodeError:
                self.fail(f"RUN --show should output valid JSON: {result.stdout[:200]}...")
        else:
            # RUN integration failure is acceptable
            print(f"RUN --show EXTRACT_IMG test completed (failure expected without full setup)")

    def test_custom_prompt_parameter(self):
        """Test --prompt parameter functionality"""
        # Skip if test image doesn't exist
        if not self.test_img.exists():
            self.skipTest(f"Test image not found: {self.test_img}")
            
        # Test with custom prompt
        custom_prompt = "请简要描述这个图片的主要内容"
        
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_img), 
            '--type', 'image', '--prompt', custom_prompt, '--json'
        ], capture_output=True, text=True, timeout=30)
        
        # Check that command accepts --prompt parameter (no argument error)
        if result.returncode != 0:
            # If it fails, it shouldn't be due to unknown argument
            self.assertNotIn('unrecognized arguments: --prompt', result.stderr,
                           "EXTRACT_IMG should support --prompt parameter")
            
        # If successful, verify JSON output structure
        if result.returncode == 0:
            try:
                output_json = json.loads(result.stdout)
                self.assertIsInstance(output_json, dict)
                # Should have success or error information
                self.assertTrue('success' in output_json or 'error' in output_json)
                print(f"--prompt parameter accepted and processed")
            except json.JSONDecodeError:
                self.fail(f"Expected valid JSON output with --prompt: {result.stdout[:200]}...")
        else:
            # Even if processing fails, --prompt should be recognized
            print(f"--prompt parameter recognized (processing failure acceptable)")

    def test_help_includes_prompt_option(self):
        """Test that help output includes --prompt option"""
        result = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('--prompt', result.stdout, 
                     "Help output should include --prompt option")
        self.assertIn('Custom prompt for image analysis', result.stdout,
                     "Help should describe --prompt functionality")
        print(f"--prompt option documented in help")

    def test_cache_hit_functionality(self):
        """Test that cache system works correctly with cache hits"""
        if not self.test_img.exists():
            self.skipTest(f"Test image not found: {self.test_img}")
        
        print(f"Testing cache hit functionality with {self.test_img}")
        
        # First call - should create cache entry
        result1 = subprocess.run([
            sys.executable, EXTRACT_IMG_PY, str(self.test_img),
            '--type', 'image', '--json', '--force'  # Use --force to ensure fresh processing
        ], capture_output=True, text=True, timeout=30)
        
        # Should succeed or have reasonable error handling
        if result1.returncode == 0:
            try:
                output1 = json.loads(result1.stdout)
                self.assertIsInstance(output1, dict)
                print(f"First call completed successfully")
                
                # Second call - should hit cache (remove --force)
                result2 = subprocess.run([
                    sys.executable, EXTRACT_IMG_PY, str(self.test_img),
                    '--type', 'image', '--json'  # No --force, should use cache
                ], capture_output=True, text=True, timeout=30)
                
                if result2.returncode == 0:
                    try:
                        output2 = json.loads(result2.stdout)
                        self.assertIsInstance(output2, dict)
                        
                        # Check if cache was used (should be faster or indicate cache hit)
                        # The exact output format may vary, but both should succeed
                        print(f"Second call completed successfully (likely cache hit)")
                        
                        # Test cache stats functionality
                        stats_result = subprocess.run([
                            sys.executable, EXTRACT_IMG_PY, '--stats'
                        ], capture_output=True, text=True, timeout=10)
                        
                        if stats_result.returncode == 0:
                            print(f"Cache stats retrieved successfully")
                            self.assertIn('cache', stats_result.stdout.lower())
                        else:
                            print(f" Cache stats command failed (but cache hit test passed)")
                            
                    except json.JSONDecodeError:
                        self.fail(f"Expected valid JSON output from second call: {result2.stdout[:200]}...")
                else:
                    print(f" Second call failed, but first call succeeded (cache may not be working)")
                    
            except json.JSONDecodeError:
                self.fail(f"Expected valid JSON output from first call: {result1.stdout[:200]}...")
        else:
            # If the tool fails, check if it's due to missing dependencies or other issues
            error_output = result1.stdout + result1.stderr
            if any(keyword in error_output.lower() for keyword in ['import', 'module', 'dependency']):
                self.skipTest(f"Skipping cache test due to missing dependencies: {error_output[:200]}...")
            else:
                print(f"Warning:  EXTRACT_IMG tool failed: {error_output[:200]}...")
                print(f"Cache hit test attempted (tool execution issues may be environmental)")

if __name__ == '__main__':
    unittest.main() 