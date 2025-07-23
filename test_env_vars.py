#!/usr/bin/env python3
"""
测试 Google Drive 环境变量
"""

import os
import sys
sys.path.insert(0, "GOOGLE_DRIVE_PROJ")

def test_env_vars():
    """测试环境变量"""
    print("🔍 检查 Google Drive 环境变量...")
    
    required_vars = [
        'GOOGLE_DRIVE_SERVICE_TYPE',
        'GOOGLE_DRIVE_PROJECT_ID', 
        'GOOGLE_DRIVE_PRIVATE_KEY',
        'GOOGLE_DRIVE_CLIENT_EMAIL'
    ]
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value[:50]}..." if len(value) > 50 else f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
    
    print("\n🔧 测试 Google Drive API 初始化...")
    try:
        from google_drive_api import GoogleDriveService
        service = GoogleDriveService()
        print("✅ Google Drive API 初始化成功！")
        return True
    except Exception as e:
        print(f"❌ Google Drive API 初始化失败: {e}")
        return False

if __name__ == "__main__":
    # 手动加载 .zshrc 中的环境变量
    import subprocess
    result = subprocess.run(['zsh', '-c', 'source ~/.zshrc && env'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("📥 从 .zshrc 加载环境变量...")
        for line in result.stdout.split('\n'):
            if line.startswith('GOOGLE_DRIVE_'):
                key, _, value = line.partition('=')
                os.environ[key] = value
        print("✅ 环境变量加载完成")
    else:
        print("⚠️ 无法从 .zshrc 加载环境变量")
    
    test_env_vars() 