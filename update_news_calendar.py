import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime
import pytz

# --- Fetch Forex Factory feed ---
url = "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml"
response = requests.get(url)
xml_data = response.content

root = ET.fromstring(xml_data)
events = []

for item in root.findall("event"):
    currency = item.find("country").text or ""
    impact = item.find("impact").text or ""
    title = item.find("title").text or ""
    date = item.find("date").text or ""
    time_str = item.find("time").text or ""

    if currency == "USD" and impact in ("High", "Medium"):
        try:
            dt_str = f"{date} {time_str}"
            dt = datetime.strptime(dt_str, "%b %d, %Y %I:%M%p")
            dt_utc = pytz.timezone("US/Eastern").localize(dt).astimezone(pytz.UTC)
            events.append([dt_utc.strftime("%Y-%m-%d %H:%M"), impact, currency, title])
        except:
            continue

df = pd.DataFrame(events, columns=["datetime", "impact", "currency", "title"])
csv_text = df.to_csv(index=False, header=False)

with open("news_calendar.csv", "w", encoding="utf-8") as f:
    f.write(csv_text)

print("✅ News calendar updated successfully.")
