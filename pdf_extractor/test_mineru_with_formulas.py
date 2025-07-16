#!/usr/bin/env python3
"""
Test script for MinerU with formulas and tables enabled on demo1.pdf
"""

import sys
import os
from pathlib import Path
import tempfile
import subprocess

# Add the pdf_extractor directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_mineru_with_formulas():
    """Test MinerU with formulas and tables enabled on demo1.pdf"""
    print("Testing MinerU with formulas and tables enabled on demo1.pdf...")
    
    # Test with demo1.pdf
    test_pdf = "/Users/wukunhuan/.local/bin/pdf_extractor/pdf_extractor_MinerU/demo/pdfs/demo1.pdf"
    
    if not os.path.exists(test_pdf):
        print(f"Test PDF not found: {test_pdf}")
        return
    
    # Create temporary directory for MinerU output
    temp_dir = tempfile.mkdtemp(prefix="mineru_test_")
    
    try:
        print("🔄 Testing MinerU with formulas and tables enabled...")
        
        # Construct MinerU command with formulas and tables enabled
        cmd = [
            "python3",
            "-m", "mineru.cli.client",
            "-p", test_pdf,
            "-o", temp_dir,
            "-s", "4",  # Page 5 (0-indexed)
            "-e", "4",
            "-f", "true",  # Enable formula parsing
            "-t", "true"   # Enable table parsing
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        # Execute MinerU command
        result = subprocess.run(
            cmd,
            cwd="/Users/wukunhuan/.local/bin/pdf_extractor/pdf_extractor_MinerU",
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        if result.returncode == 0:
            print("✅ MinerU with formulas and tables test successful!")
            
            # Check for output files
            output_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.md'):
                        output_files.append(os.path.join(root, file))
            
            print(f"📄 Output files found: {len(output_files)}")
            for file in output_files:
                print(f"  - {file}")
                
        else:
            print("❌ MinerU with formulas and tables test failed!")
            
    except subprocess.TimeoutExpired:
        print("❌ MinerU test timed out!")
    except Exception as e:
        print(f"❌ MinerU test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_mineru_with_formulas() 