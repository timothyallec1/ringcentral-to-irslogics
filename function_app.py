import azure.functions as func
from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics
import sys
import io

# Ensure stdout uses UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

app = func.FunctionApp()

# ✅ Timer trigger (runs every Monday at 2 AM UTC)
@app.function_name(name="WeeklyAutomation")
@app.schedule(schedule="0 0 2 * * 1", arg_name="mytimer", run_on_startup=False, use_monitor=True)
def weekly_timer(mytimer: func.TimerRequest) -> None:
    print("⏰ Timer trigger fired — running automation...")
    try:
        automate_ringcentral_to_irslogics()
        print("✅ Automation completed via Timer Trigger.")
    except Exception as e:
        print(f"❌ Automation failed: {e}")


# ✅ HTTP trigger (manual run)
@app.function_name(name="ManualAutomation")
@app.route(route="run-automation", methods=["GET", "POST"])
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    print("▶️ Manual HTTP trigger fired — running automation...")
    try:
        automate_ringcentral_to_irslogics()
        return func.HttpResponse("✅ Automation triggered successfully!", status_code=200)
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        return func.HttpResponse(f"❌ Automation failed: {e}", status_code=500)
