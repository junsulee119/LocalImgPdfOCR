"""
PDF preprocessing module
Handles PDF to image conversion with page selection.
"""
import pypdfium2 as pdfium
from pathlib import Path
import re
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import PDF_RENDER_SCALE, PDF_RENDER_DPI

def get_pdf_page_count(pdf_path):
    """
    Get total number of pages in a PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        int: Number of pages
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        count = len(pdf)
        pdf.close()
        return count
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {pdf_path}. Error: {e}")

def parse_page_selection(page_str):
    """
    Parse page selection string into list of 0-indexed page numbers
    
    Examples:
        "all" -> None (means all pages)
        "1" -> [0]
        "1-5" -> [0, 1, 2, 3, 4]
        "1,3,5" -> [0, 2, 4]
        "1-3,5,7-9" -> [0, 1, 2, 4, 6, 7, 8]
    
    Args:
        page_str: String with page numbers/ranges (1-indexed)
    
    Returns:
        List of 0-indexed page numbers, or None for "all"
    """
    if not page_str or page_str.strip().lower() == 'all':
        return None
    
    pages = set()
    # Remove all whitespace and split by comma
    parts = page_str.strip().replace(' ', '').split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if '-' in part:
            # Range: "1-5"
            try:
                start, end = part.split('-', 1)
                start = int(start)
                end = int(end)
                if start < 1 or end < 1:
                    print(f"[PDF] Warning: Invalid page range '{part}' - pages must be >= 1, skipping")
                    continue
                if start > end:
                    print(f"[PDF] Warning: Invalid range '{part}' - start > end, skipping")
                    continue
                # Convert to 0-indexed
                pages.update(range(start - 1, end))
            except ValueError as e:
                print(f"[PDF] Warning: Invalid range format '{part}', skipping: {e}")
                continue
        else:
            # Single page: "5"
            try:
                page_num = int(part)
                if page_num < 1:
                    print(f"[PDF] Warning: Invalid page number '{part}' - must be >= 1, skipping")
                    continue
                # Convert to 0-indexed
                pages.add(page_num - 1)
            except ValueError as e:
                print(f"[PDF] Warning: Invalid page number '{part}', skipping: {e}")
                continue
    
    result = sorted(list(pages)) if pages else None
    print(f"[PDF] Parsed '{page_str}' -> {len(result) if result else 'all'} pages")
    return result

def render_page(pdf, page_num, scale=PDF_RENDER_SCALE):
    """
    Render a single PDF page to PIL Image
    
    Args:
        pdf: pypdfium2 PdfDocument object
        page_num: Page number (0-indexed)
        scale: Scale factor for rendering (default: 2.77 for 200 DPI)
        
    Returns:
        PIL.Image: Rendered page image
    """
    page = pdf[page_num]
    pil_image = page.render(scale=scale).to_pil()
    return pil_image

def pdf_to_images(pdf_path, page_numbers=None, dpi=PDF_RENDER_DPI):
    """
    Convert PDF pages to PIL Images
    
    Args:
        pdf_path: Path to PDF file
        page_numbers: List of page numbers to convert (0-indexed), None for all pages
        dpi: DPI for rendering (default: 200)
        
    Returns:
        list: List of (page_num, PIL.Image) tuples
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Calculate scale factor from DPI
    scale = dpi / 72.0  # 72 is the base DPI
    
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        total_pages = len(pdf)
        
        # Determine which pages to process
        if page_numbers is None:
            page_numbers = list(range(total_pages))
        else:
            # Validate page numbers
            page_numbers = [p for p in page_numbers if 0 <= p < total_pages]
        
        # Render pages
        images = []
        for page_num in page_numbers:
            img = render_page(pdf, page_num, scale)
            images.append((page_num, img))
        
        pdf.close()
        return images
        
    except Exception as e:
        raise ValueError(f"Failed to convert PDF to images: {pdf_path}. Error: {e}")
