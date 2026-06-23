import threading
import time
import os
import sys
import subprocess
import logging
import tempfile
from datetime import datetime, timezone

from database import get_pending_job, update_job_status

logger = logging.getLogger("worker")

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
MODELS_DIR = os.path.join(BASE_DIR, "models")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PIPER_DIR  = os.path.join(BASE_DIR, "piper")          # thư mục chứa piper.exe

_stop_event = threading.Event()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_piper_exe() -> str:
    """Tìm piper.exe theo thứ tự ưu tiên."""
    candidates = [
        os.path.join(PIPER_DIR, "piper.exe"),          # Windows — piper/piper.exe
        os.path.join(PIPER_DIR, "piper"),               # Linux/macOS — piper/piper
        "piper",                                        # đã có trong PATH
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
        # kiểm tra PATH
        if not os.path.sep in c:
            import shutil
            found = shutil.which(c)
            if found:
                return found
    raise FileNotFoundError(
        "Không tìm thấy piper.exe. "
        "Tải piper_windows_amd64.zip từ GitHub và giải nén vào thư mục 'piper/'."
    )


def _run_piper(text: str, model_name: str, speaker_id: int, speed: float, out_path: str):
    piper_exe = _find_piper_exe()
    model_path = os.path.join(MODELS_DIR, model_name + ".onnx")
    config_path = model_path + ".json"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model không tìm thấy: {model_path}")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config model không tìm thấy: {config_path}")

    cmd = [
        piper_exe,
        "--model", model_path,
        "--config", config_path,
        "--output_file", out_path,
        "--length_scale", str(round(1.0 / max(speed, 0.01), 4)),
    ]
    if speaker_id and speaker_id > 0:
        cmd += ["--speaker", str(speaker_id)]

    # Piper đọc text từ stdin
    result = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=300,
    )

    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Piper lỗi (code {result.returncode}): {err}")


def _process_job(job: dict):
    job_id = job["id"]
    update_job_status(job_id, "processing", _now())
    logger.info(f"Xử lý job {job_id} | model={job['model_name']}")

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_filename = f"{job_id}.wav"
        out_path = os.path.join(OUTPUT_DIR, out_filename)

        _run_piper(
            text=job["text"],
            model_name=job["model_name"],
            speaker_id=int(job.get("speaker_id") or 0),
            speed=float(job.get("speed") or 1.0),
            out_path=out_path,
        )

        update_job_status(job_id, "done", _now(), output_file=out_filename)
        logger.info(f"Job {job_id} hoàn thành -> {out_filename}")

    except Exception as exc:
        logger.error(f"Job {job_id} lỗi: {exc}")
        update_job_status(job_id, "error", _now(), error_msg=str(exc))


def worker_loop():
    logger.info("Worker khởi động, đang poll jobs...")
    while not _stop_event.is_set():
        job = get_pending_job()
        if job:
            _process_job(job)
        else:
            time.sleep(2)


def start_worker() -> threading.Thread:
    t = threading.Thread(target=worker_loop, daemon=True, name="tts-worker")
    t.start()
    return t


def stop_worker():
    _stop_event.set()
