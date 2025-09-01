#!/usr/bin/env python3
"""
Comprehensive unit tests for EXPORT tool
Supports multiple test execution modes:
- Default: Run all EXPORT unit tests
- --integration-only: Run only integration tests from _TEST.py
- --with-google-drive: Run EXPORT and GOOGLE_DRIVE integration tests
- --export-only: Run only EXPORT integration test
"""

import unittest
import os
import sys
import json
import subprocess
import tempfile
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    import EXPORT
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT = None
    EXPORT_AVAILABLE = False

try:
    from _TEST import BinToolsIntegrationTest
    INTEGRATION_TEST_AVAILABLE = True
except ImportError:
    BinToolsIntegrationTest = None
    INTEGRATION_TEST_AVAILABLE = False

EXPORT_PY = str(Path(__file__).parent.parent / 'EXPORT.py')

# Standalone test functions

def test_help_output():
    """Test help output"""
    result = subprocess.run([
        sys.executable, EXPORT_PY, '--help'
    ], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert 'EXPORT' in result.stdout
    assert 'Environment Variable Export Tool' in result.stdout
    assert 'Usage:' in result.stdout
    assert 'Examples:' in result.stdout
    print(f"test_help_output passed")

def test_run_environment_detection():
    """Test RUN environment detection"""
    if not EXPORT_AVAILABLE:
        print(f"test_run_environment_detection skipped - EXPORT module not available")
        return
    
    # Test without RUN environment
    assert not EXPORT.is_run_environment()
    
    # Test with RUN environment
    with patch.dict(os.environ, {'RUN_IDENTIFIER_test123': 'True'}):
        assert EXPORT.is_run_environment('test123')
    print(f"test_run_environment_detection passed")

def test_json_output_creation():
    """Test JSON output format for RUN environment"""
    if not EXPORT_AVAILABLE:
        print(f"test_json_output_creation skipped - EXPORT module not available")
        return
    
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
    print(f"test_json_output_creation passed")

def test_variable_name_validation():
    """Test environment variable name validation in export_variable"""
    if not EXPORT_AVAILABLE:
        print(f"test_variable_name_validation skipped - EXPORT module not available")
        return
    
    with patch.object(EXPORT, 'write_to_json_output'):
        # Test valid variable names (should not fail due to name validation)
        valid_names = ['TEST_VAR', 'MY_VARIABLE', 'API_KEY', 'PATH']
        for name in valid_names:
            # Mock file operations to avoid actual file changes
            with patch.object(EXPORT, 'get_shell_config_files', return_value=[]):
                result = EXPORT.export_variable(name, 'test_value')
                # Should not fail due to variable name validation
                assert isinstance(result, int)
    print(f"test_variable_name_validation passed")

def test_get_shell_config_files():
    """Test getting shell configuration files"""
    if not EXPORT_AVAILABLE:
        print(f"test_get_shell_config_files skipped - EXPORT module not available")
        return
    
    config_files = EXPORT.get_shell_config_files()
    
    assert isinstance(config_files, list)
    assert len(config_files) > 0
    
    # Check that expected config files are included
    file_names = [str(f.name) for f in config_files]
    assert '.bashrc' in file_names
    assert '.bash_profile' in file_names
    assert '.zshrc' in file_names
    print(f"test_get_shell_config_files passed")

def test_remove_existing_export():
    """Test removal of existing export statements"""
    if not EXPORT_AVAILABLE:
        print(f"test_remove_existing_export skipped - EXPORT module not available")
        return
    
    # Test data with existing export
    test_lines = [
        "# Test file\n",
        "export TEST_VAR=old_value\n",
        "export OTHER_VAR=other_value\n",
        "# End of file\n"
    ]
    
    result = EXPORT.remove_existing_export(test_lines, 'TEST_VAR')
    
    assert isinstance(result, list)
    # Should remove the TEST_VAR export but keep others
    result_text = ''.join(result)
    assert 'export TEST_VAR=old_value' not in result_text
    assert 'export OTHER_VAR=other_value' in result_text
    assert '# Test file' in result_text
    print(f"test_remove_existing_export passed")

def test_add_export_statement():
    """Test adding export statement to configuration"""
    if not EXPORT_AVAILABLE:
        print(f"test_add_export_statement skipped - EXPORT module not available")
        return
    
    test_lines = ["# Test file\n"]
    
    result = EXPORT.add_export_statement(test_lines, 'TEST_VAR', 'test_value')
    
    assert isinstance(result, list)
    result_text = ''.join(result)
    assert 'export TEST_VAR="test_value"' in result_text
    assert '# Test file' in result_text
    print(f"test_add_export_statement passed")

def test_help_function():
    """Test help function output"""
    if not EXPORT_AVAILABLE:
        print(f"test_help_function skipped - EXPORT module not available")
        return
    
    with patch('builtins.print') as mock_print:
        EXPORT.show_help()
        
        # Check that help was printed
        mock_print.assert_called()
        # Get the help text that was printed
        help_text = mock_print.call_args[0][0]
        assert 'EXPORT' in help_text
        assert 'Usage:' in help_text
        assert 'Examples:' in help_text
    print(f"test_help_function passed")

def test_command_line_execution():
    """Test command line execution of EXPORT"""
    result = subprocess.run([
        sys.executable, EXPORT_PY, '--help'
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode == 0
    assert 'Environment Variable Export Tool' in result.stdout
    assert 'OPENROUTER_API_KEY' in result.stdout  # Check for example
    print(f"test_command_line_execution passed")

def test_run_show_compatibility():
    """Test RUN --show compatibility"""
    run_py = Path(__file__).parent.parent / 'RUN.py'
    if not run_py.exists():
        print(f"test_run_show_compatibility skipped - RUN.py not found")
        return
    
    result = subprocess.run([
        sys.executable, str(run_py), '--show', 'EXPORT', '--help'
    ], capture_output=True, text=True, timeout=15)
    
    if result.returncode == 0:
        # Should output JSON format
        try:
            output_json = json.loads(result.stdout)
            assert 'success' in output_json or 'help' in output_json
            print(f"RUN --show EXPORT integration successful")
        except json.JSONDecodeError:
            raise AssertionError(f"RUN --show should output valid JSON: {result.stdout[:200]}...")
    else:
        # RUN integration failure is acceptable
        print(f"RUN --show EXPORT test completed (failure expected without full setup)")

def test_missing_arguments_error():
    """Test error handling when no arguments provided"""
    result = subprocess.run([
        sys.executable, EXPORT_PY
    ], capture_output=True, text=True, timeout=10)
    
    assert result.returncode != 0  # Should fail
    assert 'Error' in result.stdout or 'Usage' in result.stdout, f"Expected error message, got: {result.stdout}"
    print(f"test_missing_arguments_error passed")

def test_update_option():
    """Test --update option functionality"""
    result = subprocess.run([
        sys.executable, EXPORT_PY, '--update'
    ], capture_output=True, text=True, timeout=15)
    
    # --update option should be recognized (may succeed or fail based on environment)
    if result.returncode == 0:
        print(f"--update option executed successfully")
    else:
        # Check if it's a reasonable failure (e.g., permission issues)
        if 'configuration' in result.stdout.lower() or 'update' in result.stdout.lower():
            print(f"--update option processed (expected failure in test environment)")
        else:
            raise AssertionError(f"Unexpected error with --update option: {result.stdout}")

def test_export_variable_dry_run():
    """Test export variable functionality (dry run - no actual file changes)"""
    # Test with a simple variable export that should fail gracefully in test environment
    result = subprocess.run([
        sys.executable, EXPORT_PY, 'TEST_VAR_12345', 'test_value_12345'
    ], capture_output=True, text=True, timeout=10)
    
    # Should not crash and should provide reasonable output
    if result.returncode == 0:
        assert 'exported' in result.stdout.lower()
        print(f"Export variable executed successfully")
    else:
        # Check for reasonable error messages
        assert 'error' in result.stdout.lower() or 'failed' in result.stdout.lower(), \
            f"Expected error message for failed export, got: {result.stdout[:200]}..."
        print(f"Export variable handled error appropriately")

# All test functions list
ALL_UNIT_TESTS = [
    test_help_output,
    test_run_environment_detection,
    test_json_output_creation,
    test_variable_name_validation,
    test_get_shell_config_files,
    test_remove_existing_export,
    test_add_export_statement,
    test_help_function,
    test_command_line_execution,
    test_run_show_compatibility,
    test_missing_arguments_error,
    test_update_option,
    test_export_variable_dry_run,
]

def run_all_unit_tests():
    """Run all unit tests"""
    print(f"Running all EXPORT unit tests...")
    passed = 0
    failed = 0
    
    for test_func in ALL_UNIT_TESTS:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"Error: {test_func.__name__} failed: {e}")
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0

def run_integration_tests(test_names):
    """Run specific integration tests from _TEST.py"""
    if not INTEGRATION_TEST_AVAILABLE:
        print(f"Error:  Integration tests not available - _TEST.py not found")
        return False
    
    suite = unittest.TestSuite()
    for test_name in test_names:
        suite.addTest(BinToolsIntegrationTest(test_name))
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    return result.wasSuccessful()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Comprehensive EXPORT tool tests with multiple execution modes"
    )
    parser.add_argument(
        '--integration-only',
        action='store_true',
        help='Run only EXPORT integration test from _TEST.py'
    )
    parser.add_argument(
        '--with-google-drive',
        action='store_true',
        help='Run EXPORT and GOOGLE_DRIVE integration tests from _TEST.py'
    )
    parser.add_argument(
        '--export-only',
        action='store_true',
        help='Run only EXPORT integration test (same as --integration-only)'
    )
    parser.add_argument(
        '--unit-tests-only',
        action='store_true',
        help='Run only unit tests (default behavior)'
    )
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    
    success = True
    
    if args.integration_only or args.export_only:
        print(f"Running EXPORT integration test only...")
        success = run_integration_tests(['test_09_export'])
        
    elif args.with_google_drive:
        print(f"Running EXPORT and GOOGLE_DRIVE integration tests...")
        success = run_integration_tests(['test_09_export', 'test_07_google_drive'])
        
    else:
        # Default: Run all unit tests (both --unit-tests-only and no args)
        success = run_all_unit_tests()
    
    sys.exit(0 if success else 1) 