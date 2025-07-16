#!/usr/bin/env python3
"""
Enhanced MinerU Wrapper Module
Supports new output interface with same-name files and _extract_data folders
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path
import tempfile
import shutil
from typing import Optional, Union

# Add MinerU path to sys.path
MINERU_PATH = Path(__file__).parent / "pdf_extractor_MinerU"
sys.path.insert(0, str(MINERU_PATH))

class EnhancedMinerUWrapper:
    """
    Enhanced wrapper class for MinerU functionality.
    Supports new output interface with same-name files and _extract_data folders.
    """
    
    def __init__(self):
        self.mineru_path = MINERU_PATH
        self.temp_dir = None
        
    def extract_and_analyze_pdf(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        layout_mode: str = "arxiv",
        mode: str = "academic", 
        call_api: bool = True,
        call_api_force: bool = False,
        page_range: Optional[str] = None,
        debug: bool = False
    ) -> str:
        """
        Extract and analyze PDF using MinerU with enhanced output interface.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Output directory (if None, uses PDF's directory)
            layout_mode: Layout detection mode (ignored for MinerU)
            mode: Analysis mode (ignored for MinerU)
            call_api: Whether to call image analysis API (ignored for MinerU)
            call_api_force: Whether to force API call (ignored for MinerU)
            page_range: Page range to process (e.g., "1-5", "1,3,5")
            debug: Enable debug mode
            
        Returns:
            Path to the output markdown file
        """
        
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Determine output directory
        if output_dir is None:
            output_dir = pdf_path.parent
        else:
            output_dir = Path(output_dir)
        
        # Create temporary directory for MinerU output
        self.temp_dir = tempfile.mkdtemp(prefix="mineru_output_")
        
        try:
            # Construct MinerU command
            cmd = [
                "python3",
                "-m", "mineru.cli.client",
                "-p", str(pdf_path),
                "-o", self.temp_dir
            ]
            
            # Add page range if specified
            if page_range:
                start_page, end_page = self._parse_page_range(page_range)
                if start_page is not None:
                    cmd.extend(["-s", str(start_page)])
                if end_page is not None:
                    cmd.extend(["-e", str(end_page)])
            
            # Enable formula and table parsing for better recognition
            cmd.extend(["-f", "true"])  # Enable formula parsing
            cmd.extend(["-t", "true"])  # Enable table parsing
            
            if debug:
                print(f"MinerU command: {' '.join(cmd)}", file=sys.stderr)
            
            # Calculate timeout based on page range
            page_count = self._estimate_page_count(page_range)
            timeout = max(600, page_count * 120)  # 2 minutes per page, minimum 10 minutes
            
            print(f"🔄 Starting MinerU processing with {timeout}s timeout...", file=sys.stderr)
            
            # Execute MinerU command with real-time output
            result = self._run_with_progress(cmd, timeout)
            
            # Print debug output if enabled or if there was an error
            if debug or result.returncode != 0:
                print(f"MinerU stdout: {result.stdout}", file=sys.stderr)
                print(f"MinerU stderr: {result.stderr}", file=sys.stderr)
                print(f"MinerU return code: {result.returncode}", file=sys.stderr)
            
            if result.returncode != 0:
                raise RuntimeError(f"MinerU processing failed: {result.stderr}")
            
            # Check for runtime errors even if return code is 0
            if "Exception:" in result.stdout or "Error:" in result.stdout or "Traceback" in result.stdout:
                raise RuntimeError("MinerU: Runtime error detected in output")
            
            # Find the output markdown file
            output_file = self._find_output_file(self.temp_dir)
            if not output_file:
                raise RuntimeError("MinerU: No output file found")
            
            # Process and move to final location with enhanced output interface
            return self._create_enhanced_output(output_file, pdf_path, output_dir)
                
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"MinerU: Process timed out after {timeout}s")
        except KeyboardInterrupt:
            raise RuntimeError("MinerU: Process interrupted by user")
        except Exception as e:
            raise RuntimeError(f"MinerU: Unexpected error: {e}")
        finally:
            # Keep temporary directory for debugging if needed
            if debug and self.temp_dir and os.path.exists(self.temp_dir):
                print(f"🔧 Debug: Keeping temp directory: {self.temp_dir}", file=sys.stderr)
    
    def _create_enhanced_output(self, source_file: str, pdf_path: Path, output_dir: Path) -> str:
        """Create enhanced output with same-name files and _extract_data folder"""
        
        pdf_stem = pdf_path.stem
        
        # Create target markdown file (same name as PDF)
        target_md_file = output_dir / f"{pdf_stem}.md"
        
        # Create extract data directory
        extract_data_dir = output_dir / f"{pdf_stem}_extract_data"
        extract_data_dir.mkdir(exist_ok=True)
        
        # Create images subdirectory
        images_dir = extract_data_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Move all MinerU output files to extract_data directory
        self._move_mineru_files(self.temp_dir, extract_data_dir, images_dir, pdf_stem)
        
        # Process markdown content to add image placeholders
        processed_content = self._process_markdown_with_placeholders(source_file, images_dir)
        
        # Write processed content to target markdown file
        with open(target_md_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"✅ Enhanced output created:", file=sys.stderr)
        print(f"📄 Markdown file: {target_md_file}", file=sys.stderr)
        print(f"📁 Extract data: {extract_data_dir}", file=sys.stderr)
        
        return str(target_md_file)
    
    def _move_mineru_files(self, temp_dir: str, extract_data_dir: Path, images_dir: Path, pdf_stem: str):
        """Move MinerU output files to appropriate locations"""
        
        temp_path = Path(temp_dir)
        
        # Find all files in temp directory
        for root, dirs, files in os.walk(temp_path):
            root_path = Path(root)
            
            for file in files:
                file_path = root_path / file
                
                # Skip markdown files - we'll process them separately
                if file.endswith('.md'):
                    continue
                
                # Move intermediate files to extract_data
                if file.endswith(('_content_list.json', '_layout.pdf', '_middle.json', '_model.json', '_origin.pdf', '_span.pdf')):
                    # Rename to include PDF stem
                    if '_' in file:
                        suffix = file.split('_', 1)[1]
                        target_name = f"{pdf_stem}_{suffix}"
                    else:
                        target_name = file
                    
                    shutil.copy2(file_path, extract_data_dir / target_name)
                    
                # Move images to images subdirectory
                elif file.endswith(('.jpg', '.jpeg', '.png')):
                    shutil.copy2(file_path, images_dir / file)
    
    def _process_markdown_with_placeholders(self, md_file_path: str, images_dir: Path) -> str:
        """Process markdown content to add image placeholders"""
        
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match image references
        # MinerU generates patterns like ![](images/filename.jpg)
        image_pattern = r'!\[\]\(([^)]+)\)'
        
        def replace_image_ref(match):
            image_path = match.group(1)
            
            # Extract filename from path
            filename = os.path.basename(image_path)
            
            # Check if image exists in our images directory
            full_image_path = images_dir / filename
            if not full_image_path.exists():
                # Try to find the image with different extension or name
                for img_file in images_dir.glob("*"):
                    if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        filename = img_file.name
                        break
            
            # Return image reference with placeholder
            return f"![](images/{filename})[DESCRIPTION]"
        
        # Replace all image references
        processed_content = re.sub(image_pattern, replace_image_ref, content)
        
        return processed_content
    
    def _run_with_progress(self, cmd: list, timeout: int):
        """Run MinerU command with real-time progress output."""
        import subprocess
        import threading
        import time
        
        print("📊 MinerU processing started...", file=sys.stderr)
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            cwd=str(self.mineru_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Collect output
        stdout_lines = []
        
        def read_output():
            for line in iter(process.stdout.readline, ''):
                stdout_lines.append(line)
                # Show progress indicators
                if any(keyword in line.lower() for keyword in ['batch', 'processing', 'predict', 'pages']):
                    print(f"📈 Progress: {line.strip()}", file=sys.stderr)
        
        # Start output reading thread
        output_thread = threading.Thread(target=read_output)
        output_thread.daemon = True
        output_thread.start()
        
        # Wait for process completion
        try:
            while process.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⚠️  User interrupted process", file=sys.stderr)
            process.terminate()
            process.wait()
            raise KeyboardInterrupt("User interrupted MinerU process")
        
        # Wait for output thread to finish
        output_thread.join(timeout=5)
        
        # Create result object
        class ProcessResult:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        
        stdout_text = ''.join(stdout_lines)
        
        return ProcessResult(process.returncode, stdout_text, "")
    
    def _find_output_file(self, output_dir: str) -> Optional[str]:
        """Find the markdown output file in MinerU output directory."""
        output_path = Path(output_dir)
        
        # Look for markdown files in root directory
        md_files = list(output_path.glob("*.md"))
        if md_files:
            return str(md_files[0])
        
        # Look in subdirectories recursively
        md_files = list(output_path.rglob("*.md"))
        if md_files:
            return str(md_files[0])
        
        return None
    
    def _parse_page_range(self, page_range: str) -> tuple[Optional[int], Optional[int]]:
        """Parse page range string into start and end page numbers."""
        if not page_range:
            return None, None
        
        try:
            if '-' in page_range:
                parts = page_range.split('-')
                start_page = int(parts[0]) - 1  # Convert to 0-based
                end_page = int(parts[1]) - 1 if len(parts) > 1 else None
                return start_page, end_page
            elif ',' in page_range:
                # For comma-separated pages, just use the first page
                first_page = int(page_range.split(',')[0]) - 1
                return first_page, first_page
            else:
                # Single page
                page = int(page_range) - 1
                return page, page
        except ValueError:
            return None, None
    
    def _estimate_page_count(self, page_range: Optional[str]) -> int:
        """Estimate the number of pages to process."""
        if not page_range:
            return 10  # Default assumption
        
        try:
            if '-' in page_range:
                parts = page_range.split('-')
                start = int(parts[0])
                end = int(parts[1]) if len(parts) > 1 else start
                return max(1, end - start + 1)
            elif ',' in page_range:
                return len(page_range.split(','))
            else:
                return 1
        except ValueError:
            return 10


# Create a global instance
enhanced_mineru_wrapper = EnhancedMinerUWrapper()

def extract_and_analyze_pdf_with_enhanced_mineru(
    pdf_path: str,
    output_dir: Optional[str] = None,
    layout_mode: str = "arxiv",
    mode: str = "academic",
    call_api: bool = True,
    call_api_force: bool = False,
    page_range: Optional[str] = None,
    debug: bool = False
) -> str:
    """
    Main function that uses enhanced MinerU for PDF extraction.
    """
    try:
        wrapper = EnhancedMinerUWrapper()
        return wrapper.extract_and_analyze_pdf(
            pdf_path, output_dir, layout_mode, mode, call_api, call_api_force, page_range, debug
        )
    except Exception as e:
        print(f"⚠️  Enhanced MinerU failed: {e}", file=sys.stderr)
        raise 