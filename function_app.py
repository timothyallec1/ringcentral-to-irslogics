import azure.functions as func
from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics
from missed_call_google_sheet import populate_missed_calls_google_sheet
from weekly_ringcentral_automation import run_weekly_ringcentral_automation
import sys
import io
import logging
import threading

# Ensure stdout uses UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

app = func.FunctionApp()

# ✅ Timer trigger (runs every Monday at 2 AM UTC)
@app.function_name(name="WeeklyAutomation")
@app.schedule(schedule="0 0 2 * * 1", arg_name="mytimer", run_on_startup=False, use_monitor=True)
def weekly_timer(mytimer: func.TimerRequest) -> None:
    logging.info("⏰ Timer trigger fired — running automation...")
    try:
        automate_ringcentral_to_irslogics()
        logging.info("✅ Automation completed via Timer Trigger.")
    except Exception as e:
        logging.error(f"❌ Automation failed: {e}")


# ✅ HTTP trigger (manual run, background execution with refresh token logs)
@app.function_name(name="ManualAutomation")
@app.route(route="run-automation", methods=["GET", "POST"])
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("▶️ Manual HTTP trigger fired — starting automation in background...")

    def run_job():
        try:
            automate_ringcentral_to_irslogics()
            logging.info("✅ Automation completed via Manual HTTP Trigger (background).")
        except Exception as e:
            # 👇 Log out the refresh token if available
            try:
                with open("/home/refresh_token.txt", "r") as f:
                    token = f.read().strip()
                    logging.info(f"🔑 Refresh token (first/last 6): {token[:6]}...{token[-6:]}")
            except FileNotFoundError:
                logging.warning("⚠️ /home/refresh_token.txt not found")
            except Exception as ex:
                logging.warning(f"⚠️ Could not read refresh token: {ex}")

            logging.error(f"❌ Automation failed in background: {e}")

    # Run automation in a background thread to avoid HTTP timeout
    threading.Thread(target=run_job, daemon=True).start()

    # Immediately return so Azure doesn’t kill the request
    return func.HttpResponse("✅ Automation started (running in background)...", status_code=200)

# Captures unknown missed callers for Isabella's callback sheet every weekday.
@app.function_name(name="WeekdayMissedCallsSheet")
@app.schedule(schedule="0 0 14 * * 1-5", arg_name="mytimer", run_on_startup=False, use_monitor=True)
def weekday_missed_calls_sheet(mytimer: func.TimerRequest) -> None:
    logging.info("Missed-calls sheet timer fired.")
    try:
        result = populate_missed_calls_google_sheet()
        logging.info(f"Missed-calls sheet completed: {result}")
    except Exception as e:
        logging.error(f"Missed-calls sheet failed: {e}")


@app.function_name(name="ManualMissedCallsSheet")
@app.route(route="populate-missed-calls-sheet", methods=["GET", "POST"])
def manual_missed_calls_sheet(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Manual missed-calls sheet trigger fired.")

    def run_job():
        try:
            result = populate_missed_calls_google_sheet()
            logging.info(f"Manual missed-calls sheet completed: {result}")
        except Exception as e:
            logging.error(f"Manual missed-calls sheet failed: {e}")

    threading.Thread(target=run_job, daemon=True).start()
    return func.HttpResponse("Missed-calls sheet population started.", status_code=200)


@app.function_name(name="ManualWeeklyRingCentralAutomation")
@app.route(route="run-weekly-ringcentral-automation", methods=["GET", "POST"])
def manual_weekly_ringcentral_automation(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Manual combined weekly RingCentral automation trigger fired.")

    def run_job():
        try:
            result = run_weekly_ringcentral_automation()
            logging.info(f"Combined weekly RingCentral automation completed: {result}")
        except Exception as e:
            logging.error(f"Combined weekly RingCentral automation failed: {e}")

    threading.Thread(target=run_job, daemon=True).start()
    return func.HttpResponse("Combined weekly RingCentral automation started.", status_code=200)
