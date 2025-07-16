"""
Paper processor for handling PDF paper learning with chapter-based segmentation
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path to import pdf_extractor
sys.path.append(str(Path(__file__).parent.parent))

try:
    from pdf_extractor.pdf_extractor import extract_and_analyze_pdf
    PDF_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: PDF extractor not available: {e}")
    PDF_EXTRACTOR_AVAILABLE = False

from .utils import chunk_pages, identify_paper_sections, sanitize_filename


class PaperProcessor:
    """
    Handles processing of academic papers for learning purposes.
    """
    
    def __init__(self, base_path: str = "learn_project"):
        self.base_path = Path(base_path)
        self.pdf_extractor_path = Path(__file__).parent.parent / "pdf_extractor"
        
    def process_paper(self, paper_path: str, read_images: bool = False, 
                     max_pages_per_chunk: int = 5, chapters: List[str] = None) -> Dict:
        """
        Process a paper PDF and extract content in chunks.
        
        Args:
            paper_path: Path to the PDF file
            read_images: Whether to analyze images in the paper
            max_pages_per_chunk: Maximum pages to process at once
            chapters: List of chapter types to focus on
            
        Returns:
            Dictionary containing processed content by chapters
        """
        if chapters is None:
            chapters = ["background", "methodology", "evaluation", "future_work"]
        
        paper_path = Path(paper_path)
        if not paper_path.exists():
            raise FileNotFoundError(f"Paper not found: {paper_path}")
        
        # Check if PDF extractor is available
        if not PDF_EXTRACTOR_AVAILABLE:
            raise ImportError("PDF extractor is not available. Please ensure pdf_extractor module is properly installed.")
        
        # Get total pages by opening the PDF
        try:
            import fitz
            doc = fitz.open(paper_path)
            total_pages = len(doc)
            doc.close()
        except ImportError:
            # Fallback: assume reasonable number of pages
            total_pages = 20
        
        # Process paper in chunks
        all_markdown_content = ""
        chunks = chunk_pages(total_pages, max_pages_per_chunk)
        
        for i, (start_page, end_page) in enumerate(chunks):
            print(f"Processing pages {start_page}-{end_page} ({i+1}/{len(chunks)})...")
            
            # Call pdf_extractor with appropriate flags
            page_range = f"{start_page}-{end_page}"
            
            try:
                # Import and call the function directly
                output_path = extract_and_analyze_pdf(
                    str(paper_path),
                    layout_mode="arxiv",
                    mode="academic",
                    call_api=read_images,
                    call_api_force=False,
                    page_range=page_range,
                    debug=False
                )
                
                # Read the generated markdown
                with open(output_path, 'r', encoding='utf-8') as f:
                    chunk_content = f.read()
                
                all_markdown_content += chunk_content + "\n\n"
                
            except Exception as e:
                print(f"Error processing pages {start_page}-{end_page}: {e}")
                continue
        
        # Identify sections by chapter
        sections = identify_paper_sections(all_markdown_content)
        
        # Filter to requested chapters
        filtered_sections = {
            chapter: sections.get(chapter, []) 
            for chapter in chapters
        }
        
        # Add other content if it exists
        if sections.get("other"):
            filtered_sections["other"] = sections["other"]
        
        return {
            "paper_path": str(paper_path),
            "total_pages": total_pages,
            "sections": filtered_sections,
            "full_content": all_markdown_content
        }
    
    def create_chapter_tutorials(self, paper_data: Dict, topic: str, 
                               mode: str = "Beginner", style: str = "Rigorous") -> Dict[str, str]:
        """
        Create tutorials for each chapter of the paper.
        
        Args:
            paper_data: Processed paper data from process_paper
            topic: Learning topic
            mode: Tutorial mode (Beginner/Advanced/Practical)
            style: Explanation style (Rigorous/Witty)
            
        Returns:
            Dictionary mapping chapter names to tutorial content
        """
        tutorials = {}
        
        for chapter, content_chunks in paper_data["sections"].items():
            if not content_chunks:
                continue
                
            # Combine all content for this chapter
            chapter_content = "\n\n".join(content_chunks)
            
            # Generate tutorial for this chapter
            tutorial_content = self._generate_chapter_tutorial(
                chapter, chapter_content, topic, mode, style
            )
            
            tutorials[chapter] = tutorial_content
        
        return tutorials
    
    def _generate_chapter_tutorial(self, chapter: str, content: str, 
                                 topic: str, mode: str, style: str) -> str:
        """
        Generate a tutorial for a specific chapter.
        
        Args:
            chapter: Chapter name
            content: Chapter content
            topic: Learning topic
            mode: Tutorial mode
            style: Explanation style
            
        Returns:
            Generated tutorial content
        """
        # Create a focused tutorial prompt for this chapter
        tutorial_template = f"""
# {chapter.title()} Tutorial: {topic}

## Overview
This tutorial focuses on the **{chapter}** aspects of {topic}.

## Content Analysis
Based on the paper content, here are the key points for {chapter}:

{self._extract_key_points(content)}

## Detailed Explanation
{self._create_detailed_explanation(chapter, content, mode, style)}

## Key Takeaways
{self._extract_takeaways(content)}

## Further Reading
- Review the original paper sections related to {chapter}
- Look for related work in this area
- Consider practical applications

---
*Generated from paper analysis*
"""
        
        return tutorial_template
    
    def _extract_key_points(self, content: str) -> str:
        """Extract key points from content."""
        # Simple extraction - look for headers and important sentences
        lines = content.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or line.startswith('**') or 'important' in line.lower():
                key_points.append(f"- {line}")
        
        return '\n'.join(key_points[:10])  # Limit to top 10 points
    
    def _create_detailed_explanation(self, chapter: str, content: str, 
                                   mode: str, style: str) -> str:
        """Create detailed explanation based on mode and style."""
        explanation = f"This section covers {chapter} in {mode.lower()} mode with {style.lower()} style.\n\n"
        
        # Add content summary
        explanation += "## Summary\n"
        explanation += content[:1000] + "...\n\n"  # First 1000 chars
        
        # Add mode-specific content
        if mode == "Beginner":
            explanation += "## For Beginners\n"
            explanation += "This section introduces fundamental concepts that are essential for understanding the topic.\n\n"
        elif mode == "Advanced":
            explanation += "## Advanced Analysis\n"
            explanation += "This section delves into complex aspects and technical details.\n\n"
        elif mode == "Practical":
            explanation += "## Practical Applications\n"
            explanation += "This section focuses on how these concepts can be applied in practice.\n\n"
        
        return explanation
    
    def _extract_takeaways(self, content: str) -> str:
        """Extract key takeaways from content."""
        # Simple takeaway extraction
        takeaways = [
            "Understanding the core concepts presented",
            "Recognizing the methodology used",
            "Identifying potential applications",
            "Noting limitations and future work"
        ]
        
        return '\n'.join(f"- {takeaway}" for takeaway in takeaways)
    
    def save_chapter_tutorials(self, tutorials: Dict[str, str], 
                             project_path: Path, paper_name: str) -> List[Path]:
        """
        Save chapter tutorials to files.
        
        Args:
            tutorials: Dictionary of chapter tutorials
            project_path: Project directory path
            paper_name: Name of the paper
            
        Returns:
            List of created file paths
        """
        created_files = []
        
        for chapter, tutorial_content in tutorials.items():
            # Create filename
            safe_paper_name = sanitize_filename(paper_name)
            filename = f"{safe_paper_name}_{chapter}_tutorial.md"
            file_path = project_path / "docs" / filename
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write tutorial
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(tutorial_content)
            
            created_files.append(file_path)
            print(f"Created tutorial: {file_path}")
        
        return created_files 