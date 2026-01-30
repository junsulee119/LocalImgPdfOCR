"""
GUI module for OCR application with detailed logging
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import sys
import threading

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from input import validate_input_file, get_file_type
from ocr_module import load_model, detect_device
from job_module import create_batch_jobs, process_batch
from config import get_queue_timestamp
from logger import logger, Color

class OCRApp:
    """Main GUI application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Application")
        self.root.geometry("800x600")
        
        # Print detailed system info at startup
        print()
        from system_info import print_system_info
        print_system_info(logger)
        logger.section("Initializing GUI Application")
        logger.indent()
        
        # State
        self.files = []
        self.model_type = "text_only"
        self.device = None
        self.dtype = None
        self.processing = False
        
        # Auto-detect device on startup  
        logger.info("Auto-detecting compute device...")
        self.device, self.dtype = detect_device()
        logger.dedent()
        print()
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create GUI widgets"""
        # Top: Mode selector
        mode_frame = ttk.Frame(self.root, padding=10)
        mode_frame.pack(fill=tk.X)
        
        ttk.Label(mode_frame, text="Processing Mode:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value="text_only")
        ttk.Radiobutton(
            mode_frame, 
           text="Text Only", 
            variable=self.mode_var,
            value="text_only",
            command=self.on_mode_change
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="Text + Images",
            variable=self.mode_var,
            value="text_img",
            command=self.on_mode_change
        ).pack(side=tk.LEFT, padx=5)
        
        # PDF page selection
        pdf_frame = ttk.Frame(self.root, padding=10)
        pdf_frame.pack(fill=tk.X)
        
        ttk.Label(
            pdf_frame,
            text="PDF Pages:",
            font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        self.page_selection_var = tk.StringVar(value="")
        page_entry = ttk.Entry(
            pdf_frame,
            textvariable=self.page_selection_var,
            width=30
        )
        page_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            pdf_frame,
            text="(e.g., '1-5,7,10-12' or leave empty for all pages)",
            font=('Arial', 8),
            foreground='gray'
        ).pack(side=tk.LEFT, padx=5)
        
        # Middle: File list area with drag-and-drop
        files_frame = ttk.LabelFrame(self.root, text="Files to Process", padding=10)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File listbox
        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=('Arial', 10),
            selectmode=tk.MULTIPLE
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # Buttons for file management
        button_frame = ttk.Frame(files_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Add Files", command=self.add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Add Folder", command=self.add_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        
        # Bottom: Progress and controls
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Device indicator
        device_frame = ttk.Frame(bottom_frame)
        device_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(device_frame, text="Device:", font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        device_label = ttk.Label(
            device_frame,
            text=self.device.upper(),
            font=('Arial', 9, 'bold'),
            foreground='green' if self.device == 'cuda' else 'orange'
        )
        device_label.pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            bottom_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(
            bottom_frame,
            textvariable=self.status_var,
            font=('Arial', 9)
        )
        status_label.pack(fill=tk.X, pady=5)
        
        # Process button
        self.process_btn = ttk.Button(
            bottom_frame,
            text="Process Files",
            command=self.process_files,
            style='Accent.TButton'
        )
        self.process_btn.pack(pady=5)
        
    def on_mode_change(self):
        """Handle mode change"""
        self.model_type = self.mode_var.get()
        mode_name = "Text Only" if self.model_type == "text_only" else "Text + Images"
        logger.info(f"Mode changed to: {mode_name}")
        
    def add_files(self):
        """Add files via file dialog"""
        logger.section("Adding Files")
        logger.indent()
        
        filetypes = [
            ("All supported", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif *.pdf"),
            ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif *.gif"),
            ("PDF", "*.pdf"),
            ("All files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="Select files to process",
            filetypes=filetypes
        )
        
        added_count = 0
        for file_path in files:
            try:
                validate_input_file(file_path)
                if file_path not in self.files:
                    self.files.append(file_path)
                    self.file_listbox.insert(tk.END, Path(file_path).name)
                    logger.success(f"Added: {Path(file_path).name}")
                    added_count += 1
                else:
                    logger.warning(f"Already in list: {Path(file_path).name}")
            except Exception as e:
                logger.error(f"Invalid file: {Path(file_path).name}")
                logger.indent()
                logger.plain(f"Reason: {e}")
                logger.dedent()
                messagebox.showwarning("Invalid File", f"Could not add {file_path}:\n{e}")
        
        if added_count > 0:
            logger.info(f"Total files in queue: {len(self.files)}")
        logger.dedent()
        
        self.update_status()
        
    def add_folder(self):
        """Add all supported files from a folder"""
        from input import get_supported_files
        
        folder = filedialog.askdirectory(title="Select folder")
        if folder:
            try:
                files = get_supported_files(folder)
                added = 0
                for file_path in files:
                    file_str = str(file_path)
                    if file_str not in self.files:
                        self.files.append(file_str)
                        self.file_listbox.insert(tk.END, file_path.name)
                        added += 1
                
                if added > 0:
                    messagebox.showinfo("Files Added", f"Added {added} file(s) from folder")
                else:
                    messagebox.showinfo("No Files", "No new supported files found in folder")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Could not load folder:\n{e}")
        
        self.update_status()
        
    def remove_selected(self):
        """Remove selected files from list"""
        selected = self.file_listbox.curselection()
        if selected:
            for index in reversed(selected):
                filename = Path(self.files[index]).name
                logger.warning(f"Removed: {filename}")
                self.file_listbox.delete(index)
                del self.files[index]
            logger.info(f"Total files in queue: {len(self.files)}")
            print()
        
        self.update_status()
        
    def clear_all(self):
        """Clear all files"""
        count = len(self.files)
        if count > 0:
            logger.warning(f"Cleared all {count} files from queue")
            print()
        self.files.clear()
        self.file_listbox.delete(0, tk.END)
        self.update_status()
        
    def update_status(self):
        """Update status label"""
        count = len(self.files)
        if count == 0:
            self.status_var.set("Ready - No files selected")
        else:
            self.status_var.set(f"Ready - {count} file(s) queued")
        
    def process_files(self):
        """Process all files in the queue"""
        if not self.files:
            messagebox.showwarning("No Files", "Please add files to process")
            return
        
        if self.processing:
            messagebox.showwarning("Processing", "Already processing files")
            return
        
        # Log processing start
        logger.header("PROCESS FILES INITIATED")
        logger.indent()
        logger.info(f"Total files: {len(self.files)}")
        logger.info(f"Mode: {'Text Only' if self.model_type == 'text_only' else 'Text + Images'}")
        page_sel = self.page_selection_var.get().strip()
        if page_sel:
            logger.info(f"PDF Pages: {page_sel}")
        logger.dedent()
        print()
        
        # Run processing in a separate thread to keep GUI responsive
        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()
        
    def _process_thread(self):
        """Process files in background thread"""
        self.processing = True
        self.process_btn.config(state='disabled')
        
        try:
            # Update status
            self.status_var.set(f"Loading {self.model_type} model...")
            self.progress_var.set(0)
            
            # Load model
            model, processor, device, dtype = load_model(
                model_type=self.model_type,
                device=self.device,
                dtype=self.dtype
            )
            
            # Create jobs
            self.status_var.set("Creating job queue...")
            
            # Get page selection (only applies to PDFs)
            page_selection = self.page_selection_var.get().strip()
            if not page_selection:
                page_selection = None  # Process all pages
            
            jobs, queue_timestamp, output_base_dir = create_batch_jobs(
                [Path(f) for f in self.files],
                model_type=self.model_type,
                page_selection=page_selection,
                model=model,
                processor=processor
            )
            
            total = len(jobs)
            completed_count = 0
            
            def progress_callback(job, index, total):
                nonlocal completed_count
                completed_count += 1
                progress = (completed_count / total) * 100
                self.progress_var.set(progress)
                self.status_var.set(f"Processing ({completed_count}/{total}): {job.file_path.name}")
            
            # Process
            self.status_var.set("Processing files...")
            completed, failed = process_batch(jobs, callback=progress_callback)
            
            # Show results
            self.root.after(0, lambda: self._show_results(completed, failed, output_base_dir))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Processing error: {error_msg}")
            print()
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Processing failed:\n{msg}"))
        finally:
            self.processing = False
            self.root.after(0, lambda: self.process_btn.config(state='normal'))
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, self.update_status)
    
    def _show_results(self, completed, failed, output_dir):
        """Show processing results"""
        total = completed + failed
        
        msg = f"Processing Complete!\n\n"
        msg += f"Completed: {completed}/{total}\n"
        msg += f"Failed: {failed}/{total}\n\n"
        msg += f"Output directory:\n{output_dir}"
        
        if failed == 0:
            messagebox.showinfo("Success", msg)
        else:
            messagebox.showwarning("Completed with Errors", msg)
        
        # Ask if user wants to clear the queue
        if messagebox.askyesno("Clear Queue", "Clear the processed files from queue?"):
            self.clear_all()

def main():
    """Main GUI entry point"""
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
