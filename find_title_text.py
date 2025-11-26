import pdfplumber
import re
import argparse
import difflib
from pathlib import Path

def group_chars_into_lines(chars, tolerance=2):
    """Group pdfplumber chars into text lines while keeping font info."""
    lines = []
    current_line = []
    current_y = None

    for char in chars:
        char_y = char.get("top", 0)

        if current_y is None or abs(char_y - current_y) > tolerance:
            if current_line:
                lines.append(current_line)
            current_line = []
            current_y = char_y

        current_line.append(char)

    if current_line:
        lines.append(current_line)

    return lines

def is_title_line(line_chars, page_width):
    """
    Check if a line is a title based on:
    1. Number pattern (e.g., 1.2.3, 1, 2.1, etc.)
    2. Hard-left alignment (x position near 0 or very small)
    3. ALL CAPS text OR font size larger than normal
    """
    if not line_chars:
        return False
    
    # Get line text
    line_text = "".join(c.get("text", "") for c in line_chars).strip()
    
    if not line_text:
        return False
    
    # Check 1: Number pattern at start (like 1.2.3, 5.4.2, etc.)
    # Must have at least one dot to be a proper section number
    has_number_pattern = bool(re.match(r'^\d+\.\d+', line_text))
    
    # Check 2: Hard-left alignment (x position should be small, typically < 50)
    first_char = line_chars[0]
    x_position = first_char.get("x0", 0)
    is_left_aligned = x_position < 50
    
    # Check 3: Font size - titles are usually larger (check average font size)
    avg_font_size = sum(c.get("size", 0) for c in line_chars) / len(line_chars) if line_chars else 0
    is_large_font = avg_font_size > 10  # Titles are typically > 10pt
    
    # Check 4: ALL CAPS (at least 60% of alphabetic characters are uppercase)
    alpha_chars = [c for c in line_text if c.isalpha()]
    if alpha_chars:
        upper_count = sum(1 for c in alpha_chars if c.isupper())
        caps_ratio = upper_count / len(alpha_chars)
        is_all_caps = caps_ratio > 0.6
    else:
        is_all_caps = False
    
    # Title must have: number pattern AND left alignment AND (large font OR all caps)
    return has_number_pattern and is_left_aligned and (is_large_font or is_all_caps)

def normalize_title(text: str) -> str:
    """Normalize titles for fuzzy comparison."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text

def title_matches(target: str, candidate: str, threshold: float) -> float:
    """Return fuzzy similarity score between target and candidate."""
    normalized_target = normalize_title(target)
    normalized_candidate = normalize_title(candidate)
    return difflib.SequenceMatcher(None, normalized_target, normalized_candidate).ratio()

def extract_text_under_title(pdf_path: str, target_title: str, threshold: float = 0.75):
    """
    Find a title matching target_title and extract all text under it until the next title.
    Returns dict with title info and extracted text, or None if not found.
    """
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        target_found = False
        start_page = None
        end_page = None
        found_title = None
        found_section = None
        content_lines = []
        extraction_complete = False
        
        for page_num, page in enumerate(pdf.pages, start=1):
            if extraction_complete:
                break
                
            chars = page.chars
            if not chars:
                continue
            
            # Get page width for alignment check
            page_width = page.width
            
            lines = group_chars_into_lines(chars)
            
            i = 0
            while i < len(lines):
                if extraction_complete:
                    break
                    
                line_chars = lines[i]
                line_text = "".join(c.get("text", "") for c in line_chars).strip()
                
                if not line_text:
                    i += 1
                    continue
                
                # Check if this is a title line
                if is_title_line(line_chars, page_width):
                    if not target_found:
                        # Check if this matches our target title
                        similarity = title_matches(target_title, line_text, threshold)
                        
                        if similarity >= threshold:
                            # Found our target!
                            target_found = True
                            start_page = page_num
                            found_title = line_text
                            
                            # Extract section number if present
                            section_match = re.match(r'^(\d+(?:\.\d+)*)', line_text)
                            found_section = section_match.group(1) if section_match else ""
                            
                            # Start collecting content from next line
                            i += 1
                            continue
                    else:
                        # We've found the target and this is the next title - stop extraction
                        end_page = page_num
                        extraction_complete = True
                        break
                
                # If we've found the target, collect this line as content
                if target_found:
                    content_lines.append(line_text)
                
                i += 1
            
            # Check if we need to stop after processing this page
            if extraction_complete:
                break
            
            # If we found the target and reached end of page, check if we should continue
            if target_found and not extraction_complete:
                if page_num >= total_pages:
                    # End of document
                    end_page = page_num
                    extraction_complete = True
                    break
        
        if not target_found:
            return None
        
        content = "\n".join(content_lines).strip()
        
        return {
            "title": found_title,
            "section": found_section,
            "start_page": start_page,
            "end_page": end_page or start_page,
            "content": content,
            "content_length": len(content)
        }

def main():
    parser = argparse.ArgumentParser(
        description="Find a title in PDF and extract text under it until next title"
    )
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument("--title", required=True, help="Title to search for (fuzzy match)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Fuzzy match threshold between 0 and 1 (default: 0.75)"
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: extracted/title_text.txt)"
    )
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"[ERROR] PDF not found: {pdf_path}")
    
    print("=" * 70)
    print("FIND TITLE AND EXTRACT TEXT")
    print("=" * 70)
    print(f"\nPDF: {pdf_path}")
    print(f"Target title: {args.title}")
    print(f"Fuzzy threshold: {args.threshold}\n")
    
    result = extract_text_under_title(str(pdf_path), args.title, args.threshold)
    
    if not result:
        print("[ERROR] Title not found. Try lowering the threshold or verifying the title.")
        return
    
    # Prepare output
    output_dir = Path("extracted")
    output_dir.mkdir(exist_ok=True)
    
    if args.output:
        output_path = Path(args.output)
    else:
        # Create safe filename from title
        safe_title = re.sub(r'[^A-Za-z0-9_\-]+', '_', result["title"][:50])
        output_path = output_dir / f"{safe_title}.txt"
    
    # Save text file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {result['title']}\n")
        if result['section']:
            f.write(f"Section: {result['section']}\n")
        f.write(f"Pages: {result['start_page']}")
        if result['end_page'] != result['start_page']:
            f.write(f"-{result['end_page']}")
        f.write(f"\n")
        f.write(f"Content length: {result['content_length']} characters\n")
        f.write("\n" + "=" * 70 + "\n\n")
        f.write(result['content'])
        f.write("\n")
    
    print("[OK] Title found!")
    print(f"  Title: {result['title']}")
    if result['section']:
        print(f"  Section: {result['section']}")
    print(f"  Pages: {result['start_page']}-{result['end_page']}")
    print(f"  Content length: {result['content_length']} characters")
    print(f"\n[Saved] Output: {output_path}")
    
    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)

if __name__ == "__main__":
    main()

