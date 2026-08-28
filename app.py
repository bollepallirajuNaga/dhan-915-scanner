import datetime
import os
import time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ==========================================
# 1. కాన్ఫిగరేషన్ & పెరామీటర్స్
# ==========================================
st.set_page_config(
    page_title="F&O Momentum Scalper", layout="wide", page_icon="⚡"
)

VIRTUAL_CAPITAL = 125000.0
TARGET_PERCENT = 1.0
SL_PERCENT = 0.5
SCAN_START_TIME = datetime.time(9, 15, 30)
ENTRY_END_TIME = datetime.time(9, 25, 0)
HARD_EXIT_TIME = datetime.time(9, 35, 0)
LOG_FILE = "trade_history.csv"

# 185 NSE F&O స్టాక్స్ లిస్ట్
FO_STOCKS = [
    "AARTIIND.NS",
    "ABB.NS",
    "ABBOTINDIA.NS",
    "ABCAPITAL.NS",
    "ABFRL.NS",
    "ACC.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "ALKEM.NS",
    "AMBUJACEM.NS",
    "APOLLOHOSP.NS",
    "APOLLOTYRE.NS",
    "ASHOKLEY.NS",
    "ASIANPAINT.NS",
    "ASTRAL.NS",
    "ATUL.NS",
    "AUBANK.NS",
    "AUROPHARMA.NS",
    "AXISBANK.NS",
    "BAJAJ-AUTO.NS",
    "BAJAJFINSV.NS",
    "BAJFINANCE.NS",
    "BALKRISIND.NS",
    "BALRAMCHIN.NS",
    "BANDHANBNK.NS",
    "BANKBARODA.NS",
    "BATAINDIA.NS",
    "BEL.NS",
    "BERGEPAINT.NS",
    "BHARATFORG.NS",
    "BHARTIARTL.NS",
    "BHEL.NS",
    "BIOCON.NS",
    "BOSCHLTD.NS",
    "BPCL.NS",
    "BRITANNIA.NS",
    "BSOFT.NS",
    "CANBK.NS",
    "CANFINHOME.NS",
    "CHAMBLFERT.NS",
    "CHOLAFIN.NS",
    "CIPLA.NS",
    "COALINDIA.NS",
    "COFORGE.NS",
    "COLPAL.NS",
    "CONCOR.NS",
    "COROMANDEL.NS",
    "CROMPTON.NS",
    "CUB.NS",
    "CUMMINSIND.NS",
    "DABUR.NS",
    "DALBHARAT.NS",
    "DEEPAKNTR.NS",
    "DELHIVERY.NS",
    "DIVISLAB.NS",
    "DIXON.NS",
    "DLF.NS",
    "DRREDDY.NS",
    "EICHERMOT.NS",
    "ESCORTS.NS",
    "EXIDEIND.NS",
    "FEDERALBNK.NS",
    "GAIL.NS",
    "GLENMARK.NS",
    "GMRINFRA.NS",
    "GNFC.NS",
    "GODREJCP.NS",
    "GODREJPROP.NS",
    "GRANULES.NS",
    "GRASIM.NS",
    "GUJGASLTD.NS",
    "HAL.NS",
    "HAVELLS.NS",
    "HCLTECH.NS",
    "HDFCAMC.NS",
    "HDFCBANK.NS",
    "HDFCLIFE.NS",
    "HEROMOTOCO.NS",
    "HINDALCO.NS",
    "HINDCOPPER.NS",
    "HINDPETRO.NS",
    "HINDUNILVR.NS",
    "ICICIBANK.NS",
    "ICICIGI.NS",
    "ICICIPRULI.NS",
    "IDEA.NS",
    "IDFCFIRSTB.NS",
    "IEX.NS",
    "IGL.NS",
    "INDHOTEL.NS",
    "INDIACEM.NS",
    "INDIAMART.NS",
    "INDIGO.NS",
    "INDUSINDBK.NS",
    "INDUSTOWER.NS",
    "INFY.NS",
    "IOC.NS",
    "IPCALAB.NS",
    "IRCTC.NS",
    "ITC.NS",
    "JINDALSTEL.NS",
    "JKCEMENT.NS",
    "JSWSTEEL.NS",
    "JUBLFOOD.NS",
    "KOTAKBANK.NS",
    "LALPATHLAB.NS",
    "LAURUSLABS.NS",
    "LICHSGFIN.NS",
    "LTIM.NS",
    "LT.NS",
    "LTTS.NS",
    "LUPIN.NS",
    "M&MFIN.NS",
    "M&M.NS",
    "MANAPPURAM.NS",
    "MARICO.NS",
    "MARUTI.NS",
    "MCX.NS",
    "METROPOLIS.NS",
    "MFSL.NS",
    "MGL.NS",
    "MOTHERSON.NS",
    "MPHASIS.NS",
    "MRF.NS",
    "MUTHOOTFIN.NS",
    "NATIONALUM.NS",
    "NAUKRI.NS",
    "NAVINFLUOR.NS",
    "NESTLEIND.NS",
    "NMDC.NS",
    "NTPC.NS",
    "OBEROIRLTY.NS",
    "OFSS.NS",
    "ONGC.NS",
    "PAGEIND.NS",
    "PEL.NS",
    "PERSISTENT.NS",
    "PETRONET.NS",
    "PFC.NS",
    "PIDILITIND.NS",
    "PIIND.NS",
    "PNB.NS",
    "POLYCAB.NS",
    "POWERGRID.NS",
    "PVRINOX.NS",
    "RAMCOCEM.NS",
    "RBLBANK.NS",
    "RECLTD.NS",
    "RELIANCE.NS",
    "SAIL.NS",
    "SBICARD.NS",
    "SBILIFE.NS",
    "SBIN.NS",
    "SHREECEM.NS",
    "SIEMENS.NS",
    "SRF.NS",
    "SUNPHARMA.NS",
    "SUNTV.NS",
    "SYNGENE.NS",
    "TATACHEM.NS",
    "TATACOMM.NS",
    "TATACONSUM.NS",
    "TATAMOTORS.NS",
    "TATAPOWER.NS",
    "TATASTEEL.NS",
    "TCS.NS",
    "TECHM.NS",
    "TITAN.NS",
    "TORNTPHARM.NS",
    "TORNTPOWER.NS",
    "TRENT.NS",
    "TVSMOTOR.NS",
    "UBL.NS",
    "ULTRACEMCO.NS",
    "UPL.NS",
    "VEDL.NS",
    "VOLTAS.NS",
    "WIPRO.NS",
    "ZEEL.NS",
    "ZYDUSLIFE.NS",
]


# ==========================================
# 2. టెక్నికల్ ఇండికేటర్స్ & సేవింగ్ ఫంక్షన్
# ==========================================
def calculate_indicators(df):
    if len(df) == 0:
        return df
    df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_vol = df["Volume"].cumsum()
    cum_vp = (typical_price * df["Volume"]).cumsum()
    df["VWAP"] = np.where(cum_vol > 0, cum_vp / cum_vol, df["Close"])
    return df


def save_trade_record(record):
    """Saves completed trade details into CSV file"""
    df_new = pd.DataFrame([record])
    if not os.path.exists(LOG_FILE):
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode="a", header=False, index=False)


# ==========================================
# 3. స్కానర్ ఇంజిన్
# ==========================================
def scan_top_gainer(universe, dry_run=False):
    if dry_run:
        return {
            "symbol": "MANAPPURAM.NS",
            "name": "MANAPPURAM",
            "open": 180.0,
            "ltp": 184.5,
            "change_pct": 2.50,
        }

    try:
        tickers_str = " ".join(universe)
        data = yf.download(
            tickers_str,
            period="1d",
            interval="1m",
            progress=False,
            timeout=10,
            threads=True,
        )
        gainers = []
        for sym in universe:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    sub = data.xs(sym, level=1, axis=1).dropna()
                else:
                    sub = data.dropna()

                if len(sub) >= 1:
                    open_p = float(sub["Open"].iloc[0])
                    ltp = float(sub["Close"].iloc[-1])
                    if open_p > 50:
                        pct = ((ltp - open_p) / open_p) * 100.0
                        if 0 < pct <= 4.0:
                            gainers.append(
                                {
                                    "symbol": sym,
                                    "name": sym.replace(".NS", ""),
                                    "open": open_p,
                                    "ltp": ltp,
                                    "change_pct": pct,
                                }
                            )
            except Exception:
                continue

        if gainers:
            gainers.sort(key=lambda x: x["change_pct"], reverse=True)
            return gainers[0]
    except Exception as e:
        st.warning(f"Scanner warning: {e}")
    return None


# ==========================================
# 4. STREAMLIT DASHBOARD
# ==========================================
st.title("⚡ F&O Intraday Scalper (09:15 - 09:35)")
st.caption("Pure Python Standalone Paper Trading Engine | Auto-Excel Logging")

# Controls
st.sidebar.header("🕹️ కంట్రోల్ ప్యానెల్")
dry_run = st.sidebar.checkbox(
    "🧪 Dry Run / Simulation Mode (వీకెండ్ టెస్టింగ్)", value=True
)
start_btn = st.sidebar.button("🚀 Start Engine")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital", f"₹{VIRTUAL_CAPITAL:,.2f}")
col2.metric("Window", "09:15 - 09:35 AM")
col3.metric("Target / SL", f"+{TARGET_PERCENT}% / -{SL_PERCENT}%")
col4.metric("Mode", "SIMULATION" if dry_run else "LIVE PAPER")

status_box = st.empty()
data_table_box = st.empty()
log_box = st.empty()


# ==========================================
# 5. EXECUTION & LOGGING LOOP
# ==========================================
def run_strategy():
    logs = []

    def log(msg):
        logs.append(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
        )
        log_box.text_area("📜 సిస్టమ్ లాగ్స్", "\n".join(logs), height=220)

    log(
        "ఇంజిన్ ప్రారంభమైంది..."
        if not dry_run
        else "డ్రై-రన్ సిమ్యులేషన్ రన్ అవుతోంది."
    )

    selected_stock = None
    state = "SCANNING"
    position = None

    mock_ltp = 184.5
    mock_high_1m = 185.0

    while True:
        now = datetime.datetime.now().time()
        today_date = datetime.date.today().strftime("%Y-%m-%d")

        # స్టేజ్ 1: స్కానింగ్
        if state == "SCANNING":
            status_box.info("🔍 185 F&O స్టాక్స్‌ను స్కాన్ చేస్తున్నాం...")
            selected_stock = scan_top_gainer(FO_STOCKS, dry_run=dry_run)

            if selected_stock:
                sym_name = selected_stock["name"]
                gain = selected_stock["change_pct"]
                log(f"🎯 టాప్ గెయినర్ ఎంపికైంది: {sym_name} (+{gain:.2f}%)")
                state = "MONITORING"
            else:
                time.sleep(3)
                continue

        # స్టేజ్ 2: కండిషన్ మానిటరింగ్
        elif state == "MONITORING":
            if not dry_run and now > ENTRY_END_TIME:
                status_box.warning(
                    "⏰ 09:25 AM కటాఫ్ దాటింది. ఎలాంటి బ్రేకౌట్ రాలేదు (No Trade Day)."
                )
                log("09:25 AM Cut-off reached. Strategy Stopped.")
                break

            sym = selected_stock["symbol"]
            status_box.info(
                f"👀 మానిటరింగ్ {selected_stock['name']}: 1-Min High, 9 EMA & VWAP చెక్ చేస్తున్నాం..."
            )

            if not dry_run:
                try:
                    df = yf.download(
                        sym, period="1d", interval="1m", progress=False
                    )
                    df = calculate_indicators(df)
                    if len(df) < 2:
                        time.sleep(3)
                        continue
                    first_min_high = df["High"].iloc[0]
                    cur_ltp = df["Close"].iloc[-1]
                    cur_ema = df["EMA_9"].iloc[-1]
                    cur_vwap = df["VWAP"].iloc[-1]
                except Exception as e:
                    log(f"డేటా ఎర్రర్: {e}, రీ-కనెక్ట్ చేస్తున్నాం...")
                    time.sleep(2)
                    continue
            else:
                mock_ltp += 0.30
                cur_ltp = mock_ltp
                first_min_high = mock_high_1m
                cur_ema = 183.0
                cur_vwap = 182.5

            c1 = cur_ltp > first_min_high
            c2 = cur_ltp > cur_ema
            c3 = cur_ltp > cur_vwap

            data_table_box.table(
                pd.DataFrame(
                    [
                        {
                            "Stock": selected_stock["name"],
                            "LTP": f"₹{cur_ltp:.2f}",
                            "1-Min High": f"₹{first_min_high:.2f}",
                            "9 EMA": f"₹{cur_ema:.2f}",
                            "VWAP": f"₹{cur_vwap:.2f}",
                            "1-Min High Break": "✅ YES" if c1 else "❌ NO",
                            "Above EMA": "✅ YES" if c2 else "❌ NO",
                            "Above VWAP": "✅ YES" if c3 else "❌ NO",
                        }
                    ]
                )
            )

            if c1 and c2 and c3:
                qty = int(VIRTUAL_CAPITAL / cur_ltp)
                entry_price = cur_ltp
                target_p = entry_price * (1 + TARGET_PERCENT / 100.0)
                sl_p = entry_price * (1 - SL_PERCENT / 100.0)

                position = {
                    "date": today_date,
                    "stock": selected_stock["name"],
                    "symbol": sym,
                    "qty": qty,
                    "entry_time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "entry_price": entry_price,
                    "target": target_p,
                    "sl": sl_p,
                }
                log(
                    f"🟢 BUY ORDER: {position['stock']} | Qty: {qty} @ ₹{entry_price:.2f}"
                )
                state = "IN_POSITION"

            time.sleep(3)

        # స్టేజ్ 3: పొజిషన్ ట్రాకింగ్ & ఎగ్జిట్ (ఎక్సెల్ సేవింగ్)
        elif state == "IN_POSITION":
            if not dry_run:
                try:
                    df = yf.download(
                        position["symbol"],
                        period="1d",
                        interval="1m",
                        progress=False,
                    )
                    cur_ltp = df["Close"].iloc[-1]
                except Exception:
                    time.sleep(2)
                    continue
            else:
                cur_ltp += 0.20

            pnl = (cur_ltp - position["entry_price"]) * position["qty"]
            pnl_pct = (
                (cur_ltp - position["entry_price"]) / position["entry_price"]
            ) * 100.0

            status_box.success(
                f"🟢 IN TRADE: {position['stock']} | Entry: ₹{position['entry_price']:.2f} | LTP: ₹{cur_ltp:.2f} | P&L: ₹{pnl:,.2f} ({pnl_pct:+.2f}%)"
            )

            exit_reason = None

            if cur_ltp >= position["target"]:
                exit_reason = "TARGET_HIT"
                log(
                    f"🎉 TARGET HIT! Exit @ ₹{cur_ltp:.2f} | Profit: +₹{pnl:,.2f}"
                )
                status_box.balloons()
            elif cur_ltp <= position["sl"]:
                exit_reason = "SL_HIT"
                log(f"🛑 STOP LOSS HIT! Exit @ ₹{cur_ltp:.2f} | Loss: ₹{pnl:,.2f}")
            elif not dry_run and now >= HARD_EXIT_TIME:
                exit_reason = "TIME_EXIT_0935"
                log(
                    f"⏰ 09:35 AM HARD CUT-OFF! Exit @ ₹{cur_ltp:.2f} | P&L: ₹{pnl:,.2f}"
                )

            # ట్రేడ్ ముగిసిన వెంటనే ఎక్సెల్ లోకి సేవ్ చేయడం
            if exit_reason:
                trade_record = {
                    "Date": position["date"],
                    "Stock": position["stock"],
                    "Qty": position["qty"],
                    "Entry Time": position["entry_time"],
                    "Entry Price (₹)": round(position["entry_price"], 2),
                    "Exit Time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "Exit Price (₹)": round(cur_ltp, 2),
                    "Exit Reason": exit_reason,
                    "Net P&L (₹)": round(pnl, 2),
                    "P&L (%)": round(pnl_pct, 2),
                }
                save_trade_record(trade_record)
                log("📁 Trade details successfully saved to CSV file!")
                break

            time.sleep(3)


if start_btn:
    run_strategy()

# ==========================================
# 6. గత ట్రేడ్ల రికార్డ్ & డౌన్‌లోడ్ (TRADE HISTORY)
# ==========================================
st.divider()
st.subheader("📊 ట్రేడ్ హిస్టరీ బుక్ (Daily Trade Log)")

if os.path.exists(LOG_FILE):
    history_df = pd.read_csv(LOG_FILE)
    st.dataframe(history_df, use_container_width=True)

    csv_data = history_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Complete Trade Book (CSV)",
        data=csv_data,
        file_name="FO_Scalping_Trades.csv",
        mime="text/csv",
    )
else:
    st.info(
        "ఇంకా ఎలాంటి ట్రేడ్లు రికార్డ్ కాలేదు. మొదటి ట్రేడ్ పూర్తయిన వెంటనే ఇక్కడ కనిపిస్తుంది."
    )
