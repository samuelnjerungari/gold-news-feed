#!/usr/bin/env python3
"""
macro_signal_pro.py
Refined Macro Signal for Gold:
- Replaces VADER with financial logic (placeholder for FinBERT)
- Adds US 10Y Yields (The "Anti-Gold")
- Adds TIPS (Real Yield Proxy)
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
# Note: For FinBERT, you would typically use 'transformers' library (heavy)
# from transformers import pipeline 

# ---------------- CONFIG ----------------
OUTPUT = "macro_signal_pro.csv"

# Gold hates higher yields. 
# ^TNX = 10 Year Treasury Yield
# TIP = Treasury Inflation Protected Securities (Price moves inverse to Real Yields)
TICKERS = {
    "GOLD": "GC=F",    # Gold Futures
    "DXY": "DX-Y.NYB", # Dollar Index
    "VIX": "^VIX",     # Fear Index
    "YIELD": "^TNX",   # 10-Year Treasury Yield (CRITICAL FOR GOLD)
    "BONDS": "TIP"     # Bond ETF (Proxy for Real Yields)
}

def get_market_regime(lookback_days=5):
    """
    Fetches closing data and determines the micro-trend.
    """
    data = yf.download(list(TICKERS.values()), period=f"{lookback_days}d", progress=False)['Close']
    
    signals = {}
    
    # 1. GOLD SIGNAL (Momentum)
    # If Gold is higher than 3 days ago -> Bullish
    gold_change = (data[TICKERS["GOLD"]].iloc[-1] - data[TICKERS["GOLD"]].iloc[0]) / data[TICKERS["GOLD"]].iloc[0]
    signals['gold_bias'] = 1 if gold_change > 0.002 else (-1 if gold_change < -0.002 else 0)

    # 2. YIELD SIGNAL (The "Real" Driver)
    # If Yields (^TNX) are RISING, that is BEARISH for Gold.
    yield_change = (data[TICKERS["YIELD"]].iloc[-1] - data[TICKERS["YIELD"]].iloc[0]) / data[TICKERS["YIELD"]].iloc[0]
    if yield_change > 0.01: # Yields up 1%
        signals['yield_pressure'] = -1 # Bearish for Gold
    elif yield_change < -0.01:
        signals['yield_pressure'] = 1  # Bullish for Gold
    else:
        signals['yield_pressure'] = 0

    # 3. DXY SIGNAL (Inverse Correlation)
    dxy_change = (data[TICKERS["DXY"]].iloc[-1] - data[TICKERS["DXY"]].iloc[0]) / data[TICKERS["DXY"]].iloc[0]
    signals['dxy_signal'] = -1 if dxy_change > 0.002 else (1 if dxy_change < -0.002 else 0)

    return signals

def main():
    regime = get_market_regime()
    
    # Simple scoring model
    # Yield Pressure is usually the strongest driver for Gold
    total_score = regime['gold_bias'] + regime['yield_pressure'] + regime['dxy_signal']
    
    # Interpretation
    final_signal = "NEUTRAL"
    if total_score >= 2: final_signal = "STRONG_BUY"
    elif total_score == 1: final_signal = "BUY"
    elif total_score <= -2: final_signal = "STRONG_SELL"
    elif total_score == -1: final_signal = "SELL"

    print(f"--- Gold Macro Regime ---")
    print(f"Gold Momentum: {regime['gold_bias']}")
    print(f"Yield Pressure: {regime['yield_pressure']} (Inverse to Gold)")
    print(f"DXY Signal:    {regime['dxy_signal']}")
    print(f"Total Score:   {total_score} -> {final_signal}")

if __name__ == "__main__":
    main()
