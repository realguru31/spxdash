"""
data_fetcher.py — Barchart SPX options chain fetcher.
Mirrors GEXdon gex_utils.py session/chain logic.
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

_session = None
_api_headers = None
_page_html = None
_parsed_expiries = []


def _clean(v):
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("%", "").replace("+", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _create_session():
    global _session, _api_headers, _page_html, _parsed_expiries

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

        # Parse available expiry dates from HTML
        _parsed_expiries = _parse_expiry_dates_from_html(_page_html)
        logger.info("Session OK. XSRF: %s… | %d expiries available", xsrf[:20], len(_parsed_expiries))
        if _parsed_expiries:
            logger.info("Available expiries: %s", ", ".join(_parsed_expiries[:10]))
        return True

    except Exception as e:
        logger.error("Session failed: %s", e)
        return False


def _ensure_session():
    if _session is None or _api_headers is None:
        return _create_session()
    return True


# ═══════════════════════════════════════
# SPX Quote
# ═══════════════════════════════════════
def get_spx_quote() -> dict:
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
                    return {
                        "lastPrice": _clean(lp),
                        "previousClose": _clean(raw.get("previousClose", 0)),
                        "netChange": _clean(raw.get("netChange", 0)),
                        "percentChange": _clean(raw.get("percentChange", 0)),
                        "highPrice": _clean(raw.get("highPrice", 0)),
                        "lowPrice": _clean(raw.get("lowPrice", 0)),
                        "openPrice": _clean(raw.get("openPrice", 0)),
                    }
        logger.warning("Quote returned no data")
    except Exception as e:
        logger.error("Quote failed: %s", e)

    # Fallback: parse from HTML
    if _page_html:
        spot = _parse_spot_from_html(_page_html)
        if spot:
            defaults["lastPrice"] = spot
    return defaults


def _parse_spot_from_html(html):
    for pat in [r'"lastPrice"\s*:\s*"?([\d,.]+)"?', r'"last"\s*:\s*"?([\d,.]+)"?']:
        m = re.search(pat, html)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def get_spx_price() -> Optional[float]:
    q = get_spx_quote()
    p = q.get("lastPrice", 0)
    return p if p > 0 else None


# ═══════════════════════════════════════
# Expiry Dates — parsed from Barchart HTML
# ═══════════════════════════════════════
def get_expirations() -> List[str]:
    """Return actual available expiry dates from Barchart."""
    if not _ensure_session():
        return _calculate_expiry_dates()
    if _parsed_expiries:
        return _parsed_expiries
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

    # SPX has daily 0DTE — inject today if weekday
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
# Options Chain
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
