import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.api.routes import router
from backend.config import REPORTS_DIR

app = FastAPI(
    title="Physics-Based ENF Forensic Analyzer",
    description="Digital Video Evidence Authentication and Tampering Detection via Electrical Network Frequency (ENF)",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(router)

# Mount reports folder as static (for direct download)
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

# Mount frontend folder at the root path
# Check if frontend folder exists, if not, create it
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
frontend_dir.mkdir(exist_ok=True)

# Mount the static files
app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
