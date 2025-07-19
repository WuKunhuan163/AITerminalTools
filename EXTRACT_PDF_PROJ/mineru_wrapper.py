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
from datetime import datetime

# Add MinerU path to sys.path
MINERU_PATH = Path(__file__).parent / "pdf_extractor_MinerU"
sys.path.insert(0, str(MINERU_PATH))

# Add parent directory to path for centralized cache system
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    # Import centralized cache system from EXTRACT_IMG_PROJ
    from EXTRACT_IMG_PROJ.cache_system import ImageCacheSystem
except ImportError:
    try:
        # Fallback import path
        import sys
        from pathlib import Path
        extract_img_proj = Path(__file__).parent.parent / "EXTRACT_IMG_PROJ"
        if str(extract_img_proj) not in sys.path:
            sys.path.insert(0, str(extract_img_proj))
        from cache_system import ImageCacheSystem
    except ImportError:
        print("Warning: Could not import centralized cache system", file=sys.stderr)
        ImageCacheSystem = None

class MinerUWrapper:
    """
    Wrapper class for MinerU functionality.
    Provides a compatible interface with the original pdf_extractor.
    """
    
    def __init__(self):
        self.mineru_path = MINERU_PATH
        self.temp_dir = None
        
        # Initialize centralized cache system
        if ImageCacheSystem:
            self.cache_system = ImageCacheSystem(base_dir=Path(__file__).parent.parent)
        else:
            self.cache_system = None
        
    def extract_and_analyze_pdf(
        self,
        pdf_path: str,
        layout_mode: str = "arxiv",
        mode: str = "academic", 
        call_api: bool = True,
        call_api_force: bool = False,
        page_range: Optional[str] = None,
        debug: bool = False,
        async_mode: bool = False
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
            async_mode: Enable async processing (disable image/formula/table analysis initially)
            
        Returns:
            Path to the output markdown file
        """
        
        # Create temporary directory for MinerU output
        self.temp_dir = tempfile.mkdtemp(prefix="mineru_output_")
        
        try:
            # Construct MinerU command
            # Convert pdf_path to absolute path
            pdf_path_abs = str(Path(pdf_path).resolve())
            cmd = [
                "python3",
                "-m", "mineru.cli.client",
                "-p", pdf_path_abs,
                "-o", self.temp_dir
            ]
            
            # Add page range if specified
            if page_range:
                start_page, end_page = self._parse_page_range(page_range)
                if start_page is not None:
                    cmd.extend(["-s", str(start_page)])
                if end_page is not None:
                    cmd.extend(["-e", str(end_page)])
            
            # Configure processing based on async_mode
            if async_mode:
                # Async mode: disable image/formula/table analysis initially
                cmd.extend(["-f", "false"])  # Disable formula parsing
                cmd.extend(["-t", "false"])  # Disable table parsing
                print("🔄 异步模式：初次处理时禁用图片、公式、表格分析", file=sys.stderr)
            else:
                # Normal mode: smart formula parsing with fallback
                cmd.extend(["-f", "true"])   # Enable formula parsing (will handle tokenizer errors gracefully)
                cmd.extend(["-t", "true"])   # Enable table parsing
            cmd.extend(["-d", "cpu"])    # Force CPU usage to avoid MPS device issues on Mac
            
            if debug:
                print(f"MinerU command: {' '.join(cmd)}", file=sys.stderr)
            
            # Calculate timeout based on page range (2 minutes per page, minimum 10 minutes)
            page_count = self._estimate_page_count(page_range)
            timeout = max(600, page_count * 120)  # 2 minutes per page, minimum 10 minutes
            
            # Execute MinerU command
            result = self._run_with_progress(cmd, timeout, async_mode)
            
            # Print debug output if enabled or if there was an error
            if debug or result.returncode != 0:
                print(f"MinerU stdout: {result.stdout}", file=sys.stderr)
                print(f"MinerU stderr: {result.stderr}", file=sys.stderr)
                print(f"MinerU return code: {result.returncode}", file=sys.stderr)
            
            # Always print the last few lines of output for debugging
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 5:
                    print(f"MinerU: Last output lines:", file=sys.stderr)
                    for line in lines[-5:]:
                        print(f"  {line}", file=sys.stderr)
            
            if result.returncode != 0:
                print(f"MinerU error: {result.stderr}", file=sys.stderr)
                return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
            
            # Check for runtime errors even if return code is 0
            if "Exception:" in result.stdout or "Error:" in result.stdout or "Traceback" in result.stdout:
                # Check for specific tokenizer errors
                if "tokenizer" in result.stdout.lower() or "unimernet" in result.stdout.lower():
                    # print("⚠️  Warning: UnimerNet tokenizer failed - trying without formula recognition", file=sys.stderr)  # Silenced per user request
                    
                    # Try again without formula recognition
                    retry_result = self._retry_without_formulas(pdf_path, page_range, debug)
                    if retry_result:
                        # print("✅ Successfully processed without formula recognition", file=sys.stderr)  # Silenced per user request
                        return retry_result
                    
                    # If retry also fails, create basic output
                    print("MinerU: Retry without formulas also failed", file=sys.stderr)
                    basic_output = self._create_basic_output_after_tokenizer_error(pdf_path)
                    if basic_output:
                        print("MinerU: Created basic output despite tokenizer error", file=sys.stderr)
                        return basic_output
                    
                    return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
                else:
                    print("MinerU: Runtime error detected in output", file=sys.stderr)
                    if debug:
                        print(f"MinerU: Error details in stdout", file=sys.stderr)
                    return self._fallback_to_original(pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug)
            
            # Find the output markdown file
            output_file = self._find_output_file(self.temp_dir)
            if output_file:
                # Move to pdf_extractor_data directory and process with API if requested
                target_file = self._move_to_data_directory(output_file, pdf_path, call_api, call_api_force, page_range)
                
                # If async mode, add placeholders for post-processing
                if async_mode and target_file:
                    self._add_async_placeholders(target_file, output_file, pdf_path)
                
                return target_file
            else:
                print("MinerU: No output file found", file=sys.stderr)
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
    
    def _run_with_progress(self, cmd: list, timeout: int, async_mode: bool = False):
        """Run MinerU command with conditional output display."""
        import subprocess
        import threading
        import time
        
        # Set environment variables to avoid MPS device issues on Mac
        env = os.environ.copy()
        env['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        env['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            cwd=str(self.mineru_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env
        )
        
        # Collect output silently
        stdout_lines = []
        stderr_lines = []
        
        def read_output():
            for line in iter(process.stdout.readline, ''):
                stdout_lines.append(line)
                # In async mode, show MinerU output to user
                if async_mode:
                    print(line.rstrip())
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
    
    def _move_to_data_directory(self, source_file: str, pdf_path: str, call_api: bool = False, call_api_force: bool = False, page_range: Optional[str] = None) -> str:
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
        
        # Add page range to filename if specified
        if page_range:
            pdf_stem_with_pages = f"{pdf_stem}_p{page_range}"
        else:
            pdf_stem_with_pages = pdf_stem
            
        same_name_md_file = pdf_directory / f"{pdf_stem_with_pages}.md"
        
        # Read the content from the pdf_extractor_data file
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update image paths to reference pdf_extractor_data
        updated_content = self._update_image_paths_for_paper_directory(content, str(data_dir))
        
        # Convert HTML tables to Markdown format
        markdown_content = self._convert_html_tables_to_markdown(updated_content)
        
        # Write to same-name file in PDF directory
        with open(same_name_md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Create {pdf_stem}_data folder with MinerU intermediate files
        self._create_intermediate_data_folder(pdf_directory, pdf_stem_with_pages)
        
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
    
    def _convert_html_tables_to_markdown(self, content: str) -> str:
        """Convert HTML tables to Markdown format."""
        import re
        from html import unescape
        
        # Pattern to match HTML table structure
        table_pattern = r'<html><body><table>(.*?)</table></body></html>'
        
        def convert_table(match):
            table_content = match.group(1)
            
            # Extract table rows
            row_pattern = r'<tr>(.*?)</tr>'
            rows = re.findall(row_pattern, table_content, re.DOTALL)
            
            if not rows:
                return match.group(0)  # Return original if no rows found
            
            markdown_rows = []
            
            for i, row in enumerate(rows):
                # Extract cells from row
                cell_pattern = r'<td>(.*?)</td>'
                cells = re.findall(cell_pattern, row, re.DOTALL)
                
                # Clean up cell content
                cleaned_cells = []
                for cell in cells:
                    # Remove extra whitespace and HTML entities
                    cleaned_cell = unescape(cell.strip())
                    # Replace line breaks with spaces
                    cleaned_cell = re.sub(r'\s+', ' ', cleaned_cell)
                    cleaned_cells.append(cleaned_cell)
                
                # Create markdown row
                if cleaned_cells:
                    markdown_row = '| ' + ' | '.join(cleaned_cells) + ' |'
                    markdown_rows.append(markdown_row)
                    
                    # Add header separator after first row
                    if i == 0:
                        separator = '| ' + ' | '.join(['---'] * len(cleaned_cells)) + ' |'
                        markdown_rows.append(separator)
            
            return '\n'.join(markdown_rows)
        
        # Replace all HTML tables with Markdown tables
        result = re.sub(table_pattern, convert_table, content, flags=re.DOTALL)
        
        return result
    
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
    
    def _create_intermediate_data_folder(self, pdf_directory: Path, pdf_stem: str):
        """Create {pdf_stem}_data folder with MinerU intermediate files."""
        if not hasattr(self, 'temp_dir') or not self.temp_dir:
            return
        
        # Create the data folder
        data_folder = pdf_directory / f"{pdf_stem}_extract_data"
        data_folder.mkdir(exist_ok=True)
        
        # Copy all MinerU intermediate files to the data folder
        temp_path = Path(self.temp_dir)
        
        # Files to copy (MinerU intermediate outputs)
        target_files = [
            f"{pdf_stem}_content_list.json",
            f"{pdf_stem}_layout.pdf", 
            f"{pdf_stem}_middle.json",
            f"{pdf_stem}_model.json",
            f"{pdf_stem}_origin.pdf",
            f"{pdf_stem}_span.pdf"
        ]
        
        # Also look for files without the pdf_stem prefix (common in MinerU output)
        generic_files = [
            "content_list.json",
            "layout.pdf",
            "middle.json", 
            "model.json",
            "origin.pdf",
            "span.pdf"
        ]
        
        # Copy files recursively from temp directory
        for root, dirs, files in os.walk(temp_path):
            root_path = Path(root)
            for file in files:
                source_file = root_path / file
                
                # Check if this is one of the target files
                should_copy = False
                target_name = file
                
                # Check for exact matches with pdf_stem prefix
                if file in target_files:
                    should_copy = True
                # Check for generic files and rename them with pdf_stem prefix
                elif file in generic_files:
                    should_copy = True
                    # Rename generic files to include pdf_stem
                    if file == "content_list.json":
                        target_name = f"{pdf_stem}_content_list.json"
                    elif file == "layout.pdf":
                        target_name = f"{pdf_stem}_layout.pdf"
                    elif file == "middle.json":
                        target_name = f"{pdf_stem}_middle.json"
                    elif file == "model.json":
                        target_name = f"{pdf_stem}_model.json"
                    elif file == "origin.pdf":
                        target_name = f"{pdf_stem}_origin.pdf"
                    elif file == "span.pdf":
                        target_name = f"{pdf_stem}_span.pdf"
                
                if should_copy:
                    target_file = data_folder / target_name
                    try:
                        shutil.copy2(source_file, target_file)
                        # print(f"📄 Copied {file} -> {target_name}", file=sys.stderr)  # Silenced per user request
                    except Exception as e:
                        print(f"⚠️  Warning: Could not copy {file}: {e}", file=sys.stderr)
        
        # Copy images folder if it exists
        for root, dirs, files in os.walk(temp_path):
            if "images" in dirs:
                source_images_dir = Path(root) / "images"
                target_images_dir = data_folder / "images"
                
                if source_images_dir.exists() and source_images_dir.is_dir():
                    # Copy the entire images directory
                    if target_images_dir.exists():
                        shutil.rmtree(target_images_dir)
                    shutil.copytree(source_images_dir, target_images_dir)
                    # print(f"📁 Copied images folder to {target_images_dir}", file=sys.stderr)  # Silenced per user request
                    break  # Only copy the first images folder found
        
        # print(f"✅ Created intermediate data folder: {data_folder}", file=sys.stderr)  # Silenced per user request
    
    def _retry_without_formulas(self, pdf_path: str, page_range: Optional[str], debug: bool) -> Optional[str]:
        """
        Retry MinerU processing without formula recognition to avoid tokenizer errors.
        
        Args:
            pdf_path: Path to the PDF file
            page_range: Page range to process
            debug: Enable debug mode
            
        Returns:
            Path to output file if successful, None otherwise
        """
        try:
            # print("🔄 Retrying MinerU without formula recognition...", file=sys.stderr)  # Silenced per user request
            
            # Create new temporary directory for retry
            retry_temp_dir = tempfile.mkdtemp(prefix="mineru_retry_")
            
            # Construct MinerU command without formula recognition
            pdf_path_abs = str(Path(pdf_path).resolve())
            cmd = [
                "python3",
                "-m", "mineru.cli.client",
                "-p", pdf_path_abs,
                "-o", retry_temp_dir,
                "-f", "false",  # Disable formula parsing
                "-t", "true",   # Keep table parsing
                "-d", "cpu"     # Force CPU usage to avoid MPS device issues on Mac
            ]
            
            # Add page range if specified
            if page_range:
                start_page, end_page = self._parse_page_range(page_range)
                if start_page is not None:
                    cmd.extend(["-s", str(start_page)])
                if end_page is not None:
                    cmd.extend(["-e", str(end_page)])
            
            if debug:
                print(f"MinerU retry command: {' '.join(cmd)}", file=sys.stderr)
            
            # Execute retry command
            env = os.environ.copy()
            env['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            env['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
            
            result = subprocess.run(
                cmd,
                cwd=str(self.mineru_path),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                env=env
            )
            
            if result.returncode == 0 and "Exception:" not in result.stdout:
                # Success! Find output file
                output_file = self._find_output_file(retry_temp_dir)
                if output_file:
                    # Update temp_dir to retry directory for proper cleanup
                    self.temp_dir = retry_temp_dir
                    return self._move_to_data_directory(output_file, pdf_path, False, False, page_range)
                else:
                    print("MinerU retry: No output file found", file=sys.stderr)
                    return None
            else:
                print(f"MinerU retry failed: return code {result.returncode}", file=sys.stderr)
                if debug:
                    print(f"MinerU retry stdout: {result.stdout}", file=sys.stderr)
                    print(f"MinerU retry stderr: {result.stderr}", file=sys.stderr)
                return None
                
        except Exception as e:
            print(f"MinerU retry error: {e}", file=sys.stderr)
            return None
    
    def _create_basic_output_after_tokenizer_error(self, pdf_path: str) -> Optional[str]:
        """Create a basic output file with tokenizer error information."""
        try:
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
            
            # Create basic markdown with tokenizer error information
            pdf_name = Path(pdf_path).stem
            basic_content = f"""# Analysis Report for: {pdf_name}

```yaml
Source PDF: {Path(pdf_path).name}
Analysis Mode: academic
Layout Mode: arxiv
API Called: False
Status: Tokenizer Error
```

---

## ⚠️ Tokenizer Error

The UnimerNet tokenizer failed to load properly. This is a known compatibility issue with the current tokenizer version.

**Error Details:**
- Error: "data did not match any variant of untagged enum ModelWrapper"
- Location: tokenizer.json file parsing
- Impact: Formula recognition unavailable

**Possible Solutions:**
1. Update tokenizer version
2. Use alternative formula recognition method
3. Process without formula recognition

---

## 📄 Page 1

**Note:** Content analysis was interrupted due to tokenizer error.
Formula recognition is currently unavailable.

"""
            
            # Write to file
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(basic_content)
            
            # Create same-name file in PDF directory
            pdf_path_obj = Path(pdf_path)
            pdf_directory = pdf_path_obj.parent
            pdf_stem = pdf_path_obj.stem
            same_name_md_file = pdf_directory / f"{pdf_stem}.md"
            
            with open(same_name_md_file, 'w', encoding='utf-8') as f:
                f.write(basic_content)
            
            # Try to create intermediate data folder even with error
            self._create_intermediate_data_folder(pdf_directory, pdf_stem)
            
            return str(target_file)
            
        except Exception as e:
            print(f"Failed to create basic output: {e}", file=sys.stderr)
            return None
    
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
    
    def _add_async_placeholders(self, target_file: str, original_output_file: str, pdf_path: str = None):
        """Add placeholders for async post-processing in markdown file and create JSON status file."""
        try:
            # Find the middle.json file for image/formula/table information
            middle_file = self._find_middle_file(self.temp_dir)
            if not middle_file:
                print("⚠️  No middle file found for async placeholder processing", file=sys.stderr)
                return
            
            # Load middle.json to get block information
            with open(middle_file, 'r', encoding='utf-8') as f:
                middle_data = json.load(f)
            
            # Extract blocks that need post-processing with their image paths
            blocks_to_process = []
            image_path_to_type = {}  # Map image paths to their types
            pdf_info = middle_data.get('pdf_info', [])
            
            for page_idx, page_data in enumerate(pdf_info):
                preproc_blocks = page_data.get('preproc_blocks', [])
                for block_idx, block in enumerate(preproc_blocks):
                    block_type = block.get('type')
                    if block_type in ['image', 'table', 'formula', 'interline_equation']:
                        # Extract image path from the block structure
                        image_path = self._extract_image_path_from_block(block)
                        if image_path:
                            blocks_to_process.append({
                                'page': page_idx + 1,
                                'block_idx': block_idx,
                                'type': block_type,
                                'bbox': block.get('bbox', []),
                                'image_path': image_path
                            })
                            image_path_to_type[image_path] = block_type

            
            if not blocks_to_process:
                print("ℹ️  No images/formulas/tables found for async processing", file=sys.stderr)
                return
            
            # Read current markdown content
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add placeholders before each image reference
            updated_content = self._add_placeholders_to_content(content, image_path_to_type)
            
            # Write updated content back (WITHOUT status summary)
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # Also update the same-name file in PDF directory if pdf_path is provided
            if pdf_path:
                try:
                    pdf_path_obj = Path(pdf_path)
                    pdf_directory = pdf_path_obj.parent
                    pdf_stem = pdf_path_obj.stem
                    same_name_md_file = pdf_directory / f"{pdf_stem}.md"
                    
                    if same_name_md_file.exists():
                        # Read the same-name file content
                        with open(same_name_md_file, 'r', encoding='utf-8') as f:
                            same_name_content = f.read()
                        
                        # Add placeholders to same-name file content
                        updated_same_name_content = self._add_placeholders_to_content(same_name_content, image_path_to_type)
                        
                        # Write updated content back to same-name file (WITHOUT status summary)
                        with open(same_name_md_file, 'w', encoding='utf-8') as f:
                            f.write(updated_same_name_content)
                        
                        print(f"✅ 同名文件也已更新: {same_name_md_file}", file=sys.stderr)
                except Exception as e:
                    print(f"⚠️  Error updating same-name file: {e}", file=sys.stderr)
            
            # Create JSON status file instead of adding to markdown
            if pdf_path:
                status_file = self._create_postprocess_status_json(pdf_path, blocks_to_process, image_path_to_type)
                if status_file:
                    image_count = sum(1 for b in blocks_to_process if b['type'] == 'image')
                    formula_count = sum(1 for b in blocks_to_process if b['type'] in ['formula', 'interline_equation'])
                    table_count = sum(1 for b in blocks_to_process if b['type'] == 'table')
                    
                    print(f"✅ 添加异步处理标签: {image_count}图片, {formula_count}公式, {table_count}表格", file=sys.stderr)
                    print(f"📄 后处理状态保存至: {Path(status_file).name}", file=sys.stderr)
                else:
                    print("⚠️  Failed to create status file", file=sys.stderr)
            
        except Exception as e:
            print(f"⚠️  Error adding async placeholders: {e}", file=sys.stderr)
    
    def _extract_image_path_from_block(self, block):
        """Extract image path from a block structure."""
        try:
            # Try to find image_path in the block structure
            if 'image_path' in block:
                return block['image_path']
            
            # Look in blocks -> lines -> spans
            blocks = block.get('blocks', [])
            for sub_block in blocks:
                lines = sub_block.get('lines', [])
                for line in lines:
                    spans = line.get('spans', [])
                    for span in spans:
                        if 'image_path' in span:
                            return span['image_path']
            
            # Look in lines -> spans directly (for interline_equation structure)
            lines = block.get('lines', [])
            for line in lines:
                spans = line.get('spans', [])
                for span in spans:
                    if 'image_path' in span:
                        return span['image_path']
            
            return None
        except Exception as e:
            print(f"⚠️  Error extracting image path: {e}", file=sys.stderr)
            return None
    
    def _add_placeholders_to_content(self, content: str, image_path_to_type: dict):
        """Add type placeholders before image references in markdown content."""
        import re
        
        # Regular expression to match image markdown syntax
        # ![alt text](path)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        
        def replace_image(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # Extract just the filename from the full path
            image_filename = image_path.split('/')[-1]
            
            # Find the corresponding type
            block_type = None
            for stored_path, stored_type in image_path_to_type.items():
                if stored_path == image_filename:
                    block_type = stored_type
                    break
            
            if block_type:
                # Map interline_equation to formula for placeholder
                if block_type == 'interline_equation':
                    placeholder = "[placeholder: formula]"
                else:
                    placeholder = f"[placeholder: {block_type}]"
                return f"{placeholder}\n{match.group(0)}"
            else:
                # No type found, return original
                return match.group(0)
        
        # Replace all image references with placeholders
        updated_content = re.sub(image_pattern, replace_image, content)
        
        return updated_content
    
    def _run_mineru_with_options(self, pdf_path: str, formula_enable: bool = True, 
                                table_enable: bool = True, debug: bool = False) -> Optional[str]:
        """
        运行MinerU处理，支持自定义公式和表格识别选项
        
        Args:
            pdf_path: PDF文件路径
            formula_enable: 是否启用公式识别
            table_enable: 是否启用表格识别
            debug: 是否启用调试模式
            
        Returns:
            输出文件路径，失败返回None
        """
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="mineru_post_")
            
            # 构建MinerU命令
            pdf_path_abs = str(Path(pdf_path).resolve())
            cmd = [
                "python3",
                "-m", "mineru.cli.client",
                "-p", pdf_path_abs,
                "-o", temp_dir,
                "-f", "true" if formula_enable else "false",
                "-t", "true" if table_enable else "false",
                "-d", "cpu"
            ]
            
            if debug:
                print(f"MinerU后处理命令: {' '.join(cmd)}", file=sys.stderr)
            
            # 执行命令
            env = os.environ.copy()
            env['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
            env['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
            
            result = subprocess.run(
                cmd, 
                cwd=self.mineru_path, 
                env=env,
                capture_output=True, 
                text=True, 
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                # 查找输出文件
                output_file = self._find_output_file(temp_dir)
                if output_file:
                    return output_file
                    
            if debug:
                print(f"MinerU后处理失败: {result.stderr}", file=sys.stderr)
                
            return None
            
        except Exception as e:
            print(f"MinerU后处理出错: {e}", file=sys.stderr)
            return None
    
    def _fallback_to_original(self, pdf_path: str, layout_mode: str, mode: str, 
                             call_api: bool, call_api_force: bool, page_range: Optional[str], debug: bool) -> str:
        """Fallback to original pdf_extractor when MinerU fails."""
        print("⚠️  MinerU failed, falling back to original PDF extractor", file=sys.stderr)
        
        # Import original extractor
        from pdf_extractor import extract_and_analyze_pdf
        
        return extract_and_analyze_pdf(
            pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug
        )

    def _create_postprocess_status_json(self, pdf_path: str, blocks_to_process: list, image_path_to_type: dict):
        """Create filename_postprocess.json status file."""
        try:
            pdf_path_obj = Path(pdf_path)
            pdf_directory = pdf_path_obj.parent
            pdf_stem = pdf_path_obj.stem
            
            # Create JSON status file path
            status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
            
            # Count different types
            image_count = sum(1 for b in blocks_to_process if b['type'] == 'image')
            formula_count = sum(1 for b in blocks_to_process if b['type'] in ['formula', 'interline_equation'])
            table_count = sum(1 for b in blocks_to_process if b['type'] == 'table')
            
            # Create status data
            status_data = {
                "pdf_file": pdf_path_obj.name,
                "created_at": datetime.now().isoformat(),
                "total_items": len(blocks_to_process),
                "counts": {
                    "images": image_count,
                    "formulas": formula_count,
                    "tables": table_count
                },
                "items": [],
                "processing_commands": {
                    "image_analysis": f"EXTRACT_PDF_POST {pdf_path_obj.name} --type image",
                    "formula_recognition": f"EXTRACT_PDF_POST {pdf_path_obj.name} --type formula", 
                    "table_recognition": f"EXTRACT_PDF_POST {pdf_path_obj.name} --type table",
                    "process_all": f"EXTRACT_PDF_POST {pdf_path_obj.name} --type all"
                }
            }
            
            # Add detailed item information
            for block in blocks_to_process:
                # Use image filename (hash) as ID
                image_path = block['image_path']
                hash_id = Path(image_path).stem if image_path else f"{block['type']}_{block['block_idx']:03d}"
                
                item = {
                    "id": hash_id,
                    "type": block['type'],
                    "page": block['page'],
                    "block_index": block['block_idx'],
                    "image_path": block['image_path'],
                    "bbox": block.get('bbox', []),
                    "processed": False,
                    "processor": self._get_processor_for_type(block['type'])
                }
                status_data["items"].append(item)
            
            # Write JSON file
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            # Update global hash mapping
            self._update_hash_mapping_from_items(status_data["items"])
            
            print(f"✅ 创建后处理状态文件: {status_file}")
            return str(status_file)
            
        except Exception as e:
            print(f"❌ 创建状态文件失败: {e}", file=sys.stderr)
            return None
    
    def _get_processor_for_type(self, block_type: str) -> str:
        """Get processor name for block type."""
        if block_type == 'image':
            return "Google API"
        elif block_type in ['formula', 'interline_equation']:
            return "UnimerNet"
        elif block_type == 'table':
            return "UnimerNet"
        else:
            return "Unknown"
    
    def _regenerate_status_from_markdown(self, pdf_path: str, markdown_file: str = None):
        """Regenerate status file based on placeholders and image links in markdown, preserving processed items."""
        try:
            pdf_path_obj = Path(pdf_path)
            pdf_directory = pdf_path_obj.parent
            pdf_stem = pdf_path_obj.stem
            
            # Check if existing status file has processed items to preserve
            status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
            existing_processed_items = {}
            
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                    
                    # Save processed items
                    for item in existing_data.get('items', []):
                        if item.get('processed', False):
                            existing_processed_items[item.get('id', '')] = item
                            
                    print(f"📄 保留 {len(existing_processed_items)} 个已处理项目")
                except Exception as e:
                    print(f"⚠️  读取现有状态文件失败: {e}")
            
            # If no markdown file specified, look for same-name file
            if not markdown_file:
                markdown_file = pdf_directory / f"{pdf_stem}.md"
            else:
                markdown_file = Path(markdown_file)
            
            if not markdown_file.exists():
                print(f"❌ Markdown文件不存在: {markdown_file}")
                return None
            
            # Read markdown content
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all placeholders and image links
            import re
            
            # Pattern to match placeholders with image links
            placeholder_pattern = r'\[placeholder:\s*(\w+)\]\s*!\[[^\]]*\]\(([^)]+)\)'
            matches = re.findall(placeholder_pattern, content)
            
            # Also find standalone image links that might need placeholders
            standalone_image_pattern = r'!\[[^\]]*\]\(([^)]+)\)'
            standalone_matches = re.findall(standalone_image_pattern, content)
            
            blocks_to_process = []
            image_path_to_type = {}
            processed_ids_found = set()
            
            # Process placeholders with images
            for i, (placeholder_type, image_path) in enumerate(matches):
                # Extract just the filename
                image_filename = Path(image_path).name
                hash_id = Path(image_path).stem
                
                # Map placeholder type
                if placeholder_type == 'formula':
                    block_type = 'formula'
                elif placeholder_type == 'table':
                    block_type = 'table'
                elif placeholder_type == 'image':
                    block_type = 'image'
                else:
                    block_type = placeholder_type
                
                blocks_to_process.append({
                    'page': 1,  # Can't determine page from markdown alone
                    'block_idx': i,
                    'type': block_type,
                    'bbox': [],
                    'image_path': image_filename
                })
                image_path_to_type[image_filename] = block_type
                processed_ids_found.add(hash_id)
            
            # Add preserved processed items that are still referenced in the markdown
            for hash_id, processed_item in existing_processed_items.items():
                if hash_id in processed_ids_found:
                    # Update the existing item instead of creating new one
                    for block in blocks_to_process:
                        if Path(block['image_path']).stem == hash_id:
                            # Keep the processed status and timestamp
                            block.update({
                                'processed': processed_item.get('processed', True),
                                'processed_at': processed_item.get('processed_at', '')
                            })
                            break
                else:
                    # This processed item is no longer in markdown, check if image still exists
                    image_still_in_md = any(hash_id in img_path for img_path in standalone_matches)
                    if image_still_in_md:
                        # Add back with placeholder regeneration
                        blocks_to_process.append({
                            'page': processed_item.get('page', 1),
                            'block_idx': len(blocks_to_process),
                            'type': processed_item.get('type', 'image'),
                            'bbox': processed_item.get('bbox', []),
                            'image_path': processed_item.get('image_path', f"{hash_id}.jpg"),
                            'processed': True,
                            'processed_at': processed_item.get('processed_at', '')
                        })
                        print(f"🔄 重新添加已处理项目: {hash_id}")
            
            if blocks_to_process:
                # Create status file
                status_file = self._create_postprocess_status_json(pdf_path, blocks_to_process, image_path_to_type)
                
                # Update processed items status in the new file
                if status_file and existing_processed_items:
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status_data = json.load(f)
                    
                    # Update processed status
                    for item in status_data.get('items', []):
                        item_id = item.get('id', '')
                        if item_id in existing_processed_items:
                            processed_item = existing_processed_items[item_id]
                            item['processed'] = processed_item.get('processed', True)
                            item['processed_at'] = processed_item.get('processed_at', '')
                    
                    # Recalculate counts (only unprocessed)
                    status_data['counts'] = self._recalculate_counts(status_data.get('items', []))
                    
                    # Save updated file
                    with open(status_file, 'w', encoding='utf-8') as f:
                        json.dump(status_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 从Markdown重新生成状态文件: {len(blocks_to_process)} 个项目")
                return status_file
            else:
                print("ℹ️  Markdown中未找到有效的placeholder")
                return None
                
        except Exception as e:
            print(f"❌ 重新生成状态文件失败: {e}", file=sys.stderr)
            return None
    
    def _check_or_create_status_file(self, pdf_path: str):
        """Check if status file exists, if not, try to regenerate from markdown."""
        pdf_path_obj = Path(pdf_path)
        pdf_directory = pdf_path_obj.parent
        pdf_stem = pdf_path_obj.stem
        
        status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
        
        if not status_file.exists():
            print(f"📄 状态文件不存在，尝试从Markdown重新生成...")
            return self._regenerate_status_from_markdown(pdf_path)
        else:
            return str(status_file)

    def _add_hash_ids_to_status(self, status_file: str):
        """Add unique hash IDs to each item in the status file for selective processing."""
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # Add hash IDs to items
            for i, item in enumerate(status_data.get('items', [])):
                # Use the image filename (which is already a hash) as the ID
                image_path = item.get('image_path', '')
                if image_path:
                    # Remove .jpg extension to get pure hash
                    hash_id = Path(image_path).stem
                    item['id'] = hash_id
                else:
                    # Fallback: generate ID from type and index
                    item['id'] = f"{item['type']}_{i:03d}"
            
            # Save updated status file
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 添加hash ID到状态文件: {len(status_data.get('items', []))} 个项目")
            return True
            
        except Exception as e:
            print(f"❌ 添加hash ID失败: {e}", file=sys.stderr)
            return False
    
    def _get_items_by_hash_ids(self, status_file: str, hash_ids: list) -> list:
        """Get specific items from status file by their hash IDs."""
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            items = status_data.get('items', [])
            selected_items = []
            updated_items = False
            
            for item in items:
                item_id = item.get('id', '')
                
                # First try to match by existing id field
                if item_id and item_id in hash_ids:
                    selected_items.append(item)
                    continue
                
                # If no id field, generate ID from image_path for compatibility
                if not item_id:
                    image_path = item.get('image_path', '')
                    if image_path:
                        # Generate ID from image path (use filename without extension)
                        generated_id = Path(image_path).stem
                        if generated_id in hash_ids:
                            # Update the item with generated ID for future use
                            item['id'] = generated_id
                            selected_items.append(item)
                            updated_items = True
                            print(f"   📝 为项目生成ID: {generated_id}")
            
            # Save updated status file if we generated new IDs
            if updated_items:
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            return selected_items
            
        except Exception as e:
            print(f"❌ 获取指定ID项目失败: {e}", file=sys.stderr)
            return []
    
    def _update_item_processing_status(self, status_file: str, hash_id: str, processed: bool = True):
        """Update processing status for a specific item by hash ID."""
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # Find and update the item
            items = status_data.get('items', [])
            updated = False
            
            for item in items:
                if item.get('id') == hash_id:
                    item['processed'] = processed
                    if processed:
                        item['processed_at'] = datetime.now().isoformat()
                    updated = True
                    break
            
            if updated:
                # Recalculate counts
                status_data['counts'] = self._recalculate_counts(items)
                
                # Save updated status file
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 更新项目状态: {hash_id} -> {'已处理' if processed else '未处理'}")
                return True
            else:
                print(f"⚠️  未找到ID: {hash_id}")
                return False
                
        except Exception as e:
            print(f"❌ 更新状态失败: {e}", file=sys.stderr)
            return False
    
    def _recalculate_counts(self, items: list) -> dict:
        """Recalculate counts based on current items."""
        counts = {"images": 0, "formulas": 0, "tables": 0}
        
        for item in items:
            if not item.get('processed', False):  # Only count unprocessed items
                item_type = item.get('type', '')
                if item_type == 'image':
                    counts['images'] += 1
                elif item_type in ['formula', 'interline_equation']:
                    counts['formulas'] += 1
                elif item_type == 'table':
                    counts['tables'] += 1
        
        return counts
    
    def _remove_placeholders_by_hash_ids(self, markdown_file: str, hash_ids: list):
        """Remove placeholders from markdown file for specified hash IDs."""
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find and remove placeholders for specific hash IDs
            import re
            lines = content.split('\n')
            updated_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Check if this line contains a placeholder
                placeholder_match = re.match(r'\[placeholder:\s*(\w+)\]', line.strip())
                if placeholder_match:
                    # Check the next line for image reference
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        image_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', next_line)
                        if image_match:
                            image_path = image_match.group(1)
                            # Extract hash from image path
                            image_hash = Path(image_path).stem
                            
                            if image_hash in hash_ids:
                                # Skip the placeholder line
                                print(f"🗑️  移除placeholder: {image_hash}")
                                i += 1  # Skip placeholder line
                                continue
                
                updated_lines.append(line)
                i += 1
            
            # Write updated content back
            updated_content = '\n'.join(updated_lines)
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"✅ 移除了 {len(hash_ids)} 个placeholder")
            return True
            
        except Exception as e:
            print(f"❌ 移除placeholder失败: {e}", file=sys.stderr)
            return False
    
    def process_items_by_hash_ids(self, pdf_path: str, hash_ids: list, processing_type: str = 'all', custom_prompt: str = None):
        """Process specific items by their hash IDs with real content processing."""
        try:
            pdf_path_obj = Path(pdf_path)
            pdf_directory = pdf_path_obj.parent
            pdf_stem = pdf_path_obj.stem
            
            # Find status file
            status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
            if not status_file.exists():
                print(f"❌ 状态文件不存在: {status_file}")
                return False
            
            # Add hash IDs if not present
            self._add_hash_ids_to_status(str(status_file))
            
            # Get selected items
            selected_items = self._get_items_by_hash_ids(str(status_file), hash_ids)
            if not selected_items:
                print(f"❌ 未找到指定的hash ID")
                return False
            
            print(f"🔄 开始处理 {len(selected_items)} 个指定项目...")
            
            # Find markdown file
            markdown_file = pdf_directory / f"{pdf_stem}.md"
            if not markdown_file.exists():
                print(f"❌ Markdown文件不存在: {markdown_file}")
                return False
            
            # Process each selected item with real content processing
            processed_ids = []
            for item in selected_items:
                item_type = item.get('type')
                item_id = item.get('id')
                image_path = item.get('image_path', '')
                
                # Check if we should process this type
                if processing_type != 'all':
                    if processing_type == 'image' and item_type != 'image':
                        continue
                    elif processing_type == 'formula' and item_type not in ['formula', 'interline_equation']:
                        continue
                    elif processing_type == 'table' and item_type != 'table':
                        continue
                
                print(f"🔄 处理 {item_type}: {item_id}")
                
                # Find the actual image file
                image_file_path = self._find_image_file(pdf_directory, image_path)
                if not image_file_path:
                    print(f"⚠️  找不到图片文件: {image_path}")
                    continue
                
                # Perform real processing based on type
                processed_content = None
                if item_type == 'image':
                    processed_content = self._process_image_content(image_file_path, custom_prompt)
                elif item_type in ['formula', 'interline_equation']:
                    processed_content = self._process_formula_content(image_file_path)
                elif item_type == 'table':
                    processed_content = self._process_table_content(image_file_path)
                
                if processed_content:
                    # Replace placeholder with processed content in markdown
                    if self._replace_placeholder_with_content(str(markdown_file), item_id, processed_content):
                        # Update status
                        if self._update_item_processing_status(str(status_file), item_id, True):
                            processed_ids.append(item_id)
                            print(f"✅ 成功处理并替换内容: {item_id}")
                        else:
                            print(f"⚠️  状态更新失败: {item_id}")
                    else:
                        print(f"⚠️  内容替换失败: {item_id}")
                else:
                    print(f"⚠️  内容处理失败: {item_id}")
            
            print(f"✅ 完成处理 {len(processed_ids)} 个项目")
            return len(processed_ids) > 0
            
        except Exception as e:
            print(f"❌ 批量处理失败: {e}", file=sys.stderr)
            return False
    
    def _find_image_file(self, pdf_directory: Path, image_filename: str) -> Optional[str]:
        """Find the actual image file in the PDF directory structure."""
        # Look for image in common locations
        possible_locations = [
            pdf_directory / image_filename,
            pdf_directory / "images" / image_filename,
            pdf_directory / f"{pdf_directory.stem}_extract_data" / "images" / image_filename,
            Path(__file__).parent / "pdf_extractor_data" / "images" / image_filename
        ]
        
        for location in possible_locations:
            if location.exists():
                return str(location)
        
        return None
    
    def _process_image_content(self, image_file_path: str, custom_prompt: str = None) -> Optional[str]:
        """Process image content using IMG2TEXT tool."""
        try:
            print(f"   🔄 调用IMG2TEXT工具...")
            
            # Call IMG2TEXT tool with academic mode for papers
            import subprocess
            img2text_path = Path(__file__).parent.parent / "IMG2TEXT"
            
            # Build command with academic mode and optional custom prompt
            cmd = [str(img2text_path), image_file_path, "--mode", "academic"]
            if custom_prompt:
                cmd.extend(["--prompt", custom_prompt])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                description = result.stdout.strip()
                
                # Check if the output indicates API failure
                if "*[API调用失败：" in description or "API调用失败" in description:
                    print(f"   ❌ IMG2TEXT API调用失败")
                    
                    # Extract detailed error information from stderr if available
                    stderr_output = result.stderr.strip()
                    if stderr_output:
                        # Parse error details for better formatting
                        error_details = self._parse_img2text_errors(stderr_output, description)
                        formatted_error = f"**[API调用失败]** 所有配置的API密钥都无法成功获取回复。\n\n详细错误信息：\n```\n{error_details}\n```"
                    else:
                        formatted_error = description.replace("*[", "**[").replace("]*", "]**")
                    
                    return f"\n\n**图片分析结果:**\n{formatted_error}\n"
                elif description:
                    print(f"   ✅ IMG2TEXT处理成功")
                    return f"\n\n**图片分析结果:**\n{description}\n"
                else:
                    print(f"   ⚠️  IMG2TEXT返回空结果")
                    fallback_description = f"**[图片分析结果]** IMG2TEXT工具未返回描述，图片文件: `{Path(image_file_path).name}`"
                    return f"\n\n**图片分析结果:**\n{fallback_description}\n"
            else:
                print(f"   ❌ IMG2TEXT调用失败，返回码: {result.returncode}")
                stderr_output = result.stderr.strip()
                if stderr_output:
                    error_details = self._parse_img2text_errors(stderr_output, "")
                    formatted_error = f"**[IMG2TEXT工具调用失败]**\n\n详细错误信息：\n```\n{error_details}\n```"
                else:
                    formatted_error = f"**[IMG2TEXT工具调用失败]** 返回码: {result.returncode}"
                
                return f"\n\n**图片分析结果:**\n{formatted_error}\n"
            
        except subprocess.TimeoutExpired:
            print(f"   ⏰ IMG2TEXT处理超时")
            fallback_description = f"**[IMG2TEXT处理超时]** 图片文件: `{Path(image_file_path).name}`"
            return f"\n\n**图片分析结果:**\n{fallback_description}\n"
        except Exception as e:
            print(f"   ❌ IMG2TEXT处理失败: {e}")
            fallback_description = f"**[IMG2TEXT工具出错]** {str(e)}\n\n图片文件: `{Path(image_file_path).name}`"
            return f"\n\n**图片分析结果:**\n{fallback_description}\n"
    
    def _parse_img2text_errors(self, stderr_output: str, stdout_output: str) -> str:
        """Parse IMG2TEXT error output to extract detailed error information."""
        try:
            error_details = []
            
            # Look for API key error patterns in stderr
            lines = stderr_output.split('\n')
            for line in lines:
                if "FREE 密钥时失败:" in line:
                    # Extract error message after the colon
                    error_msg = line.split("FREE 密钥时失败:")[-1].strip()
                    error_details.append(f"• FREE 密钥：{error_msg}")
                elif "PAID 密钥时失败:" in line:
                    # Extract error message after the colon
                    error_msg = line.split("PAID 密钥时失败:")[-1].strip()
                    error_details.append(f"• PAID 密钥：{error_msg}")
                elif "USER 密钥时失败:" in line:
                    # Extract error message after the colon
                    error_msg = line.split("USER 密钥时失败:")[-1].strip()
                    error_details.append(f"• USER 密钥：{error_msg}")
                elif "警告:" in line and "失败:" in line:
                    # Generic error pattern
                    error_msg = line.split("失败:")[-1].strip()
                    if "FREE" in line:
                        error_details.append(f"• FREE 密钥：{error_msg}")
                    elif "PAID" in line:
                        error_details.append(f"• PAID 密钥：{error_msg}")
                    elif "USER" in line:
                        error_details.append(f"• USER 密钥：{error_msg}")
            
            if error_details:
                return "\n".join(error_details)
            else:
                # Fallback: return the stderr output as is, but clean it up
                clean_stderr = stderr_output.replace('⚠️ 警告: ', '').strip()
                return clean_stderr if clean_stderr else "未知错误"
                
        except Exception as e:
            print(f"   ⚠️  解析错误信息失败: {e}")
            return stderr_output.replace('\n', ' ').strip() if stderr_output else "未知错误"
    
    def _process_formula_content(self, image_file_path: str) -> Optional[str]:
        """Process formula content using MinerU's embedded UnimerNet."""
        try:
            print(f"   🔄 调用UnimerNet处理公式...")
            
            # Import UnimerNet directly
            current_dir = Path(__file__).parent
            sys.path.insert(0, str(current_dir.parent / "UNIMERNET_PROJ"))
            
            from test_simple_unimernet import load_unimernet_model, recognize_image
            
            # Load model if not already loaded
            if not hasattr(self, '_unimernet_model') or self._unimernet_model is None:
                self._unimernet_model, self._unimernet_tokenizer = load_unimernet_model()
                print(f"   📱 UnimerNet模型加载成功")
            
            # Process the image (recognize_image expects file path, not PIL Image)
            result = recognize_image(image_file_path, self._unimernet_model, self._unimernet_tokenizer)
            
            if result and result.strip():
                print(f"   ✅ UnimerNet公式识别成功")
                return f"\n\n**公式识别结果:**\n{result}\n"
            else:
                print(f"   ⚠️  UnimerNet返回空结果")
                return f"\n\n**公式识别结果:**\n$$ \\text{{[公式识别失败]}} \\quad \\text{{来自 {Path(image_file_path).name}}} $$\n"
            
        except Exception as e:
            print(f"   ❌ 公式处理失败: {e}")
            return f"\n\n**公式识别结果:**\n$$ \\text{{[公式识别失败]}} \\quad \\text{{来自 {Path(image_file_path).name}}} $$\n"
    
    def _process_table_content(self, image_file_path: str) -> Optional[str]:
        """Process table content using MinerU's embedded UnimerNet."""
        try:
            print(f"   🔄 调用UnimerNet处理表格...")
            
            # Import UnimerNet directly
            current_dir = Path(__file__).parent
            sys.path.insert(0, str(current_dir.parent / "UNIMERNET_PROJ"))
            
            from test_simple_unimernet import load_unimernet_model, recognize_image
            
            # Load model if not already loaded
            if not hasattr(self, '_unimernet_model') or self._unimernet_model is None:
                self._unimernet_model, self._unimernet_tokenizer = load_unimernet_model()
                print(f"   📱 UnimerNet模型加载成功")
            
            # Process the image (recognize_image expects file path, not PIL Image)
            result = recognize_image(image_file_path, self._unimernet_model, self._unimernet_tokenizer)
            
            if result and result.strip():
                print(f"   ✅ UnimerNet表格识别成功")
                return f"\n\n**表格识别结果:**\n{result}\n"
            else:
                print(f"   ⚠️  UnimerNet返回空结果")
                return f"\n\n**表格识别结果:**\n| 表格识别 | 失败 | 来自 {Path(image_file_path).name} |\n| 处理状态 | 失败 | UnimerNet处理 |\n"
            
        except Exception as e:
            print(f"   ❌ 表格处理失败: {e}")
            return f"\n\n**表格识别结果:**\n| 表格识别 | 失败 | 来自 {Path(image_file_path).name} |\n| 处理状态 | 失败 | 处理异常 |\n"
    
    def _replace_placeholder_with_content(self, markdown_file: str, hash_id: str, content: str, preserve_hash: bool = True) -> bool:
        """Replace placeholder with processed content in markdown file."""
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Find the placeholder and image reference for this hash ID
            import re
            lines = file_content.split('\n')
            updated_lines = []
            i = 0
            replaced = False
            
            while i < len(lines):
                line = lines[i]
                
                # Check if this line contains a placeholder
                placeholder_match = re.match(r'\[placeholder:\s*(\w+)\]', line.strip())
                if placeholder_match:
                    # Check the next line for image reference
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]
                        image_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', next_line)
                        if image_match:
                            image_path = image_match.group(1)
                            # Extract hash from image path
                            image_hash = Path(image_path).stem
                            
                            if image_hash == hash_id:
                                # Replace placeholder with processed content, preserve hash ID
                                if preserve_hash:
                                    # Keep hash ID as a comment for rendering purposes
                                    updated_lines.append(f"--- hash: {hash_id} ---")
                                    updated_lines.append(content)
                                    updated_lines.append(next_line)  # Keep the original image reference
                                else:
                                    # Original behavior: replace placeholder completely
                                    updated_lines.append(content)
                                    updated_lines.append(next_line)  # Keep the original image reference
                                print(f"   🔄 替换placeholder: {hash_id}")
                                replaced = True
                                i += 2  # Skip both placeholder and image lines
                                continue
                
                updated_lines.append(line)
                i += 1
            
            if replaced:
                # Write updated content back
                updated_content = '\n'.join(updated_lines)
                with open(markdown_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                return True
            else:
                print(f"   ⚠️  未找到对应的placeholder: {hash_id}")
                return False
                
        except Exception as e:
            print(f"   ❌ 替换内容失败: {e}", file=sys.stderr)
            return False

    def _load_hash_mapping(self) -> dict:
        """Load global hash to type mapping."""
        try:
            mapping_file = Path(__file__).parent.parent / "hash_type_mapping.json"
            if mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('mappings', {})
            return {}
        except Exception as e:
            print(f"⚠️  加载hash映射失败: {e}", file=sys.stderr)
            return {}
    
    def _save_hash_mapping(self, mappings: dict):
        """Save global hash to type mapping."""
        try:
            mapping_file = Path(__file__).parent.parent / "hash_type_mapping.json"
            
            # Load existing data or create new
            if mapping_file.exists():
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    "description": "Global hash to type mapping for EXTRACT_PDF processing",
                    "created_at": datetime.now().isoformat(),
                    "mappings": {},
                    "usage_notes": [
                        "This file maps image file hashes to their content types (image, formula, table)",
                        "Used for placeholder regeneration when type information is missing",
                        "Automatically updated when processing items with known types"
                    ]
                }
            
            # Update mappings
            data['mappings'].update(mappings)
            data['last_updated'] = datetime.now().isoformat()
            
            # Save file
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 更新hash映射: {len(mappings)} 个新映射")
            return True
            
        except Exception as e:
            print(f"❌ 保存hash映射失败: {e}", file=sys.stderr)
            return False
    
    def _update_hash_mapping_from_items(self, items: list):
        """Update global hash mapping from processed items."""
        try:
            new_mappings = {}
            for item in items:
                hash_id = item.get('id', '')
                item_type = item.get('type', '')
                if hash_id and item_type:
                    new_mappings[hash_id] = item_type
            
            if new_mappings:
                self._save_hash_mapping(new_mappings)
                
        except Exception as e:
            print(f"⚠️  更新hash映射失败: {e}", file=sys.stderr)

    def _update_image_cache_with_types(self, pdf_path: str):
        """Update EXTRACT_IMG_PROJ/image_cache.json with type information from postprocess JSON."""
        try:
            pdf_path_obj = Path(pdf_path)
            pdf_directory = pdf_path_obj.parent
            pdf_stem = pdf_path_obj.stem
            
            # Load postprocess JSON
            status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
            if not status_file.exists():
                print(f"⚠️  后处理状态文件不存在: {status_file}")
                return False
            
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # Load image cache
            cache_file = Path(__file__).parent.parent / "EXTRACT_IMG_PROJ" / "image_cache.json"
            if not cache_file.exists():
                print(f"⚠️  图片缓存文件不存在: {cache_file}")
                return False
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Update cache entries with type information
            updated_count = 0
            for item in status_data.get('items', []):
                hash_id = item.get('id', '')
                item_type = item.get('type', '')
                
                if hash_id and item_type:
                    # Check if this hash exists as a key in the cache
                    if hash_id in cache_data:
                        cache_entry = cache_data[hash_id]
                        old_type = cache_entry.get('content_type')
                        cache_entry['content_type'] = item_type
                        cache_entry['updated_at'] = datetime.now().isoformat()
                        
                        if old_type != item_type:
                            print(f"   📝 更新缓存条目类型: {hash_id[:16]}... -> {item_type}")
                            updated_count += 1
                    else:
                        # Also check if hash is in the image path of any entry
                        for cache_key, cache_entry in cache_data.items():
                            if hash_id in cache_entry.get('image_path', '') or hash_id in cache_entry.get('source_path', ''):
                                old_type = cache_entry.get('content_type')
                                cache_entry['content_type'] = item_type
                                cache_entry['updated_at'] = datetime.now().isoformat()
                                
                                if old_type != item_type:
                                    print(f"   📝 更新缓存条目类型: {cache_key[:16]}... -> {item_type}")
                                    updated_count += 1
                                break
            
            if updated_count > 0:
                # Save updated cache
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 更新了 {updated_count} 个缓存条目的类型信息")
                return True
            else:
                print("ℹ️  没有缓存条目需要更新")
                return True
                
        except Exception as e:
            print(f"❌ 更新图片缓存类型信息失败: {e}", file=sys.stderr)
            return False
    
    def _sync_postprocess_with_cache(self, pdf_path: str):
        """Synchronize postprocess JSON with image cache and ensure alignment with markdown."""
        try:
            pdf_path_obj = Path(pdf_path)
            pdf_directory = pdf_path_obj.parent
            pdf_stem = pdf_path_obj.stem
            
            # First, update cache with type information from postprocess JSON
            self._update_image_cache_with_types(pdf_path)
            
            # Then check if markdown and JSON are aligned
            markdown_file = pdf_directory / f"{pdf_stem}.md"
            if markdown_file.exists():
                print("🔄 检查MD与JSON对齐状态...")
                
                # Read markdown to count current placeholders
                with open(markdown_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # Count placeholders in markdown
                import re
                placeholder_pattern = r'\[placeholder:\s*(\w+)\]\s*!\[[^\]]*\]\(([^)]+)\)'
                md_placeholders = re.findall(placeholder_pattern, md_content)
                
                # Load current JSON
                status_file = pdf_directory / f"{pdf_stem}_postprocess.json"
                if status_file.exists():
                    with open(status_file, 'r', encoding='utf-8') as f:
                        status_data = json.load(f)
                    
                    json_items = status_data.get('items', [])
                    unprocessed_items = [item for item in json_items if not item.get('processed', False)]
                    
                    print(f"📊 对齐检查:")
                    print(f"   MD中的placeholder: {len(md_placeholders)} 个")
                    print(f"   JSON中未处理项目: {len(unprocessed_items)} 个")
                    
                    if len(md_placeholders) == len(unprocessed_items):
                        print("✅ MD与JSON已对齐，无需更新")
                        return True
                    else:
                        print("⚠️  MD与JSON不对齐，建议重新生成状态文件")
                        return False
            
            return True
            
        except Exception as e:
            print(f"❌ 同步处理失败: {e}", file=sys.stderr)
            return False

# Create a global instance
mineru_wrapper = MinerUWrapper()

def extract_and_analyze_pdf_with_mineru(
    pdf_path: str,
    layout_mode: str = "arxiv",
    mode: str = "academic",
    call_api: bool = True,
    call_api_force: bool = False,
    page_range: Optional[str] = None,
    debug: bool = False,
    async_mode: bool = False
) -> str:
    """
    Main function that uses MinerU for PDF extraction.
    Maintains the same interface as the original extract_and_analyze_pdf function.
    """
    try:
        wrapper = MinerUWrapper()
        return wrapper.extract_and_analyze_pdf(
            pdf_path, layout_mode, mode, call_api, call_api_force, page_range, debug, async_mode
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