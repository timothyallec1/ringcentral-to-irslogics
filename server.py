from fastapi import FastAPI, BackgroundTasks
import logging
import sys
from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics

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

    # Run automation as a background task (FastAPI handles thread mgmt)
    background_tasks.add_task(run_job)

    return {"status": "✅ Automation started (running in background)..."}

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
