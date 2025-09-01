#!/usr/bin/env python3
"""
LINTER.py - Multi-language Syntax and Style Checker
Supports Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, SQL, JSON, YAML, HTML, CSS, Shell scripts
"""

import os
import sys
import subprocess
import json
import tempfile
import argparse
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class MultiLanguageLinter:
    """Multi-language linter for syntax and style checking"""
    
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
        '.css': 'css',
        '.sql': 'sql'
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
        for linter in ['eslint', 'jshint', 'standard']:
            if self._command_exists(linter):
                linters['javascript'] = linter
                linters['typescript'] = linter
                break
        
        # Java linters
        if self._command_exists('checkstyle'):
            linters['java'] = 'checkstyle'
        elif self._command_exists('javac'):
            linters['java'] = 'javac'
        
        # C/C++ linters
        cpp_linter_found = False
        for linter in ['cppcheck', 'clang-tidy']:
            if self._command_exists(linter):
                linters['cpp'] = linter
                linters['c'] = linter
                cpp_linter_found = True
                break
        
        if not cpp_linter_found:
            for compiler in ['gcc', 'clang']:
                if self._command_exists(compiler):
                    linters['cpp'] = compiler
                    linters['c'] = compiler
                    break
        
        # Go linter
        if self._command_exists('golint'):
            linters['go'] = 'golint'
        elif self._command_exists('gofmt'):
            linters['go'] = 'gofmt'
        
        # Rust linter
        if self._command_exists('cargo'):
            linters['rust'] = 'cargo'
        
        # SQL linters
        if self._command_exists('sqlfluff'):
            linters['sql'] = 'sqlfluff'
        elif self._command_exists('sql-formatter'):
            linters['sql'] = 'sql-formatter'
        
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
        
        # HTML linter
        if self._command_exists('htmlhint'):
            linters['html'] = 'htmlhint'
        
        # CSS linter
        if self._command_exists('stylelint'):
            linters['css'] = 'stylelint'
        
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
    
    def lint_file(self, filename: str, language: Optional[str] = None) -> Dict:
        """
        Lint a file and return results
        
        Args:
            filename: Path to file to lint
            language: Language override (optional)
            
        Returns:
            Dict with success, errors, warnings, and info
        """
        if not os.path.exists(filename):
            return {
                "success": False,
                "language": "unknown",
                "message": f"File not found: {filename}",
                "errors": [f"File not found: {filename}"],
                "warnings": [],
                "info": []
            }
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filename, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                return {
                    "success": False,
                    "language": "unknown", 
                    "message": f"Error reading file: {e}",
                    "errors": [f"Error reading file: {e}"],
                    "warnings": [],
                    "info": []
                }
        
        return self.lint_content(content, filename, language)
    
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
                "info": ["Language not detected - use --language to specify"]
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
                elif language == 'rust':
                    return self._lint_rust(tmp_file_path, linter)
                elif language == 'sql':
                    return self._lint_sql(tmp_file_path, linter)
                elif language == 'json':
                    return self._lint_json(tmp_file_path, linter)
                elif language == 'yaml':
                    return self._lint_yaml(tmp_file_path, linter)
                elif language == 'bash':
                    return self._lint_bash(tmp_file_path, linter)
                elif language == 'html':
                    return self._lint_html(tmp_file_path, linter)
                elif language == 'css':
                    return self._lint_css(tmp_file_path, linter)
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
            elif linter == 'standard':
                result = subprocess.run(['standard', file_path], 
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
            elif linter == 'checkstyle':
                result = subprocess.run(['checkstyle', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('java', "Java linting not fully implemented")
            
            return self._parse_java_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('java', f"Java linting failed: {e}")
    
    def _lint_cpp(self, file_path: str, linter: str) -> Dict:
        """Lint C/C++ code"""
        try:
            if linter == 'cppcheck':
                result = subprocess.run(['cppcheck', '--enable=all', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'clang-tidy':
                result = subprocess.run(['clang-tidy', file_path], 
                                      capture_output=True, text=True)
            elif linter in ['gcc', 'clang']:
                result = subprocess.run([linter, '-Wall', '-Wextra', '-fsyntax-only', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('cpp', "C++ linting not available")
            
            return self._parse_cpp_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('cpp', f"C++ linting failed: {e}")
    
    def _lint_go(self, file_path: str, linter: str) -> Dict:
        """Lint Go code"""
        try:
            if linter == 'golint':
                result = subprocess.run(['golint', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'gofmt':
                result = subprocess.run(['gofmt', '-l', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('go', "Go linting not available")
            
            return self._parse_go_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('go', f"Go linting failed: {e}")
    
    def _lint_rust(self, file_path: str, linter: str) -> Dict:
        """Lint Rust code"""
        try:
            if linter == 'cargo':
                result = subprocess.run(['cargo', 'check', '--manifest-path', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('rust', "Rust linting not available")
            
            return self._parse_rust_output(result)
            
        except Exception as e:
            return self._generic_lint_result('rust', f"Rust linting failed: {e}")
    
    def _lint_sql(self, file_path: str, linter: str) -> Dict:
        """Lint SQL code"""
        try:
            if linter == 'sqlfluff':
                result = subprocess.run(['sqlfluff', 'lint', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'sql-formatter':
                result = subprocess.run(['sql-formatter', '--check', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('sql', "SQL linting not available")
            
            return self._parse_sql_output(result, linter)
            
        except Exception as e:
            return self._generic_lint_result('sql', f"SQL linting failed: {e}")
    
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
            elif linter == 'jsonlint':
                result = subprocess.run(['jsonlint', file_path], 
                                      capture_output=True, text=True)
                return self._parse_json_output(result)
            else:
                return self._generic_lint_result('json', "JSON linting not available")
                
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
    
    def _lint_yaml(self, file_path: str, linter: str) -> Dict:
        """Lint YAML content"""
        try:
            if linter == 'yamllint':
                result = subprocess.run(['yamllint', file_path], 
                                      capture_output=True, text=True)
                return self._parse_yaml_output(result)
            else:
                return self._generic_lint_result('yaml', "YAML linting not available")
                
        except Exception as e:
            return self._generic_lint_result('yaml', f"YAML linting failed: {e}")
    
    def _lint_bash(self, file_path: str, linter: str) -> Dict:
        """Lint Bash scripts"""
        try:
            if linter == 'shellcheck':
                result = subprocess.run(['shellcheck', file_path], 
                                      capture_output=True, text=True)
                return self._parse_shellcheck_output(result)
            else:
                return self._generic_lint_result('bash', "Shell linting not available")
            
        except Exception as e:
            return self._generic_lint_result('bash', f"Bash linting failed: {e}")
    
    def _lint_html(self, file_path: str, linter: str) -> Dict:
        """Lint HTML content"""
        try:
            if linter == 'htmlhint':
                result = subprocess.run(['htmlhint', file_path], 
                                      capture_output=True, text=True)
                return self._parse_html_output(result)
            else:
                return self._generic_lint_result('html', "HTML linting not available")
                
        except Exception as e:
            return self._generic_lint_result('html', f"HTML linting failed: {e}")
    
    def _lint_css(self, file_path: str, linter: str) -> Dict:
        """Lint CSS content"""
        try:
            if linter == 'stylelint':
                result = subprocess.run(['stylelint', file_path], 
                                      capture_output=True, text=True)
                return self._parse_css_output(result)
            else:
                return self._generic_lint_result('css', "CSS linting not available")
                
        except Exception as e:
            return self._generic_lint_result('css', f"CSS linting failed: {e}")
    
    # Output parsing methods
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
    
    def _parse_java_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse Java linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "java",
            "message": f"Java linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_cpp_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse C++ linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "cpp",
            "message": f"C++ linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_go_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse Go linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "go",
            "message": f"Go linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_rust_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse Rust linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "rust",
            "message": "Rust linting completed with cargo",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_sql_output(self, result: subprocess.CompletedProcess, linter: str) -> Dict:
        """Parse SQL linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "sql",
            "message": f"SQL linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_json_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse JSON linter output"""
        errors = []
        warnings = []
        
        if result.returncode != 0:
            output = result.stdout + result.stderr
            for line in output.strip().split('\n'):
                if line.strip():
                    errors.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "json",
            "message": "JSON validation completed",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_yaml_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse YAML linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "yaml",
            "message": "YAML linting completed with yamllint",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_shellcheck_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse shellcheck output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "bash",
            "message": "Shell script linting completed with shellcheck",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_html_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse HTML linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "html",
            "message": "HTML linting completed with htmlhint",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_css_output(self, result: subprocess.CompletedProcess) -> Dict:
        """Parse CSS linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                elif 'warning' in line.lower():
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "css",
            "message": "CSS linting completed with stylelint",
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


def is_run_environment(command_identifier=None):
    """Check if running in RUN environment"""
    return bool(os.environ.get('RUN_IDENTIFIER'))


def write_to_json_output(data, command_identifier=None):
    """Write JSON output for RUN environment"""
    if command_identifier and os.environ.get('RUN_DATA_FILE'):
        try:
            with open(os.environ.get('RUN_DATA_FILE'), 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


def main():
    """Command line interface for multi-language linter"""
    parser = argparse.ArgumentParser(
        description='Multi-language Syntax and Style Checker',
        epilog='Supports Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, SQL, JSON, YAML, HTML, CSS, Shell scripts'
    )
    parser.add_argument('file', help='File to lint')
    parser.add_argument('--language', '-l', help='Language override (python, javascript, java, etc.)')
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='text', help='Output format')
    parser.add_argument('--version', '-v', action='version', version='LINTER 1.0.0')
    
    # Check for RUN environment
    args = None
    command_identifier = None
    
    # Handle RUN environment command identifier
    if len(sys.argv) > 1 and is_run_environment(sys.argv[1]):
        command_identifier = sys.argv[1]
        args = parser.parse_args(sys.argv[2:])
    else:
        args = parser.parse_args()
    
    if not os.path.exists(args.file):
        error_msg = f"File not found: {args.file}"
        if is_run_environment(command_identifier):
            write_to_json_output({
                "success": False,
                "error": error_msg
            }, command_identifier)
        else:
            print(f"Error: {error_msg}")
        sys.exit(1)
    
    linter = MultiLanguageLinter()
    result = linter.lint_file(args.file, args.language)
    
    if is_run_environment(command_identifier):
        write_to_json_output(result, command_identifier)
    elif args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Text format without emoji
        print(f"Language: {result['language']}")
        status = "PASS" if result['success'] else "FAIL"
        print(f"Status: {status}")
        print(f"Linter: {result['message']}")
        
        total_issues = len(result['errors']) + len(result['warnings'])
        if total_issues > 0:
            print(f"\n{total_issues} linter warnings or errors found:")
            
            for error in result['errors']:
                print(f"ERROR: {error}")
            
            for warning in result['warnings']:
                print(f"WARNING: {warning}")
        
        if result['info']:
            print(f"\nInfo:")
            for info in result['info']:
                print(f"• {info}")
    
    # Exit with error code if linting failed
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
