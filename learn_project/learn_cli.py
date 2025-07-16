#!/usr/bin/env python3
"""
LEARN Command Line Interface
Usage: python learn_cli.py [LEARN_COMMAND]
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from learn_project.learn_core import LearnSystem
    from learn_project.interactive_input import get_interactive_params
    FULL_SYSTEM_AVAILABLE = True
except ImportError:
    from learn_project.standalone_learn import main as standalone_main
    FULL_SYSTEM_AVAILABLE = False


def main():
    """Main CLI entry point for LEARN command."""
    if len(sys.argv) < 2:
        # No arguments provided - enter interactive mode
        command = "LEARN"
    else:
        # Reconstruct the command
        command = ' '.join(sys.argv[1:])
    
    # Check if it's just "LEARN" for interactive mode
    if command.strip().upper() == "LEARN":
        if FULL_SYSTEM_AVAILABLE:
            # Use full system interactive mode
            params = get_interactive_params()
            if params is None:
                print("Setup cancelled.")
                return 1
            
            # Create learning system and process
            output_dir = params.get("output_dir", os.getcwd())
            learn_system = LearnSystem(base_path=output_dir)
            
            # Convert params to command format
            if params.get("type") == "paper":
                cmd = f'LEARN "{params["paper_path"]}"'
                if params.get("read_images"):
                    cmd += " --read-images"
                if params.get("max_pages", 5) != 5:
                    cmd += f" --max-pages {params['max_pages']}"
                cmd += f" --mode {params['mode']} --style {params['style']}"
                # Add descriptions as a parameter
                if params.get("descriptions"):
                    cmd += f' --descriptions "{params["descriptions"]}"'
            else:
                cmd = f'LEARN "{params["topic"]}" --mode {params["mode"]} --style {params["style"]}'
            
            result = learn_system.process_learn_command(cmd)
            
            if result["success"]:
                print(f"\n✅ Learning project created successfully!")
                print(f"📁 Project path: {result['project_path']}")
                print("\n📝 Created files:")
                for file_path in result["created_files"]:
                    print(f"   - {file_path}")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                return 1
        else:
            # Fall back to standalone system
            sys.argv = ['learn_cli.py', command]
            try:
                standalone_main()
                return 0
            except SystemExit as e:
                return e.code
            except Exception as e:
                print(f"ERROR: {str(e)}")
                return 1
    else:
        # Direct command processing
        if FULL_SYSTEM_AVAILABLE:
            try:
                learn_system = LearnSystem()
                result = learn_system.process_learn_command(command)
                
                if result["success"]:
                    print(f"\n✅ Learning project created successfully!")
                    print(f"📁 Project path: {result['project_path']}")
                    print("\n📝 Created files:")
                    for file_path in result["created_files"]:
                        print(f"   - {file_path}")
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
                    return 1
            except Exception as e:
                print(f"ERROR: {str(e)}")
                return 1
        else:
            # Fall back to standalone system
            sys.argv = ['learn_cli.py', command]
            try:
                standalone_main()
                return 0
            except SystemExit as e:
                return e.code
            except Exception as e:
                print(f"ERROR: {str(e)}")
                return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 