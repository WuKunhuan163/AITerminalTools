# Cursor Rule for LEARN System

## Rule Configuration

```yaml
---
description: 'Handles LEARN commands by calling the interactive learning system'
globs:
  - 'LEARN*'
alwaysApply: false
prompt: |-
  You have received a LEARN command. Execute the following:
  
  1. Run the command: python learn_project/learn_entry.py "{userInput}"
  2. Follow the output and execute any generated commands
  3. Report the results to the user
---
```

## Usage

Add this rule to your Cursor configuration to automatically detect and handle LEARN commands:

- `LEARN` - Starts interactive parameter collection
- `LEARN "topic"` - Direct topic learning
- `LEARN "/path/to/paper.pdf"` - Paper learning with options

## Examples

```
LEARN
LEARN "Python basics" --mode Beginner --style Rigorous
LEARN "/path/to/paper.pdf" --read-images --max-pages 3
``` 