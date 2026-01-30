"""
Model loading and device management module
"""
import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config
from logger import logger, Color

# Global model cache (singleton pattern)
_MODEL_CACHE = {}

def detect_device():
    """
    Auto-detect best available device (CUDA > MPS > CPU)
    
    Returns:
        tuple: (device_string, dtype)
    """
    logger.debug("Checking available devices...")
    logger.debug(f"torch.cuda.is_available() = {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        device = "cuda"
        dtype = torch.bfloat16
        gpu_name = torch.cuda.get_device_name(0)
        logger.success(f"CUDA detected: {gpu_name}")
    elif torch.backends.mps.is_available():
        device = "mps"
        dtype = torch.float32  # MPS doesn't support bfloat16
        logger.success("MPS (Apple Silicon) detected")
    else:
        device = "cpu"
        dtype = torch.float32
        logger.warning("No GPU detected, using CPU")
    
    logger.info(f"Selected device: {device.upper()}")
    return device, dtype

def load_model(model_type="text_only", device=None, dtype=None):
    """
    Load OCR model and processor with caching
    
    Args:
        model_type: "text_only" or "text_img"
        device: Device to load model on (None for auto-detect)
        dtype: Data type for model (None for auto-detect)
        
    Returns:
        tuple: (model, processor, device, dtype)
    """
    # Auto-detect device if not specified
    if device is None:
        device, dtype = detect_device()
    elif dtype is None:
        # Device specified but dtype not - infer default dtype for device
        if device == "cpu":
            dtype = torch.float32
        elif device == "mps":
            dtype = torch.float32
        elif device == "cuda":
            dtype = torch.bfloat16
        else:
            dtype = torch.float32
    
    # Check cache
    cache_key = f"{model_type}_{device}_{dtype}"
    if cache_key in _MODEL_CACHE:
        logger.info(f"Using cached model: {model_type} on {device}")
        return _MODEL_CACHE[cache_key]
    
    # Get model path
    model_path = config.MODEL_PATHS.get(model_type)
    if model_path is None:
        raise ValueError(f"Unknown model type: {model_type}. Use 'text_only' or 'text_img'")
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. "
            f"Please ensure the model is downloaded to the models directory."
        )
    
    logger.info(f"Loading {model_type} model on {device.upper()}...")
    logger.debug(f"Model path: {model_path}")
    
    try:
        # Load model and processor
        model = LightOnOcrForConditionalGeneration.from_pretrained(
            str(model_path),
            torch_dtype=dtype
        ).to(device)
        
        processor = LightOnOcrProcessor.from_pretrained(str(model_path))
        
        # Test CUDA with a small operation to catch kernel errors early
        if device == "cuda":
            try:
                test_tensor = torch.tensor([1.0], device=device, dtype=dtype)
                _ = test_tensor + test_tensor  # Simple operation to trigger kernel loading
                logger.success("CUDA test passed")
            except RuntimeError as cuda_err:
                if "no kernel image is available" in str(cuda_err):
                    logger.warning("CUDA kernel error detected")
                    logger.warning("Your GPU may be too new for this PyTorch build")
                    logger.warning("Falling back to CPU mode...")
                    
                    # Reload model on CPU
                    device = "cpu"
                    dtype = torch.float32
                    model = LightOnOcrForConditionalGeneration.from_pretrained(
                        str(model_path),
                        torch_dtype=dtype
                    ).to(device)
                    
                    config.DEVICE = device
                    config.DTYPE = dtype
                    cache_key = f"{model_type}_{device}_{dtype}"
                else:
                    raise
        
        # Cache the loaded model
        _MODEL_CACHE[cache_key] = (model, processor, device, dtype)
        
        # Update global config
        config.DEVICE = device
        config.DTYPE = dtype
        
        logger.success(f"Model loaded successfully on {device.upper()}")
        return model, processor, device, dtype
        
    except Exception as e:
        raise RuntimeError(f"Failed to load model: {e}")

def clear_model_cache():
    """Clear the model cache to free memory"""
    global _MODEL_CACHE
    _MODEL_CACHE = {}
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("Model cache cleared")
