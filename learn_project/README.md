# LEARN Project System

A comprehensive learning system that automatically generates tutorials, questions, and example code for various topics, with special support for academic paper learning with chapter-based segmentation.

## Features

### General Topic Learning
- Generate structured tutorials for any topic
- Create self-assessment questions with collapsible answers
- Support for different learning modes (Beginner, Advanced, Practical)
- Support for different explanation styles (Rigorous, Witty)

### Paper Learning (Special Feature)
- Process PDF papers in chunks (max 5 pages by default)
- Automatically segment content by chapters:
  - Background/Introduction
  - Methodology
  - Evaluation/Results
  - Future Work
- Optional image analysis using existing PDF extractor
- Generate chapter-specific tutorials
- Create comprehensive questions based on paper content

## Installation

1. Ensure you have the required dependencies:
```bash
pip install PyMuPDF>=1.23.0
```

2. The system integrates with the existing `pdf_extractor` module in the parent directory.

## Usage

### Command Line Interface

#### General Topic Learning
```bash
python learn_project/main.py 'LEARN "Python basics" --mode Beginner --style Rigorous'
python learn_project/main.py 'LEARN "Machine Learning" --mode Advanced --style Witty'
```

#### Paper Learning
```bash
# Basic paper learning (no image analysis)
python learn_project/main.py 'LEARN "/path/to/paper.pdf"'

# With image analysis
python learn_project/main.py 'LEARN "/path/to/paper.pdf" --read-images'

# Custom settings
python learn_project/main.py 'LEARN "/path/to/paper.pdf" --read-images --max-pages 3 --chapters "background,methodology"'
```

### Python API

```python
from learn_project import LearnSystem

# Initialize the system
learn_system = LearnSystem()

# Process a general topic
result = learn_system.process_learn_command('LEARN "Python basics" --mode Beginner')

# Process a paper
result = learn_system.process_learn_command('LEARN "/path/to/paper.pdf" --read-images')

if result["success"]:
    print(f"Created project at: {result['project_path']}")
    print(f"Files created: {result['created_files']}")
else:
    print(f"Error: {result['error']}")
```

## Command Options

### General Options
- `--mode`: Learning mode
  - `Beginner`: Focus on core concepts and simplest usage
  - `Advanced`: Include more complex or advanced techniques
  - `Practical`: Driven by a small, integrated project

- `--style`: Explanation style
  - `Rigorous`: Accurate and professional
  - `Witty`: Use analogies, be light-hearted and humorous

### Paper-Specific Options
- `--read-images`: Enable image analysis (default: false)
- `--max-pages N`: Maximum pages to process at once (default: 5)
- `--chapters "list"`: Comma-separated list of chapters to focus on
  - Default: `"background,methodology,evaluation,future_work"`

## Output Structure

### General Topic Learning
```
learn_project/
├── learn_<topic_name>/
│   ├── README.md           # Project overview
│   ├── tutorial.md         # Main tutorial
│   ├── questions.md        # Self-assessment questions
│   └── src/               # Example code (if applicable)
```

### Paper Learning
```
learn_project/
├── learn_paper_<paper_name>/
│   ├── README.md           # Project overview
│   ├── tutorial.md         # Combined tutorial from all chapters
│   ├── questions.md        # Paper-specific questions
│   └── docs/              # Individual chapter tutorials
│       ├── <paper>_background_tutorial.md
│       ├── <paper>_methodology_tutorial.md
│       ├── <paper>_evaluation_tutorial.md
│       └── <paper>_future_work_tutorial.md
```

## Integration with User Rules

The system integrates with the existing user rule system. When a `LEARN` command is detected:

1. The `learn_prompt_builder.py` checks if it's a paper learning command
2. If it's a paper, it delegates to the new `learn_project` system
3. If it's a general topic, it uses the original prompt builder workflow

## Architecture

### Core Components

1. **LearnSystem** (`learn_core.py`): Main orchestrator
2. **PaperProcessor** (`paper_processor.py`): Handles PDF paper processing
3. **Utils** (`utils.py`): Command parsing and utility functions
4. **Main** (`main.py`): Command-line entry point

### Key Functions

- `parse_learn_command()`: Parses LEARN commands and extracts parameters
- `create_project_structure()`: Creates the basic project directory structure
- `process_paper()`: Processes PDF papers in chunks with chapter segmentation
- `create_chapter_tutorials()`: Generates tutorials for each paper chapter
- `identify_paper_sections()`: Automatically categorizes paper content by section type

## Testing

Run the test suite:
```bash
python learn_project/test_learn_system.py
```

## Examples

### Example 1: Learning Python Basics
```bash
python learn_project/main.py 'LEARN "Python basics" --mode Beginner --style Rigorous'
```

This creates a structured learning project with:
- A comprehensive tutorial covering Python fundamentals
- Self-assessment questions with collapsible answers
- Example code demonstrating key concepts

### Example 2: Learning from a Research Paper
```bash
python learn_project/main.py 'LEARN "/path/to/research_paper.pdf" --read-images --max-pages 3'
```

This processes the paper and creates:
- Chapter-specific tutorials for background, methodology, evaluation, and future work
- A combined tutorial integrating all chapters
- Questions tailored to the paper's content
- Image analysis if `--read-images` is enabled

## Error Handling

The system includes comprehensive error handling:
- File not found errors for PDF papers
- PDF processing errors
- Command parsing errors
- Project creation errors

All errors are reported with helpful messages and suggestions for resolution.

## Future Enhancements

- Support for more document formats (Word, PowerPoint, etc.)
- Integration with external knowledge bases
- Advanced NLP for better content analysis
- Interactive tutorial generation
- Integration with learning management systems

## Contributing

To extend the system:

1. Add new processors to `paper_processor.py` for different document types
2. Extend `utils.py` with new parsing functions
3. Add new learning modes or styles to `learn_core.py`
4. Update tests in `test_learn_system.py`

## License

This project is part of the larger learning assistant system and follows the same licensing terms. 