"""
snapshot_worker.py — Runs via GitHub Actions at 9:31 ET.
Fetches SPX options chain and saves as today's baseline.
Saves only what's needed for delta panels: strike, volumes, OI, GEX.
"""

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from urllib.parse import unquote
import pytz

# ── Config ──
BASE_SYM = "$SPX"
PAGE_TYPE = "indices"
OPTIONS_API = "https://www.barchart.com/proxies/core-api/v1/options/get"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ── Output path ──
os.makedirs("data/baseline", exist_ok=True)

def get_today_et():
    et = pytz.timezone("US/Eastern")
    return datetime.now(et)

def create_session():
    page_url = f"https://www.barchart.com/{PAGE_TYPE}/quotes/{BASE_SYM}/volatility-greeks"
    sess = requests.Session()
    r = sess.get(page_url, params={"page": "all"}, headers={
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": _UA,
    }, timeout=15)
    r.raise_for_status()
    cookies = sess.cookies.get_dict()
    xsrf = unquote(cookies["XSRF-TOKEN"])
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "referer": page_url,
        "user-agent": _UA,
        "x-xsrf-token": xsrf,
    }
    print(f"Session OK. XSRF: {xsrf[:20]}...")
    return sess, headers

def fetch_chain(sess, headers, expiry):
    r = sess.get(OPTIONS_API, params={
        "baseSymbol": BASE_SYM,
        "groupBy": "optionType",
        "expirationDate": expiry,
        "orderBy": "strikePrice",
        "orderDir": "desc",
        "raw": "1",
        "fields": "strikePrice,volume,openInterest,gamma,optionType",
    }, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", {})
    rows = []
    if isinstance(data, dict):
        for opt_type, opts in data.items():
            if isinstance(opts, list):
                for o in opts:
                    rec = o.get("raw", o)
                    if isinstance(rec, dict):
                        rec["optionType"] = opt_type
                        rows.append(rec)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    for col in ["strikePrice", "volume", "openInterest", "gamma"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["openInterest"] = df["openInterest"].astype(int)
    df["volume"] = df["volume"].astype(int)
    return df

def build_baseline(df):
    """Aggregate by strike, compute GEX, return dict keyed by strike."""
    calls = df[df["optionType"] == "Call"].groupby("strikePrice").agg(
        c_volume=("volume", "sum"),
        c_oi=("openInterest", "sum"),
        c_gamma=("gamma", "mean"),
    ).reset_index()
    puts = df[df["optionType"] == "Put"].groupby("strikePrice").agg(
        p_volume=("volume", "sum"),
        p_oi=("openInterest", "sum"),
        p_gamma=("gamma", "mean"),
    ).reset_index()
    merged = pd.merge(calls, puts, on="strikePrice", how="outer").fillna(0)
    merged["call_gex"] = np.round(merged["c_oi"] * merged["c_gamma"] * 100, 0)
    merged["put_gex"] = -np.round(merged["p_gamma"] * merged["p_oi"] * 100, 0)
    merged["net_gex"] = merged["call_gex"] + merged["put_gex"]

    result = {}
    for _, row in merged.iterrows():
        result[int(row["strikePrice"])] = {
            "c_volume": int(row["c_volume"]),
            "p_volume": int(row["p_volume"]),
            "c_oi": int(row["c_oi"]),
            "p_oi": int(row["p_oi"]),
            "call_gex": float(row["call_gex"]),
            "put_gex": float(row["put_gex"]),
            "net_gex": float(row["net_gex"]),
        }
    return result

def main():
    now_et = get_today_et()
    today_str = now_et.strftime("%Y-%m-%d")
    expiry = today_str  # 0DTE baseline
    print(f"Running baseline snapshot for {expiry} at {now_et.strftime('%H:%M ET')}")

    sess, headers = create_session()
    df = fetch_chain(sess, headers, expiry)

    if df is None or df.empty:
        print(f"No chain data for {expiry} — trying tomorrow")
        from datetime import timedelta
        tomorrow = (now_et.date() + timedelta(days=1)).strftime("%Y-%m-%d")
        df = fetch_chain(sess, headers, tomorrow)
        if df is None or df.empty:
            print("Failed to fetch any chain. Exiting.")
            return
        expiry = tomorrow

    baseline = build_baseline(df)
    output = {
        "date": today_str,
        "expiry": expiry,
        "timestamp_et": now_et.strftime("%Y-%m-%d %H:%M ET"),
        "source": "github_actions",
        "strikes": baseline,
    }

    out_path = f"data/baseline/{today_str}.json"
    with open(out_path, "w") as f:
        json.dump(output, f)

    print(f"Saved {len(baseline)} strikes to {out_path}")

if __name__ == "__main__":
    main()
