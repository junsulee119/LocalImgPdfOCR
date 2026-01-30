from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import zipfile
import io
import os
from pathlib import Path
from datetime import datetime

from ..storage import get_job, OUTPUT_DIR

router = APIRouter()

class BatchDownloadRequest(BaseModel):
    job_ids: List[str]

@router.post("/download")
async def batch_download(payload: BatchDownloadRequest):
    """
    Generate a ZIP file containing results from multiple jobs.
    Structure:
    root/
      JobName1/
        file1.md
        file2.md
      JobName2/
        ...
    """
    job_ids = payload.job_ids
    if not job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")

    # verify jobs exist and have paths
    jobs_to_zip = []
    for job_id in job_ids:
        job = get_job(job_id)
        if job:
            results_path = OUTPUT_DIR / job_id / "results"
            if results_path.exists():
                jobs_to_zip.append({
                    "name": job['name'],
                    "path": results_path
                })
        # If job has no results or doesn't exist, we skip it silently or warn?
        # User requested filtering on client side, so backend just processes what it can.

    if not jobs_to_zip:
        raise HTTPException(status_code=404, detail="No valid results found for selected jobs")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in jobs_to_zip:
            folder_name = item["name"]
            # Sanitize folder name for OS compatibility (basic)
            folder_name = "".join([c for c in folder_name if c.isalnum() or c in (' ', '-', '_')]).strip()
            
            base_path = item["path"]
            
            # Walk through the results directory
            for root, _, files in os.walk(base_path):
                for file in files:
                    file_path = Path(root) / file
                    # Calculate arcname relative to results folder, prefixed with Job Name
                    # e.g. results/foo.md -> JobName/foo.md
                    
                    rel_path = file_path.relative_to(base_path)
                    arcname = Path(folder_name) / rel_path
                    
                    zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    
    filename = f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
