"""
tpo.py — Market Profile (TPO) charter with DEVELOPING POC, powered by tvdatafeed.

Enter a TradingView-style symbol + exchange (e.g. NIFTY / NSE), pull intraday
bars, and render BellTPO / NinjaTrader-style profiles side by side:
  - TPO letters grouped into brackets (default 30 min)
  - Volume-at-price histogram (built from the base interval bars)
  - DEVELOPING POC  (TPO point-of-control recomputed after every bracket)
  - DEVELOPING VPOC (volume point-of-control recomputed after every bracket)
  - Developing Value Area (VAH / VAL, 70%)
  - Toggle: render the latest (or any) day SPLIT/EXPANDED — one column per bracket

Single data fetch: bars are pulled at `base_interval`; TPO letters are grouped
from those bars into `bracket_minutes` brackets, and the volume profile is built
from the same bars, so letters and volume always agree.

Version: 0.1.0   (changelog at bottom of file)
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

__version__ = "0.5.0"

# ----------------------------------------------------------------------------- 
# TPO letters: A..Z then a..z  (52 brackets max — plenty for any cash session)
# ----------------------------------------------------------------------------- 
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + \
          [chr(c) for c in range(ord("a"), ord("z") + 1)]


# ----------------------------------------------------------------------------- 
# Core data structures
# ----------------------------------------------------------------------------- 
@dataclass
class DayProfile:
    """Everything needed to draw and analyse one session."""
    day: dt.date
    tick: float
    # price (row low edge) -> ordered list of bracket letters that touched it
    tpo: Dict[float, List[str]] = field(default_factory=dict)
    # price -> total volume
    vol: Dict[float, float] = field(default_factory=dict)
    # bracket letter -> (low_price, high_price) touched in that bracket
    bracket_range: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    brackets: List[str] = field(default_factory=list)      # ordered A,B,C...
    # developing series, one entry per completed bracket
    dev_poc: List[Tuple[str, float]] = field(default_factory=list)
    dev_vpoc: List[Tuple[str, float]] = field(default_factory=list)
    dev_vah: List[Tuple[str, float]] = field(default_factory=list)
    dev_val: List[Tuple[str, float]] = field(default_factory=list)

    # final (whole-session) levels
    poc: Optional[float] = None
    vpoc: Optional[float] = None
    vah: Optional[float] = None
    val: Optional[float] = None

    def prices_asc(self) -> List[float]:
        return sorted(self.tpo.keys())


# ----------------------------------------------------------------------------- 
# Pure helpers (unit-testable, no network / no streamlit)
# ----------------------------------------------------------------------------- 
def _row_edges(low: float, high: float, tick: float) -> List[float]:
    """Row (bucket) low-edges spanned by [low, high] at the given tick."""
    lo = np.floor(low / tick) * tick
    hi = np.floor(high / tick) * tick
    n = int(round((hi - lo) / tick)) + 1
    return [round(lo + i * tick, 8) for i in range(max(n, 1))]


def _bracket_index(ts: pd.Timestamp, session_start: dt.time, bracket_minutes: int) -> int:
    start = ts.normalize() + pd.Timedelta(hours=session_start.hour, minutes=session_start.minute)
    return int((ts - start).total_seconds() // 60 // bracket_minutes)


_TICK_LADDER = [0.01, 0.02, 0.05, 0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5,
                5.0, 10.0, 20.0, 25.0, 50.0, 100.0, 250.0, 500.0]


def nice_tick(bars: pd.DataFrame, target_rows: int = 25) -> float:
    """Choose a sensible row height so a typical session spans ~target_rows rows."""
    if bars is None or bars.empty:
        return 1.0
    g = bars.groupby(bars.index.date)
    rng = (g["high"].max() - g["low"].min())
    typ = float(rng.median()) if len(rng) else float(bars["high"].max() - bars["low"].min())
    if typ <= 0:
        return 1.0
    raw = typ / max(target_rows, 1)
    for t in _TICK_LADDER:
        if t >= raw:
            return t
    return _TICK_LADDER[-1]


# Exchange -> IANA timezone. tvdatafeed hands back naive timestamps (usually UTC);
# we convert to the exchange's local wall-clock so `session_start` is intuitive.
_EXCHANGE_TZ = {
    "NYSE": "America/New_York", "AMEX": "America/New_York",
    "NASDAQ": "America/New_York", "ARCA": "America/New_York",
    "BATS": "America/New_York", "CBOE": "America/New_York",
    "COMEX": "America/New_York", "NYMEX": "America/New_York",
    "CME": "America/Chicago", "CME_MINI": "America/Chicago",
    "CBOT": "America/Chicago",
    "NSE": "Asia/Kolkata", "BSE": "Asia/Kolkata", "MCX": "Asia/Kolkata",
    "LSE": "Europe/London", "EURONEXT": "Europe/Paris",
    "XETR": "Europe/Berlin", "FWB": "Europe/Berlin",
    "TSE": "Asia/Tokyo", "HKEX": "Asia/Hong_Kong",
    "SSE": "Asia/Shanghai", "SZSE": "Asia/Shanghai",
    "ASX": "Australia/Sydney", "SGX": "Asia/Singapore",
    "BINANCE": "UTC", "COINBASE": "UTC", "BITSTAMP": "UTC", "KRAKEN": "UTC",
    "BYBIT": "UTC", "OKX": "UTC",
    "FX_IDC": "UTC", "OANDA": "UTC", "FOREXCOM": "UTC",
}


def resolve_tz(exchange: str) -> str:
    """Best-guess IANA timezone for an exchange code (defaults to UTC)."""
    return _EXCHANGE_TZ.get((exchange or "").upper(), "UTC")


def localize_index(df: pd.DataFrame, source_tz: str, target_tz: str) -> pd.DataFrame:
    """Reinterpret a naive index as `source_tz`, convert to `target_tz`, drop tz.

    Result is naive local wall-clock in the exchange timezone, so that a naive
    `session_start` (e.g. 09:30) compares correctly.
    """
    if df is None or df.empty:
        return df
    idx = pd.DatetimeIndex(df.index)
    try:
        if idx.tz is None:
            idx = idx.tz_localize(source_tz, nonexistent="shift_forward",
                                  ambiguous="NaT")
        idx = idx.tz_convert(target_tz).tz_localize(None)
    except Exception:  # noqa: BLE001 - bad tz string etc.; leave as-is
        return df
    out = df.copy()
    out.index = idx
    return out


def poc_from_counts(counts: Dict[float, float], prices_asc: List[float]) -> Optional[float]:
    """Row with the greatest weight; ties break toward the centre of the range."""
    if not counts:
        return None
    mx = max(counts.values())
    winners = [p for p in prices_asc if counts.get(p, 0) == mx]
    if len(winners) == 1:
        return winners[0]
    mid = (prices_asc[0] + prices_asc[-1]) / 2.0
    return min(winners, key=lambda p: abs(p - mid))


def value_area(counts: Dict[float, float], prices_asc: List[float],
               poc_price: float, pct: float = 0.70) -> Tuple[float, float]:
    """
    Classic Steidlmayer value area: start at POC, repeatedly add the richer of the
    two rows above vs two rows below until `pct` of total weight is enclosed.
    Returns (VAL, VAH).
    """
    if not counts or poc_price is None:
        return (None, None)
    n = len(prices_asc)
    idx = prices_asc.index(poc_price)
    total = sum(counts.values())
    target = total * pct
    acc = counts.get(poc_price, 0.0)
    lo = hi = idx

    def cval(i: int) -> float:
        return counts.get(prices_asc[i], 0.0) if 0 <= i < n else 0.0

    while acc < target and (hi < n - 1 or lo > 0):
        up_pair = (cval(hi + 1) + cval(hi + 2)) if hi < n - 1 else -1.0
        dn_pair = (cval(lo - 1) + cval(lo - 2)) if lo > 0 else -1.0
        if up_pair < 0 and dn_pair < 0:
            break
        if up_pair >= dn_pair:
            hi = min(hi + 1, n - 1); acc += cval(hi)
            if hi < n - 1 and acc < target:
                hi += 1; acc += cval(hi)
        else:
            lo = max(lo - 1, 0); acc += cval(lo)
            if lo > 0 and acc < target:
                lo -= 1; acc += cval(lo)
    return (prices_asc[lo], prices_asc[hi])


def build_day_profile(bars: pd.DataFrame, day: dt.date, tick: float,
                      bracket_minutes: int, va_pct: float = 0.70,
                      anchor: str = "first_bar",
                      session_start: Optional[dt.time] = None) -> DayProfile:
    """Build one DayProfile from that day's base-interval bars.

    anchor="first_bar": bracket A starts at the day's opening bar (timezone-proof).
    anchor="session":  brackets are cut from a fixed wall-clock `session_start`.
    """
    dp = DayProfile(day=day, tick=tick)
    if bars.empty:
        return dp

    if anchor == "session" and session_start is not None:
        anchor_ts = bars.index.min().normalize() + pd.Timedelta(
            hours=session_start.hour, minutes=session_start.minute)
    else:
        anchor_ts = bars.index.min()

    # group bars into brackets, measured from the anchor
    bar_bracket: List[int] = [
        int((ts - anchor_ts).total_seconds() // 60 // bracket_minutes)
        for ts in bars.index
    ]
    seen_brackets: List[int] = sorted(set(b for b in bar_bracket if b >= 0))
    bracket_letter = {b: LETTERS[i] for i, b in enumerate(seen_brackets)
                      if i < len(LETTERS)}
    dp.brackets = [bracket_letter[b] for b in seen_brackets if b in bracket_letter]

    # running cumulative structures for developing series
    cum_tpo_count: Dict[float, int] = {}
    cum_vol: Dict[float, float] = dp.vol

    for b in seen_brackets:
        letter = bracket_letter.get(b)
        if letter is None:
            continue
        sub = bars[[x == b for x in bar_bracket]]
        b_low = float(sub["low"].min())
        b_high = float(sub["high"].max())
        dp.bracket_range[letter] = (b_low, b_high)

        # TPO letters for this bracket (one letter per row it spans)
        for edge in _row_edges(b_low, b_high, tick):
            dp.tpo.setdefault(edge, []).append(letter)
            cum_tpo_count[edge] = cum_tpo_count.get(edge, 0) + 1

        # volume-at-price from base bars in this bracket (spread across rows)
        for _, row in sub.iterrows():
            edges = _row_edges(float(row["low"]), float(row["high"]), tick)
            share = float(row.get("volume", 0.0)) / len(edges) if edges else 0.0
            for edge in edges:
                cum_vol[edge] = cum_vol.get(edge, 0.0) + share

        # developing levels AFTER this bracket closes
        p_asc = sorted(cum_tpo_count.keys())
        d_poc = poc_from_counts(cum_tpo_count, p_asc)
        dp.dev_poc.append((letter, d_poc))
        v_asc = sorted(cum_vol.keys())
        d_vpoc = poc_from_counts(cum_vol, v_asc)
        dp.dev_vpoc.append((letter, d_vpoc))
        d_val, d_vah = value_area(cum_tpo_count, p_asc, d_poc, va_pct)
        dp.dev_val.append((letter, d_val))
        dp.dev_vah.append((letter, d_vah))

    # finalise
    if dp.tpo:
        counts = {p: len(v) for p, v in dp.tpo.items()}
        p_asc = dp.prices_asc()
        dp.poc = poc_from_counts(counts, p_asc)
        dp.val, dp.vah = value_area(counts, p_asc, dp.poc, va_pct)
        dp.vpoc = poc_from_counts(dp.vol, sorted(dp.vol.keys())) if dp.vol else None
    return dp


def split_days(bars: pd.DataFrame, tick: float, bracket_minutes: int,
               va_pct: float = 0.70, anchor: str = "first_bar",
               session_start: Optional[dt.time] = None) -> List[DayProfile]:
    """Split a multi-day bar frame into per-day DayProfiles (chronological)."""
    out: List[DayProfile] = []
    if bars is None or bars.empty:
        return out
    bars = bars.sort_index()
    for day, grp in bars.groupby(bars.index.date):
        out.append(build_day_profile(grp, day, tick, bracket_minutes, va_pct,
                                     anchor=anchor, session_start=session_start))
    return out


# ----------------------------------------------------------------------------- 
# Data fetch (tvdatafeed) — cached
# ----------------------------------------------------------------------------- 
_INTERVAL_MAP = {
    "1m": "in_1_minute", "3m": "in_3_minute", "5m": "in_5_minute",
    "15m": "in_15_minute", "30m": "in_30_minute", "45m": "in_45_minute",
    "1h": "in_1_hour", "2h": "in_2_hour",
}
_INTERVAL_MINUTES = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                     "45m": 45, "1h": 60, "2h": 120}


@st.cache_data(show_spinner=False, ttl=300)
def fetch_bars(symbol: str, exchange: str, base_interval: str, n_bars: int,
               username: Optional[str], password: Optional[str]) -> pd.DataFrame:
    """Pull bars from TradingView via tvdatafeed. Cached for 5 min."""
    from tvDatafeed import TvDatafeed, Interval  # imported lazily

    tv = TvDatafeed(username, password) if username and password else TvDatafeed()
    interval = getattr(Interval, _INTERVAL_MAP[base_interval])
    df = tv.get_hist(symbol=symbol, exchange=exchange,
                     interval=interval, n_bars=n_bars)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns=str.lower)
    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df


# ----------------------------------------------------------------------------- 
# Rendering
# ----------------------------------------------------------------------------- 
LETTER_COLORS = ["#4FC3F7", "#4DB6AC", "#81C784", "#AED581", "#DCE775",
                 "#FFD54F", "#FFB74D", "#FF8A65", "#E57373", "#F06292",
                 "#BA68C8", "#9575CD", "#7986CB"]


def _letter_color(letter: str) -> str:
    return LETTER_COLORS[(ord(letter.upper()) - ord("A")) % len(LETTER_COLORS)]


def render_chart(profiles: List[DayProfile], tick: float, *,
                 show_volume: bool, show_letters: bool,
                 show_dev_poc: bool, show_dev_vpoc: bool, show_dev_va: bool,
                 split_indices: Optional[set] = None,
                 title: str = "") -> go.Figure:
    """Compose the side-by-side profile figure."""
    split_indices = split_indices or set()

    SLOT = 1.0            # horizontal slot width per collapsed day (data units)
    GAP = 0.25            # gap between days
    VOL_FRAC = 0.32       # fraction of slot used by the volume histogram
    LETTER_X = VOL_FRAC + 0.02

    fig = go.Figure()
    x_offset = 0.0
    for di, dp in enumerate(profiles):
        if not dp.tpo:
            continue
        is_split = di in split_indices
        prices = dp.prices_asc()
        counts = {p: len(v) for p, v in dp.tpo.items()}
        max_count = max(counts.values()) if counts else 1
        max_vol = max(dp.vol.values()) if dp.vol else 1.0

        if is_split:
            ncol = max(len(dp.brackets), 1)
            slot_w = max(1.0, ncol * 0.18)
        else:
            slot_w = SLOT

        # volume histogram (collapsed view only)
        if show_volume and not is_split and dp.vol:
            vx, vy = [], []
            for p in prices:
                vx.append(dp.vol.get(p, 0.0) / max_vol * (slot_w * VOL_FRAC))
                vy.append(p + tick / 2)
            fig.add_trace(go.Bar(
                x=vx, y=vy, base=x_offset, width=tick * 0.9,
                orientation="h", marker=dict(color="rgba(214,178,94,0.40)",
                                             line=dict(width=0)),
                hoverinfo="skip", showlegend=False,
            ))

        # letters
        if show_letters:
            if is_split:
                for bi, letter in enumerate(dp.brackets):
                    lo, hi = dp.bracket_range[letter]
                    col_x = x_offset + bi * (slot_w / max(len(dp.brackets), 1))
                    ys = [e + tick / 2 for e in _row_edges(lo, hi, tick)]
                    fig.add_trace(go.Scatter(
                        x=[col_x] * len(ys), y=ys, mode="text",
                        text=[letter] * len(ys),
                        textfont=dict(family="monospace", size=11,
                                      color=_letter_color(letter)),
                        hoverinfo="skip", showlegend=False,
                    ))
            else:
                # collapsed: one concatenated string per row
                txt, ys, colors = [], [], []
                for p in prices:
                    letters = dp.tpo[p]
                    txt.append("".join(letters))
                    ys.append(p + tick / 2)
                    colors.append(_letter_color(letters[0]))
                fig.add_trace(go.Scatter(
                    x=[x_offset + slot_w * LETTER_X] * len(ys), y=ys,
                    mode="text", text=txt,
                    textposition="middle right",
                    textfont=dict(family="monospace", size=10, color="#E0E0E0"),
                    hoverinfo="skip", showlegend=False,
                ))

        # invisible hover layer (price / tpo count / volume)
        hy = [p + tick / 2 for p in prices]
        htext = [f"{p:.2f}<br>TPO {counts[p]}<br>Vol {dp.vol.get(p,0):,.0f}"
                 for p in prices]
        fig.add_trace(go.Scatter(
            x=[x_offset + slot_w * 0.5] * len(hy), y=hy, mode="markers",
            marker=dict(size=slot_w * 20, opacity=0), hovertext=htext,
            hoverinfo="text", showlegend=False,
        ))

        # developing lines spread across the slot (left=open -> right=close)
        nb = max(len(dp.brackets), 1)
        def spread_x(i):
            return x_offset + (i + 0.5) * (slot_w / nb)

        def add_dev(series, color, name, dash=None):
            xs = [spread_x(i) for i, (_, v) in enumerate(series) if v is not None]
            ys = [v + tick / 2 for (_, v) in series if v is not None]
            if xs:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers", line=dict(color=color, width=2,
                    shape="hv", dash=dash), marker=dict(size=4, color=color),
                    name=name, legendgroup=name, showlegend=(di == 0),
                    hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>",
                ))

        if show_dev_poc:
            add_dev(dp.dev_poc, "#2962FF", "Developing POC")
        if show_dev_vpoc:
            add_dev(dp.dev_vpoc, "#FF6D00", "Developing VPOC")
        if show_dev_va:
            add_dev(dp.dev_vah, "#E53935", "Developing VAH", dash="dot")
            add_dev(dp.dev_val, "#E53935", "Developing VAL", dash="dot")

        # final level ticks at right edge
        for lvl, col in [(dp.poc, "#2962FF"), (dp.vah, "#B71C1C"),
                         (dp.val, "#B71C1C")]:
            if lvl is not None:
                fig.add_shape(type="line",
                              x0=x_offset, x1=x_offset + slot_w,
                              y0=lvl + tick / 2, y1=lvl + tick / 2,
                              line=dict(color=col, width=1, dash="dot"),
                              opacity=0.35, layer="below")

        # day label
        fig.add_annotation(x=x_offset + slot_w * 0.5, xref="x",
                           y=1.0, yref="paper", showarrow=False,
                           text=dp.day.strftime("%d %b"),
                           font=dict(size=11, color="#BDBDBD"), yanchor="bottom")

        x_offset += slot_w + GAP

    fig.update_layout(
        title=title, template="plotly_dark",
        height=760, bargap=0, barmode="overlay",
        margin=dict(l=10, r=70, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.03,
                    xanchor="right", x=1.0),
        plot_bgcolor="#2b2b2b", paper_bgcolor="#2b2b2b",
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False,
                     range=[-GAP, x_offset])
    fig.update_yaxes(side="right", showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                     zeroline=False, title="Price")
    return fig


# ----------------------------------------------------------------------------- 
# Streamlit UI
# ----------------------------------------------------------------------------- 
def main():
    st.set_page_config(page_title="TPO Market Profile", layout="wide")
    st.title("TPO Market Profile — developing POC")
    st.caption(f"tvdatafeed · v{__version__}")

    with st.sidebar:
        st.header("Instrument")
        ticker = st.text_input(
            "Ticker (EXCHANGE:SYMBOL)", value="AMEX:SPY",
            help="TradingView style, e.g. AMEX:SPY, NSE:NIFTY, BINANCE:BTCUSDT",
        ).strip().upper()
        if ":" in ticker:
            exchange, symbol = (p.strip() for p in ticker.split(":", 1))
        else:
            exchange, symbol = "", ticker
        if not symbol:
            st.caption("Enter a ticker to begin.")
        elif not exchange:
            st.caption(f"Symbol **{symbol}** · no exchange — add one like `NSE:{symbol}`")
        else:
            st.caption(f"Exchange **{exchange}** · symbol **{symbol}**")

        st.header("Data")
        base_interval = st.selectbox("Base interval (fetched)",
                                     list(_INTERVAL_MAP.keys()), index=2)
        n_bars = st.number_input("Bars to fetch", 200, 5000, 1500, step=100)
        tz_override = st.text_input(
            "Exchange timezone", value=resolve_tz(exchange),
            help="IANA name, e.g. America/New_York, Asia/Kolkata, UTC")
        source_is_local = st.checkbox(
            "Feed already returns exchange-local time", value=False,
            help="Leave OFF if tvdatafeed hands back UTC (usual). "
                 "Turn ON only if your build already localises.")

        st.header("Profile")
        bracket_minutes = st.selectbox("Bracket size (TPO letter)",
                                       [5, 15, 30, 45, 60], index=2)
        anchor_mode = st.radio(
            "Bracket anchor",
            ["First bar of session", "Fixed clock time"],
            index=0,
            help="First bar = timezone-proof (recommended). Fixed time cuts "
                 "brackets from the clock time below.")
        auto_tick = st.checkbox("Auto row size", True,
                                help="Pick a sensible row height from the data range")
        tick_manual = st.number_input("Row size / tick (manual)",
                                      0.01, 500.0, 0.25, step=0.05, format="%.2f",
                                      disabled=auto_tick)
        st.caption("Typical: SPY 0.25–0.5 · NIFTY 5–10 · BTC 25–50 (or use Auto)")
        va_pct = st.slider("Value area %", 50, 90, 70) / 100.0
        c1, c2 = st.columns(2)
        sess_start = c1.time_input("Session start (fixed)", dt.time(9, 30),
                                   disabled=(anchor_mode == "First bar of session"))
        max_days = c2.number_input("Days to show", 1, 30, 5)

        st.header("Overlays")
        show_letters = st.checkbox("TPO letters", True)
        show_volume = st.checkbox("Volume profile", True)
        show_dev_poc = st.checkbox("Developing POC", True)
        show_dev_vpoc = st.checkbox("Developing VPOC", True)
        show_dev_va = st.checkbox("Developing value area", False)

        st.header("Expand / split")
        expand_latest = st.checkbox("Expand latest day", True)
        expand_pick = st.multiselect(
            "Also expand (by date, filled after load)", [])

        st.header("TradingView auth (optional)")
        tv_user = st.text_input("Username", value="")
        tv_pass = st.text_input("Password", value="", type="password")

        go_btn = st.button("Load / refresh", type="primary")

    bmin = _INTERVAL_MINUTES[base_interval]
    if bracket_minutes < bmin:
        st.warning(f"Bracket ({bracket_minutes}m) is smaller than the base "
                   f"interval ({bmin}m). Set bracket ≥ base interval.")
        return

    if not go_btn and "profiles" not in st.session_state:
        st.info("Set your instrument on the left and hit **Load / refresh**.")
        return

    if go_btn:
        try:
            with st.spinner(f"Fetching {symbol}:{exchange} {base_interval}…"):
                bars = fetch_bars(symbol, exchange, base_interval, int(n_bars),
                                  tv_user or None, tv_pass or None)
        except ModuleNotFoundError:
            st.error("tvdatafeed is not installed. `pip install -r requirementstpo.txt`")
            return
        except Exception as e:  # noqa: BLE001
            st.error(f"Fetch failed: {e}")
            return
        if bars.empty:
            st.error("No data returned. Check the symbol/exchange spelling.")
            return
        if not source_is_local:
            bars = localize_index(bars, "UTC", tz_override.strip() or "UTC")
        tick = nice_tick(bars) if auto_tick else float(tick_manual)
        anchor = "first_bar" if anchor_mode == "First bar of session" else "session"
        profiles = split_days(bars, tick, int(bracket_minutes), va_pct,
                              anchor=anchor, session_start=sess_start)
        profiles = profiles[-int(max_days):]
        st.session_state["profiles"] = profiles
        st.session_state["tick"] = tick
        st.session_state["meta"] = (symbol, exchange, base_interval)
        # first bar of the most recent session, for alignment sanity-check
        last_day = bars.index.date.max()
        first_ts = bars[bars.index.date == last_day].index.min()
        st.session_state["first_ts"] = first_ts

    profiles: List[DayProfile] = st.session_state.get("profiles", [])
    tick = st.session_state.get("tick", float(tick_manual))
    if not profiles:
        return

    if auto_tick:
        st.caption(f"Auto row size: **{tick:g}** per row")

    first_ts = st.session_state.get("first_ts")
    if first_ts is not None:
        st.caption(
            f"Latest session opens at **{first_ts:%H:%M}** "
            f"({tz_override.strip() or 'UTC'}). Brackets anchor to this first bar, "
            f"so the timezone only affects how bars group into calendar days."
        )

    split_idx = set()
    if expand_latest and profiles:
        split_idx.add(len(profiles) - 1)

    sym, exch, bi = st.session_state["meta"]
    fig = render_chart(
        profiles, tick,
        show_volume=show_volume, show_letters=show_letters,
        show_dev_poc=show_dev_poc, show_dev_vpoc=show_dev_vpoc,
        show_dev_va=show_dev_va, split_indices=split_idx,
        title=f"{sym}:{exch} · {bi} base · {bracket_minutes}m brackets",
    )
    st.plotly_chart(fig, use_container_width=True)

    # summary table of final levels
    rows = []
    for dp in profiles:
        rows.append({
            "Day": dp.day.strftime("%d %b"),
            "POC": dp.poc, "VAH": dp.vah, "VAL": dp.val, "VPOC": dp.vpoc,
            "Brackets": len(dp.brackets),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()


# =============================================================================
# CHANGELOG
# 0.5.0  bracket anchoring defaults to FIRST BAR of each session -> fully
#        timezone-independent (fixes NSE:NIFTY). Fixed-clock anchoring kept as
#        an option. Tick guidance in UI. Timezone now only affects day grouping.
# 0.4.0  exchange-timezone handling: naive feed timestamps (assumed UTC) are
#        converted to the exchange's local wall-clock, so `session_start` means
#        real local open. Exchange->tz map + manual override + "already local"
#        toggle + first-bar alignment check caption.
# 0.3.0  auto row-size (nice_tick) so profiles resolve correctly per instrument
#        (fixes SPY-on-$5-tick collapse); session start default 9:30; lighter
#        volume bars; resolved tick persisted in session_state.
# 0.2.0  single combined "EXCHANGE:SYMBOL" ticker input (e.g. AMEX:SPY),
#        parsed into exchange + symbol; default changed to AMEX:SPY.
# 0.1.0  initial build: tvdatafeed fetch, TPO letters (grouped brackets),
#        volume profile, developing POC / VPOC / value area, expand-latest-day
#        split view, per-day summary table.
# =============================================================================
