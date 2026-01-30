"""
Output generation module
Handles markdown creation and image embedding
"""
from pathlib import Path
import json
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent))
from utils import ensure_dir

def create_job_output_dir(queue_timestamp):
    """
    Create output directory for a job queue
    
    Args:
        queue_timestamp: Timestamp string for the queue (YYYYMMDD_HHMMSS)
        
    Returns:
        Path: Created output directory
    """
    from config import get_output_dir
    output_dir = get_output_dir(queue_timestamp)
    return ensure_dir(output_dir)

def save_text_only(text, output_path):
    """
    Save OCR text as markdown file (text-only mode)
    
    Args:
        text: OCR extracted text
        output_path: Path to output markdown file
        
    Returns:
        Path: Path to saved file
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return output_path

def save_markdown_with_images(text, output_path):
    """
    Save OCR text with embedded image references (text+img mode)
    
    The text should already have image references updated by ocr.py
    Images should already be saved in the same directory
    
    Args:
        text: OCR text with image references
        output_path: Path to output markdown file
        
    Returns:
        Path: Path to saved file
    """
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return output_path

def generate_metadata(job_info, output_dir):
    """
    Create metadata JSON file for the job
    
    Args:
        job_info: Dict with job information
        output_dir: Directory to save metadata
        
    Returns:
        Path: Path to metadata file
    """
    output_dir = Path(output_dir)
    metadata_path = output_dir / "metadata.json"
    
    # Add timestamp if not present
    if 'timestamp' not in job_info:
        job_info['timestamp'] = datetime.now().isoformat()
    
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(job_info, f, indent=2, ensure_ascii=False)
    
    return metadata_path

def get_output_filename(input_path, page_num=None):
    """
    Generate output filename from input filename
    
    Args:
        input_path: Path to input file
        page_num: Page number for PDFs (optional, 1-indexed)
        
    Returns:
        str: Output filename (without extension)
    """
    input_path = Path(input_path)
    base_name = input_path.stem
    
    if page_num is not None:
        return f"{base_name}_page_{page_num}"
    else:
        return base_name
