#!/usr/bin/env python3
"""
macro_signal_pro.py
Refined Macro Signal for Gold (Production Ready - v2.1):
- Fixed: Silences YFinance FutureWarning
- Fixed: Prints VIX status in console log
- Dependencies: curl_cffi, yfinance, pandas
"""
from curl_cffi import requests as curl_requests
import yfinance as yf
import pandas as pd
import os
from datetime import datetime, timezone

# ---------------- CONFIG ----------------
OUTPUT = "macro_signal.csv"

TICKERS = {
    "GOLD": "GC=F",    # Gold Futures
    "DXY": "DX-Y.NYB", # Dollar Index
    "VIX": "^VIX",     # Fear Index
    "YIELD": "^TNX",   # 10-Year Treasury Yield
    "BONDS": "TIP"     # Bond ETF
}

# ---------------- HELPERS ----------------

def get_cffi_session():
    """Creates a browser-impersonating session to bypass Yahoo blocking."""
    return curl_requests.Session(impersonate="chrome")

def is_high_impact_window():
    """Returns 1 if we are in the US Session Morning 'Danger Zone'."""
    now_utc = datetime.now(timezone.utc)
    # 12:00 UTC to 15:00 UTC (approx 8am - 11am NY Time)
    if 12 <= now_utc.hour <= 15:
        return 1 
    return 0

def get_market_regime(lookback_days=5):
    session = get_cffi_session()
    try:
        # Added auto_adjust=True to silence FutureWarning
        ticker_list = list(TICKERS.values())
        data = yf.download(ticker_list, period=f"{lookback_days}d", progress=False, session=session, auto_adjust=True)['Close']
        
        if data.empty or len(data) < 2:
            return None
            
        signals = {}

        # 1. GOLD MOMENTUM
        gold_price = data[TICKERS["GOLD"]]
        gold_change = (gold_price.iloc[-1] - gold_price.iloc[0]) / gold_price.iloc[0]
        signals['gold_bias'] = 1 if gold_change > 0.002 else (-1 if gold_change < -0.002 else 0)

        # 2. YIELD SIGNAL (Inverse to Gold)
        yield_price = data[TICKERS["YIELD"]]
        yield_change = (yield_price.iloc[-1] - yield_price.iloc[0]) / yield_price.iloc[0]
        
        if yield_change > 0.015:    signals['yield_pressure'] = -1 # Bearish for Gold
        elif yield_change < -0.015: signals['yield_pressure'] = 1  # Bullish for Gold
        else:                       signals['yield_pressure'] = 0

        # 3. DXY SIGNAL
        dxy_price = data[TICKERS["DXY"]]
        dxy_change = (dxy_price.iloc[-1] - dxy_price.iloc[0]) / dxy_price.iloc[0]
        signals['dxy_signal'] = -1 if dxy_change > 0.002 else (1 if dxy_change < -0.002 else 0)

        # 4. VIX SIGNAL (Added to print output below)
        vix_price = data[TICKERS["VIX"]]
        vix_now = vix_price.iloc[-1]
        signals['vix_signal'] = 1 if vix_now > 18 else 0

        return signals

    except Exception as e:
        print(f"[Error] Fetch failed: {e}")
        return None

# ---------------- MAIN ----------------
def main():
    regime = get_market_regime()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    if regime is None:
        # Fallback
        row = [ts, "0", "0", "0", "0", "0"]
    else:
        total_score = regime['gold_bias'] + regime['yield_pressure'] + regime['dxy_signal'] + regime['vix_signal']
        high_impact = is_high_impact_window()
        
        row = [
            ts, 
            str(total_score), 
            str(regime['gold_bias']), 
            str(regime['yield_pressure']), 
            str(regime['dxy_signal']),
            str(regime['vix_signal']),
            str(high_impact)
        ]

        print(f"--- MACRO REPORT {ts} ---")
        print(f"Total Score:   {total_score}")
        print(f"Drivers:       Gold({regime['gold_bias']}) Yields({regime['yield_pressure']}) DXY({regime['dxy_signal']}) VIX({regime['vix_signal']})")
        print(f"News Window:   {'DANGER (1)' if high_impact else 'SAFE (0)'}")

    # Write CSV
    try:
        with open(OUTPUT, "w", newline="") as f:
            header = "timestamp,total_score,gold_bias,yield_pressure,dxy_signal,vix_signal,high_impact\n"
            f.write(header)
            f.write(",".join(row) + "\n")
        print(f"[Success] Wrote signal to {OUTPUT}")
    except Exception as e:
        print(f"[Error] Write failed: {e}")

if __name__ == "__main__":
    main()
