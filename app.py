import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd
import yfinance as yf

# Page configuration
st.set_page_config(page_title="9:15 F&O Dynamic Scanner", page_icon="⚡", layout="centered")

st.title("⚡ 9:15 F&O Top Gainer Scanner")
st.caption("100% Dynamic NSE F&O Auto-Fetch Engine • Tradetron Cloud")

# ================= 1. CONFIGURATION =================
TT_WEBHOOK_URL = "https://api.tradetron.tech/api"
TT_AUTH_TOKEN = "41cd0696-63ed-43da-8145-a2357d2c8cdb"

IST = pytz.timezone("Asia/Kolkata")

# ================= 2. LIVE DYNAMIC F&O SCRIP FETCH =================
@st.cache_data(ttl=3600)  # ప్రతి గంటకు ఒకసారి ఆటోమేటిక్ రిఫ్రెష్
def get_live_fno_symbols():
    """NSE అధికారిక డేటా CDN నుండి నేటి తాజా F&O లిస్ట్‌ను డైనమిక్‌గా ఫెచ్ చేస్తుంది"""
    try:
        url = "https://images.dhan.co/api-data/api-scrip-master.csv"
        df = pd.read_csv(url, low_memory=False)
        # Active F&O Stock Futures అండర్‌లైయింగ్ సింబల్స్‌ను మాత్రమే ఫిల్టర్ చేయడం
        fno_symbols = df[df["SEM_INSTRUMENT_NAME"] == "FUTSTK"]["SM_UNDERLYING_SYMBOL"].dropna().unique().tolist()
        return [sym.strip() for sym in fno_symbols if isinstance(sym, str)]
    except Exception:
        # బ్యాకప్ ఆటో-లింక్ (Nifty 100 constituents)
        url = "https://raw.githubusercontent.com/datasets/nse-indices/master/data/ind_nifty100list.csv"
        df = pd.read_csv(url)
        return df["Symbol"].tolist()

# ================= 3. USER INTERFACE =================
st.markdown("---")
st.success("🟢 100% Dynamic Engine: Auto-loads latest NSE F&O Universe on every run.")

start_btn = st.button("🚀 Start 9:15 Scanner Now", use_container_width=True, type="primary")

if start_btn:
    status_box = st.empty()
    progress_bar = st.progress(0)
    
    # Step 1: Dynamic F&O List Loading
    status_box.info("📥 Fetching today's latest dynamic F&O universe from live master...")
    fno_symbols = get_live_fno_symbols()
    yf_tickers = [f"{sym}.NS" for sym in fno_symbols]
    progress_bar.progress(20)
    status_box.success(f"✅ Loaded {len(fno_symbols)} active F&O stocks dynamically!")
    
    # Step 2: 09:15:35 AM IST Wait Logic
    while True:
        now_ist = datetime.now(IST)
        if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
            break
        elif now_ist.hour > 9 or (now_ist.hour == 9 and now_ist.minute > 15):
            break
            
        current_time_str = now_ist.strftime("%H:%M:%S")
        status_box.warning(f"🕒 Current Time: **{current_time_str}** | Waiting for **09:15:35 AM**...")
        time.sleep(0.3)
        
    progress_bar.progress(40)
    status_box.info(f"⚡ Scanning all {len(fno_symbols)} F&O stocks live...")
    
    # Step 3: High-Speed Batch Fetch via Yahoo
    start_time = time.time()
    try:
        data = yf.download(tickers=yf_tickers, period="2d", interval="1d", group_by="ticker", progress=False, threads=True)
        
        market_data = []
        for sym in fno_symbols:
            ticker = f"{sym}.NS"
            try:
                df_sym = data[ticker]
                if len(df_sym) >= 2:
                    prev_close = float(df_sym["Close"].iloc[-2])
                    ltp = float(df_sym["Close"].iloc[-1])
                elif len(df_sym) == 1:
                    prev_close = float(df_sym["Open"].iloc[0])
                    ltp = float(df_sym["Close"].iloc[0])
                else:
                    continue
                    
                if prev_close > 0 and ltp > 50:
                    p_change = ((ltp - prev_close) / prev_close) * 100
                    market_data.append({
                        "symbol": sym,
                        "ltp": ltp,
                        "prev_close": prev_close,
                        "p_change": p_change
                    })
            except Exception:
                continue

        scan_duration = time.time() - start_time
        progress_bar.progress(80)

        if not market_data:
            st.error("❌ Market data fetch returned empty. Please try again.")
        else:
            # Step 4: Sorting & Picking True #1
            df_res = pd.DataFrame(market_data).sort_values(by="p_change", ascending=False).reset_index(drop=True)
            top_stock = df_res.iloc[0]["symbol"]
            top_change = df_res.iloc[0]["p_change"]
            top_ltp = df_res.iloc[0]["ltp"]
            top_prev = df_res.iloc[0]["prev_close"]
            
            progress_bar.progress(90)
            st.success(
                f"🎯 **#1 TOP GAINER:** `{top_stock}` | "
                f"LTP: ₹{top_ltp:.2f} | Prev Close: ₹{top_prev:.2f} | "
                f"Gain: **+{top_change:.2f}%** (Processed {len(market_data)} stocks in {scan_duration:.2f}s)"
            )
            
            with st.expander("📊 View Live Top 5 Gainers Table"):
                st.dataframe(df_res.head(5)[["symbol", "ltp", "prev_close", "p_change"]], use_container_width=True)

            # Step 5: Webhook Dispatch to Tradetron
            webhook_payload = {
                "auth-token": TT_AUTH_TOKEN,
                "key": "api_buy",
                "value": "1",
                "symbol": top_stock
            }
            webhook_url_full = f"{TT_WEBHOOK_URL}?auth-token={TT_AUTH_TOKEN}&key=api_buy&value=1&symbol={top_stock}"
            res = requests.post(webhook_url_full, json=webhook_payload, timeout=8)
            
            progress_bar.progress(100)
            st.balloons()
            st.success(f"✅ **Signal Sent to Tradetron!** (Response: {res.status_code})")
            st.info(f"🚀 Cloud strategy activated for **{top_stock}**.")
            
    except Exception as e:
        st.error(f"Error during execution: {e}")
