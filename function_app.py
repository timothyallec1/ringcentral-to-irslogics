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


# ✅ HTTP trigger (manual run, background execution with refresh token logs)
@app.function_name(name="ManualAutomation")
@app.route(route="run-automation", methods=["GET", "POST"])
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    print("▶️ Manual HTTP trigger fired — starting automation in background...")

    def run_job():
        try:
            automate_ringcentral_to_irslogics()
            print("✅ Automation completed via Manual HTTP Trigger (background).")
        except Exception as e:
            # 👇 Print out the refresh token currently in the file
            try:
                with open("/home/refresh_token.txt", "r") as f:
                    token = f.read().strip()
                    print(f"🔑 Refresh token (first/last 6): {token[:6]}...{token[-6:]}")
            except FileNotFoundError:
                print("⚠️ /home/refresh_token.txt not found")
            except Exception as ex:
                print(f"⚠️ Could not read refresh token: {ex}")

            print(f"❌ Automation failed in background: {e}")

    # Run automation in a background thread to avoid HTTP timeout
    import threading
    threading.Thread(target=run_job, daemon=True).start()

    # Immediately return so Azure doesn’t kill the request
    return func.HttpResponse("✅ Automation started (running in background)...", status_code=200)

