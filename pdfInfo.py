import pymupdf as fitz  # PyMuPDF

def get_toc_pymupdf(pdf_path: str) -> list:
    """
    Get table of contents using PyMuPDF's get_toc() method.
    Returns list of tuples: (level, title, page)
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    doc.close()
    return toc

def get_pdf_titles(pdf_path: str, start_title: int = 1, end_title: int = 10) -> dict:
    """
    Get PDF titles in a range and basic PDF information.
    
    Args:
        pdf_path: Path to the PDF file
        start_title: Starting title number (1-indexed, default: 1)
        end_title: Ending title number (1-indexed, default: 10)
    
    Returns:
        Simple dict with pdf_info and titles list
    """
    doc = fitz.open(pdf_path)
    
    # Get basic PDF info
    pdf_info = {
        "total_pages": len(doc),
        "title": doc.metadata.get("Title", "") if doc.metadata else ""
    }
    
    # Get table of contents
    toc = doc.get_toc()
    doc.close()
    
    # Get titles in range
    total_titles = len(toc)
    # end_title defaults to 10, but cap at total if there are fewer titles
    
    # Adjust for 1-indexed input
    start_idx = max(0, start_title - 1)
    end_idx = min(total_titles, end_title)
    
    # Format titles simply
    titles = []
    for i, item in enumerate(toc[start_idx:end_idx], start=start_title):
        level, title, page = item
        titles.append({
            "num": i,
            "title": title,
            "page": page
        })
    
    return {
        "pdf_info": pdf_info,
        "titles": titles,
        "total": total_titles
    }

if __name__ == "__main__":
    # Example usage
    pdf_path = "C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
    result = get_pdf_titles(pdf_path, start_title=1, end_title=10)
    
    print("PDF Info:")
    print(f"  Total Pages: {result['pdf_info']['total_pages']}")
    print(f"  Title: {result['pdf_info']['title']}")
    print(f"\nTotal Titles: {result['total']}")
    print(f"\nTitles 1-10:")
    for title in result['titles']:
        print(f"  {title['num']}. Page {title['page']}: {title['title']}")
