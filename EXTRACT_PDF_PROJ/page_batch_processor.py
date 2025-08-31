#!/usr/bin/env python3
"""
分页批处理器 - 支持PDF分页处理和进度保存
Page Batch Processor - Supports PDF page-by-page processing with progress saving
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import sys

@dataclass
class PageProgress:
    """单页处理进度"""
    page_num: int
    status: str  # 'pending', 'processing', 'completed', 'failed'
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_file: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class BatchProgress:
    """批处理进度"""
    pdf_hash: str
    pdf_path: str
    total_pages: int
    pages: Dict[int, PageProgress]
    created_time: float
    updated_time: float
    output_dir: str
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'pdf_hash': self.pdf_hash,
            'pdf_path': self.pdf_path,
            'total_pages': self.total_pages,
            'pages': {k: asdict(v) for k, v in self.pages.items()},
            'created_time': self.created_time,
            'updated_time': self.updated_time,
            'output_dir': self.output_dir
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建对象"""
        pages = {int(k): PageProgress(**v) for k, v in data['pages'].items()}
        return cls(
            pdf_hash=data['pdf_hash'],
            pdf_path=data['pdf_path'],
            total_pages=data['total_pages'],
            pages=pages,
            created_time=data['created_time'],
            updated_time=data['updated_time'],
            output_dir=data['output_dir']
        )

class PageBatchProcessor:
    """分页批处理器"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """初始化处理器"""
        self.cache_dir = cache_dir or Path(__file__).parent / "batch_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.progress_file = self.cache_dir / "batch_progress.json"
        
    def get_pdf_hash(self, pdf_path: Path) -> str:
        """计算PDF文件哈希值"""
        hash_md5 = hashlib.md5()
        with open(pdf_path, "rb") as f:
            # 读取文件头部和尾部来计算哈希，避免大文件全读取
            chunk_size = 8192
            # 读取开头
            chunk = f.read(chunk_size)
            hash_md5.update(chunk)
            
            # 读取文件大小
            f.seek(0, 2)  # 移到文件末尾
            file_size = f.tell()
            hash_md5.update(str(file_size).encode())
            
            # 如果文件足够大，读取中间和末尾
            if file_size > chunk_size * 2:
                # 读取中间
                f.seek(file_size // 2)
                chunk = f.read(chunk_size)
                hash_md5.update(chunk)
                
                # 读取末尾 - 修复负数seek问题
                tail_size = min(chunk_size, file_size)
                if tail_size > 0:
                    f.seek(file_size - tail_size)
                    chunk = f.read()
                    hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def get_pdf_page_count(self, pdf_path: Path) -> int:
        """获取PDF页数"""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages)
        except ImportError:
            # 如果没有PyPDF2，使用pdfinfo命令
            try:
                result = subprocess.run(['pdfinfo', str(pdf_path)], 
                                      capture_output=True, text=True, check=True)
                for line in result.stdout.split('\n'):
                    if line.startswith('Pages:'):
                        return int(line.split(':')[1].strip())
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # 如果都失败了，返回默认值
            print(f"⚠️ 无法获取PDF页数，假设为50页", file=sys.stderr)
            return 50
    
    def load_progress(self) -> Dict[str, BatchProgress]:
        """加载进度文件"""
        if not self.progress_file.exists():
            return {}
        
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {k: BatchProgress.from_dict(v) for k, v in data.items()}
        except Exception as e:
            print(f"⚠️ 加载进度文件失败: {e}", file=sys.stderr)
            return {}
    
    def save_progress(self, progress_dict: Dict[str, BatchProgress]):
        """保存进度文件"""
        try:
            data = {k: v.to_dict() for k, v in progress_dict.items()}
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存进度文件失败: {e}", file=sys.stderr)
    
    def get_or_create_batch_progress(self, pdf_path: Path, output_dir: Path, 
                                   page_range: Optional[str] = None) -> BatchProgress:
        """获取或创建批处理进度"""
        pdf_hash = self.get_pdf_hash(pdf_path)
        progress_dict = self.load_progress()
        
        if pdf_hash in progress_dict:
            batch_progress = progress_dict[pdf_hash]
            # 更新输出目录（可能有变化）
            batch_progress.output_dir = str(output_dir)
            batch_progress.updated_time = time.time()
            print(f"📂 找到现有进度: {len([p for p in batch_progress.pages.values() if p.status == 'completed'])}/{batch_progress.total_pages} 页已完成")
            return batch_progress
        
        # 创建新的批处理进度
        total_pages = self.get_pdf_page_count(pdf_path)
        
        # 解析页面范围
        if page_range:
            page_numbers = self.parse_page_range(page_range, total_pages)
        else:
            page_numbers = list(range(1, total_pages + 1))
        
        pages = {}
        for page_num in page_numbers:
            pages[page_num] = PageProgress(page_num=page_num, status='pending')
        
        batch_progress = BatchProgress(
            pdf_hash=pdf_hash,
            pdf_path=str(pdf_path),
            total_pages=len(page_numbers),
            pages=pages,
            created_time=time.time(),
            updated_time=time.time(),
            output_dir=str(output_dir)
        )
        
        print(f"📝 创建新的批处理进度: {batch_progress.total_pages} 页待处理")
        return batch_progress
    
    def parse_page_range(self, page_range: str, total_pages: int) -> List[int]:
        """解析页面范围"""
        pages = []
        for part in page_range.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                start = int(start.strip())
                end = int(end.strip())
                pages.extend(range(start, min(end + 1, total_pages + 1)))
            else:
                page_num = int(part.strip())
                if 1 <= page_num <= total_pages:
                    pages.append(page_num)
        return sorted(set(pages))
    
    def get_pending_pages(self, batch_progress: BatchProgress) -> List[int]:
        """获取待处理的页面"""
        return [page_num for page_num, page in batch_progress.pages.items() 
                if page.status in ['pending', 'failed']]
    
    def process_single_page(self, pdf_path: Path, page_num: int, output_dir: Path) -> Tuple[bool, str, Optional[str]]:
        """处理单个页面"""
        try:
            # 创建单页输出目录
            page_output_dir = output_dir / f"page_{page_num:03d}"
            page_output_dir.mkdir(exist_ok=True)
            
            # 首先检查MinerU是否可用
            try:
                result_check = subprocess.run(
                    ["python3", "-m", "mineru.cli.client", "--help"], 
                    capture_output=True, text=True, timeout=10
                )
                if result_check.returncode != 0:
                    raise ImportError("MinerU not available")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                # MinerU不可用，使用传统的PDF处理方式
                return self._process_single_page_fallback(pdf_path, page_num, page_output_dir)
            
            # 构建MinerU命令处理单页
            cmd = [
                "python3", "-m", "mineru.cli.client",
                "-p", str(pdf_path.resolve()),
                "-o", str(page_output_dir),
                "-s", str(page_num),
                "-e", str(page_num),
                "-f", "false",  # 禁用公式解析以提高速度
                "-t", "false",  # 禁用表格解析以提高速度
                "-d", "cpu"     # 使用CPU避免设备问题
            ]
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5分钟超时
            
            if result.returncode == 0:
                # 查找生成的markdown文件
                md_files = list(page_output_dir.glob("*.md"))
                if md_files:
                    return True, f"页面 {page_num} 处理成功", str(md_files[0])
                else:
                    return False, f"页面 {page_num} 处理完成但未找到输出文件", None
            else:
                # MinerU失败，尝试回退方式
                print(f"⚠️ MinerU处理页面{page_num}失败，尝试回退方式", file=sys.stderr)
                return self._process_single_page_fallback(pdf_path, page_num, page_output_dir)
                
        except subprocess.TimeoutExpired:
            return False, f"页面 {page_num} 处理超时", None
        except Exception as e:
            return False, f"页面 {page_num} 处理异常: {str(e)}", None
    
    def _process_single_page_fallback(self, pdf_path: Path, page_num: int, output_dir: Path) -> Tuple[bool, str, Optional[str]]:
        """回退的单页处理方法 - 使用基础PDF提取"""
        try:
            # 使用PyPDF2或其他基础方法提取单页文本
            try:
                import PyPDF2
                
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    if page_num <= len(reader.pages):
                        page = reader.pages[page_num - 1]  # PyPDF2使用0-based索引
                        text = page.extract_text()
                        
                        # 保存为markdown文件
                        output_file = output_dir / f"page_{page_num:03d}.md"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(f"# 第 {page_num} 页\n\n")
                            f.write(text)
                        
                        return True, f"页面 {page_num} 基础提取成功", str(output_file)
                    else:
                        return False, f"页面 {page_num} 超出范围", None
                        
            except ImportError:
                # PyPDF2也不可用，创建占位符
                output_file = output_dir / f"page_{page_num:03d}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# 第 {page_num} 页\n\n")
                    f.write("*此页面需要手动处理 - 批处理器缺少必要的PDF处理库*\n")
                
                return True, f"页面 {page_num} 创建占位符", str(output_file)
                
        except Exception as e:
            return False, f"页面 {page_num} 回退处理失败: {str(e)}", None
    
    def update_page_status(self, batch_progress: BatchProgress, page_num: int, 
                          status: str, output_file: Optional[str] = None, 
                          error_message: Optional[str] = None):
        """更新页面状态"""
        if page_num in batch_progress.pages:
            page = batch_progress.pages[page_num]
            page.status = status
            page.updated_time = time.time()
            
            if status == 'processing':
                page.start_time = time.time()
            elif status in ['completed', 'failed']:
                page.end_time = time.time()
                
            if output_file:
                page.output_file = output_file
            if error_message:
                page.error_message = error_message
            
            batch_progress.updated_time = time.time()
    
    def merge_page_outputs(self, batch_progress: BatchProgress, final_output_path: Path) -> bool:
        """合并所有页面的输出"""
        try:
            completed_pages = [page for page in batch_progress.pages.values() 
                             if page.status == 'completed' and page.output_file]
            
            if not completed_pages:
                return False
            
            # 按页码排序
            completed_pages.sort(key=lambda x: x.page_num)
            
            # 合并markdown内容
            merged_content = []
            merged_content.append(f"# PDF提取结果\n")
            merged_content.append(f"**文件**: {batch_progress.pdf_path}\n")
            merged_content.append(f"**处理时间**: {datetime.fromtimestamp(batch_progress.updated_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
            merged_content.append(f"**页面数**: {len(completed_pages)}/{batch_progress.total_pages}\n\n")
            
            for page in completed_pages:
                merged_content.append(f"## 第 {page.page_num} 页\n\n")
                
                # 读取页面内容
                if page.output_file and Path(page.output_file).exists():
                    with open(page.output_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        merged_content.append(content)
                        merged_content.append("\n\n---\n\n")
                else:
                    merged_content.append("*页面内容缺失*\n\n---\n\n")
            
            # 写入最终文件
            with open(final_output_path, 'w', encoding='utf-8') as f:
                f.write(''.join(merged_content))
            
            return True
            
        except Exception as e:
            print(f"⚠️ 合并输出失败: {e}", file=sys.stderr)
            return False
    
    def process_pdf_batch(self, pdf_path: Path, output_dir: Path, 
                         page_range: Optional[str] = None, 
                         max_concurrent: int = 1) -> Tuple[bool, str]:
        """批量处理PDF"""
        
        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取或创建批处理进度
        batch_progress = self.get_or_create_batch_progress(pdf_path, output_dir, page_range)
        progress_dict = self.load_progress()
        progress_dict[batch_progress.pdf_hash] = batch_progress
        
        # 获取待处理页面
        pending_pages = self.get_pending_pages(batch_progress)
        
        if not pending_pages:
            print("✅ 所有页面已处理完成")
            # 合并输出
            final_output = output_dir / f"{pdf_path.stem}_merged.md"
            if self.merge_page_outputs(batch_progress, final_output):
                return True, f"所有页面已完成，合并输出: {final_output}"
            else:
                return True, "所有页面已完成，但合并输出失败"
        
        print(f"📋 开始处理 {len(pending_pages)} 个待处理页面...")
        
        # 处理每个页面
        for i, page_num in enumerate(pending_pages, 1):
            print(f"\n🔄 处理页面 {page_num} ({i}/{len(pending_pages)})")
            
            # 更新状态为处理中
            self.update_page_status(batch_progress, page_num, 'processing')
            self.save_progress(progress_dict)
            
            # 处理页面
            success, message, output_file = self.process_single_page(pdf_path, page_num, output_dir)
            
            if success:
                print(f"✅ {message}")
                self.update_page_status(batch_progress, page_num, 'completed', output_file)
            else:
                print(f"❌ {message}")
                self.update_page_status(batch_progress, page_num, 'failed', error_message=message)
            
            # 保存进度
            self.save_progress(progress_dict)
            
            # 显示总体进度
            completed_count = len([p for p in batch_progress.pages.values() if p.status == 'completed'])
            total_count = len(batch_progress.pages)
            progress_percent = (completed_count / total_count) * 100
            print(f"📊 总进度: {completed_count}/{total_count} ({progress_percent:.1f}%)")
        
        # 最终合并
        print(f"\n🔗 合并所有页面输出...")
        final_output = output_dir / f"{pdf_path.stem}_merged.md"
        if self.merge_page_outputs(batch_progress, final_output):
            return True, f"批处理完成，输出文件: {final_output}"
        else:
            return False, "页面处理完成，但合并输出失败"
    
    def get_batch_status(self, pdf_path: Path) -> Optional[Dict]:
        """获取批处理状态"""
        pdf_hash = self.get_pdf_hash(pdf_path)
        progress_dict = self.load_progress()
        
        if pdf_hash not in progress_dict:
            return None
        
        batch_progress = progress_dict[pdf_hash]
        
        # 统计状态
        status_counts = {}
        for page in batch_progress.pages.values():
            status_counts[page.status] = status_counts.get(page.status, 0) + 1
        
        return {
            'pdf_path': batch_progress.pdf_path,
            'total_pages': batch_progress.total_pages,
            'status_counts': status_counts,
            'created_time': datetime.fromtimestamp(batch_progress.created_time).strftime('%Y-%m-%d %H:%M:%S'),
            'updated_time': datetime.fromtimestamp(batch_progress.updated_time).strftime('%Y-%m-%d %H:%M:%S'),
            'output_dir': batch_progress.output_dir
        }
    
    def clean_cache(self, older_than_days: int = 7):
        """清理旧的缓存"""
        cutoff_time = time.time() - (older_than_days * 24 * 3600)
        progress_dict = self.load_progress()
        
        cleaned_count = 0
        for pdf_hash, batch_progress in list(progress_dict.items()):
            if batch_progress.updated_time < cutoff_time:
                del progress_dict[pdf_hash]
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.save_progress(progress_dict)
            print(f"🧹 清理了 {cleaned_count} 个旧的批处理记录")

def main():
    """测试函数"""
    processor = PageBatchProcessor()
    
    # 示例用法
    pdf_path = Path("test.pdf")
    output_dir = Path("output")
    
    if pdf_path.exists():
        success, message = processor.process_pdf_batch(pdf_path, output_dir, page_range="1-5")
        print(f"结果: {success}, 消息: {message}")
    else:
        print("测试PDF文件不存在")

if __name__ == "__main__":
    main()
