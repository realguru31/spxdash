"""
colab_diagnostic.py — Barchart SPX Options Data Diagnostic
Run this in Google Colab BEFORE deploying the full Streamlit app.

Tests:
  1. Session initialization + XSRF token acquisition
  2. SPX spot price fetch
  3. SPX options chain fetch (0DTE)
  4. Field verification (all required columns present)
  5. Sample GEX calculations
  6. Latency measurements
"""

# !pip install requests pandas numpy -q  # Uncomment in Colab

import requests
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

# ===========================================================================
# CONFIG
# ===========================================================================
BARCHART_BASE = "https://www.barchart.com"
OPTIONS_URL = f"{BARCHART_BASE}/proxies/core-api/v1/options/chain"
QUOTE_URL = f"{BARCHART_BASE}/proxies/core-api/v1/quotes/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": f"{BARCHART_BASE}/stocks/quotes/$SPX/options",
}

# ===========================================================================
# DIAGNOSTIC FUNCTIONS
# ===========================================================================

def test_session():
    """Test 1: Session initialization"""
    print("=" * 60)
    print("TEST 1: Session Initialization")
    print("=" * 60)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    t0 = time.time()
    try:
        resp = session.get(f"{BARCHART_BASE}/stocks/quotes/$SPX/options", timeout=15)
        latency = time.time() - t0
        
        print(f"  Status: {resp.status_code}")
        print(f"  Latency: {latency:.2f}s")
        
        xsrf = session.cookies.get("XSRF-TOKEN")
        if xsrf:
            print(f"  XSRF Token: {xsrf[:20]}...")
            session.headers["X-XSRF-TOKEN"] = xsrf
            print("  ✅ Session initialized successfully")
        else:
            print("  ⚠️ No XSRF token found (may still work)")
            
        return session
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return None


def test_spot_price(session):
    """Test 2: SPX Spot Price"""
    print("\n" + "=" * 60)
    print("TEST 2: SPX Spot Price")
    print("=" * 60)
    
    t0 = time.time()
    try:
        resp = session.get(QUOTE_URL, params={
            "symbol": "$SPX",
            "fields": "lastPrice,previousClose,netChange,percentChange,highPrice,lowPrice,openPrice"
        }, timeout=10)
        latency = time.time() - t0
        
        print(f"  Status: {resp.status_code}")
        print(f"  Latency: {latency:.2f}s")
        
        data = resp.json()
        results = data.get("data", [])
        if results:
            raw = results[0].get("raw", results[0])
            spot = float(raw.get("lastPrice", 0))
            print(f"  SPX Last: {spot:.2f}")
            print(f"  Change: {raw.get('netChange', 'N/A')}")
            print(f"  High: {raw.get('highPrice', 'N/A')}")
            print(f"  Low: {raw.get('lowPrice', 'N/A')}")
            print(f"  ✅ Spot price fetched successfully")
            return spot
        else:
            print("  ❌ No data returned")
            return None
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return None


def test_options_chain(session, spot):
    """Test 3: Options Chain Fetch"""
    print("\n" + "=" * 60)
    print("TEST 3: Options Chain (0DTE)")
    print("=" * 60)
    
    today = date.today().strftime("%Y-%m-%d")
    print(f"  Expiration: {today}")
    
    t0 = time.time()
    try:
        params = {
            "symbol": "$SPX",
            "fields": "strikePrice,bid,ask,last,highPrice,lowPrice,openPrice,"
                      "mark,delta,gamma,vega,theta,impliedVolatility,openInterest,"
                      "volume,optionType,expirationDate",
            "expiration": today,
            "meta": "field.shortName,field.type,field.description",
            "raw": "1",
            "hasQuotes": "true",
        }
        resp = session.get(OPTIONS_URL, params=params, timeout=15)
        latency = time.time() - t0
        
        print(f"  Status: {resp.status_code}")
        print(f"  Latency: {latency:.2f}s")
        
        data = resp.json()
        rows = data.get("data", [])
        print(f"  Rows returned: {len(rows)}")
        
        if not rows:
            # Try tomorrow
            tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"  No 0DTE data. Trying {tomorrow}...")
            params["expiration"] = tomorrow
            resp = session.get(OPTIONS_URL, params=params, timeout=15)
            data = resp.json()
            rows = data.get("data", [])
            print(f"  Rows returned: {len(rows)}")
        
        if rows:
            # Parse
            records = []
            for row in rows:
                raw = row.get("raw", row)
                records.append({
                    "strike": raw.get("strikePrice"),
                    "type": raw.get("optionType"),
                    "bid": raw.get("bid"),
                    "ask": raw.get("ask"),
                    "last": raw.get("last"),
                    "high": raw.get("highPrice"),
                    "low": raw.get("lowPrice"),
                    "open": raw.get("openPrice"),
                    "mark": raw.get("mark"),
                    "delta": raw.get("delta"),
                    "gamma": raw.get("gamma"),
                    "vega": raw.get("vega"),
                    "theta": raw.get("theta"),
                    "iv": raw.get("impliedVolatility"),
                    "oi": raw.get("openInterest"),
                    "volume": raw.get("volume"),
                })
            
            df = pd.DataFrame(records)
            print(f"\n  DataFrame shape: {df.shape}")
            print(f"  Columns: {list(df.columns)}")
            print(f"  Strike range: {df['strike'].min()} — {df['strike'].max()}")
            print(f"  Call count: {(df['type'] == 'Call').sum()}")
            print(f"  Put count: {(df['type'] == 'Put').sum()}")
            
            # Field verification
            print("\n  --- Field Verification ---")
            required = ["strike", "type", "bid", "ask", "delta", "gamma", "iv", "oi", "volume"]
            for f in required:
                non_null = df[f].notna().sum()
                pct = non_null / len(df) * 100
                status = "✅" if pct > 50 else "⚠️" if pct > 0 else "❌"
                print(f"  {status} {f}: {non_null}/{len(df)} ({pct:.0f}%) non-null")
            
            # Sample near ATM
            if spot:
                atm = round(spot / 5) * 5
                near = df[(df["strike"] >= atm - 25) & (df["strike"] <= atm + 25)]
                print(f"\n  --- Near-ATM Sample (±25 pts around {atm}) ---")
                print(near[["strike", "type", "mark", "delta", "gamma", "oi", "volume"]].to_string(index=False))
            
            print(f"\n  ✅ Options chain fetched successfully")
            return df
        else:
            print("  ❌ No chain data available")
            return None
            
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_gex_calculation(df, spot):
    """Test 4: GEX Calculation Verification"""
    print("\n" + "=" * 60)
    print("TEST 4: GEX Calculation Sample")
    print("=" * 60)
    
    if df is None or spot is None:
        print("  ⚠️ Skipped (no data)")
        return
    
    calls = df[df["type"] == "Call"].copy()
    puts = df[df["type"] == "Put"].copy()
    
    # Merge
    calls = calls.rename(columns={c: f"c_{c}" for c in calls.columns if c not in ("strike",)})
    puts = puts.rename(columns={c: f"p_{c}" for c in puts.columns if c not in ("strike",)})
    merged = pd.merge(calls, puts, on="strike", how="outer")
    
    for col in ["c_gamma", "c_oi", "p_gamma", "p_oi", "c_delta", "p_delta"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    
    # GEX
    merged["call_gex"] = np.round(merged["c_oi"] * merged["c_gamma"] * 100, 0)
    merged["put_gex"] = -np.round(merged["p_gamma"] * merged["p_oi"] * 100, 0)
    merged["net_gex"] = merged["call_gex"] + merged["put_gex"]
    
    # S²-normalized
    s2 = spot * spot / 1e9
    merged["raw_cgex"] = merged["c_gamma"] * s2 * merged["c_oi"]
    merged["raw_pgex"] = -merged["p_gamma"] * s2 * merged["p_oi"]
    
    atm = round(spot / 5) * 5
    near = merged[(merged["strike"] >= atm - 25) & (merged["strike"] <= atm + 25)].sort_values("strike", ascending=False)
    
    print(f"  ATM: {atm}")
    print(f"  Total Net GEX: {merged['net_gex'].sum():,.0f}")
    print(f"  Max +GEX strike: {merged.loc[merged['net_gex'].idxmax(), 'strike']}")
    print(f"  Max -GEX strike: {merged.loc[merged['net_gex'].idxmin(), 'strike']}")
    
    gex_ratio = merged["call_gex"].sum() / abs(merged["put_gex"].sum()) if merged["put_gex"].sum() != 0 else 999
    print(f"  GEX Ratio: {gex_ratio:.2f} → {'CALL' if gex_ratio >= 1 else 'PUT'} dominant")
    
    print(f"\n  Near-ATM GEX:")
    print(near[["strike", "call_gex", "put_gex", "net_gex", "raw_cgex", "raw_pgex"]].to_string(index=False))
    print(f"\n  ✅ GEX calculations verified")


def test_expirations(session):
    """Test 5: Available Expirations"""
    print("\n" + "=" * 60)
    print("TEST 5: Available Expirations")
    print("=" * 60)
    
    try:
        params = {"symbol": "$SPX", "fields": "expirationDate", "meta": "field.shortName", "raw": "1"}
        resp = session.get(OPTIONS_URL, params=params, timeout=10)
        data = resp.json()
        exps = data.get("meta", {}).get("expirations", [])
        if exps:
            print(f"  Found {len(exps)} expirations")
            for e in exps[:10]:
                print(f"    {e}")
            if len(exps) > 10:
                print(f"    ... and {len(exps) - 10} more")
            print(f"  ✅ Expirations list fetched")
        else:
            print("  ⚠️ No expirations in meta (may need different parsing)")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")


# ===========================================================================
# RUN ALL TESTS
# ===========================================================================
if __name__ == "__main__":
    print("🔍 SPX Gamma Dashboard — Barchart Data Diagnostic")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    session = test_session()
    if session is None:
        print("\n💀 Cannot proceed without session. Check network/VPN.")
    else:
        spot = test_spot_price(session)
        df = test_options_chain(session, spot)
        test_gex_calculation(df, spot)
        test_expirations(session)
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
