import yfinance as yf
import pandas as pd
import numpy as np
import requests
import pytz
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram error: {e}")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calculate_vwap(df):
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cumulative_tp_vol = (typical_price * df["Volume"]).cumsum()
    cumulative_vol = df["Volume"].cumsum()
    df["vwap"] = cumulative_tp_vol / cumulative_vol
    return df

def calculate_atr(df, period=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def is_trading_session():
    """Only run during prime NY session windows."""
    now_et = datetime.now(pytz.timezone("America/New_York"))
    hour = now_et.hour
    minute = now_et.minute
    time_val = hour * 60 + minute
    # Prime: 9:45–11:30 AM and 1:30–3:00 PM ET, Mon–Fri
    prime1 = (9 * 60 + 45) <= time_val <= (11 * 60 + 30)
    prime2 = (13 * 60 + 30) <= time_val <= (15 * 60)
    is_weekday = now_et.weekday() < 5
    return is_weekday and (prime1 or prime2)

def fetch_data():
    ticker = yf.Ticker("NQ=F")  # NASDAQ 100 Futures
    df = ticker.history(period="3d", interval="5m")
    if df.empty or len(df) < 35:
        return None
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.dropna(inplace=True)
    return df

def check_signals(df):
    df["ema9"]  = df["Close"].ewm(span=9, adjust=False).mean()
    df["ema21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["rsi"]   = calculate_rsi(df["Close"])
    df["atr"]   = calculate_atr(df)
    df = calculate_vwap(df)

    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    price = round(last["Close"], 1)
    vwap  = round(last["vwap"], 1)
    rsi   = round(last["rsi"], 1)
    atr   = round(last["atr"], 1)
    sl_pts = round(atr * 1.1, 1)
    tp1_pts = round(sl_pts * 1.5, 1)
    tp2_pts = round(sl_pts * 2.5, 1)

    signals = []

    # --- LONG signal ---
    long_conditions = {
        "EMA9 > EMA21": last["ema9"] > last["ema21"],
        "Price > VWAP": last["Close"] > last["vwap"],
        "Prev close near/below VWAP": prev["Close"] <= last["vwap"] * 1.001,
        "RSI 40-65": 40 <= last["rsi"] <= 65,
        "EMA9 slope up": last["ema9"] > df.iloc[-3]["ema9"],
    }
    if all(long_conditions.values()):
        signals.append({
            "direction": "LONG",
            "emoji": "BUY",
            "entry": price,
            "sl": round(price - sl_pts, 1),
            "tp1": round(price + tp1_pts, 1),
            "tp2": round(price + tp2_pts, 1),
            "vwap": vwap,
            "rsi": rsi,
            "atr": atr,
        })

    # --- SHORT signal ---
    short_conditions = {
        "EMA9 < EMA21": last["ema9"] < last["ema21"],
        "Price < VWAP": last["Close"] < last["vwap"],
        "Prev close near/above VWAP": prev["Close"] >= last["vwap"] * 0.999,
        "RSI 35-60": 35 <= last["rsi"] <= 60,
        "EMA9 slope down": last["ema9"] < df.iloc[-3]["ema9"],
    }
    if all(short_conditions.values()):
        signals.append({
            "direction": "SHORT",
            "emoji": "SELL",
            "entry": price,
            "sl": round(price + sl_pts, 1),
            "tp1": round(price - tp1_pts, 1),
            "tp2": round(price - tp2_pts, 1),
            "vwap": vwap,
            "rsi": rsi,
            "atr": atr,
        })

    return signals

def format_message(sig):
    arrow = "▲" if sig["direction"] == "LONG" else "▼"
    return (
        f"<b>{arrow} US100 {sig['direction']} SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Entry:   <b>{sig['entry']}</b>\n"
        f"SL:      {sig['sl']}  (1.1x ATR)\n"
        f"TP1:     {sig['tp1']}  (1:1.5 RR)\n"
        f"TP2:     {sig['tp2']}  (1:2.5 RR)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"VWAP: {sig['vwap']}  |  RSI: {sig['rsi']}  |  ATR: {sig['atr']}\n"
        f"Strategy: VWAP Momentum Pullback\n"
        f"Timeframe: 5-min · NQ Futures"
    )

def main():
    if not is_trading_session():
        print("Outside trading session window. Skipping.")
        return

    df = fetch_data()
    if df is None:
        print("Could not fetch data.")
        return

    signals = check_signals(df)

    if signals:
        for sig in signals:
            msg = format_message(sig)
            send_telegram(msg)
            print(f"Signal sent: {sig['direction']} @ {sig['entry']}")
    else:
        print("No signal this bar.")

if __name__ == "__main__":
    main()
