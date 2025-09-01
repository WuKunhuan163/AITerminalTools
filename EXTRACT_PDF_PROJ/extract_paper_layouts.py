# extract_paper_layouts.py
import fitz
import re
from pathlib import Path
import io
from PIL import Image
import sys
from collections import defaultdict

def rejoin_paragraphs(text_block: str) -> str:
    """
    A robust utility function to rejoin broken paragraphs, preserving internal paragraph breaks.
    """
    if not text_block: return ""
    
    # 1. Fix words broken by hyphenation at line ends.
    # This is a critical first step.
    rejoined_text = re.sub(r"(\w)-\s*\n\s*", r"\1", text_block)
    
    # 2. Split the entire block into paragraphs based on one or more empty lines.
    # This correctly identifies hard breaks between paragraphs.
    potential_paragraphs = re.split(r'\n\s*\n', rejoined_text)
    
    # 3. For each potential paragraph, join the internal lines (soft breaks).
    final_paragraphs = []
    for para in potential_paragraphs:
        if not para.strip(): continue
        # Replace any remaining single newlines (which are now guaranteed to be soft breaks) with a space.
        single_line_para = re.sub(r'\s*\n\s*', ' ', para.strip())
        final_paragraphs.append(single_line_para)
        
    # 4. Join the fully processed paragraphs with a standard double newline.
    return "\n\n".join(final_paragraphs)


def classify_text_block(text: str) -> str:
    """Classifies a text block into a semantic type using heuristics for academic papers."""
    stripped_text = text.strip().lower()
    if not stripped_text: return "Whitespace"
    # More specific patterns first
    if re.match(r'^(fig\. |figure |table )\d+', stripped_text): return "Figure Caption"
    if re.match(r'^(abstract|introduction|related work|method|experiment|conclusion|references|appendix)', stripped_text): return "Section Header"
    if re.search(r'authors’ addresses:', stripped_text): return "Author Addresses"
    if re.search(r'ccs concepts:', stripped_text): return "CCS Concepts"
    if re.search(r'additional key words and phrases:', stripped_text): return "Keywords"
    if re.search(r'acm reference format:', stripped_text): return "Reference Format"
    if re.search(r'acm trans\. graph', stripped_text): return "Publication Info" # New rule
    if re.search(r'^(∗|†|‡)', text.strip()): return "Author Notes"
    # A more specific heuristic for author lists
    if len(re.findall(r'[A-Z][A-Z\s]+', text.strip())) > 3 and 'china' in stripped_text: return "Author Info"
    if re.search(r'arxiv:\d+\.\d+v\d+', stripped_text): return "Metadata"
    return "Main Text"

class ArxivLayoutProcessor:
    """A dedicated processor for the typical single-column arXiv layout."""

    def _merge_text_blocks(self, classified_texts: list) -> list:
        """
        Separates Main Text, merges it into a single logical block, 
        then recombines with other blocks for final output.
        """
        if not classified_texts: 
            return []

        # STAGE 1: SEPARATION (As per your suggestion)
        main_text_blocks = [b for b in classified_texts if b["type"] == "Main Text"]
        other_semantic_blocks = [b for b in classified_texts if b["type"] != "Main Text"]

        # STAGE 2: MERGING Main Text
        if main_text_blocks:
            # Sort by reading order for multi-column layout: x first, then y
            main_text_blocks.sort(key=lambda b: (b["bbox"].x0, b["bbox"].y0))
            
            # Smart concatenation with paragraph detection
            merged_content_parts = []
            for i, block in enumerate(main_text_blocks):
                content = block["content"].strip()
                if not content:
                    continue
                    
                if i == 0:
                    # First block, add as-is
                    merged_content_parts.append(content)
                else:
                    # Check if previous block ends with sentence-ending punctuation
                    prev_content = merged_content_parts[-1] if merged_content_parts else ""
                    if prev_content and re.search(r'[.!?;:]\s*$', prev_content):
                        # Previous block ends with punctuation - start new paragraph
                        merged_content_parts.append(content)
                    else:
                        # Previous block doesn't end with punctuation - continue same paragraph
                        # Check if we need to add a space to avoid word concatenation
                        if prev_content and not prev_content.endswith(' ') and not content.startswith(' '):
                            merged_content_parts[-1] = prev_content + ' ' + content
                        else:
                            merged_content_parts[-1] = prev_content + content
            
            # Join all parts with double newlines (paragraph breaks)
            full_main_text_content = '\n\n'.join(merged_content_parts)
            
            # Create a single, unified Main Text block
            unified_bbox = fitz.Rect()
            for b in main_text_blocks:
                unified_bbox.include_rect(b["bbox"])
            
            unified_main_text_block = {
                "type": "Main Text",
                "content": full_main_text_content, # The processed, concatenated content
                "bbox": unified_bbox
            }
            
            # STAGE 3: RECOMBINATION
            final_blocks = other_semantic_blocks + [unified_main_text_block]
        else:
            final_blocks = other_semantic_blocks
        
        return final_blocks

    def process_page(self, page: fitz.Page, image_temp_dir: Path, debug: bool) -> list:
        main_content_bbox = self._get_main_content_area(page)
        images = [b for b in page.get_image_info(xrefs=True) if fitz.Rect(b["bbox"]).intersects(main_content_bbox)]
        texts = [b for b in page.get_text("blocks") if fitz.Rect(b[:4]).intersects(main_content_bbox)]
        
        figure_groups = self._group_figures(images)
        remaining_texts = self._associate_texts_to_figures(figure_groups, texts)
        
        for group in figure_groups:
            path, bytes_data = self._generate_figure_screenshot(group, page, image_temp_dir)
            if path and bytes_data:
                group["screenshot_path"], group["bytes_data"] = path, bytes_data
        
        classified_texts = []
        is_first_main_block = True
        for text_block in remaining_texts:
            content, block_type = text_block[4], classify_text_block(text_block[4])
            if page.number == 0 and block_type == "Main Text" and is_first_main_block:
                block_type, is_first_main_block = "Title", False
            classified_texts.append({"type": block_type, "content": content, "bbox": fitz.Rect(text_block[:4])})
        
        # Call the new, robust merging function
        merged_texts = self._merge_text_blocks(classified_texts)
        
        # STAGE 4: FINAL FORMATTING & RECOMPOSITION
        for block in merged_texts:
            if "content" in block:
                block["content"] = rejoin_paragraphs(block["content"])

        all_semantic_blocks = merged_texts + figure_groups
        return sorted(all_semantic_blocks, key=lambda b: b.get("bbox").y0)
    
    # ... All other helper methods (_get_main_content_area, _group_figures, etc.) remain unchanged ...
    def _get_main_content_area(self, page: fitz.Page) -> fitz.Rect:
        rect = page.rect
        if page.number == 0:
            left_margin_end = 0
            for block in page.get_text("blocks"):
                bbox = fitz.Rect(block[:4])
                if bbox.x1 < rect.width * 0.25: left_margin_end = max(left_margin_end, bbox.x1)
            if left_margin_end > 0:
                print(f"     - Detected arXiv left sidebar. Adjusting content area.", file=sys.stderr)
                return fitz.Rect(left_margin_end + 10, rect.y0, rect.x1, rect.y1)
        return rect

    def _group_figures(self, images: list) -> list:
        if not images: return []
        images.sort(key=lambda img: (fitz.Rect(img["bbox"]).y0, fitz.Rect(img["bbox"]).x0))
        visited, groups = [False] * len(images), []
        for i in range(len(images)):
            if visited[i]: continue
            current_group = {"type": "Figure", "images": [], "bbox": fitz.Rect(images[i]["bbox"])}
            q, visited[i] = [i], True
            head = 0
            while head < len(q):
                curr_idx = q[head]; head += 1
                current_group["images"].append(images[curr_idx])
                current_group["bbox"].include_rect(images[curr_idx]["bbox"])
                expanded_bbox = fitz.Rect(images[curr_idx]["bbox"]) + (-30, -30, 30, 30)
                for next_idx in range(len(images)):
                    if not visited[next_idx]:
                        next_bbox = fitz.Rect(images[next_idx]["bbox"])
                        if expanded_bbox.intersects(next_bbox):
                            visited[next_idx] = True; q.append(next_idx)
            groups.append(current_group)
        return groups

    def _associate_texts_to_figures(self, figure_groups: list, texts: list) -> list:
        unassociated_texts = []
        for text_block in texts:
            text_bbox = fitz.Rect(text_block[:4])
            closest_group, min_dist = None, float('inf')
            text_center = (text_bbox.tl + text_bbox.br) / 2
            for group in figure_groups:
                group_center = (group["bbox"].tl + group["bbox"].br) / 2
                dist = text_center.distance_to(group_center)
                if dist < min_dist: min_dist, closest_group = dist, group
            if closest_group and min_dist < 150:
                closest_group.setdefault("associated_texts", []).append(text_block)
            else:
                unassociated_texts.append(text_block)
        return unassociated_texts

    def _generate_figure_screenshot(self, figure_group: dict, page: fitz.Page, image_temp_dir: Path) -> tuple[Path, bytes]:
        tight_bbox = fitz.Rect()
        for img in figure_group["images"]: tight_bbox.include_rect(img["bbox"])
        for text_block in figure_group.get("associated_texts", []): tight_bbox.include_rect(text_block[:4])
        if tight_bbox.is_empty: return None, None
        
        # Create a deterministic filename based on bbox coordinates and page number
        import hashlib
        bbox_str = f"page_{page.number}_bbox_{tight_bbox.x0:.2f}_{tight_bbox.y0:.2f}_{tight_bbox.x1:.2f}_{tight_bbox.y1:.2f}"
        bbox_hash = hashlib.md5(bbox_str.encode()).hexdigest()[:8]
        save_path = image_temp_dir / f"figure_screenshot_{bbox_hash}.png"
        
        # Only generate if file doesn't exist
        if not save_path.exists():
            pix = page.get_pixmap(clip=tight_bbox, dpi=200)
            pil_img = Image.frombytes("RGB" if pix.n - pix.alpha == 3 else "RGBA", [pix.width, pix.height], pix.samples)
            pil_img.save(save_path)
        
        # Always read the file to get bytes_data for cache hash
        with open(save_path, 'rb') as f:
            bytes_data = f.read()
        
        return save_path, bytes_data

def get_layout_processor(layout_mode: str):
    if layout_mode == 'arxiv':
        print("ℹ️ Using arXiv layout processor.", file=sys.stderr)
        return ArxivLayoutProcessor()
    else:
        print(f"Warning: Layout '{layout_mode}' not recognized, using default (arXiv).", file=sys.stderr)
        return ArxivLayoutProcessor()