import requests
import pandas as pd
from datetime import datetime
import pytz

# --------------------------------------------
# CONFIG
# --------------------------------------------
SAVE_PATH = "news_calendar.csv"
TARGET_CURRENCY = "USD"
MIN_IMPORTANCE = ["High", "Medium"]

# --------------------------------------------
# 1️⃣ Fetch calendar data from Investing.com proxy
# --------------------------------------------
def fetch_calendar():
    url = "https://economic-calendar-api.p.rapidapi.com/calendar"
    headers = {
        "x-rapidapi-host": "economic-calendar-api.p.rapidapi.com",
        "x-rapidapi-key": "demo"  # Replace with your free RapidAPI key
    }
    params = {"country": "United States", "importance": "1,2", "limit": 50}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()["data"]

# --------------------------------------------
# 2️⃣ Normalize and save to CSV
# --------------------------------------------
def build_csv(events):
    rows = []
    for e in events:
        try:
            title = e.get("event", "")
            impact = e.get("impact", "Medium")
            currency = e.get("currency", "USD")
            date_str = e.get("date", "")
            time_str = e.get("time", "")

            if currency != TARGET_CURRENCY or impact not in MIN_IMPORTANCE:
                continue

            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            dt_utc = pytz.timezone("US/Eastern").localize(dt).astimezone(pytz.UTC)
            rows.append([dt_utc.strftime("%Y-%m-%d %H:%M"), impact, currency, title])
        except Exception:
            continue

    df = pd.DataFrame(rows, columns=["datetime", "impact", "currency", "title"])
    df.to_csv(SAVE_PATH, index=False, header=False)
    print(f"✅ Updated {SAVE_PATH} with {len(df)} events.")

# --------------------------------------------
# MAIN
# --------------------------------------------
if __name__ == "__main__":
    try:
        print("🔹 Fetching latest economic calendar...")
        data = fetch_calendar()
        build_csv(data)
    except Exception as e:
        print("❌ Failed to update calendar:", str(e))
        raise
