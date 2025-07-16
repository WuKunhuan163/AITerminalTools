#!/usr/bin/env python3
"""
Enhanced LEARN Command Line Interface with Prompt Generation
Usage: python learn_cli_enhanced.py [LEARN_COMMAND]
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
    """Display a welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                            LEARN System Setup                               ║
║                     Enhanced Interactive Learning                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_interactive_params():
    """Get parameters interactively from user."""
    clear_terminal()
    show_banner()
    
    print("What would you like to learn about?")
    print("1. General topic (e.g., Python, Machine Learning, etc.)")
    print("2. Academic paper (PDF file)")
    print()
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            return get_general_topic_params()
        elif choice == "2":
            return get_paper_params()
        else:
            print("Please enter 1 or 2.")


def get_general_topic_params():
    """Get parameters for general topic learning."""
    print("\n" + "="*50)
    print("GENERAL TOPIC LEARNING")
    print("="*50)
    
    # Get topic
    topic = input("Enter the topic you want to learn: ").strip()
    if not topic:
        topic = "Python basics"
        print(f"Using default topic: {topic}")
    
    # Get mode
    print("\nLearning modes:")
    print("1. Beginner - Focus on core concepts and simplest usage")
    print("2. Advanced - Include more complex or advanced techniques")
    print("3. Practical - Driven by a small, integrated project")
    
    mode_choice = input("Choose learning mode (1-3, default: 1): ").strip()
    mode_map = {"1": "Beginner", "2": "Advanced", "3": "Practical"}
    mode = mode_map.get(mode_choice, "Beginner")
    
    # Get style
    print("\nExplanation styles:")
    print("1. Rigorous - Accurate and professional")
    print("2. Witty - Use analogies, be light-hearted and humorous")
    
    style_choice = input("Choose explanation style (1-2, default: 1): ").strip()
    style_map = {"1": "Rigorous", "2": "Witty"}
    style = style_map.get(style_choice, "Rigorous")
    
    return {
        "topic": topic,
        "mode": mode,
        "style": style,
        "type": "general"
    }


def get_paper_params():
    """Get parameters for paper learning."""
    print("\n" + "="*50)
    print("PAPER LEARNING")
    print("="*50)
    
    # Get paper path with file selector option
    print("Choose PDF input method:")
    print("1. Enter file path manually")
    print("2. Use file selector dialog")
    
    input_choice = input("Choose input method (1-2, default: 1): ").strip()
    
    if input_choice == "2":
        # Use file selector
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            paper_path = filedialog.askopenfilename(
                title="Choose the PDF",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
            )
            
            root.destroy()
            
            if not paper_path:
                print("No file selected. Exiting.")
                return None
                
        except ImportError:
            print("tkinter not available. Please enter path manually.")
            paper_path = input("Enter the path to your PDF paper: ").strip()
    else:
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
    print("\nImage analysis:")
    print("Should the system analyze images in the paper?")
    read_images = input("Analyze images? (y/n, default: n): ").strip().lower() == 'y'
    
    # Get max pages per chunk
    print("\nPage processing:")
    max_pages_input = input("Max pages to process at once (default: 5): ").strip()
    try:
        max_pages = int(max_pages_input) if max_pages_input else 5
    except ValueError:
        max_pages = 5
        print("Invalid input, using default: 5")
    
    # Get chapters
    print("\nChapters to focus on:")
    print("Available chapters: background, methodology, evaluation, future_work")
    chapters_input = input("Enter chapters (comma-separated, default: all): ").strip()
    
    if chapters_input:
        chapters = [ch.strip() for ch in chapters_input.split(',')]
    else:
        chapters = ["background", "methodology", "evaluation", "future_work"]
    
    # Get learning mode and style
    print("\nLearning preferences:")
    print("Modes: 1=Beginner, 2=Advanced, 3=Practical")
    mode_choice = input("Choose mode (1-3, default: 1): ").strip()
    mode_map = {"1": "Beginner", "2": "Advanced", "3": "Practical"}
    mode = mode_map.get(mode_choice, "Beginner")
    
    print("Styles: 1=Rigorous, 2=Witty")
    style_choice = input("Choose style (1-2, default: 1): ").strip()
    style_map = {"1": "Rigorous", "2": "Witty"}
    style = style_map.get(style_choice, "Rigorous")
    
    return {
        "paper_path": paper_path,
        "read_images": read_images,
        "max_pages": max_pages,
        "chapters": chapters,
        "mode": mode,
        "style": style,
        "type": "paper"
    }


def parse_learn_command(command: str) -> dict:
    """Parse LEARN command and extract parameters."""
    # Remove LEARN prefix
    command = command.strip()
    if command.upper().startswith("LEARN"):
        command = command[5:].strip()
    
    # Initialize result
    result = {
        "topic": "",
        "mode": "Beginner",
        "style": "Rigorous",
        "type": "general",
        "paper_path": None,
        "read_images": False,
        "max_pages": 5,
        "chapters": ["background", "methodology", "evaluation", "future_work"]
    }
    
    # Check if it's a paper learning command
    if command.startswith('"') and command.count('"') >= 2:
        # Extract quoted topic/path
        topic_match = re.search(r'"([^"]+)"', command)
        if topic_match:
            topic = topic_match.group(1)
            result["topic"] = topic
            
            # Check if it's a PDF path
            if topic.endswith('.pdf') or os.path.exists(topic):
                result["type"] = "paper"
                result["paper_path"] = topic
    else:
        # Simple topic extraction
        parts = command.split()
        if parts:
            result["topic"] = parts[0]
    
    # Parse flags
    if "--mode" in command:
        mode_match = re.search(r'--mode\s+([^\s]+)', command)
        if mode_match:
            result["mode"] = mode_match.group(1)
    
    if "--style" in command:
        style_match = re.search(r'--style\s+([^\s]+)', command)
        if style_match:
            result["style"] = style_match.group(1)
    
    if "--read-images" in command:
        result["read_images"] = True
    
    if "--max-pages" in command:
        pages_match = re.search(r'--max-pages\s+(\d+)', command)
        if pages_match:
            result["max_pages"] = int(pages_match.group(1))
    
    if "--chapters" in command:
        chapters_match = re.search(r'--chapters\s+"([^"]+)"', command)
        if chapters_match:
            result["chapters"] = [ch.strip() for ch in chapters_match.group(1).split(',')]
    
    return result


def process_pdf_and_generate_prompt(params):
    """Process PDF and generate learning prompt."""
    paper_path = params["paper_path"]
    read_images = params["read_images"]
    max_pages = params["max_pages"]
    mode = params["mode"]
    style = params["style"]
    chapters = params["chapters"]
    
    print(f"📄 Processing PDF: {paper_path}")
    
    # Call PDF extractor
    pdf_cli_path = Path(__file__).parent.parent / "pdf_extractor" / "pdf_extract_cli.py"
    
    # Build PDF extraction command
    cmd = [sys.executable, str(pdf_cli_path), paper_path]
    
    if not read_images:
        cmd.append("--no-image-api")
    
    # Process in chunks based on max_pages
    try:
        import fitz
        doc = fitz.open(paper_path)
        total_pages = len(doc)
        doc.close()
        
        # Calculate chunks
        pdf_markdown_paths = []
        for start_page in range(1, total_pages + 1, max_pages):
            end_page = min(start_page + max_pages - 1, total_pages)
            page_range = f"{start_page}-{end_page}"
            
            print(f"📄 Processing pages {page_range}...")
            
            # Run PDF extraction for this chunk
            chunk_cmd = cmd + ["--page", page_range]
            result = subprocess.run(chunk_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract output path from result
                for line in result.stdout.split('\n'):
                    if "SUCCESS: PDF extracted to" in line:
                        output_path = line.split("SUCCESS: PDF extracted to")[1].strip()
                        pdf_markdown_paths.append(output_path)
                        break
            else:
                print(f"❌ Error processing pages {page_range}: {result.stderr}")
        
    except ImportError:
        print("⚠️ PyMuPDF not available, processing entire PDF...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Extract output path from result
            for line in result.stdout.split('\n'):
                if "SUCCESS: PDF extracted to" in line:
                    output_path = line.split("SUCCESS: PDF extracted to")[1].strip()
                    pdf_markdown_paths.append(output_path)
                    break
        else:
            print(f"❌ Error processing PDF: {result.stderr}")
            return None
    
    # Generate prompt using PromptManager
    print(f"📝 Generating learning prompt...")
    
    prompt_manager = PromptManager()
    prompt_path = prompt_manager.create_paper_prompt(
        paper_path, mode, style, read_images, max_pages, chapters, pdf_markdown_paths
    )
    
    return prompt_path


def generate_general_prompt(params):
    """Generate prompt for general topic learning."""
    topic = params["topic"]
    mode = params["mode"]
    style = params["style"]
    
    print(f"📝 Generating learning prompt for: {topic}")
    
    prompt_manager = PromptManager()
    prompt_path = prompt_manager.create_general_prompt(topic, mode, style)
    
    return prompt_path


def main():
    """Main entry point."""
    
    # Check if command is provided
    if len(sys.argv) < 2:
        print("🔍 No command provided. Starting interactive mode...")
        params = get_interactive_params()
        if params is None:
            print("Setup cancelled.")
            return
    else:
        # Parse command line arguments
        command = ' '.join(sys.argv[1:])
        
        # Check for just "LEARN" to trigger interactive mode
        if command.strip().upper() == "LEARN":
            params = get_interactive_params()
            if params is None:
                print("Setup cancelled.")
                return
        else:
            # Parse the command
            params = parse_learn_command(command)
    
    # Process based on type
    if params["type"] == "paper":
        prompt_path = process_pdf_and_generate_prompt(params)
    else:
        prompt_path = generate_general_prompt(params)
    
    if prompt_path:
        print(f"\n✅ Learning prompt generated successfully!")
        print(f"📁 Prompt saved to: {prompt_path}")
        
        # Print the prompt path for external scripts to read
        print(f"LATEST_PROMPT_PATH: {prompt_path}")
        
        # Also print the content for immediate use
        print(f"\n📖 Generated prompt content:")
        print("=" * 60)
        with open(prompt_path, 'r', encoding='utf-8') as f:
            print(f.read())
        print("=" * 60)
        
    else:
        print("❌ Failed to generate learning prompt.")
        sys.exit(1)


if __name__ == "__main__":
    main() 