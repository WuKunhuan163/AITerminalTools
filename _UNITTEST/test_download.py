#!/usr/bin/env python3
"""
Unit tests for DOWNLOAD tool
"""

import unittest
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import DOWNLOAD
except ImportError:
    DOWNLOAD = None

class TestDownload(unittest.TestCase):
    """Test cases for DOWNLOAD tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(DOWNLOAD.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_OUTPUT_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(DOWNLOAD.is_run_environment())
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = DOWNLOAD.create_json_output(
            success=True,
            message="Download completed successfully",
            url="https://example.com/file.txt",
            destination="/tmp/file.txt",
            file_size=1024
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('url', result)
        self.assertIn('destination', result)
        self.assertIn('file_size', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        valid_urls = [
            'https://example.com/file.txt',
            'http://example.com/file.pdf',
            'https://github.com/user/repo/archive/main.zip'
        ]
        for url in valid_urls:
            self.assertTrue(DOWNLOAD.is_valid_url(url))
        
        # Invalid URLs
        invalid_urls = [
            'not_a_url',
            'ftp://example.com/file.txt',
            'file:///local/file.txt',
            ''
        ]
        for url in invalid_urls:
            self.assertFalse(DOWNLOAD.is_valid_url(url))
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_filename_extraction(self):
        """Test filename extraction from URLs"""
        test_cases = [
            ('https://example.com/file.txt', 'file.txt'),
            ('https://example.com/path/to/document.pdf', 'document.pdf'),
            ('https://example.com/file?param=value', 'file'),
            ('https://example.com/', 'download')
        ]
        
        for url, expected in test_cases:
            result = DOWNLOAD.extract_filename(url)
            self.assertEqual(result, expected)
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test basic download
        args = DOWNLOAD.parse_arguments(['https://example.com/file.txt'])
        self.assertEqual(args.url, 'https://example.com/file.txt')
        self.assertEqual(args.destination, '.')  # default
        
        # Test with destination
        args = DOWNLOAD.parse_arguments(['https://example.com/file.txt', '/tmp/'])
        self.assertEqual(args.destination, '/tmp/')
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    @patch('requests.get')
    def test_download_success(self, mock_get):
        """Test successful download"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content = lambda chunk_size: [b'test content']
        mock_get.return_value = mock_response
        
        result = DOWNLOAD.download_file(
            'https://example.com/file.txt',
            str(self.test_dir / 'file.txt')
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['file_size'], 1024)
        mock_get.assert_called_once()
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    @patch('requests.get')
    def test_download_failure(self, mock_get):
        """Test download failure"""
        mock_get.side_effect = Exception("Network error")
        
        result = DOWNLOAD.download_file(
            'https://example.com/file.txt',
            str(self.test_dir / 'file.txt')
        )
        
        self.assertFalse(result['success'])
        self.assertIn('failed', result['message'].lower())
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_directory_creation(self):
        """Test automatic directory creation"""
        dest_dir = self.test_dir / 'new_dir'
        dest_file = dest_dir / 'file.txt'
        
        result = DOWNLOAD.ensure_directory(str(dest_file))
        
        self.assertTrue(result['success'])
        self.assertTrue(dest_dir.exists())
    
    @unittest.skipIf(DOWNLOAD is None, "DOWNLOAD module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['DOWNLOAD.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    DOWNLOAD.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()

class TestDownloadIntegration(unittest.TestCase):
    """Integration tests for DOWNLOAD tool"""
    
    def test_command_line_execution(self):
        """Test command line execution of DOWNLOAD"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'DOWNLOAD.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Download files from URLs', result.stdout)
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'DOWNLOAD'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show DOWNLOAD did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 