import pdfplumber
import re
import json
from pathlib import Path

# Default settings
PDF_PATH = "C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
SHOW_FIRST = 10  # Show first N titles by default
TITLE_RANGE = None  # e.g., (5, 15) to show titles 5-15, None means use SHOW_FIRST

def find_all_titles(pdf_path: str) -> list:
    """
    Find all titles using pdfplumber's outlines (table of contents/bookmarks).
    Returns list of dicts with title text and page number.
    """
    titles = []
    
    with pdfplumber.open(pdf_path) as pdf:
        if pdf.outlines:
            def extract_outline_items(items, level=0):
                """Recursively extract outline items"""
                for item in items:
                    if isinstance(item, list):
                        # Nested outline (sub-items)
                        extract_outline_items(item, level + 1)
                    else:
                        # Outline item
                        title_text = item.get('title', '') if isinstance(item, dict) else str(item)
                        page_num = None
                        
                        # Try to get page number
                        if isinstance(item, dict):
                            if 'page' in item:
                                page_num = item['page']
                            elif 'page_number' in item:
                                page_num = item['page_number']
                        
                        if title_text:
                            titles.append({
                                "title": title_text,
                                "page": page_num,
                                "level": level,
                                "type": "outline"
                            })
            
            extract_outline_items(pdf.outlines)
        else:
            # If no outlines, return empty list
            return []
    
    return titles

def get_pdf_info(pdf_path: str) -> dict:
    """
    Get PDF metadata and information using pdfplumber.
    """
    info = {
        "path": pdf_path,
        "total_pages": 0,
        "metadata": {}
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            info["total_pages"] = len(pdf.pages)
            if pdf.metadata:
                info["metadata"] = {
                    "title": pdf.metadata.get("Title", ""),
                    "author": pdf.metadata.get("Author", ""),
                    "subject": pdf.metadata.get("Subject", ""),
                    "creator": pdf.metadata.get("Creator", ""),
                    "producer": pdf.metadata.get("Producer", ""),
                }
    except Exception as e:
        info["error"] = str(e)
    
    return info

# Main execution
if __name__ == "__main__":
    print("="*60)
    print("FINDING ALL TITLES IN PDF USING PDFPLUMBER OUTLINES")
    print("="*60)
    print(f"\nPDF Path: {PDF_PATH}")
    if TITLE_RANGE:
        print(f"Title Range: {TITLE_RANGE[0]}-{TITLE_RANGE[1]}")
    else:
        print(f"Show First: {SHOW_FIRST} titles")
    print()
    
    # Get PDF info
    print("[Info] Getting PDF information...")
    pdf_info = get_pdf_info(PDF_PATH)
    print(f"Total Pages: {pdf_info['total_pages']}")
    if pdf_info.get('metadata'):
        print(f"Title: {pdf_info['metadata'].get('title', 'N/A')}")
        print(f"Author: {pdf_info['metadata'].get('author', 'N/A')}")
    print()
    
    # Find all titles using pdfplumber outlines
    print("[Searching] Extracting titles from PDF outlines (table of contents)...")
    all_titles = find_all_titles(PDF_PATH)
    
    # Print results
    print("="*60)
    print("ALL TITLES FOUND")
    print("="*60)
    
    if not all_titles:
        print("\n[No Titles Found] No titles were found in the specified page range")
    else:
        print(f"\n[Total Titles Found] {len(all_titles)}\n")
        
        # Count by level
        level_counts = {}
        for title in all_titles:
            level = title.get('level', 0)
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print("Titles by level:")
        for level in sorted(level_counts.keys()):
            print(f"  Level {level}: {level_counts[level]}")
        print()
        
        # Determine range to show
        if TITLE_RANGE:
            start_idx, end_idx = TITLE_RANGE
            titles_to_show = all_titles[start_idx-1:end_idx]
            range_info = f"Showing titles {start_idx}-{end_idx} of {len(all_titles)}"
        else:
            titles_to_show = all_titles[:SHOW_FIRST]
            range_info = f"Showing first {len(titles_to_show)} of {len(all_titles)} titles"
        
        # Print titles in range
        print("-" * 60)
        print(f"[{range_info}]")
        print("-" * 60)
        for i, title_info in enumerate(titles_to_show, start=1 if not TITLE_RANGE else TITLE_RANGE[0]):
            page_info = f"Page {title_info['page']}" if title_info['page'] else "Page N/A"
            level_info = f"Level {title_info.get('level', 0)}"
            indent = "  " * title_info.get('level', 0)  # Indent based on level
            print(f"{i}. [{level_info}] {page_info}")
            print(f"   {indent}{title_info['title']}")
            print()
        
        # Save results to JSON
        output_dir = Path("extracted")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "all_titles.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "pdf_info": pdf_info,
                "titles": all_titles,
                "summary": {
                    "total": len(all_titles),
                    "levels": level_counts
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[Saved] All titles JSON: {output_file}")
    
    print("\n" + "="*60)

