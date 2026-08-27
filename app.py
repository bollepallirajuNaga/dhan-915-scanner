import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd
import yfinance as yf

# 1. Page Configuration
st.set_page_config(
    page_title="9:15 NIFTY 50 Scanner",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ 9:15 Top Gainer Scanner & Tradetron Bridge")
st.caption("Tradetron Cloud Execution • NIFTY 50 Universe")

# ================= CONFIGURATION =================
TT_WEBHOOK_URL = "https://api.tradetron.tech/api"
TT_AUTH_TOKEN = "41cd0696-63ed-43da-8145-a2357d2c8cdb"
IST = pytz.timezone("Asia/Kolkata")

# NIFTY 50 Default Base Universe
DEFAULT_FNO_SYMBOLS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL", 
    "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", 
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", 
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", 
    "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", 
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", 
    "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", "SBIN", 
    "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", 
    "TECHM", "TITAN", "ULTRACEMCO", "WIPRO", "BEL"
]

# ================= 2. DYNAMIC UNIVERSE LOADER =================
@st.cache_data(ttl=86400)
def load_dynamic_universe():
    try:
        url = "https://raw.githubusercontent.com/bollepallirajuNaga/dhan-915-scanner/main/fno_stocks.txt"
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            lines = [line.strip().upper() for line in res.text.splitlines() if line.strip()]
            if len(lines) >= 40:
                return lines
    except Exception:
        pass
    return DEFAULT_FNO_SYMBOLS

FNO_SYMBOLS = load_dynamic_universe()
YF_TICKERS = [f"{sym}.NS" for sym in FNO_SYMBOLS]

# ================= 3. SCANNER ENGINE FUNCTION =================
def execute_scan_and_webhook():
    status_box = st.empty()
    progress_bar = st.progress(30)
    status_box.info(f"⚡ Scanning all {len(FNO_SYMBOLS)} stocks in parallel...")
    
    start_time = time.time()
    try:
        df_all = yf.download(tickers=YF_TICKERS, period="5d", interval="1d", progress=False)
        market_data = []
        close_prices = df_all["Close"]
        
        for sym in FNO_SYMBOLS:
            ticker = f"{sym}.NS"
            try:
                if ticker in close_prices.columns:
                    s = close_prices[ticker].dropna()
                    if len(s) >= 2:
                        prev_close = float(s.iloc[-2])
                        ltp = float(s.iloc[-1])
                        
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
            
            with st.expander("📊 View Live Top 5 Gainers Table", expanded=True):
                st.dataframe(df_res.head(8)[["symbol", "ltp", "prev_close", "p_change"]], use_container_width=True)

            # Webhook Post to Tradetron
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
        st.error(f"Error during scan: {e}")

# ================= 4. USER INTERFACE (DUAL BUTTONS) =================
st.markdown("---")
st.success(f"🟢 **System Ready:** {len(FNO_SYMBOLS)} NIFTY 50 Stocks loaded.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("⚡ Instant Test")
    if st.button("🚀 Run Instant Scan (No Wait)", use_container_width=True):
        execute_scan_and_webhook()

with col2:
    st.subheader("⏰ Auto-Pilot (9:10 - 9:15 AM)")
    arm_btn = st.button("🛡️ Arm Auto-Pilot Schedule", use_container_width=True, type="primary")
    
    if arm_btn:
        status_box = st.empty()
        
        while True:
            now_ist = datetime.now(IST)
            current_time_str = now_ist.strftime("%H:%M:%S")
            
            if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
                status_box.success(f"🚀 Trigger Time reached ({current_time_str})! Running Scanner...")
                execute_scan_and_webhook()
                break
            elif now_ist.hour > 9 or (now_ist.hour == 9 and now_ist.minute > 15):
                status_box.info("Market already past 09:15:35 AM. Running scanner now...")
                execute_scan_and_webhook()
                break
                
            status_box.warning(f"🕒 Current IST: **{current_time_str}** | Auto-Trigger at **09:15:35 AM**...")
            time.sleep(0.5)
