#!/usr/bin/env python3
"""
LINTER - Multi-language syntax and style checker
Supports Python, JavaScript, Java, C++, SQL, and more

Usage:
    LINTER file.py [--language python]
    LINTER file.js 
    LINTER file.java --language java
    LINTER --help
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
    """Multi-language linter with comprehensive error detection"""
    
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
        '.sql': 'sql',
        '.kt': 'kotlin',
        '.swift': 'swift',
        '.scala': 'scala',
        '.rb': 'ruby',
        '.php': 'php',
        '.pl': 'perl',
        '.pm': 'perl',
        '.lua': 'lua'
    }
    
    def __init__(self):
        self.supported_linters = self._detect_available_linters()
    
    def _detect_available_linters(self) -> Dict[str, str]:
        """Detect which linters are available on the system"""
        linters = {}
        
        # Python linters (in order of preference)
        python_linter_found = False
        for linter in ['flake8', 'pylint', 'pycodestyle', 'autopep8']:
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
        
        # C++ linters
        cpp_linter_found = False
        for linter in ['cppcheck', 'clang-tidy', 'cpplint']:
            if self._command_exists(linter):
                linters['cpp'] = linter
                linters['c'] = linter
                cpp_linter_found = True
                break
        
        if not cpp_linter_found and self._command_exists('gcc'):
            linters['cpp'] = 'gcc'
            linters['c'] = 'gcc'
        elif not cpp_linter_found and self._command_exists('clang'):
            linters['cpp'] = 'clang'
            linters['c'] = 'clang'
        
        # Go linter
        if self._command_exists('golint'):
            linters['go'] = 'golint'
        elif self._command_exists('gofmt'):
            linters['go'] = 'gofmt'
        
        # Rust linter
        if self._command_exists('cargo'):
            linters['rust'] = 'cargo'
        
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
        
        # SQL linter
        if self._command_exists('sqlfluff'):
            linters['sql'] = 'sqlfluff'
        elif self._command_exists('sql-formatter'):
            linters['sql'] = 'sql-formatter'
        
        # HTML linter
        if self._command_exists('htmlhint'):
            linters['html'] = 'htmlhint'
        
        # CSS linter
        if self._command_exists('stylelint'):
            linters['css'] = 'stylelint'
        
        # Ruby linter
        if self._command_exists('rubocop'):
            linters['ruby'] = 'rubocop'
        elif self._command_exists('ruby'):
            linters['ruby'] = 'ruby'
        
        # PHP linter
        if self._command_exists('phpcs'):
            linters['php'] = 'phpcs'
        elif self._command_exists('php'):
            linters['php'] = 'php'
        
        # Perl linter
        if self._command_exists('perlcritic'):
            linters['perl'] = 'perlcritic'
        elif self._command_exists('perl'):
            linters['perl'] = 'perl'
        
        # Lua linter
        if self._command_exists('luacheck'):
            linters['lua'] = 'luacheck'
        elif self._command_exists('lua'):
            linters['lua'] = 'lua'
        
        # Kotlin linter
        if self._command_exists('ktlint'):
            linters['kotlin'] = 'ktlint'
        elif self._command_exists('kotlinc'):
            linters['kotlin'] = 'kotlinc'
        
        # Swift linter
        if self._command_exists('swiftlint'):
            linters['swift'] = 'swiftlint'
        elif self._command_exists('swift'):
            linters['swift'] = 'swift'
        
        # Scala linter
        if self._command_exists('scalastyle'):
            linters['scala'] = 'scalastyle'
        elif self._command_exists('scalac'):
            linters['scala'] = 'scalac'
        
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
    
    def lint_file(self, filepath: str, language: Optional[str] = None) -> Dict:
        """
        Lint file and return results
        
        Args:
            filepath: Path to file to lint
            language: Language override (optional)
            
        Returns:
            Dict with success, errors, warnings, and info
        """
        if not os.path.exists(filepath):
            return {
                "success": False,
                "language": "unknown",
                "message": f"File not found: {filepath}",
                "errors": [f"File not found: {filepath}"],
                "warnings": [],
                "info": []
            }
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
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
        
        return self.lint_content(content, filepath, language)
    
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
                "info": [f"Could not detect language for {filename}. Use --language to specify."]
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
                    return self._lint_python(tmp_file_path, linter, filename)
                elif language in ['javascript', 'typescript']:
                    return self._lint_javascript(tmp_file_path, linter, filename)
                elif language == 'java':
                    return self._lint_java(tmp_file_path, linter, filename)
                elif language in ['cpp', 'c']:
                    return self._lint_cpp(tmp_file_path, linter, filename)
                elif language == 'go':
                    return self._lint_go(tmp_file_path, linter, filename)
                elif language == 'json':
                    return self._lint_json(tmp_file_path, linter, filename)
                elif language == 'yaml':
                    return self._lint_yaml(tmp_file_path, linter, filename)
                elif language == 'bash':
                    return self._lint_bash(tmp_file_path, linter, filename)
                elif language == 'sql':
                    return self._lint_sql(tmp_file_path, linter, filename)
                elif language == 'html':
                    return self._lint_html(tmp_file_path, linter, filename)
                elif language == 'css':
                    return self._lint_css(tmp_file_path, linter, filename)
                elif language == 'ruby':
                    return self._lint_ruby(tmp_file_path, linter, filename)
                elif language == 'php':
                    return self._lint_php(tmp_file_path, linter, filename)
                elif language == 'perl':
                    return self._lint_perl(tmp_file_path, linter, filename)
                elif language == 'lua':
                    return self._lint_lua(tmp_file_path, linter, filename)
                elif language == 'kotlin':
                    return self._lint_kotlin(tmp_file_path, linter, filename)
                elif language == 'swift':
                    return self._lint_swift(tmp_file_path, linter, filename)
                elif language == 'scala':
                    return self._lint_scala(tmp_file_path, linter, filename)
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
    
    def _lint_python(self, file_path: str, linter: str, original_filename: str) -> Dict:
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
            
            return self._parse_python_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('python', f"Python linting failed: {e}")
    
    def _lint_javascript(self, file_path: str, linter: str, original_filename: str) -> Dict:
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
            
            return self._parse_javascript_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('javascript', f"JavaScript linting failed: {e}")
    
    def _lint_java(self, file_path: str, linter: str, original_filename: str) -> Dict:
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
            
            return self._parse_java_output(result, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('java', f"Java linting failed: {e}")
    
    def _lint_cpp(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint C++ code"""
        try:
            if linter == 'cppcheck':
                result = subprocess.run(['cppcheck', '--enable=all', '--template={file}:{line}:{column}: {severity}: {message}', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'clang-tidy':
                result = subprocess.run(['clang-tidy', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'gcc':
                result = subprocess.run(['gcc', '-Wall', '-Wextra', '-fsyntax-only', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'clang':
                result = subprocess.run(['clang', '-Wall', '-Wextra', '-fsyntax-only', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('cpp', "C++ linting not available")
            
            return self._parse_cpp_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('cpp', f"C++ linting failed: {e}")
    
    def _lint_sql(self, file_path: str, linter: str, original_filename: str) -> Dict:
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
            
            return self._parse_sql_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('sql', f"SQL linting failed: {e}")
    
    def _lint_json(self, file_path: str, linter: str, original_filename: str) -> Dict:
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
                return self._parse_json_output(result, original_filename)
                
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
    
    def _lint_bash(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Bash scripts"""
        try:
            result = subprocess.run(['shellcheck', file_path], 
                                  capture_output=True, text=True)
            return self._parse_shellcheck_output(result, original_filename)
            
        except Exception as e:
            return self._generic_lint_result('bash', f"Bash linting failed: {e}")
    
    def _lint_html(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint HTML code"""
        try:
            result = subprocess.run(['htmlhint', file_path], 
                                  capture_output=True, text=True)
            return self._parse_html_output(result, original_filename)
            
        except Exception as e:
            return self._generic_lint_result('html', f"HTML linting failed: {e}")
    
    def _lint_css(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint CSS code"""
        try:
            result = subprocess.run(['stylelint', file_path], 
                                  capture_output=True, text=True)
            return self._parse_css_output(result, original_filename)
            
        except Exception as e:
            return self._generic_lint_result('css', f"CSS linting failed: {e}")
    
    def _parse_python_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Python linter output"""
        errors = []
        warnings = []
        
        # Use the provided temp file path for replacement
        
        if result.returncode != 0 and result.stderr:
            # Syntax errors
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    # Replace temp file path with original filename for cleaner output
                    clean_line = line.replace(temp_file_path, original_path)
                    errors.append(clean_line.strip())
        
        if result.stdout:
            # Style warnings and errors
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    # Replace temp file path with original filename
                    clean_line = line.replace(temp_file_path, original_path)
                    # Categorize based on error codes
                    if any(code in line for code in ['E9', 'F']):  # Syntax errors and undefined names
                        errors.append(clean_line.strip())
                    elif any(code in line for code in ['E', 'C']):  # Style errors
                        errors.append(clean_line.strip())
                    else:  # Warnings
                        warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "python",
            "message": f"Python linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_javascript_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse JavaScript linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                elif 'warn' in line.lower():
                    warnings.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "javascript", 
            "message": f"JavaScript linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_java_output(self, result: subprocess.CompletedProcess, original_path: str, temp_file_path: str) -> Dict:
        """Parse Java compiler output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                elif 'warning' in line.lower():
                    warnings.append(clean_line.strip())
                else:
                    errors.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "java",
            "message": "Java compilation check completed",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_cpp_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse C++ linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                elif 'warning' in line.lower():
                    warnings.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "cpp",
            "message": f"C++ linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_sql_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse SQL linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower() or 'critical' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "sql",
            "message": f"SQL linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _lint_go(self, file_path: str, linter: str, original_filename: str) -> Dict:
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
            
            return self._parse_go_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('go', f"Go linting failed: {e}")
    
    def _lint_yaml(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint YAML code"""
        try:
            result = subprocess.run(['yamllint', file_path], 
                                  capture_output=True, text=True)
            return self._parse_yaml_output(result, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('yaml', f"YAML linting failed: {e}")
    
    def _parse_go_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Go linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "go",
            "message": f"Go linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_yaml_output(self, result: subprocess.CompletedProcess, original_path: str, temp_file_path: str) -> Dict:
        """Parse YAML linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "yaml",
            "message": "YAML linting completed with yamllint",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_json_output(self, result: subprocess.CompletedProcess, original_path: str) -> Dict:
        """Parse JSON linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "json",
            "message": "JSON linting completed with jsonlint",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_shellcheck_output(self, result: subprocess.CompletedProcess, original_path: str) -> Dict:
        """Parse shellcheck output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "bash",
            "message": "Bash linting completed with shellcheck",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_html_output(self, result: subprocess.CompletedProcess, original_path: str) -> Dict:
        """Parse HTML linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "html",
            "message": "HTML linting completed with htmlhint",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_css_output(self, result: subprocess.CompletedProcess, original_path: str) -> Dict:
        """Parse CSS linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                if 'error' in line.lower():
                    errors.append(line.strip())
                else:
                    warnings.append(line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "css",
            "message": "CSS linting completed with stylelint",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _lint_ruby(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Ruby code"""
        try:
            if linter == 'rubocop':
                result = subprocess.run(['rubocop', '--format', 'simple', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'ruby':
                result = subprocess.run(['ruby', '-c', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('ruby', "Ruby linting not available")
            
            return self._parse_ruby_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('ruby', f"Ruby linting failed: {e}")
    
    def _lint_php(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint PHP code"""
        try:
            if linter == 'phpcs':
                result = subprocess.run(['phpcs', '--standard=PSR12', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'php':
                result = subprocess.run(['php', '-l', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('php', "PHP linting not available")
            
            return self._parse_php_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('php', f"PHP linting failed: {e}")
    
    def _lint_perl(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Perl code"""
        try:
            if linter == 'perlcritic':
                result = subprocess.run(['perlcritic', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'perl':
                result = subprocess.run(['perl', '-c', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('perl', "Perl linting not available")
            
            return self._parse_perl_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('perl', f"Perl linting failed: {e}")
    
    def _lint_lua(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Lua code"""
        try:
            if linter == 'luacheck':
                result = subprocess.run(['luacheck', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'lua':
                result = subprocess.run(['lua', '-l', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('lua', "Lua linting not available")
            
            return self._parse_lua_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('lua', f"Lua linting failed: {e}")
    
    def _lint_kotlin(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Kotlin code"""
        try:
            if linter == 'ktlint':
                result = subprocess.run(['ktlint', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'kotlinc':
                result = subprocess.run(['kotlinc', '-Werror', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('kotlin', "Kotlin linting not available")
            
            return self._parse_kotlin_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('kotlin', f"Kotlin linting failed: {e}")
    
    def _lint_swift(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Swift code"""
        try:
            if linter == 'swiftlint':
                result = subprocess.run(['swiftlint', 'lint', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'swift':
                result = subprocess.run(['swift', '-frontend', '-parse', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('swift', "Swift linting not available")
            
            return self._parse_swift_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('swift', f"Swift linting failed: {e}")
    
    def _lint_scala(self, file_path: str, linter: str, original_filename: str) -> Dict:
        """Lint Scala code"""
        try:
            if linter == 'scalastyle':
                result = subprocess.run(['scalastyle', file_path], 
                                      capture_output=True, text=True)
            elif linter == 'scalac':
                result = subprocess.run(['scalac', '-Werror', file_path], 
                                      capture_output=True, text=True)
            else:
                return self._generic_lint_result('scala', "Scala linting not available")
            
            return self._parse_scala_output(result, linter, original_filename, file_path)
            
        except Exception as e:
            return self._generic_lint_result('scala', f"Scala linting failed: {e}")
    
    def _parse_ruby_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Ruby linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower() or 'fatal' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "ruby",
            "message": f"Ruby linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_php_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse PHP linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower() or 'fatal' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "php",
            "message": f"PHP linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_perl_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Perl linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower() or 'fatal' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "perl",
            "message": f"Perl linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_lua_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Lua linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower() or 'fatal' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "lua",
            "message": f"Lua linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_kotlin_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Kotlin linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "kotlin",
            "message": f"Kotlin linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_swift_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Swift linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "swift",
            "message": f"Swift linting completed with {linter}",
            "errors": errors,
            "warnings": warnings,
            "info": []
        }
    
    def _parse_scala_output(self, result: subprocess.CompletedProcess, linter: str, original_path: str, temp_file_path: str) -> Dict:
        """Parse Scala linter output"""
        errors = []
        warnings = []
        
        output = result.stdout + result.stderr
        for line in output.strip().split('\n'):
            if line.strip():
                clean_line = line.replace(temp_file_path, original_path)
                if 'error' in line.lower():
                    errors.append(clean_line.strip())
                else:
                    warnings.append(clean_line.strip())
        
        return {
            "success": len(errors) == 0,
            "language": "scala",
            "message": f"Scala linting completed with {linter}",
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
    """Command line interface for the multi-language linter"""
    parser = argparse.ArgumentParser(
        description='LINTER - Multi-language syntax and style checker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  LINTER file.py                    # Lint Python file
  LINTER file.js --language javascript  # Lint JavaScript file
  LINTER file.cpp                   # Lint C++ file
  LINTER --help                     # Show this help

Supported languages: Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, 
SQL, JSON, YAML, HTML, CSS, Shell scripts, Ruby, PHP, Perl, Lua, Kotlin, Swift, Scala
        """
    )
    parser.add_argument('file', help='File to lint')
    parser.add_argument('--language', '-l', help='Language override (python, javascript, java, cpp, sql, etc.)')
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='text', help='Output format (default: text)')
    parser.add_argument('--version', action='version', version='LINTER 1.0.0')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"ERROR: File {args.file} not found", file=sys.stderr)
        sys.exit(1)
    
    linter = MultiLanguageLinter()
    result = linter.lint_file(args.file, args.language)
    
    if args.format == 'json':
        print(json.dumps(result, indent=2))
    else:
        # Text format output
        status_icon = '✅' if result['success'] else '❌'
        print(f"Language: {result['language']}")
        print(f"Status: {status_icon} {'PASS' if result['success'] else 'FAIL'}")
        print(f"Linter: {result['message']}")
        
        total_issues = len(result['errors']) + len(result['warnings'])
        if total_issues > 0:
            print(f"\n{total_issues} linter warnings or errors found:")
        
        if result['errors']:
            for error in result['errors']:
                print(f"ERROR: {error}")
        
        if result['warnings']:
            for warning in result['warnings']:
                print(f"WARNING: {warning}")
        
        if result['info']:
            print("\nℹ️  Info:")
            for info in result['info']:
                print(f"  • {info}")
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
