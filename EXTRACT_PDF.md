# EXTRACT_PDF

Enhanced PDF extraction using MinerU without image API analysis

## Description

EXTRACT_PDF is a powerful tool for extracting content from PDF files using MinerU technology. It supports page-specific extraction, custom output directories, and GUI file selection when called without arguments.

## Usage

```bash
EXTRACT_PDF <pdf_file> [options]
EXTRACT_PDF  # GUI file selection mode
```

## Options

- `--page <spec>`: Extract specific page(s) (e.g., 3, 1-5, 1,3,5)
- `--output <dir>`: Output directory (default: same as PDF)
- `--use-original`: Use original extractor instead of MinerU
- `--with-image-api`: Enable image API analysis (disabled by default)
- `--help, -h`: Show help message

## Examples

### Basic Usage
```bash
# Extract entire PDF
EXTRACT_PDF document.pdf

# Extract specific page
EXTRACT_PDF document.pdf --page 3

# Extract page range
EXTRACT_PDF paper.pdf --page 1-5

# Extract with custom output directory
EXTRACT_PDF paper.pdf --page 1-5 --output /path/to/output
```

### GUI Mode
```bash
# Open file selection dialog
EXTRACT_PDF
```

### RUN Integration
```bash
# Get JSON output
RUN --show EXTRACT_PDF document.pdf --page 3
```

## Features

- **MinerU Integration**: Uses advanced MinerU technology for better extraction
- **Page Selection**: Extract specific pages or ranges
- **GUI File Selection**: Interactive file picker when no arguments provided
- **Custom Output**: Specify output directory
- **RUN Compatible**: Works with RUN command for JSON output
- **Multiple Formats**: Supports various PDF types and structures

## Output

The tool extracts content to markdown format and saves it in the specified output directory. When used with RUN, it returns JSON with extraction status and file paths.

## Dependencies

- Python 3.9+
- MinerU library
- pdf_extract_cli.py (located in ~/.local/project/pdf_extractor/)

## Notes

- Default behavior uses MinerU with image API disabled
- GUI mode requires tkinter (usually included with Python)
- RUN mode provides JSON output for automation
- Direct execution shows progress and detailed logs 