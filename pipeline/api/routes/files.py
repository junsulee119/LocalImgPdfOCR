"""
Additional API routes for serving uploaded files
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from ..storage import OUTPUT_DIR

router = APIRouter()

@router.get("/{job_id}/files/{filename}")
async def get_job_file(job_id: str, filename: str):
    """Serve uploaded file for preview"""
    file_path = OUTPUT_DIR / job_id / "files" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

@router.get("/{job_id}/files/{filename}/page/{page_num}")
async def get_pdf_page_endpoint(job_id: str, filename: str, page_num: int):
    """
    Serve a single page from a PDF as a new PDF file.
    This ensures the browser's PDF viewer only shows this specific page.
    """
    import pypdfium2 as pdfium
    import io
    from fastapi.responses import StreamingResponse

    file_path = OUTPUT_DIR / job_id / "files" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Load PDF
        pdf = pdfium.PdfDocument(file_path)
        
        # Validate page number (1-based from URL -> 0-based for API)
        if page_num < 1 or page_num > len(pdf):
            raise HTTPException(status_code=400, detail="Invalid page number")
            
        page_idx = page_num - 1
        
        # Create a new PDF with just this page
        new_pdf = pdfium.PdfDocument.new()
        new_pdf.import_pages(pdf, [page_idx])
        
        # Save to memory buffer
        buffer = io.BytesIO()
        new_pdf.save(buffer)
        buffer.seek(0)
        
        pdf.close()
        # new_pdf.close() # pypdfium2 might needed explicit close logic if not saving to file, but save() works.

        return StreamingResponse(
            buffer, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=page_{page_num}.pdf"}
        )

    except Exception as e:
        print(f"Error serving PDF page: {e}")
        raise HTTPException(status_code=500, detail=str(e))
