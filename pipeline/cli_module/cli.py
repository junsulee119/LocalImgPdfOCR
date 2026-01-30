"""
CLI module for OCR application
Provides command-line interface with colored output and formatted logging
"""
import argparse
from pathlib import Path
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from parse_module import parse_input_files
from ocr_module import load_model, detect_device
from job_module import create_batch_jobs, process_batch
from config import get_queue_timestamp
from logger import logger, Color, ProgressBar, format_duration

def create_parser():
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(
        description='OCR Application - Extract text from images and PDFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single image (text-only mode)
  python -m pipeline.cli_module process image.png
  
  # Process with text+image mode
  python -m pipeline.cli_module process document.pdf --mode text-img
  
  # Process specific PDF pages
  python -m pipeline.cli_module process document.pdf --pages "1-5,7,10-12"
  
  # Batch process multiple files
  python -m pipeline.cli_module process *.pdf *.jpg
  
  # Force CPU mode
  python -m pipeline.cli_module process image.png --device cpu
"""
    )
    
    # Main commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process files with OCR')
    process_parser.add_argument(
        'files',
        nargs='+',
        help='Input files or directories to process'
    )
    process_parser.add_argument(
        '--mode',
        choices=['text-only', 'text-img'],
        default='text-only',
        help='Processing mode (default: text-only)'
    )
    process_parser.add_argument(
        '--pages',
        type=str,
        default=None,
        help='PDF page selection (e.g., "1-5,7,10-12"). Applies to all PDF files.'
    )
    process_parser.add_argument(
        '--device',
        choices=['auto', 'cuda', 'cpu', 'mps'],
        default='auto',
        help='Device to use (default: auto-detect)'
    )
    process_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    return parser

def run_process(args):
    """Execute the process command"""
    logger.verbose = args.verbose
    start_time = datetime.now()
    
    # Print system information
    from system_info import print_system_info
    print_system_info(logger)
    
    # Header
    logger.header("OCR BATCH PROCESSING")
    logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {'Text Only' if args.mode == 'text-only' else 'Text + Images'}")
    if args.pages:
        logger.info(f"PDF Pages: {args.pages}")
    print()
    
    # Parse input files
    logger.section("Parsing Input Files")
    logger.indent()
    logger.debug(f"Input arguments: {args.files}")
    files = parse_input_files(args.files)
    
    if not files:
        logger.error("No valid files found to process")
        logger.dedent()
        return 1
    
    logger.success(f"Found {len(files)} file(s) to process")
    if logger.verbose:
        for i, f in enumerate(files, 1):
            logger.debug(f"{i}. {f.name}", indent=1)
    logger.dedent()
    print()
    
    # Device detection
    logger.section("Device Configuration")
    logger.indent()
    logger.debug("Scanning available compute devices...")
    if args.device == 'auto':
        device, dtype = detect_device()
    else:
        device = args.device
        import torch
        dtype = torch.bfloat16 if device == 'cuda' else torch.float32
        logger.info(f"Using specified device: {device.upper()}")
    logger.debug(f"Data type: {dtype}")
    logger.dedent()
    print()
    
    # Load model
    logger.section("Loading Model")
    logger.indent()
    model_type = "text_only" if args.mode == "text-only" else "text_img"
    model, processor, device, dtype = load_model(model_type, device=device, dtype=dtype)
    logger.dedent()
    print()
    
    # Create batch jobs
    logger.section("Creating Job Queue")
    logger.indent()
    logger.debug(f"Generating job queue for {len(files)} files...")
    jobs, queue_timestamp, output_base_dir = create_batch_jobs(
        files,
        model_type=model_type,
        page_selection=args.pages,
        model=model,
        processor=processor
    )
    logger.info(f"Queue ID: {queue_timestamp}")
    logger.info(f"Jobs created: {len(jobs)}")
    logger.info(f"Output directory: {output_base_dir}")
    logger.dedent()
    print()
    
    # Process jobs with custom progress display
    logger.section("Processing Jobs")
    logger.indent()
    
    processed = 0
    completed_count = 0
    failed_count = 0
    
    progress = ProgressBar(len(jobs), prefix='Progress', length=50)
    
    def progress_callback(job, index, total):
        nonlocal processed, completed_count, failed_count
        processed += 1
        
        logger.debug(f"Starting job {index + 1}/{total}: {job.file_path.name}", indent=1)
        progress.update()
        
        if job.status == "completed":
            completed_count += 1
            logger.success(f"{job.file_path.name}", indent=1)
            if args.verbose and job.output_files:
                logger.indent()
                logger.indent()
                for output_file in job.output_files:
                    logger.debug(f"→ {output_file.name}")
                logger.dedent()
                logger.dedent()
        else:
            failed_count += 1
            logger.error(f"{job.file_path.name}", indent=1)
            if job.error:
                logger.indent()
                logger.indent()
                logger.plain(f"Error: {job.error}")
                logger.dedent()
                logger.dedent()
    
    logger.info("Starting batch processing...")
    completed, failed = process_batch(jobs, callback=progress_callback)
    logger.dedent()
    print()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.header("PROCESSING COMPLETE")
    logger.indent()
    
    # Stats
    logger.colored(f"Total Jobs:  {len(jobs)}", Color.CYAN, bold=True)
    logger.colored(f"Completed:   {completed}/{len(jobs)}", 
                   Color.BRIGHT_GREEN if failed == 0 else Color.CYAN, bold=True)
    if failed > 0:
        logger.colored(f"Failed:      {failed}/{len(jobs)}", Color.BRIGHT_RED, bold=True)
    logger.colored(f"Duration:    {format_duration(duration)}", Color.CYAN, bold=True)
    logger.colored(f"Output:      {output_base_dir}", Color.BLUE, bold=True)
    logger.colored(f"Finished:    {end_time.strftime('%Y-%m-%d %H:%M:%S')}", Color.CYAN, bold=True)
    
    logger.dedent()
    print()
    
    return 0 if failed == 0 else 1

def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    if args.command == 'process':
        return run_process(args)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
