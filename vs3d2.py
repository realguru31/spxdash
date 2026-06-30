"""
vs3d2_v1.16.py — SPX 0DTE+ Gamma & Charm (Streamlit POC)
=================================================
Point your streamlit.io app at this file.

CHANGELOG (newest first) — what changed and why, per version
─────────────────────────────────────────────────────────────────────────────
v1.16  [NEW 'Forward models' tab — VS3D-style price×time forward simulation]
  • Added 5th tab '🔮 Forward models (price×time sim)'. Replicates VS3D's Gradient
    Chart mechanic: each pixel (price P, time-of-day τ) = the greek IF spot were P at
    time τ, from the CURRENT chain, advancing the clock and re-pricing with BS SEEDED
    by each strike's Barchart IV (anchors to real skew, projects forward). Blue 'now'
    line: left held flat (no past re-sim), right = pure forward sim to 16:00. Real
    SPX500 candles overlaid up to now. Charm colored by HEDGING EFFECT (red=sell,
    green=buy) per docs 7.7. All 5 model weightings (naive OI, zero-open VOL, OI+VOL,
    dVOL, vol/OI); dVOL & vol/OI flagged 'forward-sim weak' (defined by past change).
  • New: forward_sim_grid(), _fwd_weight(), _fwd_norm(). Reuses bs_gamma/bs_charm/_T_at
    and the existing candle + time-axis helpers. NO IPython (that was a Colab-only dep;
    deploying the Colab script as the app caused ModuleNotFoundError: IPython).
v1.15  [NEW 'VS3D' TAB — sign-free dashboard ported from Colab; robust auto-refresh]
  • Added a 4th tab '🧭 VS3D (sign-free dashboard)' alongside Cone/Landscape/Surface
    (nothing removed). 6 panels, all computable from FREE Barchart data:
      GAMMA net exposure · |GAMMA| magnitude (walls, sign-free) · SPEED ∂γ/∂spot ·
      CHARM ∂δ/∂t (empirical, w/ flip lines) · COLOR ∂γ/∂t · SIGNALS block
      (straddle range, straddle-decay 'snake-oil' gate, fishbone, gamma absorption,
       skew proxy, VIX regime, timing window).
    Charm/Color/decay populate on the 2nd snapshot (same pattern as Cone charm).
    All panels carry SPX500 candles on the session-time axis (reuses draw_candles).
  • Honest limit shown in-tab: strike-level dealer long/short (anchor vs test),
    net-hedgeable filtering, and OTC flow are NOT replicable without paid data.
  • Auto-refresh hardened: uses streamlit-autorefresh when present; otherwise a
    built-in JS 5-min full-page reload (re-pulls; session_state/snapshots persist),
    replacing the old fragment ticker that didn't re-pull.
  • New analytics (sign-free): vs3d_profiles/_density, vs3d_straddle, vs3d_fishbone,
    vs3d_absorption, vs3d_skew, vs3d_timing, vs3d_vix_regime + mag/speed cmaps.
v1.14  [CONE: real Barchart gamma density + tunable smoothing — still no surface/proj]
  • Cone gamma profile rebuilt as a DENSITY: net signed GEX per strike (Barchart gamma,
    calls+/puts−) interpolated onto the price grid. Smoothing is a SIDEBAR SLIDER
    ("Gradient smoothing", default low) — 0 = raw per-strike detail (bumpy, like vols3d
    live), higher = smoother. Confirmed via vols3d hover tooltip that per-strike
    granularity is desired (bumpy is NOT a bug).
  • Learned from vols3d tooltip: the dashed line is a CONTOUR (zero-boundary of the
    gamma field), not a single "flip" level; the field has multiple real pockets. The
    cone x-axis carries NO time/forecast meaning — width = gamma magnitude per price,
    candles overlaid only for price context. (Corrected my repeated misreading.)
  • Empirical charm profile also rebuilt as interpolated density with same slider.
v1.13  [CONE converted to real Barchart data — surface/projection still pending]
  • Confirmed via Colab: Barchart returns gamma+delta per strike (430/430), but NO charm/
    vanna (only delta,gamma,theta,vega,rho). So gamma is used DIRECTLY; charm is derived
    empirically as Δdelta/Δt from real Barchart deltas across snapshots (user's choice).
  • CONE gamma: net GEX per price level from Barchart per-strike gamma (flat bands, vs3d
    style). NO Black-Scholes. compute_walls also switched to Barchart gamma.
  • CONE charm: empirical Δdelta/Δt vs the previous snapshot; BLANK on the 1st snapshot
    (shows a placeholder), populates once a 2nd snapshot exists. Chain now stores 'delta'.
  • New helpers _gex_profile_barchart() and _empirical_charm_profile(). Verified: gamma
    matches Barchart, charm None on snap1 and populated on snap2.
  • TODO: Landscape (per-strike Barchart gamma projected with T-decay shape, pinned per
    strike + bad-strike clipping) and Intraday surface still use BS internally — next.
v1.12
  • FIX: candles filled the chart to ~16:00 even at 11:56. Cause: tvdatafeed returns
    NAIVE UTC timestamps (verified: last bar 15:56 == UTC now, +3.99h vs EST), but the
    code assumed they were already EST — so every bar was plotted +4h to the right.
  • fetch_bars_raw now localizes timestamps as UTC and converts to EST via zoneinfo
    (DST-aware: −4h summer / −5h winter, never hardcoded), then drops tz.
  • prep_bars now also cuts bars at <= now_est(), so the chart never extends past the
    current minute. Verified with a simulated UTC feed: 13:30 UTC→09:30 EST, series ends at now.
v1.11
  • THE ACTUAL ROOT CAUSE: the symbol was wrong. CAPITALCOM:SPX is a ~68-handle
    instrument (1–3 vol/min) — NOT the index. The real S&P 500 is CAPITALCOM:SPX500
    (~7400, real volume), already on correct scale. Confirmed via live Colab dump.
  • Switched fetch_bars_raw to symbol "SPX500" and REMOVED all scaling/anchoring/window-
    gating from prep_bars. Bars are plotted exactly as returned — no transform. This
    retires the entire v1.2–v1.10 scaling saga, which was chasing a wrong-symbol artifact.
  • Diagnostics (Colab): colab_rth_dump.py (raw RTH dump) + colab_symbol_probe.py.
v1.10
  • Bar handling rewritten to the user's rule (cleaner than the v1.9 threshold):
    anchor CAPITAL.COM bars to the trusted BARCHART SPOT — scale by ratio=spot/feed-median
    (skipped when ratio is 0.98–1.02, i.e. already correct, so a normal day is untouched) —
    then KEEP ONLY bars within ±window_pct of spot (the slider); anything else is ignored.
    Caption/diagnostics report the scale factor and how many bars were dropped.
  • Added colab_bar_diagnostic.py (separate file): standalone Colab cell that pulls the
    REAL CAPITAL.COM bars + REAL Barchart spot and prints the scale/window numbers, so the
    feed's behaviour can be confirmed without fighting Streamlit.
v1.9
  • ROOT CAUSE FOUND (via v1.8 diagnostics): the CAPITAL.COM:SPX feed quotes SPX on a
    DIVIDED scale (~108×, e.g. ~68 instead of ~7400). Candles were being drawn correctly
    but at y≈68, far below the price window, so invisible. (Not contrast, not date/tz.)
  • FIX: prep_bars scales bars by the EXACT ratio spot/bar-level, but ONLY when it's a
    GROSS mismatch (>3× or <1/3×). A normal/trending day (ratio≈1) is left EXACTLY as-is,
    so the old '7429 shown at 7450' inflation cannot recur. Diagnostics shows the factor.
  • Verified: ~108× and ~10× feeds corrected onto spot; normal ~7400 day untouched (out==raw).
v1.8
  • Added a DIAGNOSTICS expander at the bottom of the Cone tab. Shows the bar pipeline
    at every stage: raw feed rows/dtypes/dates/times, prep_bars result, session window
    datenums vs bar datenums, how many bars land INSIDE the x-window (i.e. actually get
    drawn), and price-window coverage. Purpose: stop guessing why candles don't appear —
    read the numbers. If "bars INSIDE session window" = 0, it's a date/tz mismatch, not contrast.
v1.7
  • FIX: candles were being DRAWN (256 of them) but invisible — the old thin 0.3px
    gray outline got swallowed by the saturated gradient. Candles now have a dark halo
    on wicks + a contrasting body outline so they read on top of any gradient color.
    (This was a contrast bug, not a data/filter bug — bars were in-window the whole time.)
v1.6
  • FIX (regression from v1.5): y-axis collapsed to 0–7400 again. Cause: v1.5 window
    math did lo=min(lo, bars['l'].min()) with NO guard, so a single feed bar with a
    near-zero low dragged the whole axis to 0 (gradient invisible, candles flat).
  • Y-axis is now PURELY spot ± window_pct. Bars NEVER influence the axis range, so no
    stray feed value can collapse or inflate it. A junk bar just plots off-screen.
    Tested with an injected low=0.01 bar: axis stays spot±2.5%, gradient spans it.
v1.5
  • Simplified bar handling: CAPITAL.COM:SPX is clean index data, so prep_bars now
    just keeps today's RTH bars (09:30–16:00 EST) and plots them. Removed the spot-band
    filter, median fallback, and numeric-coercion logic from v1.4 that was rejecting
    ALL bars ("all bars outside ±20% of spot"). Window = spot ± window_pct, widened by
    today's RTH range. WHY: the v1.4 safety net over-rejected; the data doesn't need it.
v1.4
  • FIX (regression from v1.3): price y-axis collapsed to 0–7400, gradient invisible,
    candles flat at bottom. Two root causes fixed:
    1) Bar sanity filter judged bars against their OWN median, so a cluster of corrupt
       feed rows dragged the median down and let junk (near-zero lows) survive. Now
       bars are filtered against the KNOWN spot (±20%), which cannot be fooled.
    2) Window math took bars' raw min/max, so one bad low collapsed p_min→~0. Window
       is now ANCHORED to spot (±window_pct), only widened by bars within ±15% of spot,
       with a final check that the range straddles spot and is a sane width.
  WHY v1.3 broke it: removing the spot*0.5 clamp exposed the weak median filter; the
  alignment guard didn't catch it because price/gradient/axis all shared the SAME bad range.
v1.3
  • Removed ALL price rescaling. CAPITAL.COM:SPX is the SPX index 1:1, so candles
    are now drawn exactly as TradingView reports them (prep_bars only drops
    obviously corrupt rows; it never multiplies/shifts a price).
  • Removed every `p_min = max(p_min, spot*0.5)` clamp in the three builders, so the
    price grid (pg) equals the requested window exactly — no hidden range shift.
  • Added an on-chart ALIGNMENT GUARD in _finish(): checks each gradient image's
    y-extent == price grid == axis ylim; if they ever drift it stamps a red
    "⚠ Y-AXIS MISALIGNED — DO NOT TRADE OFF THIS" banner. Verified it stays silent
    when aligned and fires when broken.
  • Added a numeric regression (run offline) across all 3 renderers × tight/normal/
    wide windows confirming price/gradient/axis share one y-scale.
  WHY: a candle high of 7429 was displaying at ~7450 — caused by rescaling bars by
  the session median (inflates on a trending day). Decisions need price ON the true
  gradient level, so every value-altering transform was stripped and guarded.

v1.2
  • First fix attempt for the above: rescale only on a gross (>=2x) mismatch vs the
    latest bar instead of the day's median. (Superseded by v1.3, which removes it
    entirely — the right call since the feed is already 1:1.)

v1.1
  • X-axis hard-locked to RTH 09:30–16:00 EST: set_autoscalex_on(False) + margins(x=0)
    so candle wicks / wall-track plots can no longer re-expand the window. Hourly ticks.
  WHY: the display window kept drifting because plotting bars outside RTH triggered
  matplotlib autoscale after set_xlim.

v1.0
  • Surface projection (right of "now") now uses REAL TIME-DECAY: the current book is
    re-evaluated at shrinking T minute-by-minute to the 0DTE close, so pockets sharpen
    as T→0 (reuses the BS engine; per-option expiry, so multi-expiry decays correctly).
  • Candles pulled FRESH from tvdatafeed every run — caching removed entirely.
  WHY: flat projection "looked like shit"; candles looked stale due to the bars cache.

v0.9
  • Surface projects the CURRENT structure FLAT from now→close (dimmed levels map, no
    decay yet); recorded portion still shows real migration. Filename versioning began.

v0.8
  • Surface tab reworked to "Option A": positioning heatmap over real recorded time
    (first snapshot→now), migrating γ-flip contour + call/put wall migration tracks.
    No projection. WHY: trader view = watch positioning shift vs price reaction.

v0.7
  • Candles switched to 1-minute bars (from 5-min) for tighter price tracking.

v0.6
  • Snapshot scrubber slider: view the book as of any past snapshot; cone/landscape
    redraw to that snapshot, surface trims to snapshots up to the selected time.

v0.5
  • Unified candles + x-axis across all 3 tabs: one draw_candles(), one session_window(),
    one style_time_axis(). Only the gradient math differs per tab now.

v0.4
  • All times pinned to US Eastern via now_est()/today_est() (zoneinfo); tvdatafeed
    bars treated as already-EST. WHY: cloud box runs UTC, distorting T and the bar-date
    filter so today's candles weren't printing.

v0.3
  • Tabbed UI: Cone | Landscape (forward projection) | Intraday surface. Each tab stacks
    all its methods, every chart shows Gamma + Charm.

v0.2
  • Removed TradingView login — no-login CAPITALCOM:SPX works.

v0.1
  • Streamlit POC: in-memory 5-min chain snapshots (st.session_state, no files),
    auto-refresh every 5 min, manual Snapshot/Refresh/Clear.
─────────────────────────────────────────────────────────────────────────────

requirements.txt (put this next to vs3d.py in your GitHub repo):
    streamlit
    streamlit-autorefresh
    requests
    pandas
    numpy
    scipy
    matplotlib
    git+https://github.com/rongardF/tvdatafeed.git

Notes
-----
• Snapshots are kept ENTIRELY IN MEMORY (st.session_state) — POC, no files.
  They accumulate while the app session is alive and reset if the app restarts
  or sleeps. That's fine for a proof of concept.
• A snapshot of the option chain is taken when one is "due" (≥5 min since the
  last) or when you click "Snapshot now". Auto-refresh re-runs the app every
  5 minutes which triggers a due snapshot.
• Landscape/cone views use the latest snapshot. The "Intraday surface" view
  uses the full snapshot history (so OI+flow / flow-from-open / interval-flow
  actually accumulate over the session).
• Sign = standard dealer convention (calls +, puts −). Volume is unsigned; we
  do not guess buy/sell.
"""
import datetime as dt, time as _time, warnings
import requests, numpy as np, pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from scipy.stats import norm
from scipy.ndimage import gaussian_filter1d
from urllib.parse import unquote
warnings.filterwarnings("ignore")

# ── all times are US Eastern (CAPITALCOM:SPX trades on EST/EDT) ───────────────
from zoneinfo import ZoneInfo
EST = ZoneInfo("America/New_York")
def now_est():            # current time, EST, naive (tz stripped for arithmetic)
    return dt.datetime.now(EST).replace(tzinfo=None)
def today_est():
    return now_est().date()

st.set_page_config(page_title="vs3d · SPX 0DTE Gamma/Charm", layout="wide")

# ════════════════════════════ Barchart ══════════════════════════════════════
_UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
BASE="https://www.barchart.com"
OPTIONS_URL=f"{BASE}/proxies/core-api/v1/options/get"; QUOTE_URL=f"{BASE}/proxies/core-api/v1/quotes/get"
def _page(sym): return f"{BASE}/stocks/quotes/{sym.replace('$','%24')}/options"
def init_session(sym="$SPX"):
    s=requests.Session()
    r=s.get(_page(sym),headers={"accept":"text/html,application/xhtml+xml",
            "user-agent":_UA,"cache-control":"max-age=0"},timeout=20); r.raise_for_status()
    ck=s.cookies.get_dict()
    if "XSRF-TOKEN" not in ck: raise RuntimeError("No XSRF-TOKEN cookie")
    xsrf=unquote(unquote(ck["XSRF-TOKEN"]))
    return s,{"accept":"application/json","referer":_page(sym),"user-agent":_UA,"x-xsrf-token":xsrf}
def get_spot(s,h,sym="$SPX"):
    r=s.get(QUOTE_URL,params={"symbols":sym,"fields":"lastPrice","raw":"1"},headers=h,timeout=10); r.raise_for_status()
    d=r.json().get("data",[]); return float(d[0].get("raw",d[0]).get("lastPrice",0))
def fetch_chain(s,h,expiry,sym="$SPX"):
    f="strikePrice,bidPrice,askPrice,optionType,volatility,delta,gamma,openInterest,volume"
    for a in range(3):
        try:
            r=s.get(OPTIONS_URL,params={"baseSymbol":sym,"groupBy":"optionType","expirationDate":expiry,
                "fields":f,"orderBy":"strikePrice","orderDir":"asc","raw":"1"},headers=h,timeout=15)
            if r.status_code==401: _,h2=init_session(sym); h.update(h2); continue
            r.raise_for_status(); data=r.json().get("data",{}); rows=[]
            if isinstance(data,dict):
                for ot,items in data.items():
                    for it in (items or []):
                        raw=it.get("raw",it)
                        def num(k):
                            v=raw.get(k,None); return float(v) if v not in (None,"") else np.nan
                        rows.append({"strike":num("strikePrice"),"type":ot.lower(),"iv":num("volatility"),
                            "gamma":num("gamma"),"delta":num("delta"),"oi":num("openInterest"),"volume":num("volume"),
                            "bid":num("bidPrice"),"ask":num("askPrice")})
            return pd.DataFrame(rows) if rows else None
        except Exception as ex:
            _time.sleep(2)
    return None
def discover_expiries(s,h,n,sym="$SPX"):
    from datetime import date,timedelta
    d=today_est(); found=[]; exps=[]
    while len(found)<n and (d-today_est()).days<40:
        if d.weekday()<5:
            es=d.strftime("%Y-%m-%d"); ch=fetch_chain(s,h,es,sym)
            if ch is not None and not ch.empty:
                ch=ch.copy(); ch["expiry"]=es; found.append(ch); exps.append(es)
        d+=timedelta(days=1)
    if not found: raise RuntimeError("No valid expiries found")
    return exps, pd.concat(found, ignore_index=True)

# ════════════════════════════ Greeks / weights ══════════════════════════════
def bs_gamma(S,K,T,sig):
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    d1=(np.log(S/K)+0.5*sig**2*T)/(sig*np.sqrt(T)); return norm.pdf(d1)/(S*sig*np.sqrt(T))
def bs_charm(S,K,T,sig):
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    sq=sig*np.sqrt(T); d1=(np.log(S/K)+0.5*sig**2*T)/sq; d2=d1-sq; return norm.pdf(d1)*d2/(2.0*T)
def _T_at(es, ts):
    exp=dt.datetime.combine(dt.datetime.strptime(es,"%Y-%m-%d").date(),dt.time(16,0))
    return max((exp-ts).total_seconds(),60.)/(365*24*3600)
def weight_for(c, method):
    oi=c["oi"].fillna(0); vol=c["volume"].fillna(0)
    if method=="oi":           return oi.where(oi>0,vol)
    if method in ("volume","flow_reset"): return vol.where(vol>0,oi)
    if method=="oi_plus_flow": return oi+vol
    raise ValueError(method)

# ════════════════════════════ GEX / charm from BARCHART data ════════════════
# Gamma is taken DIRECTLY from Barchart per strike (confirmed: every strike has it).
# Net signed GEX per strike (calls +, puts −) is aggregated, then turned into a SMOOTH
# DENSITY across price (gamma magnitude tailing off across strikes) — NOT discrete
# per-strike bumps. NO Black-Scholes anywhere.
def _gex_profile_barchart(c, pg, mult=100, smooth_frac=0.01):
    """Net dealer GEX as a density vs price level pg, from Barchart per-strike gamma.
    Net signed GEX per strike (calls +, puts −) is interpolated onto the price grid,
    then smoothed by smooth_frac (0 = raw per-strike detail, higher = smoother)."""
    if c.empty: return np.zeros_like(pg)
    sign=np.where(c["type"].values=="call",1.0,-1.0)
    per=pd.Series(sign*c["gamma"].fillna(0).values*c["w"].values,
                  index=c["strike"].values).groupby(level=0).sum().sort_index()
    if per.empty: return np.zeros_like(pg)
    ks=per.index.values.astype(float); vs=per.values.astype(float)
    prof=np.interp(pg, ks, vs, left=0.0, right=0.0)
    sigma=len(pg)*smooth_frac
    if sigma>0.3: prof=gaussian_filter1d(prof, sigma)
    return prof*mult*pg

def _empirical_charm_profile(c_now, c_prev, dt_hours, pg, mult=100, smooth_frac=0.025):
    """Charm proxy from REAL Barchart deltas: per strike (delta_now−delta_prev)/Δt,
    weighted, signed (call +/put −), aggregated per strike then interpolated+smoothed
    into a density across price (matching the gamma cone). None if no prior snapshot."""
    if c_prev is None or c_now is None or c_now.empty or dt_hours<=0: return None
    prev=c_prev.set_index(["expiry","strike","type"])["delta"] if len(c_prev) else None
    if prev is None or prev.empty: return None
    recs={}
    any_pair=False
    for _,r in c_now.iterrows():
        key=(r["expiry"],r["strike"],r["type"])
        if key not in prev.index: continue
        dprev=prev.loc[key]
        if isinstance(dprev,pd.Series): dprev=float(dprev.iloc[0])
        if pd.isna(dprev) or pd.isna(r["delta"]): continue
        ddelta=(float(r["delta"])-dprev)/dt_hours
        sign=1.0 if r["type"]=="call" else -1.0
        w=float(r["w"]) if not pd.isna(r["w"]) else 0.0
        amt=sign*ddelta*w
        recs[r["strike"]]=recs.get(r["strike"],0.0)+amt; any_pair=True
    if not any_pair or not recs: return None
    ks=np.array(sorted(recs)); vs=np.array([recs[k] for k in ks])
    prof=np.interp(pg, ks, vs, left=0.0, right=0.0)
    sigma=len(pg)*smooth_frac
    if sigma>0.3: prof=gaussian_filter1d(prof, sigma)
    return prof*mult*pg

# ════════════════════════════ Forward projection ════════════════════════════
def build_projection(chain, spot, method, p_min, p_max, n_time=120, n_price=220):
    c=chain.dropna(subset=["strike","iv","expiry"]).copy()
    c["w"]=weight_for(c, method)
    c=c[(c["strike"]>=p_min*0.85)&(c["strike"]<=p_max*1.15)]
    if c.empty: raise RuntimeError("No strikes near window")
    pg=np.linspace(p_min,p_max,n_price); S=pg[:,None]   # price grid == requested window, no clamp
    exp_dt={e:dt.datetime.combine(dt.datetime.strptime(e,"%Y-%m-%d").date(),dt.time(16,0)) for e in c["expiry"].unique()}
    day=min(exp_dt.values()).date()
    sess_start=dt.datetime.combine(day,dt.time(9,30)); sess_end=min(exp_dt.values())
    times=[sess_start+k*(sess_end-sess_start)/(n_time-1) for k in range(n_time)]
    ca=c[c.type=="call"]; pu=c[c.type=="put"]
    def arrs(df): return (df["strike"].values,df["w"].values,df["iv"].values,
                          np.array([exp_dt[e].timestamp() for e in df["expiry"]]))
    Kc,Wc,Vc,Ec=arrs(ca); Kp,Wp,Vp,Ep=arrs(pu); YR=365*24*3600
    Zg=np.zeros((n_price,n_time)); Zc=np.zeros_like(Zg)
    for j,t in enumerate(times):
        ts=t.timestamp(); Tc=np.maximum(Ec-ts,60)/YR; Tp=np.maximum(Ep-ts,60)/YR
        Zg[:,j]=((bs_gamma(S,Kc[None,:],Tc[None,:],Vc[None,:])*Wc[None,:]).sum(1)
                -(bs_gamma(S,Kp[None,:],Tp[None,:],Vp[None,:])*Wp[None,:]).sum(1))*100*pg
        Zc[:,j]=((bs_charm(S,Kc[None,:],Tc[None,:],Vc[None,:])*Wc[None,:]).sum(1)
                -(bs_charm(S,Kp[None,:],Tp[None,:],Vp[None,:])*Wp[None,:]).sum(1))*100*pg
    Zg=gaussian_filter1d(Zg,1.4,axis=0); Zc=gaussian_filter1d(Zc,1.4,axis=0)
    now=now_est()
    jnow=int(np.clip((now-sess_start).total_seconds()/max((sess_end-sess_start).total_seconds(),1)*(n_time-1),0,n_time-1))
    return pg,Zg,Zc,times,jnow,c

# ════════════════════════════ Cone (single snapshot) ════════════════════════
def cone_profiles(chain, spot, p_min, p_max, weighting, n_price=220, mult=100,
                  prev_chain=None, dt_hours=None, smooth_frac=0.01):
    """Cone GEX/charm from BARCHART data. Gamma per strike → net GEX density (smoothing
    tunable via smooth_frac; low = per-strike detail like vols3d). Charm = empirical
    Δdelta/Δt from real Barchart deltas vs prior snapshot; None when no prior snapshot."""
    c=chain.dropna(subset=["strike","gamma"]).copy()
    c["w"]=weight_for(c, weighting)
    c=c[(c["strike"]>=p_min*0.85)&(c["strike"]<=p_max*1.15)]
    if "expiry" not in c.columns: c["expiry"]="0"
    pg=np.linspace(p_min,p_max,n_price)
    gex=_gex_profile_barchart(c, pg, mult, smooth_frac)
    pc=None
    if prev_chain is not None and dt_hours:
        pc=prev_chain.dropna(subset=["strike","delta"]).copy()
        if "expiry" not in pc.columns: pc["expiry"]="0"
    chm=_empirical_charm_profile(c, pc, dt_hours or 0, pg, mult, smooth_frac)
    return pg,gex,chm,c
def field_from_profile(vals, n_x=360, gain=4.5, glow=True):
    scale=np.percentile(np.abs(vals),85) or 1.0
    b=0.5+0.5*np.tanh(vals/scale); b=gaussian_filter1d(b,2.0)
    xs=np.linspace(0,1,n_x); V=np.tanh(gain*(b[:,None]-xs[None,:]))
    if glow:
        cap=np.percentile(np.abs(vals),97) or 1.0
        mag=np.clip(np.abs(vals)/cap,0,1); mag=gaussian_filter1d(mag,2.0); V=V*(0.55+0.45*mag)[:,None]
    return V,b

# ════════════════════════════ Intraday surface (history) ════════════════════
def _strike_weight(ch, mode, base_vol, prev_vol, weighting):
    oi=ch["oi"].fillna(0); vol=ch["volume"].fillna(0)
    key=list(zip(ch["expiry"],ch["strike"],ch["type"]))
    v0=pd.Series([base_vol.get(k,0.0) for k in key],index=ch.index).fillna(0)
    if mode=="cumulative":     return weight_for(ch, weighting)
    if mode=="oi_plus_flow":   return oi+(vol-v0).clip(lower=0)
    if mode=="flow_from_open": return (vol-v0).clip(lower=0)
    if mode=="interval_flow":
        if prev_vol is None: return (vol-v0).clip(lower=0)
        vp=pd.Series([prev_vol.get(k,0.0) for k in key],index=ch.index).fillna(0)
        return (vol-vp).clip(lower=0)
    raise ValueError(mode)
def build_time_surface(snaps, mode, p_min, p_max, weighting="volume", n_price=220, smooth_p=1.4):
    spot=snaps[-1]["spot"]
    pg=np.linspace(p_min,p_max,n_price); S=pg[:,None]   # price grid == requested window, no clamp
    base=snaps[0]["chain"]
    base_vol={(e,k,t):float(v) for e,k,t,v in zip(base["expiry"],base["strike"],base["type"],base["volume"].fillna(0))}
    Zg=np.zeros((n_price,len(snaps))); Zc=np.zeros_like(Zg); times=[]; prev_vol=None; last=None
    cwalls=[]; pwalls=[]                       # per-snapshot call/put wall tracks
    for j,snap in enumerate(snaps):
        ch=snap["chain"].dropna(subset=["strike","iv","expiry"]).copy()
        ch["w"]=_strike_weight(ch,mode,base_vol,prev_vol,weighting)
        ch["T"]=ch["expiry"].map(lambda e:_T_at(e,snap["ts"]))
        ca=ch[ch.type=="call"]; pu=ch[ch.type=="put"]
        def prof(df,fn):
            if df.empty: return np.zeros(n_price)
            return (fn(S,df["strike"].values[None,:],df["T"].values[None,:],df["iv"].values[None,:])*df["w"].values[None,:]).sum(1)
        Zg[:,j]=(prof(ca,bs_gamma)-prof(pu,bs_gamma))*100*pg
        Zc[:,j]=(prof(ca,bs_charm)-prof(pu,bs_charm))*100*pg
        cwj,pwj=compute_walls(ch,snap["spot"])   # walls as of THIS snapshot
        cwalls.append(cwj); pwalls.append(pwj)
        times.append(snap["ts"])
        prev_vol={(e,k,t):float(v) for e,k,t,v in zip(ch["expiry"],ch["strike"],ch["type"],ch["volume"].fillna(0))}
        last=ch
    if smooth_p>0:
        Zg=gaussian_filter1d(Zg,smooth_p,axis=0); Zc=gaussian_filter1d(Zc,smooth_p,axis=0)
    return pg,Zg,Zc,times,last,spot,cwalls,pwalls

# ════════════════════════════ shared analytics ══════════════════════════════
def zero_crossings(pg, vals):
    s=np.sign(vals); idx=np.where(np.diff(s)!=0)[0]; out=[]
    for i in idx:
        y0,y1=vals[i],vals[i+1]
        if y1!=y0: out.append(pg[i]-y0*(pg[i+1]-pg[i])/(y1-y0))
    return out
def compute_walls(c, spot, mult=100):
    # walls from BARCHART per-strike gamma (same source as the gradient), not BS.
    g=c["gamma"].fillna(0).values if "gamma" in c else np.zeros(len(c))
    sign=np.where(c["type"].values=="call",1.0,-1.0)
    per=pd.Series(g*c["w"].values*sign*mult*spot,index=c["strike"].values).groupby(level=0).sum()
    if per.empty: return None,None
    return float(per.idxmax()),float(per.idxmin())

# ═══════════════ VS3D sign-free analytics (replicable from Barchart) ═══════════
# Everything here is computable WITHOUT participant/signed data. The one thing we
# canNOT do (strike-level dealer long/short = anchor vs test) is intentionally absent.
def _vs3d_per(st, arr):
    d={}
    for k,a in zip(st,arr): d[k]=d.get(k,0.0)+a
    return d
def _vs3d_density(strike_map, pg, smooth=0.02):
    if not strike_map: return np.zeros_like(pg)
    ks=np.array(sorted(strike_map)); vs=np.array([strike_map[k] for k in ks])
    p=np.interp(pg,ks,vs,left=0,right=0); sig=len(pg)*smooth
    return gaussian_filter1d(p,sig) if sig>0.3 else p
def vs3d_profiles(chain, spot, p_min, p_max, prev_chain=None, dt_hours=None, n_price=240, smooth=0.02):
    """Returns dict of all sign-free VS3D fields on price grid pg."""
    c=chain.dropna(subset=["strike","gamma"]).copy()
    c=c[(c["strike"]>=p_min)&(c["strike"]<=p_max)]
    pg=np.linspace(p_min,p_max,n_price)
    st=c["strike"].values; sign=np.where(c["type"].values=="call",1.0,-1.0)
    g=c["gamma"].fillna(0).values; oi=c["oi"].fillna(0).values; vol=c["volume"].fillna(0).values
    w=np.where(vol>0,vol,oi)
    gex=_vs3d_density(_vs3d_per(st,sign*g*w),pg,smooth)*100*spot      # net exposure (convention)
    mag=_vs3d_density(_vs3d_per(st,np.abs(g)*w),pg,smooth)*100*spot   # magnitude (sign-free walls)
    speed=np.gradient(gex,pg)                                         # ∂γ/∂spot
    out=dict(pg=pg,gex=gex,mag=mag,speed=speed,charm=None,color=None,charm_flips=[])
    if prev_chain is not None and dt_hours and dt_hours>0:
        pc=prev_chain.dropna(subset=["strike"]).copy()
        cj=c.set_index(["strike","type"]); pj=pc.set_index(["strike","type"])
        j=cj.join(pj[["gamma","delta","volume"]],rsuffix="_p")
        stj=cj.index.get_level_values(0).values
        signj=np.where(cj.index.get_level_values(1).values=="call",1.0,-1.0)
        volj=cj["volume"].fillna(0).values; oij=cj["oi"].fillna(0).values; wj=np.where(volj>0,volj,oij)
        ddel=(j["delta"]-j["delta_p"]).fillna(0).values/dt_hours
        dgam=(j["gamma"]-j["gamma_p"]).fillna(0).values/dt_hours
        out["charm"]=_vs3d_density(_vs3d_per(stj,signj*ddel*wj),pg,smooth)*100*spot
        out["color"]=_vs3d_density(_vs3d_per(stj,signj*dgam*wj),pg,smooth)*100*spot
        out["charm_flips"]=zero_crossings(pg,out["charm"])
    return out,c
def vs3d_straddle(c, spot):
    cc=c[c.type=="call"]; pp=c[c.type=="put"]
    if cc.empty or pp.empty: return None
    kc=cc.iloc[(cc.strike-spot).abs().argmin()]; kp=pp.iloc[(pp.strike-spot).abs().argmin()]
    cm=(kc.bid+kc.ask)/2 if kc.ask>0 else kc.bid; pm=(kp.bid+kp.ask)/2 if kp.ask>0 else kp.bid
    if cm<=0 or pm<=0: return None
    return float(cm+pm)
def vs3d_fishbone(c):
    sign=np.where(c["type"].values=="call",1.0,-1.0)
    net=pd.Series(sign*c["gamma"].fillna(0).values*np.where(c["volume"].fillna(0)>0,c["volume"].fillna(0),c["oi"].fillna(0)),
                  index=c["strike"].values).groupby(level=0).sum().sort_index()
    v=net.values
    return int(sum(1 for i in range(1,len(v)) if np.sign(v[i])!=np.sign(v[i-1]) and v[i]!=0))
def vs3d_absorption(c):
    d=c["delta"].abs().clip(0,1); rem=np.where(d>0.5,(1-d),d)
    return float((rem*c["oi"].fillna(0)*100).sum())
def vs3d_skew(c):
    cc=c[c.type=="call"].set_index("strike")["iv"]; pp=c[c.type=="put"].set_index("strike")["iv"]
    common=sorted(set(cc.index)&set(pp.index))
    return float(np.nanmean([pp[k]-cc[k] for k in common])) if common else float("nan")
def vs3d_timing(now):
    t=now.time()
    if t<dt.time(11,0): return "OPEN 9:30-11 · avoid charm (external flow)"
    if t<dt.time(13,0): return "MIDDAY 11-1 · charm building, not dominant"
    if t<dt.time(15,0): return "SWEET SPOT 1:30-3 · best charm signal"
    return "CLOSE 3-4 · gamma asymptotic, pin resolution"
def vs3d_vix_regime(v):
    if v is None: return "VIX n/a"
    if v<16: return f"VIX {v:.1f} LOW · charm rules, vanna negligible"
    if v<20: return f"VIX {v:.1f} MID · charm ok, watch vanna"
    return f"VIX {v:.1f} HIGH · vanna can dominate, size down"
def mag_cmap():
    return mcolors.LinearSegmentedColormap.from_list("mag",[(0,(0,0,0)),(0.5,(0.15,0.45,0.6)),(1,(0.55,0.9,1.0))])
def speed_cmap():
    return mcolors.LinearSegmentedColormap.from_list("spd",[(0,(0.5,0,0.4)),(0.5,(0,0,0)),(1,(0.4,0.9,0.4))])

# ═══════════════ VS3D-style FORWARD SIMULATION (price × time-of-day) ═══════════
# Each pixel (price P, time τ) = greek IF spot were P at time τ, from the CURRENT
# chain, advancing the clock and re-pricing with BS seeded by each strike's Barchart
# IV (anchors to real skew). Left of 'now' held flat (we don't re-sim the past);
# right of now = pure forward sim to 16:00. Real candles overlay up to now.
_FWD_MODELS=["1 naive OI","2 zero-open VOL","3 OI+VOL","4 dVOL","5 vol/OI"]
def _fwd_weight(c, model, prev_chain=None):
    oi=c["oi"].fillna(0).values.astype(float); vol=c["volume"].fillna(0).values.astype(float)
    if model=="1 naive OI":      return oi
    if model=="2 zero-open VOL": return vol
    if model=="3 OI+VOL":        return oi+vol
    if model=="5 vol/OI":        return np.divide(vol,oi,out=np.zeros_like(vol),where=oi>0)
    if model=="4 dVOL":
        if prev_chain is None: return vol*0.0
        pj=prev_chain.set_index(["strike","type"])["volume"]
        cj=c.set_index(["strike","type"])
        j=cj.join(pj.rename("vp"),how="left")
        return (cj["volume"].fillna(0).values - j["vp"].fillna(0).values).clip(0)
    return oi
def forward_sim_grid(chain, spot, exp, now, model, prev_chain=None, p_min=None, p_max=None,
                     n_price=160, n_time=80, window_pct=2.5):
    c=chain.dropna(subset=["strike","iv"]).copy()
    if p_min is None: p_min=spot*(1-window_pct/100)
    if p_max is None: p_max=spot*(1+window_pct/100)
    c=c[(c["strike"]>=p_min)&(c["strike"]<=p_max)]
    pg=np.linspace(p_min,p_max,n_price)
    open_=dt.datetime.combine(now.date(),dt.time(9,30)); close=dt.datetime.combine(now.date(),dt.time(16,0))
    taus=[open_+dt.timedelta(seconds=t) for t in np.linspace(0,(close-open_).total_seconds(),n_time)]
    K=c["strike"].values; iv=c["iv"].values; sgn=np.where(c["type"].values=="call",1.0,-1.0)
    w=_fwd_weight(c,model,prev_chain)
    Zg=np.zeros((n_price,n_time)); Zc=np.zeros((n_price,n_time))
    for j,tau in enumerate(taus):
        when=max(tau,now); T=_T_at(exp,when); Sg=pg[:,None]
        g=bs_gamma(Sg,K[None,:],T,iv[None,:]); ch=bs_charm(Sg,K[None,:],T,iv[None,:])
        Zg[:,j]=(g*sgn*w).sum(1)*100*pg; Zc[:,j]=(ch*sgn*w).sum(1)*100*pg
    Zg=gaussian_filter1d(Zg,1.2,axis=0); Zc=gaussian_filter1d(Zc,1.2,axis=0)
    return pg,Zg,Zc,[mdates.date2num(t) for t in taus]
def _fwd_norm(Z):
    sc=np.percentile(np.abs(Z),92) or 1.0; return np.clip(Z/sc,-1,1)



# ════════════════════════════ colors / labels ═══════════════════════════════
def gex_cmap():
    return mcolors.LinearSegmentedColormap.from_list("gex",
        [(0.0,(0.50,0,0)),(0.34,(0.86,0.06,0.06)),(0.47,(0.10,0,0)),
         (0.50,(0,0,0)),(0.53,(0,0.10,0)),(0.66,(0.10,0.74,0.18)),(1.0,(0.02,0.42,0.06))])
def charm_cmap():
    return mcolors.LinearSegmentedColormap.from_list("charm",
        [(0.0,(0.42,0.24,0)),(0.34,(0.86,0.58,0.02)),(0.47,(0.10,0.06,0)),
         (0.50,(0,0,0)),(0.53,(0,0.05,0.12)),(0.66,(0.12,0.52,0.95)),(1.0,(0.02,0.22,0.58))])
DARK="#0d1117";TXT="#c9d1d9";GRID="#222a35";WHITE="#e6edf3"
UP="#ffffff";DOWN="#000000";WICKFX=[pe.Stroke(linewidth=1.7,foreground="#6b7280"),pe.Normal()]
def _place_labels(ax, levels, p_min, p_max, x=0.012, min_gap=0.045, fs=9.5):
    levels=[L for L in levels if p_min<L["price"]<p_max]
    if not levels: return
    levels.sort(key=lambda L:L["price"]); ys=[(L["price"]-p_min)/(p_max-p_min) for L in levels]
    for i in range(1,len(ys)):
        if ys[i]-ys[i-1]<min_gap: ys[i]=ys[i-1]+min_gap
    over=ys[-1]-0.985
    if over>0: ys=[max(0.015,y-over) for y in ys]
    for L,y in zip(levels,ys):
        ax.text(x,y,L["text"],transform=ax.transAxes,color=L["color"],fontsize=fs,va="center",
                ha="left",fontfamily="monospace",zorder=10,fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3",facecolor="#0d1117",edgecolor=L["color"],alpha=0.92,linewidth=0.7))
def session_window():
    """Single source of truth for the x-axis: today's RTH session in EST,
    as matplotlib datenums. Every tab uses this identical window."""
    d=today_est()
    x0=mdates.date2num(dt.datetime.combine(d,dt.time(9,30)))
    x1=mdates.date2num(dt.datetime.combine(d,dt.time(16,0)))
    return x0,x1

def draw_candles(ax,bars,x0,x1,p_min,p_max):
    """The ONE candle drawer used by every tab. Bars plotted by real EST timestamp on
    the shared session x-axis. Outlined strongly so they read on top of the gradient."""
    if bars is None or not len(bars): return
    bn=np.array([mdates.date2num(t) for t in bars["t"]]); inwin=(bn>=x0)&(bn<=x1)
    if not inwin.sum(): return
    bw=inwin.sum()
    bvis=np.sort(bn[inwin])
    spacing=np.median(np.diff(bvis)) if bw>1 else (x1-x0)/390.0
    cwidth=spacing*0.8
    halo=[pe.Stroke(linewidth=2.4,foreground="#000000"),pe.Normal()]   # dark outline so it pops on any color
    for x,(_,r) in zip(bn[inwin],bars[inwin].iterrows()):
        up=r["c"]>=r["o"]; body=UP if up else DOWN
        # wick with dark halo
        ln,=ax.plot([x,x],[r["l"],r["h"]],color=body,lw=1.0,zorder=5); ln.set_path_effects(halo)
        # body: filled, with a contrasting outline (dark for up/white candle, light for down/black)
        edge="#000000" if up else "#cbd5e1"
        h=max(abs(r["c"]-r["o"]),(p_max-p_min)*0.0012)
        rect=plt.Rectangle((x-cwidth/2,min(r["o"],r["c"])),cwidth,h,
                           facecolor=body,edgecolor=edge,lw=0.6,zorder=6)
        rect.set_path_effects([pe.withStroke(linewidth=1.4,foreground="#000000" if up else "#1f2937")])
        ax.add_patch(rect)

def style_time_axis(ax,x0,x1):
    """Identical x-axis styling for every tab. Hard-locked to RTH 09:30–16:00 EST —
    autoscale off + zero margins so candle/track plots can't expand the window."""
    ax.set_autoscalex_on(False)
    ax.margins(x=0)
    ax.set_xlim(x0,x1); ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator())
    ax.tick_params(axis="x",colors=TXT,labelsize=8)

def _panel_meta():
    return [dict(key="g",cmap=gex_cmap(),label="Gamma",pos_c="#3fb950",neg_c="#f85149",
                 pos_l="Long γ (dealer)",neg_l="Short γ (dealer)",flip_c="#ffd166",flip_name="γ-flip",walls=True),
            dict(key="c",cmap=charm_cmap(),label="Charm",pos_c="#58a6ff",neg_c="#d29922",
                 pos_l="Call charm (+)",neg_l="Put charm (−)",flip_c="#9d4edd",flip_name="charm-flip",walls=False)]

def _finish(ax,P,pg,spot,p_min,p_max,prof_now,cw,pw,label_suffix,straddle,gps):
    levels=[]
    for fp in sorted(zero_crossings(pg,prof_now),key=lambda v:abs(v-spot))[:2]:
        ax.axhline(fp,color=P["flip_c"],lw=1.1,ls=(0,(6,3)),alpha=0.9,zorder=6)
        levels.append(dict(price=fp,text=f"{P['flip_name']} {fp:.0f}",color=P["flip_c"]))
    if P["walls"]:
        if cw: ax.axhline(cw,color="#3fb950",lw=1.0,ls=":",alpha=0.85,zorder=6); levels.append(dict(price=cw,text=f"Call wall {cw:.0f}",color="#3fb950"))
        if pw: ax.axhline(pw,color="#f85149",lw=1.0,ls=":",alpha=0.85,zorder=6); levels.append(dict(price=pw,text=f"Put wall {pw:.0f}",color="#f85149"))
    _place_labels(ax,levels,p_min,p_max)
    ax.axhline(spot,color=WHITE,lw=1.0,ls="--",alpha=0.85,zorder=5)
    ax.text(1.004,spot,f"{spot:.2f}",transform=ax.get_yaxis_transform(),color=WHITE,fontsize=9.5,
            va="center",ha="left",fontweight="bold",fontfamily="monospace")
    ax.set_ylim(p_min,p_max); ax.yaxis.set_label_position("right"); ax.yaxis.tick_right()
    # ── ALIGNMENT GUARD: price, gradient and axis must share ONE y-scale. If any
    #    gradient image's y-extent drifts from the price grid / ylim, scream on-chart
    #    (a silent y-offset would corrupt every price-vs-level read).
    bad=False
    for im in ax.images:
        ex=im.get_extent()
        if abs(ex[2]-pg[0])>1e-6 or abs(ex[3]-pg[-1])>1e-6: bad=True
    if abs(ax.get_ylim()[0]-pg[0])>1e-6 or abs(ax.get_ylim()[1]-pg[-1])>1e-6: bad=True
    if bad:
        ax.text(0.5,0.5,"⚠ Y-AXIS MISALIGNED — DO NOT TRADE OFF THIS",transform=ax.transAxes,
                color="#ff4d4d",fontsize=16,fontweight="bold",ha="center",va="center",zorder=20,
                bbox=dict(boxstyle="round,pad=0.5",facecolor="#0d1117",edgecolor="#ff4d4d",lw=2))
    ax.set_yticks(gps[(gps>p_min)&(gps<p_max)]); ax.tick_params(axis="y",colors=TXT,labelsize=9.5,length=0,pad=3)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.text(0.012,0.985,f"SPX · {P['label']}  [{label_suffix}]",transform=ax.transAxes,color=TXT,
            fontsize=10.5,va="top",ha="left",fontfamily="monospace",zorder=8,fontweight="bold")
    if straddle: ax.text(0.012,0.953,f"Straddle: ${straddle:.2f}",transform=ax.transAxes,color="#22c55e",
                         fontsize=9.5,va="top",ha="left",fontfamily="monospace",zorder=8)
    leg=ax.legend(handles=[mpatches.Patch(facecolor=P["pos_c"],label=P["pos_l"]),
                           mpatches.Patch(facecolor=P["neg_c"],label=P["neg_l"])],
                  loc="lower left",fontsize=9,framealpha=0.3,labelcolor=TXT,facecolor=DARK,edgecolor=GRID); leg.set_zorder(9)

def fig_projection(method,pg,Zg,Zc,times,jnow,cfull,spot,bars,straddle):
    p_min,p_max=pg[0],pg[-1]; x0,x1=session_window()
    cw,pw=compute_walls(cfull,spot)
    fig,(ag,ac)=plt.subplots(1,2,figsize=(16,8.6),facecolor=DARK); fig.subplots_adjust(wspace=0.0,left=0.01,right=0.945,top=0.93,bottom=0.06)
    step=max(5,round((p_max-p_min)/8/5)*5); gps=np.arange(round(p_min/step)*step,round(p_max/step)*step+step,step)
    for ax,P,Z in [(ag,_panel_meta()[0],Zg),(ac,_panel_meta()[1],Zc)]:
        ax.set_facecolor(DARK); cap=np.percentile(np.abs(Z),99) or 1.0
        ax.imshow(Z,origin="lower",extent=[x0,x1,p_min,p_max],aspect="auto",cmap=P["cmap"],vmin=-cap,vmax=cap,interpolation="bilinear",zorder=0)
        try: ax.contour(np.linspace(x0,x1,Z.shape[1]),pg,Z,levels=[0],colors=["white"],linewidths=[0.9],linestyles=["--"],zorder=3)
        except Exception: pass
        for gp in gps:
            if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
        draw_candles(ax,bars,x0,x1,p_min,p_max)
        _finish(ax,P,pg,spot,p_min,p_max,Z[:,jnow],cw,pw,method,straddle,gps)
        style_time_axis(ax,x0,x1)
    return fig

def fig_cone(pg,gex,chm,cfull,spot,bars,straddle):
    p_min,p_max=pg[0],pg[-1]; Vg,bg=field_from_profile(gex)
    charm_ok = chm is not None
    if charm_ok: Vc,bc=field_from_profile(chm)
    x0,x1=session_window(); cw,pw=compute_walls(cfull,spot)
    fig,(ag,ac)=plt.subplots(1,2,figsize=(16,8.6),facecolor=DARK); fig.subplots_adjust(wspace=0.0,left=0.01,right=0.945,top=0.93,bottom=0.06)
    step=max(5,round((p_max-p_min)/8/5)*5); gps=np.arange(round(p_min/step)*step,round(p_max/step)*step+step,step)
    panels=[(ag,_panel_meta()[0],Vg,bg,gex,True)]
    panels.append((ac,_panel_meta()[1],Vc,bc,chm,True) if charm_ok else (ac,_panel_meta()[1],None,None,None,False))
    for ax,P,V,b,prof,ok in panels:
        ax.set_facecolor(DARK)
        if ok:
            ax.imshow(V,origin="lower",extent=[x0,x1,p_min,p_max],aspect="auto",cmap=P["cmap"],vmin=-1,vmax=1,interpolation="bilinear",zorder=0)
            ax.plot(x0+b*(x1-x0),pg,color="white",lw=1.0,ls="--",zorder=3)
            for gp in gps:
                if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
            draw_candles(ax,bars,x0,x1,p_min,p_max)
            _finish(ax,P,pg,spot,p_min,p_max,prof,cw,pw,"cone",straddle,gps)
        else:
            # charm needs a prior snapshot to difference deltas — show placeholder
            for gp in gps:
                if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
            draw_candles(ax,bars,x0,x1,p_min,p_max)
            ax.set_ylim(p_min,p_max); ax.set_xlim(x0,x1)
            ax.text(0.5,0.5,"charm = Δdelta/Δt\nneeds a 2nd snapshot\n(take/await one more)",
                    transform=ax.transAxes,color="#8b949e",fontsize=13,ha="center",va="center",
                    fontfamily="monospace",zorder=8,
                    bbox=dict(boxstyle="round,pad=0.6",facecolor="#161b22",edgecolor="#30363d"))
            ax.text(0.012,0.985,f"SPX · {P['label']}  [cone]",transform=ax.transAxes,color=TXT,
                    fontsize=10.5,va="top",ha="left",fontfamily="monospace",zorder=8,fontweight="bold")
        style_time_axis(ax,x0,x1)
    return fig

def decay_surface(last, pg, t_now_dt, t_end_dt, n_time=90, smooth_p=1.4):
    """Project the CURRENT book forward by time-decay only: same strikes/weights/IV,
    T shrinks from now to the 0DTE close. Per-option expiry, so multi-expiry is handled
    (today's 0DTE sharpens hardest as T→0; later expiries stay flatter). Returns
    (future datenums, Zg, Zc) or (None,None,None) if nothing to project."""
    if last is None or len(last)==0 or t_now_dt>=t_end_dt: return None,None,None
    S=pg[:,None]; YR=365*24*3600
    ca=last[last["type"]=="call"]; pu=last[last["type"]=="put"]
    def arrs(df):
        es=df["expiry"].map(lambda e:dt.datetime.combine(
            dt.datetime.strptime(e,"%Y-%m-%d").date(),dt.time(16,0)).timestamp()).values
        return df["strike"].values,df["w"].values,df["iv"].values,es
    Kc,Wc,Vc,Ec=arrs(ca); Kp,Wp,Vp,Ep=arrs(pu)
    tms=[t_now_dt+k*(t_end_dt-t_now_dt)/(n_time-1) for k in range(n_time)]
    Zg=np.zeros((len(pg),n_time)); Zc=np.zeros_like(Zg)
    for j,t in enumerate(tms):
        ts=t.timestamp(); Tc=np.maximum(Ec-ts,60)/YR; Tp=np.maximum(Ep-ts,60)/YR
        Zg[:,j]=((bs_gamma(S,Kc[None,:],Tc[None,:],Vc[None,:])*Wc[None,:]).sum(1)
                -(bs_gamma(S,Kp[None,:],Tp[None,:],Vp[None,:])*Wp[None,:]).sum(1))*100*pg
        Zc[:,j]=((bs_charm(S,Kc[None,:],Tc[None,:],Vc[None,:])*Wc[None,:]).sum(1)
                -(bs_charm(S,Kp[None,:],Tp[None,:],Vp[None,:])*Wp[None,:]).sum(1))*100*pg
    if smooth_p>0:
        Zg=gaussian_filter1d(Zg,smooth_p,axis=0); Zc=gaussian_filter1d(Zc,smooth_p,axis=0)
    return np.array([mdates.date2num(t) for t in tms]),Zg,Zc

def fig_surface(mode,pg,Zg,Zc,times,last,spot,bars,straddle,cwalls=None,pwalls=None):
    p_min,p_max=pg[0],pg[-1]; x0,x1=session_window()
    tnum=np.array([mdates.date2num(t) for t in times])
    if len(tnum)==1:                       # single snapshot → give it a little width
        tnum=np.array([tnum[0],tnum[0]+5/1440.0]); Zg=np.repeat(Zg,2,axis=1); Zc=np.repeat(Zc,2,axis=1)
        if cwalls is not None: cwalls=[cwalls[0],cwalls[0]]; pwalls=[pwalls[0],pwalls[0]]
    t_left,t_now=tnum[0],tnum[-1]          # recorded heatmap fills first snapshot → now
    # T-DECAY PROJECTION: current book re-evaluated at shrinking T, now → 0DTE close
    t_now_dt=times[-1] if len(times) else now_est()
    t_end_dt=dt.datetime.combine(today_est(),dt.time(16,0))
    dtnum,Zg_p,Zc_p=decay_surface(last,pg,t_now_dt,t_end_dt) if (last is not None and t_now<x1) else (None,None,None)
    fig,(ag,ac)=plt.subplots(1,2,figsize=(16,8.6),facecolor=DARK); fig.subplots_adjust(wspace=0.0,left=0.01,right=0.945,top=0.93,bottom=0.06)
    step=max(5,round((p_max-p_min)/8/5)*5); gps=np.arange(round(p_min/step)*step,round(p_max/step)*step+step,step)
    for ax,P,Z,Zp in [(ag,_panel_meta()[0],Zg,Zg_p),(ac,_panel_meta()[1],Zc,Zc_p)]:
        ax.set_facecolor(DARK)
        # shared color scale across recorded + projected so the seam is continuous
        allv=np.abs(Z) if Zp is None else np.abs(np.concatenate([Z,Zp],axis=1))
        cap=np.percentile(allv,99) or 1.0
        # 1) recorded positioning heatmap over REAL time (first snapshot → now)
        ax.imshow(Z,origin="lower",extent=[t_left,t_now,p_min,p_max],aspect="auto",cmap=P["cmap"],
                  vmin=-cap,vmax=cap,interpolation="bilinear",zorder=0)
        # 2) DECAY PROJECTION: current book at shrinking T, now → close (pockets sharpen as T→0)
        if Zp is not None:
            ax.imshow(Zp,origin="lower",extent=[t_now,x1,p_min,p_max],aspect="auto",cmap=P["cmap"],
                      vmin=-cap,vmax=cap,interpolation="bilinear",alpha=0.92,zorder=0)
            try: ax.contour(dtnum,pg,Zp,levels=[0],colors=["white"],linewidths=[0.8],linestyles=[(0,(2,2))],zorder=3)
            except Exception: pass
        # migrating zero-flip contour over recorded window
        try: ax.contour(np.linspace(t_left,t_now,Z.shape[1]),pg,Z,levels=[0],colors=["white"],
                        linewidths=[0.9],linestyles=["--"],zorder=3)
        except Exception: pass
        ax.axvline(t_now,color="#e6edf3",lw=1.0,ls="-",alpha=0.7,zorder=5)   # 'now' divider
        for gp in gps:
            if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
        # WALL MIGRATION TRACKS (gamma): recorded path; walls are strike levels → flat forward
        if P["walls"] and cwalls is not None and len(tnum)==len(cwalls):
            cwt=np.array(cwalls,float); pwt=np.array(pwalls,float)
            ax.plot(tnum,cwt,color="#3fb950",lw=1.4,ls=":",zorder=6)
            ax.plot(tnum,pwt,color="#f85149",lw=1.4,ls=":",zorder=6)
            ax.scatter(tnum,cwt,s=10,color="#3fb950",zorder=6); ax.scatter(tnum,pwt,s=10,color="#f85149",zorder=6)
            if t_now<x1:
                ax.plot([t_now,x1],[cwt[-1],cwt[-1]],color="#3fb950",lw=1.0,ls=":",alpha=0.5,zorder=6)
                ax.plot([t_now,x1],[pwt[-1],pwt[-1]],color="#f85149",lw=1.0,ls=":",alpha=0.5,zorder=6)
        draw_candles(ax,bars,x0,x1,p_min,p_max)
        cw,pw=(cwalls[-1],pwalls[-1]) if (cwalls is not None and len(cwalls)) else compute_walls(last,spot)
        _finish(ax,P,pg,spot,p_min,p_max,Z[:,-1],cw,pw,f"surface·{mode}",straddle,gps)
        style_time_axis(ax,x0,x1)
    return fig

# ════════════════════════════ bars ══════════════════════════════════════════
# 1-minute bars pulled FRESH from tvdatafeed on every run — no caching, no reuse.
# (Candles must always reflect the latest 1-min TradingView data.)
def fetch_bars_raw():
    from tvDatafeed import TvDatafeed, Interval
    tv=TvDatafeed()                      # no-login works for CAPITALCOM:SPX500
    # CAPITALCOM:SPX500 is the real S&P 500 index (~7400), correct scale, real volume.
    # (CAPITALCOM:SPX is a different ~68-handle instrument — do NOT use it.)
    for itv,n in ((Interval.in_1_minute,500),(Interval.in_5_minute,300),(Interval.in_15_minute,200)):
        try:
            df=tv.get_hist(symbol="SPX500",exchange="CAPITALCOM",interval=itv,n_bars=n)
            if df is not None and len(df)>3:
                df=df.reset_index().rename(columns={"datetime":"t","open":"o","high":"h","low":"l","close":"c"})
                # tvdatafeed returns NAIVE UTC timestamps (verified: last bar == UTC now).
                # Localize as UTC and convert to EST, DST-aware, then drop tz to stay naive-EST.
                t=pd.to_datetime(df["t"]).dt.tz_localize("UTC").dt.tz_convert(EST).dt.tz_localize(None)
                df["t"]=t
                # return the full pull; prep_bars selects today's session and cuts at 'now'.
                return df[["t","o","h","l","c"]].dropna().reset_index(drop=True)
        except Exception: pass
    return None
def prep_bars():
    """CAPITALCOM:SPX500 1-min bars (UTC→EST converted in fetch). Real index scale, NO
    scaling. Keep TODAY's RTH bars from 09:30 EST up to NOW (never into the future)."""
    bars=fetch_bars_raw()
    if bars is None or not len(bars): return None,"feed returned no bars"
    bars=bars.dropna(subset=["o","h","l","c"]).reset_index(drop=True)
    if bars.empty: return None,"feed returned no usable bars"
    now=now_est(); today=today_est()
    todays=bars[bars["t"].dt.date==today]
    if len(todays)>0:
        bars=todays; sess=today; stale=False
    else:
        last=bars["t"].dt.date.max(); bars=bars[bars["t"].dt.date==last]; sess=last; stale=True
    # RTH 09:30–16:00 EST, and never past 'now' (no future-stamped bars on the chart)
    keep=(bars["t"].dt.time>=dt.time(9,30))&(bars["t"].dt.time<=dt.time(16,0))
    if not stale: keep&=(bars["t"]<=now)
    bars=bars[keep].reset_index(drop=True)
    if not len(bars): return None,f"no RTH bars for {sess} yet"
    msg=(f"showing {sess} RTH ({len(bars)} bars, to {bars['t'].max():%H:%M} EST)"
         + (" — today not in feed yet, prior session" if stale else ""))
    return bars,msg

# ════════════════════════════ snapshot taking ═══════════════════════════════
def take_snapshot(num_expiries):
    s,h=init_session("$SPX"); spot=get_spot(s,h)
    exps,chain=discover_expiries(s,h,num_expiries)
    ts=now_est()
    st.session_state.snaps.append(dict(ts=ts,spot=spot,chain=chain,exps=exps))
    st.session_state.last_ts=ts
    return spot,exps

# ════════════════════════════ UI ════════════════════════════════════════════
if "snaps" not in st.session_state: st.session_state.snaps=[]
if "last_ts" not in st.session_state: st.session_state.last_ts=None

st.sidebar.title("vs3d · SPX 0DTE")
num_expiries=st.sidebar.slider("Expiries to aggregate",1,5,1)
window_pct=st.sidebar.slider("Price window ±%",1.0,5.0,2.5,0.5)/100.0
smooth_frac=st.sidebar.slider("Gradient smoothing",0.0,5.0,1.0,0.25,
    help="0 = raw per-strike detail (bumpy, like vols3d), higher = smoother density")/100.0
auto_on=st.sidebar.toggle("Auto-refresh (5 min)",value=True)
c1,c2=st.sidebar.columns(2)
force=c1.button("📸 Snapshot now",use_container_width=True)
if c2.button("🗑 Clear",use_container_width=True):
    st.session_state.snaps=[]; st.session_state.last_ts=None; st.rerun()
st.sidebar.caption("POC · snapshots in-memory (reset on app restart) · "
                   "sign = dealer calls+/puts− · volume unsigned")

# manual data refresh (clears bars cache + forces a fresh snapshot)
refresh=c2.button("🔄 Refresh data",use_container_width=True)
if refresh:
    st.cache_data.clear()

# auto-refresh: component rerun preserves session_state (a meta-refresh would wipe it).
# st.fragment(run_every=) is the dependency-free fallback if the package is absent.
_AUTOREFRESH_OK=False
if auto_on:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5*60*1000, key="auto5min")
        _AUTOREFRESH_OK=True
    except Exception:
        _AUTOREFRESH_OK=False

def _due():
    if not st.session_state.snaps: return True
    return (now_est()-st.session_state.last_ts).total_seconds() >= 5*60-5

if force or refresh or _due():
    with st.spinner("Taking chain snapshot…"):
        try: take_snapshot(num_expiries)
        except Exception as ex: st.error(f"Snapshot failed: {ex}")

if auto_on and not _AUTOREFRESH_OK:
    # Fallback that actually RE-RUNS THE WHOLE SCRIPT (so it re-pulls), without the
    # package. A JS timer reloads the tab every 5 min; session_state survives reloads
    # within the same browser session, so snapshots/charm history persist.
    st.warning("`streamlit-autorefresh` not installed — using a built-in 5-min reload. "
               "For the smoothest experience add `streamlit-autorefresh` to requirements.txt.",icon="⚠️")
    import streamlit.components.v1 as _components
    _components.html(
        "<script>setTimeout(function(){ window.parent.location.reload(); }, 300000);</script>",
        height=0)

snaps=st.session_state.snaps
if not snaps:
    st.info("No snapshot yet. Click 📸 Snapshot now in the sidebar."); st.stop()

# ── snapshot scrubber: view the book as of any recorded snapshot ─────────────
st.sidebar.markdown("---")
labels=[s["ts"].strftime("%H:%M:%S") for s in snaps]
if len(snaps)==1:
    sel_i=0; st.sidebar.caption(f"1 snapshot · {labels[0]} EST")
else:
    sel_label=st.sidebar.select_slider("View snapshot (EST)",options=labels,value=labels[-1])
    sel_i=labels.index(sel_label)
if sel_i!=len(snaps)-1:
    st.sidebar.info(f"Viewing #{sel_i+1}/{len(snaps)} — not the latest.")

latest=snaps[sel_i]; spot=latest["spot"]; exps=latest["exps"]
sel_ts=latest["ts"]
exp_date=dt.datetime.strptime(exps[0],"%Y-%m-%d").date()
bars,bars_msg=prep_bars()

# Y-AXIS = spot ± window_pct, FULL STOP. Bars never influence the range, so no
# stray feed value can ever collapse or blow out the axis. Widen the window % in
# the sidebar if price runs off-screen.
lo=spot*(1-window_pct); hi=spot*(1+window_pct)
pad=(hi-lo)*0.05; p_min,p_max=lo-pad,hi+pad

straddle=None
try:
    c0=latest["chain"]; c0=c0[c0["expiry"]==exps[0]]
    k=c0.loc[(c0["strike"]-spot).abs().idxmin(),"strike"]
    cc=c0[(c0["strike"]==k)&(c0["type"]=="call")]; pp=c0[(c0["strike"]==k)&(c0["type"]=="put")]
    if not cc.empty and not pp.empty:
        straddle=((cc["bid"].values[0]+cc["ask"].values[0])/2+(pp["bid"].values[0]+pp["ask"].values[0])/2)
except Exception: pass

m1,m2,m3,m4,m5=st.columns(5)
m1.metric("SPX spot",f"{spot:.2f}")
m2.metric("Straddle",f"${straddle:.2f}" if straddle else "—")
m3.metric("Expiry",exps[0]+(f" +{len(exps)-1}" if len(exps)>1 else ""))
m4.metric("Viewing snap",f"{sel_i+1}/{len(snaps)}")
m5.metric("Snapshot (EST)",sel_ts.strftime("%H:%M:%S"))
if bars is None:
    st.caption(f"Candles: none overlaid — {bars_msg}.")
else:
    st.caption(f"Candles: {bars_msg}.")

tab_cone,tab_land,tab_surf,tab_vs3d,tab_fwd=st.tabs(["🟢 Cone (single snapshot)",
                                    "📐 Landscape (forward projection)",
                                    "🕒 Intraday surface (snapshot history)",
                                    "🧭 VS3D (sign-free dashboard)",
                                    "🔮 Forward models (price×time sim)"])

with tab_cone:
    st.caption(f"x-axis = session clock · gamma = Barchart per-strike · charm = Δdelta/Δt · snapshot {sel_ts:%H:%M:%S} EST.")
    # previous snapshot (for empirical charm). None if viewing the first snapshot.
    prev_snap=snaps[sel_i-1] if sel_i>0 else None
    prev_chain=prev_snap["chain"] if prev_snap is not None else None
    dt_hours=((sel_ts-prev_snap["ts"]).total_seconds()/3600.0) if prev_snap is not None else None
    for w in ["volume","oi","oi_plus_flow"]:
        st.markdown(f"**Cone — weight: `{w}`**")
        try:
            pg,gex,chm,cf=cone_profiles(latest["chain"],spot,p_min,p_max,w,
                                        prev_chain=prev_chain,dt_hours=dt_hours,
                                        smooth_frac=smooth_frac)
            fig=fig_cone(pg,gex,chm,cf,spot,bars,straddle); st.pyplot(fig,use_container_width=True); plt.close(fig)
        except Exception as ex: st.error(f"cone[{w}] failed: {ex}")

    # ── DIAGNOSTICS ──────────────────────────────────────────────────────────
    with st.expander("🔧 Candle / bar diagnostics", expanded=True):
        x0,x1=session_window()
        st.write({
            "today_est()": str(today_est()),
            "session window x0..x1 (datenum)": [round(x0,5),round(x1,5)],
            "session window (clock)": [str(mdates.num2date(x0))[:19], str(mdates.num2date(x1))[:19]],
            "prep_bars msg": bars_msg,
            "bars is None": bars is None,
            "bars count (post prep_bars)": (0 if bars is None else int(len(bars))),
        })
        # raw feed, before prep_bars filtering
        try:
            raw=fetch_bars_raw()
            if raw is None or not len(raw):
                st.warning("fetch_bars_raw() returned no rows.")
            else:
                st.write({
                    "RAW feed rows": int(len(raw)),
                    "RAW dtypes o/h/l/c": [str(raw[c].dtype) for c in ["o","h","l","c"]],
                    "RAW date(s) present": sorted({str(d) for d in raw["t"].dt.date.unique()})[:6],
                    "RAW time min..max": [str(raw["t"].min()), str(raw["t"].max())],
                    "RAW close min..max": [round(float(raw["c"].min()),2), round(float(raw["c"].max()),2)],
                })
        except Exception as ex:
            st.error(f"fetch_bars_raw() raised: {ex}")
        # what draw_candles actually sees: how many bars land inside the x-window
        if bars is not None and len(bars):
            bn=np.array([mdates.date2num(t) for t in bars["t"]])
            inwin=(bn>=x0)&(bn<=x1)
            st.write({
                "bars datenum min..max": [round(float(bn.min()),5), round(float(bn.max()),5)],
                "bars CLOCK min..max": [str(bars["t"].min()), str(bars["t"].max())],
                "bars INSIDE session window (drawn)": int(inwin.sum()),
                "bars OUTSIDE window (skipped)": int((~inwin).sum()),
                "price window p_min..p_max": [round(p_min,2), round(p_max,2)],
                "bars high/low": [round(float(bars["h"].max()),2), round(float(bars["l"].min()),2)],
                "bars within price window": int(((bars["l"]>=p_min)&(bars["h"]<=p_max)).sum()),
            })
            if inwin.sum()==0:
                st.error("0 bars fall inside the session x-window → nothing to draw. "
                         "Likely a date/timezone mismatch between bar timestamps and today_est().")
        st.caption("If 'bars INSIDE session window' is 0 but RAW rows exist, it's a time-axis "
                   "mismatch (not contrast). If bars are far outside the price window, it's a scale issue.")

with tab_land:
    st.caption(f"x-axis = session clock · book at {sel_ts:%H:%M:%S} EST projected to the close "
               "as T decays (pockets sharpen rightward). Note: `volume` ≈ `flow_reset` on one pull.")
    for m in ["oi","volume","oi_plus_flow","flow_reset"]:
        st.markdown(f"**Projection — method: `{m}`**")
        try:
            pg,Zg,Zc,times,jnow,cf=build_projection(latest["chain"],spot,m,p_min,p_max)
            fig=fig_projection(m,pg,Zg,Zc,times,jnow,cf,spot,bars,straddle); st.pyplot(fig,use_container_width=True); plt.close(fig)
        except Exception as ex: st.error(f"projection[{m}] failed: {ex}")

with tab_surf:
    st.caption("x-axis = real recorded time. Built from your in-memory snapshot history — "
               "this is the only view that EVOLVES as flow lands. The slider trims the surface "
               "to snapshots up to the selected time.")
    surf_snaps=snaps[:sel_i+1]
    if len(surf_snaps)<2:
        st.warning(f"Only {len(surf_snaps)} snapshot up to {sel_ts:%H:%M:%S}. Let it run (or hit 📸) "
                   "to build history; the surface fills in as snapshots accumulate.")
    for m in ["oi_plus_flow","flow_from_open","interval_flow","cumulative"]:
        st.markdown(f"**Surface — mode: `{m}`**")
        try:
            wt="volume"
            pg,Zg,Zc,times,last,sp,cwalls,pwalls=build_time_surface(surf_snaps,m,p_min,p_max,weighting=wt)
            fig=fig_surface(m,pg,Zg,Zc,times,last,sp,bars,straddle,cwalls,pwalls); st.pyplot(fig,use_container_width=True); plt.close(fig)
        except Exception as ex: st.error(f"surface[{m}] failed: {ex}")

with tab_vs3d:
    st.caption("Everything replicable from FREE Barchart data, sign-free. The one thing we "
               "canNOT do — strike-level dealer long/short (anchor vs test) — is intentionally absent.")
    prev_snap=snaps[sel_i-1] if sel_i>0 else None
    prev_chain=prev_snap["chain"] if prev_snap is not None else None
    dt_hours=((sel_ts-prev_snap["ts"]).total_seconds()/3600.0) if prev_snap is not None else None
    try:
        vals,cc=vs3d_profiles(latest["chain"],spot,p_min,p_max,
                              prev_chain=prev_chain,dt_hours=dt_hours,smooth=smooth_frac)
        pg=vals["pg"]; x0,x1=session_window()
        # VIX for regime (best-effort; don't break the tab if it fails)
        vix_val=None
        try:
            _s,_h=init_session("$SPX"); vix_val=get_spot(_s,_h,"$VIX")
        except Exception: vix_val=None
        straddle_v=vs3d_straddle(cc,spot); fish=vs3d_fishbone(cc)
        absorb=vs3d_absorption(cc); skew=vs3d_skew(cc)
        decaying=None
        if prev_chain is not None:
            ps=vs3d_straddle(prev_chain.dropna(subset=["strike"]),prev_snap["spot"])
            if ps is not None and straddle_v is not None: decaying=straddle_v<ps

        def vs3d_panel(prof,cmap,title,signed=True,flips=None):
            fig,ax=plt.subplots(figsize=(8.2,4.4),facecolor=DARK); ax.set_facecolor(DARK)
            V,_b=field_from_profile(prof) if signed else (None,None)
            if signed:
                ax.imshow(V,origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=cmap,vmin=-1,vmax=1,interpolation="bilinear",zorder=0)
            else:
                sc=np.percentile(np.abs(prof),90) or 1.0
                b=gaussian_filter1d(0.5+0.5*np.tanh(prof/sc),2.0); xs=np.linspace(0,1,360)
                Vm=0.5+0.5*np.tanh(4.5*(b[:,None]-xs[None,:]))
                ax.imshow(Vm,origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=cmap,vmin=0,vmax=1,interpolation="bilinear",zorder=0)
            draw_candles(ax,bars,x0,x1,pg[0],pg[-1])
            ax.axhline(spot,color="white",ls="--",lw=1,zorder=7)
            for f in (flips or []):
                if pg[0]<f<pg[-1]: ax.axhline(f,color="#ff5555",lw=0.8,ls=":",zorder=6)
            ax.set_ylim(pg[0],pg[-1]); ax.set_title(title,color=TXT,fontsize=10,loc="left")
            style_time_axis(ax,x0,x1); return fig

        c1,c2=st.columns(2)
        with c1:
            st.pyplot(vs3d_panel(vals["gex"],gex_cmap(),"GAMMA net exposure (signed = convention)"),use_container_width=True)
            st.pyplot(vs3d_panel(vals["speed"],speed_cmap(),"SPEED ∂γ/∂spot · wall edges"),use_container_width=True)
            if vals["charm"] is not None:
                st.pyplot(vs3d_panel(vals["charm"],charm_cmap(),"CHARM ∂δ/∂t (empirical) · dotted = flips",flips=vals["charm_flips"]),use_container_width=True)
            else:
                st.info("CHARM needs a 2nd snapshot — fills in next refresh.")
        with c2:
            st.pyplot(vs3d_panel(vals["mag"],mag_cmap(),"|GAMMA| magnitude · walls/pins (sign-free)",signed=False),use_container_width=True)
            if vals["color"] is not None:
                st.pyplot(vs3d_panel(vals["color"],gex_cmap(),"COLOR ∂γ/∂t · profile drift"),use_container_width=True)
            else:
                st.info("COLOR needs a 2nd snapshot — fills in next refresh.")
            # signals block
            rng=f"{spot-straddle_v:.0f} — {spot+straddle_v:.0f}" if straddle_v else "n/a"
            dec=("YES — charm valid" if decaying else ("NO — charm SUSPECT" if decaying is not None else "need 2nd snapshot"))
            fishtxt="CLEAN, trade" if fish<=4 else ("MESSY, size down" if fish<=8 else "FISHBONE, sit out")
            st.markdown(f"""**Signals**
- {vs3d_timing(sel_ts)}
- {vs3d_vix_regime(vix_val)}
- **Straddle** {('$%.2f'%straddle_v) if straddle_v else 'n/a'} · expected range **{rng}**
- **Decaying?** {dec}  *(snake-oil gate: charm only leads if straddle is falling)*
- **Fishbone** {fish} sign-flips → **{fishtxt}**
- **Gamma absorption** {absorb:,.0f} fut-equiv remaining hedge
- **Skew** (put−call IV) {skew:+.3f} → {'put-skew' if (skew==skew and skew>0) else 'call-skew'}
- **Charm flips** {', '.join(f'{x:.0f}' for x in vals['charm_flips']) if vals['charm_flips'] else 'pending'}
""")
    except Exception as ex:
        import traceback; st.error(f"VS3D dashboard failed: {ex}"); st.code(traceback.format_exc())

with tab_fwd:
    st.caption("VS3D-style FORWARD SIMULATION. Each pixel (price × time-of-day) = the greek "
               "IF spot were there at that time — from the CURRENT chain, clock advanced, BS "
               "re-priced with each strike's Barchart IV. Blue line = now (left actual, right simulated). "
               "Charm colored by hedging effect: red = dealers sell as time passes, green = buy.")
    now_naive=sel_ts.replace(tzinfo=None) if getattr(sel_ts,'tzinfo',None) else sel_ts
    exp_use=(latest.get("exps") or [None])[0]
    if not exp_use:
        st.warning("No expiry available on the latest snapshot yet.")
    else:
        prev_snap=snaps[sel_i-1] if sel_i>0 else None
        prev_chain=prev_snap["chain"] if prev_snap is not None else None
        x0,x1=session_window()
        for m in _FWD_MODELS:
            st.markdown(f"**Forward — model: `{m}`**"
                        + ("  ·  ⚠️ forward-sim weak (defined by past change)" if m in ("4 dVOL","5 vol/OI") else ""))
            try:
                pg,Zg,Zc,taus=forward_sim_grid(latest["chain"],spot,exp_use,now_naive,m,prev_chain=prev_chain,
                                               p_min=p_min,p_max=p_max)
                fig,(ag,ac)=plt.subplots(1,2,figsize=(16,5.2),facecolor=DARK)
                ag.imshow(_fwd_norm(Zg),origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=gex_cmap(),vmin=-1,vmax=1,interpolation="bilinear",zorder=0)
                ac.imshow(_fwd_norm(-Zc),origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=gex_cmap(),vmin=-1,vmax=1,interpolation="bilinear",zorder=0)
                nowx=mdates.date2num(now_naive)
                for a,ttl in [(ag,f"GAMMA · {m}"),(ac,f"CHARM · {m} (red=sell / green=buy)")]:
                    a.set_facecolor(DARK); draw_candles(a,bars,x0,x1,pg[0],pg[-1])
                    a.axhline(spot,color="white",ls="--",lw=1,zorder=7)
                    a.axvline(nowx,color="#3399dd",ls=":",lw=1.2,zorder=7)
                    a.set_ylim(pg[0],pg[-1]); a.set_title(ttl,color=TXT,fontsize=10,loc="left")
                    style_time_axis(a,x0,x1)
                ag.set_ylabel("price",color="#777",fontsize=8)
                st.pyplot(fig,use_container_width=True); plt.close(fig)
            except Exception as ex:
                import traceback; st.error(f"forward[{m}] failed: {ex}"); st.code(traceback.format_exc())
