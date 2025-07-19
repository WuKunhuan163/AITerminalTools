# LEARN

## Purpose
Generate structured tutorials and learning materials for various topics and academic papers.

**Note: This tool now supports brainstorming-only mode with --no-auto-create option.**

## Description
LEARN是一个智能学习系统，能够自动生成结构化的教程、问题和示例代码。支持通用主题学习和学术论文学习，具有章节分割功能。

## Usage
```
LEARN                                    # Interactive mode
LEARN "<topic>" [options]                # General topic learning
LEARN "<pdf_path>" [options]             # Academic paper learning
```

### Options
- `--mode <mode>`: Learning mode
  - `Beginner`: Focus on core concepts and simplest usage
  - `Advanced`: Include more complex or advanced techniques  
  - `Practical`: Driven by a small, integrated project
- `--style <style>`: Explanation style
  - `Rigorous`: Accurate and professional
  - `Witty`: Use analogies, be light-hearted and humorous
- `--output-dir <path>`: Output directory for generated materials
- `--read-images`: Enable image analysis for PDF papers (default: false)
- `--no-auto-create`: Only perform brainstorming, don't create files automatically
- `--not-default`: Don't use default settings, enable interactive selection

## Examples
```
LEARN                                    # Interactive mode with FILEDIALOG
LEARN "Python basics" --mode Beginner   # General topic learning
LEARN "Machine Learning" --mode Advanced --style Witty
LEARN "/path/to/paper.pdf" --read-images # Academic paper learning
LEARN "/path/to/paper.pdf" --mode Practical --output-dir ~/tutorials
LEARN "AI Ethics" --mode Practical --style Witty --no-auto-create
```

## Interactive Mode
When run without arguments, LEARN enters interactive mode:
1. Choose between general topic or academic paper learning
2. Use FILEDIALOG tool to choose output directory
3. Configure learning parameters through prompts
4. Generate and confirm the command before execution

## Output Structure
### General Topic Learning
```
<output_dir>/
├── learn_<topic_name>/
│   ├── README.md           # Project overview
│   ├── tutorial.md         # Main tutorial
│   ├── questions.md        # Self-assessment questions
│   └── src/               # Example code (if applicable)
```

### Paper Learning
```
<output_dir>/
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

## Dependencies
- Python 3.8+
- PyMuPDF>=1.23.0 (for PDF processing)
- FILEDIALOG tool (for interactive directory selection)

## Integration
The LEARN system integrates with existing tools:
- Uses FILEDIALOG for directory and file selection in interactive mode
- Supports RUN --show for JSON output
- Compatible with the existing PDF extractor module

## Features
- **Interactive Setup**: GUI-based file and directory selection
- **Flexible Learning Modes**: Beginner, Advanced, Practical approaches
- **Multiple Styles**: Rigorous or Witty explanations
- **Paper Processing**: Automatic chapter segmentation and analysis
- **Image Analysis**: Optional image extraction and analysis for PDFs
- **Structured Output**: Organized learning materials with tutorials and questions 