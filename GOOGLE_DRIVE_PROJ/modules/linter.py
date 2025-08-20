#!/usr/bin/env python3
"""
GDS Linter - Multi-language syntax and style checker
Supports Python, JavaScript, Java, C++, and more
"""

import os
import sys
import subprocess
import json
import tempfile
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class GDSLinter:
    """Multi-language linter for GDS file operations"""
    
    # Language detection by file extension
    LANGUAGE_MAP = {
        '.py': 'python',
        '.js': 'javascript', 
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.cc': 'cpp', 
        '.cxx': 'cpp',
        '.c': 'c',
        '.h': 'cpp',
        '.hpp': 'cpp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.sh': 'bash',
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css'
    }
    
    def __init__(self):
        self.supported_linters = self._detect_available_linters()
    
    def _detect_available_linters(self) -> Dict[str, str]:
        """Detect which linters are available on the system"""
        linters = {}
        
        # Python linters
        python_linter_found = False
        for linter in ['flake8', 'pylint', 'pycodestyle']:
            if self._command_exists(linter):
                linters['python'] = linter
                python_linter_found = True
                break
        
        # Fallback to built-in Python syntax checking if no external linter found
        if not python_linter_found and self._command_exists('python3'):
            linters['python'] = 'python3'
        
        # JavaScript/TypeScript linters
        for linter in ['eslint', 'jshint']:
            if self._command_exists(linter):
                linters['javascript'] = linter
                linters['typescript'] = linter
                break
        
        # Java linters
        if self._command_exists('checkstyle'):
            linters['java'] = 'checkstyle'
        elif self._command_exists('javac'):
            linters['java'] = 'javac'
        
        # C++ linters
        cpp_linter_found = False
        for linter in ['cppcheck', 'clang-tidy']:
            if self._command_exists(linter):
                linters['cpp'] = linter
                linters['c'] = linter
                cpp_linter_found = True
                break
        
        if not cpp_linter_found and self._command_exists('gcc'):
            linters['cpp'] = 'gcc'
            linters['c'] = 'gcc'
        
        # Go linter
        if self._command_exists('gofmt'):
            linters['go'] = 'gofmt'
        
        # JSON linter
        if self._command_exists('jsonlint'):
            linters['json'] = 'jsonlint'
        elif self._command_exists('python3'):
            linters['json'] = 'python-json'
        
        # YAML linter
        if self._command_exists('yamllint'):
            linters['yaml'] = 'yamllint'
        
        # Shell linter
        if self._command_exists('shellcheck'):
            linters['bash'] = 'shellcheck'
        
        return linters
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def detect_language(self, filename: str, language: Optional[str] = None) -> str:
        """Detect language from filename or use provided language"""
        if language:
            return language.lower()
        
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        
        return self.LANGUAGE_MAP.get(extension, 'unknown')
    
    def lint_content(self, content: str, filename: str, language: Optional[str] = None) -> Dict:
        """
        Lint content and return results
        
        Args:
            content: File content to lint
            filename: Original filename for context
            language: Language override (optional)
            
        Returns:
            Dict with success, errors, warnings, and info
        """
        detected_language = self.detect_language(filename, language)
        
        if detected_language == 'unknown':
            return {
                "success": True,
                "language": detected_language,
                "message": f"Language not detected for {filename}, skipping linting",
                "errors": [],
                "warnings": [],
                "info": []
            }
        
        if detected_language not in self.supported_linters:
            return {
                "success": True, 
                "language": detected_language,
                "message": f"No linter available for {detected_language}",
                "errors": [],
                "warnings": [],
                "info": [f"Install a {detected_language} linter for better checking"]
            }
        
        linter = self.supported_linters[detected_language]
        return self._run_linter(content, filename, detected_language, linter)
    
    def _run_linter(self, content: str, filename: str, language: str, linter: str) -> Dict:
        """Run the specific linter on content"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix=Path(filename).suffix, delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                if language == 'python':
                    return self._lint_python(tmp_file_path, linter)
                elif language in ['javascript', 'typescript']:
                    return self._lint_javascript(tmp_file_path, linter)
                elif language == 'java':
                    return self._lint_java(tmp_file_path, linter)
                elif language in ['cpp', 'c']:
                    return self._lint_cpp(tmp_file_path, linter)
                elif language == 'go':
                    return self._lint_go(tmp_file_path, linter)
                elif language == 'json':
                    return self._lint_json(tmp_file_path, linter)
                elif language == 'yaml':
                    return self._lint_yaml(tmp_file_path, linter)
                elif language == 'bash':
                    return self._lint_bash(tmp_file_path, linter)
                else:
                    return self._generic_lint_result(language, "Linter not implemented")
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            return {
                "success": False,
                "language": language,
                "message": f"Linting failed: {str(e)}",
                "errors": [f"Linter error: {str(e)}"],
                "warnings": [],
                "info": []
            }
    
    def _lint_python(self, file_path: str, linter: str) -> Dict:
        """Lint Python code"""
        try:
            if linter == 'flake8':
                result = subprocess.run(['flake8', '--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'pylint':
                result = subprocess.run(['pylint', '--output-format=text', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'pycodestyle':
                result = subprocess.run(['pycodestyle', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'python3':
                # Built-in Python syntax check
                result = subprocess.run(['python3', '-m', 'py_compile', file_path], 
                                      capture_output=True, text=True)
            else:
                # Unknown linter fallback: basic Python syntax check
                result = subprocess.run(['python3', '-m', 'py_compile', file_path], 
                                      capture_output=True, text=True)
            
            return self._parse_python_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('python', f"Python linting failed: {e}")
    
    def _lint_javascript(self, file_path: str, linter: str) -> Dict:
        """Lint JavaScript/TypeScript code"""
        try:
            if linter == 'eslint':
                result = subprocess.run(['eslint', '--format=compact', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'jshint':
                result = subprocess.run(['jshint', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('javascript', "No JavaScript linter available")
            
            return self._parse_javascript_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('javascript', f"JavaScript linting failed: {e}")
    
    def _lint_java(self, file_path: str, linter: str) -> Dict:
        """Lint Java code"""
        try:
            if linter == 'javac':
                result = subprocess.run(['javac', '-Xlint', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('java', "Java linting not fully implemented")
            
            return self._parse_java_output(result)
            
        except Exception as e:
            return self._generic_lint_result('java', f"Java linting failed: {e}")
    
    def _lint_cpp(self, file_path: str, linter: str) -> Dict:
        """Lint C++ code"""
        try:
            if linter == 'cppcheck':
                result = subprocess.run(['cppcheck', '--enable=all', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'gcc':
                result = subprocess.run(['gcc', '-Wall', '-Wextra', '-fsyntax-only', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('cpp', "C++ linting not available")
            
            return self._parse_cpp_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('cpp', f"C++ linting failed: {e}")
    
    def _lint_json(self, file_path: str, linter: str) -> Dict:
        """Lint JSON content"""
        try:
            if linter == 'python-json':
                # Use Python's json module for validation
                with open(file_path, 'r') as f:
                    json.load(f)
                return {
                    "success": True,
                    "language": "json",
                    "message": "JSON is valid",
                    "errors": [],
                    "warnings": [],
                    "info": []
                }
            else:
                result = subprocess.run(['jsonlint', file_path], 
                                      capture_output=True, text=True)
                return self._parse_json_output(result)
                
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "language": "json",
                "message": "JSON syntax error",
                "errors": [f"Line {e.lineno}: {e.msg}"],
                "warnings": [],
                "info": []
            }
        except Exception as e:
            return self._generic_lint_result('json', f"JSON linting failed: {e}")
    
    def _lint_bash(self, file_path: str, linter: str) -> Dict:
        """Lint Bash scripts"""
        try:
            result = subprocess.run(['shellcheck', file_path], 
                                  capture_output=True, text=True)
            return self._parse_shellcheck_output(result)
            
        except Exception as e:
            return self._generic_lint_result('bash', f"Bash linting failed: {e}")
    
    def _parse_python_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse Python linter output"""
        errors = []
        warnings = []
        
        if result.returncode != 0 and result.stderr:
            # Syntax errors
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    errors.append(line.strip())
        
        if result.stdout:
            # Style warnings
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    if any(code in line for code in ['E', 'F']):  # Errors
                        errors.append(line.strip())
                    else:  # Warnings
                        warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "python",
            "message": f"Python linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_javascript_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse JavaScript linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warn' in line.lower():
                    warnings.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "javascript", 
            "message": f"JavaScript linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _generic_lint_result(self, language: str, message: str) -> Dict:
        """Generic lint result for unsupported cases"""
        return {
            "success": True,
            "language": language,
            "message": message,
            "errors": [],
            "warnings": [],
            "info": [message]
        }


def main():
    """Command line interface for GDS linter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GDS Multi-language Linter')
    parser.add_argument('file', help='File to lint')
    parser.add_argument('--language', '-l', help='Language override')
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found")
        sys.exit(1)
    
    linter = GDSLinter()
    
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(args.file, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    
    result = linter.lint_content(content, args.file, args.language)
    
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Text format
        print(f"Language: {result['language']}")
        print(f"Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")
        print(f"Message: {result['message']}")
        
        if result['errors']:
            print("\n🚫 Errors:")
            for error in result['errors']:
                print(f"  • {error}")
        
        if result['warnings']:
            print("\n⚠️  Warnings:")
            for warning in result['warnings']:
                print(f"  • {warning}")
        
        if result['info']:
            print("\nℹ️  Info:")
            for info in result['info']:
                print(f"  • {info}")


if __name__ == '__main__':
    main()
