"""
app.py — SPX Gamma Exposure Dashboard
Excel-matching ladder with heatmap, inline bars, color-coded level rows.
Delta panels: Volume, GEX, Volume-GEX, V/OI — all vs opening baseline.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import logging

from data_fetcher import get_spx_quote, get_options_chain, get_active_source
from calculations import compute_chain_metrics, compute_dashboard_levels, filter_chain_for_display
from utils import get_ny_time, get_ny_datetime, is_market_hours, get_upcoming_expirations

st.set_page_config(page_title="SPX Gamma Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── CSS ──
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

# ══════════════════════════════════════
# BASELINE LOADING
# Priority: 1) GitHub Actions JSON  2) Session state (first load)
# ══════════════════════════════════════
try:
    import pytz
    today_et = datetime.now(pytz.timezone("US/Eastern")).date()
except:
    today_et = datetime.now().date()

today_str = today_et.strftime("%Y-%m-%d")
baseline_path = f"data/baseline/{today_str}.json"

def _chain_to_baseline(chain_df, source, timestamp):
    """Convert current chain to baseline dict."""
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
    return {"strikes": bl, "source": source, "timestamp_et": timestamp, "date": today_str}

# Try GitHub Actions file first
baseline = None
baseline_source = None
baseline_time = None

if os.path.exists(baseline_path):
    try:
        with open(baseline_path) as f:
            bl_data = json.load(f)
        if bl_data.get("date") == today_str:
            baseline = {int(k): v for k, v in bl_data["strikes"].items()}
            baseline_source = "📸 GitHub Actions"
            baseline_time = bl_data.get("timestamp_et", "09:31 ET")
            logger.info("Loaded baseline from GitHub Actions: %s", baseline_path)
    except Exception as e:
        logger.warning("Failed to load baseline file: %s", e)

# Fallback: session state
if baseline is None:
    if "baseline" not in st.session_state or st.session_state.get("baseline_date") != today_str:
        # First load today — save current chain as baseline
        if not full_chain.empty:
            now_et_str = et_now.strftime("%H:%M ET")
            bl_data = _chain_to_baseline(full_chain, "first_load", now_et_str)
            st.session_state["baseline"] = bl_data
            st.session_state["baseline_date"] = today_str
            logger.info("Baseline set from first load at %s", now_et_str)
    if "baseline" in st.session_state:
        bl_data = st.session_state["baseline"]
        baseline = {int(k): v for k, v in bl_data["strikes"].items()}
        baseline_source = "⏱ First load"
        baseline_time = bl_data.get("timestamp_et", "unknown")

# Show baseline info in sidebar
with st.sidebar:
    st.divider()
    if baseline:
        st.caption(f"Baseline: {baseline_source}")
        st.caption(f"Captured: {baseline_time}")
    else:
        st.caption("⚠️ No baseline yet")

# ── DTE ──
try:
    import pytz
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

# ── Level colors ──
LEVEL_COLORS = {
    "call_wall": "rgb(233,113,50)",
    "put_wall":  "rgb(204,153,0)",
    "coi":       "rgb(97,203,243)",
    "poi":       "rgb(216,109,205)",
    "pgex":      "rgb(148,220,248)",
    "ngex":      "rgb(228,158,221)",
    "ptrans":    "rgb(202,237,251)",
    "ntrans":    "rgb(242,206,239)",
}
LEVEL_LABELS = {
    "call_wall":"Call Wall","put_wall":"Put Wall","coi":"COI","poi":"POI",
    "pgex":"pGEX","ngex":"nGEX","ptrans":"pTrans","ntrans":"nTrans",
}

# ══════════════════════════════════════
# MAIN: Ladder (55%) + Charts (45%)
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

    mx_cv = max(ldf["c_volume"].max(), 1)
    mx_pv = max(ldf["p_volume"].max(), 1)
    mx_gex = max(abs(ldf["net_gex"].max()), abs(ldf["net_gex"].min()), 1)
    mx_coi = max(ldf["c_oi"].max(), 1)
    mx_poi = max(ldf["p_oi"].max(), 1)
    mx_toi = max(ldf["total_oi"].max(), 1)

    def _bar(val, mx, color, w=70):
        if mx <= 0 or val <= 0: return ""
        pct = min(val / mx * w, w)
        return f'<div style="background:{color};height:11px;width:{pct:.0f}%;border-radius:2px;display:inline-block;"></div>'

    def _heat(val, mx, base_color):
        if mx <= 0 or val <= 0: return ""
        intensity = min(val / mx, 1.0) * 0.5
        return f"background:rgba({base_color},{intensity:.2f});"

    rows_html = []
    for _, r in ldf.iterrows():
        k = int(r["strike"])
        bg = ""
        if k == atm:
            bg = "background:rgba(30,144,255,0.25);"
        elif k in strike_levels:
            first_key = strike_levels[k][0]
            rgb = LEVEL_COLORS[first_key]
            bg = f"background:{rgb.replace('rgb','rgba').replace(')',',0.15)')};"

        label_parts = []
        if k in strike_levels:
            for lk in strike_levels[k]:
                c = LEVEL_COLORS[lk]
                label_parts.append(f'<span style="color:{c};font-weight:bold;font-size:9px;">{LEVEL_LABELS[lk]}</span>')
        label_html = " ".join(label_parts)

        cv_bar = _bar(r["c_volume"], mx_cv, "#1e90ff")
        pv_bar = _bar(r["p_volume"], mx_pv, "#ff00ff")
        gv = r["net_gex"]; gc = "#1e90ff" if gv >= 0 else "#ff00ff"
        gex_bar = _bar(abs(gv), mx_gex, gc)
        gex_str = f'<span style="color:{gc}">{gv:,.0f}</span>'

        coi_bg = _heat(r["c_oi"], mx_coi, "30,144,255")
        poi_bg = _heat(r["p_oi"], mx_poi, "255,0,255")
        toi_bg = _heat(r["total_oi"], mx_toi, "100,100,255")
        cv_bg = _heat(r["c_volume"], mx_cv, "30,144,255")
        pv_bg = _heat(r["p_volume"], mx_pv, "255,0,255")

        dex = r["net_dex"]; dc = "#1e90ff" if dex >= 0 else "#ff00ff"
        noi = r["net_oi"]; nc = "#1e90ff" if noi >= 0 else "#ff00ff"
        strike_color = "#ffd600" if k == atm else "#e0e0e0"
        spot_dot = " •" if k == atm else ""

        rows_html.append(f"""<tr style="{bg}">
<td style="text-align:right;font-size:10px;{cv_bg}">{int(r['c_volume']):,}</td>
<td style="width:50px;">{cv_bar}</td>
<td style="text-align:center;font-weight:bold;font-size:11px;color:{strike_color}">{k}{spot_dot}</td>
<td style="width:50px;">{pv_bar}</td>
<td style="text-align:left;font-size:10px;{pv_bg}">{int(r['p_volume']):,}</td>
<td style="text-align:right;font-size:10px;">{gex_str}</td>
<td style="width:45px;">{gex_bar}</td>
<td style="text-align:right;font-size:10px;color:{dc}">{int(dex):,}</td>
<td style="text-align:right;font-size:10px;{coi_bg}">{int(r['c_oi']):,}</td>
<td style="text-align:right;font-size:10px;{poi_bg}">{int(r['p_oi']):,}</td>
<td style="text-align:right;font-size:10px;{toi_bg}">{int(r['total_oi']):,}</td>
<td style="text-align:right;font-size:10px;color:{nc}">{int(noi):,}</td>
<td style="text-align:right;font-size:10px;">{r['pct_from_spot']:.2%}</td>
<td style="font-size:9px;padding-left:3px;">{label_html}</td>
</tr>""")

    table_html = f"""<div style="max-height:850px;overflow-y:auto;border:1px solid #262730;border-radius:6px;">
<table style="width:100%;border-collapse:collapse;font-family:monospace;font-size:10px;">
<thead style="position:sticky;top:0;background:#16213e;z-index:1;">
<tr style="color:#a0a0a0;font-size:9px;">
<th>C Vol</th><th></th><th>Strike</th><th></th><th>P Vol</th>
<th>GEX</th><th></th><th>DEX</th><th>C OI</th><th>P OI</th><th>Tot OI</th><th>Net OI</th><th>%Spot</th><th>Level</th>
</tr></thead><tbody>{''.join(rows_html)}</tbody></table></div>"""
    st.markdown(table_html, unsafe_allow_html=True)

with col_charts:
    cdf = display_chain.sort_values("strike").copy()

    def _prof(y_pos, y_neg, title, split=False, tfmt=","):
        fig = go.Figure()
        if split:
            fig.add_trace(go.Bar(x=cdf["strike"], y=y_pos, marker_color="rgba(30,144,255,0.7)", name="+"))
            fig.add_trace(go.Bar(x=cdf["strike"], y=y_neg, marker_color="rgba(255,0,255,0.7)", name="−"))
        else:
            net = y_pos + y_neg if y_neg is not None else y_pos
            colors = ["#1e90ff" if v >= 0 else "#ff00ff" for v in net]
            fig.add_trace(go.Bar(x=cdf["strike"], y=net, marker_color=colors))
        fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1)
        fig.update_layout(
            title=dict(text=title, font=dict(size=11, color="#a0a0a0")),
            height=205, template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
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
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#555",
                     "dtick": 10, "tickfont": {"size": 8, "color": "#777"}},
            "bar": {"color": "#ffd600", "thickness": 0.3},
            "bgcolor": "#0e1117", "borderwidth": 0,
            "steps": [
                {"range": [0, 10], "color": "rgba(255,0,255,0.5)"},
                {"range": [10, 25], "color": "rgba(150,150,150,0.3)"},
                {"range": [25, 75], "color": "rgba(30,144,255,0.35)"},
                {"range": [75, 90], "color": "rgba(150,150,150,0.3)"},
                {"range": [90, 100], "color": "rgba(255,0,255,0.5)"},
            ],
            "threshold": {"line": {"color": "#ffd600", "width": 3}, "thickness": 0.8, "value": value},
        },
    ))
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                      font={"color": "#e0e0e0"}, height=180,
                      margin=dict(t=30, b=0, l=20, r=20))
    return fig

cbp = levels.get("avg_bp_call", 50)
pbp = levels.get("avg_bp_put", 50)
combo = (cbp + pbp) / 2 if (cbp + pbp) > 0 else 50
g1, g2, g3 = st.columns(3)
with g1: st.plotly_chart(_gauge(cbp, "Call BP%"), use_container_width=True, key="g1")
with g2: st.plotly_chart(_gauge(pbp, "Put BP%"), use_container_width=True, key="g2")
with g3: st.plotly_chart(_gauge(combo, "Combined BP%"), use_container_width=True, key="g3")
if not is_market_hours(): st.caption("⚠️ BP% gauges need RTH data.")

# ══════════════════════════════════════
# DELTA PANELS — dropdown
# ══════════════════════════════════════
st.markdown("---")

if baseline:
    bl_label = f"{baseline_source} @ {baseline_time}"
    panel = st.selectbox(
        f"📊 Delta Panels (vs baseline: {bl_label})",
        ["— Select Panel —",
         "1. Volume Delta from Open",
         "2. GEX Delta from Open",
         "3. Volume-GEX (intraday gamma)",
         "4. V/OI Ratio"],
        index=0,
    )

    # Build per-strike delta arrays aligned to display_chain
    def _get_bl(k, field, default=0):
        return baseline.get(int(k), {}).get(field, default)

    def _delta_chart(strikes, calls_vals, puts_vals, title, baseline_label, fmt=","):
        """
        Vertical layout: strikes on Y-axis, calls extend RIGHT (blue),
        puts extend LEFT (magenta). Spot line horizontal.
        """
        fig = go.Figure()

        # Puts go left (negative x)
        fig.add_trace(go.Bar(
            y=strikes, x=[-v for v in puts_vals],
            orientation="h",
            marker_color="rgba(255,0,255,0.7)",
            name="Puts",
        ))
        # Calls go right (positive x)
        fig.add_trace(go.Bar(
            y=strikes, x=calls_vals,
            orientation="h",
            marker_color="rgba(30,144,255,0.7)",
            name="Calls",
        ))

        # Spot horizontal line
        fig.add_hline(y=spot, line_dash="dash", line_color="#ffd600",
                      line_width=1.5, annotation_text=f"Spot {spot:.0f}",
                      annotation_font_color="#ffd600", annotation_font_size=9)

        fig.update_layout(
            title=dict(
                text=f"{title} &nbsp;<span style='font-size:10px;color:#666'>vs {baseline_label}</span>",
                font=dict(size=12, color="#a0a0a0")
            ),
            height=600, template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            barmode="overlay",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02,
                        xanchor="center", x=0.5, font=dict(size=9)),
            margin=dict(t=50, b=30, l=70, r=30),
            font=dict(size=9),
            xaxis=dict(gridcolor="#1a2a4a", zeroline=True,
                       zerolinecolor="#444", tickformat=fmt,
                       title="← Puts &nbsp;&nbsp;&nbsp; Calls →"),
            yaxis=dict(gridcolor="#1a2a4a", tickformat=".0f",
                       title="Strike", dtick=5),
        )
        return fig

    ldf_sorted = display_chain.sort_values("strike").copy()
    strikes_list = ldf_sorted["strike"].tolist()

    if panel == "1. Volume Delta from Open":
        c_delta = [max(0, int(r["c_volume"]) - _get_bl(r["strike"], "c_volume")) for _, r in ldf_sorted.iterrows()]
        p_delta = [max(0, int(r["p_volume"]) - _get_bl(r["strike"], "p_volume")) for _, r in ldf_sorted.iterrows()]
        fig = _delta_chart(strikes_list, c_delta, p_delta,
                           "Volume Delta from Open", baseline_time, fmt=",")
        st.plotly_chart(fig, use_container_width=True, key="dp1")
        st.caption("Bars show volume added since baseline. Zero-delta strikes show no bar.")

    elif panel == "2. GEX Delta from Open":
        c_gex_delta = [float(r["call_gex"]) - _get_bl(r["strike"], "call_gex") for _, r in ldf_sorted.iterrows()]
        p_gex_delta = [abs(float(r["put_gex"])) - abs(_get_bl(r["strike"], "put_gex")) for _, r in ldf_sorted.iterrows()]
        fig = _delta_chart(strikes_list, c_gex_delta, p_gex_delta,
                           "GEX Delta from Open", baseline_time, fmt=",")
        st.plotly_chart(fig, use_container_width=True, key="dp2")
        st.caption("Change in gamma exposure since baseline. Positive = more gamma created.")

    elif panel == "3. Volume-GEX (intraday gamma)":
        # Replace OI with today's volume in GEX formula
        c_vgex = [float(r["c_volume"]) * float(r["c_gamma"]) * 100 for _, r in ldf_sorted.iterrows()]
        p_vgex = [float(r["p_volume"]) * float(r["p_gamma"]) * 100 for _, r in ldf_sorted.iterrows()]
        fig = _delta_chart(strikes_list, c_vgex, p_vgex,
                           "Volume-GEX (Volume × Gamma × 100)", baseline_time, fmt=".1f")
        st.plotly_chart(fig, use_container_width=True, key="dp3")
        st.caption("GEX using today's volume instead of OI. Shows intraday gamma being created.")

    elif panel == "4. V/OI Ratio":
        c_voi = [float(r["c_voi"]) for _, r in ldf_sorted.iterrows()]
        p_voi = [float(r["p_voi"]) for _, r in ldf_sorted.iterrows()]
        fig = _delta_chart(strikes_list, c_voi, p_voi,
                           "V/OI Ratio (Volume ÷ Open Interest)", baseline_time, fmt=".2f")
        st.plotly_chart(fig, use_container_width=True, key="dp4")
        st.caption("Ratio > 1 means more volume than prior OI — new positions being opened aggressively.")

else:
    st.info("⏳ Baseline not yet available. Will be set on first chain load.")

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
