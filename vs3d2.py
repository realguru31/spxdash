# ═══════════════════════════════════════════════════════════════════════════════
# 5 MODELS as VS3D-style FORWARD-SIMULATED gradients (price × time-of-day), in Colab.
# Exactly like VS3D's Gradient Chart: each pixel (price P, time τ) = the greek's value
# IF spot were P at time τ, computed from the CURRENT chain by advancing the clock and
# re-pricing with BS seeded by each strike's BARCHART IV (anchors to real skew).
# Real SPX500 candles overlay up to 'now'; forward sim continues to 16:00.
#
# Greeks (per VS3D): GAMMA net exposure; CHARM colored by HEDGING EFFECT
#   (positive charm -> RED = dealers must SELL; negative -> GREEN = must BUY).
# 5 model weightings set per-strike w: 1 naive OI | 2 zero-open VOL | 3 OI+VOL |
#   4 dVOL | 5 vol/OI.  (dVOL/vol-ratio can't truly forward-sim — flagged.)
# ═══════════════════════════════════════════════════════════════════════════════
import subprocess, sys
subprocess.run([sys.executable,"-m","pip","install","-q","requests","pandas","numpy","scipy","matplotlib"], check=True)
import requests, numpy as np, pandas as pd, datetime as dt
from urllib.parse import unquote
from scipy.stats import norm
from scipy.ndimage import gaussian_filter1d
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import matplotlib.colors as mcolors, matplotlib.dates as mdates
from zoneinfo import ZoneInfo
from IPython.display import Image, display, clear_output
try:
    from tvDatafeed import TvDatafeed, Interval
except Exception:
    subprocess.run([sys.executable,"-m","pip","install","-q","--upgrade","git+https://github.com/rongardF/tvdatafeed.git"],check=False)
    from tvDatafeed import TvDatafeed, Interval
EST=ZoneInfo("America/New_York")
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
BASE="https://www.barchart.com"; WINDOW_PCT=2.5; POLL_MIN=5; RUN_HOURS=6; N_PRICE=160; N_TIME=80

def sess():
    s=requests.Session(); s.get(f"{BASE}/stocks/quotes/%24SPX/options",headers={"accept":"text/html","user-agent":UA},timeout=20)
    x=unquote(unquote(s.cookies.get_dict()["XSRF-TOKEN"])); return s,{"accept":"application/json","referer":f"{BASE}/stocks/quotes/%24SPX/options","user-agent":UA,"x-xsrf-token":x}
def spot(s,h):
    r=s.get(f"{BASE}/proxies/core-api/v1/quotes/get",params={"symbols":"$SPX","fields":"lastPrice","raw":"1"},headers=h,timeout=10)
    return float(r.json()["data"][0].get("raw",r.json()["data"][0])["lastPrice"])
def has_chain(s,h,d):
    try:
        r=s.get(f"{BASE}/proxies/core-api/v1/options/get",params={"baseSymbol":"$SPX","expirationDate":d,"groupBy":"optionType","fields":"strikePrice,gamma","raw":"1"},headers=h,timeout=15)
        return int(r.json().get("total",0) or 0)>0
    except Exception: return False
def pick_expiry(s,h):
    today=str(dt.datetime.now(EST).date())
    if has_chain(s,h,today): return today
    r=s.get(f"{BASE}/proxies/core-api/v1/options/get",params={"baseSymbol":"$SPX","groupBy":"optionType","expirationType":"weekly","fields":"strikePrice,expirationDate","raw":"1"},headers=h,timeout=15)
    d=r.json().get("data",{}); exps=set()
    for ot,items in (d.items() if isinstance(d,dict) else []):
        for it in items or []: exps.add((it.get("raw",it)).get("expirationDate"))
    fut=sorted(e for e in exps if e and dt.datetime.strptime(e,"%Y-%m-%d").date()>=dt.datetime.now(EST).date())
    return fut[0] if fut else today
def chain(s,h,exp):
    r=s.get(f"{BASE}/proxies/core-api/v1/options/get",params={"baseSymbol":"$SPX","expirationDate":exp,"groupBy":"optionType","fields":"strikePrice,optionType,volatility,gamma,delta,openInterest,volume","orderBy":"strikePrice","orderDir":"asc","raw":"1"},headers=h,timeout=15)
    d=r.json().get("data",{}); rows=[]
    for ot,items in (d.items() if isinstance(d,dict) else []):
        for it in items or []:
            raw=it.get("raw",it)
            def nz(k):
                v=raw.get(k); return float(v) if v not in (None,"") else 0.0
            rows.append(dict(strike=nz("strikePrice"),type=ot.lower(),iv=nz("volatility"),gamma=nz("gamma"),delta=nz("delta"),oi=nz("openInterest"),vol=nz("volume")))
    return pd.DataFrame(rows)
def bars_tv(tv):
    try:
        df=tv.get_hist(symbol="SPX500",exchange="CAPITALCOM",interval=Interval.in_1_minute,n_bars=600)
        if df is None or df.empty: return None
        df=df.reset_index(); df["datetime"]=pd.to_datetime(df["datetime"]).dt.tz_localize("UTC").dt.tz_convert(EST).dt.tz_localize(None)
        today=dt.datetime.now(EST).date(); op=dt.datetime.combine(today,dt.time(9,30)); now=dt.datetime.now(EST).replace(tzinfo=None)
        df=df[(df["datetime"]>=op)&(df["datetime"]<=now)]
        return df if not df.empty else None
    except Exception: return None

# ── BS greeks (seeded with Barchart IV), VS3D forward simulation ───────────────
def bs_gamma(S,K,T,sig):
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    d1=(np.log(S/K)+0.5*sig**2*T)/(sig*np.sqrt(T)); return norm.pdf(d1)/(S*sig*np.sqrt(T))
def bs_charm(S,K,T,sig):
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    sq=sig*np.sqrt(T); d1=(np.log(S/K)+0.5*sig**2*T)/sq; d2=d1-sq; return norm.pdf(d1)*d2/(2.0*T)
def T_at(exp, when):   # years to 16:00 ET on expiry, from 'when'
    e=dt.datetime.combine(dt.datetime.strptime(exp,"%Y-%m-%d").date(),dt.time(16,0))
    return max((e-when).total_seconds(),60.)/(365*24*3600)

def forward_grid(c,S,exp,now,wcol):
    """price × time-of-day forward simulation from CURRENT chain. Returns Zg,Zc,pg,taus,x_now."""
    p_min,p_max=S*(1-WINDOW_PCT/100),S*(1+WINDOW_PCT/100)
    pg=np.linspace(p_min,p_max,N_PRICE)
    close=dt.datetime.combine(now.date(),dt.time(16,0))
    open_=dt.datetime.combine(now.date(),dt.time(9,30))
    # time axis spans full session; forward sim from now->close
    taus=[open_+dt.timedelta(seconds=t) for t in np.linspace(0,(close-open_).total_seconds(),N_TIME)]
    K=c["strike"].values; iv=c["iv"].values; sgn=np.where(c["type"].values=="call",1.0,-1.0); w=c[wcol].values
    Zg=np.zeros((N_PRICE,N_TIME)); Zc=np.zeros((N_PRICE,N_TIME))
    for j,tau in enumerate(taus):
        when=max(tau,now)               # don't simulate the past; hold at 'now' left of now
        T=T_at(exp,when)
        Sgrid=pg[:,None]
        g=bs_gamma(Sgrid,K[None,:],T,iv[None,:]); ch=bs_charm(Sgrid,K[None,:],T,iv[None,:])
        Zg[:,j]=((g*sgn*w).sum(1))*100*pg
        Zc[:,j]=((ch*sgn*w).sum(1))*100*pg
    Zg=gaussian_filter1d(Zg,1.2,axis=0); Zc=gaussian_filter1d(Zc,1.2,axis=0)
    x_now=mdates.date2num(now)
    return Zg,Zc,pg,[mdates.date2num(t) for t in taus]

def gex_cmap(): return mcolors.LinearSegmentedColormap.from_list("gex",[(0,(0.5,0,0)),(0.34,(0.86,0.06,0.06)),(0.47,(0.1,0,0)),(0.5,(0,0,0)),(0.53,(0,0.1,0)),(0.66,(0.1,0.74,0.18)),(1,(0.02,0.42,0.06))])
# charm colored by HEDGING EFFECT: +charm -> red (sell), -charm -> green (buy)  => reuse gex but invert sign
def norm_field(Z):
    sc=np.percentile(np.abs(Z),92) or 1.0; return np.clip(Z/sc,-1,1)
def draw_candles(a,bars,x0,x1,p_min,p_max):
    if bars is None or bars.empty: return
    b=bars[(bars["close"]>=p_min)&(bars["close"]<=p_max)]
    if b.empty: return
    x=mdates.date2num(list(b["datetime"])); w=(x1-x0)/(6.5*60)*0.7
    for xi,o,hi,lo,cl in zip(x,b["open"],b["high"],b["low"],b["close"]):
        col="#ffffff" if cl>=o else "#0a0a0a"
        a.plot([xi,xi],[lo,hi],color=col,lw=0.55,zorder=5)
        a.add_patch(plt.Rectangle((xi-w/2,min(o,cl)),w,max(abs(cl-o),0.05),facecolor=col,edgecolor="#999",lw=0.3,zorder=6))

MODELS=["1 naive OI","2 zero-open VOL","3 OI+VOL","4 dVOL","5 vol/OI"]
def wcolify(c, prev):
    oi=c["oi"].fillna(0); vol=c["vol"].fillna(0)
    c=c.copy()
    c["w1"]=oi
    c["w2"]=vol
    c["w3"]=oi+vol
    if prev is not None:
        pj=prev.set_index(["strike","type"])["vol"]; cj=c.set_index(["strike","type"])
        dv=(cj.index.map(lambda k: c.set_index(["strike","type"]).loc[k,"vol"] if k in cj.index else 0))
        c["w4"]=(c.set_index(["strike","type"]).join(pj.rename("vp"),how="left").reset_index()["vol"].fillna(0)
                 - c.set_index(["strike","type"]).join(pj.rename("vp"),how="left").reset_index()["vp"].fillna(0)).clip(lower=0).values
    else:
        c["w4"]=vol*0
    c["w5"]=np.divide(vol,oi,out=np.zeros(len(c)),where=oi>0)
    return c

s,h=sess(); exp=pick_expiry(s,h); today=str(dt.datetime.now(EST).date())
print(f"expiry={exp} {'<-- 0DTE' if exp==today else '<-- nearest'}")
try: tv=TvDatafeed()
except Exception as e: tv=None; print("tv init failed:",e)
import time as _t; prev=None; t_end=_t.time()+RUN_HOURS*3600; n=0
while _t.time()<t_end:
    n+=1
    try:
        S=spot(s,h); c=chain(s,h,exp); now=dt.datetime.now(EST).replace(tzinfo=None)
        c=c[(c["strike"]>=S*(1-WINDOW_PCT/100))&(c["strike"]<=S*(1+WINDOW_PCT/100))].copy()
        c=wcolify(c,prev)
        bars=bars_tv(tv) if tv else None
        wcols={"1 naive OI":"w1","2 zero-open VOL":"w2","3 OI+VOL":"w3","4 dVOL":"w4","5 vol/OI":"w5"}
        fig,ax=plt.subplots(5,2,figsize=(15,24),facecolor="#0d1117")
        for a in ax.flat: a.set_facecolor("#0d1117")
        x0=mdates.date2num(dt.datetime.combine(now.date(),dt.time(9,30))); x1=mdates.date2num(dt.datetime.combine(now.date(),dt.time(16,0)))
        for r,m in enumerate(MODELS):
            Zg,Zc,pg,taus=forward_grid(c,S,exp,now,wcols[m])
            ag,ac=ax[r,0],ax[r,1]
            ag.imshow(norm_field(Zg),origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=gex_cmap(),vmin=-1,vmax=1,interpolation="bilinear",zorder=0)
            ac.imshow(norm_field(-Zc),origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=gex_cmap(),vmin=-1,vmax=1,interpolation="bilinear",zorder=0)  # -Zc: +charm->red(sell)
            for a in (ag,ac):
                draw_candles(a,bars,x0,x1,pg[0],pg[-1])
                a.axhline(S,color="white",ls="--",lw=1,zorder=7)
                a.axvline(mdates.date2num(now),color="#39d",ls=":",lw=1,zorder=7)   # 'now' divider: left=actual, right=forward sim
                a.set_ylim(pg[0],pg[-1]); a.set_xlim(x0,x1); a.xaxis_date()
                a.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M")); a.xaxis.set_major_locator(mdates.HourLocator()); a.tick_params(colors="#777",labelsize=7)
            ag.set_title(f"GAMMA · {m}",color="#c9d1d9",fontsize=10,loc="left"); ag.set_ylabel("price",color="#777",fontsize=8)
            ac.set_title(f"CHARM · {m}  (red=sell pressure / green=buy)",color="#c9d1d9",fontsize=10,loc="left")
            if m in ("4 dVOL","5 vol/OI"): ag.text(0.01,0.02,"forward-sim weak for this model",transform=ag.transAxes,color="#aa7",fontsize=8)
        fig.suptitle(f"VS3D-style forward simulation · SPX {S:.2f} · exp {exp} · poll {n} {now:%H:%M:%S} EST · blue line = now (left actual, right simulated)",color="#c9d1d9",y=0.997)
        fig.tight_layout(rect=[0,0,1,0.99]); fig.savefig("/content/fwd_models.png",dpi=85,facecolor="#0d1117",bbox_inches="tight"); plt.close(fig)
        clear_output(wait=True); print(f"poll {n} {now:%H:%M:%S} SPX {S:.2f}"); display(Image("/content/fwd_models.png"))
        prev=c[["strike","type","vol"]].copy()
    except Exception as ex:
        import traceback; print("err",ex); traceback.print_exc()
    _t.sleep(POLL_MIN*60)
