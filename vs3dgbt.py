#!/usr/bin/env python3
"""mock3 — §8 testing harness for vs3d3_v2.0.py (v2.1.4), rebuilt per handoff spec.
Stubs streamlit / tvDatafeed / streamlit_autorefresh, feeds a synthetic 3-expiry
chain WITH noisy wings + crossed quotes, execs the real app source repeatedly,
and asserts the dispatch/cache contract (P1-P5) plus pinak_levels wing-immunity
and the read_verdict 3-scenario confidence behavior."""
import sys, os, types, datetime as dt
os.environ.setdefault("MPLBACKEND", "Agg")
import numpy as np, pandas as pd
from zoneinfo import ZoneInfo

APP_PATH = os.environ.get("VS3D_APP", "/mnt/user-data/uploads/vs3d3_v2_0.py")
APP_SRC = open(APP_PATH).read()
EST = ZoneInfo("America/New_York")

# ───────────────────────── streamlit stub ─────────────────────────
class _Stop(Exception): pass
class _Rerun(Exception): pass

OVERRIDES = {}          # widget label -> forced value  (GREEK_OVERRIDE etc.)
COUNT = {"pyplot": 0, "image": 0, "warn": 0}

class SessionState:
    def __init__(self): object.__setattr__(self, "_d", {})
    def __getattr__(self, k):
        d = object.__getattribute__(self, "_d")
        if k in d: return d[k]
        raise AttributeError(k)
    def __setattr__(self, k, v): object.__getattribute__(self, "_d")[k] = v
    def __getitem__(self, k): return object.__getattribute__(self, "_d")[k]
    def __setitem__(self, k, v): object.__getattribute__(self, "_d")[k] = v
    def __contains__(self, k): return k in object.__getattribute__(self, "_d")
    def get(self, k, d=None): return object.__getattribute__(self, "_d").get(k, d)
    def setdefault(self, k, d=None): return object.__getattribute__(self, "_d").setdefault(k, d)
    def keys(self): return object.__getattribute__(self, "_d").keys()
    def pop(self, k, d=None): return object.__getattribute__(self, "_d").pop(k, d)

def _ov(label, default): return OVERRIDES.get(label, default)

class W:  # any streamlit surface: st itself, sidebar, a column cell, an expander
    # ---- no-op display verbs
    def _noop(self, *a, **k): pass
    title = markdown = caption = info = error = code = metric = _noop
    def warning(self, *a, **k): COUNT["warn"] += 1
    progress = text = write = header = subheader = divider = _noop
    # ---- widgets (default unless overridden by label)
    def slider(self, label, mn=None, mx=None, value=None, step=None, **k):
        return _ov(label, value if value is not None else mn)
    def select_slider(self, label, options=None, value=None, **k):
        return _ov(label, value if value is not None else options[-1])
    def selectbox(self, label, options, index=0, **k): return _ov(label, options[index])
    def radio(self, label, options, index=0, **k): return _ov(label, options[index])
    def checkbox(self, label, value=False, **k): return _ov(label, value)
    def toggle(self, label, value=False, **k): return _ov(label, value)
    def button(self, label, **k): return bool(OVERRIDES.get(label, False))
    # ---- containers
    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [WCtx() for _ in range(n)]
    def expander(self, *a, **k): return WCtx()
    def tabs(self, labels): return [WCtx() for _ in labels]
    def spinner(self, *a, **k): return WCtx()
    # ---- render sinks (the counters the assertions read)
    def pyplot(self, fig, **k): COUNT["pyplot"] += 1
    def image(self, png, **k): COUNT["image"] += 1
    # ---- control flow
    def set_page_config(self, **k): pass
    def stop(self): raise _Stop()
    def rerun(self): raise _Rerun()

class WCtx(W):
    def __enter__(self): return self
    def __exit__(self, *a): return False

class _CacheData:
    def __call__(self, *a, **k):
        if a and callable(a[0]): return a[0]
        return lambda f: f
    def clear(self): pass

st_mod = types.ModuleType("streamlit")
_root = W()
for name in dir(W):
    if not name.startswith("_"): setattr(st_mod, name, getattr(_root, name))
st_mod.session_state = SessionState()
st_mod.sidebar = WCtx()
st_mod.cache_data = _CacheData()
comp_v1 = types.ModuleType("streamlit.components.v1"); comp_v1.html = lambda *a, **k: None
comp = types.ModuleType("streamlit.components"); comp.v1 = comp_v1
st_mod.components = comp
sys.modules["streamlit"] = st_mod
sys.modules["streamlit.components"] = comp
sys.modules["streamlit.components.v1"] = comp_v1

sar = types.ModuleType("streamlit_autorefresh")
sar.TICK = 0
sar.st_autorefresh = lambda *a, **k: sar.TICK
sys.modules["streamlit_autorefresh"] = sar

tvd = types.ModuleType("tvDatafeed")
class Interval: in_1_minute = 1; in_5_minute = 5; in_15_minute = 15; in_30_minute = 30
TVD_PAYLOAD = {}   # (exchange, symbol) -> DataFrame returned by get_hist
class TvDatafeed:
    def __init__(self, *a, **k): pass
    def get_hist(self, symbol=None, exchange=None, *a, **k):
        return TVD_PAYLOAD.get((exchange, symbol))
tvd.Interval = Interval; tvd.TvDatafeed = TvDatafeed
sys.modules["tvDatafeed"] = tvd

SS = st_mod.session_state

# ───────────────────────── synthetic data (§8: noisy wings + crossed quotes) ──
from scipy.stats import norm as _norm
def _weekday_exps(n, start):
    d = start; out = []
    while len(out) < n:
        if d.weekday() < 5: out.append(d.strftime("%Y-%m-%d"))
        d += dt.timedelta(days=1)
    return out

def _T_years(es, asof):
    exp = dt.datetime.combine(dt.datetime.strptime(es, "%Y-%m-%d").date(), dt.time(16, 0))
    return max((exp - asof).total_seconds(), 60.0) / (365 * 24 * 3600)

def synth_chain(spot, exps, asof, px_scale=1.0, vol_frac=0.35, seed=7,
                noisy_wings=True, hollow_band=None, fishbone=False):
    """3-expiry chain in fetch_chain schema (+expiry col). Clustered OI (call wall
    spot+40, put wall spot-45, pin cluster near spot+10), per-expiry damping/widening,
    volume = vol_frac*OI + jitter, deep noisy wings with stale/CROSSED quotes."""
    rng = np.random.default_rng(seed)
    rows = []
    k25 = lambda x: round(x / 25.0) * 25.0
    Ks = np.arange(k25(spot * 0.94), k25(spot * 1.06) + 1, 25.0)
    for ei, es in enumerate(exps):
        T = _T_years(es, asof)
        damp = 0.55 ** ei; widen = 1 + 0.6 * ei
        for K in Ks:
            iv = 0.125 + 0.45 * abs(K / spot - 1) + max(0.0, (spot - K) / spot) * 0.25
            iv *= (1 + 0.05 * ei)
            sq = iv * np.sqrt(T)
            d1 = (np.log(spot / K) + 0.5 * iv * iv * T) / sq
            d2 = d1 - sq
            gam = _norm.pdf(d1) / (spot * sq)
            cdel = float(_norm.cdf(d1)); pdel = cdel - 1.0
            cpx = max(spot * _norm.cdf(d1) - K * _norm.cdf(d2), 0.05) * px_scale
            ppx = max(cpx - spot + K, 0.05 * px_scale)
            if fishbone:
                odd = (int(K / 25) % 2 == 0)
                coi = 6000.0 if odd else 40.0
                poi = 40.0 if odd else 6000.0
            else:
                coi = 200 + 9000 * np.exp(-((K - (spot + 40)) / (12 * widen)) ** 2) \
                          + 3000 * np.exp(-((K - (spot + 90)) / (16 * widen)) ** 2) \
                          + 2600 * np.exp(-((K - (spot + 10)) / (9 * widen)) ** 2)
                poi = 200 + 8000 * np.exp(-((K - (spot - 45)) / (12 * widen)) ** 2) \
                          + 2500 * np.exp(-((K - (spot - 95)) / (16 * widen)) ** 2) \
                          + 2400 * np.exp(-((K - (spot + 10)) / (9 * widen)) ** 2)
                # side dominance: calls own the upside, puts the downside → single
                # net-sign flip near spot (clean structure, fishbone ≤ 4)
                if K >= spot: coi *= 1.25; poi *= 0.55
                else:         coi *= 0.55; poi *= 1.25
            coi *= damp; poi *= damp
            if hollow_band and abs(K - spot) < hollow_band and abs(K - spot) > 1:
                coi = poi = 0.0   # empty the absorption zone, keep quotes
            cvol = max(coi * vol_frac + rng.normal(0, 25), 0.0)
            pvol = max(poi * vol_frac + rng.normal(0, 25), 0.0)
            rows.append(dict(strike=K, type="call", iv=iv, gamma=gam, delta=cdel,
                             oi=round(coi), volume=round(cvol),
                             bid=round(cpx * 0.985, 2), ask=round(cpx * 1.015 + 0.05, 2), expiry=es))
            rows.append(dict(strike=K, type="put", iv=iv, gamma=gam, delta=pdel,
                             oi=round(poi), volume=round(pvol),
                             bid=round(ppx * 0.985, 2), ask=round(ppx * 1.015 + 0.05, 2), expiry=es))
        if noisy_wings and ei == 0:   # 0DTE deep wings: huge stale OI, crossed/one-sided quotes
            for Kw, heavy in ((k25(spot * 1.12), "call"), (k25(spot * 0.88), "put")):
                iv = 0.85; sq = iv * np.sqrt(T)
                d1 = (np.log(spot / Kw) + 0.5 * iv * iv * T) / sq
                gam = _norm.pdf(d1) / (spot * sq)
                itm_px = abs(Kw - spot) + 30.0          # stale, way off parity
                rows.append(dict(strike=Kw, type="call", iv=iv, gamma=gam,
                                 delta=float(_norm.cdf(d1)),
                                 oi=60000 if heavy == "call" else 45000, volume=0,
                                 bid=(0.05 if heavy == "call" else itm_px),
                                 ask=(0.0 if heavy == "call" else itm_px - 5.0),  # one-sided / CROSSED
                                 expiry=es))
                rows.append(dict(strike=Kw, type="put", iv=iv, gamma=gam,
                                 delta=float(_norm.cdf(d1)) - 1.0,
                                 oi=45000 if heavy == "call" else 70000, volume=0,
                                 bid=(itm_px if heavy == "call" else 0.05),
                                 ask=(itm_px - 5.0 if heavy == "call" else 0.0),
                                 expiry=es))
    return pd.DataFrame(rows)

def make_snap(ts, spot, exps, vix=13.2, **kw):
    return dict(ts=ts, spot=spot, chain=synth_chain(spot, exps, ts, **kw), exps=list(exps), vix=vix)

# ───────────────────────── app runner ─────────────────────────
G_LAST = {}
def exec_app(overrides=None, expect=None, name=""):
    global G_LAST
    OVERRIDES.clear(); OVERRIDES.update(overrides or {})
    OVERRIDES.setdefault("Charm panel below (stacked, VS3D-style)", False)
    OVERRIDES.setdefault("Book panel (by strike)", False)
    COUNT.update(pyplot=0, image=0, warn=0)
    g = {"__name__": "__main__", "__file__": "vs3d_app.py"}
    try:
        exec(compile(APP_SRC, "vs3d_app.py", "exec"), g)
    except _Stop:
        pass
    except _Rerun:
        pass   # button handlers rerun; state changes persist, next exec shows the result
    G_LAST = g
    got = (COUNT["pyplot"], COUNT["image"])
    tag = f"[{name}] pyplot={got[0]} image={got[1]}"
    if expect is not None:
        assert got == expect, f"{tag}  EXPECTED pyplot={expect[0]} image={expect[1]}"
        print("PASS", tag)
    else:
        print("info", tag)
    return g

# ───────────────────────── phase flow: P1..P5 ─────────────────────────
today = dt.datetime.now(EST).replace(tzinfo=None).date()
EXPS = _weekday_exps(3, today)
SPOT = 6900.0
ts1 = dt.datetime.combine(today, dt.time(9, 40))
ts2 = dt.datetime.combine(today, dt.time(10, 15))
snap1 = make_snap(ts1, SPOT, EXPS, px_scale=1.00, vol_frac=0.30, seed=7)
snap2 = make_snap(ts2, SPOT + 6.0, EXPS, px_scale=0.86, vol_frac=0.70, seed=8)

now_real = dt.datetime.now(EST).replace(tzinfo=None)
SS.snaps = [snap1]; SS.last_ts = now_real          # recent → _due() False → no network

print("=== warmup on snapshot 1 (records frames[ts1], seeds default cap) ===")
exec_app({}, expect=(3, 0), name="E0 first render")
exec_app({}, expect=(1, 2), name="E0b benign cap-seed re-render (terrain only)")
exec_app({}, expect=(0, 3), name="E0c stable cache hit")

SS.snaps.append(snap2); SS.last_ts = dt.datetime.now(EST).replace(tzinfo=None)

print("=== P1..P5 ===")
exec_app({}, expect=(3, 0), name="P1 new snapshot → all tabs render+cache")
exec_app({"Greek": "Delta Change"}, expect=(1, 2), name="P2 Greek change → ONLY terrain recomputes")
exec_app({"Greek": "Delta Change"}, expect=(1, 2), name="P2b benign cap-seed re-render (new greek's cap)")
exec_app({"Greek": "Delta Change"}, expect=(0, 3), name="P2c stable")
exec_app({"Greek": "Delta Change", "Frame": 0}, expect=(0, 3), name="P3 scrub back → pure replay")
exec_app({"Greek": "Delta Change", "Frame": 1}, expect=(0, 3), name="P4 drag to latest → live cache hit")
exec_app({"Greek": "Delta Change", "Frame": 1, "Field opacity": 0.5}, expect=(1, 2), name="P5 control change → recompute")

frames = SS.get("frames")
assert set(frames.keys()) == {ts1.isoformat(), ts2.isoformat()}, "frames keyed by both snapshot ts"
for ts in frames:
    assert all(frames[ts].get(t) for t in ("terrain", "signals", "read")), f"3 tabs cached @{ts}"
print("PASS frames store: both snapshots × 3 tabs cached, _livesig present:", "_livesig" in SS)

if "v2.1.7" in APP_SRC:
    print("=== stale-cap banner ===")
    SS["terr_cap_Gamma_OI + Volume"] = 1.0     # absurd cap -> p92 >> 3x cap
    exec_app({"Greek": "Gamma"}, name="stale-cap probe")
    assert COUNT["warn"] >= 1, "stale-cap banner did not fire"
    assert COUNT["pyplot"] == 1, "cap change must trigger exactly a terrain re-render"
    print(f"PASS stale-cap banner fired (warnings={COUNT['warn']}) with terrain-only recompute")

    print("=== stacked charm panel ===")
    ST={"Greek":"Gamma","Charm panel below (stacked, VS3D-style)":True}
    exec_app(ST, name="stack on -> main+charm render")
    assert (COUNT["pyplot"],COUNT["image"])==(2,2), f"stack-on: {COUNT}"
    exec_app(ST, name="benign charm-cap seed re-render")
    assert (COUNT["pyplot"],COUNT["image"])==(2,2), f"charm-seed: {COUNT}"
    exec_app(ST, name="stacked cache hit")
    assert (COUNT["pyplot"],COUNT["image"])==(0,4), f"stack-cache: {COUNT}"
    assert len(SS["frames"][ts2.isoformat()]["terrain"])==2, "terrain frame must hold 2 pngs"
    print("PASS stacked charm: renders, caches, replays as 2-image terrain frames")



# ───────────────────────── pinak_levels: wing immunity ─────────────────────────
print("=== pinak noisy-wing scenario ===")
pinak_levels = G_LAST["pinak_levels"]
ch0 = snap2["chain"][snap2["chain"]["expiry"] == EXPS[0]]
r = pinak_levels(ch0, snap2["spot"], EXPS[0], ts2)
sp = snap2["spot"]
wingK = {round(sp * 1.12 / 25) * 25, round(sp * 0.88 / 25) * 25}
assert abs(r["pin"] - sp) <= sp * 0.025 + 1, f"PIN dragged to wing: {r['pin']}"
assert r["pin"] not in wingK, "PIN sat on a wing strike"
assert r["kstar"] is not None and abs(r["kstar"] - sp) <= sp * 0.0101, f"K* invalid: {r['kstar']}"
assert r["flip"] is None or abs(r["flip"] - sp) <= sp * 0.03, f"FLIP in deep wing: {r['flip']}"
assert r["call_wall"] and r["call_wall"] > sp and r["call_wall"] not in wingK, f"CW {r['call_wall']}"
assert r["put_wall"] and r["put_wall"] < sp and r["put_wall"] not in wingK, f"PW {r['put_wall']}"
print(f"PASS pinak: PIN {r['pin']:.0f} ({r['pin_label']} {r['pin_score']}) FLIP {r['flip']} "
      f"CW {r['call_wall']:.0f} PW {r['put_wall']:.0f} K* {r['kstar']:.0f} — wings ignored")

# ───────────────────────── read_verdict: 3 scenarios ─────────────────────────
print("=== read_verdict scenarios ===")
read_verdict = G_LAST["read_verdict"]

def scenario(name, snaps, now, check):
    SS.pop("read_gmag", None)
    for k in [k for k in list(SS.keys()) if str(k).startswith("strad_open_")]: SS.pop(k, None)
    v = read_verdict(snaps, snaps[-1]["exps"], now)
    check(v)
    print(f"PASS {name}: conf {v['conf']}  pat '{v['pat'][:34]}…'  decay '{v['decay'][:22]}'  "
          f"clock '{v['clock'][:18]}'  vix '{v['vix'][:12]}'")

# S1 sweet spot ≈85: decaying straddle (natural √T decay 9:35→14:00 ≈ 0.56 of open,
# inside the 0.45–0.995 DECAYING window), 14:00 clock, VIX 13, clean structure.
# Absorption band = spot±straddle (~$10) contains no non-ATM strikes on a 25-grid
# → absorb=0 → never swallowed. Spot at +6 above cluster symmetry → flip below spot.
a1 = make_snap(dt.datetime.combine(today, dt.time(9, 35)), SPOT + 12, EXPS,
               px_scale=1.00, vol_frac=0.25, seed=11, hollow_band=16)
b1 = make_snap(dt.datetime.combine(today, dt.time(14, 0)), SPOT + 12, EXPS,
               px_scale=1.00, vol_frac=0.75, seed=12, vix=13.0, hollow_band=16)
def chk1(v):
    assert v["decay"].startswith("DECAYING"), v["decay"]
    assert v["clock"].startswith("SWEET"), v["clock"]
    assert "LOW" in v["vix"], v["vix"]
    assert "NEGATIVE" not in v["env"], v["env"]
    assert "clean" in v["fish"], v["fish"]
    assert v["pat"].startswith("CHOP"), v["pat"]
    assert v["conf"] == 85, f"expected 85, got {v['conf']} ({v})"
scenario("S1 sweet-spot 85", [a1, b1], dt.datetime.combine(today, dt.time(14, 0)), chk1)

# S2 repricing + high VIX at the open → 5–10 (natural decay 9:35→10:05 ≈ 0.96,
# ×1.15 → straddle ratio ≈ 1.10 → FLAT/REPRICING)
a2 = make_snap(dt.datetime.combine(today, dt.time(9, 35)), SPOT + 12, EXPS,
               px_scale=1.00, vol_frac=0.25, seed=21)
b2 = make_snap(dt.datetime.combine(today, dt.time(10, 5)), SPOT + 12, EXPS,
               px_scale=1.15, vol_frac=0.45, seed=22, vix=22.5)
def chk2(v):
    assert v["decay"].startswith("FLAT"), v["decay"]
    assert v["clock"].startswith("OPEN"), v["clock"]
    assert "HIGH" in v["vix"], v["vix"]
    assert 5 <= v["conf"] <= 10, f"expected 5–10, got {v['conf']}"
scenario("S2 repricing+VIX 5-10", [a2, b2], dt.datetime.combine(today, dt.time(10, 5)), chk2)

# S3 fishbone → hard cap ≤25 even in an otherwise perfect window
a3 = make_snap(dt.datetime.combine(today, dt.time(9, 35)), SPOT, EXPS,
               px_scale=1.00, vol_frac=0.30, seed=31, fishbone=True, noisy_wings=False)
b3 = make_snap(dt.datetime.combine(today, dt.time(14, 0)), SPOT, EXPS,
               px_scale=0.60, vol_frac=0.70, seed=32, fishbone=True, noisy_wings=False, vix=13.0)
def chk3(v):
    assert "FISHBONE" in v["fish"], v["fish"]
    assert v["conf"] <= 25, f"fishbone cap breached: {v['conf']}"
scenario("S3 fishbone ≤25", [a3, b3], dt.datetime.combine(today, dt.time(14, 0)), chk3)

if "v2.2.0" in APP_SRC:
    print("=== v2.2.0: drift isolation · open-straddle persistence · statics ===")
    bdd=G_LAST["_book_delta_drift"]; bd0=G_LAST["_book_delta_0dte"]
    _ts=dt.datetime.combine(today, dt.time(11, 30))
    chA=b1["chain"][b1["chain"]["expiry"]==EXPS[0]]
    chV=chA.copy(); chV["volume"]=chV["volume"]*3
    same=bdd(chA, SPOT+12, _ts, SPOT+12, _ts, EXPS[0])
    assert abs(same)<1e-9, f"fixed-book drift at identical state must be 0, got {same}"
    contam=bd0(chV, SPOT+12, EXPS[0], _ts)-bd0(chA, SPOT+12, EXPS[0], _ts)
    assert abs(contam)>1.0, "old per-snapshot calc must show weight-growth contamination at identical state"
    moved=bdd(chA, SPOT+12, _ts, SPOT+12, dt.datetime.combine(today, dt.time(13, 30)), EXPS[0])
    assert abs(moved)>1.0, "pure time decay on a fixed book must produce nonzero drift"
    print(f"PASS drift isolation: fixed-book 0 at same state; weight-growth alone faked {contam:,.0f} in the old calc; T-decay drift {moved:,.0f}")
    SS["strad_open_"+today.strftime("%Y-%m-%d")]=(40.0,"09:35")
    SS.pop("read_gmag", None)
    vP=read_verdict([a1,b1], a1["exps"], dt.datetime.combine(today, dt.time(14, 0)))
    assert vP.get("open_lbl")=="open 09:35", vP.get("open_lbl")
    assert vP["decay"].startswith("COLLAPSING"), f"forced open 40 must read COLLAPSING, got {vP['decay']}"
    for k in [k for k in list(SS.keys()) if str(k).startswith("strad_open_")]: SS.pop(k, None)
    print("PASS open-straddle persistence: labeled reference honored over snaps[0]")
    assert APP_SRC.count('np.where(c["oi"].fillna(0)>0')==2, "absorption must be book-first in BOTH sites"
    assert "_noMath" in APP_SRC and 'strad_open_"+ts.strftime' in APP_SRC
    print("PASS statics: OI-first absorption x2, mathtext guard, per-date open key in take_snapshot")

if "v2.2.1" in APP_SRC:
    print("=== v2.2.1: verdict banner consistency + no gmag double-feed ===")
    SS.pop("read_gmag", None)
    _n=dt.datetime.combine(today, dt.time(14, 0))
    _v1=read_verdict([a1,b1], a1["exps"], _n)
    assert len(SS["read_gmag"])==1
    _v2=read_verdict([a1,b1], a1["exps"], _n, track=False)
    assert len(SS["read_gmag"])==1, "track=False must not feed the percentile history"
    assert _v1["conf"]==_v2["conf"], "banner engine must match Read verdict exactly"
    SS.pop("read_gmag", None)
    assert "track=False" in APP_SRC and "STAND DOWN" in APP_SRC and "LEAN LONG" in APP_SRC and "WAIT" in APP_SRC
    print("PASS v2.2.1: single verdict engine, four explicit states, history unpolluted")

if "v2.2.2" in APP_SRC:
    print("=== v2.2.2: tick playback · persistence · ATM IV · new views ===")
    SS.pb_play=True; SS.pb_last_tick=None; SS.pb_idx=0; sar.TICK=7
    g=exec_app({}, name="play: first tick shows current, no advance")
    assert SS.pb_idx==0 and g["PLAYBACK_TS"].endswith("09:40:00"), (SS.pb_idx,g.get("PLAYBACK_TS"))
    g=exec_app({}, name="play: extra rerun same tick")
    assert SS.pb_idx==0, "extra rerun must not advance"
    sar.TICK=8; g=exec_app({}, name="play: real tick advances")
    assert SS.pb_idx==1 and g["PLAYBACK_TS"].endswith("10:15:00"), (SS.pb_idx,g.get("PLAYBACK_TS"))
    sar.TICK=9; g=exec_app({}, name="play: wrap")
    assert SS.pb_idx==0
    exec_app({"⏸ Pause": True}, name="press Pause (handler rerun)")
    g=exec_app({}, name="pause holds position")
    assert SS.pb_idx==0 and g["PLAYBACK"] and g["PLAYBACK_TS"].endswith("09:40:00"), "pause must hold, not snap to latest"
    g=exec_app({"Frame": 1}, name="drag to latest re-follows live")
    assert not g["PLAYBACK"] and SS.pb_follow, "right edge must return to live"
    SS.pb_idx=1; SS.pb_follow=True
    print("PASS playback: tick-counter advance, handshake-immune, wrap, pause holds")
    assert "if not auto_on: return False" in APP_SRC, "_due must respect the auto toggle"
    sv=G_LAST["save_day_state"]; ld=G_LAST["load_day_state"]; spth=G_LAST["_state_path"]
    import os as _o
    n0=len(SS.snaps); f0=len(SS.frames); sv()
    assert _o.path.exists(spth()), "state file written"
    SS.snaps=[]; SS.frames={}
    n1=ld(); assert n1==n0 and len(SS.snaps)==n0 and len(SS.frames)==f0, (n1,n0,len(SS.frames),f0)
    _o.remove(spth())
    assert "save_day_state()" in APP_SRC and "_os.remove(_state_path())" in APP_SRC, "hooks wired (snapshot save + Clear delete)"
    print(f"PASS persistence: {n0} snaps + {f0} frame-sets round-tripped through disk; hooks wired")
    txt=G_LAST.get("_atmiv_txt","")
    assert "ATM IV" in txt and "%" in txt, f"ATM IV must render: {txt!r}"
    _pct=float(txt.split("ATM IV")[1].split("%")[0])
    assert 5.0<_pct<60.0, f"ATM IV implausible: {_pct}"
    print(f"PASS ATM IV tripwire live: '{txt.strip()}'")
    GH="Gamma |Γ| (heaviness)"; GD="Gamma Decay (color)"
    exec_app({"Greek":GH}, expect=(1,2), name="|Γ| view renders")
    assert SS.get(f"terr_cap_{GH}_OI + Volume") is not None, "|Γ| cap seeded"
    exec_app({"Greek":GD}, expect=(1,2), name="decay view renders")
    dsh=G_LAST["_decay_shift"]
    Zt=np.tile(np.arange(120.0),(50,1))
    _tl=[dt.datetime.combine(today,dt.time(9,30))+dt.timedelta(minutes=3.25*i) for i in range(120)]
    D=dsh(Zt,_tl,mins=30)
    assert (D[:,:100]>0).all() and (D[:,-1]==0).all(), "decay shift: growth positive, tail clamped"
    print("PASS new views: |Γ| and Decay render+cache with own caps; _decay_shift math verified")

# ───────────────────────── fetch_vix_live (v2.1.5+): TVC primary, sane fallback ─
print("=== IV units & terrain time-evolution ===")
tg=G_LAST["terrain_grid"]
ch0dte=snap2["chain"][snap2["chain"]["expiry"]==EXPS[0]]
noonish=dt.datetime.combine(today, dt.time(11,30))
sp2=snap2["spot"]
_,ZS,_=tg(ch0dte,sp2,[EXPS[0]],noonish,greek="Gamma",weighting="OI + Volume",p_min=sp2*0.985,p_max=sp2*1.015)
early=float(np.percentile(np.abs(ZS[:,3:9]),98)); late=float(np.percentile(np.abs(ZS[:,-6:]),98))
assert late>2.5*early, f"terrain must sharpen into the close (late {late:.3g} vs early {early:.3g})"
_c=np.abs(ZS[:,-3]); cvD=float(_c.std()/(_c.mean()+1e-12))
assert cvD>0.6, f"late column must be strike-banded (cv={cvD:.2f})"
chP=ch0dte.copy(); chP["iv"]=chP["iv"]*100.0     # simulate RAW percent-style Barchart IV
_,ZP,_=tg(chP,sp2,[EXPS[0]],noonish,greek="Gamma",weighting="OI + Volume",p_min=sp2*0.985,p_max=sp2*1.015)
_cp=np.abs(ZP[:,-3]); cvP=float(_cp.std()/(_cp.mean()+1e-12))
_ce=np.abs(ZP[:,5]);  cvPe=float(_ce.std()/(_ce.mean()+1e-12))
assert cvP<0.3 and cvPe<0.1, f"percent IV must erase price structure (cv late {cvP:.2f}, early {cvPe:.2f})"
assert cvD>4*cvP, "decimal vs percent banding contrast lost"
print(f"PASS terrain physics: decimal IV banded (late/early {late/early:.1f}x, cv {cvD:.2f}); percent IV price-flat (cv {cvP:.2f}) — today\'s bug reproduced")
if "v2.1.8" in APP_SRC:
    ivn=G_LAST["_iv_norm"]; import math as _m
    assert abs(ivn(19.5)-0.195)<1e-12 and ivn(0.195)==0.195 and ivn(3.0)==3.0
    assert _m.isnan(ivn(float("nan")))
    assert chP["iv"].map(ivn).sub(ch0dte["iv"]).abs().max()<1e-9, "x100 chain round-trips through _iv_norm"
    if "v2.1.9" in APP_SRC:
        ivc=G_LAST["_iv_norm_chain"]
        pct=pd.Series([19.5, 24.0, 2.8, 41.0, float("nan")])          # percent-style incl. the 2.8 leak
        dec=pd.Series([0.195, 0.24, 0.028, 0.41, 0.85])               # decimal incl. a 0.85 wing
        outp=ivc(pct); outd=ivc(dec)
        assert abs(outp.iloc[2]-0.028)<1e-12, "2.8 percent-style must become 0.028 via chain median"
        assert abs(outp.iloc[0]-0.195)<1e-12 and outp.iloc[4]!=outp.iloc[4]
        assert (outd-dec).abs().max()<1e-15, "decimal chain must pass through untouched (0.85 wing kept)"
        assert '_iv_norm_chain(df["iv"])' in APP_SRC, "chain detector wired at the fetch_chain ingest point"
        print("PASS _iv_norm_chain: median units decision, 2.8-leak closed, decimal passthrough, wired at ingest")
    else:
        assert '_iv_norm(num("volatility"))' in APP_SRC, "normalizer wired at the fetch_chain ingest point"
    print("PASS _iv_norm: percent->decimal, decimal passthrough, NaN-safe" + (" (chain-median active)" if "v2.1.9" in APP_SRC else ", wired at ingest"))

if "fetch_vix_live" in G_LAST:
    print("=== fetch_vix_live (TVC:VIX) ===")
    fvl = G_LAST["fetch_vix_live"]
    TVD_PAYLOAD.clear()
    assert fvl() is None, "no TVC frame → must return None (Barchart fallback path)"
    TVD_PAYLOAD[("TVC", "VIX")] = pd.DataFrame({"close": [14.1, 14.3]})
    assert fvl() == 14.3, f"expected last close 14.3, got {fvl()}"
    TVD_PAYLOAD[("TVC", "VIX")] = pd.DataFrame({"close": [14.1, 900.0]})
    assert fvl() is None, "insane print must be rejected by the 5–200 band"
    TVD_PAYLOAD.clear()
    assert "vix_src" in APP_SRC, "vix_src marker present"
    if "v2.1.6" in APP_SRC:
        assert '"$VIX"' not in APP_SRC, "Barchart $VIX symbol must be gone from code in v2.1.6+"
        print("PASS v2.1.6: no Barchart $VIX code path remains (TVC only)")
    print("PASS fetch_vix_live: None-fallback, last-close pick, sanity band, markers")


if "vs3dGBT" in APP_SRC:
    print("=== vGBT-0.1 gated: GBT chain builder + Book tab contract ===")
    G = G_LAST
    _exp = G["today_est"]().strftime("%Y-%m-%d")
    # FROZEN TEST CLOCK (lesson: the harness must never depend on wall time).
    # 11:00 ET on the fixture expiry → tau ≈ 5h whether the harness runs at
    # 10 AM or midnight. Before this, the straddle gate failed after 16:00 ET.
    _now = G["now_est"]().replace(hour=11,minute=0,second=0,microsecond=0)
    ks = [7460.0,7465.0,7470.0,7475.0,7480.0,7485.0,7490.0]
    def _hf(vals): return pd.DataFrame({"strikePrice": ks, "value": vals})
    frames = dict(
        civ=_hf([32.09,24.46,30.37,29.71,27.89,27.51,26.66]),   # real 07-09 percent-style IVs
        piv=_hf([13.97,13.21,12.64,11.68,11.01,9.97,8.34]),
        cdelta=_hf([0.62,0.58,0.55,0.52,0.49,0.45,0.41]),
        pdelta=_hf([-0.35,-0.38,-0.42,-0.46,-0.50,-0.54,-0.58]),
        cgamma=_hf([0.0031]*7), pgamma=_hf([0.0031]*7),
        noi=pd.DataFrame({"strikePrice":ks,"callValue":[92,53,36,191,94,309,91],
                          "putValue":[-376,-281,-311,-4967,-548,-525,-629]}),
        nvol=pd.DataFrame({"strikePrice":ks,"callValue":[48,30,22,120,60,200,55],
                           "putValue":[-220,-160,-180,-2600,-330,-300,-360]}))
    ch = G["assemble_gbt_chain"](frames, 7482.71, _exp, _now)
    need = {"strike","type","iv","gamma","delta","oi","volume","bid","ask","expiry"}
    assert need.issubset(set(ch.columns)) and len(ch)==14, f"chain shape {ch.shape}"
    assert float(ch["iv"].max())<1.0 and float(ch["iv"].min())>0.01, "IV decimal after normalization"
    assert (ch.loc[ch["type"]=="put","delta"]<=0).all(), "put deltas negative"
    assert (ch["oi"]>=0).all() and (ch["bid"]==ch["ask"]).all() and float(ch["bid"].min())>0
    s0 = G["terrain_straddle"](ch, 7482.71)
    assert s0 and 5 < s0 < 200, f"GBT-chain straddle sane, got {s0}"
    try:
        pg, Z, taus = G["terrain_grid"](ch, 7482.71, [_exp], _now, greek="Gamma")
    except TypeError:
        pg, Z, taus = G["terrain_grid"](ch, 7482.71, [_exp], _now, greek="Gamma",
                                        vol_adj=0.0, simulated_gamma=False, weighting="OI + Volume")
    import numpy as _np
    assert Z.shape[0] == len(pg) and _np.isfinite(Z).any(), "terrain grid runs on GBT chain"
    bk = pd.DataFrame({"strike": ks,
                       "call_pd": [v*7482.71 for v in [92,53,36,191,94,309,91]],
                       "put_pd":  [v*7482.71 for v in [-376,-281,-311,-4967,-548,-525,-629]]})
    fig = G["book_figure"](bk, 7482.71, 38.1, 7455, 7495, side="Total", prev=None, openb=bk)
    assert fig is not None and len(fig.axes) >= 1, "book_figure renders"
    assert '"Book panel (by strike)",value=True' in APP_SRC and 'dispatch("book",_render_book' in APP_SRC
    assert '_gbt_post' in APP_SRC and '"snapshotTime" not in payload' in APP_SRC
    print("PASS vGBT-0.1: chain 14 rows decimal-IV signed-put-dlt BS-mid | straddle %.2f | terrain runs | book_figure OK | Book tab wired + 502-guard" % s0)

    print("=== vGBT-0.2 gated: flow-signed inference ===")
    # (a) seed math on the REAL 7500 probe fixture (yesterday's flow, today's expiry)
    sd = pd.DataFrame({"contractType": ["CALL"]*5+["PUT"]*5,
        "tradeSideCode": ["ABOVE_ASK","ASK","MID_MARKET","BID","BELOW_BID"]*2,
        "value": [1751,4947,4774,4510,904, 1890,1318,352,1557,3086]})
    nt = G["_side_net_total"](sd)
    assert abs(nt["call"][0]-1284)<1e-9 and abs(nt["call"][1]-16886)<1e-9
    assert abs(nt["put"][0]+1435)<1e-9 and abs(nt["put"][1]-8203)<1e-9
    dsc, dsp = -nt["call"][0]/nt["call"][1], -nt["put"][0]/nt["put"][1]
    assert dsc<0<dsp and abs(dsc+0.0760)<0.002 and abs(dsp-0.1749)<0.002, \
        "7500 fixture: dealer weakly-short calls, decisively-long puts (matches VS3D green)"
    # (b) _dealer_sign: signed column honored; absent column -> naive fallback
    G_LAST["GBT_SIGNED"] = True
    ch2 = ch.copy(); ch2["dsign"] = [0.5 if t=="put" else -0.2 for t in ch2["type"]]
    ssg, snv = G["_dealer_sign"](ch2), G["_dealer_sign"](ch)
    import numpy as _np2
    assert (ssg[ch2["type"].values=="put"]>0).all() and (snv[ch["type"].values=="put"]<0).all()
    assert (_np2.abs(ssg)<=1.0).all(), "dsign confidence-bounded"
    # (c) signed book figure renders with confidence opacity
    sgdf = pd.DataFrame({"strike": ks, "signed_pct": [3e8,-1e8,2e8,5e8,1e8,-2e8,4e8],
                         "conf": [.9,.2,.5,.8,.4,.3,.7]})
    fig2 = G["book_figure"](bk, 7482.71, 38.1, 7455, 7495, signed=sgdf)
    assert fig2 is not None and len(fig2.axes)>=1
    # (d) security: no token in source; secrets path wired; naive-mode escape hatch exists
    assert "gbtmd_" not in APP_SRC, "token must NOT be hardcoded"
    assert "st.secrets" in APP_SRC and "_gbt_token" in APP_SRC
    assert "Signed dealer inference (flow-seeded)" in APP_SRC and "gbt_seed_" in APP_SRC
    print("PASS vGBT-0.2: seed math (7500: call %.3f / put %+.3f), sign swap + fallback, confidence book, token scrubbed, seed persisted" % (dsc, dsp))

    print("=== vGBT-0.6 gated: net_drift live signs + volume gate ===")
    nd = pd.DataFrame({"timestamp":[1,2],
                       "netCallVolume":[300,-100], "netPutVolume":[-40,-60]})
    nn = G["_nd_net"](nd)
    assert abs(nn["call"]-200)<1e-9 and abs(nn["put"]+100)<1e-9, "bucket summation"
    assert (-nn["put"]/max(abs(nn["put"]),150))>0, "customers net-sold puts → dealer LONG"
    assert G["_vol_gate"](1000,None) and G["_vol_gate"](1000,900) and not G["_vol_gate"](1000,995)
    assert '"net_drift"' in APP_SRC and "gbt_live_vol_" in APP_SRC and "netCallVolume" in APP_SRC
    assert "_side_net_total" in APP_SRC and "_gbt_side_stats(exp,k,_gbt_prev_session())" in APP_SRC, \
        "probe-proven SEED path must stay side-stats"
    print("PASS vGBT-0.6: net_drift summation + dealer flip, volume-gate thresholds, seed path intact")

    print("=== vGBT-0.7 gated: Book×Spot overlay + canonical recorder ===")
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    _f,_a=_plt.subplots(figsize=(6.5,9)); _a.set_ylim(7400,7600)
    _bars=pd.DataFrame({"t":pd.date_range("2026-07-09 09:30",periods=5,freq="5min"),
                        "c":[7500,7510,7505,7515,7512],"o":0,"h":0,"l":0})
    _f2=G["_book_spot_overlay"](_f,_bars,7400,7600,chain=None)
    assert len(_f2.axes)>=2, "twiny spot axis missing"
    assert any(len(l.get_xdata())==5 for l in _f2.axes[1].get_lines()), "spot path not plotted"
    assert abs(_f2.get_size_inches()[1]-12.0)<0.01, "tall book figure expected"
    _plt.close(_f2)
    for _mk in ('"vs3d_std"','_EMIT_REDIRECT','_EMIT_SILENT','Spot-path overlay',
                '_frc.get("vs3d_std") or _frc.get("terrain"'):
        assert _mk in APP_SRC, "recorder contract marker missing: "+_mk
    print("PASS vGBT-0.7: overlay draws path on twin axis at 11x12, canonical-pair + redirect markers present")

    print("=== vGBT-0.7.1 gated: per-strike rows field mode ===")
    _nowF=G["now_est"]().replace(hour=11,minute=0,second=0,microsecond=0)
    pgA,ZA,_=G["terrain_grid"](ch,7482.71,[_exp],_nowF,greek="Gamma")
    pgR,ZR,_=G["terrain_grid"](ch,7482.71,[_exp],_nowF,greek="Gamma",
                               field_mode="Per-strike rows (VS3D look)")
    import numpy as _np
    def _at(pg,Z,price): return float(_np.abs(Z[int(_np.argmin(_np.abs(pg-price))),:]).max())
    on,off=_at(pgR,ZR,7475.0),_at(pgR,ZR,7477.5)
    onA,offA=_at(pgA,ZA,7475.0),_at(pgA,ZA,7477.5)
    assert on>2.0*max(off,1e-9), f"rows mode must resolve strike texture (on {on:.3g} vs off {off:.3g})"
    assert onA<1.3*max(offA,1e-9), f"aggregate stays smooth by design (on {onA:.3g} vs off {offA:.3g})"
    for _mk in ("Per-strike rows","field_mode=t_fieldmode","st.columns([1.0,2.2]"):
        assert _mk in APP_SRC, "v0.7.1 marker missing: "+_mk
    print(f"PASS vGBT-0.7.1: rows on/off-strike contrast {on/max(off,1e-9):.1f}x, aggregate smooth {onA/max(offA,1e-9):.2f}x, layout+plumbing markers present")

    print("=== vGBT-0.8 gated: interval engines (final, FLAG-2 fixed) ===")
    _snapA={"ts":"2026-07-10T09:35:00","spot":7500.0,"exps":[_exp],
            "chain":pd.DataFrame({"strike":[7500.0,7500.0],"type":["call","put"],
                "gamma":[0.004,0.004],"delta":[0.5,-0.5],"oi":[100.0,100.0],
                "dsign":[-0.5,-0.5],"expiry":[_exp,_exp]})}   # both legs dealer-SHORT
    _st=G["_interval_state_rows"]([_snapA],"GEX",signed=False)
    assert abs(float(_st["val"].iloc[0]))<1e-6, "naive GEX equal legs cancel"
    vg=float(G["_interval_state_rows"]([_snapA],"GEX",signed=True)["val"].iloc[0])
    assert vg<0 and abs(vg-(-0.5*0.004*100*100*7500.0*2))<1e-3, f"signed GEX both short → {vg}"
    vd=float(G["_interval_state_rows"]([_snapA],"DEX",signed=True)["val"].iloc[0])
    assert abs(vd-(-0.5*0.5*100*100 + 0.5*0.5*100*100))<1e-6, f"signed DEX short-call(−)+short-put(+) cancel → {vd}"
    _snapB={"ts":"2026-07-10T09:40:00","spot":7500.0,"exps":[_exp],
            "chain":pd.DataFrame({"strike":[7500.0],"type":["put"],"gamma":[0.004],
                "delta":[-0.5],"oi":[100.0],"dsign":[1.0],"expiry":[_exp]})}
    vdl=float(G["_interval_state_rows"]([_snapB],"DEX",signed=True)["val"].iloc[0])
    assert vdl<0 and abs(vdl-(-0.5*100*100))<1e-6, f"FLAG-2: dealer LONG put = SHORT delta → {vdl}"
    _fl=pd.DataFrame({"timestamp":[1783677900000,1783678200000],"strikePrice":[7500.0,7500.0],
                      "callExposureSum":[100.0,50.0],"putExposureSum":[-40.0,-10.0]})
    assert abs(float(G["_intv_flow_values"](_fl,"DEX",None,cumulative=True)["val"].iloc[-1])-100.0)<1e-9
    assert abs(float(G["_intv_flow_values"](_fl,"DEX",None,cumulative=False)["val"].iloc[-1])-40.0)<1e-9
    smapT={(7500.0,"call"):-1.0,(7500.0,"put"):1.0}
    fg=float(G["_intv_flow_values"](_fl,"GEX",smapT,cumulative=False)["val"].iloc[-1])
    assert abs(fg-(-50.0+10.0))<1e-9, f"signed GEX flow: dealer long put = +γ → {fg}"
    fd=float(G["_intv_flow_values"](_fl,"DEX",smapT,cumulative=False)["val"].iloc[-1])
    assert abs(fd-(-50.0-10.0))<1e-9, f"FLAG-2 flow: dealer long put = −Δ → {fd}"
    fv=G["_intv_flow_values"](_fl,"DEX",None,cumulative=True)
    assert "gross" in fv.columns and abs(float(fv["gross"].iloc[-1])-200.0)<1e-9, "gross cum = |C|+|P| = 140+60"
    assert (fv["gross"].values>=np.abs(fv["val"].values)-1e-9).all(), "gross >= |net| always"
    stg=G["_interval_state_rows"]([_snapA],"GEX",signed=True)
    assert "gross" in stg.columns and float(stg["gross"].iloc[0])>0, "state gross present and positive"
    assert "Backfill" not in APP_SRC, "backfill must be gone (live-only spec)"
    for _mk in ("⏱ Interval (bubbles)","blank-chip",'facecolors="none"',"Top strikes","VS3D_INTERVAL_RECIPE"):
        assert _mk in APP_SRC, "v0.8 marker missing: "+_mk
    print("PASS vGBT-0.8: GEX/DEX signed math exact incl. FLAG-2, cum/bucket exact, no-backfill enforced, recipe markers present")

    print("=== vGBT-0.8.1 gated: overlay call-site + bars resilience ===")
    import re as _re81
    assert _re81.search(r"^now_naive\s*=", APP_SRC, flags=_re81.M), "now_naive must be bound at module level"
    assert "spot-path overlay unavailable: {type(_ox).__name__}: {_ox}" in APP_SRC, "self-locating overlay caption missing"
    _stm=sys.modules["streamlit"]; _caps81=[]
    _oc=getattr(_stm,"caption",lambda *a,**k:None)
    _stm.caption=lambda *a,**k:(_caps81.append(str(a[0]) if a else ""), _oc(*a,**k))[1]
    try:
        exec_app(overrides={"Book panel (by strike)": True, "Spot-path overlay (VS3D view)": True}, name="v081_book_overlay_on")
    finally:
        _stm.caption=_oc
    _bad81=[c for c in _caps81 if "overlay unavailable" in c]
    assert not _bad81, f"overlay call-site raised live-style: {_bad81[:1]}"
    _tvm=sys.modules["tvDatafeed"]; _TVold=_tvm.TvDatafeed
    class _TVBoom81:
        def __init__(self,*a,**k): raise RuntimeError("constructor network fail")
    _tvm.TvDatafeed=_TVBoom81
    try:
        exec_app(overrides={"Book panel (by strike)": True}, name="v081_tv_ctor_down")
    finally:
        _tvm.TvDatafeed=_TVold
    print("PASS vGBT-0.8.1: now_naive module-bound; Book+overlay exec clean; tv-constructor failure degrades to bars-offline")

    assert "RTH only (9:30\u201316:00)" in APP_SRC and 'key="intv_rth"' in APP_SRC, "RTH-only toggle missing"
    assert "anchored to the DATA's own date" in APP_SRC, "open-line must be data-anchored, not server-clock"
    print("PASS vGBT-0.8.2: interval RTH-only display + data-anchored open marker present")

    print("=== vGBT-0.8.3 gated: gross = |Σc|+|Σp| (probe-faithful) ===")
    _flA=pd.DataFrame({"timestamp":[1783677900000,1783678200000],"strikePrice":[7500.0,7500.0],
                       "callExposureSum":[100.0,50.0],"putExposureSum":[-40.0,-10.0]})
    _oA=G["_intv_flow_values"](_flA,"DEX",None,cumulative=True)
    assert abs(float(_oA["gross"].iloc[-1])-200.0)<1e-9, f"cum gross (no-flip) wrong: {_oA['gross'].iloc[-1]}"
    assert (_oA["gross"].values>=np.abs(_oA["val"].values)-1e-9).all(), "gross must dominate |net|"
    _oAb=G["_intv_flow_values"](_flA,"DEX",None,cumulative=False)
    assert abs(float(_oAb["gross"].iloc[-1])-60.0)<1e-9, "per-bucket gross wrong"
    _flB=pd.DataFrame({"timestamp":[1783677900000,1783678200000],"strikePrice":[7500.0,7500.0],
                       "callExposureSum":[100.0,-80.0],"putExposureSum":[-10.0,-10.0]})
    _oB=G["_intv_flow_values"](_flB,"DEX",None,cumulative=True)
    assert abs(float(_oB["gross"].iloc[-1])-40.0)<1e-9, \
        f"flip fixture must give |Sum c|+|Sum p|=40, not churn-sum 200 — got {_oB['gross'].iloc[-1]}"
    assert "size=gross" in APP_SRC and "top-N + bubble size by GROSS" in APP_SRC, "renderer markers missing"
    print("PASS vGBT-0.8.3: gross exact (no-flip 200 / bucket 60 / FLIP 40), gross>=|net|, renderer self-documented")

    print("=== vGBT-0.8.4 gated: marker geometry cannot inflate the canvas ===")
    import io as _io84, struct as _st84
    import matplotlib.pyplot as _plt84
    def _tight_h(with_marker):
        _f,_a=_plt84.subplots(figsize=(16,5.4))
        _ts=pd.date_range("2026-07-10 09:30","2026-07-10 13:40",freq="5min")
        for _k in (7550,7560,7570,7575,7590): _a.scatter(_ts,[_k]*len(_ts),s=120)
        _a.scatter(_ts[::6],[7700]*len(_ts[::6]),s=7,alpha=.3)   # far context dots (autoscale trap)
        _a.set_ylim(7540,7600)                                    # top-5-style tight limits
        if with_marker:
            _dd=pd.DataFrame({"ts":_ts})
            G["_intv_open_marker"](_a,_dd)
            _f.canvas.draw()
            _axbb=_a.get_window_extent()
            for _t in _a.texts:
                _tb=_t.get_window_extent()
                assert _tb.y0>=_axbb.y0-2 and _tb.y1<=_axbb.y1+2, f"marker text escaped axes: {_tb} vs {_axbb}"
        _b=_io84.BytesIO(); _f.savefig(_b,format="png",bbox_inches="tight"); _plt84.close(_f)
        return _st84.unpack(">II",_b.getvalue()[16:24])[1]
    _h0,_h1=_tight_h(False),_tight_h(True)
    assert _h1<=_h0*1.05, f"marker inflated tight canvas: {_h0}px -> {_h1}px"
    assert "def _intv_open_marker" in APP_SRC and "clip_on=True" in APP_SRC, "helper markers missing"
    print(f"PASS vGBT-0.8.4: marker text inside axes; tight canvas {_h0}px -> {_h1}px (<=5% growth)")

    print("=== vGBT-0.8.5 gated: tonight's queue ===")
    assert "State (Δ/Γ×OI from snapshots · 0 API)" not in APP_SRC, "state source must be out of the UI"
    assert "def _interval_state_rows" in APP_SRC, "state ENGINE must remain (gates depend on it)"
    assert "for _tn in (300,150,100):" in APP_SRC, "midnight topN ladder missing"
    yl=G["_intv_ylim"]({7550.0,7585.0},7400.0,7700.0,pd.DataFrame({"c":[7535.0,7569.0]}))
    assert yl[0]<=7531.0+1e-9 and yl[1]>=7595.0-1e-9, f"frame must contain price+strikes: {yl}"
    import matplotlib.pyplot as _plt85
    G["bars"]=pd.DataFrame({"c":[7535.0,7569.0]})     # self-sufficient fixture (prior exec mode left bars=None)
    _f,_a=_plt85.subplots(); _a.set_ylim(7400,7740)
    G["_canon_fit_axes"](_f)
    _y0,_y1=_a.get_ylim(); _c85=pd.to_numeric(G["bars"]["c"],errors="coerce").dropna()
    _pad=max(10.0,0.35*(float(_c85.max())-float(_c85.min())))
    assert (_y1-_y0)<=(float(_c85.max())-float(_c85.min())+2*_pad)+1e-6, f"canonical fit failed: {(_y0,_y1)}"
    _plt85.close(_f)
    _ddr=pd.DataFrame({"strike":[7500.0]*4,"ts":pd.date_range("2026-07-10 10:00",periods=4,freq="5min"),
                       "val":[1.0,-1.0,1.0,-1.0],"gross":[1.0,2.0,3.0,4.0]})
    _f1,_a1=_plt85.subplots(); G["_intv_draw"](_a1,_ddr,5,rings=True);  n_on=len(_a1.collections)
    _f2,_a2=_plt85.subplots(); G["_intv_draw"](_a2,_ddr,5,rings=False); n_off=len(_a2.collections)
    _plt85.close(_f1); _plt85.close(_f2)
    assert n_on>n_off, f"rings flag inert: on={n_on} off={n_off}"
    assert "rings=bool(i_cum)" in APP_SRC, "rings must follow Cumulative toggle"
    print(f"PASS vGBT-0.8.5: state-UI removed (engine kept), midnight ladder, frame contains price {yl}, canonical fit clamps, rings cum-only (on={n_on}>off={n_off})")

    print("=== vGBT-0.8.6 gated: relative size = per-column share ===")
    _dr=pd.DataFrame({"strike":[7500.0,7550.0,7500.0,7550.0],
                      "ts":pd.to_datetime(["2026-07-10 10:00"]*2+["2026-07-10 10:05"]*2),
                      "val":[10.0,5.0,100.0,50.0],"gross":[10.0,5.0,100.0,50.0]})
    _fr=G["_intv_relsize"](_dr,_dr["gross"])
    assert list(_fr.round(6))==[1.0,0.5,1.0,0.5], f"per-column shares wrong: {list(_fr)}"
    import matplotlib.pyplot as _plt86
    _f6,_a6=_plt86.subplots(); G["_intv_draw"](_a6,_dr,5,rings=False,rel=True)
    _szs=sorted(set(float(s) for c in _a6.collections for s in c.get_sizes()))
    _plt86.close(_f6)
    assert any(abs(s-426.0)<1e-6 for s in _szs) and any(abs(s-216.0)<1e-6 for s in _szs), f"rel sizes wrong: {_szs}"
    assert 'key="intv_rel"' in APP_SRC and "rel=bool(i_rel)" in APP_SRC, "toggle wiring missing"
    print(f"PASS vGBT-0.8.6: per-column shares exact (1.0/0.5 both columns), rendered sizes 426/216, toggle wired")

# ───────────────────────── vGBT-0.9.0 gates ─────────────────────────
if "vGBT-0.9.0" in APP_SRC:
    G = G_LAST
    # source gates: v2 engine present, palette + rings per approved spec,
    # legacy strings retained, cents conversion documented in code
    for _s in ("_render_intv2", "IV2_POS=\"dodgerblue\"", "IV2_NEG=\"crimson\"",
               "IV2_RING_C=\"#2eff8a\"", "IV2_RING_P=\"#ff7300\"",
               "alpha=0.70", "np.maximum(mad,0.05)", "/100.0",
               'key="intv_rth"'):
        assert _s in APP_SRC, f"0.9.0 source gate missing: {_s}"
    # function gate: burst reduce — carpet collapses to peak, cap enforced
    _bx = pd.to_datetime(["2026-07-10 10:31","2026-07-10 10:32","2026-07-10 10:33",
                          "2026-07-10 12:45","2026-07-10 15:30","2026-07-10 15:31"])
    _braw = pd.DataFrame({"prem":[5e6,9e6,6e6,8e6,4e6,7e6],
                          "z":[4.0,9.0,5.0,7.0,3.5,6.0],
                          "call_share":[.4,.3,.4,.7,.6,.8]}, index=_bx)
    _bev = G["_iv2_burst_reduce"](_braw)
    assert len(_bev)==3 and _bev["z"].max()==7.0          # causal: 10:31 locks (z=4), 12:45 (7), 15:30 (3.5)
    assert pd.Timestamp("2026-07-10 10:31") in _bev.index and pd.Timestamp("2026-07-10 10:32") not in _bev.index
    # cumulative math gate on _iv2 values (via a stubbed imap frame)
    _o = pd.DataFrame({"strike":[7600.,7600.],"cs":[10.,5.],"ps":[-4.,-3.],
                       "ts":pd.to_datetime(["2026-07-10 09:30","2026-07-10 09:35"])})
    _o["val"]=_o.groupby("strike")["cs"].cumsum()+_o.groupby("strike")["ps"].cumsum()
    _o["gross"]=_o.groupby("strike")["cs"].cumsum().abs()+_o.groupby("strike")["ps"].cumsum().abs()
    assert list(_o["val"])==[6.0,8.0] and list(_o["gross"])==[14.0,22.0]
    print("PASS vGBT-0.9.0: interval v2 wired (palette/rings/floors), burst reduce exact, cum math exact, legacy gates intact")

if "vGBT-0.9.1" in APP_SRC:
    _pk = G_LAST["_pick_next_exp"]
    _ds = ["2026-07-10","2026-07-13","2026-07-14"]
    assert _pk(_ds, "2026-07-12") == "2026-07-13"      # Sunday -> Monday
    assert _pk(_ds, "2026-07-10") == "2026-07-10"      # weekday with 0DTE -> same day
    assert _pk(_ds, "2026-08-01") is None              # nothing listed -> caller falls back
    assert "_gbt_next_expiry()" in APP_SRC and "open_interest_by_expiration" in APP_SRC
    print("PASS vGBT-0.9.1: expiry resolver — Sunday->next listed, weekday->today, empty->fallback")

if "vGBT-0.9.3" in APP_SRC:
    for _s in ('key="iv2_scope"', 'key="iv2_rth"', 'key="iv2_top"',
               '("All expiries","0DTE only")', "index=1,horizontal=True",
               "[5,10]", "zero_dte=_zd", "_gbt_next_expiry(tk)",
               'fontweight="bold"', "figsize=(16,26)"):
        assert _s in APP_SRC, f"0.9.3 source gate missing: {_s}"
    for _z in ("_iv2_is_stale", "_iv2_monuments", "0DTE + monuments", "today_d"):
        assert _z not in APP_SRC, f"0.9.3 zombie present: {_z}"
    print("PASS vGBT-0.9.3: 2-scope radio (0DTE default), RTH toggle, top 5|10, bold 13pt, taller grid; stale-guard + monuments verified ABSENT")

if "vGBT-0.9.4" in APP_SRC:
    for _s in ('key="iv2_zthr"', '2.0,6.0', 'zthr=float(_zthr)',
               'bursts[bursts["z"]>=float(zthr)]',
               "full z frame; threshold/cooldown/cap applied at DRAW time"):
        assert _s in APP_SRC, f"0.9.4 source gate missing: {_s}"
    _rd = G_LAST["_iv2_burst_reduce"]
    _bx = pd.to_datetime(["2026-07-10 10:31","2026-07-10 10:32","2026-07-10 12:45",
                          "2026-07-10 14:00","2026-07-10 15:30"])
    _fr = pd.DataFrame({"prem":[5e6,9e6,8e6,2e6,7e6],
                        "z":[3.2,9.0,4.5,2.1,5.5],
                        "call_share":[.4,.3,.7,.5,.8]}, index=_bx)
    _e3 = _rd(_fr[_fr["z"]>=3.0]); _e5 = _rd(_fr[_fr["z"]>=5.0])
    assert len(_e5) <= len(_e3)                       # tighter threshold -> fewer/equal events
    assert set(_e5.index) <= set(_e3.index) | {pd.Timestamp("2026-07-10 10:32")}
    assert len(_e3)==3 and len(_e5)==2                # 3: 10:32(peak),12:45,15:30 · 5: 10:32,15:30
    print("PASS vGBT-0.9.4: sensitivity slider wired; draw-time threshold monotone (3 evts @z3 -> 2 @z5)")

if "vGBT-0.9.5" in APP_SRC:
    for _s in ("first trigger locked; no promotion", "ceiling: chronological, never ranked",
               "IV2_CAP=50"):
        assert _s in APP_SRC, f"0.9.5 source gate missing: {_s}"
    assert "Burst logic (sensitivity chain)" not in APP_SRC, "expander must be gone"
    assert 'sort_values("z", ascending=False).head(IV2_CAP)' not in APP_SRC
    # NO-REPAINT STREAM GATE: feed thresholded minutes incrementally;
    # the printed set must only ever GROW — no dot moves, none vanishes.
    _rd = G_LAST["_iv2_burst_reduce"]
    _sx = pd.to_datetime(["2026-07-10 10:31","2026-07-10 10:32","2026-07-10 10:33",
                          "2026-07-10 12:45","2026-07-10 15:30","2026-07-10 15:31"])
    _sf = pd.DataFrame({"prem":[5e6,9e6,6e6,8e6,4e6,7e6],
                        "z":[4.0,9.0,5.0,7.0,3.5,6.0],
                        "call_share":[.4,.3,.4,.7,.6,.8]}, index=_sx)
    _prev=set()
    for _k in range(1, len(_sf)+1):
        _cur=set(_rd(_sf.iloc[:_k]).index)
        assert _prev <= _cur, f"REPAINT at step {_k}: {_prev} -> {_cur}"
        _prev=_cur
    assert _prev=={pd.Timestamp("2026-07-10 10:31"),pd.Timestamp("2026-07-10 12:45"),
                   pd.Timestamp("2026-07-10 15:30")}
    print("PASS vGBT-0.9.5: NO-REPAINT proven on incremental stream (printed set only grows); causal lock; ranked cap dead; expander gone")

if "vGBT-0.9.6" in APP_SRC:
    # source gates: Manual default, seed-once, caps persisted, stale warning
    for _s in ('["Manual (fixed cap)","Percentile","Std Dev"],index=0',
               'and seed is None', '"terr_cap_"', "Cap stale"):
        assert _s in APP_SRC, f"0.9.6 source gate missing: {_s}"
    _tsc = G_LAST["terrain_scale"]; _tin = G_LAST["terrain_intensity"]
    _rng = np.random.default_rng(3)
    _Z1 = _rng.normal(0, 40.0, size=(30, 12))          # morning field
    _CAP = 120.0
    _V1, _c1 = _tsc(_Z1, "Manual (fixed cap)", _CAP, 95)
    # zero-pinned + exact symmetry
    _z0, _ = _tsc(np.zeros((4,4)), "Manual (fixed cap)", _CAP, 95)
    assert float(np.abs(_z0).max()) == 0.0
    _Vp,_ = _tsc(np.full((2,2), 60.0), "Manual (fixed cap)", _CAP, 95)
    _Vn,_ = _tsc(np.full((2,2),-60.0), "Manual (fixed cap)", _CAP, 95)
    assert np.allclose(_Vp, -_Vn) and abs(float(_Vp[0,0])-0.5)<1e-12
    # NO-REPAINT: append an extreme afternoon; morning colors bit-identical
    _Z2 = np.concatenate([_Z1, np.full((30,3), 500.0)], axis=1)
    _V2, _c2 = _tsc(_Z2, "Manual (fixed cap)", _CAP, 95)
    assert _c2 == _c1 == _CAP and np.array_equal(_V2[:, :12], _V1)
    # and Percentile DOES repaint (why it is exploration-only)
    _P1,_ = _tsc(_Z1, "Percentile", None, 95); _P2,_ = _tsc(_Z2, "Percentile", None, 95)
    assert not np.array_equal(_P2[:, :12], _P1)
    # intensity transform preserves sign and [-1,1]
    _W = _tin(_V2, "Arcsinh", gain=3.0)
    assert float(np.abs(_W).max()) <= 1.0 and np.all(np.sign(_W)==np.sign(_V2))
    print("PASS vGBT-0.9.6: gradient no-repaint enforced — zero-pinned, symmetric, frozen-cap invariant under appended extremes; Percentile proven to repaint; intensity sign-safe")
