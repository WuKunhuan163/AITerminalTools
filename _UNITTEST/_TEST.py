#!/usr/bin/env python3
"""
_TEST.py - Universal Test Runner for Binary Tools
Automatically discovers and runs all test_ files, manages test_passed status in AI_TOOL.json
"""

import os
import sys
import json
import subprocess
import argparse
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class BinToolsIntegrationTest(unittest.TestCase):
    """Compatibility class for old test files that expect BinToolsIntegrationTest"""
    
    def test_09_export(self):
        """Test EXPORT tool"""
        result = subprocess.run([sys.executable, "test_export.py"], 
                               capture_output=True, text=True, cwd=Path(__file__).parent)
        self.assertEqual(result.returncode, 0, f"EXPORT test failed: {result.stderr}")
    
    def test_07_google_drive(self):
        """Test GOOGLE_DRIVE tool"""
        result = subprocess.run([sys.executable, "test_google_drive.py"], 
                               capture_output=True, text=True, cwd=Path(__file__).parent)
        self.assertEqual(result.returncode, 0, f"GOOGLE_DRIVE test failed: {result.stderr}")
    
    def test_05_overleaf_compilation(self):
        """Test OVERLEAF tool"""
        result = subprocess.run([sys.executable, "test_overleaf.py"], 
                               capture_output=True, text=True, cwd=Path(__file__).parent)
        self.assertEqual(result.returncode, 0, f"OVERLEAF test failed: {result.stderr}")
    
    def test_08_search_paper(self):
        """Test SEARCH_PAPER tool"""
        result = subprocess.run([sys.executable, "test_search_paper.py"], 
                               capture_output=True, text=True, cwd=Path(__file__).parent)
        self.assertEqual(result.returncode, 0, f"SEARCH_PAPER test failed: {result.stderr}")
    
    def test_10_download(self):
        """Test DOWNLOAD tool"""
        result = subprocess.run([sys.executable, "test_download.py"], 
                               capture_output=True, text=True, cwd=Path(__file__).parent)
        self.assertEqual(result.returncode, 0, f"DOWNLOAD test failed: {result.stderr}")


class TestRunner:
    """Universal test runner for binary tools"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.bin_dir = self.test_dir.parent
        self.bin_json_path = self.bin_dir / "AI_TOOL.json"
        
        # Load AI_TOOL.json
        self.bin_data = self.load_bin_json()
        
        # Discover test files
        self.test_files = self.discover_test_files()
        
        # Map tools to test files
        self.tool_test_mapping = self.create_tool_test_mapping()
    
    def load_bin_json(self) -> Dict:
        """Load AI_TOOL.json file"""
        try:
            with open(self.bin_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading AI_TOOL.json: {e}")
            sys.exit(1)
    
    def save_bin_json(self) -> bool:
        """Save AI_TOOL.json file"""
        try:
            with open(self.bin_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.bin_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving AI_TOOL.json: {e}")
            return False
    
    def discover_test_files(self) -> List[Path]:
        """Discover all test_ files in the _UNITTEST directory"""
        test_files = []
        for file_path in self.test_dir.glob("test_*.py"):
            if file_path.name != "test_current_tools.py":  # Skip meta test file
                test_files.append(file_path)
        
        return sorted(test_files)
    
    def create_tool_test_mapping(self) -> Dict[str, List[Path]]:
        """Create mapping from tool names to their test files"""
        mapping = {}
        
        for test_file in self.test_files:
            # Extract tool name from test file name
            # e.g., test_google_drive.py -> GOOGLE_DRIVE
            test_name = test_file.stem  # Remove .py extension
            
            if test_name.startswith("test_"):
                tool_part = test_name[5:]  # Remove "test_" prefix
                
                # Convert to uppercase and handle special cases
                if tool_part == "google_drive":
                    tool_name = "GOOGLE_DRIVE"
                elif tool_part == "export_google_drive":
                    tool_name = "EXPORT"  # Special case for export test
                elif tool_part in ["export_only", "download_only"]:
                    continue  # Skip utility test files
                else:
                    tool_name = tool_part.upper()
                
                # Check if tool exists in AI_TOOL.json
                if tool_name in self.bin_data.get("tools", {}):
                    if tool_name not in mapping:
                        mapping[tool_name] = []
                    mapping[tool_name].append(test_file)
                else:
                    print(f"⚠️  Warning: Test file {test_file.name} doesn't match any tool in AI_TOOL.json")
        
        return mapping
    
    def get_available_tools(self) -> List[str]:
        """Get list of tools that have test files"""
        return sorted(self.tool_test_mapping.keys())
    
    def reset_test_status(self, tools: List[str]) -> None:
        """Reset test_passed to false for specified tools"""
        for tool_name in tools:
            if tool_name in self.bin_data["tools"]:
                self.bin_data["tools"][tool_name]["test_passed"] = False
                print(f"🔄 Reset {tool_name} test_passed to false")
    
    def set_test_passed(self, tool_name: str, passed: bool) -> None:
        """Set test_passed status for a tool"""
        if tool_name in self.bin_data["tools"]:
            self.bin_data["tools"][tool_name]["test_passed"] = passed
            status = "✅ true" if passed else "❌ false"
            print(f"📝 Set {tool_name} test_passed to {status}")
    
    def run_test_file(self, test_file: Path) -> Tuple[bool, str, str]:
        """Run a single test file and return (success, stdout, stderr)"""
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout per test file
                cwd=self.bin_dir  # Run from bin directory
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Test timed out after 2 minutes"
        except Exception as e:
            return False, "", f"Error running test: {e}"
    
    def run_tool_tests(self, tool_name: str, verbose: bool = False) -> bool:
        """Run all tests for a specific tool"""
        if tool_name not in self.tool_test_mapping:
            print(f"❌ No test files found for tool: {tool_name}")
            return False
        
        test_files = self.tool_test_mapping[tool_name]
        print(f"\n🧪 Testing {tool_name} ({len(test_files)} test file(s))")
        print("=" * 50)
        
        all_passed = True
        
        for test_file in test_files:
            print(f"📋 Running {test_file.name}...")
            
            success, stdout, stderr = self.run_test_file(test_file)
            
            if success:
                print(f"✅ {test_file.name} PASSED")
                if verbose and stdout:
                    print(f"📝 Output:\n{stdout}")
            else:
                print(f"❌ {test_file.name} FAILED")
                all_passed = False
                
                if stderr:
                    print(f"💥 Error:\n{stderr}")
                if stdout and verbose:
                    print(f"📝 Output:\n{stdout}")
        
        return all_passed
    
    def run_tests(self, tools: Optional[List[str]] = None, verbose: bool = False) -> Dict[str, bool]:
        """Run tests for specified tools (or all tools if None)"""
        if tools is None:
            tools = self.get_available_tools()
        else:
            # Validate tool names
            available_tools = self.get_available_tools()
            invalid_tools = [t for t in tools if t not in available_tools]
            if invalid_tools:
                print(f"❌ Invalid tool names: {', '.join(invalid_tools)}")
                print(f"Available tools: {', '.join(available_tools)}")
                return {}
        
        print(f"🚀 Starting test run for {len(tools)} tool(s)")
        print(f"Tools to test: {', '.join(tools)}")
        
        # Reset test status for all tools being tested
        self.reset_test_status(tools)
        self.save_bin_json()
        
        results = {}
        start_time = time.time()
        
        for tool_name in tools:
            tool_passed = self.run_tool_tests(tool_name, verbose)
            results[tool_name] = tool_passed
            
            # Update test_passed status
            self.set_test_passed(tool_name, tool_passed)
        
        # Save final results
        self.save_bin_json()
        
        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed_count = sum(1 for passed in results.values() if passed)
        total_count = len(results)
        
        for tool_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{tool_name:20} {status}")
        
        print("-" * 60)
        print(f"Total: {passed_count}/{total_count} tools passed")
        print(f"Duration: {duration:.2f} seconds")
        
        if passed_count == total_count:
            print("🎉 All tests passed!")
        else:
            print(f"💔 {total_count - passed_count} tool(s) failed")
        
        return results
    
    def list_tools(self) -> None:
        """List all available tools and their test files"""
        print("📋 Available Tools and Test Files:")
        print("=" * 50)
        
        for tool_name in sorted(self.tool_test_mapping.keys()):
            test_files = self.tool_test_mapping[tool_name]
            current_status = self.bin_data["tools"][tool_name].get("test_passed", False)
            status_icon = "✅" if current_status else "❌"
            
            print(f"{status_icon} {tool_name}")
            for test_file in test_files:
                print(f"    📄 {test_file.name}")
        
        print(f"\nTotal: {len(self.tool_test_mapping)} tools with tests")
    
    def ensure_test_file_fields(self) -> None:
        """Ensure all tools in AI_TOOL.json have proper test file fields"""
        updated = False
        
        for tool_name, tool_data in self.bin_data["tools"].items():
            # Ensure test_command field exists
            if "test_command" not in tool_data:
                if tool_name in self.tool_test_mapping:
                    # Use the test file
                    test_files = self.tool_test_mapping[tool_name]
                    test_file = test_files[0]  # Use first test file
                    tool_data["test_command"] = [
                        "python",
                        f"_UNITTEST/{test_file.name}"
                    ]
                else:
                    # Use --help as fallback
                    tool_data["test_command"] = ["--help"]
                updated = True
                print(f"📝 Added test_command for {tool_name}")
            
            # Ensure testable field exists
            if "testable" not in tool_data:
                tool_data["testable"] = tool_name in self.tool_test_mapping
                updated = True
                print(f"📝 Set testable={tool_data['testable']} for {tool_name}")
        
        if updated:
            self.save_bin_json()
            print("✅ Updated AI_TOOL.json with test file fields")
        else:
            print("✅ All tools already have proper test file fields")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Universal Test Runner for Binary Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python _TEST.py                           # Run all tests
  python _TEST.py GOOGLE_DRIVE LEARN        # Test specific tools
  python _TEST.py --list                    # List available tools
  python _TEST.py --verbose                 # Run with verbose output
  python _TEST.py --ensure-fields           # Ensure AI_TOOL.json has test fields
        """
    )
    
    parser.add_argument(
        'tools',
        nargs='*',
        help='Specific tools to test (default: all tools)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available tools and their test files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose test output'
    )
    
    parser.add_argument(
        '--ensure-fields',
        action='store_true',
        help='Ensure AI_TOOL.json has proper test file fields'
    )
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    
    # Handle different modes
    if args.list:
        runner.list_tools()
        return 0
    
    if args.ensure_fields:
        runner.ensure_test_file_fields()
        return 0
    
    # Run tests
    tools = args.tools if args.tools else None
    results = runner.run_tests(tools, args.verbose)
    
    # Return appropriate exit code
    if results:
        failed_count = sum(1 for passed in results.values() if not passed)
        return failed_count
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main()) 