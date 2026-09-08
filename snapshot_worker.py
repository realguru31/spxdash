"""
snapshot_worker.py — Runs via GitHub Actions at 9:31 ET.
Fetches the SPX chain from CBOE and saves today's baseline.

Saves: per-strike volumes, OI, GEX, plus the ATM straddle price.
Source is CBOE (free, no auth) — Barchart was dropped after they added
AWS WAF, which blocks server-side fetching.
"""

import os
import re
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json"
_OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")
TV_EXCHANGES = ["CBOE", "SP", "FOREXCOM", "OANDA", "TVC"]

os.makedirs("data/baseline", exist_ok=True)


def _f(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def get_today_et():
    return datetime.now(pytz.timezone("US/Eastern"))


def fetch_cboe():
    r = requests.get(CBOE_URL, timeout=30, headers={
        "accept": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    })
    r.raise_for_status()
    data = r.json()["data"]
    print(f"CBOE payload: {len(data['options'])} contracts, close={data.get('close')}")
    return data


def get_spot(raw):
    """tvDatafeed for live spot; CBOE close as fallback."""
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv = TvDatafeed()
        for ex in TV_EXCHANGES:
            try:
                df = tv.get_hist(symbol="SPX", exchange=ex,
                                 interval=Interval.in_1_minute, n_bars=1)
                if df is not None and not df.empty:
                    return float(df["close"].iloc[-1])
            except Exception:
                continue
    except Exception as e:
        print(f"tvDatafeed unavailable: {e}")
    return _f(raw.get("close"))


def chain_for(raw, expiry):
    rows = []
    for o in raw["options"]:
        m = _OCC.match(o.get("option", ""))
        if not m:
            continue
        _, ymd, cp, strike = m.groups()
        if f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}" != expiry:
            continue
        bid, ask = _f(o.get("bid")), _f(o.get("ask"))
        last = _f(o.get("last_trade_price"))
        rows.append({
            "strikePrice": int(strike) / 1000.0,
            "optionType": "Call" if cp == "C" else "Put",
            "openInterest": int(_f(o.get("open_interest"))),
            "volume": int(_f(o.get("volume"))),
            "gamma": _f(o.get("gamma")),
            "mark": round((bid + ask) / 2, 2) if (bid > 0 and ask > 0) else last,
        })
    return pd.DataFrame(rows) if rows else None


def compute_straddle(df, spot):
    """ATM straddle = ATM call mark + ATM put mark at the strike nearest spot."""
    if df is None or df.empty or spot <= 0:
        return None, None, None, None
    atm = round(spot / 5) * 5

    def price(side, target):
        s = df[df["optionType"] == side]
        if s.empty:
            return 0.0, target
        idx = (s["strikePrice"] - target).abs().idxmin()
        row = s.loc[idx]
        return float(row["mark"]), int(row["strikePrice"])

    c_price, c_k = price("Call", atm)
    p_price, p_k = price("Put", atm)
    straddle = round(c_price + p_price, 2)
    print(f"  ATM: {atm}, Call({c_k})={c_price}, Put({p_k})={p_price}, Straddle={straddle}")
    return straddle, atm, c_price, p_price


def build_baseline(df):
    calls = df[df["optionType"] == "Call"].groupby("strikePrice").agg(
        c_volume=("volume", "sum"), c_oi=("openInterest", "sum"), c_gamma=("gamma", "mean"),
    ).reset_index()
    puts = df[df["optionType"] == "Put"].groupby("strikePrice").agg(
        p_volume=("volume", "sum"), p_oi=("openInterest", "sum"), p_gamma=("gamma", "mean"),
    ).reset_index()
    m = pd.merge(calls, puts, on="strikePrice", how="outer").fillna(0)
    m["call_gex"] = np.round(m["c_oi"] * m["c_gamma"] * 100, 0)
    m["put_gex"] = -np.round(m["p_gamma"] * m["p_oi"] * 100, 0)
    m["net_gex"] = m["call_gex"] + m["put_gex"]
    return {
        int(r["strikePrice"]): {
            "c_volume": int(r["c_volume"]), "p_volume": int(r["p_volume"]),
            "c_oi": int(r["c_oi"]), "p_oi": int(r["p_oi"]),
            "call_gex": float(r["call_gex"]), "put_gex": float(r["put_gex"]),
            "net_gex": float(r["net_gex"]),
        }
        for _, r in m.iterrows()
    }


def main():
    now_et = get_today_et()
    today_str = now_et.strftime("%Y-%m-%d")
    print(f"Baseline snapshot: {today_str} at {now_et.strftime('%H:%M ET')}")

    raw = fetch_cboe()
    spot = get_spot(raw)
    print(f"Spot: {spot}")

    expiry = today_str
    df = chain_for(raw, expiry)
    if df is None or df.empty:
        print(f"No chain for {expiry} — trying next weekday")
        d = now_et.date() + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        expiry = d.strftime("%Y-%m-%d")
        df = chain_for(raw, expiry)
        if df is None or df.empty:
            print("Failed to find any chain. Exiting.")
            return

    print(f"Chain {expiry}: {len(df)} contracts")
    straddle, atm_strike, c_price, p_price = compute_straddle(df, spot)
    baseline = build_baseline(df)

    output = {
        "date": today_str,
        "expiry": expiry,
        "timestamp_et": now_et.strftime("%Y-%m-%d %H:%M ET"),
        "source": "github_actions",
        "data_source": "cboe",
        "spot_at_baseline": spot,
        "straddle": {
            "price": straddle, "atm_strike": atm_strike,
            "call_price": c_price, "put_price": p_price,
            "upper": round(spot + straddle, 2) if (spot and straddle) else None,
            "lower": round(spot - straddle, 2) if (spot and straddle) else None,
        },
        "strikes": baseline,
    }

    out_path = f"data/baseline/{today_str}.json"
    with open(out_path, "w") as f:
        json.dump(output, f)
    print(f"Saved {len(baseline)} strikes -> {out_path}")
    print(f"Straddle: {straddle} (upper={output['straddle']['upper']}, "
          f"lower={output['straddle']['lower']})")


if __name__ == "__main__":
    main()
