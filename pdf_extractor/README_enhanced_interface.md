# Enhanced PDF Extraction Interface

This enhanced PDF extraction interface provides a new output format that creates same-name `.md` files and `_extract_data` folders for better organization and async processing capabilities.

## Features

### 🔄 Enhanced Output Structure
- **Same-name output**: Creates `document.md` for `document.pdf`
- **Extract data folder**: Creates `document_extract_data/` containing all intermediate files
- **Organized images**: All images stored in `document_extract_data/images/`
- **Intermediate files**: MinerU outputs (`_content.json`, `_layout.pdf`, `_middle.json`, etc.)

### 🔬 Async UnimerNet Processing
- **Formula recognition**: Recognizes mathematical formulas and converts to LaTeX
- **Table recognition**: Recognizes table structures and converts to LaTeX
- **Image API fallback**: Falls back to image analysis API when UnimerNet fails
- **Placeholder system**: Uses `[DESCRIPTION]` placeholders for async processing

### 🎯 Improved Workflow
- **Two-step process**: 1) PDF extraction with MinerU, 2) Async image processing
- **Overwrite protection**: Asks before overwriting existing files
- **Debug support**: Comprehensive debug output for troubleshooting
- **Error handling**: Graceful fallback mechanisms

## Usage

### Basic Usage

```bash
# Extract PDF with enhanced interface
python pdf_extractor_enhanced.py document.pdf

# Extract specific pages
python pdf_extractor_enhanced.py document.pdf --page 1-5

# Extract with debug output
python pdf_extractor_enhanced.py document.pdf --debug
```

### Complete Workflow

```bash
# Complete workflow with async processing
python pdf_extract_workflow.py document.pdf --async-process

# Extract without image API, then process with UnimerNet
python pdf_extract_workflow.py document.pdf --no-image-api --async-process

# Process specific pages with full debug
python pdf_extract_workflow.py document.pdf --page 1-3 --async-process --debug
```

### Async Processing Only

```bash
# Process existing markdown file with UnimerNet
python unimernet_processor.py document.md

# Process without image API fallback
python unimernet_processor.py document.md --no-image-api

# Batch process directory
python unimernet_processor.py /path/to/directory --async-process
```

## Output Structure

For a PDF file `document.pdf`, the enhanced interface creates:

```
document.pdf                    # Original PDF
document.md                     # Main markdown output
document_extract_data/          # Extract data folder
├── images/                     # All extracted images
│   ├── image1.jpg
│   ├── image2.jpg
│   └── ...
├── document_content_list.json  # Content structure
├── document_layout.pdf         # Layout visualization
├── document_middle.json        # Intermediate processing data
├── document_model.json         # Model outputs
├── document_origin.pdf         # Original PDF copy
└── document_span.pdf           # Span visualization
```

## Image Processing Workflow

### 1. Initial Extraction
- MinerU extracts PDF and creates images
- Images are saved with hash-based names for uniqueness
- Markdown contains image references with `[DESCRIPTION]` placeholders

### 2. Async Processing
- UnimerNet attempts to recognize formulas and tables
- If successful, replaces `[DESCRIPTION]` with LaTeX content
- If failed, falls back to image analysis API
- Final fallback: `[DESCRIPTION: UnimerNet recognition failed]`

### 3. Placeholder Types
- `[DESCRIPTION]` - Awaiting processing
- `[DESCRIPTION: Image API not called]` - API disabled
- `[DESCRIPTION: UnimerNet recognition failed]` - Recognition failed
- `[DESCRIPTION: Image file not found]` - File missing
- `[DESCRIPTION: ...]` - Image API result
- Direct LaTeX content - UnimerNet recognition successful

## Configuration

### Environment Variables
- `MINERU_MODEL_SOURCE=local` - Use local models
- `MINERU_CONFIG_PATH=/path/to/config` - Custom config path

### Dependencies
- MinerU with UnimerNet support
- Image analysis API (optional)
- Python 3.8+

## Examples

### Example 1: Academic Paper
```bash
python pdf_extract_workflow.py research_paper.pdf --async-process
```

Output:
- `research_paper.md` - Main content with LaTeX formulas
- `research_paper_extract_data/` - All supporting files

### Example 2: Technical Document
```bash
python pdf_extract_workflow.py technical_doc.pdf --page 1-10 --async-process --debug
```

Output includes detailed debug information and processes only first 10 pages.

### Example 3: Batch Processing
```bash
python unimernet_processor.py /documents/ --async-process
```

Processes all `.md` files in the directory with async UnimerNet recognition.

## Troubleshooting

### Common Issues

1. **UnimerNet model not found**
   - Ensure models are in `pdf_extractor/models/` directory
   - Check `mineru.json` configuration

2. **Image API failures**
   - Use `--no-image-api` to disable API calls
   - Check API configuration in `image2text_api.py`

3. **MinerU processing errors**
   - Use `--debug` for detailed output
   - Check temp directory for intermediate files

### Debug Mode
Enable debug mode for detailed output:
```bash
python pdf_extract_workflow.py document.pdf --debug --async-process
```

## Testing

Run the test suite to verify functionality:
```bash
python test_enhanced_interface.py
```

The test suite includes:
1. Basic enhanced extraction
2. Async UnimerNet processing
3. Complete workflow validation

## Migration from Original Interface

### Old Interface
```bash
python pdf_extractor.py document.pdf
# Output: pdf_extractor_data/markdown/0.md
```

### New Interface
```bash
python pdf_extractor_enhanced.py document.pdf
# Output: document.md + document_extract_data/
```

### Benefits
- ✅ Same-name files for easy identification
- ✅ Organized intermediate files
- ✅ Async processing capabilities
- ✅ Better error handling
- ✅ Improved debugging

## API Reference

### EnhancedPDFExtractor
```python
from pdf_extractor_enhanced import EnhancedPDFExtractor

extractor = EnhancedPDFExtractor()
result = extractor.extract_pdf(
    pdf_path="document.pdf",
    page_range="1-5",
    debug=True
)
```

### AsyncUnimerNetProcessor
```python
from async_unimernet_processor import AsyncUnimerNetProcessor

processor = AsyncUnimerNetProcessor(debug=True)
success = processor.process_markdown_file(
    "document.md",
    call_image_api=True
)
```

## Contributing

1. Test changes with `python test_enhanced_interface.py`
2. Update this README for new features
3. Follow the existing code style and error handling patterns
4. Add debug output for troubleshooting

## License

Same as the original pdf_extractor project. 