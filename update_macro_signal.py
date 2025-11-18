#!/usr/bin/env python3
"""
update_macro_signal.py
Generates macro_signal.csv for the EA:
timestamp,news_sentiment,dxy_signal,vix_signal,gold_bias,high_impact_event

- news_sentiment: float [-1.0 .. +1.0] (headline aggregate)
- dxy_signal: -1,0,1 (1 = USD strong = bearish for gold)
- vix_signal: -1,0,1 (1 = fear = bullish for gold)
- gold_bias: -1,0,1 (1 = bullish micro gold)
- high_impact_event: 0/1 (1 = an upcoming high impact calendar event in next X hours)
"""
import requests
import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import math

# ---------------- CONFIG ----------------
OUTPUT = "macro_signal.csv"
RECENT_HOURS = 6            # how many hours of headlines to inspect
HEADLINE_FEEDS = [
    "https://www.forexlive.com/feed/news",
    "https://www.dailyfx.com/feeds/market-news",
    "https://www.fxstreet.com/rss",
    "https://www.kitco.com/news/index.rss",
    "https://www.investing.com/rss/news_30.rss",
]
RELEVANT_KEYWORDS = ["gold","xau","xauusd","dxy","dollar","fed","fomc","inflation","cpi","nfp","employment","yield","vix","geopolitical","risk-on","risk-off"]
# calendar CSV produced by your existing gold-news-feed (same repo)
CALENDAR_CSV = "news_calendar.csv"
HIGH_IMPACT_WINDOW_HOURS = 6  # mark event if it occurs within next N hours
USER_AGENT = "MacroSignalBot/1.0 (+https://github.com/yourname)"

# ---------------- HELPERS ----------------
def fetch_headlines():
    analyzer = SentimentIntensityAnalyzer()
    headlines = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=RECENT_HOURS)

    for url in HEADLINE_FEEDS:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            for entry in feed.entries:
                title = (entry.get("title") or "").strip()
                published = entry.get("published") or entry.get("updated") or ""
                # try to parse published to a datetime; fallback to now
                try:
                    pub_dt = None
                    if "published_parsed" in entry and entry.published_parsed:
                        pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_dt = None
                    if not pub_dt:
                        # fallback: ignore time filter if unknown
                        pub_dt = datetime.now(timezone.utc)
                except Exception:
                    pub_dt = datetime.now(timezone.utc)

                # filter recency & keywords
                title_l = title.lower()
                if pub_dt < cutoff and not any(kw in title_l for kw in RELEVANT_KEYWORDS):
                    continue

                if not any(kw in title_l for kw in RELEVANT_KEYWORDS):
                    continue

                score = analyzer.polarity_scores(title)["compound"]
                headlines.append((title, score, pub_dt.isoformat()))
        except Exception as e:
            print(f"[feed error] {url} -> {e}")

    return headlines

def aggregate_headline_sentiment(headlines):
    if not headlines:
        return 0.0
    # weight more recent headlines slightly more
    now = datetime.now(timezone.utc)
    weighted_sum = 0.0
    weight_total = 0.0
    for title, score, iso in headlines:
        try:
            t = datetime.fromisoformat(iso)
            age_hours = max(0.1, (now - t).total_seconds()/3600.0)
            weight = 1.0 / (1.0 + age_hours)   # recent -> higher weight
        except Exception:
            weight = 0.5
        weighted_sum += score * weight
        weight_total += weight
    agg = weighted_sum / weight_total
    # clamp
    return max(-1.0, min(1.0, agg))

def get_yf_signal(ticker, lookback_days=2):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=f"{lookback_days}d", interval="1d")
        if len(hist) < 2:
            return 0.0
        change = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]
        return change
    except Exception as e:
        print(f"[yfinance error] {ticker} -> {e}")
        return 0.0

def discrete_signal_from_change(change, threshold_up=0.01, threshold_down=-0.01):
    if change >= threshold_up:
        return 1
    if change <= threshold_down:
        return -1
    return 0

def detect_high_impact_event():
    # Read your existing news_calendar.csv (if present)
    if not os.path.exists(CALENDAR_CSV):
        return 0
    try:
        df = pd.read_csv(CALENDAR_CSV, names=["datetime","impact","currency","title"], header=None, parse_dates=["datetime"], infer_datetime_format=True)
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=HIGH_IMPACT_WINDOW_HOURS)
        # last column 'title' contains holidays with emoji in your feed
        df = df.dropna(subset=["datetime"])
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        upcoming = df[(df["datetime"] >= now) & (df["datetime"] <= window_end)]
        # consider only High impact or bank holidays
        if len(upcoming) > 0:
            return 1
    except Exception as e:
        print(f"[calendar parse] {e}")
    return 0

# --------------- MAIN ---------------
def main():
    headlines = fetch_headlines()
    news_score = aggregate_headline_sentiment(headlines)
    # DXY: using yfinance DX-Y.NYB
    dxy_change = get_yf_signal("DX-Y.NYB", lookback_days=3)  # fractional change ~ e.g., 0.003 = 0.3%
    dxy_signal = discrete_signal_from_change(dxy_change, threshold_up=0.003, threshold_down=-0.003)
    # VIX: ^VIX (rises -> bullish for gold)
    vix_change = get_yf_signal("^VIX", lookback_days=3)
    vix_signal = discrete_signal_from_change(vix_change, threshold_up=0.06, threshold_down=-0.06)  # adjust thresholds
    # Gold micro bias: GC=F (or "XAUUSD" via yfinance) -> bullish if short-term is up
    gold_change = get_yf_signal("GC=F", lookback_days=3)
    gold_signal = discrete_signal_from_change(gold_change, threshold_up=0.005, threshold_down=-0.005)

    high_impact_flag = detect_high_impact_event()

    # final safety clamps and formatting
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    row = [ts, f"{news_score:.4f}", str(dxy_signal), str(vix_signal), str(gold_signal), str(int(high_impact_flag))]

    # write CSV (single-row, overwrite)
    with open(OUTPUT, "w", newline="") as f:
        f.write(",".join(row) + "\n")

    print("[ok] wrote", OUTPUT, "->", row)

if __name__ == "__main__":
    main()
