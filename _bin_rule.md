# Binary Tools Available in ~/.local/bin

When working with the user, you have access to the following custom binary tools:

## RUN-Compatible Tools (can be used with `RUN --show` for JSON output):

### OVERLEAF
- **Purpose**: Compile LaTeX files to PDF
- **Description**: LaTeX文件编译工具，支持GUI文件选择和JSON返回值
- **Usage**: `OVERLEAF [file.tex]`
- **Examples**:
  - `OVERLEAF document.tex`
  - `OVERLEAF  # GUI file selection`

### SEARCH_PAPER
- **Purpose**: Search academic papers from multiple platforms (arXiv, Google Scholar, Semantic Scholar)
- **Description**: Enhanced Academic Paper Search Tool
- **Usage**: `SEARCH_PAPER [query] [options]`
- **Examples**:
  - `SEARCH_PAPER  # Interactive mode`
  - `SEARCH_PAPER "machine learning"`
  - `SEARCH_PAPER "deep learning" --max-results 20`
  - `SEARCH_PAPER "NLP" --sources arxiv,semantic_scholar`

### EXPORT
- **Purpose**: Export environment variables and write to multiple shell configuration files
- **Description**: Environment Variable Export Tool
- **Usage**: `EXPORT <variable_name> <value>`
- **Examples**:
  - `EXPORT OPENROUTER_API_KEY "sk-or-v1-..."`
  - `EXPORT PATH "/usr/local/bin:$PATH"`
  - `EXPORT MY_VAR "some value"`

### DOWNLOAD
- **Purpose**: Download resources from URLs to specified destination folders
- **Description**: Resource Download Tool
- **Usage**: `DOWNLOAD <url> [destination]`
- **Examples**:
  - `DOWNLOAD https://example.com/file.pdf`
  - `DOWNLOAD https://example.com/file.pdf ~/Desktop/`
  - `DOWNLOAD https://example.com/file.pdf ~/Desktop/my.pdf`

### USERINPUT
- **Purpose**: Get user feedback in Cursor AI workflows
- **Description**: User Input Script for Cursor AI
- **Usage**: `USERINPUT`
- **Examples**:
  - `USERINPUT`

### FILE_SELECT
- **Purpose**: Open tkinter file selection dialog to specify file types
- **Description**: File Selection Tool with tkinter GUI
- **Usage**: `FILE_SELECT [options]`
- **Examples**:
  - `FILE_SELECT`
  - `FILE_SELECT --types pdf`
  - `FILE_SELECT --types pdf,txt,doc`
  - `FILE_SELECT --types image --title "Select Image"`
  - `FILE_SELECT --multiple --types pdf`

### ALIAS
- **Purpose**: Create permanent aliases in shell configuration files
- **Description**: Permanent Shell Alias Creation Tool
- **Usage**: `ALIAS <alias_name> <alias_command>`
- **Examples**:
  - `ALIAS ll 'ls -la'`
  - `ALIAS gs 'git status'`
  - `ALIAS --help`

## Usage Guidelines:

1. **For RUN-compatible tools**: Use `RUN --show TOOL_NAME [args]` to get JSON output
2. **For direct execution**: Use `./TOOL_NAME [args]` for terminal output
3. **Interactive modes**: Some tools support interactive mode when called without arguments
4. **File selection**: Tools like OVERLEAF and EXTRACT_PDF support GUI file selection
5. **Help**: All tools support `--help` or `-h` for usage information
6. **Avoid GUI when possible**: Always provide specific parameters when known, rather than relying on GUI file selection or interactive prompts
7. **Use USERINPUT for missing info**: If you need file paths or other parameters, use USERINPUT to ask the user instead of interactive modes
8. **Handle errors gracefully**: When encountering errors (file not found, invalid paths, etc.), use USERINPUT to get corrected information from the user

## When to Use These Tools:

- **OVERLEAF**: When user needs to compile LaTeX documents
- **SEARCH_PAPER**: When user needs to search for academic papers
- **EXPORT**: When user needs to set environment variables persistently
- **DOWNLOAD**: When user needs to download files from URLs
- **USERINPUT**: When you need to get user feedback in workflows
- **FILE_SELECT**: When user needs to select specific file types through a GUI dialog
- **ALIAS**: When user needs to create permanent shell aliases

Always prefer using these tools over manual implementations when the functionality matches the user's needs.