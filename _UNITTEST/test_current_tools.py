#!/usr/bin/env python3
"""
Script to run all currently active tests with detailed output
"""

import sys
import unittest
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from _TEST import BinToolsIntegrationTest

if __name__ == "__main__":
    # Create test suite with all currently active tests
    suite = unittest.TestSuite()
    suite.addTest(BinToolsIntegrationTest('test_05_overleaf_compilation'))
    suite.addTest(BinToolsIntegrationTest('test_07_google_drive'))
    suite.addTest(BinToolsIntegrationTest('test_08_search_paper'))
    suite.addTest(BinToolsIntegrationTest('test_09_export'))
    suite.addTest(BinToolsIntegrationTest('test_10_download'))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1) 