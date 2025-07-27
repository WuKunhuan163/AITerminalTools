# Binary Tools Available in ~/.local/bin

When working with the user, you have access to the following custom binary tools:

## RUN-Compatible Tools (PREFERRED: use `RUN --show` for clean JSON output):

### ALIAS
- **Purpose**: Create, remove, and manage permanent aliases in shell configuration files
- **Description**: Permanent Shell Alias Creation Tool
- **Usage**: `ALIAS <alias_name> <alias_command> [options]`
- **Examples**:
  - `ALIAS ll 'ls -la'`
  - `ALIAS gs 'git status'`
  - `ALIAS --remove ll`
  - `ALIAS --update`
  - `ALIAS --help`

### DOWNLOAD
- **Purpose**: Download resources from URLs to specified destination folders
- **Description**: Resource Download Tool
- **Usage**: `DOWNLOAD <url> [destination]`
- **Examples**:
  - `DOWNLOAD https://example.com/file.pdf`
  - `DOWNLOAD https://example.com/file.pdf ~/Desktop/`
  - `DOWNLOAD https://example.com/file.pdf ~/Desktop/my.pdf`

### EXPORT
- **Purpose**: Export environment variables and write to multiple shell configuration files
- **Description**: Environment Variable Export Tool
- **Usage**: `EXPORT <variable_name> <value>`
- **Examples**:
  - `EXPORT OPENROUTER_API_KEY "sk-or-v1-..."`
  - `EXPORT PATH "/usr/local/bin:$PATH"`
  - `EXPORT MY_VAR "some value"`

### EXTRACT_PDF
- **Purpose**: Extract text from PDF files using multiple extraction engines with image processing and text formatting, and post-process markdown files to replace placeholders with actual content
- **Description**: Enhanced PDF extraction using MinerU with post-processing support
- **Usage**: `EXTRACT_PDF <pdf_file> [options] | EXTRACT_PDF --post [<markdown_file>] [--post-type <type>] | EXTRACT_PDF --full <pdf_file> [options]`
- **Examples**:
  - `EXTRACT_PDF document.pdf --page 3`
  - `EXTRACT_PDF paper.pdf --page 1-5 --output-dir /path/to/output`
  - `EXTRACT_PDF paper.pdf --engine mineru-asyn --page 1-3`
  - `EXTRACT_PDF --post`
  - `EXTRACT_PDF --post document.md --post-type image`
  - `EXTRACT_PDF --post document.md --post-type all`
  - `EXTRACT_PDF --full document.pdf`
  - `EXTRACT_PDF --full paper.pdf --engine mineru --page 1-10`

### EXTRACT_IMG
- **Purpose**: Automatically detect image content types and route to appropriate processors with integrated caching
- **Description**: Intelligent Image Analysis Tool
- **Usage**: `EXTRACT_IMG [image_path] [options]`
- **Examples**:
  - `EXTRACT_IMG image.png`
  - `EXTRACT_IMG image.png --type formula`
  - `EXTRACT_IMG image.png --type table`
  - `EXTRACT_IMG --batch *.png`
  - `EXTRACT_IMG --stats`

### FILEDIALOG
- **Purpose**: Open tkinter file selection dialog to specify file types
- **Description**: File Selection Tool with tkinter GUI
- **Usage**: `FILEDIALOG [options]`
- **Examples**:
  - `FILEDIALOG`
  - `FILEDIALOG --types pdf`
  - `FILEDIALOG --types pdf,txt,doc`
  - `FILEDIALOG --types image --title "Select Image"`
  - `FILEDIALOG --multiple --types pdf`

### GOOGLE_DRIVE
- **Purpose**: Access Google Drive in browser and manage files remotely through an interactive shell interface (GDS). Supports file operations, remote Python execution, and comprehensive Google Drive API integration.
- **Description**: Google Drive access tool with GDS (Google Drive Shell) for remote file management
- **Usage**: `GOOGLE_DRIVE [url] [options] | GOOGLE_DRIVE --shell [command] | GDS [command]`
- **Examples**:
  - `GOOGLE_DRIVE`
  - `GOOGLE_DRIVE -my`
  - `GOOGLE_DRIVE https://drive.google.com/drive/my-drive`
  - `GOOGLE_DRIVE --shell`
  - `GOOGLE_DRIVE --shell pwd`
  - `GOOGLE_DRIVE --shell ls`
  - `GOOGLE_DRIVE --shell "cd test && ls"`
  - `GOOGLE_DRIVE --shell upload file.txt`
  - `GOOGLE_DRIVE --upload file.txt remote/path`
  - `GDS pwd`
  - `GDS ls`
  - `GDS mkdir test`
  - `GDS cd test`
  - `GDS upload file.txt`
  - `GOOGLE_DRIVE --create-remote-shell`
  - `GOOGLE_DRIVE --list-remote-shell`
  - `GOOGLE_DRIVE --console-setup`
  - `GOOGLE_DRIVE --desktop --status`

### IMG2TEXT
- **Purpose**: Convert images to structured text descriptions using Google Gemini Vision API with multiple analysis modes
- **Description**: Image to text conversion tool using Google Gemini Vision API
- **Usage**: `IMG2TEXT [image_path] [options]`
- **Examples**:
  - `IMG2TEXT example.png --mode academic`
  - `IMG2TEXT example.png --mode general --output result.txt`
  - `IMG2TEXT example.png --mode code_snippet`
  - `IMG2TEXT --test-connection`
  - `IMG2TEXT`

### LEARN
- **Purpose**: Create structured learning materials from topics or papers with advanced context support, paper search, and command generation
- **Description**: 智能学习系统，支持文件引用、论文搜索、命令生成等高级功能
- **Usage**: `LEARN <topic> [options] | LEARN --pdf <file> [options] | LEARN --description <text> [options] | LEARN --gen-command <description>`
- **Examples**:
  - `LEARN -o ~/tutorials -m 初学者 -s 简洁明了 "Python基础编程"`
  - `LEARN -o ~/tutorials -m 中级 --pdf "/path/to/paper.pdf"`
  - `LEARN -o ~/tutorials -m 高级 -d "3D Gaussian Splatting" --negative "Pi3"`
  - `LEARN -o ~/tutorials -m 初学者 "学习论文3.1节 @\"/path/to/paper.md\""`
  - `LEARN --gen-command "我想学习深度学习论文的前五页"`

### OPENROUTER
- **Purpose**: Call OpenRouter API with customizable query, model, and API key parameters, with cost tracking and dynamic token limits
- **Description**: OpenRouter API 调用工具
- **Usage**: `OPENROUTER <query> [options]`
- **Examples**:
  - `OPENROUTER "What is machine learning?"`
  - `OPENROUTER "解释量子计算" --model "deepseek/deepseek-r1"`
  - `OPENROUTER "Write a Python function" --key "sk-or-v1-..." --max-tokens 2000`
  - `OPENROUTER --list`
  - `OPENROUTER --default "google/gemini-2.5-flash-lite-preview-06-17"`
  - `OPENROUTER --test-connection`

### OVERLEAF
- **Purpose**: Compile LaTeX files to PDF
- **Description**: LaTeX文件编译工具，支持GUI文件选择和JSON返回值
- **Usage**: `OVERLEAF [file.tex]`
- **Examples**:
  - `OVERLEAF document.tex`
  - `OVERLEAF`

### SEARCH_PAPER
- **Purpose**: Search academic papers from multiple platforms (arXiv, Google Scholar) with web crawling
- **Description**: Enhanced Academic Paper Search Tool
- **Usage**: `SEARCH_PAPER [query] [options]`
- **Examples**:
  - `SEARCH_PAPER "machine learning"`
  - `SEARCH_PAPER "deep learning" --max-results 20`
  - `SEARCH_PAPER "NLP" --sources arxiv,google_scholar`

### UNIMERNET
- **Purpose**: Convert mathematical formulas and tables in images to text using UnimerNet neural network
- **Description**: UnimerNet Formula and Table Recognition Tool
- **Usage**: `UNIMERNET <image_path> [options]`
- **Examples**:
  - `UNIMERNET formula.png`
  - `UNIMERNET table.png --type table`
  - `UNIMERNET image.png --json --output result.json`
  - `UNIMERNET --check`
  - `UNIMERNET --stats`

### USERINPUT
- **Purpose**: Get user feedback in Cursor AI workflows
- **Description**: User Input Script for Cursor AI
- **Usage**: `USERINPUT`
- **Examples**:
  - `USERINPUT`

## Other Tools:

### RUN
- **Purpose**: Execute other tools and capture their output in JSON format with unique identifiers
- **Description**: Universal command wrapper with JSON output
- **Usage**: `RUN [--show] <command> [args...]`
- **Examples**:
  - `RUN OVERLEAF document.tex`
  - `RUN SEARCH_PAPER "3DGS" --max-results 3`
  - `RUN --show SEARCH_PAPER "3DGS" --max-results 3`

## Usage Guidelines:

1. **PREFERRED: Use RUN --show for clean output**: Always use `RUN --show TOOL_NAME [args]` to get structured JSON output and avoid verbose terminal logs
2. **For direct execution**: Use `./TOOL_NAME [args]` only when you need terminal output or interactive features
3. **Interactive modes**: Some tools support interactive mode when called without arguments
4. **File selection**: Tools like OVERLEAF and EXTRACT_PDF support GUI file selection
5. **Help**: All tools support `--help` or `-h` for usage information
6. **Avoid GUI when possible**: Always provide specific parameters when known, rather than relying on GUI file selection or interactive prompts
7. **Use USERINPUT for missing info**: If you need file paths or other parameters, use USERINPUT to ask the user instead of interactive modes
8. **Handle errors gracefully**: When encountering errors (file not found, invalid paths, etc.), use USERINPUT to get corrected information from the user
9. **Clean output preference**: Use `RUN --show` to minimize terminal noise and focus on key results

## When to Use These Tools:

- **ALIAS**: When user needs to create, remove, or manage permanent shell aliases
- **DOWNLOAD**: When user needs to download files from URLs
- **EXPORT**: When user needs to set environment variables persistently
- **EXTRACT_PDF**: When user needs to extract text from PDF files with different extraction engines
- **EXTRACT_IMG**: When user needs intelligent image analysis with automatic content type detection
- **FILEDIALOG**: When user needs to select specific file types through a GUI dialog
- **GOOGLE_DRIVE**: When user needs to access Google Drive, manage remote files through shell interface, upload/download files, execute remote Python code, or set up Google Drive API integration
- **IMG2TEXT**: When user needs to convert images to text descriptions
- **LEARN**: When user needs structured learning materials, paper analysis, context-aware tutorials, or LEARN command generation
- **OPENROUTER**: When user needs to call OpenRouter API for AI responses with cost tracking
- **OVERLEAF**: When user needs to compile LaTeX documents
- **RUN**: When user needs to execute other tools with JSON output
- **SEARCH_PAPER**: When user needs to search for academic papers
- **UNIMERNET**: When user needs to extract mathematical formulas or tables from images
- **USERINPUT**: When you need to get user feedback in workflows

Always prefer using these tools over manual implementations when the functionality matches the user's needs.