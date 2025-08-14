#!/usr/bin/env python3
"""
Simple runner script for GDS comprehensive tests.

This script provides an easy way to run the newly created comprehensive tests
for GDS read, edit, upload, and echo commands.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Main function to run GDS comprehensive tests"""
    print("🧪 GDS Comprehensive Test Runner")
    print("=" * 50)
    print()
    print("This will run comprehensive tests for:")
    print("- GDS read command (with --force, line ranges, multiple ranges)")
    print("- GDS edit command (line-based, text-based, --preview, --backup)")
    print("- GDS upload command (single/multiple files, --target-dir)")
    print("- GDS echo command (basic text, file creation)")
    print()
    print("📝 These tests require user interaction through tkinter windows")
    print("⏰ No timeouts are set - take your time to complete each step")
    print("📁 Tests use temporary folders in ~/tmp with hashed timestamps")
    print()
    
    # Ask user for confirmation
    response = input("Do you want to proceed with the tests? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Tests cancelled.")
        return 0
    
    print()
    print("🚀 Starting comprehensive tests...")
    print()
    
    # Run the comprehensive tests
    test_file = Path(__file__).parent / "test_gds_comprehensive.py"
    
    try:
        result = subprocess.run([
            sys.executable, str(test_file)
        ], cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print()
            print("✅ All comprehensive tests completed successfully!")
        else:
            print()
            print("❌ Some tests failed. Check the output above for details.")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print()
        print("🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 