# FILEDIALOG - File Selection Tool

## Overview
FILEDIALOG is a file selection tool that opens a tkinter file selection dialog to let users specify certain types of files. It supports various file type filters, custom dialog titles, initial directories, and both single and multiple file selection modes.

## Usage
```bash
FILEDIALOG [options]
```

## Options
- `--types <types>`: Comma-separated list of file types (default: all)
- `--title <title>`: Dialog title (default: "Select File")
- `--dir <directory>`: Initial directory (default: current directory)
- `--multiple`: Allow multiple file selection
- `--help, -h`: Show help message

## File Types
### Predefined Types
- `pdf`: PDF files
- `txt`: Text files
- `doc`: Word documents (.doc, .docx)
- `docx`: Word documents (.docx)
- `image`: Image files (png, jpg, jpeg, gif, bmp, tiff)
- `png`: PNG images
- `jpg`, `jpeg`: JPEG images
- `gif`: GIF images
- `tex`: LaTeX files
- `py`: Python files
- `js`: JavaScript files
- `html`: HTML files
- `css`: CSS files
- `json`: JSON files
- `xml`: XML files
- `csv`: CSV files
- `xlsx`: Excel files
- `ppt`: PowerPoint files
- `zip`: Archive files
- `mp3`: Audio files
- `mp4`: Video files
- `all`: All files

### Custom Extensions
You can also specify custom file extensions:
- Use format like `*.ext` or just `ext`
- Example: `--types "*.log"` or `--types "log"`

## Examples

### Basic Usage
```bash
# Select any file
FILEDIALOG

# Select PDF files only
FILEDIALOG --types pdf

# Select multiple file types
FILEDIALOG --types pdf,txt,doc
```

### Advanced Usage
```bash
# Select image files with custom title
FILEDIALOG --types image --title "Select Image"

# Select log files from specific directory
FILEDIALOG --types "*.log" --dir /var/log

# Select multiple PDF files
FILEDIALOG --multiple --types pdf

# Select from Desktop with custom title
FILEDIALOG --dir ~/Desktop --title "Choose Document"
```

## Output

### Interactive Mode
In interactive mode, the tool will:
1. Open a file selection dialog
2. Display the selected file path(s)
3. Show file information (size, etc.)

### RUN Environment
When used with RUN, the tool outputs JSON:

#### Single File Selection
```json
{
  "success": true,
  "message": "File selected successfully",
  "selected_file": "/path/to/selected/file.pdf",
  "file_name": "file.pdf",
  "file_size": 1024000
}
```

#### Multiple File Selection
```json
{
  "success": true,
  "message": "Selected 3 file(s)",
  "selected_files": [
    "/path/to/file1.pdf",
    "/path/to/file2.pdf",
    "/path/to/file3.pdf"
  ],
  "file_count": 3
}
```

#### Cancelled Selection
```json
{
  "success": false,
  "message": "File selection cancelled by user",
  "selected_files": null
}
```

## Error Handling
- If tkinter is not available, the tool will report an error
- If the specified initial directory doesn't exist, an error will be shown
- If the user cancels the dialog, it will be reported as cancelled
- Invalid arguments will show appropriate error messages

## Dependencies
- Python 3.x
- tkinter (usually included with Python)

## Integration with RUN
FILEDIALOG is fully compatible with the RUN command wrapper:

```bash
# Test with RUN --show
RUN --show FILEDIALOG --types pdf

# Use in RUN environment
RUN FILEDIALOG --types image --title "Select Image"
```

## Notes
- The tool automatically adds "All files" as the last option in the file type list
- File selection dialogs will remember the last used directory within the session
- The tool supports both absolute and relative paths for the initial directory
- Multiple file selection returns an array of file paths
- Single file selection returns a single file path string 