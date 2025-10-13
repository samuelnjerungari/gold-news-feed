import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import pytz
import time

PRIMARY_URLS = [
    "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml",
    "https://cdn.forexfactory.net/ff_calendar_thisweek.xml",
]

# --- Add GitHub-safe proxy fallback ---
FALLBACK_PROXY = (
    "https://r.jina.ai/http://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml"
)

def fetch_calendar():
    urls = PRIMARY_URLS + [FALLBACK_PROXY]
    for url in urls:
        try:
            print(f"🔹 Fetching: {url}")
            response = requests.get(url, timeout=25)
            if response.status_code == 200:
                if response.text.strip().startswith("<") or "xml" in response.text[:100]:
                    print(f"✅ Successfully fetched from {url}")
                    return response.content
            print(f"⚠️ Invalid content from {url} (status {response.status_code})")
        except Exception as e:
            print(f"⚠️ Failed from {url}: {e}")
        time.sleep(2)

    raise RuntimeError("❌ All sources failed — Forex Factory feed unavailable.")

# --- Fetch XML (with retry/fallback) ---
xml_data = fetch_calendar()

# --- Parse events ---
root = ET.fromstring(xml_data)
events = []

for item in root.findall("event"):
    currency = item.findtext("country", "")
    impact = item.findtext("impact", "")
    title = item.findtext("title", "")
    date = item.findtext("date", "")
    time_str = item.findtext("time", "")

    if currency == "USD" and impact in ("High", "Medium"):
        try:
            dt_str = f"{date} {time_str}"
            dt = datetime.strptime(dt_str, "%b %d, %Y %I:%M%p")
            dt_utc = pytz.timezone("US/Eastern").localize(dt).astimezone(pytz.UTC)
            events.append([dt_utc.strftime("%Y-%m-%d %H:%M"), impact, currency, title])
        except Exception as e:
            continue

# --- Save to CSV ---
df = pd.DataFrame(events, columns=["datetime", "impact", "currency", "title"])
df.to_csv("news_calendar.csv", index=False, header=False, encoding="utf-8")

print(f"✅ News calendar updated successfully ({len(df)} events).")
