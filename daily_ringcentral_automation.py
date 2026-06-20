from automate_ringcentral_to_irslogics import automate_ringcentral_to_irslogics
from missed_call_google_sheet import populate_missed_calls_google_sheet


def run_daily_ringcentral_automation():
    print("[Daily] Starting recording upload automation...")
    automate_ringcentral_to_irslogics()
    print("[Daily] Recording upload automation completed.")

    print("[Daily] Starting missed-calls Google Sheet automation...")
    missed_calls_result = populate_missed_calls_google_sheet()
    print(f"[Daily] Missed-calls automation completed: {missed_calls_result}")

    return {
        "recording_upload": "completed",
        "missed_calls": missed_calls_result,
    }


if __name__ == "__main__":
    print(run_daily_ringcentral_automation())
