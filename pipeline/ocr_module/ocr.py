"""
OCR processing module
Handles text extraction and image bbox extraction
"""
import re
from PIL import Image
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))
import config
from ocr_module.load_model import load_model
from preprocessing_module.img import load_image
from ocr_module.streams import TextCallbackStreamer

def process_image(model, processor, image, device, dtype, stream_callback=None):
    """
    Run OCR on a single image
    
    Args:
        model: Loaded OCR model
        processor: Model processor
        image: PIL Image object
        device: Device to run on
        dtype: Data type
        
    Returns:
        str: OCR output text (may include bbox coordinates)
    """
    # Prepare conversation input
    conversation = [{
        "role": "user",
        "content": [{"type": "image", "image": image}]
    }]
    
    # Apply chat template
    inputs = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    
    # Move inputs to device
    inputs = {
        k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device) 
        for k, v in inputs.items()
    }
    
    # Generate output
    gen_kwargs = {
        "max_new_tokens": config.MAX_NEW_TOKENS,
        "temperature": config.TEMPERATURE,
        "top_p": config.TOP_P
    }
    
    # Add streamer if callback provided
    if stream_callback:
        streamer = TextCallbackStreamer(processor, stream_callback, skip_prompt=True)
        gen_kwargs["streamer"] = streamer
        
    output_ids = model.generate(
        **inputs,
        **gen_kwargs
    )
    
    # Decode output
    generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
    output_text = processor.decode(generated_ids, skip_special_tokens=True)
    
    return output_text

def parse_bbox_output(output_text):
    """
    Parse bbox model output to extract text and image coordinates
    
    The bbox model outputs in format: ![image](image_N.png)x1,y1,x2,y2
    where coordinates are normalized to [0, 1000]
    
    Args:
        output_text: Raw output from bbox model
        
    Returns:
        tuple: (clean_text, bbox_list)
            clean_text: Text with bbox coordinates removed
            bbox_list: List of dicts with keys: image_ref, x1, y1, x2, y2
    """
    bbox_list = []
    
    # Pattern to match ![image](image_N.png)x1,y1,x2,y2
    # Enhanced to allow optional spaces around comma
    pattern = r'!\[image\]\(([^)]+)\)\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)'
    
    def replace_bbox(match):
        image_ref = match.group(1)
        x1, y1, x2, y2 = map(int, match.groups()[1:])
        
        # Log found bbox
        print(f"[OCR_DEBUG] Parsed bbox: ref={image_ref}, coords=({x1},{y1},{x2},{y2})")
        
        bbox_list.append({
            'image_ref': image_ref,
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2
        })
        
        # Replace with just the image reference (will be updated later)
        return f'![image]({image_ref})'
    
    # Remove bbox coordinates but keep image references
    clean_text = re.sub(pattern, replace_bbox, output_text)
    
    return clean_text, bbox_list

def denormalize_coordinates(bbox, original_width, original_height):
    """
    Convert normalized bbox coordinates [0-1000] to pixel coordinates
    
    Args:
        bbox: Dict with x1, y1, x2, y2 in [0-1000] range
        original_width: Original image width in pixels
        original_height: Original image height in pixels
        
    Returns:
        tuple: (x1, y1, x2, y2) in pixel coordinates
    """
    x1 = int(bbox['x1'] * original_width / config.BBOX_COORD_MAX)
    y1 = int(bbox['y1'] * original_height / config.BBOX_COORD_MAX)
    x2 = int(bbox['x2'] * original_width / config.BBOX_COORD_MAX)
    y2 = int(bbox['y2'] * original_height / config.BBOX_COORD_MAX)
    
    return (x1, y1, x2, y2)

def extract_image_regions(original_image, bbox_list, output_dir, prefix=""):
    """
    Crop image regions based on bbox coordinates and save them
    
    Args:
        original_image: PIL Image object (original input)
        bbox_list: List of bbox dicts from parse_bbox_output
        output_dir: Directory to save cropped images
        prefix: Prefix for saved image filenames
        
    Returns:
        dict: Mapping from old image_ref to new saved image path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    width, height = original_image.size
    image_mapping = {}
    
    print(f"[OCR_DEBUG] Extracting {len(bbox_list)} regions to {output_dir}")
    print(f"[OCR_DEBUG] Image prefix: '{prefix}'")
    
    for i, bbox in enumerate(bbox_list):
        # Denormalize coordinates
        x1, y1, x2, y2 = denormalize_coordinates(bbox, width, height)
        
        # Crop image region
        cropped = original_image.crop((x1, y1, x2, y2))
        
        # Save cropped image
        image_filename = f"{prefix}image_{i+1}.png"
        image_path = output_dir / image_filename
        cropped.save(image_path)
        
        # Map old reference to new filename
        image_mapping[bbox['image_ref']] = image_filename
    
    return image_mapping

def extract_text_only(image_path, model=None, processor=None, device=None, stream_callback=None):
    """
    Extract text from image using text-only model
    
    Args:
        image_path: Path to image file
        model: Pre-loaded model (optional)
        processor: Pre-loaded processor (optional)
        device: Device to run on (optional)
        
    Returns:
        str: Extracted text
    """
    # Load model if not provided
    if model is None or processor is None:
        model, processor, device, dtype = load_model(model_type="text_only", device=device)
    else:
        # If model provided, use config defaults if device not specified
        if device is None:
            device = config.DEVICE
        dtype = config.DTYPE
    
    # Load image
    image = load_image(image_path)
    
    # Process
    text = process_image(model, processor, image, device, dtype, stream_callback=stream_callback)
    
    return text

def extract_text_with_images(image_path, output_dir, model=None, processor=None, image_prefix="", device=None, stream_callback=None):
    """
    Extract text and images from document using bbox model
    
    Args:
        image_path: Path to image file
        output_dir: Directory to save extracted images
        model: Pre-loaded model (optional)
        processor: Pre-loaded processor (optional)
        image_prefix: Prefix for saved image filenames
        device: Device to run on (optional)
        
    Returns:
        tuple: (text, image_mapping)
            text: Extracted text with image references
            image_mapping: Dict mapping old refs to new image filenames
    """
    # Load model if not provided
    if model is None or processor is None:
        model, processor, device, dtype = load_model(model_type="text_img", device=device)
    else:
        if device is None:
            device = config.DEVICE
        dtype = config.DTYPE
    
    # Load image
    image = load_image(image_path)
    
    # Process
    raw_output = process_image(model, processor, image, device, dtype, stream_callback=stream_callback)
    print(f"[OCR_DEBUG] Raw output: {raw_output[:100]}...")
    
    # Parse bbox output
    clean_text, bbox_list = parse_bbox_output(raw_output)
    print(f"[OCR_DEBUG] Found {len(bbox_list)} bboxes")
    
    # Extract and save image regions
    if bbox_list:
        image_mapping = extract_image_regions(image, bbox_list, output_dir, prefix=image_prefix)
        
        # Update text with new image references
        for old_ref, new_ref in image_mapping.items():
            clean_text = clean_text.replace(old_ref, new_ref)
    else:
        image_mapping = {}
    
    return clean_text, image_mapping
