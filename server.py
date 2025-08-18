import io
import logging
import os
import sys
import threading
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# === Import your existing pipeline ===
# Make sure Python can see the repo root when running `uvicorn api.main:app`
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics
from api.job_manager import JobManager, JobState
from api.security import verify_api_key

app = FastAPI(title="RingCentral → IRS Logics Automation API", version="1.0.0")

# --- CORS (set your website origin here) ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory job manager (fine for one host; swap to Redis if needed) ---
jobs = JobManager()

class RunResponse(BaseModel):
    job_id: str
    state: JobState
    started_at: datetime

class StatusResponse(BaseModel):
    job_id: str
    state: JobState
    started_at: datetime | None
    finished_at: datetime | None
    log: str

singleflight_lock = threading.Lock()
is_running = False

@app.post("/automation/run", response_model=RunResponse)
def run_automation(_: None = Depends(verify_api_key)):
    global is_running
    # prevent overlapping runs (single-flight)
    if singleflight_lock.locked() or is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A run is already in progress. Try again later."
        )

    # Capture logs from your pipeline into a buffer
    log_buffer = io.StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setLevel(logging.INFO)

    logger = logging.getLogger()
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.INFO)

    job_id = jobs.create_job(log_buffer)

    def _run():
        global is_running
        is_running = True
        with singleflight_lock:
            try:
                jobs.mark_running(job_id)
                automate_ringcentral_to_irslogics()
                jobs.mark_finished(job_id, success=True)
            except Exception as e:
                logging.exception("Automation failed")
                jobs.mark_finished(job_id, success=False, error=str(e))
            finally:
                # restore logging
                logger.removeHandler(handler)
                logger.setLevel(previous_level)
                is_running = False

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return RunResponse(job_id=job_id, state=jobs.get(job_id)["state"], started_at=jobs.get(job_id)["started_at"])

@app.get("/automation/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: str, _: None = Depends(verify_api_key)):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # snapshot current log text
    log_text = job["log_buffer"].getvalue() if job["log_buffer"] else ""
    return StatusResponse(
        job_id=job_id,
        state=job["state"],
        started_at=job["started_at"],
        finished_at=job["finished_at"],
        log=log_text,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")  # no reload param
