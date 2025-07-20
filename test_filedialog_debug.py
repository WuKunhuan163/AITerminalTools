#!/usr/bin/env python3
"""调试FILEDIALOG的实际返回结果"""
import subprocess
import json

print("🖼️  正在启动文件选择对话框...")
print("📋 请选择一个图片文件，或者点击取消来查看不同的返回结果")

result = subprocess.run(['./RUN', '--show', 'FILEDIALOG', '--types', 'image', '--title', '选择图片文件 - 调试测试'], 
                       capture_output=True, text=True, check=False)

print(f"\n🔍 调试信息:")
print(f"   返回码: {result.returncode}")
print(f"   STDOUT: {repr(result.stdout)}")
print(f"   STDERR: {repr(result.stderr)}")

if result.stdout.strip():
    try:
        run_result = json.loads(result.stdout.strip())
        print(f"\n📋 解析后的JSON结果:")
        print(f"   success: {run_result.get('success')}")
        print(f"   message: {run_result.get('message')}")
        print(f"   result: {run_result.get('result')}")
        print(f"   完整结果: {run_result}")
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON解析失败: {e}")
else:
    print(f"\n⚠️  没有STDOUT输出")
