# Cursor User Rules for Toolized Commands

## Rule 1: PDF_EXTRACT Command Handler

```yaml
---
description: 'Handles PDF_EXTRACT commands by calling the PDF extraction tool'
globs:
  - 'PDF_EXTRACT*'
alwaysApply: false
prompt: |-
  You have received a PDF_EXTRACT command. Execute the following steps:
  
  1. Run the command: python others/tool_dispatcher.py "{userInput}"
  2. If the command is just "PDF_EXTRACT", the system will:
     - Open a file selector dialog titled "Choose the PDF"
     - Prompt for page range (default: all pages)
     - Ask about image analysis options
     - Ask about debug mode
  3. Report the results to the user
  4. If successful, inform the user about the generated markdown file location
---
```

## Rule 2: LEARN Command Handler

```yaml
---
description: 'Handles LEARN commands with enhanced prompt generation'
globs:
  - 'LEARN*'
alwaysApply: false
prompt: |-
  You have received a LEARN command. Execute the following steps:
  
  1. Run the command: python learn_project/learn_cursor_userinput.py
  2. The system will:
     - Process the LEARN command interactively or directly
     - Generate a structured prompt markdown file
     - Save it to learn_project/prompt/ directory
     - Output the latest prompt path and content
  3. Extract the generated prompt content and use it to create learning materials
  4. Report the results and provide next steps for learning
---
```

## Rule 3: Combined Workflow Handler

```yaml
---
description: 'Handles combined commands that require multiple tools'
globs:
  - 'LEARN *.pdf*'
alwaysApply: false
prompt: |-
  You have received a LEARN command with PDF processing. Execute the following steps:
  
  1. Run the command: python others/tool_dispatcher.py "{userInput}"
  2. The dispatcher will automatically:
     - First extract the PDF content
     - Then create learning materials based on the PDF
  3. Report the results to the user
  4. If successful, inform the user about both the extracted PDF data and the learning project
---
```

## Usage Examples

### PDF Extraction
```
PDF_EXTRACT "paper.pdf" --no-image-api --page 1-5
```

### Learning Project Creation
```
LEARN "Python basics" --mode Beginner --style Rigorous
LEARN
```

### Combined PDF Learning
```
LEARN "paper.pdf" --read-images --max-pages 3
```

## Command Mapping

| User Input | CLI Tool | Description |
|------------|----------|-------------|
| `PDF_EXTRACT [args]` | `pdf_extractor/pdf_extract_cli.py` | Extract PDF content to markdown |
| `LEARN [args]` | `learn_project/learn_cli.py` | Create learning materials |
| `LEARN [pdf] [args]` | `others/tool_dispatcher.py` | Combined PDF + learning workflow |

## Tool Paths

- **PDF_EXTRACT**: `python pdf_extractor/pdf_extract_cli.py`
- **LEARN**: `python learn_project/learn_cli.py`
- **Dispatcher**: `python others/tool_dispatcher.py` 