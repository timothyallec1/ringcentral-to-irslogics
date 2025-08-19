# --------------------------------------------------------------------
# Script: ringe_central_get_tokens.py
# Date Created: 2025-05-06
# Description:
#   This utility script initiates the OAuth 2.0 flow for RingCentral's
#   API to obtain an access token and refresh token using a client ID,
#   client secret, and redirect URI.
#
#   Features:
#   - Opens the RingCentral authorization page in a web browser
#   - Prompts the user to paste the authorization code
#   - Exchanges the code for access and refresh tokens via API
#   - Prints both tokens to the console and instructs where to store them
#
#   Usage:
#     1. Run the script in a terminal: `python ringe_central_get_tokens.py`
#     2. Log into RingCentral when the browser opens
#     3. After redirection, copy the `code` from the URL
#     4. Paste it into the terminal when prompted
#     5. Copy the `refresh_token` and store it in `.env.local`... overwrite the old one if it exists
#
#   Prerequisites:
#     - Environment variables set in `.env.local`:
#         RINGCENTRAL_CLIENT_ID
#         RINGCENTRAL_CLIENT_SECRET
#         RINGCENTRAL_REDIRECT_URI (optional; defaults to localhost)
# --------------------------------------------------------------------


import os
import requests
import urllib.parse
import webbrowser
from dotenv import load_dotenv

# Load client credentials
# Load from .env.local if present (for local dev), otherwise Azure will use Function App settings
if os.path.exists(".env.local"):
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
