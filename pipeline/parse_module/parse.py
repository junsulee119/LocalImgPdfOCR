"""
Parse module for CLI argument and input parsing
"""
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from pipeline.input import validate_input_file, get_supported_files, normalize_path
from logger import logger

def parse_input_files(paths):
    """
    Parse input file paths (can be files or directories)
    
    Args:
        paths: List of path strings
        
    Returns:
        list: List of valid file Path objects
    """
    files = []
    
    for path_str in paths:
        path = normalize_path(path_str)
        
        if path.is_file():
            try:
                validate_input_file(path)
                files.append(path)
            except ValueError as e:
                logger.warning(f"Skipping {path}: {e}")
        elif path.is_dir():
            # Get all supported files in directory
            dir_files = get_supported_files(path, recursive=False)
            files.extend(dir_files)
        else:
            logger.warning(f"Path not found: {path}")
    
    return files

def expand_wildcards(pattern):
    """
    Expand wildcard patterns like '*.pdf'
    
    Args:
        pattern: Glob pattern string
        
    Returns:
        list: List of matching Path objects
    """
    from pathlib import Path
    
    # Use current directory if no path specified
    if '/' not in pattern and '\\' not in pattern:
        pattern = f"./{pattern}"
    
    path_obj = Path(pattern)
    parent = path_obj.parent
    pattern_name = path_obj.name
    
    if parent.exists():
        matches = list(parent.glob(pattern_name))
        return [m for m in matches if m.is_file()]
    
    return []

def filter_supported_files(paths):
    """
    Filter out unsupported file types
    
    Args:
        paths: List of Path objects
        
    Returns:
        list: List of supported file Path objects
    """
    from pipeline.input import validate_input_file
    
    supported = []
    for path in paths:
        try:
            validate_input_file(path)
            supported.append(path)
        except (ValueError, FileNotFoundError):
            pass  # Skip unsupported files
    
    return supported
