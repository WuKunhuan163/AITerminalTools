"""
Core learning system that handles both general topics and paper learning
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from .utils import parse_learn_command, create_project_structure, sanitize_filename
from .paper_processor import PaperProcessor


class LearnSystem:
    """
    Main learning system that orchestrates the entire learning process.
    """
    
    def __init__(self, base_path: str = "learn_project"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        self.paper_processor = PaperProcessor(str(self.base_path))
        
    def process_learn_command(self, command: str) -> Dict:
        """
        Process a LEARN command and generate appropriate learning materials.
        
        Args:
            command: The LEARN command string
            
        Returns:
            Dictionary containing processing results
        """
        # Parse the command
        parsed = parse_learn_command(command)
        
        if parsed["is_paper"]:
            return self._process_paper_learning(parsed)
        else:
            return self._process_general_learning(parsed)
    
    def _process_paper_learning(self, parsed: Dict) -> Dict:
        """
        Process paper learning with chapter-based segmentation.
        
        Args:
            parsed: Parsed command dictionary
            
        Returns:
            Processing results
        """
        paper_path = parsed["paper_path"]
        topic = parsed["topic"]
        mode = parsed["mode"]
        style = parsed["style"]
        read_images = parsed["read_images"]
        max_pages_per_chunk = parsed["max_pages_per_chunk"]
        chapters = parsed["chapters"]
        
        print(f"Processing paper: {paper_path}")
        print(f"Mode: {mode}, Style: {style}")
        print(f"Read images: {read_images}")
        print(f"Max pages per chunk: {max_pages_per_chunk}")
        print(f"Chapters: {chapters}")
        
        # Create project structure
        project_path = create_project_structure(str(self.base_path), topic)
        
        try:
            # Process the paper
            paper_data = self.paper_processor.process_paper(
                paper_path, read_images, max_pages_per_chunk, chapters
            )
            
            # Create chapter tutorials
            tutorials = self.paper_processor.create_chapter_tutorials(
                paper_data, topic, mode, style
            )
            
            # Save tutorials
            paper_name = Path(paper_path).stem
            created_files = self.paper_processor.save_chapter_tutorials(
                tutorials, project_path, paper_name
            )
            
            # Create main tutorial.md that combines all chapters
            main_tutorial = self._create_main_paper_tutorial(
                tutorials, topic, paper_name, mode, style
            )
            
            tutorial_path = project_path / "tutorial.md"
            with open(tutorial_path, 'w', encoding='utf-8') as f:
                f.write(main_tutorial)
            
            # Create questions.md with detailed section-based questions
            questions = self._create_paper_questions(paper_data, topic)
            questions_path = project_path / "questions.md"
            with open(questions_path, 'w', encoding='utf-8') as f:
                f.write(questions)
            
            # Create README.md
            readme = self._create_paper_readme(topic, paper_name, chapters)
            readme_path = project_path / "README.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme)
            
            return {
                "success": True,
                "project_path": str(project_path),
                "created_files": [str(f) for f in created_files] + [
                    str(tutorial_path), str(questions_path), str(readme_path)
                ],
                "paper_data": paper_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": str(project_path)
            }
    
    def _process_general_learning(self, parsed: Dict) -> Dict:
        """
        Process general topic learning using the existing prompt builder.
        
        Args:
            parsed: Parsed command dictionary
            
        Returns:
            Processing results
        """
        topic = parsed["topic"]
        mode = parsed["mode"]
        style = parsed["style"]
        
        print(f"Processing general topic: {topic}")
        print(f"Mode: {mode}, Style: {style}")
        
        # Create project structure
        project_path = create_project_structure(str(self.base_path), topic)
        
        try:
            # Use the existing prompt builder
            prompt_builder_path = Path(__file__).parent.parent / "others" / "learn_prompt_builder.py"
            
            # Reconstruct the command for the prompt builder
            command_for_builder = f'LEARN "{topic}" --mode {mode} --style {style}'
            
            # Run the prompt builder
            result = subprocess.run([
                sys.executable, str(prompt_builder_path), command_for_builder
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Prompt builder failed: {result.stderr}")
            
            # The prompt builder output is the detailed instruction
            detailed_prompt = result.stdout
            
            # For now, create a basic structure
            # In a real implementation, you would use the detailed_prompt to generate content
            tutorial_content = self._create_basic_tutorial(topic, mode, style, detailed_prompt)
            questions_content = self._create_basic_questions(topic)
            readme_content = self._create_basic_readme(topic)
            
            # Save files
            tutorial_path = project_path / "tutorial.md"
            questions_path = project_path / "questions.md"
            readme_path = project_path / "README.md"
            
            with open(tutorial_path, 'w', encoding='utf-8') as f:
                f.write(tutorial_content)
            
            with open(questions_path, 'w', encoding='utf-8') as f:
                f.write(questions_content)
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            return {
                "success": True,
                "project_path": str(project_path),
                "created_files": [str(tutorial_path), str(questions_path), str(readme_path)],
                "detailed_prompt": detailed_prompt
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "project_path": str(project_path)
            }
    
    def _create_main_paper_tutorial(self, tutorials: Dict[str, str], 
                                  topic: str, paper_name: str, 
                                  mode: str, style: str) -> str:
        """Create the main tutorial.md that combines all chapters."""
        content = f"""# {topic} - Complete Tutorial

## Overview
This tutorial is generated from the academic paper: **{paper_name}**

**Mode:** {mode}  
**Style:** {style}

## Table of Contents
"""
        
        # Add table of contents
        for chapter in tutorials.keys():
            content += f"- [{chapter.title()}](#{chapter.replace('_', '-')})\n"
        
        content += "\n---\n\n"
        
        # Add each chapter
        for chapter, tutorial_content in tutorials.items():
            content += f"## {chapter.title()}\n\n"
            content += tutorial_content + "\n\n---\n\n"
        
        return content
    
    def _create_paper_questions(self, paper_data: Dict, topic: str) -> str:
        """Create detailed questions based on paper content, organized by sections."""
        content = f"""# Questions for {topic}

## Section-Based Understanding Questions

This question set is organized by paper sections to help you thoroughly understand each aspect of the research.

"""
        
        # Questions organized by sections
        section_questions = {
            "background": [
                "What is the main problem this paper addresses?",
                "Why is this problem important or significant?",
                "What are the key limitations of existing approaches?",
                "What gap in knowledge does this work fill?",
                "How does the authors' motivation align with current research trends?",
                "What are the key assumptions made in the problem formulation?",
                "What related work is most relevant and why?",
                "How does this work differentiate itself from previous research?",
                "What theoretical foundations does this work build upon?",
                "What are the key definitions and terminology introduced?"
            ],
            "methodology": [
                "What is the core methodology or approach proposed?",
                "What are the key components of the proposed system/method?",
                "How does the proposed approach work step by step?",
                "What are the key innovations in the methodology?",
                "What assumptions does the methodology make?",
                "What are the computational or practical requirements?",
                "How does the method handle edge cases or limitations?",
                "What parameters or hyperparameters are involved?",
                "How does the approach scale with problem size?",
                "What are the theoretical guarantees or properties?",
                "How does the method compare conceptually to alternatives?",
                "What implementation details are crucial for success?"
            ],
            "evaluation": [
                "What datasets or experimental setups were used?",
                "What metrics were chosen and why are they appropriate?",
                "What are the main quantitative results?",
                "How do the results compare to baselines or state-of-the-art?",
                "What do the results tell us about the method's effectiveness?",
                "Are there any surprising or unexpected findings?",
                "What are the statistical significance levels of the results?",
                "How robust are the results across different conditions?",
                "What ablation studies were conducted and what do they show?",
                "What are the failure cases or limitations observed?",
                "How do qualitative results support quantitative findings?",
                "What insights can be drawn from the error analysis?",
                "How do the results generalize to different domains or settings?"
            ],
            "future_work": [
                "What are the main limitations acknowledged by the authors?",
                "What directions for future research are suggested?",
                "What improvements could be made to the current approach?",
                "What new research questions emerge from this work?",
                "How could this work be extended or generalized?",
                "What practical applications are suggested or possible?",
                "What technical challenges remain unsolved?",
                "How might this work influence the broader field?",
                "What interdisciplinary connections could be explored?",
                "What ethical or societal implications should be considered?"
            ]
        }
        
        # Generate questions for each section that has content
        for section, section_content in paper_data["sections"].items():
            if section_content and section in section_questions:
                content += f"## {section.title()} Questions\n\n"
                
                for i, question in enumerate(section_questions[section], 1):
                    content += f"### {section.title()} Q{i}\n{question}\n\n"
                    content += """<details>
<summary>Click to see suggested approach</summary>
Review the relevant sections of the paper carefully. Look for both explicit statements and implicit implications. Consider the context and connections to other parts of the paper.
</details>

"""
        
        # Add comprehensive questions
        content += """## Comprehensive Understanding Questions

### Integration Q1
How do the different components of this work fit together to achieve the overall goal?

<details>
<summary>Click to see suggested approach</summary>
Think about how the background motivates the methodology, how the methodology addresses the problem, and how the evaluation validates the approach.
</details>

### Critical Analysis Q1
What are the strongest and weakest aspects of this work?

<details>
<summary>Click to see suggested approach</summary>
Consider the novelty, technical soundness, experimental rigor, and practical impact. Think about both what the authors did well and what could be improved.
</details>

### Broader Impact Q1
How might this work influence future research in the field?

<details>
<summary>Click to see suggested approach</summary>
Consider the potential for follow-up work, applications to other domains, and the broader implications for the research community.
</details>

### Personal Reflection Q1
What aspects of this work do you find most interesting or surprising?

<details>
<summary>Click to see suggested approach</summary>
Reflect on what you learned, what challenged your assumptions, and what sparked your curiosity for further exploration.
</details>

"""
        
        return content
    
    def _create_paper_readme(self, topic: str, paper_name: str, chapters: List[str]) -> str:
        """Create README for paper learning project."""
        content = f"""# {topic} Learning Project

## Overview
This project contains learning materials generated from the academic paper: **{paper_name}**

## Structure
- `tutorial.md` - Main tutorial combining all chapters
- `questions.md` - Detailed section-based questions for thorough understanding
- `docs/` - Individual chapter tutorials

## Chapters Covered
"""
        
        for chapter in chapters:
            content += f"- {chapter.title()}\n"
        
        content += f"""
## How to Use
1. Start with `tutorial.md` for a comprehensive overview
2. Use individual chapter tutorials in `docs/` for focused study
3. Work through the detailed questions in `questions.md` section by section

## Generated Content
This content was automatically generated from PDF analysis. 
Please refer to the original paper for authoritative information.
"""
        
        return content
    
    def _create_basic_tutorial(self, topic: str, mode: str, style: str, detailed_prompt: str) -> str:
        """Create basic tutorial for general topics."""
        return f"""# {topic} Tutorial

## Overview
This tutorial covers {topic} in {mode} mode with {style} style.

## Generated Instructions
{detailed_prompt}

## Next Steps
Use the detailed instructions above to create comprehensive learning materials.
"""
    
    def _create_basic_questions(self, topic: str) -> str:
        """Create basic questions for general topics."""
        return f"""# Questions for {topic}

## Basic Questions

### Question 1
What are the core concepts of {topic}?

<details>
<summary>Click to see the answer</summary>
Review the fundamental principles and key terminology.
</details>

### Question 2
How can {topic} be applied in practice?

<details>
<summary>Click to see the answer</summary>
Consider real-world use cases and implementation examples.
</details>

### Question 3
What are the advantages and limitations of {topic}?

<details>
<summary>Click to see the answer</summary>
Analyze the strengths and weaknesses compared to alternatives.
</details>
"""
    
    def _create_basic_readme(self, topic: str) -> str:
        """Create basic README for general topics."""
        return f"""# {topic} Learning Project

## Overview
This project contains learning materials for {topic}.

## Structure
- `tutorial.md` - Main tutorial
- `questions.md` - Self-assessment questions
- `src/` - Example code (if applicable)

## How to Use
1. Read through `tutorial.md`
2. Work through any example code in `src/`
3. Test your understanding with `questions.md`

## Getting Started
Follow the instructions in the tutorial to begin learning {topic}.
"""


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python -m learn_project.learn_core 'LEARN command'")
        sys.exit(1)
    
    command = ' '.join(sys.argv[1:])
    
    # Initialize the learning system
    learn_system = LearnSystem()
    
    # Process the command
    result = learn_system.process_learn_command(command)
    
    if result["success"]:
        print(f"✅ Learning materials created successfully!")
        print(f"📁 Project path: {result['project_path']}")
        print("📝 Created files:")
        for file_path in result["created_files"]:
            print(f"   - {file_path}")
    else:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main() 