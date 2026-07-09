#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════════════════════
# gbt_diagnostic_colab.py — EXPERIMENTAL FEEDS DIAGNOSTIC LOOP (Colab edition)
# ══════════════════════════════════════════════════════════════════════════════
# Purpose: evaluate every GBT feed we are NOT yet using in vs3dGBT, live, on a
# 9-panel dark dashboard, so tonight's "what earns a slot" decision is made from
# pictures instead of guesses. Touches NOTHING in the deployed apps.
#
# HOW TO RUN (3 steps):
#   1) In a separate Colab cell first (the ORIGINAL tvdatafeed PyPI package is
#      dead — the apps use the rongardF fork, and so does this script):
#          !pip install --quiet git+https://github.com/rongardF/tvdatafeed
#      (requests / pandas / matplotlib are preinstalled)
#   2) Paste this whole file into ONE cell, put your token on the TOKEN line.
#      >>> DELETE THE TOKEN BEFORE SHARING THE NOTEBOOK <<<
#   3) Run. One dashboard every LOOP_MINUTES. Stop with the ■ button (clean exit).
#
# Budget: ~24 GBT calls/iteration, paced 1.5s apart (all inside one minute,
# documented VIP 30/min; identical repeats are server-cache hits = free).
# Panels are schema-DEFENSIVE: feeds we've never parsed (volatility_drift,
# iv_rank, dark_pool_levels) print their own columns on first contact —
# probe-first rule, baked in. A failing feed shows an error box, never kills
# the loop.
# ══════════════════════════════════════════════════════════════════════════════
TOKEN = "PASTE_YOUR_TOKEN_HERE"

LOOP_MINUTES = 5          # dashboard refresh cadence
MAX_ITERS    = 999        # safety ceiling
N_SIDE       = 6          # strikes cross-checked in panel 1 (each = 1 call)

import json, io, time, datetime as dt
import requests, pandas as pd, numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

TOKEN = TOKEN.strip()
if (not TOKEN) or ("PASTE" in TOKEN.upper()) or (" " in TOKEN):
    raise SystemExit(">>> Edit the TOKEN line first.")
BASE = "https://api.groupbuytrading.com/v1"
HDR  = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
DARK, GRID = "#0e1117", "#2a2f3a"
GREEN, RED, GOLD, BLUE, PURP = "#26a69a", "#ef5350", "#d9a90b", "#6f9bd1", "#c084fc"

def today_et():
    return (dt.datetime.utcnow() - dt.timedelta(hours=4)).strftime("%Y-%m-%d")

def prev_session(dstr):
    d = dt.datetime.strptime(dstr, "%Y-%m-%d") - dt.timedelta(days=1)
    while d.weekday() >= 5: d -= dt.timedelta(days=1)
    return d.strftime("%Y-%m-%d")

CALLS = {"n": 0}
def gbt(ep, payload):
    """CSV-envelope call. Returns (meta, df). Raises on hard failure.
    HARD RULE: never send snapshotTime, or startTime without endTime (502 bugs)."""
    assert "snapshotTime" not in payload, "snapshotTime is server-broken (502)"
    assert not ("startTime" in payload) ^ ("endTime" in payload), \
        "doc: startTime and endTime must be set together"
    CALLS["n"] += 1; time.sleep(1.5)   # ~22 calls/iter spread over ~35s → well under the 30/min budget
    r = requests.post(f"{BASE}/{ep}", headers=HDR, json=payload, timeout=45)
    if r.status_code == 429:
        time.sleep(8); r = requests.post(f"{BASE}/{ep}", headers=HDR, json=payload, timeout=45)
    if r.status_code != 200:
        raise RuntimeError(f"{ep} HTTP {r.status_code}: {r.text[:300]}")
    j = r.json(); raw = j.get("data", "") or ""
    meta, lines, i = {}, raw.split("\n"), 0
    while i < len(lines) and ("=" in lines[i] or lines[i].strip() == ""):
        s = lines[i].strip()
        if s and "=" in s:
            k, _, v = s.partition("="); meta[k.strip()] = v.strip()
        i += 1
    body = "\n".join(lines[i:]).strip()
    df = pd.read_csv(io.StringIO(body)) if body else pd.DataFrame()
    return meta, df

def gbt_try(ep, variants):
    """Try payload variants in order — the API's 422 text names missing params,
    so a failing run documents its own fix for the next iteration."""
    errs = []
    for p in variants:
        try: return gbt(ep, p)
        except Exception as ex: errs.append(str(ex)[:180])
    raise RuntimeError(" || ".join(errs))

def ms_to_et(ms):
    return dt.datetime.utcfromtimestamp(float(ms)/1000.0) - dt.timedelta(hours=4)

def style(ax, title):
    ax.set_facecolor(DARK); ax.set_title(title, color="#ddd", fontsize=8, loc="left")
    ax.tick_params(colors="#888", labelsize=6)
    for s in ax.spines.values(): s.set_color(GRID)

def fail(ax, title, ex):
    style(ax, title)
    ax.text(0.5, 0.5, f"feed error:\n{type(ex).__name__}: {str(ex)[:220]}",
            color=RED, fontsize=6, ha="center", va="center", wrap=True, transform=ax.transAxes)

def schema_note(ax, df, keep=6):
    """First-contact schema discovery: show the columns the feed actually has."""
    cols = list(df.columns)[:12]
    ax.text(0.02, 0.02, "cols: " + ", ".join(map(str, cols)),
            color="#777", fontsize=5.5, transform=ax.transAxes)

# ── optional tvdatafeed (same sources as the apps: SP:SPX candles, TVC:VIX) ───
TV = None
try:
    from tvDatafeed import TvDatafeed, Interval
    TV = TvDatafeed()                                     # nologin mode
    print("tvdatafeed ready (CAPITALCOM:SPX500 candles, TVC:VIX — project-standard sources)")
except Exception as _tvx:
    print("tvdatafeed unavailable →", type(_tvx).__name__,
          "| SPX falls back to GBT bars; VIX panel shows n/a."
          " (separate cell: !pip install git+https://github.com/rongardF/tvdatafeed — the fork; original PyPI package is dead)")

def tv_hist(symbol, exchange, bars=90):
    if TV is None: return None
    try:
        return TV.get_hist(symbol=symbol, exchange=exchange,
                           interval=Interval.in_5_minute, n_bars=bars)
    except Exception:
        return None

def side_net(df):
    """{type:(net customer initiative, total)} — SAME formula as vs3dGBT:
    net = (ABOVE_ASK+ASK) − (BID+BELOW_BID); dealer sign = −net/total."""
    out = {}
    for typ, g in df.groupby("contractType"):
        m = dict(zip(g["tradeSideCode"], g["value"]))
        net = (m.get("ABOVE_ASK",0)+m.get("ASK",0)) - (m.get("BID",0)+m.get("BELOW_BID",0))
        out[str(typ).lower()] = (float(net), float(sum(m.values())))
    return out

# ══════════════════════════════════════════════════════════════════════════════
def iteration(it):
    EXP = today_et(); YD = prev_session(EXP); CALLS["n"] = 0
    fig, axes = plt.subplots(3, 3, figsize=(16.5, 11.5))
    fig.patch.set_facecolor(DARK)
    fig.suptitle(f"GBT EXPERIMENTAL FEEDS · iter {it} · {dt.datetime.utcnow():%H:%M:%S} UTC"
                 f" · exp {EXP} · [tag] = VS3D-framework fit", color="#ccc", fontsize=10)
    A = axes.ravel()

    # spot + OI ground truth once (shared by several panels)
    spot, oi = None, pd.DataFrame()
    try:
        meta, _ = gbt("exposure_by_strike", {"greekMode":"GAMMA","representationMode":"RAW",
                      "ticker":"SPX","strikePriceRange":{"min":1,"max":2}})
        spot = float(meta.get("SPX.stockPrice") or 0) or None
        _, oi = gbt("open_interest_by_strike", {"ticker":"SPX","expirationDate":EXP})
    except Exception as ex:
        print("spot/OI fetch failed:", ex)
    lo, hi = (round(spot*0.98/5)*5, round(spot*1.02/5)*5) if spot else (7300, 7650)

    # 1 ── [VALIDATION] our side-stats dsign  vs  net_drift's official polarity ──
    ttl1 = "1· dsign CROSS-CHECK — side-stats (ours) vs net_drift (official)  [validates signed engine]"
    try:
        big = oi.assign(tot=oi["callOpenInterest"]+oi["putOpenInterest"])
        big = big[(big.strikePrice>=lo)&(big.strikePrice<=hi)].nlargest(N_SIDE,"tot")["strikePrice"].tolist()
        rows = []
        for k in big:
            _, sd = gbt("contract_trade_side_statistics",
                        {"dataMode":"VOLUME","tickers":["SPX"],"expirationDates":[EXP],
                         "strikePrices":[float(k)]})
            nt = side_net(sd)
            for typ,(n,t) in nt.items():
                if t>0: rows.append(dict(strike=k, typ=typ, ours=-n/t))
        ours = pd.DataFrame(rows)
        nd_rows=[]
        for k in big:                       # one call per strike — multi-strike aggregates (no strike col)
            try:
                _, nd1 = gbt("net_drift", {"tickers":["SPX"],"expirationDates":[EXP],
                             "strikePrices":[float(k)],"aggregationPeriod":"FIVE_MINUTE"})
                row={"strikePrice":k}
                for cn in ("netCallVolume","netPutVolume"):
                    if cn in nd1.columns: row[cn]=float(nd1[cn].sum())
                nd_rows.append(row); _nd_cols=list(nd1.columns)
            except Exception: pass
        ndf=pd.DataFrame(nd_rows)
        ax = A[0]; style(ax, ttl1)
        if not ours.empty:
            for typ, col in (("call", GREEN), ("put", RED)):
                s = ours[ours.typ==typ]
                ax.barh(s.strike + (2 if typ=="call" else -2), s.ours, height=3.4,
                        color=col, alpha=.85, label=f"{typ} dsign (ours)")
            ax.axvline(0, color="#666", lw=.7); ax.legend(fontsize=6, facecolor=DARK, labelcolor="#ccc")
            ax.set_xlim(-1,1)
        agree = "n/a"
        if not ndf.empty:
            cum = ndf.set_index("strikePrice")
            hits = tot = 0
            for k in big:
                if k in cum.index:
                    for typ, cn in (("call","netCallVolume"),("put","netPutVolume")):
                        if cn in cum.columns and cn in cum.loc[[k]].dropna(axis=1).columns:
                            nd_sign = -np.sign(cum.loc[k, cn])       # dealer = minus customer
                            our = ours[(ours.strike==k)&(ours.typ==typ)]
                            if len(our) and nd_sign != 0:
                                tot += 1; hits += int(np.sign(our.iloc[0]["ours"]) == nd_sign)
            if tot: agree = f"{100*hits/tot:.0f}% ({hits}/{tot})"
        ax.text(.98,.02, f"sign agreement: {agree}", color=GOLD, fontsize=8,
                ha="right", transform=ax.transAxes)
        schema_note(ax, ndf)
        print(f"  [1] dsign vs net_drift agreement: {agree}")
    except Exception as ex: fail(A[0], ttl1, ex)

    # 2 ── [VS3D: vanna context / VIX-regime gate] ────────────────────────────
    ttl2 = "2· VANNA exposure by strike  [VS3D: vanna context — the regime gate's input]"
    try:
        _, vn = gbt("exposure_by_strike", {"greekMode":"VANNA","representationMode":"RAW",
                    "ticker":"SPX","expirationDates":[EXP],
                    "strikePriceRange":{"min":lo,"max":hi}})
        ax = A[1]; style(ax, ttl2)
        v = vn.assign(net=vn.get("callExposureSum",0)+vn.get("putExposureSum",0))
        ax.barh(v.strikePrice, v.net, height=3.4,
                color=[GREEN if x>=0 else RED for x in v.net], alpha=.85)
        if spot: ax.axhline(spot, color="w", ls="--", lw=.8)
        ax.axvline(0, color="#666", lw=.7); schema_note(ax, vn)
    except Exception as ex: fail(A[1], ttl2, ex)

    # 3 ── [VS3D: Decay ground truth] real dΓ/dt per strike ───────────────────
    ttl3 = "3· CALL/PUT COLOR (real dΓ/dt)  [VS3D: Decay view's ground truth]"
    try:
        _, cc = gbt("heat_map", {"dataMode":"CALL_COLOR","ticker":"SPX",
                    "expirationDates":[EXP],"strikePriceRange":{"min":lo,"max":hi}})
        _, pc = gbt("heat_map", {"dataMode":"PUT_COLOR","ticker":"SPX",
                    "expirationDates":[EXP],"strikePriceRange":{"min":lo,"max":hi}})
        ax = A[2]; style(ax, ttl3)
        vcol = [c for c in cc.columns if c not in ("strikePrice","ticker")][0]
        ax.plot(cc[vcol], cc.strikePrice, color=GREEN, lw=1.2, label="call color")
        ax.plot(pc[vcol], pc.strikePrice, color=RED, lw=1.2, label="put color")
        if spot: ax.axhline(spot, color="w", ls="--", lw=.8)
        ax.axvline(0, color="#666", lw=.7)
        ax.legend(fontsize=6, facecolor=DARK, labelcolor="#ccc"); schema_note(ax, cc)
    except Exception as ex: fail(A[2], ttl3, ex)

    # 4 ── [VS3D: regime + straddle honesty] IV vs realized, per minute ───────
    ttl4 = "4· volatility_drift — IV vs realized  [VS3D: regime / snake-oil check] (schema discovery)"
    try:
        _, vd = gbt_try("volatility_drift", [
            {"ticker": "SPX", "expirationDate": EXP},
            {"ticker": "SPX", "expirationDate": EXP, "aggregationPeriod": "FIVE_MINUTE"},
            {"tickers": ["SPX"], "expirationDates": [EXP], "aggregationPeriod": "FIVE_MINUTE"},
        ])
        ax = A[3]; style(ax, ttl4)
        if "timestamp" in vd.columns:
            t = vd["timestamp"].map(ms_to_et)
            num = [c for c in vd.select_dtypes("number").columns if c != "timestamp"][:4]
            for c, col in zip(num, (GOLD, BLUE, GREEN, PURP)):
                ax.plot(t, vd[c], lw=1.0, color=col, label=c[:18])
            ax.legend(fontsize=5.5, facecolor=DARK, labelcolor="#ccc")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        else:
            ax.text(.5,.5, f"{vd.shape[0]}x{vd.shape[1]} — see cols below",
                    color="#aaa", fontsize=7, ha="center", transform=ax.transAxes)
        schema_note(ax, vd)
    except Exception as ex: fail(A[3], ttl4, ex)

    # 5 ── [VS3D: fresh paper → FRESH GAMMA development] ──────────────────────
    ttl5 = "5· FRESH GAMMA — overnight ΔOI × Γ, $M per 1%  [VS3D: fresh-paper layer; OI ticks once/day]"
    try:
        _, oc = gbt("open_interest_change", {"tickers":["SPX"],"expirationDates":[EXP],
                    "size":14,"sortField":"CHANGE_IN_OPEN_INTEREST","sortDirection":"DESCENDING"})
        _, cg = gbt("heat_map", {"dataMode":"CALL_GAMMA","ticker":"SPX",
                    "expirationDates":[EXP],"strikePriceRange":{"min":lo,"max":hi}})
        _, pg2 = gbt("heat_map", {"dataMode":"PUT_GAMMA","ticker":"SPX",
                    "expirationDates":[EXP],"strikePriceRange":{"min":lo,"max":hi}})
        ax = A[4]; style(ax, ttl5)
        def _gmap(df):
            vcol=[c for c in df.columns if c not in ("strikePrice","ticker")][0]
            g=df.set_index("strikePrice")[vcol].astype(float)
            return (g/100.0 if len(g.dropna()) and g.abs().median()>1.0 else g).to_dict()
        GC, GP = _gmap(cg), _gmap(pg2)
        kc = [c for c in oc.columns if "strike" in c.lower()][:1]
        vc = [c for c in oc.columns if "change" in c.lower() and oc[c].dtype != object][:1]
        tc = [c for c in oc.columns if "contract" in c.lower() or c.lower()=="type"][:1]
        if kc: oc[kc[0]] = pd.to_numeric(oc[kc[0]], errors="coerce")
        if vc: oc[vc[0]] = pd.to_numeric(oc[vc[0]], errors="coerce")
        notes=[]
        if kc and vc and spot:
            oid = oi.set_index("strikePrice") if len(oi) else None
            for _, r in oc.dropna(subset=[kc[0], vc[0]]).iterrows():
                k=float(r[kc[0]]); d=float(r[vc[0]])
                typ=(str(r[tc[0]]).upper()[:1] if tc else "?")
                g=(GC if typ=="C" else GP).get(k)
                if g is None: continue
                v = d*g*100.0*spot*spot/1e4/1e6            # ΔOI × Γ → $M per 1%
                ax.barh(k, v, height=3.4, alpha=(.9 if d>=0 else .35),
                        color=(GREEN if typ=="C" else RED),
                        hatch=(None if d>=0 else "///"))
                if oid is not None and k in oid.index and len(notes)<4:
                    tot=float(oid.loc[k, "callOpenInterest" if typ=="C" else "putOpenInterest"] or 0)
                    if tot>0: notes.append(f"{k:g}{typ} {100*abs(d)/tot:.0f}% fresh")
            ax.axhline(spot, color="w", ls="--", lw=.8); ax.axvline(0, color="#666", lw=.7)
            ax.text(.98,.02,"solid = built overnight · hatched = unwound · color = leg",
                    color="#888", fontsize=5.5, ha="right", transform=ax.transAxes)
        schema_note(ax, oc)
        if notes: print("  [5] fresh fraction of standing OI:", " · ".join(notes),
                        "→ vGBT-0.6 idea: seed confidence × fresh-fraction")
    except Exception as ex: fail(A[4], ttl5, ex)

    # 6 ── [VS3D-adjacent: flow terrain] interval_map today ───────────────────
    ttl6 = "6· interval_map GAMMA — per-bucket FLOW surface  [flow-terrain; NOT book state]"
    try:
        _, im = gbt("interval_map", {"greekMode":"GAMMA","ticker":"SPX",
                    "aggregationPeriod":"FIFTEEN_MINUTE","expirationDate":EXP,
                    "minStrikePrice":lo,"maxStrikePrice":hi,"topN":30})
        ax = A[5]; style(ax, ttl6)
        im["net"] = im.get("callExposureSum",0) + im.get("putExposureSum",0)
        pv = im.pivot_table(index="strikePrice", columns="timestamp", values="net", aggfunc="sum")
        if pv.size:
            m = np.nanpercentile(np.abs(pv.values), 98) or 1.0
            ax.pcolormesh(range(pv.shape[1]), pv.index.values,
                          np.clip(pv.values, -m, m), cmap="RdYlGn", shading="auto")
            ax.set_xticks(range(0, pv.shape[1], max(1, pv.shape[1]//6)))
            ax.set_xticklabels([ms_to_et(pv.columns[i]).strftime("%H:%M")
                                for i in range(0, pv.shape[1], max(1, pv.shape[1]//6))], fontsize=5.5)
            if spot: ax.axhline(spot, color="w", ls="--", lw=.8)
    except Exception as ex: fail(A[5], ttl6, ex)

    # 7 ── [EXTRA — not in the VS3D guide] institutional S/R ──────────────────
    ttl7 = "7· dark_pool_levels SPY (×10 → SPX)  [EXTRA: outside the VS3D framework]"
    dp_levels = []
    try:
        _, dp = gbt_try("dark_pool_levels", [
            {"ticker": "SPY"},
            {"tickers": ["SPY"]},
            {"ticker": "SPY", "sessionDate": EXP},
        ])
        ax = A[6]; style(ax, ttl7)
        pcols = [c for c in dp.select_dtypes("number").columns if "price" in c.lower() or "level" in c.lower()]
        if pcols and len(dp):
            for _, r in dp.head(12).iterrows():
                lvl = float(r[pcols[0]]) * 10.0
                dp_levels.append(lvl)
                ax.axhline(lvl, color=PURP, lw=.9, alpha=.7)
                ax.text(.01, lvl, f"{lvl:.0f}", color=PURP, fontsize=6, va="bottom",
                        transform=ax.get_yaxis_transform())
            if spot: ax.axhline(spot, color="w", ls="--", lw=.9)
            ax.set_ylim(min(dp_levels+[spot or 1e9])*0.998, max(dp_levels+[spot or 0])*1.002)
        else:
            ax.text(.5,.5,"no numeric price column — see schema", color="#aaa",
                    fontsize=7, ha="center", transform=ax.transAxes)
        schema_note(ax, dp)
    except Exception as ex: fail(A[6], ttl7, ex)

    # 8 ── [anchor] SPX candles (tvdatafeed SP:SPX; fallback GBT bars) ─────────
    ttl8 = "8· SPX500 5-min (CAPITALCOM via tvdatafeed; fallback GBT bars) + GBT spot + dark-pool ×10"
    try:
        ax = A[7]; style(ax, ttl8)
        bars = tv_hist("SPX500", "CAPITALCOM")   # project standard — NOT SP:SPX, NOT CAPITALCOM:SPX (a ~68-handle instrument, wrong asset)
        if bars is not None and len(bars):
            t = bars.index; c = bars["close"].values
        else:
            _, gb = gbt("stock_price_over_time", {"ticker":"SPX",
                        "aggregationPeriod":"FIVE_MINUTE","sessionDate":EXP})
            t = gb["timestamp"].map(ms_to_et); c = gb["closePrice"].values
        ax.plot(t, c, color=BLUE, lw=1.1)
        if spot: ax.axhline(spot, color="w", ls="--", lw=.8, label=f"GBT spot {spot:.2f}")
        for lvl in dp_levels[:8]: ax.axhline(lvl, color=PURP, lw=.6, alpha=.5)
        ax.legend(fontsize=6, facecolor=DARK, labelcolor="#ccc")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    except Exception as ex: fail(A[7], ttl8, ex)

    # 9 ── [VS3D: vol regime] VIX (TVC) + iv_rank ─────────────────────────────
    ttl9 = "9· VIX (TVC via tvdatafeed) + iv_rank  [VS3D: regime gate context]"
    try:
        ax = A[8]; style(ax, ttl9)
        vb = tv_hist("VIX", "TVC")
        if vb is not None and len(vb):
            ax.plot(vb.index, vb["close"], color=GOLD, lw=1.1, label="VIX (TVC)")
            ax.legend(fontsize=6, facecolor=DARK, labelcolor="#ccc")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        else:
            ax.text(.5,.6,"VIX n/a (tvdatafeed missing)", color="#aaa", fontsize=7,
                    ha="center", transform=ax.transAxes)
        try:
            _, ir = gbt("iv_rank", {"tickers":["SPX"]})
            txt = " · ".join(f"{c}={ir.iloc[0][c]}" for c in list(ir.columns)[:4]) if len(ir) else "empty"
            ax.text(.02,.04, f"iv_rank: {txt}"[:110], color="#8fd", fontsize=6,
                    transform=ax.transAxes)
        except Exception as _ix:
            ax.text(.02,.04, f"iv_rank: {type(_ix).__name__}", color=RED, fontsize=6,
                    transform=ax.transAxes)
    except Exception as ex: fail(A[8], ttl9, ex)

    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fname = f"gbt_diag_{dt.datetime.utcnow():%H%M%S}.png"
    fig.savefig(fname, dpi=110, facecolor=DARK)
    plt.show(); plt.close(fig)
    print(f"  saved {fname} · GBT calls this iteration: {CALLS['n']} (paced ≤26/min)")

# ══════════════════════════════════════════════════════════════════════════════
print("#"*78)
print(f"# GBT DIAGNOSTIC LOOP — every {LOOP_MINUTES} min · Ctrl/■ to stop cleanly")
print("#"*78)
for it in range(1, MAX_ITERS + 1):
    try:
        iteration(it)
    except KeyboardInterrupt:
        print("\nstopped by user — done."); break
    except Exception as ex:
        print(f"iteration {it} failed whole: {type(ex).__name__}: {ex}")
    try:
        time.sleep(LOOP_MINUTES * 60)
    except KeyboardInterrupt:
        print("\nstopped by user — done."); break
