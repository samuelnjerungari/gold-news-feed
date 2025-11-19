#!/usr/bin/env python3
"""
macro_signal_pro.py
Refined Macro Signal for Gold (Production Ready):
- Uses custom headers to bypass Yahoo IP blocking in GitHub Actions
- Analyzes Technicals (Gold, Yields, DXY)
- Adds "Time-Based" Volatility safety check (NY Session news windows)
- Writes output to CSV
"""
import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime, timezone, timedelta

# ---------------- CONFIG ----------------
OUTPUT = "macro_signal.csv"

# Tickers for Correlation Analysis
TICKERS = {
    "GOLD": "GC=F",    # Gold Futures
    "DXY": "DX-Y.NYB", # Dollar Index
    "VIX": "^VIX",     # Fear Index
    "YIELD": "^TNX",   # 10-Year Treasury Yield (The Anti-Gold)
    "BONDS": "TIP"     # Bond ETF (Real Yield Proxy)
}

# ---------------- HELPERS ----------------

def get_session():
    """
    Creates a browser-like session to avoid Yahoo blocking GitHub Actions IPs.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    })
    return session

def is_high_impact_window():
    """
    Checks if current time is within a standard US News Release window.
    Common High Impact Times: 08:30 AM ET (CPI/NFP), 10:00 AM ET (Consumer Conf), 02:00 PM ET (FOMC)
    """
    now_utc = datetime.now(timezone.utc)
    # Convert UTC to Eastern Time (approx UTC-5 or UTC-4) - Simplifying to UTC offsets for speed
    # Winter (EST) is UTC-5. Summer (EDT) is UTC-4. 
    # Let's stick to UTC for robustness. 
    # 8:30 AM EST = 13:30 UTC (Winter) / 12:30 UTC (Summer)
    
    current_hour = now_utc.hour
    current_minute = now_utc.minute
    
    # Simple "Danger Zone" logic (Adjust as needed)
    # Zone 1: 12:00 UTC to 15:00 UTC (US Morning Session Open + Data)
    if 12 <= current_hour <= 15:
        return 1 # Warning: High Volatility Window
        
    return 0 # Safe(r) Window

def get_market_regime(lookback_days=5):
    """
    Fetches closing data and determines the micro-trend using the robust session.
    """
    session = get_session()
    
    # Pass the session to yfinance to prevent 403 Errors
    try:
        # We use tickers as a list
        ticker_list = list(TICKERS.values())
        data = yf.download(ticker_list, period=f"{lookback_days}d", progress=False, session=session)['Close']
        
        if data.empty or len(data) < 2:
            print("[Error] YFinance returned empty data.")
            return None
            
        signals = {}

        # 1. GOLD MOMENTUM
        gold_price = data[TICKERS["GOLD"]]
        gold_change = (gold_price.iloc[-1] - gold_price.iloc[0]) / gold_price.iloc[0]
        signals['gold_bias'] = 1 if gold_change > 0.002 else (-1 if gold_change < -0.002 else 0)

        # 2. YIELD SIGNAL (The "Real" Driver)
        # Rising Yields = Bearish Gold
        yield_price = data[TICKERS["YIELD"]]
        yield_change = (yield_price.iloc[-1] - yield_price.iloc[0]) / yield_price.iloc[0]
        
        if yield_change > 0.015:    signals['yield_pressure'] = -1 # Bearish for Gold
        elif yield_change < -0.015: signals['yield_pressure'] = 1  # Bullish for Gold
        else:                       signals['yield_pressure'] = 0

        # 3. DXY SIGNAL (Inverse Correlation)
        dxy_price = data[TICKERS["DXY"]]
        dxy_change = (dxy_price.iloc[-1] - dxy_price.iloc[0]) / dxy_price.iloc[0]
        signals['dxy_signal'] = -1 if dxy_change > 0.002 else (1 if dxy_change < -0.002 else 0)

        # 4. VIX SIGNAL (Fear = Gold Bullish)
        vix_price = data[TICKERS["VIX"]]
        vix_now = vix_price.iloc[-1]
        signals['vix_signal'] = 1 if vix_now > 18 else 0 # If fear is high, Gold is bid

        return signals

    except Exception as e:
        print(f"[Critical Error] Data fetch failed: {e}")
        return None

# ---------------- MAIN ----------------
def main():
    regime = get_market_regime()
    
    if regime is None:
        # Fail safe: Write a neutral/hold signal so EA doesn't crash
        row = [datetime.now(timezone.utc).isoformat(), "0", "0", "0", "0", "0"]
    else:
        # Scoring
        total_score = regime['gold_bias'] + regime['yield_pressure'] + regime['dxy_signal'] + regime['vix_signal']
        
        # Logic: If Yields are crushing Gold (-1) and DXY is strong (-1), Score is -2.
        
        high_impact = is_high_impact_window()
        
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        
        # Create Row for CSV: 
        # timestamp, total_score, gold_bias, yield_pressure, dxy_signal, high_impact_flag
        row = [
            ts, 
            str(total_score), 
            str(regime['gold_bias']), 
            str(regime['yield_pressure']), 
            str(regime['dxy_signal']), 
            str(high_impact)
        ]

        # Console Output for Debugging in GitHub Actions
        interpretation = "NEUTRAL"
        if total_score >= 2: interpretation = "STRONG BUY"
        elif total_score <= -2: interpretation = "STRONG SELL"
        
        print(f"--- MACRO REPORT {ts} ---")
        print(f"Signal: {interpretation} (Score: {total_score})")
        print(f"Drivers: Gold({regime['gold_bias']}) Yields({regime['yield_pressure']}) DXY({regime['dxy_signal']})")
        print(f"News Window: {'YES' if high_impact else 'NO'}")

    # Write to CSV (Overwriting mode 'w' to keep it light)
    try:
        with open(OUTPUT, "w", newline="") as f:
            header = "timestamp,total_score,gold_bias,yield_pressure,dxy_signal,high_impact\n"
            f.write(header)
            f.write(",".join(row) + "\n")
        print(f"[Success] Wrote signal to {OUTPUT}")
    except Exception as e:
        print(f"[Error] Could not write CSV: {e}")

if __name__ == "__main__":
    main()
