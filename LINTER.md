# LINTER - Multi-language Syntax and Style Checker

## Overview

LINTER is a comprehensive multi-language syntax and style checker that supports Python, JavaScript, TypeScript, Java, C/C++, SQL, JSON, YAML, HTML, CSS, and more. It automatically detects the programming language from file extensions and applies appropriate linting rules.

## Features

- **Multi-language Support**: Python, JavaScript, TypeScript, Java, C/C++, Go, Rust, SQL, JSON, YAML, HTML, CSS, Shell scripts
- **Automatic Language Detection**: Detects language from file extensions
- **Manual Language Override**: Specify language explicitly with `--language` option
- **Multiple Output Formats**: Human-readable text or structured JSON output
- **Comprehensive Error Detection**: Syntax errors, style violations, unused variables, and more
- **Extensible Architecture**: Easy to add support for new languages and linters

## Installation Requirements

The tool automatically detects available linters on your system. For best results, install the following linters:

### Python
- `flake8` (recommended): `pip install flake8`
- `pylint`: `pip install pylint`
- `pycodestyle`: `pip install pycodestyle`

### JavaScript/TypeScript
- `eslint`: `npm install -g eslint`
- `jshint`: `npm install -g jshint`
- `standard`: `npm install -g standard`

### Java
- `checkstyle`: Download from https://checkstyle.org/
- `javac`: Part of JDK

### C/C++
- `cppcheck`: `brew install cppcheck` (macOS) or `apt install cppcheck` (Linux)
- `clang-tidy`: Part of LLVM/Clang
- `gcc` or `clang`: Standard compilers

### SQL
- `sqlfluff`: `pip install sqlfluff`
- `sql-formatter`: `npm install -g sql-formatter`

### Other Languages
- `shellcheck`: `brew install shellcheck` (Shell scripts)
- `yamllint`: `pip install yamllint` (YAML)
- `jsonlint`: `npm install -g jsonlint` (JSON)
- `htmlhint`: `npm install -g htmlhint` (HTML)
- `stylelint`: `npm install -g stylelint` (CSS)

## Usage

### Basic Usage

```bash
# Lint a Python file
LINTER file.py

# Lint a JavaScript file
LINTER script.js

# Lint a C++ file
LINTER program.cpp

# Lint a JSON file
LINTER config.json
```

### Advanced Usage

```bash
# Specify language explicitly
LINTER file.txt --language python

# Get JSON output for programmatic use
LINTER file.py --format json

# Show help
LINTER --help

# Show version
LINTER --version
```

## Output Format

### Text Format (Default)

```
Language: python
Status: ❌ FAIL
Linter: Python linting completed with flake8

22 linter warnings or errors found:
ERROR: file.py:6:1: F401 'os' imported but unused
ERROR: file.py:12:19: E231 missing whitespace after ','
WARNING: file.py:47:18: W292 no newline at end of file
```

### JSON Format

```json
{
  "success": false,
  "language": "python",
  "message": "Python linting completed with flake8",
  "errors": [
    "file.py:6:1: F401 'os' imported but unused",
    "file.py:12:19: E231 missing whitespace after ','"
  ],
  "warnings": [
    "file.py:47:18: W292 no newline at end of file"
  ],
  "info": []
}
```

## Supported Languages

| Language | Extensions | Primary Linter | Fallback |
|----------|------------|----------------|----------|
| Python | `.py` | flake8 | python3 -m py_compile |
| JavaScript | `.js`, `.jsx` | eslint | jshint |
| TypeScript | `.ts`, `.tsx` | eslint | jshint |
| Java | `.java` | javac | checkstyle |
| C/C++ | `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp` | gcc/clang | cppcheck |
| Go | `.go` | golint | gofmt |
| Rust | `.rs` | cargo | - |
| SQL | `.sql` | sqlfluff | sql-formatter |
| JSON | `.json` | python-json | jsonlint |
| YAML | `.yaml`, `.yml` | yamllint | - |
| Shell | `.sh` | shellcheck | - |
| HTML | `.html` | htmlhint | - |
| CSS | `.css` | stylelint | - |

## Error Codes

### Python (flake8)
- **E**: Style errors (PEP 8 violations)
- **F**: Logical errors (undefined names, syntax errors)
- **W**: Warnings (style recommendations)
- **C**: Complexity warnings

### JavaScript (eslint)
- **error**: Syntax and logical errors
- **warn**: Style and best practice warnings

### C/C++ (gcc)
- **error**: Compilation errors
- **warning**: Compiler warnings

## Integration

### GDS Edit Command Integration

When using the GDS (Google Drive Shell) edit command, LINTER automatically runs on edited files and displays results:

```bash
GDS edit file.py '[["old_code", "new_code"]]'
```

After editing, you'll see:
```
========
(edit comparison showing changes)
========
========
5 linter warnings or errors found: 
ERROR: file.py:10:1: F401 'sys' imported but unused
WARNING: file.py:25:80: E501 line too long (85 > 79 characters)
...
========
```

### Programmatic Usage

```python
from LINTER import MultiLanguageLinter

linter = MultiLanguageLinter()
result = linter.lint_file("script.py")

if result['success']:
    print(f"No issues found!")
else:
    for error in result['errors']:
        print(f"ERROR: {error}")
    for warning in result['warnings']:
        print(f"WARNING: {warning}")
```

## Exit Codes

- `0`: Success (no linting errors found)
- `1`: Linting errors found or linter execution failed

## Examples

### Python Linting
```bash
# Check a Python script
LINTER my_script.py

# Output:
# Language: python
# Status: ❌ FAIL
# Linter: Python linting completed with flake8
#
# 3 linter warnings or errors found:
# ERROR: my_script.py:1:1: F401 'os' imported but unused
# ERROR: my_script.py:5:10: E225 missing whitespace around operator
# WARNING: my_script.py:10:80: E501 line too long (85 > 79 characters)
```

### JavaScript Linting
```bash
# Check a JavaScript file
LINTER app.js --language javascript

# Output:
# Language: javascript
# Status: ✅ PASS
# Linter: No linter available for javascript
#
# ℹ️  Info:
#   • Install a javascript linter for better checking
```

### JSON Validation
```bash
# Validate JSON syntax
LINTER config.json

# Output:
# Language: json
# Status: ❌ FAIL
# Linter: JSON syntax error
#
# 1 linter warnings or errors found:
# ERROR: Line 7: Expecting ',' delimiter
```

## Troubleshooting

### Common Issues

1. **"No linter available for [language]"**
   - Install the appropriate linter for your language
   - Check that the linter is in your PATH

2. **"Language not detected"**
   - Use the `--language` option to specify explicitly
   - Check that your file has the correct extension

3. **"File not found"**
   - Verify the file path is correct
   - Ensure you have read permissions for the file

### Debug Information

For debugging, you can:
- Use `--format json` to see structured output
- Check if linters are installed: `which flake8`, `which eslint`, etc.
- Verify file permissions: `ls -la yourfile.py`

## Contributing

To add support for a new language:

1. Add the file extension to `LANGUAGE_MAP`
2. Add linter detection in `_detect_available_linters()`
3. Implement `_lint_[language]()` method
4. Implement `_parse_[language]_output()` method
5. Add the language to the routing in `_run_linter()`

## License

This tool is part of the ~/.local/bin toolkit and follows the same license terms.
