#!/usr/bin/env python3
"""
EXTRACT_PDF.py - Enhanced PDF extraction using MinerU with integrated post-processing
All-in-one PDF processing tool with image analysis using IMG2TEXT
"""

import os
import sys
import json
import subprocess
import hashlib
import re
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_pdf_extractor_data_dir():
    """Get the PDF extractor data directory path."""
    script_dir = Path(__file__).parent
    # 优先使用EXTRACT_PDF_DATA目录（数据与代码分离）
    data_dir = script_dir / "EXTRACT_PDF_DATA"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        # 创建必要的子目录
        (data_dir / "images").mkdir(exist_ok=True)
        (data_dir / "markdown").mkdir(exist_ok=True)
    return data_dir


def save_to_unified_data_directory(content: str, pdf_path: Path, page_spec: str = None, images_data: list = None, output_dir: Path = None) -> Tuple[str, str]:
    """
    统一的数据存储接口，供basic和mineru模式共用
    
    Args:
        content: markdown内容
        pdf_path: 原PDF文件路径
        page_spec: 页码规格 (如 "1", "1-5", "1,3,5")
        images_data: 图片数据列表 [{'bytes': bytes, 'hash': str, 'filename': str}, ...]
    
    Returns:
        tuple: (data_directory_md_path, pdf_directory_md_path)
    """
    import shutil
    
    # 获取数据目录
    data_dir = get_pdf_extractor_data_dir()
    markdown_dir = data_dir / "markdown"
    images_dir = data_dir / "images"
    
    # 确保目录存在
    markdown_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 找到下一个可用的数字文件名
    counter = 0
    while True:
        target_file = markdown_dir / f"{counter}.md"
        if not target_file.exists():
            break
        counter += 1
    
    # 保存markdown到数据目录
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 保存图片到数据目录
    if images_data:
        for img_data in images_data:
            img_file = images_dir / img_data['filename']
            with open(img_file, 'wb') as f:
                f.write(img_data['bytes'])
    
    # 创建输出目录的文件（如果指定了输出目录，否则使用PDF同层目录）
    pdf_stem = pdf_path.stem
    if page_spec:
        pdf_stem_with_pages = f"{pdf_stem}_p{page_spec}"
    else:
        pdf_stem_with_pages = pdf_stem
    
    # 使用指定的输出目录或PDF同层目录
    output_parent = output_dir if output_dir else pdf_path.parent
    same_name_md_file = output_parent / f"{pdf_stem_with_pages}.md"
    
    # 更新图片路径到绝对路径 (指向EXTRACT_PDF_DATA)
    updated_content = update_image_paths_to_data_directory(content, str(data_dir))
    
    # 保存到PDF同层目录
    with open(same_name_md_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    # 复制图片到输出目录的images文件夹
    if images_data:
        output_images_dir = output_parent / "images"
        output_images_dir.mkdir(exist_ok=True)
        
        for img_data in images_data:
            src_file = images_dir / img_data['filename']
            dst_file = output_images_dir / img_data['filename']
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
    
    return str(target_file), str(same_name_md_file)


def update_image_paths_to_data_directory(content: str, data_dir: str) -> str:
    """更新markdown内容中的图片路径，指向EXTRACT_PDF_DATA目录"""
    import re
    
    # 将相对路径的图片引用更新为绝对路径
    def replace_image_path(match):
        image_filename = match.group(2)
        abs_image_path = Path(data_dir) / "images" / image_filename
        return f"![{match.group(1)}]({abs_image_path})"
    
    # 匹配 ![...](images/filename) 格式
    updated_content = re.sub(r'!\[([^\]]*)\]\(images/([^)]+)\)', replace_image_path, content)
    
    return updated_content


def create_postprocess_status_file(pdf_path: Path, page_spec: str = None, images_data: list = None) -> str:
    """创建后处理状态文件，用于追踪placeholder处理状态"""
    import json
    from datetime import datetime
    
    pdf_stem = pdf_path.stem
    if page_spec:
        pdf_stem_with_pages = f"{pdf_stem}_p{page_spec}"
    else:
        pdf_stem_with_pages = pdf_stem
    
    status_file = pdf_path.parent / f"{pdf_stem_with_pages}_postprocess.json"
    
    # 创建状态数据
    status_data = {
        "pdf_file": str(pdf_path),
        "created_at": datetime.now().isoformat(),
        "page_range": page_spec,
        "total_items": len(images_data) if images_data else 0,
        "processed_items": 0,
        "items": []
    }
    
    # 添加图片项目
    if images_data:
        for img_data in images_data:
            item = {
                "id": img_data['hash'],
                "type": "image",  # basic模式主要处理图片
                "filename": img_data['filename'],
                "image_path": f"images/{img_data['filename']}",  # 添加image_path字段
                "processor": "basic_extractor",
                "processed": False,
                "placeholder": f"![](images/{img_data['filename']})",
                "bbox": img_data.get('bbox', []),
                "page": img_data.get('page', 1)
            }
            status_data["items"].append(item)
    
    # 保存状态文件
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)
    
    print(f"Post-processing status saved to: {status_file.name}")
    return str(status_file)

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 全局变量
original_pdf_dir = None

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
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
        """基础PDF提取功能 - 使用统一数据存储接口"""
        import time
        import hashlib
        
        start_time = time.time()
        
        try:
            # 使用Python的基础PDF处理库
            import fitz  # PyMuPDF
            
            # 打开PDF文件
            doc = fitz.open(str(pdf_path))
            
            # 确定要处理的页面
            if page_spec:
                pages = self._parse_page_spec(page_spec, doc.page_count)
            else:
                pages = list(range(doc.page_count))
            
            content = []
            images_data = []
            
            # 结束性标点符号列表（用于文本处理）
            ending_punctuations = {'。', '.', '!', '?', '！', '？', ':', '：', ';', '；'}
            
            # 处理每一页
            for page_num in pages:
                page = doc[page_num]
                
                # 提取文本
                text = page.get_text()
                
                # 提取图片 - 使用图片合并功能
                image_list = page.get_images(full=True)
                page_content = f"# Page {page_num + 1}\n\n"
                
                # 图片合并处理：将临近的图片合并成一张大图
                if image_list:
                    # 使用与basic模式相同的图片合并逻辑
                    merged_images_info = self._merge_nearby_images_to_data(doc, page, image_list, page_num + 1)
                    
                    # 收集图片数据
                    images_data.extend(merged_images_info)
                    
                    # 为每个合并后的图片添加placeholder（与basic模式一致）
                    for img_info in merged_images_info:
                        page_content += f"[placeholder: image]\n"
                        page_content += f"![](images/{img_info['filename']})\n\n"
                
                # 处理正文换行符（与basic模式一致）
                processed_text = self._process_text_linebreaks(text, ending_punctuations)
                
                # 添加页面文本
                page_content += f"{processed_text}\n\n"
                content.append(page_content)
            
            doc.close()
            
            # 合并所有内容
            full_content = '\n'.join(content)
            
            # 使用统一数据存储接口保存数据
            data_md_path, pdf_md_path = save_to_unified_data_directory(
                full_content, pdf_path, page_spec, images_data, output_dir
            )
            
            # 创建extract_data文件夹（用户要求）
            if output_dir:
                extract_data_dir = output_dir / f"{pdf_path.stem}_extract_data"
                extract_data_dir.mkdir(exist_ok=True)
                
                # 复制markdown文件到extract_data文件夹
                extract_data_md = extract_data_dir / f"{pdf_path.stem}.md"
                import shutil
                shutil.copy2(pdf_md_path, extract_data_md)
                
                # 复制图片到extract_data文件夹
                if images_data:
                    extract_data_images_dir = extract_data_dir / "images"
                    extract_data_images_dir.mkdir(exist_ok=True)
                    
                    images_dir = output_dir / "images"
                    if images_dir.exists():
                        for img_data in images_data:
                            src_file = images_dir / img_data['filename']
                            dst_file = extract_data_images_dir / img_data['filename']
                            if src_file.exists():
                                shutil.copy2(src_file, dst_file)
                
                print(f"Created extract_data folder: {extract_data_dir}")
            
            # 创建postprocess状态文件
            if images_data:
                create_postprocess_status_file(pdf_path, page_spec, images_data)
            
            # 计算处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"Total processing time: {processing_time:.2f} seconds")
            print(f"Data saved to: {data_md_path}")
            if images_data:
                print(f"Extracted {len(images_data)} images")
            
            return True, f"Basic extraction completed: {pdf_md_path}"
            
        except Exception as e:
            return False, f"Basic extraction failed: {str(e)}"
    
    def extract_pdf_mineru(self, pdf_path: Path, page_spec: str = None, output_dir: Path = None, 
                          enable_analysis: bool = False, use_batch_processing: bool = True) -> Tuple[bool, str]:
        """使用MinerU进行PDF提取"""
        import time
        
        start_time = time.time()
        
        try:
            # 如果启用批处理模式，使用新的分页处理器
            if use_batch_processing:
                try:
                    from EXTRACT_PDF_PROJ.page_batch_processor import PageBatchProcessor
                    
                    processor = PageBatchProcessor()
                    
                    # 设置输出目录
                    if output_dir is None:
                        output_dir = self.data_dir / "batch_output" / pdf_path.stem
                    
                    print(f"Using batch processing mode for PDF: {pdf_path.name}")
                    success, message = processor.process_pdf_batch(pdf_path, output_dir, page_spec)
                    
                    if success:
                        # 计算处理时间
                        end_time = time.time()
                        processing_time = end_time - start_time
                        return True, f"批处理完成 ({processing_time:.1f}s): {message}"
                    else:
                        print(f"Batch processing failed, fallback to traditional mode: {message}")
                        # 继续使用传统模式
                except ImportError as e:
                    print(f"Batch processing module unavailable, using traditional mode: {e}")
                except Exception as e:
                    print(f"Batch processing mode error, using traditional mode: {e}")
            
            # 传统模式处理
            print("Using traditional mode to process PDF...")
            
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
            
            # Print stderr for debugging
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            # 计算处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            if result.returncode == 0:
                # 检查是否有输出文件被创建，并复制到用户指定的目录
                output_file = self._handle_mineru_output(pdf_path, output_dir, result.stdout, page_spec)
                print(f"Total processing time: {processing_time:.2f} seconds")
                return True, f"MinerU extraction completed: {output_file}"
            else:
                print(f"Total processing time: {processing_time:.2f} seconds")
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
            mineru_data_dir = get_pdf_extractor_data_dir() / "markdown"
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
                    images_dir = get_pdf_extractor_data_dir() / "images"
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
            data_dir = get_pdf_extractor_data_dir()
            
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
                print(f"Deleted {md_count} markdown files")
            
            # 删除图片文件
            if images_dir.exists():
                for img_file in images_dir.glob("*"):
                    if img_file.is_file():
                        img_file.unlink()
                print(f"Deleted {img_count} image files")
            
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
                print(f"Deleted {cache_count} cache files")
            
            total_deleted = md_count + img_count + cache_count
            if total_deleted > 0:
                return True, f"Successfully cleaned {total_deleted} cached files"
            else:
                return True, "No files to clean"
                
        except Exception as e:
            return False, f"Failed to clean data: {str(e)}"
    
    def extract_pdf(self, pdf_path: str, page_spec: str = None, output_dir: str = None, 
                   engine_mode: str = "mineru", use_batch_processing: bool = True) -> Tuple[bool, str]:
        """执行PDF提取"""
        pdf_path = Path(pdf_path).expanduser().resolve()
        
        # 显示处理信息
        engine_descriptions = {
            "basic": "Basic extractor (no image/formula/table processing)",
            "basic-asyn": "Basic extractor asynchronous mode (disable analysis)",
            "mineru": "MinerU extractor (batch processing enabled)" if use_batch_processing else "MinerU extractor (traditional mode)",
            "mineru-asyn": "MinerU extractor asynchronous mode (disable analysis)",
            "full": "Full processing pipeline (includes image/formula/table processing)"
        }
        
        if engine_mode in engine_descriptions:
            print(f"Using engine: {engine_descriptions[engine_mode]}")
        
        if not pdf_path.exists():
            return False, f"PDF file not found: {pdf_path}"
        
        output_dir_path = Path(output_dir) if output_dir else None
        
        # 根据引擎模式选择处理方式
        if engine_mode == "basic":
            return self.extract_pdf_basic_with_images(pdf_path, page_spec, output_dir_path)
        elif engine_mode == "basic-asyn":
            return self.extract_pdf_basic(pdf_path, page_spec, output_dir_path)
        elif engine_mode == "mineru":
            return self.extract_pdf_mineru(pdf_path, page_spec, output_dir_path, enable_analysis=False, use_batch_processing=use_batch_processing)
        elif engine_mode == "mineru-asyn":
            return self.extract_pdf_mineru(pdf_path, page_spec, output_dir_path, enable_analysis=False, use_batch_processing=use_batch_processing)
        elif engine_mode == "full":
            return self.extract_pdf_mineru(pdf_path, page_spec, output_dir_path, enable_analysis=True, use_batch_processing=use_batch_processing)
        else:
            return False, f"Unknown engine mode: {engine_mode}"
    
    def extract_pdf_basic_with_images(self, pdf_path: Path, page_spec: str = None, output_dir: Path = None) -> Tuple[bool, str]:
        """基础PDF提取功能，包含图片提取和placeholder生成 - 使用统一数据存储"""
        import time
        import hashlib
        from PIL import Image
        
        start_time = time.time()
        
        try:
            # 使用Python的基础PDF处理库
            import fitz  # PyMuPDF
            
            # 打开PDF文件
            doc = fitz.open(str(pdf_path))
            
            # 确定要处理的页面
            if page_spec:
                pages = self._parse_page_spec(page_spec, doc.page_count)
            else:
                pages = list(range(doc.page_count))
            
            content = []
            images_data = []
            
            # 结束性标点符号列表
            ending_punctuations = {'。', '.', '!', '?', '！', '？', ':', '：', ';', '；'}
            
            for page_num in pages:
                page = doc[page_num]
                text = page.get_text()
                
                # 提取页面中的图片
                image_list = page.get_images(full=True)
                page_content = f"# Page {page_num + 1}\n\n"
                
                # 图片合并处理：将临近的图片合并成一张大图
                if image_list:
                    merged_images_info = self._merge_nearby_images_to_data(doc, page, image_list, page_num + 1)
                    
                    # 收集图片数据
                    images_data.extend(merged_images_info)
                    
                    # 为每个合并后的图片添加placeholder
                    for img_info in merged_images_info:
                        page_content += f"[placeholder: image]\n"
                        page_content += f"![](images/{img_info['filename']})\n\n"
                
                # 处理正文换行符
                processed_text = self._process_text_linebreaks(text, ending_punctuations)
                
                # 添加页面文本
                page_content += f"{processed_text}\n\n"
                content.append(page_content)
            
            doc.close()
            
            # 合并所有内容
            full_content = '\n'.join(content)
            
            # 使用统一数据存储接口保存数据
            data_md_path, pdf_md_path = save_to_unified_data_directory(
                full_content, pdf_path, page_spec, images_data, output_dir
            )
            
            # 创建postprocess状态文件
            if images_data:
                create_postprocess_status_file(pdf_path, page_spec, images_data)
            
            # 计算处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"Total processing time: {processing_time:.2f} seconds")
            print(f"Data saved to: {data_md_path}")
            if images_data:
                print(f"Extracted and merged {len(images_data)} images")
            
            return True, f"Basic extraction with images completed: {pdf_md_path}"
            
        except Exception as e:
            return False, f"Basic extraction with images failed: {str(e)}"
    
    def _merge_nearby_images_to_data(self, doc, page, image_list, page_num):
        """通过PDF截屏合并临近的图片，返回图片数据"""
        import hashlib
        import fitz
        
        images_data = []
        
        if not image_list:
            return images_data
        
        try:
            # 获取所有图片的bbox信息
            image_rects = []
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    # 获取图片在页面中的矩形区域
                    img_rects = page.get_image_rects(xref)
                    if img_rects:
                        for rect in img_rects:
                            image_rects.append({
                                'index': img_index,
                                'xref': xref,
                                'bbox': rect,
                                'page': page_num
                            })
                except Exception as e:
                    print(f"Warning: Error getting image {img_index} position: {e}")
                    continue
            
            if not image_rects:
                return images_data
            
            # 如果只有一张图片，直接截屏
            if len(image_rects) == 1:
                rect_info = image_rects[0]
                bbox = rect_info['bbox']
                
                # 对单张图片区域进行截屏
                pix = page.get_pixmap(clip=bbox, dpi=200)
                img_bytes = pix.tobytes("png")
                img_hash = hashlib.md5(img_bytes).hexdigest()
                img_filename = f"{img_hash}.png"
                
                images_data.append({
                    'bytes': img_bytes,
                    'hash': img_hash,
                    'filename': img_filename,
                    'bbox': list(bbox),
                    'page': page_num
                })
                
                pix = None
                print(f"Screenshot saved single image: {img_filename}")
                
            else:
                # 多张图片：计算合并后的bbox并截屏
                # 找到所有图片的边界
                min_x0 = min(rect['bbox'].x0 for rect in image_rects)
                min_y0 = min(rect['bbox'].y0 for rect in image_rects)
                max_x1 = max(rect['bbox'].x1 for rect in image_rects)
                max_y1 = max(rect['bbox'].y1 for rect in image_rects)
                
                # 创建合并后的bbox
                merged_bbox = fitz.Rect(min_x0, min_y0, max_x1, max_y1)
                
                # 对合并区域进行截屏
                pix = page.get_pixmap(clip=merged_bbox, dpi=200)
                img_bytes = pix.tobytes("png")
                img_hash = hashlib.md5(img_bytes).hexdigest()
                img_filename = f"{img_hash}.png"
                
                images_data.append({
                    'bytes': img_bytes,
                    'hash': img_hash,
                    'filename': img_filename,
                    'bbox': list(merged_bbox),
                    'page': page_num
                })
                
                pix = None
                print(f"Screenshot merged {len(image_rects)} images into one large image: {img_filename}")
                
        except Exception as e:
            print(f"PDF screenshot process error: {e}")
            # 如果截屏失败，回退到传统方式处理
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    # 跳过CMYK图片
                    if pix.n - pix.alpha >= 4:
                        pix = None
                        continue
                    
                    # 转换为RGB
                    if pix.n - pix.alpha == 1:  # 灰度图
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                    img_data = pix.tobytes("png")
                    img_hash = hashlib.md5(img_data).hexdigest()
                    img_filename = f"{img_hash}.png"
                    
                    # 获取图片位置信息
                    try:
                        img_rects = page.get_image_rects(xref)
                        bbox = list(img_rects[0]) if img_rects else []
                    except:
                        bbox = []
                    
                    images_data.append({
                        'bytes': img_data,
                        'hash': img_hash,
                        'filename': img_filename,
                        'bbox': bbox,
                        'page': page_num
                    })
                    
                    pix = None
                    
                except Exception as e:
                    print(f"Failed to process image {img_index}: {e}")
        
        return images_data
    
    def _process_text_linebreaks(self, text, ending_punctuations):
        """处理正文换行符，智能合并句子和分段"""
        if not text.strip():
            return text
        
        lines = text.split('\n')
        processed_lines = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行
            if not line:
                if current_paragraph:
                    # 如果当前段落有内容，结束当前段落
                    paragraph_text = ' '.join(current_paragraph)
                    processed_lines.append(paragraph_text)
                    current_paragraph = []
                    processed_lines.append('')  # 添加空行表示段落分隔
                continue
            
            # 将当前行添加到段落中
            current_paragraph.append(line)
            
            # 检查行是否以结束性标点符号结尾
            if line and line[-1] in ending_punctuations:
                # 结束当前段落
                paragraph_text = ' '.join(current_paragraph)
                processed_lines.append(paragraph_text)
                current_paragraph = []
                processed_lines.append('')  # 添加空行表示段落分隔
        
        # 处理最后一个段落
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            processed_lines.append(paragraph_text)
        
        # 清理多余的空行
        result = []
        prev_empty = False
        for line in processed_lines:
            if line == '':
                if not prev_empty:
                    result.append(line)
                prev_empty = True
            else:
                result.append(line)
                prev_empty = False
        
        return '\n'.join(result)



class PDFPostProcessor:
    """PDF后处理器，用于处理图片、公式、表格的标签替换"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.script_dir = Path(__file__).parent
        
        # Use UNIMERNET tool for formula/table recognition instead of MinerU
        self.unimernet_tool = self.script_dir / "UNIMERNET"
        

    
    def process_file_unified(self, file_path: str, process_type: str, specific_ids: str = None, custom_prompt: str = None, force: bool = False, timeout_multi: float = 1.0) -> bool:
        """
        统一的后处理接口 - 不依赖于提取模式
        
        Args:
            file_path: PDF文件路径或markdown文件路径
            process_type: 处理类型 ('image', 'formula', 'table', 'all')
            specific_ids: 特定ID列表或关键词
            custom_prompt: 自定义提示词
            force: 是否强制重新处理
            
        Returns:
            是否处理成功
        """
        file_path = Path(file_path)
        
        # 确定PDF文件和markdown文件路径
        if file_path.suffix == '.pdf':
            pdf_file_path = file_path
            md_file = file_path.parent / f"{file_path.stem}.md"
        elif file_path.suffix == '.md':
            md_file = file_path
            # 尝试找到对应的PDF文件
            pdf_file_path = file_path.parent / f"{file_path.stem}.pdf"
        else:
            print(f"Error: Unsupported file type: {file_path.suffix}")
            return False
            
        if not md_file.exists():
            print(f"Error: Markdown file not found: {md_file}")
            return False
            
        print(f"Starting unified post-processing {md_file.name}...")
        
        try:
            # 第一步：确保有postprocess状态文件
            status_file = self._ensure_postprocess_status_file(pdf_file_path, md_file)
            if not status_file:
                print("Error: Failed to create or find status file")
                return False
            
            # 第二步：读取状态文件
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # 第三步：同步markdown和JSON中的placeholder信息
            print("Syncing markdown and JSON placeholder information...")
            status_data = self._sync_placeholders_with_markdown(md_file, status_data, status_file)
            
            # 第四步：筛选要处理的项目
            items_to_process = self._filter_items_to_process(status_data, process_type, specific_ids, force)
            
            if not items_to_process:
                print("No items to process")
                return True
            
            # 第五步：使用统一的混合处理方式
            success = self._process_items_unified(str(pdf_file_path), str(md_file), status_data, 
                                                items_to_process, process_type, custom_prompt, force, timeout_multi)
            
            return success
            
        except Exception as e:
            print(f"Error: Unified post-processing error: {e}")
            return False
    
    def _ensure_postprocess_status_file(self, pdf_file_path: Path, md_file: Path) -> Optional[Path]:
        """确保存在postprocess状态文件，如果不存在则创建"""
        status_file = pdf_file_path.parent / f"{pdf_file_path.stem}_postprocess.json"
        
        if status_file.exists():
            return status_file
        
        print("📄 Status file not found, regenerating from markdown...")
        
        # 从markdown文件分析placeholder，创建状态文件
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找所有placeholder和图片引用
            import re
            # 修复正则表达式以匹配包含分析结果的完整placeholder块
            # 这个模式匹配：[placeholder: type]\n![...](path) 后面可能跟着分析结果
            placeholder_pattern = r'\[placeholder:\s*(\w+)\]\s*\n!\[[^\]]*\]\(([^)]+)\)(?:\s*\n\n\*\*[^*]+\*\*.*?)?'
            matches = re.findall(placeholder_pattern, content, re.DOTALL)
            
            if not matches:
                print("No placeholder found, no post-processing needed")
                return None
            
            # 创建状态数据
            from datetime import datetime
            status_data = {
                "pdf_file": str(pdf_file_path),
                "created_at": datetime.now().isoformat(),
                "page_range": None,
                "total_items": len(matches),
                "processed_items": 0,
                "items": []
            }
            
            # 添加项目
            for item_type, image_path in matches:
                # 从图片路径提取hash ID
                image_filename = Path(image_path).name
                hash_id = Path(image_path).stem
                
                item = {
                    "id": hash_id,
                    "type": item_type,
                    "filename": image_filename,
                    "image_path": image_path,
                    "processor": "unified_processor",
                    "processed": False,
                    "placeholder": f"[placeholder: {item_type}]",
                    "bbox": [],
                    "page": 1  # 默认页码
                }
                status_data["items"].append(item)
            
            # 保存状态文件
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            print(f"Created status file: {status_file.name}")
            return status_file
            
        except Exception as e:
            print(f"Error: Failed to create status file: {e}")
            return None
    
    def _filter_items_to_process(self, status_data: dict, process_type: str, specific_ids: str, force: bool) -> list:
        """筛选需要处理的项目"""
        items_to_process = []
        
        for item in status_data.get('items', []):
            # 跳过已处理的项目（除非强制重新处理）
            if item.get('processed', False) and not force:
                continue
            
            item_type = item.get('type')
            item_id = item.get('id')
            
            # 根据处理类型筛选
            if process_type != 'all':
                if process_type == 'image' and item_type != 'image':
                    continue
                elif process_type == 'formula' and item_type not in ['formula', 'interline_equation']:
                    continue
                elif process_type == 'table' and item_type != 'table':
                    continue
            
            # 根据specific_ids筛选
            if specific_ids:
                if specific_ids in ['all_images', 'all_formulas', 'all_tables', 'all']:
                    if specific_ids == 'all':
                        pass  # 处理所有类型
                    elif specific_ids == 'all_images' and item_type != 'image':
                        continue
                    elif specific_ids == 'all_formulas' and item_type not in ['formula', 'interline_equation']:
                        continue
                    elif specific_ids == 'all_tables' and item_type != 'table':
                        continue
                else:
                    # 具体的hash ID列表
                    target_ids = [id.strip() for id in specific_ids.split(',')]
                    if item_id not in target_ids:
                        continue
            
            items_to_process.append(item_id)
        
        return items_to_process
    
    def _process_items_unified(self, pdf_file: str, md_file: str, status_data: dict, 
                             items_to_process: list, process_type: str, custom_prompt: str = None, force: bool = False, timeout_multi: float = 1.0) -> bool:
        """统一的项目处理方法"""
        try:
            # 读取markdown文件
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 处理每个项目
            updated = False
            for item_id in items_to_process:
                # 找到对应的项目
                item = None
                for status_item in status_data.get('items', []):
                    if status_item.get('id') == item_id:
                        item = status_item
                        break
                
                if not item:
                    print(f"Warning: Item not found: {item_id}")
                    continue
                
                item_type = item.get('type')
                image_path = item.get('image_path', '')
                
                if not image_path:
                    print(f"Warning: Image path is empty: {item_id}")
                    continue
                
                # 查找实际的图片文件路径
                actual_image_path = self._find_actual_image_path(pdf_file, image_path)
                if not actual_image_path:
                    print(f"Warning: Image file not found: {image_path}")
                    continue
                
                print(f"\nProcessing {item_type} item: {item_id}")
                
                # 根据类型选择处理方式
                result_text = ""
                if item_type == 'image':
                    result_text = self._process_image_with_api(actual_image_path, custom_prompt, timeout_multi)
                elif item_type in ['formula', 'interline_equation']:
                    result_text = self._process_with_unimernet(actual_image_path, "formula", force, timeout_multi)
                elif item_type == 'table':
                    result_text = self._process_with_unimernet(actual_image_path, "table", force, timeout_multi)
                
                if result_text:
                    # 更新markdown内容
                    success = self._update_markdown_with_result(md_content, item, result_text)
                    if success:
                        md_content = success
                        item['processed'] = True
                        updated = True
                        print(f"Completed {item_type} processing: {item_id}")
                    else:
                        print(f"Warning: Failed to update markdown: {item_id}")
                else:
                    print(f"Error: Processing failed: {item_id}")
            
            if updated:
                # 保存更新的markdown文件
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                # 更新状态文件
                status_file = Path(pdf_file).parent / f"{Path(pdf_file).stem}_postprocess.json"
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)
                
                print(f"Updated file: {Path(md_file).name}")
                return True
            else:
                print("No content to update")
                return True
                
        except Exception as e:
            print(f"Error: Unified processing error: {e}")
            return False
    def _find_actual_image_path(self, pdf_file: str, image_filename: str) -> Optional[str]:
        """查找图片文件的实际路径"""
        pdf_path = Path(pdf_file)
        pdf_directory = pdf_path.parent
        
        # 检查可能的图片位置
        possible_locations = [
            Path(image_filename),  # 绝对路径
            pdf_directory / image_filename,  # 相对于PDF的路径
            pdf_directory / "images" / Path(image_filename).name,  # PDF目录下的images文件夹
            get_pdf_extractor_data_dir() / "images" / Path(image_filename).name,  # 统一数据目录
        ]
        
        for location in possible_locations:
            if location.exists():
                return str(location)
        
        return None
    
    def _process_image_with_api(self, image_path: str, custom_prompt: str = None, timeout_multi: float = 1.0) -> str:
        """使用IMG2TEXT API处理图片"""
        try:
            # 调用IMG2TEXT工具
            img2text_path = self.script_dir / "IMG2TEXT"
            if not img2text_path.exists():
                return "IMG2TEXT tool not available"
            
            cmd = [str(img2text_path), image_path, "--json"]
            if custom_prompt:
                cmd.extend(["--prompt", custom_prompt])
            
            # 计算超时时间 (IMG2TEXT默认没有超时，我们设置2分钟 * timeout_multi)
            timeout = int(120 * timeout_multi)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
            
            if result.returncode == 0:
                try:
                    # 尝试解析JSON输出
                    output_data = json.loads(result.stdout)
                    if output_data.get('success'):
                        description = output_data.get('result', 'Image analysis completed')
                        return description
                    else:
                        error_msg = output_data.get('error', 'Unknown error')
                        return f"Image analysis failed: {error_msg}"
                except json.JSONDecodeError:
                    # 如果不是JSON格式，直接使用输出
                    return result.stdout.strip() if result.stdout.strip() else "Image analysis completed"
            else:
                return f"IMG2TEXT execution failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return f"IMG2TEXT processing timeout (timeout: {int(120 * timeout_multi)} seconds)"
        except Exception as e:
            return f"Image processing error: {e}"
    
    def _sync_placeholders_with_markdown(self, md_file: Path, status_data: dict, status_file: Path) -> dict:
        """同步markdown和JSON文件中的placeholder信息"""
        try:
            # 读取markdown内容
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找所有placeholder和图片引用
            import re
            # 修复正则表达式以匹配包含分析结果的完整placeholder块
            # 这个模式匹配：[placeholder: type]\n![...](path) 后面可能跟着分析结果
            placeholder_pattern = r'\[placeholder:\s*(\w+)\]\s*\n!\[[^\]]*\]\(([^)]+)\)(?:\s*\n\n\*\*[^*]+\*\*.*?)?'
            matches = re.findall(placeholder_pattern, content, re.DOTALL)
            
            # 更新状态数据中的项目
            existing_items = {item.get('id'): item for item in status_data.get('items', [])}
            updated_items = []
            
            for item_type, image_path in matches:
                # 从图片路径提取hash ID
                image_filename = Path(image_path).name
                hash_id = Path(image_path).stem
                
                # 如果项目已存在，保持其processed状态
                if hash_id in existing_items:
                    existing_item = existing_items[hash_id]
                    existing_item.update({
                        "type": item_type,
                        "filename": image_filename,
                        "image_path": image_path,
                        "placeholder": f"[placeholder: {item_type}]"
                    })
                    updated_items.append(existing_item)
                else:
                    # 新项目
                    item = {
                        "id": hash_id,
                        "type": item_type,
                        "filename": image_filename,
                        "image_path": image_path,
                        "processor": "unified_processor",
                        "processed": False,
                        "placeholder": f"[placeholder: {item_type}]",
                        "bbox": [],
                        "page": 1
                    }
                    updated_items.append(item)
            
            # 更新状态数据
            status_data["items"] = updated_items
            status_data["total_items"] = len(updated_items)
            status_data["processed_items"] = sum(1 for item in updated_items if item.get('processed', False))
            
            # 保存更新的状态文件
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            return status_data
            
        except Exception as e:
            print(f"Error: Failed to sync placeholder information: {e}")
            return status_data
    
    def _update_markdown_with_result(self, md_content: str, item: dict, result_text: str) -> Optional[str]:
        """更新markdown内容，保留placeholder，精确替换分析结果，避免误删正文"""
        import re
        
        item_type = item.get('type')
        image_path = item.get('image_path', '')
        image_filename = Path(image_path).name
        escaped_filename = re.escape(image_filename)
        escaped_type = re.escape(item_type)
        
        # 使用分步方法：先找到placeholder和图片，然后检查后面是否有分析结果
        # 更精确的模式：图片引用应该以.jpg/.png/.pdf等结尾，然后是)
        placeholder_img_pattern = (
            rf'\[placeholder:\s*{escaped_type}\]\s*\n'
            rf'!\[[^\]]*\]\([^)]*{escaped_filename}\)'
        )
        
        # 查找placeholder和图片的位置
        placeholder_match = re.search(placeholder_img_pattern, md_content)
        if not placeholder_match:
            print(f"Warning: No matching placeholder pattern found")
            return None
        
        placeholder_and_img = placeholder_match.group(0)
        start_pos = placeholder_match.start()
        end_pos = placeholder_match.end()
        
        # 检查后面是否有现有的分析结果需要替换
        remaining_content = md_content[end_pos:]
        
        # 定义各种分析结果的模式 - 更精确地匹配，避免误删正文
        analysis_patterns = [
            r'\n\n--- 图像分析结果 ---.*?\n--------------------',  # --- 图像分析结果 --- 块（包括后续内容和分隔线）
            r'\n\n\*\*图片分析:\*\*.*?(?=\n\n(?!\*\*)|$)',  # **图片分析:** 块（兼容旧格式）
            r'\n\n\*\*表格内容:\*\*.*?(?=\n\n(?!\*\*)|$)',  # **表格内容:** 块
            r'\n\n\*\*分析结果:\*\*.*?(?=\n\n(?!\*\*)|$)',  # **分析结果:** 块
            r'\n\n\$\$\n.*?\n\$\$',  # 多行公式块
            r'\n\n\$\$[^$\n]+\$\$',  # 单行公式块
            r'\n\n\$\$\n\\text\{.*?\}\n\$\$',  # 错误公式块（如识别失败信息）
        ]
        
        # 找到最早出现的分析结果
        earliest_match = None
        earliest_pos = len(remaining_content)
        
        for pattern in analysis_patterns:
            match = re.search(pattern, remaining_content, re.DOTALL)
            if match and match.start() < earliest_pos:
                earliest_match = match
                earliest_pos = match.start()
        
        if earliest_match:
            # 有现有分析结果，替换它
            print(f"🔍 Found existing analysis result, position: {earliest_pos}, length: {earliest_match.end() - earliest_match.start()}")
            analysis_end = end_pos + earliest_match.end()
            before_analysis = md_content[:start_pos]
            after_analysis = md_content[analysis_end:]
        else:
            # 没有现有分析结果，在placeholder后直接添加
            print(f"🔍 No existing analysis result found, adding directly")
            before_analysis = md_content[:start_pos]
            after_analysis = md_content[end_pos:]
        
        # 构建新的内容
        if item_type == 'image':
            new_content = f"{placeholder_and_img}\n\n{result_text}"
        elif item_type in ['formula', 'interline_equation']:
            new_content = f"{placeholder_and_img}\n\n{result_text}"
        elif item_type == 'table':
            new_content = f"{placeholder_and_img}\n\n**表格内容:**\n{result_text}"
        else:
            new_content = f"{placeholder_and_img}\n\n**分析结果:**\n{result_text}"
        
        # 组合最终内容
        updated_content = before_analysis + new_content + after_analysis
        
        return updated_content
    
    def _process_with_unimernet(self, image_path: str, content_type: str = "auto", force: bool = False, timeout_multi: float = 1.0) -> str:
        """使用UNIMERNET工具处理公式或表格图片"""
        try:
            # 使用EXTRACT_IMG工具（整合了UNIMERNET和cache）
            extract_img_tool = self.script_dir / "EXTRACT_IMG"
            if not extract_img_tool.exists():
                print(f"Warning: EXTRACT_IMG tool not available: {extract_img_tool}")
                return ""
            
            # 构建EXTRACT_IMG命令
            cmd = [str(extract_img_tool), image_path, "--json"]
            if content_type != "auto":
                cmd.extend(["--type", content_type])
            else:
                cmd.extend(["--type", "formula"])  # Default to formula for UNIMERNET
            
            # 添加force参数
            if force:
                cmd.append("--force")
            
            # 计算超时时间 (EXTRACT_IMG内部默认120秒，我们乘以timeout_multi)
            timeout = int(120 * timeout_multi)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
            
            if result.returncode == 0:
                # 解析EXTRACT_IMG的JSON输出
                try:
                    extract_result = json.loads(result.stdout)
                    if extract_result.get('success'):
                        recognition_result = extract_result.get('result', '')
                        if recognition_result:
                            # Check if it's from cache
                            cache_info = " (from cache)" if extract_result.get('from_cache') else ""
                            # Get processing time if available
                            processing_time = extract_result.get('processing_time', 0)
                            time_info = f" (processing time: {processing_time:.2f} seconds)" if processing_time > 0 else ""
                            print(f"EXTRACT_IMG recognition successful{cache_info}{time_info}: {len(recognition_result)} characters")
                            # Directly format as $$ without description wrapper
                            cleaned_result = recognition_result.strip()
                            return f"$$\n{cleaned_result}\n$$"
                        else:
                            print("Warning: EXTRACT_IMG returned empty result")
                            return f"$$\n\\text{{[formula recognition failed: EXTRACT_IMG returned empty result]}}\n$$"
                    else:
                        error_msg = extract_result.get('error', 'Unknown error')
                        print(f"Error: EXTRACT_IMG processing failed: {error_msg}")
                        return f"$$\n\\text{{[formula recognition failed: {error_msg}]}}\n$$"
                except json.JSONDecodeError as e:
                    error_msg = f"JSON parsing failed: {e}"
                    print(f"Error: Failed to parse EXTRACT_IMG JSON output: {e}")
                    print(f"   original output: {result.stdout[:200]}...")
                    return f"$$\n\\text{{[formula recognition failed: {error_msg}]}}\n$$"
            else:
                error_msg = f"EXTRACT_IMG execution failed: {result.stderr}"
                print(f"Error: EXTRACT_IMG execution failed: {result.stderr}")
                return f"$$\n\\text{{[formula recognition failed: {error_msg}]}}\n$$"
                
        except subprocess.TimeoutExpired:
            timeout_msg = f"EXTRACT_IMG processing timeout (timeout: {int(120 * timeout_multi)} seconds)"
            print(f"Error: {timeout_msg}")
            return f"$$\n\\text{{[formula recognition failed: {timeout_msg}]}}\n$$"
        except Exception as e:
            print(f"Error: UNIMERNET processing error: {e}")
            return f"$$\n\\text{{[formula recognition failed: UNIMERNET processing error: {e}]}}\n$$"
    

    

    
    def _select_markdown_file_interactive(self) -> str:
        """交互式选择markdown文件"""
        print("🔍 Selecting markdown file for post-processing...")
        
        # 使用FILEDIALOG工具选择文件
        try:
            filedialog_path = self.script_dir / "FILEDIALOG"
            if not filedialog_path.exists():
                print("Warning: FILEDIALOG tool not available, using traditional file selection")
                return self._select_markdown_file_traditional()
            
            # 调用FILEDIALOG工具选择.md文件
            cmd = [str(filedialog_path), '--types', 'md', '--title', 'Select Markdown File for Post-processing']
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                # 解析FILEDIALOG的输出
                output_text = result.stdout.strip()
                
                # 检查是否是" Selected file:"格式的输出
                if " Selected file:" in output_text:
                    lines = output_text.split('\n')
                    for line in lines:
                        if " Selected file:" in line:
                            selected_file = line.split(" Selected file: ", 1)[1].strip()
                            if selected_file and Path(selected_file).exists():
                                print(f" Selected: {Path(selected_file).name}")
                                return selected_file
                            break
                    print("Error: Failed to parse selected file path")
                    return None
                else:
                    # 尝试解析JSON输出（RUN环境下）
                    try:
                        output_data = json.loads(output_text)
                        if output_data.get('success') and output_data.get('selected_file'):
                            selected_file = output_data['selected_file']
                            print(f" Selected: {Path(selected_file).name}")
                            return selected_file
                        else:
                            print("Error: User cancelled file selection")
                            return None
                    except json.JSONDecodeError:
                        # 如果既不是标准格式也不是JSON，直接使用输出
                        if output_text and Path(output_text).exists():
                            print(f" Selected: {Path(output_text).name}")
                            return output_text
                        else:
                            print("Error: User cancelled file selection")
                            return None
            else:
                print("Error: File selection failed")
                return None
                
        except Exception as e:
            print(f"Warning: Error using FILEDIALOG: {e}")
            print("Using traditional file selection")
            return self._select_markdown_file_traditional()
    
    def _select_markdown_file_traditional(self) -> str:
        """传统方式选择markdown文件（备用方案）"""
        print("🔍 Searching for EXTRACT_PDF generated markdown files...")
        
        # 搜索当前目录及其子目录中的markdown文件
        md_files = []
        search_dirs = [Path.cwd(), get_pdf_extractor_data_dir()]
        
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
            print("Error: No EXTRACT_PDF generated markdown files found")
            return None
        
        # 显示文件列表
        print("\n📄 Found the following markdown files:")
        for i, md_file in enumerate(md_files, 1):
            # 检查是否有待处理的placeholder
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                image_count = len(re.findall(r'\[placeholder: image\]', content))
                formula_count = len(re.findall(r'\[placeholder: formula\]', content))
                table_count = len(re.findall(r'\[placeholder: table\]', content))
                total_count = image_count + formula_count + table_count
                
                status = f"({total_count} items to process: images:{image_count} formulas:{formula_count} tables:{table_count})" if total_count > 0 else "(processed)"
                print(f"  {i}. {md_file.name} {status}")
                print(f"     path: {md_file}")
                
            except Exception as e:
                print(f"  {i}. {md_file.name} (cannot read)")
                print(f"     path: {md_file}")
        
        # 用户选择
        while True:
            try:
                choice = input(f"\nPlease select the file to process (1-{len(md_files)}, or press Enter to cancel): ").strip()
                
                if not choice:
                    print("Error: Cancelled")
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(md_files):
                    selected_file = md_files[choice_num - 1]
                    print(f" Selected: {selected_file.name}")
                    return str(selected_file)
                else:
                    print(f"Error: Please enter a number between 1 and {len(md_files)}")
                    
            except ValueError:
                print("Error: Please enter a valid number")
            except KeyboardInterrupt:
                print("\nError: Cancelled")
                return None
        
    def process_file(self, file_path: str, process_type: str, specific_ids: str = None, custom_prompt: str = None, force: bool = False, timeout_multi: float = 1.0) -> bool:
        """
        处理PDF文件的后处理 - 使用统一接口（不依赖于提取模式）
        
        Args:
            file_path: PDF文件路径或markdown文件路径，或者"interactive"进入交互模式
            process_type: 处理类型 ('image', 'formula', 'table', 'all')
            specific_ids: 特定ID列表或关键词
            custom_prompt: 自定义提示词
            force: 是否强制重新处理
            
        Returns:
            是否处理成功
        """
        # 检查是否进入交互模式
        if file_path == "interactive":
            file_path = self._select_markdown_file_interactive()
            if not file_path:
                return False
        
        # 直接调用统一接口
        return self.process_file_unified(file_path, process_type, specific_ids, custom_prompt, force, timeout_multi)
    

    
    def _sync_placeholders_with_markdown(self, md_file: Path, status_data: dict, status_file: Path) -> dict:
        """
        同步markdown文件和JSON文件中的placeholder信息
        
        Args:
            md_file: markdown文件路径
            status_data: JSON状态数据
            status_file: JSON状态文件路径
            
        Returns:
            更新后的状态数据
        """
        try:
            # 读取markdown文件内容
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 解析markdown中的placeholder信息
            md_placeholders = self._parse_placeholders_from_markdown(md_content)
            print(f"   📋 Found {len(md_placeholders)} placeholders in markdown")
            
            # 创建JSON中现有项目的映射
            json_items = {item['id']: item for item in status_data.get('items', [])}
            print(f"   📄 {len(json_items)} items in JSON")
            
            # 同步过程
            updated_items = []
            md_content_modified = False
            
            # 1. 处理markdown中的placeholder，更新或添加到JSON
            for img_id, placeholder_type in md_placeholders.items():
                if img_id in json_items:
                    # 更新现有项目的类型
                    item = json_items[img_id]
                    old_type = item.get('type', 'unknown')
                    if old_type != placeholder_type:
                        print(f"   Updating item {img_id[:8]}... type: {old_type} → {placeholder_type}")
                        item['type'] = placeholder_type
                        item['processed'] = False  # 重置处理状态
                        # 更新处理器
                        if placeholder_type == 'image':
                            item['processor'] = 'Google API'
                        elif placeholder_type in ['formula', 'interline_equation']:
                            item['processor'] = 'UnimerNet'
                        elif placeholder_type == 'table':
                            item['processor'] = 'UnimerNet'
                    updated_items.append(item)
                    del json_items[img_id]  # 从待处理列表中移除
                else:
                    # 新增项目到JSON
                    print(f"   ➕ Adding new item {img_id[:8]}... type: {placeholder_type}")
                    new_item = {
                        "id": img_id,
                        "type": placeholder_type,
                        "page": 1,  # 默认页码
                        "block_index": -1,  # 标记为用户添加
                        "image_path": f"{img_id}.jpg",
                        "bbox": [],
                        "processed": False,
                        "processor": self._get_processor_for_type(placeholder_type)
                    }
                    updated_items.append(new_item)
            
            # 2. 处理JSON中剩余的项目（markdown中缺失的）
            for img_id, item in json_items.items():
                print(f"   🔧 Restoring missing placeholder {img_id[:8]}... type: {item['type']}")
                # 在markdown中恢复placeholder
                md_content = self._restore_placeholder_in_markdown(md_content, img_id, item['type'])
                md_content_modified = True
                updated_items.append(item)
            
            # 3. 保存修改后的markdown文件
            if md_content_modified:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"   Updated markdown file")
            
            # 4. 更新状态数据
            status_data['items'] = updated_items
            status_data['total_items'] = len(updated_items)
            
            # 重新计算counts
            counts = {"images": 0, "formulas": 0, "tables": 0}
            for item in updated_items:
                if not item.get('processed', False):  # 只计算未处理的项目
                    item_type = item.get('type', '')
                    if item_type == 'image':
                        counts['images'] += 1
                    elif item_type in ['formula', 'interline_equation']:
                        counts['formulas'] += 1
                    elif item_type == 'table':
                        counts['tables'] += 1
            
            status_data['counts'] = counts
            
            # 5. 保存更新后的JSON文件
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
            
            print(f"    Sync completed: {len(updated_items)} items")
            return status_data
            
        except Exception as e:
            print(f"   Warning: Sync error: {e}")
            return status_data
    
    def _parse_placeholders_from_markdown(self, md_content: str) -> dict:
        """从markdown内容中解析placeholder信息"""
        import re
        
        placeholders = {}
        
        # 修复正则表达式以正确匹配完整的哈希文件名
        # 匹配 [placeholder: type] 后跟 ![](path/to/hash.ext) 的模式
        pattern = r'\[placeholder:\s*(\w+)\]\s*\n!\[[^\]]*\]\([^)]*\/([a-f0-9]{16,64})\.(jpg|jpeg|png|gif|webp)\)'
        
        matches = re.findall(pattern, md_content)
        for placeholder_type, img_id, ext in matches:
            placeholders[img_id] = placeholder_type
        
        return placeholders
    
    def _restore_placeholder_in_markdown(self, md_content: str, img_id: str, placeholder_type: str) -> str:
        """在markdown中恢复缺失的placeholder"""
        import re
        
        # 查找对应的图片引用
        pattern = rf'!\[[^\]]*\]\([^)]*{re.escape(img_id)}\.jpg\)'
        match = re.search(pattern, md_content)
        
        if match:
            # 在图片前添加placeholder
            img_ref = match.group(0)
            placeholder_line = f"[placeholder: {placeholder_type}]\n{img_ref}"
            md_content = md_content.replace(img_ref, placeholder_line)
        
        return md_content
    
    def _get_processor_for_type(self, item_type: str) -> str:
        """根据类型获取处理器名称"""
        if item_type == 'image':
            return "Google API"
        elif item_type in ['formula', 'interline_equation']:
            return "UnimerNet"
        elif item_type == 'table':
            return "UnimerNet"
        else:
            return "Unknown"

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
  --output-dir <dir>   Alias for --output
  --engine <mode>      Processing engine mode:
                       basic        - Basic extractor, with image/formula/table analysis
                       basic-asyn   - Basic extractor, async mode (disable analysis)
                       mineru       - MinerU extractor, with image/formula/table analysis
                       mineru-asyn  - MinerU extractor, async mode (disable analysis)
                       full         - Full pipeline with image/formula/table analysis
                       (default: mineru)
  --post [<file>]      Post-process markdown file (replace placeholders)
                       If no file specified, enter interactive mode
  --post-type <type>   Post-processing type: image, formula, table, all (default: all)
  --ids <ids>          Specific hash IDs to process (comma-separated) or keywords:
                       all_images, all_formulas, all_tables, all
  --prompt <text>      Custom prompt for IMG2TEXT image analysis
  --force              Force reprocessing even if items are marked as processed
  --unimernet-timeout-multi <multiplier>  Timeout multiplier for UNIMERNET/IMG2TEXT processing
                       Default: 1.0 (120 seconds). Use 2.0 for 240 seconds, etc.
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
EXTRACT_PDF --post document.md --ids all_formulas --unimernet-timeout-multi 2.0  # Double timeout for large formulas
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
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        return file_path if file_path else None
    except ImportError:
        print("tkinter not available, GUI file selection not supported")
        return None
    except Exception as e:
        print(f"Error in file selection: {e}")
        return None

def main(args=None, command_identifier=None):
    """主函数"""
    global original_pdf_dir
    # 获取command_identifier
    if args is None:
        args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    if not args:
        # 如果没有参数，尝试使用GUI选择文件
        pdf_file = select_pdf_file()
        if pdf_file:
            print(f"Selected file: {Path(pdf_file).name}")
            print(f"Starting MinerU engine processing...")
            print("Please wait ...")
            
            extractor = PDFExtractor()
            success, message = extractor.extract_pdf(pdf_file)
            
            if success:
                success_data = {
                    "success": True,
                    "message": message
                }
                if is_run_environment(command_identifier):
                    write_to_json_output(success_data, command_identifier)
                else:
                    print(f"{message}")
                return 0
            else:
                error_data = {
                    "success": False,
                    "error": message
                }
                if is_run_environment(command_identifier):
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(f"{message}")
                return 1
        else:
            if is_run_environment(command_identifier):
                error_data = {"success": False, "error": "No PDF file specified"}
                write_to_json_output(error_data, command_identifier)
            else:
                print("Error: No PDF file specified")
                print("Use --help for usage information")
            return 1
    
    # 解析参数
    pdf_file = None
    page_spec = None
    output_dir = None
    engine_mode = "basic"
    post_file = None
    post_type = "all"
    post_ids = None
    post_prompt = None
    post_force = False
    post_timeout_multi = 1.0  # 超时倍数，默认1倍
    original_pdf_dir = None
    full_pipeline = False
    clean_data = False
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg in ['--help', '-h']:
            if is_run_environment(command_identifier):
                help_data = {
                    "success": True,
                    "message": "Help information",
                    "help": show_help.__doc__
                }
                write_to_json_output(help_data, command_identifier)
            else:
                show_help()
            return 0
        elif arg == '--page':
            if i + 1 < len(args):
                page_spec = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --page requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--output' or arg == '--output-dir':
            if i + 1 < len(args):
                output_dir = args[i + 1]
                i += 2
            else:
                error_msg = f"Error: {arg} requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--engine':
            if i + 1 < len(args):
                engine_mode = args[i + 1]
                if engine_mode not in ['basic', 'basic-asyn', 'mineru', 'mineru-asyn', 'full']:
                    error_msg = f"Error: Invalid engine mode: {engine_mode}"
                    if is_run_environment(command_identifier):
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, command_identifier)
                    else:
                        print(error_msg)
                    return 1
                i += 2
            else:
                error_msg = "Error: --engine requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
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
                error_msg = "Error: --full requires a PDF file"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--clean-data':
            clean_data = True
            i += 1
        elif arg == '--batch':
            # 启用批处理模式（默认已启用）
            i += 1
        elif arg == '--no-batch':
            # 禁用批处理模式
            i += 1
        elif arg == '--status':
            # 显示批处理状态
            i += 1
        elif arg == '--ids':
            if i + 1 < len(args):
                post_ids = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --ids requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--prompt':
            if i + 1 < len(args):
                post_prompt = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --prompt requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--post-type':
            if i + 1 < len(args):
                post_type = args[i + 1]
                if post_type not in ['image', 'formula', 'table', 'all', 'all_images', 'all_formulas', 'all_tables']:
                    error_msg = f"Error: Invalid post-type: {post_type}"
                    if is_run_environment(command_identifier):
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, command_identifier)
                    else:
                        print(error_msg)
                    return 1
                i += 2
            else:
                error_msg = "Error: --post-type requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--original-pdf-dir':
            if i + 1 < len(args):
                original_pdf_dir = args[i + 1]
                i += 2
            else:
                error_msg = "Error: --original-pdf-dir requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--force':
            post_force = True
            i += 1
        elif arg == '--unimernet-timeout-multi':
            if i + 1 < len(args):
                try:
                    post_timeout_multi = float(args[i + 1])
                    if post_timeout_multi <= 0:
                        error_msg = "Error: --unimernet-timeout-multi must be positive"
                        if is_run_environment(command_identifier):
                            error_data = {"success": False, "error": error_msg}
                            write_to_json_output(error_data, command_identifier)
                        else:
                            print(error_msg)
                        return 1
                    i += 2
                except ValueError:
                    error_msg = "Error: --unimernet-timeout-multi must be a number"
                    if is_run_environment(command_identifier):
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, command_identifier)
                    else:
                        print(error_msg)
                    return 1
            else:
                error_msg = "Error: --unimernet-timeout-multi requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg.startswith('-'):
            error_msg = f"Unknown option: {arg}"
            if is_run_environment(command_identifier):
                error_data = {"success": False, "error": error_msg}
                write_to_json_output(error_data, command_identifier)
            else:
                print(error_msg)
                print("Use --help for usage information")
            return 1
        else:
            if pdf_file is None:
                pdf_file = arg
            else:
                error_msg = "Multiple PDF files specified. Only one file is supported."
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
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
            if is_run_environment(command_identifier):
                write_to_json_output(success_data, command_identifier)
            else:
                print(f"{message}")
            return 0
        else:
            error_data = {
                "success": False,
                "error": message,
                "action": "clean_data"
            }
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"{message}")
            return 1
    
    # 处理完整流程模式
    if full_pipeline:
        print(f" Starting full pipeline processing: {pdf_file}")
        
        # 构造第一步命令：PDF提取
        step1_cmd = [sys.executable, __file__, pdf_file]
        if page_spec:
            step1_cmd.extend(["--page", page_spec])
        if output_dir:
            step1_cmd.extend(["--output", output_dir])
        if engine_mode != "mineru":
            step1_cmd.extend(["--engine", engine_mode])
        if clean_data:
            step1_cmd.append("--clean-data")
        
        print("Step 1: PDF extraction...")
        print(f"   Executing command: {' '.join(step1_cmd)}")
        
        try:
            result1 = subprocess.run(step1_cmd, capture_output=True, text=True, check=False)
            
            if result1.returncode != 0:
                error_data = {
                    "success": False,
                    "error": f"PDF extraction failed: {result1.stderr}",
                    "step": "extraction",
                    "command": " ".join(step1_cmd)
                }
                if is_run_environment(command_identifier):
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(f"PDF extraction failed: {result1.stderr}")
                return 1
            
            print(f" PDF extraction completed")
            
            # 根据PDF文件路径推断markdown文件路径
            pdf_path = Path(pdf_file).expanduser().resolve()
            
            # 构建正确的markdown文件名，考虑页码规格
            if page_spec:
                page_suffix = f"_p{page_spec}"
                md_filename = f"{pdf_path.stem}{page_suffix}.md"
            else:
                md_filename = f"{pdf_path.stem}.md"
            
            if output_dir:
                md_file = Path(output_dir) / md_filename
            else:
                md_file = pdf_path.parent / md_filename
            
            if md_file.exists():
                # 构造第二步命令：后处理
                step2_cmd = [sys.executable, __file__, "--post", str(md_file)]
                # 传递原始PDF文件目录，以便后处理器能找到状态文件
                step2_cmd.extend(["--original-pdf-dir", str(pdf_path.parent)])
                if post_type != "all":
                    step2_cmd.extend(["--post-type", post_type])
                if post_ids:
                    step2_cmd.extend(["--ids", post_ids])
                if post_prompt:
                    step2_cmd.extend(["--prompt", post_prompt])
                if post_force:
                    step2_cmd.append("--force")
                
                print("Step 2: Post-processing...")
                print(f"   Executing command: {' '.join(step2_cmd)}")
                
                result2 = subprocess.run(step2_cmd, capture_output=True, text=True, check=False)
                
                if result2.returncode == 0:
                    success_data = {
                        "success": True,
                        "message": f"Full pipeline completed: {pdf_file} -> {md_file}",
                        "extraction_output": result1.stdout,
                        "post_processing": "completed",
                        "post_processing_output": result2.stdout,
                        "post_type": post_type,
                        "step1_command": " ".join(step1_cmd),
                        "step2_command": " ".join(step2_cmd)
                    }
                    if is_run_environment(command_identifier):
                        write_to_json_output(success_data, command_identifier)
                    else:
                        print(f"Full pipeline completed: {pdf_file} -> {md_file}")
                    return 0
                else:
                    # 即使后处理失败，PDF提取已成功
                    warning_data = {
                        "success": True,
                        "message": f"PDF extraction completed but post-processing failed: {md_file}",
                        "extraction_output": result1.stdout,
                        "post_processing": "failed",
                        "post_processing_error": result2.stderr,
                        "post_type": post_type,
                        "step1_command": " ".join(step1_cmd),
                        "step2_command": " ".join(step2_cmd)
                    }
                    if is_run_environment(command_identifier):
                        write_to_json_output(warning_data, command_identifier)
                    else:
                        print(f"PDF extraction completed, but post-processing failed: {md_file}")
                        print("You can later use EXTRACT_PDF --post to manually perform post-processing")
                        print(f"Post-processing error: {result2.stderr}")
                    return 0
            else:
                # markdown文件不存在
                warning_data = {
                    "success": True,
                    "message": f"PDF extraction completed but markdown file not found: {md_file}",
                    "extraction_output": result1.stdout,
                    "post_processing": "skipped",
                    "step1_command": " ".join(step1_cmd)
                }
                if is_run_environment(command_identifier):
                    write_to_json_output(warning_data, command_identifier)
                else:
                    print(f"PDF extraction completed, but markdown file not found: {md_file}")
                return 0
                
        except Exception as e:
            error_data = {
                "success": False,
                "error": f"Full pipeline execution failed: {str(e)}",
                "step": "command_execution"
            }
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"Full pipeline execution failed: {str(e)}")
            return 1
    
    # 处理后处理模式
    if post_file:
        processor = PDFPostProcessor(debug=False)
        success = processor.process_file(post_file, post_type, post_ids, post_prompt, force=post_force, timeout_multi=post_timeout_multi)
        
        if success:
            success_data = {
                "success": True,
                "message": f"Post-processing completed: {post_file}",
                "post_type": post_type
            }
            if is_run_environment(command_identifier):
                write_to_json_output(success_data, command_identifier)
            else:
                print(f"Post-processing completed: {post_file}")
            return 0
        else:
            error_data = {
                "success": False,
                "error": f"Post-processing failed: {post_file}",
                "post_type": post_type
            }
            if is_run_environment(command_identifier):
                write_to_json_output(error_data, command_identifier)
            else:
                print(f"Post-processing failed: {post_file}")
            return 1
    
    # 检查是否提供了PDF文件
    if pdf_file is None:
        error_msg = "Error: No PDF file specified"
        if is_run_environment(command_identifier):
            error_data = {"success": False, "error": error_msg}
            write_to_json_output(error_data, command_identifier)
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
        if is_run_environment(command_identifier):
            write_to_json_output(success_data, command_identifier)
        else:
            print(f"{message}")
        return 0
    else:
        error_data = {
            "success": False,
            "error": message,
            "engine_mode": engine_mode
        }
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"{message}")
        return 1

def cleanup_images_folder():
    """Clean up images folder created by MinerU module imports in current working directory"""
    # Only clean up in the script directory (~/.local/bin), not in PDF directories
    script_dir = Path(__file__).parent
    images_path = script_dir / "images"
    
    if images_path.exists() and images_path.is_dir():
        try:
            # Only remove if it's empty or contains only MinerU-generated files
            contents = list(images_path.iterdir())
            if not contents:  # Empty folder
                images_path.rmdir()
            else:
                # Check if all contents are image files (likely from MinerU)
                image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
                all_images = all(
                    item.is_file() and item.suffix.lower() in image_extensions 
                    for item in contents
                )
                if all_images and len(contents) < 10:  # Safety check: only clean small image folders
                    shutil.rmtree(images_path)
                    print(f"🧹 Cleaned images folder containing {len(contents)} image files")
        except Exception as e:
            # Silently ignore cleanup errors
            pass

if __name__ == "__main__":
    try:
        exit_code = main()
        cleanup_images_folder()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        cleanup_images_folder()
        print("\nCancelled")
        sys.exit(1)
    except Exception as e:
        cleanup_images_folder()
        print(f"Program exception: {e}")
        sys.exit(1) 