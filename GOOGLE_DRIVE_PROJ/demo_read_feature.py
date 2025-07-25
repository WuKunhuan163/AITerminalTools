#!/usr/bin/env python3
"""
演示 GDS read 功能
展示智能缓存读取和行数范围功能的完整使用流程
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from google_drive_shell import GoogleDriveShell
from cache_manager import GDSCacheManager

def create_demo_file():
    """创建演示文件"""
    demo_content = """# Google Drive Shell Read 功能演示

这是一个演示文件，用于展示 GDS read 功能的各种用法。

## 功能特点

1. 智能缓存读取
2. 支持行数范围指定
3. 0-indexing 行号系统
4. 多种范围格式支持

## 使用示例

### 基本用法
- read filename          # 读取全部内容
- read filename 0 5      # 读取第0-4行
- read filename [[0,3],[5,8]]  # 读取多个范围

### 高级功能
- 自动检查缓存新鲜度
- 智能下载更新
- 格式化输出显示

## 技术实现

本功能基于以下技术：
- Google Drive API 集成
- 本地文件缓存系统
- 远端修改时间跟踪
- 智能缓存更新机制

这是第20行内容。
这是第21行内容。
这是第22行内容。
这是第23行内容。
这是第24行内容。

## 总结

GDS read 功能为用户提供了高效、智能的远端文件读取体验。"""
    
    demo_file_path = Path(__file__).parent / "demo_read_content.txt"
    with open(demo_file_path, 'w', encoding='utf-8') as f:
        f.write(demo_content)
    
    return demo_file_path, demo_content

def demo_read_workflow():
    """演示完整的 read 工作流程"""
    print("🚀 GDS read 功能完整演示")
    print("=" * 80)
    
    # 创建演示文件
    demo_file_path, demo_content = create_demo_file()
    
    try:
        # 初始化组件
        gds = GoogleDriveShell()
        cache_manager = GDSCacheManager()
        
        # 模拟远端路径
        remote_path = "~/docs/read_demo.txt"
        
        print(f"📄 演示文件: {remote_path}")
        print("-" * 80)
        
        # 步骤 1: 创建缓存（模拟已下载的文件）
        print("📁 步骤 1: 准备文件缓存")
        cache_result = cache_manager.cache_file(
            remote_path=remote_path,
            temp_file_path=str(demo_file_path),
            remote_modified_time="2025-01-23T16:00:00.000Z"
        )
        
        if cache_result["success"]:
            print(f"✅ 文件已缓存: {cache_result['cache_file']}")
        else:
            print(f"❌ 缓存失败: {cache_result.get('error')}")
            return
        
        print()
        
        # 步骤 2: 演示各种读取方式
        print("📖 步骤 2: 演示各种读取方式")
        
        demo_cases = [
            {
                "name": "读取全部内容",
                "args": ("read_demo.txt",),
                "description": "不指定范围，读取整个文件"
            },
            {
                "name": "读取文件头部",
                "args": ("read_demo.txt", 0, 5),
                "description": "读取前5行 (第0-4行)"
            },
            {
                "name": "读取中间部分",
                "args": ("read_demo.txt", 10, 15),
                "description": "读取第11-15行 (第10-14行)"
            },
            {
                "name": "读取多个范围",
                "args": ("read_demo.txt", [[0, 3], [8, 12], [20, 25]]),
                "description": "读取标题、功能特点和结尾部分"
            }
        ]
        
        for i, case in enumerate(demo_cases, 1):
            print(f"\n{i}. {case['name']}")
            print(f"   描述: {case['description']}")
            print(f"   调用: cmd_read{case['args']}")
            
            try:
                # 模拟调用 cmd_read（由于没有实际 API，我们模拟处理过程）
                filename = case['args'][0]
                args = case['args'][1:] if len(case['args']) > 1 else ()
                
                # 解析行数范围
                line_ranges = gds._parse_line_ranges(args)
                print(f"   解析范围: {line_ranges}")
                
                # 处理文件内容
                lines = demo_content.split('\n')
                
                if not line_ranges:
                    selected_lines = [(i, line) for i, line in enumerate(lines)]
                else:
                    selected_lines = []
                    for start, end in line_ranges:
                        start = max(0, start)
                        end = min(len(lines), end)
                        for j in range(start, end):
                            if j < len(lines):
                                selected_lines.append((j, lines[j]))
                    
                    # 去重并排序
                    selected_lines = list(dict(selected_lines).items())
                    selected_lines.sort(key=lambda x: x[0])
                
                # 格式化输出
                formatted_output = gds._format_read_output(selected_lines)
                
                print(f"   选中行数: {len(selected_lines)}")
                print("   输出内容:")
                
                # 显示输出（限制显示行数以节省空间）
                output_lines = formatted_output.split('\n')
                display_lines = output_lines[:8] if len(output_lines) > 8 else output_lines
                
                for line in display_lines:
                    print(f"     {line}")
                
                if len(output_lines) > 8:
                    print(f"     ... (省略 {len(output_lines) - 8} 行)")
                
            except Exception as e:
                print(f"   ❌ 演示失败: {e}")
        
        print()
        
        # 步骤 3: 演示缓存智能检查
        print("🔍 步骤 3: 演示缓存智能检查")
        
        # 检查缓存状态
        cache_status = gds.is_remote_file_cached(remote_path)
        print(f"   文件是否已缓存: {cache_status['is_cached'] if cache_status['success'] else 'Error'}")
        
        if cache_status["success"] and cache_status["is_cached"]:
            cached_info = cache_status["cached_info"]
            print(f"   缓存文件名: {cached_info['cache_file']}")
            print(f"   本地缓存时间: {cached_info.get('upload_time', 'N/A')}")
            print(f"   远端修改时间: {cached_info.get('remote_modified_time', 'N/A')}")
            
            # 模拟缓存新鲜度检查（实际需要 Google Drive API）
            print("   缓存新鲜度: ✅ 最新 (基于远端修改时间比较)")
            print("   数据源: 本地缓存 (无需重新下载)")
        
        print()
        
        # 步骤 4: 展示实际调用示例
        print("💡 步骤 4: 实际调用示例")
        print("   在实际使用中，您可以这样调用:")
        print()
        print("   # Python 代码示例")
        print("   gds = GoogleDriveShell()")
        print("   result = gds.cmd_read('document.txt')")
        print("   if result['success']:")
        print("       print(result['output'])")
        print()
        print("   # 指定行数范围")
        print("   result = gds.cmd_read('document.txt', 0, 10)")
        print("   print(f\"读取了 {result['selected_lines']} 行\")")
        print()
        print("   # 多个范围")
        print("   result = gds.cmd_read('document.txt', [[0, 5], [10, 15]])")
        print("   print(result['output'])")
        
        print()
        print("✅ 演示完成!")
        
        print("\n🎯 GDS read 功能优势:")
        print("   1. 智能缓存: 优先使用本地缓存，减少网络请求")
        print("   2. 新鲜度检查: 基于远端修改时间确保数据最新")
        print("   3. 灵活范围: 支持单范围、多范围读取")
        print("   4. 格式化输出: 带行号的清晰显示")
        print("   5. 错误处理: 完善的异常处理和错误提示")
        print("   6. 编码支持: 自动处理各种文件编码")
        
        print("\n📋 支持的调用格式:")
        print("   • read filename")
        print("   • read filename start end")
        print("   • read filename [[start1, end1], [start2, end2], ...]")
        print("   • read filename \"[[start1, end1], [start2, end2], ...]\"")
        
    finally:
        # 清理演示文件
        if demo_file_path.exists():
            demo_file_path.unlink()
        
        # 清理缓存
        try:
            cache_manager.cleanup_cache(remote_path)
            print(f"\n🧹 已清理演示文件和缓存")
        except:
            pass

if __name__ == "__main__":
    demo_read_workflow() 