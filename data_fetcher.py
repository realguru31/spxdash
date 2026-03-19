"""
data_fetcher.py — SPX data fetcher.
  tvDatafeed  → spot price, OHLC, previous close (primary)
  Barchart    → options chain (primary)
Mirrors GEXdon gex_utils.py logic.
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

# tvDatafeed config for SPX (same pattern as GEXdon config.py)
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
# tvDatafeed — spot price + OHLC + prev close
# ═══════════════════════════════════════
def _get_tv_quote() -> dict:
    """
    Fetch SPX spot + OHLC from tvDatafeed.
    Uses daily bar for previousClose, 1-min bar for current spot.
    """
    defaults = {
        "lastPrice": 0, "previousClose": 0, "netChange": 0,
        "percentChange": 0, "highPrice": 0, "lowPrice": 0, "openPrice": 0,
    }
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv = TvDatafeed()

        # Try each exchange
        for ex in TV_EXCHANGES:
            try:
                # Daily bars for prev close + today OHLC
                daily = tv.get_hist(symbol=TV_SYMBOL, exchange=ex,
                                    interval=Interval.in_daily, n_bars=3)
                if daily is not None and len(daily) >= 2:
                    today_bar = daily.iloc[-1]
                    prev_bar = daily.iloc[-2]

                    spot = float(today_bar["close"])
                    prev_close = float(prev_bar["close"])
                    net_chg = spot - prev_close
                    pct_chg = (net_chg / prev_close * 100) if prev_close > 0 else 0

                    result = {
                        "lastPrice": spot,
                        "previousClose": prev_close,
                        "netChange": round(net_chg, 2),
                        "percentChange": round(pct_chg, 2),
                        "highPrice": float(today_bar["high"]),
                        "lowPrice": float(today_bar["low"]),
                        "openPrice": float(today_bar["open"]),
                    }
                    logger.info("tvDatafeed quote OK via %s: SPX=%.2f prevClose=%.2f chg=%.2f (%.2f%%)",
                               ex, spot, prev_close, net_chg, pct_chg)
                    return result

            except Exception as e:
                logger.debug("tvDatafeed %s/%s failed: %s", TV_SYMBOL, ex, e)
                continue

    except ImportError:
        logger.warning("tvDatafeed not installed — falling back to Barchart for quote")
    except Exception as e:
        logger.warning("tvDatafeed failed: %s", e)

    return defaults


def _get_tv_spot() -> Optional[float]:
    """Quick spot price from tvDatafeed 1-min bar."""
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv = TvDatafeed()
        for ex in TV_EXCHANGES:
            try:
                df = tv.get_hist(symbol=TV_SYMBOL, exchange=ex,
                                 interval=Interval.in_1_minute, n_bars=1)
                if df is not None and not df.empty:
                    return float(df["close"].iloc[-1])
            except Exception:
                continue
    except ImportError:
        pass
    return None


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
            logger.error("No XSRF-TOKEN cookie. Got: %s", list(cookies.keys()))
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
    """tvDatafeed first (reliable OHLC + prevClose), Barchart fallback."""

    # Try tvDatafeed first
    result = _get_tv_quote()
    if result.get("lastPrice", 0) > 0:
        return result

    logger.info("tvDatafeed failed → Barchart fallback for quote")

    # Barchart fallback
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
        data = r.json()
        items = data.get("data", [])
        if items:
            raw_list = items if isinstance(items, list) else [items]
            for item in raw_list:
                raw = item.get("raw", item)
                lp = raw.get("lastPrice")
                if lp is not None:
                    spot = _clean(lp)
                    pct = _clean(raw.get("percentChange", 0))
                    # Compute prev close from pct if not provided
                    pc = _clean(raw.get("previousClose", 0))
                    if pc == 0 and pct != 0 and spot > 0:
                        pc = round(spot / (1 + pct / 100), 2)
                    nc = _clean(raw.get("netChange", 0))
                    if nc == 0 and pc > 0:
                        nc = round(spot - pc, 2)
                    return {
                        "lastPrice": spot,
                        "previousClose": pc,
                        "netChange": nc,
                        "percentChange": pct,
                        "highPrice": _clean(raw.get("highPrice", 0)),
                        "lowPrice": _clean(raw.get("lowPrice", 0)),
                        "openPrice": _clean(raw.get("openPrice", 0)),
                    }
    except Exception as e:
        logger.error("Barchart quote failed: %s", e)

    return defaults


def get_spx_price() -> Optional[float]:
    # Try tvDatafeed spot first (fastest)
    spot = _get_tv_spot()
    if spot and spot > 0:
        return spot
    q = get_spx_quote()
    p = q.get("lastPrice", 0)
    return p if p > 0 else None


# ═══════════════════════════════════════
# Expiry Dates
# ═══════════════════════════════════════
def get_expirations() -> List[str]:
    if not _ensure_session():
        return _calculate_expiry_dates()
    if _page_html:
        dates = _parse_expiry_dates_from_html(_page_html)
        if dates:
            return dates
    return _calculate_expiry_dates()


def _parse_expiry_dates_from_html(html) -> List[str]:
    try:
        import pytz
        et = datetime.now(pytz.timezone("US/Eastern"))
        today_str = et.strftime("%Y-%m-%d")
    except Exception:
        today_str = datetime.now().strftime("%Y-%m-%d")

    all_dates = re.findall(r'20\d{2}-\d{2}-\d{2}', html)
    valid = sorted(set(d for d in all_dates if d >= today_str))

    try:
        import pytz
        et_now = datetime.now(pytz.timezone("US/Eastern"))
    except Exception:
        et_now = datetime.now()
    if et_now.weekday() < 5:
        if today_str not in (valid or []):
            valid = [today_str] + (valid or [])

    return valid if valid else []


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
# Options Chain (Barchart)
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
            "orderDir": "asc",
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
            logger.warning("Chain returned 0 rows for %s", expiry)
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
            vol_nonzero = df["volatility"][df["volatility"] > 0]
            if len(vol_nonzero) > 0:
                median_vol = vol_nonzero.median()
                if median_vol > 1.0:
                    df["iv_decimal"] = df["volatility"] / 100.0
                else:
                    df["iv_decimal"] = df["volatility"]
            else:
                df["iv_decimal"] = df["volatility"]
        else:
            df["iv_decimal"] = 0.0

        logger.info("Chain %s: %d rows (%d Call, %d Put)",
                    expiry, len(df),
                    len(df[df["optionType"] == "Call"]),
                    len(df[df["optionType"] == "Put"]))
        return df

    except Exception as e:
        logger.error("Chain fetch failed for %s: %s", expiry, e)
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
        out[f"{prefix}_bid"] = side_df["bid"].values if "bid" in side_df.columns else 0
        out[f"{prefix}_ask"] = side_df["ask"].values if "ask" in side_df.columns else 0
        out[f"{prefix}_last"] = side_df["lastPrice"].values
        out[f"{prefix}_high"] = side_df["highPrice"].values if "highPrice" in side_df.columns else 0
        out[f"{prefix}_low"] = side_df["lowPrice"].values if "lowPrice" in side_df.columns else 0
        out[f"{prefix}_open"] = side_df["openPrice"].values if "openPrice" in side_df.columns else 0
        out[f"{prefix}_mark"] = side_df["lastPrice"].values
        out[f"{prefix}_delta"] = side_df["delta"].values
        out[f"{prefix}_gamma"] = side_df["gamma"].values
        out[f"{prefix}_vega"] = side_df["vega"].values if "vega" in side_df.columns else 0
        out[f"{prefix}_theta"] = side_df["theta"].values if "theta" in side_df.columns else 0
        out[f"{prefix}_iv"] = side_df["iv_decimal"].values
        out[f"{prefix}_oi"] = side_df["openInterest"].values
        out[f"{prefix}_volume"] = side_df["volume"].values if "volume" in side_df.columns else 0
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

    logger.info("Merged chain: %d strikes", len(merged))
    return merged


def get_active_source() -> str:
    return "barchart" if _session is not None else "none"
