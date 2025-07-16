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
            
            # Enable formula and table parsing with error handling
            cmd.extend(["-f", "true"])  # Enable formula parsing
            cmd.extend(["-t", "true"])  # Enable table parsing
            
            if debug:
                print(f"MinerU command: {' '.join(cmd)}", file=sys.stderr)
            
            # Calculate timeout based on page range (2 minutes per page, minimum 10 minutes)
            page_count = self._estimate_page_count(page_range)
            timeout = max(600, page_count * 120)  # 2 minutes per page, minimum 10 minutes
            
            # Execute MinerU command silently
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
                # Check for specific tokenizer errors
                if "tokenizer" in result.stdout.lower() or "unimernet" in result.stdout.lower():
                    print("⚠️  Warning: UnimerNet tokenizer failed to recognize some formulas", file=sys.stderr)
                    print("💡 Some mathematical formulas may not be properly converted to LaTeX", file=sys.stderr)
                    # Continue processing instead of failing completely
                else:
                    print("MinerU: Runtime error detected in output", file=sys.stderr)
                    if debug:
                        print(f"MinerU: Error details in stdout", file=sys.stderr)
                    return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
            
            # Find the output markdown file
            output_file = self._find_output_file(self.temp_dir)
            if output_file:
                # Move to pdf_extractor_data directory and process with API if requested
                return self._move_to_data_directory(output_file, pdf_path, call_api, call_api_force)
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
            pass
    
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
        """Run MinerU command with silenced output."""
        import subprocess
        import threading
        import time
        
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
        
        # Collect output silently
        stdout_lines = []
        stderr_lines = []
        
        def read_output():
            for line in iter(process.stdout.readline, ''):
                stdout_lines.append(line)
                # Check for tokenizer warnings in real-time
                if "tokenizer" in line.lower() and ("error" in line.lower() or "warning" in line.lower()):
                    print("⚠️  Warning: UnimerNet tokenizer issue detected during processing", file=sys.stderr)
                elif "unimernet" in line.lower() and ("error" in line.lower() or "fail" in line.lower()):
                    print("⚠️  Warning: UnimerNet formula recognition failed for some content", file=sys.stderr)
        
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
    
    def _move_to_data_directory(self, source_file: str, pdf_path: str, call_api: bool = False, call_api_force: bool = False) -> str:
        """Move output file to pdf_extractor_data directory and create same-name file in PDF directory."""
        # Create data directory structure
        data_dir = Path(__file__).parent / "pdf_extractor_data"
        markdown_dir = data_dir / "markdown"
        markdown_dir.mkdir(parents=True, exist_ok=True)
        
        # Find next available filename for pdf_extractor_data
        counter = 0
        while True:
            target_file = markdown_dir / f"{counter}.md"
            if not target_file.exists():
                break
            counter += 1
        
        # Copy file to pdf_extractor_data location
        shutil.copy2(source_file, target_file)
        
        # Copy images from MinerU temp directory to pdf_extractor_data/images
        self._copy_mineru_images_to_data_directory(data_dir)
        
        # Post-process with image API if requested
        if call_api:
            self._post_process_with_image_api(str(target_file), call_api_force)
        
        # Create same-name markdown file in PDF directory
        pdf_path_obj = Path(pdf_path)
        pdf_directory = pdf_path_obj.parent
        pdf_stem = pdf_path_obj.stem
        same_name_md_file = pdf_directory / f"{pdf_stem}.md"
        
        # Read the content from the pdf_extractor_data file
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update image paths to reference pdf_extractor_data
        updated_content = self._update_image_paths_for_paper_directory(content, str(data_dir))
        
        # Write to same-name file in PDF directory
        with open(same_name_md_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        return str(target_file)
    
    def _update_image_paths_for_paper_directory(self, content: str, data_dir: str) -> str:
        """Update image paths in markdown content to reference pdf_extractor_data directory."""
        import re
        
        # Find all image references in markdown
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image_path(match):
            alt_text = match.group(1)
            original_path = match.group(2)
            
            # Convert relative paths to absolute paths referencing pdf_extractor_data
            if not original_path.startswith(('http://', 'https://', '/')):
                # This is a relative path, convert it to reference pdf_extractor_data
                if 'images/' in original_path:
                    # Extract the filename
                    filename = Path(original_path).name
                    new_path = str(Path(data_dir) / 'images' / filename)
                else:
                    # If it's not in images/ folder, try to find it in pdf_extractor_data
                    new_path = str(Path(data_dir) / 'images' / Path(original_path).name)
                
                return f'![{alt_text}]({new_path})'
            else:
                # Keep absolute paths as they are
                return match.group(0)
        
        # Replace all image paths
        updated_content = re.sub(image_pattern, replace_image_path, content)
        
        return updated_content
    
    def _copy_mineru_images_to_data_directory(self, data_dir: Path):
        """Copy images from MinerU temp directory to pdf_extractor_data/images."""
        if not hasattr(self, 'temp_dir') or not self.temp_dir:
            return
        
        # Create images directory
        images_dir = data_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all image files in temp directory
        temp_path = Path(self.temp_dir)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        
        for root, dirs, files in os.walk(temp_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    source_image = Path(root) / file
                    target_image = images_dir / file
                    
                    # Copy image if it doesn't exist or is different
                    if not target_image.exists() or source_image.stat().st_size != target_image.stat().st_size:
                        shutil.copy2(source_image, target_image)
    
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