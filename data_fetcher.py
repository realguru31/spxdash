"""
data_fetcher.py — Barchart SPX options chain fetcher with session/XSRF handling.
Replicates the RTD("tos.rtd",...) data feed from the original Excel workbook.
"""

import requests
import time
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BARCHART_BASE = "https://www.barchart.com"
OPTIONS_URL = f"{BARCHART_BASE}/proxies/core-api/v1/options/chain"
QUOTE_URL = f"{BARCHART_BASE}/proxies/core-api/v1/quotes/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": f"{BARCHART_BASE}/stocks/quotes/$SPX/options",
}

MAX_RETRIES = 3
RETRY_DELAY = 2


class BarchartFetcher:
    """Handles authenticated Barchart session and data retrieval."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.xsrf_token: Optional[str] = None
        self._last_init = 0.0

    # ------------------------------------------------------------------
    # Session bootstrap
    # ------------------------------------------------------------------
    def _init_session(self) -> bool:
        """Visit Barchart to obtain session cookies + XSRF token."""
        if time.time() - self._last_init < 30:
            return self.xsrf_token is not None
        try:
            resp = self.session.get(
                f"{BARCHART_BASE}/stocks/quotes/$SPX/options",
                timeout=15,
            )
            resp.raise_for_status()
            self.xsrf_token = self.session.cookies.get("XSRF-TOKEN")
            if self.xsrf_token:
                self.session.headers["X-XSRF-TOKEN"] = self.xsrf_token
            self._last_init = time.time()
            logger.info("Barchart session initialized (XSRF=%s…)", str(self.xsrf_token)[:12])
            return True
        except Exception as e:
            logger.error("Session init failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # SPX spot price
    # ------------------------------------------------------------------
    def get_spx_price(self) -> Optional[float]:
        """Fetch current SPX last price."""
        for attempt in range(MAX_RETRIES):
            if not self.xsrf_token and not self._init_session():
                continue
            try:
                resp = self.session.get(
                    QUOTE_URL,
                    params={"symbol": "$SPX", "fields": "lastPrice,previousClose,netChange,percentChange,highPrice,lowPrice,openPrice"},
                    timeout=10,
                )
                if resp.status_code == 401:
                    self.xsrf_token = None
                    self._init_session()
                    continue
                resp.raise_for_status()
                data = resp.json()
                results = data.get("data", [])
                if results:
                    return float(results[0].get("lastPrice", 0))
            except Exception as e:
                logger.warning("SPX price attempt %d failed: %s", attempt + 1, e)
                time.sleep(RETRY_DELAY)
        return None

    def get_spx_quote(self) -> dict:
        """Fetch SPX quote with OHLC + change data."""
        defaults = {"lastPrice": 0, "previousClose": 0, "netChange": 0,
                    "percentChange": 0, "highPrice": 0, "lowPrice": 0, "openPrice": 0}
        for attempt in range(MAX_RETRIES):
            if not self.xsrf_token and not self._init_session():
                continue
            try:
                resp = self.session.get(
                    QUOTE_URL,
                    params={"symbol": "$SPX",
                            "fields": "lastPrice,previousClose,netChange,percentChange,highPrice,lowPrice,openPrice"},
                    timeout=10,
                )
                if resp.status_code == 401:
                    self.xsrf_token = None
                    self._init_session()
                    continue
                resp.raise_for_status()
                data = resp.json()
                results = data.get("data", [])
                if results:
                    raw = results[0].get("raw", results[0])
                    return {k: float(raw.get(k, 0)) for k in defaults}
            except Exception as e:
                logger.warning("SPX quote attempt %d: %s", attempt + 1, e)
                time.sleep(RETRY_DELAY)
        return defaults

    # ------------------------------------------------------------------
    # Options chain
    # ------------------------------------------------------------------
    def get_options_chain(self, expiration: str, num_strikes: int = 50) -> Optional[pd.DataFrame]:
        """
        Fetch SPX options chain for a given expiration (YYYY-MM-DD).
        Returns DataFrame with call/put greeks, OI, volume, prices.
        """
        for attempt in range(MAX_RETRIES):
            if not self.xsrf_token and not self._init_session():
                continue
            try:
                params = {
                    "symbol": "$SPX",
                    "fields": "strikePrice,bid,ask,last,highPrice,lowPrice,openPrice,"
                              "mark,delta,gamma,vega,theta,impliedVolatility,openInterest,"
                              "volume,optionType,expirationDate",
                    "expiration": expiration,
                    "meta": "field.shortName,field.type,field.description",
                    "raw": "1",
                    "hasQuotes": "true",
                }
                resp = self.session.get(OPTIONS_URL, params=params, timeout=15)
                if resp.status_code == 401:
                    self.xsrf_token = None
                    self._init_session()
                    continue
                resp.raise_for_status()
                data = resp.json()
                rows = data.get("data", [])
                if not rows:
                    logger.warning("Empty chain for %s", expiration)
                    return None
                df = self._parse_chain(rows)
                return df
            except Exception as e:
                logger.warning("Chain attempt %d: %s", attempt + 1, e)
                time.sleep(RETRY_DELAY)
        return None

    def _parse_chain(self, rows: list) -> pd.DataFrame:
        """Parse raw Barchart JSON rows into a merged call/put DataFrame."""
        records = []
        for row in rows:
            raw = row.get("raw", row)
            records.append({
                "strike": self._float(raw.get("strikePrice")),
                "optionType": raw.get("optionType", ""),
                "bid": self._float(raw.get("bid")),
                "ask": self._float(raw.get("ask")),
                "last": self._float(raw.get("last")),
                "high": self._float(raw.get("highPrice")),
                "low": self._float(raw.get("lowPrice")),
                "open": self._float(raw.get("openPrice")),
                "mark": self._float(raw.get("mark", raw.get("last"))),
                "delta": self._float(raw.get("delta")),
                "gamma": self._float(raw.get("gamma")),
                "vega": self._float(raw.get("vega")),
                "theta": self._float(raw.get("theta")),
                "iv": self._float(raw.get("impliedVolatility")),
                "oi": self._int(raw.get("openInterest")),
                "volume": self._int(raw.get("volume")),
            })

        df = pd.DataFrame(records)
        if df.empty:
            return df

        calls = df[df["optionType"] == "Call"].copy()
        puts = df[df["optionType"] == "Put"].copy()

        calls = calls.rename(columns={c: f"c_{c}" for c in calls.columns if c != "strike"})
        puts = puts.rename(columns={c: f"p_{c}" for c in puts.columns if c != "strike"})
        calls = calls.drop(columns=["c_optionType"], errors="ignore")
        puts = puts.drop(columns=["p_optionType"], errors="ignore")

        merged = pd.merge(calls, puts, on="strike", how="outer").sort_values("strike", ascending=False).reset_index(drop=True)
        return merged

    @staticmethod
    def _float(val) -> float:
        try:
            return float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _int(val) -> int:
        try:
            return int(val) if val is not None else 0
        except (ValueError, TypeError):
            return 0

    # ------------------------------------------------------------------
    # Expirations list
    # ------------------------------------------------------------------
    def get_expirations(self) -> List[str]:
        """Get available SPX expiration dates."""
        for attempt in range(MAX_RETRIES):
            if not self.xsrf_token and not self._init_session():
                continue
            try:
                params = {"symbol": "$SPX", "fields": "expirationDate", "meta": "field.shortName", "raw": "1"}
                resp = self.session.get(OPTIONS_URL, params=params, timeout=10)
                if resp.status_code == 401:
                    self.xsrf_token = None
                    self._init_session()
                    continue
                resp.raise_for_status()
                data = resp.json()
                exps = data.get("meta", {}).get("expirations", [])
                if isinstance(exps, list):
                    return sorted(set(exps))
                return []
            except Exception as e:
                logger.warning("Expirations attempt %d: %s", attempt + 1, e)
                time.sleep(RETRY_DELAY)
        return []


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------
_fetcher = BarchartFetcher()

def get_spx_price() -> Optional[float]:
    return _fetcher.get_spx_price()

def get_spx_quote() -> dict:
    return _fetcher.get_spx_quote()

def get_options_chain(expiration: str, num_strikes: int = 50) -> Optional[pd.DataFrame]:
    return _fetcher.get_options_chain(expiration, num_strikes)

def get_expirations() -> List[str]:
    return _fetcher.get_expirations()
