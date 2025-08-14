#!/usr/bin/env python3
"""
Simple runner for GDS Echo Comprehensive Tests
"""

import sys
from pathlib import Path

# Add the test directory to Python path
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))

# Import and run the tests
from test_gds_echo_comprehensive import run_echo_tests

if __name__ == '__main__':
    print("🎯 GDS Echo Comprehensive Test Runner")
    print("=" * 50)
    
    # Confirm with user
    try:
        response = input("This will run comprehensive echo tests with user interaction. Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Test execution cancelled")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n❌ Test execution cancelled")
        sys.exit(1)
    
    print("\n🚀 Starting echo tests...")
    success = run_echo_tests()
    
    if success:
        print("\n✅ All echo tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some echo tests failed!")
        sys.exit(1) 