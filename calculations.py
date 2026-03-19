"""
calculations.py — Replicates ALL Excel formulas from SPX_Gamma_Dashboard_v1_3b.xlsm.

Excel formula mapping:
  AI = Call GEX  = ROUND(Call_OI * Call_Gamma * 100, 0)
  AJ = Put GEX   = -ROUND(Put_Gamma * Put_OI * 100, 0)
  AK = Tot GEX   = Call_GEX + Put_GEX
  AL = Call DEX  = ROUND(Call_Delta * Call_OI * 100, 0)
  AM = Put DEX   = ROUND(Put_Delta * Put_OI * 100, 0)
  AN = Tot DEX   = Call_DEX + Put_DEX
  AE = AbsDelta  = Call_Delta + |Put_Delta|
  AO = B%Call    = ((HIGH-OPEN+(MARK-LOW))/2/(HIGH-LOW))*100
  AP = B%Put     = same for puts
  AO51/AP51      = AVERAGE of BP% for 11 strikes below ATM (rows 23:33)
  AA/AB/AC       = Transition zone: sign-change within max-GEX to min-GEX region
  AT-BA          = S²-normalized GEX profile
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any


def compute_chain_metrics(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()

    # V/OI
    out["c_voi"] = np.where(out["c_oi"] > 0, out["c_volume"] / out["c_oi"], 0.0)
    out["p_voi"] = np.where(out["p_oi"] > 0, out["p_volume"] / out["p_oi"], 0.0)

    # AbsDelta
    out["abs_delta"] = out["c_delta"].abs() + out["p_delta"].abs()

    # GEX
    out["call_gex"] = np.round(out["c_oi"] * out["c_gamma"] * 100, 0).astype(int)
    out["put_gex"] = -np.round(out["p_gamma"] * out["p_oi"] * 100, 0).astype(int)
    out["net_gex"] = out["call_gex"] + out["put_gex"]

    # DEX
    out["call_dex"] = np.round(out["c_delta"] * out["c_oi"] * 100, 0).astype(int)
    out["put_dex"] = np.round(out["p_delta"] * out["p_oi"] * 100, 0).astype(int)
    out["net_dex"] = out["call_dex"] + out["put_dex"]

    # Buying pressure
    out["bp_call"] = _buying_pressure(out["c_high"], out["c_low"], out["c_open"], out["c_mark"], out["c_volume"])
    out["bp_put"] = _buying_pressure(out["p_high"], out["p_low"], out["p_open"], out["p_mark"], out["p_volume"])

    # % from spot
    out["pct_from_spot"] = (out["strike"] / spot - 1) if spot > 0 else 0.0

    # Total OI / Net OI
    out["total_oi"] = out["c_oi"] + out["p_oi"]
    out["net_oi"] = out["c_oi"] - out["p_oi"]

    # S²-normalized GEX profile
    s2_norm = spot * spot / 1e9 if spot > 0 else 1.0
    out["raw_cgex"] = out["c_gamma"] * s2_norm * out["c_oi"]
    out["raw_pgex"] = -out["p_gamma"] * s2_norm * out["p_oi"]
    out["raw_pos"] = np.where((out["raw_cgex"] + out["raw_pgex"]) > 0,
                               out["raw_cgex"] + out["raw_pgex"], 0)
    out["raw_neg"] = np.where((out["raw_cgex"] + out["raw_pgex"]) < 0,
                               out["raw_cgex"] + out["raw_pgex"], 0)
    out["dadj_cgex"] = out["raw_cgex"] * out["c_delta"]
    out["dadj_pgex"] = out["raw_pgex"] * out["p_delta"]
    out["dadj_pos"] = np.where((out["dadj_cgex"] + out["dadj_pgex"]) > 0,
                                out["dadj_cgex"] + out["dadj_pgex"], 0)
    out["dadj_neg"] = np.where((out["dadj_cgex"] + out["dadj_pgex"]) < 0,
                                out["dadj_cgex"] + out["dadj_pgex"], 0)

    return out


def compute_dashboard_levels(df: pd.DataFrame, spot: float) -> Dict[str, Any]:
    if df.empty or spot <= 0:
        return _empty_levels()

    levels = {}

    # Call Wall / Put Wall (max OI)
    levels["call_wall"] = int(df.loc[df["c_oi"].idxmax(), "strike"]) if df["c_oi"].max() > 0 else None
    levels["put_wall"] = int(df.loc[df["p_oi"].idxmax(), "strike"]) if df["p_oi"].max() > 0 else None
    levels["coi"] = levels["call_wall"]
    levels["poi"] = levels["put_wall"]

    # pGEX / nGEX
    pos_gex = df[df["net_gex"] > 0]
    levels["pgex"] = int(pos_gex.loc[pos_gex["net_gex"].idxmax(), "strike"]) if not pos_gex.empty else None
    neg_gex = df[df["net_gex"] < 0]
    levels["ngex"] = int(neg_gex.loc[neg_gex["net_gex"].idxmin(), "strike"]) if not neg_gex.empty else None

    # ── Transition zones (Excel AA/AB/AC logic) ──
    # Sort ascending for sequential analysis
    sdf = df.sort_values("strike").reset_index(drop=True)
    gex = sdf["net_gex"].values
    strikes = sdf["strike"].values

    # Y1 = strike with max GEX (col Y: where H=MAX → that strike)
    max_gex_strike = strikes[np.argmax(gex)] if len(gex) > 0 else spot
    # Z1 = strike with min GEX
    min_gex_strike = strikes[np.argmin(gex)] if len(gex) > 0 else spot

    # AA: TRUE if strike <= max_gex_strike AND (GEX<0 OR (GEX>0 and next_GEX<0))
    # AB: TRUE if strike >= min_gex_strike AND (GEX>0 OR (GEX<0 and prev_GEX>0))
    # AC: where BOTH AA and AB are TRUE → that strike is a transition
    transition_strikes = []
    for i in range(len(strikes)):
        k = strikes[i]
        g = gex[i]
        g_next = gex[i + 1] if i + 1 < len(gex) else 0
        g_prev = gex[i - 1] if i > 0 else 0

        aa = k <= max_gex_strike and (g < 0 or (g > 0 and g_next < 0))
        ab = k >= min_gex_strike and (g > 0 or (g < 0 and g_prev > 0))
        if aa and ab:
            transition_strikes.append(k)

    # AC1 = MAX of transition strikes (pTrans — positive/above)
    # AD1 = MIN of transition strikes (nTrans — negative/below)
    levels["ptrans"] = int(max(transition_strikes)) if transition_strikes else None
    levels["ntrans"] = int(min(transition_strikes)) if transition_strikes else None

    # Gamma dominance
    total_call_gex = df["call_gex"].sum()
    total_put_gex = abs(df["put_gex"].sum())
    gex_ratio = total_call_gex / total_put_gex if total_put_gex > 0 else 999.0
    levels["gex_ratio"] = round(gex_ratio, 2)
    levels["gamma_dominant"] = "CALL" if gex_ratio >= 1 else "PUT"

    levels["centered_spot"] = int(round(spot / 5) * 5)
    levels["spot"] = round(spot, 2)

    # Aggregates
    levels["total_call_volume"] = int(df["c_volume"].sum())
    levels["total_put_volume"] = int(df["p_volume"].sum())
    levels["total_call_oi"] = int(df["c_oi"].sum())
    levels["total_put_oi"] = int(df["p_oi"].sum())
    levels["pcr_volume"] = round(df["p_volume"].sum() / max(df["c_volume"].sum(), 1), 3)
    levels["pcr_oi"] = round(df["p_oi"].sum() / max(df["c_oi"].sum(), 1), 3)
    levels["total_net_gex"] = int(df["net_gex"].sum())
    levels["total_net_dex"] = int(df["net_dex"].sum())

    # ── Gauge needle: AVERAGE of BP% for 11 strikes below ATM ──
    # Excel: rows 23:33 in descending-sorted Dashboard = 11 rows just below spot
    # That's AO51 = IFERROR(ROUND(AVERAGE(AO23:AO33),1),0)
    atm = levels["centered_spot"]
    below_atm = df[df["strike"] < atm].sort_values("strike", ascending=False).head(11)
    if not below_atm.empty:
        valid_c = below_atm["bp_call"][(below_atm["bp_call"] > 0) & (below_atm["bp_call"] < 100)]
        valid_p = below_atm["bp_put"][(below_atm["bp_put"] > 0) & (below_atm["bp_put"] < 100)]
        levels["avg_bp_call"] = round(valid_c.mean(), 1) if not valid_c.empty else 0
        levels["avg_bp_put"] = round(valid_p.mean(), 1) if not valid_p.empty else 0
    else:
        levels["avg_bp_call"] = 0
        levels["avg_bp_put"] = 0

    return levels


def filter_chain_for_display(df: pd.DataFrame, spot: float,
                              num_above: int = 20, num_below: int = 20) -> pd.DataFrame:
    if df.empty or spot <= 0:
        return df
    atm = round(spot / 5) * 5
    low = atm - num_below * 5
    high = atm + num_above * 5
    mask = (df["strike"] >= low) & (df["strike"] <= high)
    return df[mask].sort_values("strike", ascending=False).reset_index(drop=True)


def _buying_pressure(high, low, opn, mark, volume) -> pd.Series:
    """
    Excel: =ROUND((ROUND(((HIGH-OPEN+(MARK-LOW))/2/(HIGH-LOW))*VOL,0))/VOL*100,0)
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
