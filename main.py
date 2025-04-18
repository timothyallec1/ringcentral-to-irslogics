import os
import requests
from dotenv import load_dotenv

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
    params = {
        "withRecording": "true",
        "perPage": 100
    }
    response = requests.get(CALL_LOG_URL, headers=headers, params=params)
    response.raise_for_status()
    return response.json().get("records", [])

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

def main():
    access_token = get_access_token_from_refresh_token()
    calls = fetch_call_logs(access_token)

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
