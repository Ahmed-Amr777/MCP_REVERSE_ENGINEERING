import pdfplumber
import sys

def inspect_page_fonts(pdf_path: str, page_num: int, output_txt=None):
    """
    Inspect each line in a PDF page, showing font size and bold info.
    If output_txt is provided, save the result to a file.
    If output_txt is None, automatically generates filename based on page_num.
    """
    # Auto-generate output filename if not provided
    if output_txt is None:
        output_txt = f"page{page_num}_fonts.txt"
    results = []
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num - 1]  # Convert 1-indexed to 0-indexed
        # Get characters with font info
        chars = page.chars
        
        # Group characters into words/lines
        current_line = []
        current_y = None
        line_height_tolerance = 2
        
        for char in chars:
            char_y = char['top']
            char_text = char['text']
            fontname = char.get('fontname', '')
            size = char.get('size', 0)
            is_bold = 'Bold' in fontname or 'Bd' in fontname or 'Black' in fontname
            
            # Start new line if y position changes significantly
            if current_y is None or abs(char_y - current_y) > line_height_tolerance:
                if current_line:
                    # Process previous line
                    line_text = ''.join([c['text'] for c in current_line])
                    if line_text.strip():
                        avg_size = sum([c.get('size', 0) for c in current_line]) / len(current_line) if current_line else 0
                        is_line_bold = any('Bold' in c.get('fontname', '') or 'Bd' in c.get('fontname', '') for c in current_line)
                        results.append(f"[Size: {avg_size:.1f}, Bold: {is_line_bold}] {line_text}")
                current_line = []
                current_y = char_y
            
            current_line.append({
                'text': char_text,
                'fontname': fontname,
                'size': size,
                'top': char_y
            })
        
        # Don't forget the last line
        if current_line:
            line_text = ''.join([c['text'] for c in current_line])
            if line_text.strip():
                avg_size = sum([c.get('size', 0) for c in current_line]) / len(current_line) if current_line else 0
                is_line_bold = any('Bold' in c.get('fontname', '') or 'Bd' in c.get('fontname', '') for c in current_line)
                results.append(f"[Size: {avg_size:.1f}, Bold: {is_line_bold}] {line_text}")
    
    # Print to console with safe encoding
    for r in results:
        try:
            print(r)
        except UnicodeEncodeError:
            # Replace problematic Unicode characters that can't be encoded in console
            safe_r = r.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace')
            print(safe_r)
    
    # Optional save
    if output_txt:
        with open(output_txt, 'w', encoding='utf-8') as f:
            f.write("\n".join(results))

if __name__ == "__main__":
    # Example usage
    pdf_file = r"C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
    # Output filenames are automatically generated based on page_num
    # Check page 572 for CAN mailbox registers
    inspect_page_fonts(pdf_file, page_num=572)
    inspect_page_fonts(pdf_file, page_num=723)
    inspect_page_fonts(pdf_file, page_num=724)