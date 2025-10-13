import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# --- CONFIG ---
API_URL = "https://ultimate-economic-calendar.p.rapidapi.com/economic-events/tradingview"
API_KEY = os.getenv("RAPIDAPI_KEY", "").strip()

COUNTRIES = "US"
CSV_PATH = "news_calendar.csv"

# --- FETCH DATA ---
def fetch_news():
    today = datetime.now(timezone.utc)
    from_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")

    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "ultimate-economic-calendar.p.rapidapi.com"
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
    events = fetch_news()
    if not events:
        print("⚠️ No events returned from API.")
        return

    rows = []
    for ev in events:
        try:
            date_str = ev["date"][:16].replace("T", " ")  # e.g. 2024-10-15 12:30
            impact = ev.get("impact", "")
            currency = ev.get("country", "")
            title = ev.get("title", "")
            rows.append([date_str, impact, currency, title])
        except Exception as e:
            print("⚠️ Parse error:", e)

    df = pd.DataFrame(rows, columns=["datetime", "impact", "currency", "title"])
    df = df.sort_values("datetime")

    # Save to CSV
    df.to_csv(CSV_PATH, index=False, header=False)
    print(f"✅ Updated {CSV_PATH} with {len(df)} events.")

if __name__ == "__main__":
    update_news_calendar()
