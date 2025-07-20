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
LEARN --pdf "<pdf_path>" [options]       # Direct PDF processing
LEARN --description "<description>" [options]  # Paper search and download
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

### Paper Input Options
- `-p, --paper <path>`: Local paper file path (Markdown)
- `--pdf <path>`: Direct PDF file path (skips search/download)
- `-u, --url <url>`: Paper URL for download
- `-d, --description <text>`: Paper description for search and download
- `--negative <text>`: Negative prompt to exclude unwanted papers
- `--read-images`: Enable image/formula/table processing in PDFs

### Advanced Options
- `--model <model>`: Specify OpenRouter model (default: auto)
- `--max-tokens <num>`: Maximum tokens per API call
- `--not-default`: Disable default settings, enable interactive selection
- `--brainstorm-only`: Only perform brainstorming, don't create files
- `--gen-command <description>`: Generate LEARN command based on description

### File Reference Support
LEARN supports @"file_path" syntax to include file content in prompts:
- `@"/path/to/file.md"`: Include markdown file content
- `@"/path/to/file.txt"`: Include text file content
- Only .md and .txt files are supported for security

## Examples

### General Topic Learning
```bash
LEARN -o ~/tutorials -m 初学者 -s 简洁明了 "Python基础编程"
LEARN -o ~/tutorials -m 高级 -s 实例丰富 "机器学习算法"
```

### Academic Paper Learning
```bash
# Direct PDF processing
LEARN -o ~/tutorials -m 中级 --pdf "/path/to/paper.pdf"

# Search and download paper
LEARN -o ~/tutorials -m 初学者 -d "3D Gaussian Splatting mesh reconstruction"

# With negative prompt to exclude specific papers
LEARN -o ~/tutorials -m 中级 -d "deep learning" --negative "GAN, generative models"

# With image processing enabled
LEARN -o ~/tutorials -m 高级 --pdf "/path/to/paper.pdf" --read-images
```

### Context-Aware Learning with File References
```bash
# Learn specific section with full paper context
LEARN -o ~/tutorials -m 初学者 "学习论文3.1节的技术原理 @\"/path/to/paper.md\""

# Multiple file references
LEARN -o ~/tutorials -m 中级 "比较两篇论文的方法 @\"/paper1.md\" @\"/paper2.md\""
```

### Command Generation
```bash
# Generate LEARN command from description
LEARN --gen-command "我想学习A论文的前五页"
LEARN --gen-command "帮我创建深度学习入门教程"
LEARN --gen-command "分析这篇NLP论文的核心算法"
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
2. **Multi-source Search**: Searches arXiv, Google Scholar, Semantic Scholar
3. **AI Paper Selection**: Uses AI to select the most relevant papers
4. **Automatic Download**: Downloads selected papers with AI-generated filenames
5. **Content Extraction**: Extracts text/images using EXTRACT_PDF tool

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