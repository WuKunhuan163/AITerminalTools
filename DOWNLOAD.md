# DOWNLOAD

Resource Download Tool

## Description

DOWNLOAD is a versatile tool for downloading resources from URLs to specified destination folders. It supports progress tracking, automatic filename detection, and various file types.

## Usage

```bash
DOWNLOAD <url> [destination]
```

## Arguments

- `url`: URL of the resource to download
- `destination`: Destination file path or directory (default: current directory)

## Options

- `--help, -h`: Show help message

## Examples

### Basic Usage
```bash
# Download to current directory
DOWNLOAD https://example.com/file.pdf

# Download to specific directory
DOWNLOAD https://example.com/file.pdf ~/Desktop/

# Download with custom filename
DOWNLOAD https://example.com/file.pdf ~/Desktop/my.pdf

# Download various file types
DOWNLOAD https://example.com/image.jpg ~/Downloads/
DOWNLOAD https://example.com/archive.zip ~/Downloads/
DOWNLOAD https://example.com/document.docx ~/Documents/
```

### RUN Integration
```bash
# Get JSON output
RUN --show DOWNLOAD https://example.com/file.pdf ~/Desktop/
```

## Features

- **Progress Tracking**: Shows download progress with percentage and bytes
- **Automatic Filename**: Extracts filename from URL if not specified
- **Directory Support**: Can download to directories or specific file paths
- **File Type Support**: Handles various file types and content types
- **Resume Support**: Handles connection issues gracefully
- **RUN Compatible**: Works with RUN command for JSON output
- **Path Expansion**: Supports ~ (home directory) expansion

## Output

When executed directly, the tool shows download progress, final file location, and size information. When used with RUN, it returns JSON with download status, file path, size, and content type.

## Dependencies

- Python 3.9+
- requests library
- Internet connection

## Notes

- Automatically creates destination directories if they don't exist
- Uses appropriate User-Agent for better compatibility
- Handles redirects and various HTTP response codes
- RUN mode provides JSON output for automation
- Direct execution shows real-time progress
- Supports both HTTP and HTTPS protocols 