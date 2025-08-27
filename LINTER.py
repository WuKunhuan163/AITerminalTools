#!/bin/bash
# LINTER 命令脚本
# 多语言代码检查工具 - 现在调用Python版本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 调用Python版本的LINTER脚本
exec /usr/bin/python3 "$SCRIPT_DIR/LINTER.py" "$@"    