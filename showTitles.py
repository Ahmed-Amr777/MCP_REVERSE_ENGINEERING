import pdfplumber
import re
import json
from pathlib import Path
from difflib import SequenceMatcher

# Default settings
PDF_PATH = "C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
SEARCH_TITLE = "OTG_FS core interrupt register (OTG_FS_GINTSTS)"  # Title to search for
FUZZY_SEARCH = True  # Default is on
START_PAGE_HINT = 730  # Optional: hint for starting page (1-indexed)
MAX_PAGES_TO_SEARCH = 100  # Maximum pages to search

def normalize(text: str) -> str:
    """Normalize text for comparison"""
    return re.sub(r'\s+', ' ', text.strip()).lower()

def find_all_titles(pdf_path: str, start_page: int = 1, max_pages: int = None, fuzzy_search: bool = True) -> list:
    """
    Find all section/register titles in the PDF using pdfplumber text extraction.
    Returns list of dicts with page number and title text.
    """
    titles = []
    seen_titles = set()  # To avoid duplicates
    
    with pdfplumber.open(pdf_path) as pdf:
        search_end = len(pdf.pages) if max_pages is None else min(start_page + max_pages, len(pdf.pages))
        
        for page_num in range(start_page - 1, search_end):
            page = pdf.pages[page_num]
            text = page.extract_text() or ""
            
            if not text:
                continue
            
            lines = text.split('\n')
            
            for line in lines:
                line_clean = line.strip()
                if len(line_clean) < 5:
                    continue
                
                # Pattern 1: Section number + title (e.g., "5.4.4 Backup control/status register")
                section_pattern = r'^\s*(\d+\.\d+(?:\.\d+)?)\s+(.+?)(?:$|\n)'
                section_match = re.match(section_pattern, line_clean)
                
                if section_match:
                    section_num = section_match.group(1)
                    section_title = section_match.group(2).strip()
                    full_title = f"{section_num} {section_title}"
                    
                    if full_title not in seen_titles:
                        seen_titles.add(full_title)
                        titles.append({
                            "page": page_num + 1,
                            "title": full_title,
                            "type": "section"
                        })
                
                # Pattern 2: Register title (e.g., "OTG_FS core interrupt register (OTG_FS_GINTSTS)")
                # More flexible pattern to catch register names
                register_pattern = r'([A-Z][A-Z0-9_/]+(?:\s+[A-Z][a-z]+)*\s+register\s*\([A-Z0-9_]+\))'
                register_match = re.search(register_pattern, line_clean, re.IGNORECASE)
                
                if register_match:
                    register_title = register_match.group(1).strip()
                    if register_title not in seen_titles:
                        seen_titles.add(register_title)
                        titles.append({
                            "page": page_num + 1,
                            "title": register_title,
                            "type": "register"
                        })
                
                # Pattern 3: Any line that looks like a register name in parentheses
                # This catches cases where the format is slightly different
                if '(' in line_clean and ')' in line_clean:
                    paren_match = re.search(r'\(([A-Z0-9_]+)\)', line_clean)
                    if paren_match:
                        # Check if this looks like a register name (contains uppercase and underscores)
                        reg_name = paren_match.group(1)
                        if '_' in reg_name and len(reg_name) > 5:
                            # Look backwards for register description
                            before_paren = line_clean[:paren_match.start()].strip()
                            if 'register' in before_paren.lower() or len(before_paren) > 10:
                                full_reg_title = f"{before_paren} ({reg_name})"
                                if full_reg_title not in seen_titles and len(full_reg_title) > 15:
                                    seen_titles.add(full_reg_title)
                                    titles.append({
                                        "page": page_num + 1,
                                        "title": full_reg_title,
                                        "type": "register"
                                    })
    
    return titles

def find_title_with_context(pdf_path: str, search_title: str, start_page_hint: int = 1, 
                           max_pages: int = 100, fuzzy_search: bool = True) -> dict:
    """
    Search for a title in the PDF and return it with context (previous and next titles).
    
    Returns:
        {
            "exists": bool,
            "found_title": dict or None,
            "title_before": dict or None,
            "title_after": dict or None,
            "confidence": float (0-1)
        }
    """
    result = {
        "exists": False,
        "found_title": None,
        "title_before": None,
        "title_after": None,
        "confidence": 0.0,
        "error": None
    }
    
    try:
        # First, find all titles in the PDF
        print(f"[Searching] Looking for titles in PDF...")
        all_titles = find_all_titles(pdf_path, start_page_hint, max_pages, fuzzy_search)
        
        if not all_titles:
            result["error"] = "No titles found in the specified page range"
            return result
        
        # Search for the target title
        search_title_norm = normalize(search_title)
        best_match = None
        best_score = 0.5 if fuzzy_search else 1.0  # Threshold
        
        for title_info in all_titles:
            title_text = title_info["title"]
            title_norm = normalize(title_text)
            
            if fuzzy_search:
                # Fuzzy matching
                similarity = SequenceMatcher(None, search_title_norm, title_norm).ratio()
                
                # Check word overlap
                search_words = set(re.findall(r'\b\w+\b', search_title_norm))
                title_words = set(re.findall(r'\b\w+\b', title_norm))
                if search_words:
                    overlap = len(search_words & title_words) / len(search_words)
                    combined_score = (similarity * 0.7 + overlap * 0.3)
                else:
                    combined_score = similarity
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_match = title_info
            else:
                # Exact matching
                if search_title_norm == title_norm or search_title in title_text:
                    best_match = title_info
                    best_score = 1.0
                    break
        
        if best_match:
            result["exists"] = True
            result["found_title"] = {
                "title": best_match["title"],
                "page": best_match["page"],
                "type": best_match["type"]
            }
            result["confidence"] = best_score
            
            # Find title before
            match_index = all_titles.index(best_match)
            if match_index > 0:
                prev_title = all_titles[match_index - 1]
                result["title_before"] = {
                    "title": prev_title["title"],
                    "page": prev_title["page"],
                    "type": prev_title["type"]
                }
            
            # Find title after
            if match_index < len(all_titles) - 1:
                next_title = all_titles[match_index + 1]
                result["title_after"] = {
                    "title": next_title["title"],
                    "page": next_title["page"],
                    "type": next_title["type"]
                }
        else:
            result["error"] = f"Title '{search_title}' not found (fuzzy search: {fuzzy_search})"
    
    except Exception as e:
        result["error"] = f"Error searching PDF: {str(e)}"
    
    return result

# Main execution
print("="*60)
print("FINDING ALL TITLES IN PDF")
print("="*60)
print(f"\nPDF Path: {PDF_PATH}")
print(f"Start Page: {START_PAGE_HINT}")
print(f"Max Pages to Search: {MAX_PAGES_TO_SEARCH}\n")

# Find all titles
print("[Searching] Looking for all titles in PDF...")
all_titles = find_all_titles(PDF_PATH, START_PAGE_HINT, MAX_PAGES_TO_SEARCH, FUZZY_SEARCH)

# Print results
print("="*60)
print("ALL TITLES FOUND")
print("="*60)

if not all_titles:
    print("\n[No Titles Found] No titles were found in the specified page range")
else:
    print(f"\n[Total Titles Found] {len(all_titles)}\n")
    
    # Group by type
    sections = [t for t in all_titles if t['type'] == 'section']
    registers = [t for t in all_titles if t['type'] == 'register']
    
    print(f"Sections: {len(sections)}")
    print(f"Registers: {len(registers)}\n")
    
    # Print all titles
    print("-" * 60)
    for i, title_info in enumerate(all_titles, 1):
        print(f"{i}. [{title_info['type'].upper()}] Page {title_info['page']}")
        print(f"   {title_info['title']}")
        print()
    
    # Save results to JSON
    output_dir = Path("extracted")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "all_titles.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_titles, f, indent=2, ensure_ascii=False)
    
    print(f"[Saved] All titles JSON: {output_file}")

print("\n" + "="*60)

