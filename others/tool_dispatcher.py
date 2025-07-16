#!/usr/bin/env python3
"""
Tool Dispatcher for handling different command types
Routes commands to appropriate tools
"""

import sys
import os
import subprocess
import re
from pathlib import Path


def detect_command_type(user_input):
    """
    Detect the type of command from user input.
    
    Returns:
        tuple: (command_type, parsed_command)
    """
    user_input = user_input.strip()
    
    # Check for PDF_EXTRACT command
    if user_input.upper().startswith("PDF_EXTRACT"):
        return "pdf_extract", user_input[11:].strip()
    
    # Check for LEARN command
    if user_input.upper().startswith("LEARN"):
        return "learn", user_input
    
    # Default: unknown command
    return "unknown", user_input


def execute_pdf_extract(args):
    """Execute PDF extraction command."""
    print(f"🔄 Executing PDF extraction...")
    
    # Build command
    pdf_cli_path = Path(__file__).parent.parent / "pdf_extractor" / "pdf_extract_cli.py"
    
    # If no args provided, run in interactive mode
    if not args.strip():
        cmd = [sys.executable, str(pdf_cli_path)]
    else:
        cmd = [sys.executable, str(pdf_cli_path)] + args.split()
    
    try:
        # Run without capturing output for interactive mode
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print(f"✅ PDF extraction completed successfully")
            return True
        else:
            print(f"❌ PDF extraction failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error executing PDF extraction: {e}")
        return False


def execute_learn(command):
    """Execute LEARN command using enhanced CLI."""
    print(f"🔄 Executing LEARN command...")
    
    # Build command - use enhanced CLI
    learn_cli_path = Path(__file__).parent.parent / "learn_project" / "learn_cli_enhanced.py"
    
    # If no command provided, run in interactive mode
    if not command.strip() or command.strip().upper() == "LEARN":
        cmd = [sys.executable, str(learn_cli_path)]
    else:
        cmd = [sys.executable, str(learn_cli_path), command]
    
    try:
        # Run without capturing output for interactive mode
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print(f"✅ LEARN command completed successfully")
            return True
        else:
            print(f"❌ LEARN command failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error executing LEARN command: {e}")
        return False


def execute_combined_workflow(user_input):
    """
    Execute combined workflow for complex commands.
    For example: LEARN with PDF processing
    """
    # Check if it's a LEARN command with PDF
    if user_input.upper().startswith("LEARN") and ".pdf" in user_input:
        print("🔄 Detected LEARN command with PDF - executing combined workflow...")
        
        # Extract PDF path from LEARN command
        pdf_path_match = re.search(r'"([^"]*\.pdf)"', user_input)
        if pdf_path_match:
            pdf_path = pdf_path_match.group(1)
            
            # Step 1: Extract PDF first
            print("📄 Step 1: Extracting PDF content...")
            pdf_args = f'"{pdf_path}" --no-image-api'
            
            if execute_pdf_extract(pdf_args):
                print("📄 PDF extraction completed, proceeding to LEARN...")
                
                # Step 2: Execute LEARN command
                print("📚 Step 2: Creating learning materials...")
                return execute_learn(user_input)
            else:
                print("❌ PDF extraction failed, cannot proceed with LEARN")
                return False
        else:
            # No PDF path found, execute as regular LEARN
            return execute_learn(user_input)
    else:
        # Regular single command
        command_type, parsed_command = detect_command_type(user_input)
        
        if command_type == "pdf_extract":
            return execute_pdf_extract(parsed_command)
        elif command_type == "learn":
            return execute_learn(parsed_command)
        else:
            print(f"❌ Unknown command type: {user_input}")
            return False


def main():
    """Main dispatcher entry point."""
    if len(sys.argv) < 2:
        print("Usage: python tool_dispatcher.py '[COMMAND]'")
        print("Supported commands:")
        print("  PDF_EXTRACT [pdf_path] [options]")
        print("  LEARN [topic] [options]")
        print("  LEARN [pdf_path] [options]  # Combined workflow")
        sys.exit(1)
    
    # Get full command
    user_input = ' '.join(sys.argv[1:])
    
    print(f"🚀 Tool Dispatcher - Processing: {user_input}")
    print("=" * 60)
    
    # Execute the appropriate workflow
    success = execute_combined_workflow(user_input)
    
    print("=" * 60)
    if success:
        print("✅ Command execution completed successfully!")
    else:
        print("❌ Command execution failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 