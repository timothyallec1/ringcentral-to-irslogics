import csv
import io
import os
import time
from collections import Counter
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


if os.path.exists(".env.local"):
    load_dotenv(".env.local", override=True)

BASE_URL = os.getenv("RINGCENTRAL_BASE_URL", "https://platform.ringcentral.com")
TOKEN_URL = f"{BASE_URL}/restapi/oauth/token"
CALL_LOG_URL = f"{BASE_URL}/restapi/v1.0/account/~/call-log"
REFRESH_TOKEN_FILE = "/home/refresh_token.txt"
MAX_RINGCENTRAL_RETRIES = 5

TARGET_NUMBERS = {
    "2139004504": "Isabella",
    "8668000829": "Choice Tax Relief",
}


def phone_key(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def load_refresh_token():
    if os.path.exists(".env.local"):
        token = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
        if token:
            return token

    if os.path.exists(REFRESH_TOKEN_FILE):
        with open(REFRESH_TOKEN_FILE, "r", encoding="utf-8") as f:
            token = f.read().strip()
        if token:
            return token

    token = os.getenv("RINGCENTRAL_REFRESH_TOKEN")
    if token:
        return token

    raise RuntimeError("Missing RINGCENTRAL_REFRESH_TOKEN.")


def save_refresh_token(new_token):
    token_dir = os.path.dirname(REFRESH_TOKEN_FILE)
    if os.path.isdir(token_dir):
        with open(REFRESH_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(new_token)

    if os.path.exists(".env.local"):
        lines = []
        updated = False
        with open(".env.local", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("RINGCENTRAL_REFRESH_TOKEN="):
                    lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
                    updated = True
                else:
                    lines.append(line)
        if not updated:
            lines.append(f"RINGCENTRAL_REFRESH_TOKEN={new_token}\n")
        with open(".env.local", "w", encoding="utf-8") as f:
            f.writelines(lines)


def get_access_token_from_refresh_token():
    client_id = os.getenv("RINGCENTRAL_CLIENT_ID")
    client_secret = os.getenv("RINGCENTRAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing RingCentral client credentials.")

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": load_refresh_token(),
        },
        auth=(client_id, client_secret),
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"RingCentral token exchange failed with {response.status_code}: {response.text}"
        )

    token_data = response.json()
    if token_data.get("refresh_token"):
        save_refresh_token(token_data["refresh_token"])
    return token_data["access_token"]


def parse_month_year(month, year, label):
    try:
        month_int = int(month)
        year_int = int(year)
    except (TypeError, ValueError):
        raise ValueError(f"{label}_month and {label}_year must be numbers.")

    if month_int < 1 or month_int > 12:
        raise ValueError(f"{label}_month must be between 1 and 12.")
    if year_int < 2000 or year_int > 2100:
        raise ValueError(f"{label}_year must be between 2000 and 2100.")

    return year_int, month_int


def add_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


def month_range(start_year, start_month, end_year, end_month):
    if (end_year, end_month) < (start_year, start_month):
        raise ValueError("End month/year must be after or equal to start month/year.")

    months = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        months.append((year, month))
        year, month = add_month(year, month)
    return months


def iso_month_start(year, month):
    return datetime(year, month, 1, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def month_key_from_start_time(start_time):
    if not start_time:
        return None
    for date_format in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(start_time, date_format)
            return parsed.year, parsed.month
        except ValueError:
            continue
    return None


def month_label(year, month):
    return datetime(year, month, 1).strftime("%B %Y")


def audit_label(months):
    start_year, start_month = months[0]
    end_year, end_month = months[-1]
    if start_year == end_year:
        if start_month == end_month:
            return month_label(start_year, start_month)
        return (
            f"{datetime(start_year, start_month, 1).strftime('%B')} to "
            f"{datetime(end_year, end_month, 1).strftime('%B')} {start_year}"
        )
    return f"{month_label(start_year, start_month)} to {month_label(end_year, end_month)}"


def fetch_inbound_call_logs(date_from, date_to):
    access_token = get_access_token_from_refresh_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "direction": "Inbound",
        "perPage": 1000,
    }

    records = []
    page = 1
    while True:
        params["page"] = page
        for attempt in range(1, MAX_RINGCENTRAL_RETRIES + 1):
            response = requests.get(CALL_LOG_URL, headers=headers, params=params, timeout=30)
            if response.status_code != 429:
                response.raise_for_status()
                break

            retry_after = response.headers.get("Retry-After")
            try:
                wait_seconds = int(retry_after) if retry_after else 30 * attempt
            except ValueError:
                wait_seconds = 30 * attempt
            time.sleep(wait_seconds)
        else:
            response.raise_for_status()

        payload = response.json()
        records.extend(payload.get("records", []))

        navigation = payload.get("navigation", {}) or {}
        if not navigation.get("nextPage"):
            return records
        page += 1


def classify_record(call, wanted_months):
    if call.get("direction") != "Inbound":
        return None

    target_key = phone_key((call.get("to") or {}).get("phoneNumber"))
    if target_key not in TARGET_NUMBERS:
        return None

    month_key = month_key_from_start_time(call.get("startTime"))
    if month_key not in wanted_months:
        return None

    result = str(call.get("result") or "").strip().lower()
    if result == "missed":
        return month_key, "Answering Service"
    return month_key, "Live Answered"


def build_call_audit(start_month, start_year, end_month, end_year):
    start_year, start_month = parse_month_year(start_month, start_year, "start")
    end_year, end_month = parse_month_year(end_month, end_year, "end")
    months = month_range(start_year, start_month, end_year, end_month)

    next_year, next_month = add_month(end_year, end_month)
    records = fetch_inbound_call_logs(
        iso_month_start(start_year, start_month),
        iso_month_start(next_year, next_month),
    )

    wanted_months = set(months)
    counts = Counter()
    for call in records:
        classification = classify_record(call, wanted_months)
        if not classification:
            continue
        month_key, call_type = classification
        counts[(call_type, month_key)] += 1
        counts[("Total Calls Audited", month_key)] += 1

    return months, counts


def build_audit_csv(start_month, start_year, end_month, end_year):
    months, counts = build_call_audit(start_month, start_year, end_month, end_year)
    output = io.StringIO()
    headers = ["Total Calls", *[month_label(year, month) for year, month in months], "Total"]
    writer = csv.writer(output)
    writer.writerow([f"RingCentral Audit ({audit_label(months)})"])
    writer.writerow([])
    writer.writerow(headers)

    for row_label in ("Total Calls Audited", "Live Answered", "Answering Service"):
        month_counts = [counts[(row_label, month)] for month in months]
        writer.writerow([row_label, *month_counts, sum(month_counts)])

    return output.getvalue()


def csv_filename(start_month, start_year, end_month, end_year):
    start_year, start_month = parse_month_year(start_month, start_year, "start")
    end_year, end_month = parse_month_year(end_month, end_year, "end")
    return f"ringcentral_call_audit_{start_year}-{start_month:02d}_to_{end_year}-{end_month:02d}.csv"
