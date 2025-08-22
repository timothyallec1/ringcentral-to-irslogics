from fastapi import FastAPI, BackgroundTasks
import logging
import sys
from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics
from irs_logics_upload_call_recordings import upload_call_recordings_to_irslogics  # ✅ new import
from irs_logics_match_caseID_with_call_logs import match_calls_to_cases
from utilities import get_latest_json_file

# ✅ Configure logging so logs go to stdout (captured by Azure Log Stream)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# ✅ Root healthcheck
@app.get("/")
def home():
    logger.info("💓 Healthcheck hit at '/'")
    return {"status": "ok", "message": "IRS Logics Automation API running"}

# ✅ Manual trigger (like your HTTP trigger)
@app.get("/run-automation")
def manual_trigger(background_tasks: BackgroundTasks):
    logger.info("▶️ Manual HTTP trigger fired — starting automation in background...")

    def run_job():
        try:
            automate_ringcentral_to_irslogics()
            logger.info("✅ Automation completed via Manual HTTP Trigger (background).")
        except Exception as e:
            logger.exception(f"❌ Automation failed in background: {e}")

    background_tasks.add_task(run_job)
    return {"status": "✅ Automation started (running in background)..."}


# Invoke-WebRequest -Uri "https://automated-ringcentral-irslogics-fra6hxard8aadwd9.canadacentral-01.azurewebsites.net/upload-call-recordings" -Method GET
@app.get("/upload-call-recordings")
def upload_call_recordings(background_tasks: BackgroundTasks):
    logger.info("▶️ Upload Call Recordings endpoint triggered...")

    latest_calls = get_latest_json_file("ring_central_call_logs_cache")
    latest_cases = get_latest_json_file("irs_logics_case_info_cache")
    merged_file, _ = match_calls_to_cases(latest_calls, latest_cases)  # ✅ capture

    def run_upload():
        try:
            upload_call_recordings_to_irslogics(merged_file)  # ✅ pass directly
            logger.info("✅ Call recordings upload completed.")
        except Exception as e:
            logger.exception(f"❌ Upload failed in background: {e}")

    background_tasks.add_task(run_upload)
    return {"status": "✅ Upload Call Recordings started (running in background)..."}


# (Optional) Timer-like endpoint (since App Service doesn’t have CRON triggers by default)
@app.get("/weekly-automation")
def weekly_trigger(background_tasks: BackgroundTasks):
    logger.info("⏰ Weekly automation endpoint called...")

    background_tasks.add_task(automate_ringcentral_to_irslogics)

    return {"status": "✅ Weekly automation started"}

# # ✅ Local dev entrypoint
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
