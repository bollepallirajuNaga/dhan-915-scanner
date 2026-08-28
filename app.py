import datetime
import os
import time
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# ==============================================================================
# 1. కాన్ఫిగరేషన్ & పెరామీటర్స్ (CONFIGURATION)
# ==============================================================================
st.set_page_config(
    page_title="F&O Top-3 Basket Scalper", layout="wide", page_icon="⚡"
)

VIRTUAL_CAPITAL = 125000.0  # వర్చువల్ క్యాపిటల్ (₹1,25,000)
TARGET_PERCENT = 1.0  # టార్గెట్ 1.0%
SL_PERCENT = 0.5  # స్టాప్‌లాస్ 0.5%
SCAN_START_TIME = datetime.time(9, 15, 30)  # 09:15:30 AM
ENTRY_END_TIME = datetime.time(9, 25, 0)  # 09:25:00 AM (కటాఫ్ టైమ్)
HARD_EXIT_TIME = datetime.time(9, 35, 0)  # 09:35:00 AM (మాండేటరీ స్క్వేర్-ఆఫ్)
LOG_FILE = "trade_history.csv"  # ఎక్సెల్ డేటా ఫైల్
STOCKS_FILE = "fno_stocks.txt"  # స్టాక్స్ లిస్ట్ టెక్స్ట్ ఫైల్

# ==============================================================================
# 2. fno_stocks.txt నుండి స్టాక్స్ లోడ్ చేసే ఫంక్షన్
# ==============================================================================
DEFAULT_FALLBACK_STOCKS = [
    "ATHERENERG.NS",
    "COFORGE.NS",
    "MANAPPURAM.NS",
    "BHEL.NS",
    "TATAMOTORS.NS",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "INFY.NS",
]


def load_stock_universe(file_path=STOCKS_FILE):
    """fno_stocks.txt ఫైల్ నుండి స్టాక్స్ సింబల్స్ రీడ్ చేస్తుంది"""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            stocks = [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.startswith("#")
            ]
            if len(stocks) > 0:
                return stocks
    return DEFAULT_FALLBACK_STOCKS


FO_STOCKS = load_stock_universe(STOCKS_FILE)


# ==============================================================================
# 3. టెక్నికల్ ఇండికేటర్స్ & ఎక్సెల్ సేవింగ్ ఫంక్షన్స్
# ==============================================================================
def calculate_indicators(df):
    """EMA 9 మరియు ఇంట్రాడే VWAP లెక్కిస్తుంది"""
    if len(df) == 0:
        return df

    # 9 EMA
    df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()

    # VWAP = Cumulative(Price * Volume) / Cumulative(Volume)
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_vol = df["Volume"].cumsum()
    cum_vp = (typical_price * df["Volume"]).cumsum()
    df["VWAP"] = np.where(cum_vol > 0, cum_vp / cum_vol, df["Close"])

    return df


def save_trade_record(record):
    """పూర్తయిన ట్రేడ్ వివరాలను CSV ఫైల్‌కు అపెండ్ చేస్తుంది"""
    df_new = pd.DataFrame([record])
    if not os.path.exists(LOG_FILE):
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode="a", header=False, index=False)


# ==============================================================================
# 4. టాప్-3 స్కానర్ ఇంజిన్ (TOP-3 SCANNER ENGINE)
# ==============================================================================
def scan_top_3_gainers(universe, dry_run=False):
    """185+ స్టాక్స్‌ను స్కాన్ చేసి టాప్-3 గెయినర్లను ఫిల్టర్ చేస్తుంది"""
    if dry_run:
        # డ్రై-రన్ సిమ్యులేషన్ బాస్కెట్
        return [
            {
                "symbol": "ATHERENERG.NS",
                "name": "ATHERENERG",
                "open": 1560.0,
                "ltp": 1568.0,
                "change_pct": 3.20,
            },
            {
                "symbol": "COFORGE.NS",
                "name": "COFORGE",
                "open": 1920.0,
                "ltp": 1945.0,
                "change_pct": 2.80,
            },
            {
                "symbol": "MANAPPURAM.NS",
                "name": "MANAPPURAM",
                "open": 180.0,
                "ltp": 184.0,
                "change_pct": 2.20,
            },
        ]

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
                    if open_p > 50:  # పెన్నీ స్టాక్స్ కాకుండా ₹50 పైన ఉన్నవి
                        pct = ((ltp - open_p) / open_p) * 100.0
                        if 0 < pct <= 4.0:  # సేఫ్ మొమెంటమ్ జోన్ (0% నుండి 4%)
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
            return gainers[:3]  # టాప్-3 స్టాక్స్ బాస్కెట్
    except Exception as e:
        st.warning(f"Scanner fetch warning: {e}")
    return []


# ==============================================================================
# 5. STREAMLIT UI & డ్యాష్‌బోర్డ్ (DASHBOARD)
# ==============================================================================
st.title("⚡ F&O Top-3 Basket Scalper (09:15 - 09:35)")
st.caption(
    f"Universe: {len(FO_STOCKS)} Stocks loaded from '{STOCKS_FILE}' | First-Come First-Served Execution"
)

# Sidebar Controls
st.sidebar.header("🕹️ కంట్రోల్ ప్యానెల్")
dry_run = st.sidebar.checkbox(
    "🧪 Dry Run / Simulation Mode (వీకెండ్ టెస్టింగ్)", value=True
)
start_btn = st.sidebar.button("🚀 Start Engine")

# Metric Cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital", f"₹{VIRTUAL_CAPITAL:,.2f}")
col2.metric("Window", "09:15 - 09:35 AM")
col3.metric("Target / SL", f"+{TARGET_PERCENT}% / -{SL_PERCENT}%")
col4.metric("Mode", "SIMULATION" if dry_run else "LIVE PAPER")

status_box = st.empty()
data_table_box = st.empty()
log_box = st.empty()


# ==============================================================================
# 6. మెయిన్ ట్రేడింగ్ లూప్ (MAIN EXECUTION LOOP)
# ==============================================================================
def run_strategy():
    logs = []

    def log(msg):
        logs.append(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
        )
        log_box.text_area("📜 సిస్టమ్ లాగ్స్", "\n".join(logs), height=220)

    log(
        "సిస్టమ్ ఆన్ అయింది. మార్కెట్ సమయం కోసం వేచి చూస్తున్నాం..."
        if not dry_run
        else "డ్రై-రన్ సిమ్యులేషన్ మోడ్ ప్రారంభమైంది."
    )

    basket = []
    state = "SCANNING"
    position = None

    while True:
        now = datetime.datetime.now().time()
        today_date = datetime.date.today().strftime("%Y-%m-%d")

        # ----------------------------------------------------------------------
        # స్టేజ్ 1: టాప్-3 బాస్కెట్ స్కానింగ్ (09:15:30 AM)
        # ----------------------------------------------------------------------
        if state == "SCANNING":
            status_box.info(
                f"🔍 {len(FO_STOCKS)} స్టాక్స్‌ను స్కాన్ చేసి Top-3 గెయినర్ల బాస్కెట్‌ను ఎంపిక చేస్తున్నాం..."
            )
            basket = scan_top_3_gainers(FO_STOCKS, dry_run=dry_run)

            if len(basket) > 0:
                names_str = ", ".join(
                    [f"{s['name']} (+{s['change_pct']:.2f}%)" for s in basket]
                )
                log(f"🎯 టాప్-3 బాస్కెట్ ఎంపికైంది: {names_str}")
                state = "MONITORING"
            else:
                log("స్టాక్స్ ఫెచ్ కాలేదు, 3 సెకన్లలో రీ-ట్రై అవుతుంది...")
                time.sleep(3)
                continue

        # ----------------------------------------------------------------------
        # స్టేజ్ 2: సమాంతర మానిటరింగ్ & ఫస్ట్ బ్రేకౌట్ ట్రిగ్గర్ (09:16 - 09:25 AM)
        # ----------------------------------------------------------------------
        elif state == "MONITORING":
            if not dry_run and now > ENTRY_END_TIME:
                status_box.warning(
                    "⏰ 09:25 AM కటాఫ్ దాటింది. ఏ స్టాక్‌లోనూ బ్రేకౌట్ రాలేదు (No Trade Day)."
                )
                log("09:25 AM Cut-off reached. Strategy Stopped.")
                break

            status_box.info(
                "👀 టాప్-3 స్టాక్స్‌ను సమాంతరంగా గమనిస్తున్నాం... మొదటి బ్రేకౌట్ కోసం వేచి చూస్తున్నాం..."
            )

            table_rows = []
            triggered_stock = None
            triggered_data = None

            if not dry_run:
                basket_tickers = " ".join([s["symbol"] for s in basket])
                try:
                    df_all = yf.download(
                        basket_tickers,
                        period="1d",
                        interval="1m",
                        progress=False,
                        timeout=5,
                    )
                except Exception as e:
                    log(f"డేటా ఎర్రర్: {e}, రీ-కనెక్ట్ చేస్తున్నాం...")
                    time.sleep(2)
                    continue

            for s in basket:
                sym = s["symbol"]
                s_name = s["name"]

                if not dry_run:
                    try:
                        if isinstance(df_all.columns, pd.MultiIndex):
                            sub = df_all.xs(sym, level=1, axis=1).dropna()
                        else:
                            sub = df_all.dropna()

                        if len(sub) < 2:
                            continue
                        sub = calculate_indicators(sub)
                        first_min_high = sub["High"].iloc[0]
                        cur_ltp = sub["Close"].iloc[-1]
                        cur_ema = sub["EMA_9"].iloc[-1]
                        cur_vwap = sub["VWAP"].iloc[-1]
                    except Exception:
                        continue
                else:
                    # డ్రై-రన్ సిమ్యులేషన్: Ather drop, Coforge breaks out
                    if s_name == "ATHERENERG":
                        first_min_high = 1573.9
                        cur_ltp = 1550.0  # పడిపోయింది (నో ట్రేడ్)
                        cur_ema = 1560.0
                        cur_vwap = 1558.0
                    elif s_name == "COFORGE":
                        first_min_high = 1929.9
                        cur_ltp = 1935.0  # బ్రేక్ అయింది! (ట్రిగ్గర్)
                        cur_ema = 1925.0
                        cur_vwap = 1924.0
                    else:
                        first_min_high = 185.0
                        cur_ltp = 184.2
                        cur_ema = 183.0
                        cur_vwap = 182.5

                c1 = cur_ltp > first_min_high
                c2 = cur_ltp > cur_ema
                c3 = cur_ltp > cur_vwap

                table_rows.append(
                    {
                        "Stock": s_name,
                        "LTP": f"₹{cur_ltp:.2f}",
                        "1-Min High": f"₹{first_min_high:.2f}",
                        "9 EMA": f"₹{cur_ema:.2f}",
                        "VWAP": f"₹{cur_vwap:.2f}",
                        "High Break": "✅ YES" if c1 else "❌ NO",
                        "Above EMA": "✅ YES" if c2 else "❌ NO",
                        "Above VWAP": "✅ YES" if c3 else "❌ NO",
                    }
                )

                # మొదటి కండిషన్ మీట్ అయిన స్టాక్ ను లాక్ చేయడం
                if c1 and c2 and c3 and triggered_stock is None:
                    triggered_stock = s
                    triggered_data = {"ltp": cur_ltp}

            if table_rows:
                data_table_box.table(pd.DataFrame(table_rows))

            if triggered_stock:
                qty = int(VIRTUAL_CAPITAL / triggered_data["ltp"])
                entry_price = triggered_data["ltp"]
                target_p = entry_price * (1 + TARGET_PERCENT / 100.0)
                sl_p = entry_price * (1 - SL_PERCENT / 100.0)

                position = {
                    "date": today_date,
                    "stock": triggered_stock["name"],
                    "symbol": triggered_stock["symbol"],
                    "qty": qty,
                    "entry_time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "entry_price": entry_price,
                    "target": target_p,
                    "sl": sl_p,
                }
                log(
                    f"🟢 FIRST BREAKOUT: {position['stock']} | Qty: {qty} @ ₹{entry_price:.2f}"
                )
                log(
                    f"🎯 Target: ₹{target_p:.2f} (+1%) | 🛑 SL: ₹{sl_p:.2f} (-0.5%)"
                )
                log("🔒 మిగిలిన స్టాక్స్ ట్రాకింగ్ ఆపివేయబడింది. 1-Trade Locked!")
                state = "IN_POSITION"

            time.sleep(3)

        # ----------------------------------------------------------------------
        # స్టేజ్ 3: పొజిషన్ ట్రాకింగ్ & ఆటో-ఎగ్జిట్ (09:16 - 09:35 AM)
        # ----------------------------------------------------------------------
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
                cur_ltp = position["entry_price"] * 1.011  # డ్రై-రన్ ప్రాఫిట్

            pnl = (cur_ltp - position["entry_price"]) * position["qty"]
            pnl_pct = (
                (cur_ltp - position["entry_price"]) / position["entry_price"]
            ) * 100.0

            status_box.success(
                f"🟢 ACTIVE TRADE: {position['stock']} | Entry: ₹{position['entry_price']:.2f} | LTP: ₹{cur_ltp:.2f} | P&L: ₹{pnl:,.2f} ({pnl_pct:+.2f}%)"
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
                    f"⏰ 09:35 AM HARD CUT-OFF! Exit @ ₹{cur_ltp:.2f} | Net P&L: ₹{pnl:,.2f}"
                )

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

# ==============================================================================
# 7. ట్రేడ్ హిస్టరీ బుక్ & ఎక్సెల్ డౌన్‌లోడ్
# ==============================================================================
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
    st.info("ఇంకా ఎలాంటి ట్రేడ్లు రికార్డ్ కాలేదు.")
