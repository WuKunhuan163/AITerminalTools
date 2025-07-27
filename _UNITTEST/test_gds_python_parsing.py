#!/usr/bin/env python3
"""
Unit test for GDS python command parsing
Testing multi-line string parsing issues
"""

import sys
import os
import re
import shlex

# Add the parent directory to path to import GOOGLE_DRIVE
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_python_command_parsing():
    """Test python -c command parsing with different quote styles"""
    
    # Test cases
    test_cases = [
        # Single line with double quotes
        'python -c "print(\'hello world\')"',
        
        # Single line with triple quotes  
        'python -c """print("hello world")"""',
        
        # Multi-line with triple quotes
        '''python -c """
import os
print("Current directory:", os.getcwd())
print("Hello from multi-line!")
"""''',
        
        # Complex multi-line case
        '''python -c """
import os
try:
    with open('test.txt', 'r') as f:
        content = f.read()
    print('File content:', content)
except Exception as e:
    print(f'Error: {e}')
"""''',
    ]
    
    print("Testing python command parsing:")
    print("=" * 50)
    
    for i, shell_cmd in enumerate(test_cases, 1):
        print(f"\nTest case {i}:")
        print(f"Input: {repr(shell_cmd)}")
        
        # Current parsing logic from GOOGLE_DRIVE.py
        try:
            cmd_parts = shlex.split(shell_cmd)
        except ValueError as e:
            print(f"  shlex.split failed: {e}")
            cmd_parts = shell_cmd.split()
        
        print(f"  shlex result: {cmd_parts}")
        
        cmd = cmd_parts[0]
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        # Current regex fix from GOOGLE_DRIVE.py
        if cmd == "python" and len(args) >= 1 and (len(args) == 1 or args[0] == "-c"):
            if len(args) == 1 and args[0] != "-c":
                # This might be the case where shlex failed to parse properly
                # Try to extract the full command
                match = re.search(r'python\s+-c\s+(.+)', shell_cmd, re.DOTALL)
                if match:
                    python_code = match.group(1).strip()
                    # Handle different quote styles
                    if python_code.startswith('"""') and python_code.endswith('"""'):
                        python_code = python_code[3:-3]
                    elif (python_code.startswith('"') and python_code.endswith('"')) or \
                         (python_code.startswith("'") and python_code.endswith("'")):
                        python_code = python_code[1:-1]
                    args = ["-c", python_code]
                    print(f"  Fixed args: {args}")
                else:
                    print(f"  No regex match found")
            elif args[0] == "-c":
                # Re-extract from original command
                match = re.search(r'python\s+-c\s+(.+)', shell_cmd, re.DOTALL)
                if match:
                    python_code = match.group(1).strip()
                    # Handle different quote styles
                    if python_code.startswith('"""') and python_code.endswith('"""'):
                        python_code = python_code[3:-3]
                    elif (python_code.startswith('"') and python_code.endswith('"')) or \
                         (python_code.startswith("'") and python_code.endswith("'")):
                        python_code = python_code[1:-1]
                    args = ["-c", python_code]
                    print(f"  Fixed args: {args}")
                else:
                    print(f"  No regex match found")
        
        print(f"  Final command: {cmd}")
        print(f"  Final args: {args}")
        
        # Test if the extracted code is valid Python
        if len(args) >= 2 and args[0] == "-c":
            try:
                compile(args[1], '<string>', 'exec')
                print(f"  ✅ Python code is valid")
            except SyntaxError as e:
                print(f"  ❌ Python syntax error: {e}")
        else:
            print(f"  ❌ Invalid command structure")

if __name__ == "__main__":
    test_python_command_parsing() 