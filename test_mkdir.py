#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/wukunhuan/.local/bin/GOOGLE_DRIVE_PROJ')

from google_drive_shell import GoogleDriveShell

def test_mkdir():
    """测试新的mkdir功能"""
    print("🧪 测试GDS mkdir功能...")
    
    try:
        shell = GoogleDriveShell()
        
        # 测试路径解析
        current_shell = shell.get_current_shell()
        if not current_shell:
            print("❌ 没有活跃的shell")
            return
            
        print(f"📍 当前shell: {current_shell.get('current_path', '~')}")
        
        # 测试路径解析函数
        test_paths = [
            "test_dir",
            "~/test_dir", 
            "./test_dir",
            "sub/dir"
        ]
        
        for path in test_paths:
            absolute_path = shell._resolve_absolute_mkdir_path(path, current_shell, False)
            print(f"📂 {path} -> {absolute_path}")
            
        # 测试验证函数
        print("\n🔍 测试验证功能...")
        verification = shell._verify_mkdir_result("test", current_shell)
        print(f"验证结果: {verification}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mkdir() 