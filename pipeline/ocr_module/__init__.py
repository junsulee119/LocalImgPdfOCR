# OCR module
from .load_model import load_model, detect_device, clear_model_cache
from .ocr import (
    process_image,
    extract_text_only,
    extract_text_with_images,
    parse_bbox_output,
    extract_image_regions
)

__all__ = [
    'load_model',
    'detect_device',
    'clear_model_cache',
    'process_image',
    'extract_text_only',
    'extract_text_with_images',
    'parse_bbox_output',
    'extract_image_regions'
]
