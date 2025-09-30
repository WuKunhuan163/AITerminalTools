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
    OUTPUT_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stdout_1759273907_d83bfa3d"
    ERROR_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stderr_1759273907_d83bfa3d"
    EXITCODE_FILE="/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_exitcode_1759273907_d83bfa3d"
    
    # 直接执行命令，捕获输出和错误
    set +e  # 允许命令失败
    echo "bWtkaXIgLXAgL2NvbnRlbnQvZHJpdmUvTXlEcml2ZS9SRU1PVEVfUk9PVC90bXAgJiYgXAogICAgICAgICAgICBlY2hvICJkVzVrWldacGJtVmtYM1poY2c9PSIgPiAiL2NvbnRlbnQvZHJpdmUvTXlEcml2ZS9SRU1PVEVfUk9PVC90bXAvcHl0aG9uX2NvZGVfMTc1OTI3MzkwN18wNmNiLmI2NCIgJiYgXAogICAgICAgICAgICBzb3VyY2UgL2NvbnRlbnQvZHJpdmUvTXlEcml2ZS9SRU1PVEVfRU5WL3ZlbnYvdmVudl9weXRob25wYXRoLnNoIDI+L2Rldi9udWxsIHx8IHRydWUKICAgICAgICAgICAgCiAgICAgICAgICAgICMg5Zyo6L+c56iL546v5aKD5Lit5pm66IO96YCJ5oupUHl0aG9u5Y+v5omn6KGM5paH5Lu2CiAgICAgICAgICAgICMgMS4g5qOA5p+l5piv5ZCm5pyJcHllbnborr7nva7nmoRQeXRob27niYjmnKwKICAgICAgICAgICAgUFlUSE9OX0VYRUM9InB5dGhvbjMiICAjIOm7mOiupAogICAgICAgICAgICBQWVRIT05fQkFTRV9QQVRIPSIvY29udGVudC9kcml2ZS9NeURyaXZlL1JFTU9URV9FTlYvcHl0aG9uIgogICAgICAgICAgICBTVEFURV9GSUxFPSIkUFlUSE9OX0JBU0VfUEFUSC9weXRob25fc3RhdGVzLmpzb24iCiAgICAgICAgICAgIAogICAgICAgICAgICAjIOiOt+WPluW9k+WJjXNoZWxsIElEICjnroDljJbniYjmnKwpCiAgICAgICAgICAgIFNIRUxMX0lEPSJkZWZhdWx0IgogICAgICAgICAgICAKICAgICAgICAgICAgIyDlpoLmnpznirbmgIHmlofku7blrZjlnKjvvIzlsJ3or5Xor7vlj5ZQeXRob27niYjmnKzorr7nva4KICAgICAgICAgICAgaWYgWyAtZiAiJFNUQVRFX0ZJTEUiIF07IHRoZW4KICAgICAgICAgICAgICAgICMg5LyY5YWI5qOA5p+lbG9jYWzniYjmnKwKICAgICAgICAgICAgICAgIExPQ0FMX1ZFUlNJT049JChweXRob24zIC1jICIKaW1wb3J0IGpzb24sIHN5cwp0cnk6CiAgICB3aXRoIG9wZW4oJyRTVEFURV9GSUxFJywgJ3InKSBhcyBmOgogICAgICAgIHN0YXRlcyA9IGpzb24ubG9hZChmKQogICAgcHJpbnQoc3RhdGVzLmdldCgnc2hlbGxfJHtTSEVMTF9JRH0nLCAnJykpCmV4Y2VwdDoKICAgIHBhc3MKIiAyPi9kZXYvbnVsbCB8fCBlY2hvICIiKQogICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAjIOWmguaenOayoeaciWxvY2Fs54mI5pys77yM5qOA5p+lZ2xvYmFs54mI5pysCiAgICAgICAgICAgICAgICBpZiBbIC16ICIkTE9DQUxfVkVSU0lPTiIgXTsgdGhlbgogICAgICAgICAgICAgICAgICAgIEdMT0JBTF9WRVJTSU9OPSQocHl0aG9uMyAtYyAiCmltcG9ydCBqc29uLCBzeXMKdHJ5OgogICAgd2l0aCBvcGVuKCckU1RBVEVfRklMRScsICdyJykgYXMgZjoKICAgICAgICBzdGF0ZXMgPSBqc29uLmxvYWQoZikKICAgIHByaW50KHN0YXRlcy5nZXQoJ2dsb2JhbCcsICcnKSkKZXhjZXB0OgogICAgcGFzcwoiIDI+L2Rldi9udWxsIHx8IGVjaG8gIiIpCiAgICAgICAgICAgICAgICAgICAgQ1VSUkVOVF9WRVJTSU9OPSIkR0xPQkFMX1ZFUlNJT04iCiAgICAgICAgICAgICAgICBlbHNlCiAgICAgICAgICAgICAgICAgICAgQ1VSUkVOVF9WRVJTSU9OPSIkTE9DQUxfVkVSU0lPTiIKICAgICAgICAgICAgICAgIGZpCiAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICMg5aaC5p6c5om+5Yiw5LqG54mI5pys6K6+572u77yM5qOA5p+l5a+55bqU55qEUHl0aG9u5piv5ZCm5a2Y5ZyoCiAgICAgICAgICAgICAgICBpZiBbIC1uICIkQ1VSUkVOVF9WRVJTSU9OIiBdICYmIFsgIiRDVVJSRU5UX1ZFUlNJT04iICE9ICJzeXN0ZW0iIF07IHRoZW4KICAgICAgICAgICAgICAgICAgICBQWUVOVl9QWVRIT049IiRQWVRIT05fQkFTRV9QQVRILyRDVVJSRU5UX1ZFUlNJT04vYmluL3B5dGhvbjMiCiAgICAgICAgICAgICAgICAgICAgaWYgWyAtZiAiJFBZRU5WX1BZVEhPTiIgXSAmJiBbIC14ICIkUFlFTlZfUFlUSE9OIiBdOyB0aGVuCiAgICAgICAgICAgICAgICAgICAgICAgIFBZVEhPTl9FWEVDPSIkUFlFTlZfUFlUSE9OIgogICAgICAgICAgICAgICAgICAgIGZpCiAgICAgICAgICAgICAgICBmaQogICAgICAgICAgICBmaQogICAgICAgICAgICAKICAgICAgICAgICAgIyDmiafooYxQeXRob27ku6PnoIEKICAgICAgICAgICAgJFBZVEhPTl9FWEVDIC1jICJpbXBvcnQgYmFzZTY0OyBleGVjKGJhc2U2NC5iNjRkZWNvZGUob3BlbihcIi9jb250ZW50L2RyaXZlL015RHJpdmUvUkVNT1RFX1JPT1QvdG1wL3B5dGhvbl9jb2RlXzE3NTkyNzM5MDdfMDZjYi5iNjRcIikucmVhZCgpLnN0cmlwKCkpLmRlY29kZShcInV0Zi04XCIpKSIKICAgICAgICAgICAgUFlUSE9OX0VYSVRfQ09ERT0kPwogICAgICAgICAgICAKICAgICAgICAgICAgIyDmuIXnkIbkuLTml7bmlofku7YKICAgICAgICAgICAgcm0gLWYgIi9jb250ZW50L2RyaXZlL015RHJpdmUvUkVNT1RFX1JPT1QvdG1wL3B5dGhvbl9jb2RlXzE3NTkyNzM5MDdfMDZjYi5iNjQiCiAgICAgICAgICAgIAogICAgICAgICAgICAjIOi/lOWbnlB5dGhvbuiEmuacrOeahOmAgOWHuueggQogICAgICAgICAgICBleGl0ICRQWVRIT05fRVhJVF9DT0RF" | base64 -d | bash > "$OUTPUT_FILE" 2> "$ERROR_FILE"
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
    PYTHON_SCRIPT="/content/drive/MyDrive/REMOTE_ROOT/tmp/json_generator_1759273907_d83bfa3d.py"
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
stdout_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stdout_1759273907_d83bfa3d"
stderr_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_stderr_1759273907_d83bfa3d"
exitcode_file = "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_exitcode_1759273907_d83bfa3d"

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
    "args": ["-c", "mkdir -p /content/drive/MyDrive/REMOTE_ROOT/tmp && \\\n            echo \"dW5kZWZpbmVkX3Zhcg==\" > \"/content/drive/MyDrive/REMOTE_ROOT/tmp/python_code_1759273907_06cb.b64\" && \\\n            source /content/drive/MyDrive/REMOTE_ENV/venv/venv_pythonpath.sh 2>/dev/null || true\n            \n            # \u5728\u8fdc\u7a0b\u73af\u5883\u4e2d\u667a\u80fd\u9009\u62e9Python\u53ef\u6267\u884c\u6587\u4ef6\n            # 1. \u68c0\u67e5\u662f\u5426\u6709pyenv\u8bbe\u7f6e\u7684Python\u7248\u672c\n            PYTHON_EXEC=\"python3\"  # \u9ed8\u8ba4\n            PYTHON_BASE_PATH=\"/content/drive/MyDrive/REMOTE_ENV/python\"\n            STATE_FILE=\"$PYTHON_BASE_PATH/python_states.json\"\n            \n            # \u83b7\u53d6\u5f53\u524dshell ID (\u7b80\u5316\u7248\u672c)\n            SHELL_ID=\"default\"\n            \n            # \u5982\u679c\u72b6\u6001\u6587\u4ef6\u5b58\u5728\uff0c\u5c1d\u8bd5\u8bfb\u53d6Python\u7248\u672c\u8bbe\u7f6e\n            if [ -f \"$STATE_FILE\" ]; then\n                # \u4f18\u5148\u68c0\u67e5local\u7248\u672c\n                LOCAL_VERSION=$(python3 -c \"\nimport json, sys\ntry:\n    with open('$STATE_FILE', 'r') as f:\n        states = json.load(f)\n    print(states.get('shell_${SHELL_ID}', ''))\nexcept:\n    pass\n\" 2>/dev/null || echo \"\")\n                \n                # \u5982\u679c\u6ca1\u6709local\u7248\u672c\uff0c\u68c0\u67e5global\u7248\u672c\n                if [ -z \"$LOCAL_VERSION\" ]; then\n                    GLOBAL_VERSION=$(python3 -c \"\nimport json, sys\ntry:\n    with open('$STATE_FILE', 'r') as f:\n        states = json.load(f)\n    print(states.get('global', ''))\nexcept:\n    pass\n\" 2>/dev/null || echo \"\")\n                    CURRENT_VERSION=\"$GLOBAL_VERSION\"\n                else\n                    CURRENT_VERSION=\"$LOCAL_VERSION\"\n                fi\n                \n                # \u5982\u679c\u627e\u5230\u4e86\u7248\u672c\u8bbe\u7f6e\uff0c\u68c0\u67e5\u5bf9\u5e94\u7684Python\u662f\u5426\u5b58\u5728\n                if [ -n \"$CURRENT_VERSION\" ] && [ \"$CURRENT_VERSION\" != \"system\" ]; then\n                    PYENV_PYTHON=\"$PYTHON_BASE_PATH/$CURRENT_VERSION/bin/python3\"\n                    if [ -f \"$PYENV_PYTHON\" ] && [ -x \"$PYENV_PYTHON\" ]; then\n                        PYTHON_EXEC=\"$PYENV_PYTHON\"\n                    fi\n                fi\n            fi\n            \n            # \u6267\u884cPython\u4ee3\u7801\n            $PYTHON_EXEC -c \"import base64; exec(base64.b64decode(open(\\\"/content/drive/MyDrive/REMOTE_ROOT/tmp/python_code_1759273907_06cb.b64\\\").read().strip()).decode(\\\"utf-8\\\"))\"\n            PYTHON_EXIT_CODE=$?\n            \n            # \u6e05\u7406\u4e34\u65f6\u6587\u4ef6\n            rm -f \"/content/drive/MyDrive/REMOTE_ROOT/tmp/python_code_1759273907_06cb.b64\"\n            \n            # \u8fd4\u56dePython\u811a\u672c\u7684\u9000\u51fa\u7801\n            exit $PYTHON_EXIT_CODE"],
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
    python3 "$PYTHON_SCRIPT" > "/content/drive/MyDrive/REMOTE_ROOT/tmp/cmd_1759273907_d83bfa3d.json"
    rm -f "$PYTHON_SCRIPT"
    
    # 清理临时文件（在JSON生成之后）
    rm -f "$OUTPUT_FILE" "$ERROR_FILE" "$EXITCODE_FILE"
    }
fi