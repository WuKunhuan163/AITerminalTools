#!/usr/bin/env python3
"""
Standalone LEARN system for general topics
No dependencies on PDF extractor or other modules
"""

import sys
import os
import re
from pathlib import Path


def clear_terminal():
    """Clear the terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def show_banner():
    """Display a welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                            LEARN System Setup                               ║
║                     Interactive Parameter Collection                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def parse_learn_command(command: str) -> dict:
    """Parse LEARN command and extract topic, flags, and options."""
    # Remove LEARN prefix
    command = command.strip()
    if command.upper().startswith("LEARN"):
        command = command[5:].strip()
    
    # Initialize result
    result = {
        "topic": "",
        "mode": "Beginner",
        "style": "Rigorous",
        "is_paper": False,
        "paper_path": None,
        "read_images": False,
        "max_pages_per_chunk": 5,
        "chapters": ["background", "methodology", "evaluation", "future_work"]
    }
    
    # Check if it's a paper learning command
    if command.startswith('"') and command.count('"') >= 2:
        # Extract quoted topic/path
        topic_match = re.search(r'"([^"]+)"', command)
        if topic_match:
            topic = topic_match.group(1)
            result["topic"] = topic
            
            # Check if it's a PDF path
            if topic.endswith('.pdf') or os.path.exists(topic):
                result["is_paper"] = True
                result["paper_path"] = topic
                result["topic"] = f"Paper: {Path(topic).stem}"
    else:
        # Simple topic extraction
        parts = command.split()
        if parts:
            result["topic"] = parts[0]
    
    # Parse flags
    if "--mode" in command:
        mode_match = re.search(r'--mode\s+([^\s]+)', command)
        if mode_match:
            result["mode"] = mode_match.group(1)
    
    if "--style" in command:
        style_match = re.search(r'--style\s+([^\s]+)', command)
        if style_match:
            result["style"] = style_match.group(1)
    
    return result


def create_project_structure(base_path: str, topic: str) -> Path:
    """Create the basic project directory structure."""
    # Sanitize topic name for directory
    safe_topic = re.sub(r'[^\w\s-]', '', topic).strip()
    safe_topic = re.sub(r'[-\s]+', '_', safe_topic).lower()
    
    project_name = f"learn_{safe_topic}"
    project_path = Path(base_path) / project_name
    
    # Create directories
    project_path.mkdir(exist_ok=True)
    (project_path / "src").mkdir(exist_ok=True)
    (project_path / "docs").mkdir(exist_ok=True)
    
    return project_path


def get_interactive_params():
    """Get parameters interactively from user."""
    clear_terminal()
    
    print("What would you like to learn about?")
    print("1. General topic (e.g., Python, Machine Learning, etc.)")
    print("2. Academic paper (PDF file)")
    print()
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            return get_general_topic_params()
        elif choice == "2":
            print("❌ Paper learning is not available in this standalone version.")
            print("   Please use the full learn_project system for paper learning.")
            return None
        else:
            print("Please enter 1 or 2.")


def get_general_topic_params():
    """Get parameters for general topic learning."""
    print("\n" + "="*50)
    print("GENERAL TOPIC LEARNING")
    print("="*50)
    
    # Get topic
    topic = input("Enter the topic you want to learn: ").strip()
    if not topic:
        topic = "Python basics"
        print(f"Using default topic: {topic}")
    
    # Get mode
    print("\nLearning modes:")
    print("1. Beginner - Focus on core concepts and simplest usage")
    print("2. Advanced - Include more complex or advanced techniques")
    print("3. Practical - Driven by a small, integrated project")
    
    mode_choice = input("Choose learning mode (1-3, default: 1): ").strip()
    mode_map = {"1": "Beginner", "2": "Advanced", "3": "Practical"}
    mode = mode_map.get(mode_choice, "Beginner")
    
    # Get style
    print("\nExplanation styles:")
    print("1. Rigorous - Accurate and professional")
    print("2. Witty - Use analogies, be light-hearted and humorous")
    
    style_choice = input("Choose explanation style (1-2, default: 1): ").strip()
    style_map = {"1": "Rigorous", "2": "Witty"}
    style = style_map.get(style_choice, "Rigorous")
    
    return {
        "topic": topic,
        "mode": mode,
        "style": style,
        "is_paper": False
    }


def create_learning_project(params):
    """Create a learning project based on parameters."""
    topic = params["topic"]
    mode = params["mode"]
    style = params["style"]
    
    print(f"\nCreating learning project for: {topic}")
    print(f"Mode: {mode}, Style: {style}")
    
    # Create project structure
    project_path = create_project_structure(".", topic)
    
    # Create tutorial.md
    tutorial_content = f"""# {topic} Tutorial

## Overview
This tutorial covers **{topic}** in **{mode}** mode with **{style}** style.

## Learning Objectives
By the end of this tutorial, you will understand:
- Core concepts of {topic}
- Practical applications
- Best practices and common pitfalls

## Getting Started
Welcome to learning {topic}! This tutorial is designed to give you a comprehensive understanding of the topic.

## Key Concepts
The fundamental concepts you need to understand:

### Concept 1: Foundations
[Core foundational knowledge]

### Concept 2: Applications
[How to apply the concepts]

### Concept 3: Best Practices
[Recommended approaches and patterns]

## Examples
Here are practical examples to help you understand {topic}:

### Example 1: Basic Usage
[Simple example demonstrating core concepts]

### Example 2: Real-world Application
[More complex example showing practical use]

## Exercises
Try these exercises to reinforce your learning:

1. **Exercise 1**: Basic implementation
2. **Exercise 2**: Problem-solving application
3. **Exercise 3**: Creative project

## Common Pitfalls
Avoid these common mistakes:
- [Common mistake 1]
- [Common mistake 2]
- [Common mistake 3]

## Resources
- Official documentation
- Community resources
- Further reading materials
- Practice platforms

## Next Steps
After completing this tutorial:
1. Build a project using {topic}
2. Explore advanced topics
3. Join the community
4. Share your knowledge

---
*Generated by LEARN system - {mode} mode, {style} style*
"""
    
    # Create detailed questions.md
    questions_content = f"""# Questions for {topic}

## Foundational Questions

### Question 1: Core Concepts
What are the fundamental concepts of {topic}?

<details>
<summary>Click to see approach</summary>
Identify the key terminology, principles, and foundational ideas that form the basis of {topic}. Consider what makes this topic unique and important.
</details>

### Question 2: Problem Solving
What types of problems does {topic} help solve?

<details>
<summary>Click to see approach</summary>
Think about the practical applications and use cases where {topic} is most valuable. Consider both common and unique applications.
</details>

### Question 3: Implementation
How would you implement a basic example using {topic}?

<details>
<summary>Click to see approach</summary>
Break down the step-by-step process and identify the required components for a simple implementation.
</details>

### Question 4: Prerequisites
What knowledge or skills are needed before learning {topic}?

<details>
<summary>Click to see approach</summary>
Consider the foundational concepts, tools, or experiences that would be helpful before diving into {topic}.
</details>

## Intermediate Questions

### Question 5: Best Practices
What are the best practices when working with {topic}?

<details>
<summary>Click to see approach</summary>
Think about common patterns, conventions, and recommended approaches that experts use in this field.
</details>

### Question 6: Common Pitfalls
What are common mistakes or pitfalls to avoid with {topic}?

<details>
<summary>Click to see approach</summary>
Consider typical errors beginners make and strategies to avoid them.
</details>

### Question 7: Comparison
How does {topic} compare to similar approaches or technologies?

<details>
<summary>Click to see approach</summary>
Analyze the strengths and weaknesses relative to alternatives. When would you choose {topic} over other options?
</details>

### Question 8: Tools and Resources
What tools and resources are essential for working with {topic}?

<details>
<summary>Click to see approach</summary>
Consider development tools, libraries, documentation, and community resources that are most helpful.
</details>

## Advanced Questions

### Question 9: Optimization
How can you optimize performance when using {topic}?

<details>
<summary>Click to see approach</summary>
Think about efficiency improvements, scaling considerations, and performance tuning strategies.
</details>

### Question 10: Integration
How does {topic} integrate with other systems or technologies?

<details>
<summary>Click to see approach</summary>
Consider ecosystem compatibility, integration patterns, and interoperability challenges.
</details>

### Question 11: Future Trends
What are the emerging trends and future directions for {topic}?

<details>
<summary>Click to see approach</summary>
Research ongoing developments and consider how the field might evolve.
</details>

### Question 12: Troubleshooting
How would you debug or troubleshoot issues with {topic}?

<details>
<summary>Click to see approach</summary>
Think about common problems and systematic approaches to identifying and solving them.
</details>

## Application Questions

### Question 13: Project Design
How would you design a project that heavily uses {topic}?

<details>
<summary>Click to see approach</summary>
Consider architecture decisions, planning phases, and key considerations for a successful project.
</details>

### Question 14: Team Collaboration
How would you work with a team when using {topic}?

<details>
<summary>Click to see approach</summary>
Think about collaboration patterns, knowledge sharing, and team coordination strategies.
</details>

### Question 15: Learning Path
What should you learn next to deepen your understanding of {topic}?

<details>
<summary>Click to see approach</summary>
Consider advanced topics, related technologies, or specialized areas to explore.
</details>

## Reflection Questions

### Question 16: Personal Application
How might you apply {topic} in your own projects or work?

<details>
<summary>Click to see approach</summary>
Reflect on specific use cases relevant to your interests and professional goals.
</details>

### Question 17: Teaching Others
How would you explain {topic} to someone who is completely new to it?

<details>
<summary>Click to see approach</summary>
Practice simplifying complex concepts and using analogies or examples that others can relate to.
</details>

### Question 18: Continuous Learning
How will you stay updated with developments in {topic}?

<details>
<summary>Click to see approach</summary>
Consider resources, communities, and practices for ongoing learning and skill development.
</details>

## Challenge Questions

### Question 19: Innovation
How could you innovate or improve upon current approaches in {topic}?

<details>
<summary>Click to see approach</summary>
Think creatively about limitations in current methods and potential improvements or novel applications.
</details>

### Question 20: Critical Analysis
What are the most significant limitations or criticisms of {topic}?

<details>
<summary>Click to see approach</summary>
Consider both technical limitations and broader concerns about the field or approach.
</details>

"""
    
    # Create README.md
    readme_content = f"""# {topic} Learning Project

## Overview
This project contains comprehensive learning materials for **{topic}** generated in **{mode}** mode with **{style}** style.

## Project Structure
- `tutorial.md` - Complete tutorial with concepts, examples, and exercises
- `questions.md` - 20 detailed questions organized by difficulty level
- `src/` - Directory for example code and exercises
- `docs/` - Additional documentation and resources

## How to Use This Project

### Phase 1: Foundation (Beginner)
1. Read through `tutorial.md` sections on key concepts
2. Work through foundational questions (1-4) in `questions.md`
3. Try the basic exercises in the tutorial

### Phase 2: Development (Intermediate)
1. Study the examples and best practices in `tutorial.md`
2. Answer intermediate questions (5-8) in `questions.md`
3. Start building small projects using {topic}

### Phase 3: Mastery (Advanced)
1. Focus on optimization and integration topics
2. Challenge yourself with advanced questions (9-12)
3. Work on complex projects and real-world applications

### Phase 4: Application (Expert)
1. Complete application questions (13-15)
2. Reflect on personal learning with questions (16-18)
3. Push boundaries with challenge questions (19-20)

## Learning Strategy
- **Active Learning**: Don't just read - try to implement concepts
- **Question-Driven**: Use the questions to guide your exploration
- **Project-Based**: Build real projects to solidify understanding
- **Community Engagement**: Join discussions and share your progress

## Success Metrics
You'll know you're making progress when you can:
- Explain {topic} concepts clearly to others
- Implement solutions using {topic} independently
- Identify when and why to use {topic} over alternatives
- Troubleshoot common issues effectively

## Additional Resources
- Create a `resources.md` file to track useful links
- Use the `src/` directory for code examples and experiments
- Document your learning journey in a personal log

## Next Steps After Completion
1. **Build a Portfolio Project**: Create something substantial using {topic}
2. **Contribute to Open Source**: Find projects related to {topic}
3. **Teach Others**: Write blog posts or give presentations
4. **Specialize**: Choose advanced areas for deeper study

---
*Generated by LEARN system - Start your learning journey today!*
"""
    
    # Write files
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
        "created_files": [str(tutorial_path), str(questions_path), str(readme_path)]
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python standalone_learn.py 'command' or python standalone_learn.py")
        print("Examples:")
        print("  python standalone_learn.py 'LEARN \"Python basics\" --mode Beginner'")
        print("  python standalone_learn.py  # Interactive mode")
        
        # If no arguments, start interactive mode
        params = get_interactive_params()
        if params is None:
            print("Setup cancelled.")
            return
    else:
        # Parse command line arguments
        command = ' '.join(sys.argv[1:])
        
        # Check for just "LEARN" to trigger interactive mode
        if command.strip().upper() == "LEARN":
            params = get_interactive_params()
            if params is None:
                print("Setup cancelled.")
                return
        else:
            # Parse the command
            params = parse_learn_command(command)
            
            if params["is_paper"]:
                print("❌ Paper learning is not available in this standalone version.")
                print("   Please use the full learn_project system for paper learning.")
                return
    
    # Create the learning project
    result = create_learning_project(params)
    
    if result["success"]:
        print(f"\n✅ Learning project created successfully!")
        print(f"📁 Project path: {result['project_path']}")
        print("\n📝 Created files:")
        for file_path in result["created_files"]:
            print(f"   - {file_path}")
        
        print(f"\n🎯 Your learning journey for '{params['topic']}' is ready!")
        print(f"   Mode: {params['mode']} | Style: {params['style']}")
        print(f"\n📚 Next steps:")
        print(f"   1. Open {result['project_path']}/tutorial.md to start learning")
        print(f"   2. Work through the 20 questions in questions.md")
        print(f"   3. Build projects in the src/ directory")
        print(f"   4. Track your progress and resources")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main() 