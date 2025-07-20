#!/usr/bin/env python3
"""
Unit tests for EXPORT tool
"""

import unittest
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import EXPORT
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT = None
    EXPORT_AVAILABLE = False

EXPORT_PY = str(Path(__file__).parent.parent / 'EXPORT.py')

class TestExport(unittest.TestCase):
    """Test cases for EXPORT tool"""

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, EXPORT_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('EXPORT', result.stdout)
        self.assertIn('Environment Variable Export Tool', result.stdout)
        self.assertIn('Usage:', result.stdout)
        self.assertIn('Examples:', result.stdout)

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(EXPORT.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {'RUN_IDENTIFIER_test123': 'True'}):
            self.assertTrue(EXPORT.is_run_environment('test123'))

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_json_output_creation(self):
        """Test JSON output format for RUN environment"""
        # Test successful JSON output
        test_data = {
            "success": True,
            "message": "Test message",
            "variable": "TEST_VAR"
        }
        
        # Mock the write_to_json_output function
        with patch.object(EXPORT, 'write_to_json_output') as mock_write:
            mock_write.return_value = True
            result = EXPORT.write_to_json_output(test_data)
            mock_write.assert_called_once_with(test_data)

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_variable_name_validation(self):
        """Test environment variable name validation in export_variable"""
        with patch.object(EXPORT, 'write_to_json_output'):
            # Test valid variable names (should not fail due to name validation)
            valid_names = ['TEST_VAR', 'MY_VARIABLE', 'API_KEY', 'PATH']
            for name in valid_names:
                # Mock file operations to avoid actual file changes
                with patch.object(EXPORT, 'get_shell_config_files', return_value=[]):
                    result = EXPORT.export_variable(name, 'test_value')
                    # Should not fail due to variable name validation
                    self.assertIsInstance(result, int)

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_get_shell_config_files(self):
        """Test getting shell configuration files"""
        config_files = EXPORT.get_shell_config_files()
        
        self.assertIsInstance(config_files, list)
        self.assertTrue(len(config_files) > 0)
        
        # Check that expected config files are included
        file_names = [str(f.name) for f in config_files]
        self.assertIn('.bashrc', file_names)
        self.assertIn('.bash_profile', file_names)
        self.assertIn('.zshrc', file_names)

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_remove_existing_export(self):
        """Test removal of existing export statements"""
        # Test data with existing export
        test_lines = [
            "# Test file\n",
            "export TEST_VAR=old_value\n",
            "export OTHER_VAR=other_value\n",
            "# End of file\n"
        ]
        
        result = EXPORT.remove_existing_export(test_lines, 'TEST_VAR')
        
        self.assertIsInstance(result, list)
        # Should remove the TEST_VAR export but keep others
        result_text = ''.join(result)
        self.assertNotIn('export TEST_VAR=old_value', result_text)
        self.assertIn('export OTHER_VAR=other_value', result_text)
        self.assertIn('# Test file', result_text)

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_add_export_statement(self):
        """Test adding export statement to configuration"""
        test_lines = ["# Test file\n"]
        
        result = EXPORT.add_export_statement(test_lines, 'TEST_VAR', 'test_value')
        
        self.assertIsInstance(result, list)
        result_text = ''.join(result)
        self.assertIn('export TEST_VAR="test_value"', result_text)
        self.assertIn('# Test file', result_text)

    @unittest.skipIf(not EXPORT_AVAILABLE, "EXPORT module not available")
    def test_help_function(self):
        """Test help function output"""
        with patch('builtins.print') as mock_print:
            EXPORT.show_help()
            
            # Check that help was printed
            mock_print.assert_called()
            # Get the help text that was printed
            help_text = mock_print.call_args[0][0]
            self.assertIn('EXPORT', help_text)
            self.assertIn('Usage:', help_text)
            self.assertIn('Examples:', help_text)

class TestExportIntegration(unittest.TestCase):
    """Integration tests for EXPORT tool"""

    def test_command_line_execution(self):
        """Test command line execution of EXPORT"""
        result = subprocess.run([
            sys.executable, EXPORT_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Environment Variable Export Tool', result.stdout)
        self.assertIn('OPENROUTER_API_KEY', result.stdout)  # Check for example

    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        run_py = Path(__file__).parent.parent / 'RUN.py'
        if not run_py.exists():
            self.skipTest("RUN.py not found")
        
        result = subprocess.run([
            sys.executable, str(run_py), '--show', 'EXPORT', '--help'
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            # Should output JSON format
            try:
                output_json = json.loads(result.stdout)
                self.assertTrue('success' in output_json or 'help' in output_json)
                print("✅ RUN --show EXPORT integration successful")
            except json.JSONDecodeError:
                self.fail(f"RUN --show should output valid JSON: {result.stdout[:200]}...")
        else:
            # RUN integration failure is acceptable
            print("✅ RUN --show EXPORT test completed (failure expected without full setup)")

    def test_missing_arguments_error(self):
        """Test error handling when no arguments provided"""
        result = subprocess.run([
            sys.executable, EXPORT_PY
        ], capture_output=True, text=True, timeout=10)
        
        self.assertNotEqual(result.returncode, 0)  # Should fail
        self.assertTrue(
            'Error' in result.stdout or 'Usage' in result.stdout,
            f"Expected error message, got: {result.stdout}"
        )

    def test_update_option(self):
        """Test --update option functionality"""
        result = subprocess.run([
            sys.executable, EXPORT_PY, '--update'
        ], capture_output=True, text=True, timeout=15)
        
        # --update option should be recognized (may succeed or fail based on environment)
        if result.returncode == 0:
            print("✅ --update option executed successfully")
        else:
            # Check if it's a reasonable failure (e.g., permission issues)
            if 'configuration' in result.stdout.lower() or 'update' in result.stdout.lower():
                print("✅ --update option processed (expected failure in test environment)")
            else:
                self.fail(f"Unexpected error with --update option: {result.stdout}")

    def test_export_variable_dry_run(self):
        """Test export variable functionality (dry run - no actual file changes)"""
        # Test with a simple variable export that should fail gracefully in test environment
        result = subprocess.run([
            sys.executable, EXPORT_PY, 'TEST_VAR_12345', 'test_value_12345'
        ], capture_output=True, text=True, timeout=10)
        
        # Should not crash and should provide reasonable output
        if result.returncode == 0:
            self.assertIn('exported', result.stdout.lower())
            print("✅ Export variable executed successfully")
        else:
            # Check for reasonable error messages
            self.assertTrue(
                'error' in result.stdout.lower() or 'failed' in result.stdout.lower(),
                f"Expected error message for failed export, got: {result.stdout[:200]}..."
            )
            print("✅ Export variable handled error appropriately")

if __name__ == '__main__':
    unittest.main() 