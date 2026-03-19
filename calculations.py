"""
calculations.py — Replicates all Option Chain + Dashboard calculations
from the original SPX_Gamma_Dashboard_v1_3b.xlsm workbook.

Excel formula mapping:
  AI = Call GEX  = ROUND(Call_OI * Call_Gamma * 100, 0)
  AJ = Put GEX   = -ROUND(Put_Gamma * Put_OI * 100, 0)
  AK = Tot GEX   = Call_GEX + Put_GEX
  AL = Call DEX  = ROUND(Call_Delta * Call_OI * 100, 0)
  AM = Put DEX   = ROUND(Put_Delta * Put_OI * 100, 0)
  AN = Tot DEX   = Call_DEX + Put_DEX
  AE = AbsDelta  = Call_Delta + |Put_Delta|
  AO = B%Call    = buying pressure from OHLC
  AP = B%Put     = buying pressure from OHLC
  AT-BA = GEX profile (S²-normalized, delta-adjusted)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any


def compute_chain_metrics(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    """
    Given a merged call/put chain DataFrame, compute all derived columns
    matching the Excel Option Chain sheet formulas.
    """
    if df.empty:
        return df

    out = df.copy()

    # ---------- V/OI (cols O, S in Excel) ----------
    out["c_voi"] = np.where(out["c_oi"] > 0, out["c_volume"] / out["c_oi"], 0.0)
    out["p_voi"] = np.where(out["p_oi"] > 0, out["p_volume"] / out["p_oi"], 0.0)

    # ---------- AbsDelta (col AE) ----------
    out["abs_delta"] = out["c_delta"].abs() + out["p_delta"].abs()

    # ---------- AbsDelta bands (AF, AG, AH) ----------
    out["ad_tight"]  = np.where(out["abs_delta"] < 1.1, out["abs_delta"], np.nan)
    out["ad_mid"]    = np.where((out["abs_delta"] >= 1.1) & (out["abs_delta"] < 1.2), out["abs_delta"], np.nan)
    out["ad_wide"]   = np.where(out["abs_delta"] >= 1.2, out["abs_delta"], np.nan)

    # ---------- GEX (AI, AJ, AK) ----------
    # Call GEX: OI * Gamma * 100 (positive for calls — dealers long gamma)
    out["call_gex"] = np.round(out["c_oi"] * out["c_gamma"] * 100, 0).astype(int)
    # Put GEX: -OI * Gamma * 100 (negative — dealers short gamma on puts)
    out["put_gex"]  = -np.round(out["p_gamma"] * out["p_oi"] * 100, 0).astype(int)
    out["net_gex"]  = out["call_gex"] + out["put_gex"]

    # ---------- DEX (AL, AM, AN) ----------
    out["call_dex"] = np.round(out["c_delta"] * out["c_oi"] * 100, 0).astype(int)
    out["put_dex"]  = np.round(out["p_delta"] * out["p_oi"] * 100, 0).astype(int)
    out["net_dex"]  = out["call_dex"] + out["put_dex"]

    # ---------- Buying pressure % (AO, AP) ----------
    out["bp_call"] = _buying_pressure(out["c_high"], out["c_low"], out["c_open"], out["c_mark"], out["c_volume"])
    out["bp_put"]  = _buying_pressure(out["p_high"], out["p_low"], out["p_open"], out["p_mark"], out["p_volume"])

    # ---------- % from spot (Dashboard col M) ----------
    out["pct_from_spot"] = (out["strike"] / spot - 1) if spot > 0 else 0.0

    # ---------- Total OI / Net OI (Dashboard I, J) ----------
    out["total_oi"] = out["c_oi"] + out["p_oi"]
    out["net_oi"]   = out["c_oi"] - out["p_oi"]

    # ---------- GEX profile columns (AT-BA) — S²-normalized ----------
    s2_norm = spot * spot / 1e9 if spot > 0 else 1.0
    out["raw_cgex"]    = out["c_gamma"] * s2_norm * out["c_oi"]
    out["raw_pgex"]    = -out["p_gamma"] * s2_norm * out["p_oi"]
    out["raw_pos"]     = np.where((out["raw_cgex"] + out["raw_pgex"]) > 0,
                                   out["raw_cgex"] + out["raw_pgex"], 0)
    out["raw_neg"]     = np.where((out["raw_cgex"] + out["raw_pgex"]) < 0,
                                   out["raw_cgex"] + out["raw_pgex"], 0)
    # Delta-adjusted GEX
    out["dadj_cgex"]   = out["raw_cgex"] * out["c_delta"]
    out["dadj_pgex"]   = out["raw_pgex"] * out["p_delta"]
    out["dadj_pos"]    = np.where((out["dadj_cgex"] + out["dadj_pgex"]) > 0,
                                   out["dadj_cgex"] + out["dadj_pgex"], 0)
    out["dadj_neg"]    = np.where((out["dadj_cgex"] + out["dadj_pgex"]) < 0,
                                   out["dadj_cgex"] + out["dadj_pgex"], 0)

    return out


def compute_dashboard_levels(df: pd.DataFrame, spot: float) -> Dict[str, Any]:
    """
    Compute the Dashboard 'Levels of Interest' replicating the N18-N25 / O18-O25 block.
    Returns a dict with strike levels and metadata.
    """
    if df.empty or spot <= 0:
        return _empty_levels()

    levels = {}

    # Call Wall = strike with max Call OI
    if df["c_oi"].max() > 0:
        levels["call_wall"] = int(df.loc[df["c_oi"].idxmax(), "strike"])
    else:
        levels["call_wall"] = None

    # Put Wall = strike with max Put OI
    if df["p_oi"].max() > 0:
        levels["put_wall"] = int(df.loc[df["p_oi"].idxmax(), "strike"])
    else:
        levels["put_wall"] = None

    # COI = strike with max Call OI (same as call wall in this sheet)
    levels["coi"] = levels["call_wall"]

    # POI = strike with max Put OI (same as put wall)
    levels["poi"] = levels["put_wall"]

    # pGEX = strike with max positive net GEX
    pos_gex = df[df["net_gex"] > 0]
    if not pos_gex.empty:
        levels["pgex"] = int(pos_gex.loc[pos_gex["net_gex"].idxmax(), "strike"])
    else:
        levels["pgex"] = None

    # nGEX = strike with min (most negative) net GEX
    neg_gex = df[df["net_gex"] < 0]
    if not neg_gex.empty:
        levels["ngex"] = int(neg_gex.loc[neg_gex["net_gex"].idxmin(), "strike"])
    else:
        levels["ngex"] = None

    # Gamma flip / transition zone (pTrans, nTrans)
    # pTrans/nTrans: find where net_gex crosses zero
    sorted_df = df.sort_values("strike").reset_index(drop=True)
    gex_vals = sorted_df["net_gex"].values
    strikes = sorted_df["strike"].values
    crossings = []
    for i in range(len(gex_vals) - 1):
        if gex_vals[i] * gex_vals[i + 1] < 0:
            # Linear interpolation of zero crossing
            w = abs(gex_vals[i]) / (abs(gex_vals[i]) + abs(gex_vals[i + 1]))
            cross_strike = strikes[i] + w * (strikes[i + 1] - strikes[i])
            crossings.append(round(cross_strike / 5) * 5)

    above_spot = [c for c in crossings if c >= spot]
    below_spot = [c for c in crossings if c < spot]
    levels["ptrans"] = min(above_spot) if above_spot else None   # positive transition (above)
    levels["ntrans"] = max(below_spot) if below_spot else None   # negative transition (below)

    # Gamma dominance (from GEX ratio — sum of call GEX / abs(sum of put GEX))
    total_call_gex = df["call_gex"].sum()
    total_put_gex = abs(df["put_gex"].sum())
    if total_put_gex > 0:
        gex_ratio = total_call_gex / total_put_gex
    else:
        gex_ratio = 999.0
    levels["gex_ratio"] = round(gex_ratio, 2)
    levels["gamma_dominant"] = "CALL" if gex_ratio >= 1 else "PUT"

    # Centered spot (ATM rounded to 5)
    levels["centered_spot"] = int(round(spot / 5) * 5)
    levels["spot"] = round(spot, 2)

    # Aggregate metrics
    levels["total_call_volume"] = int(df["c_volume"].sum())
    levels["total_put_volume"]  = int(df["p_volume"].sum())
    levels["total_call_oi"]     = int(df["c_oi"].sum())
    levels["total_put_oi"]      = int(df["p_oi"].sum())
    levels["pcr_volume"]        = round(df["p_volume"].sum() / max(df["c_volume"].sum(), 1), 3)
    levels["pcr_oi"]            = round(df["p_oi"].sum() / max(df["c_oi"].sum(), 1), 3)
    levels["total_net_gex"]     = int(df["net_gex"].sum())
    levels["total_net_dex"]     = int(df["net_dex"].sum())

    # ATM-area avg buying pressure (matching AO51/AP51)
    atm = levels["centered_spot"]
    near_atm = df[(df["strike"] >= atm - 25) & (df["strike"] <= atm + 25)]
    levels["avg_bp_call"] = round(near_atm["bp_call"].mean(), 1) if not near_atm.empty else 0
    levels["avg_bp_put"]  = round(near_atm["bp_put"].mean(), 1) if not near_atm.empty else 0

    return levels


def filter_chain_for_display(df: pd.DataFrame, spot: float,
                              num_above: int = 20, num_below: int = 20) -> pd.DataFrame:
    """Filter chain to strikes around ATM for dashboard display."""
    if df.empty or spot <= 0:
        return df
    atm = round(spot / 5) * 5
    low = atm - num_below * 5
    high = atm + num_above * 5
    mask = (df["strike"] >= low) & (df["strike"] <= high)
    return df[mask].sort_values("strike", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _buying_pressure(high, low, opn, mark, volume) -> pd.Series:
    """
    Replicate Excel OHLC-based buying pressure:
    =ROUND((ROUND(((HIGH - OPEN + (MARK - LOW)) / 2 / (HIGH - LOW)) * VOLUME, 0)) / VOLUME * 100, 0)
    Simplifies to: ((HIGH - OPEN + MARK - LOW) / 2 / (HIGH - LOW)) * 100
    """
    hl_range = high - low
    numerator = (high - opn + mark - low) / 2
    bp = np.where(hl_range > 0, numerator / hl_range * 100, 50)
    return pd.Series(np.round(bp, 0).astype(int), index=high.index)


def _empty_levels() -> Dict[str, Any]:
    return {
        "call_wall": None, "put_wall": None, "coi": None, "poi": None,
        "pgex": None, "ngex": None, "ptrans": None, "ntrans": None,
        "gex_ratio": 0, "gamma_dominant": "N/A",
        "centered_spot": 0, "spot": 0,
        "total_call_volume": 0, "total_put_volume": 0,
        "total_call_oi": 0, "total_put_oi": 0,
        "pcr_volume": 0, "pcr_oi": 0,
        "total_net_gex": 0, "total_net_dex": 0,
        "avg_bp_call": 0, "avg_bp_put": 0,
    }
