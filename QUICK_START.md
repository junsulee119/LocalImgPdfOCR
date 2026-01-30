# OCR Application - Quick Start Guide

## 🚀 Quick Start

### Double-click `ocr.bat`
- Automatically sets up environment (first time only)
- Starts web server on http://localhost:8000
- Opens browser automatically
- Press Ctrl+C to stop

### CLI Mode
```batch
ocr.bat input.png --output result.md
```

---

## What Happens When You Run ocr.bat

1. **First Time:**
   - Creates Python 3.11 virtual environment (`.venv`)
   - Auto-detects GPU and installs PyTorch (CUDA or CPU)
   - Installs all dependencies from `requirements.txt`

2. **Every Time:**
   - Activates virtual environment
   - Starts FastAPI server on port 8000
   - Opens http://localhost:8000 in browser
   - Shows live server logs

3. **Stop Server:**
   - Press `Ctrl+C` in terminal
   - Server shuts down gracefully

---

## Web Interface Features

- **Drag & Drop** - PDFs and images
- **Real-time Progress** - WebSocket updates
- **Job Queue** - Multiple files, sequential processing
- **Results Editor** - Edit OCR output before saving
- **Per-file Results** - Each file gets its own .md

---

## File Locations

- **Jobs**: `output/jobs.json`
- **Uploaded Files**: `output/{job_id}/files/`
- **Results**: `output/{job_id}/results/`

---

## Troubleshooting

### Server won't start
```batch
# Manually activate venv and check
.venv\Scripts\activate
python -m uvicorn pipeline.api.server:app --host 127.0.0.1 --port 8000
```

### Port already in use
```batch
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Browser doesn't open
Manually navigate to: http://localhost:8000

---

## Advanced Usage

### Run on different port
```batch
.venv\Scripts\activate
python -m uvicorn pipeline.api.server:app --port 8080
```

### CLI with custom settings
```batch
ocr.bat input.pdf --mode img --device cuda --pages 1-5
```

### Reinstall dependencies
```batch
.venv\Scripts\activate
pip install -r requirements.txt --upgrade
```
