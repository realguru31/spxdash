"""
calculations.py — Excel-exact formulas from SPX_Gamma_Dashboard_v1_3b.xlsm.

Level definitions (from O column formulas):
  Call Wall (O18) = strike with MAX Call VOLUME (col A)
  Put Wall  (O19) = strike with MAX Put VOLUME (col E)
  COI       (O20) = strike with MAX Call OI (col K)
  POI       (O25) = strike with MAX Put OI (col L)
  pGEX      (O21) = strike with MAX positive net GEX (col F)
  nGEX      (O24) = strike with MIN net GEX (col F)
  pTrans    (O22) = MAX of transition strikes (AC1)
  nTrans    (O23) = MIN of transition strikes (AD1)

Gauge needle: AVERAGE of BP% for 11 strikes below ATM (AO51/AP51)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any


def compute_chain_metrics(df: pd.DataFrame, spot: float) -> pd.DataFrame:
    if df.empty: return df
    o = df.copy()
    o["c_voi"] = np.where(o["c_oi"]>0, o["c_volume"]/o["c_oi"], 0.0)
    o["p_voi"] = np.where(o["p_oi"]>0, o["p_volume"]/o["p_oi"], 0.0)
    o["abs_delta"] = o["c_delta"].abs() + o["p_delta"].abs()
    o["call_gex"] = np.round(o["c_oi"]*o["c_gamma"]*100,0).astype(int)
    o["put_gex"] = -np.round(o["p_gamma"]*o["p_oi"]*100,0).astype(int)
    o["net_gex"] = o["call_gex"] + o["put_gex"]
    o["call_dex"] = np.round(o["c_delta"]*o["c_oi"]*100,0).astype(int)
    o["put_dex"] = np.round(o["p_delta"]*o["p_oi"]*100,0).astype(int)
    o["net_dex"] = o["call_dex"] + o["put_dex"]
    o["bp_call"] = _bp(o["c_high"],o["c_low"],o["c_open"],o["c_mark"],o["c_volume"])
    o["bp_put"] = _bp(o["p_high"],o["p_low"],o["p_open"],o["p_mark"],o["p_volume"])
    o["pct_from_spot"] = (o["strike"]/spot - 1) if spot > 0 else 0.0
    o["total_oi"] = o["c_oi"] + o["p_oi"]
    o["net_oi"] = o["c_oi"] - o["p_oi"]
    s2 = spot*spot/1e9 if spot>0 else 1.0
    o["raw_cgex"] = o["c_gamma"]*s2*o["c_oi"]
    o["raw_pgex"] = -o["p_gamma"]*s2*o["p_oi"]
    o["raw_pos"] = np.where((o["raw_cgex"]+o["raw_pgex"])>0, o["raw_cgex"]+o["raw_pgex"], 0)
    o["raw_neg"] = np.where((o["raw_cgex"]+o["raw_pgex"])<0, o["raw_cgex"]+o["raw_pgex"], 0)
    o["dadj_cgex"] = o["raw_cgex"]*o["c_delta"]
    o["dadj_pgex"] = o["raw_pgex"]*o["p_delta"]
    o["dadj_pos"] = np.where((o["dadj_cgex"]+o["dadj_pgex"])>0, o["dadj_cgex"]+o["dadj_pgex"], 0)
    o["dadj_neg"] = np.where((o["dadj_cgex"]+o["dadj_pgex"])<0, o["dadj_cgex"]+o["dadj_pgex"], 0)
    return o


def compute_dashboard_levels(df: pd.DataFrame, spot: float) -> Dict[str, Any]:
    if df.empty or spot <= 0: return _empty()
    lv = {}

    # Call Wall = max Call VOLUME strike (Excel O18: MAX(A2:A42))
    lv["call_wall"] = int(df.loc[df["c_volume"].idxmax(),"strike"]) if df["c_volume"].max()>0 else None
    # Put Wall = max Put VOLUME strike (Excel O19: MAX(E2:E42))
    lv["put_wall"] = int(df.loc[df["p_volume"].idxmax(),"strike"]) if df["p_volume"].max()>0 else None
    # COI = max Call OI strike (Excel O20: MAX(K2:K42))
    lv["coi"] = int(df.loc[df["c_oi"].idxmax(),"strike"]) if df["c_oi"].max()>0 else None
    # POI = max Put OI strike (Excel O25: MAX(L2:L42))
    lv["poi"] = int(df.loc[df["p_oi"].idxmax(),"strike"]) if df["p_oi"].max()>0 else None
    # pGEX = max positive GEX (Excel O21: MAX(F2:F42))
    pg = df[df["net_gex"]>0]
    lv["pgex"] = int(pg.loc[pg["net_gex"].idxmax(),"strike"]) if not pg.empty else None
    # nGEX = min GEX (Excel O24: MIN(F2:F42))
    ng = df[df["net_gex"]<0]
    lv["ngex"] = int(ng.loc[ng["net_gex"].idxmin(),"strike"]) if not ng.empty else None

    # Transition zones — Excel AA/AB/AC logic
    sdf = df.sort_values("strike").reset_index(drop=True)
    gex = sdf["net_gex"].values; strikes = sdf["strike"].values
    max_gex_k = strikes[np.argmax(gex)] if len(gex)>0 else spot
    min_gex_k = strikes[np.argmin(gex)] if len(gex)>0 else spot
    trans = []
    for i in range(len(strikes)):
        k,g = strikes[i], gex[i]
        gn = gex[i+1] if i+1<len(gex) else 0
        gp = gex[i-1] if i>0 else 0
        aa = k <= max_gex_k and (g<0 or (g>0 and gn<0))
        ab = k >= min_gex_k and (g>0 or (g<0 and gp>0))
        if aa and ab: trans.append(k)
    lv["ptrans"] = int(max(trans)) if trans else None
    lv["ntrans"] = int(min(trans)) if trans else None

    # Gamma dominance
    tcg = df["call_gex"].sum(); tpg = abs(df["put_gex"].sum())
    gr = tcg/tpg if tpg>0 else 999.0
    lv["gex_ratio"] = round(gr,2)
    lv["gamma_dominant"] = "CALL" if gr>=1 else "PUT"
    lv["centered_spot"] = int(round(spot/5)*5)
    lv["spot"] = round(spot,2)

    # Aggregates
    lv["total_call_volume"] = int(df["c_volume"].sum())
    lv["total_put_volume"] = int(df["p_volume"].sum())
    lv["total_call_oi"] = int(df["c_oi"].sum())
    lv["total_put_oi"] = int(df["p_oi"].sum())
    lv["pcr_volume"] = round(df["p_volume"].sum()/max(df["c_volume"].sum(),1),3)
    lv["pcr_oi"] = round(df["p_oi"].sum()/max(df["c_oi"].sum(),1),3)
    lv["total_net_gex"] = int(df["net_gex"].sum())
    lv["total_net_dex"] = int(df["net_dex"].sum())

    # Gauge: 11 strikes below ATM
    atm = lv["centered_spot"]
    below = df[df["strike"]<atm].sort_values("strike",ascending=False).head(11)
    if not below.empty:
        vc = below["bp_call"][(below["bp_call"]>0)&(below["bp_call"]<100)]
        vp = below["bp_put"][(below["bp_put"]>0)&(below["bp_put"]<100)]
        lv["avg_bp_call"] = round(vc.mean(),1) if not vc.empty else 0
        lv["avg_bp_put"] = round(vp.mean(),1) if not vp.empty else 0
    else:
        lv["avg_bp_call"] = 0; lv["avg_bp_put"] = 0
    return lv


def filter_chain_for_display(df, spot, num_above=20, num_below=20):
    if df.empty or spot<=0: return df
    atm = round(spot/5)*5
    lo,hi = atm-num_below*5, atm+num_above*5
    return df[(df["strike"]>=lo)&(df["strike"]<=hi)].sort_values("strike",ascending=False).reset_index(drop=True)


def _bp(high,low,opn,mark,volume):
    hl = high-low; num = (high-opn+mark-low)/2
    bp = np.where(hl>0, num/hl*100, 50)
    return pd.Series(np.round(bp,0).astype(int), index=high.index)


def _empty():
    return {"call_wall":None,"put_wall":None,"coi":None,"poi":None,
            "pgex":None,"ngex":None,"ptrans":None,"ntrans":None,
            "gex_ratio":0,"gamma_dominant":"N/A","centered_spot":0,"spot":0,
            "total_call_volume":0,"total_put_volume":0,"total_call_oi":0,"total_put_oi":0,
            "pcr_volume":0,"pcr_oi":0,"total_net_gex":0,"total_net_dex":0,
            "avg_bp_call":0,"avg_bp_put":0}
