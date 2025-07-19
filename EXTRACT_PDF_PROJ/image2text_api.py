#!/usr/bin/env python3
"""
image2text_api.py - Compatibility wrapper for IMG2TEXT tool
This is a compatibility layer to maintain backward compatibility with existing code
"""

import subprocess
import json
import sys
from pathlib import Path

def get_image_analysis(image_path, mode="academic"):
    """
    Get image analysis using IMG2TEXT tool
    
    Args:
        image_path: Path to the image file
        mode: Analysis mode (academic, general, etc.)
    
    Returns:
        str: Image analysis result
    """
    try:
        # Find IMG2TEXT tool
        script_dir = Path(__file__).parent.parent
        img2text_path = script_dir / "IMG2TEXT"
        
        if not img2text_path.exists():
            return "IMG2TEXT tool not available"
        
        # Call IMG2TEXT tool
        cmd = [str(img2text_path), str(image_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            try:
                # Try to parse JSON output
                output_data = json.loads(result.stdout)
                if output_data.get('success'):
                    return output_data.get('description', 'Image analysis completed')
                else:
                    return output_data.get('error', 'Image analysis failed')
            except json.JSONDecodeError:
                # If not JSON, return plain text
                return result.stdout.strip() if result.stdout.strip() else "Image analysis completed"
        else:
            return f"Image analysis failed: {result.stderr}"
            
    except Exception as e:
        return f"Image analysis error: {str(e)}"

# For backward compatibility
def analyze_image(image_path, mode="academic"):
    """Alias for get_image_analysis"""
    return get_image_analysis(image_path, mode) 