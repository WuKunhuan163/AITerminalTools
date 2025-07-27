# EXTRACT_PDF

Enhanced PDF extraction using MinerU with integrated post-processing support

## Description

EXTRACT_PDF is a comprehensive tool for extracting content from PDF files using advanced MinerU technology. It supports multiple extraction engines, page-specific extraction, custom output directories, GUI file selection, and sophisticated post-processing of markdown files to replace placeholders with actual content using IMG2TEXT and UNIMERNET tools.

## Usage

```bash
# Basic PDF extraction
EXTRACT_PDF <pdf_file> [options]
EXTRACT_PDF  # GUI file selection mode

# Post-processing existing markdown files
EXTRACT_PDF --post [<markdown_file>] [--post-type <type>] [--ids <ids>] [--prompt <text>] [--force]
EXTRACT_PDF --post  # Interactive mode for post-processing

# Full pipeline (extract + auto post-process)
EXTRACT_PDF --full <pdf_file> [options]

# Data management
EXTRACT_PDF --clean-data  # Clean cached data
```

## Options

### PDF Extraction Options
- `--page <spec>`: Extract specific page(s) (e.g., 3, 1-5, 1,3,5)
- `--output-dir <dir>`: Output directory (default: same as PDF)
- `--engine <mode>`: Extraction engine mode (default: mineru):
  - `basic`: Basic extractor with image processing (merge nearby images, generate placeholders)
  - `basic-asyn`: Basic extractor with PDF screenshot merging (merges nearby images via PDF clipping, adds placeholders, processes text linebreaks, creates extract_data folder)
  - `mineru`: MinerU extractor with full image/formula/table analysis
  - `mineru-asyn`: MinerU extractor, async mode (no image/formula/table analysis)
  - `full`: Full analysis mode (equivalent to mineru - enable all features including image/formula/table processing)

### Post-processing Options
- `--post [<file>]`: Post-process markdown file (replace placeholders with actual content)
  - If no file specified, uses FILEDIALOG for interactive file selection
- `--post-type <type>`: Post-processing type (default: all):
  - `image`: Process only image placeholders using IMG2TEXT
  - `formula`: Process only formula placeholders using UNIMERNET
  - `table`: Process only table placeholders using UNIMERNET
  - `all`: Process all types of placeholders
- `--ids <ids>`: Selective processing by hash IDs or keywords:
  - Comma-separated hash IDs: `4edf23de78f80bed...,39a7f2bc45d12...`
  - Keywords: `all_images`, `all_formulas`, `all_tables`, `all`
- `--prompt <text>`: Custom prompt for IMG2TEXT image analysis (academic mode by default)
- `--force`: Force reprocessing even if items are already marked as processed

### Pipeline Options
- `--full <file>`: Full pipeline - extract PDF then automatically post-process the result
- `--clean-data`: Clean all cached markdown files and images from EXTRACT_PDF_PROJ

### General Options
- `--help, -h`: Show detailed help message

## Examples

### PDF Extraction Examples
```bash
# Extract entire PDF using default MinerU engine
EXTRACT_PDF document.pdf

# Extract specific page with basic engine
EXTRACT_PDF document.pdf --page 3 --engine basic

# Extract with PDF screenshot merging (adds placeholders, processes text, creates extract_data folder)
EXTRACT_PDF document.pdf --engine basic-asyn --output-dir ~/Desktop/output

# Extract page range with custom output directory
EXTRACT_PDF paper.pdf --page 1-5 --output-dir /path/to/output --engine mineru-asyn

# Extract multiple pages using full engine (with image/formula/table processing)
EXTRACT_PDF research.pdf --page 1,3,5-7 --engine full

# Open GUI file selection dialog
EXTRACT_PDF
```

### Post-processing Examples
```bash
# Interactive post-processing mode (opens file dialog)
EXTRACT_PDF --post

# Post-process specific markdown file (all types)
EXTRACT_PDF --post document.md

# Post-process only images with custom prompt
EXTRACT_PDF --post document.md --post-type image --prompt "Analyze this research figure focusing on quantitative results"

# Post-process only formulas
EXTRACT_PDF --post document.md --post-type formula

# Post-process only tables
EXTRACT_PDF --post document.md --post-type table

# Selective processing by hash IDs
EXTRACT_PDF --post document.md --ids 4edf23de78f80bedade9e9628d7de04677faf669c945a7438bc5741c054af036

# Process all images using keyword
EXTRACT_PDF --post document.md --ids all_images

# Force reprocessing of all items
EXTRACT_PDF --post document.md --post-type all --force
```

### Full Pipeline Examples
```bash
# Full pipeline with default settings
EXTRACT_PDF --full document.pdf

# Full pipeline with specific page range and custom output
EXTRACT_PDF --full paper.pdf --page 1-10 --output-dir /path/to/output

# Full pipeline with specific engine
EXTRACT_PDF --full document.pdf --engine full --page 1-5
```

### Data Management Examples
```bash
# Clean cached data
EXTRACT_PDF --clean-data
```

### RUN Integration Examples
```bash
# Get JSON output for extraction
RUN --show EXTRACT_PDF document.pdf --page 3 --engine mineru

# Get JSON output for post-processing
RUN --show EXTRACT_PDF --post document.md --post-type all

# Get JSON output for full pipeline
RUN --show EXTRACT_PDF --full document.pdf --engine full
```

## Features

### PDF Extraction Features
- **Multiple Engines**: Choose between basic PyMuPDF and advanced MinerU extraction
- **Page Selection**: Extract specific pages, ranges, or combinations (e.g., 1,3,5-7)
- **GUI File Selection**: Interactive file picker when no arguments provided
- **Custom Output**: Specify output directory for organized file management
- **Image Processing**: 
  - Basic engine merges nearby images and creates placeholders
  - Basic-asyn engine uses PDF screenshot technology to merge nearby images by calculating combined bounding boxes and clipping directly from PDF pages (preserves original layout and quality, adds `[placeholder: image]` tags for post-processing)
- **Text Processing**: 
  - Smart linebreak handling and paragraph formatting for all engines
  - Basic-asyn engine includes text processing to prevent sentence fragmentation
- **Multiple Formats**: Supports various PDF types and structures
- **Extract Data Folder**: Basic-asyn engine creates `{pdf_name}_extract_data` folder in output directory with organized content

### Post-processing Features
- **GUI File Selection**: Uses FILEDIALOG tool for easy markdown file selection
- **Placeholder System**: Replaces `[placeholder: type]` tags with actual content
- **Hybrid Processing**: 
  - Images processed with IMG2TEXT API (academic mode by default)
  - Formulas processed with UNIMERNET for LaTeX recognition
  - Tables processed with UNIMERNET for structure analysis
- **Selective Processing**: Process specific items by hash IDs or content types
- **Custom Prompts**: Support for detailed custom instructions for image analysis
- **Error Handling**: Preserves placeholders when processing fails with detailed error messages
- **Status Tracking**: Maintains processing status to avoid duplicate work
- **Force Reprocessing**: Option to reprocess already completed items

### Full Pipeline Features
- **Automated Workflow**: Extract PDF and post-process in single command
- **Intelligent File Detection**: Automatically finds generated markdown files
- **Graceful Degradation**: Continues even if post-processing fails
- **Progress Feedback**: Clear indication of each step's progress
- **Flexible Configuration**: All extraction options available in pipeline mode

### Advanced Features
- **Cache System**: Integrated with EXTRACT_IMG tool for efficient image processing
- **Status Files**: JSON tracking of processing status for large documents
- **Error Recovery**: Detailed error messages and recovery suggestions
- **Memory Management**: Automatic cleanup of temporary resources
- **Path Handling**: Support for both absolute and relative image paths

### General Features
- **RUN Compatible**: Full integration with RUN command for JSON output
- **Cross-platform**: Works on macOS, Linux, and Windows
- **Dependency Management**: Graceful handling of missing dependencies
- **Logging**: Comprehensive progress and error logging

## Output

### PDF Extraction Output
The tool extracts content to markdown format with the following features:
- Page headers for clear organization
- Image placeholders with hash-based filenames (`[placeholder: image]` tags)
- Preserved text formatting and structure
- Smart paragraph breaks based on punctuation (prevents sentence fragmentation)
- Absolute paths for reliable image references

#### Basic-asyn Engine Specific Output:
- **PDF Screenshot Images**: High-quality PNG images created by clipping merged bounding boxes directly from PDF pages
- **Extract Data Folder**: Creates `{pdf_name}_extract_data/` folder containing:
  - Main markdown file with processed content
  - `images/` subfolder with all extracted images
- **Enhanced Text Processing**: Continuous paragraphs with proper sentence flow
- **Placeholder Integration**: Properly formatted `[placeholder: image]` tags for seamless post-processing

### Post-processing Output
Post-processing transforms placeholders into actual content:
- **Image placeholders** → Detailed academic analysis using IMG2TEXT
- **Formula placeholders** → LaTeX markup using UNIMERNET
- **Table placeholders** → Structured text using UNIMERNET
- Error information preserved when processing fails
- Original images remain accessible with absolute paths

### JSON Output (RUN Mode)
When used with RUN, returns structured JSON with:
- Success/failure status
- Processing messages and results
- File paths and metadata
- Error details when applicable
- Processing time and statistics

## Dependencies

### Core Dependencies
- Python 3.9+
- pathlib, json, subprocess (built-in)

### Optional Dependencies
- **PyMuPDF (fitz)**: Required for basic engine mode
- **MinerU library**: Required for mineru engine modes
- **tkinter**: Required for GUI file selection (usually included)

### Tool Dependencies
- **IMG2TEXT**: Required for image analysis in post-processing
- **UNIMERNET**: Required for formula and table recognition
- **EXTRACT_IMG**: Used for cached image processing
- **FILEDIALOG**: Used for interactive file selection

## Project Structure

```
EXTRACT_PDF_PROJ/
├── extract_paper_layouts.py     # Layout analysis utilities
├── fix_formula_templates.py     # Formula template processing
├── image2text_api.py           # Image analysis API wrapper
├── pdf_extractor_data/         # Cached extraction data
│   ├── images/                 # Extracted images
│   └── markdown/               # Generated markdown files
└── pdf_extractor_MinerU/       # MinerU integration
    └── mineru/                 # MinerU package

UNIMERNET_PROJ/
├── extract_paper_layouts.py     # Layout analysis for UNIMERNET
├── image2text_api.py           # Image API for UNIMERNET
├── unimernet_hf/               # Hugging Face UNIMERNET models
└── unimernet_models/           # Local model storage
```

## Error Handling

The tool provides comprehensive error handling:
- **Missing files**: Clear error messages with suggested solutions
- **Invalid arguments**: Detailed parameter validation
- **Dependency issues**: Graceful degradation with informative messages
- **Processing failures**: Error preservation in markdown with recovery options
- **API failures**: Detailed error logging with retry suggestions

## Performance Considerations

- **MinerU processing**: Can be slow for large documents; use page selection for testing
- **Image processing**: Cached via EXTRACT_IMG to avoid redundant API calls
- **Memory usage**: Automatic cleanup of temporary resources
- **Network calls**: IMG2TEXT and UNIMERNET may require internet connectivity

## Notes

- Default engine is `mineru` with full image/formula/table analysis for best quality
- GUI mode requires tkinter (usually included with Python installations)
- RUN mode provides structured JSON output for automation
- Post-processing preserves original placeholders on failure for manual review
- Image paths are converted to absolute paths for reliability
- Formula recognition uses UNIMERNET for higher accuracy than traditional OCR
- Table processing attempts to preserve structure and formatting 