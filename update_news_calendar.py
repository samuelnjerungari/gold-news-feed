import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import xml.etree.ElementTree as ET

# --- CONFIG ---
RSS_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
COUNTRIES = "USD"
CSV_PATH = "news_calendar.csv"
SKIP_DAYS = {5, 6}  # Saturday, Sunday
MIN_REQUEST_HOUR = 6

# --- US BANK HOLIDAYS 2025 ---
US_HOLIDAYS_2025 = {
    "2025-01-01": "New Year's Day",
    "2025-01-20": "Martin Luther King Jr. Day",
    "2025-02-17": "Presidents' Day",
    "2025-05-26": "Memorial Day",
    "2025-06-19": "Juneteenth",
    "2025-07-04": "Independence Day",
    "2025-09-01": "Labor Day",
    "2025-11-11": "Veterans Day",  # ← TODAY!
    "2025-11-27": "Thanksgiving",
    "2025-12-25": "Christmas Day"
}

# --- FETCH HOLIDAYS ---
def get_upcoming_holidays():
    """Returns upcoming US bank holidays as events"""
    today = datetime.now(timezone.utc).date()
    holiday_events = []
    
    for date_str, name in US_HOLIDAYS_2025.items():
        holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Only include future holidays or today
        if holiday_date >= today:
            # Set time to midnight for all-day events
            dt_str = f"{date_str} 00:00"
            holiday_events.append([dt_str, "High", "USD", f"🏦 US Bank Holiday: {name}"])
    
    return holiday_events

# --- FETCH NEWS DATA ---
def fetch_news():
    """Fetches and parses the XML from the Forex Factory RSS feed."""
    
    print(f"🔹 Fetching news from {RSS_URL}")
    
    try:
        r = requests.get(RSS_URL, timeout=20)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching URL: {e}")
        return []

    root = ET.fromstring(r.content)
    events = []
    
    for event_tag in root.findall('event'):
        try:
            title = event_tag.find('title').text if event_tag.find('title') is not None else ""
            country = event_tag.find('country').text if event_tag.find('country') is not None else ""
            date_str = event_tag.find('date').text if event_tag.find('date') is not None else ""
            time_str = event_tag.find('time').text if event_tag.find('time') is not None else ""
            impact = event_tag.find('impact').text if event_tag.find('impact') is not None else ""
            
            if date_str and time_str:
                time_str = time_str.replace("am", " AM").replace("pm", " PM").strip()
                dt_obj_naive = datetime.strptime(f"{date_str} {time_str}", "%m-%d-%Y %I:%M %p")
                dt_obj_utc = dt_obj_naive.replace(tzinfo=timezone.utc)
                date_time = dt_obj_utc.strftime("%Y-%m-%d %H:%M")
            else:
                date_time = ""

            # Filter for USD and High/Moderate Impact
            if country == COUNTRIES and (impact == "High" or impact == "Moderate"):
                events.append([date_time, impact, country, title])

        except Exception as e:
            print(f"⚠️ Parse error for an event: {e}")
            
    return events

# --- UPDATE CSV ---
def update_news_calendar():
    """Checks conditions, fetches news + holidays, and saves the CSV."""
    now = datetime.now(timezone.utc)

    # 🛑 Skip weekends
    if now.weekday() in SKIP_DAYS:
        print(f"⏸️ Weekend detected ({now.strftime('%A')}), skipping news update.")
        return

    # 🛑 Skip if too early
    if now.hour < MIN_REQUEST_HOUR:
        print(f"⏸️ Before {MIN_REQUEST_HOUR}:00 UTC, no update needed.")
        return

    # ✅ Fetch news events
    events = fetch_news()
    
    # ✅ Add bank holidays
    holiday_events = get_upcoming_holidays()
    events.extend(holiday_events)
    
    if not events:
        print("⚠️ No relevant events returned from feed.")
        return

    df = pd.DataFrame(events, columns=["datetime", "impact", "currency", "title"])
    df = df.sort_values("datetime")
    
    # Remove duplicates (in case of any overlap)
    df = df.drop_duplicates(subset=["datetime", "title"])
    
    df.to_csv(CSV_PATH, index=False, header=False)
    
    # Count news vs holidays
    news_count = len([e for e in events if "🏦" not in e[3]])
    holiday_count = len([e for e in events if "🏦" in e[3]])
    
    print(f"✅ Updated {CSV_PATH} with:")
    print(f"   📰 {news_count} High/Moderate {COUNTRIES} news events")
    print(f"   🏦 {holiday_count} US bank holidays")
    print(f"   📊 {len(df)} total events")

if __name__ == "__main__":
    update_news_calendar()
