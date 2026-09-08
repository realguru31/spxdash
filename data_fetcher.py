"""
data_fetcher.py — SPX data.

  tvDatafeed → live spot / OHLC / prev close
  Barchart   → options chain (live) when minted WAF cookies are available
  CBOE       → options chain (delayed ~15min) as automatic fallback

Barchart sits behind AWS WAF. Cookies are minted by mint_cookies.py in
GitHub Actions and committed to data/session/cookies.json. They only work
from a plain client if the request carries browser-shaped headers AND a
Chrome TLS fingerprint (curl_cffi impersonate) — plain `requests` gets 403.

If cookies are absent, stale or rejected, every path silently falls back to
CBOE, so a broken mint degrades to delayed data instead of a dead app.

Public API unchanged: get_spx_quote, get_spx_price, get_options_chain,
get_expirations, get_active_source.
"""

import os
import re
import json
import time
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# ── Barchart ──
BC_API = "https://www.barchart.com/proxies/core-api/v1/options/get"
BC_PAGE = "https://www.barchart.com/stocks/quotes/$SPX/volatility-greeks"
COOKIE_PATH = "data/session/cookies.json"
BC_FIELDS = ("strikePrice,lastPrice,volatility,delta,gamma,theta,vega,"
             "volume,openInterest,optionType,bidPrice,askPrice,"
             "highPrice,lowPrice,openPrice,baseLastPrice")

# ── CBOE ──
CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json"
_OCC = re.compile(r"^([A-Z]+)(\d{6})([CP])(\d{8})$")

# ── tvDatafeed ──
TV_SYMBOL = "SPX"
TV_EXCHANGES = ["CBOE", "SP", "FOREXCOM", "OANDA", "TVC"]

_cboe_cache = {"ts": 0.0, "raw": None}
_CBOE_TTL = 60
_last_source = "none"


def _f(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


# ═══════════════════════════════════════
# Barchart
# ═══════════════════════════════════════
def _load_cookies() -> Optional[dict]:
    if not os.path.exists(COOKIE_PATH):
        return None
    try:
        with open(COOKIE_PATH) as f:
            blob = json.load(f)
        ck = blob.get("cookies") or {}
        if "aws-waf-token" not in ck or "laravel_session" not in ck:
            logger.warning("cookie file missing required keys")
            return None
        logger.info("Barchart cookies age %.0f min",
                    (time.time() - blob.get("minted_at", 0)) / 60)
        return blob
    except Exception as e:
        logger.warning("cookie load failed: %s", e)
        return None


def _bc_headers(ua: str) -> dict:
    # Origin + Sec-Fetch-Site: same-origin are what WAF checks to tell a real
    # page's XHR from an outside client. Dropping them returns 403.
    return {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BC_PAGE,
        "Origin": "https://www.barchart.com",
        "User-Agent": ua,
        "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }


_DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def _bc_get(params: dict) -> Optional[dict]:
    """One Barchart call. Returns parsed JSON, or None on any failure."""
    blob = _load_cookies()
    if not blob:
        return None
    try:
        from curl_cffi import requests as creq
    except ImportError:
        logger.warning("curl_cffi not installed — Barchart unavailable")
        return None
    try:
        ua = blob.get("user_agent") or _DEFAULT_UA
        s = creq.Session(impersonate="chrome120")
        r = s.get(BC_API, params=params, cookies=blob["cookies"],
                  headers=_bc_headers(ua), timeout=20)
        if r.status_code != 200:
            logger.warning("Barchart %s — falling back to CBOE", r.status_code)
            return None
        return r.json()
    except Exception as e:
        logger.warning("Barchart request failed: %s", e)
        return None


def _bc_chain(expiry: str) -> Optional[pd.DataFrame]:
    """Flat rows for one expiry. orderDir=desc keeps ATM inside the 1000-row cap."""
    j = _bc_get({
        "baseSymbol": "$SPX",
        "groupBy": "optionType",
        "expirationDate": expiry,
        "orderBy": "strikePrice",
        "orderDir": "desc",
        "raw": "1",
        "fields": BC_FIELDS,
    })
    if not j:
        return None

    data = j.get("data") or {}
    rows = []
    for side, opts in (data.items() if isinstance(data, dict) else []):
        if not isinstance(opts, list):
            continue
        for o in opts:
            rec = o.get("raw", o) if isinstance(o, dict) else None
            if not isinstance(rec, dict):
                continue
            bid, ask = _f(rec.get("bidPrice")), _f(rec.get("askPrice"))
            last = _f(rec.get("lastPrice"))
            rows.append({
                "strikePrice": _f(rec.get("strikePrice")),
                "optionType": side,
                "openInterest": int(_f(rec.get("openInterest"))),
                "volume": int(_f(rec.get("volume"))),
                "gamma": _f(rec.get("gamma")),
                "delta": _f(rec.get("delta")),
                "vega": _f(rec.get("vega")),
                "theta": _f(rec.get("theta")),
                "volatility": _f(rec.get("volatility")),
                "bid": bid,
                "ask": ask,
                "mark": round((bid + ask) / 2, 2) if (bid > 0 and ask > 0) else last,
                "lastPrice": last,
                "highPrice": _f(rec.get("highPrice")),
                "lowPrice": _f(rec.get("lowPrice")),
                "openPrice": _f(rec.get("openPrice")),
            })

    if not rows:
        logger.warning("Barchart: no contracts for %s", expiry)
        return None
    logger.info("Barchart chain %s: %d rows", expiry, len(rows))
    return pd.DataFrame(rows)


def _bc_expirations() -> Optional[List[str]]:
    """Real expiry list from meta — weekly + monthly, deduped."""
    j = _bc_get({
        "baseSymbol": "$SPX", "groupBy": "optionType",
        "expirationDate": "nearest", "raw": "1",
        "meta": "expirations", "fields": "strikePrice,optionType",
    })
    if not j:
        return None
    exps = (j.get("meta") or {}).get("expirations") or {}
    out = sorted(set(exps.get("weekly", [])) | set(exps.get("monthly", [])))
    return out or None


# ═══════════════════════════════════════
# CBOE
# ═══════════════════════════════════════
def _cboe_raw(force: bool = False) -> Optional[dict]:
    now = time.time()
    if not force and _cboe_cache["raw"] is not None and (now - _cboe_cache["ts"]) < _CBOE_TTL:
        return _cboe_cache["raw"]
    try:
        r = requests.get(CBOE_URL, timeout=30, headers={
            "accept": "application/json", "user-agent": _DEFAULT_UA})
        r.raise_for_status()
        data = r.json().get("data")
        if not data or "options" not in data:
            return None
        _cboe_cache["raw"], _cboe_cache["ts"] = data, now
        logger.info("CBOE payload: %d contracts", len(data["options"]))
        return data
    except Exception as e:
        logger.error("CBOE fetch failed: %s", e)
        return _cboe_cache["raw"]


def _cboe_chain(expiry: str) -> Optional[pd.DataFrame]:
    raw = _cboe_raw()
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
            "mark": round((bid + ask) / 2, 2) if (bid > 0 and ask > 0) else last,
            "lastPrice": last,
            "highPrice": _f(o.get("high")),
            "lowPrice": _f(o.get("low")),
            "openPrice": _f(o.get("open")),
        })
    if not rows:
        logger.warning("CBOE: no contracts for %s", expiry)
        return None
    logger.info("CBOE chain %s: %d rows", expiry, len(rows))
    return pd.DataFrame(rows)


# ═══════════════════════════════════════
# Quote
# ═══════════════════════════════════════
def _tv_quote() -> dict:
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
                    logger.info("tvDatafeed via %s: %.2f prev=%.2f", ex, spot, pc)
                    return {"lastPrice": spot, "previousClose": pc,
                            "netChange": round(nc, 2),
                            "percentChange": round(nc / pc * 100, 2) if pc > 0 else 0,
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
    q = _tv_quote()
    if q.get("lastPrice", 0) > 0:
        return q
    logger.info("tvDatafeed failed -> CBOE quote fallback")
    raw = _cboe_raw()
    if not raw:
        return q
    spot, pc = _f(raw.get("close")), _f(raw.get("prev_day_close"))
    if spot <= 0:
        return q
    nc = spot - pc if pc > 0 else 0.0
    return {"lastPrice": spot, "previousClose": pc, "netChange": round(nc, 2),
            "percentChange": round(nc / pc * 100, 2) if pc > 0 else 0.0,
            "highPrice": _f(raw.get("high")), "lowPrice": _f(raw.get("low")),
            "openPrice": _f(raw.get("open"))}


def get_spx_price() -> Optional[float]:
    p = get_spx_quote().get("lastPrice", 0)
    return p if p > 0 else None


# ═══════════════════════════════════════
# Expirations
# ═══════════════════════════════════════
def get_expirations(n: int = 30) -> List[str]:
    today = datetime.now().strftime("%Y-%m-%d")

    bc = _bc_expirations()
    if bc:
        return [e for e in bc if e >= today][:n]

    raw = _cboe_raw()
    if raw:
        exps = set()
        for o in raw["options"]:
            m = _OCC.match(o.get("option", ""))
            if m:
                ymd = m.group(2)
                exps.add(f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}")
        if exps:
            return sorted(e for e in exps if e >= today)[:n]

    out, d = [], datetime.now().date()
    for i in range(90):
        c = d + timedelta(days=i)
        if c.weekday() < 5:
            out.append(c.strftime("%Y-%m-%d"))
        if len(out) >= n:
            break
    return out


# ═══════════════════════════════════════
# Chain — one row per strike
# ═══════════════════════════════════════
_AGG_FIELDS = [("bid", "bid"), ("ask", "ask"), ("lastPrice", "last"),
               ("highPrice", "high"), ("lowPrice", "low"), ("openPrice", "open"),
               ("mark", "mark"), ("delta", "delta"), ("gamma", "gamma"),
               ("vega", "vega"), ("theta", "theta"), ("iv_decimal", "iv")]


def _merge(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Aggregate SPX + SPXW at the same strike: OI/volume summed,
    greeks and prices OI-weighted."""
    df = df.copy()
    nz = df["volatility"][df["volatility"] > 0]
    df["iv_decimal"] = df["volatility"] / 100.0 if len(nz) and nz.median() > 1 else df["volatility"]

    def agg(sdf, px):
        if sdf.empty:
            return pd.DataFrame()
        out = []
        for strike, g in sdf.groupby("strikePrice"):
            w = g["openInterest"].values.astype(float)
            ws = w.sum()
            row = {"strike": strike,
                   f"{px}_oi": int(g["openInterest"].sum()),
                   f"{px}_volume": int(g["volume"].sum())}
            for src, dst in _AGG_FIELDS:
                v = g[src].values.astype(float)
                row[f"{px}_{dst}"] = float(np.average(v, weights=w)) if ws > 0 else float(v.mean())
            out.append(row)
        return pd.DataFrame(out)

    c = agg(df[df["optionType"] == "Call"], "c")
    p = agg(df[df["optionType"] == "Put"], "p")
    if c.empty and p.empty:
        return None
    m = pd.merge(c, p, on="strike", how="outer") if (not c.empty and not p.empty) \
        else (c if not c.empty else p)
    m = m.sort_values("strike", ascending=False).reset_index(drop=True)
    for col in m.select_dtypes(include=[np.number]).columns:
        m[col] = m[col].fillna(0)
    return m


def get_options_chain(expiration: str, num_strikes: int = 50) -> Optional[pd.DataFrame]:
    global _last_source

    df = _bc_chain(expiration)
    if df is not None and not df.empty:
        _last_source = "barchart"
    else:
        df = _cboe_chain(expiration)
        if df is None or df.empty:
            _last_source = "none"
            return None
        _last_source = "cboe"

    m = _merge(df)
    if m is None:
        _last_source = "none"
        return None
    logger.info("Merged: %d unique strikes (source=%s)", len(m), _last_source)
    return m


def get_active_source() -> str:
    return _last_source


def get_source_info() -> Tuple[str, str]:
    """(source, human-readable freshness) for display."""
    if _last_source == "barchart":
        blob = _load_cookies()
        age = (time.time() - blob.get("minted_at", 0)) / 60 if blob else 0
        return "barchart", f"live (cookies {age:.0f}m old)"
    if _last_source == "cboe":
        return "cboe", "delayed ~15min"
    return _last_source, "unavailable"


# ═══════════════════════════════════════
# Cookie minting — runs in GitHub Actions only
#   python data_fetcher.py --mint
# Playwright is imported lazily, so the app never needs it installed.
# ═══════════════════════════════════════
_KEEP_COOKIES = ("aws-waf-token", "laravel_session", "bc_anon", "bcFreeUserPageView")


async def _mint_async() -> dict:
    from playwright.async_api import async_playwright

    p = await async_playwright().start()
    browser = await p.chromium.launch(args=[
        "--no-sandbox", "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled"])
    ctx = await browser.new_context(user_agent=_DEFAULT_UA,
                                    viewport={"width": 1440, "height": 900},
                                    locale="en-US")
    page = await ctx.new_page()

    t0 = time.time()
    await page.goto(BC_PAGE, wait_until="domcontentloaded", timeout=60000)

    # WAF solves its challenge in-page, then the app sets laravel_session.
    cookies = {}
    for _ in range(40):
        cookies = {c["name"]: c["value"] for c in await ctx.cookies()}
        if "laravel_session" in cookies and "aws-waf-token" in cookies:
            break
        await page.wait_for_timeout(1000)

    title = await page.title()

    # Verify from inside the page before trusting the cookies.
    verify = await page.evaluate(
        """async (url) => {
            const r = await fetch(url, {headers: {'Accept': 'application/json'},
                                        credentials: 'include'});
            return {status: r.status, len: (await r.text()).length};
        }""",
        BC_API + "?baseSymbol=%24SPX&groupBy=optionType&expirationDate=nearest"
                 "&orderBy=strikePrice&orderDir=desc&raw=1"
                 "&fields=strikePrice,gamma,openInterest,optionType")

    await browser.close()
    await p.stop()

    print(f"solve time: {time.time() - t0:.1f}s")
    print(f"page title: {title[:70]}")
    print(f"cookies: {sorted(cookies)}")
    print(f"in-page verify: status={verify['status']} bytes={verify['len']}")

    if verify["status"] != 200:
        raise RuntimeError(f"in-page verify failed: {verify['status']}")

    kept = {k: v for k, v in cookies.items() if k in _KEEP_COOKIES}
    missing = [k for k in ("aws-waf-token", "laravel_session") if k not in kept]
    if missing:
        raise RuntimeError(f"missing required cookies: {missing}")
    return kept


def mint_cookies() -> dict:
    """Solve the WAF challenge and write COOKIE_PATH. Raises on failure."""
    import asyncio
    os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)
    cookies = asyncio.run(_mint_async())
    blob = {
        "minted_at": int(time.time()),
        "minted_at_iso": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "user_agent": _DEFAULT_UA,
        "cookies": cookies,
    }
    with open(COOKIE_PATH, "w") as f:
        json.dump(blob, f, indent=2)
    print(f"saved {COOKIE_PATH} ({len(cookies)} cookies)")
    return blob


if __name__ == "__main__":
    import sys
    if "--mint" in sys.argv:
        logging.basicConfig(level=logging.INFO)
        mint_cookies()
    else:
        print("usage: python data_fetcher.py --mint")
