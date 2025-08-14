#!/usr/bin/env python3
"""
Comprehensive runner for all GDS (Google Drive Shell) tests.

This script runs all available GDS tests including:
1. New comprehensive tests (read, edit, upload, echo with all variations)
2. Original upload improvement tests (with temporary folder support)
3. Basic functionality tests

All tests use temporary folders in ~/tmp to avoid conflicts with existing files.
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_comprehensive_tests():
    """Run the new comprehensive GDS tests"""
    print("🧪 Running Comprehensive GDS Tests...")
    print("=" * 60)
    print("This includes tests for:")
    print("- Echo, Upload, Read, Edit commands with all options")
    print("- Cat, Grep, Find, Mv, Download commands")
    print("- Python execution and Virtual environment management")
    print("- Advanced workflows and error handling")
    print()
    
    test_file = Path(__file__).parent / "test_gds_comprehensive.py"
    result = subprocess.run([sys.executable, str(test_file)], cwd=Path(__file__).parent)
    
    return result.returncode == 0

def run_upload_improvement_tests():
    """Run the upload improvement tests"""
    print("🧪 Running Upload Improvement Tests...")
    print("=" * 60)
    print("This includes tests for:")
    print("- Sequential upload and validation")
    print("- Progress display improvements")
    print("- Parameter parsing (--force, --target-dir, --remove-local)")
    print("- Upload-folder improvements")
    print()
    
    test_file = Path(__file__).parent / "test_google_drive.py"
    result = subprocess.run([
        sys.executable, str(test_file), "--upload-improvements"
    ], cwd=Path(__file__).parent)
    
    return result.returncode == 0

def run_traditional_tests():
    """Run traditional GDS functionality tests"""
    print("🧪 Running Traditional GDS Tests...")
    print("=" * 60)
    print("This includes tests for:")
    print("- Basic command functionality")
    print("- Shell management")
    print("- Desktop integration")
    print("- Return command functionality")
    print()
    
    test_file = Path(__file__).parent / "test_google_drive.py"
    result = subprocess.run([sys.executable, str(test_file)], cwd=Path(__file__).parent)
    
    return result.returncode == 0

def main():
    """Main function to run GDS tests"""
    parser = argparse.ArgumentParser(
        description="Comprehensive GDS Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  comprehensive    - New comprehensive tests (read, edit, upload, echo, etc.)
  upload          - Upload improvement tests with temporary folders  
  traditional     - Traditional functionality and shell management tests
  all            - Run all test categories (default)

Examples:
  python3 run_all_gds_tests.py                    # Run all tests
  python3 run_all_gds_tests.py --category comprehensive  # Only comprehensive
  python3 run_all_gds_tests.py --category upload         # Only upload tests
  python3 run_all_gds_tests.py --no-confirm             # Skip confirmation
        """
    )
    
    parser.add_argument(
        '--category',
        choices=['comprehensive', 'upload', 'traditional', 'all'],
        default='all',
        help='Test category to run (default: all)'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    print("🧪 GDS Comprehensive Test Runner")
    print("=" * 60)
    print()
    
    if args.category == 'all':
        print("This will run ALL GDS tests including:")
        print("✅ Comprehensive tests (27 test methods)")
        print("✅ Upload improvement tests (4 test methods)")  
        print("✅ Traditional functionality tests (40+ test methods)")
    elif args.category == 'comprehensive':
        print("This will run COMPREHENSIVE GDS tests including:")
        print("✅ All major command variations and options")
        print("✅ Advanced workflows and integration tests")
    elif args.category == 'upload':
        print("This will run UPLOAD IMPROVEMENT tests including:")
        print("✅ Sequential upload and validation")
        print("✅ Progress display improvements")
    elif args.category == 'traditional':
        print("This will run TRADITIONAL GDS tests including:")
        print("✅ Basic command functionality")
        print("✅ Shell management and desktop integration")
    
    print()
    print("📝 All tests require user interaction through tkinter windows")
    print("⏰ No timeouts are set - take your time to complete each step")
    print("📁 Tests use temporary folders in ~/tmp with hashed timestamps")
    print("🧹 Automatic cleanup after each test category")
    print()
    
    if not args.no_confirm:
        response = input("Do you want to proceed with the tests? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Tests cancelled.")
            return 0
    
    print()
    print("🚀 Starting GDS tests...")
    print()
    
    success_count = 0
    total_count = 0
    
    try:
        if args.category in ['all', 'comprehensive']:
            print("📊 [1/3] Running Comprehensive Tests..." if args.category == 'all' else "📊 Running Comprehensive Tests...")
            if run_comprehensive_tests():
                print("✅ Comprehensive tests completed successfully!")
                success_count += 1
            else:
                print("❌ Comprehensive tests failed!")
            total_count += 1
            print()
        
        if args.category in ['all', 'upload']:
            print("📊 [2/3] Running Upload Improvement Tests..." if args.category == 'all' else "📊 Running Upload Improvement Tests...")
            if run_upload_improvement_tests():
                print("✅ Upload improvement tests completed successfully!")
                success_count += 1
            else:
                print("❌ Upload improvement tests failed!")
            total_count += 1
            print()
        
        if args.category in ['all', 'traditional']:
            print("📊 [3/3] Running Traditional Tests..." if args.category == 'all' else "📊 Running Traditional Tests...")
            if run_traditional_tests():
                print("✅ Traditional tests completed successfully!")
                success_count += 1
            else:
                print("❌ Traditional tests failed!")
            total_count += 1
            print()
        
        # Final summary
        print("=" * 60)
        print(f"📊 Final Results: {success_count}/{total_count} test categories passed")
        
        if success_count == total_count:
            print("🎉 All test categories completed successfully!")
            return 0
        else:
            print("⚠️  Some test categories failed. Check the output above for details.")
            return 1
            
    except KeyboardInterrupt:
        print()
        print("🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 