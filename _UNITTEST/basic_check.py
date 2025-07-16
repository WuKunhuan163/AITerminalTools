#!/usr/bin/env python3
"""
Basic check script to verify tools exist
"""

import sys
import os
from pathlib import Path

def check_files():
    """Check if all required files exist"""
    print("Checking file existence...")
    
    base_dir = Path(__file__).parent.parent
    
    tools = ['OVERLEAF', 'EXTRACT_PDF', 'GOOGLE_DRIVE', 'SEARCH_PAPER', 
             'EXPORT', 'DOWNLOAD', 'RUN', 'USERINPUT']
    
    all_good = True
    
    for tool in tools:
        py_file = base_dir / f"{tool}.py"
        sh_file = base_dir / tool
        md_file = base_dir / f"{tool}.md"
        
        py_exists = py_file.exists()
        sh_exists = sh_file.exists()
        md_exists = md_file.exists()
        
        print(f"{tool}: py={py_exists}, sh={sh_exists}, md={md_exists}")
        
        if not (py_exists and sh_exists and md_exists):
            all_good = False
    
    return all_good

def check_bin_json():
    """Check _bin.json"""
    print("\nChecking _bin.json...")
    
    base_dir = Path(__file__).parent.parent
    bin_json = base_dir / '_bin.json'
    
    if not bin_json.exists():
        print("❌ _bin.json not found")
        return False
    
    try:
        import json
        with open(bin_json, 'r') as f:
            data = json.load(f)
        
        print(f"✅ _bin.json loaded with {len(data)} tools")
        return True
    except Exception as e:
        print(f"❌ Error loading _bin.json: {e}")
        return False

def check_imports():
    """Check if we can import the test module"""
    print("\nChecking imports...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from _UNITTEST._TEST import BinToolsIntegrationTest
        print("✅ Can import BinToolsIntegrationTest")
        return True
    except Exception as e:
        print(f"❌ Cannot import test module: {e}")
        return False

def main():
    """Main check function"""
    print("="*50)
    print("BASIC SYSTEM CHECK")
    print("="*50)
    
    files_ok = check_files()
    json_ok = check_bin_json()
    imports_ok = check_imports()
    
    print(f"\n{'='*50}")
    print("RESULTS")
    print('='*50)
    print(f"Files: {'✅' if files_ok else '❌'}")
    print(f"JSON: {'✅' if json_ok else '❌'}")
    print(f"Imports: {'✅' if imports_ok else '❌'}")
    
    all_ok = files_ok and json_ok and imports_ok
    print(f"Overall: {'✅ READY' if all_ok else '❌ ISSUES'}")
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main()) 