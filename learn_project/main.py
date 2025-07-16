#!/usr/bin/env python3
"""
Main entry point for the LEARN system.
This script is designed to be called from the user rule system.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path to import the learn_project package
sys.path.insert(0, str(Path(__file__).parent.parent))

from learn_project.learn_core import LearnSystem


def main():
    """Main entry point for the LEARN system."""
    
    # Get the command from command line arguments
    if len(sys.argv) < 2:
        print("Usage: python main.py 'LEARN command'")
        print("Examples:")
        print("  python main.py 'LEARN Python basics --mode Beginner --style Rigorous'")
        print("  python main.py 'LEARN \"/path/to/paper.pdf\" --read-images --max-pages 5'")
        sys.exit(1)
    
    # Join all arguments to form the complete command
    command = ' '.join(sys.argv[1:])
    
    print(f"Processing command: {command}")
    print("=" * 50)
    
    # Initialize the learning system
    learn_system = LearnSystem()
    
    # Process the command
    result = learn_system.process_learn_command(command)
    
    # Display results
    if result["success"]:
        print(f"\n✅ Learning materials created successfully!")
        print(f"📁 Project path: {result['project_path']}")
        print("\n📝 Created files:")
        for file_path in result["created_files"]:
            print(f"   - {file_path}")
        
        # If it's a paper, show additional info
        if "paper_data" in result:
            paper_data = result["paper_data"]
            print(f"\n📄 Paper info:")
            print(f"   - Total pages: {paper_data['total_pages']}")
            print(f"   - Sections found: {list(paper_data['sections'].keys())}")
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Review the generated tutorial.md")
        print(f"   2. Work through the questions.md")
        print(f"   3. Explore individual chapter tutorials in docs/")
        
    else:
        print(f"\n❌ Error: {result['error']}")
        if "project_path" in result:
            print(f"📁 Partial project created at: {result['project_path']}")
        sys.exit(1)


if __name__ == "__main__":
    main() 