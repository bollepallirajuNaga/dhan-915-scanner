import streamlit as st
import pandas as pd
import requests
import datetime
import time
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

# Page Configuration
st.set_page_config(page_title="9:15 NIFTY 50 Scanner", page_icon="🎯", layout="wide")

st.title("🎯 9:15 NIFTY 50 Scanner & Tradetron Bridge")
st.caption("Auto-picks the #1 Top Gainer at 09:15:35 AM IST and pushes it to Tradetron")

# IST Timezone Setup
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Settings & Credentials")
tradetron_auth_token = st.sidebar.text_input(
    "Tradetron Auth Token",
    type="password",
    help="Enter your Tradetron webhook auth token"
)

# Load Stock Universe
@st.cache_data
def load_stock_list():
    try:
        with open("fno_stocks.txt", "r") as f:
            stocks = [line.strip().upper() for line in f if line.strip()]
        return stocks
    except Exception:
        # Fallback default NIFTY 50 list
        return [
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

stock_universe = load_stock_list()

# --- FAST SCANNER CORE ---
def fetch_stock_data(symbol):
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        fast_info = ticker.fast_info
        ltp = round(fast_info.last_price, 2)
        prev_close = round(fast_info.previous_close, 2)
        
        if prev_close and prev_close > 0:
            p_change = round(((ltp - prev_close) / prev_close) * 100, 4)
            return {"symbol": symbol, "ltp": ltp, "prev_close": prev_close, "p_change": p_change}
    except Exception:
        pass
    return None

def run_scanner():
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(fetch_stock_data, sym) for sym in stock_universe]
        for f in futures:
            res = f.result()
            if res is not None:
                results.append(res)
                
    elapsed = round(time.time() - start_time, 2)
    df = pd.DataFrame(results)
    
    if df.empty:
        return None, df, elapsed
    
    # Sort descending by % Change
    df = df.sort_values(by="p_change", ascending=False).reset_index(drop=True)
    top_stock = df.iloc[0]
    return top_stock, df, elapsed

def send_to_tradetron(symbol, auth_token):
    if not auth_token:
        st.error("⚠️ Tradetron Auth Token is missing in the sidebar!")
        return None
        
    url = f"https://api.tradetron.tech/api?auth-token={auth_token}&key=api_buy&value=1&symbol={symbol}"
    try:
        response = requests.post(url, timeout=5)
        return response.status_code
    except Exception as e:
        st.error(f"Webhook Failed: {e}")
        return None

# --- UI CONTROLS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("⚡ Manual Scanner")
    if st.button("🚀 Run Scanner Instantly", use_container_width=True):
        with st.spinner("Scanning NIFTY 50 Universe..."):
            top_stock, df, elapsed = run_scanner()
            
            if top_stock is not None:
                st.success(
                    f"🎯 **#1 TOP GAINER:** {top_stock['symbol']} | "
                    f"LTP: ₹{top_stock['ltp']} | Prev Close: ₹{top_stock['prev_close']} | "
                    f"Gain: +{top_stock['p_change']}% (Processed {len(df)} stocks in {elapsed}s)"
                )
                
                with st.expander("📊 View Live Top 5 Gainers Table", expanded=True):
                    st.dataframe(df.head(8), use_container_width=True)
                
                # Send Webhook
                status = send_to_tradetron(top_stock['symbol'], tradetron_auth_token)
                if status == 200:
                    st.success("✅ Signal Sent to Tradetron! (Response: 200)")
                else:
                    st.warning(f"Webhook returned status: {status}")

with col2:
    st.subheader("⏰ Auto-Pilot Mode (09:15:35 AM)")
    arm_auto = st.button("🛡️ Arm Auto-Pilot Schedule", use_container_width=True)
    
    if arm_auto:
        status_box = st.empty()
        status_box.info("⏳ Auto-Pilot is ARMED! Monitoring IST time for 09:15:35 AM...")
        
        while True:
            now_ist = datetime.datetime.now(IST)
            current_time_str = now_ist.strftime("%H:%M:%S")
            
            # Check if 09:15:35 reached
            if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
                status_box.success(f"🚀 Trigger Time reached ({current_time_str})! Running Scanner...")
                top_stock, df, elapsed = run_scanner()
                
                if top_stock is not None:
                    st.success(
                        f"🎯 **#1 TOP GAINER:** {top_stock['symbol']} | "
                        f"Gain: +{top_stock['p_change']}% (Scanned in {elapsed}s)"
                    )
                    status = send_to_tradetron(top_stock['symbol'], tradetron_auth_token)
                    if status == 200:
                        st.success("✅ Signal Sent to Tradetron! (Response: 200)")
                break
            
            status_box.markdown(f"**Current IST:** `{current_time_str}` | Target: `09:15:35`")
            time.sleep(1)
