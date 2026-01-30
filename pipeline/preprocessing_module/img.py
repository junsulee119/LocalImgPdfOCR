"""
Image preprocessing module
Handles loading and validation of image files.
Actual preprocessing (resize, normalize) is handled by the model's processor.
"""
from PIL import Image
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import SUPPORTED_IMAGE_FORMATS

def validate_image(path):
    """
    Check if file is a supported image format and readable
    
    Args:
        path: Path to image file
        
    Returns:
        bool: True if valid, raises exception otherwise
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    
    if path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        raise ValueError(
            f"Unsupported image format: {path.suffix}. "
            f"Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
        )
    
    # Try to open the image to verify it's valid
    try:
        with Image.open(path) as img:
            img.verify()  # Verify it's a valid image
        return True
    except Exception as e:
        raise ValueError(f"Invalid or corrupted image file: {path}. Error: {e}")

def load_image(path):
    """
    Load an image file and return PIL Image object
    
    Image preprocessing (resize to longest_edge=1540px, normalization, etc.) 
    is handled automatically by the model's processor.
    
    Args:
        path: Path to image file
        
    Returns:
        PIL.Image: Loaded image in RGB mode
    """
    validate_image(path)
    
    # Load and convert to RGB (processor expects RGB)
    img = Image.open(path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    return img

def get_image_dimensions(path):
    """
    Get dimensions of an image file
    
    Args:
        path: Path to image file
        
    Returns:
        tuple: (width, height)
    """
    with Image.open(path) as img:
        return img.size
