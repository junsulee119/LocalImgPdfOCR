"""
Single job processing
Represents one file to be processed
"""
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent))
from input import get_file_type
from preprocessing_module import load_image, pdf_to_images, parse_page_selection
from ocr_module import extract_text_only, extract_text_with_images
from output import (
    save_text_only, 
    save_markdown_with_images, 
    get_output_filename,
    generate_metadata
)
from utils import ensure_dir
from logger import logger

class JobStatus:
    """Job status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    """
    Represents a single OCR job for one file
    """
    
    def __init__(self, file_path, output_dir, model_type="text_only", 
                 page_selection=None, model=None, processor=None):
        """
        Initialize a job
        
        Args:
            file_path: Path to input file
            output_dir: Directory for output
            model_type: "text_only" or "text_img"
            page_selection: For PDFs, page selection string (e.g., "1-5,7")
            model: Pre-loaded model (optional)
            processor: Pre-loaded processor (optional)
        """
        self.file_path = Path(file_path)
        self.output_dir = Path(output_dir)
        self.model_type = model_type
        self.page_selection = page_selection
        self.model = model
        self.processor = processor
        
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.error = None
        self.start_time = None
        self.end_time = None
        self.output_files = []
        
    def execute(self):
        """
        Execute the job
        
        Returns:
            bool: True if successful, False otherwise
        """
        self.status = JobStatus.PROCESSING
        self.start_time = datetime.now()
        self.progress = 0.0
        
        try:
            file_type = get_file_type(self.file_path)
            ensure_dir(self.output_dir)
            
            if file_type == 'image':
                self._process_image(self.file_path)
            elif file_type == 'pdf':
                self._process_pdf(self.file_path)
            
            self.status = JobStatus.COMPLETED
            self.progress = 1.0
            self.end_time = datetime.now()
            
            # Generate metadata
            metadata = {
                'input_file': str(self.file_path),
                'model_type': self.model_type,
                'status': self.status,
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration_seconds': (self.end_time - self.start_time).total_seconds(),
                'output_files': [str(f) for f in self.output_files]
            }
            generate_metadata(metadata, self.output_dir)
            
            return True
            
        except Exception as e:
            self.status = JobStatus.FAILED
            self.error = str(e)
            self.end_time = datetime.now()
            logger.error(f"Job failed for {self.file_path.name}: {e}")
            return False
    
    def _process_image(self, image_path):
        """Process a single image file"""
        output_filename = get_output_filename(image_path)
        output_md_path = self.output_dir / f"{output_filename}.md"
        
        if self.model_type == "text_only":
            text = extract_text_only(
                image_path,
                model=self.model,
                processor=self.processor
            )
            save_text_only(text, output_md_path)
            self.output_files.append(output_md_path)
            
        else:  # text_img
            # Use unique prefix
            img_prefix = f"{Path(image_path).stem}_"
            text, image_mapping = extract_text_with_images(
                image_path,
                self.output_dir,
                model=self.model,
                processor=self.processor,
                image_prefix=img_prefix
            )
            save_markdown_with_images(text, output_md_path)
            self.output_files.append(output_md_path)
            
            # Add extracted images to output files
            for img_file in image_mapping.values():
                self.output_files.append(self.output_dir / img_file)
    
    def _process_pdf(self, pdf_path):
        """Process a PDF file (multiple pages)"""
        # Parse page selection
        if self.page_selection:
            page_numbers = parse_page_selection(self.page_selection)
        else:
            page_numbers = None  # All pages
        
        # Convert PDF to images
        page_images = pdf_to_images(pdf_path, page_numbers)
        total_pages = len(page_images)
        
        # Process each page
        for idx, (page_num, image) in enumerate(page_images):
            # Save image temporarily
            temp_image_path = self.output_dir / f"temp_page_{page_num}.png"
            image.save(temp_image_path)
            
            # Process the page
            output_filename = get_output_filename(pdf_path, page_num + 1)  # 1-indexed
            output_md_path = self.output_dir / f"{output_filename}.md"
            
            if self.model_type == "text_only":
                text = extract_text_only(
                    temp_image_path,
                    model=self.model,
                    processor=self.processor
                )
                save_text_only(text, output_md_path)
                self.output_files.append(output_md_path)
                
            else:  # text_img
                # Use unique prefix
                img_prefix = f"{Path(pdf_path).stem}_page_{page_num + 1}_"
                text, image_mapping = extract_text_with_images(
                    temp_image_path,
                    self.output_dir,
                    model=self.model,
                    processor=self.processor,
                    image_prefix=img_prefix
                )
                save_markdown_with_images(text, output_md_path)
                self.output_files.append(output_md_path)
                
                # Add extracted images
                for img_file in image_mapping.values():
                    self.output_files.append(self.output_dir / img_file)
            
            # Clean up temp image
            temp_image_path.unlink()
            
            # Update progress
            self.progress = (idx + 1) / total_pages
