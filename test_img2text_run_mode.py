#!/usr/bin/env python3
"""测试IMG2TEXT使用RUN模式调用FILEDIALOG"""
import sys
import os
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

# 模拟RUN FILEDIALOG的JSON输出
def mock_run_filedialog():
    return json.dumps({
        "success": True,
        "message": "File selected successfully",
        "result": "/Users/wukunhuan/.local/bin/_UNITTEST/_DATA/test_image.jpg"
    })

# 模拟subprocess.run
class MockResult:
    def __init__(self, stdout, returncode=0):
        self.stdout = stdout
        self.returncode = returncode

def mock_subprocess_run(cmd, **kwargs):
    if 'RUN' in str(cmd[0]) and 'FILEDIALOG' in cmd:
        return MockResult(mock_run_filedialog())
    return MockResult("", 1)

# 替换subprocess.run
import subprocess
original_run = subprocess.run
subprocess.run = mock_subprocess_run

# 模拟sys.argv为空参数（交互模式）
sys.argv = ['IMG2TEXT.py']

try:
    # 导入并运行IMG2TEXT的main函数
    import IMG2TEXT
    IMG2TEXT.main()
except SystemExit:
    pass
finally:
    # 恢复原来的subprocess.run
    subprocess.run = original_run
