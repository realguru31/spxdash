"""
data_fetcher.py — SPX data fetcher.

  tvDatafeed → spot, OHLC, previous close (live)
  CBOE       → options chain (delayed ~15min, free, no auth)

Barchart was dropped: they added AWS WAF, whose token requires a JavaScript
challenge bound to the solving IP, so server-side fetching is not possible.

CBOE returns the FULL chain (all expiries, ~28k contracts) in one call, so
there is no row cap and no orderDir truncation to work around.

Public API unchanged: get_spx_quote, get_spx_price, get_options_chain,
get_expirations, get_active_source.
"""

import re
import time
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json"
TV_SYMBOL = "SPX"
TV_EXCHANGES = ["CBOE", "SP", "FOREXCOM", "OANDA", "TVC"]

# OCC symbol: SPXW260908C07500000 -> root, YYMMDD, C/P, strike*1000
_OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")

# Module-level cache — the CBOE payload is ~5MB and holds every expiry,
# so one fetch serves all expiry selections within the TTL.
_cache = {"ts": 0.0, "raw": None}
_CACHE_TTL = 60


def _f(v) -> float:
    """CBOE sends nulls for untraded contracts."""
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


# ═══════════════════════════════════════
# CBOE payload (cached)
# ═══════════════════════════════════════
def _get_cboe_raw(force: bool = False) -> Optional[dict]:
    now = time.time()
    if not force and _cache["raw"] is not None and (now - _cache["ts"]) < _CACHE_TTL:
        return _cache["raw"]
    try:
        r = requests.get(CBOE_URL, timeout=30, headers={
            "accept": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
        })
        r.raise_for_status()
        data = r.json().get("data")
        if not data or "options" not in data:
            logger.error("CBOE payload missing options")
            return None
        _cache["raw"] = data
        _cache["ts"] = now
        logger.info("CBOE payload: %d contracts", len(data["options"]))
        return data
    except Exception as e:
        logger.error("CBOE fetch failed: %s", e)
        return _cache["raw"]  # serve stale rather than nothing


# ═══════════════════════════════════════
# Quote — tvDatafeed primary, CBOE fallback
# ═══════════════════════════════════════
def _get_tv_quote() -> dict:
    d = {"lastPrice": 0, "previousClose": 0, "netChange": 0,
         "percentChange": 0, "highPrice": 0, "lowPrice": 0, "openPrice": 0}
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv = TvDatafeed()
        for ex in TV_EXCHANGES:
            try:
                daily = tv.get_hist(symbol=TV_SYMBOL, exchange=ex,
                                    interval=Interval.in_daily, n_bars=3)
                if daily is not None and len(daily) >= 2:
                    t, p = daily.iloc[-1], daily.iloc[-2]
                    spot, pc = float(t["close"]), float(p["close"])
                    nc = spot - pc
                    pct = (nc / pc * 100) if pc > 0 else 0
                    logger.info("tvDatafeed via %s: %.2f prev=%.2f chg=%.2f (%.2f%%)",
                                ex, spot, pc, nc, pct)
                    return {"lastPrice": spot, "previousClose": pc,
                            "netChange": round(nc, 2), "percentChange": round(pct, 2),
                            "highPrice": float(t["high"]), "lowPrice": float(t["low"]),
                            "openPrice": float(t["open"])}
            except Exception:
                continue
    except ImportError:
        logger.warning("tvDatafeed not installed")
    except Exception as e:
        logger.warning("tvDatafeed: %s", e)
    return d


def get_spx_quote() -> dict:
    q = _get_tv_quote()
    if q.get("lastPrice", 0) > 0:
        return q

    logger.info("tvDatafeed failed -> CBOE quote fallback")
    raw = _get_cboe_raw()
    if not raw:
        return q
    spot = _f(raw.get("close"))
    pc = _f(raw.get("prev_day_close"))
    if spot <= 0:
        return q
    nc = spot - pc if pc > 0 else 0.0
    return {
        "lastPrice": spot,
        "previousClose": pc,
        "netChange": round(nc, 2),
        "percentChange": round(nc / pc * 100, 2) if pc > 0 else 0.0,
        "highPrice": _f(raw.get("high")),
        "lowPrice": _f(raw.get("low")),
        "openPrice": _f(raw.get("open")),
    }


def get_spx_price() -> Optional[float]:
    p = get_spx_quote().get("lastPrice", 0)
    return p if p > 0 else None


# ═══════════════════════════════════════
# Expirations
# ═══════════════════════════════════════
def get_expirations(n: int = 30) -> List[str]:
    """Real expiries present in the CBOE chain, ascending."""
    raw = _get_cboe_raw()
    if raw:
        exps = set()
        for o in raw["options"]:
            m = _OCC.match(o.get("option", ""))
            if m:
                ymd = m.group(2)
                exps.add(f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}")
        if exps:
            today = datetime.now().strftime("%Y-%m-%d")
            return sorted(e for e in exps if e >= today)[:n]

    # Fallback: next n weekdays
    out, d = [], datetime.now().date()
    for i in range(90):
        c = d + timedelta(days=i)
        if c.weekday() < 5:
            out.append(c.strftime("%Y-%m-%d"))
        if len(out) >= n:
            break
    return out


# ═══════════════════════════════════════
# Options chain
# ═══════════════════════════════════════
def _parse_expiry(expiry: str) -> Optional[pd.DataFrame]:
    """Flat rows for one expiry across all roots (SPX + SPXW)."""
    raw = _get_cboe_raw()
    if not raw:
        return None

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
            "delta": _f(o.get("delta")),
            "vega": _f(o.get("vega")),
            "theta": _f(o.get("theta")),
            "volatility": _f(o.get("iv")),
            "bid": bid,
            "ask": ask,
            # mid when quoted, else last trade
            "mark": round((bid + ask) / 2, 2) if (bid > 0 and ask > 0) else last,
            "lastPrice": last,
            "highPrice": _f(o.get("high")),
            "lowPrice": _f(o.get("low")),
            "openPrice": _f(o.get("open")),
        })

    if not rows:
        logger.warning("CBOE: no contracts for %s", expiry)
        return None

    df = pd.DataFrame(rows)
    # IV: CBOE sends decimal (0.1457). Divide only if a feed change makes it pct.
    nz = df["volatility"][df["volatility"] > 0]
    df["iv_decimal"] = df["volatility"] / 100.0 if len(nz) and nz.median() > 1 else df["volatility"]
    logger.info("Chain %s: %d rows (%dC/%dP)", expiry, len(df),
                int((df.optionType == "Call").sum()), int((df.optionType == "Put").sum()))
    return df


def get_options_chain(expiration: str, num_strikes: int = 50) -> Optional[pd.DataFrame]:
    """One row per strike. SPX + SPXW at the same strike are aggregated:
    OI/volume summed, greeks and prices OI-weighted."""
    df = _parse_expiry(expiration)
    if df is None or df.empty:
        return None

    calls = df[df["optionType"] == "Call"]
    puts = df[df["optionType"] == "Put"]
    if calls.empty and puts.empty:
        return None

    FIELDS = [("bid", "bid"), ("ask", "ask"), ("lastPrice", "last"),
              ("highPrice", "high"), ("lowPrice", "low"), ("openPrice", "open"),
              ("mark", "mark"), ("delta", "delta"), ("gamma", "gamma"),
              ("vega", "vega"), ("theta", "theta"), ("iv_decimal", "iv")]

    def _agg(sdf, px):
        if sdf.empty:
            return pd.DataFrame()
        out = []
        for strike, g in sdf.groupby("strikePrice"):
            w = g["openInterest"].values.astype(float)
            ws = w.sum()
            row = {"strike": strike,
                   f"{px}_oi": int(g["openInterest"].sum()),
                   f"{px}_volume": int(g["volume"].sum())}
            for src, dst in FIELDS:
                v = g[src].values.astype(float)
                row[f"{px}_{dst}"] = float(np.average(v, weights=w)) if ws > 0 else float(v.mean())
            out.append(row)
        return pd.DataFrame(out)

    c, p = _agg(calls, "c"), _agg(puts, "p")
    if not c.empty and not p.empty:
        m = pd.merge(c, p, on="strike", how="outer")
    else:
        m = c if not c.empty else p

    m = m.sort_values("strike", ascending=False).reset_index(drop=True)
    for col in m.select_dtypes(include=[np.number]).columns:
        m[col] = m[col].fillna(0)
    logger.info("Merged: %d unique strikes", len(m))
    return m


def get_active_source() -> str:
    return "cboe" if _cache["raw"] is not None else "none"
