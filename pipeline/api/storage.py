"""
Job storage management using /output directory
No database - just JSON files for job metadata
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

OUTPUT_DIR = Path("output")
CARDS_FILE = OUTPUT_DIR / "cards.json"

def ensure_output_dir():
    """Ensure output directory exists"""
    OUTPUT_DIR.mkdir(exist_ok=True)

def load_jobs() -> Dict[str, dict]:
    """Load all jobs from cards.json"""
    ensure_output_dir()
    if not CARDS_FILE.exists():
        return {}
    try:
        return json.loads(CARDS_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}

def save_jobs(jobs: Dict[str, dict]):
    """Save all jobs to cards.json"""
    ensure_output_dir()
    CARDS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding='utf-8')

def get_job(job_id: str) -> Optional[dict]:
    """Get single job by ID"""
    jobs = load_jobs()
    return jobs.get(job_id)

def create_job(job_data: dict) -> dict:
    """Create new job"""
    jobs = load_jobs()
    job_id = job_data['id']
    
    # Create job directory structure
    job_dir = OUTPUT_DIR / job_id
    (job_dir / "files").mkdir(parents=True, exist_ok=True)
    (job_dir / "results").mkdir(parents=True, exist_ok=True)
    
    # Save job metadata
    jobs[job_id] = job_data
    save_jobs(jobs)
    
    return job_data

def update_job(job_id: str, **updates) -> Optional[dict]:
    """Update job fields"""
    jobs = load_jobs()
    if job_id not in jobs:
        return None
    
    jobs[job_id].update(updates)
    save_jobs(jobs)
    return jobs[job_id]

def delete_job(job_id: str) -> bool:
    """Delete job and its files"""
    jobs = load_jobs()
    if job_id not in jobs:
        return False
    
    # Delete job directory
    job_dir = OUTPUT_DIR / job_id
    if job_dir.exists():
        import shutil
        shutil.rmtree(job_dir)
    
    # Remove from jobs.json
    del jobs[job_id]
    save_jobs(jobs)
    return True

def get_all_jobs() -> List[dict]:
    """Get all jobs as list"""
    jobs = load_jobs()
    return list(jobs.values())

def save_uploaded_file(job_id: str, filename: str, content: bytes) -> Path:
    """Save uploaded file to job directory"""
    file_path = OUTPUT_DIR / job_id / "files" / filename
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    return file_path

def get_result_path(job_id: str, filename: str) -> Path:
    """Get path for result file"""
    return OUTPUT_DIR / job_id / "results" / filename
