# Backend Server Setup

## Dependencies Added to requirements.txt

```
fastapi>=0.104.0           # Web framework
uvicorn[standard]>=0.24.0  # ASGI server
python-multipart>=0.0.6    # File upload support
websockets>=12.0           # Real-time communication
```

## Installation

### Option 1: Using Virtual Environment (Recommended)

```bash
# Create venv
python -m venv venv

# Activate venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install all dependencies
pip install -r requirements.txt
```

### Option 2: Global Installation (Current)

```bash
# Install all dependencies globally
pip install -r requirements.txt
```

## Running the Server

```bash
# Start backend server
python -m uvicorn pipeline.api.server:app --reload --port 8000

# Or with custom settings
uvicorn pipeline.api.server:app --host 0.0.0.0 --port 8000 --reload
```

## Accessing the Application

- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc

## Notes

- The server is currently running globally (no venv detected)
- Dependencies were already installed: `fastapi`, `uvicorn`, `python-multipart`, `websockets`
- requirements.txt updated for future installations
