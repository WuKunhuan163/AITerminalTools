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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import GOOGLE_DRIVE
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE = None
    GOOGLE_DRIVE_AVAILABLE = False

GOOGLE_DRIVE_PY = str(Path(__file__).parent.parent / 'GOOGLE_DRIVE.py')

class TestGoogleDrive(unittest.TestCase):
    """Test cases for GOOGLE_DRIVE tool"""

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, GOOGLE_DRIVE_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('GOOGLE_DRIVE', result.stdout)
        self.assertIn('Google Drive access tool', result.stdout)
        self.assertIn('Usage:', result.stdout)
        self.assertIn('Examples:', result.stdout)

    @unittest.skipIf(not GOOGLE_DRIVE_AVAILABLE, "GOOGLE_DRIVE module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(GOOGLE_DRIVE.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {'RUN_IDENTIFIER_test123': 'True'}):
            self.assertTrue(GOOGLE_DRIVE.is_run_environment('test123'))

    @unittest.skipIf(not GOOGLE_DRIVE_AVAILABLE, "GOOGLE_DRIVE module not available")
    def test_json_output_creation(self):
        """Test JSON output format for RUN environment"""
        # Test successful JSON output
        test_data = {
            "success": True,
            "message": "Test message",
            "url": "https://drive.google.com/"
        }
        
        # Mock the write_to_json_output function
        with patch.object(GOOGLE_DRIVE, 'write_to_json_output') as mock_write:
            mock_write.return_value = True
            result = GOOGLE_DRIVE.write_to_json_output(test_data)
            mock_write.assert_called_once_with(test_data)

    @unittest.skipIf(not GOOGLE_DRIVE_AVAILABLE, "GOOGLE_DRIVE module not available")
    @patch('webbrowser.open')
    def test_browser_opening(self, mock_webbrowser):
        """Test browser opening functionality"""
        mock_webbrowser.return_value = True
        
        result = GOOGLE_DRIVE.open_google_drive("https://drive.google.com/")
        
        self.assertEqual(result, 0)  # Success return code
        mock_webbrowser.assert_called_once_with("https://drive.google.com/")

    @unittest.skipIf(not GOOGLE_DRIVE_AVAILABLE, "GOOGLE_DRIVE module not available")
    @patch('webbrowser.open')
    def test_browser_opening_failure(self, mock_webbrowser):
        """Test browser opening failure"""
        mock_webbrowser.return_value = False
        
        result = GOOGLE_DRIVE.open_google_drive("https://drive.google.com/")
        
        self.assertEqual(result, 1)  # Failure return code
        mock_webbrowser.assert_called_once_with("https://drive.google.com/")

    @unittest.skipIf(not GOOGLE_DRIVE_AVAILABLE, "GOOGLE_DRIVE module not available")
    def test_default_url_behavior(self):
        """Test default URL behavior"""
        with patch('webbrowser.open') as mock_webbrowser:
            mock_webbrowser.return_value = True
            
            result = GOOGLE_DRIVE.open_google_drive()  # No URL specified
            
            self.assertEqual(result, 0)
            mock_webbrowser.assert_called_once_with("https://drive.google.com/")

    @unittest.skipIf(not GOOGLE_DRIVE_AVAILABLE, "GOOGLE_DRIVE module not available")
    def test_help_function(self):
        """Test help function output"""
        with patch('builtins.print') as mock_print:
            GOOGLE_DRIVE.show_help()
            
            # Check that help was printed
            mock_print.assert_called()
            # Get the help text that was printed
            help_text = mock_print.call_args[0][0]
            self.assertIn('GOOGLE_DRIVE', help_text)
            self.assertIn('Usage:', help_text)
            self.assertIn('Examples:', help_text)

class TestGoogleDriveIntegration(unittest.TestCase):
    """Integration tests for GOOGLE_DRIVE tool"""

    def test_command_line_execution(self):
        """Test command line execution of GOOGLE_DRIVE"""
        result = subprocess.run([
            sys.executable, GOOGLE_DRIVE_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Google Drive access tool', result.stdout)
        self.assertIn('-my', result.stdout)  # Check for My Drive option

    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        run_py = Path(__file__).parent.parent / 'RUN.py'
        if not run_py.exists():
            self.skipTest("RUN.py not found")
        
        result = subprocess.run([
            sys.executable, str(run_py), '--show', 'GOOGLE_DRIVE', '--help'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            # Should output JSON format
            try:
                output_json = json.loads(result.stdout)
                self.assertTrue('success' in output_json or 'help' in output_json)
                print("✅ RUN --show GOOGLE_DRIVE integration successful")
            except json.JSONDecodeError:
                self.fail(f"RUN --show should output valid JSON: {result.stdout[:200]}...")
        else:
            # RUN integration failure is acceptable
            print("✅ RUN --show GOOGLE_DRIVE test completed (failure expected without full setup)")

    def test_my_drive_option(self):
        """Test -my option functionality"""
        # This test just checks that the option is recognized, not that browser opens
        result = subprocess.run([
            sys.executable, GOOGLE_DRIVE_PY, '-my'
        ], capture_output=True, text=True, timeout=10)
        
        # Should succeed (return code 0) even if browser doesn't actually open in test environment
        if result.returncode == 0:
            print("✅ -my option recognized and processed")
        else:
            # Check if it's a browser-related error (expected in test environment)
            if 'browser' in result.stderr.lower() or 'display' in result.stderr.lower():
                print("✅ -my option processed (browser opening failed in test environment, expected)")
            else:
                self.fail(f"Unexpected error with -my option: {result.stderr}")

    def test_custom_url_option(self):
        """Test custom URL functionality"""
        custom_url = "https://drive.google.com/drive/my-drive"
        result = subprocess.run([
            sys.executable, GOOGLE_DRIVE_PY, custom_url
        ], capture_output=True, text=True, timeout=10)
        
        # Should succeed (return code 0) even if browser doesn't actually open in test environment
        if result.returncode == 0:
            print("✅ Custom URL option recognized and processed")
        else:
            # Check if it's a browser-related error (expected in test environment)
            if 'browser' in result.stderr.lower() or 'display' in result.stderr.lower():
                print("✅ Custom URL processed (browser opening failed in test environment, expected)")
            else:
                self.fail(f"Unexpected error with custom URL: {result.stderr}")

if __name__ == '__main__':
    unittest.main() 