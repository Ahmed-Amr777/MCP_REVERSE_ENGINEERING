import pdfplumber
import pymupdf  # PyMuPDF for image extraction
import json
from pathlib import Path
import base64

PDF_PATH = "C:/Users/ahmed/OneDrive/Desktop/information/machine learning/projects/stm32f10xxx.pdf"
START_PAGE = 122  # 1-indexed
END_PAGE = 122   # 1-indexed
OUTPUT_DIR = Path("extracted")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_images_from_pages(pdf_path: str, start_page: int, end_page: int, output_dir: Path) -> dict:
    """
    Extract images from PDF pages and save them.
    Returns dict with image paths and metadata.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    result = {
        "pages": [],
        "total_images": 0
    }
    
    # Open PDF with PyMuPDF for image extraction
    doc = pymupdf.open(pdf_path)
    
    for page_num in range(start_page - 1, end_page):  # Convert to 0-indexed
        if page_num >= len(doc):
            break
            
        page = doc[page_num]
        page_images = []
        
        # Get image list from the page
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]  # Image XREF number
            
            try:
                # Extract image
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Save image
                image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                image_path = images_dir / image_filename
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # Get image metadata
                # Get relative path
                try:
                    rel_path = str(image_path.relative_to(Path.cwd()))
                except ValueError:
                    rel_path = str(image_path)
                
                image_info = {
                    "filename": image_filename,
                    "path": rel_path,
                    "format": image_ext,
                    "size_bytes": len(image_bytes),
                    "xref": xref
                }
                
                page_images.append(image_info)
                
            except Exception as e:
                print(f"[WARNING] Could not extract image {img_index + 1} from page {page_num + 1}: {e}")
                continue
        
        if page_images:
            result["pages"].append({
                "page_number": page_num + 1,
                "images": page_images,
                "image_count": len(page_images)
            })
            result["total_images"] += len(page_images)
    
    doc.close()
    return result

def extract_page_as_image(pdf_path: str, page_num: int, output_dir: Path, dpi: int = 150) -> str:
    """
    Render entire page as an image and save it.
    Returns path to saved image.
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    doc = pymupdf.open(pdf_path)
    page = doc[page_num - 1]  # Convert to 0-indexed
    
    # Render page as image
    pix = page.get_pixmap(dpi=dpi)
    image_path = images_dir / f"page_{page_num}_full.png"
    pix.save(str(image_path))
    
    doc.close()
    # Return relative path from current directory
    try:
        return str(image_path.relative_to(Path.cwd()))
    except ValueError:
        # If not relative, return the path as is
        return str(image_path)

# Usage - only run when executed directly, not when imported
if __name__ == "__main__":
    print("="*60)
    print("EXTRACTING IMAGES FROM PDF PAGES")
    print("="*60)
    print(f"\nPDF: {PDF_PATH}")
    print(f"Pages: {START_PAGE} to {END_PAGE}")
    print(f"Output Directory: {OUTPUT_DIR}\n")

    # Extract embedded images
    print("[Extracting] Embedded images from pages...")
    images_result = extract_images_from_pages(PDF_PATH, START_PAGE, END_PAGE, OUTPUT_DIR)

    # Also render full pages as images
    print("\n[Rendering] Full page images...")
    full_page_images = []
    for page_num in range(START_PAGE, END_PAGE + 1):
        page_image_path = extract_page_as_image(PDF_PATH, page_num, OUTPUT_DIR)
        full_page_images.append({
            "page_number": page_num,
            "image_path": page_image_path
        })

    # Combine results
    output_data = {
        "pdf_path": PDF_PATH,
        "pages_range": {
            "start": START_PAGE,
            "end": END_PAGE
        },
        "embedded_images": images_result,
        "full_page_images": full_page_images,
        "summary": {
            "total_embedded_images": images_result["total_images"],
            "total_full_page_images": len(full_page_images),
            "pages_with_images": len(images_result["pages"])
        }
    }

    # Save results to JSON
    output_file = OUTPUT_DIR / "images_extraction_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n[Saved] Results JSON: {output_file}")

    # Print summary
    print("\n[Summary]")
    print(f"  Embedded Images Found: {images_result['total_images']}")
    print(f"  Full Page Images: {len(full_page_images)}")
    print(f"  Pages with Embedded Images: {len(images_result['pages'])}")

    if images_result['pages']:
        print("\n  Images by Page:")
        for page_info in images_result['pages']:
            print(f"    Page {page_info['page_number']}: {page_info['image_count']} image(s)")
            for img in page_info['images']:
                print(f"      - {img['filename']} ({img['format']}, {img['size_bytes']} bytes)")

    print(f"\n  Full Page Images:")
    for page_img in full_page_images:
        print(f"    Page {page_img['page_number']}: {page_img['image_path']}")

    print("\n" + "="*60)
    print("Done! Images saved to extracted/images/")
    print("="*60)

