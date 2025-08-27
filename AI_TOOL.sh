#!/bin/bash
# AI_TOOL Command Script
# AI工具 - 现在调用Python版本

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call Python version of AI_TOOL script
exec /usr/bin/python3 "$SCRIPT_DIR/AI_TOOL.py" "$@" 