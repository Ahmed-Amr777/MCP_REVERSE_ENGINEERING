import pymupdf  # PyMuPDF
from pathlib import Path
import json

def extract_pdf_pages(pdf_path: str, start_page: int, end_page: int, output_path: str = None) -> dict:
    """
    Extract a range of pages from a PDF and save as a new PDF file.
    
    Args:
        pdf_path: Path to the source PDF file
        start_page: Starting page number (1-indexed)
        end_page: Ending page number (1-indexed, inclusive)
        output_path: Path for the output PDF file. If None, auto-generates based on input.
    
    Returns:
        dict with output_path, pages_extracted, and metadata
    """
    # Validate page range
    if start_page < 1:
        raise ValueError("start_page must be >= 1")
    if end_page < start_page:
        raise ValueError("end_page must be >= start_page")
    
    # Open source PDF
    source_doc = pymupdf.open(pdf_path)
    total_pages = len(source_doc)
    
    # Validate page range against PDF
    if start_page > total_pages:
        raise ValueError(f"start_page ({start_page}) exceeds total pages ({total_pages})")
    if end_page > total_pages:
        end_page = total_pages  # Cap at total pages
    
    # Convert 1-indexed to 0-indexed
    start_idx = start_page - 1
    end_idx = end_page  # end_page is inclusive, but insert_pdf uses exclusive end
    
    # Create new PDF document
    new_doc = pymupdf.open()
    
    # Insert pages from source PDF
    new_doc.insert_pdf(source_doc, from_page=start_idx, to_page=end_idx)
    
    # Generate output path if not provided
    if output_path is None:
        source_path = Path(pdf_path)
        output_dir = source_path.parent / "extracted"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"{source_path.stem}_pages_{start_page}_to_{end_page}.pdf"
        output_path = str(output_dir / output_filename)
    else:
        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the new PDF
    new_doc.save(output_path)
    
    # Close documents
    new_doc.close()
    source_doc.close()
    
    # Verify file was created
    output_path_abs = Path(output_path).resolve()
    file_size = output_path_abs.stat().st_size if output_path_abs.exists() else 0
    
    return {
        "source_pdf": pdf_path,
        "output_path": str(output_path_abs),
        "pages_extracted": {
            "start_page": start_page,
            "end_page": end_page,
            "total_pages": end_page - start_page + 1
        },
        "source_pdf_total_pages": total_pages,
        "file_size_bytes": file_size,
        "file_exists": output_path_abs.exists()
    }

if __name__ == "__main__":
    # Example usage
    pdf_file = r"C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
    result = extract_pdf_pages(pdf_file, start_page=724, end_page=724)
    print(json.dumps(result, indent=2, ensure_ascii=False))

