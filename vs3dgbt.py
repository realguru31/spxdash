"""
vs3dgbt.py — SPX 0DTE Dealer Terrain on GBT market data · current: vGBT-0.5

vGBT-0.5 [VS3D PARITY — combined page + terrain zoom]
  • 🖥 VS3D tab: Book + Gamma + Charm on ONE page, assembled from the current
    frame's PNG cache (zero recompute) — sidebar checkbox to enable
  • Terrain ➕/➖/reset strike-zoom (display-only, like the Book's; matches the
    range controls on real VS3D) — applied to Gamma, Charm and side profile
  • sign convention audited & unchanged: bid/below-bid = customer SELLS = dealer
    LONG; ask/above-ask = customer BUYS = dealer SHORT; mid excluded; conf = |net|/total

vGBT-0.4.1 [BOOK RESPONDS TO THE MASTER TOGGLE + STABLE FIGURE SIZE]
  • Signed-inference checkbox now flips the Book too (was: only terrain + future
    snapshots; the Book kept using the stored dsign column either way)
  • cached frames are saved at the figure's own dpi with no tight-crop → a frame
    renders pixel-identical whether live or replayed (no more small/long jumping)

vGBT-0.4 [BOOK ZOOM + SEED ANCHOR — user-spec'd method]
  • Book zoom: ➕/➖/reset buttons (display-only sub-window of the fetched range) and a
    range caption that states EXACTLY what was fetched, shown, and seeded — no guessing
  • seed universe re-anchored: YESTERDAY's RTH close ±2% (union live window) — the
    session that built the book defines the sweep; intraday drift can't orphan strikes
  • ♻ Re-run signed seed = ONE click: clears seed+live, re-sweeps, takes a fresh
    snapshot (~2-2.5 min with spinner)
  • Price window default 1.5% → 2.0% (user spec) · FIX: signed Book no longer gets its
    x-label overwritten by the naive one
(lineage: cloned from vs3d2 v2.2.2, which grew from the vs3d3_v2.0 baseline)

vGBT-0.3.1 [file identity fix — header now names THIS file; no functional change]
=================================================
Point your streamlit.io app at this file.

CHANGELOG (newest first) — what changed and why, per version
─────────────────────────────────────────────────────────────────────────────
vGBT-0.3 [DEPLOY-PROOFING + BOOK UX — √ scale, version stamp, all 0.2.x fixes rolled up]
  • sidebar stamp vGBT-0.3: if the running app says 0.2, the repo has a stale file
  • Book: √ display scale (default ON, matches the reference chart) so the 7475/7500
    towers stop flattening every other strike; Price window ±% slider = the zoom
  • rolled up: NULLs fix · Gamma default · SIGNED·flow title badge · re-seed button ·
    seed coverage badge · budget-safe pacing
vGBT-0.2 [SIGNED INFERENCE — same morning · flow-seeded dealer signs EVERYWHERE]
  • dealer sign per leg inferred from aggressor flow: seed = YESTERDAY's session flow on
    TODAY's expiry (net customer initiative = (above_ask+ask)−(bid+below_bid); dealer =
    minus that; confidence = |net|/total). Live cumulative refresh for top-OI strikes.
  • signed mode drives BOTH the gradient (Gamma & Charm & Delta-Change fields) and the
    Book tab (MM-inferred $/1% bars, opacity = confidence). Toggle OFF = naive.
  • token: st.secrets["GBT_TOKEN"] or sidebar input — NO token in the repo.
vGBT-0.1 [GBT MIGRATION — first light 07-09 · clone of v2.2.2, ingestion swapped]
  • data: GroupBuyTrading API, SPX native, ~9 calls/snapshot (1 exposure + 8 heat)
  • chain rebuilt per strike from heat_map IV/Δ/Γ + NET_OI/NET_VOL; bid=ask=BS-mid so
    the ENTIRE v2.2.2 stack (terrain, pinak, verdict, playback, persistence) runs unchanged
  • NEW first tab 📊 Book (by strike): VS3D 'Positions' analogue — naive calls+/puts−
    convention (honest label), comparison dots (prev + market open), 1× straddle lines
  • staged for vGBT-0.2+: GBT candles/true straddle/vanna/color panels · Phase C signed flow ledger
v2.2.2 [ENGINE NIGHT-BUILD — built midday 07-08, deploy pre-open 07-09]
  • PLAYBACK rebuilt: frame advance driven by the autorefresh TICK COUNTER —
    extra reruns (button/component handshakes) can no longer skip frames;
    Rewind→Play now shows frame 1 first; Pause HOLDS position (slider no
    longer snaps to latest); Play works with the auto toggle off.
  • _due() respects the Auto-refresh toggle — no surprise Barchart pulls when
    scrubbing in manual mode (the 'back-step didn\u2019t load' spinner mystery).
  • DAY-STATE PERSISTENCE: snaps/frames/open-straddle/caps pickled to /tmp
    after every snapshot; restored automatically on an empty session. A browser
    reload now costs NOTHING (twice-burned 07-07/07-08). Clear deletes the file.
  • ATM IV tripwire FIXED — it had never rendered: NameError (use_exps before
    definition) swallowed by its own silent except since v2.1.9. New rule:
    tripwires fail loud (shows 'ATM IV unavailable (Type)' instead of nothing).
  • Banner because-line names the BINDING constraint (fishbone cap) first.
  • Two new Greek views: 'Gamma |Γ| (heaviness)' — single-hue magnitude, the
    honest unsigned map (direction blank by design) — and 'Gamma Decay (color)'
    — Γ(P,τ+30m)−Γ(P,τ), where pin energy is BUILDING. Own caps, own
    legends, ride all existing cache/playback machinery.
v2.2.1 [INTERPRETABILITY — the actual ask]
  • Signals verdict banner: one of four explicit states — LEAN LONG / LEAN
    SHORT (with play + target), SMALL SIZE ONLY, WAIT (with the specific
    blocker), STAND DOWN. Driven by read_verdict (track=False) so Signals and
    Read can never disagree; includes confidence and a plain because/flips line.
  • Every row now carries an inline plain-English interpretation; directional
    rows are explicitly ▲/▼ (path, PIN magnet, walls ±distance), gate rows say
    LIVE/OFF instead of implying it; jargon glossed in place (fishbone, snake-
    oil, K*, flip side). Terminology kept true to VS3D, meaning made explicit.
v2.2.0 [NIGHT BUILD — signals trust & readability]
  • Empirical charm lean now uses _book_delta_drift(): the FIXED prior book
    repriced at both (spot,T) states. Weight growth (volume accumulating) no
    longer masquerades as hedge flow — the ≈61k minis/5min was contaminated;
    the ×2/100 e-mini conversion itself audited CORRECT vs the cheat sheet.
  • Absorption weights book-first (OI, volume fallback) in Signals + Read —
    absorption is the EXISTING book’s remaining hedge (§5.4), not day flow.
  • Per-date open straddle persisted at first snapshot (survives Clear); decay
    gate labels its reference honestly (“open 09:35” vs “open (1st snap)”).
  • Signals tab rebuilt: grouped sections, aligned columns, status colors,
    bigger type. Fixed matplotlib mathtext swallowing dollar signs (the
    “now 18.97·open11.45” cram) — all fig text now mathtext-safe.
v2.1.9 [IV KILL-SHOT + TRIPWIRE — post-close hardening]
  • _iv_norm_chain(): units decided ONCE per fetched chain from the MEDIAN and
    applied uniformly — closes the per-value leak (a legit 2.8%-IV strike
    printed percent-style as 2.8 passed the >3 test and entered as 280%).
    Mixed-units chains are now impossible by construction.
  • Header shows ATM IV next to the candles caption (e.g. · ATM IV 19.4%) —
    a units regression can never again hide behind a rendered field.
v2.1.8 [IV UNITS ROOT CAUSE + STACKED CHARM — 2026-07-07 midday]
  • ROOT CAUSE of the flat two-tone terrain: Barchart serves IV percent-style
    (19.5 = 19.5%) and we consumed it as decimal → every BS greek priced at
    ~1950% vol → gamma smeared ±700pts → ALL price structure erased (strike
    banding cv 1.5→0.17 in the harness repro; flat two-tone is the symptom). Proof: a
    fresh Reset re-seeded cap ≈4.69e9 ≈ the "stale" 4.25e9 (a fresh seed cannot
    saturate its own frame), and straddle $26.10 @ spot 7486 implies ~19.5% ATM.
    FIX: _iv_norm() at the fetch_chain ingest point — >3 → ÷100. Snapshot
    chains are now decimal everywhere downstream (terrain, Delta Change, read
    lean, pinak vanna, decay/forward surfaces all healed by the one choke point).
  • STACKED CHARM PANEL (user request): Charm field rendered below the main
    greek on the Terrain tab, VS3D-style — no dropdown flip-flopping. Own cap
    (terr_cap_Charm_*), rides the same playback/frame cache (multi-image tabs
    were already supported), zero-contour + candles + spot for alignment.
v2.1.7 [LIVE-SESSION FIXES — 2026-07-07 first RTH validation]
  • DEFAULTS: Expiries to aggregate 3→1 (0DTE only — the gradient chart is a
    0DTE tool; multi-expiry background was washing out asymptotic structure).
    Price window ±2.5%→±1.5% (comparable zoom to the VS3D reference).
  • Calibrate range / Reset cap moved OUT of the collapsed Terrain expander to
    top-level sidebar — mid-session scale fixes must be one click away.
  • Stale-cap banner: if the live p92 exceeds 3× the fixed cap, the app says so
    (today the field sat saturated for ~90 min before anyone noticed).
  • K* parity band tightened ±3%→±1%: stale-but-uncrossed quotes 160 pts out
    won K* (7330 @ spot 7490). Near-spot parity only.
v2.1.6 [VIX = TVC ONLY] Barchart $VIX fallback REMOVED per user rule — VIX now
  comes exclusively from TradingView TVC:VIX (fetch_vix_live). If the TVC pull
  fails, the gate shows "VIX n/a · TVC feed unavailable" (zero confidence
  effect) instead of silently regressing to a possibly-delayed quote.
v2.1.5 [LIVE VIX] VIX regime gate now sourced from TradingView TVC:VIX (live)
  via the existing tvdatafeed dependency — fetch_vix_live(), last 1-min close,
  sanity band 5–200. Barchart $VIX kept as automatic fallback (its free index
  quote may be delayed; a stale VIX matters most exactly during a spike, when
  the vanna gate should flip). Snapshot stores vix_src ("tvc"/"bc"); the Read
  tab's VIX line shows the source so live validation can confirm which fed it.
  No greek math touched — VIX is regime gate + confidence only.
v2.1.4 [PERF/JIGGLE FIX] Two changes for CPU + screen-shake:
  • Fixed-size chart rendering (use_container_width off, dpi 80). The jiggle was
    Streamlit's resize feedback loop: responsive image ↔ scrollbar ↔ container
    width oscillating on tall pages (Read tab). Fixed-size images end the loop.
  • Live-render signature cache: each tab re-computes ONLY when its snapshot or
    its own controls change; otherwise the cached PNG is shown with zero math.
    Changing the Greek recomputes Terrain alone — Signals/Read stay cached. An
    idle page now does no per-rerun BS-grid work at all (one benign extra render
    right after a cap first seeds).
v2.1.3 [Terrain strike scale] 25-pt price ticks now bright (#9fb0c3, larger) on
  BOTH sides — left on the main field, right beside the profile histogram (VS3D
  style) — plus subtle horizontal gridlines across the field so ridges and walls
  map to strikes at a glance.
v2.1.2 [Read tab glance graphics] Two cheat-sheet panels under the text:
  left = minimal sketch of the current pattern (chop zigzag with range band for
  +γ; expansion curve with trigger dot for −γ, in direction color); right = 'the
  day on one map' drawn with LIVE levels — UPPER/LOWER TEST (walls, amber),
  ANCHOR (PIN, blue; merged label when pin sits on a wall), spot dot, and a lean
  arrow to target (label suppressed when it would collide with a level label).
v2.1.1 [Read tab visual + pin fix] Read card rebuilt: large bold pattern header
  with ▲/▼ in direction color (green bullish / red bearish vs spot), wrapped NEXT
  line, colored gate stack (bull/bear/amber semantics; fixed FLOW-contains-LOW
  substring bug), colored confidence bar. PIN candidates now constrained to ±2.5%
  of spot — deep-wing OI was dragging pin to absurd levels (e.g. 6825 with spot
  7537), corrupting the tension note; same class of fix as flip/K* earlier.
v2.1  [NEW 📖 Read tab — the cheat-sheet as a decision engine] γ environment
  (side of flip + magnitude vs session trailing) × charm lean (empirical Δbook-
  delta/Δt when 2+ snaps, else model charm; hedging-effect: rising book delta =
  dealers SELL = lean down) → one of the four day patterns (chop-up / chop-down /
  bull expansion / bear flush) with structure suggestion and 'buy what price goes
  through, sell what price goes to' strikes. Gates: charm clock, straddle check
  (decaying / flat-repricing / collapsing), VIX regime (now fetched per snapshot),
  fishbone (hard-caps confidence at 25 — SIT OUT), γ-absorption along the path
  (§5.4), negative-γ 'needs a trigger' penalty, pin-vs-charm tension flagged when
  PIN sits against the lean. Confidence 5–95 from the gate stack. Playback key
  'read'. Proxy-honest footer throughout.
v2.0.2 [Weighting made explicit + honest] New Terrain control 'Weighting':
  OI + Volume (default: yesterday's settled book + today's cumulative flow),
  OI (opening book — static all day, §4.5 'respect the opening position'),
  Volume (today's flow — cumulative, resets overnight only, counts round-trips),
  Vol-else-OI (legacy rule; kept, but it under-weights a big-OI strike the moment
  it prints 2 lots — that discontinuity is why it's no longer default).
  Nothing is signed; nothing resets intraday; OI cannot change intraday (OCC
  publishes once daily). Cap seeds/history are per greek+weighting.
v2.0.1 [FIX — controls now apply instantly] PLAYBACK was engaging whenever ANY
  frame was cached, so after the first snapshot every rerun replayed a frozen PNG
  and sidebar changes (Greek, opacity, cap…) did nothing until the next 5-min
  snapshot. Now: replay ONLY while ▶ playing or scrubbed to an older frame;
  paused at the latest frame = LIVE render every rerun (cache overwritten so
  playback stays current). Also: Expiries-to-aggregate default 1→3 (§1.5 whole
  book), cap seeds at 1.2×p98 (less saturation, more gradient), side histogram
  scales to its own shape (no more slab), off-hours banner explains the flat
  pre-market field.
v2.0  [REBUILD to VS3D guide spec — 7 tabs → 2]
  After a word-by-word read of the VS3D Onboarding Guide (all 7 chapters):
  • 🗺 TERRAIN — the Gradient Chart done right. Multi-expiry book (each expiry
    decays on its own clock; 0DTE dominates via asymptotic gamma, §1.5/1.6).
    Greeks: Delta Change (§7.7, new — book_delta(now) − book_delta(P,τ); the
    'path of least resistance', combines gamma+charm), Gamma (model or §2.7
    simulated $5 finite-diff), Charm (hedging-effect polarity: SELL=gold).
    Rendering per §2.4: MANUAL symmetric range with Calibrate-from-trailing
    (a loose day looks loose; no per-frame percentile rescaling), Power
    intensity default 1.0 (near-linear; low power = Dan's 'cartoon setting'
    warning), field opacity default 0.38 BEHIND candles. §1.5 contours: dotted
    zero boundary, RED ridge chains (local maxima through time), BLUE troughs.
    Straddle bounds (§5.3), side profile histogram (right edge), Vol Adjust
    0/+1%, Pinak dealer-levels overlay.
  • 🧭 SIGNALS — the §5.1 daily workflow as one panel: straddle now/open +
    decaying gate (snake-oil check), spot±straddle range, fishbone verdict,
    regime vs trailing, timing window, CHARM GATE (decaying AND 1:30–3pm),
    gamma absorption to each bound in e-mini equiv (§5.4 'profile consumes
    itself') with path-of-least-resistance read, Pinak levels block.
  • Playback engine unchanged (keys: terrain, signals). Old tabs retired; their
    logic lives on inside these two. v1.19 kept as deploy fallback.
v1.19.2 [FIX] Pinak tab, on live 0DTE: three glitches fixed.
  • VOL TRIGGER (flip) showed nonsense (e.g. 4800) — the zero-cross finder grabbed the
    first sign flip in the deep near-zero wings. Now ignores crossings where |GEX| is
    <2% of max and picks the crossing NEAREST spot.
  • K* (parity forward) showed nonsense (e.g. 7320) — parity solver trusted stale/crossed
    deep-ITM quotes. Now restricted to strikes within ±3% of spot with valid two-sided
    quotes (ask>bid), using bid/ask MIDS.
  • Level labels collided/overwrote (CALL WALL+CEILING+K* stacked). Now labels are
    staggered vertically with leader lines when levels sit close together.
v1.19.1 [FIX] Forward-sim field was TIME-FLAT (looked like flat green/red blocks, not
  the smooth fade-and-intensify of the real VS3D chart). Cause: forward_sim_grid clamped
  every time column's T to 'now' (when=max(tau,now)), so gamma never decayed across the
  session. Fix: T=_T_at(exp,tau) across the WHOLE 09:30–16:00 axis, so near-dated gamma
  goes asymptotic toward expiry (verified: ATM gamma grows ~16x open→close; time-var
  ratio 0.00→0.17). This also feeds the Forward-models tab (same function). The blue
  'now' line still marks present; candles still overlay actual price.
v1.19  [NEW 'Pinak 2' tab — VS3D Gradient Chart with normalization/transform controls]
  • Added 7th tab '🌈 Pinak 2 (VS3D gradient)'. Reuses the forward-sim grid (model 2,
    today's live-flow VOL weight) and layers the VS3D handoff's tuning chain on top:
      - Normalization modes: Percentile(default, tunable hi pctile) / Linear / Std Dev / Z-Score
      - Intensity transforms: Arcsinh(default, gain slider) / Square Root / Power Law / Linear
        (these tame the 0DTE asymptotic 'deep green all the time' blowout)
      - γ=0 boundary + ridge/trough contour lines
      - Reverse +/- toggle; Greek selector (Gamma green/red · Charm gold/blue)
    All controls live in a sidebar '🌈 Pinak 2 gradient controls' expander.
  • New helpers: pinak2_normalize(), pinak2_transform(), pinak2_contours().
  • Honest note in-tab: OI-proxy sign gives a clean green/red split, not green-with-
    red-pockets (that needs dealer long/short, which free data lacks) — the split is
    the proxy's tell, not a bug. Caches for playback (1 fig/snapshot).
v1.18  [NEW 'Pinak' tab — dealer-positioning levels, NIFTY-GEX method]
  • Added 6th tab '🎯 Pinak (dealer levels)'. Ports the NIFTY GEX skill's
    methodology onto Barchart 0DTE data, in our price-axis style.
  • GEX per strike = gamma·OI·spot·100 (Barchart gamma). Computes: vol trigger
    (gamma flip = net-GEX zero-cross), call/put walls, ceiling/floor (positive-net-
    GEX ranked by |gex|·OI), upside/downside hedge walls (exp proximity-decay ×
    (1+vanna)), K* (put-call parity forward vs no-arb band), 3 gravity centers,
    pin level + 0-100 confidence score/label, Color exposure (∂γ/∂t).
  • Vanna: TRUE closed-form bs_vanna = -φ(d1)·d2/σ seeded with Barchart IV
    (the skill's #1 upgrade), not the OI×GEX proxy. Also added bs_delta, bs_color.
  • Visual: GEX profile as left-gutter density (green call / red put / gold net) on
    the price axis + candles + all levels as labeled horizontal lines. Signals figure
    below. Uses dispatch/emit so it caches for playback (2 figs/snapshot).
  • Sign remains dealers-short-options CONVENTION (not measured) — noted in-tab.
v1.17.3 Fixed VS3D tab panels rendering at giant full-width size (regression from the
  playback refactor, which emitted each panel full-width). Restored a 2-column grid
  for VS3D in BOTH live and playback so the 6 panels stay a sane size. emit() now
  accepts a container arg to render into a specific column.
v1.17.2 Removed the Cone-tab candle/bar diagnostics expander (was for debugging the
  'candles not drawing' issue, now resolved — just clutter).
v1.17.1 [hotfix] Frame slider crashed when only 1 playback frame existed
  (Streamlit requires slider min<max). Now: <2 frames shows a caption instead of
  the slider, and Play won't start until ≥2 frames are cached. Rest unchanged.
v1.17  [PLAYBACK engine + charm colors + 5-min candles; all tabs refactored]
  • PLAYBACK: every snapshot, all 5 tabs render to PNG and cache in
    session_state.frames[ts][tab]. Sidebar ▶Play/⏸Pause, ⏮Rewind, Speed 1/2/4 s/frame,
    Frame slider. Play advances a frame each fast tick (st_autorefresh at the chosen
    speed); Pause holds so you can read. Playback shows CACHED PNGs — no recompute
    (verified: 22 figs cached live, 22 replayed with 0 recompute). Live 5-min refresh
    is suspended while playing; resumes on pause.
  • All 5 tab bodies refactored into _render_*() funcs called via dispatch(tab,fn),
    which either renders+caches (live) or replays cached frames (playback). emit()
    replaces st.pyplot so every figure is both shown and cached. Nothing removed.
  • Forward-model CHARM recolored to the gold/blue charm_cmap (was red/green); titles
    updated to 'gold=put/− · blue=call/+'.
  • Candles switched to 5-MIN (prep_bars resamples 1-min→5-min OHLC) — less busy;
    candle width auto-adapts to bar spacing.
  • dVOL empty earlier was GENUINE: Barchart volume often unchanged between two 5-min
    snapshots (coarse cache), so Δvol≈0. Not a bug; needs wider spacing to populate.
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

st.set_page_config(page_title="vs3dGBT · SPX 0DTE (GBT data)", layout="wide")

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
def _iv_norm(v):
    """Barchart serves IV percent-style (e.g. 19.5 = 19.5%). Normalize to decimal
    at INGEST so every snapshot chain is decimal everywhere downstream. >3 cannot
    be a real decimal index vol (300%), so the detector is safe either way.
    v2.1.8 root-cause: BS greeks were priced at ~1950% vol all morning."""
    try:
        import math
        if v is None or (isinstance(v,float) and math.isnan(v)): return v
        return v/100.0 if v>3.0 else v
    except Exception: return v

def _iv_norm_chain(s):
    """Chain-level units detector (v2.1.9): decide percent-vs-decimal ONCE from the
    chain MEDIAN (percent-style medians ~15-30, decimal ~0.15-0.3), then apply
    uniformly. Closes the per-value leak where a legit 2.8%-IV strike printed
    percent-style as 2.8 would pass the >3 test and enter as 280%."""
    try:
        ss=pd.Series(s).astype(float)
        med=float(ss.dropna().median())
        return ss/100.0 if (med==med and med>3.0) else ss
    except Exception: return s

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
            if not rows: return None
            df=pd.DataFrame(rows); df["iv"]=_iv_norm_chain(df["iv"])
            return df
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
def _dealer_sign(c):
    """vGBT-0.2: per-leg dealer sign. Signed mode → flow-inferred dsign in [-1,1]
    (confidence-weighted); falls back to naive calls+/puts− when the toggle is off
    or the column is absent (harness/synthetic frames)."""
    nv=np.where(c["type"].values=="call",1.0,-1.0)
    try:
        if GBT_SIGNED and "dsign" in c.columns:
            d=c["dsign"].values.astype(float)
            return np.where(np.isfinite(d),d,nv)
    except Exception: pass
    return nv
def _gex_profile_barchart(c, pg, mult=100, smooth_frac=0.01):
    """Net dealer GEX as a density vs price level pg, from Barchart per-strike gamma.
    Net signed GEX per strike (calls +, puts −) is interpolated onto the price grid,
    then smoothed by smooth_frac (0 = raw per-strike detail, higher = smoother)."""
    if c.empty: return np.zeros_like(pg)
    sign=_dealer_sign(c)
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
    sign=_dealer_sign(c)
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
    st=c["strike"].values; sign=_dealer_sign(c)
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
    sign=_dealer_sign(c)
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
    K=c["strike"].values; iv=c["iv"].values; sgn=_dealer_sign(c)
    w=_fwd_weight(c,model,prev_chain)
    Zg=np.zeros((n_price,n_time)); Zc=np.zeros((n_price,n_time))
    for j,tau in enumerate(taus):
        # T decays across the WHOLE session axis (09:30->16:00) so near-dated gamma
        # goes asymptotic toward expiry — the 'increasingly local' intensification the
        # VS3D chart shows. (Previously clamped to now → time-flat field.)
        T=_T_at(exp,tau); Sg=pg[:,None]
        g=bs_gamma(Sg,K[None,:],T,iv[None,:]); ch=bs_charm(Sg,K[None,:],T,iv[None,:])
        Zg[:,j]=(g*sgn*w).sum(1)*100*pg; Zc[:,j]=(ch*sgn*w).sum(1)*100*pg
    Zg=gaussian_filter1d(Zg,1.2,axis=0); Zc=gaussian_filter1d(Zc,1.2,axis=0)
    return pg,Zg,Zc,[mdates.date2num(t) for t in taus]
def _fwd_norm(Z):
    sc=np.percentile(np.abs(Z),92) or 1.0; return np.clip(Z/sc,-1,1)

# ═══════════════ PINAK 2 — VS3D gradient normalization / transforms / contours ══
# From the VS3D handoff: normalization modes + intensity transforms exist to tame
# the 0DTE asymptotic blowout ("deep green all the time"). All operate on a signed
# field Z and return values in [-1,1] preserving sign, centered on 0.
def pinak2_normalize(Z, mode="Percentile", lo=5, hi=95):
    a=np.abs(Z)
    if mode=="Linear":
        sc=a.max() or 1.0
    elif mode=="Percentile":
        sc=np.percentile(a,hi) or 1.0
    elif mode=="Std Dev":
        sc=(2.0*a.std()) or 1.0
    elif mode=="Z-Score":
        mu=a.mean(); sd=a.std() or 1.0
        return np.clip(np.sign(Z)*((a-mu)/sd),-3,3)/3.0
    else:  # Manual handled by caller passing a scale via lo (abs cap)
        sc=(lo if lo>0 else a.max()) or 1.0
    return np.clip(Z/sc,-1,1)
def pinak2_transform(V, kind="Arcsinh", power=0.5, gain=3.0):
    """Intensity transform on a signed [-1,1] field; preserves sign, keeps [-1,1]."""
    s=np.sign(V); m=np.abs(V)
    if kind=="Square Root":
        m=np.sqrt(m)
    elif kind=="Power Law":
        m=np.power(m, max(power,0.05))
    elif kind=="Arcsinh":
        m=np.arcsinh(gain*m)/np.arcsinh(gain)      # normalized so max stays 1
    # "Linear" → unchanged
    return s*m
def pinak2_contours(ax, Z, x0, x1, pg, zero=True, ridges=True):
    """Draw γ=0 boundary + ridge/trough lines on an imshow'd field."""
    import numpy as _np
    X=_np.linspace(x0,x1,Z.shape[1]); Y=pg
    if zero:
        try: ax.contour(X,Y,Z,levels=[0.0],colors="#dddddd",linewidths=1.1,alpha=.85,zorder=6)
        except Exception: pass
    if ridges:
        try:
            lv=[_np.nanpercentile(Z[Z>0],80)] if (Z>0).any() else []
            lo=[_np.nanpercentile(Z[Z<0],20)] if (Z<0).any() else []
            for L,col in ((lv,"#39d353"),(lo,"#ff5a3c")):
                if L and _np.isfinite(L[0]) and L[0]!=0:
                    ax.contour(X,Y,Z,levels=L,colors=col,linewidths=0.7,alpha=.6,linestyles="--",zorder=6)
        except Exception: pass

# ═══════════════ PINAK — dealer-positioning levels (NIFTY-GEX method) ═══════════
# Adapted from the NIFTY GEX skill to Barchart 0DTE data. GEX per strike =
# gamma·OI·spot·100 (Barchart gamma). TRUE closed-form Vanna (BS, seeded with
# Barchart IV) feeds the hedge-wall amplifier. All levels: vol trigger (gamma
# flip), call/put walls, pin + confidence, floor/ceiling, upside/downside hedge
# walls, K* (put-call parity forward), gravity centers, Color (∂γ/∂t).
def bs_delta(S,K,T,sig,is_call=True):
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    d1=(np.log(S/K)+0.5*sig**2*T)/(sig*np.sqrt(T))
    return norm.cdf(d1) if is_call else norm.cdf(d1)-1.0
def bs_vanna(S,K,T,sig):
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    sq=sig*np.sqrt(T); d1=(np.log(S/K)+0.5*sig**2*T)/sq; d2=d1-sq
    return -norm.pdf(d1)*d2/sig                                   # closed-form ∂delta/∂σ
def bs_color(S,K,T,sig,r=0.0):
    # ∂gamma/∂T closed form (q=0); returns per-day color = -raw/365
    S=np.asarray(S,float);K=np.asarray(K,float);T=np.maximum(T,1e-9);sig=np.maximum(sig,1e-4)
    sq=sig*np.sqrt(T); d1=(np.log(S/K)+(r+0.5*sig**2)*T)/sq; d2=d1-sq
    raw=-norm.pdf(d1)/(2*S*T*sq)*(1+d1*(2*r*T-d2*sq)/sq)
    return raw/365.0

def pinak_levels(chain, spot, exp, now):
    """Compute all dealer-positioning levels from a Barchart chain. Strike-indexed."""
    c=chain.dropna(subset=["strike"]).copy()
    c=c.groupby(["strike","type"],as_index=False).first()
    cc=c[c.type=="call"].set_index("strike"); pp=c[c.type=="put"].set_index("strike")
    K=np.array(sorted(set(cc.index)|set(pp.index)),float)
    def col(df,k): return df[k].reindex(K).fillna(0).values
    cg=col(cc,"gamma"); pg=col(pp,"gamma"); coi=col(cc,"oi"); poi=col(pp,"oi")
    civ=col(cc,"iv"); piv=col(pp,"iv"); cpx=col(cc,"bid"); ppx=col(pp,"bid")
    mult=100.0
    call_gex=cg*coi*spot*mult; put_gex=pg*poi*spot*mult
    net_gex=call_gex-put_gex; tot_gex=call_gex+put_gex
    # ---- vol trigger / gamma flip: zero-cross of net_gex NEAREST spot ----
    # (ignore deep-wing noise where |GEX| is tiny; pick the crossing closest to spot)
    flip=None
    gex_floor=0.02*np.abs(net_gex).max()          # ignore crossings in near-zero wings
    cross=[]
    for i in range(len(K)-1):
        a,b=net_gex[i],net_gex[i+1]
        if np.sign(a)!=np.sign(b) and b!=a and max(abs(a),abs(b))>=gex_floor:
            xc=float(K[i]+(K[i+1]-K[i])*(-a)/(b-a)); cross.append(xc)
    if cross:
        flip=float(min(cross,key=lambda x:abs(x-spot)))   # nearest to spot
    # ---- call / put walls ----
    above=K>spot; below=K<spot
    call_wall=float(K[above][np.argmax(call_gex[above])]) if above.any() and call_gex[above].max()>0 else None
    put_wall =float(K[below][np.argmax(put_gex[below])])  if below.any() and put_gex[below].max()>0 else None
    # ---- true closed-form vanna (seeded with Barchart IV) ----
    T=_T_at(exp, now)
    vanna=np.abs(bs_vanna(spot,K,T,np.where(civ>0,civ,np.where(piv>0,piv,0.15))))
    vn=vanna/ (vanna.max() or 1.0)
    # ---- upside hedge wall (above call wall) ----
    up_hw=None
    if call_wall is not None:
        m=K>call_wall
        if m.any():
            hp=(call_gex[m]*coi[m])*np.exp(-5*(K[m]-call_wall)/call_wall)*(1+vn[m])
            if hp.max()>0: up_hw=float(K[m][np.argmax(hp)])
    # ---- downside hedge wall (below put wall) ----
    dn_hw=None
    if put_wall is not None:
        m=K<put_wall
        if m.any():
            hp=(put_gex[m]*poi[m])*np.exp(-5*(put_wall-K[m])/put_wall)*(1+vn[m])
            if hp.max()>0: dn_hw=float(K[m][np.argmax(hp)])
    # ---- floor / ceiling: positive-net-gex strikes ranked by |gex|*OI ----
    posmask=net_gex>0
    def side_level(mask):
        idx=np.where(mask)[0]
        if len(idx)==0: return None
        score=np.abs(net_gex[idx])*(coi[idx]+poi[idx])
        return float(K[idx][np.argmax(score)])
    ceiling=side_level(posmask & above); floor=side_level(posmask & below)
    # ---- gravity centers (3 methods, call side toward ceiling / put toward floor) ----
    def centroid(mask):
        w=np.abs(net_gex[mask]); return float((K[mask]*w).sum()/w.sum()) if w.sum()>0 else None
    call_grav=centroid(above) ; put_grav=centroid(below)
    # ---- pin level + confidence ----
    nb=np.abs(K-spot)<=spot*0.025          # near-spot band: wings can't own the pin
    if nb.any():
        tg=np.where(nb,tot_gex,-1); to_=np.where(nb,coi+poi,-1)
        max_gex_k=float(K[np.argmax(tg)]) if tg.max()>0 else spot
        max_oi_k =float(K[np.argmax(to_)]) if to_.max()>0 else spot
    else:
        max_gex_k=max_oi_k=spot
    in_pos=(flip is not None and spot>flip) or (flip is None and net_gex[np.argmin(np.abs(K-spot))]>0)
    conv=abs(max_gex_k-max_oi_k)
    grav_agree=(call_grav is not None and put_grav is not None and abs(call_grav-put_grav)<spot*0.01)
    pin=float(np.average([max_gex_k,max_oi_k]))
    score=0
    score+=35 if in_pos else 0
    score+=30 if conv<spot*0.0015 else (15 if conv<spot*0.004 else 0)
    score+=20 if grav_agree else 0
    score+=15 if abs(pin-spot)<spot*0.003 else (7 if abs(pin-spot)<spot*0.008 else 0)
    label=("STRONG PIN" if score>=75 else "MODERATE PIN" if score>=50 else "WEAK PIN" if score>=25 else "NO PIN")
    # ---- K*: put-call parity forward vs no-arb band (near-spot, valid quotes only) ----
    cask=col(cc,"ask"); pask=col(pp,"ask")
    kstar=None; best=1e18; band=spot*0.01   # ±1% (was 3%): live 2026-07-07 a stale 7330 won at spot 7490
    for i,k in enumerate(K):
        if abs(k-spot)>band: continue                      # near-spot only
        if cpx[i]<=0 or ppx[i]<=0: continue                # need two-sided
        if cask[i]<cpx[i] or pask[i]<ppx[i]: continue      # skip crossed/stale quotes
        cmid=0.5*(cpx[i]+cask[i]); pmid=0.5*(ppx[i]+pask[i])
        F=cmid+k-pmid                                       # implied forward (mids)
        d=abs(F-spot)
        if d<best: best=d; kstar=float(k)
    # ---- color exposure (∂γ/∂t) per strike ----
    colr=(bs_color(spot,K,T,np.where(civ>0,civ,0.15))*coi + bs_color(spot,K,T,np.where(piv>0,piv,0.15))*poi)*spot*mult
    return dict(K=K,call_gex=call_gex,put_gex=put_gex,net_gex=net_gex,tot_gex=tot_gex,color=colr,
                flip=flip,call_wall=call_wall,put_wall=put_wall,up_hw=up_hw,dn_hw=dn_hw,
                ceiling=ceiling,floor=floor,call_grav=call_grav,put_grav=put_grav,
                pin=pin,pin_score=score,pin_label=label,kstar=kstar,in_pos=in_pos)





# ═══════════════ TERRAIN — the VS3D Gradient Chart, built to guide spec ═════════
# Guide §1.5/§1.6: models the WHOLE book (multi-expiry), 0DTE dominates naturally
# via asymptotic gamma. §7.7: greeks = Delta Change (new, combines gamma+charm,
# "path of least resistance"), Gamma, Charm (hedging-effect polarity). §2.4:
# near-linear intensity, MANUAL symmetric range (fixed cap, not per-frame
# percentile), ~35% opacity so the field sits BEHIND price. §1.5 contours:
# red=local maxima ridges, blue=local minima troughs, dotted=zero boundary.
from scipy.signal import argrelextrema

def terrain_grid(chain, spot, exps, now, greek="Delta Change", vol_adj=0.0,
                 p_min=None, p_max=None, n_price=170, n_time=84, simulated_gamma=False,
                 weighting="OI + Volume"):
    """Field Z(price,time) for the chosen greek over ALL expiries in `exps`.
    Each expiry decays on its own T(τ) across the 09:30–16:00 axis.
    Sign convention (proxy): calls +, puts − (dealer long/short NOT measured).
    Delta Change = book_delta(now) − book_delta(P,τ)  [§7.9: futures dealers must
    trade to arrive hedged at (P,τ); + = they BUY along the way (supportive)]."""
    if p_min is None: p_min=spot*0.975
    if p_max is None: p_max=spot*1.025
    pg=np.linspace(p_min,p_max,n_price)
    open_=dt.datetime.combine(now.date(),dt.time(9,30)); close=dt.datetime.combine(now.date(),dt.time(16,0))
    taus=[open_+dt.timedelta(seconds=s) for s in np.linspace(0,(close-open_).total_seconds(),n_time)]
    Z=np.zeros((n_price,n_time))
    book_now=0.0
    for es in exps:
        ce=chain[chain.get("expiry",es)==es] if "expiry" in chain.columns else chain
        ce=ce.dropna(subset=["strike","gamma"])
        if ce.empty: continue
        cc=ce[ce.type=="call"]; pp=ce[ce.type=="put"]
        def arr(df):
            K=df["strike"].values.astype(float)
            iv=np.where(df["iv"].fillna(0).values>0,df["iv"].fillna(0).values,0.15)+vol_adj
            vol=df["volume"].fillna(0).values.astype(float); oi=df["oi"].fillna(0).values.astype(float)
            # Weighting semantics (all magnitudes — none signed, none reset intraday):
            #   vol = TODAY'S CUMULATIVE session volume (Barchart resets overnight only;
            #         counts round-trips and both sides — flow, not positions)
            #   oi  = YESTERDAY'S settled open interest (OCC, static all session ≈ the
            #         opening structural book Dan says to respect, §4.5)
            if weighting=="Volume (today's flow)":      w=vol
            elif weighting=="OI (opening book)":        w=oi
            elif weighting=="Vol else OI (legacy)":     w=np.where(vol>0,vol,oi)
            else:                                       w=oi+vol   # OI + Volume (default)
            return K,iv,w
        Kc,ivc,wc=arr(cc); Kp,ivp,wp=arr(pp)
        Tn=_T_at(es,now)
        if greek=="Delta Change":
            book_now+= (wc*bs_delta(spot,Kc,Tn,ivc,True)).sum()*100 \
                      -(wp*bs_delta(spot,Kp,Tn,ivp,False)).sum()*100
        Sg=pg[:,None]
        for j,tau in enumerate(taus):
            T=_T_at(es,tau)
            if greek=="Gamma":
                if simulated_gamma:  # §2.7 finite difference over $5 (effective gamma)
                    dU=bs_delta(Sg+5,Kc[None,:],T,ivc[None,:],True); dD=bs_delta(Sg-5,Kc[None,:],T,ivc[None,:],True)
                    gc=(dU-dD)/10.0
                    dU=bs_delta(Sg+5,Kp[None,:],T,ivp[None,:],False); dD=bs_delta(Sg-5,Kp[None,:],T,ivp[None,:],False)
                    gp=(dU-dD)/10.0
                else:
                    gc=bs_gamma(Sg,Kc[None,:],T,ivc[None,:]); gp=bs_gamma(Sg,Kp[None,:],T,ivp[None,:])
                Z[:,j]+= (gc*wc[None,:]).sum(1)*100*pg - (gp*wp[None,:]).sum(1)*100*pg
            elif greek=="Charm":
                ch_c=bs_charm(Sg,Kc[None,:],T,ivc[None,:]); ch_p=bs_charm(Sg,Kp[None,:],T,ivp[None,:])
                Z[:,j]+= (ch_c*wc[None,:]).sum(1)*100 - (ch_p*wp[None,:]).sum(1)*100
            else:  # Delta Change
                dc=bs_delta(Sg,Kc[None,:],T,ivc[None,:],True); dp=bs_delta(Sg,Kp[None,:],T,ivp[None,:],False)
                Z[:,j]+= (dc*wc[None,:]).sum(1)*100 - (dp*wp[None,:]).sum(1)*100
    if greek=="Delta Change":
        Z=book_now-Z            # + = dealers BUY futures to arrive hedged there
    Z=gaussian_filter1d(Z,1.2,axis=0)   # smooth PRICE only, never time
    return pg,Z,taus

def terrain_scale(Z, mode, cap, pct):
    """§2.4: Manual symmetric range is the default — a loose day LOOKS loose.
    Percentile/StdDev kept for exploration (they rescale per frame)."""
    if mode=="Manual (fixed cap)":
        sc=cap if cap and cap>0 else (np.percentile(np.abs(Z),92) or 1.0)
    elif mode=="Percentile":
        sc=np.percentile(np.abs(Z),pct) or 1.0
    else:  # Std Dev
        sc=(2.0*np.abs(Z).std()) or 1.0
    return np.clip(Z/sc,-1,1), sc

def terrain_intensity(V, kind="Power", power=1.0, gain=3.0):
    s=np.sign(V); m=np.abs(V)
    if kind=="Sqrt": m=np.sqrt(m)
    elif kind=="Arcsinh": m=np.arcsinh(gain*m)/np.arcsinh(gain)
    else: m=np.power(m,max(power,0.05))     # Power, default 1.0 = linear (§2.4)
    return s*m

def terrain_contours(ax, Z, x0, x1, pg, cap, zero=True, ridges=True):
    """§1.5: dotted zero boundary + RED ridge lines (local maxima through time)
    and BLUE trough lines (local minima). Chains linked across adjacent columns."""
    X=np.linspace(x0,x1,Z.shape[1])
    if zero:
        try: ax.contour(X,pg,Z,levels=[0.0],colors="#e8e8e8",linewidths=1.0,
                        linestyles=(0,(4,3)),alpha=.9,zorder=6)
        except Exception: pass
    if not ridges: return
    thr=0.15*(cap or (np.abs(Z).max() or 1.0)); edge=4
    def chains(sign):
        pts={}   # col -> list of row idx (edges excluded — border artifacts)
        for j in range(Z.shape[1]):
            colv=Z[:,j]*sign
            idx=argrelextrema(colv,np.greater,order=3)[0]
            pts[j]=[i for i in idx if colv[i]>thr and edge<=i<Z.shape[0]-edge]
        used=set(); out=[]
        for j0 in range(Z.shape[1]):
            for i0 in pts.get(j0,[]):
                if (j0,i0) in used: continue
                ch=[(j0,i0)]; used.add((j0,i0)); j,i=j0,i0
                while j+1<Z.shape[1]:
                    cand=[k for k in pts.get(j+1,[]) if abs(k-i)<=4 and (j+1,k) not in used]
                    if not cand: break
                    k=min(cand,key=lambda q:abs(q-i)); ch.append((j+1,k)); used.add((j+1,k)); j,i=j+1,k
                if len(ch)>=8: out.append(ch)
        return out
    for ch in chains(+1):
        ax.plot([X[j] for j,_ in ch],[pg[i] for _,i in ch],color="#ff5a6a",lw=0.9,alpha=.85,zorder=6)
    for ch in chains(-1):
        ax.plot([X[j] for j,_ in ch],[pg[i] for _,i in ch],color="#4aa8ff",lw=0.9,alpha=.85,zorder=6)

def terrain_straddle(chain0, spot):
    """ATM straddle (mid) from the 0DTE chain — Dan's range tool (§5.3)."""
    c=chain0.dropna(subset=["strike"])
    if c.empty: return None
    ks=c["strike"].unique(); k=ks[np.argmin(np.abs(ks-spot))]
    def mid(df):
        if df.empty: return np.nan
        b=df["bid"].iloc[0] or 0; a=df.get("ask",df["bid"]).iloc[0] or b
        return (b+a)/2 if (b or a) else np.nan
    cm=mid(c[(c.strike==k)&(c.type=="call")]); pm=mid(c[(c.strike==k)&(c.type=="put")])
    v=(0 if np.isnan(cm) else cm)+(0 if np.isnan(pm) else pm)
    return float(v) if v>0 else None



# ═══════════════ READ — cheat-sheet decision engine (gamma × charm + gates) ═════
def _book_delta_0dte(ch, spot, exp, when):
    c=ch.dropna(subset=["strike"]); T=_T_at(exp,when)
    out=0.0
    for typ,sgn in (("call",+1),("put",-1)):
        d=c[c.type==typ]
        if d.empty: continue
        K=d["strike"].values.astype(float)
        iv=np.where(d["iv"].fillna(0).values>0,d["iv"].fillna(0).values,0.15)
        w=np.where(d["volume"].fillna(0).values>0,d["volume"].fillna(0).values,d["oi"].fillna(0).values)
        out+=sgn*(w*bs_delta(spot,K,T,iv,typ=="call")).sum()*100
    return out

def _book_delta_drift(chp0, spot_prev, t_prev, spot_now, t_now, exp):
    """d(book delta) holding the BOOK FIXED (prev snapshot's strikes/iv/weights),
    repriced at the two (spot,T) states. Isolates hedge drift (charm + spot move)
    from WEIGHT GROWTH: volume accumulating between snapshots is new positioning,
    not decay of the existing book (v2.2.0 — the 61k-minis/5min audit)."""
    c=chp0.dropna(subset=["strike"]); out=0.0
    Tn=_T_at(exp,t_now); Tp=_T_at(exp,t_prev)
    for typ,sgn in (("call",+1),("put",-1)):
        d=c[c.type==typ]
        if d.empty: continue
        K=d["strike"].values.astype(float)
        iv=np.where(d["iv"].fillna(0).values>0,d["iv"].fillna(0).values,0.15)
        w=np.where(d["volume"].fillna(0).values>0,d["volume"].fillna(0).values,d["oi"].fillna(0).values)
        out+=sgn*(w*(bs_delta(spot_now,K,Tn,iv,typ=="call")-bs_delta(spot_prev,K,Tp,iv,typ=="call"))).sum()*100
    return out

def read_verdict(snaps, exps, now, track=True):
    """Cheat-sheet logic → what happens next. Returns dict of lines + confidence.
    gamma sign (env) × charm lean (direction) = four patterns; gated by charm clock,
    straddle check, VIX regime, fishbone, absorption. All proxy-honest."""
    latest=snaps[-1]; spot=latest["spot"]; e0=exps[0]
    ch=latest["chain"]; ch0=ch[ch["expiry"]==e0] if "expiry" in ch.columns else ch
    r=pinak_levels(ch0,spot,e0,now)
    # ---- gamma environment: sign at spot from flip side + magnitude vs trailing
    gsign=+1 if (r["flip"] is None or spot>=r["flip"]) else -1
    K=r["K"]; gnow=float(np.interp(spot,K,np.abs(r["net_gex"])))
    hh=st.session_state.setdefault("read_gmag",[])
    if track: hh.append(gnow); hh[:] = hh[-60:]
    pct=float(np.mean(np.array(hh)<=gnow))*100 if len(hh)>2 else 50.0
    env=("HEAVY γ (top decile — saturated, pinned)" if pct>=90 else
         "LIGHT γ (bottom quartile — moves come easier)" if pct<=25 else
         f"NORMAL γ ({pct:.0f}th pctile of session)")
    if gsign<0: env="NEGATIVE γ side of flip — dealers chase, trend/expansion"
    # ---- charm lean: empirical d(book delta)/dt if 2+ snaps, else BS book charm
    lean=None; src="model"
    if len(snaps)>=2:
        prev=snaps[-2]; chp=prev["chain"]; chp0=chp[chp["expiry"]==prev["exps"][0]] if "expiry" in chp.columns else chp
        hrs=max((latest["ts"]-prev["ts"]).total_seconds()/3600.0,1/60)
        dbook=_book_delta_drift(chp0,prev["spot"],prev["ts"].replace(tzinfo=None),spot,now,e0)/hrs
        lean=("SELL flow (drift down)" if dbook>0 else "BUY flow (drift up)"); src="empirical Δδ/Δt"
        flow5=abs(dbook)/12.0*(2/100.0)   # ≈ e-mini per 5 min (×−2 per exposure, /100 per contract-δ)
    else:
        c=ch0.dropna(subset=["strike"]); T=_T_at(e0,now); dbook=0.0
        for typ,sgn in (("call",+1),("put",-1)):
            d=c[c.type==typ]
            if d.empty: continue
            Kk=d["strike"].values.astype(float)
            iv=np.where(d["iv"].fillna(0).values>0,d["iv"].fillna(0).values,0.15)
            w=np.where(d["volume"].fillna(0).values>0,d["volume"].fillna(0).values,d["oi"].fillna(0).values)
            dbook+=sgn*(w*bs_charm(spot,Kk,T,iv)).sum()*100
        lean=("SELL flow (drift down)" if dbook>0 else "BUY flow (drift up)"); flow5=abs(dbook)/(365*24*12)*2/100
    up=lean.startswith("BUY")
    # ---- gates
    strad_now=terrain_straddle(ch0,spot)
    _so=st.session_state.get("strad_open_"+now.strftime("%Y-%m-%d"))
    if _so and _so[0]:
        strad_open=float(_so[0]); open_lbl=f"open {_so[1]}"
    else:
        first=snaps[0]; chf=first["chain"]; chf0=chf[chf["expiry"]==first["exps"][0]] if "expiry" in chf.columns else chf
        strad_open=terrain_straddle(chf0,first["spot"]) if len(snaps)>=2 else None
        open_lbl="open (1st snap)"
    decay=("n/a — need open reference" if (not strad_now or not strad_open) else
           "COLLAPSING — very local, pin tightens" if strad_now<0.45*strad_open else
           "DECAYING — charm signal live" if strad_now<0.995*strad_open else
           "FLAT/REPRICING — stand down (snake-oil check)")
    t=now.time()
    clock=("OPEN 9:30–11 — external flow, avoid charm" if t<dt.time(11,0) else
           "MIDDAY 11–1:30 — settling, building" if t<dt.time(13,30) else
           "SWEET SPOT 1:30–3 — best charm window" if t<=dt.time(15,0) else
           "CLOSE 3–4 — very local, pin resolution")
    vix=latest.get("vix"); vixline=vs3d_vix_regime(vix)
    vixline+=(" · live (TVC)" if latest.get("vix_src")=="tvc" else
              (" · TVC feed unavailable" if latest.get("vix") is None else ""))
    fish=vs3d_fishbone(ch0)
    fishline=("clean structure" if fish<=4 else "messy — size down" if fish<=8 else "FISHBONE — sit out")
    # absorption vs charm flow toward the lean-side bound (§5.4 / sheet: gamma absorbs charm)
    c=ch0.dropna(subset=["strike","delta"])
    w=np.where(c["oi"].fillna(0)>0,c["oi"].fillna(0),c["volume"].fillna(0)).astype(float)  # absorption = EXISTING book (v2.2.0)
    dlt=c["delta"].fillna(0).values; Ks=c["strike"].values
    rem=np.abs(np.where(dlt>=0,1-dlt,-1-dlt))*w*100/50.0
    bound=spot+(strad_now or spot*0.004)*(1 if up else -1)
    mask=(Ks>spot)&(Ks<=bound) if up else (Ks<spot)&(Ks>=bound)
    absorb=float(rem[mask].sum()); swallowed=absorb>0 and flow5*24>0 and absorb>flow5*24*3
    # ---- four-pattern verdict
    if gsign>0 and up:    pat,do=("CHOP, LEANS UP — grind toward resistance, pin near anchor","call flies / spreads · sell the target strike")
    elif gsign>0:         pat,do=("CHOP, LEANS DOWN — drift lower but contained, fade extremes","put flies / spreads · sell the target strike")
    elif up:              pat,do=("BULL EXPANSION — squeeze higher, needs a trigger","long calls / single-leg · never fade the void")
    else:                 pat,do=("BEAR FLUSH — sell-off/expansion, needs a trigger","long puts / put flies · never fade the void")
    target=r["pin"]; wall_up=r["call_wall"]; wall_dn=r["put_wall"]
    through=(wall_up if up else wall_dn)          # first wall in the LEAN direction — price must clear it
    tension=None
    if target and ((up and target<spot) or ((not up) and target>spot)):
        tension=f"PIN {target:,.0f} sits {'ABOVE' if target>spot else 'BELOW'} against the charm lean — pin-vs-charm tension, respect the weaker read"
        to=spot+(strad_now or spot*0.004)*(1 if up else -1)   # lean-side straddle bound instead
    else:
        to=target if target else spot+(strad_now or spot*0.004)*(1 if up else -1)
    # ---- confidence
    conf=50
    conf+= 15 if decay.startswith("DECAYING") else (5 if decay.startswith("COLLAPSING") else (-15 if decay.startswith("FLAT") else 0))
    conf+= 10 if clock.startswith("SWEET") else (5 if clock.startswith("MIDDAY") else (-10 if clock.startswith("OPEN") else 0))
    conf+= (10 if (vix and vix<16) else -15 if (vix and vix>=20) else 0)
    conf+= -20 if fish>8 else (-8 if fish>4 else 0)
    conf+= -12 if swallowed else 0
    conf+= -10 if gsign<0 else 0     # needs a trigger we cannot see
    if fish>8: conf=min(conf,25)      # cheat sheet: FISHBONE = SIT OUT — hard cap
    conf=int(max(5,min(95,conf)))
    nxt=(f"expect drift {'UP' if up else 'DOWN'} toward {to:,.0f}" if to else f"expect drift {'UP' if up else 'DOWN'}")
    if gsign>0:
        rails=[x for x in (wall_up,wall_dn) if x and (not to or abs(x-to)>1)]
        if rails: nxt+=", repelled near "+" / ".join(f"{x:,.0f}" for x in rails)
        if target and to and abs(target-to)<=1: nxt+=f", settle ≈ PIN {target:,.0f} into close"
    if gsign<0: nxt+=" IF a trigger arrives — without one it floats (γ is a multiplier, not a generator)"
    if swallowed: nxt+=f" · WARNING: ~{absorb:,.0f} minis of γ absorption in path — pin may land short (profile consumes itself)"
    if tension: nxt+="  ·  "+tension
    return dict(pat=pat,do=do,env=env,lean=lean+f"  [{src} · ≈{flow5:,.0f} minis/5min proxy]",
                decay=decay,clock=clock,vix=vixline,fish=f"{fishline} (score {fish})",
                nxt=nxt,conf=conf,through=through,to=to,spot=spot,wall_up=wall_up,wall_dn=wall_dn,pin=target,
                strad=f"\\${strad_now:.2f}" if strad_now else "n/a",open_lbl=open_lbl)

def gex_cmap():
    return mcolors.LinearSegmentedColormap.from_list("gex",
        [(0.0,(0.50,0,0)),(0.34,(0.86,0.06,0.06)),(0.47,(0.10,0,0)),
         (0.50,(0,0,0)),(0.53,(0,0.10,0)),(0.66,(0.10,0.74,0.18)),(1.0,(0.02,0.42,0.06))])
def charm_cmap():
    return mcolors.LinearSegmentedColormap.from_list("charm",
        [(0.0,(0.42,0.24,0)),(0.34,(0.86,0.58,0.02)),(0.47,(0.10,0.06,0)),
         (0.50,(0,0,0)),(0.53,(0,0.05,0.12)),(0.66,(0.12,0.52,0.95)),(1.0,(0.02,0.22,0.58))])
def heat_cmap():
    """|Γ| heaviness (v2.2.2): single hue — bright = heavy book, direction UNKNOWN by design."""
    return mcolors.LinearSegmentedColormap.from_list("vs3dheat",
        [(0.0,(0.05,0.07,0.09)),(0.30,(0.05,0.22,0.26)),(0.60,(0.10,0.50,0.55)),
         (0.85,(0.22,0.82,0.85)),(1.0,(0.85,0.99,1.0))])
def decay_cmap():
    """Gamma Decay / 'color' (v2.2.2): orange = gamma BUILDING as the clock runs · purple = fading."""
    return mcolors.LinearSegmentedColormap.from_list("vs3ddecay",
        [(0.0,(0.42,0.20,0.75)),(0.42,(0.09,0.05,0.14)),(0.50,(0,0,0)),
         (0.58,(0.16,0.10,0.03)),(1.0,(1.0,0.62,0.20))])
def _decay_shift(Z,taus,mins=30):
    """Γ(P,τ+Δ)−Γ(P,τ): where the book's gamma is BUILDING as time passes — the
    'color' greek made explicit (v2.2.2). Positive = pin energy accumulating."""
    n=Z.shape[1]
    if n<3: return np.zeros_like(Z)
    span_min=max((taus[-1]-taus[0]).total_seconds()/60.0,1.0)
    step=max(1,int(round(mins/(span_min/max(n-1,1)))))
    j2=np.minimum(np.arange(n)+step,n-1)
    return Z[:,j2]-Z
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
    # resample 1-min -> 5-min OHLC (less busy candles); anchor to :30 so 09:30 aligns
    try:
        b=bars.set_index("t")
        agg=b.resample("5min",offset="0min",label="left",closed="left").agg(
            {"o":"first","h":"max","l":"min","c":"last"}).dropna(subset=["o","h","l","c"]).reset_index()
        if len(agg)>0: bars=agg
    except Exception:
        pass
    msg=(f"showing {sess} RTH ({len(bars)} 5-min bars, to {bars['t'].max():%H:%M} EST)"
         + (" — today not in feed yet, prior session" if stale else ""))
    return bars,msg

# ════════════════════════════ snapshot taking ═══════════════════════════════
def fetch_vix_live():
    """VIX from TradingView TVC:VIX via tvdatafeed — the ONLY VIX source
    (user rule: never Barchart $VIX). Last 1-min close; None on any failure,
    which the Read tab reports as “TVC feed unavailable”. 5–200 sanity band."""
    try:
        from tvDatafeed import TvDatafeed, Interval
        tv=TvDatafeed()
        df=tv.get_hist(symbol="VIX",exchange="TVC",interval=Interval.in_1_minute,n_bars=2)
        if df is not None and len(df):
            v=float(df["close"].iloc[-1])
            if 5.0<v<200.0: return v
    except Exception: pass
    return None


# ════════════════════ GBT ingestion (vGBT-0.1) ═══════════════════════════════
# Conventions verified by probe rounds 1-3 (07-09): CSV-in-JSON envelope; epoch-ms;
# IV percent-style; exposure calls>=0/puts<=0 BY CONSTRUCTION (naive); PER_$1 = RAW×spot;
# snapshotTime/startTime SERVER-BROKEN (502) — hard-blocked below.
GBT_BASE="https://api.groupbuytrading.com/v1"
def _gbt_token():
    tok=""
    try: tok=str(st.secrets.get("GBT_TOKEN","")).strip()
    except Exception: tok=""
    if not tok:
        try: tok=str(st.session_state.get("gbt_tok_input","")).strip()
        except Exception: tok=""
    return tok
import io as _io
def _gbt_post(ep,payload,retries=2):
    assert "snapshotTime" not in payload and "startTime" not in payload, "server-broken params (502)"
    err=None
    for a in range(retries+1):
        try:
            _tok=_gbt_token()
            if not _tok: raise RuntimeError("GBT token missing — add GBT_TOKEN to app Secrets (see deploy guide) or paste it in the sidebar")
            r=requests.post(f"{GBT_BASE}/{ep}",json=payload,timeout=25,
                headers={"Authorization":f"Bearer {_tok}","Content-Type":"application/json"})
            if r.status_code==200:
                j=r.json(); raw=j.get("data","") or ""
                meta={}; lines=raw.split("\n"); i=0
                while i<len(lines) and ("=" in lines[i] or lines[i].strip()==""):
                    s2=lines[i].strip()
                    if s2 and "=" in s2:
                        k,_,v=s2.partition("="); meta[k.strip()]=v.strip()
                    i+=1
                body="\n".join(lines[i:]).strip()
                df=pd.read_csv(_io.StringIO(body)) if body else pd.DataFrame()
                return meta,df
            err=f"HTTP {r.status_code}"
            if r.status_code==429: _time.sleep(6.0*(a+1)); continue   # documented budget: back off
        except Exception as ex: err=f"{type(ex).__name__}: {ex}"
        _time.sleep(1.0+a)
    raise RuntimeError(f"GBT {ep} failed: {err}")
def _pct_iv(s):
    s=pd.Series(s,dtype=float); med=s.dropna().median()
    return s/100.0 if (med==med and med>3.0) else s
def _bs_price(S,K,T,sig,cp):
    T=max(T,1e-9); sig=max(sig,1e-4)
    d1=(np.log(S/K)+0.5*sig*sig*T)/(sig*np.sqrt(T)); d2=d1-sig*np.sqrt(T)
    if cp=="call": return S*norm.cdf(d1)-K*norm.cdf(d2)
    return K*norm.cdf(-d2)-S*norm.cdf(-d1)
def assemble_gbt_chain(frames,spot,exp,now):
    """Per-strike 2-row chain from GBT heat frames — SAME schema as fetch_chain, so the
    whole v2.2.2 stack runs unchanged. bid=ask=BS-mid (terrain_straddle reads mids)."""
    T=_T_at(exp,now)
    def _m(df,col="value"): return df.set_index("strikePrice")[col].to_dict() if df is not None and len(df) else {}
    civ,piv=_pct_iv(frames["civ"].set_index("strikePrice")["value"]),_pct_iv(frames["piv"].set_index("strikePrice")["value"])
    cde,pde=_m(frames["cdelta"]),_m(frames["pdelta"]); cga,pga=_m(frames["cgamma"]),_m(frames["pgamma"])
    noi,nvl=frames["noi"].set_index("strikePrice"),frames["nvol"].set_index("strikePrice")
    def _guard_delta(d,put=False):
        s=pd.Series(d,dtype=float)
        if len(s.dropna()) and s.abs().median()>1.5: s=s/100.0
        if put and len(s.dropna()) and s.median()>0: s=-s
        return s.to_dict()
    cde,pde=_guard_delta(cde),_guard_delta(pde,put=True)
    rows=[]
    for k in sorted(set(civ.index)|set(piv.index)):
        for typ,ivs,des,gas,side in (("call",civ,cde,cga,"callValue"),("put",piv,pde,pga,"putValue")):
            iv=float(ivs.get(k,np.nan))
            if not (iv==iv) or iv<0.005: continue          # dead quote (0.0477% wings)
            ga=float(gas.get(k,np.nan))
            if ga==ga and abs(ga)>1.0: ga=ga/100.0
            mid=_bs_price(spot,float(k),T,iv,typ)
            rows.append(dict(strike=float(k),type=typ,iv=iv,gamma=ga,
                delta=float(des.get(k,np.nan)),
                oi=abs(float(noi[side].get(k,0) or 0)),volume=abs(float(nvl[side].get(k,0) or 0)),
                bid=mid,ask=mid,expiry=exp))
    ch=pd.DataFrame(rows)
    if ch.empty: raise RuntimeError("GBT chain empty — all quotes dead?")
    if not ch["iv"].dropna().empty:
        _am=float(ch["iv"].dropna().median())
        assert 0.005<_am<3.0, f"GBT IV units suspicious after normalization: median {_am}"
    return ch
# ── vGBT-0.2: flow-inferred dealer signs (seed = YESTERDAY's flow on TODAY's expiry) ─
def _gbt_prev_session(d=None):
    dd=(d or today_est())-dt.timedelta(days=1)
    while dd.weekday()>=5: dd-=dt.timedelta(days=1)
    return dd.strftime("%Y-%m-%d")
def _side_net_total(df):
    """{type:(net customer initiative, total)} from a side-stats frame.
    net=(ABOVE_ASK+ASK)-(BID+BELOW_BID); MID is direction-ambiguous by design."""
    out={}
    if df is None or getattr(df,"empty",True): return out
    for typ,g in df.groupby("contractType"):
        m=dict(zip(g["tradeSideCode"],g["value"]))
        net=(m.get("ABOVE_ASK",0)+m.get("ASK",0))-(m.get("BID",0)+m.get("BELOW_BID",0))
        out[str(typ).lower()]=(float(net),float(sum(m.values())))
    return out
def _gbt_side_stats(exp,strike,session_date=None):
    p={"dataMode":"VOLUME","tickers":["SPX"],"expirationDates":[exp],"strikePrices":[float(strike)]}
    if session_date: p["sessionDate"]=session_date
    _,df=_gbt_post("contract_trade_side_statistics",p); return df
def gbt_dsign_map(exp,strikes,spot):
    """{(strike,type): dsign in [-1,1]} — dealer direction × confidence.
    Seed fetched ONCE per day (yesterday is immutable; server caches 24h; paced
    inside the 30/min budget — the FIRST snapshot of the day takes ~1-2 min) and
    persisted to disk; today's CUMULATIVE side stats refreshed each snapshot for
    the 10 top-OI + 4 nearest-ATM strikes."""
    ss=st.session_state
    seedk=f"gbt_seed_{exp}"; livek=f"gbt_live_{exp}"
    seed=ss.get(seedk)
    if seed is None:
        # anchor the sweep to YESTERDAY's close ±2% (the session that built this book),
        # union the live window's strikes — intraday drift can't orphan a strike
        try:
            _pc=ss.get("gbt_seed_prevclose")
            if _pc is None:
                _,_pb=_gbt_post("stock_price_over_time",{"ticker":"SPX",
                        "aggregationPeriod":"FIVE_MINUTE","sessionDate":_gbt_prev_session()})
                _pc=float(_pb.iloc[-1]["closePrice"]) if _pb is not None and len(_pb) else float(spot)
                ss["gbt_seed_prevclose"]=_pc
        except Exception: _pc=float(spot)
        _g0,_g1=round(_pc*0.98/5)*5,round(_pc*1.02/5)*5
        strikes=sorted(set([float(k) for k in strikes])|
                       set(float(_g0+i*5) for i in range(int((_g1-_g0)/5)+1)))
        seed={}; _errs=[]
        for k in strikes:
            try: seed[float(k)]=_side_net_total(_gbt_side_stats(exp,k,_gbt_prev_session()))
            except Exception as _se:
                seed[float(k)]={}; _errs.append(f"{k:g}: {type(_se).__name__}")
            _time.sleep(2.3)                      # ≤26/min — inside the documented 30/min budget
        ss[seedk]=seed
        ss["gbt_seed_meta_"+exp]={"ok":sum(1 for v in seed.values() if v),
                                  "n":len(seed),"errs":_errs[-3:]}
        save_day_state()
    live=ss.get(livek,{})
    def _wt(k):
        d=seed.get(float(k),{}); return sum(t for _,t in d.values()) if d else 0.0
    hot=sorted(strikes,key=_wt,reverse=True)[:10]
    atm=sorted(strikes,key=lambda k:abs(float(k)-spot))[:4]
    for k in dict.fromkeys([*hot,*atm]):
        try: live[float(k)]=_side_net_total(_gbt_side_stats(exp,k))
        except Exception: pass
    ss[livek]=live
    _m=ss.get("gbt_seed_meta_"+exp,{}); _m["live"]=len(live); ss["gbt_seed_meta_"+exp]=_m
    out={}
    for k in strikes:
        kf=float(k); s=seed.get(kf,{}); l=live.get(kf,{})
        for typ in ("call","put"):
            n1,t1=s.get(typ,(0.0,0.0)); n2,t2=l.get(typ,(0.0,0.0))
            net,tot=n1+n2,t1+t2
            if tot>0: out[(kf,typ)]=float(np.clip(-net/tot,-1.0,1.0))
    return out

def gbt_snapshot_frame(window_pct):
    """One snapshot: wide exposure (spot from preamble + Book bars) then 8 heat calls."""
    meta,expo=_gbt_post("exposure_by_strike",{"greekMode":"GAMMA","representationMode":"PER_ONE_DOLLAR_MOVE",
        "ticker":"SPX","expirationDates":[today_est().strftime("%Y-%m-%d")],
        "strikePriceRange":{"min":5000,"max":9500}})
    spot=float(meta.get("SPX.stockPrice") or 0.0)
    if not spot: raise RuntimeError("GBT spot missing from exposure preamble")
    exp=today_est().strftime("%Y-%m-%d")
    lo,hi=round(spot*(1-window_pct)/5)*5,round(spot*(1+window_pct)/5)*5
    H=lambda m:_gbt_post("heat_map",{"dataMode":m,"ticker":"SPX","expirationDates":[exp],
        "strikePriceRange":{"min":lo,"max":hi}})[1]
    frames=dict(civ=H("CALL_IMPLIED_VOLATILITY"),piv=H("PUT_IMPLIED_VOLATILITY"),
        cdelta=H("CALL_DELTA"),pdelta=H("PUT_DELTA"),cgamma=H("CALL_GAMMA"),pgamma=H("PUT_GAMMA"),
        noi=H("NET_OPEN_INTEREST"),nvol=H("NET_VOLUME"))
    chain=assemble_gbt_chain(frames,spot,exp,now_est())
    bk=expo.rename(columns={"strikePrice":"strike","callExposureSum":"call_pd","putExposureSum":"put_pd"})
    bk=bk[(bk["strike"]>=lo)&(bk["strike"]<=hi)][["strike","call_pd","put_pd"]].reset_index(drop=True)
    try:
        if GBT_SIGNED:
            _dm=gbt_dsign_map(exp,sorted(chain["strike"].unique().tolist()),spot)
            chain["dsign"]=[_dm.get((float(t.strike),t.type),np.nan) for t in chain.itertuples()]
    except Exception as _sx:
        try: st.sidebar.caption(f"⚠ signed inference degraded → naive this frame: {type(_sx).__name__}")
        except Exception: pass
    return spot,chain,bk,exp
def book_figure(book,spot,straddle,lo,hi,side="Total",prev=None,openb=None,signed=None,sqrt_scale=False):
    def _tx(v): return np.sign(v)*np.sqrt(np.abs(v)) if sqrt_scale else v
    """VS3D 'Positions by Strike' analogue. Bars in e-minis per $1 (per-$1 ÷ 50).
    NAIVE calls+/puts− convention — measured signing arrives with the flow ledger."""
    fig,ax=plt.subplots(figsize=(6.5,9)); fig.patch.set_facecolor("#0e1117"); ax.set_facecolor("#0e1117")
    if signed is not None and len(signed):
        sg=signed[(signed["strike"]>=lo)&(signed["strike"]<=hi)].reset_index(drop=True)
        for _,r in sg.iterrows():
            v=_tx(float(r["signed_pct"])/1e6)
            ax.barh(float(r["strike"]),v,height=3.6,zorder=3,
                    color=("#26a69a" if v>=0 else "#ef5350"),
                    alpha=0.35+0.6*min(1.0,float(r.get("conf",0.5))))
        ax.set_xlabel(("√" if sqrt_scale else "")+"dealer GEX $M per 1% — MM-inferred (flow-signed · opacity = confidence)",color="#aaa",fontsize=8)
        prev=openb=None
    else:
        b=book.copy(); b=b[(b["strike"]>=lo)&(b["strike"]<=hi)]
        c=b["call_pd"].fillna(0)/50.0; p=b["put_pd"].fillna(0)/50.0; ks=b["strike"].values
        if side=="Calls": vals=c.values; cols=["#26a69a"]*len(ks)
        elif side=="Puts": vals=p.values; cols=["#ef5350"]*len(ks)
        else: vals=(c+p).values; cols=["#26a69a" if v>=0 else "#ef5350" for v in vals]
        ax.barh(ks,_tx(np.asarray(vals,float)),height=3.6,color=cols,alpha=0.9,zorder=3)
    def _dots(src,color,lbl):
        if src is None or getattr(src,"empty",True): return
        s2=src[(src["strike"]>=lo)&(src["strike"]<=hi)]
        c2=s2["call_pd"].fillna(0)/50.0; p2=s2["put_pd"].fillna(0)/50.0
        v2=c2.values if side=="Calls" else (p2.values if side=="Puts" else (c2+p2).values)
        ax.scatter(_tx(np.asarray(v2,float)),s2["strike"].values,s=14,color=color,zorder=4,label=lbl)
    _dots(prev,"#e0e0e0","prev snap"); _dots(openb,"#6f9bd1","market open")
    ax.axhline(spot,color="w",lw=0.9,ls="--",alpha=0.8)
    ax.text(ax.get_xlim()[1],spot,f" {spot:.2f}",color="w",va="center",fontsize=8)
    if straddle:
        for yy,tag in ((spot+straddle,f"+{straddle:.2f}"),(spot-straddle,f"-{straddle:.2f}")):
            ax.axhline(yy,color="#c084fc",lw=0.9,ls=":",alpha=0.9)
            ax.text(ax.get_xlim()[1],yy,f" {yy:.2f} ({tag})",color="#c084fc",va="center",fontsize=7)
    ax.axvline(0,color="#666",lw=0.8)
    if signed is None or not len(signed):
        ax.set_xlabel(("√" if sqrt_scale else "")+"e-minis per $1 (naive calls+ / puts−)",color="#aaa",fontsize=8)
    ax.tick_params(colors="#aaa",labelsize=7)
    for _sp in ax.spines.values(): _sp.set_color("#333")
    if prev is not None or openb is not None: ax.legend(loc="lower right",fontsize=7,facecolor="#0e1117",labelcolor="#ccc")
    ax.set_ylim(lo,hi); fig.tight_layout(); return fig

def take_snapshot(num_expiries):
    # vGBT-0.1: GBT is the chain source; num_expiries kept for UI compat (0DTE only).
    spot,chain,book,exp=gbt_snapshot_frame(window_pct)
    exps=[exp]
    # VIX: TradingView TVC:VIX ONLY (user rule — never Barchart $VIX; its free
    # quote can lag, and a stale LOW during a spike is worse than an honest n/a).
    vix=fetch_vix_live(); vix_src=("tvc" if vix is not None else None)
    ts=now_est()
    _dk="strad_open_"+ts.strftime("%Y-%m-%d")
    if _dk not in st.session_state:
        try:
            _s0=terrain_straddle(chain,spot)
            if _s0: st.session_state[_dk]=(float(_s0),ts.strftime("%H:%M"))
        except Exception: pass
    st.session_state.snaps.append(dict(ts=ts,spot=spot,chain=chain,exps=exps,vix=vix,vix_src=vix_src,book=book))
    st.session_state.last_ts=ts
    save_day_state()
    return spot,exps

# ── day-state persistence (v2.2.2): a browser reload must cost NOTHING ───────
import os as _os, pickle as _pickle, glob as _glob
def _state_path(d=None):
    return f"/tmp/vs3dgbt_state_{d or now_est().strftime('%Y-%m-%d')}.pkl"
def save_day_state():
    """Write snaps/frames/day-keys to /tmp after each snapshot. Survives F5 and new
    tabs; dies only with the container. Fails LOUD-ish (sidebar note), never silent."""
    try:
        ss=st.session_state
        blob={"snaps":ss.get("snaps",[]),"frames":ss.get("frames",{}),"last_ts":ss.get("last_ts"),
              "keys":{k:ss[k] for k in list(ss.keys())
                      if str(k).startswith(("strad_open_","terr_cap_","terr_hist_","read_gmag","gbt_seed_","gbt_live_"))}}
        with open(_state_path(),"wb") as f: _pickle.dump(blob,f,protocol=4)
        for _old in _glob.glob("/tmp/vs3dgbt_state_*.pkl"):
            if _old!=_state_path() and _os.path.getmtime(_old)<_time.time()-2*86400:
                try: _os.remove(_old)
                except Exception: pass
    except Exception as ex:
        st.sidebar.caption(f"⚠ state save failed: {type(ex).__name__}: {ex}")
def load_day_state():
    try:
        p=_state_path()
        if not _os.path.exists(p): return 0
        with open(p,"rb") as f: blob=_pickle.load(f)
        if not blob.get("snaps"): return 0
        st.session_state.snaps=blob["snaps"]; st.session_state.frames=blob.get("frames",{})
        st.session_state.last_ts=blob.get("last_ts")
        for k,v in blob.get("keys",{}).items(): st.session_state[k]=v
        return len(st.session_state.snaps)
    except Exception as ex:
        st.sidebar.caption(f"⚠ state restore failed: {type(ex).__name__}: {ex}"); return 0

# ════════════════════════════ UI ════════════════════════════════════════════
if "snaps" not in st.session_state: st.session_state.snaps=[]
if not st.session_state.snaps:
    _n=load_day_state()
    if _n: st.sidebar.success(f"🔁 restored {_n} snapshots from disk (reload-proof since v2.2.2)")
if "last_ts" not in st.session_state: st.session_state.last_ts=None

st.sidebar.title("vs3dGBT · SPX 0DTE")
st.sidebar.caption("vGBT-0.5 · GBT data · flow-signed · engine = v2.2.2")
try:
    if not _gbt_token():
        st.sidebar.text_input("GBT token (or set app Secrets: GBT_TOKEN)",type="password",key="gbt_tok_input")
except Exception: pass
num_expiries=st.sidebar.slider("Expiries to aggregate",1,5,1,help="1 = 0DTE only (default — the gradient chart is a 0DTE tool; asymptotics own the field). Raise to model the whole book (§1.5).")
window_pct=st.sidebar.slider("Price window ±%",1.0,5.0,2.0,0.5)/100.0
smooth_frac=st.sidebar.slider("Gradient smoothing",0.0,5.0,1.0,0.25,
    help="0 = raw per-strike detail (bumpy, like vols3d), higher = smoother density")/100.0
# field scale controls — TOP LEVEL on purpose (v2.1.7): mid-session you must not
# have to dig through a collapsed drawer to fix a saturated cap.
capc1,capc2=st.sidebar.columns(2)
if capc1.button("Calibrate range",use_container_width=True):
    for k in [k for k in st.session_state.keys() if k.startswith("terr_hist_")]:
        h=st.session_state.get(k,[])
        if h: st.session_state["terr_cap_"+k[len("terr_hist_"):]]=1.3*float(np.mean(h[-24:]))
if capc2.button("Reset cap",use_container_width=True):
    for k in [k for k in list(st.session_state.keys()) if k.startswith("terr_cap_")]: st.session_state.pop(k,None)
st.sidebar.caption("Field scale (§2.4 fixed cap) — Reset at the open · Calibrate after 2–3 snapshots.")
if st.sidebar.button("♻ Re-run signed seed",
        help="Discards the persisted flow-seed and re-sweeps yesterday's flow on today's expiry (~2 min, paced). Use if the seed badge shows failures or the start looked broken."):
    for _k in [k for k in list(st.session_state.keys()) if str(k).startswith(("gbt_seed_","gbt_live_"))]:
        st.session_state.pop(_k,None)
    save_day_state()
    with st.spinner("re-sweeping yesterday's flow + fresh snapshot (~2-2.5 min)..."):
        try: take_snapshot(num_expiries)
        except Exception as _rx: st.sidebar.error(f"re-seed failed: {type(_rx).__name__}: {_rx}")
    st.sidebar.success("book re-seeded + fresh snapshot taken")
GBT_SIGNED=st.sidebar.checkbox("Signed dealer inference (flow-seeded)",value=True,
    help="Dealer signs from aggressor flow: yesterday's flow on today's expiry seeds the book pre-open; today's flow updates it live. Drives the gradient AND the Book bars. OFF = naive calls+/puts−.")
try:
    _gm=[v for k,v in st.session_state.items() if str(k).startswith("gbt_seed_meta_")]
    if _gm:
        _g=_gm[0]
        _cov=f"🧬 signed seed {_g.get('ok','?')}/{_g.get('n','?')} strikes · live {_g.get('live',0)}"
        if _g.get("errs"): _cov+=f" · ⚠ {len(_g['errs'])}+ failed (last: {_g['errs'][-1]})"
        (st.sidebar.warning if _g.get("ok",0)<0.5*max(1,_g.get("n",1)) else st.sidebar.caption)(_cov)
except Exception: pass
book_on=st.sidebar.checkbox("Book panel (by strike)",value=True,
    help="GBT dealer book per 5-pt strike — VS3D 'Positions by Strike' analogue. NAIVE calls+/puts− (measured signing arrives with the flow ledger).")
with st.sidebar.expander("📊 Book controls", expanded=False):
    b_mode=st.radio("Bars",["MM-inferred (signed)","Naive calls+/puts−"],index=0)
    if st.button("➕ zoom in (strikes)"):  st.session_state["book_zoom"]=max(0.25,st.session_state.get("book_zoom",1.0)*0.7)
    if st.button("➖ zoom out (strikes)"): st.session_state["book_zoom"]=min(1.0,st.session_state.get("book_zoom",1.0)/0.7)
    if st.button("↔ full fetched range"):  st.session_state["book_zoom"]=1.0
    b_sqrt=st.checkbox("√ scale (compress towers)",value=True,
        help="sign(v)·√|v| — the 7475/7500 monsters stop flattening every other strike. Same trick as the reference chart.")
    b_side=st.radio("Show (naive mode)",["Total","Calls","Puts"],index=0,horizontal=True)
    b_dots=st.checkbox("Comparison dots (prev + open)",value=True)
    b_strad=st.checkbox("1× straddle lines",value=True)
with st.sidebar.expander("🗺 Terrain controls", expanded=False):
    if st.button("➕ zoom in (terrain)"):  st.session_state["terr_zoom"]=max(0.25,st.session_state.get("terr_zoom",1.0)*0.7)
    if st.button("➖ zoom out (terrain)"): st.session_state["terr_zoom"]=min(1.0,st.session_state.get("terr_zoom",1.0)/0.7)
    if st.button("↔ full range (terrain)"): st.session_state["terr_zoom"]=1.0
    t_greek=st.selectbox("Greek",["Delta Change","Gamma","Charm","Gamma |Γ| (heaviness)","Gamma Decay (color)"],index=1,   # default = Gamma (standing user preference)
        help="Delta Change (§7.7): futures dealers must trade to arrive hedged at each price/time — combines gamma+charm; path of least resistance.")
    t_wt=st.selectbox("Weighting",["OI + Volume","OI (opening book)","Volume (today's flow)","Vol else OI (legacy)"],index=0,
        help="OI = yesterday's settled book (static all day, ≈ the opening position §4.5 says to respect). "
             "Volume = today's CUMULATIVE session flow (resets overnight only; counts round-trips — flow, not positions). "
             "OI+Volume = structural book + today's flow (default). Legacy = old per-strike fallback rule.")
    t_norm=st.selectbox("Range",["Manual (fixed cap)","Percentile","Std Dev"],index=0,
        help="Manual (guide §2.4): fixed symmetric cap so a loose day LOOKS loose. Percentile rescales every frame.")
    t_pct=st.slider("Percentile hi",80,99,95) if t_norm=="Percentile" else 95
    t_int=st.selectbox("Intensity",["Power","Sqrt","Arcsinh"],index=0)
    t_pow=st.slider("Power exponent",0.4,1.5,1.0,0.05,
        help="§2.4: ~1 feels most natural. Low values = the 'cartoon setting' Dan warns about.")
    t_alpha=st.slider("Field opacity",0.15,1.0,0.38,0.01,help="Dan uses ~35% — field behind price.")
    t_cont=st.checkbox("Contours (zero + ridges/troughs)",value=True)
    t_strad=st.checkbox("Straddle bounds",value=True)
    t_lvls=st.checkbox("Dealer levels overlay (Pinak)",value=True)
    t_voladj=st.radio("Vol adjust",["0%","+1%"],index=0,horizontal=True)
    t_simg=st.checkbox("Simulated gamma ($5 finite diff, §2.7)",value=False)
    t_charm2=st.checkbox("Charm panel below (stacked, VS3D-style)",value=True,
        help="Second field under the main greek — gold = dealers must SELL as time passes · blue = BUY. No more dropdown flip-flopping.")
auto_on=st.sidebar.toggle("Auto-refresh (5 min)",value=True)
c1,c2=st.sidebar.columns(2)
force=c1.button("📸 Snapshot now",use_container_width=True)
if c2.button("🗑 Clear",use_container_width=True):
    st.session_state.snaps=[]; st.session_state.last_ts=None; st.session_state.frames={}
    try: _os.remove(_state_path())
    except Exception: pass
    st.rerun()
st.sidebar.caption("POC · snapshots in-memory (reset on app restart) · "
                   "sign = dealer calls+/puts− · volume unsigned · quotes as-of snapshot (Barchart may lag ~15m)")

# manual data refresh (clears bars cache + forces a fresh snapshot)
refresh=c2.button("🔄 Refresh data",use_container_width=True)
if refresh:
    st.cache_data.clear()

# auto-refresh: component rerun preserves session_state (a meta-refresh would wipe it).
# st.fragment(run_every=) is the dependency-free fallback if the package is absent.
_AUTOREFRESH_OK=False; _tick=None
try:
    from streamlit_autorefresh import st_autorefresh
    # During Play, tick at the chosen speed REGARDLESS of the auto toggle (v2.2.2 —
    # playback used to silently require auto-refresh ON); else 5-min live if auto.
    if st.session_state.get("pb_play") and st.session_state.get("frames"):
        _iv=int(st.session_state.get("pb_speed",2.0)*1000)
        _tick=st_autorefresh(interval=_iv,key="pb_tick")
        _AUTOREFRESH_OK=True
    elif auto_on:
        st_autorefresh(interval=5*60*1000, key="auto5min")
        _AUTOREFRESH_OK=True
    else:
        _AUTOREFRESH_OK=True   # nothing to install in manual mode; not an error
except Exception:
    _AUTOREFRESH_OK=False

# advance playback frame on each fast tick while playing (handled after controls below)


def _due():
    if st.session_state.get("pb_play"): return False   # don't pull live during playback
    if not auto_on: return False   # manual mode: only 📸/🔄 pull data (v2.2.2 — no surprise fetch on scrub)
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

# ── PLAYBACK: replay cached snapshot renders like a film ─────────────────────
# All tabs are rendered to PNG each snapshot and cached in session_state.frames,
# keyed by snapshot timestamp. Playback flips through them fast (no recompute).
if "frames" not in st.session_state: st.session_state.frames={}   # {ts_iso: {tab:[png,...]}}
if "pb_play" not in st.session_state: st.session_state.pb_play=False
if "pb_idx"  not in st.session_state: st.session_state.pb_idx=0
if "pb_follow" not in st.session_state: st.session_state.pb_follow=True   # at latest = follow new frames live (v2.2.2)
if "pb_speed" not in st.session_state: st.session_state.pb_speed=2.0
st.sidebar.markdown("---"); st.sidebar.markdown("**▶ Playback (recorded snapshots)**")
_frame_ts=[s["ts"] for s in snaps if s["ts"].isoformat() in st.session_state.frames]
_nframes=len(_frame_ts)
if _nframes==0:
    st.sidebar.caption("No cached frames yet — they record automatically each snapshot.")
    PLAYBACK=False
else:
    pbc1,pbc2=st.sidebar.columns(2)
    if pbc1.button("▶ Play" if not st.session_state.pb_play else "⏸ Pause",use_container_width=True):
        _was=st.session_state.pb_play
        st.session_state.pb_play=(not _was) and _nframes>1
        st.session_state.pb_last_tick=None   # first tick SHOWS the current frame, no advance (v2.2.2)
        if _was: st.session_state.pb_follow=(st.session_state.pb_idx>=_nframes-1)  # pausing mid-film holds
        st.rerun()
    if pbc2.button("⏮ Rewind",use_container_width=True):
        st.session_state.pb_idx=0; st.session_state.pb_play=False
        st.session_state.pb_follow=(_nframes<=1)
        st.rerun()
    st.session_state.pb_speed=st.sidebar.radio("Speed (sec/frame)",[1.0,2.0,4.0],
        index=[1.0,2.0,4.0].index(st.session_state.pb_speed),horizontal=True)
    if st.session_state.pb_play:
        # advance ONLY on a genuine timer tick — extra reruns (button handshakes,
        # component mounts, widget touches) can no longer skip frames (v2.2.2)
        _lt=st.session_state.get("pb_last_tick")
        if _tick is not None and _tick!=_lt:
            if _lt is not None:
                st.session_state.pb_idx=(st.session_state.pb_idx+1)%_nframes
            st.session_state.pb_last_tick=_tick
        st.sidebar.progress((st.session_state.pb_idx+1)/_nframes)
    elif _nframes>1:
        # paused: if you were FOLLOWING (at the latest frame), new frames keep you
        # live; if you scrubbed back, your position HOLDS even as frames arrive.
        # Drag to the right edge to re-follow live. (v2.2.2)
        _def=(_nframes-1 if st.session_state.get("pb_follow",True)
              else int(min(st.session_state.get("pb_idx",_nframes-1),_nframes-1)))
        st.session_state.pb_idx=st.sidebar.slider("Frame",0,_nframes-1,_def)
        st.session_state.pb_follow=(st.session_state.pb_idx>=_nframes-1)
    else:
        st.session_state.pb_idx=0
        st.sidebar.caption("1 frame cached — more appear each snapshot.")
    st.session_state.pb_idx=min(st.session_state.pb_idx,_nframes-1)
    _cur=_frame_ts[st.session_state.pb_idx]
    # REPLAY only while playing or scrubbed to an older frame. Paused at the latest
    # frame = LIVE (control changes recompute and overwrite that frame's cache).
    PLAYBACK=st.session_state.pb_play or (st.session_state.pb_idx<_nframes-1)
    if PLAYBACK:
        PLAYBACK_TS=_frame_ts[st.session_state.pb_idx].isoformat()
        st.sidebar.caption(f"Frame {st.session_state.pb_idx+1}/{_nframes} · {_cur:%H:%M:%S} EST"
                           + (" · ▶ playing" if st.session_state.pb_play else " · ⏸ replay"))
    else:
        st.sidebar.caption(f"Frame {st.session_state.pb_idx+1}/{_nframes} · {_cur:%H:%M:%S} EST · live")
if _nframes==0: PLAYBACK=False

latest=snaps[sel_i]; spot=latest["spot"]; exps=latest["exps"]
sel_ts=latest["ts"]
exp_date=dt.datetime.strptime(exps[0],"%Y-%m-%d").date()
bars,bars_msg=prep_bars()
try:  # ATM IV tripwire (v2.1.9): a units regression must be humanly visible
    _c0=latest["chain"]; _c0=_c0[_c0["expiry"]==exps[0]] if "expiry" in latest["chain"].columns else latest["chain"]
    _aiv=float(_c0.iloc[(_c0["strike"]-spot).abs().argsort()[:2]]["iv"].median())
    _atmiv_txt=f"  ·  ATM IV {100*_aiv:.1f}%" if _aiv==_aiv else ""
except Exception as _ex:                      # tripwires FAIL LOUD (v2.2.2 rule)
    _atmiv_txt=f"  ·  ATM IV unavailable ({type(_ex).__name__})"

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
    st.caption(f"Candles: none overlaid — {bars_msg}.{_atmiv_txt}")
else:
    st.caption(f"Candles: {bars_msg}.{_atmiv_txt}")

# ── frame emit / replay helpers ──────────────────────────────────────────────
import io as _io
_EMIT_BUF={}   # tab -> list of png bytes, filled during a live render pass
def emit(tab, fig, caption=None, container=None):
    """Live mode: display the figure AND stash its PNG for playback caching.
    If container is given (e.g. a st.columns() cell), render into it at a sane size."""
    tgt=container if container is not None else st
    if caption: tgt.markdown(caption)
    tgt.pyplot(fig,use_container_width=False)   # fixed size: prevents resize/jiggle feedback loop
    try:
        buf=_io.BytesIO(); fig.savefig(buf,format="png",dpi=fig.dpi,facecolor=DARK)   # == st.pyplot pixel size: live and cached render identically
        _EMIT_BUF.setdefault(tab,[]).append(buf.getvalue())
    except Exception: pass
    plt.close(fig)
def emit_caption(tab, text):
    st.caption(text)
def _replay_show(tab, ts_iso=None):
    """Show cached PNGs for a frame (playback OR unchanged live view), no recompute."""
    frame=st.session_state.frames.get(ts_iso or PLAYBACK_TS,{})
    imgs=frame.get(tab,[])
    if not imgs:
        st.info(f"No cached frame for this tab at {PLAYBACK_TS[11:19]}. "
                "Switch to this tab during a live snapshot to record it."); return
    for png in imgs: st.image(png)   # natural size == live pyplot size (same dpi, no crop)
def dispatch(tab, render_fn, sig=None):
    """PLAYBACK → replay old frame. Live + unchanged (same snapshot & controls)
    → show cached PNG, ZERO recompute. Live + changed → render, cache, store sig."""
    ts=sel_ts.isoformat()
    if PLAYBACK:
        _replay_show(tab); return
    last=st.session_state.setdefault("_livesig",{})
    if sig is not None and last.get(tab)==sig and st.session_state.frames.get(ts,{}).get(tab):
        _replay_show(tab, ts); return
    _EMIT_BUF[tab]=[]
    render_fn()
    st.session_state.frames.setdefault(ts,{})[tab]=list(_EMIT_BUF.get(tab,[]))
    last[tab]=sig

combo_on=st.sidebar.checkbox("🖥 Combined VS3D layout",value=False,
    help="Book + Gamma + Charm on one page, composed from the current frame's cached panels — zero recompute.")
tab_combo,tab_book,tab_terr,tab_sig,tab_read=st.tabs(["🖥 VS3D (combined)","📊 Book (by strike)","🗺 Terrain (gradient chart)","🧭 Signals (daily workflow)","📖 Read (what happens next)"])
with tab_combo:
    if combo_on:
        _frc=st.session_state.frames.get(sel_ts.isoformat() if hasattr(sel_ts,"isoformat") else str(sel_ts),{})
        _bp,_tp=_frc.get("book",[]),_frc.get("terrain",[])
        if not _bp and not _tp:
            st.info("No cached panels for this frame yet — take a 📸 snapshot (panels cache automatically).")
        else:
            _c1,_c2=st.columns([1.0,1.55])
            with _c1:
                st.caption("Positions (Book)")
                for _p in _bp: st.image(_p,use_container_width=True)
            with _c2:
                st.caption("Gamma + Charm terrain")
                for _p in _tp: st.image(_p,use_container_width=True)
    else:
        st.caption("Enable '🖥 Combined VS3D layout' in the sidebar to compose Book + Gamma + Charm here.")

with tab_book:
    emit_caption("book","GBT dealer book by 5-pt strike — VS3D 'Positions by Strike' analogue. "
        "MM-inferred mode: $M per 1%, signs from aggressor flow (yesterday's flow on today's expiry seeds "
        "pre-open; live flow updates top strikes), opacity = sign confidence. Naive mode: e-minis per $1, "
        "calls+/puts−, with comparison dots (white = prev snapshot · blue = market open).")
    def _render_book():
        bk=latest.get("book")
        if bk is None or getattr(bk,"empty",True):
            st.info("No book frame in this snapshot (pre-GBT or synthetic)."); return
        prevb=openb=None
        if b_dots:
            try:
                _sl=st.session_state.snaps
                _i=[i for i,s in enumerate(_sl) if s["ts"]==latest["ts"]][0]
                if _i>0: prevb=_sl[_i-1].get("book")
                if _i>0: openb=_sl[0].get("book")
            except Exception: pass
        _strv=None
        if b_strad:
            try: _strv=terrain_straddle(latest["chain"],latest["spot"])
            except Exception: _strv=None
        _sg=None
        if b_mode.startswith("MM") and not GBT_SIGNED:
            st.caption("Signed dealer inference is OFF (sidebar toggle) — naive bars shown")
        elif b_mode.startswith("MM"):
            try:
                ch=latest["chain"]
                if "dsign" in ch.columns and ch["dsign"].notna().any():
                    cc=ch.copy(); sp=float(latest["spot"])
                    nv=np.where(cc["type"].values=="call",1.0,-1.0)
                    eff=cc["dsign"].where(cc["dsign"].notna(),pd.Series(nv,index=cc.index))
                    cc["_v"]=eff*cc["gamma"].fillna(0)*cc["oi"].fillna(0)*100.0*sp*sp/10000.0
                    cc["_w"]=cc["oi"].fillna(0); cc["_a"]=cc["dsign"].abs().fillna(0)*cc["_w"]
                    g=cc.groupby("strike",as_index=False).agg(signed_pct=("_v","sum"),_w=("_w","sum"),_a=("_a","sum"))
                    g["conf"]=(g["_a"]/g["_w"].replace(0,np.nan)).fillna(0.0)
                    _sg=g[["strike","signed_pct","conf"]]
                else: st.caption("no signed data in this frame — naive bars shown")
            except Exception as _bx: st.caption(f"signed book unavailable this frame: {type(_bx).__name__}")
        _z=float(st.session_state.get("book_zoom",1.0))
        _sp=float(latest["spot"]); _half=_sp*window_pct*_z
        _lo2,_hi2=max(lo,_sp-_half),min(hi,_sp+_half)
        try:
            _gm2=[v for k,v in st.session_state.items() if str(k).startswith("gbt_seed_meta_")]
            _cv=f" · seeded {_gm2[0].get('ok','?')}/{_gm2[0].get('n','?')} · live {_gm2[0].get('live',0)}" if (_gm2 and _sg is not None) else ""
        except Exception: _cv=""
        st.caption(f"showing {int(_lo2)}–{int(_hi2)} · fetched {int(lo)}–{int(hi)} (spot {_sp:.2f} ±{window_pct*100:.1f}%) · zoom ×{_z:.2f}{_cv}")
        fig=book_figure(bk,latest["spot"],_strv,_lo2,_hi2,side=b_side,prev=prevb,openb=openb,signed=_sg,sqrt_scale=bool(b_sqrt))
        emit("book",fig)
    if book_on:
        _bsig=repr((sel_ts.isoformat(),b_mode,b_side,bool(b_dots),bool(b_strad),bool(b_sqrt),bool(GBT_SIGNED),round(float(st.session_state.get("book_zoom",1.0)),3),round(window_pct,5),len(st.session_state.snaps)))
        dispatch("book",_render_book,sig=_bsig)


with tab_terr:
    emit_caption("terrain","VS3D Gradient Chart, guide-spec. Field = chosen greek across price×time for the "
        "WHOLE fetched book (each expiry decays on its own clock; 0DTE dominates via asymptotic gamma). "
        "Manual symmetric range (a loose day looks loose) · near-linear intensity · field behind price. "
        "Contours: dotted = zero boundary · red = ridge (local max) · blue = trough. Sign is the "
        "calls+/puts− convention when Signed inference is OFF; when ON, per-leg signs are aggressor-flow inferred (seeded from yesterday's flow on today's expiry, refreshed live).")
    def _render_terrain():
        now_naive=sel_ts.replace(tzinfo=None) if getattr(sel_ts,'tzinfo',None) else sel_ts
        use_exps=(latest.get("exps") or [])[:max(1,int(num_expiries))]
        if not use_exps:
            st.warning("No expiries in this snapshot yet."); return
        _GHEAVY="Gamma |Γ| (heaviness)"; _GDECAY="Gamma Decay (color)"
        _base_greek="Gamma" if t_greek in (_GHEAVY,_GDECAY) else t_greek
        try:
            pg,Z,taus=terrain_grid(latest["chain"],spot,use_exps,now_naive,greek=_base_greek,
                                   vol_adj=(0.01 if t_voladj=="+1%" else 0.0),
                                   p_min=p_min,p_max=p_max,simulated_gamma=t_simg,weighting=t_wt)
            if t_greek==_GHEAVY: Z=np.abs(Z)
            elif t_greek==_GDECAY: Z=_decay_shift(Z,taus)
        except Exception as ex:
            import traceback; st.error(f"terrain grid failed: {ex}"); st.code(traceback.format_exc()); return
        # fixed-cap scaling (per greek, seeded once; Calibrate button re-seeds)
        capkey=f"terr_cap_{t_greek}_{t_wt}"
        seed=st.session_state.get(capkey)
        V,used_cap=terrain_scale(Z,t_norm,seed if t_norm=="Manual (fixed cap)" else None,t_pct)
        if t_norm=="Manual (fixed cap)" and seed is None:
            st.session_state[capkey]=1.2*float(np.percentile(np.abs(Z),98)); V,used_cap=terrain_scale(Z,t_norm,st.session_state[capkey],t_pct)
        _p92=float(np.percentile(np.abs(Z),92))
        st.session_state.setdefault(f"terr_hist_{t_greek}_{t_wt}",[]).append(_p92)
        if t_norm=="Manual (fixed cap)" and used_cap and _p92>3.0*used_cap:
            st.warning(f"⚠ Cap stale — current p92 ({_p92:,.0f}) is {_p92/used_cap:.1f}× the cap "
                       f"({used_cap:,.0f}); the field is saturating into flat color blocks. "
                       f"Press Reset cap, then Calibrate after 2–3 snapshots.")
        _t=now_naive.time()
        if _t<dt.time(9,30) or _t>dt.time(16,0):
            st.caption("⏸ off-hours: time-to-expiry ~constant across the session axis → field is nearly "
                       "time-flat and candles are absent. Structure appears live during RTH on 0DTE.")
        V=terrain_intensity(V,t_int,power=t_pow,gain=3.0)
        cmap=(charm_cmap() if t_greek=="Charm" else heat_cmap() if t_greek==_GHEAVY
              else decay_cmap() if t_greek==_GDECAY else gex_cmap())
        plotV=(-V if t_greek=="Charm" else V)   # hedging-effect polarity: dealers-must-SELL renders gold (§7.7)
        _vmin=(0.0 if t_greek==_GHEAVY else -1.0)
        x0,x1=session_window()
        fig=plt.figure(figsize=(16.5,7.6),dpi=80,facecolor=DARK)
        gs=fig.add_gridspec(1,2,width_ratios=[24,2.2],wspace=0.015)
        ax=fig.add_subplot(gs[0,0]); axp=fig.add_subplot(gs[0,1],sharey=ax)
        ax.set_facecolor(DARK); axp.set_facecolor(DARK)
        ax.imshow(plotV,origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",cmap=cmap,
                  vmin=_vmin,vmax=1,interpolation="bilinear",zorder=0,alpha=t_alpha)
        if t_cont: terrain_contours(ax,Z,x0,x1,pg,st.session_state.get(capkey))
        draw_candles(ax,bars,x0,x1,pg[0],pg[-1])
        ax.axhline(spot,color=WHITE,ls="--",lw=1.0,alpha=.9,zorder=7)
        ax.axvline(mdates.date2num(now_naive),color="#3399dd",ls=":",lw=1.1,zorder=7)
        # straddle bounds (§5.3) from the 0DTE chain
        strad=terrain_straddle(latest["chain"][latest["chain"].get("expiry",use_exps[0])==use_exps[0]]
                               if "expiry" in latest["chain"].columns else latest["chain"], spot)
        if t_strad and strad:
            for b in (spot-strad,spot+strad):
                if pg[0]<b<pg[-1]:
                    ax.axhline(b,color="#e06ce0",ls=(0,(5,3)),lw=1.0,alpha=.85,zorder=7)
                    ax.text(x1,b,f" {b:.0f}",color="#e06ce0",fontsize=8,va="center",zorder=8)
        # Pinak dealer-level overlay (0DTE)
        if t_lvls:
            try:
                ch0=latest["chain"][latest["chain"].get("expiry",use_exps[0])==use_exps[0]] \
                    if "expiry" in latest["chain"].columns else latest["chain"]
                r=pinak_levels(ch0,spot,use_exps[0],now_naive)
                _labels=[]
                def lvl(v,color,txt,ls,lw):
                    if v is None or not(pg[0]<v<pg[-1]): return
                    ax.axhline(v,color=color,ls=ls,lw=lw,alpha=.9,zorder=7); _labels.append([v,color,txt])
                lvl(r["pin"],"#FF6600","PIN","-",1.8); lvl(r["flip"],"#0080ff","FLIP","-",1.2)
                lvl(r["call_wall"],"#ff5a3c","CW","--",1.0); lvl(r["put_wall"],"#3ca0ff","PW","--",1.0)
                lvl(r["kstar"],"#cccccc","K*","-.",0.9)
                mg=(pg[-1]-pg[0])*0.04; _labels.sort(key=lambda z:z[0]); last=-1e9
                for v,color,txt in _labels:
                    y=max(v,last+mg); last=y
                    ax.text(x0+(x1-x0)*0.002,y,f"{txt} {v:.0f}",color=color,fontsize=8,va="center",zorder=8,
                            bbox=dict(boxstyle="round,pad=0.2",facecolor=DARK,edgecolor=color,alpha=.85,lw=.6))
            except Exception: pass
        # side profile histogram — the current-time column (real VS3D right-edge panel)
        jnow=int(np.clip(round((mdates.date2num(now_naive)-x0)/(x1-x0)*(Z.shape[1]-1)),0,Z.shape[1]-1))
        prof=Z[:,jnow]; capv=float(np.percentile(np.abs(prof),98)) or 1.0   # local shape scale
        posc,negc=(("#d9a90b","#3399dd") if t_greek=="Charm"
                   else ("#39d0d8","#39d0d8") if t_greek==_GHEAVY
                   else ("#ff9f43","#7a3fd0") if t_greek==_GDECAY
                   else ("#22b14c","#d13438"))
        axp.fill_betweenx(pg,0,np.clip(prof/capv,-1,1),where=prof>=0,color=posc,alpha=.85)
        axp.fill_betweenx(pg,0,np.clip(prof/capv,-1,1),where=prof<0,color=negc,alpha=.85)
        axp.axvline(0,color="#555",lw=.6); axp.axhline(spot,color=WHITE,ls="--",lw=.8,alpha=.8)
        axp.set_xlim(-1,1); axp.set_xticks([])
        for s_ in ("top","right","left","bottom"): axp.spines[s_].set_color(GRID)
        try:
            _ch0=latest["chain"]
            _sgmode="SIGNED·flow" if (GBT_SIGNED and "dsign" in _ch0.columns and _ch0["dsign"].notna().any()) else "naive±"
        except Exception: _sgmode="naive±"
        pol=("green = dealers BUY to arrive hedged (supportive) · red = SELL" if t_greek=="Delta Change"
             else "green = +γ suppressive · red = −γ amplifying" if t_greek=="Gamma"
             else "bright = heavy book · direction UNKNOWN by design (roles come from behavior)" if t_greek==_GHEAVY
             else "orange = γ BUILDING into the close (pin energy) · purple = fading" if t_greek==_GDECAY
             else "gold = dealers must SELL as time passes · blue = must BUY")
        ax.set_title(f"TERRAIN · {t_greek} · {t_wt} · {_sgmode} · exps {len(use_exps)} · cap {st.session_state.get(capkey,0):,.0f}"
                     f" · {t_int}({t_pow:g}) · α{t_alpha:.2f}   [{pol}]",color=TXT,fontsize=10.5,loc="left")
        # strike scale: 25-pt gridlines across the field + bright labels both sides
        _yt=np.arange(np.ceil(pg[0]/25)*25, pg[-1]+1, 25)
        for _y in _yt:
            ax.axhline(_y,color="#1a2330",lw=0.6,zorder=1)
        ax.set_yticks(_yt)
        ax.tick_params(axis="y",colors="#9fb0c3",labelsize=10.5,length=3)
        axp.yaxis.tick_right()
        axp.set_yticks(_yt)
        plt.setp(axp.get_yticklabels(),visible=True)
        axp.tick_params(axis="y",colors="#9fb0c3",labelsize=9,length=2)
        _tz=float(st.session_state.get("terr_zoom",1.0))
        _zl,_zh=pg[0],pg[-1]
        if _tz<0.999:
            _hz=(pg[-1]-pg[0])*_tz/2.0; _zc=float(spot)
            _zl,_zh=max(pg[0],_zc-_hz),min(pg[-1],_zc+_hz)
        ax.set_ylim(_zl,_zh); axp.set_ylim(_zl,_zh); style_time_axis(ax,x0,x1)
        emit("terrain",fig)
        # ---- stacked Charm panel (v2.1.8, user request): same window/time axis,
        # hedging-effect polarity (gold = dealers must SELL as clock runs, blue = BUY)
        if t_charm2 and t_greek!="Charm":
            try:
                _,Zc,_=terrain_grid(latest["chain"],spot,use_exps,now_naive,greek="Charm",
                                    vol_adj=(0.01 if t_voladj=="+1%" else 0.0),
                                    p_min=p_min,p_max=p_max,weighting=t_wt)
                ck=f"terr_cap_Charm_{t_wt}"
                cseed=st.session_state.get(ck)
                Vc,c_cap=terrain_scale(Zc,t_norm,cseed if t_norm=="Manual (fixed cap)" else None,t_pct)
                if t_norm=="Manual (fixed cap)" and cseed is None:
                    st.session_state[ck]=1.2*float(np.percentile(np.abs(Zc),98)); Vc,c_cap=terrain_scale(Zc,t_norm,st.session_state[ck],t_pct)
                st.session_state.setdefault(f"terr_hist_Charm_{t_wt}",[]).append(float(np.percentile(np.abs(Zc),92)))
                Vc=terrain_intensity(Vc,t_int,power=t_pow,gain=3.0)
                fc=plt.figure(figsize=(16.5,4.4),dpi=80,facecolor=DARK)
                axc=fc.add_subplot(111); axc.set_facecolor(DARK)
                axc.imshow(-Vc,origin="lower",extent=[x0,x1,pg[0],pg[-1]],aspect="auto",
                           cmap=charm_cmap(),vmin=-1,vmax=1,interpolation="bilinear",zorder=0,alpha=t_alpha)
                if t_cont:
                    try: axc.contour(np.linspace(x0,x1,Zc.shape[1]),pg,Zc,levels=[0.0],
                                     colors="#e8e8e8",linewidths=1.0,linestyles=(0,(4,3)),alpha=.9,zorder=6)
                    except Exception: pass
                draw_candles(axc,bars,x0,x1,pg[0],pg[-1])
                axc.axhline(spot,color=WHITE,ls="--",lw=1.0,alpha=.9,zorder=7)
                axc.axvline(mdates.date2num(now_naive),color="#3399dd",ls=":",lw=1.1,zorder=7)
                for _y in _yt: axc.axhline(_y,color="#1a2330",lw=0.6,zorder=1)
                axc.set_yticks(_yt); axc.tick_params(axis="y",colors="#9fb0c3",labelsize=10.5,length=3)
                axc.set_ylim(_zl,_zh); style_time_axis(axc,x0,x1)
                axc.set_title(f"CHARM · {t_wt} · {_sgmode} · cap {st.session_state.get(ck,0):,.0f}   "
                              f"[gold = dealers must SELL as time passes · blue = must BUY]",
                              color=TXT,fontsize=10.5,loc="left")
                emit("terrain",fc)
            except Exception as ex:
                st.caption(f"charm panel unavailable: {ex}")
    _tsig=repr((sel_ts.isoformat(),t_greek,t_wt,t_norm,t_pct,t_int,round(t_pow,3),round(t_alpha,3),
                t_cont,t_strad,t_lvls,t_voladj,t_simg,t_charm2,bool(GBT_SIGNED),round(float(st.session_state.get("terr_zoom",1.0)),3),int(num_expiries),round(window_pct,5),
                st.session_state.get(f"terr_cap_{t_greek}_{t_wt}"),
                st.session_state.get(f"terr_cap_Charm_{t_wt}") if t_charm2 else None))
    dispatch("terrain",_render_terrain,sig=_tsig)

with tab_sig:
    emit_caption("signals","§5.1 daily workflow: straddle range → structure quality → charm gate → absorption. "
                 "All sign-free; Pinak levels included. Charm is a weighted coin — needs a decaying straddle "
                 "and the 1:30–3pm window to have a say.")
    def _render_signals():
        now_naive=sel_ts.replace(tzinfo=None) if getattr(sel_ts,'tzinfo',None) else sel_ts
        use_exps=(latest.get("exps") or [])
        if not use_exps: st.warning("No data yet."); return
        ch0=latest["chain"][latest["chain"].get("expiry",use_exps[0])==use_exps[0]] \
            if "expiry" in latest["chain"].columns else latest["chain"]
        strad_now=terrain_straddle(ch0,spot)
        _so=st.session_state.get("strad_open_"+now_naive.strftime("%Y-%m-%d"))
        if _so and _so[0]:
            strad_open=float(_so[0]); open_lbl=f"{_so[1]}"
        else:
            first=snaps[0]; ch0_first=first["chain"][first["chain"].get("expiry",use_exps[0])==first["exps"][0]] \
                if "expiry" in first["chain"].columns else first["chain"]
            strad_open=terrain_straddle(ch0_first,first["spot"]) if len(snaps)>1 else None
            open_lbl="1st snap"
        decaying=None
        if strad_now and strad_open: decaying=strad_now<strad_open*0.995
        # gamma absorption toward each straddle bound (§5.4 mental math, futures-equiv)
        c=ch0.dropna(subset=["strike","delta"])
        w=np.where(c["oi"].fillna(0)>0,c["oi"].fillna(0),c["volume"].fillna(0)).astype(float)  # book-first (v2.2.0)
        dlt=c["delta"].fillna(0).values; K=c["strike"].values
        rem=np.abs(np.where(dlt>=0,1-dlt,-1-dlt))*w*100/50.0   # e-mini equiv remaining hedge
        up=float(rem[(K>spot)&(K<=spot+(strad_now or spot*0.005))].sum())
        dn=float(rem[(K<spot)&(K>=spot-(strad_now or spot*0.005))].sum())
        fish=vs3d_fishbone(ch0); fishtxt="CLEAN — trade" if fish<=4 else("MESSY — size down" if fish<=8 else "FISHBONE — sit out")
        _hk=[k for k in st.session_state.keys() if k.startswith("terr_hist_")]
        hist=st.session_state.get(_hk[0],[]) if _hk else []
        reg=""
        if hist:
            cur=hist[-1]; avg=float(np.mean(hist)) if len(hist)>1 else cur
            reg=("HEAVY (γ > 1.5× trailing)" if cur>1.5*avg else "LOOSE (γ < 0.5× trailing)" if cur<0.5*avg else "NORMAL")
        t=now_naive.time(); win=vs3d_timing(now_naive)
        charm_ok=(decaying is True) and dt.time(13,30)<=t<=dt.time(15,0)
        gate=("OPEN — straddle decaying, in window" if charm_ok else
              "CLOSED — "+("straddle NOT decaying (snake-oil check)" if decaying is False else
              "need 2nd snapshot" if decaying is None else "outside 1:30–3pm window"))
        try: r=pinak_levels(ch0,spot,use_exps[0],now_naive)
        except Exception: r=None
        f=lambda v: f"{v:,.0f}" if isinstance(v,(int,float)) and v is not None else "n/a"
        _noMath=lambda s: str(s).replace("$","\\$")   # matplotlib treats $…$ as mathtext
        GRN="#22c55e"; RED="#ef4444"; GLD="#f0a020"; DIM="#8b949e"; WHT="#e6edf3"; CYN="#38bdf8"
        # ── verdict banner — same engine as the Read tab, so they can never disagree
        try: v=read_verdict(snaps[:sel_i+1] if sel_i+1<=len(snaps) else snaps, use_exps, now_naive, track=False)
        except Exception: v=None
        if v:
            vup=("LEANS UP" in v["pat"]) or ("BULL" in v["pat"])
            if v["conf"]<=25 and "FISHBONE" in v["fish"]:
                ban=("\u26d4 STAND DOWN","no trade — structure is whipsaw (fishbone): hedging flips strike to strike",RED)
            elif v["conf"]>=60:
                ban=((("\u25b2 LEAN LONG") if vup else ("\u25bc LEAN SHORT")),
                     f"{v['do']}  ·  target {v['to']:,.0f}" if v.get("to") else v["do"],(GRN if vup else RED))
            elif v["conf"]>=40:
                ban=("\u26a0 SMALL SIZE ONLY",f"{v['do']}  ·  reduced conviction",GLD)
            else:
                blocker=("straddle not decaying — charm signal is off" if v["decay"].startswith("FLAT")
                         else "open-hour external flow — signal not live yet" if v["clock"].startswith("OPEN")
                         else "VIX high — vanna can steamroll charm" if "HIGH" in v["vix"]
                         else "no reference yet — need the open straddle" if v["decay"].startswith("n/a")
                         else "weak/conflicting gates")
                ban=("\u23f8 WAIT",f"inaction is the trade right now — {blocker}",GLD)
            why=[]
            if v["conf"]<=25 and "FISHBONE" in v["fish"]:
                why.append("fishbone structure (BINDING — caps everything else)")
            why.append("charm live" if v["decay"].startswith(("DECAYING","COLLAPSING")) else "charm off")
            why.append("prime window" if "SWEET" in v["clock"] else ("pin hour" if v["clock"].startswith("CLOSE") else ("open hour" if v["clock"].startswith("OPEN") else "midday")))
            why.append(v["vix"].split(" \u00b7 ")[0])
            banner_why="because: "+" \u00b7 ".join(why)+"    flips if: straddle reprices \u00b7 VIX spikes \u00b7 a test breaks & holds"
        path=("DOWN" if up>dn*1.4 else "UP" if dn>up*1.4 else "balanced")
        d_txt,d_col,d_int=(("YES — charm flow is real today",GRN,"decay drips onto dealer books — the drift is live") if decaying
                           else ("NO — repricing/flat",RED,"options not bleeding — ignore charm today") if decaying is False
                           else ("n/a",DIM,"need the open reference"))
        rows=[("sec","STRADDLE — is the charm signal usable today? (snake-oil check)",CYN),
              ("kv2","now",(f"${strad_now:.2f}" if strad_now else "n/a"),WHT,
                     f"open ({open_lbl})",(f"${strad_open:.2f}" if strad_open else "n/a"),WHT,""),
              ("kv","decaying?",d_txt,d_col,d_int),
              ("kv","range spot\u00b1straddle",f"{f(spot-(strad_now or 0))} — {f(spot+(strad_now or 0))}",WHT,
                    "the market's own guess for today's travel"),
              ("sec","STRUCTURE \u00b7 REGIME \u00b7 CLOCK — can the signal be trusted right now?",CYN),
              ("kv","fishbone",f"{fish}  \u00b7  {fishtxt}",(GRN if fish<=4 else GLD if fish<=8 else RED),
                    ("one-sided book = orderly hedging" if fish<=4 else "mixed book = degraded signal" if fish<=8 else "alternating strikes = whipsaw, no edge")),
              ("kv","gamma regime",reg or "building trailing…",WHT,
                    ("tight, pinned tape — fade the edges" if reg.startswith("HEAVY") else "moves travel further than usual" if reg.startswith("LOOSE") else "typical range behavior")),
              ("kv","window",win,(GRN if "SWEET" in win else GLD),
                    ("prime charm hours" if "SWEET" in win else "pin gravity strongest" if win.startswith("CLOSE") else "external flow dominates — wait" if win.startswith("OPEN") else "signal building")),
              ("kv","CHARM GATE",gate,(GRN if gate.startswith("OPEN") else RED),
                    ("all clear — the drift can be leaned on" if gate.startswith("OPEN") else "do NOT trade the charm story while this is closed")),
              ("sec","DIRECTION — which way is the path of least resistance?",CYN),
              ("kv","absorption up/down",f"{up:,.0f} / {dn:,.0f} e-mini",WHT,
                    "hedge supply waiting in each direction — thicker side is harder to cross"),
              ("kv","path",("\u25bc DOWN" if path=="DOWN" else "\u25b2 UP" if path=="UP" else "\u25c6 balanced"),
                    (RED if path=="DOWN" else GRN if path=="UP" else GLD),
                    ("more hedge supply above than below" if path=="DOWN" else "more hedge supply below than above" if path=="UP" else "no edge from absorption")),]
        if r:
            _pin,_ps=r["pin"],r["pin_score"]
            pin_int=("no reliable magnet today — don't lean on the pin" if (_ps or 0)<40 else
                     ("\u25b2 magnet ABOVE spot — drift-up pull into the close" if _pin and _pin>spot else
                      "\u25bc magnet BELOW spot — drift-down pull into the close" if _pin and _pin<spot else "at spot — expect stickiness"))
            flip_side=(r["flip"] is None or spot>=r["flip"])
            rows+=[("kv","PIN",f"{f(_pin)}  \u00b7  {r['pin_label']} {_ps}/100",GLD,pin_int),
                   ("kv","FLIP",f"{f(r['flip'])}  \u00b7  spot is {'ABOVE' if flip_side else 'BELOW'}",(CYN if flip_side else RED),
                        ("+\u03b3 side: chop / mean-revert regime" if flip_side else "\u2212\u03b3 side: trend risk — needs a trigger, never fade the void")),
                   ("kv2","CALL WALL",f"{f(r['call_wall'])}"+(f"  (resistance {r['call_wall']-spot:+,.0f})" if r["call_wall"] else ""),RED,
                          "PUT WALL",f"{f(r['put_wall'])}"+(f"  (support {r['put_wall']-spot:+,.0f})" if r["put_wall"] else ""),GRN,""),
                   ("kv2","K*",f"{f(r['kstar'])}  (implied fair spot)",WHT,"CEIL / FLOOR",f"{f(r['ceiling'])} / {f(r['floor'])}",WHT,"")]
        rows+=[("foot","cannot measure: dealer long/short (anchor vs test) \u00b7 MM-on-MM netting \u00b7 OTC flow — treat as a weighted coin",DIM)]
        fs,axs=plt.subplots(figsize=(16,7.4),dpi=80,facecolor=DARK); axs.axis("off"); axs.set_facecolor(DARK)
        y=0.988
        axs.text(0.012,y,f"SPX {spot:,.2f}    {sel_ts:%H:%M:%S} EST    expiry {use_exps[0]}    snapshots {len(snaps)}",
                 transform=axs.transAxes,color=WHT,va="top",ha="left",family="monospace",fontsize=14,fontweight="bold"); y-=0.058
        if v:
            import matplotlib.patches as _mp
            axs.add_patch(_mp.FancyBboxPatch((0.010,y-0.088),0.978,0.086,boxstyle="round,pad=0.004",
                          transform=axs.transAxes,facecolor=ban[2],alpha=0.13,edgecolor=ban[2],linewidth=1.4))
            axs.text(0.026,y-0.012,ban[0],transform=axs.transAxes,color=ban[2],va="top",ha="left",
                     family="monospace",fontsize=16.5,fontweight="bold")
            axs.text(0.300,y-0.014,_noMath(ban[1]),transform=axs.transAxes,color=WHT,va="top",ha="left",
                     family="monospace",fontsize=11.5,fontweight="bold")
            axs.text(0.945,y-0.012,f"{v['conf']}/100",transform=axs.transAxes,color=ban[2],va="top",ha="right",
                     family="monospace",fontsize=15,fontweight="bold")
            axs.text(0.026,y-0.056,banner_why,transform=axs.transAxes,color=DIM,va="top",ha="left",
                     family="monospace",fontsize=9.5)
            y-=0.118
        for rw in rows:
            kind=rw[0]
            if kind=="sec":
                y-=0.010
                axs.text(0.012,y,rw[1],transform=axs.transAxes,color=rw[2],va="top",ha="left",
                         family="monospace",fontsize=10.5,alpha=.95); y-=0.048
            elif kind=="kv":
                axs.text(0.030,y,rw[1],transform=axs.transAxes,color=DIM,va="top",ha="left",family="monospace",fontsize=11)
                axs.text(0.230,y,_noMath(rw[2]),transform=axs.transAxes,color=rw[3],va="top",ha="left",
                         family="monospace",fontsize=12,fontweight="bold")
                if len(rw)>4 and rw[4]:
                    axs.text(0.565,y,"\u2192 "+rw[4],transform=axs.transAxes,color=DIM,va="top",ha="left",
                             family="monospace",fontsize=9.5,style="italic")
                y-=0.046
            elif kind=="kv2":
                axs.text(0.030,y,rw[1],transform=axs.transAxes,color=DIM,va="top",ha="left",family="monospace",fontsize=11)
                axs.text(0.230,y,_noMath(rw[2]),transform=axs.transAxes,color=rw[3],va="top",ha="left",
                         family="monospace",fontsize=12,fontweight="bold")
                axs.text(0.565,y,rw[4],transform=axs.transAxes,color=DIM,va="top",ha="left",family="monospace",fontsize=11)
                axs.text(0.740,y,_noMath(rw[5]),transform=axs.transAxes,color=rw[6],va="top",ha="left",
                         family="monospace",fontsize=12,fontweight="bold"); y-=0.046
            else:
                y-=0.010
                axs.text(0.012,y,rw[1],transform=axs.transAxes,color=rw[2],va="top",ha="left",family="monospace",fontsize=9.5)
        emit("signals",fs)
    _ssig=repr((sel_ts.isoformat(),int(num_expiries),round(window_pct,5),len(snaps)))
    dispatch("signals",_render_signals,sig=_ssig)

with tab_read:
    emit_caption("read","Cheat-sheet decision engine: γ environment × charm lean → one of four day patterns, "
                 "gated by the charm clock, straddle check (snake-oil), VIX/vanna regime, fishbone and γ-absorption. "
                 "Buy what price goes through, sell what price goes to. Proxy-honest: dealer long/short not measured; "
                 "with real positioning Dan claims ~65% — treat this as a weighted coin, not an oracle.")
    def _render_read():
        now_naive=sel_ts.replace(tzinfo=None) if getattr(sel_ts,'tzinfo',None) else sel_ts
        use_exps=(latest.get("exps") or [])
        if not use_exps: st.warning("No data yet."); return
        try: v=read_verdict(snaps[:sel_i+1] if sel_i+1<=len(snaps) else snaps, use_exps, now_naive)
        except Exception as ex:
            import traceback; st.error(f"read failed: {ex}"); st.code(traceback.format_exc()); return
        BULL="#22c55e"; BEAR="#ef4444"; WARN="#f0a020"; DIM="#8b949e"; CYAN="#38bdf8"; WHT="#e6edf3"
        up="LEANS UP" in v["pat"] or "BULL" in v["pat"]
        dirc=BULL if up else BEAR
        def gate_color(txt):
            t=" "+txt.upper()
            if any(k in t for k in ["SELL FLOW","FISHBONE","FLAT/REPRICING","VIX HIGH"," HIGH ·","OPEN 9:30","NEGATIVE"]): return BEAR
            if any(k in t for k in ["BUY FLOW","DECAYING","SWEET"," LOW ·","CLEAN"]): return BULL
            return WARN
        import textwrap
        lines=[]   # (text, color, size, bold)
        lines.append((f"SPX {v['spot']:,.2f}   {sel_ts:%H:%M:%S} EST   straddle {v['strad']}",WHT,13,False))
        lines.append(("",WHT,6,False))
        lines.append((("▲ " if up else "▼ ")+v["pat"],dirc,17,True))
        for i,w in enumerate(textwrap.wrap("NEXT  "+v["nxt"],96)):
            lines.append((w if i==0 else "      "+w, dirc if "WARNING" not in w and "tension" not in w else WARN, 12.5,False))
        lines.append(("STRUCTURE  "+v["do"],CYAN,12.5,False))
        thr=f"{v['through']:,.0f}" if v['through'] else "n/a"; to=f"{v['to']:,.0f}" if v['to'] else "n/a"
        lines.append((f"PLAY  buy through {thr} · sell to {to}",CYAN,12.5,True))
        lines.append(("",WHT,6,False))
        cc=BULL if v["conf"]>=65 else (WARN if v["conf"]>=40 else BEAR)
        nb=int(round(v["conf"]/5))
        lines.append((f"CONFIDENCE {v['conf']}/100  "+"█"*nb+"─"*(20-nb),cc,14,True))
        lines.append(("",WHT,6,False))
        for lab,val in [("γ env",v["env"]),("charm",v["lean"]),("straddle",v["decay"]),
                        ("clock",v["clock"]),("vix",v["vix"]),("structure",v["fish"])]:
            lines.append((f"  {lab:<10}{val}",gate_color(val),12,False))
        lines.append(("",WHT,6,False))
        lines.append(("flips this read: straddle repricing up · VIX spike (vanna over charm) · a test",DIM,10.5,False))
        lines.append(("breaking AND holding (delta 30→100, new range) · any external trigger",DIM,10.5,False))
        # ---- layout: text block on top, two glance-graphics below (cheat-sheet style)
        textH=sum(l[2] for l in lines)*1.55/72+0.35; gfxH=1.9; H=textH+gfxH
        fr=plt.figure(figsize=(13.5,H),dpi=80,facecolor=DARK)
        axr=fr.add_axes([0.0,gfxH/H,1.0,textH/H]); axr.axis("off"); axr.set_facecolor(DARK)
        y=1.0
        for txt,col,fs,bold in lines:
            axr.text(0.012,y,txt,transform=axr.transAxes,color=col,va="top",ha="left",
                     family="monospace",fontsize=fs,fontweight=("bold" if bold else "normal"))
            y-=fs*1.55/(textH*72)
        # left: minimal pattern sketch (from the cheat sheet 'pick the day' row)
        axl=fr.add_axes([0.015,0.045,0.30,(gfxH-0.35)/H]); axl.set_facecolor("#10151d")
        axl.set_xticks([]); axl.set_yticks([])
        for sp in axl.spines.values(): sp.set_color("#242c38")
        gpos="LEANS" in v["pat"]
        xs=np.linspace(0,1,13)
        if gpos:
            drift=0.16 if up else -0.16
            ys=0.5+0.16*np.array([0,1,-1,1,-1,1,-1,1,-1,1,-1,1,0])[:13]*0.9+drift*xs
            axl.axhspan(0.30,0.70,color=("#12331f" if up else "#331416"),alpha=.5,zorder=0)
            axl.plot(xs,ys,color="#e6edf3",lw=2.0,solid_capstyle="round")
        else:
            ys=(0.18+0.64*xs**1.7) if up else (0.82-0.64*xs**1.7)
            axl.plot(xs,ys,color=dirc,lw=2.4,solid_capstyle="round")
            axl.plot([0.42],[np.interp(0.42,xs,ys)],marker="o",color=WARN,ms=6)
            axl.text(0.44,np.interp(0.42,xs,ys)+(0.09 if up else -0.13),"trigger",color=WARN,fontsize=8)
            axl.plot([1.0],[ys[-1]],marker=("^" if up else "v"),color=dirc,ms=8)
        axl.set_xlim(0,1.04); axl.set_ylim(0,1)
        axl.set_title(("RANGE — fade edges" if gpos else "TREND — needs trigger"),
                      color=("#3fb950" if gpos else dirc),fontsize=9,loc="left",pad=3)
        # right: the day on one map — LIVE levels
        axm=fr.add_axes([0.365,0.045,0.615,(gfxH-0.35)/H]); axm.set_facecolor("#10151d")
        axm.set_xticks([]); axm.set_yticks([])
        for sp in axm.spines.values(): sp.set_color("#242c38")
        cw,pw,pin,sp_,to=v.get("through") and None or None, None, None, v["spot"], v["to"]
        cw=v.get("wall_up"); pw=v.get("wall_dn"); pin=v.get("pin")
        lv=[x for x in (cw,pw,pin,sp_,to) if x]
        ylo,yhi=min(lv),max(lv); pad=max((yhi-ylo)*0.30,sp_*0.0015); axm.set_ylim(ylo-pad,yhi+pad)
        axm.set_xlim(0,1)
        pin_on_cw=pin and cw and abs(pin-cw)<=1; pin_on_pw=pin and pw and abs(pin-pw)<=1
        if cw and not pin_on_cw:
            axm.axhline(cw,color=WARN,lw=1.6); axm.text(0.995,cw,f"UPPER TEST {cw:,.0f} ",color=WARN,fontsize=8.5,ha="right",va="bottom")
        if pw and not pin_on_pw:
            axm.axhline(pw,color=WARN,lw=1.6); axm.text(0.995,pw,f"LOWER TEST {pw:,.0f} ",color=WARN,fontsize=8.5,ha="right",va="top")
        if pin:
            lbl=(f"ANCHOR = UPPER TEST {pin:,.0f} " if pin_on_cw else
                 f"ANCHOR = LOWER TEST {pin:,.0f} " if pin_on_pw else f"ANCHOR {pin:,.0f} ")
            axm.axhline(pin,color="#3b82f6",lw=1.8)
            axm.text(0.995,pin,lbl,color="#3b82f6",fontsize=8.5,ha="right",
                     va=("bottom" if pin>=sp_ else "top"))
        axm.plot([0.10],[sp_],marker="o",color="#e6edf3",ms=7,zorder=5)
        axm.text(0.10,sp_,f"  spot {sp_:,.0f}",color="#e6edf3",fontsize=8.5,va="center")
        if to:
            axm.annotate("",xy=(0.80,to),xytext=(0.13,sp_),
                         arrowprops=dict(arrowstyle="-|>",color=dirc,lw=2.0,
                                         connectionstyle="arc3,rad="+("-0.08" if to>=sp_ else "0.08")))
            _near=[x for x in (cw,pw,pin) if x and abs(x-to)<pad*0.45]
            if not _near:
                axm.text(0.81,to,f" target {to:,.0f}",color=dirc,fontsize=8.5,
                         va="center",ha="left")
        axm.set_title("the day on one map — tests bound it, anchor holds it",color="#8b949e",fontsize=9,loc="left",pad=3)
        emit("read",fr)
    _rsig=repr((sel_ts.isoformat(),sel_i,len(snaps)))
    dispatch("read",_render_read,sig=_rsig)
