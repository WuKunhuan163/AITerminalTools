#!/usr/bin/env python3
"""
Script to run EXPORT and GOOGLE_DRIVE tests with detailed output
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from _TEST import BinToolsIntegrationTest

if __name__ == "__main__":
    # Create test suite with EXPORT and GOOGLE_DRIVE tests
    suite = unittest.TestSuite()
    suite.addTest(BinToolsIntegrationTest('test_09_export'))
    suite.addTest(BinToolsIntegrationTest('test_07_google_drive'))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1) 