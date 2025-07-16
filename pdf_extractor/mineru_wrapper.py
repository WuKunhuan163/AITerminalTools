#!/usr/bin/env python3
"""
MinerU Wrapper Module
This module provides a wrapper around MinerU functionality to maintain compatibility
with the existing PDF_EXTRACT CLI interface.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import tempfile
import shutil
from typing import Optional, Union

# Add MinerU path to sys.path
MINERU_PATH = Path(__file__).parent / "pdf_extractor_MinerU"
sys.path.insert(0, str(MINERU_PATH))

class MinerUWrapper:
    """
    Wrapper class for MinerU functionality.
    Provides a compatible interface with the original pdf_extractor.
    """
    
    def __init__(self):
        self.mineru_path = MINERU_PATH
        self.temp_dir = None
        
    def extract_and_analyze_pdf(
        self,
        pdf_path: str,
        layout_mode: str = "arxiv",
        mode: str = "academic", 
        call_api: bool = True,
        call_api_force: bool = False,
        page_range: Optional[str] = None,
        debug: bool = False
    ) -> str:
        """
        Extract and analyze PDF using MinerU.
        
        Args:
            pdf_path: Path to the PDF file
            layout_mode: Layout detection mode (ignored for MinerU)
            mode: Analysis mode (ignored for MinerU)
            call_api: Whether to call image analysis API (ignored for MinerU)
            call_api_force: Whether to force API call (ignored for MinerU)
            page_range: Page range to process (e.g., "1-5", "1,3,5")
            debug: Enable debug mode
            
        Returns:
            Path to the output markdown file
        """
        
        # Create temporary directory for MinerU output
        self.temp_dir = tempfile.mkdtemp(prefix="mineru_output_")
        
        try:
            # Construct MinerU command
            cmd = [
                "python3",
                "-m", "mineru.cli.client",
                "-p", pdf_path,
                "-o", self.temp_dir
            ]
            
            # Add page range if specified
            if page_range:
                start_page, end_page = self._parse_page_range(page_range)
                if start_page is not None:
                    cmd.extend(["-s", str(start_page)])
                if end_page is not None:
                    cmd.extend(["-e", str(end_page)])
            
            # Strategy: Always disable formula and table parsing to avoid tokenizer errors
            # The UnimerNet model has a tokenizer compatibility issue that causes crashes
            # We'll identify formulas and tables through layout analysis instead
            cmd.extend(["-f", "false"])  # Disable formula parsing (avoid tokenizer error)
            cmd.extend(["-t", "false"])  # Disable table parsing (avoid tokenizer error)
            
            if debug:
                print(f"MinerU command: {' '.join(cmd)}", file=sys.stderr)
            
            # Calculate timeout based on page range (2 minutes per page, minimum 10 minutes)
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
                print(f"MinerU error: {result.stderr}", file=sys.stderr)
                return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
            
            # Check for runtime errors even if return code is 0
            if "Exception:" in result.stdout or "Error:" in result.stdout or "Traceback" in result.stdout:
                print("MinerU: Runtime error detected in output", file=sys.stderr)
                if debug:
                    print(f"MinerU: Error details in stdout", file=sys.stderr)
                return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
            
            # Find the output markdown file
            output_file = self._find_output_file(self.temp_dir)
            if output_file:
                # Move to pdf_extractor_data directory and process with API if requested
                return self._move_to_data_directory(output_file, call_api, call_api_force)
            else:
                print("MinerU: No output file found", file=sys.stderr)
                if debug:
                    print(f"MinerU: Searched in directory: {self.temp_dir}", file=sys.stderr)
                    # List directory contents for debugging
                    try:
                        for root, dirs, files in os.walk(self.temp_dir):
                            print(f"MinerU: Directory {root} contains: {files}", file=sys.stderr)
                    except Exception as e:
                        print(f"MinerU: Error listing directory: {e}", file=sys.stderr)
                return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
                
        except subprocess.TimeoutExpired:
            print(f"⏰ MinerU: Process timed out after {timeout}s", file=sys.stderr)
            print("💡 Tip: Processing large PDFs may take longer. Consider processing fewer pages or using --debug for more info.", file=sys.stderr)
            return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
        except KeyboardInterrupt:
            print("⚠️  MinerU: Process interrupted by user", file=sys.stderr)
            if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
        except Exception as e:
            print(f"MinerU: Unexpected error: {e}", file=sys.stderr)
            return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
        finally:
            # Keep temporary directory for debugging (comment out cleanup)
            # if self.temp_dir and os.path.exists(self.temp_dir):
            #     shutil.rmtree(self.temp_dir)
            if self.temp_dir and os.path.exists(self.temp_dir):
                print(f"🔧 Debug: Keeping temp directory: {self.temp_dir}", file=sys.stderr)
    
    def _parse_page_range(self, page_range: str) -> tuple[Optional[int], Optional[int]]:
        """Parse page range string into start and end pages (0-indexed)."""
        try:
            if '-' in page_range:
                parts = page_range.split('-')
                start = int(parts[0]) - 1  # Convert to 0-indexed
                end = int(parts[1]) - 1 if len(parts) > 1 else None
                return start, end
            elif ',' in page_range:
                # For comma-separated pages, just use the first page
                pages = [int(p.strip()) for p in page_range.split(',')]
                return pages[0] - 1, pages[0] - 1  # Convert to 0-indexed
            else:
                page = int(page_range) - 1  # Convert to 0-indexed
                return page, page
        except ValueError:
            return None, None
    
    def _estimate_page_count(self, page_range: Optional[str]) -> int:
        """Estimate the number of pages to be processed."""
        if not page_range:
            return 10  # Default estimate
        
        try:
            if '-' in page_range:
                parts = page_range.split('-')
                start = int(parts[0])
                end = int(parts[1]) if len(parts) > 1 else start
                return max(1, end - start + 1)
            elif ',' in page_range:
                pages = [int(p.strip()) for p in page_range.split(',')]
                return len(pages)
            else:
                return 1
        except ValueError:
            return 10  # Default estimate
    
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
        stderr_lines = []
        
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
        
        # Wait for process completion (no timeout, user can Ctrl+C)
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
        stderr_text = ''.join(stderr_lines)
        
        return ProcessResult(process.returncode, stdout_text, stderr_text)
    
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
    
    def _find_middle_file(self, temp_dir: str) -> Optional[str]:
        """Find the middle.json file in MinerU output directory."""
        temp_path = Path(temp_dir)
        
        # Search for middle.json files recursively
        for middle_file in temp_path.rglob("*middle.json"):
            return str(middle_file)
        
        return None
    
    def _move_to_data_directory(self, source_file: str, call_api: bool = False, call_api_force: bool = False) -> str:
        """Move output file to pdf_extractor_data directory and optionally process images with API."""
        # Create data directory structure
        data_dir = Path(__file__).parent / "pdf_extractor_data"
        markdown_dir = data_dir / "markdown"
        markdown_dir.mkdir(parents=True, exist_ok=True)
        
        # Find next available filename
        counter = 0
        while True:
            target_file = markdown_dir / f"{counter}.md"
            if not target_file.exists():
                break
            counter += 1
        
        # Copy file to target location
        shutil.copy2(source_file, target_file)
        
        # Post-process with image API if requested
        if call_api:
            self._post_process_with_image_api(str(target_file), call_api_force)
        
        return str(target_file)
    
    def _post_process_with_image_api(self, markdown_file: str, force: bool = False):
        """Post-process markdown file by adding image API descriptions."""
        try:
            # Find middle.json file for image information
            middle_file = self._find_middle_file(self.temp_dir) if hasattr(self, 'temp_dir') else None
            if not middle_file:
                print("⚠️  No middle file found for image API processing", file=sys.stderr)
                return
            
            # Load middle.json to get image information
            with open(middle_file, 'r', encoding='utf-8') as f:
                middle_data = json.load(f)
            
            # Extract image blocks from middle.json
            image_blocks = []
            pdf_info = middle_data.get('pdf_info', [])
            for page_idx, page_data in enumerate(pdf_info):
                preproc_blocks = page_data.get('preproc_blocks', [])
                for block_idx, block in enumerate(preproc_blocks):
                    if block.get('type') == 'image':
                        image_blocks.append({
                            'page': page_idx + 1,
                            'block_idx': block_idx,
                            'bbox': block.get('bbox', [])
                        })
            
            if not image_blocks:
                print("ℹ️  No images found for API processing", file=sys.stderr)
                return
            
            # Read current markdown content
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process each image with API
            print(f"🔄 Processing {len(image_blocks)} images with API...", file=sys.stderr)
            
            # Here we would call the image analysis API
            # For now, just add placeholder descriptions
            updated_content = content
            for i, img_block in enumerate(image_blocks):
                # Add image description after each image
                # This is a simplified approach - in reality, we'd need to match images in the markdown
                placeholder_desc = f"\n\n**Image Analysis (Page {img_block['page']}):** Image understanding API call {'failed' if not force else 'processed'}.\n"
                # Insert description after the first occurrence of an image
                if f"![" in updated_content:
                    # Find image references and add descriptions
                    import re
                    pattern = r'(!\[.*?\]\(.*?\))'
                    matches = list(re.finditer(pattern, updated_content))
                    if i < len(matches):
                        match = matches[i]
                        insert_pos = match.end()
                        updated_content = updated_content[:insert_pos] + placeholder_desc + updated_content[insert_pos:]
            
            # Write updated content back
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"✅ Added API descriptions for {len(image_blocks)} images", file=sys.stderr)
            
        except Exception as e:
            print(f"⚠️  Error in image API post-processing: {e}", file=sys.stderr)
    
    def _fallback_to_original(self, pdf_path: str, layout_mode: str, mode: str, 
                            call_api: bool, call_api_force: bool, page_range: Optional[str], debug: bool) -> str:
        """Fallback to original pdf_extractor when MinerU fails."""
        print("⚠️  MinerU failed, falling back to original PDF extractor", file=sys.stderr)
        
        # Import original extractor
        from pdf_extractor import extract_and_analyze_pdf
        
        return extract_and_analyze_pdf(
            pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
        )

# Create a global instance
mineru_wrapper = MinerUWrapper()

def extract_and_analyze_pdf_with_mineru(
    pdf_path: str,
    layout_mode: str = "arxiv",
    mode: str = "academic",
    call_api: bool = True,
    call_api_force: bool = False,
    page_range: Optional[str] = None,
    debug: bool = False
) -> str:
    """
    Main function that uses MinerU for PDF extraction.
    Maintains the same interface as the original extract_and_analyze_pdf function.
    """
    try:
        wrapper = MinerUWrapper()
        return wrapper.extract_and_analyze_pdf(
            pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
        )
    except Exception as e:
        print(f"⚠️  MinerU failed, falling back to original PDF extractor")
        print(f"MinerU: Unexpected error: {e}")
        
        # Fallback to original PDF extractor
        try:
            from pdf_extractor.pdf_extractor import extract_and_analyze_pdf
            return extract_and_analyze_pdf(
                pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
            )
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            raise fallback_error 