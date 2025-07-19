#!/usr/bin/env python3
"""
EXTRACT_PDF.py - Enhanced PDF extraction using MinerU with integrated post-processing
All-in-one PDF processing tool with image analysis using IMG2TEXT
"""

import os
import sys
import json
import subprocess
import argparse
import hashlib
import re
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def get_run_context():
    """获取 RUN 执行上下文信息"""
    run_identifier = os.environ.get('RUN_IDENTIFIER')
    output_file = os.environ.get('RUN_OUTPUT_FILE')
    
    if run_identifier and output_file:
        return {
            'in_run_context': True,
            'identifier': run_identifier,
            'output_file': output_file
        }
    else:
        return {
            'in_run_context': False,
            'identifier': None,
            'output_file': None
        }

def write_to_json_output(data, run_context):
    """将结果写入到指定的 JSON 输出文件中"""
    if not run_context['in_run_context'] or not run_context['output_file']:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(run_context['output_file'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(run_context['output_file'], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

class PDFExtractor:
    """PDF提取器，集成所有PDF处理功能"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.script_dir = Path(__file__).parent
        self.proj_dir = self.script_dir / "EXTRACT_PDF_PROJ"
        
    def extract_pdf_basic(self, pdf_path: Path, page_spec: str = None, output_dir: Path = None) -> Tuple[bool, str]:
        """基础PDF提取功能"""
        try:
            # 使用Python的基础PDF处理库
            import fitz  # PyMuPDF
            
            # 打开PDF文件
            doc = fitz.open(str(pdf_path))
            
            # 确定输出目录
            if output_dir is None:
                output_dir = pdf_path.parent
            else:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # 确定要处理的页面
            if page_spec:
                pages = self._parse_page_spec(page_spec, doc.page_count)
            else:
                pages = list(range(doc.page_count))
            
            # 构建输出文件名，包含页码信息
            base_name = pdf_path.stem
            if page_spec:
                # 格式化页码信息：例如 "1,3,5" -> "_p1,3,5"，"1-5" -> "_p1-5"
                page_suffix = f"_p{page_spec}"
                output_filename = f"{base_name}{page_suffix}.md"
            else:
                output_filename = f"{base_name}.md"
            
            output_file = output_dir / output_filename
            content = []
            
            for page_num in pages:
                page = doc[page_num]
                text = page.get_text()
                content.append(f"# Page {page_num + 1}\n\n{text}\n\n")
            
            # 写入markdown文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
            
            doc.close()
            return True, f"Basic extraction completed: {output_file}"
            
        except Exception as e:
            return False, f"Basic extraction failed: {str(e)}"
    
    def extract_pdf_mineru(self, pdf_path: Path, page_spec: str = None, output_dir: Path = None, 
                          enable_analysis: bool = False) -> Tuple[bool, str]:
        """使用MinerU进行PDF提取"""
        try:
            # 检查MinerU CLI是否可用
            mineru_cli = self.proj_dir / "pdf_extract_cli.py"
            if not mineru_cli.exists():
                return False, "MinerU CLI not available"
            
            # 构建MinerU命令
            cmd = [
                sys.executable, 
                str(mineru_cli),
                str(pdf_path)
            ]
            
            if page_spec:
                cmd.extend(['--page', page_spec])
            
            if output_dir:
                cmd.extend(['--output', str(output_dir)])
            
            # 始终使用MinerU
            cmd.append('--use-mineru')
            
            if not enable_analysis:
                cmd.append('--no-image-api')
                cmd.append('--async-mode')
            
            # 执行MinerU
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                # 检查是否有输出文件被创建，并复制到用户指定的目录
                output_file = self._handle_mineru_output(pdf_path, output_dir, result.stdout, page_spec)
                return True, f"MinerU extraction completed: {output_file}"
            else:
                return False, f"MinerU extraction failed: {result.stderr}"
                
        except Exception as e:
            return False, f"MinerU extraction error: {str(e)}"
    
    def _parse_page_spec(self, page_spec: str, total_pages: int) -> List[int]:
        """解析页面规格"""
        pages = []
        
        for part in page_spec.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                start = int(start.strip()) - 1  # 转换为0-based
                end = int(end.strip()) - 1
                pages.extend(range(max(0, start), min(total_pages, end + 1)))
            else:
                page = int(part.strip()) - 1  # 转换为0-based
                if 0 <= page < total_pages:
                    pages.append(page)
        
        return sorted(list(set(pages)))
    
    def _handle_mineru_output(self, pdf_path: Path, output_dir: Path, stdout: str, page_spec: str = None) -> str:
        """处理MinerU输出，将文件复制到用户指定的目录并修正图片路径"""
        try:
            # 确定输出目录
            if output_dir is None:
                output_dir = pdf_path.parent
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # 查找MinerU生成的markdown文件
            mineru_data_dir = self.proj_dir / "pdf_extractor_data" / "markdown"
            if mineru_data_dir.exists():
                # 找到最新的markdown文件
                md_files = list(mineru_data_dir.glob("*.md"))
                if md_files:
                    # 按修改时间排序，取最新的
                    latest_md = max(md_files, key=lambda f: f.stat().st_mtime)
                    
                    # 读取markdown内容并修正图片路径
                    with open(latest_md, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 修正图片路径：从相对路径改为绝对路径
                    images_dir = self.proj_dir / "pdf_extractor_data" / "images"
                    content = self._fix_image_paths(content, images_dir)
                    
                    # 构建目标文件名，包含页码信息
                    base_name = pdf_path.stem
                    if page_spec:
                        # 格式化页码信息：例如 "1,3,5" -> "_p1,3,5"，"1-5" -> "_p1-5"
                        page_suffix = f"_p{page_spec}"
                        target_filename = f"{base_name}{page_suffix}.md"
                    else:
                        target_filename = f"{base_name}.md"
                    
                    target_file = output_dir / target_filename
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    return str(target_file)
            
            # 如果没有找到文件，返回原始输出
            return stdout.strip()
            
        except Exception as e:
            return f"Output handling failed: {str(e)}"
    
    def _fix_image_paths(self, content: str, images_dir: Path) -> str:
        """修正markdown内容中的图片路径"""
        import re
        
        # 匹配图片引用：![alt](images/filename.jpg)
        pattern = r'!\[([^\]]*)\]\(images/([^)]+)\)'
        
        def replace_path(match):
            alt_text = match.group(1)
            filename = match.group(2)
            # 使用绝对路径
            absolute_path = images_dir / filename
            return f'![{alt_text}]({absolute_path})'
        
        return re.sub(pattern, replace_path, content)
    
    def clean_data(self) -> Tuple[bool, str]:
        """清理EXTRACT_PDF_PROJ中的缓存数据"""
        try:
            data_dir = self.proj_dir / "pdf_extractor_data"
            
            if not data_dir.exists():
                return True, "No cached data found"
            
            # 统计要删除的文件
            markdown_dir = data_dir / "markdown"
            images_dir = data_dir / "images"
            
            md_count = len(list(markdown_dir.glob("*.md"))) if markdown_dir.exists() else 0
            img_count = len(list(images_dir.glob("*"))) if images_dir.exists() else 0
            
            # 删除markdown文件
            if markdown_dir.exists():
                for md_file in markdown_dir.glob("*.md"):
                    md_file.unlink()
                print(f"🗑️  已删除 {md_count} 个markdown文件")
            
            # 删除图片文件
            if images_dir.exists():
                for img_file in images_dir.glob("*"):
                    if img_file.is_file():
                        img_file.unlink()
                print(f"🗑️  已删除 {img_count} 个图片文件")
            
            # 删除其他缓存文件
            cache_files = [
                data_dir / "images_analysis_cache.json"
            ]
            
            cache_count = 0
            for cache_file in cache_files:
                if cache_file.exists():
                    cache_file.unlink()
                    cache_count += 1
            
            if cache_count > 0:
                print(f"🗑️  已删除 {cache_count} 个缓存文件")
            
            total_deleted = md_count + img_count + cache_count
            if total_deleted > 0:
                return True, f"Successfully cleaned {total_deleted} cached files"
            else:
                return True, "No files to clean"
                
        except Exception as e:
            return False, f"Failed to clean data: {str(e)}"
    
    def extract_pdf(self, pdf_path: str, page_spec: str = None, output_dir: str = None, 
                   engine_mode: str = "mineru") -> Tuple[bool, str]:
        """执行PDF提取"""
        pdf_path = Path(pdf_path).expanduser().resolve()
        
        # 显示处理信息
        engine_descriptions = {
            "basic": "基础提取器（无图像/公式/表格处理）",
            "basic-asyn": "基础提取器异步模式（禁用分析）",
            "mineru": "MinerU提取器（无图像/公式/表格处理）",
            "mineru-asyn": "MinerU提取器异步模式（禁用分析）",
            "full": "完整处理流程（包含图像/公式/表格处理）"
        }
        
        if engine_mode in engine_descriptions:
            print(f"🚀 使用引擎: {engine_descriptions[engine_mode]}")
        
        if not pdf_path.exists():
            return False, f"PDF file not found: {pdf_path}"
        
        output_dir_path = Path(output_dir) if output_dir else None
        
        # 根据引擎模式选择处理方式
        if engine_mode == "basic":
            return self.extract_pdf_basic(pdf_path, page_spec, output_dir_path)
        elif engine_mode == "basic-asyn":
            return self.extract_pdf_basic(pdf_path, page_spec, output_dir_path)
        elif engine_mode == "mineru":
            return self.extract_pdf_mineru(pdf_path, page_spec, output_dir_path, enable_analysis=False)
        elif engine_mode == "mineru-asyn":
            return self.extract_pdf_mineru(pdf_path, page_spec, output_dir_path, enable_analysis=False)
        elif engine_mode == "full":
            return self.extract_pdf_mineru(pdf_path, page_spec, output_dir_path, enable_analysis=True)
        else:
            return False, f"Unknown engine mode: {engine_mode}"

class PDFPostProcessor:
    """PDF后处理器，用于处理图片、公式、表格的标签替换"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.script_dir = Path(__file__).parent
        
        # Import MinerUWrapper for advanced selective processing
        sys.path.insert(0, str(self.script_dir / "EXTRACT_PDF_PROJ"))
        from mineru_wrapper import MinerUWrapper
        self.mineru_wrapper = MinerUWrapper()
    
    def _select_markdown_file_interactive(self) -> str:
        """交互式选择markdown文件"""
        print("🔍 选择markdown文件进行后处理...")
        
        # 使用FILEDIALOG工具选择文件
        try:
            filedialog_path = self.script_dir / "FILEDIALOG"
            if not filedialog_path.exists():
                print("⚠️  FILEDIALOG工具不可用，使用传统方式选择文件")
                return self._select_markdown_file_traditional()
            
            # 调用FILEDIALOG工具选择.md文件
            cmd = [str(filedialog_path), '--types', 'md', '--title', 'Select Markdown File for Post-processing']
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                # 解析FILEDIALOG的输出
                output_text = result.stdout.strip()
                
                # 检查是否是"✅ Selected file:"格式的输出
                if "✅ Selected file:" in output_text:
                    lines = output_text.split('\n')
                    for line in lines:
                        if "✅ Selected file:" in line:
                            selected_file = line.split("✅ Selected file: ", 1)[1].strip()
                            if selected_file and Path(selected_file).exists():
                                print(f"✅ 已选择: {Path(selected_file).name}")
                                return selected_file
                            break
                    print("❌ 无法解析选择的文件路径")
                    return None
                else:
                    # 尝试解析JSON输出（RUN环境下）
                    try:
                        output_data = json.loads(output_text)
                        if output_data.get('success') and output_data.get('selected_file'):
                            selected_file = output_data['selected_file']
                            print(f"✅ 已选择: {Path(selected_file).name}")
                            return selected_file
                        else:
                            print("❌ 用户取消了文件选择")
                            return None
                    except json.JSONDecodeError:
                        # 如果既不是标准格式也不是JSON，直接使用输出
                        if output_text and Path(output_text).exists():
                            print(f"✅ 已选择: {Path(output_text).name}")
                            return output_text
                        else:
                            print("❌ 用户取消了文件选择")
                            return None
            else:
                print("❌ 文件选择失败")
                return None
                
        except Exception as e:
            print(f"⚠️  使用FILEDIALOG时出错: {e}")
            print("使用传统方式选择文件")
            return self._select_markdown_file_traditional()
    
    def _select_markdown_file_traditional(self) -> str:
        """传统方式选择markdown文件（备用方案）"""
        print("🔍 搜索EXTRACT_PDF生成的markdown文件...")
        
        # 搜索当前目录及其子目录中的markdown文件
        md_files = []
        search_dirs = [Path.cwd(), self.script_dir / "EXTRACT_PDF_PROJ" / "pdf_extractor_data"]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for md_file in search_dir.rglob("*.md"):
                    # 检查是否是EXTRACT_PDF生成的文件
                    # 方法1：有对应的extract_data目录
                    extract_data_dir = md_file.parent / f"{md_file.stem}_extract_data"
                    # 方法2：文件包含placeholder标记
                    has_placeholder = False
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        has_placeholder = '[placeholder:' in content
                    except:
                        pass
                    
                    if extract_data_dir.exists() or has_placeholder:
                        md_files.append(md_file)
        
        if not md_files:
            print("❌ 未找到任何EXTRACT_PDF生成的markdown文件")
            return None
        
        # 显示文件列表
        print("\n📄 找到以下markdown文件:")
        for i, md_file in enumerate(md_files, 1):
            # 检查是否有待处理的placeholder
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                image_count = len(re.findall(r'\[placeholder: image\]', content))
                formula_count = len(re.findall(r'\[placeholder: formula\]', content))
                table_count = len(re.findall(r'\[placeholder: table\]', content))
                total_count = image_count + formula_count + table_count
                
                status = f"({total_count}个待处理项目: 🖼️{image_count} 🧮{formula_count} 📊{table_count})" if total_count > 0 else "(已处理)"
                print(f"  {i}. {md_file.name} {status}")
                print(f"     路径: {md_file}")
                
            except Exception as e:
                print(f"  {i}. {md_file.name} (无法读取)")
                print(f"     路径: {md_file}")
        
        # 用户选择
        while True:
            try:
                choice = input(f"\n请选择要处理的文件 (1-{len(md_files)}, 或按回车取消): ").strip()
                
                if not choice:
                    print("❌ 已取消")
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(md_files):
                    selected_file = md_files[choice_num - 1]
                    print(f"✅ 已选择: {selected_file.name}")
                    return str(selected_file)
                else:
                    print(f"❌ 请输入1-{len(md_files)}之间的数字")
                    
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n❌ 已取消")
                return None
        
    def process_file(self, file_path: str, process_type: str, specific_ids: str = None, custom_prompt: str = None) -> bool:
        """
        处理PDF文件的后处理 - 使用高级selective processing
        
        Args:
            file_path: PDF文件路径或markdown文件路径，或者"interactive"进入交互模式
            process_type: 处理类型 ('image', 'formula', 'table', 'all')
            
        Returns:
            是否处理成功
        """
        # 检查是否进入交互模式
        if file_path == "interactive":
            file_path = self._select_markdown_file_interactive()
            if not file_path:
                return False
        
        file_path = Path(file_path)
        
        # 确定PDF文件和markdown文件路径
        if file_path.suffix == '.pdf':
            pdf_file = file_path
            md_file = file_path.parent / f"{file_path.stem}.md"
        elif file_path.suffix == '.md':
            md_file = file_path
            # 尝试找到对应的PDF文件
            pdf_file = file_path.parent / f"{file_path.stem}.pdf"
            if not pdf_file.exists():
                print(f"⚠️  未找到对应的PDF文件: {pdf_file}")
                print("🔄 使用传统处理方式...")
                return self._process_file_traditional(md_file, process_type)
        else:
            print(f"❌ 不支持的文件类型: {file_path.suffix}")
            return False
            
        if not md_file.exists():
            print(f"❌ Markdown文件不存在: {md_file}")
            return False
        
        if not pdf_file.exists():
            print(f"❌ PDF文件不存在: {pdf_file}")
            return False
            
        print(f"🔄 开始高级后处理 {md_file.name}...")
        
        try:
            # 使用MinerU wrapper的selective processing功能
            # 首先检查是否有postprocess JSON文件
            status_file = pdf_file.parent / f"{pdf_file.stem}_postprocess.json"
            
            if status_file.exists():
                print(f"📄 找到状态文件: {status_file.name}")
                
                # 读取状态文件，获取所有未处理的项目
                with open(status_file, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                
                # 直接使用MinerU wrapper进行selective processing
                # 它会处理ID生成和筛选逻辑
                if specific_ids:
                    # 处理specific_ids参数
                    if specific_ids in ['all_images', 'all_formulas', 'all_tables', 'all']:
                        # 将特殊关键词转换为具体的ID列表
                        items_to_process = []
                        for item in status_data.get('items', []):
                            if item.get('processed', False):
                                continue  # 跳过已处理的项目
                            
                            item_type = item.get('type')
                            # Generate ID from image_path if no id field
                            item_id = item.get('id')
                            if not item_id:
                                image_path = item.get('image_path', '')
                                if image_path:
                                    item_id = Path(image_path).stem
                            
                            if item_id:
                                if specific_ids == 'all':
                                    items_to_process.append(item_id)
                                elif specific_ids == 'all_images' and item_type == 'image':
                                    items_to_process.append(item_id)
                                elif specific_ids == 'all_formulas' and item_type in ['formula', 'interline_equation']:
                                    items_to_process.append(item_id)
                                elif specific_ids == 'all_tables' and item_type == 'table':
                                    items_to_process.append(item_id)
                    else:
                        # 处理具体的hash ID列表
                        items_to_process = [id.strip() for id in specific_ids.split(',')]
                else:
                    # 根据process_type筛选需要处理的项目
                    items_to_process = []
                    for item in status_data.get('items', []):
                        if item.get('processed', False):
                            continue  # 跳过已处理的项目
                        
                        item_type = item.get('type')
                        # Generate ID from image_path if no id field
                        item_id = item.get('id')
                        if not item_id:
                            image_path = item.get('image_path', '')
                            if image_path:
                                item_id = Path(image_path).stem
                        
                        if item_id:
                            if process_type == 'all':
                                items_to_process.append(item_id)
                            elif process_type == 'image' and item_type == 'image':
                                items_to_process.append(item_id)
                            elif process_type == 'formula' and item_type in ['formula', 'interline_equation']:
                                items_to_process.append(item_id)
                            elif process_type == 'table' and item_type == 'table':
                                items_to_process.append(item_id)
                
                if items_to_process:
                    print(f"🎯 找到 {len(items_to_process)} 个需要处理的项目")
                    
                    # 使用MinerU wrapper进行selective processing
                    success = self.mineru_wrapper.process_items_by_hash_ids(
                        str(pdf_file), items_to_process, process_type, custom_prompt
                    )
                    
                    if success:
                        print(f"✅ 高级后处理完成")
                        return True
                    else:
                        print(f"❌ 高级后处理失败")
                        return False
                else:
                    print(f"ℹ️  没有找到需要处理的 {process_type} 类型项目")
                    return True
            else:
                print(f"⚠️  未找到状态文件: {status_file.name}")
                print("🔄 尝试重新生成状态文件...")
                
                # 尝试重新生成状态文件
                regenerated = self.mineru_wrapper._regenerate_status_from_markdown(str(pdf_file), str(md_file))
                if regenerated:
                    print("✅ 状态文件重新生成成功，请重新运行后处理命令")
                    return True
                else:
                    print("🔄 使用传统处理方式...")
                    return self._process_file_traditional(md_file, process_type)
                    
        except Exception as e:
            print(f"❌ 高级后处理出错: {e}")
            print("🔄 回退到传统处理方式...")
            return self._process_file_traditional(md_file, process_type)
    
    def _process_file_traditional(self, md_file: Path, process_type: str) -> bool:
        """传统的文件处理方式（备用方案）"""
        print(f"🔄 使用传统方式处理 {md_file.name}...")
        
        # 不再依赖于特定的extract_data目录结构
        # 直接从markdown文件中解析图片路径
        extract_data_dir = None  # 设置为None，表示使用绝对路径模式
            
        # 根据处理类型执行相应的处理
        if process_type == 'all':
            success = True
            success &= self._process_images(md_file, extract_data_dir)
            success &= self._process_formulas(md_file, extract_data_dir)
            success &= self._process_tables(md_file, extract_data_dir)
            return success
        elif process_type == 'image':
            return self._process_images(md_file, extract_data_dir)
        elif process_type == 'formula':
            return self._process_formulas(md_file, extract_data_dir)
        elif process_type == 'table':
            return self._process_tables(md_file, extract_data_dir)
        else:
            print(f"❌ 不支持的处理类型: {process_type}")
            return False
    
    def _process_images(self, md_file: Path, extract_data_dir: Path) -> bool:
        """处理图片标签替换"""
        print("🖼️  处理图片...")
        
        try:
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找图片placeholder
            placeholder_pattern = r'\[placeholder: image\]\s*\n!\[([^\]]*)\]\(([^)]+)\)'
            matches = re.findall(placeholder_pattern, content)
            
            if not matches:
                print("ℹ️  未找到需要处理的图片placeholder")
                return True
            
            processed_count = 0
            for alt_text, image_path in matches:
                # 构建完整的图片路径
                if image_path.startswith('/'):
                    # 绝对路径，直接使用
                    full_image_path = Path(image_path)
                else:
                    # 相对路径，需要基于extract_data_dir
                    if extract_data_dir is None:
                        print(f"⚠️  相对路径但没有提取数据目录: {image_path}")
                        continue
                    full_image_path = extract_data_dir / image_path
                
                if full_image_path.exists():
                    # 使用IMG2TEXT工具分析图片
                    success, description = self._analyze_image_with_img2text(str(full_image_path))
                    
                    if success:
                        # 替换placeholder和图片引用
                        old_pattern = f"[placeholder: image]\n![{alt_text}]({image_path})"
                        new_content = f"![{alt_text}]({image_path})\n\n**图片分析:** {description}\n"
                        
                        content = content.replace(old_pattern, new_content, 1)
                        processed_count += 1
                    else:
                        # API调用失败，保留placeholder，添加错误信息
                        old_pattern = f"[placeholder: image]\n![{alt_text}]({image_path})"
                        new_content = f"[placeholder: image]\n[message: {description}]\n![{alt_text}]({image_path})"
                        
                        content = content.replace(old_pattern, new_content, 1)
                        print(f"⚠️  图片分析失败，保留placeholder: {description}")
                else:
                    # 图片文件不存在，也添加错误信息
                    old_pattern = f"[placeholder: image]\n![{alt_text}]({image_path})"
                    new_content = f"[placeholder: image]\n[message: 图片文件不存在: {full_image_path}]\n![{alt_text}]({image_path})"
                    
                    content = content.replace(old_pattern, new_content, 1)
                    print(f"⚠️  图片文件不存在: {full_image_path}")
            
            # 写回文件
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if processed_count > 0:
                print(f"✅ 成功处理了 {processed_count} 个图片")
            else:
                print("ℹ️  没有图片被成功处理")
            return True
            
        except Exception as e:
            print(f"❌ 处理图片时出错: {e}")
            return False
    
    def _analyze_image_with_img2text(self, image_path: str) -> tuple[bool, str]:
        """使用IMG2TEXT工具分析图片
        
        Returns:
            tuple[bool, str]: (是否成功, 分析结果或错误信息)
        """
        try:
            # 调用IMG2TEXT工具
            img2text_path = self.script_dir / "IMG2TEXT"
            if not img2text_path.exists():
                return False, "IMG2TEXT工具不可用"
            
            cmd = [str(img2text_path), image_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                try:
                    # 尝试解析JSON输出
                    output_data = json.loads(result.stdout)
                    if output_data.get('success'):
                        description = output_data.get('result', '图片分析完成')
                        return True, description
                    else:
                        # 从JSON中获取详细的错误信息
                        error_msg = output_data.get('reason', output_data.get('message', '图片分析失败'))
                        return False, error_msg
                except json.JSONDecodeError:
                    # 如果不是JSON，直接返回文本
                    output_text = result.stdout.strip()
                    if output_text:
                        # 检查是否是错误信息格式
                        if output_text.startswith("*[") and output_text.endswith("]*"):
                            # 移除错误信息的包装符号
                            error_msg = output_text[2:-2]  # 去掉 *[ 和 ]*
                            return False, error_msg
                        else:
                            return True, output_text
                    else:
                        return False, "图片分析无输出"
            else:
                # 检查stderr是否有详细错误信息
                stderr_text = result.stderr.strip()
                if stderr_text:
                    return False, f"图片分析失败: {stderr_text}"
                else:
                    return False, "图片分析失败: 未知错误"
                
        except Exception as e:
            return False, f"图片分析失败: {str(e)}"
    
    def _process_formulas(self, md_file: Path, extract_data_dir: Path) -> bool:
        """处理公式标签替换"""
        print("🧮 处理公式...")
        
        try:
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找公式placeholder
            placeholder_pattern = r'\[placeholder: formula\]\s*\n!\[([^\]]*)\]\(([^)]+)\)'
            matches = re.findall(placeholder_pattern, content)
            
            if not matches:
                print("ℹ️  未找到需要处理的公式placeholder")
                return True
            
            processed_count = 0
            for alt_text, image_path in matches:
                # 构建完整的图片路径
                if image_path.startswith('/'):
                    # 绝对路径，直接使用
                    full_image_path = Path(image_path)
                else:
                    # 相对路径，需要基于extract_data_dir
                    if extract_data_dir is None:
                        print(f"⚠️  相对路径但没有提取数据目录: {image_path}")
                        continue
                    full_image_path = extract_data_dir / image_path
                
                if full_image_path.exists():
                    # 使用UnimerNet分析公式图片
                    success, formula_latex = self._analyze_formula_with_unimernet(str(full_image_path))
                    
                    if success:
                        # 替换placeholder和图片引用
                        old_pattern = f"[placeholder: formula]\n![{alt_text}]({image_path})"
                        new_content = f"![{alt_text}]({image_path})\n\n**公式识别:** {formula_latex}\n"
                        
                        content = content.replace(old_pattern, new_content, 1)
                        processed_count += 1
                    else:
                        # API调用失败，保留placeholder，添加错误信息
                        old_pattern = f"[placeholder: formula]\n![{alt_text}]({image_path})"
                        new_content = f"[placeholder: formula]\n[message: {formula_latex}]\n![{alt_text}]({image_path})"
                        
                        content = content.replace(old_pattern, new_content, 1)
                        print(f"⚠️  公式识别失败，保留placeholder: {formula_latex}")
                else:
                    # 公式图片文件不存在，也添加错误信息
                    old_pattern = f"[placeholder: formula]\n![{alt_text}]({image_path})"
                    new_content = f"[placeholder: formula]\n[message: 公式图片文件不存在: {full_image_path}]\n![{alt_text}]({image_path})"
                    
                    content = content.replace(old_pattern, new_content, 1)
                    print(f"⚠️  公式图片文件不存在: {full_image_path}")
            
            # 写回文件
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if processed_count > 0:
                print(f"✅ 成功处理了 {processed_count} 个公式")
            else:
                print("ℹ️  没有公式被成功处理")
            return True
            
        except Exception as e:
            print(f"❌ 处理公式时出错: {e}")
            return False
    
    def _analyze_formula_with_unimernet(self, image_path: str) -> tuple[bool, str]:
        """使用UnimerNet分析公式图片
        
        Returns:
            tuple[bool, str]: (是否成功, 分析结果或错误信息)
        """
        try:
            # 检查UnimerNet是否可用
            unimernet_processor = self.script_dir / "EXTRACT_PDF_PROJ" / "unimernet_processor.py"
            if not unimernet_processor.exists():
                return False, "UnimerNet处理器不可用"
            
            # 调用UnimerNet处理器
            cmd = [sys.executable, str(unimernet_processor), image_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                output_text = result.stdout.strip()
                if output_text:
                    return True, output_text
                else:
                    return False, "公式识别无输出"
            else:
                return False, f"公式识别失败: {result.stderr}"
                
        except Exception as e:
            return False, f"公式识别失败: {str(e)}"

    def _process_tables(self, md_file: Path, extract_data_dir: Path) -> bool:
        """处理表格标签替换"""
        print("📊 处理表格...")
        
        try:
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找表格placeholder
            placeholder_pattern = r'\[placeholder: table\]\s*\n!\[([^\]]*)\]\(([^)]+)\)'
            matches = re.findall(placeholder_pattern, content)
            
            if not matches:
                print("ℹ️  未找到需要处理的表格placeholder")
                return True
            
            processed_count = 0
            for alt_text, image_path in matches:
                # 构建完整的图片路径
                if image_path.startswith('/'):
                    # 绝对路径，直接使用
                    full_image_path = Path(image_path)
                else:
                    # 相对路径，需要基于extract_data_dir
                    if extract_data_dir is None:
                        print(f"⚠️  相对路径但没有提取数据目录: {image_path}")
                        continue
                    full_image_path = extract_data_dir / image_path
                
                if full_image_path.exists():
                    # 使用IMG2TEXT工具分析表格图片
                    success, table_text = self._analyze_image_with_img2text(str(full_image_path))
                    
                    if success:
                        # 替换placeholder和图片引用
                        old_pattern = f"[placeholder: table]\n![{alt_text}]({image_path})"
                        new_content = f"![{alt_text}]({image_path})\n\n**表格识别:**\n{table_text}\n"
                        
                        content = content.replace(old_pattern, new_content, 1)
                        processed_count += 1
                    else:
                        # API调用失败，保留placeholder，添加错误信息
                        old_pattern = f"[placeholder: table]\n![{alt_text}]({image_path})"
                        new_content = f"[placeholder: table]\n[message: {table_text}]\n![{alt_text}]({image_path})"
                        
                        content = content.replace(old_pattern, new_content, 1)
                        print(f"⚠️  表格分析失败，保留placeholder: {table_text}")
                else:
                    # 表格图片文件不存在，也添加错误信息
                    old_pattern = f"[placeholder: table]\n![{alt_text}]({image_path})"
                    new_content = f"[placeholder: table]\n[message: 表格图片文件不存在: {full_image_path}]\n![{alt_text}]({image_path})"
                    
                    content = content.replace(old_pattern, new_content, 1)
                    print(f"⚠️  表格图片文件不存在: {full_image_path}")
            
            # 写回文件
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            if processed_count > 0:
                print(f"✅ 成功处理了 {processed_count} 个表格")
            else:
                print("ℹ️  没有表格被成功处理")
            return True
            
        except Exception as e:
            print(f"❌ 处理表格时出错: {e}")
            return False

def show_help():
    """显示帮助信息"""
    help_text = """EXTRACT_PDF - Enhanced PDF extraction using MinerU with post-processing

Usage: EXTRACT_PDF <pdf_file> [options]
       EXTRACT_PDF --post [<markdown_file>] [--post-type <type>]
       EXTRACT_PDF --full <pdf_file> [options]
       EXTRACT_PDF --clean-data

Options:
  --page <spec>        Extract specific page(s) (e.g., 3, 1-5, 1,3,5)
  --output <dir>       Output directory (default: same as PDF)
  --engine <mode>      Processing engine mode:
                       basic        - Basic extractor, no image/formula/table processing
                       basic-asyn   - Basic extractor, async mode (disable analysis)
                       mineru       - MinerU extractor, no image/formula/table processing
                       mineru-asyn  - MinerU extractor, async mode (disable analysis)
                       full         - Full pipeline with image/formula/table processing
                       (default: mineru)
  --post [<file>]      Post-process markdown file (replace placeholders)
                       If no file specified, enter interactive mode
  --post-type <type>   Post-processing type: image, formula, table, all (default: all)
  --ids <ids>          Specific hash IDs to process (comma-separated) or keywords:
                       all_images, all_formulas, all_tables, all
  --prompt <text>      Custom prompt for IMG2TEXT image analysis
  --full <file>        Full pipeline: extract PDF then post-process automatically
  --clean-data         Clean all cached markdown files and images from EXTRACT_PDF_PROJ
  --help, -h           Show this help message

Examples:
  EXTRACT_PDF document.pdf --page 3
  EXTRACT_PDF paper.pdf --page 1-5 --output /path/to/output
  EXTRACT_PDF document.pdf --engine full
  EXTRACT_PDF document.pdf --engine mineru
  EXTRACT_PDF --post document.md --post-type all
EXTRACT_PDF --post document.md --post-type image
EXTRACT_PDF --post document.md --ids 4edf23de78f80bedade9e9628d7de04677faf669c945a7438bc5741c054af036
EXTRACT_PDF --post document.md --ids all_images --prompt "Analyze this research figure focusing on quantitative results"
EXTRACT_PDF --post  # Interactive mode
EXTRACT_PDF --full document.pdf  # Full pipeline
EXTRACT_PDF --clean-data  # Clean cached data"""
    
    print(help_text)

def select_pdf_file():
    """使用GUI选择PDF文件"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        return file_path if file_path else None
    except ImportError:
        print("❌ tkinter not available, GUI file selection not supported")
        return None
    except Exception as e:
        print(f"❌ Error in file selection: {e}")
        return None

def main():
    """主函数"""
    run_context = get_run_context()
    
    args = sys.argv[1:]
    if not args:
        # 如果没有参数，尝试使用GUI选择文件
        pdf_file = select_pdf_file()
        if pdf_file:
            print(f"📄 已选择文件: {Path(pdf_file).name}")
            print(f"🔄 开始使用 MinerU 引擎处理...")
            print("⏳ 处理中，请稍候...")
            
            extractor = PDFExtractor()
            success, message = extractor.extract_pdf(pdf_file)
            
            if success:
                success_data = {
                    "success": True,
                    "message": message
                }
                if run_context['in_run_context']:
                    write_to_json_output(success_data, run_context)
                else:
                    print(f"✅ {message}")
                return 0
            else:
                error_data = {
                    "success": False,
                    "error": message
                }
                if run_context['in_run_context']:
                    write_to_json_output(error_data, run_context)
                else:
                    print(f"❌ {message}")
                return 1
        else:
            if run_context['in_run_context']:
                error_data = {"success": False, "error": "No PDF file specified"}
                write_to_json_output(error_data, run_context)
            else:
                print("❌ Error: No PDF file specified")
                print("Use --help for usage information")
            return 1
    
    # 解析参数
    pdf_file = None
    page_spec = None
    output_dir = None
    engine_mode = "mineru"
    post_file = None
    post_type = "all"
    post_ids = None
    post_prompt = None
    full_pipeline = False
    clean_data = False
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ['--help', '-h']:
            if run_context['in_run_context']:
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": show_help.__doc__
                }
                write_to_json_output(help_data, run_context)
            else:
                show_help()
            return 0
        elif arg == '--page':
            if i + 1 < len(args):
                page_spec = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --page requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--output':
            if i + 1 < len(args):
                output_dir = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --output requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--engine':
            if i + 1 < len(args):
                engine_mode = args[i + 1]
                if engine_mode not in ['basic', 'basic-asyn', 'mineru', 'mineru-asyn', 'full']:
                    error_msg = f"❌ Error: Invalid engine mode: {engine_mode}"
                    if run_context['in_run_context']:
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, run_context)
                    else:
                        print(error_msg)
                    return 1
                i += 2
            else:
                error_msg = "❌ Error: --engine requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--post':
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                post_file = args[i + 1]
                i += 2
            else:
                # 进入interactive mode
                post_file = "interactive"
                i += 1
        elif arg == '--full':
            if i + 1 < len(args) and not args[i + 1].startswith('-'):
                pdf_file = args[i + 1]
                full_pipeline = True
                i += 2
            else:
                error_msg = "❌ Error: --full requires a PDF file"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--clean-data':
            clean_data = True
            i += 1
        elif arg == '--ids':
            if i + 1 < len(args):
                post_ids = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --ids requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--prompt':
            if i + 1 < len(args):
                post_prompt = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --prompt requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg == '--post-type':
            if i + 1 < len(args):
                post_type = args[i + 1]
                if post_type not in ['image', 'formula', 'table', 'all', 'all_images', 'all_formulas', 'all_tables']:
                    error_msg = f"❌ Error: Invalid post-type: {post_type}"
                    if run_context['in_run_context']:
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, run_context)
                    else:
                        print(error_msg)
                    return 1
                i += 2
            else:
                error_msg = "❌ Error: --post-type requires a value"
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
        elif arg.startswith('-'):
            error_msg = f"❌ Unknown option: {arg}"
            if run_context['in_run_context']:
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, run_context)
            else:
                print(error_msg)
                print("Use --help for usage information")
            return 1
        else:
            if pdf_file is None:
                pdf_file = arg
            else:
                error_msg = "❌ Multiple PDF files specified. Only one file is supported."
                if run_context['in_run_context']:
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, run_context)
                else:
                    print(error_msg)
                return 1
            i += 1
    
    # 处理清理数据模式
    if clean_data:
        extractor = PDFExtractor()
        success, message = extractor.clean_data()
        
        if success:
            success_data = {
                "success": True,
                "message": message,
                "action": "clean_data"
            }
            if run_context['in_run_context']:
                write_to_json_output(success_data, run_context)
            else:
                print(f"✅ {message}")
            return 0
        else:
            error_data = {
                "success": False,
                "error": message,
                "action": "clean_data"
            }
            if run_context['in_run_context']:
                write_to_json_output(error_data, run_context)
            else:
                print(f"❌ {message}")
            return 1
    
    # 处理完整流程模式
    if full_pipeline:
        print(f"🚀 开始完整流程处理: {pdf_file}")
        
        # 第一步：PDF提取
        print("📄 第一步：PDF提取...")
        extractor = PDFExtractor()
        success, message = extractor.extract_pdf(pdf_file, page_spec, output_dir, engine_mode)
        
        if not success:
            error_data = {
                "success": False,
                "error": f"PDF extraction failed: {message}",
                "step": "extraction"
            }
            if run_context['in_run_context']:
                write_to_json_output(error_data, run_context)
            else:
                print(f"❌ PDF提取失败: {message}")
            return 1
        
        print(f"✅ PDF提取完成: {message}")
        
        # 第二步：自动查找生成的markdown文件并进行后处理
        print("🔄 第二步：自动后处理...")
        
        # 根据PDF文件路径推断markdown文件路径
        pdf_path = Path(pdf_file).expanduser().resolve()
        if output_dir:
            md_file = Path(output_dir) / f"{pdf_path.stem}.md"
        else:
            md_file = pdf_path.parent / f"{pdf_path.stem}.md"
        
        if md_file.exists():
            processor = PDFPostProcessor(debug=False)
            success = processor.process_file(str(md_file), post_type)
            
            if success:
                success_data = {
                    "success": True,
                    "message": f"Full pipeline completed: {pdf_file} -> {md_file}",
                    "extraction_result": message,
                    "post_processing": "completed",
                    "post_type": post_type
                }
                if run_context['in_run_context']:
                    write_to_json_output(success_data, run_context)
                else:
                    print(f"✅ 完整流程完成: {pdf_file} -> {md_file}")
                return 0
            else:
                # 即使后处理失败，PDF提取已成功
                warning_data = {
                    "success": True,
                    "message": f"PDF extraction completed but post-processing failed: {md_file}",
                    "extraction_result": message,
                    "post_processing": "failed",
                    "post_type": post_type
                }
                if run_context['in_run_context']:
                    write_to_json_output(warning_data, run_context)
                else:
                    print(f"✅ PDF提取完成，但后处理失败: {md_file}")
                    print("💡 您可以稍后使用 EXTRACT_PDF --post 手动进行后处理")
                return 0
        else:
            # markdown文件不存在
            warning_data = {
                "success": True,
                "message": f"PDF extraction completed but markdown file not found: {md_file}",
                "extraction_result": message,
                "post_processing": "skipped"
            }
            if run_context['in_run_context']:
                write_to_json_output(warning_data, run_context)
            else:
                print(f"✅ PDF提取完成，但未找到markdown文件: {md_file}")
            return 0
    
    # 处理后处理模式
    if post_file:
        processor = PDFPostProcessor(debug=False)
        success = processor.process_file(post_file, post_type, post_ids, post_prompt)
        
        if success:
            success_data = {
                "success": True,
                "message": f"Post-processing completed: {post_file}",
                "post_type": post_type
            }
            if run_context['in_run_context']:
                write_to_json_output(success_data, run_context)
            else:
                print(f"✅ 后处理完成: {post_file}")
            return 0
        else:
            error_data = {
                "success": False,
                "error": f"Post-processing failed: {post_file}",
                "post_type": post_type
            }
            if run_context['in_run_context']:
                write_to_json_output(error_data, run_context)
            else:
                print(f"❌ 后处理失败: {post_file}")
            return 1
    
    # 检查是否提供了PDF文件
    if pdf_file is None:
        error_msg = "❌ Error: No PDF file specified"
        if run_context['in_run_context']:
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, run_context)
        else:
            print(error_msg)
            print("Use --help for usage information")
        return 1
    
    # 执行PDF提取
    extractor = PDFExtractor()
    success, message = extractor.extract_pdf(pdf_file, page_spec, output_dir, engine_mode)
    
    if success:
        success_data = {
            "success": True,
            "message": message,
            "engine_mode": engine_mode
        }
        if run_context['in_run_context']:
            write_to_json_output(success_data, run_context)
        else:
            print(f"✅ {message}")
        return 0
    else:
        error_data = {
            "success": False,
            "error": message,
            "engine_mode": engine_mode
        }
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ {message}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 