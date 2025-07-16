# GOOGLE_DRIVE

Google Drive access tool

## Description

GOOGLE_DRIVE is a simple tool for opening Google Drive in your default web browser. It supports custom URLs and has a special flag for accessing My Drive directly.

## Usage

```bash
GOOGLE_DRIVE [url] [options]
GOOGLE_DRIVE  # Open main Google Drive
```

## Options

- `-my`: Open My Drive (https://drive.google.com/drive/u/0/my-drive)
- `--help, -h`: Show help message

## Examples

### Basic Usage
```bash
# Open main Google Drive
GOOGLE_DRIVE

# Open My Drive folder
GOOGLE_DRIVE -my

# Open specific Google Drive URL
GOOGLE_DRIVE https://drive.google.com/drive/my-drive
```

### RUN Integration
```bash
# Get JSON output
RUN --show GOOGLE_DRIVE
RUN --show GOOGLE_DRIVE -my
```

## Features

- **Quick Access**: Fast way to open Google Drive
- **My Drive Shortcut**: Direct access to My Drive with -my flag
- **Custom URLs**: Support for specific Google Drive URLs
- **RUN Compatible**: Works with RUN command for JSON output
- **Cross-Platform**: Works on macOS, Linux, and Windows

## Output

When executed directly, the tool opens Google Drive in your default browser and shows status messages. When used with RUN, it returns JSON with operation status and URL information.

## Dependencies

- Python 3.9+
- webbrowser module (included with Python)

## Notes

- Opens in your default web browser
- Requires internet connection
- RUN mode provides JSON output for automation
- Direct execution shows browser opening status 