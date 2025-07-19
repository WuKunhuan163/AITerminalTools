#!/usr/bin/env python3
"""
Unit tests for GOOGLE_DRIVE tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import GOOGLE_DRIVE
except ImportError:
    GOOGLE_DRIVE = None

class TestGoogleDrive(unittest.TestCase):
    """Test cases for GOOGLE_DRIVE tool"""
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(GOOGLE_DRIVE.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_DATA_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(GOOGLE_DRIVE.is_run_environment())
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = GOOGLE_DRIVE.create_json_output(
            success=True,
            message="Browser opened successfully",
            url="https://drive.google.com/"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('url', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    def test_url_construction(self):
        """Test URL construction for different scenarios"""
        # Test default URL
        url = GOOGLE_DRIVE.get_drive_url()
        self.assertEqual(url, "https://drive.google.com/")
        
        # Test My Drive URL
        url = GOOGLE_DRIVE.get_drive_url(my_drive=True)
        self.assertEqual(url, "https://drive.google.com/drive/my-drive")
        
        # Test custom URL
        custom_url = "https://drive.google.com/drive/folders/123456"
        url = GOOGLE_DRIVE.get_drive_url(custom_url=custom_url)
        self.assertEqual(url, custom_url)
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test default arguments
        args = GOOGLE_DRIVE.parse_arguments([])
        self.assertFalse(args.my)
        self.assertIsNone(args.url)
        
        # Test -my flag
        args = GOOGLE_DRIVE.parse_arguments(['-my'])
        self.assertTrue(args.my)
        
        # Test custom URL
        args = GOOGLE_DRIVE.parse_arguments(['https://drive.google.com/drive/folders/123'])
        self.assertEqual(args.url, 'https://drive.google.com/drive/folders/123')
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    @patch('webbrowser.open')
    def test_browser_opening(self, mock_browser_open):
        """Test browser opening functionality"""
        mock_browser_open.return_value = True
        
        result = GOOGLE_DRIVE.open_browser("https://drive.google.com/")
        
        self.assertTrue(result['success'])
        mock_browser_open.assert_called_once_with("https://drive.google.com/")
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    @patch('webbrowser.open')
    def test_browser_opening_failure(self, mock_browser_open):
        """Test browser opening failure"""
        mock_browser_open.side_effect = Exception("Browser not found")
        
        result = GOOGLE_DRIVE.open_browser("https://drive.google.com/")
        
        self.assertFalse(result['success'])
        self.assertIn('failed', result['message'].lower())
    
    @unittest.skipIf(GOOGLE_DRIVE is None, "GOOGLE_DRIVE module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['GOOGLE_DRIVE.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    GOOGLE_DRIVE.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()

class TestGoogleDriveIntegration(unittest.TestCase):
    """Integration tests for GOOGLE_DRIVE tool"""
    
    def test_command_line_execution(self):
        """Test command line execution of GOOGLE_DRIVE"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'GOOGLE_DRIVE.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Open Google Drive', result.stdout)
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'GOOGLE_DRIVE'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show GOOGLE_DRIVE did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 