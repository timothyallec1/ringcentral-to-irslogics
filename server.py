from fastapi import FastAPI, BackgroundTasks, Response
import logging
import sys
from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics
from missed_call_google_sheet import populate_missed_calls_google_sheet
from daily_ringcentral_automation import run_daily_ringcentral_automation
from irs_logics_upload_call_recordings import upload_call_recordings_to_irslogics  # ✅ new import
from irs_logics_match_caseID_with_call_logs import match_calls_to_cases
from ringcentral_call_audit import build_audit_csv, csv_filename
from storage_utils import load_latest_json  # ✅ new import

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

# Invoke-WebRequest -Uri "https://automated-ringcentral-irslogics-fra6hxard8aadwd9.canadacentral-01.azurewebsites.net/run-automation" -Method GET
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


@app.get("/populate-missed-calls-sheet")
def populate_missed_calls_sheet(background_tasks: BackgroundTasks, days_back: int | None = None):
    logger.info(f"Manual missed-calls sheet endpoint fired. days_back={days_back}")

    def run_job():
        try:
            result = populate_missed_calls_google_sheet(days_back=days_back)
            logger.info(f"Missed-calls sheet completed: {result}")
        except Exception as e:
            logger.exception(f"Missed-calls sheet failed: {e}")

    background_tasks.add_task(run_job)
    return {"status": "Missed-calls sheet population started."}


@app.get("/run-daily-ringcentral-automation")
def daily_ringcentral_automation(background_tasks: BackgroundTasks):
    logger.info("Manual combined daily RingCentral automation endpoint fired.")

    def run_job():
        try:
            result = run_daily_ringcentral_automation()
            logger.info(f"Combined daily RingCentral automation completed: {result}")
        except Exception as e:
            logger.exception(f"Combined daily RingCentral automation failed: {e}")

    background_tasks.add_task(run_job)
    return {"status": "Combined daily RingCentral automation started."}


@app.get("/ringcentral-call-audit")
def ringcentral_call_audit(
    start_month: int | None = None,
    start_year: int | None = None,
    end_month: int | None = None,
    end_year: int | None = None,
    begin_month: int | None = None,
    begin_year: int | None = None,
):
    start_month = start_month or begin_month
    start_year = start_year or begin_year
    if not all((start_month, start_year, end_month, end_year)):
        return Response(
            "Missing required query parameter(s). Example: "
            "/ringcentral-call-audit?start_month=1&start_year=2026&end_month=6&end_year=2026",
            status_code=400,
            media_type="text/plain",
        )

    try:
        csv_body = build_audit_csv(start_month, start_year, end_month, end_year)
        filename = csv_filename(start_month, start_year, end_month, end_year)
    except ValueError as exc:
        return Response(str(exc), status_code=400, media_type="text/plain")
    except Exception as exc:
        logger.exception("RingCentral call audit failed.")
        return Response(
            f"RingCentral call audit failed: {exc}",
            status_code=500,
            media_type="text/plain",
        )

    return Response(
        csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Invoke-WebRequest -Uri "https://automated-ringcentral-irslogics-fra6hxard8aadwd9.canadacentral-01.azurewebsites.net/upload-call-recordings" -Method GET

# ✅ New endpoint: Upload Call Recordings only
# @app.get("/upload-call-recordings")
# def upload_call_recordings(background_tasks: BackgroundTasks):
#     logger.info("▶️ Upload Call Recordings endpoint triggered...")
#     latest_calls = load_latest_json("ring_central_call_logs_cache", "fetchedcallsringcentral")
#     latest_cases = load_latest_json("irs_logics_case_info_cache", "caseinfo")
#     match_calls_to_cases(latest_calls, latest_cases)

#     def run_upload():
#         try:
#             upload_call_recordings_to_irslogics()
#             logger.info("✅ Call recordings upload completed.")
#         except Exception as e:
#             logger.exception(f"❌ Upload failed in background: {e}")

#     background_tasks.add_task(run_upload)
#     return {"status": "✅ Upload Call Recordings started (running in background)..."}

# # (Optional) Timer-like endpoint (since App Service doesn’t have CRON triggers by default)
# @app.get("/weekly-automation")
# def weekly_trigger(background_tasks: BackgroundTasks):
#     logger.info("⏰ Weekly automation endpoint called...")

#     background_tasks.add_task(automate_ringcentral_to_irslogics)

#     return {"status": "✅ Weekly automation started"}

# # ✅ Local dev entrypoint
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
