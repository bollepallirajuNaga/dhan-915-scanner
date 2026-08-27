import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from dhanhq import DhanContext, dhanhq

# Page configuration
st.set_page_config(
    page_title="9:15 F&O Production Scanner",
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ 9:15 F&O Top Gainer Scanner")
st.caption("Production Engine • Live NSE F&O Universe • Tradetron Webhook")

# ================= 1. PRODUCTION CONFIGURATION =================
# మీ శాశ్వత ఐడీలు
CLIENT_ID = "1113235897"            # మీ 10-అంకెల Dhan Client ID
TT_WEBHOOK_URL = "https://api.tradetron.tech/api"
TT_AUTH_TOKEN = "41cd0696-63ed-43da-8145-a2357d2c8cdb" # మీ Tradetron Auth Token

IST = pytz.timezone("Asia/Kolkata")

# ================= 2. LIVE F&O SCRIP MASTER LOADER =================
@st.cache_data(ttl=86400)
def load_live_fo_universe():
    """Dhan official master నుండి మొత్తం F&O Universe (~180+ stocks) ను డైనమిక్‌గా లోడ్ చేస్తుంది"""
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    df = pd.read_csv(url, low_memory=False)
    
    # 1. Active Stock Futures (FUTSTK) అండర్‌లైయింగ్ సింబల్స్‌ను ఫిల్టర్ చేయడం
    fno_symbols = set(df[df["SEM_INSTRUMENT_NAME"] == "FUTSTK"]["SM_UNDERLYING_SYMBOL"].dropna().unique())
    
    # 2. NSE Cash Equity సెగ్మెంట్‌లో ఉన్న సరైన Security IDs ని మ్యాప్ చేయడం
    nse_eq = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")]
    fno_eq = nse_eq[nse_eq["SEM_TRADING_SYMBOL"].isin(fno_symbols)]
    
    # {Symbol: Security_ID} డిక్షనరీ నిర్మాణం
    stock_map = dict(zip(fno_eq["SEM_TRADING_SYMBOL"], fno_eq["SEM_SMST_SECURITY_ID"].astype(str)))
    return stock_map

# ================= 3. USER INTERFACE =================
st.markdown("---")
access_token = st.text_input("🔑 Today's Dhan Access Token:", type="password", placeholder="Paste daily token from Dhan Web here")

start_btn = st.button("🚀 Start Production 9:15 Scanner", use_container_width=True, type="primary")

if start_btn:
    if not access_token:
        st.error("❌ Please paste today's Dhan Access Token to proceed!")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        # Step 1: Initialize Dhan Connection
        status_box.info("📡 Connecting to DhanHQ Production API...")
        try:
            context = DhanContext(CLIENT_ID, access_token)
            dhan = dhanhq(context)
        except Exception as e:
            st.error(f"❌ Failed to initialize Dhan Client: {e}")
            st.stop()
            
        # Step 2: Load Full F&O Scrip Universe
        status_box.info("📥 Fetching official NSE F&O Universe (~180+ Stocks)...")
        try:
            FO_STOCKS = load_live_fo_universe()
            progress_bar.progress(20)
            status_box.success(f"✅ Loaded {len(FO_STOCKS)} active F&O Stocks from Dhan Master!")
        except Exception as e:
            st.error(f"❌ Failed to load Scrip Master: {e}")
            st.stop()
            
        # Step 3: Precision 09:15:35 AM IST Wait Window
        while True:
            now_ist = datetime.now(IST)
            if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
                break
            elif now_ist.hour > 9 or (now_ist.hour == 9 and now_ist.minute > 15):
                # 09:16 దాటిన తర్వాత రన్ చేస్తే ఆలస్యం లేకుండా వెంటనే స్కాన్ అవుతుంది
                break
                
            current_time_str = now_ist.strftime("%H:%M:%S")
            status_box.warning(f"🕒 Current Time: **{current_time_str}** | Waiting for **09:15:35 AM**...")
            time.sleep(0.3)
            
        progress_bar.progress(40)
        status_box.info(f"⚡ Scanning all {len(FO_STOCKS)} F&O stocks concurrently in real-time...")
        
        # Step 4: Multi-Threaded Quote Fetcher
        def fetch_single_stock(item):
            symbol, sec_id = item
            try:
                quote = dhan.get_quote(security_id=sec_id, exchange_segment="NSE_EQ")
                if quote and quote.get("status") == "success":
                    data = quote.get("data", {})
                    ltp = float(data.get("last_price", 0))
                    prev_close = float(data.get("ohlc", {}).get("close", 0))
                    
                    if prev_close > 0 and ltp > 0:
                        p_change = ((ltp - prev_close) / prev_close) * 100
                        return {"symbol": symbol, "ltp": ltp, "prev_close": prev_close, "p_change": p_change}
            except Exception:
                pass
            return None

        # 10 ప్యారలల్ వర్కర్లతో వేగంగా స్కాన్ చేయడం
        start_scan_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(fetch_single_stock, FO_STOCKS.items()))
            
        scan_duration = time.time() - start_scan_time
        market_data = [r for r in results if r is not None]
        progress_bar.progress(80)

        if not market_data:
            st.error("❌ No market data received. Please verify if Dhan Token is valid and active.")
        else:
            # Step 5: Ranking & Picking Absolute #1 Top Gainer
            df = pd.DataFrame(market_data).sort_values(by="p_change", ascending=False).reset_index(drop=True)
            top_stock = df.iloc[0]["symbol"]
            top_change = df.iloc[0]["p_change"]
            top_ltp = df.iloc[0]["ltp"]
            top_prev = df.iloc[0]["prev_close"]
            
            st.success(
                f"🎯 **#1 TOP GAINER:** `{top_stock}` | "
                f"LTP: ₹{top_ltp:.2f} | Prev Close: ₹{top_prev:.2f} | "
                f"Gain: **+{top_change:.2f}%** (Scanned {len(market_data)} stocks in {scan_duration:.2f}s)"
            )
            
            # Step 6: Post Signal to Tradetron Webhook
            payload = {
                "auth-token": TT_AUTH_TOKEN,
                "key": "api_buy",
                "value": "1",
                "symbol": top_stock
            }
            
            try:
                res = requests.post(TT_WEBHOOK_URL, json=payload, timeout=10)
                progress_bar.progress(100)
                st.balloons()
                st.success(f"✅ **Signal Delivered to Tradetron!** (Response Code: {res.status_code})")
                st.info(f"🚀 Cloud Engine is now actively managing trades for **{top_stock}**.")
            except Exception as e:
                st.error(f"⚠️ Webhook Delivery Failed: {e}")
