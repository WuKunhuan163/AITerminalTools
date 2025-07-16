"""
Utility functions for the LEARN project system
"""

import re
import os
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def parse_learn_command(command: str) -> Dict:
    """
    Parse LEARN command and extract topic, flags, and options.
    
    Args:
        command: The full LEARN command string
        
    Returns:
        Dictionary containing parsed components
    """
    # Remove LEARN prefix
    command = command.strip()
    if command.upper().startswith("LEARN"):
        command = command[5:].strip()
    
    # Initialize result
    result = {
        "topic": "",
        "mode": "Beginner",
        "style": "Rigorous",
        "is_paper": False,
        "paper_path": None,
        "read_images": False,
        "max_pages_per_chunk": 5,
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
                result["is_paper"] = True
                result["paper_path"] = topic
                result["topic"] = f"Paper: {Path(topic).stem}"
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
            result["max_pages_per_chunk"] = int(pages_match.group(1))
    
    if "--chapters" in command:
        chapters_match = re.search(r'--chapters\s+"([^"]+)"', command)
        if chapters_match:
            result["chapters"] = [ch.strip() for ch in chapters_match.group(1).split(',')]
    
    return result


def create_project_structure(base_path: str, topic: str) -> Path:
    """
    Create the basic project directory structure.
    
    Args:
        base_path: Base directory path
        topic: Learning topic
        
    Returns:
        Path to the created project directory
    """
    # Sanitize topic name for directory
    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip()
    safe_topic = re.sub(r'[-\s]+', '_', safe_topic).lower()
    
    project_name = f"learn_{safe_topic}"
    project_path = Path(base_path) / project_name
    
    # Create directories
    project_path.mkdir(exist_ok=True)
    (project_path / "src").mkdir(exist_ok=True)
    (project_path / "docs").mkdir(exist_ok=True)
    
    return project_path


def chunk_pages(total_pages: int, max_pages_per_chunk: int) -> List[Tuple[int, int]]:
    """
    Split pages into chunks for processing.
    
    Args:
        total_pages: Total number of pages
        max_pages_per_chunk: Maximum pages per chunk
        
    Returns:
        List of (start_page, end_page) tuples
    """
    chunks = []
    for start in range(1, total_pages + 1, max_pages_per_chunk):
        end = min(start + max_pages_per_chunk - 1, total_pages)
        chunks.append((start, end))
    return chunks


def identify_paper_sections(markdown_content: str) -> Dict[str, List[str]]:
    """
    Identify and categorize sections in a paper markdown.
    
    Args:
        markdown_content: The markdown content of the paper
        
    Returns:
        Dictionary mapping section types to content chunks
    """
    sections = {
        "background": [],
        "methodology": [],
        "evaluation": [],
        "future_work": [],
        "other": []
    }
    
    # Keywords for each section type
    keywords = {
        "background": ["introduction", "background", "related work", "literature review", "motivation"],
        "methodology": ["method", "approach", "algorithm", "implementation", "design", "architecture"],
        "evaluation": ["experiment", "evaluation", "result", "analysis", "performance", "comparison"],
        "future_work": ["future", "conclusion", "discussion", "limitation", "future work"]
    }
    
    # Split content by pages or sections
    pages = markdown_content.split("## 📄 Page")
    
    for page in pages:
        if not page.strip():
            continue
            
        page_lower = page.lower()
        classified = False
        
        # Try to classify based on keywords
        for section_type, section_keywords in keywords.items():
            if any(keyword in page_lower for keyword in section_keywords):
                sections[section_type].append(page)
                classified = True
                break
        
        if not classified:
            sections["other"].append(page)
    
    return sections


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe for filesystem.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = re.sub(r'\s+', '_', safe_name)
    return safe_name[:100]  # Limit length 