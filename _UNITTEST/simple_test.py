#!/usr/bin/env python3
"""
Simple test script to debug issues
"""

import os
import sys
import subprocess
from pathlib import Path

def test_basic_functionality():
    """Test basic functionality of tools"""
    print("Testing basic functionality...")
    
    # Test OVERLEAF help
    try:
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'OVERLEAF.py'),
            '--help'
        ], capture_output=True, text=True, timeout=10)
        
        print(f"OVERLEAF help: {result.returncode}")
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"OVERLEAF error: {e}")
    
    # Test RUN --show
    try:
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--help'
        ], capture_output=True, text=True, timeout=10)
        
        print(f"RUN help: {result.returncode}")
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"RUN error: {e}")

if __name__ == '__main__':
    test_basic_functionality() 