"""
Job management endpoints
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List
from datetime import datetime
import uuid

from ..storage import (
    get_all_jobs, get_job, create_job, update_job, delete_job,
    save_uploaded_file, OUTPUT_DIR
)
from ...preprocessing_module.pdf import get_pdf_page_count
from ..queue_manager import job_queue
from fastapi.responses import StreamingResponse
import zipfile
import io
import os
from pathlib import Path

router = APIRouter()

def generate_job_id() -> str:
    """Generate unique job ID"""
    return uuid.uuid4().hex[:12]

def generate_file_id() -> str:
    """Generate unique file ID"""
    return uuid.uuid4().hex[:8]

def now_name() -> str:
    """Generate timestamp-based job name"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

@router.post("")
async def create_new_job(
    files: List[UploadFile] = File(...),
    kind: str = Form(...),
    mode: str = Form(...),
    device: str = Form(...)
):
    """Create new job with uploaded files"""
    job_id = generate_job_id()
    
    # Process uploaded files
    file_objects = []
    for upload_file in files:
        file_id = generate_file_id()
        filename = upload_file.filename
        
        # Save file
        content = await upload_file.read()
        save_uploaded_file(job_id, filename, content)
        
        # Determine file type
        ext = filename.lower().split('.')[-1]
        if ext == 'pdf':
            file_type = 'pdf'
        elif ext in ['png', 'jpg', 'jpeg', 'webp']:
            file_type = 'img'
        else:
            file_type = 'file'
        
        # Get page count if PDF
        page_count = 1
        if file_type == 'pdf':
            try:
                page_count = get_pdf_page_count(save_uploaded_file(job_id, filename, content))
            except Exception as e:
                print(f"Failed to count PDF pages: {e}")
        
        file_objects.append({
            "id": file_id,
            "name": filename,
            "type": file_type,
            "pagesSel": "all",
            "pageCount": page_count
        })
    
    # Create job
    job_data = {
        "id": job_id,
        "name": now_name(),
        "createdAt": datetime.now().isoformat(),
        "kind": kind,
        "files": file_objects,
        "mode": mode,
        "device": device,
        "status": "OCR진행가능" if file_objects else "대기",
        "progress": 0,
        "perFileResults": {}
    }
    
    created_job = create_job(job_data)
    return created_job

@router.get("")
async def get_jobs():
    """Get all jobs"""
    jobs = get_all_jobs()
    return {"jobs": jobs}

@router.get("/{job_id}")
async def get_job_by_id(job_id: str):
    """Get specific job"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/enqueue")
async def enqueue_job(job_id: str):
    """Add job to processing queue"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = await job_queue.enqueue(job_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@router.delete("/{job_id}")
async def remove_job(job_id: str):
    """Delete job"""
    success = delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted"}

@router.post("/{job_id}/files/add")
async def add_files_to_job(job_id: str, files: List[UploadFile] = File(...)):
    """Add files to existing job"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    added_files = []
    
    for upload_file in files:
        # Generate file metadata
        file_id = str(uuid.uuid4()).replace('-', '')[:12]
        filename = upload_file.filename
        ext = filename.lower().split('.')[-1]
        file_type = 'pdf' if ext == 'pdf' else 'img'
        
        # Save file
        content = await upload_file.read()
        saved_path = save_uploaded_file(job_id, filename, content)
        
        # Get page count
        page_count = 1
        if file_type == 'pdf':
            try:
                page_count = get_pdf_page_count(saved_path)
            except Exception as e:
                print(f"Failed to count PDF pages: {e}")

        # Create file object
        file_obj = {
            "id": file_id,
            "name": filename,
            "type": file_type,
            "pagesSel": "all",
            "pageCount": page_count
        }
        
        added_files.append(file_obj)
    
    # Update job's file list
    job['files'].extend(added_files)
    update_job(job_id, files=job['files'])
    
    return {
        "message": f"Added {len(added_files)} files",
        "files": added_files
    }

@router.put("/{job_id}/files/{file_id}/pages")
async def update_file_page_selection(job_id: str, file_id: str, data: dict):
    """Update page selection for a specific PDF file"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Find the file in job's file list
    file_found = False
    for file_obj in job['files']:
        if file_obj['id'] == file_id:
            file_obj['pagesSel'] = data.get('pagesSel', 'all')
            file_found = True
            break
    
    if not file_found:
        raise HTTPException(status_code=404, detail="File not found in job")
    
    # Update job
    update_job(job_id, files=job['files'])
    
    return {
        "message": "Page selection updated",
        "file_id": file_id,
        "pagesSel": data.get('pagesSel', 'all')
    }

@router.put("/{job_id}/name")
async def update_job_name(job_id: str, data: dict):
    """Update job name"""
    job = update_job(job_id, name=data.get("name"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.put("/{job_id}/mode")
async def update_job_mode(job_id: str, data: dict):
    """Update job mode (text/img)"""
    job = update_job(job_id, mode=data.get("mode"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.put("/{job_id}/device")
async def update_job_device(job_id: str, data: dict):
    """Update job device (cpu/cuda)"""
    job = update_job(job_id, device=data.get("device"))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.delete("/{job_id}")
async def remove_job(job_id: str):
    """Delete job and its files"""
    success = delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"message": "Job deleted"}
    return {"message": "Job deleted"}

@router.get("/{job_id}/results/download")
async def download_job_results(job_id: str):
    """Download all results for a job as ZIP"""
    job = get_job(job_id)
    if not job:
         raise HTTPException(status_code=404, detail="Job not found")

    results_dir = OUTPUT_DIR / job_id / "results"
    if not results_dir.exists():
         raise HTTPException(status_code=404, detail="Results not found")
    
    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
         for root, _, files in os.walk(results_dir):
             for file in files:
                 file_path = Path(root) / file
                 rel_path = file_path.relative_to(results_dir)
                 zip_file.write(file_path, rel_path)
    
    zip_buffer.seek(0)
    
    # Filename: JobName_results.zip
    safe_name = "".join([c for c in job['name'] if c.isalnum() or c in (' ', '-', '_')]).strip()
    filename = f"{safe_name}_results.zip"
    
    return StreamingResponse(
        zip_buffer, 
        media_type="application/zip", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
