# UNIMERNET - UnimerNet Formula and Table Recognition Tool

## Overview

UNIMERNET is a standalone tool for mathematical formula and table recognition using the UnimerNet neural network. It provides high-accuracy recognition of mathematical expressions, equations, and table structures from images.

## Features

- **Mathematical Formula Recognition**: Converts formula images to LaTeX or text format
- **Table Structure Recognition**: Extracts table content and structure
- **Centralized Caching**: Advanced hash-based caching system
- **Batch Processing**: Process multiple images efficiently
- **Multiple Output Formats**: Text and JSON output options
- **Cache Management**: Built-in cache statistics and cleanup

## Usage

### Basic Usage

```bash
# Recognize a formula image
UNIMERNET formula.png

# Recognize a table image
UNIMERNET table.png --type table

# Check if UnimerNet is available
UNIMERNET --check
```

### Content Type Specification

```bash
# Explicit formula recognition
UNIMERNET image.png --type formula

# Explicit table recognition
UNIMERNET image.png --type table

# Auto-detect content type
UNIMERNET image.png --type auto
```

### Batch Processing

```bash
# Process multiple images
UNIMERNET --batch formula1.png formula2.png table1.png

# Batch with specific type
UNIMERNET --batch *.png --type formula
```

### Output Options

```bash
# JSON output
UNIMERNET formula.png --json

# Save to file
UNIMERNET formula.png --output results.json

# Combine JSON and file output
UNIMERNET formula.png --json --output results.json
```

### Cache Management

```bash
# Show cache statistics
UNIMERNET --stats

# Disable cache for processing
UNIMERNET formula.png --no-cache

# Force reprocessing (ignore cache)
UNIMERNET formula.png --force
```

## Command Line Options

- `image_path`: Path to image file (optional for some commands)
- `--type {formula,table,auto}`: Content type hint (default: auto)
- `--force`: Force reprocessing even if cached
- `--batch`: Process multiple images
- `--no-cache`: Disable cache system
- `--stats`: Show cache statistics
- `--output`: Specify a file to save the result
- `--json`: Output in JSON format
- `--check`: Check if UnimerNet is available

## Recognition Capabilities

### Mathematical Formulas
- Complex equations and expressions
- Greek letters and mathematical symbols
- Subscripts and superscripts
- Fractions and integrals
- Matrix notation
- LaTeX output format

### Table Structures
- Cell content extraction
- Row and column detection
- Table boundary identification
- Merged cell handling
- Text and numeric content

## Integration

UNIMERNET integrates with:
- **EXTRACT_IMG**: Used as the formula/table processor
- **EXTRACT_PDF**: Processes mathematical content in PDFs
- **Centralized Cache System**: Shares cache with other tools

## Cache System

Uses the same advanced caching system as other tools:
- **Dual Hash Algorithm**: SHA256 + MD5 for collision avoidance
- **Centralized Storage**: Cached in `EXTRACT_IMG_CACHE/`
- **Metadata Tracking**: Timestamps and processing information
- **Automatic Deduplication**: Avoids reprocessing identical images

## Examples

### Formula Recognition
```bash
# Simple formula
UNIMERNET "E=mc^2.png" --type formula

# Complex equation with output
UNIMERNET equation.png --json --output equation_result.json
```

### Table Recognition
```bash
# Extract table structure
UNIMERNET data_table.png --type table

# Batch table processing
UNIMERNET --batch table*.png --type table --json
```

### Availability Check
```bash
# Check system status
UNIMERNET --check

# Expected output if available:
# UnimerNet is available and ready
# Cache: X images cached
```

## Error Handling

Common error scenarios and solutions:

### UnimerNet Not Available
```bash
❌ UnimerNet is not available
Please ensure UnimerNet dependencies are installed
```
**Solution**: Install UnimerNet dependencies or check installation

### Image File Issues
```bash
{
  "success": false,
  "error": "Image file not found: image.png"
}
```
**Solution**: Verify image file path and format

### Processing Failures
```bash
{
  "success": false,
  "error": "UnimerNet processing failed: [details]"
}
```
**Solution**: Check image quality and format compatibility

## Performance

- **Caching**: Dramatically reduces processing time for duplicate images
- **Batch Processing**: Efficient handling of multiple images
- **Memory Management**: Optimized for large recognition workflows
- **GPU Acceleration**: Utilizes GPU when available for faster processing

## Output Formats

### Text Output
```
Image: formula.png
Type: formula
From cache: false

Result:
E = mc^2
```

### JSON Output
```json
{
  "success": true,
  "result": "E = mc^2",
  "image_path": "formula.png",
  "content_type": "formula",
  "processor": "unimernet",
  "timestamp": "2025-07-18T23:15:00.000000",
  "from_cache": false
}
```

## Dependencies and Configuration

### System Requirements
- Python 3.7+
- PyTorch 1.9.0+ (for neural network processing)
- transformers 4.21.0+ (HuggingFace transformers library)
- PIL (Pillow) for image handling
- NumPy for numerical operations

### Model Configuration
- **Model**: UnimerNet Base Model
- **Model Path**: `UNIMERNET_PROJ/unimernet_models/unimernet_base/`
- **Model Files Required**:
  - `pytorch_model.bin` (1.2GB) - Main model weights
  - `config.json` - Model configuration
  - `tokenizer.json` - Tokenizer configuration
  - `preprocessor_config.json` - Image preprocessing config
  - `tokenizer_config.json` - Tokenizer settings

### Transformers Version Compatibility
- **Recommended**: transformers >= 4.21.0
- **Tested with**: transformers 4.21.0 - 4.35.0
- **Note**: Newer versions may require attention implementation updates

### Model Architecture
- **Encoder**: Swin Transformer (Vision Encoder)
- **Decoder**: BART-based text decoder
- **Attention**: Configurable attention implementation
- **Device Support**: CPU, CUDA, MPS (Apple Silicon)

### Performance Configuration
- **CPU Mode**: Default, works on all systems
- **GPU Mode**: Automatically detected if CUDA available
- **MPS Mode**: Apple Silicon acceleration (experimental)
- **Memory**: Requires ~2GB RAM for model loading
- **Batch Size**: Configurable (default: 32 for batch processing)

## Installation Notes

### Quick Setup
1. Ensure UnimerNet dependencies are properly installed
2. Download required model files to `UNIMERNET_PROJ/unimernet_models/unimernet_base/`
3. Configure GPU support if available
4. Verify installation with `UNIMERNET --check`

### Detailed Installation

#### 1. Install Dependencies
```bash
pip install torch torchvision torchaudio
pip install transformers>=4.21.0
pip install pillow numpy
```

#### 2. Model Files Setup
The model files should be located in:
```
UNIMERNET_PROJ/
├── unimernet_models/
│   └── unimernet_base/
│       ├── pytorch_model.bin    # Main model weights (1.2GB)
│       ├── config.json          # Model configuration
│       ├── tokenizer.json       # Tokenizer data
│       ├── preprocessor_config.json
│       └── tokenizer_config.json
```

#### 3. Verify Installation
```bash
UNIMERNET --check
```

Expected output:
```
UnimerNet is available and ready
Cache: X images cached
```

### Troubleshooting Installation

#### Model Loading Issues
If you see warnings about uninitialized weights:
```
Some weights of UnimernetModel were not initialized from the model checkpoint...
```
This indicates the model files may not be properly loaded. Check:
1. Model file paths are correct
2. Model files are not corrupted
3. transformers version compatibility

#### Memory Issues
For systems with limited RAM:
- Use CPU mode instead of GPU
- Reduce batch size in batch processing
- Process images individually instead of in batches

#### Attention Implementation
For MPS (Apple Silicon) or NPU devices:
- The tool automatically uses "eager" attention implementation
- This may be slower but more compatible

### MinerU Integration and Configuration

UNIMERNET now includes MinerU-compatible configuration for better model management:

#### MinerU Configuration File
Create a `mineru.json` file in your home directory for advanced configuration:

```json
{
  "models-dir": {
    "pipeline": "/path/to/your/models",
    "vlm": "/path/to/vlm/models"
  },
  "device": "cuda",
  "formula_config": {
    "enable": true
  },
  "table_config": {
    "enable": true
  }
}
```

#### Environment Variables
Control behavior with environment variables:

```bash
# Device selection
export MINERU_DEVICE_MODE=cuda          # Force device (cuda/cpu/mps/npu)

# Model source
export MINERU_MODEL_SOURCE=huggingface  # huggingface/modelscope/local

# Feature toggles
export MINERU_FORMULA_ENABLE=true       # Enable formula recognition
export MINERU_TABLE_ENABLE=true         # Enable table recognition

# Configuration file
export MINERU_TOOLS_CONFIG_JSON=~/my-mineru-config.json
```

#### MinerU Model Downloads
UNIMERNET can automatically download models from MinerU repositories:

```bash
# Download from HuggingFace (default)
export MINERU_MODEL_SOURCE=huggingface

# Download from ModelScope (for Chinese users)
export MINERU_MODEL_SOURCE=modelscope

# Use local models
export MINERU_MODEL_SOURCE=local
```

#### Full MinerU Installation (Optional)
For complete MinerU compatibility, install MinerU:

```bash
# Install MinerU
pip install mineru

# Or install from source
git clone https://github.com/opendatalab/MinerU.git
cd MinerU
pip install -e .
```

#### Model Repository Information
- **HuggingFace**: `opendatalab/PDF-Extract-Kit-1.0`
- **ModelScope**: `OpenDataLab/PDF-Extract-Kit-1.0`
- **UnimerNet Model Path**: `models/MFR/unimernet_hf_small_2503`

#### Configuration Priority
1. Explicit parameters in code
2. Environment variables
3. Configuration file (`mineru.json`)
4. Default values

## Troubleshooting

### Common Issues

1. **Model Loading Failures**: Check model file paths and permissions
2. **GPU Memory Issues**: Reduce batch size or use CPU processing
3. **Image Format Issues**: Ensure images are in supported formats (PNG, JPG, etc.)
4. **Cache Corruption**: Clear cache directory if needed

### Debug Mode

For detailed debugging information:
```bash
# Enable verbose logging
python3 UNIMERNET.py image.png --json 2>&1 | grep -E "(ERROR|WARNING|INFO)"
```

## See Also

- [EXTRACT_IMG](EXTRACT_IMG.md) - Intelligent image analysis tool
- [EXTRACT_PDF](EXTRACT_PDF.md) - PDF extraction with formula recognition
- [IMG2TEXT](IMG2TEXT.md) - General image to text conversion 