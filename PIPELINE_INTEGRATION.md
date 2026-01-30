# Pipeline Integration Guide

This guide shows how to integrate the OCR application into your data pipelines programmatically.

## Python API

### Basic OCR Processing

```python
from pathlib import Path
from pipeline.ocr_module import load_model, extract_text_only, extract_text_with_images

# Load model (do this once, reuse across multiple files)
model, processor, device, dtype = load_model(model_type="text_only")

# Process a single image - text only
text = extract_text_only(
    "path/to/image.png",
    model=model,
    processor=processor
)
print(text)

# Process with image extraction
text, image_mapping = extract_text_with_images(
    "path/to/document.png",
    output_dir="output/images",
    model=model,
    processor=processor
)
# image_mapping: dict of extracted image filenames
```

### PDF Processing

```python
from pipeline.preprocessing_module import pdf_to_images, parse_page_selection

# Convert entire PDF to images
page_images = pdf_to_images("document.pdf")
# Returns: list of (page_num, PIL.Image) tuples

# Convert specific pages
page_selection = parse_page_selection("1-5,10,15-20")  # Returns [0, 1, 2, 3, 4, 9, 14, 15, ...19]
page_images = pdf_to_images("document.pdf", page_numbers=page_selection)

# Process each page
for page_num, image in page_images:
    # Save temp image or process directly
    temp_path = f"temp_page_{page_num}.png"
    image.save(temp_path)
    text = extract_text_only(temp_path, model=model, processor=processor)
    # Save or process text
```

### Batch Processing

```python
from pipeline.job_module import create_batch_jobs, process_batch
from pipeline.ocr_module import load_model

# Load model once for all jobs
model, processor, device, dtype = load_model("text_img")

# Create jobs for multiple files
file_paths = [
    Path("file1.pdf"),
    Path("file2.png"),
    Path("file3.jpg")
]

jobs, queue_timestamp, output_dir = create_batch_jobs(
    file_paths=file_paths,
    model_type="text_img",
    page_selection=None,  # Or "1-10" for PDFs
    model=model,
    processor=processor
)

# Process with callback
def on_job_complete(job, index, total):
    print(f"[{index}/{total}] {job.file_path.name}: {job.status}")
    if job.error:
        print(f"  Error: {job.error}")

completed, failed = process_batch(jobs, callback=on_job_complete)
print(f"Output directory: {output_dir}")
```

### Custom Job Processing

```python
from pipeline.job_module import Job, JobStatus

# Create a custom job
job = Job(
    file_path="document.pdf",
    output_dir="output/custom",
    model_type="text_only",
    page_selection="1-5",
    model=model,
    processor=processor
)

# Execute
success = job.execute()

if success:
    print(f"Output files: {job.output_files}")
    print(f"Duration: {(job.end_time - job.start_time).total_seconds()}s")
else:
    print(f"Error: {job.error}")
```

## Input Validation

```python
from pipeline.input import validate_input_file, get_file_type, get_supported_files

# Validate single file
try:
    validate_input_file("document.pdf")
    file_type = get_file_type("document.pdf")  # 'pdf' or 'image'
    print(f"Valid {file_type} file")
except (FileNotFoundError, ValueError) as e:
    print(f"Invalid: {e}")

# Get all supported files from directory
files = get_supported_files("path/to/directory", recursive=True)
for file in files:
    print(file)
```

## Output Handling

```python
from pipeline.output import (
    save_text_only,
    save_markdown_with_images,
    create_job_output_dir,
    generate_metadata
)
from pipeline.config import get_queue_timestamp

# Create output directory
timestamp = get_queue_timestamp()  # e.g., "20260128_194500"
output_dir = create_job_output_dir(timestamp)

# Save text-only output
save_text_only(text, output_dir / "result.md")

# Save with images (text already has image references updated)
save_markdown_with_images(text, output_dir / "result.md")

# Generate metadata
metadata = {
    'input_file': 'document.pdf',
    'model_type': 'text_img',
    'pages_processed': 10,
    'duration_seconds': 45.2
}
generate_metadata(metadata, output_dir)
```

## Advanced: Custom Preprocessing

```python
from PIL import Image
from pipeline.preprocessing_module import load_image, validate_image

# Custom image loading with preprocessing
def custom_load_image(path):
    # Validate first
    validate_image(path)
    
    # Load with PIL
    img = Image.open(path)
    
    # Custom preprocessing (rotation, cropping, etc.)
    if img.width > img.height:
        img = img.rotate(270, expand=True)
    
    # Convert to RGB (required)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    return img

# Use with OCR
img = custom_load_image("rotated_doc.png")
# Save temporarily or process directly...
```

## Configuration

Access and modify configuration programmatically:

```python
from pipeline import config

# View current config
print(f"Models: {config.MODEL_PATHS}")
print(f"Device: {config.DEVICE}")
print(f"Supported formats: {config.SUPPORTED_FORMATS}")

# Modify settings (before loading model)
config.MAX_NEW_TOKENS = 8192  # Increase for longer documents
config.PDF_RENDER_DPI = 300   # Higher quality PDF rendering
```

## Error Handling

```python
from pipeline.ocr_module import load_model, extract_text_only

try:
    model, processor, device, dtype = load_model("text_only")
    text = extract_text_only("image.png", model=model, processor=processor)
except FileNotFoundError as e:
    print(f"File or model not found: {e}")
except ValueError as e:
    print(f"Invalid input: {e}")
except RuntimeError as e:
    print(f"Model loading failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Load models once**: Reuse model instances across multiple files
2. **Batch similar files**: Process all text-only or all text+img together
3. **Use GPU**: Ensure CUDA is available; use `detect_device()` to verify
4. **Adjust max_tokens**: Set `config.MAX_NEW_TOKENS` based on document length
5. **Monitor memory**: Clear model cache with `clear_model_cache()` if needed

```python
from pipeline.ocr_module import clear_model_cache

# After processing large batch
clear_model_cache()
```

## Example: Custom Pipeline

```python
import sys
from pathlib import Path
from pipeline.ocr_module import load_model, extract_text_only
from pipeline.preprocessing_module import pdf_to_images
from pipeline.output import create_job_output_dir, save_text_only, generate_metadata
from pipeline.config import get_queue_timestamp
from datetime import datetime

def process_directory(input_dir, output_base="output"):
    """Process all PDFs in a directory"""
    input_dir = Path(input_dir)
    all_pdfs = list(input_dir.glob("*.pdf"))
    
    if not all_pdfs:
        print("No PDFs found")
        return
    
    # Load model
    print("Loading model...")
    model, processor, device, dtype = load_model("text_only")
    
    # Create output directory
    timestamp = get_queue_timestamp()
    output_dir = create_job_output_dir(timestamp)
    
    start_time = datetime.now()
    processed = 0
    
    for pdf_path in all_pdfs:
        print(f"Processing {pdf_path.name}...")
        
        try:
            # Convert PDF to images
            page_images = pdf_to_images(pdf_path)
            
            # Process each page
            for page_num, image in page_images:
                # Save temp image
                temp_img = output_dir / f"temp_{pdf_path.stem}_p{page_num}.png"
                image.save(temp_img)
                
                # OCR
                text = extract_text_only(temp_img, model=model, processor=processor)
                
                # Save result
                output_file = output_dir / f"{pdf_path.stem}_page_{page_num+1}.md"
                save_text_only(text, output_file)
                
                # Cleanup
                temp_img.unlink()
            
            processed += 1
            
        except Exception as e:
            print(f"Error processing {pdf_path.name}: {e}")
    
    # Generate summary metadata
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    metadata = {
        'total_files': len(all_pdfs),
        'processed': processed,
        'failed': len(all_pdfs) - processed,
        'duration_seconds': duration,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat()
    }
    generate_metadata(metadata, output_dir)
    
    print(f"\nComplete! Processed {processed}/{len(all_pdfs)} files")
    print(f"Output: {output_dir}")
    print(f"Duration: {duration:.1f}s")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        process_directory(sys.argv[1])
    else:
        print("Usage: python pipeline_example.py <input_directory>")
```

## Further Reading

- See `pipeline/config.py` for all configuration options
- Check `README.md` for CLI and GUI usage
- Review individual module files for detailed docstrings
