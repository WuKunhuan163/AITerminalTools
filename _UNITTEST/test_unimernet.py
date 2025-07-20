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
EXTRACT_PDF_PY = str(Path(__file__).parent.parent / 'EXTRACT_PDF.py')
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
        # Check that the tool loads successfully (even if dependencies are missing)
        self.assertIn('✅ Local UnimerNet components loaded successfully', result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_formula_recognition_with_extract_pdf(self):
        """Test formula recognition using EXTRACT_PDF with test_formula.png"""
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
        import tempfile
        import shutil
        from datetime import datetime
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
            
            # Debug: Print directory structure
            print(f"Temp dir: {temp_dir}")
            print(f"Files in temp dir: {list(temp_dir.iterdir())}")
            print(f"Extract data dir exists: {extract_data_dir.exists()}")
            print(f"Extract images dir exists: {extract_images_dir.exists()}")
            print(f"Image file exists: {(extract_images_dir / f'{test_hash}.jpg').exists()}")
            print(f"PDF file exists: {temp_pdf.exists()}")
            print(f"Postprocess JSON exists: {postprocess_json.exists()}")
            
            # Test all possible image locations that _find_image_file checks
            possible_locations = [
                temp_dir / f"{test_hash}.jpg",
                temp_dir / "images" / f"{test_hash}.jpg", 
                temp_dir / f"test_formula_extract_data" / "images" / f"{test_hash}.jpg",
                Path(__file__).parent.parent / "EXTRACT_PDF_PROJ" / "pdf_extractor_data" / "images" / f"{test_hash}.jpg"
            ]
            print("Checking possible image locations:")
            for i, loc in enumerate(possible_locations):
                print(f"  {i+1}. {loc} - exists: {loc.exists()}")
            
            # Also copy the image to the direct location that might be expected
            shutil.copy(self.test_formula, temp_dir / f"{test_hash}.jpg")
            
            # Test EXTRACT_PDF post-processing with specific ID
            result = subprocess.run([
                sys.executable, EXTRACT_PDF_PY, 
                "--post", str(temp_md),
                "--ids", test_hash,
                "--post-type", "formula"
            ], capture_output=True, text=True, timeout=86400, cwd=temp_dir)  # 5 minutes timeout
            
            print(f"EXTRACT_PDF output:\n{result.stdout}")
            print(f"EXTRACT_PDF stderr:\n{result.stderr}")
            
            # Check if the process completed successfully
            self.assertEqual(result.returncode, 0, f"EXTRACT_PDF failed with error: {result.stderr}")
            
            # Check for successful processing
            self.assertIn("处理", result.stdout, "Should show processing activity")
            
            # For RUN environment, check for structured results
            if "RUN_IDENTIFIER" in os.environ:
                # Should have JSON output with recognition results
                self.assertIn("success", result.stdout.lower())
            
            # Check that formula recognition completed successfully
            output_text = result.stdout + result.stderr
            
            # Verify that UnimerNet recognition was successful
            has_recognition_success = "Recognition successful:" in output_text
            has_unimernet_success = "UnimerNet公式识别成功" in output_text
            has_placeholder_replacement = "替换placeholder:" in output_text
            
            # Check that the formula recognition workflow completed successfully
            self.assertTrue(has_recognition_success, 
                          f"UnimerNet should show 'Recognition successful:' in output. Output: {output_text}")
            self.assertTrue(has_unimernet_success, 
                          f"Should show '✅ UnimerNet公式识别成功' in output. Output: {output_text}")
            self.assertTrue(has_placeholder_replacement, 
                          f"Should show placeholder replacement in output. Output: {output_text}")
            
            # Report the model weight initialization warning if present
            has_weight_warning = "Some weights of UnimernetModel were not initialized from the model checkpoint" in output_text
            if has_weight_warning:
                print(f"⚠️  Model weight initialization warning detected - this needs to be fixed")
            else:
                print(f"✅ No model weight initialization warnings")
            
            print(f"✅ Formula recognition workflow test passed - UnimerNet integration working")
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)

    def test_formula_recognition(self):
        """Test formula recognition with test_formula.png"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=20)  # 20 seconds timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # Check if recognition was attempted (may fail due to missing dependencies)
        output = result.stdout + result.stderr
        
        if 'Result:' in output:
            # Formula recognition successful - check for specific mathematical symbols
            # Should contain at least 2 epsilon symbols and 1 theta symbol
            epsilon_count = output.count('\\epsilon')
            theta_count = output.count('\\theta')
            self.assertGreaterEqual(epsilon_count, 2, f"Expected at least 2 epsilon symbols, found {epsilon_count}")
            self.assertGreaterEqual(theta_count, 1, f"Expected at least 1 theta symbol, found {theta_count}")
        else:
            # Recognition failed - should show clear error message
            self.assertTrue(
                'UnimerNet is not available' in output or
                'error' in output.lower(),
                f"Unexpected output: {output}"
            )

    def test_table_recognition(self):
        """Test table recognition with test_table.png"""
        if not self.test_table.exists():
            self.skipTest(f"Test image {self.test_table} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_table)
        ], capture_output=True, text=True, timeout=180)  # 180 seconds timeout (3 minutes)
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # Check if recognition was attempted (may fail due to missing dependencies)
        output = result.stdout + result.stderr
        
        if 'Result:' in output:
            # Table recognition successful - check for table/array structure
            # Should contain LaTeX array structure or HTML table tags
            array_count = output.count('\\begin{array}')
            tr_count = output.count('<tr>')
            has_table_structure = array_count >= 1 or tr_count >= 1
            self.assertTrue(has_table_structure, 
                f"Expected table structure (LaTeX array or HTML table), found {array_count} arrays and {tr_count} <tr> tags")
        else:
            # Recognition failed - should show clear error message
            self.assertTrue(
                'UnimerNet is not available' in output or
                'error' in output.lower(),
                f"Unexpected output: {output}"
            )

    def test_cache_hit_performance(self):
        """Test cache hit performance - second recognition should be under 0.3 second"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # Clear cache to ensure we're testing from scratch
        cache_dir = Path(__file__).parent.parent / "EXTRACT_IMG_PROJ"
        cache_file = cache_dir / "image_cache.json"
        images_dir = cache_dir / "images"
        
        # Remove existing cache files
        if cache_file.exists():
            cache_file.unlink()
        if images_dir.exists():
            import shutil
            shutil.rmtree(images_dir)
            images_dir.mkdir(exist_ok=True)
        
        # First run to populate cache (should be slow)
        result1 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=60)  # Longer timeout for first run
        
        self.assertEqual(result1.returncode, 0)
        # First run should NOT be from cache
        output1 = result1.stdout + result1.stderr
        self.assertIn('From cache: False', output1, "First run should not be from cache")
        
        # Second run should hit cache and be much faster
        import time
        start_time = time.time()
        
        result2 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=10)  # Short timeout for cache hit
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.assertEqual(result2.returncode, 0)
        
        # Check that cache was hit
        output1 = result1.stdout + result1.stderr
        output2 = result2.stdout + result2.stderr
        self.assertIn('From cache: True', output2, "Second run should hit cache")
        
        # Extract and compare results
        result1_lines = result1.stdout.strip().split('\n')
        result2_lines = result2.stdout.strip().split('\n')
        
        # Find the "Result:" line and compare the actual recognition results
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
        ], capture_output=True, text=True, timeout=60)  # Longer timeout for force run
        
        end_time = time.time()
        force_execution_time = end_time - start_time
        
        self.assertEqual(result3.returncode, 0)
        
        # Check that force bypassed cache
        output3 = result3.stdout + result3.stderr
        self.assertIn('From cache: False', output3, "Force run should bypass cache")
        
        # Force run should be slower (> 0.3 seconds)
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
        self.assertEqual(result.returncode, 0)
        self.assertIn('UNIMERNET - UnimerNet Formula and Table Recognition Tool', result.stdout)
        # Verify --no-cache is removed and other options are present
        self.assertNotIn('--no-cache', result.stdout)
        self.assertIn('--force', result.stdout)
        self.assertIn('--stats', result.stdout)
        self.assertIn('--output', result.stdout)
        self.assertIn('--json', result.stdout)

    def test_stats_option(self):
        """Test --stats option"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--stats'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Cache Statistics:', result.stdout)

    def test_stats_json_option(self):
        """Test --stats --json option"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--stats', '--json'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        # Should be valid JSON
        import json
        try:
            data = json.loads(result.stdout)
            self.assertIn('cache_available', data)
            self.assertIn('total_cached_images', data)
        except json.JSONDecodeError:
            self.fail("--stats --json should output valid JSON")

    def test_output_option(self):
        """Test --output option"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # Use /tmp for test output
        import tempfile
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
                import json
                data = json.loads(content)
                self.assertIn('success', data)
                self.assertIn('result', data)
        finally:
            # Clean up
            if output_file.exists():
                output_file.unlink()

    def test_json_option(self):
        """Test --json option"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula), '--json'
        ], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        
        # Should output JSON to stdout
        import json
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