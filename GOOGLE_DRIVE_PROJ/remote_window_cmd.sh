#!/bin/bash
# Generated at 2025-10-05 22:56:58
# Command: echo Hello


# 统一JSON结果生成脚本
# 首先检查挂载是否成功
python3 -c "
import os
import sys
try:
    mount_hash = '2100fe37'
    if mount_hash:
        fingerprint_file = \"/content/drive/MyDrive/REMOTE_ROOT/tmp/.gds_mount_fingerprint_\" + mount_hash
        if os.path.exists(fingerprint_file):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
"
if [ $? -ne 0 ]; then
    echo "当前session的GDS无法访问Google Drive文件结构。请使用GOOGLE_DRIVE --remount指令重新挂载，然后执行GDS的其他命令"
else
    # 确保工作目录存在并切换到正确的基础目录
    mkdir -p "/content/drive/MyDrive/REMOTE_ROOT"
    cd "/content/drive/MyDrive/REMOTE_ROOT" && {
        # 确保tmp目录存在
        mkdir -p "/content/drive/MyDrive/REMOTE_ROOT/tmp"
        
        # 执行用户命令并捕获输出
        TIMESTAMP="1759676218"
        HASH="c454a78b"
        OUTPUT_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stdout_${TIMESTAMP}_${HASH}"
        ERROR_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stderr_${TIMESTAMP}_${HASH}"
        EXITCODE_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_exitcode_${TIMESTAMP}_${HASH}"
        
        # 直接执行用户命令，捕获输出和错误
        set +e  # 允许命令失败
        bash -c 'echo Hello' > "$OUTPUT_FILE" 2> "$ERROR_FILE"
        EXIT_CODE=$?
        echo "$EXIT_CODE" > "$EXITCODE_FILE"
        set -e
        
        # 显示stderr内容（如果有）
        if [ -s "$ERROR_FILE" ]; then
            cat "$ERROR_FILE" >&2
        fi
        
        # 统一的执行完成提示
        clear && echo "✅执行完成"
        
        # 生成JSON结果文件
        export EXIT_CODE=$EXIT_CODE
        export TIMESTAMP=$TIMESTAMP
        export HASH=$HASH
        python3 << 'JSON_SCRIPT_EOF'
import json
import os
import sys
from datetime import datetime

# 从环境变量获取文件路径参数
timestamp = os.environ.get('TIMESTAMP', '1759676218')
hash_val = os.environ.get('HASH', 'c454a78b')

# 构建文件路径
stdout_file = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stdout_{timestamp}_{hash_val}"
stderr_file = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stderr_{timestamp}_{hash_val}"
exitcode_file = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_exitcode_{timestamp}_{hash_val}"

# 读取输出文件
stdout_content = ""
stderr_content = ""

if os.path.exists(stdout_file):
    try:
        with open(stdout_file, "r", encoding="utf-8", errors="ignore") as f:
            stdout_content = f.read()
    except Exception as e:
        stdout_content = f"ERROR: 无法读取stdout文件: {e}"
else:
    stdout_content = ""

if os.path.exists(stderr_file):
    try:
        with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
            stderr_content = f.read()
    except Exception as e:
        stderr_content = f"ERROR: 无法读取stderr文件: {e}"
else:
    stderr_content = ""

# 读取退出码
exit_code = int(os.environ.get('EXIT_CODE', '0'))

# 构建统一的结果JSON格式
result = {
    "cmd": "remote_command_executed",
    "working_dir": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "exit_code": exit_code,
    "stdout": stdout_content,
    "stderr": stderr_content
}

# 写入结果文件
result_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_1759676218_5427e608.json"
result_dir = os.path.dirname(result_file)
if result_dir:
    os.makedirs(result_dir, exist_ok=True)

with open(result_file, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

JSON_SCRIPT_EOF
        
        # 清理临时文件
        rm -f "$OUTPUT_FILE" "$ERROR_FILE" "$EXITCODE_FILE"
    }
fi
