import os
import requests
import urllib.parse
import webbrowser
from dotenv import load_dotenv

# Load client credentials
load_dotenv(".env.local")

CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
REDIRECT_URI = os.getenv("RINGCENTRAL_REDIRECT_URI", "https://localhost/callback")
BASE_URL = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")

AUTH_URL = f"{BASE_URL}/restapi/oauth/authorize"
TOKEN_URL = f"{BASE_URL}/restapi/oauth/token"

def get_authorization_code():
    # Step 1: Build authorization URL
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
    }

    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("[🌐] Opening browser to log into RingCentral...")
    webbrowser.open(url)

    print("👉 After logging in and authorizing, copy the 'code' parameter from the URL you’re redirected to.")
    auth_code = input("Paste the code here: ").strip()
    return auth_code

def exchange_code_for_tokens(auth_code):
    # Step 2: Exchange authorization code for tokens
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
    }

    auth = (CLIENT_ID, CLIENT_SECRET)

    print("[🔁] Exchanging code for access and refresh tokens...")
    response = requests.post(TOKEN_URL, data=data, auth=auth)
    response.raise_for_status()

    tokens = response.json()
    print("\n✅ Access Token:\n", tokens["access_token"])
    print("\n🔄 Refresh Token:\n", tokens["refresh_token"])
    print("\n⚠️ Save the refresh token in your `.env.local` under:")
    print("RINGCENTRAL_REFRESH_TOKEN=your_token_here\n")

    return tokens

def main():
    auth_code = get_authorization_code()
    exchange_code_for_tokens(auth_code)

if __name__ == "__main__":
    main()
