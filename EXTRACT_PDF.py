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
import time
import io
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


def save_to_unified_data_directory(content: str, pdf_path: Path, page_spec: str = None, images_data: list = None) -> Tuple[str, str]:
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
    
    # 创建PDF同层目录的文件
    pdf_stem = pdf_path.stem
    if page_spec:
        pdf_stem_with_pages = f"{pdf_stem}_p{page_spec}"
    else:
        pdf_stem_with_pages = pdf_stem
    
    same_name_md_file = pdf_path.parent / f"{pdf_stem_with_pages}.md"
    
    # 更新图片路径到绝对路径 (指向EXTRACT_PDF_DATA)
    updated_content = update_image_paths_to_data_directory(content, str(data_dir))
    
    # 保存到PDF同层目录
    with open(same_name_md_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    # 复制图片到PDF同层目录的images文件夹
    if images_data:
        pdf_images_dir = pdf_path.parent / "images"
        pdf_images_dir.mkdir(exist_ok=True)
        
        for img_data in images_data:
            src_file = images_dir / img_data['filename']
            dst_file = pdf_images_dir / img_data['filename']
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
    
    print(f"📄 后处理状态保存至: {status_file.name}")
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
            
            # 处理每一页
            for page_num in pages:
                page = doc[page_num]
                
                # 提取文本
                text = page.get_text()
                content.append(f"# Page {page_num + 1}\n\n{text}\n\n")
                
                # 提取图片
                image_list = page.get_images()
                for img_index, img in enumerate(image_list):
                    # 获取图片数据
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # 确保是RGB或灰度图像
                        # 转换为字节数据
                        if pix.alpha:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        
                        img_bytes = pix.tobytes("jpeg")
                        
                        # 生成hash文件名
                        img_hash = hashlib.md5(img_bytes).hexdigest()
                        img_filename = f"{img_hash}.jpg"
                        
                        # 获取图片位置信息
                        img_rects = page.get_image_rects(xref)
                        bbox = list(img_rects[0]) if img_rects else []
                        
                        # 保存图片数据
                        images_data.append({
                            'bytes': img_bytes,
                            'hash': img_hash,
                            'filename': img_filename,
                            'bbox': bbox,
                            'page': page_num + 1
                        })
                        
                        # 在markdown中添加图片引用
                        content.append(f"![](images/{img_filename})\n\n")
                    
                    pix = None  # 释放内存
            
            doc.close()
            
            # 合并所有内容
            full_content = '\n'.join(content)
            
            # 使用统一数据存储接口保存数据
            data_md_path, pdf_md_path = save_to_unified_data_directory(
                full_content, pdf_path, page_spec, images_data
            )
            
            # 创建postprocess状态文件
            if images_data:
                create_postprocess_status_file(pdf_path, page_spec, images_data)
            
            # 计算处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"⏱️  总处理时间: {processing_time:.2f} 秒")
            print(f"📄 数据已保存到: {data_md_path}")
            if images_data:
                print(f"🖼️  提取了 {len(images_data)} 张图片")
            
            return True, f"Basic extraction completed: {pdf_md_path}"
            
        except Exception as e:
            return False, f"Basic extraction failed: {str(e)}"
    
    def extract_pdf_mineru(self, pdf_path: Path, page_spec: str = None, output_dir: Path = None, 
                          enable_analysis: bool = False) -> Tuple[bool, str]:
        """使用MinerU进行PDF提取"""
        import time
        
        start_time = time.time()
        
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
            
            # Print stderr for debugging
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            # 计算处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            if result.returncode == 0:
                # 检查是否有输出文件被创建，并复制到用户指定的目录
                output_file = self._handle_mineru_output(pdf_path, output_dir, result.stdout, page_spec)
                print(f"⏱️  总处理时间: {processing_time:.2f} 秒")
                return True, f"MinerU extraction completed: {output_file}"
            else:
                print(f"⏱️  总处理时间: {processing_time:.2f} 秒")
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
            return self.extract_pdf_basic_with_images(pdf_path, page_spec, output_dir_path)
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
                full_content, pdf_path, page_spec, images_data
            )
            
            # 创建postprocess状态文件
            if images_data:
                create_postprocess_status_file(pdf_path, page_spec, images_data)
            
            # 计算处理时间
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"⏱️  总处理时间: {processing_time:.2f} 秒")
            print(f"📄 数据已保存到: {data_md_path}")
            if images_data:
                print(f"🖼️  提取并合并了 {len(images_data)} 张图片")
            
            return True, f"Basic extraction with images completed: {pdf_md_path}"
            
        except Exception as e:
            return False, f"Basic extraction with images failed: {str(e)}"
    
    def _merge_nearby_images_to_data(self, doc, page, image_list, page_num):
        """合并临近的图片成一张大图，返回图片数据"""
        from PIL import Image
        import hashlib
        import fitz
        import io
        
        images_data = []
        
        if not image_list:
            return images_data
        
        try:
            # 提取所有图片的位置和数据
            image_data = []
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
                    
                    # 获取图片在页面中的位置（简化处理，使用图片索引作为位置）
                    y_position = img_index * 100  # 简化的位置计算
                    
                    image_data.append({
                        'index': img_index,
                        'pix': pix,
                        'y_pos': y_position,
                        'page': page_num
                    })
                    
                except Exception as e:
                    print(f"⚠️  处理图片 {img_index} 时出错: {e}")
                    continue
            
            if not image_data:
                return images_data
            
            # 按Y位置排序
            image_data.sort(key=lambda x: x['y_pos'])
            
            # 合并临近的图片（简化版：将所有图片垂直合并成一张大图）
            if len(image_data) > 1:
                # 计算合并后图片的总高度和最大宽度
                total_height = 0
                max_width = 0
                pil_images = []
                
                for img_info in image_data:
                    pix = img_info['pix']
                    # 转换为PIL Image
                    img_data = pix.tobytes("png")
                    pil_img = Image.open(io.BytesIO(img_data))
                    pil_images.append(pil_img)
                    
                    total_height += pil_img.height
                    max_width = max(max_width, pil_img.width)
                
                # 创建合并后的大图
                merged_img = Image.new('RGB', (max_width, total_height), 'white')
                
                y_offset = 0
                for pil_img in pil_images:
                    # 居中放置每张图片
                    x_offset = (max_width - pil_img.width) // 2
                    merged_img.paste(pil_img, (x_offset, y_offset))
                    y_offset += pil_img.height
                
                # 生成合并图片的字节数据和哈希文件名
                img_bytes_io = io.BytesIO()
                merged_img.save(img_bytes_io, format='PNG')
                img_bytes = img_bytes_io.getvalue()
                img_hash = hashlib.md5(img_bytes).hexdigest()  # 使用md5保持一致性
                merged_filename = f"{img_hash}.png"
                
                # 添加到图片数据列表
                images_data.append({
                    'bytes': img_bytes,
                    'hash': img_hash,
                    'filename': merged_filename,
                    'bbox': [],  # 合并图片没有单一的bbox
                    'page': page_num
                })
                
                print(f"🖼️  合并了 {len(image_data)} 张图片成一张大图: {merged_filename}")
                
                # 清理临时资源
                for img_info in image_data:
                    if img_info['pix']:
                        img_info['pix'] = None
                        
            elif len(image_data) == 1:
                # 只有一张图片，直接处理
                pix = image_data[0]['pix']
                img_data = pix.tobytes("jpeg")
                img_hash = hashlib.md5(img_data).hexdigest()
                img_filename = f"{img_hash}.jpg"
                
                # 获取图片位置信息
                try:
                    xref = image_list[0][0]
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
            print(f"⚠️  图片合并过程出错: {e}")
            # 如果合并失败，回退到单独处理每张图片
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:
                        if pix.n - pix.alpha == 1:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        
                        img_data = pix.tobytes("jpeg")
                        img_hash = hashlib.md5(img_data).hexdigest()
                        img_filename = f"{img_hash}.jpg"
                        
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
                    print(f"⚠️  保存单张图片 {img_index} 失败: {e}")
        
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

    def process_file_unified_moved_to_postprocessor(self, file_path: str, process_type: str, specific_ids: str = None, custom_prompt: str = None, force: bool = False) -> bool:
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
            print(f"❌ 不支持的文件类型: {file_path.suffix}")
            return False
            
        if not md_file.exists():
            print(f"❌ Markdown文件不存在: {md_file}")
            return False
            
        print(f"🔄 开始统一后处理 {md_file.name}...")
        
        try:
            # 第一步：确保有postprocess状态文件
            status_file = self._ensure_postprocess_status_file(pdf_file_path, md_file)
            if not status_file:
                print("❌ 无法创建或找到状态文件")
                return False
            
            # 第二步：读取状态文件
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # 第三步：同步markdown和JSON中的placeholder信息
            print("🔄 同步markdown和JSON中的placeholder信息...")
            status_data = self._sync_placeholders_with_markdown(md_file, status_data, status_file)
            
            # 第四步：筛选要处理的项目
            items_to_process = self._filter_items_to_process(status_data, process_type, specific_ids, force)
            
            if not items_to_process:
                print("ℹ️  没有需要处理的项目")
                return True
            
            # 第五步：使用统一的混合处理方式
            success = self._process_items_unified(str(pdf_file_path), str(md_file), status_data, 
                                                items_to_process, process_type, custom_prompt, force)
            
            return success
            
        except Exception as e:
            print(f"❌ 统一后处理异常: {e}")
            return False
    
    def _ensure_postprocess_status_file(self, pdf_file_path: Path, md_file: Path) -> Optional[Path]:
        """确保存在postprocess状态文件，如果不存在则创建"""
        status_file = pdf_file_path.parent / f"{pdf_file_path.stem}_postprocess.json"
        
        if status_file.exists():
            return status_file
        
        print("📄 状态文件不存在，从markdown重新生成...")
        
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
                print("ℹ️  未找到placeholder，无需后处理")
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
            
            print(f"✅ 创建状态文件: {status_file.name}")
            return status_file
            
        except Exception as e:
            print(f"❌ 创建状态文件失败: {e}")
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
                             items_to_process: list, process_type: str, custom_prompt: str = None, force: bool = False) -> bool:
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
                    print(f"⚠️  未找到项目: {item_id}")
                    continue
                
                item_type = item.get('type')
                image_path = item.get('image_path', '')
                
                if not image_path:
                    print(f"⚠️  图片路径为空: {item_id}")
                    continue
                
                # 查找实际的图片文件路径
                actual_image_path = self._find_actual_image_path(pdf_file, image_path)
                if not actual_image_path:
                    print(f"⚠️  图片文件不存在: {image_path}")
                    continue
                
                print(f"🔄 处理 {item_type} 项目: {item_id}")
                
                # 根据类型选择处理方式
                result_text = ""
                if item_type == 'image':
                    result_text = self._process_image_with_api(actual_image_path, custom_prompt)
                elif item_type in ['formula', 'interline_equation']:
                    result_text = self._process_with_unimernet(actual_image_path, "formula", force)
                elif item_type == 'table':
                    result_text = self._process_with_unimernet(actual_image_path, "table", force)
                
                if result_text:
                    # 更新markdown内容
                    success = self._update_markdown_with_result(md_content, item, result_text)
                    if success:
                        md_content = success
                        item['processed'] = True
                        updated = True
                        print(f"✅ 完成 {item_type} 处理: {item_id}")
                    else:
                        print(f"⚠️  更新markdown失败: {item_id}")
                else:
                    print(f"❌ 处理失败: {item_id}")
            
            if updated:
                # 保存更新的markdown文件
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                # 更新状态文件
                status_file = Path(pdf_file).parent / f"{Path(pdf_file).stem}_postprocess.json"
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)
                
                print(f"📝 已更新文件: {Path(md_file).name}")
                return True
            else:
                print("ℹ️  没有内容需要更新")
                return True
                
        except Exception as e:
            print(f"❌ 统一处理异常: {e}")
            return False
    
    def _update_markdown_with_result(self, md_content: str, item: dict, result_text: str) -> Optional[str]:
        """更新markdown内容，保留placeholder，清除已有分析结果并替换为新结果"""
        import re
        
        item_type = item.get('type')
        image_path = item.get('image_path', '')
        
        # 构建更复杂的模式来匹配整个块（包括可能存在的分析结果）
        # 先尝试匹配已经包含分析结果的完整块
        image_filename = Path(image_path).name
        escaped_filename = re.escape(image_filename)
        escaped_type = re.escape(item_type)
        
        # 模式1: 匹配包含分析结果的完整块
        # [placeholder: type]\n![...](path)\n\n**分析结果:**...\n 直到下一个空行或文件结束
        complete_block_pattern = (
            rf'\[placeholder:\s*{escaped_type}\]\s*\n'
            rf'!\[[^\]]*\]\([^)]*{escaped_filename}\)[^)]*\)\s*\n'
            rf'(?:\n\*\*图片分析:\*\*.*?(?=\n\n|\n#|\Z))?'
            rf'(?:\n\n\*\*图片分析:\*\*.*?(?=\n\n|\n#|\Z))?'
            rf'(?:\n\*\*表格内容:\*\*.*?(?=\n\n|\n#|\Z))?'
            rf'(?:\n\*\*分析结果:\*\*.*?(?=\n\n|\n#|\Z))?'
        )
        
        # 模式2: 简单匹配placeholder和图片（没有分析结果的情况）
        simple_pattern = (
            rf'\[placeholder:\s*{escaped_type}\]\s*\n'
            rf'!\[[^\]]*\]\([^)]*{escaped_filename}\)[^)]*\)'
        )
        
        # 先尝试完整块模式
        if re.search(complete_block_pattern, md_content, re.DOTALL):
            pattern_to_use = complete_block_pattern
            flags = re.DOTALL
        elif re.search(simple_pattern, md_content):
            pattern_to_use = simple_pattern
            flags = 0
        else:
            # 尝试更宽松的匹配（只匹配文件名）
            loose_pattern = rf'\[placeholder:\s*{escaped_type}\]\s*\n!\[[^\]]*\]\([^)]*{escaped_filename}[^)]*\)'
            if re.search(loose_pattern, md_content):
                pattern_to_use = loose_pattern
                flags = 0
            else:
                print(f"⚠️  未找到匹配的placeholder模式")
                # 调试信息：显示markdown中实际存在的placeholder
                debug_pattern = r'\[placeholder:\s*(\w+)\]\s*!\[[^\]]*\]\(([^)]+)\)'
                debug_matches = re.findall(debug_pattern, md_content)
                if debug_matches:
                    print(f"📋 markdown中找到的placeholder: {debug_matches}")
                return None
        
        def replace_with_new_result(match):
            # 获取原始的placeholder和图片引用部分
            matched_text = match.group(0)
            
            # 提取placeholder和图片引用（去掉可能存在的分析结果）
            placeholder_img_pattern = rf'(\[placeholder:\s*{escaped_type}\]\s*\n!\[[^\]]*\]\([^)]*{escaped_filename}[^)]*\))'
            placeholder_img_match = re.search(placeholder_img_pattern, matched_text)
            
            if placeholder_img_match:
                placeholder_and_img = placeholder_img_match.group(1)
            else:
                # 如果提取失败，使用整个匹配的开头部分
                lines = matched_text.split('\n')
                if len(lines) >= 2:
                    placeholder_and_img = f"{lines[0]}\n{lines[1]}"
                else:
                    placeholder_and_img = matched_text
            
            # 构建新的内容
            if item_type == 'image':
                return f"{placeholder_and_img}\n\n**图片分析:** {result_text}\n"
            elif item_type in ['formula', 'interline_equation']:
                return f"{placeholder_and_img}\n\n{result_text}\n"
            elif item_type == 'table':
                return f"{placeholder_and_img}\n\n**表格内容:**\n{result_text}\n"
            else:
                return f"{placeholder_and_img}\n\n**分析结果:**\n{result_text}\n"
        
        # 执行替换
        updated_content = re.sub(pattern_to_use, replace_with_new_result, md_content, flags=flags)
        
        # 检查是否实际进行了替换
        if updated_content != md_content:
            return updated_content
        else:
            print(f"⚠️  没有进行任何替换，使用的模式: {pattern_to_use}")
            return None

class PDFPostProcessor:
    """PDF后处理器，用于处理图片、公式、表格的标签替换"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.script_dir = Path(__file__).parent
        
        # Use UNIMERNET tool for formula/table recognition instead of MinerU
        self.unimernet_tool = self.script_dir / "UNIMERNET"
        
        # Import MinerUWrapper for image processing only
        sys.path.insert(0, str(self.script_dir / "EXTRACT_PDF_PROJ"))
        from mineru_wrapper import MinerUWrapper
        self.mineru_wrapper = MinerUWrapper()
    
    def process_file_unified(self, file_path: str, process_type: str, specific_ids: str = None, custom_prompt: str = None, force: bool = False) -> bool:
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
            print(f"❌ 不支持的文件类型: {file_path.suffix}")
            return False
            
        if not md_file.exists():
            print(f"❌ Markdown文件不存在: {md_file}")
            return False
            
        print(f"🔄 开始统一后处理 {md_file.name}...")
        
        try:
            # 第一步：确保有postprocess状态文件
            status_file = self._ensure_postprocess_status_file(pdf_file_path, md_file)
            if not status_file:
                print("❌ 无法创建或找到状态文件")
                return False
            
            # 第二步：读取状态文件
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # 第三步：同步markdown和JSON中的placeholder信息
            print("🔄 同步markdown和JSON中的placeholder信息...")
            status_data = self._sync_placeholders_with_markdown(md_file, status_data, status_file)
            
            # 第四步：筛选要处理的项目
            items_to_process = self._filter_items_to_process(status_data, process_type, specific_ids, force)
            
            if not items_to_process:
                print("ℹ️  没有需要处理的项目")
                return True
            
            # 第五步：使用统一的混合处理方式
            success = self._process_items_unified(str(pdf_file_path), str(md_file), status_data, 
                                                items_to_process, process_type, custom_prompt, force)
            
            return success
            
        except Exception as e:
            print(f"❌ 统一后处理异常: {e}")
            return False
    
    def _ensure_postprocess_status_file(self, pdf_file_path: Path, md_file: Path) -> Optional[Path]:
        """确保存在postprocess状态文件，如果不存在则创建"""
        status_file = pdf_file_path.parent / f"{pdf_file_path.stem}_postprocess.json"
        
        if status_file.exists():
            return status_file
        
        print("📄 状态文件不存在，从markdown重新生成...")
        
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
                print("ℹ️  未找到placeholder，无需后处理")
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
            
            print(f"✅ 创建状态文件: {status_file.name}")
            return status_file
            
        except Exception as e:
            print(f"❌ 创建状态文件失败: {e}")
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
                             items_to_process: list, process_type: str, custom_prompt: str = None, force: bool = False) -> bool:
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
                    print(f"⚠️  未找到项目: {item_id}")
                    continue
                
                item_type = item.get('type')
                image_path = item.get('image_path', '')
                
                if not image_path:
                    print(f"⚠️  图片路径为空: {item_id}")
                    continue
                
                # 查找实际的图片文件路径
                actual_image_path = self._find_actual_image_path(pdf_file, image_path)
                if not actual_image_path:
                    print(f"⚠️  图片文件不存在: {image_path}")
                    continue
                
                print(f"🔄 处理 {item_type} 项目: {item_id}")
                
                # 根据类型选择处理方式
                result_text = ""
                if item_type == 'image':
                    result_text = self._process_image_with_api(actual_image_path, custom_prompt)
                elif item_type in ['formula', 'interline_equation']:
                    result_text = self._process_with_unimernet(actual_image_path, "formula", force)
                elif item_type == 'table':
                    result_text = self._process_with_unimernet(actual_image_path, "table", force)
                
                if result_text:
                    # 更新markdown内容
                    success = self._update_markdown_with_result(md_content, item, result_text)
                    if success:
                        md_content = success
                        item['processed'] = True
                        updated = True
                        print(f"✅ 完成 {item_type} 处理: {item_id}")
                    else:
                        print(f"⚠️  更新markdown失败: {item_id}")
                else:
                    print(f"❌ 处理失败: {item_id}")
            
            if updated:
                # 保存更新的markdown文件
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                # 更新状态文件
                status_file = Path(pdf_file).parent / f"{Path(pdf_file).stem}_postprocess.json"
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)
                
                print(f"📝 已更新文件: {Path(md_file).name}")
                return True
            else:
                print("ℹ️  没有内容需要更新")
                return True
                
        except Exception as e:
            print(f"❌ 统一处理异常: {e}")
            return False
    
    def _update_markdown_with_result(self, md_content: str, item: dict, result_text: str) -> Optional[str]:
        """更新markdown内容，保留placeholder，清除已有分析结果并替换为新结果"""
        import re
        
        item_type = item.get('type')
        image_path = item.get('image_path', '')
        
        # 构建更复杂的模式来匹配整个块（包括可能存在的分析结果）
        # 先尝试匹配已经包含分析结果的完整块
        image_filename = Path(image_path).name
        escaped_filename = re.escape(image_filename)
        escaped_type = re.escape(item_type)
        
        # 模式1: 匹配包含分析结果的完整块
        # [placeholder: type]\n![...](path)\n\n**分析结果:**...\n 直到下一个空行或文件结束
        complete_block_pattern = (
            rf'\[placeholder:\s*{escaped_type}\]\s*\n'
            rf'!\[[^\]]*\]\([^)]*{escaped_filename}\)[^)]*\)\s*\n'
            rf'(?:\n\*\*图片分析:\*\*.*?(?=\n\n|\n#|\Z))?'
            rf'(?:\n\n\*\*图片分析:\*\*.*?(?=\n\n|\n#|\Z))?'
            rf'(?:\n\*\*表格内容:\*\*.*?(?=\n\n|\n#|\Z))?'
            rf'(?:\n\*\*分析结果:\*\*.*?(?=\n\n|\n#|\Z))?'
        )
        
        # 模式2: 简单匹配placeholder和图片（没有分析结果的情况）
        simple_pattern = (
            rf'\[placeholder:\s*{escaped_type}\]\s*\n'
            rf'!\[[^\]]*\]\([^)]*{escaped_filename}\)[^)]*\)'
        )
        
        # 先尝试完整块模式
        if re.search(complete_block_pattern, md_content, re.DOTALL):
            pattern_to_use = complete_block_pattern
            flags = re.DOTALL
        elif re.search(simple_pattern, md_content):
            pattern_to_use = simple_pattern
            flags = 0
        else:
            # 尝试更宽松的匹配（只匹配文件名）
            loose_pattern = rf'\[placeholder:\s*{escaped_type}\]\s*\n!\[[^\]]*\]\([^)]*{escaped_filename}[^)]*\)'
            if re.search(loose_pattern, md_content):
                pattern_to_use = loose_pattern
                flags = 0
            else:
                print(f"⚠️  未找到匹配的placeholder模式")
                # 调试信息：显示markdown中实际存在的placeholder
                debug_pattern = r'\[placeholder:\s*(\w+)\]\s*!\[[^\]]*\]\(([^)]+)\)'
                debug_matches = re.findall(debug_pattern, md_content)
                if debug_matches:
                    print(f"📋 markdown中找到的placeholder: {debug_matches}")
                return None
        
        def replace_with_new_result(match):
            # 获取原始的placeholder和图片引用部分
            matched_text = match.group(0)
            
            # 提取placeholder和图片引用（去掉可能存在的分析结果）
            placeholder_img_pattern = rf'(\[placeholder:\s*{escaped_type}\]\s*\n!\[[^\]]*\]\([^)]*{escaped_filename}[^)]*\))'
            placeholder_img_match = re.search(placeholder_img_pattern, matched_text)
            
            if placeholder_img_match:
                placeholder_and_img = placeholder_img_match.group(1)
            else:
                # 如果提取失败，使用整个匹配的开头部分
                lines = matched_text.split('\n')
                if len(lines) >= 2:
                    placeholder_and_img = f"{lines[0]}\n{lines[1]}"
                else:
                    placeholder_and_img = matched_text
            
            # 构建新的内容
            if item_type == 'image':
                return f"{placeholder_and_img}\n\n**图片分析:** {result_text}\n"
            elif item_type in ['formula', 'interline_equation']:
                return f"{placeholder_and_img}\n\n{result_text}\n"
            elif item_type == 'table':
                return f"{placeholder_and_img}\n\n**表格内容:**\n{result_text}\n"
            else:
                return f"{placeholder_and_img}\n\n**分析结果:**\n{result_text}\n"
        
        # 执行替换
        updated_content = re.sub(pattern_to_use, replace_with_new_result, md_content, flags=flags)
        
        # 检查是否实际进行了替换
        if updated_content != md_content:
            return updated_content
        else:
            print(f"⚠️  没有进行任何替换，使用的模式: {pattern_to_use}")
            return None
    
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
    
    def _process_image_with_api(self, image_path: str, custom_prompt: str = None) -> str:
        """使用IMG2TEXT API处理图片"""
        try:
            # 调用IMG2TEXT工具
            img2text_path = self.script_dir / "IMG2TEXT"
            if not img2text_path.exists():
                return "IMG2TEXT工具不可用"
            
            cmd = [str(img2text_path), image_path, "--json"]
            if custom_prompt:
                cmd.extend(["--prompt", custom_prompt])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                try:
                    # 尝试解析JSON输出
                    output_data = json.loads(result.stdout)
                    if output_data.get('success'):
                        description = output_data.get('result', '图片分析完成')
                        return description
                    else:
                        error_msg = output_data.get('error', 'Unknown error')
                        return f"图片分析失败: {error_msg}"
                except json.JSONDecodeError:
                    # 如果不是JSON格式，直接使用输出
                    return result.stdout.strip() if result.stdout.strip() else "图片分析完成"
            else:
                return f"IMG2TEXT执行失败: {result.stderr}"
                
        except Exception as e:
            return f"图片处理异常: {e}"
    
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
            print(f"❌ 同步placeholder信息失败: {e}")
            return status_data
    
    def _process_with_unimernet(self, image_path: str, content_type: str = "auto", force: bool = False) -> str:
        """使用UNIMERNET工具处理公式或表格图片"""
        try:
            # 使用EXTRACT_IMG工具（整合了UNIMERNET和cache）
            extract_img_tool = self.script_dir / "EXTRACT_IMG"
            if not extract_img_tool.exists():
                print(f"⚠️  EXTRACT_IMG工具不可用: {extract_img_tool}")
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                # 解析EXTRACT_IMG的JSON输出
                try:
                    extract_result = json.loads(result.stdout)
                    if extract_result.get('success'):
                        recognition_result = extract_result.get('result', '')
                        if recognition_result:
                            # Check if it's from cache
                            cache_info = " (来自缓存)" if extract_result.get('from_cache') else ""
                            # Get processing time if available
                            processing_time = extract_result.get('processing_time', 0)
                            time_info = f" (耗时: {processing_time:.2f}秒)" if processing_time > 0 else ""
                            print(f"✅ EXTRACT_IMG识别成功{cache_info}{time_info}: {len(recognition_result)} 字符")
                            # Directly format as $$ without description wrapper
                            cleaned_result = recognition_result.strip()
                            return f"$$\n{cleaned_result}\n$$"
                        else:
                            print("⚠️  EXTRACT_IMG返回空结果")
                            return f"**公式识别失败:**\n\n```\n错误信息: EXTRACT_IMG返回空结果\n```"
                    else:
                        error_msg = extract_result.get('error', 'Unknown error')
                        print(f"❌ EXTRACT_IMG处理失败: {error_msg}")
                        return f"**公式识别失败:**\n\n```\n错误信息: {error_msg}\n```"
                except json.JSONDecodeError as e:
                    error_msg = f"JSON解析失败: {e}\n原始输出: {result.stdout[:200]}..."
                    print(f"❌ 无法解析EXTRACT_IMG JSON输出: {e}")
                    print(f"   原始输出: {result.stdout[:200]}...")
                    return f"**公式识别失败:**\n\n```\n错误信息: {error_msg}\n```"
            else:
                error_msg = f"EXTRACT_IMG执行失败: {result.stderr}"
                print(f"❌ EXTRACT_IMG执行失败: {result.stderr}")
                return f"**公式识别失败:**\n\n```\n错误信息: {error_msg}\n```"
                
        except Exception as e:
            print(f"❌ UNIMERNET处理异常: {e}")
            return f"**公式识别失败:**\n\n```\n错误信息: UNIMERNET处理异常: {e}\n```"
    
    def _process_items_hybrid(self, pdf_file: str, md_file: str, status_data: dict, 
                             items_to_process: list, process_type: str, custom_prompt: str = None, force: bool = False) -> bool:
        """使用混合方式处理项目：图像用传统API，公式表格用UNIMERNET"""
        try:
            # 读取markdown文件
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 处理每个项目
            updated = False
            for item_id in items_to_process:
                # 在status_data中找到对应的项目
                item = None
                for status_item in status_data.get('items', []):
                    status_item_id = status_item.get('id')
                    if not status_item_id:
                        # 从image_path生成ID
                        image_path = status_item.get('image_path', '')
                        if image_path:
                            status_item_id = Path(image_path).stem
                    
                    if status_item_id == item_id:
                        item = status_item
                        break
                
                if not item:
                    print(f"⚠️  未找到项目: {item_id}")
                    continue
                
                if item.get('processed', False) and not force:
                    print(f"⏭️  跳过已处理项目: {item_id}")
                    continue
                elif item.get('processed', False) and force:
                    print(f"🔄 强制重新处理项目: {item_id}")
                
                item_type = item.get('type')
                image_path = item.get('image_path', '')
                
                if not image_path:
                    print(f"⚠️  图片路径为空: {item_id}")
                    continue
                
                # 查找实际的图片文件路径
                actual_image_path = self._find_actual_image_path(pdf_file, image_path)
                if not actual_image_path:
                    print(f"⚠️  图片文件不存在: {image_path}")
                    continue
                
                print(f"🔄 处理 {item_type} 项目: {item_id}")
                
                # 根据类型选择处理方式
                result_text = ""
                if item_type == 'image':
                    # 图像使用传统的图像API（通过MinerU wrapper）
                    result_text = self._process_image_with_api(actual_image_path, custom_prompt)
                elif item_type in ['formula', 'interline_equation']:
                    # 公式使用UNIMERNET
                    result_text = self._process_with_unimernet(actual_image_path, "formula", force)
                elif item_type == 'table':
                    # 表格使用UNIMERNET
                    result_text = self._process_with_unimernet(actual_image_path, "table", force)
                
                if result_text:
                    # 更新markdown文件中的占位符 - 使用新的placeholder格式
                    # 查找 [placeholder: type] 和对应的图片行
                    import re
                    
                    # 构建图片路径的正则表达式（支持绝对和相对路径）
                    image_filename = Path(image_path).name
                    # 匹配placeholder和图片，以及可能存在的description或reason
                    # 使用更精确的匹配，考虑到reason块可能包含嵌套的方括号
                    placeholder_pattern = rf'\[placeholder:\s*{item_type}\]\s*\n!\[[^\]]*\]\([^)]*{re.escape(image_filename)}\)(\s*\n\n\[(description|reason):.*?\n\n---+\])?'
                    
                    # Check if result_text contains error information
                    is_error = any(error_keyword in result_text for error_keyword in 
                                  ["失败", "错误信息", "处理异常", "执行失败", "解析失败"])
                    
                    # Use absolute path for images
                    abs_image_path = get_pdf_extractor_data_dir() / "images" / image_filename
                    
                    if is_error:
                        # For errors, keep placeholder and add error info below image
                        replacement = f"[placeholder: {item_type}]\n![]({abs_image_path})\n\n[description: {result_text}]"
                    else:
                        # For successful processing
                        if item_type in ['formula', 'interline_equation', 'table'] and result_text.strip().startswith('$$') and result_text.strip().endswith('$$'):
                            # For formulas and tables already in $$ format, don't add description wrapper
                            replacement = f"[placeholder: {item_type}]\n![]({abs_image_path})\n\n{result_text}"
                        else:
                            # For image content and other types, keep placeholder and add description below image
                            replacement = f"[placeholder: {item_type}]\n![]({abs_image_path})\n\n[description: {result_text}]"
                    
                    if re.search(placeholder_pattern, md_content, re.DOTALL):
                        # Use lambda to avoid regex interpretation of replacement string
                        md_content = re.sub(placeholder_pattern, lambda m: replacement, md_content, flags=re.DOTALL)
                        
                        # Additional cleanup: remove any remaining fragments of old reason/description blocks
                        # This handles cases where the regex didn't capture the complete block
                        cleanup_pattern = rf'----+\]\s*.*?使用.*?密钥时失败.*?\n\n---+\]'
                        md_content = re.sub(cleanup_pattern, '', md_content, flags=re.DOTALL)
                        
                        updated = True
                        
                        # 标记为已处理
                        item['processed'] = True
                        if is_error:
                            print(f"⚠️  处理失败但已记录错误信息: {item_id}")
                        else:
                            print(f"✅ 完成 {item_type} 处理: {item_id}")
                    else:
                        print(f"⚠️  未找到占位符模式: [placeholder: {item_type}] + image {image_filename}")
                        if self.debug:
                            print(f"   调试：搜索模式: {placeholder_pattern}")
                            # 显示markdown内容的前几行以便调试
                            lines = md_content.split('\n')[:20]
                            print("   调试：markdown前20行:")
                            for i, line in enumerate(lines):
                                print(f"   {i+1:2d}: {line}")
                else:
                    print(f"❌ 处理失败: {item_id}")
            
            if updated:
                # 保存更新的markdown文件
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
                # 更新状态文件
                status_file = Path(pdf_file).parent / f"{Path(pdf_file).stem}_postprocess.json"
                with open(status_file, 'w', encoding='utf-8') as f:
                    json.dump(status_data, f, indent=2, ensure_ascii=False)
                
                print(f"📝 已更新文件: {Path(md_file).name}")
                return True
            else:
                print("ℹ️  没有内容需要更新")
                return True
                
        except Exception as e:
            print(f"❌ 混合处理异常: {e}")
            return False
    
    def _process_image_with_api(self, image_path: str, custom_prompt: str = None) -> str:
        """使用EXTRACT_IMG工具处理图像"""
        try:
            print(f"🖼️  使用EXTRACT_IMG处理: {Path(image_path).name}")
            
            # 调用EXTRACT_IMG工具（整合了IMG2TEXT和cache）
            extract_img_tool = self.script_dir / "EXTRACT_IMG"
            if not extract_img_tool.exists():
                print(f"⚠️  EXTRACT_IMG工具不可用: {extract_img_tool}")
                return ""
            
            cmd = [str(extract_img_tool), image_path, "--type", "image", "--mode", "academic", "--json"]
            if custom_prompt:
                cmd.extend(["--prompt", custom_prompt])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                # 解析EXTRACT_IMG的JSON输出
                try:
                    extract_result = json.loads(result.stdout)
                    if extract_result.get('success'):
                        analysis_result = extract_result.get('result', '')
                        if analysis_result:
                            # Check if it's from cache
                            cache_info = " (来自缓存)" if extract_result.get('from_cache') else ""
                            print(f"✅ EXTRACT_IMG分析完成{cache_info}: {len(analysis_result)} 字符")
                            return f"--- 图像分析结果 ---\n\n{analysis_result}\n\n--------------------"
                        else:
                            print("⚠️  EXTRACT_IMG返回空结果")
                            return f"--- 图像分析失败 ---\n\n**错误信息**: EXTRACT_IMG返回空结果\n\n--------------------"
                    else:
                        error_msg = extract_result.get('error', 'Unknown error')
                        print(f"❌ EXTRACT_IMG处理失败: {error_msg}")
                        return f"--- 图像分析失败 ---\n\n**错误信息**: {error_msg}\n\n-------------------"
                except json.JSONDecodeError as e:
                    error_msg = f"JSON解析失败: {e}\n原始输出: {result.stdout[:200]}..."
                    print(f"❌ 无法解析EXTRACT_IMG JSON输出: {e}")
                    print(f"   原始输出: {result.stdout[:200]}...")
                    return f"--- 图像分析失败 ---\n\n**错误信息**: {error_msg}\n\n--------------------"
            else:
                error_msg = f"EXTRACT_IMG执行失败: {result.stderr}"
                print(f"❌ EXTRACT_IMG执行失败: {result.stderr}")
                return f"--- 图像分析失败 ---\n\n**错误信息**: {error_msg}\n\n--------------------"
                
        except Exception as e:
            print(f"❌ IMG2TEXT处理异常: {e}")
            return f"--- 图像分析失败 ---\n\n**错误信息**: IMG2TEXT处理异常: {e}\n\n--------------------"
    
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
        
    def process_file(self, file_path: str, process_type: str, specific_ids: str = None, custom_prompt: str = None, force: bool = False) -> bool:
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
        return self.process_file_unified(file_path, process_type, specific_ids, custom_prompt, force)
    
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
                        # 保留placeholder，在下方添加分析结果
                        old_pattern = f"[placeholder: image]\n![{alt_text}]({image_path})"
                        new_content = f"[placeholder: image]\n![{alt_text}]({image_path})\n\n**图片分析:** {description}\n"
                        
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
            print(f"   📋 从markdown中识别到 {len(md_placeholders)} 个placeholder")
            
            # 创建JSON中现有项目的映射
            json_items = {item['id']: item for item in status_data.get('items', [])}
            print(f"   📄 JSON中现有 {len(json_items)} 个项目")
            
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
                        print(f"   🔄 更新项目 {img_id[:8]}... 类型: {old_type} → {placeholder_type}")
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
                    print(f"   ➕ 新增项目 {img_id[:8]}... 类型: {placeholder_type}")
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
                print(f"   🔧 恢复缺失的placeholder {img_id[:8]}... 类型: {item['type']}")
                # 在markdown中恢复placeholder
                md_content = self._restore_placeholder_in_markdown(md_content, img_id, item['type'])
                md_content_modified = True
                updated_items.append(item)
            
            # 3. 保存修改后的markdown文件
            if md_content_modified:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"   💾 已更新markdown文件")
            
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
            
            print(f"   ✅ 同步完成: {len(updated_items)} 个项目")
            return status_data
            
        except Exception as e:
            print(f"   ⚠️  同步过程中出现错误: {e}")
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
  --force              Force reprocessing even if items are marked as processed
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
                if is_run_environment(command_identifier):
                    write_to_json_output(success_data, command_identifier)
                else:
                    print(f"✅ {message}")
                return 0
            else:
                error_data = {
                    "success": False,
                    "error": message
                }
                if is_run_environment(command_identifier):
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(f"❌ {message}")
                return 1
        else:
            if is_run_environment(command_identifier):
                error_data = {"success": False, "error": "No PDF file specified"}
                write_to_json_output(error_data, command_identifier)
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
    post_force = False
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
                error_msg = "❌ Error: --page requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--output':
            if i + 1 < len(args):
                output_dir = args[i + 1]
                i += 2
            else:
                error_msg = "❌ Error: --output requires a value"
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
                    error_msg = f"❌ Error: Invalid engine mode: {engine_mode}"
                    if is_run_environment(command_identifier):
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, command_identifier)
                    else:
                        print(error_msg)
                    return 1
                i += 2
            else:
                error_msg = "❌ Error: --engine requires a value"
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
                error_msg = "❌ Error: --full requires a PDF file"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
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
                error_msg = "❌ Error: --prompt requires a value"
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
                    error_msg = f"❌ Error: Invalid post-type: {post_type}"
                    if is_run_environment(command_identifier):
                        error_data = {"success": False, "error": error_msg}
                        write_to_json_output(error_data, command_identifier)
                    else:
                        print(error_msg)
                    return 1
                i += 2
            else:
                error_msg = "❌ Error: --post-type requires a value"
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
                error_msg = "❌ Error: --original-pdf-dir requires a value"
                if is_run_environment(command_identifier):
                    error_data = {"success": False, "error": error_msg}
                    write_to_json_output(error_data, command_identifier)
                else:
                    print(error_msg)
                return 1
        elif arg == '--force':
            post_force = True
            i += 1
        elif arg.startswith('-'):
            error_msg = f"❌ Unknown option: {arg}"
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
                error_msg = "❌ Multiple PDF files specified. Only one file is supported."
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
                print(f"✅ {message}")
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
                print(f"❌ {message}")
            return 1
    
    # 处理完整流程模式
    if full_pipeline:
        print(f"🚀 开始完整流程处理: {pdf_file}")
        
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
        
        print("📄 第一步：PDF提取...")
        print(f"   🔧 执行命令: {' '.join(step1_cmd)}")
        
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
                    print(f"❌ PDF提取失败: {result1.stderr}")
                return 1
            
            print(f"✅ PDF提取完成")
            
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
                
                print("🔄 第二步：自动后处理...")
                print(f"   🔧 执行命令: {' '.join(step2_cmd)}")
                
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
                        print(f"✅ 完整流程完成: {pdf_file} -> {md_file}")
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
                        print(f"✅ PDF提取完成，但后处理失败: {md_file}")
                        print("💡 您可以稍后使用 EXTRACT_PDF --post 手动进行后处理")
                        print(f"⚠️  后处理错误: {result2.stderr}")
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
                    print(f"✅ PDF提取完成，但未找到markdown文件: {md_file}")
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
                print(f"❌ 完整流程执行失败: {str(e)}")
            return 1
    
    # 处理后处理模式
    if post_file:
        processor = PDFPostProcessor(debug=False)
        success = processor.process_file(post_file, post_type, post_ids, post_prompt, force=post_force)
        
        if success:
            success_data = {
                "success": True,
                "message": f"Post-processing completed: {post_file}",
                "post_type": post_type
            }
            if is_run_environment(command_identifier):
                write_to_json_output(success_data, command_identifier)
            else:
                print(f"✅ 后处理完成: {post_file}")
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
                print(f"❌ 后处理失败: {post_file}")
            return 1
    
    # 检查是否提供了PDF文件
    if pdf_file is None:
        error_msg = "❌ Error: No PDF file specified"
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
            print(f"✅ {message}")
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
            print(f"❌ {message}")
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
                    print(f"🧹 已清理包含 {len(contents)} 个图片文件的 images 文件夹")
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
        print("\n❌ 已取消")
        sys.exit(1)
    except Exception as e:
        cleanup_images_folder()
        print(f"❌ 程序异常: {e}")
        sys.exit(1) 