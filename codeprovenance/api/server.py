"""
CodeProvenance FastAPI Server
Provides REST endpoints and serves the interactive architectural drift dashboard.
"""

from pathlib import Path
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from codeprovenance.core.drift_tracker import DriftTracker
from codeprovenance.core.rules_engine import DEFAULT_BLUEPRINT
from codeprovenance.core.models import CodebaseDriftReport

app = FastAPI(
    title="CodeProvenance API",
    description="Codebase Architecture Drift & Violation Detector",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tracker = DriftTracker()
current_target_dir = Path(__file__).resolve().parent.parent.parent


@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "scanner": "CodeProvenance AST Engine",
        "default_target": str(current_target_dir)
    }


@app.get("/api/scan", response_model=CodebaseDriftReport)
def run_scan(target_path: Optional[str] = None):
    scan_dir = Path(target_path) if target_path else current_target_dir
    if not scan_dir.exists():
        raise HTTPException(status_code=400, detail="Target path does not exist")
    return tracker.scan_project(scan_dir)


@app.get("/api/layers")
def get_layers():
    return DEFAULT_BLUEPRINT.dict()


# Mount Web Dashboard
static_path = Path(__file__).resolve().parent.parent / "web" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_index():
    index_file = static_path / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>CodeProvenance Web Dashboard</h1>")
