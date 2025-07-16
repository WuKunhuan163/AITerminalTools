# others/learn_prompt_builder.py
import sys
import argparse
import textwrap

def create_learning_prompt(args):
    """Based on the parsed arguments, generates a detailed and structured prompt."""

    # This template is the core of the workflow. It tells the AI exactly what to do.
    template = f"""
    As an expert programming educator and software engineer, your task is to create a comprehensive introductory learning project for the topic: "{args.topic}".

    The project deliverables MUST be a complete project folder structure containing code, a tutorial, and self-assessment questions. Strictly adhere to the following requirements:

    **1. Project Theme and Mode:**
    - **Core Topic:** {args.topic}
    - **Tutorial Mode:** {args.mode} (Beginner: Focus on core concepts and simplest usage; Advanced: Include more complex or advanced techniques; Practical: Driven by a small, integrated project)
    - **Explanation Style:** {args.style} (Rigorous: Accurate and professional; Witty: Use analogies, be light-hearted and humorous)

    **2. Final Deliverables Structure:**
    Please return all of the following content in a format that can be directly copied and saved into files:
    - A root project folder, recommended name: `learn_{args.topic.lower().replace(' ', '_')}`.
    - A `README.md` in the root directory.
    - A `tutorial.md` in the root directory (the detailed tutorial).
    - A `question.md` in the root directory (self-assessment questions with answers).
    - One or more example code files (e.g., `app.py`, `main.js`), which can be placed in a `src/` subdirectory if appropriate.
    - A `.gitignore` file, with content suitable for the project's language.

    **3. `tutorial.md` Content Requirements:**
    - **Clear Structure:** Must include a clear table of contents and step-by-step instructions.
    - **Concept First:** Begin by explaining the core concepts related to "{args.topic}".
    - **Code Examples:** Provide concise, runnable, and well-commented code snippets to demonstrate each point.
    - **Mode Reflection:**
        - For "Beginner" mode, focus on the most essential APIs and workflows.
        - For "Advanced" mode, introduce less common but powerful features or underlying principles.
        - For "Practical" mode, the entire tutorial should revolve around building the example project.
    - **Style Reflection:** The language must match the chosen "{args.style}" style.

    **4. `question.md` Content Requirements:**
    - **Guided Questions:** Ask 5-10 questions closely related to the tutorial's content.
    - **Hidden Answers:** You **MUST** use Markdown's `<details>` and `<summary>` tags to create collapsible answer sections, encouraging the user to think before viewing the answer. Format:
      <details>
      <summary>Click to see the answer</summary>
      Here is the detailed answer to the question.
      </details>
    - **Key Point Coverage:** Questions should cover all core concepts from the tutorial.

    **5. Example Code Requirements:**
    - **Concise and Complete:** The code should be as simple as possible but must be independently runnable.
    - **Relevant to Topic:** The functionality of the example code must demonstrate the "{args.topic}". For instance, if the topic is "Python tkinter," create a simple GUI application.
    - **Well-Commented:** Critical lines of code should have comments.

    **6. `README.md` Content Requirements:**
    - Briefly introduce the project's purpose.
    - Clearly explain how to set up the environment and run the example code.

    Please begin generating the content for all the above files now.
    """
    return textwrap.dedent(template).strip()

if __name__ == "__main__":
    full_input_str = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    
    # Check if this is a paper learning command (contains a file path)
    if full_input_str.startswith('LEARN "') and (full_input_str.count('"') >= 2):
        # Extract the quoted part
        topic_match = full_input_str.split('"')[1]
        if topic_match.endswith('.pdf') or '/' in topic_match:
            # This is a paper learning command, delegate to the new system
            import subprocess
            import sys
            from pathlib import Path
            
            learn_main_path = Path(__file__).parent.parent / "learn_project" / "main.py"
            
            try:
                result = subprocess.run([sys.executable, str(learn_main_path), full_input_str], 
                                      capture_output=False, text=True)
                sys.exit(result.returncode)
            except Exception as e:
                print(f"Error calling new learn system: {e}")
                sys.exit(1)
    
    # Original logic for general topics
    try:
        topic = full_input_str.split('"')[1]
    except IndexError:
        topic = full_input_str.replace("LEARN", "", 1).strip()

    mode = "基础"
    if "--mode" in full_input_str:
        try:
            mode = full_input_str.split('--mode')[1].split('"')[1]
        except (IndexError, AttributeError):
            mode = full_input_str.split('--mode')[1].strip().split(' ')[0]

    style = "严谨"
    if "--style" in full_input_str:
        try:
            style = full_input_str.split('--style')[1].split('"')[1]
        except (IndexError, AttributeError):
            style = full_input_str.split('--style')[1].strip().split(' ')[0]

    Args = argparse.Namespace(topic=topic, mode=mode, style=style)
    
    final_prompt = create_learning_prompt(Args)
    print(final_prompt) 