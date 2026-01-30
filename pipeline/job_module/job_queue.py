"""
Job queue for batch processing with detailed logging
"""
from collections import deque
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from logger import logger, Color

class JobQueue:
    """
    FIFO queue for managing multiple OCR jobs
    """
    
    def __init__(self):
        """Initialize empty job queue"""
        self.queue = deque()
        self.completed = []
        self.failed = []
    
    def add_job(self, job):
        """
        Add a job to the queue
        
        Args:
            job: Job instance
        """
        self.queue.append(job)
        logger.debug(f"Added job to queue: {job.file_path.name}")
    
    def add_jobs(self, jobs):
        """
        Add multiple jobs to the queue
        
        Args:
            jobs: List of Job instances
        """
        logger.debug(f"Adding {len(jobs)} jobs to queue")
        self.queue.extend(jobs)
        logger.debug(f"Queue size: {len(self.queue)} jobs")
    
    def process_queue(self, callback=None):
        """
        Process all jobs in queue with detailed per-job logging
        
        Args:
            callback: Optional callback function(job, index, total) called after each job
            
        Returns:
            tuple: (num_completed, num_failed)
        """
        total = len(self.queue)
        index = 0
        
        logger.section("Job Queue Processing")
        logger.info(f"Total jobs: {total}")
        print()
        
        while self.queue:
            job = self.queue.popleft()
            index += 1
            
            # Format job ID with zero-padding
            job_id = f"{Path(job.file_path).stem}_{index:03d}"
            
            # Start message - all on one line
            start_msg = f"{Color.BRIGHT_GREEN.value}Processing{Color.RESET.value} {Color.BRIGHT_GREEN.value}start{Color.RESET.value} Job: {job_id}"
            logger.plain(f"{Color.CYAN.value}INFO{Color.RESET.value} {start_msg}")
            
            logger.indent()
            logger.debug(f"File: {job.file_path.name}")
            logger.debug(f"Type: {job.model_type}")
            
            # Execute job
            logger.info(f"Job status: Running...")
            success = job.execute()
            
            logger.dedent()
            
            # Completion message - all on one line
            if success:
                self.completed.append(job)
                complete_msg = f"{Color.BRIGHT_GREEN.value}Processing{Color.RESET.value} {Color.BRIGHT_GREEN.value}complete{Color.RESET.value} Job: {job_id}"
                logger.plain(f"{Color.CYAN.value}INFO{Color.RESET.value} {complete_msg}")
            else:
                self.failed.append(job)
                failed_msg = f"{Color.BRIGHT_GREEN.value}Processing{Color.RESET.value} {Color.BRIGHT_RED.value}failed{Color.RESET.value} Job: {job_id}"
                logger.plain(f"{Color.CYAN.value}INFO{Color.RESET.value} {failed_msg}")
                if job.error:
                    logger.indent()
                    logger.error(f"Error: {job.error}")
                    logger.dedent()
            
            print()
            
            if callback:
                callback(job, index - 1, total)
        
        logger.debug(f"Queue processing complete: {len(self.completed)} completed, {len(self.failed)} failed")
        return len(self.completed), len(self.failed)
    
    def get_status(self):
        """
        Get queue status
        
        Returns:
            dict: Status information
        """
        return {
            'pending': len(self.queue),
            'completed': len(self.completed),
            'failed': len(self.failed),
            'total': len(self.queue) + len(self.completed) + len(self.failed)
        }
    
    def clear(self):
        """Clear all queues"""
        self.queue.clear()
        self.completed.clear()
        self.failed.clear()
