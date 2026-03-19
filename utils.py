"""
utils.py — Authentication, formatting, and helper utilities.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz


def check_password() -> bool:
    """
    Password gate using st.secrets (server-side).
    secrets.toml must contain: APP_PASSWORD = "your_password"
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    try:
        correct_pw = st.secrets["APP_PASSWORD"]
    except (KeyError, FileNotFoundError):
        st.error("⚠️ APP_PASSWORD not found in secrets.toml. See README for setup.")
        st.stop()
        return False

    with st.container():
        st.markdown("### 🔐 SPX Gamma Dashboard")
        pw = st.text_input("Password", type="password", key="pw_input")
        if st.button("Login", type="primary"):
            if pw == correct_pw:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


def get_ny_time() -> str:
    """Return current NY time string."""
    ny = pytz.timezone("America/New_York")
    return datetime.now(ny).strftime("%I:%M %p ET")


def get_ny_datetime() -> datetime:
    ny = pytz.timezone("America/New_York")
    return datetime.now(ny)


def is_market_hours() -> bool:
    """Check if within RTH (9:30-16:00 ET, weekdays)."""
    now = get_ny_datetime()
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


def get_upcoming_expirations() -> list:
    """Generate upcoming expiration date strings (today, tomorrow, Friday, OPEX)."""
    ny = pytz.timezone("America/New_York")
    today = datetime.now(ny).date()
    exps = {"0DTE": today}

    # Tomorrow
    tomorrow = today + timedelta(days=1)
    if tomorrow.weekday() >= 5:
        tomorrow = today + timedelta(days=(7 - today.weekday()))
    exps["Tomorrow"] = tomorrow

    # This Friday
    days_to_fri = (4 - today.weekday()) % 7
    if days_to_fri == 0 and today.weekday() == 4:
        friday = today
    else:
        friday = today + timedelta(days=days_to_fri)
    exps["Friday"] = friday

    # OPEX (3rd Friday of current month)
    first_day = today.replace(day=1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
    opex = first_friday + timedelta(weeks=2)
    if opex < today:
        # Move to next month
        if today.month == 12:
            first_day = today.replace(year=today.year + 1, month=1, day=1)
        else:
            first_day = today.replace(month=today.month + 1, day=1)
        first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
        opex = first_friday + timedelta(weeks=2)
    exps["OPEX"] = opex

    return exps


def format_number(val, fmt="int"):
    """Format numbers for display."""
    if pd.isna(val) or val is None:
        return "—"
    if fmt == "int":
        return f"{int(val):,}"
    elif fmt == "pct":
        return f"{val:.1%}"
    elif fmt == "float2":
        return f"{val:.2f}"
    elif fmt == "float4":
        return f"{val:.4f}"
    return str(val)


def color_gex(val):
    """Conditional formatting for GEX values (green positive, red negative)."""
    if isinstance(val, (int, float)):
        if val > 0:
            return "color: #00c853"
        elif val < 0:
            return "color: #ff1744"
    return ""


def color_pct(val):
    """Color percentage values."""
    if isinstance(val, (int, float)):
        if val > 0:
            return "color: #00c853"
        elif val < 0:
            return "color: #ff1744"
    return ""


def style_dashboard_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Apply conditional formatting to the dashboard DataFrame."""
    gex_cols = [c for c in df.columns if "gex" in c.lower() or "dex" in c.lower()]
    styled = df.style
    for col in gex_cols:
        if col in df.columns:
            styled = styled.map(color_gex, subset=[col])
    return styled
