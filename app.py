import datetime
import os
import time
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ==============================================================================
# 1. DHAN CLIENT RESOLVER & DIRECT REST FALLBACK
# ==============================================================================
class DirectDhanAPI:
    """DhanHQ లైబ్రరీ లేకుండా నేరుగా పనిచేసే డైరెక్ట్ REST API ఇంజిన్"""
    def __init__(self, client_id, access_token):
        self.client_id = str(client_id).strip()
        self.access_token = str(access_token).strip()
        self.base_url = "https://api.dhan.co/v2"
        self.headers = {
            "access-token": self.access_token,
            "client-id": self.client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_quote(self, security_id, exchange_segment="NSE_EQ", instrument_type="EQUITY"):
        try:
            url = f"{self.base_url}/marketfeed/quote"
            payload = {exchange_segment: [int(security_id)]}
            res = requests.post(url, headers=self.headers, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", {}).get(exchange_segment, {}).get(str(security_id), {})
                ohlc = data.get("ohlc", {})
                return {
                    "status": "success",
                    "data": {
                        "open": ohlc.get("open", data.get("last_price", 0.0)),
                        "last_price": data.get("last_price", 0.0)
                    }
                }
        except Exception:
            pass
        return {"status": "error"}

    def intraday_daily_minute_charts(self, security_id, exchange_segment="NSE_EQ", instrument_type="EQUITY"):
        try:
            url = f"{self.base_url}/charts/intraday"
            payload = {
                "securityId": str(security_id),
                "exchangeSegment": exchange_segment,
                "instrument": instrument_type
            }
            res = requests.post(url, headers=self.headers, json=payload, timeout=5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
        return {"status": "error"}


def init_dhan_client(client_id, access_token):
    """అన్ని రకాల ప్యాకేజీ వెర్షన్లను ఆటో-డిటెక్ట్ చేసే ఇనిషియలైజర్"""
    c_id = str(client_id).strip()
    tok = str(access_token).strip()

    # 1. అధికారిక ప్యాకేజీని సరిగ్గా లోడ్ చేయడం
    try:
        import dhanhq
        target = dhanhq
        while hasattr(target, "dhanhq") and not hasattr(target, "get_quote"):
            sub = getattr(target, "dhanhq")
            if sub == target:
                break
            target = sub
        if callable(target):
            try:
                inst = target(c_id, tok)
                if hasattr(inst, "get_quote") or hasattr(inst, "intraday_daily_minute_charts"):
                    return inst
            except Exception:
                pass
    except Exception:
        pass

    # 2. డైరెక్ట్ REST API ఫాల్‌బ్యాక్
    return DirectDhanAPI(c_id, tok)


# ==============================================================================
# 2. పేజ్ సెటప్ & కాన్ఫిగరేషన్
# ==============================================================================
st.set_page_config(
    page_title="Dhan F&O Top-3 Scalper Pro", layout="wide", page_icon="⚡"
)

IST = ZoneInfo("Asia/Kolkata")

# స్ట్రాటజీ స్థిర విలువలు
VIRTUAL_CAPITAL = 125000.0
TARGET_PERCENT = 1.0
SL_PERCENT = 0.5
SLIPPAGE_PCT = 0.05
EST_CHARGES = 40.0

# సమయాలు (IST)
SCAN_TIME = datetime.time(9, 15, 35)
ENTRY_CUTOFF_TIME = datetime.time(9, 25, 0)
HARD_EXIT_TIME = datetime.time(9, 35, 0)

LOG_FILE = "trade_history.csv"
STOCKS_FILE = "fno_stocks.txt"

# ==============================================================================
# 3. సైడ్‌బార్ - లాగిన్ & కంట్రోల్స్
# ==============================================================================
st.sidebar.header("🔑 Dhan API లాగిన్")
dhan_client_input = st.sidebar.text_input("Client ID", value="1113235897")
dhan_token_input = st.sidebar.text_input(
    "Daily Access Token (24-Hr)",
    type="password",
    help="Dhan పోర్టల్ నుండి తాజా టోకెన్ ఇక్కడ పేస్ట్ చేయండి",
)

start_engine_btn = st.sidebar.button("🚀 Start Engine")


# ==============================================================================
# 4. సెక్యూరిటీ మాస్టర్ & స్టాక్స్ లోడింగ్
# ==============================================================================
@st.cache_data(ttl=86400)
def load_security_master():
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
    except Exception:
        return {}


def load_stock_universe(file_path=STOCKS_FILE):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            stocks = [
                line.strip().replace(".NS", "")
                for line in f.readlines()
                if line.strip() and not line.startswith("#")
            ]
            if stocks:
                return stocks
    return ["ATHERENERG", "COFORGE", "LTIM", "BHEL", "TATAMOTORS", "RELIANCE", "INFY", "HDFCBANK"]


FO_STOCKS = load_stock_universe()
SCRIP_MAP = load_security_master()


# ==============================================================================
# 5. టెక్నికల్ ఇండికేటర్స్ & డేటా హెల్పర్స్
# ==============================================================================
def calculate_indicators(df):
    if len(df) == 0:
        return df

    df["EMA_9"] = df["close"].ewm(span=9, adjust=False).mean()

    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_vp = (typical_price * df["volume"]).cumsum()
    df["VWAP"] = np.where(cum_vol > 0, cum_vp / cum_vol, df["close"])
    return df


def get_live_intraday_data(dhan_obj, security_id):
    try:
        resp = dhan_obj.intraday_daily_minute_charts(
            security_id=str(security_id),
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
        )
        if isinstance(resp, dict) and resp.get("status") == "success":
            data = resp.get("data", {})
            if "timestamp" in data and len(data["timestamp"]) > 0:
                df = pd.DataFrame(
                    {
                        "timestamp": pd.to_datetime(data["timestamp"]),
                        "open": [float(x) for x in data["open"]],
                        "high": [float(x) for x in data["high"]],
                        "low": [float(x) for x in data["low"]],
                        "close": [float(x) for x in data["close"]],
                        "volume": [float(x) for x in data["volume"]],
                    }
                )
                return df.sort_values("timestamp").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()


def scan_top_3_dhan(dhan_obj):
    gainers = []
    for sym in FO_STOCKS:
        sec_id = SCRIP_MAP.get(sym)
        if not sec_id:
            continue
        try:
            quote = dhan_obj.get_quote(
                security_id=str(sec_id),
                exchange_segment="NSE_EQ",
                instrument_type="EQUITY",
            )
            if isinstance(quote, dict) and quote.get("status") == "success":
                q = quote.get("data", {})
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


def save_detailed_trade(record):
    df_new = pd.DataFrame([record])
    if not os.path.exists(LOG_FILE):
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode="a", header=False, index=False)


# ==============================================================================
# 6. UI డ్యాష్‌బోర్డ్
# ==============================================================================
st.title("⚡ Dhan F&O Top-3 Scalper Pro")
st.caption(
    f"Universe: {len(FO_STOCKS)} Stocks | Auto Scan (09:15:35) ➔ Auto Monitor (09:16-09:25) ➔ Auto Exit (09:35)"
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
# 7. మెయిన్ ఎగ్జిక్యూషన్ ఇంజిన్
# ==============================================================================
def run_full_pipeline():
    c_id = str(dhan_client_input).strip()
    tok = str(dhan_token_input).strip()

    if not c_id or not tok:
        st.error("⚠️ దయచేసి Client ID మరియు Token రెండింటినీ ఎంటర్ చేయండి!")
        return

    # ధన్ క్లయింట్ ఆటో ఇనిషియలైజేషన్
    dhan = init_dhan_client(c_id, tok)

    logs = []

    def log(msg):
        t_str = datetime.datetime.now(IST).strftime("%H:%M:%S")
        logs.append(f"[{t_str}] {msg}")
        log_box.text_area("📜 సిస్టమ్ ఆడిట్ లాగ్స్", "\n".join(logs), height=230)

    log("✅ Dhan API విజయవంతంగా కనెక్ట్ అయింది. స్టాండ్‌బై మోడ్ ఆన్ అయింది.")

    state = "WAITING_FOR_091535"
    basket = []
    position = None

    while True:
        now_dt = datetime.datetime.now(IST)
        now_time = now_dt.time()
        today_date = now_dt.strftime("%Y-%m-%d")

        # స్టేజ్ 1: 09:15:35 కోసం నిరీక్షణ
        if state == "WAITING_FOR_091535":
            if now_time < SCAN_TIME:
                diff_sec = int(
                    (
                        datetime.datetime.combine(
                            datetime.date.today(), SCAN_TIME
                        )
                        - datetime.datetime.combine(
                            datetime.date.today(), now_time
                        )
                    ).total_seconds()
                )
                status_box.info(
                    f"⏳ మార్కెట్ ఓపెన్ కోసం వేచి చూస్తున్నాం... స్కానింగ్‌కు ఇంకా **{diff_sec} సెకన్లు** ఉంది. (సమయం: {now_time.strftime('%H:%M:%S')})"
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
                log(f"🎯 టాప్-3 బాస్కెట్ లాక్ అయింది: {b_str}")
                state = "MONITORING_BREAKOUT"
            else:
                log("Dhan డేటా ఫెచ్ కాలేదు, 2 సెకన్లలో రీ-ట్రై అవుతుంది...")
                time.sleep(2)
                continue

        # స్టేజ్ 2: మానిటరింగ్ & ఫస్ట్ బ్రేకౌట్ ట్రిగ్గర్
        elif state == "MONITORING_BREAKOUT":
            if now_time > ENTRY_CUTOFF_TIME:
                status_box.warning(
                    "⏰ 09:25:00 AM కటాఫ్ ముగిసింది. ఏ స్టాక్‌లోనూ బ్రేకౌట్ రాలేదు (No Trade Day)."
                )
                log("09:25 AM Cut-off reached. Strategy Stopped.")
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

        # స్టేజ్ 3: పొజిషన్ ట్రాకింగ్ & ఎగ్జిట్
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
# 8. ట్రేడ్ బుక్ & రిపోర్ట్ డౌన్‌లోడ్
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
