"""
app.py — SPX Gamma Exposure Dashboard
Replicates SPX_Gamma_Dashboard_v1_3b.xlsm layout:
  Left:  Ladder table with inline bars, color-coded rows, level labels
  Right: 4 stacked profile charts
  Bottom: Gauges + metrics
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import logging

from data_fetcher import get_spx_quote, get_options_chain, get_active_source
from calculations import compute_chain_metrics, compute_dashboard_levels, filter_chain_for_display
from utils import check_password, get_ny_time, get_ny_datetime, is_market_hours, get_upcoming_expirations

st.set_page_config(page_title="SPX Gamma Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

logging.basicConfig(level=logging.INFO)

# ── CSS: hide Streamlit chrome + custom styles ──
st.markdown("""
<style>
    #MainMenu, header, footer, [data-testid="stHeader"], [data-testid="stToolbar"] {display:none!important;visibility:hidden!important;}
    .block-container {padding-top:0.5rem;}
    .gamma-banner {text-align:center;padding:8px;border-radius:6px;font-weight:700;font-size:1.1em;margin:4px 0;}
    .gamma-call {background:rgba(0,200,83,0.15);color:#00c853;border:1px solid #00c853;}
    .gamma-put {background:rgba(255,23,68,0.15);color:#ff1744;border:1px solid #ff1744;}
    .status-bar {display:flex;justify-content:space-between;align-items:center;padding:4px 12px;background:#16213e;border-radius:6px;margin-bottom:8px;}
    .status-text {font-size:0.82em;color:#a0a0a0;}
</style>
""", unsafe_allow_html=True)

# ── Auth ──
if not check_password():
    st.stop()

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
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=True)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear(); st.rerun()
    st.divider()
    et_now = get_ny_datetime()
    st.markdown(f"**{'🟢 MARKET OPEN' if is_market_hours() else '🔴 MARKET CLOSED'}**")
    st.markdown(f"**ET:** {et_now.strftime('%H:%M:%S')}")

if auto_refresh:
    @st.fragment(run_every=60)
    def _tick(): pass
    _tick()

# ── Data ──
@st.cache_data(ttl=55, show_spinner=False)
def load_data(exp_date, n_above, n_below, _ts):
    quote = get_spx_quote()
    spot = quote.get("lastPrice", 0)
    chain = get_options_chain(exp_date)
    if chain is None or chain.empty:
        return quote, pd.DataFrame(), {}, pd.DataFrame()
    chain = compute_chain_metrics(chain, spot)
    levels = compute_dashboard_levels(chain, spot)
    display = filter_chain_for_display(chain, spot, n_above, n_below)
    return quote, chain, levels, display

ts = int(datetime.now().timestamp() // 55)
with st.spinner("Fetching…"):
    quote, full_chain, levels, display_chain = load_data(exp_str, num_above, num_below, ts)

spot = quote.get("lastPrice", 0)
if display_chain.empty:
    st.error(f"❌ No chain data for {exp_str}. Try another expiration.")
    st.stop()

# ── DTE label ──
try:
    import pytz
    dte = (datetime.strptime(exp_str, "%Y-%m-%d").date() - datetime.now(pytz.timezone("US/Eastern")).date()).days
    dte_label = "0DTE" if dte == 0 else f"{dte}DTE"
except:
    dte_label = selected_label

# ── Header bar ──
pct_chg = quote.get("percentChange", 0)
net_chg = quote.get("netChange", 0)
if net_chg == 0 and pct_chg != 0:
    pc = quote.get("previousClose", 0)
    net_chg = round(spot - pc, 2) if pc > 0 else round(spot * pct_chg / 100, 2)

st.markdown(f"""
<div class="status-bar">
    <span class="status-text">SPX {spot:,.2f} &nbsp; {net_chg:+.2f} ({pct_chg:+.2f}%) &nbsp;•&nbsp; {selected_label} · {dte_label} ({exp_str})</span>
    <span class="status-text">NY: {get_ny_time()} &nbsp;•&nbsp; ATM: {levels.get('centered_spot',0)}</span>
</div>
""", unsafe_allow_html=True)

# ── Gamma banner ──
dom = levels.get("gamma_dominant", "N/A")
cls = "gamma-call" if dom == "CALL" else "gamma-put"
st.markdown(f"""<div class="gamma-banner {cls}">
    Gamma is {dom} dominant &nbsp;•&nbsp; GEX Ratio: {levels.get('gex_ratio',0):.2f}
    &nbsp;•&nbsp; Net GEX: {levels.get('total_net_gex',0):,}
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# MAIN LAYOUT: Ladder (left 55%) + Charts (right 45%)
# ══════════════════════════════════════════════
col_ladder, col_charts = st.columns([0.55, 0.45])

# ── LEFT: Ladder Table with inline bars + color-coded rows + level labels ──
with col_ladder:
    ldf = display_chain.sort_values("strike", ascending=False).copy()
    atm = levels.get("centered_spot", 0)

    # Map level strikes to labels
    level_map = {}
    for key, label, color in [
        ("call_wall", "Call Wall", "#e97132"),
        ("put_wall", "Put Wall", "#cc9900"),
        ("coi", "COI", "#61cbf3"),
        ("poi", "POI", "#d86dcd"),
        ("pgex", "pGEX", "#94dcf8"),
        ("ngex", "nGEX", "#e49edd"),
        ("ptrans", "pTrans", "#caedfb"),
        ("ntrans", "nTrans", "#f2ceef"),
    ]:
        v = levels.get(key)
        if v is not None:
            level_map[v] = level_map.get(v, [])
            level_map[v].append((label, color))

    # Build HTML table
    def _bar(val, max_val, color, width_pct=80):
        if max_val <= 0 or val <= 0:
            return ""
        w = min(val / max_val * width_pct, width_pct)
        return f'<div style="background:{color};height:12px;width:{w:.0f}%;border-radius:2px;display:inline-block;"></div>'

    max_cvol = ldf["c_volume"].max() if ldf["c_volume"].max() > 0 else 1
    max_pvol = ldf["p_volume"].max() if ldf["p_volume"].max() > 0 else 1
    max_gex = max(abs(ldf["net_gex"].max()), abs(ldf["net_gex"].min()), 1)

    rows_html = []
    for _, r in ldf.iterrows():
        k = int(r["strike"])

        # Row background color by zone
        bg = "transparent"
        if k == atm:
            bg = "rgba(0,200,83,0.20)"
        elif k in level_map:
            colors = [c for _, c in level_map[k]]
            bg = colors[0] + "33"  # 20% opacity

        # Level label
        label_html = ""
        if k in level_map:
            tags = " ".join(f'<span style="color:{c};font-weight:bold;font-size:10px;">{l}</span>' for l, c in level_map[k])
            label_html = tags

        # Inline bars
        cvol_bar = _bar(r["c_volume"], max_cvol, "#00c853")
        pvol_bar = _bar(r["p_volume"], max_pvol, "#ff4757")
        gex_val = r["net_gex"]
        gex_color = "#00c853" if gex_val >= 0 else "#ff1744"
        gex_bar = _bar(abs(gex_val), max_gex, gex_color)

        gex_str = f'<span style="color:{gex_color}">{gex_val:,.0f}</span>'

        spot_marker = " •" if k == atm else ""

        rows_html.append(f"""<tr style="background:{bg};">
            <td style="text-align:right;font-size:11px;">{int(r['c_volume']):,}</td>
            <td style="width:60px;">{cvol_bar}</td>
            <td style="text-align:center;font-weight:bold;font-size:12px;color:{'#ffd600' if k==atm else '#e0e0e0'}">{k}{spot_marker}</td>
            <td style="width:60px;">{pvol_bar}</td>
            <td style="text-align:left;font-size:11px;">{int(r['p_volume']):,}</td>
            <td style="text-align:right;font-size:11px;">{gex_str}</td>
            <td style="width:60px;">{gex_bar}</td>
            <td style="text-align:right;font-size:11px;">{int(r['net_dex']):,}</td>
            <td style="text-align:right;font-size:11px;">{int(r['c_oi']):,}</td>
            <td style="text-align:right;font-size:11px;">{int(r['p_oi']):,}</td>
            <td style="text-align:right;font-size:11px;">{r['pct_from_spot']:.2%}</td>
            <td style="font-size:9px;padding-left:4px;">{label_html}</td>
        </tr>""")

    table_html = f"""
    <div style="max-height:900px;overflow-y:auto;border:1px solid #262730;border-radius:6px;">
    <table style="width:100%;border-collapse:collapse;font-family:monospace;font-size:11px;">
    <thead style="position:sticky;top:0;background:#16213e;z-index:1;">
        <tr style="color:#a0a0a0;font-size:10px;">
            <th>C Vol</th><th></th><th>Strike</th><th></th><th>P Vol</th>
            <th>GEX</th><th></th><th>DEX</th><th>C OI</th><th>P OI</th><th>%Spot</th><th>Level</th>
        </tr>
    </thead>
    <tbody>{''.join(rows_html)}</tbody>
    </table></div>"""

    st.markdown(table_html, unsafe_allow_html=True)

# ── RIGHT: 4 stacked profile charts ──
with col_charts:
    cdf = display_chain.sort_values("strike").copy()

    def _make_profile(y_pos, y_neg, title, split=False):
        fig = go.Figure()
        if split:
            fig.add_trace(go.Bar(x=cdf["strike"], y=y_pos, marker_color="rgba(0,200,83,0.7)", name="+"))
            fig.add_trace(go.Bar(x=cdf["strike"], y=y_neg, marker_color="rgba(255,23,68,0.7)", name="−"))
        else:
            net = y_pos + y_neg if y_neg is not None else y_pos
            colors = ["#00c853" if v >= 0 else "#ff1744" for v in net]
            fig.add_trace(go.Bar(x=cdf["strike"], y=net, marker_color=colors))
        fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1)
        fig.update_layout(
            title=dict(text=title, font=dict(size=11, color="#a0a0a0")),
            height=210, template="plotly_dark",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            showlegend=False,
            margin=dict(t=30, b=20, l=40, r=10),
            font=dict(size=9),
            xaxis=dict(showticklabels=False, gridcolor="#1a2a4a"),
            yaxis=dict(gridcolor="#1a2a4a", tickformat=".0f" if not any("raw" in str(c) for c in [title]) else ".3f"),
        )
        # Show x-axis labels only on bottom chart
        return fig

    # 1. Net Gamma Exposure
    fig1 = _make_profile(cdf["net_gex"], None, "Net Gamma Exposure")
    fig1.update_yaxes(tickformat=",")
    st.plotly_chart(fig1, use_container_width=True, key="p1")

    # 2. Net Delta-Adjusted Gamma Exposure
    net_dadj = cdf["dadj_cgex"] + cdf["dadj_pgex"]
    fig2 = _make_profile(net_dadj, None, "Net Delta-Adjusted Gamma Exposure")
    fig2.update_yaxes(tickformat=".4f")
    st.plotly_chart(fig2, use_container_width=True, key="p2")

    # 3. Split Gamma Exposure
    fig3 = _make_profile(cdf["raw_cgex"], cdf["raw_pgex"], "Split Gamma Exposure", split=True)
    fig3.update_yaxes(tickformat=".4f")
    st.plotly_chart(fig3, use_container_width=True, key="p3")

    # 4. Split Delta-Adjusted Gamma Exposure
    fig4 = _make_profile(cdf["dadj_cgex"], cdf["dadj_pgex"], "Split Delta-Adjusted Gamma Exposure", split=True)
    fig4.update_yaxes(tickformat=".4f")
    fig4.update_xaxes(showticklabels=True)  # Show strikes on bottom chart
    st.plotly_chart(fig4, use_container_width=True, key="p4")

# ══════════════════════════════════════════════
# BOTTOM: Gauges + Metrics
# ══════════════════════════════════════════════
st.markdown("---")

# Gauges
def _gauge(value, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={"suffix": "%", "font": {"size": 26, "color": "#e0e0e0"}},
        title={"text": title, "font": {"size": 12, "color": "#a0a0a0"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#555",
                     "dtick": 10, "tickfont": {"size": 8, "color": "#777"}},
            "bar": {"color": "#ffd600", "thickness": 0.25},
            "bgcolor": "#0e1117", "borderwidth": 1, "bordercolor": "#333",
            "steps": [
                {"range": [0, 10], "color": "rgba(255,23,68,0.5)"},
                {"range": [10, 25], "color": "rgba(150,150,150,0.3)"},
                {"range": [25, 75], "color": "rgba(0,200,83,0.35)"},
                {"range": [75, 90], "color": "rgba(150,150,150,0.3)"},
                {"range": [90, 100], "color": "rgba(255,23,68,0.5)"},
            ],
            "threshold": {"line": {"color": "#ffd600", "width": 3}, "thickness": 0.8, "value": value},
        },
    ))
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                      font={"color": "#e0e0e0"}, height=190, margin=dict(t=35, b=5, l=25, r=25))
    return fig

call_bp = levels.get("avg_bp_call", 50)
put_bp = levels.get("avg_bp_put", 50)
combo = (call_bp + put_bp) / 2 if (call_bp + put_bp) > 0 else 50

g1, g2, g3 = st.columns(3)
with g1:
    st.plotly_chart(_gauge(call_bp, "Call BP%"), use_container_width=True, key="g1")
with g2:
    st.plotly_chart(_gauge(put_bp, "Put BP%"), use_container_width=True, key="g2")
with g3:
    st.plotly_chart(_gauge(combo, "Combined BP%"), use_container_width=True, key="g3")

if not is_market_hours():
    st.caption("⚠️ Buying pressure requires RTH data for accuracy.")

# Key levels summary + metrics
st.markdown("---")
lc1, lc2, lc3, lc4 = st.columns(4)
with lc1:
    st.metric("Call Wall", f"{levels.get('call_wall', '—'):,}" if levels.get('call_wall') else "—")
    st.metric("COI", f"{levels.get('coi', '—'):,}" if levels.get('coi') else "—")
with lc2:
    st.metric("Put Wall", f"{levels.get('put_wall', '—'):,}" if levels.get('put_wall') else "—")
    st.metric("POI", f"{levels.get('poi', '—'):,}" if levels.get('poi') else "—")
with lc3:
    st.metric("+GEX", f"{levels.get('pgex', '—'):,}" if levels.get('pgex') else "—")
    st.metric("−GEX", f"{levels.get('ngex', '—'):,}" if levels.get('ngex') else "—")
with lc4:
    st.metric("+Trans", f"{levels.get('ptrans', '—'):,}" if levels.get('ptrans') else "—")
    st.metric("−Trans", f"{levels.get('ntrans', '—'):,}" if levels.get('ntrans') else "—")

st.markdown("---")
m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1: st.metric("PCR (Vol)", f"{levels.get('pcr_volume',0):.3f}")
with m2: st.metric("PCR (OI)", f"{levels.get('pcr_oi',0):.3f}")
with m3: st.metric("Call Vol", f"{levels.get('total_call_volume',0):,}")
with m4: st.metric("Put Vol", f"{levels.get('total_put_volume',0):,}")
with m5: st.metric("Call OI", f"{levels.get('total_call_oi',0):,}")
with m6: st.metric("Put OI", f"{levels.get('total_put_oi',0):,}")

# Prev close
pc = quote.get("previousClose", 0)
hi = quote.get("highPrice", 0)
lo = quote.get("lowPrice", 0)
op = quote.get("openPrice", 0)
st.markdown("---")
p1, p2, p3, p4 = st.columns(4)
with p1: st.metric("Open", f"{op:,.2f}" if op > 0 else "—")
with p2: st.metric("High", f"{hi:,.2f}" if hi > 0 else "—")
with p3: st.metric("Low", f"{lo:,.2f}" if lo > 0 else "—")
with p4: st.metric("Prev Close", f"{pc:,.2f}" if pc > 0 else "—")

# Footer
st.markdown("---")
st.caption(f"SPX Gamma Dashboard — {get_ny_time()}")
