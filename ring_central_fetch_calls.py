import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json


# Load secrets
load_dotenv(".env.local")

# Env variables
CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
BASE_URL = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")

TOKEN_URL = f"{BASE_URL}/restapi/oauth/token"
CALL_LOG_URL = f"{BASE_URL}/restapi/v1.0/account/~/call-log"

def get_access_token_from_refresh_token():
    print("[🔄] Exchanging refresh token for access token...")
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
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
        update_refresh_token_env(token_data["refresh_token"])

    print("[✅] Got access token.")
    return access_token


def update_refresh_token_env(new_token, env_path=".env.local"):
    print("[💾] Updating .env.local with new refresh token...")
    lines = []
    updated = False

    # Read existing lines
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("RINGCENTRAL_REFRESH_TOKEN="):
                lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
                updated = True
            else:
                lines.append(line)

    # If token wasn't found, append it
    if not updated:
        lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")

    # Write back the updated content
    with open(env_path, "w") as f:
        f.writelines(lines)

    print("[✅] .env.local updated.")



def fetch_call_logs(access_token):
    print("[📞] Fetching call logs with recordings...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Go back 30 days
    from_date = (datetime.utcnow() - timedelta(days=365)).isoformat() + "Z"


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

        # Determine client number based on direction
        client_number = from_number if direction == "Inbound" else to_number

        print("  From:         ", from_number)
        print("  To:           ", to_number)
        print("  Direction:    ", direction)
        print("  Client Number:", client_number)
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

def save_calls_to_json(calls, output_dir="call_logs_cache"):
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
            phone = call.get("from", {}).get("phoneNumber") if direction == "Inbound" else call.get("to", {}).get("phoneNumber")
            structured_calls.append({
                "call_id": call.get("id"),
                "client_number": phone,
                "direction": direction,
                "startTime": call.get("startTime"),
                "recording_uri": call["recording"]["contentUri"]
            })

    with open(filepath, "w") as f:
        json.dump(structured_calls, f, indent=2)

    print(f"[💾] Saved {len(structured_calls)} calls with recordings to {filepath}")
def main():
    access_token = get_access_token_from_refresh_token()
    calls = fetch_call_logs(access_token)
    save_calls_to_json(calls)


    if not calls:
        print("❌ No calls with recordings found.")
        return

    for call in calls:
        if "recording" in call:
            recording_uri = call["recording"]["contentUri"]
            phone = call.get("to", {}).get("phoneNumber") or call.get("from", {}).get("phoneNumber")
            filename = f"recording_{phone.replace('+', '').replace(' ', '').replace('(', '').replace(')', '').replace('-', '')}.mp3"
            download_recording(recording_uri, access_token, filename)
            break
    else:
        print("❌ Found calls, but no recordings were downloadable.")

if __name__ == "__main__":
    main()
