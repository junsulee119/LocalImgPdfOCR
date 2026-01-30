"""
Central configuration for OCR application
"""
import os
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_BASE_DIR = PROJECT_ROOT / "output"

# Model configurations
MODEL_TEXT_ONLY = "LightOnOCR-2-1B"
MODEL_TEXT_IMG = "LightOnOCR-2-1B-bbox"

MODEL_PATHS = {
    "text_only": MODELS_DIR / MODEL_TEXT_ONLY,
    "text_img": MODELS_DIR / MODEL_TEXT_IMG
}

# Supported file formats
SUPPORTED_IMAGE_FORMATS = {
    '.png', '.jpg', '.jpeg', '.webp', 
    '.bmp', '.tiff', '.tif', '.gif'
}
SUPPORTED_PDF_FORMAT = {'.pdf'}
SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS | SUPPORTED_PDF_FORMAT

# Processing settings
PDF_RENDER_DPI = 200
PDF_RENDER_SCALE = 2.77  # 200 DPI / 72 = 2.77

# Model processor settings (from processor_config.json)
# The processor handles image preprocessing automatically with:
# - longest_edge: 1540px
# - do_resize: true
# - do_rescale: true (rescale_factor: 0.00392156862745098)
# - do_normalize: true
# - do_convert_rgb: true
# We let the processor handle all image transformations

# OCR generation settings
MAX_NEW_TOKENS = 4096
TEMPERATURE = 0.2
TOP_P = 0.9

# Bbox coordinate normalization
BBOX_COORD_MAX = 1000  # Coordinates are normalized to [0, 1000]

# Output settings
def get_queue_timestamp():
    """Generate timestamp for queue directory"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_output_dir(queue_timestamp=None):
    """Get output directory for a job queue"""
    if queue_timestamp is None:
        queue_timestamp = get_queue_timestamp()
    return OUTPUT_BASE_DIR / queue_timestamp

# Device settings (will be determined at runtime)
DEVICE = None  # Set by load_model module
DTYPE = None   # Set by load_model module
