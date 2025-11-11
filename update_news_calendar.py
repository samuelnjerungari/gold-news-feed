import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import xml.etree.ElementTree as ET # New library for XML parsing

# --- CONFIG ---
# Direct link to Forex Factory's Economic Calendar XML for the current week
RSS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
COUNTRIES = "USD" # Filter for USD events only
CSV_PATH = "news_calendar.csv"

# Optional: days to skip updates (e.g. weekends)
SKIP_DAYS = {5, 6}  # 5 = Saturday, 6 = Sunday

# Optional: minimum hour to start requesting (e.g. after London open)
MIN_REQUEST_HOUR = 6  # UTC hour (since Forex Factory times are generally UTC/GMT)

# --- FETCH DATA ---
def fetch_news():
    """Fetches and parses the XML from the Forex Factory RSS feed."""
    
    print(f"🔹 Fetching news from {RSS_URL}")
    
    try:
        r = requests.get(RSS_URL, timeout=20)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching URL: {e}")
        return []

    # Parse the XML content
    root = ET.fromstring(r.content)
    
    # Forex Factory calendar uses an <event> tag for each news item
    events = []
    for event_tag in root.findall('event'):
        try:
            # Extract fields from the XML structure
            title = event_tag.find('title').text if event_tag.find('title') is not None else ""
            country = event_tag.find('country').text if event_tag.find('country') is not None else ""
            date_str = event_tag.find('date').text if event_tag.find('date') is not None else ""
            time_str = event_tag.find('time').text if event_tag.find('time') is not None else ""
            impact = event_tag.find('impact').text if event_tag.find('impact') is not None else ""
            
            # Combine date and time and standardize to UTC (Forex Factory uses GMT/UTC)
            # Example: '11-11-2025' and '10:00am'
            if date_str and time_str:
                # Replace 'am'/'pm' with AM/PM for easier parsing
                time_str = time_str.replace("am", " AM").replace("pm", " PM").strip()
                # Create a datetime object (this assumes the time is GMT/UTC, which FF usually is)
                dt_obj_naive = datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M %p")
                # Attach the UTC timezone info
                dt_obj_utc = dt_obj_naive.replace(tzinfo=timezone.utc)
                # Format to your EA's expected format (e.g., 'YYYY-MM-DD HH:MM')
                date_time = dt_obj_utc.strftime("%Y-%m-%d %H:%M")
            else:
                date_time = ""

            # Filter for USD and High/Moderate Impact only (Red and Orange folders)
            if country == COUNTRIES and (impact == "High" or impact == "Moderate"):
                events.append([date_time, impact, country, title])

        except Exception as e:
            # Handle cases where an event tag is missing a field
            print(f"⚠️ Parse error for an event: {e}")
            
    return events

# --- UPDATE CSV ---
def update_news_calendar():
    """Checks conditions, fetches news, processes it, and saves the CSV."""
    now = datetime.now(timezone.utc)

    # 🛑 1. Skip weekends
    if now.weekday() in SKIP_DAYS:
        print(f"⏸️ Weekend detected ({now.strftime('%A')}), skipping news update.")
        return

    # 🛑 2. Optional: skip if too early in the day
    if now.hour < MIN_REQUEST_HOUR:
        print(f"⏸️ Before {MIN_REQUEST_HOUR}:00 UTC, no update needed.")
        return

    # ✅ 3. Normal update flow
    events = fetch_news()
    if not events:
        print("⚠️ No relevant events returned from feed.")
        return

    df = pd.DataFrame(events, columns=["datetime", "impact", "currency", "title"])
    df = df.sort_values("datetime")
    
    # Save the file without headers and without the index column
    df.to_csv(CSV_PATH, index=False, header=False)
    print(f"✅ Updated {CSV_PATH} with {len(df)} High/Moderate {COUNTRIES} events.")

if __name__ == "__main__":
    update_news_calendar()
