"""
data_fetcher.py — SPX data fetcher.
  tvDatafeed  → spot, OHLC, previous close
  Barchart    → options chain (orderDir=desc to capture ATM on large OPEX chains)
"""

import re
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import unquote
from typing import Optional, List

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BASE_SYM = "$SPX"
PAGE_TYPE = "indices"
OPTIONS_API = "https://www.barchart.com/proxies/core-api/v1/options/get"
QUOTE_API = "https://www.barchart.com/proxies/core-api/v1/quotes/get"
TV_SYMBOL = "SPX"
TV_EXCHANGES = ["CBOE", "SP", "FOREXCOM", "OANDA"]

_session = None
_api_headers = None
_page_html = None


def _clean(v):
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("%", "").replace("+", "").strip())
    except (ValueError, TypeError):
        return 0.0


# ═══════════════════════════════════════
# tvDatafeed — spot + OHLC + prev close
# ═══════════════════════════════════════
def _get_tv_quote() -> dict:
    defaults = {
        "lastPrice": 0, "previousClose": 0, "netChange": 0,
        "percentChange": 0, "highPrice": 0, "lowPrice": 0, "openPrice": 0,
    }
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv = TvDatafeed()
        for ex in TV_EXCHANGES:
            try:
                daily = tv.get_hist(symbol=TV_SYMBOL, exchange=ex,
                                    interval=Interval.in_daily, n_bars=3)
                if daily is not None and len(daily) >= 2:
                    today_bar = daily.iloc[-1]
                    prev_bar = daily.iloc[-2]
                    spot = float(today_bar["close"])
                    prev_close = float(prev_bar["close"])
                    net_chg = spot - prev_close
                    pct_chg = (net_chg / prev_close * 100) if prev_close > 0 else 0
                    logger.info("tvDatafeed via %s: SPX=%.2f prev=%.2f chg=%.2f (%.2f%%)",
                               ex, spot, prev_close, net_chg, pct_chg)
                    return {
                        "lastPrice": spot,
                        "previousClose": prev_close,
                        "netChange": round(net_chg, 2),
                        "percentChange": round(pct_chg, 2),
                        "highPrice": float(today_bar["high"]),
                        "lowPrice": float(today_bar["low"]),
                        "openPrice": float(today_bar["open"]),
                    }
            except Exception as e:
                logger.debug("tvDatafeed %s failed: %s", ex, e)
                continue
    except ImportError:
        logger.warning("tvDatafeed not installed")
    except Exception as e:
        logger.warning("tvDatafeed failed: %s", e)
    return defaults


# ═══════════════════════════════════════
# Barchart Session
# ═══════════════════════════════════════
def _create_session():
    global _session, _api_headers, _page_html
    page_url = f"https://www.barchart.com/{PAGE_TYPE}/quotes/{BASE_SYM}/volatility-greeks"
    try:
        sess = requests.Session()
        r = sess.get(page_url, params={"page": "all"}, headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": _UA,
        }, timeout=15)
        r.raise_for_status()
        _page_html = r.text
        cookies = sess.cookies.get_dict()
        if "XSRF-TOKEN" not in cookies:
            logger.error("No XSRF-TOKEN. Got: %s", list(cookies.keys()))
            return False
        xsrf = unquote(cookies["XSRF-TOKEN"])
        _api_headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "referer": page_url,
            "user-agent": _UA,
            "x-xsrf-token": xsrf,
        }
        _session = sess
        logger.info("Barchart session OK. XSRF: %s…", xsrf[:20])
        return True
    except Exception as e:
        logger.error("Barchart session failed: %s", e)
        return False


def _ensure_session():
    if _session is None or _api_headers is None:
        return _create_session()
    return True


# ═══════════════════════════════════════
# SPX Quote — tvDatafeed primary, Barchart fallback
# ═══════════════════════════════════════
def get_spx_quote() -> dict:
    result = _get_tv_quote()
    if result.get("lastPrice", 0) > 0:
        return result
    logger.info("tvDatafeed failed → Barchart fallback")
    defaults = {
        "lastPrice": 0, "previousClose": 0, "netChange": 0,
        "percentChange": 0, "highPrice": 0, "lowPrice": 0, "openPrice": 0,
    }
    if not _ensure_session():
        return defaults
    try:
        r = _session.get(QUOTE_API, params={
            "symbols": BASE_SYM,
            "fields": "lastPrice,previousClose,netChange,percentChange,highPrice,lowPrice,openPrice",
        }, headers=_api_headers, timeout=10)
        r.raise_for_status()
        items = r.json().get("data", [])
        if items:
            raw = (items[0] if isinstance(items, list) else items).get("raw", items[0] if isinstance(items, list) else items)
            lp = raw.get("lastPrice")
            if lp is not None:
                spot = _clean(lp)
                pct = _clean(raw.get("percentChange", 0))
                pc = _clean(raw.get("previousClose", 0))
                if pc == 0 and pct != 0 and spot > 0:
                    pc = round(spot / (1 + pct / 100), 2)
                nc = _clean(raw.get("netChange", 0))
                if nc == 0 and pc > 0:
                    nc = round(spot - pc, 2)
                return {
                    "lastPrice": spot, "previousClose": pc, "netChange": nc,
                    "percentChange": pct,
                    "highPrice": _clean(raw.get("highPrice", 0)),
                    "lowPrice": _clean(raw.get("lowPrice", 0)),
                    "openPrice": _clean(raw.get("openPrice", 0)),
                }
    except Exception as e:
        logger.error("Barchart quote failed: %s", e)
    return defaults


def get_spx_price() -> Optional[float]:
    q = get_spx_quote()
    p = q.get("lastPrice", 0)
    return p if p > 0 else None


# ═══════════════════════════════════════
# Expiry Dates
# ═══════════════════════════════════════
def get_expirations() -> List[str]:
    return _calculate_expiry_dates()


def _calculate_expiry_dates(n=30) -> List[str]:
    dates = []
    d = datetime.now().date()
    for i in range(90):
        check = d + timedelta(days=i)
        if check.weekday() < 5:
            dates.append(check.strftime("%Y-%m-%d"))
        if len(dates) >= n:
            break
    return dates


# ═══════════════════════════════════════
# Options Chain — orderDir=desc to capture ATM on large OPEX chains
# ═══════════════════════════════════════
def _fetch_single_chain(expiry: str) -> Optional[pd.DataFrame]:
    if not _ensure_session():
        return None
    try:
        r = _session.get(OPTIONS_API, params={
            "baseSymbol": BASE_SYM,
            "groupBy": "optionType",
            "expirationDate": expiry,
            "orderBy": "strikePrice",
            "orderDir": "desc",
            "raw": "1",
            "meta": "field.shortName,field.type,field.description",
            "fields": (
                "symbol,strikePrice,lastPrice,volatility,delta,gamma,"
                "theta,vega,volume,openInterest,optionType,highPrice,"
                "lowPrice,openPrice,ask,bid"
            ),
        }, headers=_api_headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = []
        raw_data = data.get("data", {})
        if isinstance(raw_data, dict):
            for opt_type, options in raw_data.items():
                if not isinstance(options, list):
                    continue
                for opt in options:
                    rec = opt.get("raw", opt) if isinstance(opt, dict) else opt
                    if isinstance(rec, dict):
                        rec["optionType"] = opt_type
                        rows.append(rec)
        elif isinstance(raw_data, list):
            for opt in raw_data:
                rec = opt.get("raw", opt) if isinstance(opt, dict) else opt
                if isinstance(rec, dict):
                    rows.append(rec)
        if not rows:
            logger.warning("Chain 0 rows for %s", expiry)
            return None
        df = pd.DataFrame(rows)
        for col in ["strikePrice", "lastPrice", "volatility", "delta",
                     "gamma", "theta", "vega", "volume", "openInterest",
                     "highPrice", "lowPrice", "openPrice", "ask", "bid"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        df["openInterest"] = df["openInterest"].astype(int)
        df["volume"] = df["volume"].astype(int) if "volume" in df.columns else 0
        if "volatility" in df.columns:
            vol_nz = df["volatility"][df["volatility"] > 0]
            if len(vol_nz) > 0:
                df["iv_decimal"] = df["volatility"] / 100.0 if vol_nz.median() > 1.0 else df["volatility"]
            else:
                df["iv_decimal"] = df["volatility"]
        else:
            df["iv_decimal"] = 0.0
        logger.info("Chain %s: %d rows (%dC/%dP)", expiry, len(df),
                    len(df[df["optionType"] == "Call"]), len(df[df["optionType"] == "Put"]))
        return df
    except Exception as e:
        logger.error("Chain failed %s: %s", expiry, e)
        return None


def get_options_chain(expiration: str, num_strikes: int = 50) -> Optional[pd.DataFrame]:
    df = _fetch_single_chain(expiration)
    if df is None or df.empty:
        return None
    calls = df[df["optionType"] == "Call"].copy()
    puts = df[df["optionType"] == "Put"].copy()
    if calls.empty and puts.empty:
        return None

    def _build_side(side_df, prefix):
        out = pd.DataFrame()
        out["strike"] = side_df["strikePrice"].values
        for src, dst in [("bid","bid"),("ask","ask"),("lastPrice","last"),
                         ("highPrice","high"),("lowPrice","low"),("openPrice","open"),
                         ("lastPrice","mark"),("delta","delta"),("gamma","gamma"),
                         ("vega","vega"),("theta","theta"),("iv_decimal","iv"),
                         ("openInterest","oi"),("volume","volume")]:
            out[f"{prefix}_{dst}"] = side_df[src].values if src in side_df.columns else 0
        return out

    c_df = _build_side(calls, "c") if not calls.empty else pd.DataFrame()
    p_df = _build_side(puts, "p") if not puts.empty else pd.DataFrame()
    if not c_df.empty and not p_df.empty:
        merged = pd.merge(c_df, p_df, on="strike", how="outer")
    elif not c_df.empty:
        merged = c_df
    else:
        merged = p_df
    merged = merged.sort_values("strike", ascending=False).reset_index(drop=True)
    for col in merged.select_dtypes(include=[np.number]).columns:
        merged[col] = merged[col].fillna(0)
    logger.info("Merged: %d strikes", len(merged))
    return merged


def get_active_source() -> str:
    return "barchart" if _session is not None else "none"
