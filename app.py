import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from dhanhq import DhanContext, dhanhq

# Page configuration
st.set_page_config(page_title="9:15 Algo Scanner (All 180+ F&O)", page_icon="⚡", layout="centered")

st.title("⚡ 9:15 F&O Top Gainer Scanner")
st.caption("Full Universe (~180+ Stocks) Auto-Scanner & Tradetron Webhook")

# ================= 1. CONFIGURATION =================
CLIENT_ID = "1113235897"            # మీ 10-అంకెల Dhan Client ID
TT_WEBHOOK_URL = "https://api.tradetron.tech/api"
TT_AUTH_TOKEN = "41cd0696-63ed-43da-8145-a2357d2c8cdb" # మీ Tradetron Auth Token

IST = pytz.timezone("Asia/Kolkata")

# ================= 2. F&O స్క్రిప్ మాస్టర్ లోడ్ చేయడం =================
@st.cache_data(ttl=86400)
def load_fo_universe():
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    df = pd.read_csv(url, low_memory=False)
    
    # కేవలం NSE Equity లో ఉన్న F&O స్టాక్స్ సెక్యూరిటీ ఐడీలను ఫిల్టర్ చేయడం
    fno_symbols = df[df["SEM_INSTRUMENT_NAME"] == "FUTSTK"]["SM_UNDERLYING_SYMBOL"].unique()
    nse_eq = df[(df["SEM_EXM_EXCH_ID"] == "NSE") & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")]
    fno_eq = nse_eq[nse_eq["SEM_TRADING_SYMBOL"].isin(fno_symbols)]
    
    stock_dict = dict(zip(fno_eq["SEM_TRADING_SYMBOL"], fno_eq["SEM_SMST_SECURITY_ID"].astype(str)))
    return stock_dict

# ================= 3. USER INTERFACE =================
st.markdown("---")
access_token = st.text_input("🔑 Today's Dhan Access Token:", type="password", placeholder="Paste daily token here")

start_btn = st.button("🚀 Start 9:15 Full Universe Scanner", use_container_width=True, type="primary")

if start_btn:
    if not access_token:
        st.error("❌ Please paste Dhan Access Token first!")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        status_box.info("📥 Loading complete NSE F&O Scrip Universe (~180+ Stocks)...")
        try:
            FO_STOCKS = load_fo_universe()
            status_box.success(f"✅ Loaded {len(FO_STOCKS)} F&O Stocks successfully!")
        except Exception:
            st.error("Failed to load Dhan Scrip master. Falling back to default list.")
            FO_STOCKS = {"RELIANCE": "2885", "HDFCBANK": "1333", "ICICIBANK": "4963", "INFY": "1594", "SBIN": "3045"}

        context = DhanContext(CLIENT_ID, access_token)
        dhan = dhanhq(context)
        
        # 09:15:35 వరకు లైవ్ కౌంట్‌డౌన్
        while True:
            now_ist = datetime.now(IST)
            if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
                break
            elif now_ist.hour > 9 or (now_ist.hour == 9 and now_ist.minute > 15):
                break
                
            current_time_str = now_ist.strftime("%H:%M:%S")
            status_box.warning(f"🕒 Current Time: **{current_time_str}** | Waiting for **09:15:35**...")
            time.sleep(0.5)
            
        progress_bar.progress(30)
        status_box.info(f"⚡ Fast-Scanning all {len(FO_STOCKS)} F&O stocks concurrently...")
        
        # 180+ స్టాక్స్ డేటాను వేగంగా ఫెచ్ చేసే ఫంక్షన్
        def fetch_stock_data(item):
            symbol, sec_id = item
            try:
                quote = dhan.get_quote(security_id=sec_id, exchange_segment="NSE_EQ")
                if quote and quote.get("status") == "success":
                    data = quote["data"]
                    ltp = float(data.get("last_price", 0))
                    prev_close = float(data.get("ohlc", {}).get("close", ltp))
                    
                    if prev_close > 0:
                        p_change = ((ltp - prev_close) / prev_close) * 100
                        # మన ఫిల్టర్లు: LTP > 50 & Change% <= 4%
                        if ltp > 50 and p_change <= 4.0:
                            return {"symbol": symbol, "ltp": ltp, "p_change": p_change}
            except Exception:
                pass
            return None

        # Multi-threading (10 Threads parallel execution)
        market_data = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(fetch_stock_data, FO_STOCKS.items())
            market_data = [r for r in results if r is not None]

        progress_bar.progress(70)

        if not market_data:
            st.error("❌ No matching stock found satisfying filters. Please check Dhan Token validity.")
        else:
            # % Change ప్రకారం Sort చేసి #1 టాప్ స్టాక్ ఎంపిక
            df = pd.DataFrame(market_data).sort_values(by="p_change", ascending=False).reset_index(drop=True)
            top_stock = df.iloc[0]["symbol"]
            top_change = df.iloc[0]["p_change"]
            top_ltp = df.iloc[0]["ltp"]
            
            progress_bar.progress(85)
            st.success(f"🎯 **#1 TOP GAINER (Out of {len(market_data)} valid stocks):** `{top_stock}` | LTP: ₹{top_ltp} | Change: +{top_change:.2f}%")
            
            # Tradetron Webhook కు పోస్ట్ చేయడం
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
                st.success(f"✅ **Signal Sent to Tradetron Successfully!** (Status: {res.status_code})")
                st.info(f"Strategy is now active on cloud for **{top_stock}**. You can close this tab.")
            except Exception as e:
                st.error(f"⚠️ Webhook Delivery Failed: {e}")
        
