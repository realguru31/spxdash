"""
data_fetcher.py — SPX data fetcher.
  tvDatafeed  → spot, OHLC, previous close
  Barchart    → options chain (orderDir=desc, auto-retry 401 with fresh session)
"""

import re, logging, requests, time
import numpy as np, pandas as pd
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
_session_time = 0


def _clean(v):
    if v is None: return 0.0
    try: return float(str(v).replace(",","").replace("%","").replace("+","").strip())
    except: return 0.0


# ═══════════════════════════════════════
# tvDatafeed
# ═══════════════════════════════════════
def _get_tv_quote() -> dict:
    defaults = {"lastPrice":0,"previousClose":0,"netChange":0,"percentChange":0,"highPrice":0,"lowPrice":0,"openPrice":0}
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv = TvDatafeed()
        for ex in TV_EXCHANGES:
            try:
                daily = tv.get_hist(symbol=TV_SYMBOL, exchange=ex, interval=Interval.in_daily, n_bars=3)
                if daily is not None and len(daily) >= 2:
                    t, p = daily.iloc[-1], daily.iloc[-2]
                    spot = float(t["close"]); pc = float(p["close"])
                    nc = spot - pc; pct = (nc/pc*100) if pc>0 else 0
                    logger.info("tvDatafeed via %s: %.2f prev=%.2f chg=%.2f (%.2f%%)", ex, spot, pc, nc, pct)
                    return {"lastPrice":spot,"previousClose":pc,"netChange":round(nc,2),"percentChange":round(pct,2),
                            "highPrice":float(t["high"]),"lowPrice":float(t["low"]),"openPrice":float(t["open"])}
            except: continue
    except ImportError: logger.warning("tvDatafeed not installed")
    except Exception as e: logger.warning("tvDatafeed: %s", e)
    return defaults


# ═══════════════════════════════════════
# Barchart Session — auto-refresh every 10 min
# ═══════════════════════════════════════
def _create_session():
    global _session, _api_headers, _page_html, _session_time
    page_url = f"https://www.barchart.com/{PAGE_TYPE}/quotes/{BASE_SYM}/volatility-greeks"
    try:
        sess = requests.Session()
        r = sess.get(page_url, params={"page":"all"}, headers={
            "accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-encoding":"gzip, deflate, br","accept-language":"en-US,en;q=0.9",
            "cache-control":"max-age=0","upgrade-insecure-requests":"1","user-agent":_UA,
        }, timeout=15)
        r.raise_for_status(); _page_html = r.text
        cookies = sess.cookies.get_dict()
        if "XSRF-TOKEN" not in cookies:
            logger.error("No XSRF-TOKEN"); return False
        xsrf = unquote(cookies["XSRF-TOKEN"])
        _api_headers = {"accept":"application/json","accept-encoding":"gzip, deflate, br",
            "accept-language":"en-US,en;q=0.9","referer":page_url,"user-agent":_UA,"x-xsrf-token":xsrf}
        _session = sess; _session_time = time.time()
        logger.info("Barchart session OK. XSRF: %s…", xsrf[:20])
        return True
    except Exception as e:
        logger.error("Session failed: %s", e); return False


def _ensure_session():
    # Refresh session if older than 10 minutes
    if _session is None or _api_headers is None or (time.time() - _session_time > 600):
        return _create_session()
    return True


# ═══════════════════════════════════════
# Quote
# ═══════════════════════════════════════
def get_spx_quote() -> dict:
    result = _get_tv_quote()
    if result.get("lastPrice",0) > 0: return result
    logger.info("tvDatafeed failed → Barchart fallback")
    defaults = {"lastPrice":0,"previousClose":0,"netChange":0,"percentChange":0,"highPrice":0,"lowPrice":0,"openPrice":0}
    if not _ensure_session(): return defaults
    try:
        r = _session.get(QUOTE_API, params={"symbols":BASE_SYM,
            "fields":"lastPrice,previousClose,netChange,percentChange,highPrice,lowPrice,openPrice"},
            headers=_api_headers, timeout=10)
        r.raise_for_status()
        items = r.json().get("data",[])
        if items:
            raw = (items[0] if isinstance(items,list) else items).get("raw", items[0] if isinstance(items,list) else items)
            lp = raw.get("lastPrice")
            if lp is not None:
                spot=_clean(lp); pct=_clean(raw.get("percentChange",0))
                pc=_clean(raw.get("previousClose",0))
                if pc==0 and pct!=0 and spot>0: pc=round(spot/(1+pct/100),2)
                nc=_clean(raw.get("netChange",0))
                if nc==0 and pc>0: nc=round(spot-pc,2)
                return {"lastPrice":spot,"previousClose":pc,"netChange":nc,"percentChange":pct,
                        "highPrice":_clean(raw.get("highPrice",0)),"lowPrice":_clean(raw.get("lowPrice",0)),
                        "openPrice":_clean(raw.get("openPrice",0))}
    except Exception as e: logger.error("Barchart quote: %s", e)
    return defaults


def get_spx_price() -> Optional[float]:
    q = get_spx_quote(); p = q.get("lastPrice",0); return p if p > 0 else None


# ═══════════════════════════════════════
# Chain — auto-retry 401 with fresh session
# ═══════════════════════════════════════
def _fetch_single_chain(expiry: str) -> Optional[pd.DataFrame]:
    global _session
    for attempt in range(2):
        if not _ensure_session(): return None
        try:
            r = _session.get(OPTIONS_API, params={
                "baseSymbol":BASE_SYM,"groupBy":"optionType","expirationDate":expiry,
                "orderBy":"strikePrice","orderDir":"desc","raw":"1",
                "meta":"field.shortName,field.type,field.description",
                "fields":"symbol,strikePrice,lastPrice,volatility,delta,gamma,theta,vega,volume,openInterest,optionType,highPrice,lowPrice,openPrice,ask,bid",
            }, headers=_api_headers, timeout=15)
            if r.status_code == 401:
                logger.warning("Chain 401 → refreshing session (attempt %d)", attempt+1)
                _session = None
                continue
            r.raise_for_status()
            rows = []; raw_data = r.json().get("data",{})
            if isinstance(raw_data, dict):
                for ot, opts in raw_data.items():
                    if isinstance(opts, list):
                        for o in opts:
                            rec = o.get("raw",o) if isinstance(o,dict) else o
                            if isinstance(rec,dict): rec["optionType"]=ot; rows.append(rec)
            elif isinstance(raw_data, list):
                for o in raw_data:
                    rec = o.get("raw",o) if isinstance(o,dict) else o
                    if isinstance(rec,dict): rows.append(rec)
            if not rows: logger.warning("Chain 0 rows for %s", expiry); return None
            df = pd.DataFrame(rows)
            for col in ["strikePrice","lastPrice","volatility","delta","gamma","theta","vega",
                         "volume","openInterest","highPrice","lowPrice","openPrice","ask","bid"]:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            df["openInterest"] = df["openInterest"].astype(int)
            df["volume"] = df["volume"].astype(int) if "volume" in df.columns else 0
            if "volatility" in df.columns:
                vn = df["volatility"][df["volatility"]>0]
                df["iv_decimal"] = df["volatility"]/100.0 if len(vn)>0 and vn.median()>1 else df["volatility"]
            else: df["iv_decimal"] = 0.0
            logger.info("Chain %s: %d rows (%dC/%dP)", expiry, len(df),
                        len(df[df["optionType"]=="Call"]), len(df[df["optionType"]=="Put"]))
            return df
        except Exception as e:
            logger.error("Chain %s: %s", expiry, e)
            if attempt == 0: _session = None; continue
    return None


def get_options_chain(expiration: str, num_strikes: int = 50) -> Optional[pd.DataFrame]:
    df = _fetch_single_chain(expiration)
    if df is None or df.empty: return None
    calls = df[df["optionType"]=="Call"].copy()
    puts = df[df["optionType"]=="Put"].copy()
    if calls.empty and puts.empty: return None
    def _side(sdf, px):
        out = pd.DataFrame(); out["strike"] = sdf["strikePrice"].values
        for src,dst in [("bid","bid"),("ask","ask"),("lastPrice","last"),("highPrice","high"),
                        ("lowPrice","low"),("openPrice","open"),("lastPrice","mark"),
                        ("delta","delta"),("gamma","gamma"),("vega","vega"),("theta","theta"),
                        ("iv_decimal","iv"),("openInterest","oi"),("volume","volume")]:
            out[f"{px}_{dst}"] = sdf[src].values if src in sdf.columns else 0
        return out
    c = _side(calls,"c") if not calls.empty else pd.DataFrame()
    p = _side(puts,"p") if not puts.empty else pd.DataFrame()
    if not c.empty and not p.empty: m = pd.merge(c,p,on="strike",how="outer")
    elif not c.empty: m = c
    else: m = p
    m = m.sort_values("strike",ascending=False).reset_index(drop=True)
    for col in m.select_dtypes(include=[np.number]).columns: m[col] = m[col].fillna(0)
    logger.info("Merged: %d strikes", len(m))
    return m


def get_active_source() -> str:
    return "barchart" if _session is not None else "none"
