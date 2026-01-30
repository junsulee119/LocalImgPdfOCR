"""
Batch job processing utilities
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from job_module.single_job import Job
from job_module.job_queue import JobQueue
from config import get_queue_timestamp
from output import create_job_output_dir

def create_batch_jobs(file_paths, model_type="text_only", 
                     page_selection=None, model=None, processor=None):
    """
    Create Job instances for multiple files
    
    Args:
        file_paths: List of file paths
        model_type: "text_only" or "text_img"
        page_selection: Page selection for PDFs (if applicable to all files)
        model: Pre-loaded model (optional, shared across jobs)
        processor: Pre-loaded processor (optional, shared across jobs)
        
    Returns:
        tuple: (jobs, queue_timestamp, output_dir)
    """
    # Create output directory with timestamp
    queue_timestamp = get_queue_timestamp()
    output_base_dir = create_job_output_dir(queue_timestamp)
    
    jobs = []
    for file_path in file_paths:
        job = Job(
            file_path=file_path,
            output_dir=output_base_dir,
            model_type=model_type,
            page_selection=page_selection,
            model=model,
            processor=processor
        )
        jobs.append(job)
    
    return jobs, queue_timestamp, output_base_dir

def process_batch(jobs, callback=None):
    """
    Process a batch of jobs using a queue
    
    Args:
        jobs: List of Job instances
        callback: Optional callback function(job, index, total)
        
    Returns:
        tuple: (num_completed, num_failed)
    """
    queue = JobQueue()
    queue.add_jobs(jobs)
    return queue.process_queue(callback=callback)
