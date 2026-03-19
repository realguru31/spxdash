"""
app.py — SPX Gamma Exposure Dashboard
Replicates SPX_Gamma_Dashboard_v1_3b.xlsm with Barchart data.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging

from data_fetcher import get_spx_quote, get_options_chain, get_active_source, get_expirations
from calculations import compute_chain_metrics, compute_dashboard_levels, filter_chain_for_display
from utils import check_password, get_ny_time, get_ny_datetime, is_market_hours, get_upcoming_expirations

st.set_page_config(
    page_title="SPX Gamma Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSS — hide Streamlit banner/footer
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
    [data-testid="stToolbar"] {display: none;}
    .block-container { padding-top: 1rem; }
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
# Sidebar — 0DTE / Tomorrow / Friday / OPEX + actual available expiries
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚡ SPX Gamma")

    # Get actual Barchart expiry dates
    available_expiries = get_expirations()

    # Build preset labels (0DTE, Tomorrow, Friday, OPEX)
    exp_presets = get_upcoming_expirations()
    exp_labels = list(exp_presets.keys())
    selected_label = st.selectbox("Expiration", exp_labels, index=0)
    target_date = exp_presets[selected_label]
    target_str = target_date.strftime("%Y-%m-%d")

    # If target date not in available expiries, find nearest available
    exp_str = target_str
    if available_expiries and target_str not in available_expiries:
        # Find nearest future date
        nearest = None
        for d in available_expiries:
            if d >= target_str:
                nearest = d
                break
        if nearest:
            exp_str = nearest
            st.caption(f"📅 {target_str} not available → using {exp_str}")
        else:
            st.caption(f"📅 {target_str} (may not have data)")
    else:
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
    et_now = get_ny_datetime()
    st.markdown(f"**{'🟢 MARKET OPEN' if is_market_hours() else '🔴 MARKET CLOSED'}**")
    st.markdown(f"**ET:** {et_now.strftime('%H:%M:%S')}")

    # Available expiries diagnostic
    with st.expander("📅 Available Expiries", expanded=False):
        if available_expiries:
            for d in available_expiries[:15]:
                marker = " ✅" if d == exp_str else ""
                st.text(f"  {d}{marker}")
            if len(available_expiries) > 15:
                st.text(f"  … +{len(available_expiries) - 15} more")
        else:
            st.text("  None found")

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
        return quote, pd.DataFrame(), {}, pd.DataFrame()

    chain = compute_chain_metrics(chain, spot)
    levels = compute_dashboard_levels(chain, spot)
    display = filter_chain_for_display(chain, spot, _n_above, _n_below)

    return quote, chain, levels, display


ts = int(datetime.now().timestamp() // 55)

with st.spinner("Fetching…"):
    quote, full_chain, levels, display_chain = load_data(
        exp_str, num_strikes_above, num_strikes_below, ts
    )

spot = quote.get("lastPrice", 0)

if display_chain.empty:
    st.error("❌ Could not fetch options chain.")
    st.markdown("""
**Troubleshooting:**
1. **Market closed / weekend?** — 0DTE chain is empty after hours. Select Tomorrow.
2. **Rate-limited?** — Wait 60s and click Refresh.
3. **Check logs** — Manage app → Logs.
    """)
    with st.expander("🔍 Debug Info"):
        st.json({
            "expiration_requested": exp_str,
            "target_date": target_str,
            "spot_price": spot,
            "quote": quote,
            "available_expiries": available_expiries[:10] if available_expiries else [],
        })
    st.stop()

# ---------------------------------------------------------------------------
# 1. HEADER
# ---------------------------------------------------------------------------
try:
    exp_dt = datetime.strptime(exp_str, "%Y-%m-%d").date()
    import pytz
    today_date = datetime.now(pytz.timezone("US/Eastern")).date()
    dte = (exp_dt - today_date).days
    dte_label = "0DTE" if dte == 0 else f"{dte}DTE"
except Exception:
    dte_label = selected_label

st.markdown(f"""
<div class="status-bar">
    <span class="status-text">SPX Gamma Dashboard — {selected_label} · {dte_label} ({exp_str})</span>
    <span class="status-text">Last update: {get_ny_time()}</span>
</div>
""", unsafe_allow_html=True)

pct_chg = quote.get("percentChange", 0)
net_chg = quote.get("netChange", 0)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    delta_str = f"{net_chg:+.2f} ({pct_chg:+.2f}%)" if net_chg != 0 else f"({pct_chg:+.2f}%)"
    st.metric("SPX", f"{spot:,.2f}", delta_str, delta_color="normal" if pct_chg >= 0 else "inverse")
with col2:
    st.metric("ATM Strike", f"{levels.get('centered_spot', 0):,}")
with col3:
    st.metric("Open", f"{quote.get('openPrice', 0):,.2f}")
with col4:
    hi = quote.get("highPrice", 0)
    lo = quote.get("lowPrice", 0)
    st.metric("High / Low", f"{hi:,.2f} / {lo:,.2f}")
with col5:
    pc = quote.get("previousClose", 0)
    st.metric("Prev Close", f"{pc:,.2f}" if pc > 0 else "—")

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
# 3. BUYING PRESSURE GAUGES
# ---------------------------------------------------------------------------
st.markdown("---")

def create_bp_gauge(value, title):
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
            "borderwidth": 1, "bordercolor": "#333",
            "steps": [
                {"range": [0, 10], "color": "rgba(255,23,68,0.5)"},
                {"range": [10, 25], "color": "rgba(150,150,150,0.3)"},
                {"range": [25, 75], "color": "rgba(0,200,83,0.35)"},
                {"range": [75, 90], "color": "rgba(150,150,150,0.3)"},
                {"range": [90, 100], "color": "rgba(255,23,68,0.5)"},
            ],
            "threshold": {
                "line": {"color": "#ffd600", "width": 3},
                "thickness": 0.8, "value": value,
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font={"color": "#e0e0e0"}, height=220,
        margin=dict(t=40, b=10, l=30, r=30),
    )
    return fig

gcol1, gcol2, gcol3 = st.columns(3)
call_bp = levels.get("avg_bp_call", 50)
put_bp = levels.get("avg_bp_put", 50)
combo = (call_bp + put_bp) / 2 if (call_bp + put_bp) > 0 else 50

with gcol1:
    st.plotly_chart(create_bp_gauge(call_bp, "Call BP% (ATM)"), use_container_width=True)
with gcol2:
    st.plotly_chart(create_bp_gauge(put_bp, "Put BP% (ATM)"), use_container_width=True)
with gcol3:
    st.plotly_chart(create_bp_gauge(combo, "Combined BP%"), use_container_width=True)

if not is_market_hours():
    st.caption("⚠️ Buying pressure gauges require RTH data for accurate readings.")

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
              annotation_text=f"Spot {spot:.0f}", row=1, col=1)

fig.add_trace(go.Bar(
    x=chart_df["strike"], y=chart_df["raw_pos"],
    marker_color="rgba(0,200,83,0.6)", name="+GEX",
), row=1, col=2)
fig.add_trace(go.Bar(
    x=chart_df["strike"], y=chart_df["raw_neg"],
    marker_color="rgba(255,23,68,0.6)", name="−GEX",
), row=1, col=2)
fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5, row=1, col=2)

fig.update_layout(
    height=420, template="plotly_dark",
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
    showlegend=False, margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11),
)
fig.update_xaxes(title_text="Strike", row=1, col=1)
fig.update_xaxes(title_text="Strike", row=1, col=2)
fig.update_yaxes(title_text="Net GEX (contracts)", row=1, col=1)
fig.update_yaxes(title_text="GEX ($B notional)", row=1, col=2)

st.plotly_chart(fig, use_container_width=True)

with st.expander("📈 Open Interest Profile", expanded=False):
    oi_fig = go.Figure()
    oi_fig.add_trace(go.Bar(x=chart_df["strike"], y=chart_df["c_oi"],
                            name="Call OI", marker_color="rgba(0,200,83,0.5)"))
    oi_fig.add_trace(go.Bar(x=chart_df["strike"], y=chart_df["p_oi"],
                            name="Put OI", marker_color="rgba(255,23,68,0.5)"))
    oi_fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5)
    oi_fig.update_layout(title="Open Interest by Strike", barmode="group", height=350,
                         template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                         margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11))
    st.plotly_chart(oi_fig, use_container_width=True)

with st.expander("📊 Delta-Adjusted GEX Profile", expanded=False):
    dadj_fig = go.Figure()
    dadj_fig.add_trace(go.Bar(x=chart_df["strike"], y=chart_df["dadj_pos"],
                              name="+DAdj", marker_color="rgba(0,200,83,0.6)"))
    dadj_fig.add_trace(go.Bar(x=chart_df["strike"], y=chart_df["dadj_neg"],
                              name="−DAdj", marker_color="rgba(255,23,68,0.6)"))
    dadj_fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5)
    dadj_fig.update_layout(title="Delta-Adjusted GEX (S² × Delta)", barmode="relative", height=380,
                           template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11))
    st.plotly_chart(dadj_fig, use_container_width=True)

with st.expander("📊 Volume Profile", expanded=False):
    vol_fig = go.Figure()
    vol_fig.add_trace(go.Bar(x=chart_df["strike"], y=chart_df["c_volume"],
                             name="Call Vol", marker_color="rgba(0,200,83,0.5)"))
    vol_fig.add_trace(go.Bar(x=chart_df["strike"], y=chart_df["p_volume"],
                             name="Put Vol", marker_color="rgba(255,23,68,0.5)"))
    vol_fig.add_vline(x=spot, line_dash="dash", line_color="#ffd600", line_width=1.5)
    vol_fig.update_layout(title="Volume by Strike", barmode="group", height=350,
                          template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                          margin=dict(t=40, b=40, l=50, r=20), font=dict(size=11))
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
    "c_delta": "C Δ", "c_gamma": "C Γ", "c_iv": "C IV", "bp_call": "C BP%",
    "p_mark": "P Mark", "p_bid": "P Bid", "p_ask": "P Ask",
    "p_volume": "P Vol", "p_oi": "P OI", "p_voi": "P V/OI",
    "p_delta": "P Δ", "p_gamma": "P Γ", "p_iv": "P IV", "bp_put": "P BP%",
    "net_gex": "Net GEX", "net_dex": "Net DEX",
    "call_gex": "C GEX", "put_gex": "P GEX",
    "total_oi": "Total OI", "net_oi": "Net OI", "pct_from_spot": "% Spot",
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
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(f"SPX Gamma Dashboard — Last refresh: {get_ny_time()}")
