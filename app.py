import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd
from dhanhq import dhanhq

# Page configuration for mobile view
st.set_page_config(page_title="9:15 Algo Scanner", page_icon="⚡", layout="centered")

st.title("⚡ 9:15 F&O Top Gainer Scanner")
st.caption("Auto Scanner & Tradetron Webhook Trigger")

# ================= CONFIGURATION =================
CLIENT_ID = "YOUR_DHAN_CLIENT_ID"            # మీ ధన్ క్లయింట్ ఐడీ
TT_WEBHOOK_URL = "YOUR_TRADETRON_WEBHOOK_URL" # ట్రేడ్‌ట్రాన్ వెబ్‌హుక్ URL
TT_AUTH_TOKEN = "YOUR_TT_AUTH_TOKEN"          # ట్రేడ్‌ట్రాన్ ఆథ్ టోకెన్

FO_STOCKS = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "KOTAKBANK", "LT", "SBIN",
    "AXISBANK", "BHARTIARTL", "BAJFINANCE", "TATAMOTORS", "MARUTI", "SUNPHARMA",
    "TATASTEEL", "HINDUNILVR", "ITC", "JSWSTEEL", "POWERGRID", "NTPC", "M&M",
    "ADANIENT", "ADANIPORTS", "COALINDIA", "VEDL", "BPCL", "HEROMOTOCO", "CIPLA"
]

IST = pytz.timezone("Asia/Kolkata")

# ================= USER INPUT =================
st.markdown("---")
access_token = st.text_input("🔑 Today's Dhan Access Token:", type="password", placeholder="Paste daily token here")

start_btn = st.button("🚀 Start 9:15 Precision Scanner", use_container_width=True, type="primary")

if start_btn:
    if not access_token:
        st.error("❌ Please paste Dhan Access Token first!")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        dhan = dhanhq(CLIENT_ID, access_token)
        
        # 1. 09:15:35 వరకు లైవ్ కౌంట్‌డౌన్
        status_box.info("⏳ Waiting for 09:15:35 AM IST opening window...")
        
        while True:
            now_ist = datetime.now(IST)
            if now_ist.hour == 9 and now_ist.minute == 15 and now_ist.second >= 35:
                break
            elif now_ist.hour >= 9 and now_ist.minute > 15:
                # 09:16 దాటిన తర్వాత టెస్ట్ రన్ చేస్తే వెంటనే స్కాన్ అవుతుంది
                break
                
            current_time_str = now_ist.strftime("%H:%M:%S")
            status_box.warning(f"🕒 Current Time: **{current_time_str}** | Waiting for **09:15:35**...")
            time.sleep(0.5)
            
        progress_bar.progress(50)
        status_box.info("🔍 Scanning F&O market data from Dhan API...")
        
        # 2. Dhan API ద్వారా డేటా ఫెచింగ్
        market_data = []
        for symbol in FO_STOCKS:
            try:
                quote = dhan.get_market_quote(security_id=symbol, exchange_segment="NSE_EQ")
                if quote and quote.get("status") == "success":
                    data = quote["data"]
                    ltp = float(data["last_price"])
                    prev_close = float(data["previous_close"])
                    p_change = ((ltp - prev_close) / prev_close) * 100
                    
                    if ltp > 50 and p_change <= 4.0:
                        market_data.append({"symbol": symbol, "ltp": ltp, "p_change": p_change})
            except Exception:
                continue
                
        if not market_data:
            st.error("❌ No matching stock found satisfying filters.")
        else:
            # 3. #1 టాప్ గెయినర్ ఎంపిక
            df = pd.DataFrame(market_data).sort_values(by="p_change", ascending=False).reset_index(drop=True)
            top_stock = df.iloc[0]["symbol"]
            top_change = df.iloc[0]["p_change"]
            top_ltp = df.iloc[0]["ltp"]
            
            progress_bar.progress(80)
            st.success(f"🎯 **#1 TOP GAINER:** `{top_stock}` | LTP: ₹{top_ltp} | Change: +{top_change:.2f}%")
            
            # 4. Tradetron Webhook కు పోస్ట్ చేయడం
            payload = {
                "auth-token": TT_AUTH_TOKEN,
                "key": "entry",
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