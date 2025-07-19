# EXTRACT_IMG - Intelligent Image Analysis Tool

## Overview

EXTRACT_IMG is an intelligent image analysis tool that automatically detects image content types and routes them to appropriate processors. It supports mathematical formulas, tables, and general images with integrated caching for improved performance.

## ⚠️ Current Status: Temporarily Redirected to EXTRACT_PDF

**Important Notice**: EXTRACT_IMG is currently redirected to use EXTRACT_PDF's MinerU-based processing for superior formula and table recognition. The original UNIMERNET/IMG2TEXT routing code is preserved but temporarily bypassed.

### Why the Redirection?
- EXTRACT_PDF's MinerU integration provides significantly better formula and table recognition
- HTML table output is automatically converted to Markdown format
- More robust processing pipeline with better error handling
- Consistent results across different image types

## Features

- **Automatic Type Detection**: Detects formula, table, or general image content
- **Superior Processing**: Currently uses EXTRACT_PDF/MinerU for all image types (temporarily)
- **Markdown Output**: Tables are automatically converted to Markdown format
- **Centralized Caching**: Uses advanced hash-based caching to avoid duplicate processing
- **Batch Processing**: Process multiple images at once
- **Multiple Output Formats**: Text and JSON output options
- **TODO Preservation**: Original UNIMERNET/IMG2TEXT code preserved for future restoration

## Usage

### Basic Usage

```bash
# Analyze a single image (auto-detect type)
EXTRACT_IMG image.png

# Specify image type explicitly
EXTRACT_IMG image.png --type formula
EXTRACT_IMG image.png --type table
EXTRACT_IMG image.png --type image

# Force reprocessing (ignore cache)
EXTRACT_IMG image.png --force
```

### Batch Processing

```bash
# Process multiple images
EXTRACT_IMG --batch image1.png image2.png image3.png

# Batch with specific type
EXTRACT_IMG --batch *.png --type formula
```

### Output Options

```bash
# JSON output
EXTRACT_IMG image.png --json

# Save to file
EXTRACT_IMG image.png --output results.json

# Combine JSON and file output
EXTRACT_IMG image.png --json --output results.json
```

### Cache Management

```bash
# Show cache statistics
EXTRACT_IMG --stats

# View cache information
python3 cache_system.py --stats
```

## Command Line Options

- `image_path`: Path to image file
- `--type {formula,table,image,auto}`: Image type hint (default: auto)
- `--mode {academic,general,code_snippet}`: Processing mode for general images (default: academic)
- `--force`: Force reprocessing even if cached
- `--batch`: Process multiple images
- `--stats`: Show cache statistics
- `--output`: Output file for results
- `--json`: Output in JSON format

## Processing Flow

1. **Image Type Detection**: Automatically detects content type based on filename and hints
2. **Cache Check**: Looks for cached results using advanced hash system
3. **Processor Selection**: 
   - Formulas/Tables → UnimerNet processor
   - General Images → IMG2TEXT processor
4. **Result Caching**: Stores results in centralized cache for future use

## Integration with Other Tools

EXTRACT_IMG integrates seamlessly with:
- **UNIMERNET**: For mathematical formula and table recognition
- **IMG2TEXT**: For general image analysis
- **EXTRACT_PDF**: Uses EXTRACT_IMG for image processing within PDFs
- **Centralized Cache System**: Shares cache with all PDF extraction tools

## Cache System

The tool uses an advanced caching system with:
- **Dual Hash Algorithm**: SHA256 + MD5 for collision avoidance
- **Centralized Storage**: All images cached in `EXTRACT_IMG_CACHE/`
- **Metadata Tracking**: Timestamps, file sizes, and source paths
- **Automatic Cleanup**: Orphaned file detection and removal

## Examples

### Formula Recognition
```bash
# Process a mathematical formula
EXTRACT_IMG formula.png --type formula --json
```

### Table Analysis
```bash
# Analyze a table structure
EXTRACT_IMG table.png --type table
```

### General Image Analysis
```bash
# Academic analysis of an image
EXTRACT_IMG diagram.png --mode academic

# General description
EXTRACT_IMG photo.png --mode general
```

### Batch Processing with Output
```bash
# Process all images in a directory
EXTRACT_IMG --batch *.png --json --output batch_results.json
```

## Error Handling

The tool provides detailed error messages for:
- Missing image files
- Unsupported image formats
- Processor initialization failures
- Cache system errors

## Performance

- **Caching**: Dramatically reduces processing time for duplicate images
- **Superior Recognition**: EXTRACT_PDF/MinerU provides better accuracy than standalone tools
- **Batch Processing**: Efficient handling of multiple images
- **Memory Management**: Optimized for large image processing workflows

## Restoring Original Functionality

To restore the original UNIMERNET/IMG2TEXT routing (when issues are resolved):

1. **Edit EXTRACT_IMG.py**:
   - Remove the early return in `process_image()` method
   - Comment out the `return self._process_with_extract_pdf(...)` line
   - The original routing logic is preserved below the TODO comments

2. **Example restoration**:
   ```python
   # Comment out this line:
   # return self._process_with_extract_pdf(image_path, image_type, force_reprocess)
   
   # The original routing logic will then be active
   ```

3. **Test the restoration**:
   ```bash
   EXTRACT_IMG test_formula.png --type formula
   EXTRACT_IMG test_table.png --type table
   EXTRACT_IMG test_image.png --type academic
   ```

## TODO Items

- [ ] Resolve UNIMERNET model loading and recognition quality issues
- [ ] Improve IMG2TEXT API key configuration and geographic restrictions
- [ ] Optimize standalone tool performance to match EXTRACT_PDF quality
- [ ] Add configuration options to choose between processing backends
- [ ] Implement hybrid processing (use best tool for each image type)

## Dependencies

- Python 3.7+
- PIL (Pillow) for image handling
- UnimerNet dependencies (for formula/table recognition)
- Google API credentials (for IMG2TEXT functionality)

## See Also

- [UNIMERNET](UNIMERNET.md) - Standalone UnimerNet tool
- [IMG2TEXT](IMG2TEXT.md) - Image to text conversion
- [EXTRACT_PDF](EXTRACT_PDF.md) - PDF extraction with image analysis 