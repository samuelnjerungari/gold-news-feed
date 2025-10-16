import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# --- CONFIG ---
API_URL = "https://ultimate-economic-calendar.p.rapidapi.com/economic-events/tradingview"
API_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
COUNTRIES = "US"
CSV_PATH = "news_calendar.csv"

# Optional: days to skip updates (e.g. weekends)
SKIP_DAYS = {5, 6}  # 5 = Saturday, 6 = Sunday

# Optional: minimum hour to start requesting (e.g. after London open)
MIN_REQUEST_HOUR = 6  # UTC hour

# --- FETCH DATA ---
def fetch_news():
    today = datetime.now(timezone.utc)
    from_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "ultimate-economic-calendar.p.rapidapi.com"
    }

    params = {
        "from": from_date,
        "to": to_date,
        "countries": COUNTRIES
    }

    print(f"🔹 Fetching news from {from_date} to {to_date}")
    r = requests.get(API_URL, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data.get("result", [])

# --- UPDATE CSV ---
def update_news_calendar():
    now = datetime.now(timezone.utc)

    # 🛑 1. Skip weekends
    if now.weekday() in SKIP_DAYS:
        print(f"⏸️ Weekend detected ({now.strftime('%A')}), skipping news update.")
        return

    # 🛑 2. Optional: skip if too early in the day
    if now.hour < MIN_REQUEST_HOUR:
        print(f"⏸️ Before {MIN_REQUEST_HOUR}:00 UTC, no update needed.")
        return

    # 🛑 3. Optional: skip if no API key
    if not API_KEY:
        print("❌ No RAPIDAPI_KEY found. Skipping update.")
        return

    # ✅ 4. Normal update flow
    events = fetch_news()
    if not events:
        print("⚠️ No events returned from API.")
        return

    rows = []
    for ev in events:
        try:
            date_str = ev["date"][:16].replace("T", " ")
            impact = ev.get("impact", "")
            currency = ev.get("country", "")
            title = ev.get("title", "")
            rows.append([date_str, impact, currency, title])
        except Exception as e:
            print("⚠️ Parse error:", e)

    df = pd.DataFrame(rows, columns=["datetime", "impact", "currency", "title"])
    df = df.sort_values("datetime")
    df.to_csv(CSV_PATH, index=False, header=False)
    print(f"✅ Updated {CSV_PATH} with {len(df)} events.")

if __name__ == "__main__":
    update_news_calendar()
