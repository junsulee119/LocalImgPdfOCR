"""
Result management routes for downloading and editing OCR results
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from pathlib import Path
import zipfile
import io
import json
from ..storage import get_job, get_result_path, OUTPUT_DIR

router = APIRouter()

class EditResultRequest(BaseModel):
    content: str

@router.put("/{job_id}/results/{filename}")
async def save_edited_result(job_id: str, filename: str, request: EditResultRequest):
    """Save edited markdown result"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result_path = get_result_path(job_id, filename)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        result_path.write_text(request.content, encoding='utf-8')
        return {"message": "Result saved successfully", "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save result: {str(e)}")

@router.get("/{job_id}/results/{filename}")
async def download_result(job_id: str, filename: str):
    """Download specific result file"""
    result_path = get_result_path(job_id, filename)
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(result_path, filename=filename, media_type='text/markdown')

@router.get("/{job_id}/download/zip")
async def download_all_results(job_id: str):
    """Download all results as ZIP archive"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add all result files
        results_dir = OUTPUT_DIR / job_id / "results"
        if results_dir.exists():
            for result_file in results_dir.glob("*.md"):
                zip_file.write(result_file, result_file.name)
        
        # Add manifest.json
        manifest = {
            "jobName": job.get("name", "Untitled"),
            "kind": job.get("kind", "img"),
            "device": job.get("device", "cuda"),
            "mode": job.get("mode", "text"),
            "outputs": [
                {
                    "input": f.get("name"),
                    "out": f"{Path(f.get('name')).stem}.md",
                    "pagesSel": f.get("pagesSel", "all")
                }
                for f in job.get("files", [])
            ]
        }
        
        zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))
    
    zip_buffer.seek(0)
    
    safe_name = "".join(c for c in job.get("name", "results") if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_name}_results.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
