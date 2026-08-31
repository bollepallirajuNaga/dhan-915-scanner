import datetime
import os
import time
from zoneinfo import ZoneInfo
from dhanhq import dhanhq
import numpy as np
import pandas as pd
import streamlit as st

# ==============================================================================
# 1. పేజ్ సెటప్ & టైమ్ జోన్ కాన్ఫిగరేషన్
# ==============================================================================
st.set_page_config(
    page_title="Dhan F&O Top-3 Scalper Pro", layout="wide", page_icon="⚡"
)

IST = ZoneInfo("Asia/Kolkata")

# స్ట్రాటజీ స్థిర విలువలు
VIRTUAL_CAPITAL = 125000.0  # ₹1,25,000 వర్చువల్ మూలధనం
TARGET_PERCENT = 1.0  # +1.0% టార్గెట్
SL_PERCENT = 0.5  # -0.5% స్టాప్‌లాస్
SLIPPAGE_PCT = 0.05  # 0.05% స్లిప్పేజ్
EST_CHARGES = 40.0  # ₹40 అంచనా బ్రోకరేజ్/ట్యాక్సులు

# స్ట్రాటజీ టైమింగ్స్ (IST)
SCAN_TIME = datetime.time(9, 15, 35)  # 09:15:35 AM స్కానింగ్
ENTRY_CUTOFF_TIME = datetime.time(9, 25, 0)  # 09:25:00 AM ఎంట్రీ కటాఫ్
HARD_EXIT_TIME = datetime.time(9, 35, 0)  # 09:35:00 AM మాండేటరీ ఎగ్జిట్

LOG_FILE = "trade_history.csv"
STOCKS_FILE = "fno_stocks.txt"

# ==============================================================================
# 2. సైడ్‌బార్ - డైలీ టోకెన్ ఎంట్రీ & కంట్రోల్స్
# ==============================================================================
st.sidebar.header("🔑 Dhan API లాగిన్")
DHAN_CLIENT_ID = st.sidebar.text_input("Client ID", value="1113235897")
DHAN_ACCESS_TOKEN = st.sidebar.text_input(
    "Daily Access Token (24-Hr)",
    type="password",
    help="Dhan పోర్టల్ నుండి తాజా టోకెన్ ఇక్కడ పేస్ట్ చేయండి",
)

start_engine_btn = st.sidebar.button("🚀 Start Engine")


# ==============================================================================
# 3. సెక్యూరిటీ మాస్టర్ & స్టాక్స్ లోడింగ్
# ==============================================================================
@st.cache_data(ttl=86400)
def load_security_master():
    """Dhan NSE Scrip Master డేటాను బ్యాక్‌గ్రౌండ్‌లో లోడ్ చేస్తుంది"""
    url = "https://images.dhan.co/api-data/api-scrip-master.csv"
    try:
        df = pd.read_csv(url, low_memory=False)
        nse_eq = df[
            (df["SEM_EXM_EXCH_ID"] == "NSE")
            & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")
        ]
        scrip_dict = {}
        for _, row in nse_eq.iterrows():
            sym = str(row["SEM_TRADING_SYMBOL"]).strip().upper()
            sec_id = str(row["SEM_SMST_SECURITY_ID"]).strip()
            scrip_dict[sym] = sec_id
        return scrip_dict
    except Exception as e:
        st.error(f"Error loading security master: {e}")
        return {}


def load_stock_universe(file_path=STOCKS_FILE):
    """fno_stocks.txt నుండి 230 స్టాక్స్‌ను రీడ్ చేస్తుంది"""
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            stocks = [
                line.strip().replace(".NS", "")
                for line in f.readlines()
                if line.strip() and not line.startswith("#")
            ]
            if stocks:
                return stocks
    return ["ATHERENERG", "COFORGE", "LTIM", "BHEL", "TATAMOTORS", "RELIANCE"]


FO_STOCKS = load_stock_universe()
SCRIP_MAP = load_security_master()


# ==============================================================================
# 4. టెక్నికల్ ఇండికేటర్స్ & డేటా హెల్పర్స్
# ==============================================================================
def calculate_indicators(df):
    """9 EMA మరియు ఇంట్రాడే VWAP లెక్కిస్తుంది"""
    if len(df) == 0:
        return df

    # 9 EMA
    df["EMA_9"] = df["close"].ewm(span=9, adjust=False).mean()

    # Intraday VWAP (09:15 నుండి రీసెట్ అవుతుంది)
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_vp = (typical_price * df["volume"]).cumsum()
    df["VWAP"] = np.where(cum_vol > 0, cum_vp / cum_vol, df["close"])

    return df


def get_live_intraday_data(dhan, security_id):
    """Dhan నుండి లైవ్ 1-మినిట్ డేటా పొందుతుంది"""
    try:
        resp = dhan.intraday_daily_minute_charts(
            security_id=str(security_id),
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
        )
        if resp.get("status") == "success" and "data" in resp:
            data = resp["data"]
            df = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(data["timestamp"]),
                    "open": data["open"],
                    "high": data["high"],
                    "low": data["low"],
                    "close": data["close"],
                    "volume": data["volume"],
                }
            )
            return df.sort_values("timestamp").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()


def save_detailed_trade(record):
    """ట్రేడ్ పూర్తవగానే CSV కి ఆటో-సేవ్ చేస్తుంది"""
    df_new = pd.DataFrame([record])
    if not os.path.exists(LOG_FILE):
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode="a", header=False, index=False)


def scan_top_3_dhan(dhan):
    """09:15:35 AM కి టాప్-3 గెయినర్లను ఫిల్టర్ చేస్తుంది"""
    gainers = []
    for sym in FO_STOCKS:
        sec_id = SCRIP_MAP.get(sym)
        if not sec_id:
            continue
        try:
            quote = dhan.get_quote(
                security_id=sec_id,
                exchange_segment="NSE_EQ",
                instrument_type="EQUITY",
            )
            if quote.get("status") == "success" and "data" in quote:
                q = quote["data"]
                open_p = float(q.get("open", 0.0))
                ltp = float(q.get("last_price", 0.0))
                if open_p > 50.0:
                    pct = ((ltp - open_p) / open_p) * 100.0
                    gainers.append(
                        {
                            "symbol": sym,
                            "security_id": sec_id,
                            "open": open_p,
                            "ltp": ltp,
                            "gain_pct": pct,
                        }
                    )
        except Exception:
            continue

    if gainers:
        gainers.sort(key=lambda x: x["gain_pct"], reverse=True)
        return gainers[:3]
    return []


# ==============================================================================
# 5. UI లేఅవుట్ & స్టేటస్ కార్డ్స్
# ==============================================================================
st.title("⚡ Dhan F&O Top-3 Scalper Pro")
st.caption(
    f"Universe: {len(FO_STOCKS)} Stocks | Auto Scan (09:15:35) ➔ Monitor (09:16-09:25) ➔ Auto Exit (09:35)"
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Capital", f"₹{VIRTUAL_CAPITAL:,.2f}")
col2.metric("Scan Time", "09:15:35 AM")
col3.metric("Target / SL", f"+{TARGET_PERCENT}% / -{SL_PERCENT}%")
col4.metric("Hard Exit", "09:35:00 AM")

status_box = st.empty()
monitor_table_box = st.empty()
log_box = st.empty()


# ==============================================================================
# 6. ఎగ్జిక్యూషన్ ఇంజిన్ (09:05 నుండి 09:35 వరకు లైఫ్‌సైకిల్)
# ==============================================================================
def run_full_pipeline():
    if not DHAN_ACCESS_TOKEN or not DHAN_CLIENT_ID:
        st.error("⚠️ దయచేసి సైడ్‌బార్‌లో మీ Dhan Client ID & Token ఎంటర్ చేయండి!")
        return

    dhan = dhanhq(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
    logs = []

    def log(msg):
        t_str = datetime.datetime.now(IST).strftime("%H:%M:%S")
        logs.append(f"[{t_str}] {msg}")
        log_box.text_area("📜 లైవ్ సిస్టమ్ ఆడిట్ లాగ్స్", "\n".join(logs), height=240)

    log("✅ Dhan API కనెక్ట్ అయింది. సిస్టమ్ స్టాండ్‌బై మోడ్‌లోకి వెళ్లింది.")

    state = "WAITING_FOR_091535"
    basket = []
    position = None

    while True:
        now_dt = datetime.datetime.now(IST)
        now_time = now_dt.time()
        today_date = now_dt.strftime("%Y-%m-%d")

        # ----------------------------------------------------------------------
        # దశ 1: 09:15:35 AM వరకు నిరీక్షణ (Waiting Room)
        # ----------------------------------------------------------------------
        if state == "WAITING_FOR_091535":
            if now_time < SCAN_TIME:
                diff_sec = int(
                    (
                        datetime.datetime.combine(datetime.date.today(), SCAN_TIME)
                        - datetime.datetime.combine(datetime.date.today(), now_time)
                    ).total_seconds()
                )
                status_box.info(
                    f"⏳ మార్కెట్ ఓపెన్ కోసం వేచి చూస్తున్నాం... స్కానింగ్ ప్రారంభానికి ఇంకా **{diff_sec} సెకన్లు** సమయం ఉంది. (ప్రస్తుత సమయం: {now_time.strftime('%H:%M:%S')})"
                )
                time.sleep(1)
                continue

            status_box.info(
                f"🔍 09:15:35 AM అయింది. {len(FO_STOCKS)} స్టాక్స్‌ను స్కాన్ చేస్తున్నాం..."
            )
            basket = scan_top_3_dhan(dhan)

            if len(basket) == 3:
                b_str = ", ".join(
                    [f"{s['symbol']} (+{s['gain_pct']:.2f}%)" for s in basket]
                )
                log(f"🎯 టాప్-3 బాస్కెట్ ఎంపికైంది: {b_str}")
                state = "MONITORING_BREAKOUT"
            else:
                log("డేటా ఫెచ్ విఫలమైంది. 2 సెకన్లలో రీ-ట్రై అవుతుంది...")
                time.sleep(2)
                continue

        # ----------------------------------------------------------------------
        # దశ 2: బ్రేకౌట్ మానిటరింగ్ & ఫస్ట్ ట్రిగ్గర్ (09:16 - 09:25 AM)
        # ----------------------------------------------------------------------
        elif state == "MONITORING_BREAKOUT":
            if now_time > ENTRY_CUTOFF_TIME:
                status_box.warning(
                    "⏰ 09:25:00 AM కటాఫ్ ముగిసింది. ఏ స్టాక్‌లోనూ బ్రేకౌట్ రాలేదు (No Trade Day)."
                )
                log("09:25 AM Cut-off reached. No trades triggered today.")
                break

            status_box.info(
                "👀 టాప్-3 స్టాక్స్‌ను సమాంతరంగా గమనిస్తున్నాం... మొదటి బ్రేకౌట్ రాగానే ఆర్డర్ లాక్ అవుతుంది."
            )

            table_rows = []
            triggered_stock = None
            triggered_entry_price = 0.0

            for s in basket:
                sym = s["symbol"]
                sec_id = s["security_id"]

                df_min = get_live_intraday_data(dhan, sec_id)
                if len(df_min) < 1:
                    continue

                df_min = calculate_indicators(df_min)
                first_candle_high = float(df_min["high"].iloc[0])
                cur_ltp = float(df_min["close"].iloc[-1])
                cur_ema = float(df_min["EMA_9"].iloc[-1])
                cur_vwap = float(df_min["VWAP"].iloc[-1])

                c1 = cur_ltp > first_candle_high
                c2 = cur_ltp > cur_ema
                c3 = cur_ltp > cur_vwap

                table_rows.append(
                    {
                        "Stock": sym,
                        "LTP": f"₹{cur_ltp:.2f}",
                        "1-Min High": f"₹{first_candle_high:.2f}",
                        "9 EMA": f"₹{cur_ema:.2f}",
                        "VWAP": f"₹{cur_vwap:.2f}",
                        "High Break": "✅ YES" if c1 else "❌ NO",
                        "Above EMA": "✅ YES" if c2 else "❌ NO",
                        "Above VWAP": "✅ YES" if c3 else "❌ NO",
                    }
                )

                if c1 and c2 and c3 and triggered_stock is None:
                    entry_with_slip = cur_ltp * (1.0 + SLIPPAGE_PCT / 100.0)
                    triggered_stock = s
                    triggered_entry_price = entry_with_slip
                    first_high_saved = first_candle_high
                    ema_saved = cur_ema
                    vwap_saved = cur_vwap

            if table_rows:
                monitor_table_box.table(pd.DataFrame(table_rows))

            if triggered_stock:
                qty = int(VIRTUAL_CAPITAL / triggered_entry_price)
                target_p = triggered_entry_price * (1 + TARGET_PERCENT / 100.0)
                sl_p = triggered_entry_price * (1 - SL_PERCENT / 100.0)

                position = {
                    "date": today_date,
                    "stock": triggered_stock["symbol"],
                    "security_id": triggered_stock["security_id"],
                    "qty": qty,
                    "entry_time": now_dt.strftime("%H:%M:%S"),
                    "entry_price": triggered_entry_price,
                    "target": target_p,
                    "sl": sl_p,
                    "first_high": first_high_saved,
                    "ema": ema_saved,
                    "vwap": vwap_saved,
                    "basket": ", ".join([x["symbol"] for x in basket]),
                }
                log(
                    f"🟢 FIRST BREAKOUT: {position['stock']} | Qty: {qty} @ ₹{triggered_entry_price:.2f}"
                )
                log(f"🎯 Target: ₹{target_p:.2f} | 🛑 SL: ₹{sl_p:.2f}")
                log("🔒 1-ట్రేడ్ లాక్ అయింది. మిగిలిన స్టాక్స్ ట్రాకింగ్ ఆపివేయబడింది.")
                state = "TRACKING_TRADE"

            time.sleep(1)

        # ----------------------------------------------------------------------
        # దశ 3: లైవ్ P&L ట్రాకింగ్ & 09:35 మాండేటరీ క్లోజింగ్
        # ----------------------------------------------------------------------
        elif state == "TRACKING_TRADE":
            df_pos = get_live_intraday_data(dhan, position["security_id"])
            if len(df_pos) == 0:
                time.sleep(1)
                continue

            cur_ltp = float(df_pos["close"].iloc[-1])
            gross_pnl = (cur_ltp - position["entry_price"]) * position["qty"]
            net_pnl = gross_pnl - EST_CHARGES
            pnl_pct = (
                (cur_ltp - position["entry_price"]) / position["entry_price"]
            ) * 100.0

            status_box.success(
                f"🟢 ACTIVE TRADE: {position['stock']} | Entry: ₹{position['entry_price']:.2f} | LTP: ₹{cur_ltp:.2f} | Net P&L: ₹{net_pnl:,.2f} ({pnl_pct:+.2f}%)"
            )

            exit_reason = None
            exit_price = cur_ltp

            if cur_ltp >= position["target"]:
                exit_reason = "TARGET_HIT"
                exit_price = cur_ltp * (1.0 - SLIPPAGE_PCT / 100.0)
                log(
                    f"🎉 TARGET HIT! Exit @ ₹{exit_price:.2f} | Net Profit: +₹{net_pnl:,.2f}"
                )
                status_box.balloons()
            elif cur_ltp <= position["sl"]:
                exit_reason = "SL_HIT"
                exit_price = cur_ltp * (1.0 - SLIPPAGE_PCT / 100.0)
                log(
                    f"🛑 STOP LOSS HIT! Exit @ ₹{exit_price:.2f} | Net Loss: ₹{net_pnl:,.2f}"
                )
            elif now_time >= HARD_EXIT_TIME:
                exit_reason = "TIME_EXIT_0935"
                exit_price = cur_ltp * (1.0 - SLIPPAGE_PCT / 100.0)
                log(
                    f"⏰ 09:35 AM HARD CUT-OFF! Exit @ ₹{exit_price:.2f} | Final Net P&L: ₹{net_pnl:,.2f}"
                )

            if exit_reason:
                final_gross = (
                    exit_price - position["entry_price"]
                ) * position["qty"]
                final_net = final_gross - EST_CHARGES
                final_ret = (
                    (exit_price - position["entry_price"])
                    / position["entry_price"]
                ) * 100.0

                trade_record = {
                    "Date": position["date"],
                    "Top-3 Basket": position["basket"],
                    "Selected Stock": position["stock"],
                    "Qty": position["qty"],
                    "Entry Time": position["entry_time"],
                    "Entry Price": round(position["entry_price"], 2),
                    "Exit Time": now_dt.strftime("%H:%M:%S"),
                    "Exit Price": round(exit_price, 2),
                    "Exit Reason": exit_reason,
                    "Gross P&L (₹)": round(final_gross, 2),
                    "Est Charges (₹)": EST_CHARGES,
                    "Net P&L (₹)": round(final_net, 2),
                    "Net Return (%)": round(final_ret, 2),
                }
                save_detailed_trade(trade_record)
                log("📁 Trade details successfully saved to CSV trade book!")
                status_box.info("🏁 నేటి ట్రేడింగ్ సెషన్ విజయవంతంగా పూర్తయింది.")
                break

            time.sleep(1)


if start_engine_btn:
    run_full_pipeline()

# ==============================================================================
# 7. ట్రేడ్ బుక్ రిపోర్ట్ & CSV డౌన్‌లోడ్
# ==============================================================================
st.divider()
st.subheader("📊 ప్రొడక్షన్ ట్రేడ్ బుక్ (Audit Log)")

if os.path.exists(LOG_FILE):
    history_df = pd.read_csv(LOG_FILE)
    st.dataframe(history_df, use_container_width=True)

    csv_data = history_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Audit Log (CSV)",
        data=csv_data,
        file_name="Dhan_Scalper_Audit_Log.csv",
        mime="text/csv",
    )
else:
    st.info("ఇంకా ఎలాంటి ట్రేడ్లు రికార్డ్ కాలేదు.")
