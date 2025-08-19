# --------------------------------------------------------------------
# Script: ring_central_fetch_calls.py
# Date Created: 2025-05-06
# Description:
#   This script authenticates with the RingCentral API using a stored
#   refresh token and fetches all call logs that include recordings
#   for the past ~1000 days. It filters these to include only sales
#   team calls and stores the results in a JSON file. The first 
#   recording is downloaded locally for quick validation.
#
#   Features:
#   - Authenticates via OAuth 2.0 (refresh token)
#   - Updates the `.env.local` file if a new refresh token is returned
#   - Fetches call logs with recordings
#   - Filters only those calls where the sales number is known
#   - Outputs a structured call log JSON for later matching
#   - Downloads the first recording as an MP3 file
#
#   Usage:
#     Run directly from terminal:
#     `python ring_central_fetch_calls.py`
#
#   Output:
#     - JSON file in `ring_central_call_logs_cache/` named like
#       `calls_YYYY-MM-DD_HHMM.json`
#     - The first valid MP3 recording downloaded as:
#       `recording_call_1_XXXXXXXXXX.mp3`
#
# --------------------------------------------------------------------


import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
from ringcentral_update_azure_refresh_token import load_refresh_token, save_refresh_token



# Load secrets
# Load from .env.local if present (for local dev), otherwise Azure will use Function App settings
if os.path.exists(".env.local"):
    load_dotenv(".env.local")

# Env variables
CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
# REFRESH_TOKEN = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
BASE_URL = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")

TOKEN_URL = f"{BASE_URL}/restapi/oauth/token"
CALL_LOG_URL = f"{BASE_URL}/restapi/v1.0/account/~/call-log"

SALE_NUMBERS = {
    "(213)900-4505",  # Aden Bustillos
    "(323)486-6977",  # Alex Feuer
    "(213)296-2235",  # Andrea Coins
    "(818)649-5689",  # Caleb Cole
    "(213)762-0668",  # Danny Guerra
    "(213)378-2141",  # David Monroe
    "(213)296-2838",  # Hailey Ritter
    "(213)291-9502",  # Kylie Klingman
    "(213)291-9541",  # Leah McLaughlin
    "(213)291-9376",  # Levon Baghdagyulyan
    "(213)291-9409",  # Logan Allec
    "(213)762-0553",  # Luke Lasiter
    "(213)291-9419",  # Lulu Peralta
    "(213)341-2065",  # Nathan Hyun
    "(855)477-5436",  # Tim Allec
}

def get_access_token_from_refresh_token():
    print("[🔄] Exchanging refresh token for access token...")
    refresh_token = load_refresh_token()   # ✅ read from /home/refresh_token.txt or fallback to env

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    auth = (CLIENT_ID, CLIENT_SECRET)
    response = requests.post(TOKEN_URL, data=data, auth=auth)

    # Debug output
    if response.status_code != 200:
        print("❌ Error response from RingCentral:")
        print("Status Code:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()

    token_data = response.json()
    access_token = token_data["access_token"]

    # If a new refresh token is returned, save it
    if "refresh_token" in token_data:
        save_refresh_token(token_data["refresh_token"])  # ✅ write to /home/refresh_token.txt

    print("[✅] Got access token.")
    return access_token



# def get_access_token_from_refresh_token():
#     print("[🔄] Exchanging refresh token for access token...")
#     data = {
#         "grant_type": "refresh_token",
#         "refresh_token": REFRESH_TOKEN
#     }

#     auth = (CLIENT_ID, CLIENT_SECRET)
#     response = requests.post(TOKEN_URL, data=data, auth=auth)

#     # Debug output
#     if response.status_code != 200:
#         print("❌ Error response from RingCentral:")
#         print("Status Code:", response.status_code)
#         print("Response:", response.text)
#         response.raise_for_status()

#     token_data = response.json()
#     access_token = token_data["access_token"]

#     # If a new refresh token is returned, save it
#     if "refresh_token" in token_data:
#         update_refresh_token_env(token_data["refresh_token"])
#         print("[✅] New refresh token saved to .env.local.")

#     print("[✅] Got access token.")
#     return access_token


# def update_refresh_token_env(new_token, env_path=".env.local"):
#     print("[💾] Updating .env.local with new refresh token...")
#     lines = []
#     updated = False

#     # Read existing lines
#     with open(env_path, "r") as f:
#         for line in f:
#             if line.startswith("RINGCENTRAL_REFRESH_TOKEN="):
#                 lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
#                 updated = True
#             else:
#                 lines.append(line)

#     # If token wasn't found, append it
#     if not updated:
#         lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")

#     # Write back the updated content
#     with open(env_path, "w") as f:
#         f.writelines(lines)

#     print("[✅] .env.local updated.")



def fetch_call_logs(access_token):
    print("[📞] Fetching call logs with recordings...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Go back 30 days
    from_date = (datetime.utcnow() - timedelta(days=1000)).isoformat() + "Z"


    params = {
        "withRecording": "True",
        "perPage": 5000,
        "dateFrom": from_date
    }

    response = requests.get(CALL_LOG_URL, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    records = data.get("records", [])
    print(f"[📊] Total call records fetched: {len(records)}")

    for i, call in enumerate(records[:10]):
        print(f"\n📞 Call #{i+1}")
        from_number = call.get("from", {}).get("phoneNumber")
        to_number = call.get("to", {}).get("phoneNumber")
        direction = call.get("direction")

        client_number = from_number if direction == "Inbound" else to_number
        sale_number = to_number if direction == "Inbound" else from_number

        print("  From:         ", from_number)
        print("  To:           ", to_number)
        print("  Direction:    ", direction)
        print("  Client Number:", format_phone_number(client_number))
        print("  Sale Number:  ", format_phone_number(sale_number))
        print("  StartTime:    ", call.get("startTime"))


        if "recording" in call:
            print("  🎙 Recording URI:", call["recording"].get("contentUri"))
        else:
            print("  ❌ No recording on this call")


    return records

def download_recording(recording_uri, access_token, filename):
    print(f"[⬇️] Downloading recording to {filename}...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(recording_uri, headers=headers)
    response.raise_for_status()

    with open(filename, "wb") as f:
        f.write(response.content)
    print("[✅] Download complete.")

def save_calls_to_json(calls, output_dir="ring_central_call_logs_cache"):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"calls_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)


    structured_calls = []

    for call in calls:
        if "recording" in call:
            direction = call.get("direction")
            client = call.get("from", {}).get("phoneNumber") if direction == "Inbound" else call.get("to", {}).get("phoneNumber")
            sale = call.get("to", {}).get("phoneNumber") if direction == "Inbound" else call.get("from", {}).get("phoneNumber")
            formatted_sale = format_phone_number(sale)

            if formatted_sale in SALE_NUMBERS:
                structured_calls.append({
                    "call_id": call.get("id"),
                    "client_number": format_phone_number(client),
                    "sale_number": formatted_sale,
                    "direction": direction,
                    "startTime": call.get("startTime"),
                    "recording_uri": call["recording"]["contentUri"]
                })


    with open(filepath, "w") as f:
        json.dump(structured_calls, f, indent=2)

    print(f"[💾] Saved {len(structured_calls)} calls with recordings to {filepath}")

def fetch_and_cache_ringcentral_calls():
    """
    Complete automated flow:
    - Get access token from refresh token
    - Fetch all RingCentral call logs
    - Filter to sales numbers + recordings
    - Save to a timestamped JSON file in `ring_central_call_logs_cache/`
    
    Returns:
        str: Path to the saved JSON file
    """
    print("🔐 Getting access token using refresh token...")
    access_token = get_access_token_from_refresh_token()
    print("✅ Access token obtained.")

    print("📞 Fetching call logs from RingCentral...")
    calls = fetch_call_logs(access_token)
    print(f"📊 Total calls fetched: {len(calls)}")

    if not calls:
        raise RuntimeError("No calls with recordings found.")

    # Count matches before saving
    structured_calls = []
    for call in calls:
        if "recording" in call:
            direction = call.get("direction")
            client = call.get("from", {}).get("phoneNumber") if direction == "Inbound" else call.get("to", {}).get("phoneNumber")
            sale = call.get("to", {}).get("phoneNumber") if direction == "Inbound" else call.get("from", {}).get("phoneNumber")
            formatted_sale = format_phone_number(sale)
            if formatted_sale in SALE_NUMBERS:
                structured_calls.append(call)

    print(f"🎯 Matching calls with sales numbers and recordings: {len(structured_calls)}")

    # Save using original logic
    save_calls_to_json(calls)

    # Confirm file written
    output_dir = "ring_central_call_logs_cache"
    if not os.path.exists(output_dir):
        raise FileNotFoundError("❌ Output folder not found.")

    all_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".json")]
    if not all_files:
        raise FileNotFoundError("❌ No JSON files found in output folder.")

    latest_file = max(all_files, key=os.path.getctime)
    print(f"💾 Latest saved call log: {latest_file}")
    return latest_file


def main():
    access_token = get_access_token_from_refresh_token()
    calls = fetch_call_logs(access_token)
    save_calls_to_json(calls)


    if not calls:
        print("❌ No calls with recordings found.")
        return

    for i, call in enumerate(calls):
        if "recording" in call:
            recording_uri = call["recording"]["contentUri"]

            direction = call.get("direction")
            raw_number = call.get("from", {}).get("phoneNumber") if direction == "Inbound" else call.get("to", {}).get("phoneNumber")
            formatted_number = format_phone_number(raw_number)

            # Sanitize phone number for filename (remove special chars)
            safe_number = formatted_number.replace("(", "").replace(")", "").replace("-", "")

            filename = f"recording_call_{i+1}_{safe_number}.mp3"
            download_recording(recording_uri, access_token, filename)
            break


    else:
        print("❌ Found calls, but no recordings were downloadable.")

def format_phone_number(raw_number):
    if not raw_number:
        return ""  # Return empty string if None or blank

    if raw_number.startswith('+1'):
        raw_number = raw_number[2:]
    
    # Ensure only digits remain
    digits = ''.join(filter(str.isdigit, raw_number))
    
    if len(digits) == 10:
        return f"({digits[:3]}){digits[3:6]}-{digits[6:]}"
    else:
        return raw_number  # Return as-is if not valid 10-digit number


if __name__ == "__main__":
    main()
