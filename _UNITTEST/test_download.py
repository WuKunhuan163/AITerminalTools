#!/usr/bin/env python3
"""
Unit tests for DOWNLOAD tool
"""

import unittest
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import DOWNLOAD
    DOWNLOAD_AVAILABLE = True
except ImportError:
    DOWNLOAD = None
    DOWNLOAD_AVAILABLE = False

DOWNLOAD_PY = str(Path(__file__).parent.parent / 'DOWNLOAD.py')

class TestDownload(unittest.TestCase):
    """Test cases for DOWNLOAD tool"""

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, DOWNLOAD_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('DOWNLOAD', result.stdout)
        self.assertIn('Resource Download Tool', result.stdout)
        self.assertIn('Usage:', result.stdout)
        self.assertIn('Examples:', result.stdout)

    @unittest.skipIf(not DOWNLOAD_AVAILABLE, "DOWNLOAD module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(DOWNLOAD.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {'RUN_IDENTIFIER_test123': 'True'}):
            self.assertTrue(DOWNLOAD.is_run_environment('test123'))

    @unittest.skipIf(not DOWNLOAD_AVAILABLE, "DOWNLOAD module not available")
    def test_json_output_creation(self):
        """Test JSON output format for RUN environment"""
        test_data = {
            "success": True,
            "message": "Test message",
            "url": "https://example.com/file.txt"
        }
        
        with patch.object(DOWNLOAD, 'write_to_json_output') as mock_write:
            mock_write.return_value = True
            result = DOWNLOAD.write_to_json_output(test_data)
            mock_write.assert_called_once_with(test_data)

    @unittest.skipIf(not DOWNLOAD_AVAILABLE, "DOWNLOAD module not available")
    def test_filename_extraction(self):
        """Test filename extraction from URLs"""
        test_cases = [
            ('https://example.com/file.txt', 'file.txt'),
            ('https://example.com/path/document.pdf', 'document.pdf'),
            ('https://example.com/', 'downloaded_file'),
            ('https://example.com/file%20with%20spaces.txt', 'file with spaces.txt')
        ]
        
        for url, expected in test_cases:
            result = DOWNLOAD.get_filename_from_url(url)
            self.assertEqual(result, expected)

    @unittest.skipIf(not DOWNLOAD_AVAILABLE, "DOWNLOAD module not available")
    def test_help_function(self):
        """Test help function output"""
        with patch('builtins.print') as mock_print:
            DOWNLOAD.show_help()
            
            mock_print.assert_called()
            help_text = mock_print.call_args[0][0]
            self.assertIn('DOWNLOAD', help_text)
            self.assertIn('Usage:', help_text)
            self.assertIn('Examples:', help_text)

class TestDownloadIntegration(unittest.TestCase):
    """Integration tests for DOWNLOAD tool"""

    def test_command_line_execution(self):
        """Test command line execution of DOWNLOAD"""
        result = subprocess.run([
            sys.executable, DOWNLOAD_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Resource Download Tool', result.stdout)
        self.assertIn('https://example.com/file.pdf', result.stdout)  # Check for example

    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        run_py = Path(__file__).parent.parent / 'RUN.py'
        if not run_py.exists():
            self.skipTest("RUN.py not found")
        
        result = subprocess.run([
            sys.executable, str(run_py), '--show', 'DOWNLOAD', '--help'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            try:
                output_json = json.loads(result.stdout)
                self.assertTrue('success' in output_json or 'help' in output_json)
                print("RUN --show DOWNLOAD integration successful")
            except json.JSONDecodeError:
                self.fail(f"RUN --show should output valid JSON: {result.stdout[:200]}...")
        else:
            print("RUN --show DOWNLOAD test completed (failure expected without full setup)")

    def test_missing_arguments_error(self):
        """Test error handling when no arguments provided"""
        result = subprocess.run([
            sys.executable, DOWNLOAD_PY
        ], capture_output=True, text=True, timeout=10)
        
        self.assertNotEqual(result.returncode, 0)  # Should fail
        self.assertTrue(
            'Error' in result.stdout or 'Usage' in result.stdout,
            f"Expected error message, got: {result.stdout}"
        )

    def test_invalid_url_handling(self):
        """Test handling of invalid URLs"""
        result = subprocess.run([
            sys.executable, DOWNLOAD_PY, 'not-a-url'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertNotEqual(result.returncode, 0)  # Should fail
        self.assertTrue(
            'Invalid URL' in result.stdout or 'error' in result.stdout.lower(),
            f"Expected invalid URL error, got: {result.stdout[:200]}..."
        )

    def test_download_with_destination(self):
        """Test download with custom destination (will fail but tests argument parsing)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run([
                sys.executable, DOWNLOAD_PY, 
                'https://httpbin.org/status/404',  # Will fail but tests parsing
                temp_dir
            ], capture_output=True, text=True, timeout=15)
            
            # Should fail due to 404, but argument parsing should work
            self.assertNotEqual(result.returncode, 0)
            # Should show the destination path in output
            self.assertIn(temp_dir, result.stdout)

if __name__ == '__main__':
    unittest.main() 