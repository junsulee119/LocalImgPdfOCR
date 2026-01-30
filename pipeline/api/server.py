"""
FastAPI Backend Server for OCR Web Application
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(
    title="OCR API",
    description="Backend API for OCR web application",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers and managers
from .routes import jobs, system, files, results, batch
from .websocket import ws_manager

# API routes (MUST come before static files mount)
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(files.router, prefix="/api/jobs", tags=["files"])
app.include_router(results.router, prefix="/api/jobs", tags=["results"])
app.include_router(batch.router, prefix="/api/batch", tags=["batch"])

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "OCR API is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# Serve frontend static files (MUST come last to not catch API routes)
frontend_path = Path(__file__).parent.parent.parent / "web_frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
