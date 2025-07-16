#!/usr/bin/env python3
"""
Manual test runner to check which tests pass/fail
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the test class
from _UNITTEST._TEST import BinToolsIntegrationTest

def run_single_test(test_class, test_method_name):
    """Run a single test method"""
    try:
        # Create test instance
        test_instance = test_class()
        
        # Set up class if needed
        if hasattr(test_class, 'setUpClass'):
            test_class.setUpClass()
        
        # Run the specific test
        test_method = getattr(test_instance, test_method_name)
        test_method()
        
        print(f"✅ {test_method_name} - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ {test_method_name} - FAILED: {str(e)}")
        return False

def main():
    """Run all tests manually"""
    print("="*60)
    print("MANUAL TEST RUNNER")
    print("="*60)
    
    test_class = BinToolsIntegrationTest
    
    # List of test methods in order
    test_methods = [
        'test_01_file_existence',
        'test_02_bin_json_registry', 
        'test_03_bin_py_management',
        'test_04_run_output_directory',
        'test_05_overleaf_compilation',
        'test_06_extract_pdf',
        'test_07_google_drive',
        'test_08_search_paper',
        'test_09_export',
        'test_10_download',
        'test_11_run_show_integration'
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        print(f"\n{'='*50}")
        print(f"Running {test_method}")
        print('='*50)
        
        if run_single_test(test_class, test_method):
            passed += 1
        else:
            failed += 1
    
    # Clean up
    try:
        if hasattr(test_class, 'tearDownClass'):
            test_class.tearDownClass()
    except:
        pass
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print('='*60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    print(f"Success rate: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main()) 