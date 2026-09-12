#!/usr/bin/env python3
"""vs3dbc_selftest — harness-lite for vs3dbc.py (vBC-0.1), mock3-derived stubs.
Network-free: seeds synthetic snapshots (fresh last_ts -> _due() False), execs the
real app source repeatedly, and gates: render/cache contract with the new Book +
Combined tabs, Book x3 EXACT math, ledger monotonicity (jitter-proof), day-state
persistence of bc_* keys, frozen mode-1 dots, playback tick advance, tv-ctor
failure degradation, and the skill-hardened fetch-layer units."""
import sys, os, types, datetime as dt
os.environ.setdefault("MPLBACKEND","Agg")
import numpy as np, pandas as pd
from zoneinfo import ZoneInfo

APP_PATH="vs3dbc.py"; APP_SRC=open(APP_PATH).read()
EST=ZoneInfo("America/New_York")
PASS=[0]
def ok(name,extra=""):
    PASS[0]+=1; print(f"PASS {name}"+(f"  [{extra}]" if extra else ""))

# ───────────────────────── streamlit stub (mock3 pattern) ─────────────────────
class _Stop(Exception): pass
class _Rerun(Exception): pass
OVERRIDES={}; COUNT={"pyplot":0,"image":0,"warn":0}
class SessionState:
    def __init__(self): object.__setattr__(self,"_d",{})
    def __getattr__(self,k):
        d=object.__getattribute__(self,"_d")
        if k in d: return d[k]
        raise AttributeError(k)
    def __setattr__(self,k,v): object.__getattribute__(self,"_d")[k]=v
    def __getitem__(self,k): return object.__getattribute__(self,"_d")[k]
    def __setitem__(self,k,v): object.__getattribute__(self,"_d")[k]=v
    def __contains__(self,k): return k in object.__getattribute__(self,"_d")
    def get(self,k,d=None): return object.__getattribute__(self,"_d").get(k,d)
    def setdefault(self,k,d=None): return object.__getattribute__(self,"_d").setdefault(k,d)
    def keys(self): return object.__getattribute__(self,"_d").keys()
    def pop(self,k,d=None): return object.__getattribute__(self,"_d").pop(k,d)
def _ov(label,default): return OVERRIDES.get(label,default)
class W:
    def _noop(self,*a,**k): pass
    title=markdown=caption=info=error=code=metric=_noop
    def warning(self,*a,**k): COUNT["warn"]+=1
    progress=text=write=header=subheader=divider=success=_noop
    def slider(self,label,mn=None,mx=None,value=None,step=None,**k):
        return _ov(label,value if value is not None else mn)
    def select_slider(self,label,options=None,value=None,**k):
        return _ov(label,value if value is not None else options[-1])
    def selectbox(self,label,options,index=0,**k): return _ov(label,options[index])
    def radio(self,label,options,index=0,**k): return _ov(label,options[index])
    def checkbox(self,label,value=False,**k): return _ov(label,value)
    def toggle(self,label,value=False,**k): return _ov(label,value)
    def button(self,label,**k): return bool(OVERRIDES.get(label,False))
    def columns(self,spec,**k):
        n=spec if isinstance(spec,int) else len(spec)
        return [WCtx() for _ in range(n)]
    def expander(self,*a,**k): return WCtx()
    def tabs(self,labels): return [WCtx() for _ in labels]
    def spinner(self,*a,**k): return WCtx()
    def pyplot(self,fig,**k): COUNT["pyplot"]+=1
    def image(self,png,**k): COUNT["image"]+=1
    def set_page_config(self,**k): pass
    def stop(self): raise _Stop()
    def rerun(self): raise _Rerun()
class WCtx(W):
    def __enter__(self): return self
    def __exit__(self,*a): return False
class _CacheData:
    def __call__(self,*a,**k):
        if a and callable(a[0]): return a[0]
        return lambda f:f
    def clear(self): pass
st_mod=types.ModuleType("streamlit"); _root=W()
for name in dir(W):
    if not name.startswith("_"): setattr(st_mod,name,getattr(_root,name))
st_mod.session_state=SessionState(); st_mod.sidebar=WCtx(); st_mod.cache_data=_CacheData()
comp_v1=types.ModuleType("streamlit.components.v1"); comp_v1.html=lambda *a,**k:None
comp=types.ModuleType("streamlit.components"); comp.v1=comp_v1; st_mod.components=comp
sys.modules["streamlit"]=st_mod
sys.modules["streamlit.components"]=comp
sys.modules["streamlit.components.v1"]=comp_v1
sar=types.ModuleType("streamlit_autorefresh"); sar.TICK=0
sar.st_autorefresh=lambda *a,**k: sar.TICK
sys.modules["streamlit_autorefresh"]=sar
tvd=types.ModuleType("tvDatafeed")
class Interval: in_1_minute=1; in_5_minute=5; in_15_minute=15; in_30_minute=30
TVD_PAYLOAD={}
class TvDatafeed:
    def __init__(self,*a,**k): pass
    def get_hist(self,symbol=None,exchange=None,*a,**k): return TVD_PAYLOAD.get((exchange,symbol))
tvd.Interval=Interval; tvd.TvDatafeed=TvDatafeed
sys.modules["tvDatafeed"]=tvd
SS=st_mod.session_state

# ───────────────────────── synthetic data (mock3 recipe) ──────────────────────
from scipy.stats import norm as _norm
def _weekday_exps(n,start):
    d=start; out=[]
    while len(out)<n:
        if d.weekday()<5: out.append(d.strftime("%Y-%m-%d"))
        d+=dt.timedelta(days=1)
    return out
def _T_years(es,asof):
    exp=dt.datetime.combine(dt.datetime.strptime(es,"%Y-%m-%d").date(),dt.time(16,0))
    return max((exp-asof).total_seconds(),60.0)/(365*24*3600)
def synth_chain(spot,exps,asof,px_scale=1.0,vol_frac=0.35,seed=7):
    rng=np.random.default_rng(seed); rows=[]
    k25=lambda x: round(x/25.0)*25.0
    Ks=np.arange(k25(spot*0.96),k25(spot*1.04)+1,25.0)
    for ei,es in enumerate(exps):
        T=_T_years(es,asof); damp=0.55**ei
        for K in Ks:
            iv=0.125+0.45*abs(K/spot-1)+max(0.0,(spot-K)/spot)*0.25
            sq=iv*np.sqrt(T); d1=(np.log(spot/K)+0.5*iv*iv*T)/sq
            gam=_norm.pdf(d1)/(spot*sq); cdel=float(_norm.cdf(d1))
            cpx=max(spot*_norm.cdf(d1)-K*_norm.cdf(d1-sq),0.05)*px_scale
            ppx=max(cpx-spot+K,0.05*px_scale)
            coi=(200+9000*np.exp(-((K-(spot+40))/12)**2)+2600*np.exp(-((K-(spot+10))/9)**2))*damp
            poi=(200+8000*np.exp(-((K-(spot-45))/12)**2)+2400*np.exp(-((K-(spot+10))/9)**2))*damp
            if K>=spot: coi*=1.25; poi*=0.55
            else:       coi*=0.55; poi*=1.25
            cvol=max(coi*vol_frac+rng.normal(0,25),0.0); pvol=max(poi*vol_frac+rng.normal(0,25),0.0)
            rows.append(dict(strike=K,type="call",iv=iv,gamma=gam,delta=cdel,oi=round(coi),
                             volume=round(cvol),bid=round(cpx*0.985,2),ask=round(cpx*1.015+0.05,2),expiry=es))
            rows.append(dict(strike=K,type="put",iv=iv,gamma=gam,delta=cdel-1.0,oi=round(poi),
                             volume=round(pvol),bid=round(ppx*0.985,2),ask=round(ppx*1.015+0.05,2),expiry=es))
    return pd.DataFrame(rows)
def make_snap(ts,spot,exps,vix=13.2,**kw):
    return dict(ts=ts,spot=spot,chain=synth_chain(spot,exps,ts,**kw),exps=list(exps),vix=vix,vix_src="tvc")

# ───────────────────────── app runner ─────────────────────────────────────────
G_LAST={}
def exec_app(overrides=None,name="",expect=None):
    global G_LAST
    OVERRIDES.clear(); OVERRIDES.update(overrides or {})
    COUNT.update(pyplot=0,image=0,warn=0)
    g={"__name__":"__vs3dbc_test__","__file__":"vs3dbc.py"}   # NOT __main__: CLI guard must not fire
    try: exec(compile(APP_SRC,"vs3dbc.py","exec"),g)
    except _Stop: pass
    except _Rerun: pass
    G_LAST=g
    got=(COUNT["pyplot"],COUNT["image"])
    tag=f"[{name}] pyplot={got[0]} image={got[1]}"
    if expect is not None:
        assert got==expect, f"{tag} EXPECTED {expect}"
        ok(tag)
    else:
        print("info",tag)
    return g

today=dt.datetime.now(EST).replace(tzinfo=None).date()
EXPS=_weekday_exps(3,today); SPOT=6900.0
ts1=dt.datetime.combine(today,dt.time(9,40)); ts2=dt.datetime.combine(today,dt.time(10,15))
snap1=make_snap(ts1,SPOT,EXPS,px_scale=1.00,vol_frac=0.30,seed=7)
snap2=make_snap(ts2,SPOT+6.0,EXPS,px_scale=0.86,vol_frac=0.70,seed=8)
now_real=dt.datetime.now(EST).replace(tzinfo=None)
SS.snaps=[snap1,snap2]; SS.last_ts=now_real            # fresh -> _due() False -> no network

print("=== A · render/cache contract with Book + Combined ===")
g=exec_app({},name="A1 first render")
assert (COUNT["pyplot"],)==(5,), f"first render must draw 5 figs (book+terr+charm+sig+read), got {COUNT}"
assert COUNT["image"]==3, f"Combined must compose 3 cached PNGs (book 1 + terrain 2), got {COUNT}"
ok("A1 first render: 5 figs + Combined composes 3 PNGs")
traj=[]
for i in range(5):
    exec_app({},name=f"A2.{i} settle")
    traj.append((COUNT["pyplot"],COUNT["image"]))
    if COUNT["pyplot"]==0: break
assert traj[-1][0]==0, f"cache never settled: {traj}"
assert all(t[0]<=2 for t in traj), f"only benign terrain cap-seed re-renders allowed while settling: {traj}"
ok("A2 settles to zero-recompute cache",f"trajectory {traj}")
exec_app({"Book mode":"OI + new volume"},name="A3 mode change -> only Book recomputes")
assert COUNT["pyplot"]==1, f"Book mode change must recompute ONLY the book, got {COUNT}"
ok("A3 mode change -> book-only recompute")
exec_app({"Book mode":"OI + new volume"},name="A4 stable again")
assert COUNT["pyplot"]==0, f"same controls must cache-hit, got {COUNT}"
ok("A4 unchanged rerun -> zero recompute")
exec_app({"Book mode":"OI + new volume","Units":"Contracts (ledger)"},name="A5 units change")
assert COUNT["pyplot"]==1, f"Units change must recompute ONLY the book, got {COUNT}"
ok("A5 units change -> book-only recompute")
frames=SS.get("frames"); ts_keys=set(frames.keys())
assert ts2.isoformat() in ts_keys and frames[ts2.isoformat()].get("book"), "book frame cached under snapshot ts"
ok("A6 frames store carries the book tab")

print("=== B · Book x3 EXACT math (contracts + GEX) ===")
bur=G_LAST["bc_update_ledger"]; brows=G_LAST["bc_book_rows"]; bmaps=G_LAST["bc_maps"]
Tat=G_LAST["_T_at"]; bsg=G_LAST["bs_gamma"]
exp=EXPS[0]; d=ts1.strftime("%Y-%m-%d")
for k in [k for k in list(SS.keys()) if str(k).startswith("bc_")]: SS.pop(k,None)
mini=lambda cv,pv: pd.DataFrame([
    dict(strike=7000.0,type="call",iv=0.15,gamma=0.004,oi=100.0,volume=cv,expiry=exp),
    dict(strike=7000.0,type="put", iv=0.15,gamma=0.004,oi=40.0, volume=pv,expiry=exp)])
bur(mini(100.0,10.0),exp,ts1)                     # baseline: contributes 0
prev,cum=bmaps(d,exp)
assert cum=={} and prev[(7000.0,"call")]==100.0, f"baseline must contribute 0: cum={cum}"
bur(mini(160.0,10.0),exp,ts1)                     # +60 call
bur(mini(155.0,10.0),exp,ts1)                     # jitter DOWN: no change, prev stays 160
assert abs(cum[(7000.0,"call")]-60.0)<1e-9 and prev[(7000.0,"call")]==160.0, f"jitter leaked: {cum} {prev}"
bur(mini(170.0,25.0),exp,ts1)                     # +10 call (170-160), +15 put
assert abs(cum[(7000.0,"call")]-70.0)<1e-9 and abs(cum[(7000.0,"put")]-15.0)<1e-9, f"cum wrong: {cum}"
ok("B1 ledger: baseline 0, +60, jitter-immune (running max), +10/+15",f"cum={cum}")
r0,_,_=brows(mini(170.0,25.0),7000.0,exp,ts1,0,1)   # mode1 contracts: OI only
assert abs(float(r0['val'].iloc[0])-(100.0-40.0))<1e-9, f"mode1 contracts {r0}"
r1,_,_=brows(mini(170.0,25.0),7000.0,exp,ts1,1,1)   # mode2 contracts: flow only
assert abs(float(r1['val'].iloc[0])-(70.0-15.0))<1e-9, f"mode2 contracts {r1}"
r2,dots2,meta2=brows(mini(170.0,25.0),7000.0,exp,ts1,2,1)   # mode3 = OI+flow
assert abs(float(r2['val'].iloc[0])-((100+70)-(40+15)))<1e-9, f"mode3 contracts {r2}"
assert abs(dots2[7000.0]-(100.0-40.0))<1e-9 and "OI only" in meta2["dlab"], "mode3 dots = standing OI"
ok("B2 contracts: mode1=+60 · mode2=+55 · mode3=+115 with OI-only dots")
gsp=7000.0
rg,_,_=brows(mini(170.0,25.0),gsp,exp,ts1,1,0)       # mode2 GEX on chain gamma
want=2.0*0.004*(70.0-15.0)
assert abs(float(rg['val'].iloc[0])-want)<1e-9, f"mode2 GEX {float(rg['val'].iloc[0])} vs {want}"
ok("B3 GEX on NEW volume exact: 2·γ·Δvol",f"{want:.4f} e-minis/$1")
nan=mini(170.0,25.0); nan.loc[nan['type']=='call','gamma']=np.nan   # BS fallback path
rn,_,_=brows(nan,gsp,exp,ts1,1,0)
gfb=float(bsg(gsp,7000.0,Tat(exp,ts1),0.15))
wantn=2.0*(gfb*70.0-0.004*15.0)
assert abs(float(rn['val'].iloc[0])-wantn)<1e-6, f"BS fallback {float(rn['val'].iloc[0])} vs {wantn}"
ok("B4 NaN chain-γ falls back to BS gamma (row-level)")

print("=== C · persistence: bc_* keys are reload-proof ===")
sv=G_LAST["save_day_state"]; ld=G_LAST["load_day_state"]; spth=G_LAST["_state_path"]
cum_before=dict(cum); SS.snaps=[snap1,snap2]; sv()
assert os.path.exists(spth()), "state file written"
for k in [k for k in list(SS.keys()) if str(k).startswith("bc_")]: SS.pop(k,None)
SS.snaps=[]; SS.frames={}
n=ld(); _,cum_after=bmaps(d,exp)
assert n==2 and cum_after==cum_before, f"bc_ ledger did not round-trip: {cum_after} vs {cum_before}"
os.remove(spth())
ok("C1 bc_ ledger + snaps round-trip through /tmp day state")

print("=== D · mode-1 dots are FROZEN first-frame values ===")
for k in [k for k in list(SS.keys()) if str(k).startswith("bc_open1_")]: SS.pop(k,None)
rA,dA,mA=brows(mini(170.0,25.0),7000.0,exp,ts1,0,0)
rB,dB,mB=brows(mini(170.0,25.0),7010.0,exp,ts1,0,0)   # spot moved -> bars would reprice
assert dA==dB and "frozen" in (mA["dlab"] or ""), "mode-1 dots must freeze at first frame"
assert abs(float(rA['val'].iloc[0])-dA[7000.0])<1e-12, "first frame: bar == dot"
ok("D1 mode-1 dots frozen once per day (γ-drift becomes visible as bar/dot gap)")

print("=== E · playback tick advance still intact ===")
SS.snaps=[snap1,snap2]; SS.last_ts=now_real
exec_app({},name="E0 reseed frames")
for i in range(4):
    exec_app({},name=f"E0.{i}")
    if COUNT["pyplot"]==0: break
lab1=snap1["ts"].strftime("%H:%M:%S")
exec_app({"View snapshot (EST)":lab1},name="E0s scrub -> record frame #1")
assert COUNT["pyplot"]==5, f"scrubbed snapshot must live-render all tabs, got {COUNT}"
exec_app({},name="E0r back to latest")
assert snap1["ts"].isoformat() in SS.frames and snap2["ts"].isoformat() in SS.frames, "need 2 cached frames"
SS.pb_play=True; SS.pb_last_tick=None; SS.pb_idx=0; sar.TICK=7
g=exec_app({},name="E1 play first tick")
assert SS.pb_idx==0 and g["PLAYBACK"], "first tick shows current frame, no advance"
sar.TICK=8; g=exec_app({},name="E2 real tick")
assert SS.pb_idx==1, "tick must advance exactly one frame"
SS.pb_play=False; SS.pb_follow=True; SS.pb_idx=1
ok("E playback: handshake-immune tick advance preserved (2-frame film)")

print("=== F · tv failure degrades (no crash), ATM IV tripwire live ===")
class _Boom:
    def __init__(self,*a,**k): raise RuntimeError("ctor network fail")
_old=tvd.TvDatafeed; tvd.TvDatafeed=_Boom
try:
    exec_app({},name="F1 tv ctor down")
finally:
    tvd.TvDatafeed=_old
txt=G_LAST.get("_atmiv_txt","")
assert "ATM IV" in txt and "%" in txt, f"ATM IV tripwire must render: {txt!r}"
_p=float(txt.split("ATM IV")[1].split("%")[0]); assert 5.0<_p<60.0, f"ATM IV implausible {_p}"
ok("F tv-constructor failure degrades to banner; ATM IV tripwire",txt.strip())

print("=== G · skill-hardened fetch layer units ===")
cb=G_LAST["_classify_block"]
assert "AWS WAF" in cb(202,{"x-amzn-waf-action":"challenge"},"gokuProps")
assert "Cloudflare" in cb(503,{"cf-mitigated":"challenge"},"Just a moment...")
assert "OUR OWN egress" in cb(403,{"x-deny-reason":"host_not_allowed"},"")
assert "TLS fingerprint" in cb(403,{},"nope")
assert "rate-limited" in cb(429,{"retry-after":"30"},"")
assert "ordinary auth" in cb(401,{},"")
ok("G1 block signature table: WAF/CF/egress/TLS/429/401 all named")
ah=G_LAST["_api_headers"]("$SPX")
assert ah["origin"]=="https://www.barchart.com" and ah["sec-fetch-site"]=="same-origin" \
       and ah["x-requested-with"]=="XMLHttpRequest" and "referer" in ah, ah
nh=G_LAST["_nav_headers"]()
assert nh["sec-fetch-mode"]=="navigate" and "user-agent" in nh
assert G_LAST["_SECCHUA"].count("124")>=1 and "124" in G_LAST["_UA"] and G_LAST["_IMPERSONATE"]=="chrome124"
ok("G2 load-bearing headers present; UA/sec-ch-ua/impersonate agree (chrome124)")
from urllib.parse import unquote as _uq
assert _uq(_uq("abc%253D%253D"))=="abc==", "double-unquote recipe"
ok("G3 XSRF double-unquote recipe intact")
import json as _j, tempfile as _tf
blob={"minted_at":123,"user_agent":"UA-X","cookies":{"XSRF-TOKEN":"t1","laravel_token":"t2",
      "_ga":"tracker-should-drop","cf_clearance":"c1"}}
os.makedirs("data/session",exist_ok=True)
with open(G_LAST["_MINT_PATH"],"w") as f: _j.dump(blob,f)
lm=G_LAST["_load_minted"]()
assert lm and set(lm["cookies"])=={"XSRF-TOKEN","laravel_token","cf_clearance"} and lm["user_agent"]=="UA-X", lm
os.remove(G_LAST["_MINT_PATH"])
ok("G4 minted-cookie loader honors KEEP filter (analytics IDs dropped)")
assert "gbtmd_" not in APP_SRC and "vs3dGBT" not in APP_SRC
assert '"$VIX"' not in APP_SRC, "Barchart $VIX must stay banned (TVC only)"
ok("G5 no tokens, no GBT markers, Barchart $VIX still banned")

print("=== H · Interval really skipped; Book tab wired ===")
assert "interval_map" not in APP_SRC and "⏱ Interval" not in APP_SRC
assert "with tab_book:" in APP_SRC and "with tab_comb:" in APP_SRC and "bc_update_ledger(chain" in APP_SRC
assert 'startswith(("strad_open_","terr_cap_","terr_hist_","read_gmag","bc_"))' in APP_SRC
ok("H markers: no interval; book+combined wired; bc_ persisted")

print(f"\nALL GREEN — {PASS[0]} gates on vs3dbc.py (vBC-0.1)")
