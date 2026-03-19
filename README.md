# SPX Gamma Exposure Dashboard

A production-grade Streamlit web app that replicates the RTD-based **SPX_Gamma_Dashboard_v1_3b.xlsm** Excel workbook, powered by **Barchart** data instead of ThinkOrSwim RTD.

## Features

- **Real-time SPX options chain** with auto-refresh (60s)
- **Gamma Exposure (GEX)** calculations — raw, S²-normalized, and delta-adjusted
- **Delta Exposure (DEX)** calculations
- **Key Levels**: Call Wall, Put Wall, COI, POI, +GEX, −GEX, transition zones
- **Gamma regime detection** (Call vs Put dominant)
- **Buying pressure** estimation from OHLC data
- **Put/Call ratios** (volume and OI)
- **GEX profile charts** (bar chart + S²-normalized profile)
- **Open Interest profile** visualization
- **Expiration selection** (0DTE, tomorrow, Friday, OPEX)
- **CSV export** for chain data and levels
- **Password protection** via server-side secrets
- **Dark theme** optimized for trading

---

## Architecture

```
app.py              ← Main Streamlit dashboard (UI + layout)
data_fetcher.py     ← Barchart session management + API calls
calculations.py     ← All Excel formula replication (GEX, DEX, levels)
utils.py            ← Auth, formatting, time utilities
colab_diagnostic.py ← Standalone Barchart connectivity test
```

### Data Flow
```
Barchart → data_fetcher.py → raw DataFrame
         → calculations.py  → compute_chain_metrics() → derived columns
                             → compute_dashboard_levels() → key levels dict
         → app.py           → Streamlit UI rendering
```

### Excel Formula Mapping

| Excel Column | Calculation | Python Column |
|---|---|---|
| AI (Call GEX) | `ROUND(Call_OI × Call_Gamma × 100, 0)` | `call_gex` |
| AJ (Put GEX) | `-ROUND(Put_Gamma × Put_OI × 100, 0)` | `put_gex` |
| AK (Net GEX) | `Call_GEX + Put_GEX` | `net_gex` |
| AL (Call DEX) | `ROUND(Call_Delta × Call_OI × 100, 0)` | `call_dex` |
| AM (Put DEX) | `ROUND(Put_Delta × Put_OI × 100, 0)` | `put_dex` |
| AN (Net DEX) | `Call_DEX + Put_DEX` | `net_dex` |
| AE (AbsDelta) | `Call_Delta + ABS(Put_Delta)` | `abs_delta` |
| AO (B%Call) | OHLC buying pressure formula | `bp_call` |
| AP (B%Put) | OHLC buying pressure formula | `bp_put` |
| AT-BA | S²-normalized GEX profile | `raw_cgex`, `raw_pgex`, `dadj_*` |

### Dashboard Levels (N18–N25 in Excel)

| Level | Logic |
|---|---|
| Call Wall | Strike with max Call OI |
| Put Wall | Strike with max Put OI |
| COI | Strike with max Call OI |
| POI | Strike with max Put OI |
| +GEX | Strike with max positive Net GEX |
| −GEX | Strike with max negative Net GEX |
| +Transition | GEX zero-crossing above spot |
| −Transition | GEX zero-crossing below spot |

---

## Setup

### 1. Local Development

```bash
# Clone
git clone https://github.com/YOUR_USER/spx-gamma-dashboard.git
cd spx-gamma-dashboard

# Install
pip install -r requirements.txt

# Configure password
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml → set APP_PASSWORD

# Run
streamlit run app.py
```

### 2. Pre-Deployment Test (Google Colab)

Before deploying, run the diagnostic in Colab to verify Barchart connectivity:

```python
# In Colab:
!pip install requests pandas numpy -q
# Upload colab_diagnostic.py or paste its contents
!python colab_diagnostic.py
```

This verifies:
- Session/XSRF token acquisition
- SPX spot price fetch
- Options chain data availability
- All required fields present
- Sample GEX calculations
- Latency measurements

### 3. GitHub Repository

```bash
git init
git add .
git commit -m "SPX Gamma Dashboard v2.0"
git remote add origin https://github.com/YOUR_USER/spx-gamma-dashboard.git
git push -u origin main
```

**⚠️ `.streamlit/secrets.toml` is in `.gitignore` — it will NOT be pushed.**

### 4. Streamlit Cloud Deployment

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repo
3. Set main file path: `app.py`
4. **Configure Secrets:**
   - Click "Advanced settings" → "Secrets"
   - Paste:
     ```toml
     APP_PASSWORD = "your_secure_password"
     ```
5. Deploy

### 5. Update Password Later

- **Streamlit Cloud**: Settings → Secrets → edit `APP_PASSWORD` → Save
- **Local**: Edit `.streamlit/secrets.toml`
- No code changes or redeployment needed

---

## Security Notes

### Why `secrets.toml` is Safe

1. **Server-side only**: `secrets.toml` is never sent to the browser. It lives on the Streamlit server and is accessed via `st.secrets`.
2. **Git-excluded**: Listed in `.gitignore`, never committed to version control.
3. **Streamlit Cloud**: Secrets are encrypted at rest and injected at runtime.
4. **No hardcoding**: The password is never in source code.
5. **Session-based**: Authentication state is per-session, not persistent.

---

## Configuration

### Sidebar Controls

| Control | Description |
|---|---|
| Expiration | 0DTE / Tomorrow / Friday / OPEX |
| Strikes above/below ATM | How many strikes to show (5–40) |
| Show Calls/Puts | Toggle columns |
| Show Greeks | Toggle delta/gamma/IV columns |
| Show Buying Pressure | Toggle BP% columns |
| Auto-refresh | Enable/disable 60s refresh |

---

## Troubleshooting

| Issue | Fix |
|---|---|
| "Could not fetch options chain" | Wait 30s and retry. Barchart may rate-limit. |
| Stale data | Click "Refresh Now" or toggle auto-refresh. |
| Missing greeks | Some deep OTM strikes may lack greeks from Barchart. |
| XSRF errors | Session will auto-reinitialize. If persistent, restart app. |
| Market closed | Data shows last available quotes. GEX levels still valid. |

---

## License

Private / personal use.

## Credits

- Original Excel workbook: Robert Payne (funwiththinkscript.com)
- Streamlit conversion: Built with Claude
