#!/usr/bin/env python3
"""
Unified unit tests for UNIMERNET tool
"""

import unittest
import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch
from datetime import datetime
import shutil

UNIMERNET_PATH = str(Path(__file__).parent.parent / 'UNIMERNET')
UNIMERNET_PY = str(Path(__file__).parent.parent / 'UNIMERNET.py')
EXTRACT_PDF_PY = str(Path(__file__).parent.parent / 'EXTRACT_PDF.py')
TEST_DATA_DIR = Path(__file__).parent / '_DATA'


class TestUnimernet(unittest.TestCase):
    """Unified test class for UNIMERNET tool functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_formula = TEST_DATA_DIR / 'test_formula.png'
        self.test_table = TEST_DATA_DIR / 'test_table.png'
        self.test_academic_image = TEST_DATA_DIR / 'test_academic_image.png'

    def test_basic_functionality(self):
        """Test basic UNIMERNET functionality including help, stats, and availability check"""
        # Test help output
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('UNIMERNET - UnimerNet Formula and Table Recognition Tool', result.stdout)
        self.assertNotIn('--no-cache', result.stdout)  # Verify --no-cache is removed
        self.assertIn('--force', result.stdout)
        self.assertIn('--stats', result.stdout)
        self.assertIn('--output', result.stdout)
        self.assertIn('--json', result.stdout)

        # Test stats option
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--stats'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Cache Statistics:', result.stdout)

        # Test stats JSON option
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--stats', '--json'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
            self.assertIn('cache_available', data)
            self.assertIn('total_cached_images', data)
        except json.JSONDecodeError:
            self.fail("--stats --json should output valid JSON")

        # Test availability check
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--check'
        ], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Local UnimerNet components loaded successfully', result.stdout)

        # Test error when image path does not exist
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, 'not_exist.png'
        ], capture_output=True, text=True, timeout=20)
        self.assertIn('Image file not found', result.stdout)

    def test_formula_recognition(self):
        """Test formula recognition functionality"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=20)
        
        self.assertEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        
        if 'Result:' in output:
            # Formula recognition successful - check for specific mathematical symbols
            epsilon_count = output.count('\\epsilon')
            theta_count = output.count('\\theta')
            self.assertGreaterEqual(epsilon_count, 2, f"Expected at least 2 epsilon symbols, found {epsilon_count}")
            self.assertGreaterEqual(theta_count, 1, f"Expected at least 1 theta symbol, found {theta_count}")
        else:
            # Recognition failed - should show clear error message
            self.assertTrue(
                'UnimerNet is not available' in output or 'error' in output.lower(),
                f"Unexpected output: {output}"
            )

    def test_table_recognition(self):
        """Test table recognition functionality"""
        if not self.test_table.exists():
            self.skipTest(f"Test image {self.test_table} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_table)
        ], capture_output=True, text=True, timeout=180)
        
        self.assertEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        
        if 'Result:' in output:
            # Table recognition successful - check for table/array structure
            array_count = output.count('\\begin{array}')
            tr_count = output.count('<tr>')
            has_table_structure = array_count >= 1 or tr_count >= 1
            self.assertTrue(has_table_structure, 
                f"Expected table structure (LaTeX array or HTML table), found {array_count} arrays and {tr_count} <tr> tags")
        else:
            # Recognition failed - should show clear error message
            self.assertTrue(
                'UnimerNet is not available' in output or 'error' in output.lower(),
                f"Unexpected output: {output}"
            )

    def test_caching_functionality(self):
        """Test cache functionality with repeated calls and performance"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # Clear cache to ensure we're testing from scratch
        cache_dir = Path(__file__).parent.parent / "EXTRACT_IMG_DATA"
        cache_file = cache_dir / "image_cache.json"
        images_dir = cache_dir / "images"
        
        # Remove existing cache files
        if cache_file.exists():
            cache_file.unlink()
        if images_dir.exists():
            shutil.rmtree(images_dir)
            images_dir.mkdir(exist_ok=True)
        
        # First run to populate cache (should be slow)
        result1 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=60)
        
        self.assertEqual(result1.returncode, 0)
        output1 = result1.stdout + result1.stderr
        self.assertIn('From cache: False', output1, "First run should not be from cache")
        
        # Second run should hit cache and be much faster
        start_time = time.time()
        result2 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=10)
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertEqual(result2.returncode, 0)
        output2 = result2.stdout + result2.stderr
        self.assertIn('From cache: True', output2, "Second run should hit cache")
        
        # Extract and compare results
        result1_lines = result1.stdout.strip().split('\n')
        result2_lines = result2.stdout.strip().split('\n')
        
        result1_content = None
        result2_content = None
        
        for i, line in enumerate(result1_lines):
            if line.strip() == "Result:":
                result1_content = '\n'.join(result1_lines[i+1:])
                break
        
        for i, line in enumerate(result2_lines):
            if line.strip() == "Result:":
                result2_content = '\n'.join(result2_lines[i+1:])
                break
        
        # Both results should be identical
        self.assertEqual(result1_content, result2_content, "Cache hit should return identical results")
        
        # Check execution time (should be under 0.3 seconds for cache hit)
        self.assertLess(execution_time, 0.3, f"Cache hit should be under 0.3 seconds, took {execution_time:.2f}s")
        
        # Third run with --force should bypass cache and be slower
        start_time = time.time()
        result3 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula), '--force'
        ], capture_output=True, text=True, timeout=60)
        end_time = time.time()
        force_execution_time = end_time - start_time
        
        self.assertEqual(result3.returncode, 0)
        output3 = result3.stdout + result3.stderr
        self.assertIn('From cache: False', output3, "Force run should bypass cache")
        self.assertGreater(force_execution_time, 0.3, f"Force run should be slower than 0.3s, took {force_execution_time:.2f}s")
        
        # Extract result from third run
        result3_lines = result3.stdout.strip().split('\n')
        result3_content = None
        
        for i, line in enumerate(result3_lines):
            if line.strip() == "Result:":
                result3_content = '\n'.join(result3_lines[i+1:])
                break
        
        # All three results should be identical
        self.assertEqual(result1_content, result3_content, "Force run should return same result as cached runs")
        self.assertEqual(result2_content, result3_content, "All three runs should return identical results")

    def test_output_options(self):
        """Test various output options including --output, --json"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # Test --output option
        output_file = Path(tempfile.mktemp(suffix='.txt'))
        
        try:
            result = subprocess.run([
                sys.executable, UNIMERNET_PY, str(self.test_formula), '--output', str(output_file)
            ], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0)
            self.assertIn('Results saved to', result.stdout)
            
            # Check output file exists and contains JSON
            self.assertTrue(output_file.exists())
            with open(output_file, 'r') as f:
                content = f.read()
                data = json.loads(content)
                self.assertIn('success', data)
                self.assertIn('result', data)
        finally:
            # Clean up
            if output_file.exists():
                output_file.unlink()
        
        # Test --json option
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula), '--json'
        ], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        
        # Should output JSON to stdout
        try:
            # Extract JSON from stdout (ignore log messages)
            lines = result.stdout.strip().split('\n')
            json_lines = []
            in_json = False
            for line in lines:
                if line.strip().startswith('{'):
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip().endswith('}') and in_json:
                    break
            
            json_content = '\n'.join(json_lines)
            data = json.loads(json_content)
            self.assertIn('success', data)
            self.assertIn('result', data)
            self.assertIn('from_cache', data)
        except (json.JSONDecodeError, IndexError):
            self.fail(f"--json should output valid JSON, got: {result.stdout}")

    def test_extract_pdf_integration(self):
        """Test EXTRACT_PDF integration with formula recognition"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # Create a temporary markdown file with formula placeholder
        test_hash = "test_formula_hash"
        temp_md_content = f"""# Test Formula Recognition

This is a test document with a formula placeholder.

[placeholder: formula]
![](images/{test_hash}.jpg)

End of document.
"""
        
        # Create temporary directory structure
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create markdown file
            temp_md = temp_dir / "test_formula.md"
            temp_md.write_text(temp_md_content)
            
            # Create a dummy PDF file
            temp_pdf = temp_dir / "test_formula.pdf"
            temp_pdf.write_bytes(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
            
            # Create extract_data directory structure to simulate post-processing
            extract_data_dir = temp_dir / "test_formula_extract_data"
            extract_data_dir.mkdir()
            extract_images_dir = extract_data_dir / "images"
            extract_images_dir.mkdir()
            
            # Copy formula image with a hash name
            shutil.copy(self.test_formula, extract_images_dir / f"{test_hash}.jpg")
            
            # Create postprocess JSON file with correct format
            postprocess_data = {
                "pdf_file": "test_formula.pdf",
                "created_at": datetime.now().isoformat(),
                "total_items": 1,
                "counts": {
                    "images": 0,
                    "formulas": 1,
                    "tables": 0
                },
                "items": [{
                    "type": "formula",
                    "page": 1,
                    "block_index": 0,
                    "image_path": f"{test_hash}.jpg",
                    "bbox": [],
                    "processed": False,
                    "processor": None,
                    "id": test_hash
                }]
            }
            postprocess_json = temp_dir / "test_formula_postprocess.json"
            postprocess_json.write_text(json.dumps(postprocess_data, indent=2))
            
            # Also copy the image to the direct location that might be expected
            shutil.copy(self.test_formula, temp_dir / f"{test_hash}.jpg")
            
            # Test EXTRACT_PDF post-processing with specific ID
            result = subprocess.run([
                sys.executable, EXTRACT_PDF_PY, 
                "--post", str(temp_md),
                "--ids", test_hash,
                "--post-type", "formula"
            ], capture_output=True, text=True, timeout=86400, cwd=temp_dir)
            
            # Check if the process completed successfully
            self.assertEqual(result.returncode, 0, f"EXTRACT_PDF failed with error: {result.stderr}")
            
            # Check for successful processing
            output_text = result.stdout + result.stderr
            self.assertIn("Processing", output_text, "Should show processing activity")
            
            # For RUN environment, check for structured results
            if "RUN_IDENTIFIER" in os.environ:
                self.assertIn("success", result.stdout.lower())
            
            # Verify that UnimerNet recognition was successful
            has_recognition_success = "Recognition successful:" in output_text
            has_unimernet_success = "UnimerNet公式识别成功" in output_text
            has_placeholder_replacement = "替换placeholder:" in output_text
            
            # Check that the formula recognition workflow completed successfully
            self.assertTrue(has_recognition_success, 
                          f"UnimerNet should show 'Recognition successful:' in output. Output: {output_text}")
            self.assertTrue(has_unimernet_success, 
                          f"Should show 'UnimerNet公式识别成功' in output. Output: {output_text}")
            self.assertTrue(has_placeholder_replacement, 
                          f"Should show placeholder replacement in output. Output: {output_text}")
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)

    def test_run_environment_compatibility(self):
        """Test RUN --show compatibility (JSON output)"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        with patch.dict(os.environ, {
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_unimernet_run.json"
        }):
            result = subprocess.run([
                sys.executable, UNIMERNET_PY, str(self.test_formula)
            ], capture_output=True, text=True, timeout=180)
            
            # Check JSON file content
            if os.path.exists('/tmp/test_unimernet_run.json'):
                with open('/tmp/test_unimernet_run.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.assertTrue(data['success'])
                self.assertIn('Recognition successful', data['output'])


def run_tests():
    """Run all tests with detailed output"""
    print(f"=== UNIMERNET Unified Unit Tests ===")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestUnimernet))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Output results
    print()
    print(f"=== Test Results ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)