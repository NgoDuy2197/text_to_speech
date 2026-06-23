import os
import uuid
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

import database as db
import worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("app")

BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output"
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    OUTPUT_DIR.mkdir(exist_ok=True)
    worker.start_worker()
    logger.info("App started, worker running.")
    yield
    worker.stop_worker()


app = FastAPI(title="Piper TTS Web", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────────────────────────

@app.get("/api/models")
def list_models():
    models = []
    if MODELS_DIR.exists():
        for f in sorted(MODELS_DIR.glob("*.onnx")):
            name = f.stem
            config = f.with_suffix(".onnx.json")
            speaker_count = 1
            if config.exists():
                import json
                try:
                    meta = json.loads(config.read_text(encoding="utf-8"))
                    speaker_count = meta.get("num_speakers", 1) or 1
                except Exception:
                    pass
            models.append({"name": name, "speaker_count": speaker_count, "size_mb": round(f.stat().st_size / 1_048_576, 1)})
    return {"models": models}


# ── Jobs ─────────────────────────────────────────────────────────────────────

class CreateJobRequest(BaseModel):
    text: str
    model_name: str
    speaker_id: int = 0
    speed: float = 1.0

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        if len(v) > 10_000:
            raise ValueError("text too long (max 10 000 chars)")
        return v

    @field_validator("speed")
    @classmethod
    def speed_range(cls, v):
        if not (0.25 <= v <= 4.0):
            raise ValueError("speed must be between 0.25 and 4.0")
        return v


@app.post("/api/jobs", status_code=201)
def create_job(req: CreateJobRequest):
    available = {f.stem for f in MODELS_DIR.glob("*.onnx")} if MODELS_DIR.exists() else set()
    if req.model_name not in available:
        raise HTTPException(400, f"Model '{req.model_name}' not found. Available: {sorted(available)}")

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.create_job(job_id, req.text, req.model_name, req.speaker_id, req.speed, now)
    return {"job_id": job_id, "status": "pending"}


@app.get("/api/jobs")
def list_jobs(limit: int = 50):
    return {"jobs": db.list_jobs(limit)}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.delete("/api/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] == "processing":
        raise HTTPException(409, "Cannot delete a job that is currently processing")
    out_file = db.delete_job(job_id)
    if out_file:
        path = OUTPUT_DIR / out_file
        if path.exists():
            path.unlink()


@app.get("/api/download/{job_id}")
def download(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done" or not job["output_file"]:
        raise HTTPException(409, "Audio not ready yet")
    path = OUTPUT_DIR / job["output_file"]
    if not path.exists():
        raise HTTPException(404, "Output file missing")
    safe_name = f"tts_{job_id[:8]}.wav"
    return FileResponse(path, media_type="audio/wav", filename=safe_name)


# ── Serve frontend ────────────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
