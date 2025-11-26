import pdfplumber
import re
import json
from pathlib import Path

def is_valid_content_line(line: str) -> bool:
    """
    Filter out lines that are invalid or weird:
    - Single character/letter lines
    - Lines with only numbers or symbols
    - Very short lines that don't make sense
    - Repetitive patterns like "rc_rc_rc_"
    """
    line_clean = line.strip()
    
    # Skip empty lines
    if not line_clean:
        return False
    
    # Skip single character lines
    if len(line_clean) == 1:
        return False
    
    # Skip lines with only one word
    words = line_clean.split()
    if len(words) == 1:
        return False
    
    # Skip very short lines (2-4 chars) that are likely noise
    if len(line_clean) <= 4:
        # Allow short lines that look meaningful (like "0x00", "Bit 0", etc.)
        # But skip if it's just letters/underscores or repetitive
        if re.match(r'^[a-z_]+$', line_clean.lower()):
            return False
        # Skip if it's a repetitive pattern (like "rc_", "rw_", etc.)
        if len(set(line_clean.lower().replace('_', ''))) <= 2:
            return False
    
    # Skip lines that are just numbers (like "1234567890")
    if re.match(r'^[\d\s]+$', line_clean) and len(line_clean) < 5:
        return False
    
    # Skip lines that are mostly special characters
    special_char_ratio = len(re.findall(r'[^\w\s]', line_clean)) / len(line_clean) if line_clean else 0
    if special_char_ratio > 0.7 and len(line_clean) < 10:
        return False
    
    # Skip lines that are just repeated characters (like "---" or "===")
    if len(set(line_clean.replace(' ', ''))) <= 2 and len(line_clean) > 3:
        return False
    
    # Skip repetitive patterns (like "rc_rc_rc_" or "rw_rw_rw_")
    # Check if the line is just a short pattern repeated
    if len(line_clean) > 4:
        # Try to detect if it's a repeating pattern
        for pattern_len in range(2, min(6, len(line_clean) // 2 + 1)):
            pattern = line_clean[:pattern_len]
            # Check if the line is just this pattern repeated
            if line_clean == pattern * (len(line_clean) // pattern_len) + pattern[:len(line_clean) % pattern_len]:
                # If pattern is very short (2-4 chars) and repeated, it's likely noise
                if pattern_len <= 4:
                    return False
    
    return True

def extract_raw_registers(pdf_path: str):
    """
    Extract raw register data from PDF without parsing content.
    Returns list of dicts with section, full_name, short_name, address_offset, 
    reset_value, start_page, end_page, and raw content.
    """
    registers = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        for page_num, page in enumerate(pdf.pages, start=1):
            # Get characters with font info
            chars = page.chars
            
            if not chars:
                continue
            
            # Group characters into lines with font info
            lines = []
            current_line = []
            current_y = None
            line_tolerance = 2
            
            for char in chars:
                char_y = char.get('top', 0)
                char_text = char.get('text', '')
                
                if current_y is None or abs(char_y - current_y) > line_tolerance:
                    if current_line:
                        lines.append(current_line)
                    current_line = []
                    current_y = char_y
                
                current_line.append(char)
            
            if current_line:
                lines.append(current_line)
            
            # Now find registers and extract content
            i = 0
            while i < len(lines):
                line_chars = lines[i]
                line_text = ''.join([c.get('text', '') for c in line_chars])
                line_text_clean = line_text.strip()
                
                if not line_text_clean:
                    i += 1
                    continue
                
                # Check font size first - should be >= 11 and bold for register headers
                avg_size = sum([c.get('size', 0) for c in line_chars]) / len(line_chars) if line_chars else 0
                
                # Check if font size is 11 or more (11, 12, etc.)
                if avg_size < 10.5:
                    i += 1
                    continue
                
                # Check if text is bold (fontname contains "Bold")
                is_bold = any('bold' in str(c.get('fontname', '')).lower() for c in line_chars)
                if not is_bold:
                    i += 1
                    continue
                
                # Check if this is a register header
                # Pattern: [optional section number] + register name [optional short name in parentheses]
                # Examples:
                #   "3.4.3 Control register (CRC_CR)"
                #   "Control register (CRC_CR)"
                #   "3.4.3 Control register"
                section = None
                full_name = None
                
                # Try pattern with section number first: "3.4.3 Control register (CRC_CR)"
                section_match = re.match(r'^(\d+\.\d+\.\d+)\s+(.+)', line_text_clean)
                if section_match:
                    section = section_match.group(1)
                    full_name = section_match.group(2).strip()
                    # Verify it contains "register" to confirm it's a register header
                    if 'register' not in full_name.lower():
                        i += 1
                        continue
                else:
                    # Try pattern without section number - must contain "register"
                    if 'register' in line_text_clean.lower():
                        section = None
                        full_name = line_text_clean
                    else:
                        # Doesn't look like a register header
                        i += 1
                        continue
                
                # Extract short name from parentheses
                # Pattern allows uppercase, lowercase, numbers, underscores, and 'x' for patterns like CAN_TDLxR
                # Also handles multiple parentheses like "(CAN_TDLxR) (x=0..2)" by taking the first one
                short_name_match = re.search(r'\(([A-Za-z0-9_]+)\)', full_name)
                short_name = short_name_match.group(1) if short_name_match else ""
                
                # Look for address offset and reset value in next few lines
                # These are REQUIRED for a valid register entry
                address_offset = None
                reset_value = None
                content_lines = []
                
                # Read next lines until we find another register header (font size >= 11 and bold)
                # Track pages for multi-page registers
                current_extraction_page = page_num
                end_page = page_num
                j = i + 1
                max_pages_to_extract = 4  # Maximum 4 pages per register
                pages_extracted = 0
                
                while pages_extracted < max_pages_to_extract:
                    # Check if we need to move to next page
                    if j >= len(lines):
                        # Move to next page if available
                        if current_extraction_page < total_pages:
                            current_extraction_page += 1
                            pages_extracted += 1
                            
                            # Get next page
                            next_page = pdf.pages[current_extraction_page - 1]
                            next_chars = next_page.chars
                            
                            if not next_chars:
                                break
                            
                            # Group characters into lines for next page
                            lines = []
                            current_line = []
                            current_y = None
                            
                            for char in next_chars:
                                char_y = char.get('top', 0)
                                if current_y is None or abs(char_y - current_y) > 2:
                                    if current_line:
                                        lines.append(current_line)
                                    current_line = []
                                    current_y = char_y
                                current_line.append(char)
                            
                            if current_line:
                                lines.append(current_line)
                            
                            j = 0
                            end_page = current_extraction_page
                        else:
                            break
                    
                    if j >= len(lines):
                        break
                    
                    next_line_chars = lines[j]
                    next_line_text = ''.join([c.get('text', '') for c in next_line_chars]).strip()
                    
                    if not next_line_text:
                        j += 1
                        continue
                    
                    # Check font size of this line
                    next_avg_size = sum([c.get('size', 0) for c in next_line_chars]) / len(next_line_chars) if next_line_chars else 0
                    
                    # If font size is >= 11 and bold and looks like a register header, stop
                    if next_avg_size >= 10.5:
                        next_is_bold = any('bold' in str(c.get('fontname', '')).lower() for c in next_line_chars)
                        if next_is_bold and 'register' in next_line_text.lower():
                            break  # New register found
                    
                    # Extract address offset
                    if address_offset is None:
                        addr_match = re.search(r'Address\s+offset:\s*(0x[0-9A-Fa-f]+)', next_line_text, re.IGNORECASE)
                        if addr_match:
                            address_offset = addr_match.group(1)
                            j += 1
                            continue
                    
                    # Extract reset value
                    if reset_value is None:
                        reset_match = re.search(r'Reset\s+value:\s*(0x[0-9A-Fa-f\s]+)', next_line_text, re.IGNORECASE)
                        if reset_match:
                            reset_value = reset_match.group(1).strip()
                            reset_value = re.sub(r'\s+', ' ', reset_value)
                            j += 1
                            continue
                    
                    # Add to content (filter out invalid lines)
                    if is_valid_content_line(next_line_text):
                        content_lines.append(next_line_text)
                    j += 1
                
                # Join content
                content = '\n'.join(content_lines).strip()
                
                # Only add if we found both address offset AND reset value (complete register)
                if address_offset and reset_value:
                    # Create page range string
                    if end_page == page_num:
                        page_range = str(page_num)
                    else:
                        page_range = f"{page_num}-{end_page}"
                    
                    register_data = {
                        "start_page": page_num,
                        "end_page": end_page,
                        "page_range": page_range,
                        "section": section or "",
                        "full_name": full_name,
                        "short_name": short_name,
                        "address_offset": address_offset,
                        "reset_value": reset_value,
                        "content": content
                    }
                    
                    registers.append(register_data)
                
                # If we moved to next page, break and continue outer loop
                if current_extraction_page > page_num:
                    break
                
                i = j
                continue
                
                i += 1

    return registers

# Usage - only run when executed directly, not when imported
if __name__ == "__main__":
    pdf_file = r"C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
    output_dir = Path("extracted")
    output_dir.mkdir(exist_ok=True)

    print("="*60)
    print("EXTRACTING RAW REGISTER DATA")
    print("="*60)
    print(f"\nPDF: {pdf_file}\n")

    regs = extract_raw_registers(pdf_file)
    print(f"Total registers found: {len(regs)}")

    # Save registers to JSON file with start_page and end_page fields
    json_file = output_dir / "registers.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(regs, f, indent=2, ensure_ascii=False)

    print(f"[Saved] Registers JSON: {json_file}")

    # Save all registers to a single .txt file
    txt_file = output_dir / "registers_all.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        for r in regs:
            # Write register header
            if r['section']:
                f.write(f"{r['section']} ")
            f.write(f"{r['full_name']}\n\n")
            f.write(f"Address offset: {r['address_offset']}\n")
            f.write(f"Reset value: {r['reset_value']}\n\n")
            
            # Write content
            if r['content']:
                f.write(r['content'])
                f.write("\n")
            
            # Add separator between registers
            f.write("\n" + "="*70 + "\n\n")

    print(f"[Saved] All registers .txt: {txt_file}")

    # Summary
    print("\n[Summary]")
    for i, r in enumerate(regs[:5], 1):
        page_info = f"Page {r['start_page']}" + (f"-{r['end_page']}" if r['end_page'] != r['start_page'] else "")
        section_info = f"{r['section']} - " if r['section'] else ""
        print(f"  {i}. {page_info}: {section_info}{r['full_name']} ({r['short_name']})")
        print(f"     Offset: {r['address_offset']} | Reset: {r['reset_value']}")
        print(f"     Content: {len(r['content'])} characters")

    print(f"\nTotal registers extracted: {len(regs)}")
    print(f"  - Registers JSON: {json_file}")
    print(f"  - All registers .txt: {txt_file}")

    print("\n" + "="*60)
    print("Done!")
    print("="*60)


