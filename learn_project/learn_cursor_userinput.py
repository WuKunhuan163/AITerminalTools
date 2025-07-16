#!/usr/bin/env python3
"""
LEARN Cursor User Input Handler
Processes LEARN commands and converts them to terminal commands, then extracts prompts
"""

import sys
import os
import subprocess
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from learn_project.prompt_manager import PromptManager


def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def show_banner():
    """Display welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        LEARN Cursor Integration                             ║
║                    Command Processing & Prompt Generation                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def detect_learn_command(user_input):
    """Detect if input is a LEARN command."""
    return user_input.strip().upper().startswith("LEARN")


def package_learn_command(user_input):
    """Package LEARN command for terminal execution."""
    user_input = user_input.strip()
    
    # If it's just "LEARN", it will trigger interactive mode
    if user_input.upper() == "LEARN":
        return "LEARN"
    
    # Otherwise, pass through the command as-is
    return user_input


def execute_learn_command(command):
    """Execute LEARN command using the enhanced CLI."""
    print(f"🚀 Executing LEARN command: {command}")
    print("=" * 60)
    
    # Path to enhanced LEARN CLI
    learn_cli_path = Path(__file__).parent / "learn_cli_enhanced.py"
    
    # Build command
    cmd = [sys.executable, str(learn_cli_path), command]
    
    try:
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ LEARN command executed successfully!")
            print(result.stdout)
            
            # Extract the latest prompt path
            latest_prompt_path = None
            for line in result.stdout.split('\n'):
                if line.startswith("LATEST_PROMPT_PATH:"):
                    latest_prompt_path = line.split("LATEST_PROMPT_PATH:")[1].strip()
                    break
            
            return True, latest_prompt_path
        else:
            print("❌ LEARN command failed!")
            print(result.stderr)
            return False, None
            
    except Exception as e:
        print(f"❌ Error executing LEARN command: {e}")
        return False, None


def extract_prompt_content(prompt_path):
    """Extract and return the content of the generated prompt."""
    if not prompt_path or not Path(prompt_path).exists():
        return None
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error reading prompt file: {e}")
        return None


def main():
    """Main entry point for LEARN cursor integration."""
    clear_terminal()
    show_banner()
    
    print("Enter your LEARN command (or 'quit' to exit):")
    print("Examples:")
    print("  LEARN")
    print("  LEARN \"Python basics\" --mode Beginner")
    print("  LEARN \"paper.pdf\" --read-images")
    print()
    
    while True:
        try:
            user_input = input("LEARN> ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Check if it's a LEARN command
            if not detect_learn_command(user_input):
                print("❌ Please enter a LEARN command (or 'quit' to exit)")
                continue
            
            # Package the command
            packaged_command = package_learn_command(user_input)
            
            print(f"\n📦 Packaged command: {packaged_command}")
            
            # Execute the command
            success, prompt_path = execute_learn_command(packaged_command)
            
            if success and prompt_path:
                print(f"\n📄 Latest prompt saved to: {prompt_path}")
                
                # Extract and display the prompt content
                prompt_content = extract_prompt_content(prompt_path)
                if prompt_content:
                    print(f"\n📖 Generated Prompt Content:")
                    print("=" * 60)
                    print(prompt_content)
                    print("=" * 60)
                    
                    # For Cursor integration, output the prompt path
                    print(f"\nLATEST_MARKDOWN_PATH: {prompt_path}")
                    
                    # Ask if user wants to continue
                    continue_choice = input("\nProcess another LEARN command? (y/n): ").strip().lower()
                    if continue_choice != 'y':
                        break
                else:
                    print("❌ Could not read the generated prompt.")
            else:
                print("❌ Failed to process LEARN command.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main() 