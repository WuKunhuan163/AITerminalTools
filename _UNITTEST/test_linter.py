#!/usr/bin/env python3
"""
Comprehensive unit tests for LINTER tool
Tests multi-language linting functionality and integration
"""

import unittest
import subprocess
import tempfile
import os
import sys
import json
from pathlib import Path

# Add parent directory to path to import LINTER
sys.path.insert(0, str(Path(__file__).parent.parent))
from LINTER import MultiLanguageLinter


class TestLinterTool(unittest.TestCase):
    """Test the LINTER tool functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.linter = MultiLanguageLinter()
        self.test_dir = Path(__file__).parent.parent
        self.linter_path = self.test_dir / "LINTER.py"
        
    def test_01_linter_exists(self):
        """Test that LINTER.py exists and is executable"""
        self.assertTrue(self.linter_path.exists(), "LINTER.py should exist")
        self.assertTrue(os.access(self.linter_path, os.X_OK), "LINTER.py should be executable")
        
    def test_02_language_detection(self):
        """Test automatic language detection from file extensions"""
        test_cases = [
            ("test.py", "python"),
            ("script.js", "javascript"),
            ("app.jsx", "javascript"),
            ("component.ts", "typescript"),
            ("Main.java", "java"),
            ("program.cpp", "cpp"),
            ("header.h", "cpp"),
            ("config.json", "json"),
            ("data.yaml", "yaml"),
            ("script.sh", "bash"),
            ("query.sql", "sql"),
            ("script.rb", "ruby"),
            ("app.php", "php"),
            ("script.pl", "perl"),
            ("game.lua", "lua"),
            ("App.kt", "kotlin"),
            ("ViewController.swift", "swift"),
            ("Main.scala", "scala"),
            ("unknown.xyz", "unknown")
        ]
        
        for filename, expected_lang in test_cases:
            with self.subTest(filename=filename):
                detected = self.linter.detect_language(filename)
                self.assertEqual(detected, expected_lang, 
                               f"Expected {expected_lang} for {filename}, got {detected}")
    
    def test_03_language_override(self):
        """Test manual language specification override"""
        result = self.linter.detect_language("test.txt", "python")
        self.assertEqual(result, "python", "Language override should work")
        
    def test_04_python_linting_errors(self):
        """Test Python linting with actual errors"""
        python_code_with_errors = '''import os, sys
import json
import unused_module

def bad_function(x,y):
    result=x+y
    if result>10:
        print(f"big")
    return result

unused_var = "never used"
'''
        
        result = self.linter.lint_content(python_code_with_errors, "test.py")
        
        self.assertFalse(result['success'], "Should detect errors")
        self.assertEqual(result['language'], 'python')
        self.assertGreater(len(result['errors']), 0, "Should have errors")
        
        # Check for specific error types
        errors_text = '\n'.join(result['errors'])
        self.assertIn('F401', errors_text, "Should detect unused imports")
        self.assertIn('E401', errors_text, "Should detect multiple imports on one line")
        self.assertIn('E225', errors_text, "Should detect missing whitespace around operators")
    
    def test_05_python_linting_clean(self):
        """Test Python linting with clean code"""
        clean_python_code = '''#!/usr/bin/env python3
"""Clean Python module"""


def add_numbers(x, y):
    """Add two numbers together"""
    return x + y


def main():
    """Main function"""
    result = add_numbers(5, 3)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
'''
        
        result = self.linter.lint_content(clean_python_code, "clean.py")
        
        self.assertTrue(result['success'], "Clean code should pass")
        self.assertEqual(len(result['errors']), 0, "Should have no errors")
        self.assertEqual(len(result['warnings']), 0, "Should have no warnings")
    
    def test_06_json_linting_valid(self):
        """Test JSON linting with valid JSON"""
        valid_json = '''{
    "name": "test",
    "value": 123,
    "items": ["a", "b", "c"],
    "nested": {
        "key": "value"
    }
}'''
        
        result = self.linter.lint_content(valid_json, "test.json")
        
        self.assertTrue(result['success'], "Valid JSON should pass")
        self.assertEqual(result['language'], 'json')
        self.assertEqual(len(result['errors']), 0, "Should have no errors")
    
    def test_07_json_linting_invalid(self):
        """Test JSON linting with invalid JSON"""
        invalid_json = '''{
    "name": "test",
    "value": 123,
    "items": [
        "a",
        "b"
        "c"
    ]
}'''
        
        result = self.linter.lint_content(invalid_json, "invalid.json")
        
        self.assertFalse(result['success'], "Invalid JSON should fail")
        self.assertEqual(result['language'], 'json')
        self.assertGreater(len(result['errors']), 0, "Should have errors")
    
    def test_08_cpp_linting(self):
        """Test C++ linting functionality"""
        cpp_code_with_errors = '''#include <iostream>

int main() {
    int x = 5
    int y = 10;
    
    if (x > y) {
        std::cout << "x is greater" << std::endl;
    }
    
    return 0
}'''
        
        result = self.linter.lint_content(cpp_code_with_errors, "test.cpp")
        
        # Should detect the language as cpp
        self.assertEqual(result['language'], 'cpp')
        
        # If gcc is available, should detect syntax errors
        if 'cpp' in self.linter.supported_linters:
            self.assertFalse(result['success'], "Should detect syntax errors")
            self.assertGreater(len(result['errors']), 0, "Should have syntax errors")
    
    def test_09_unknown_language(self):
        """Test handling of unknown file types"""
        result = self.linter.lint_content("some content", "test.unknown")
        
        self.assertTrue(result['success'], "Unknown languages should not fail")
        self.assertEqual(result['language'], 'unknown')
        self.assertIn("Language not detected", result['message'])
    
    def test_10_cli_help(self):
        """Test command line help functionality"""
        result = subprocess.run([str(self.linter_path), "--help"], 
                              capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, "Help should exit with code 0")
        self.assertIn("LINTER", result.stdout, "Help should mention LINTER")
        self.assertIn("usage", result.stdout.lower(), "Help should show usage")
    
    def test_11_cli_version(self):
        """Test command line version functionality"""
        result = subprocess.run([str(self.linter_path), "--version"], 
                              capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, "Version should exit with code 0")
        self.assertIn("LINTER", result.stdout, "Version should mention LINTER")
    
    def test_12_cli_file_not_found(self):
        """Test CLI behavior with non-existent file"""
        result = subprocess.run([str(self.linter_path), "nonexistent.py"], 
                              capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 1, "Should exit with error code")
        self.assertIn("not found", result.stderr, "Should report file not found")
    
    def test_13_cli_json_output(self):
        """Test JSON output format"""
        # Create a temporary file with errors
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('import os\nimport sys\nprint(f"hello")')
            temp_file = f.name
        
        try:
            result = subprocess.run([str(self.linter_path), temp_file, "--format", "json"], 
                                  capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 1, "Should exit with error code for errors")
            
            # Parse JSON output
            output_data = json.loads(result.stdout)
            
            self.assertIn('success', output_data)
            self.assertIn('language', output_data)
            self.assertIn('errors', output_data)
            self.assertIn('warnings', output_data)
            self.assertEqual(output_data['language'], 'python')
            
        finally:
            os.unlink(temp_file)
    
    def test_14_cli_language_override(self):
        """Test manual language specification via CLI"""
        # Create a file without extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
            f.write('print(f"hello world")')
            temp_file = f.name
        
        try:
            result = subprocess.run([str(self.linter_path), temp_file, "--language", "python"], 
                                  capture_output=True, text=True)
            
            # Should be able to lint as Python
            self.assertIn("Language: python", result.stdout)
            
        finally:
            os.unlink(temp_file)
    
    def test_15_linter_availability_detection(self):
        """Test that linter availability detection works"""
        available_linters = self.linter.supported_linters
        
        self.assertIsInstance(available_linters, dict)
        
        # Python should always be available (using built-in py_compile)
        self.assertIn('python', available_linters, "Python linting should be available")
        
        # JSON should be available (using built-in json module)
        self.assertIn('json', available_linters, "JSON validation should be available")
    
    def test_16_multiple_errors_categorization(self):
        """Test that errors and warnings are properly categorized"""
        python_code_mixed = '''import os
import sys

def test():
    x=1+2  # Missing spaces
    unused_var = "test"  # Unused variable
    return x

# Missing blank lines
test()
'''
        
        result = self.linter.lint_content(python_code_mixed, "mixed.py")
        
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0, "Should have errors")
        
        # Check that different error types are detected
        all_issues = result['errors'] + result['warnings']
        issues_text = '\n'.join(all_issues)
        
        # Should detect various issue types
        self.assertTrue(any('F401' in issue for issue in all_issues), "Should detect unused imports")
        self.assertTrue(any('E225' in issue or 'E302' in issue for issue in all_issues), "Should detect style issues")
    
    def test_17_file_reading_edge_cases(self):
        """Test file reading with different encodings"""
        # Test with a simple ASCII file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write('print(f"hello")\n')
            temp_file = f.name
        
        try:
            result = self.linter.lint_file(temp_file)
            self.assertEqual(result['language'], 'python')
            
        finally:
            os.unlink(temp_file)
    
    def test_18_integration_with_gds_format(self):
        """Test that the linter output format matches GDS edit requirements"""
        python_code_with_errors = '''import os
def test(x,y):
    return x+y
'''
        
        # Simulate the _run_linter_on_content method
        result = self.linter.lint_content(python_code_with_errors, "test.py")
        
        if result['errors'] or result['warnings']:
            # Format like GDS edit command expects
            lines = []
            for error in result['errors']:
                lines.append(f"ERROR: {error}")
            for warning in result['warnings']:
                lines.append(f"WARNING: {warning}")
            
            formatted_output = '\n'.join(lines)
            
            # Should have ERROR: and WARNING: prefixes
            self.assertTrue(any(line.startswith('ERROR:') for line in lines if 'F401' in line))
            self.assertTrue(any(line.startswith('ERROR:') for line in lines if 'E' in line))
    
    def test_19_ruby_language_detection(self):
        """Test Ruby language detection and basic linting"""
        ruby_code = '''puts "Hello, World!"
def greet(name)
  puts "Hello, #{name}!"
end
greet("Ruby")'''
        
        result = self.linter.lint_content(ruby_code, "test.rb")
        self.assertEqual(result['language'], 'ruby')
    
    def test_20_php_language_detection(self):
        """Test PHP language detection and basic linting"""
        php_code = '''<?php
echo "Hello, World!";
function greet($name) {
    echo "Hello, " . $name . "!";
}
greet("PHP");
?>'''
        
        result = self.linter.lint_content(php_code, "test.php")
        self.assertEqual(result['language'], 'php')
    
    def test_21_perl_language_detection(self):
        """Test Perl language detection and basic linting"""
        perl_code = '''#!/usr/bin/perl
use strict;
use warnings;

print "Hello, World!\\n";

sub greet {
    my $name = shift;
    print "Hello, $name!\\n";
}

greet("Perl");'''
        
        result = self.linter.lint_content(perl_code, "test.pl")
        self.assertEqual(result['language'], 'perl')
    
    def test_22_lua_language_detection(self):
        """Test Lua language detection and basic linting"""
        lua_code = '''print(f"Hello, World!")

function greet(name)
    print(f"Hello, " .. name .. "!")
end

greet("Lua")'''
        
        result = self.linter.lint_content(lua_code, "test.lua")
        self.assertEqual(result['language'], 'lua')
    
    def test_23_kotlin_language_detection(self):
        """Test Kotlin language detection and basic linting"""
        kotlin_code = '''fun main() {
    println("Hello, World!")
    greet("Kotlin")
}

fun greet(name: String) {
    println("Hello, $name!")
}'''
        
        result = self.linter.lint_content(kotlin_code, "test.kt")
        self.assertEqual(result['language'], 'kotlin')
    
    def test_24_swift_language_detection(self):
        """Test Swift language detection and basic linting"""
        swift_code = '''import Foundation

print(f"Hello, World!")

func greet(name: String) {
    print(f"Hello, \\(name)!")
}

greet(name: "Swift")'''
        
        result = self.linter.lint_content(swift_code, "test.swift")
        self.assertEqual(result['language'], 'swift')
    
    def test_25_scala_language_detection(self):
        """Test Scala language detection and basic linting"""
        scala_code = '''object Main {
  def main(args: Array[String]): Unit = {
    println("Hello, World!")
    greet("Scala")
  }
  
  def greet(name: String): Unit = {
    println(s"Hello, $name!")
  }
}'''
        
        result = self.linter.lint_content(scala_code, "test.scala")
        self.assertEqual(result['language'], 'scala')
    
    def test_26_extended_language_support(self):
        """Test that all new languages are properly supported"""
        new_languages = ['ruby', 'php', 'perl', 'lua', 'kotlin', 'swift', 'scala']
        
        for lang in new_languages:
            with self.subTest(language=lang):
                # Test that the language is in the language map
                extensions = [ext for ext, detected_lang in self.linter.LANGUAGE_MAP.items() if detected_lang == lang]
                self.assertGreater(len(extensions), 0, f"Language {lang} should have at least one file extension")
                
                # Test basic content linting (should not crash)
                result = self.linter.lint_content("# test content", f"test{extensions[0]}")
                self.assertIn('language', result)
                self.assertEqual(result['language'], lang)


class TestLinterIntegration(unittest.TestCase):
    """Test LINTER integration with other tools"""
    
    def test_01_run_compatibility(self):
        """Test RUN tool compatibility"""
        linter_path = Path(__file__).parent.parent / "LINTER.py"
        
        # Test basic RUN compatibility
        result = subprocess.run(["python3", str(linter_path), "--help"], 
                              capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, "Should work with python3 execution")
    
    def test_02_binary_symlink(self):
        """Test that LINTER binary symlink works"""
        linter_binary = Path(__file__).parent.parent / "LINTER"
        
        if linter_binary.exists():
            result = subprocess.run([str(linter_binary), "--help"], 
                                  capture_output=True, text=True)
            
            self.assertEqual(result.returncode, 0, "Binary symlink should work")


def run_comprehensive_tests():
    """Run all linter tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLinterTool))
    suite.addTests(loader.loadTestsFromTestCase(TestLinterIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Return summary
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100 if result.testsRun > 0 else 0,
        "success": len(result.failures) == 0 and len(result.errors) == 0
    }


if __name__ == "__main__":
    print(f"Running LINTER comprehensive tests...")
    print(f"=" * 60)
    
    results = run_comprehensive_tests()
    
    print(f"\n" + "=" * 60)
    print(f"TEST SUMMARY")
    print(f"=" * 60)
    print(f"Tests run: {results['tests_run']}")
    print(f"Failures: {results['failures']}")
    print(f"Errors: {results['errors']}")
    print(f"Success rate: {results['success_rate']:.1f}%")
    print(f"Overall result: {'PASS' if results['success'] else 'FAIL'}")
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)
