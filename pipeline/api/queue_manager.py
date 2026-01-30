"""
Async job queue manager
Processes OCR jobs sequentially with real-time WebSocket updates
"""
import asyncio
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import sys

# Add pipeline to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .storage import get_job, update_job, get_result_path, OUTPUT_DIR
from .websocket import ws_manager

class JobQueue:
    def __init__(self):
        self.queue: List[str] = []
        self.active_job_id: Optional[str] = None
        self.processing = False
    
    async def enqueue(self, job_id: str):
        """Add job to queue and start processing"""
        if job_id in self.queue:
            return {"error": "Job already in queue"}
        
        self.queue.append(job_id)
        
        # Broadcast queue update
        await ws_manager.broadcast({
            "type": "queue_update",
            "queue_length": len(self.queue)
        })
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_queue())
        
        return {
            "message": "Job enqueued",
            "queue_position": len(self.queue)
        }
    
    async def _process_queue(self):
        """Process jobs in queue sequentially"""
        if self.processing:
            return
        
        self.processing = True
        
        while self.queue:
            job_id = self.queue.pop(0)
            self.active_job_id = job_id
            
            # Update queue positions for remaining jobs
            await ws_manager.broadcast({
                "type": "queue_update",
                "queue_length": len(self.queue)
            })
            
            # Run the job
            await self._run_job(job_id)
            
        self.active_job_id = None
        self.processing = False
    
    async def _run_job(self, job_id: str):
        """Execute OCR job"""
        print(f"[QUEUE] Starting job {job_id}")
        job = get_job(job_id)
        if not job:
            print(f"[QUEUE] ERROR: Job {job_id} not found")
            return
        
        try:
            # Update status to running
            print(f"[QUEUE] Updating job {job_id} to running state")
            update_job(job_id, status="OCR진행중", progress=0)
            await ws_manager.broadcast({
                "type": "job_status",
                "job_id": job_id,
                "status": "OCR진행중",
                "progress": 0
            })
            
            # Import OCR functions
            print(f"[QUEUE] Importing OCR functions")
            try:
                from pipeline.ocr_module.ocr import extract_text_only, extract_text_with_images
                from pipeline.preprocessing_module.img import load_image
                from pipeline.preprocessing_module.pdf import pdf_to_images, parse_page_selection
                print(f"[QUEUE] OCR functions imported successfully")
            except Exception as e:
                print(f"[QUEUE] ERROR: Failed to import OCR functions: {e}")
                raise
            
            total_files = len(job['files'])
            per_file_results = {}
            failed_files = []  # Track failed files
            
            print(f"[QUEUE] Processing {total_files} files for job {job_id}")
            
            # Process each file
            for idx, file_obj in enumerate(job['files']):
                file_id = file_obj['id']
                file_name = file_obj['name']
                file_path = OUTPUT_DIR / job_id / "files" / file_name
                file_type = file_obj.get('type', 'img')  # 'img' or 'pdf'
                
                print(f"[QUEUE] Processing file {idx+1}/{total_files}: {file_name} (type: {file_type})")
                
                if not file_path.exists():
                    print(f"[QUEUE] WARNING: File not found: {file_path}")
                    failed_files.append(file_name)
                    continue
                
                # Update progress
                progress = int((idx / total_files) * 100)
                update_job(job_id, progress=progress)
                await ws_manager.broadcast({
                    "type": "job_progress",
                    "job_id": job_id,
                    "progress": progress,
                    "current_file": file_name
                })
                
                # Run OCR in thread pool (blocking operation)
                loop = asyncio.get_event_loop()
                output_dir = OUTPUT_DIR / job_id / "results"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    print(f"[QUEUE] Running OCR on {file_name} (mode: {job['mode']}, type: {file_type})")
                    
                    # Handle PDFs: convert to images first
                    if file_type == 'pdf':
                        # Parse page selection (e.g., "all", "1-5", "1,3,5-7")
                        pages_sel = file_obj.get('pagesSel', 'all')
                        
                        # parse_page_selection takes only the page string
                        if pages_sel == 'all':
                            page_numbers = None  # None means all pages
                        else:
                            page_numbers = parse_page_selection(pages_sel)
                        
                        print(f"[QUEUE] Converting PDF pages {pages_sel} to images")
                        # Convert PDF pages to images
                        page_images = await loop.run_in_executor(
                            None,
                            pdf_to_images,
                            file_path,
                            page_numbers
                        )
                        
                        # Process each page and save as separate file
                        page_results = {}
                        for page_num, page_img in page_images:
                            print(f"[QUEUE] Processing PDF page {page_num + 1}")
                            
                            # Define stream callback for this page
                            def stream_handler(text):
                                try:
                                    asyncio.run_coroutine_threadsafe(
                                        ws_manager.broadcast({
                                            "type": "ocr_chunk",
                                            "job_id": job_id,
                                            "file_id": file_id,
                                            "page": page_num + 1,
                                            "text": text
                                        }),
                                        loop
                                    )
                                except Exception as e:
                                    print(f"[QUEUE] Stream handler error: {e}")
                            
                            # Save page image temporarily
                            temp_img_path = output_dir / f"temp_page_{page_num}.png"
                            page_img.save(temp_img_path)
                            
                            try:
                                if job['mode'] == 'text':
                                    page_text = await loop.run_in_executor(
                                        None,
                                        extract_text_only,
                                        temp_img_path,
                                        None, # model
                                        None, # processor
                                        job.get('device'), # device
                                        stream_handler # stream_callback
                                    )
                                    image_list = []
                                else:
                                    # Use unique prefix for images to prevent overwriting
                                    img_prefix = f"{Path(file_name).stem}_page_{page_num + 1}_"
                                    page_text, image_mapping = await loop.run_in_executor(
                                        None,
                                        extract_text_with_images,
                                        temp_img_path,
                                        output_dir,
                                        None,  # model
                                        None,  # processor
                                        img_prefix,
                                        job.get('device'), # device
                                        stream_handler # stream_callback
                                    )
                                    image_list = list(image_mapping.values())
                                
                                # Create separate .md file for each page
                                page_md = f"# {Path(file_name).stem} - Page {page_num + 1}\n\n{page_text}"
                                page_out_name = f"{Path(file_name).stem}_page_{page_num + 1}.md"
                                
                                # Save page result
                                page_result_path = get_result_path(job_id, page_out_name)
                                page_result_path.parent.mkdir(parents=True, exist_ok=True)
                                page_result_path.write_text(page_md, encoding='utf-8')
                                
                                # Store this page's result
                                page_results[page_num + 1] = {
                                    'page': page_num + 1,
                                    'outName': page_out_name,
                                    'md': page_md,
                                    'originalMd': page_md,
                                    'images': image_list
                                }
                                
                                print(f"[QUEUE] Saved page {page_num + 1} as {page_out_name} with {len(image_list)} images")
                                
                                # Broadcast LIVE update for this page
                                await ws_manager.broadcast({
                                    "type": "page_complete",
                                    "job_id": job_id,
                                    "file_id": file_id,
                                    "page": page_num + 1,
                                    "result": page_results[page_num + 1]
                                })
                                
                            finally:
                                # Clean up temp file
                                if temp_img_path.exists():
                                    temp_img_path.unlink()
                        
                        # Store all page results for this file
                        per_file_results[file_id] = {
                            "pages": page_results,  # Dict keyed by page number
                            "isPdf": True,
                            "totalPages": len(page_results)
                        }
                        
                        print(f"[QUEUE] Completed {len(page_results)} pages for {file_name}")
                        
                        # Don't broadcast file_complete for PDFs (already sent page_complete for each)
                        
                    else:
                        # Regular image
                        
                        # Define stream callback for this file
                        def stream_handler(text):
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    ws_manager.broadcast({
                                        "type": "ocr_chunk",
                                        "job_id": job_id,
                                        "file_id": file_id,
                                        "page": None,
                                        "text": text
                                    }),
                                    loop
                                )
                            except Exception as e:
                                print(f"[QUEUE] Stream handler error: {e}")
                            
                        image_list = []
                        if job['mode'] == 'text':
                            # Text-only mode
                            md = await loop.run_in_executor(
                                None,
                                extract_text_only,
                                file_path,
                                None, # model
                                None, # processor
                                job.get('device'), # device
                                stream_handler # stream_callback
                            )
                        else:
                            # Text + images mode
                            # Use unique prefix for images
                            img_prefix = f"{Path(file_name).stem}_"
                            md, image_mapping = await loop.run_in_executor(
                                None,
                                extract_text_with_images,
                                file_path,
                                output_dir,
                                None,  # model
                                None,  # processor
                                img_prefix,
                                job.get('device'), # device
                                stream_handler # stream_callback
                            )
                            image_list = list(image_mapping.values())
                        
                        out_name = f"{Path(file_name).stem}.md"
                        
                        print(f"[QUEUE] OCR completed for {file_name} with {len(image_list)} images")
                        
                        # Save result
                        result_path = get_result_path(job_id, out_name)
                        result_path.parent.mkdir(parents=True, exist_ok=True)
                        result_path.write_text(md, encoding='utf-8')
                        
                        # Store in job results
                        per_file_results[file_id] = {
                            "md": md,
                            "originalMd": md,
                            "outName": out_name,
                            "images": image_list
                        }
                    
                        print(f"[QUEUE] Broadcasting file completion for {file_name}")
                    
                        # Broadcast file completion (for regular images)
                        await ws_manager.broadcast({
                            "type": "file_complete",
                            "job_id": job_id,
                            "file_id": file_id,
                            "result": per_file_results[file_id]
                        })
                    
                except Exception as e:
                    print(f"[QUEUE] ERROR processing file {file_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_files.append(file_name)
                    continue
            
            # Determine final status
            if failed_files:
                if len(failed_files) == total_files:
                    # All files failed
                    final_status = "실패"
                    error_msg = f"모든 파일 처리 실패: {', '.join(failed_files)}"
                    print(f"[QUEUE] Job {job_id} failed completely")
                    
                    update_job(job_id, status=final_status, progress=0)
                    await ws_manager.broadcast({
                        "type": "job_error",
                        "job_id": job_id,
                        "error": error_msg
                    })
                else:
                    # Partial success
                    final_status = "완료"
                    print(f"[QUEUE] Job {job_id} completed with {len(failed_files)} failures")
                    
                    update_job(
                        job_id,
                        status=final_status,
                        progress=100,
                        perFileResults=per_file_results
                    )
                    
                    await ws_manager.broadcast({
                        "type": "job_complete",
                        "job_id": job_id,
                        "status": final_status,
                        "progress": 100,
                        "warning": f"{len(failed_files)}개 파일 실패: {', '.join(failed_files)}"
                    })
            else:
                # All files succeeded
                print(f"[QUEUE] Job {job_id} completed successfully")
                update_job(
                    job_id,
                    status="완료",
                    progress=100,
                    perFileResults=per_file_results
                )
                
                await ws_manager.broadcast({
                    "type": "job_complete",
                    "job_id": job_id,
                    "status": "완료",
                    "progress": 100
                })
            
        except Exception as e:
            # Job failed
            error_msg = str(e)
            print(f"[QUEUE] ERROR: Job {job_id} failed: {error_msg}")
            import traceback
            traceback.print_exc()
            
            update_job(job_id, status="실패", progress=0)
            
            await ws_manager.broadcast({
                "type": "job_error",
                "job_id": job_id,
                "error": error_msg
            })

# Global queue instance
job_queue = JobQueue()
