"""
app.py — SPX Gamma Exposure Dashboard
Replicates SPX_Gamma_Dashboard_v1_3b.xlsm with Barchart data.

Sections:
  1. SPX Price Summary
  2. Key Levels (Call Wall, Put Wall, COI, GEX levels, transitions)
  3. Buying Pressure Gauges (from Excel AQ/AR — Call/Put needle gauges)
  4. Aggregated Metrics (PCR, totals, gamma dominance)
  5. GEX Profile Charts
  6. Options Chain Table
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging

from data_fetcher import get_spx_quote, get_options_chain, get_active_source
from calculations import compute_chain_metrics, compute_dashboard_levels, filter_chain_for_display
from utils import check_password, get_ny_time, get_ny_datetime, is_market_hours, get_upcoming_expirations

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SPX Gamma Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stMetric { background: #0e1117; border: 1px solid #262730; border-radius: 8px; padding: 12px; }
    .level-card { background: #1a1a2e; border-radius: 8px; padding: 10px 14px; margin: 4px 0;
                  border-left: 4px solid; }
    .level-call { border-left-color: #00c853; }
    .level-put  { border-left-color: #ff1744; }
    .level-gex  { border-left-color: #2196f3; }
    .level-trans { border-left-color: #ff9800; }
    .level-label { font-size: 0.8em; color: #888; margin-bottom: 2px; }
    .level-value { font-size: 1.3em; font-weight: 700; color: #e0e0e0; }
    .gamma-banner { text-align: center; padding: 8px; border-radius: 6px; font-weight: 700;
                    font-size: 1.1em; margin: 8px 0; }
    .gamma-call { background: rgba(0,200,83,0.15); color: #00c853; border: 1px solid #00c853; }
    .gamma-put  { background: rgba(255,23,68,0.15); color: #ff1744; border: 1px solid #ff1744; }
    div[data-testid="stDataFrame"] { font-size: 0.85em; }
    .status-bar { display: flex; justify-content: space-between; align-items: center;
                  padding: 6px 12px; background: #16213e; border-radius: 6px; margin-bottom: 12px; }
    .status-text { font-size: 0.85em; color: #a0a0a0; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Auth gate
# ---------------------------------------------------------------------------
if not check_password():
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Controls")

    exp_presets = get_upcoming_expirations()
    exp_labels = list(exp_presets.keys())
    selected_label = st.selectbox("Expiration", exp_labels, index=0)
    selected_date = exp_presets[selected_label]
    exp_str = selected_date.strftime("%Y-%m-%d")
    st.caption(f"📅 {exp_str}")

    st.divider()

    num_strikes_above = st.slider("Strikes above ATM", 5, 40, 20, 5)
    num_strikes_below = st.slider("Strikes below ATM", 5, 40, 20, 5)

    st.divider()

    show_calls = st.checkbox("Show Calls", value=True)
    show_puts = st.checkbox("Show Puts", value=True)
    show_greeks = st.checkbox("Show Greeks", value=True)
    show_buying_pressure = st.checkbox("Show Buying Pressure", value=True)

    st.divider()

    auto_refresh = st.checkbox("Auto-refresh (60s)", value=True)
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"🕐 {get_ny_time()}")
    st.caption("Market " + ("🟢 OPEN" if is_market_hours() else "🔴 CLOSED"))

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
if auto_refresh:
    @st.fragment(run_every=60)
    def _auto_refresh_trigger():
        pass
    _auto_refresh_trigger()

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=55, show_spinner=False)
def load_data(exp_date: str, _n_above: int = 20, _n_below: int = 20, _ts: int = 0):
    quote = get_spx_quote()
    spot = quote.get("lastPrice", 0)

    chain = get_options_chain(exp_date)
    if chain is None or chain.empty:
        return quote, pd.DataFrame(), {}, pd.DataFrame(), get_active_source()

    chain = compute_chain_metrics(chain, spot)
    levels = compute_dashboard_levels(chain, spot)
    display = filter_chain_for_display(chain, spot, _n_above, _n_below)

    return quote, chain, levels, display, get_active_source()


ts = int(datetime.now().timestamp() // 55)

with st.spinner("Fetching SPX options data…"):
    quote, full_chain, levels, display_chain, data_source = load_data(
        exp_str, num_strikes_above, num_strikes_below, ts
    )

spot = quote.get("lastPrice", 0)

if display_chain.empty:
    st.error("❌ Could not fetch options chain.")
    st.markdown("""
**Troubleshooting:**
1. **Market closed / weekend?** — 0DTE doesn't exist outside market hours. Try "Tomorrow" or "Friday".
2. **Barchart rate-limited?** — Wait 60s and click Refresh.
3. **Check logs** — Manage app → Logs for detailed errors.
    """)
    with st.expander("🔍 Debug Info"):
        st.json({
            "expiration_requested": exp_str,
            "spot_price": spot,
            "data_source": data_source,
            "quote": quote,
            "timestamp": datetime.now().isoformat(),
        })
    st.stop()

source_label = "🟢 Barchart" if data_source == "barchart" else "⚪ Unknown"

# ---------------------------------------------------------------------------
# 1. SPX PRICE SUMMARY
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="status-bar">
    <span class="status-text">SPX Gamma Dashboard — {selected_label} ({exp_str})</span>
    <span class="status-text">{source_label} &nbsp;•&nbsp; Last update: {get_ny_time()}</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    chg = quote.get("netChange", 0)
    st.metric("SPX", f"{spot:,.2f}", f"{chg:+.2f} ({quote.get('percentChange', 0):+.2f}%)")
with col2:
    st.metric("ATM Strike", f"{levels.get('centered_spot', 0):,}")
with col3:
    st.metric("Open", f"{quote.get('openPrice', 0):,.2f}")
with col4:
    st.metric("High", f"{quote.get('highPrice', 0):,.2f}")
with col5:
    st.metric("Low", f"{quote.get('lowPrice', 0):,.2f}")
with col6:
    st.metric("Prev Close", f"{quote.get('previousClose', 0):,.2f}")

# ---------------------------------------------------------------------------
# 2. KEY LEVELS + GAMMA REGIME
# ---------------------------------------------------------------------------
st.markdown("---")

dom = levels.get("gamma_dominant", "N/A")
cls = "gamma-call" if dom == "CALL" else "gamma-put"
st.markdown(f"""
<div class="gamma-banner {cls}">
    Gamma is {dom} dominant &nbsp;•&nbsp; GEX Ratio: {levels.get('gex_ratio', 0):.2f}
    &nbsp;•&nbsp; Net GEX: {levels.get('total_net_gex', 0):,}
</div>
""", unsafe_allow_html=True)

lcol1, lcol2, lcol3, lcol4 = st.columns(4)

def _level_card(label, value, css_class):
    val_str = f"{value:,}" if value else "—"
    return f"""<div class="level-card {css_class}">
        <div class="level-label">{label}</div>
        <div class="level-value">{val_str}</div>
    </div>"""

with lcol1:
    st.markdown(_level_card("🟢 Call Wall", levels.get("call_wall"), "level-call"), unsafe_allow_html=True)
    st.markdown(_level_card("📊 COI (Max Call OI)", levels.get("coi"), "level-call"), unsafe_allow_html=True)
with lcol2:
    st.markdown(_level_card("🔴 Put Wall", levels.get("put_wall"), "level-put"), unsafe_allow_html=True)
    st.markdown(_level_card("📊 POI (Max Put OI)", levels.get("poi"), "level-put"), unsafe_allow_html=True)
with lcol3:
    st.markdown(_level_card("⬆️ +GEX (Max Positive)", levels.get("pgex"), "level-gex"), unsafe_allow_html=True)
    st.markdown(_level_card("⬇️ −GEX (Max Negative)", levels.get("ngex"), "level-gex"), unsafe_allow_html=True)
with lcol4:
    st.markdown(_level_card("🔶 +Transition (Above)", levels.get("ptrans"), "level-trans"), unsafe_allow_html=True)
    st.markdown(_level_card("🔶 −Transition (Below)", levels.get("ntrans"), "level-trans"), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 3. BUYING PRESSURE GAUGES (Excel AQ/AR — Call/Put Needle)
# ---------------------------------------------------------------------------
# Excel gauge bands: Red(0-10), Gray(10-25), Green(25-75), Gray(75-90), Red(90-100)
# Needle = avg buying pressure % near ATM (AO51, AP51)
st.markdown("---")

def create_bp_gauge(value, title):
    """
    Replicate Excel buying pressure gauge.
    Bands: Red(0-10) Gray(10-25) Green(25-75) Gray(75-90) Red(90-100)
    0% = all selling, 100% = all buying, 50% = neutral
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 28, "color": "#e0e0e0"}},
        title={"text": title, "font": {"size": 14, "color": "#a0a0a0"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#555",
                     "dtick": 10, "tickfont": {"size": 9, "color": "#777"}},
            "bar": {"color": "#ffd600", "thickness": 0.25},
            "bgcolor": "#0e1117",
            "borderwidth": 1,
            "bordercolor": "#333",
            "steps": [
                {"range": [0, 10], "color": "rgba(255,23,68,0.5)"},      # Red — heavy selling
                {"range": [10, 25], "color": "rgba(150,150,150,0.3)"},    # Gray
                {"range": [25, 75], "color": "rgba(0,200,83,0.35)"},      # Green — balanced
                {"range": [75, 90], "color": "rgba(150,150,150,0.3)"},    # Gray
                {"range": [90, 100], "color": "rgba(255,23,68,0.5)"},     # Red — heavy buying
            ],
            "threshold": {
                "line": {"color": "#ffd600", "width": 3},
                "thickness": 0.8,
                "value": value,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font={"color": "#e0e0e0"},
        height=220,
        margin=dict(t=40, b=10, l=30, r=30),
    )
    return fig


gcol1, gcol2, gcol3 = st.columns([1, 1, 1])

with gcol1:
    call_bp = levels.get("avg_bp_call", 50)
    st.plotly_chart(create_bp_gauge(call_bp, "Call Buying Pressure (ATM)"),
                    use_container_width=True)

with gcol2:
    put_bp = levels.get("avg_bp_put", 50)
    st.plotly_chart(create_bp_gauge(put_bp, "Put Buying Pressure (ATM)"),
                    use_container_width=True)

with gcol3:
    # Combined gauge: average of call + put BP
    combo = (call_bp + put_bp) / 2 if (call_bp + put_bp) > 0 else 50
    st.plotly_chart(create_bp_gauge(combo, "Combined Buying Pressure"),
                    use_container_width=True)

# ---------------------------------------------------------------------------
# 4. AGGREGATE METRICS
# ---------------------------------------------------------------------------
st.markdown("---")
mcol1, mcol2, mcol3, mcol4, mcol5, mcol6 = st.columns(6)
with mcol1:
    st.metric("PCR (Volume)", f"{levels.get('pcr_volume', 0):.3f}")
with mcol2:
    st.metric("PCR (OI)", f"{levels.get('pcr_oi', 0):.3f}")
with mcol3:
    st.metric("Total Call Vol", f"{levels.get('total_call_volume', 0):,}")
with mcol4:
    st.metric("Total Put Vol", f"{levels.get('total_put_volume', 0):,}")
with mcol5:
    st.metric("Total Call OI", f"{levels.get('total_call_oi', 0):,}")
with mcol6:
    st.metric("Total Put OI", f"{levels.get('total_put_oi', 0):,}")

# ---------------------------------------------------------------------------
# 5. GEX PROFILE CHARTS
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 Gamma Exposure Profile")

chart_df = display_chain.sort_values("strike").copy()

fig = make_subplots(
    rows=1, cols=2,
    subplot_titles=("Net GEX by Strike", "GEX Profile (S²-Normalized)"),
    horizontal_spacing=0.08,
)

colors = ["#00c853" if v >= 0 else "#ff1744" for v in chart_df["net_gex"]]
fig.add_trace(go.Bar(
    x=chart_df["strike"], y=chart_df["net_gex"],
    marker_color=colors, name="Net GEX",
    hovertemplate="Strike: %{x}<br>Net GEX: %{y:,}<extra></extra>",
), row=1, col=1)

fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5,
              annotation_text=f"SPX {spot:.0f}", row=1, col=1)

fig.add_trace(go.Bar(
    x=chart_df["strike"], y=chart_df["raw_pos"],
    marker_color="rgba(0,200,83,0.6)", name="+GEX",
    hovertemplate="Strike: %{x}<br>+GEX: %{y:.4f}<extra></extra>",
), row=1, col=2)
fig.add_trace(go.Bar(
    x=chart_df["strike"], y=chart_df["raw_neg"],
    marker_color="rgba(255,23,68,0.6)", name="−GEX",
    hovertemplate="Strike: %{x}<br>−GEX: %{y:.4f}<extra></extra>",
), row=1, col=2)
fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5, row=1, col=2)

fig.update_layout(
    height=420,
    template="plotly_dark",
    paper_bgcolor="#0e1117",
    plot_bgcolor="#0e1117",
    showlegend=False,
    margin=dict(t=40, b=40, l=50, r=20),
    font=dict(size=11),
)
fig.update_xaxes(title_text="Strike", row=1, col=1)
fig.update_xaxes(title_text="Strike", row=1, col=2)
fig.update_yaxes(title_text="Net GEX (contracts)", row=1, col=1)
fig.update_yaxes(title_text="GEX ($B notional)", row=1, col=2)

st.plotly_chart(fig, use_container_width=True)

# OI Profile
with st.expander("📈 Open Interest Profile", expanded=False):
    oi_fig = go.Figure()
    oi_fig.add_trace(go.Bar(
        x=chart_df["strike"], y=chart_df["c_oi"],
        name="Call OI", marker_color="rgba(0,200,83,0.5)",
    ))
    oi_fig.add_trace(go.Bar(
        x=chart_df["strike"], y=chart_df["p_oi"],
        name="Put OI", marker_color="rgba(255,23,68,0.5)",
    ))
    oi_fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5,
                     annotation_text=f"SPX {spot:.0f}")
    oi_fig.update_layout(
        title="Open Interest by Strike",
        barmode="group", height=350,
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11),
    )
    st.plotly_chart(oi_fig, use_container_width=True)

# Delta-adjusted GEX
with st.expander("📊 Delta-Adjusted GEX Profile", expanded=False):
    dadj_fig = go.Figure()
    dadj_fig.add_trace(go.Bar(
        x=chart_df["strike"], y=chart_df["dadj_pos"],
        name="+DAdj GEX", marker_color="rgba(0,200,83,0.6)",
    ))
    dadj_fig.add_trace(go.Bar(
        x=chart_df["strike"], y=chart_df["dadj_neg"],
        name="−DAdj GEX", marker_color="rgba(255,23,68,0.6)",
    ))
    dadj_fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5,
                       annotation_text=f"SPX {spot:.0f}")
    dadj_fig.update_layout(
        title="Delta-Adjusted GEX by Strike (S²-Normalized × Delta)",
        barmode="relative", height=380,
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11),
    )
    st.plotly_chart(dadj_fig, use_container_width=True)

# Volume Profile
with st.expander("📊 Volume Profile", expanded=False):
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(
        x=chart_df["strike"], y=chart_df["c_volume"],
        name="Call Volume", marker_color="rgba(0,200,83,0.5)",
    ))
    vol_fig.add_trace(go.Bar(
        x=chart_df["strike"], y=chart_df["p_volume"],
        name="Put Volume", marker_color="rgba(255,23,68,0.5)",
    ))
    vol_fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5)
    vol_fig.update_layout(
        title="Volume by Strike",
        barmode="group", height=350,
        template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11),
    )
    st.plotly_chart(vol_fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 6. OPTIONS CHAIN TABLE
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 Options Chain")

display_cols = ["strike"]

if show_calls:
    display_cols += ["c_volume", "c_oi", "c_mark", "c_bid", "c_ask", "c_voi"]
    if show_greeks:
        display_cols += ["c_delta", "c_gamma", "c_iv"]
    if show_buying_pressure:
        display_cols += ["bp_call"]

if show_puts:
    display_cols += ["p_mark", "p_bid", "p_ask", "p_volume", "p_oi", "p_voi"]
    if show_greeks:
        display_cols += ["p_delta", "p_gamma", "p_iv"]
    if show_buying_pressure:
        display_cols += ["bp_put"]

display_cols += ["net_gex", "net_dex", "call_gex", "put_gex", "total_oi", "net_oi", "pct_from_spot"]

display_cols = [c for c in display_cols if c in display_chain.columns]
table_df = display_chain[display_cols].copy()

col_rename = {
    "strike": "Strike", "c_volume": "C Vol", "c_oi": "C OI", "c_mark": "C Mark",
    "c_bid": "C Bid", "c_ask": "C Ask", "c_voi": "C V/OI",
    "c_delta": "C Δ", "c_gamma": "C Γ", "c_iv": "C IV",
    "bp_call": "C BP%",
    "p_mark": "P Mark", "p_bid": "P Bid", "p_ask": "P Ask",
    "p_volume": "P Vol", "p_oi": "P OI", "p_voi": "P V/OI",
    "p_delta": "P Δ", "p_gamma": "P Γ", "p_iv": "P IV",
    "bp_put": "P BP%",
    "net_gex": "Net GEX", "net_dex": "Net DEX",
    "call_gex": "C GEX", "put_gex": "P GEX",
    "total_oi": "Total OI", "net_oi": "Net OI",
    "pct_from_spot": "% Spot",
}
table_df = table_df.rename(columns=col_rename)

fmt_map = {}
for col in table_df.columns:
    if col in ("Strike", "C Vol", "P Vol", "C OI", "P OI", "Net GEX", "Net DEX",
               "C GEX", "P GEX", "Total OI", "Net OI", "C BP%", "P BP%"):
        fmt_map[col] = "{:,.0f}"
    elif col in ("C Mark", "P Mark", "C Bid", "P Bid", "C Ask", "P Ask"):
        fmt_map[col] = "{:.2f}"
    elif col in ("C Δ", "P Δ"):
        fmt_map[col] = "{:.3f}"
    elif col in ("C Γ", "P Γ"):
        fmt_map[col] = "{:.5f}"
    elif col in ("C IV", "P IV"):
        fmt_map[col] = "{:.1%}"
    elif col in ("C V/OI", "P V/OI"):
        fmt_map[col] = "{:.2f}"
    elif col == "% Spot":
        fmt_map[col] = "{:.2%}"

atm_strike = levels.get("centered_spot", 0)

def highlight_atm(row):
    if row.get("Strike", 0) == atm_strike:
        return ["background-color: rgba(255,214,0,0.15)"] * len(row)
    return [""] * len(row)

def color_gex_cell(val):
    if isinstance(val, (int, float)) and not pd.isna(val):
        if val > 0:
            return "color: #00c853"
        elif val < 0:
            return "color: #ff1744"
    return ""

styled = (
    table_df.style
    .format(fmt_map, na_rep="—")
    .apply(highlight_atm, axis=1)
    .map(color_gex_cell, subset=[c for c in ["Net GEX", "Net DEX", "C GEX", "P GEX", "Net OI"] if c in table_df.columns])
)

st.dataframe(styled, use_container_width=True, height=600)

# ---------------------------------------------------------------------------
# 7. CSV EXPORT
# ---------------------------------------------------------------------------
st.markdown("---")
ecol1, ecol2 = st.columns(2)
with ecol1:
    csv = display_chain.to_csv(index=False)
    st.download_button("📥 Export Chain (CSV)", csv,
                       f"spx_gamma_{exp_str}.csv", "text/csv",
                       use_container_width=True)
with ecol2:
    levels_df = pd.DataFrame([levels])
    st.download_button("📥 Export Levels (CSV)", levels_df.to_csv(index=False),
                       f"spx_levels_{exp_str}.csv", "text/csv",
                       use_container_width=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    f"SPX Gamma Dashboard v2.0 — Barchart data — "
    f"Last refresh: {get_ny_time()} — "
    f"Replicates SPX_Gamma_Dashboard_v1_3b.xlsm logic"
)
