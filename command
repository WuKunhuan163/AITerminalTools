# 首先检查挂载是否成功（使用Python避免直接崩溃）
python3 -c "
import os
import glob
import sys
try:
    fingerprint_files = glob.glob(\"/content/drive/MyDrive/REMOTE_ROOT/.gds_mount_fingerprint_*\")
    if not fingerprint_files:
        sys.exit(1)
except Exception:
    sys.exit(1)
"
if [ $? -ne 0 ]; then
    clear
    echo "当前session的GDS无法访问Google Drive文件结构。请使用GOOGLE_DRIVE --remount指令重新挂载，然后执行GDS的其他命令"
else
    # 确保工作目录存在
mkdir -p "/content/drive/MyDrive/REMOTE_ROOT/Computer Vision/basic_cv_project"
cd "/content/drive/MyDrive/REMOTE_ROOT/Computer Vision/basic_cv_project" && {
    # 确保tmp目录存在
    mkdir -p "/content/drive/MyDrive/REMOTE_ROOT/tmp"
    
    
    # 执行命令并捕获输出
    OUTPUT_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stdout_1759354869_6e470c38"
    ERROR_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stderr_1759354869_6e470c38"
    EXITCODE_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_exitcode_1759354869_6e470c38"
    
    # 直接执行命令，捕获输出和错误
    set +e  # 允许命令失败
    echo "ZWNobyAiWm1sdVlXd2dkR1Z6ZEE9PSIgfCBiYXNlNjQgLWQgPiAiL2NvbnRlbnQvZHJpdmUvTXlEcml2ZS9SRU1PVEVfUk9PVC90bXAvZmluYWxfdGVzdC50eHQi" | base64 -d | bash > "$OUTPUT_FILE" 2> "$ERROR_FILE"
    EXIT_CODE=$?
    echo "$EXIT_CODE" > "$EXITCODE_FILE"
    set -e
    
    # stdout内容将通过JSON结果文件传递，不在这里显示
    # 这样避免重复输出问题
    
    # 显示stderr内容（如果有）
    if [ -s "$ERROR_FILE" ]; then
        cat "$ERROR_FILE" >&2
    fi
    
    # 统一的执行完成提示（无论成功失败都显示完成）
    if [ "$EXIT_CODE" -eq 0 ]; then
        clear && echo "✅执行完成"
    else
        clear && echo "✅执行完成"
    fi
    
    # 设置环境变量并生成JSON结果文件
    export EXIT_CODE=$EXIT_CODE
    PYTHON_SCRIPT="/content/drive/MyDrive/REMOTE_ROOT/tmp/json_generator_1759354869_6e470c38.py"
    cat > "$PYTHON_SCRIPT" << 'SCRIPT_END'
import json
import os
import sys
from datetime import datetime

# 读取输出文件
stdout_content = ""
stderr_content = ""
raw_stdout = ""
raw_stderr = ""

# 文件路径
stdout_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stdout_1759354869_6e470c38"
stderr_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stderr_1759354869_6e470c38"
exitcode_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_exitcode_1759354869_6e470c38"

# 调试信息
if os.path.exists(stdout_file):
    stdout_size = os.path.getsize(stdout_file)
else:
    pass

if os.path.exists(stderr_file):
    stderr_size = os.path.getsize(stderr_file)
else:
    pass

# 读取stdout文件
if os.path.exists(stdout_file):
    try:
        with open(stdout_file, "r", encoding="utf-8", errors="ignore") as f:
            raw_stdout = f.read()
        stdout_content = raw_stdout
    except Exception as e:
        raw_stdout = f"ERROR: 无法读取stdout文件: {e}"
        stdout_content = raw_stdout
else:
    raw_stdout = "ERROR: stdout文件不存在"
    stdout_content = ""

# 读取stderr文件
if os.path.exists(stderr_file):
    try:
        with open(stderr_file, "r", encoding="utf-8", errors="ignore") as f:
            raw_stderr = f.read()
        stderr_content = raw_stderr
    except Exception as e:
        raw_stderr = f"ERROR: 无法读取stderr文件: {e}"
        stderr_content = raw_stderr
else:
    raw_stderr = ""
    stderr_content = ""

# 读取退出码
exit_code = 0
if os.path.exists(exitcode_file):
    try:
        with open(exitcode_file, "r") as f:
            exit_code = int(f.read().strip())
    except:
        exit_code = -1

# 构建结果JSON
result = {
    "cmd": "bash",
    "args": ["-c", "echo \"ZmluYWwgdGVzdA==\" | base64 -d > \"/content/drive/MyDrive/REMOTE_ROOT/tmp/final_test.txt\""],
    "working_dir": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "exit_code": exit_code,
    "stdout": stdout_content,
    "stderr": stderr_content,
    "raw_output": raw_stdout,
    "raw_error": raw_stderr,
    "debug_info": {
        "stdout_file_exists": os.path.exists(stdout_file),
        "stderr_file_exists": os.path.exists(stderr_file),
        "stdout_file_size": os.path.getsize(stdout_file) if os.path.exists(stdout_file) else 0,
        "stderr_file_size": os.path.getsize(stderr_file) if os.path.exists(stderr_file) else 0
    }
}

print(json.dumps(result, indent=2, ensure_ascii=False))
SCRIPT_END
    python3 "$PYTHON_SCRIPT" > "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_1759354869_6e470c38.json"
    rm -f "$PYTHON_SCRIPT"
    
    # 清理临时文件（在JSON生成之后）
    rm -f "$OUTPUT_FILE" "$ERROR_FILE" "$EXITCODE_FILE"
    }
fi