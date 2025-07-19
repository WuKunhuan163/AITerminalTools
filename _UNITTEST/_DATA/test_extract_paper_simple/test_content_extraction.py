#!/usr/bin/env python3
"""
Test script to extract and render content from PDFs using existing MinerU output.
Analyzes middle.json files to differentiate between tables and formulas,
then generates appropriate output files.
"""

import os
import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

def find_middle_json_for_pdf(pdf_name: str) -> Optional[str]:
    """Find the middle.json file for a given PDF in formula_test_output"""
    base_name = os.path.splitext(pdf_name)[0]
    
    # Look in formula_test_output directory
    formula_test_dir = "../formula_test_output"
    if not os.path.exists(formula_test_dir):
        return None
    
    # Check different possible locations
    possible_paths = [
        f"{formula_test_dir}/{base_name}/{base_name}/auto/{base_name}_middle.json",
        f"{formula_test_dir}/{base_name}/{base_name}_middle.json",
        f"{formula_test_dir}/{base_name}/auto/{base_name}_middle.json",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, search recursively
    for root, dirs, files in os.walk(formula_test_dir):
        for file in files:
            if file == f"{base_name}_middle.json":
                return os.path.join(root, file)
    
    return None

def analyze_middle_json(middle_json_path: str) -> List[Dict]:
    """Analyze middle.json file to extract content information"""
    try:
        with open(middle_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        content_items = []
        pdf_info = data.get('pdf_info', [])
        
        for page_idx, page_data in enumerate(pdf_info):
            preproc_blocks = page_data.get('preproc_blocks', [])
            
            for block in preproc_blocks:
                block_type = block.get('type', '')
                
                if block_type == 'table':
                    # Extract table HTML
                    for sub_block in block.get('blocks', []):
                        if sub_block.get('type') == 'table_body':
                            for line in sub_block.get('lines', []):
                                for span in line.get('spans', []):
                                    if span.get('type') == 'table' and span.get('html'):
                                        content_items.append({
                                            'type': 'table',
                                            'content': span['html'],
                                            'page': page_idx,
                                            'bbox': span.get('bbox', []),
                                            'image_path': span.get('image_path', '')
                                        })
                
                elif block_type == 'interline_equation':
                    # Extract formula content
                    for line in block.get('lines', []):
                        for span in line.get('spans', []):
                            if span.get('type') == 'interline_equation' and span.get('content'):
                                content_items.append({
                                    'type': 'formula',
                                    'content': span['content'],
                                    'page': page_idx,
                                    'bbox': span.get('bbox', []),
                                    'image_path': span.get('image_path', ''),
                                    'score': span.get('score', 0.0)
                                })
        
        return content_items
        
    except Exception as e:
        print(f"❌ Error analyzing middle.json: {e}")
        return []

def create_table_html(table_html: str, output_path: str) -> bool:
    """Create a standalone HTML file for table content"""
    try:
        # Clean and format the HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Table Content</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .math {{
            font-family: 'Times New Roman', serif;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Extracted Table Content</h1>
        {table_html}
    </div>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"  ✅ Table HTML created: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating table HTML: {e}")
        return False

def create_formula_latex(formula_content: str, output_path: str) -> bool:
    """Create a standalone LaTeX file for formula content"""
    try:
        # Clean the formula content
        formula_clean = formula_content.strip()
        
        latex_content = f"""\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{amsfonts}}
\\usepackage{{mathtools}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}

\\begin{{document}}

\\title{{Extracted Formula Content}}
\\author{{MinerU PDF Extractor}}
\\date{{\\today}}
\\maketitle

\\section{{Mathematical Formula}}

The following formula was extracted from the PDF:

\\begin{{equation}}
{formula_clean}
\\end{{equation}}

\\end{{document}}"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        print(f"  ✅ Formula LaTeX created: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Error creating formula LaTeX: {e}")
        return False

def process_single_pdf(pdf_path: str, base_name: str) -> Dict:
    """Process a single PDF file and generate appropriate output"""
    print(f"\n📄 Processing {pdf_path}")
    
    # Step 1: Find existing middle.json file
    middle_json_path = find_middle_json_for_pdf(pdf_path)
    if not middle_json_path:
        return {
            'pdf': base_name,
            'status': 'failed',
            'error': 'middle.json not found in formula_test_output'
        }
    
    print(f"  📁 Found middle.json: {middle_json_path}")
    
    # Step 2: Analyze content
    content_items = analyze_middle_json(middle_json_path)
    if not content_items:
        return {
            'pdf': base_name,
            'status': 'failed',
            'error': 'No content found in middle.json'
        }
    
    # Step 3: Generate appropriate output files
    results = []
    
    for i, item in enumerate(content_items):
        if item['type'] == 'table':
            # Create HTML file for table
            html_path = f"{base_name}_table_{i+1}.html"
            success = create_table_html(item['content'], html_path)
            results.append({
                'type': 'table',
                'file': html_path,
                'success': success,
                'page': item['page']
            })
            
        elif item['type'] == 'formula':
            # Create LaTeX file for formula
            latex_path = f"{base_name}_formula_{i+1}.tex"
            success = create_formula_latex(item['content'], latex_path)
            results.append({
                'type': 'formula',
                'file': latex_path,
                'success': success,
                'page': item['page'],
                'score': item.get('score', 0.0)
            })
    
    return {
        'pdf': base_name,
        'status': 'success',
        'content_count': len(content_items),
        'results': results
    }

def main():
    """Main function to process all PDF files"""
    print("🚀 Starting content extraction test using existing MinerU output...")
    
    # Find all PDF files in current directory
    pdf_files = []
    for file in os.listdir('.'):
        if file.endswith('.pdf'):
            pdf_files.append(file)
    
    if not pdf_files:
        print("❌ No PDF files found in current directory")
        return
    
    pdf_files.sort()
    print(f"📁 Found {len(pdf_files)} PDF files: {pdf_files}")
    
    # Process each PDF
    all_results = []
    
    for pdf_file in pdf_files:
        base_name = os.path.splitext(pdf_file)[0]
        result = process_single_pdf(pdf_file, base_name)
        all_results.append(result)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 PROCESSING SUMMARY")
    print("="*60)
    
    for result in all_results:
        print(f"\n📄 {result['pdf']}.pdf:")
        if result['status'] == 'failed':
            print(f"  ❌ Status: {result['status']}")
            print(f"  💬 Error: {result['error']}")
        else:
            print(f"  ✅ Status: {result['status']}")
            print(f"  📊 Content items: {result['content_count']}")
            
            for item_result in result['results']:
                if item_result['type'] == 'table':
                    status = "✅" if item_result['success'] else "❌"
                    print(f"    {status} Table → {item_result['file']} (page {item_result['page']})")
                    
                elif item_result['type'] == 'formula':
                    status = "✅" if item_result['success'] else "❌"
                    print(f"    {status} Formula → {item_result['file']} (page {item_result['page']}, score: {item_result.get('score', 0.0):.2f})")
    
    print(f"\n🎉 Processing complete! Generated files are in the current directory.")
    print(f"📄 Tables are saved as HTML files that can be opened in a web browser.")
    print(f"📄 Formulas are saved as LaTeX files that can be compiled separately.")

if __name__ == "__main__":
    main() 