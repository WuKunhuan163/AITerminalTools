#!/usr/bin/env python3
"""
Unit tests for EXPORT tool
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
    import EXPORT
except ImportError:
    EXPORT = None

class TestExport(unittest.TestCase):
    """Test cases for EXPORT tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = str(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        if self.original_home:
            os.environ['HOME'] = self.original_home
        else:
            del os.environ['HOME']
        import shutil
        shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(EXPORT.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_OUTPUT_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(EXPORT.is_run_environment())
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = EXPORT.create_json_output(
            success=True,
            message="Variable exported successfully",
            variable_name="TEST_VAR",
            variable_value="test_value"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('variable_name', result)
        self.assertIn('variable_value', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    def test_variable_name_validation(self):
        """Test environment variable name validation"""
        # Valid names
        valid_names = ['TEST_VAR', 'API_KEY', 'MY_VAR_123', '_PRIVATE_VAR']
        for name in valid_names:
            self.assertTrue(EXPORT.is_valid_variable_name(name))
        
        # Invalid names
        invalid_names = ['123_VAR', 'test-var', 'test.var', 'test var', '']
        for name in invalid_names:
            self.assertFalse(EXPORT.is_valid_variable_name(name))
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test basic export
        args = EXPORT.parse_arguments(['TEST_VAR', 'test_value'])
        self.assertEqual(args.variable_name, 'TEST_VAR')
        self.assertEqual(args.variable_value, 'test_value')
        
        # Test with quotes
        args = EXPORT.parse_arguments(['API_KEY', '"sk-123456"'])
        self.assertEqual(args.variable_name, 'API_KEY')
        self.assertEqual(args.variable_value, '"sk-123456"')
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    @patch('builtins.open', new_callable=mock_open, read_data='# Test file\nexport OLD_VAR="old_value"\n')
    def test_remove_existing_export(self, mock_file):
        """Test removal of existing export statements"""
        result = EXPORT.remove_existing_export('/fake/path', 'OLD_VAR')
        
        self.assertIn('# Test file', result)
        self.assertNotIn('export OLD_VAR=', result)
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_update_shell_config(self, mock_exists, mock_file):
        """Test updating shell configuration files"""
        mock_exists.return_value = True
        
        result = EXPORT.update_shell_config('TEST_VAR', 'test_value')
        
        self.assertTrue(result['success'])
        # Should try to update multiple config files
        self.assertGreater(mock_file.call_count, 1)
    
    @unittest.skipIf(EXPORT is None, "EXPORT module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['EXPORT.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    EXPORT.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()

class TestExportIntegration(unittest.TestCase):
    """Integration tests for EXPORT tool"""
    
    def test_command_line_execution(self):
        """Test command line execution of EXPORT"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'EXPORT.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Export environment variable', result.stdout)
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'EXPORT'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show EXPORT did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 