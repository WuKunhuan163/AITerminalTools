# EXTRACT_PDF

Enhanced PDF extraction using MinerU with post-processing support

## Description

EXTRACT_PDF is a powerful tool for extracting content from PDF files using MinerU technology. It supports page-specific extraction, custom output directories, GUI file selection when called without arguments, and post-processing of markdown files to replace placeholders with actual content.

## Usage

```bash
# PDF extraction
EXTRACT_PDF <pdf_file> [options]
EXTRACT_PDF  # GUI file selection mode

# Post-processing
EXTRACT_PDF --post [<markdown_file>] [--post-type <type>]
EXTRACT_PDF --post  # Interactive mode for post-processing

# Full pipeline
EXTRACT_PDF --full <pdf_file> [options]  # Extract PDF then auto post-process
```

## Options

### PDF Extraction Options
- `--page <spec>`: Extract specific page(s) (e.g., 3, 1-5, 1,3,5)
- `--output <dir>`: Output directory (default: same as PDF)
- `--engine <mode>`: Extraction engine mode:
  - `basic`: Basic extractor (default)
  - `basic-asyn`: Basic extractor, async mode (disable analysis)
  - `mineru`: MinerU extractor (experimental)
  - `mineru-asyn`: MinerU extractor, async mode (disable analysis)
  - `full`: Full analysis mode (enable all features)
- `--with-image-api`: Enable image API analysis (disabled by default)

### Post-processing Options
- `--post [<file>]`: Post-process markdown file (replace placeholders)
  - If no file specified, uses FILEDIALOG for file selection
- `--post-type <type>`: Post-processing type: image, formula, table, all (default: all)
- `--full <file>`: Full pipeline - extract PDF then automatically post-process the result

### General Options
- `--help, -h`: Show help message

## Examples

### PDF Extraction Examples
```bash
# Extract entire PDF
EXTRACT_PDF document.pdf

# Extract specific page
EXTRACT_PDF document.pdf --page 3

# Extract page range
EXTRACT_PDF paper.pdf --page 1-5

# Extract with custom output directory
EXTRACT_PDF paper.pdf --page 1-5 --output /path/to/output

# Open file selection dialog
EXTRACT_PDF
```

### Post-processing Examples
```bash
# Interactive post-processing mode
EXTRACT_PDF --post

# Post-process specific markdown file (all types)
EXTRACT_PDF --post document.md --post-type all

# Post-process only images
EXTRACT_PDF --post document.md --post-type image

# Post-process only formulas
EXTRACT_PDF --post document.md --post-type formula

# Post-process only tables
EXTRACT_PDF --post document.md --post-type table
```

### Full Pipeline Examples
```bash
# Full pipeline with default settings
EXTRACT_PDF --full document.pdf

# Full pipeline with specific page range
EXTRACT_PDF --full paper.pdf --page 1-10

# Full pipeline with custom output directory
EXTRACT_PDF --full document.pdf --output /path/to/output

# Full pipeline with specific engine
EXTRACT_PDF --full paper.pdf --engine mineru --page 1-5
```

### RUN Integration
```bash
# Get JSON output for extraction
RUN --show EXTRACT_PDF document.pdf --page 3

# Get JSON output for post-processing
RUN --show EXTRACT_PDF --post document.md --post-type all
```

## Features

### PDF Extraction Features
- **MinerU Integration**: Uses advanced MinerU technology for better extraction
- **Page Selection**: Extract specific pages or ranges
- **GUI File Selection**: Interactive file picker when no arguments provided
- **Custom Output**: Specify output directory
- **Multiple Formats**: Supports various PDF types and structures

### Post-processing Features
- **GUI File Selection**: Uses FILEDIALOG tool for easy file selection
- **Placeholder Replacement**: Replace image, formula, and table placeholders with actual content
- **Image Analysis**: Uses IMG2TEXT tool for image description
- **Formula Recognition**: Uses UnimerNet for LaTeX formula recognition
- **Table Processing**: Analyzes table images for text content
- **Selective Processing**: Process only specific types (image, formula, table, or all)
- **Error Handling**: Preserves placeholders when API calls fail

### Full Pipeline Features
- **Automated Workflow**: Extract PDF and post-process in one command
- **Intelligent File Detection**: Automatically finds generated markdown files
- **Graceful Degradation**: Continues even if post-processing fails
- **Progress Feedback**: Clear indication of each step's progress

### General Features
- **RUN Compatible**: Works with RUN command for JSON output
- **Error Handling**: Graceful handling of missing files and API failures

## Output

### PDF Extraction Output
The tool extracts content to markdown format and saves it in the specified output directory. When used with RUN, it returns JSON with extraction status and file paths.

### Post-processing Output
Post-processing replaces placeholders in markdown files with actual content analysis. The original placeholders are removed and replaced with image descriptions, LaTeX formulas, or table text as appropriate.

## Dependencies

- Python 3.9+
- MinerU library
- pdf_extract_cli.py (located in ~/.local/project/pdf_extractor/)

## Notes

- Default behavior uses MinerU with image API disabled
- GUI mode requires tkinter (usually included with Python)
- RUN mode provides JSON output for automation
- Direct execution shows progress and detailed logs 