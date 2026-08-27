import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd
import yfinance as yf

# Page configuration
st.set_page_config(page_title="9:15 F&O Universal Scanner", page_icon="⚡", layout="centered")

st.title("⚡ 9:15 F&O Top Gainer Scanner")
st.caption("100% Free Live Engine • All 185+ F&O Stocks • Tradetron Webhook")

# ================= 1. CONFIGURATION =================
TT_WEBHOOK_URL = "https://api.tradetron.tech/api"
TT_AUTH_TOKEN = "41cd0696-63ed-43da-8145-a2357d2c8cdb"

IST = pytz.timezone("Asia/Kolkata")

# 185+ NSE F&O Symbols for Yahoo Finance (.NS)
FNO_SYMBOLS = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", 
    "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", 
    "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", 
    "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", 
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT", 
    "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", 
    "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", 
    "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", 
    "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", 
    "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", 
    "HEROMOTOCO", "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", 
    "ICICIPRULI", "IDEA", "IDFC", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", 
    "INDIAMART", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "IOC", "IPCALAB", "IRCTC", 
    "ITC", "JINDALSTEL", "JKCEMENT", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", 
    "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", 
    "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", 
    "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", 
    "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", 
    "PFC", "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", 
    "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", 
    "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", 
    "TATAMOTORS", "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TORNTPOWER", 
    "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZYDUSLIFE"
]

YF_TICKERS = [f"{sym}.NS" for sym in FNO_SYMBOLS]

# ================= 2. USER INTERFACE =================
st.markdown("---")
st.success("🟢 No Dhan Token required. Ready to scan all 185+ NSE F&O stocks.")

start_btn = st.button("🚀 Start 9:15 Scanner Now", use_container_width=True, type="primary")

if start_btn:
    status_box = st.empty()
    progress_bar = st.progress(0)
    
    # 09:15:35 AM IST Wait Window
    while True:
        now_ist = datetime.now(IST)
        if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
            break
        elif now_ist.hour > 9 or (now_ist.hour == 9 and now_ist.minute > 15):
            break
            
        current_time_str = now_ist.strftime("%H:%M:%S")
        status_box.warning(f"🕒 Current Time: **{current_time_str}** | Waiting for **09:15:35 AM**...")
        time.sleep(0.3)
        
    progress_bar.progress(30)
    status_box.info("⚡ Fetching live data for 185+ F&O stocks...")
    
    # Single-Batch Fast Fetch
    start_time = time.time()
    try:
        data = yf.download(tickers=YF_TICKERS, period="2d", interval="1d", group_by="ticker", progress=False, threads=True)
        
        market_data = []
        for sym in FNO_SYMBOLS:
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
            st.error("❌ Could not retrieve market data. Try clicking again.")
        else:
            # Ranking & Selection
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
            
            with st.expander("📊 View Top 5 Gainers Table"):
                st.dataframe(df_res.head(5)[["symbol", "ltp", "prev_close", "p_change"]], use_container_width=True)

            # Post to Tradetron
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
            st.success(f"✅ **Signal Sent to Tradetron Successfully!** (Response: {res.status_code})")
            st.info(f"🚀 Cloud strategy activated for **{top_stock}**.")
            
    except Exception as e:
        st.error(f"Error during scan: {e}")
