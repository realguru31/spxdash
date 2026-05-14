"""
app.py — SPX Gamma Exposure Dashboard
Excel-matching ladder with heatmap, inline bars, color-coded level rows.
Delta panels as collapsible expanders — all can be open simultaneously.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import logging

from data_fetcher import get_spx_quote, get_options_chain
from calculations import compute_chain_metrics, compute_dashboard_levels, filter_chain_for_display
from utils import get_ny_time, get_ny_datetime, is_market_hours, get_upcoming_expirations

st.set_page_config(page_title="SPX Gamma Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.markdown("""<style>
#MainMenu,header,footer,[data-testid="stHeader"],[data-testid="stToolbar"]{display:none!important;visibility:hidden!important;}
.block-container{padding-top:0.5rem;}
.gamma-banner{text-align:center;padding:8px;border-radius:6px;font-weight:700;font-size:1.1em;margin:4px 0;}
.gamma-call{background:rgba(30,144,255,0.15);color:#1e90ff;border:1px solid #1e90ff;}
.gamma-put{background:rgba(255,0,255,0.15);color:#ff00ff;border:1px solid #ff00ff;}
.status-bar{display:flex;justify-content:space-between;align-items:center;padding:4px 12px;background:#16213e;border-radius:6px;margin-bottom:8px;}
.status-text{font-size:0.82em;color:#a0a0a0;}
</style>""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown("## ⚡ SPX Gamma")
    exp_presets = get_upcoming_expirations()
    selected_label = st.selectbox("Expiration", list(exp_presets.keys()), index=0)
    exp_str = exp_presets[selected_label].strftime("%Y-%m-%d")
    st.caption(f"📅 {exp_str}")
    st.divider()
    num_above = st.slider("Strikes above ATM", 5, 40, 20, 5)
    num_below = st.slider("Strikes below ATM", 5, 40, 20, 5)
    st.divider()
    auto_refresh = st.checkbox("Auto-refresh (3 min)", value=True)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.divider()
    et_now = get_ny_datetime()
    st.markdown(f"**{'🟢 MARKET OPEN' if is_market_hours() else '🔴 MARKET CLOSED'}**")
    st.markdown(f"**ET:** {et_now.strftime('%H:%M:%S')}")

if auto_refresh:
    @st.fragment(run_every=180)
    def _tick(): pass
    _tick()

# ── Data ──
@st.cache_data(ttl=170, show_spinner=False)
def load_data(exp_date, n_above, n_below, _ts):
    quote = get_spx_quote(); spot = quote.get("lastPrice", 0)
    chain = get_options_chain(exp_date)
    if chain is None or chain.empty: return quote, pd.DataFrame(), {}, pd.DataFrame()
    chain = compute_chain_metrics(chain, spot)
    levels = compute_dashboard_levels(chain, spot)
    display = filter_chain_for_display(chain, spot, n_above, n_below)
    return quote, chain, levels, display

ts = int(datetime.now().timestamp() // 170)
with st.spinner("Fetching…"):
    quote, full_chain, levels, display_chain = load_data(exp_str, num_above, num_below, ts)

spot = quote.get("lastPrice", 0)
if display_chain.empty:
    st.error(f"❌ No data for {exp_str}. Try another expiration."); st.stop()

# ── ET date ──
try:
    import pytz
    today_et = datetime.now(pytz.timezone("US/Eastern")).date()
except:
    today_et = datetime.now().date()
today_str = today_et.strftime("%Y-%m-%d")

# ══════════════════════════════════════
# BASELINE LOADING
# ══════════════════════════════════════
baseline_path = f"data/baseline/{today_str}.json"

def _compute_straddle(chain_df, current_spot):
    """Compute ATM straddle from current chain."""
    if chain_df.empty or current_spot <= 0:
        return None, None, None, None
    atm = round(current_spot / 5) * 5
    # Find ATM call and put
    near = chain_df[(chain_df["strike"] >= atm - 5) & (chain_df["strike"] <= atm + 5)]
    if near.empty:
        near = chain_df.iloc[(chain_df["strike"] - atm).abs().argsort()[:1]]
    if near.empty:
        return None, None, None, None
    row = near.iloc[0]
    c_price = float(row.get("c_mark", row.get("c_last", 0)))
    p_price = float(row.get("p_mark", row.get("p_last", 0)))
    straddle = round(c_price + p_price, 2)
    return straddle, int(row["strike"]), c_price, p_price

def _chain_to_baseline(chain_df, source, timestamp, current_spot):
    bl = {}
    for _, row in chain_df.iterrows():
        k = int(row["strike"])
        bl[k] = {
            "c_volume": int(row.get("c_volume", 0)),
            "p_volume": int(row.get("p_volume", 0)),
            "c_oi": int(row.get("c_oi", 0)),
            "p_oi": int(row.get("p_oi", 0)),
            "call_gex": float(row.get("call_gex", 0)),
            "put_gex": float(row.get("put_gex", 0)),
            "net_gex": float(row.get("net_gex", 0)),
        }
    straddle, atm_k, c_p, p_p = _compute_straddle(chain_df, current_spot)
    return {
        "strikes": bl, "source": source, "timestamp_et": timestamp,
        "date": today_str, "spot_at_baseline": current_spot,
        "straddle": {
            "price": straddle, "atm_strike": atm_k,
            "call_price": c_p, "put_price": p_p,
            "upper": round(current_spot + straddle, 2) if straddle else None,
            "lower": round(current_spot - straddle, 2) if straddle else None,
        }
    }

baseline = None
baseline_source = None
baseline_time = None
straddle_info = {}

# Priority 1: GitHub Actions file
if os.path.exists(baseline_path):
    try:
        with open(baseline_path) as f:
            bl_data = json.load(f)
        if bl_data.get("date") == today_str:
            baseline = {int(k): v for k, v in bl_data["strikes"].items()}
            baseline_source = "📸 GitHub Actions"
            baseline_time = bl_data.get("timestamp_et", "09:31 ET")
            straddle_info = bl_data.get("straddle", {})
    except Exception as e:
        logger.warning("Baseline file load failed: %s", e)

# Priority 2: Session state
if baseline is None:
    if "baseline" not in st.session_state or st.session_state.get("baseline_date") != today_str:
        if not full_chain.empty:
            now_str = et_now.strftime("%H:%M ET")
            bl_data = _chain_to_baseline(full_chain, "first_load", now_str, spot)
            st.session_state["baseline"] = bl_data
            st.session_state["baseline_date"] = today_str
    if "baseline" in st.session_state:
        bl_data = st.session_state["baseline"]
        baseline = {int(k): v for k, v in bl_data["strikes"].items()}
        baseline_source = "⏱ First load"
        baseline_time = bl_data.get("timestamp_et", "unknown")
        straddle_info = bl_data.get("straddle", {})

with st.sidebar:
    st.divider()
    st.caption(f"Baseline: {baseline_source or '—'}")
    st.caption(f"Time: {baseline_time or '—'}")
    if straddle_info.get("price"):
        st.caption(f"Straddle: {straddle_info['price']:.2f} pts")

# ── Straddle time series ──
# Seed from baseline on first load, append current straddle each refresh
def _get_current_straddle(chain_df, current_spot, fixed_strike=None):
    """
    Get current straddle price.
    Uses fixed_strike (baseline ATM) if provided so we track the same
    contract pair decaying through the day, not a rolling ATM.
    """
    if chain_df.empty or current_spot <= 0:
        return None
    # Use fixed baseline strike if available, else current ATM
    target = fixed_strike if fixed_strike else round(current_spot / 5) * 5
    near = chain_df[(chain_df["strike"] >= target - 5) & (chain_df["strike"] <= target + 5)]
    if near.empty:
        near = chain_df.iloc[(chain_df["strike"] - target).abs().argsort()[:1]]
    if near.empty:
        return None
    row = near.iloc[0]
    c_p = float(row.get("c_mark", row.get("c_last", 0)))
    p_p = float(row.get("p_mark", row.get("p_last", 0)))
    return round(c_p + p_p, 2) if (c_p + p_p) > 0 else None

# Init time series in session state
if "straddle_ts" not in st.session_state or st.session_state.get("straddle_ts_date") != today_str:
    ts_data = []
    # Seed from baseline if available
    if straddle_info.get("price") and straddle_info.get("price") > 0:
        bl_time_raw = baseline_time or "09:31 ET"
        # Handle both "HH:MM ET" and full "YYYY-MM-DD HH:MM ET" formats
        try:
            parts = bl_time_raw.replace(" ET", "").strip().split(" ")
            # If it has a date part, take the time part (last element)
            time_part = parts[-1]  # "HH:MM"
            bl_time_hhmm = time_part + " ET"
        except:
            bl_time_hhmm = bl_time_raw
        ts_data.append({
            "time": bl_time_hhmm,
            "straddle": straddle_info["price"],
            "source": "baseline"
        })
    st.session_state["straddle_ts"] = ts_data
    st.session_state["straddle_ts_date"] = today_str

# Append current straddle on each refresh (avoid duplicates within same minute)
# Use fixed baseline ATM strike so we track same contract pair all day
fixed_atm = straddle_info.get("atm_strike") if straddle_info else None
current_straddle = _get_current_straddle(full_chain, spot, fixed_strike=fixed_atm)
if current_straddle and is_market_hours():
    now_str = et_now.strftime("%H:%M ET")
    ts = st.session_state["straddle_ts"]
    if not ts or ts[-1]["time"] != now_str:
        ts.append({"time": now_str, "straddle": current_straddle, "source": "live"})
        st.session_state["straddle_ts"] = ts

# ── DTE ──
try:
    dte = (datetime.strptime(exp_str, "%Y-%m-%d").date() - today_et).days
    dte_label = "0DTE" if dte == 0 else f"{dte}DTE"
except: dte_label = selected_label

pct_chg = quote.get("percentChange", 0); net_chg = quote.get("netChange", 0)
if net_chg == 0 and pct_chg != 0:
    pc = quote.get("previousClose", 0)
    net_chg = round(spot - pc, 2) if pc > 0 else round(spot * pct_chg / 100, 2)

# ── Header ──
st.markdown(f"""<div class="status-bar">
<span class="status-text">SPX {spot:,.2f} &nbsp; {net_chg:+.2f} ({pct_chg:+.2f}%) &nbsp;•&nbsp; {selected_label} · {dte_label} ({exp_str})</span>
<span class="status-text">NY: {get_ny_time()} &nbsp;•&nbsp; ATM: {levels.get('centered_spot',0)}</span>
</div>""", unsafe_allow_html=True)

dom = levels.get("gamma_dominant", "N/A"); cls = "gamma-call" if dom == "CALL" else "gamma-put"
st.markdown(f"""<div class="gamma-banner {cls}">
Gamma is {dom} dominant &nbsp;•&nbsp; GEX Ratio: {levels.get('gex_ratio',0):.2f} &nbsp;•&nbsp; Net GEX: {levels.get('total_net_gex',0):,}
</div>""", unsafe_allow_html=True)

LEVEL_COLORS = {
    "call_wall": "rgb(233,113,50)", "put_wall": "rgb(204,153,0)",
    "coi": "rgb(97,203,243)", "poi": "rgb(216,109,205)",
    "pgex": "rgb(148,220,248)", "ngex": "rgb(228,158,221)",
    "ptrans": "rgb(202,237,251)", "ntrans": "rgb(242,206,239)",
}
LEVEL_LABELS = {
    "call_wall":"Call Wall","put_wall":"Put Wall","coi":"COI","poi":"POI",
    "pgex":"pGEX","ngex":"nGEX","ptrans":"pTrans","ntrans":"nTrans",
}

# ══════════════════════════════════════
# MAIN: Ladder + Charts
# ══════════════════════════════════════
col_ladder, col_charts = st.columns([0.55, 0.45])

with col_ladder:
    ldf = display_chain.sort_values("strike", ascending=False).copy()
    atm = levels.get("centered_spot", 0)
    strike_levels = {}
    for key in LEVEL_COLORS:
        v = levels.get(key)
        if v is not None:
            strike_levels.setdefault(int(v), []).append(key)

    mx_cv = max(ldf["c_volume"].max(), 1); mx_pv = max(ldf["p_volume"].max(), 1)
    mx_gex = max(abs(ldf["net_gex"].max()), abs(ldf["net_gex"].min()), 1)
    mx_coi = max(ldf["c_oi"].max(), 1); mx_poi = max(ldf["p_oi"].max(), 1)
    mx_toi = max(ldf["total_oi"].max(), 1)

    def _bar(val, mx, color, w=70):
        if mx <= 0 or val <= 0: return ""
        return f'<div style="background:{color};height:11px;width:{min(val/mx*w,w):.0f}%;border-radius:2px;display:inline-block;"></div>'

    def _heat(val, mx, base_color):
        if mx <= 0 or val <= 0: return ""
        return f"background:rgba({base_color},{min(val/mx,1.0)*0.5:.2f});"

    rows_html = []
    for _, r in ldf.iterrows():
        k = int(r["strike"])
        bg = "background:rgba(30,144,255,0.25);" if k == atm else (
            f"background:{LEVEL_COLORS[strike_levels[k][0]].replace('rgb','rgba').replace(')',',0.15)')};"
            if k in strike_levels else "")
        labels = " ".join(f'<span style="color:{LEVEL_COLORS[lk]};font-weight:bold;font-size:9px;">{LEVEL_LABELS[lk]}</span>'
                          for lk in strike_levels.get(k, []))
        gv = r["net_gex"]; gc = "#1e90ff" if gv >= 0 else "#ff00ff"
        dex = r["net_dex"]; dc = "#1e90ff" if dex >= 0 else "#ff00ff"
        noi = r["net_oi"]; nc = "#1e90ff" if noi >= 0 else "#ff00ff"
        sc = "#ffd600" if k == atm else "#e0e0e0"
        rows_html.append(f"""<tr style="{bg}">
<td style="text-align:right;font-size:10px;{_heat(r['c_volume'],mx_cv,'30,144,255')}">{int(r['c_volume']):,}</td>
<td style="width:50px;">{_bar(r['c_volume'],mx_cv,'#1e90ff')}</td>
<td style="text-align:center;font-weight:bold;font-size:11px;color:{sc}">{k}{' •' if k==atm else ''}</td>
<td style="width:50px;">{_bar(r['p_volume'],mx_pv,'#ff00ff')}</td>
<td style="text-align:left;font-size:10px;{_heat(r['p_volume'],mx_pv,'255,0,255')}">{int(r['p_volume']):,}</td>
<td style="text-align:right;font-size:10px;"><span style="color:{gc}">{gv:,.0f}</span></td>
<td style="width:45px;">{_bar(abs(gv),mx_gex,gc)}</td>
<td style="text-align:right;font-size:10px;color:{dc}">{int(dex):,}</td>
<td style="text-align:right;font-size:10px;{_heat(r['c_oi'],mx_coi,'30,144,255')}">{int(r['c_oi']):,}</td>
<td style="text-align:right;font-size:10px;{_heat(r['p_oi'],mx_poi,'255,0,255')}">{int(r['p_oi']):,}</td>
<td style="text-align:right;font-size:10px;{_heat(r['total_oi'],mx_toi,'100,100,255')}">{int(r['total_oi']):,}</td>
<td style="text-align:right;font-size:10px;color:{nc}">{int(noi):,}</td>
<td style="text-align:right;font-size:10px;">{r['pct_from_spot']:.2%}</td>
<td style="font-size:9px;padding-left:3px;">{labels}</td>
</tr>""")

    st.markdown(f"""<div style="max-height:850px;overflow-y:auto;border:1px solid #262730;border-radius:6px;">
<table style="width:100%;border-collapse:collapse;font-family:monospace;font-size:10px;">
<thead style="position:sticky;top:0;background:#16213e;z-index:1;">
<tr style="color:#a0a0a0;font-size:9px;">
<th>C Vol</th><th></th><th>Strike</th><th></th><th>P Vol</th>
<th>GEX</th><th></th><th>DEX</th><th>C OI</th><th>P OI</th><th>Tot OI</th><th>Net OI</th><th>%Spot</th><th>Level</th>
</tr></thead><tbody>{''.join(rows_html)}</tbody></table></div>""", unsafe_allow_html=True)

with col_charts:
    cdf = display_chain.sort_values("strike").copy()

    def _prof(y_pos, y_neg, title, split=False, tfmt=","):
        fig = go.Figure()
        if split:
            fig.add_trace(go.Bar(x=cdf["strike"], y=y_pos, marker_color="rgba(30,144,255,0.7)", name="+"))
            fig.add_trace(go.Bar(x=cdf["strike"], y=y_neg, marker_color="rgba(255,0,255,0.7)", name="−"))
        else:
            net = y_pos + y_neg if y_neg is not None else y_pos
            fig.add_trace(go.Bar(x=cdf["strike"], y=net,
                                  marker_color=["#1e90ff" if v >= 0 else "#ff00ff" for v in net]))
        fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1)
        fig.update_layout(title=dict(text=title, font=dict(size=11, color="#a0a0a0")),
            height=205, template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            showlegend=False, margin=dict(t=28, b=18, l=40, r=10), font=dict(size=9),
            xaxis=dict(showticklabels=False, gridcolor="#1a2a4a"),
            yaxis=dict(gridcolor="#1a2a4a", tickformat=tfmt))
        return fig

    st.plotly_chart(_prof(cdf["net_gex"], None, "Net Gamma Exposure", tfmt=","), use_container_width=True, key="p1")
    st.plotly_chart(_prof(cdf["dadj_cgex"] + cdf["dadj_pgex"], None, "Net Delta-Adjusted Gamma", tfmt=".4f"), use_container_width=True, key="p2")
    fig3 = _prof(cdf["raw_cgex"], cdf["raw_pgex"], "Split Gamma Exposure", split=True, tfmt=".4f")
    st.plotly_chart(fig3, use_container_width=True, key="p3")
    fig4 = _prof(cdf["dadj_cgex"], cdf["dadj_pgex"], "Split Delta-Adjusted Gamma", split=True, tfmt=".4f")
    fig4.update_xaxes(showticklabels=True)
    st.plotly_chart(fig4, use_container_width=True, key="p4")

# ══════════════════════════════════════
# GAUGES
# ══════════════════════════════════════
st.markdown("---")

def _gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": "%", "font": {"size": 24, "color": "#e0e0e0"}},
        title={"text": title, "font": {"size": 11, "color": "#a0a0a0"}},
        gauge={"axis": {"range": [0, 100], "dtick": 10,
                        "tickfont": {"size": 8, "color": "#777"}},
               "bar": {"color": "#ffd600", "thickness": 0.3},
               "bgcolor": "#0e1117", "borderwidth": 0,
               "steps": [{"range": [0, 10], "color": "rgba(255,0,255,0.5)"},
                         {"range": [10, 25], "color": "rgba(150,150,150,0.3)"},
                         {"range": [25, 75], "color": "rgba(30,144,255,0.35)"},
                         {"range": [75, 90], "color": "rgba(150,150,150,0.3)"},
                         {"range": [90, 100], "color": "rgba(255,0,255,0.5)"}],
               "threshold": {"line": {"color": "#ffd600", "width": 3}, "thickness": 0.8, "value": value}},
    ))
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                      font={"color": "#e0e0e0"}, height=180, margin=dict(t=30, b=0, l=20, r=20))
    return fig

cbp = levels.get("avg_bp_call", 50); pbp = levels.get("avg_bp_put", 50)
combo = (cbp + pbp) / 2 if (cbp + pbp) > 0 else 50
g1, g2, g3 = st.columns(3)
with g1: st.plotly_chart(_gauge(cbp, "Call BP%"), use_container_width=True, key="g1")
with g2: st.plotly_chart(_gauge(pbp, "Put BP%"), use_container_width=True, key="g2")
with g3: st.plotly_chart(_gauge(combo, "Combined BP%"), use_container_width=True, key="g3")
if not is_market_hours(): st.caption("⚠️ BP% gauges need RTH data.")

# ══════════════════════════════════════
# DELTA PANELS — collapsible expanders
# ══════════════════════════════════════
st.markdown("---")

if not baseline:
    st.info("⏳ Baseline not yet available.")
else:
    bl_caption = f"vs baseline ({baseline_source} @ {baseline_time})"

    ldf_s = display_chain.sort_values("strike").copy()
    strikes_list = ldf_s["strike"].tolist()

    def _get_bl(k, field, default=0):
        return baseline.get(int(k), {}).get(field, default)

    def _delta_chart(strikes, calls_vals, puts_vals, title, fmt=","):
        """Vertical chart: strikes on Y, calls right (blue), puts left (magenta)."""
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=strikes, x=[-abs(v) for v in puts_vals],
            orientation="h", marker_color="rgba(255,0,255,0.7)", name="Puts",
        ))
        fig.add_trace(go.Bar(
            y=strikes, x=[abs(v) for v in calls_vals],
            orientation="h", marker_color="rgba(30,144,255,0.7)", name="Calls",
        ))
        fig.add_hline(y=spot, line_dash="dash", line_color="#ffd600", line_width=1.5,
                      annotation_text=f"Spot {spot:.0f}",
                      annotation_font_color="#ffd600", annotation_font_size=9,
                      annotation_position="right")
        fig.update_layout(
            height=620, template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            barmode="overlay", showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        xanchor="center", x=0.5, font=dict(size=9)),
            margin=dict(t=20, b=30, l=70, r=30), font=dict(size=9),
            xaxis=dict(gridcolor="#1a2a4a", zeroline=True, zerolinecolor="#444",
                       tickformat=fmt, title="← Puts     Calls →"),
            yaxis=dict(gridcolor="#1a2a4a", tickformat=".0f", title="Strike", dtick=5),
        )
        return fig

    # ── Single expander, 2x2 grid + full-width Panel 5 ──
    with st.expander(f"📊 Delta Analysis  ({bl_caption})", expanded=False):

        # Row 1: Panel 1 + Panel 2
        r1c1, r1c2 = st.columns(2)

        with r1c1:
            st.markdown("**Volume Delta from Open**")
            c_delta = [max(0, int(r["c_volume"]) - _get_bl(r["strike"], "c_volume")) for _, r in ldf_s.iterrows()]
            p_delta = [max(0, int(r["p_volume"]) - _get_bl(r["strike"], "p_volume")) for _, r in ldf_s.iterrows()]
            fig1 = _delta_chart(strikes_list, c_delta, p_delta, "Volume Delta")
            sd = straddle_info
            if sd.get("upper") and sd.get("lower") and sd.get("price"):
                for y_val, label in [(sd["upper"], f"↑ +{sd['price']:.1f} ({sd['upper']:.0f})"),
                                      (sd["lower"], f"↓ −{sd['price']:.1f} ({sd['lower']:.0f})")]:
                    fig1.add_hline(y=y_val, line_dash="dot", line_color="#ffd600",
                                   line_width=1.5, annotation_text=label,
                                   annotation_font_color="#ffd600", annotation_font_size=9,
                                   annotation_position="left")
                fig1.update_layout(title=dict(
                    text=f"Volume Delta &nbsp;<span style='font-size:9px;color:#888'>Straddle @ open: {sd['price']:.2f} pts</span>",
                    font=dict(size=11, color="#a0a0a0")))
            st.plotly_chart(fig1, use_container_width=True, key="dp1")

        with r1c2:
            st.markdown("**GEX Delta from Open**")
            c_gex_d = [float(r["call_gex"]) - _get_bl(r["strike"], "call_gex") for _, r in ldf_s.iterrows()]
            p_gex_d = [abs(float(r["put_gex"])) - abs(_get_bl(r["strike"], "put_gex")) for _, r in ldf_s.iterrows()]
            fig2 = _delta_chart(strikes_list, c_gex_d, p_gex_d, "GEX Delta")
            fig2.update_layout(xaxis_title="← Put GEX Δ     Call GEX Δ →")
            st.plotly_chart(fig2, use_container_width=True, key="dp2")

        # Row 2: Panel 3 + Panel 4
        r2c1, r2c2 = st.columns(2)

        with r2c1:
            st.markdown("**Volume-GEX (Intraday Gamma)**")
            c_vgex = [float(r["c_volume"]) * float(r["c_gamma"]) * 100 for _, r in ldf_s.iterrows()]
            p_vgex = [float(r["p_volume"]) * float(r["p_gamma"]) * 100 for _, r in ldf_s.iterrows()]
            fig3 = _delta_chart(strikes_list, c_vgex, p_vgex, "Volume-GEX", fmt=".1f")
            fig3.update_layout(xaxis_title="← Put Vol-GEX     Call Vol-GEX →")
            st.plotly_chart(fig3, use_container_width=True, key="dp3")

        with r2c2:
            st.markdown("**V/OI Ratio**")
            c_voi = [float(r["c_voi"]) for _, r in ldf_s.iterrows()]
            p_voi = [float(r["p_voi"]) for _, r in ldf_s.iterrows()]
            fig4 = _delta_chart(strikes_list, c_voi, p_voi, "V/OI", fmt=".2f")
            fig4.update_layout(xaxis_title="← Put V/OI     Call V/OI →")
            st.plotly_chart(fig4, use_container_width=True, key="dp4")

        # Row 3: Panel 5 full width
        st.markdown("**Spot & Straddle Through the Day**")
        spot_df = pd.DataFrame()
        try:
            from tvDatafeed import TvDatafeed, Interval
            tv = TvDatafeed()
            for ex in ["CBOE", "SP", "FOREXCOM", "OANDA", "TVC"]:
                try:
                    df_tv = tv.get_hist(symbol="SPX", exchange=ex,
                                        interval=Interval.in_1_minute, n_bars=400)
                    if df_tv is not None and not df_tv.empty:
                        import pytz as _pytz
                        _nyt = _pytz.timezone("US/Eastern")
                        if df_tv.index.tz is None:
                            df_tv.index = df_tv.index.tz_localize("UTC")
                        df_tv.index = df_tv.index.tz_convert(_nyt)
                        from datetime import time as dtime
                        df_tv = df_tv[
                            (df_tv.index.date == today_et) &
                            (df_tv.index.time >= dtime(9, 30)) &
                            (df_tv.index.time <= dtime(16, 0))
                        ]
                        if not df_tv.empty:
                            spot_df = df_tv
                            break
                except:
                    continue
        except ImportError:
            pass

        straddle_ts = st.session_state.get("straddle_ts", [])

        if spot_df.empty and not straddle_ts:
            st.caption("Spot & straddle chart available during RTH.")
        else:
            fig5 = go.Figure()

            if not spot_df.empty:
                fig5.add_trace(go.Scatter(
                    x=spot_df.index.to_pydatetime(),
                    y=spot_df["close"].tolist(),
                    name="Spot", line=dict(color="#ff00ff", width=1.5),
                    yaxis="y1",
                ))

            if straddle_ts:
                import pytz as _pytz2
                _et2 = _pytz2.timezone("US/Eastern")
                s_dts, s_vals, s_colors = [], [], []
                for p in straddle_ts:
                    t_str = p["time"].replace(" ET", "")
                    try:
                        hh, mm = int(t_str[:2]), int(t_str[3:5])
                        dt = _et2.localize(datetime(today_et.year, today_et.month, today_et.day, hh, mm))
                        s_dts.append(dt)
                        s_vals.append(p["straddle"])
                        s_colors.append("#ffd600" if p["source"] == "baseline" else "#00c853")
                    except:
                        continue

                if s_dts:
                    fig5.add_trace(go.Scatter(
                        x=s_dts, y=s_vals,
                        name="Straddle", line=dict(color="#00c853", width=1.5),
                        mode="lines+markers",
                        marker=dict(color=s_colors, size=6),
                        yaxis="y2",
                    ))

            fig5.update_layout(
                height=380, template="plotly_dark",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                margin=dict(t=20, b=40, l=60, r=60),
                font=dict(size=9, color="#a0a0a0"),
                legend=dict(orientation="h", yanchor="bottom", y=1.01,
                            xanchor="center", x=0.5, font=dict(size=10)),
                xaxis=dict(gridcolor="#1a2a4a",
                           title=dict(text="Time (ET)", font=dict(color="#a0a0a0")),
                           tickangle=-45, nticks=20),
                yaxis=dict(gridcolor="#1a2a4a",
                           title=dict(text="Spot", font=dict(color="#ff00ff")),
                           tickfont=dict(color="#ff00ff")),
                yaxis2=dict(title=dict(text="Straddle", font=dict(color="#00c853")),
                            tickfont=dict(color="#00c853"),
                            overlaying="y", side="right",
                            gridcolor="rgba(0,200,83,0.1)"),
            )
            st.plotly_chart(fig5, use_container_width=True, key="dp5")
            st.caption(f"Spot: tvDatafeed 1-min. Straddle: {len(straddle_ts)} pts (🟡=baseline 🟢=live). Refreshes every 3 min.")

# ══════════════════════════════════════
# LEVELS + METRICS
# ══════════════════════════════════════
st.markdown("---")

def _lv_metric(label, key, color):
    v = levels.get(key)
    val = f"{v:,}" if v else "—"
    st.markdown(f'<div style="font-size:11px;color:#888;">{label}</div>'
                f'<div style="font-size:18px;font-weight:700;color:{color};">{val}</div>',
                unsafe_allow_html=True)

l1, l2, l3, l4 = st.columns(4)
with l1:
    _lv_metric("Call Wall", "call_wall", LEVEL_COLORS["call_wall"])
    _lv_metric("COI", "coi", LEVEL_COLORS["coi"])
with l2:
    _lv_metric("Put Wall", "put_wall", LEVEL_COLORS["put_wall"])
    _lv_metric("POI", "poi", LEVEL_COLORS["poi"])
with l3:
    _lv_metric("+GEX", "pgex", LEVEL_COLORS["pgex"])
    _lv_metric("−GEX", "ngex", LEVEL_COLORS["ngex"])
with l4:
    _lv_metric("+Trans", "ptrans", LEVEL_COLORS["ptrans"])
    _lv_metric("−Trans", "ntrans", LEVEL_COLORS["ntrans"])

st.markdown("---")
m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1: st.metric("PCR (Vol)", f"{levels.get('pcr_volume',0):.3f}")
with m2: st.metric("PCR (OI)", f"{levels.get('pcr_oi',0):.3f}")
with m3: st.metric("Call Vol", f"{levels.get('total_call_volume',0):,}")
with m4: st.metric("Put Vol", f"{levels.get('total_put_volume',0):,}")
with m5: st.metric("Call OI", f"{levels.get('total_call_oi',0):,}")
with m6: st.metric("Put OI", f"{levels.get('total_put_oi',0):,}")

st.markdown("---")
p1, p2, p3, p4 = st.columns(4)
pc = quote.get("previousClose", 0); hi = quote.get("highPrice", 0)
lo = quote.get("lowPrice", 0); op = quote.get("openPrice", 0)
with p1: st.metric("Open", f"{op:,.2f}" if op > 0 else "—")
with p2: st.metric("High", f"{hi:,.2f}" if hi > 0 else "—")
with p3: st.metric("Low", f"{lo:,.2f}" if lo > 0 else "—")
with p4: st.metric("Prev Close", f"{pc:,.2f}" if pc > 0 else "—")

st.markdown("---")
st.caption(f"SPX Gamma Dashboard — {get_ny_time()}")
