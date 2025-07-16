#!/usr/bin/env python3
"""
Main entry script for LEARN system
Handles command detection and routing
"""

import sys
import subprocess
import re
from pathlib import Path


def detect_learn_command(user_input):
    """
    Detect if the user input is a LEARN command and determine its type.
    
    Returns:
        - "interactive" if just "LEARN" 
        - "direct" if "LEARN ..." with parameters
        - None if not a LEARN command
    """
    user_input = user_input.strip()
    
    # Check if it's a LEARN command
    if not user_input.upper().startswith("LEARN"):
        return None
    
    # If it's just "LEARN" or "LEARN " (with optional whitespace)
    if re.match(r'^LEARN\s*$', user_input, re.IGNORECASE):
        return "interactive"
    
    # If it has parameters
    if len(user_input) > 5:  # More than just "LEARN"
        return "direct"
    
    return None


def run_interactive_mode():
    """Run the interactive parameter collection."""
    script_path = Path(__file__).parent / "interactive_input.py"
    command_file = Path(__file__).parent / "learn_command.txt"
    
    try:
        # Remove any existing command file
        if command_file.exists():
            command_file.unlink()
        
        # Run the interactive script without capturing output so it can interact with user
        result = subprocess.run([sys.executable, str(script_path)])
        
        if result.returncode == 0:
            # Read the command from the file
            if command_file.exists():
                with open(command_file, 'r') as f:
                    command = f.read().strip()
                
                # Clean up the file
                command_file.unlink()
                
                if command:
                    return command
                else:
                    print("Interactive mode cancelled by user.")
                    return None
            else:
                print("No command file generated.")
                return None
        
        print("Interactive mode failed.")
        return None
        
    except Exception as e:
        print(f"Error running interactive mode: {e}")
        return None


def run_direct_mode(command):
    """Run the direct command execution."""
    main_script_path = Path(__file__).parent / "main.py"
    
    try:
        # Run the main script with the command
        result = subprocess.run([sys.executable, str(main_script_path), command], 
                              capture_output=False, text=True)
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running direct mode: {e}")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python learn_entry.py 'user_input'")
        sys.exit(1)
    
    user_input = ' '.join(sys.argv[1:])
    command_type = detect_learn_command(user_input)
    
    if command_type is None:
        print("Not a LEARN command. Exiting.")
        sys.exit(0)
    
    if command_type == "interactive":
        print("Starting interactive LEARN setup...")
        command = run_interactive_mode()
        if command:
            print(f"Generated command: {command}")
            success = run_direct_mode(command)
            if success:
                print("✅ LEARN process completed successfully!")
            else:
                print("❌ LEARN process failed.")
                sys.exit(1)
        else:
            print("Interactive setup cancelled.")
    
    elif command_type == "direct":
        print(f"Processing direct command: {user_input}")
        success = run_direct_mode(user_input)
        if success:
            print("✅ LEARN process completed successfully!")
        else:
            print("❌ LEARN process failed.")
            sys.exit(1)


if __name__ == "__main__":
    main() 