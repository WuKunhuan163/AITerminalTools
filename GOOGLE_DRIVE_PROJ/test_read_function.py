#!/usr/bin/env python3
"""
测试 GDS read 功能
验证智能缓存读取和行数范围功能
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from google_drive_shell import GoogleDriveShell
from cache_manager import GDSCacheManager

def create_test_file():
    """创建测试文件"""
    test_content = """这是第一行内容
这是第二行内容
这是第三行内容
这是第四行内容
这是第五行内容
这是第六行内容
这是第七行内容
这是第八行内容
这是第九行内容
这是第十行内容
这是第十一行内容
这是第十二行内容
这是第十三行内容"""
    
    test_file_path = Path(__file__).parent / "test_read_file.txt"
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    return test_file_path, test_content

def test_line_ranges_parsing():
    """测试行数范围解析功能"""
    print("🔍 测试行数范围解析功能")
    print("-" * 50)
    
    gds = GoogleDriveShell()
    
    # 测试用例
    test_cases = [
        # (args, expected_result, description)
        ((), None, "无参数 - 读取全部"),
        ((0, 5), [(0, 5)], "两个参数 - 读取0-4行"),
        (([[0, 5], [7, 12]],), [(0, 5), (7, 12)], "列表格式 - 多个范围"),
        (("[[0, 5], [7, 12]]",), [(0, 5), (7, 12)], "字符串列表格式 - 多个范围"),
        ((10, 5), False, "无效范围 - end < start"),
        ((-1, 5), False, "无效范围 - start < 0"),
        ((0, 5, 10), False, "参数过多"),
    ]
    
    for i, (args, expected, description) in enumerate(test_cases, 1):
        result = gds._parse_line_ranges(args)
        status = "✅" if result == expected else "❌"
        print(f"{i}. {description}")
        print(f"   输入: {args}")
        print(f"   预期: {expected}")
        print(f"   结果: {result} {status}")
        print()

def test_read_functionality():
    """测试读取功能"""
    print("📖 测试读取功能")
    print("-" * 50)
    
    # 创建测试文件
    test_file_path, test_content = create_test_file()
    
    try:
        # 初始化组件
        gds = GoogleDriveShell()
        cache_manager = GDSCacheManager()
        
        # 模拟远端路径
        remote_path = "~/test/read_test.txt"
        
        # 手动创建缓存（模拟已下载的文件）
        print("📁 创建测试缓存...")
        cache_result = cache_manager.cache_file(
            remote_path=remote_path,
            temp_file_path=str(test_file_path),
            remote_modified_time="2025-01-23T15:30:00.000Z"
        )
        
        if cache_result["success"]:
            print(f"✅ 缓存创建成功: {cache_result['cache_file']}")
        else:
            print(f"❌ 缓存创建失败: {cache_result.get('error')}")
            return
        
        print()
        
        # 测试各种读取方式
        test_cases = [
            ("read_test.txt", (), "读取全部内容"),
            ("read_test.txt", (0, 5), "读取前5行 (0-4)"),
            ("read_test.txt", (5, 10), "读取第6-10行 (5-9)"),
            ("read_test.txt", ([[0, 3], [5, 8]],), "读取多个范围 [0-2, 5-7]"),
        ]
        
        for i, (filename, args, description) in enumerate(test_cases, 1):
            print(f"{i}. {description}")
            print(f"   参数: filename='{filename}', args={args}")
            
            # 由于没有实际的 Google Drive API，我们直接测试解析和格式化功能
            try:
                # 模拟文件内容
                lines = test_content.split('\n')
                
                # 解析行数范围
                line_ranges = gds._parse_line_ranges(args)
                print(f"   解析的行数范围: {line_ranges}")
                
                # 选择行
                if not line_ranges:
                    selected_lines = [(i, line) for i, line in enumerate(lines)]
                else:
                    selected_lines = []
                    for start, end in line_ranges:
                        start = max(0, start)
                        end = min(len(lines), end)
                        for i in range(start, end):
                            if i < len(lines):
                                selected_lines.append((i, lines[i]))
                    
                    # 去重并排序
                    selected_lines = list(dict(selected_lines).items())
                    selected_lines.sort(key=lambda x: x[0])
                
                # 格式化输出
                formatted_output = gds._format_read_output(selected_lines)
                
                print(f"   选中行数: {len(selected_lines)}")
                print("   输出预览:")
                output_lines = formatted_output.split('\n')
                for line in output_lines[:5]:  # 只显示前5行
                    print(f"     {line}")
                if len(output_lines) > 5:
                    print(f"     ... (还有 {len(output_lines) - 5} 行)")
                
            except Exception as e:
                print(f"   ❌ 测试失败: {e}")
            
            print()
        
        # 测试缓存状态检查
        print("🔍 测试缓存状态检查")
        cache_status = gds.is_remote_file_cached(remote_path)
        print(f"   缓存状态: {cache_status['is_cached'] if cache_status['success'] else 'Error'}")
        
        if cache_status["success"] and cache_status["is_cached"]:
            cached_info = cache_status["cached_info"]
            print(f"   缓存文件: {cached_info['cache_file']}")
            print(f"   远端修改时间: {cached_info.get('remote_modified_time', 'N/A')}")
        
        print()
        
    finally:
        # 清理测试文件
        if test_file_path.exists():
            test_file_path.unlink()
        
        # 清理缓存
        try:
            cache_manager.cleanup_cache(remote_path)
            print("🧹 已清理测试文件和缓存")
        except:
            pass

def test_output_format():
    """测试输出格式"""
    print("📋 测试输出格式")
    print("-" * 50)
    
    gds = GoogleDriveShell()
    
    # 测试数据
    test_lines = [
        (0, "这是第一行"),
        (1, "这是第二行"),
        (5, "这是第六行"),
        (10, "这是第十一行"),
    ]
    
    formatted = gds._format_read_output(test_lines)
    print("格式化输出示例:")
    print(formatted)
    print()
    
    # 测试空输出
    empty_formatted = gds._format_read_output([])
    print(f"空输出测试: '{empty_formatted}' (应为空字符串)")

def main():
    """主测试函数"""
    print("🚀 测试 GDS read 功能")
    print("=" * 80)
    
    try:
        # 测试行数范围解析
        test_line_ranges_parsing()
        
        # 测试输出格式
        test_output_format()
        
        # 测试读取功能
        test_read_functionality()
        
        print("✅ 所有测试完成!")
        print("\n💡 功能特点:")
        print("   1. 支持智能缓存读取，优先使用本地缓存")
        print("   2. 支持多种行数范围格式")
        print("   3. 带行号的格式化输出 (0-indexing)")
        print("   4. 自动处理文件编码和错误")
        print("   5. 集成现有的下载和缓存系统")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 