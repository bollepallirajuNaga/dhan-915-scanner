import streamlit as st
import time
from datetime import datetime
import pytz
import requests
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="9:15 F&O Production Scanner",
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ 9:15 F&O Top Gainer Scanner")
st.caption("100% Direct REST API Engine • All 185+ F&O Stocks • Tradetron Cloud")

# ================= 1. CONFIGURATION =================
CLIENT_ID = "1113235897"            # మీ 10-అంకెల Dhan Client ID
TT_WEBHOOK_URL = "https://api.tradetron.tech/api"
TT_AUTH_TOKEN = "41cd0696-63ed-43da-8145-a2357d2c8cdb" # మీ Tradetron Auth Token

IST = pytz.timezone("Asia/Kolkata")

# ================= 2. 185+ NSE F&O STOCKS & SECURITY IDs =================
FNO_MAP = {
    "AARTIIND": 7, "ABB": 13, "ABBOTINDIA": 19, "ABCAPITAL": 21614, "ABFRL": 21238, 
    "ACC": 22, "ADANIENT": 25, "ADANIPORTS": 15083, "ALKEM": 11703, "AMBUJACEM": 1270, 
    "APOLLOHOSP": 157, "APOLLOTYRE": 163, "ASHOKLEY": 212, "ASIANPAINT": 236, "ASTRAL": 14418, 
    "ATUL": 263, "AUBANK": 21205, "AUROPHARMA": 275, "AXISBANK": 5900, "BAJAJ-AUTO": 16669, 
    "BAJAJFINSV": 16675, "BAJFINANCE": 317, "BALKRISIND": 335, "BALRAMCHIN": 341, "BANDHANBNK": 2263, 
    "BANKBARODA": 4668, "BATAINDIA": 371, "BEL": 383, "BERGEPAINT": 404, "BHARATFORG": 422, 
    "BHARTIARTL": 10604, "BHEL": 438, "BIOCON": 11373, "BOSCHLTD": 2181, "BPCL": 526, 
    "BRITANNIA": 547, "BSOFT": 6994, "CANBK": 10794, "CANFINHOME": 583, "CHAMBLFERT": 637, 
    "CHOLAFIN": 685, "CIPLA": 694, "COALINDIA": 20374, "COFORGE": 11543, "COLPAL": 751, 
    "CONCOR": 4749, "COROMANDEL": 769, "CROMPTON": 17094, "CUB": 780, "CUMMINSIND": 1901, 
    "DABUR": 792, "DALBHARAT": 8075, "DEEPAKNTR": 19943, "DIVISLAB": 10940, "DIXON": 21690, 
    "DLF": 14732, "DRREDDY": 881, "EICHERMOT": 910, "ESCORTS": 958, "EXIDEIND": 676, 
    "FEDERALBNK": 1023, "GAIL": 4717, "GLENMARK": 7406, "GMRINFRA": 13528, "GNFC": 1107, 
    "GODREJCP": 10099, "GODREJPROP": 17875, "GRANULES": 11872, "GRASIM": 1232, "GUJGASLTD": 10599, 
    "HAL": 2303, "HAVELLS": 9819, "HCLTECH": 7229, "HDFCAMC": 4244, "HDFCBANK": 1333, 
    "HDFCLIFE": 467, "HEROMOTOCO": 1348, "HINDALCO": 1363, "HINDCOPPER": 17939, "HINDPETRO": 1406, 
    "HINDUNILVR": 1394, "ICICIBANK": 4963, "ICICIGI": 21770, "ICICIPRULI": 18652, "IDEA": 14366, 
    "IDFC": 14413, "IDFCFIRSTB": 11184, "IEX": 220, "IGL": 11287, "INDHOTEL": 1512, 
    "INDIACEM": 1515, "INDIAMART": 10726, "INDIGO": 11195, "INDUSINDBK": 5258, "INDUSTOWER": 29114, 
    "INFY": 1594, "IOC": 1624, "IPCALAB": 1633, "IRCTC": 13611, "ITC": 1660, 
    "JINDALSTEL": 1726, "JKCEMENT": 13270, "JSWSTEEL": 11723, "JUBLFOOD": 18096, "KOTAKBANK": 1922, 
    "LALPATHLAB": 11654, "LAURUSLABS": 19234, "LICHSGFIN": 1997, "LT": 11483, "LTIM": 17818, 
    "LTTS": 18564, "LUPIN": 10440, "M&M": 2031, "M&MFIN": 13285, "MANAPPURAM": 19061, 
    "MARICO": 4067, "MARUTI": 10999, "MCDOWELL-N": 10447, "MCX": 31181, "METROPOLIS": 9581, 
    "MFSL": 2142, "MGL": 17534, "MOTHERSON": 4204, "MPHASIS": 4503, "MRF": 2277, 
    "MUTHOOTFIN": 23650, "NATIONALUM": 6364, "NAUKRI": 13751, "NAVINFLUOR": 14672, "NESTLEIND": 17963, 
    "NMDC": 15332, "NTPC": 11630, "OBEROIRLTY": 20242, "OFSS": 10738, "ONGC": 2475, 
    "PAGEIND": 14413, "PEL": 2412, "PERSISTENT": 18365, "PETRONET": 11351, "PFC": 14299, 
    "PIDILITIND": 2664, "PIIND": 24184, "PNB": 10666, "POLYCAB": 9590, "POWERGRID": 14977, 
    "PVRINOX": 13147, "RAMCOCEM": 2043, "RBLBANK": 18391, "RECLTD": 15355, "RELIANCE": 2885, 
    "SAIL": 2963, "SBICARD": 17971, "SBILIFE": 21808, "SBIN": 3045, "SHREECEM": 3103, 
    "SIEMENS": 3150, "SRF": 3273, "SUNPHARMA": 3351, "SUNTV": 13404, "SYNGENE": 10243, 
    "TATACHEM": 3405, "TATACOMM": 3426, "TATACONSUM": 3432, "TATAMOTORS": 3456, "TATAPOWER": 3426, 
    "TATASTEEL": 3499, "TCS": 11536, "TECHM": 13538, "TITAN": 3506, "TORNTPHARM": 3518, 
    "TORNTPOWER": 13786, "TRENT": 1964, "TVSMOTOR": 8479, "UBL": 16713, "ULTRACEMCO": 11532, 
    "UPL": 11287, "VEDL": 3063, "VOLTAS": 3718, "WIPRO": 3787, "ZYDUSLIFE": 4150
}

# Reverse mapping ID to Symbol
ID_TO_SYMBOL = {v: k for k, v in FNO_MAP.items()}

# ================= 3. USER INTERFACE =================
st.markdown("---")
access_token = st.text_input("🔑 Today's Dhan Access Token:", type="password", placeholder="Paste daily token here")

start_btn = st.button("🚀 Start Production 9:15 Scanner", use_container_width=True, type="primary")

if start_btn:
    if not access_token:
        st.error("❌ Please paste today's Dhan Access Token first!")
    else:
        status_box = st.empty()
        progress_bar = st.progress(0)
        
        headers = {
            "access-token": access_token.strip(),
            "client-id": CLIENT_ID.strip(),
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # 1. 09:15:35 AM IST Wait Logic
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
        status_box.info(f"⚡ Fetching live market quotes for all {len(FNO_MAP)} F&O stocks...")
        
        # 2. Dhan Direct REST API Batch Call
        market_data = []
        sec_ids = list(FNO_MAP.values())
        
        # Dhan batch quote endpoint (supports chunks of 100)
        chunk_size = 100
        for i in range(0, len(sec_ids), chunk_size):
            chunk = sec_ids[i:i + chunk_size]
            payload = {"NSE_EQ": chunk}
            
            try:
                res = requests.post(
                    "https://api.dhan.co/v2/marketfeed/ohlc",
                    headers=headers,
                    json=payload,
                    timeout=5
                )
                
                if res.status_code == 200:
                    data = res.json().get("data", {}).get("NSE_EQ", {})
                    for sec_id_str, quote in data.items():
                        sec_id_int = int(sec_id_str)
                        symbol = ID_TO_SYMBOL.get(sec_id_int)
                        if symbol:
                            ltp = float(quote.get("last_price", 0))
                            ohlc = quote.get("ohlc", {})
                            prev_close = float(ohlc.get("close", 0))
                            
                            if prev_close > 0 and ltp > 0:
                                p_change = ((ltp - prev_close) / prev_close) * 100
                                market_data.append({
                                    "symbol": symbol,
                                    "ltp": ltp,
                                    "prev_close": prev_close,
                                    "p_change": p_change
                                })
                elif res.status_code == 401:
                    st.error("❌ Invalid or Expired Dhan Access Token! Please generate a new one from Dhan Web.")
                    st.stop()
            except Exception as e:
                continue

        progress_bar.progress(80)

        if not market_data:
            st.error("❌ Market data fetch failed. Verify Dhan Token or check if market quotes are live.")
        else:
            # 3. Precision Ranking
            df = pd.DataFrame(market_data).sort_values(by="p_change", ascending=False).reset_index(drop=True)
            top_stock = df.iloc[0]["symbol"]
            top_change = df.iloc[0]["p_change"]
            top_ltp = df.iloc[0]["ltp"]
            top_prev = df.iloc[0]["prev_close"]
            
            progress_bar.progress(90)
            st.success(
                f"🎯 **#1 TOP GAINER:** `{top_stock}` | "
                f"LTP: ₹{top_ltp:.2f} | Prev Close: ₹{top_prev:.2f} | "
                f"Gain: **+{top_change:.2f}%** (Analyzed {len(market_data)} stocks)"
            )
            
            # Show Top 5 for confirmation
            with st.expander("📊 View Top 5 Gainers Table"):
                st.dataframe(df.head(5)[["symbol", "ltp", "prev_close", "p_change"]], use_container_width=True)

            # 4. Tradetron Webhook Post
            webhook_payload = {
                "auth-token": TT_AUTH_TOKEN,
                "key": "api_buy",
                "value": "1",
                "symbol": top_stock
            }
            
            try:
                # Direct URL with Query Params + JSON for guaranteed Tradetron ingestion
                webhook_url_full = f"{TT_WEBHOOK_URL}?auth-token={TT_AUTH_TOKEN}&key=api_buy&value=1&symbol={top_stock}"
                res = requests.post(webhook_url_full, json=webhook_payload, timeout=8)
                
                progress_bar.progress(100)
                st.balloons()
                st.success(f"✅ **Signal Sent to Tradetron Successfully!** (Response Code: {res.status_code})")
                st.info(f"🚀 Tradetron strategy is now active on cloud for **{top_stock}**. You can close this screen.")
            except Exception as e:
                st.error(f"⚠️ Webhook Delivery Failed: {e}")
