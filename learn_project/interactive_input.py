#!/usr/bin/env python3
"""
Interactive input script for LEARN system
Collects parameters from user via terminal input
"""

import os
import sys
from pathlib import Path


def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')



def interactive_select(prompt, options, default_index=0):
    """Interactive selection with numbered options."""
    print(f"{prompt}")
    for i, option in enumerate(options):
        print(f"  {i+1}. {option}")
    
    while True:
        try:
            choice = input(f"Choose (1-{len(options)}, default: {default_index+1}): ").strip()
            if not choice:
                print(f"{prompt} {options[default_index]}")
                return default_index
            
            choice_num = int(choice) - 1
            if 0 <= choice_num < len(options):
                print(f"{prompt} {options[choice_num]}")
                return choice_num
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            print(f"Please enter a valid number between 1 and {len(options)}")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def get_output_directory():
    """Get output directory for the learning project using tkinter."""
    print("\nChoose the Project Path")
    print("Opening directory selector...")
    
    while True:
        try:
            import os
            os.environ['TK_SILENCE_DEPRECATION'] = '1'
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            parent_dir = filedialog.askdirectory(
                title="Choose parent directory for LEARN project"
            )
            
            root.destroy()
            
            if not parent_dir:
                return None  # User cancelled
            
            # Create LEARN folder in the selected directory
            learn_dir = os.path.join(parent_dir, "LEARN")
            
            if os.path.exists(learn_dir):
                print(f"LEARN folder already exists in {parent_dir}")
                print("Please choose a different location.")
                continue
            else:
                os.makedirs(learn_dir)
                print(f"Created LEARN directory: {learn_dir}")
                return learn_dir
                
        except ImportError:
            # Fallback to current directory
            current_dir = os.getcwd()
            learn_dir = os.path.join(current_dir, "LEARN")
            if os.path.exists(learn_dir):
                print(f"LEARN folder already exists in {current_dir}")
                return None
            else:
                os.makedirs(learn_dir)
                return learn_dir


def show_banner():
    """Display a welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                            LEARN System Setup                               ║
║                     Interactive Parameter Collection                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_topic_type():
    """Get the type of learning topic from user."""
    print("What would you like to learn about?")
    print("1. General topic (e.g., Python, Machine Learning, etc.)")
    print("2. Academic paper (PDF file)")
    print()
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            return "general"
        elif choice == "2":
            return "paper"
        else:
            print("Please enter 1 or 2.")


def get_general_topic_params():
    """Get parameters for general topic learning."""
    # Get topic
    topic = input("\nEnter the topic you want to learn: ").strip()
    if not topic:
        topic = "Python basics"
        print(f"Using default topic: {topic}")
    
    # Get mode
    mode_options = ["Beginner", "Advanced", "Practical"]
    mode_choice = interactive_select("Learning mode:", mode_options)
    if mode_choice is None:
        return None
    mode = mode_options[mode_choice]
    
    # Get style
    print()
    style_options = ["Rigorous", "Witty"]
    style_choice = interactive_select("Explanation style:", style_options)
    if style_choice is None:
        return None
    style = style_options[style_choice]
    
    # Get output directory
    output_dir = get_output_directory()
    if output_dir is None:
        return None
    
    return {
        "topic": topic,
        "mode": mode,
        "style": style,
        "type": "general",
        "output_dir": output_dir
    }


def get_paper_params():
    """Get parameters for paper learning."""
    # Get paper path
    paper_path = input("\nEnter the path to your PDF paper: ").strip()
    if not paper_path:
        # Use file selector
        print("Opening file selector...")
        try:
            import os
            os.environ['TK_SILENCE_DEPRECATION'] = '1'
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            paper_path = filedialog.askopenfilename(
                title="Choose the PDF paper",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            root.destroy()
            
            if not paper_path:
                print("No file selected. Cancelled.")
                return None
            else:
                print(f"Selected file: {paper_path}")
                
        except ImportError:
            paper_path = input("Enter the path to your PDF paper: ").strip()
            if not paper_path:
                print("Error: Paper path is required!")
                return None
    
    # Validate path
    if not Path(paper_path).exists():
        print(f"Warning: File not found at {paper_path}")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return None
    
    # Get image analysis option
    print()
    image_options = ["No", "Yes"]
    image_choice = interactive_select("Analyze images:", image_options)
    if image_choice is None:
        return None
    read_images = image_choice == 1
    
    # Set max pages per chunk to default (no user input needed)
    max_pages = 5
    
    # Get descriptions with editable default
    try:
        import readline
        def input_with_default(prompt, default):
            def pre_input_hook():
                readline.insert_text(default)
                readline.redisplay()
            readline.set_pre_input_hook(pre_input_hook)
            try:
                return input(prompt)
            finally:
                readline.set_pre_input_hook()
        
        descriptions = input_with_default("\nDescriptions: ", "Focus on all chapters").strip()
    except ImportError:
        # Fallback if readline is not available
        print("\nDescriptions: Focus on all chapters")
        descriptions = input("Enter description (or press Enter to keep default): ").strip()
    
    if not descriptions:
        descriptions = "Focus on all chapters"
    
    # Get learning mode and style
    print()
    mode_options = ["Beginner", "Advanced", "Practical"]
    mode_choice = interactive_select("Learning mode:", mode_options)
    if mode_choice is None:
        return None
    mode = mode_options[mode_choice]
    
    print()
    style_options = ["Rigorous", "Witty"]
    style_choice = interactive_select("Explanation style:", style_options)
    if style_choice is None:
        return None
    style = style_options[style_choice]
    
    # Get output directory
    output_dir = get_output_directory()
    if output_dir is None:
        return None
    
    return {
        "paper_path": paper_path,
        "read_images": read_images,
        "max_pages": max_pages,
        "descriptions": descriptions,
        "mode": mode,
        "style": style,
        "type": "paper",
        "output_dir": output_dir
    }


def build_command(params):
    """Build the LEARN command from parameters."""
    if params["type"] == "general":
        return f'LEARN "{params["topic"]}" --mode {params["mode"]} --style {params["style"]}'
    
    elif params["type"] == "paper":
        cmd = f'LEARN "{params["paper_path"]}"'
        cmd += f' --mode {params["mode"]} --style {params["style"]}'
        
        if params["read_images"]:
            cmd += ' --read-images'
        
        if params["max_pages"] != 5:
            cmd += f' --max-pages {params["max_pages"]}'
        
        if params["chapters"] != ["background", "methodology", "evaluation", "future_work"]:
            chapters_str = ",".join(params["chapters"])
            cmd += f' --chapters "{chapters_str}"'
        
        return cmd
    
    return None


def get_interactive_params():
    """Get parameters interactively from user - full system version."""
    clear_terminal()
    
    print("What would you like to learn about?")
    
    choice = interactive_select("Learning type:", ["General topic", "Academic paper"])
    if choice is None:
        return None
    elif choice == 0:
        return get_general_topic_params()
    else:
        return get_paper_params()


def main():
    """Main interactive input collection."""
    # Clear terminal and show banner
    clear_terminal()
    show_banner()
    
    # Get topic type
    topic_type = get_topic_type()
    
    # Get parameters based on type
    if topic_type == "general":
        params = get_general_topic_params()
    else:
        params = get_paper_params()
    
    if params is None:
        print("Setup cancelled.")
        return
    
    # Build and display command
    command = build_command(params)
    
    print("\n" + "="*50)
    print("COMMAND GENERATED")
    print("="*50)
    print(f"Command: {command}")
    print()
    
    # Confirm execution
    confirm = input("Execute this command? (y/n): ").strip().lower()
    if confirm == 'y':
        print(f"\nExecuting: {command}")
        print("="*50)
        
        # Write the command to a file for the entry script to read
        with open("learn_command.txt", "w") as f:
            f.write(command)
        
        print("✅ Command saved. The system will now execute it.")
    else:
        print("Command cancelled.")
        # Write empty file to indicate cancellation
        with open("learn_command.txt", "w") as f:
            f.write("")


if __name__ == "__main__":
    main() 