"""
vs3d.py — SPX 0DTE+ Gamma & Charm (Streamlit POC)
=================================================
Point your streamlit.io app at this file.

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
                            "gamma":num("gamma"),"oi":num("openInterest"),"volume":num("volume"),
                            "bid":num("bidPrice"),"ask":num("askPrice")})
            return pd.DataFrame(rows) if rows else None
        except Exception as ex:
            _time.sleep(2)
    return None
def discover_expiries(s,h,n,sym="$SPX"):
    from datetime import date,timedelta
    d=date.today(); found=[]; exps=[]
    while len(found)<n and (d-date.today()).days<40:
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

# ════════════════════════════ Forward projection ════════════════════════════
def build_projection(chain, spot, method, p_min, p_max, n_time=160, n_price=260):
    c=chain.dropna(subset=["strike","iv","expiry"]).copy()
    c["w"]=weight_for(c, method)
    c=c[(c["strike"]>=p_min*0.85)&(c["strike"]<=p_max*1.15)]
    if c.empty: raise RuntimeError("No strikes near window")
    p_min=max(p_min, spot*0.5); pg=np.linspace(p_min,p_max,n_price); S=pg[:,None]
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
    now=dt.datetime.now()
    jnow=int(np.clip((now-sess_start).total_seconds()/max((sess_end-sess_start).total_seconds(),1)*(n_time-1),0,n_time-1))
    return pg,Zg,Zc,times,jnow,c

# ════════════════════════════ Cone (single snapshot) ════════════════════════
def cone_profiles(chain, spot, p_min, p_max, weighting, n_price=260, mult=100):
    c=chain.dropna(subset=["strike","iv","expiry"]).copy()
    c["w"]=weight_for(c, weighting)
    c=c[(c["strike"]>=p_min*0.85)&(c["strike"]<=p_max*1.15)]
    c["T"]=c["expiry"].map(lambda e:_T_at(e,dt.datetime.now()))
    p_min=max(p_min,spot*0.5); pg=np.linspace(p_min,p_max,n_price); S=pg[:,None]
    def prof(df,fn):
        if df.empty: return np.zeros_like(pg)
        return (fn(S,df["strike"].values[None,:],df["T"].values[None,:],df["iv"].values[None,:])*df["w"].values[None,:]).sum(1)
    ca=c[c.type=="call"]; pu=c[c.type=="put"]
    gex=(prof(ca,bs_gamma)-prof(pu,bs_gamma))*mult*pg
    chm=(prof(ca,bs_charm)-prof(pu,bs_charm))*mult*pg
    return pg,gaussian_filter1d(gex,2.5),gaussian_filter1d(chm,2.5),c
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
def build_time_surface(snaps, mode, p_min, p_max, weighting="volume", n_price=260, smooth_p=1.4):
    spot=snaps[-1]["spot"]; p_min=max(p_min,spot*0.5)
    pg=np.linspace(p_min,p_max,n_price); S=pg[:,None]
    base=snaps[0]["chain"]
    base_vol={(e,k,t):float(v) for e,k,t,v in zip(base["expiry"],base["strike"],base["type"],base["volume"].fillna(0))}
    Zg=np.zeros((n_price,len(snaps))); Zc=np.zeros_like(Zg); times=[]; prev_vol=None; last=None
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
        times.append(snap["ts"])
        prev_vol={(e,k,t):float(v) for e,k,t,v in zip(ch["expiry"],ch["strike"],ch["type"],ch["volume"].fillna(0))}
        last=ch
    if smooth_p>0:
        Zg=gaussian_filter1d(Zg,smooth_p,axis=0); Zc=gaussian_filter1d(Zc,smooth_p,axis=0)
    return pg,Zg,Zc,times,last,spot

# ════════════════════════════ shared analytics ══════════════════════════════
def zero_crossings(pg, vals):
    s=np.sign(vals); idx=np.where(np.diff(s)!=0)[0]; out=[]
    for i in idx:
        y0,y1=vals[i],vals[i+1]
        if y1!=y0: out.append(pg[i]-y0*(pg[i+1]-pg[i])/(y1-y0))
    return out
def compute_walls(c, spot, mult=100):
    T=c["expiry"].map(lambda e:_T_at(e,dt.datetime.now())).values if "T" not in c else c["T"].values
    g=bs_gamma(spot,c["strike"].values,T,c["iv"].values)
    sign=np.where(c["type"].values=="call",1.0,-1.0)
    per=pd.Series(g*c["w"].values*sign*mult*spot,index=c["strike"].values).groupby(level=0).sum()
    if per.empty: return None,None
    return float(per.idxmax()),float(per.idxmin())

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
def _candles_index(ax,bars,n_x,p_min,p_max):
    if bars is None or not len(bars): return
    bx=np.linspace(0.02,0.98,len(bars))*n_x; cwidth=max(0.8,n_x/len(bars)*0.5)
    for x,(_,r) in zip(bx,bars.iterrows()):
        up=r["c"]>=r["o"]; body=UP if up else DOWN
        ln,=ax.plot([x,x],[r["l"],r["h"]],color=body,lw=0.9,zorder=4); ln.set_path_effects(WICKFX)
        ax.add_patch(plt.Rectangle((x-cwidth/2,min(r["o"],r["c"])),cwidth,
            max(abs(r["c"]-r["o"]),(p_max-p_min)*0.0006),facecolor=body,edgecolor="#9aa0a6",lw=0.45,zorder=4))
def _candles_time(ax,bars,x0,x1,p_min,p_max):
    if bars is None or not len(bars): return
    bn=np.array([mdates.date2num(t) for t in bars["t"]]); inwin=(bn>=x0)&(bn<=x1)
    if not inwin.sum(): return
    cwidth=(x1-x0)/max(40,inwin.sum())*0.7
    for x,(_,r) in zip(bn[inwin],bars[inwin].iterrows()):
        up=r["c"]>=r["o"]; body=UP if up else DOWN
        ln,=ax.plot([x,x],[r["l"],r["h"]],color=body,lw=0.9,zorder=4); ln.set_path_effects(WICKFX)
        ax.add_patch(plt.Rectangle((x-cwidth/2,min(r["o"],r["c"])),cwidth,
            max(abs(r["c"]-r["o"]),(p_max-p_min)*0.0006),facecolor=body,edgecolor="#9aa0a6",lw=0.45,zorder=4))

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
    p_min,p_max=pg[0],pg[-1]; tnum=np.array([mdates.date2num(t) for t in times])
    cw,pw=compute_walls(cfull,spot)
    fig,(ag,ac)=plt.subplots(1,2,figsize=(16,8.6),facecolor=DARK); fig.subplots_adjust(wspace=0.0,left=0.01,right=0.945,top=0.93,bottom=0.06)
    step=max(5,round((p_max-p_min)/8/5)*5); gps=np.arange(round(p_min/step)*step,round(p_max/step)*step+step,step)
    for ax,P,Z in [(ag,_panel_meta()[0],Zg),(ac,_panel_meta()[1],Zc)]:
        ax.set_facecolor(DARK); cap=np.percentile(np.abs(Z),99) or 1.0
        ax.imshow(Z,origin="lower",extent=[tnum[0],tnum[-1],p_min,p_max],aspect="auto",cmap=P["cmap"],vmin=-cap,vmax=cap,interpolation="bilinear",zorder=0)
        try: ax.contour(tnum,pg,Z,levels=[0],colors=["white"],linewidths=[0.9],linestyles=["--"],zorder=3)
        except Exception: pass
        for gp in gps:
            if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
        _candles_time(ax,bars,tnum[0],tnum[-1],p_min,p_max)
        ax.axvline(tnum[jnow],color="#9aa0a6",lw=0.8,alpha=0.5,zorder=5)
        _finish(ax,P,pg,spot,p_min,p_max,Z[:,jnow],cw,pw,method,straddle,gps)
        ax.set_xlim(tnum[0],tnum[-1]); ax.xaxis_date(); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M")); ax.tick_params(axis="x",colors=TXT,labelsize=8)
    return fig

def fig_cone(pg,gex,chm,cfull,spot,bars,straddle):
    p_min,p_max=pg[0],pg[-1]; Vg,bg=field_from_profile(gex); Vc,bc=field_from_profile(chm); n_x=Vg.shape[1]
    cw,pw=compute_walls(cfull,spot)
    fig,(ag,ac)=plt.subplots(1,2,figsize=(16,8.6),facecolor=DARK); fig.subplots_adjust(wspace=0.0,left=0.01,right=0.945,top=0.93,bottom=0.05)
    step=max(5,round((p_max-p_min)/8/5)*5); gps=np.arange(round(p_min/step)*step,round(p_max/step)*step+step,step)
    for ax,P,V,b,prof in [(ag,_panel_meta()[0],Vg,bg,gex),(ac,_panel_meta()[1],Vc,bc,chm)]:
        ax.set_facecolor(DARK)
        ax.imshow(V,origin="lower",extent=[0,n_x,p_min,p_max],aspect="auto",cmap=P["cmap"],vmin=-1,vmax=1,interpolation="bilinear",zorder=0)
        ax.plot(b*n_x,pg,color="white",lw=1.0,ls="--",zorder=3)
        for gp in gps:
            if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
        _candles_index(ax,bars,n_x,p_min,p_max)
        _finish(ax,P,pg,spot,p_min,p_max,prof,cw,pw,"cone",straddle,gps)
        ax.set_xlim(0,n_x); ax.tick_params(axis="x",bottom=False,labelbottom=False)
    return fig

def fig_surface(mode,pg,Zg,Zc,times,last,spot,bars,straddle):
    p_min,p_max=pg[0],pg[-1]; tnum=np.array([mdates.date2num(t) for t in times])
    if len(tnum)==1:
        tnum=np.array([tnum[0],tnum[0]+5/1440.0]); Zg=np.repeat(Zg,2,axis=1); Zc=np.repeat(Zc,2,axis=1)
    fine=np.linspace(tnum[0],tnum[-1],max(360,len(tnum)*8))
    def interp(Z):
        out=np.empty((Z.shape[0],len(fine)))
        for i in range(Z.shape[0]): out[i]=np.interp(fine,tnum,Z[i])
        return out
    Zg_i,Zc_i=interp(Zg),interp(Zc); cw,pw=compute_walls(last,spot)
    fig,(ag,ac)=plt.subplots(1,2,figsize=(16,8.6),facecolor=DARK); fig.subplots_adjust(wspace=0.0,left=0.01,right=0.945,top=0.93,bottom=0.06)
    step=max(5,round((p_max-p_min)/8/5)*5); gps=np.arange(round(p_min/step)*step,round(p_max/step)*step+step,step)
    for ax,P,Z,Zsnap in [(ag,_panel_meta()[0],Zg_i,Zg[:,-1]),(ac,_panel_meta()[1],Zc_i,Zc[:,-1])]:
        ax.set_facecolor(DARK); cap=np.percentile(np.abs(Z),99) or 1.0
        ax.imshow(Z,origin="lower",extent=[fine[0],fine[-1],p_min,p_max],aspect="auto",cmap=P["cmap"],vmin=-cap,vmax=cap,interpolation="bilinear",zorder=0)
        try: ax.contour(fine,pg,Z,levels=[0],colors=["white"],linewidths=[0.9],linestyles=["--"],zorder=3)
        except Exception: pass
        for gp in gps:
            if p_min<gp<p_max: ax.axhline(gp,color=GRID,lw=0.5,ls="--",alpha=0.6,zorder=1)
        _candles_time(ax,bars,fine[0],fine[-1],p_min,p_max)
        _finish(ax,P,pg,spot,p_min,p_max,Zsnap,cw,pw,f"surface·{mode}",straddle,gps)
        ax.set_xlim(fine[0],fine[-1]); ax.xaxis_date(); ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M")); ax.tick_params(axis="x",colors=TXT,labelsize=8)
    return fig

# ════════════════════════════ bars ══════════════════════════════════════════
@st.cache_data(ttl=120, show_spinner=False)
def fetch_bars_raw(user, pw):
    from tvDatafeed import TvDatafeed, Interval
    tv=(TvDatafeed(user,pw) if user and pw else TvDatafeed())
    for itv in (Interval.in_5_minute,Interval.in_15_minute):
        try:
            df=tv.get_hist(symbol="SPX",exchange="CAPITALCOM",interval=itv,n_bars=300)
            if df is not None and len(df)>3:
                df=df.reset_index().rename(columns={"datetime":"t","open":"o","high":"h","low":"l","close":"c"})
                df["t"]=pd.to_datetime(df["t"]).dt.tz_localize(None)
                last=df["t"].dt.date.max(); df=df[df["t"].dt.date==last]
                return df[["t","o","h","l","c"]].dropna().reset_index(drop=True)
        except Exception: pass
    return None
def prep_bars(spot, exp_date, user, pw):
    bars=fetch_bars_raw(user,pw)
    if bars is None or not len(bars): return None
    m=float(bars[["o","h","l","c"]].stack().median())
    ok=((bars[["o","h","l","c"]]>m*0.5).all(axis=1)&(bars[["o","h","l","c"]]<m*1.5).all(axis=1))
    bars=bars[ok].reset_index(drop=True)
    if bars.empty: return None
    med=float(bars[["o","h","l","c"]].stack().median()); ratio=spot/med
    if not (0.7<=ratio<=1.3):
        for col in ("o","h","l","c"): bars[col]=bars[col]*ratio
    bars=bars[bars["t"].dt.date==exp_date].reset_index(drop=True)   # drop stale prior session
    return bars if len(bars) else None

# ════════════════════════════ snapshot taking ═══════════════════════════════
def take_snapshot(num_expiries):
    s,h=init_session("$SPX"); spot=get_spot(s,h)
    exps,chain=discover_expiries(s,h,num_expiries)
    ts=dt.datetime.now()
    st.session_state.snaps.append(dict(ts=ts,spot=spot,chain=chain,exps=exps))
    st.session_state.last_ts=ts
    return spot,exps

# ════════════════════════════ UI ════════════════════════════════════════════
if "snaps" not in st.session_state: st.session_state.snaps=[]
if "last_ts" not in st.session_state: st.session_state.last_ts=None

st.sidebar.title("vs3d · SPX 0DTE")
num_expiries=st.sidebar.slider("Expiries to aggregate",1,5,1)
view=st.sidebar.selectbox("View",["Landscape (forward projection)","Cone (single snapshot)","Intraday surface (snapshot history)"])
if view=="Landscape (forward projection)":
    method=st.sidebar.selectbox("Method",["oi","volume","oi_plus_flow","flow_reset"])
elif view=="Cone (single snapshot)":
    method=st.sidebar.selectbox("Cone weight",["volume","oi","oi_plus_flow"])
else:
    method=st.sidebar.selectbox("Surface mode",["oi_plus_flow","flow_from_open","interval_flow","cumulative"])
    surf_weight=st.sidebar.selectbox("(cumulative weight)",["volume","oi","oi_plus_flow"]) if method=="cumulative" else "volume"
window_pct=st.sidebar.slider("Price window ±%",1.0,5.0,2.5,0.5)/100.0
auto_on=st.sidebar.toggle("Auto-refresh (5 min)",value=True)
st.sidebar.caption("TradingView login (optional, for CAPITALCOM:SPX)")
tv_user=st.sidebar.text_input("TV username",value="",type="default")
tv_pw=st.sidebar.text_input("TV password",value="",type="password")
c1,c2=st.sidebar.columns(2)
force=c1.button("📸 Snapshot now",use_container_width=True)
if c2.button("🗑 Clear",use_container_width=True):
    st.session_state.snaps=[]; st.session_state.last_ts=None; st.rerun()

# auto-refresh (component rerun preserves session_state, unlike a meta-refresh)
if auto_on:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5*60*1000, key="auto5min")
    except Exception:
        st.sidebar.warning("streamlit-autorefresh not installed — add it to requirements.txt for auto-refresh.")

def due():
    if not st.session_state.snaps: return True
    return (dt.datetime.now()-st.session_state.last_ts).total_seconds() >= 5*60-5

if force or due():
    with st.spinner("Taking chain snapshot…"):
        try: take_snapshot(num_expiries)
        except Exception as ex: st.error(f"Snapshot failed: {ex}")

snaps=st.session_state.snaps
if not snaps:
    st.info("No snapshot yet. Click 📸 Snapshot now."); st.stop()

latest=snaps[-1]; spot=latest["spot"]; exps=latest["exps"]
exp_date=dt.datetime.strptime(exps[0],"%Y-%m-%d").date()
bars=prep_bars(spot,exp_date,tv_user,tv_pw)

# window
lo=spot*(1-window_pct); hi=spot*(1+window_pct)
if bars is not None and len(bars): lo=min(lo,float(bars["l"].min())); hi=max(hi,float(bars["h"].max()))
pad=(hi-lo)*0.05; p_min,p_max=lo-pad,hi+pad

# straddle (ATM, nearest expiry)
straddle=None
try:
    c0=latest["chain"]; c0=c0[c0["expiry"]==exps[0]]
    k=c0.loc[(c0["strike"]-spot).abs().idxmin(),"strike"]
    cc=c0[(c0["strike"]==k)&(c0["type"]=="call")]; pp=c0[(c0["strike"]==k)&(c0["type"]=="put")]
    if not cc.empty and not pp.empty:
        straddle=((cc["bid"].values[0]+cc["ask"].values[0])/2+(pp["bid"].values[0]+pp["ask"].values[0])/2)
except Exception: pass

# header metrics
m1,m2,m3,m4,m5=st.columns(5)
m1.metric("SPX spot",f"{spot:.2f}")
m2.metric("Straddle",f"${straddle:.2f}" if straddle else "—")
m3.metric("Expiry",exps[0]+(f" +{len(exps)-1}" if len(exps)>1 else ""))
m4.metric("Snapshots",len(snaps))
m5.metric("Last update",st.session_state.last_ts.strftime("%H:%M:%S"))

# render
try:
    if view=="Landscape (forward projection)":
        pg,Zg,Zc,times,jnow,cf=build_projection(latest["chain"],spot,method,p_min,p_max)
        fig=fig_projection(method,pg,Zg,Zc,times,jnow,cf,spot,bars,straddle)
    elif view=="Cone (single snapshot)":
        pg,gex,chm,cf=cone_profiles(latest["chain"],spot,p_min,p_max,method)
        fig=fig_cone(pg,gex,chm,cf,spot,bars,straddle)
    else:
        pg,Zg,Zc,times,last,sp=build_time_surface(snaps,method,p_min,p_max,weighting=surf_weight if method=="cumulative" else "volume")
        fig=fig_surface(method,pg,Zg,Zc,times,last,sp,bars,straddle)
    st.pyplot(fig,use_container_width=True); plt.close(fig)
except Exception as ex:
    st.error(f"Render failed: {ex}")

st.caption("In-memory POC · snapshots reset if the app restarts/sleeps · "
           "sign = dealer calls+/puts− · volume unsigned (no buy/sell inference)")
