#!/usr/bin/env python3
"""
Fix Formula Templates Script
Cleans up problematic formula templates that show placeholder text instead of actual formulas.
"""

import sys
import re
from pathlib import Path

def clean_formula_templates(markdown_file_path: str) -> bool:
    """Clean up formula templates that show placeholder text."""
    try:
        markdown_path = Path(markdown_file_path)
        if not markdown_path.exists():
            print(f"❌ 文件不存在: {markdown_file_path}")
            return False
        
        print(f"🔄 处理文件: {markdown_path}")
        
        # Read content
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern 1: Formula templates with [公式识别结果] placeholder
        pattern1 = r'\*\*公式识别结果:\*\*\s*\$\$\s*\\text\{\\?\[公式识别结果\\?\]\}.*?\$\$'
        
        def replace_formula_template(match):
            # Extract hash from the template if present
            hash_match = re.search(r'来自\s+([a-f0-9]+)\.jpg', match.group(0))
            if hash_match:
                hash_id = hash_match.group(1)
                print(f"   🔄 发现需要清理的公式模板: {hash_id}")
                return f'[placeholder: formula]\n![](images/{hash_id}.jpg)'
            else:
                print(f"   🔄 发现需要清理的公式模板: 未知hash")
                return '[placeholder: formula]\n![](images/unknown.jpg)'
        
        # Replace formula templates
        content = re.sub(pattern1, replace_formula_template, content, flags=re.DOTALL)
        
        # Pattern 2: Hash comments with problematic templates
        lines = content.split('\n')
        updated_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for hash comments followed by problematic templates
            if re.match(r'<!--\s*hash:\s*[a-f0-9]+\s*-->', line.strip()):
                hash_match = re.search(r'hash:\s*([a-f0-9]+)', line)
                if hash_match:
                    hash_id = hash_match.group(1)
                    
                    # Check next few lines for problematic formula template
                    template_found = False
                    j = i + 1
                    while j < min(i + 5, len(lines)):
                        if '**公式识别结果:**' in lines[j] and '[公式识别结果]' in ''.join(lines[j:j+3]):
                            # Found problematic template, replace with placeholder
                            updated_lines.append(f'[placeholder: formula]')
                            updated_lines.append(f'![](images/{hash_id}.jpg)')
                            print(f"   🔄 替换hash {hash_id} 的问题模板")
                            
                            # Skip the problematic template lines
                            while j < len(lines) and not lines[j].startswith('!['):
                                j += 1
                            if j < len(lines) and lines[j].startswith('!['):
                                j += 1  # Skip the image line too
                            i = j - 1  # Will be incremented at end of loop
                            template_found = True
                            break
                        j += 1
                    
                    if not template_found:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
            
            i += 1
        
        content = '\n'.join(updated_lines)
        
        # Save if changes were made
        if content != original_content:
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已清理模板占位符，文件已更新")
            return True
        else:
            print(f"ℹ️  未发现需要清理的模板")
            return False
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("用法: python fix_formula_templates.py <markdown_file>")
        print("示例: python fix_formula_templates.py paper.md")
        return 1
    
    markdown_file = sys.argv[1]
    
    print("🧹 公式模板清理工具")
    print("=" * 50)
    
    success = clean_formula_templates(markdown_file)
    
    if success:
        print("\n✅ 清理完成！现在可以重新运行 EXTRACT_PDF_POST 来正确处理公式。")
        print("使用命令: EXTRACT_PDF_POST <pdf_file> --type formula")
    else:
        print("\n❌ 清理失败或无需清理")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 