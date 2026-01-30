"""
Input validation and file handling module
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))
from config import SUPPORTED_FORMATS, SUPPORTED_IMAGE_FORMATS, SUPPORTED_PDF_FORMAT

def normalize_path(path):
    """
    Normalize file path (handle drag-and-drop paths, quotes, etc.)
    
    Args:
        path: Path string
        
    Returns:
        Path: Normalized Path object
    """
    # Remove quotes if present
    path = str(path).strip().strip('"').strip("'")
    return Path(path)

def validate_input_file(path):
    """
    Check if file exists and format is supported
    
    Args:
        path: Path to input file
        
    Returns:
        bool: True if valid, raises exception otherwise
    """
    path = normalize_path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported file format: {path.suffix}. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )
    
    return True

def get_file_type(path):
    """
    Detect if file is image or PDF based on extension
    
    Args:
        path: Path to file
        
    Returns:
        str: 'image' or 'pdf'
    """
    path = Path(path)
    suffix = path.suffix.lower()
    
    if suffix in SUPPORTED_IMAGE_FORMATS:
        return 'image'
    elif suffix in SUPPORTED_PDF_FORMAT:
        return 'pdf'
    else:
        raise ValueError(f"Unknown file type: {suffix}")

def get_supported_files(directory, recursive=False):
    """
    Get all supported files in a directory
    
    Args:
        directory: Path to directory
        recursive: Whether to search recursively
        
    Returns:
        list: List of Path objects
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    files = []
    pattern = "**/*" if recursive else "*"
    
    for path in directory.glob(pattern):
        if path.is_file() and path.suffix.lower() in SUPPORTED_FORMATS:
            files.append(path)
    
    return sorted(files)
