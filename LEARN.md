# LEARN

## Purpose
Generate structured tutorials and learning materials for various topics and academic papers with advanced context support.

## Description
LEARN是一个智能学习系统，能够自动生成结构化的教程、问题和示例代码。支持通用主题学习和学术论文学习，具有文件引用、智能搜索、负面提示等高级功能。

## Usage

### Basic Usage
```bash
LEARN                                    # Interactive mode
LEARN "<topic>" [options]                # General topic learning  
LEARN --file "<file_path>" [options]     # Direct file processing (PDF/MD/TXT)
LEARN --description "<description>" [options]  # Paper search and download
LEARN --paper-based "<topic>" [options]  # Force paper-based learning mode
LEARN --gen-command "<description>"       # Generate LEARN command
```

### Required Parameters
- `-o, --output-dir <path>`: Output directory for generated materials

### Learning Parameters
- `-m, --mode <mode>`: Learning level
  - `初学者`: Focus on core concepts and fundamentals
  - `中级`: Include intermediate techniques and applications
  - `高级`: Advanced concepts and complex implementations
  - `专家`: Expert-level analysis and cutting-edge techniques
- `-s, --style <style>`: Explanation style
  - `简洁明了`: Concise and clear explanations
  - `详细深入`: Detailed and in-depth analysis
  - `实例丰富`: Rich examples and practical applications
  - `理论导向`: Theory-focused with rigorous explanations

### File Input Options
- `--file <path>`: Direct file path (supports PDF, MD, TXT files)
- `-u, --url <url>`: Paper URL for download
- `-d, --description <text>`: Paper description for search and download
- `--negative <text>`: Negative prompt to exclude unwanted papers
- `--sources <sources>`: Specify paper search engines (comma-separated: arxiv,google_scholar), default: auto-recommend
- `--read-images`: Enable image/formula/table processing in PDFs

### Advanced Options
- `--model <model>`: Specify OpenRouter model (default: auto)
- `--max-tokens <num>`: Maximum tokens per API call
- `--context`: Treat description as direct context for brainstorming, skip paper search
- `--paper-based`: Force paper-based learning mode, search and download papers even with simple topic descriptions
- `--not-default`: Disable default settings, enable interactive selection
- `--no-override-material`: Avoid overwriting existing files, auto-rename output directory
- `--brainstorm-only`: Only perform brainstorming, don't create files
- `--gen-command <description>`: Generate LEARN command based on description

### File Reference Support
LEARN supports @"file_path" syntax to include file content in prompts:
- `@"/path/to/file.md"`: Include markdown file content
- `@"/path/to/file.txt"`: Include text file content
- `@"/path/to/file.pdf"`: Include PDF file content (processed with basic engine)
- When @file_path is detected, `--context` mode is automatically enabled
- File references skip paper search and use content directly for brainstorming

## Examples

### General Topic Learning
```bash
LEARN -o ~/tutorials -m 初学者 -s 简洁明了 "Python基础编程"
LEARN -o ~/tutorials -m 高级 -s 实例丰富 "机器学习算法"

# Force paper-based learning for topics
LEARN -o ~/tutorials -m 中级 --paper-based "深度学习优化算法"
LEARN -o ~/tutorials -m 高级 --paper-based "Transformer架构" --negative "BERT"
```

### Academic Paper Learning
```bash
# Direct PDF processing
LEARN -o ~/tutorials -m 中级 --file "/path/to/paper.pdf"

# Search and download paper
LEARN -o ~/tutorials -m 初学者 -d "3D Gaussian Splatting mesh reconstruction"

# With negative prompt to exclude specific papers
LEARN -o ~/tutorials -m 中级 -d "deep learning" --negative "GAN, generative models"

# Specify search engines
LEARN -o ~/tutorials -m 中级 -d "machine learning" --sources "arxiv,google_scholar"
LEARN -o ~/tutorials -m 高级 -d "environmental policy" --sources "google_scholar"

# With image processing enabled
LEARN -o ~/tutorials -m 高级 --file "/path/to/paper.pdf" --read-images
```

### File Input Options
```bash
# Direct file processing (with brainstorming)
LEARN -o ~/tutorials -m 中级 --file "/path/to/paper.pdf"
LEARN -o ~/tutorials -m 初学者 --file "/path/to/document.md"

# Direct file processing with context mode (skip brainstorming)
LEARN -o ~/tutorials -m 中级 --file "/path/to/paper.pdf" --context
LEARN -o ~/tutorials -m 初学者 --file "/path/to/document.txt" --context

# URL processing (with brainstorming)
LEARN -o ~/tutorials -m 高级 -u "https://arxiv.org/pdf/2106.02613.pdf"

# URL processing with context mode (skip brainstorming)
LEARN -o ~/tutorials -m 高级 -u "https://arxiv.org/pdf/2106.02613.pdf" --context
```

### File Reference with @ Symbol
```bash
# @ file references with brainstorming (default)
LEARN -o ~/tutorials -m 初学者 -d "学习论文3.1节的技术原理 @\"/path/to/paper.md\""

# @ file references with context mode (skip brainstorming)
LEARN -o ~/tutorials -m 初学者 -d "学习论文3.1节的技术原理 @\"/path/to/paper.md\"" --context

# Multiple file references with context mode
LEARN -o ~/tutorials -m 中级 -d "比较两篇论文的方法 @\"/paper1.md\" @\"/paper2.md\"" --context

# Direct context content (skip brainstorming)
LEARN -o ~/tutorials -m 专家 -d "深度学习核心概念：神经网络、反向传播、优化算法" --context
```

### Command Generation
```bash
# Generate LEARN command from description
LEARN --gen-command "我想学习A论文的前五页"
LEARN --gen-command "帮我创建深度学习入门教程"
LEARN --gen-command "分析这篇NLP论文的核心算法"
LEARN --gen-command "基于最新论文学习Transformer优化技术"
```

## Interactive Mode
When run without arguments, LEARN enters interactive mode:
1. Choose between general topic or academic paper learning
2. Configure learning parameters through prompts
3. Use GUI dialogs for file and directory selection
4. Generate and confirm the command before execution

## Paper Search and Download
LEARN can automatically search and download papers:
1. **AI Query Optimization**: Converts user descriptions to professional search terms
2. **AI Search Engine Recommendation**: Automatically recommends optimal search engines based on topic (arXiv for CS/Physics, Google Scholar for social sciences, etc.)
3. **Multi-source Search**: Searches arXiv, Google Scholar with intelligent source selection
4. **AI Paper Selection**: Uses AI to select the most relevant papers
5. **Automatic Download**: Downloads selected papers with AI-generated filenames
6. **Content Extraction**: Extracts text/images using EXTRACT_PDF tool

### Search Engine Selection
- **Auto-recommendation (default)**: AI analyzes your topic and recommends the best search engines
- **Manual specification**: Use `--sources arxiv,google_scholar` to specify engines
- **arXiv**: Best for computer science, physics, mathematics, statistics
- **Google Scholar**: Best for all disciplines, especially social sciences, medicine, humanities

### Paper-based Learning Mode
By default, LEARN treats simple topic descriptions as general learning topics. Use `--paper-based` to force paper search and analysis:

- **Default behavior**: `LEARN "machine learning"` → General tutorial about machine learning
- **Paper-based mode**: `LEARN --paper-based "machine learning"` → Search, download, and analyze academic papers about machine learning

This is useful when you want to learn from academic literature rather than general knowledge.

## Output Structure

### Generated Files
```
output_directory/
├── tutorial.md              # Main tutorial content
├── question.md              # Practice questions with answers
├── paper.pdf               # Downloaded paper (if applicable)
├── paper.md                # Extracted paper content (if applicable)
└── OPENROUTER_prompts/     # API call logs
    ├── prompt_1.txt
    ├── response_1.txt
    ├── prompt_2.txt
    └── response_2.txt
```

### Tutorial Structure
- **论文概览**: Title, authors, background, contributions
- **核心概念详解**: Key concepts and technical methods
- **技术细节**: Implementation and experimental details
- **学习要点**: Key points and comparisons
- **扩展阅读**: Related papers and resources

### Question Structure
- **基础知识测试**: Fundamental concept questions
- **理解应用题**: Application and analysis questions
- **实践练习题**: Hands-on implementation tasks
- All questions include detailed answers in collapsible sections

## Model Selection
LEARN supports automatic model selection with fallback:
- **Default**: Auto-selects from available OpenRouter models
- **Manual**: Specify model with `--model <model_id>`
- **Fallback**: Automatically tries next model if current fails
- **Free Models**: Prioritizes free models like `deepseek/deepseek-chat:free`

## Error Handling
- **PDF Extraction**: Validates content length, fails if too short
- **File References**: Checks file existence and type before expansion  
- **API Failures**: Automatic retry with different models
- **Network Issues**: Graceful handling of download failures

## Tips
1. Use `--gen-command` to generate complex LEARN commands
2. Combine `@"file.md"` references for context-aware learning
3. Use `--negative` to exclude unwanted papers in searches
4. Enable `--read-images` for papers with important figures/formulas
5. Use `--brainstorm-only` for brainstorming-only sessions 