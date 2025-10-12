#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_PROJ')

from google_drive_shell import GoogleDriveShell

def test_simple_echo():
    shell = GoogleDriveShell()
    
    print("=== Testing simple echo ===")
    cmd1 = 'echo "hello world" > test1.txt'
    print(f"Command: {cmd1}")
    result1 = shell.execute_shell_command(cmd1)
    print(f"Result: {result1}")
    
    print("\n=== Testing JSON echo ===")
    cmd2 = 'echo "{\"name\": \"test\"}" > test2.txt'
    print(f"Command: {cmd2}")
    result2 = shell.execute_shell_command(cmd2)
    print(f"Result: {result2}")

if __name__ == "__main__":
    test_simple_echo()
