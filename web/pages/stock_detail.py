import json
import streamlit as st
from analysis.technical_analysis import TechnicalAnalyzer
from data.cache.preloader import DataPreloader
from data.fetchers.bist_fetcher import BistFetcher
from data.fetchers.yahoo_fetcher import YahooFetcher
from data.database.db_manager import DBManager
from pages.news import render_news, render_pay_tedbirleri
import plotly.graph_objects as go

tech = TechnicalAnalyzer()
bist = BistFetcher()
yahoo = YahooFetcher()
db = DBManager()


def _get_data():
    data = st.session_state.get("stock_data", {})
    if not data:
        loader = DataPreloader()
        if loader.is_cache_valid(3600):
            data = loader.load_cache()
        if not data:
            data = loader.load_from_database()
        if not data:
            data = loader.load_all()
        st.session_state.stock_data = data
    return data


def render_stock_detail():
    st.title("Hisse Detay")

    data = _get_data()
    if not data:
        st.warning("Veri yuklenemedi.")
        return

    all_codes = sorted(data.keys())

    col1, col2 = st.columns([4, 1])
    with col1:
        symbol = st.selectbox("Hisse Secin", all_codes, index=all_codes.index("THYAO") if "THYAO" in all_codes else 0)
    with col2:
        period = st.selectbox("Donem", ["6ay", "1y", "2y", "5y"], index=1)

    if st.button("Analiz Et", type="primary"):
        _run_analysis(data, symbol, period)


def _run_analysis(data: dict, symbol: str, period: str):
    s = data.get(symbol, {})
    if not s:
        st.warning(f"{symbol} icin veri bulunamadi")
        return

    enriched = yahoo.get_company_data(symbol) or {}
    for key, value in enriched.items():
        if value is not None and value != 0:
            s[key] = value

    price = s.get("price") or s.get("last_price", 0) or 0
    change = s.get("change_pct", 0) or 0
    mcap = s.get("market_cap_mn", 0) or 0
    ndebt = s.get("net_debt_mn", 0) or 0
    frate = s.get("float_rate", 0) or 0
    fshares = s.get("floating_shares", 0) or 0
    calc_val = s.get("calculated_value", 0) or 0
    ratio = s.get("ratio", 0) or 0
    exp_ret = s.get("expected_return", 0) or 0
    signal = s.get("signal", "")

    st.markdown(f"## {symbol} - {s.get('company_name', '')}")

    user_view = db.get_stock_user_view(symbol) or {}
    tabs = st.tabs(["Genel Bakis", "Teknik Analiz", "Finansallar", "Benim Gorusum"])
    with tabs[0]:
        _render_snapshot(s, price, change, mcap, ndebt, frate, fshares, calc_val, ratio, exp_ret, signal)
        render_pay_tedbirleri(symbol=symbol)
        render_news(symbol=symbol, limit=10, title=f"{symbol} KAP Haberleri")

    with tabs[1]:
        tech_result = _render_technical(symbol, period)

    with tabs[2]:
        _render_financials(s)

    with tabs[3]:
        _render_user_view(symbol, user_view, price)

    st.divider()
    st.subheader("Fiyat Grafigi")
    _render_price_chart(symbol, period, tech_result)


def _render_snapshot(s, price, change, mcap, ndebt, frate, fshares, calc_val, ratio, exp_ret, signal):
    st.subheader("Piyasa Ozeti")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Fiyat", f"{price:.2f} TL", f"{change:+.2f}%")
    with col2:
        st.metric("Hesap. Deger", f"{calc_val:.2f} TL")
    with col3:
        st.metric("Oran", f"{ratio:.2f}")
    with col4:
        st.metric("Sinyal", signal)

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Piyasa Degeri", f"{mcap:,.0f} mn TL")
    with col_b:
        st.metric("Net Borc", f"{ndebt:,.0f} mn TL")
    with col_c:
        st.metric("F/D", f"%{frate}")
    with col_d:
        st.metric("Kar Beklentisi", f"%{exp_ret:+.1f}")


def _render_technical(symbol, period):
    with st.spinner("Teknik analiz yapiliyor..."):
        tech_result = tech.analyze(symbol, period)

    if tech_result and tech_result.get("current_price"):
        st.subheader("Teknik Analiz")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            rsi = tech_result.get("rsi")
            st.metric("RSI", f"{rsi:.1f}" if rsi else "N/A")
        with col2:
            ma200 = tech_result.get("ma200")
            st.metric("MA200", f"{ma200:.2f}" if ma200 else "N/A")
        with col3:
            ma50 = tech_result.get("ma50")
            st.metric("MA50", f"{ma50:.2f}" if ma50 else "N/A")
        with col4:
            ma20 = tech_result.get("ma20")
            st.metric("MA20", f"{ma20:.2f}" if ma20 else "N/A")
        with col5:
            diff = tech_result.get("price_vs_ma200")
            st.metric("MA200 Fark", f"%{diff:.1f}" if diff else "N/A")
    else:
        st.info("Teknik analiz verisi alinamadi.")
    return tech_result

def _render_financials(s):
    st.subheader("Finansal ve Sirket Bilgileri")
    rows = {
        "Sirket": s.get("company_name", "") or "-",
        "Sektor": s.get("sector", "") or "-",
        "Piyasa Degeri": f"{s.get('market_cap_mn', 0):,.1f} mn TL",
        "Net Borc": f"{s.get('net_debt_mn', 0):,.1f} mn TL",
        "Fiili Dolasim": f"%{s.get('float_rate', 0)}",
        "Toplam Hisse": f"{s.get('total_shares', 0):,.0f}",
        "Fiili Dolasim Hisse": f"{s.get('floating_shares', 0):,.0f}",
        "Hacim": f"{s.get('volume', 0):,.0f}",
        "F/K": f"{s.get('pe', 0):.2f}" if s.get("pe") else "N/A",
        "PD/DD": f"{s.get('pb', 0):.2f}" if s.get("pb") else "N/A",
        "Gelir": _format_large_value(s.get("revenue")),
        "Net Kar": _format_large_value(s.get("net_income")),
        "Ozkaynaklar": _format_large_value(s.get("total_equity")),
        "Odenmis Sermaye": _format_large_value(s.get("paid_in_capital")),
        "Bilanco Donemi": s.get("financial_period") or "N/A",
        "Hisse B. Kar": _format_number(s.get("eps")),
        "Temettu": _format_number(s.get("dividend_rate")),
        "Temettu Verimi": _format_percent(s.get("dividend_yield"), ratio=100),
        "Aktif Karliligi": _format_percent(s.get("return_on_assets"), ratio=100),
        "Ozkaynak Getirisi": _format_percent(s.get("return_on_equity"), ratio=100),
        "Brut Kar Marji": _format_percent(s.get("gross_margin"), ratio=100),
        "FAVOK": _format_large_value(s.get("ebitda")),
        "BKD/FAVOK": _format_number(s.get("enterprise_to_ebitda")),
        "Beta": _format_number(s.get("beta")),
        "Defter Degeri / Hisse": _format_number(s.get("book_value")),
    }
    st.dataframe([{"Metrik": key, "Deger": value} for key, value in rows.items()], hide_index=True, use_container_width=True)
    if s.get("financial_periods"):
        try:
            periods = json.loads(s["financial_periods"])
            if periods:
                st.caption("Is Yatirim'dan cekilen mevcut bilanço donemleri")
                st.dataframe(
                    [
                        {
                            "Donem": period,
                            "Ozkaynaklar": _format_large_value(values.get("total_equity")),
                            "Odenmis Sermaye": _format_large_value(values.get("paid_in_capital")),
                            "Net Kar": _format_large_value(values.get("net_income")),
                        }
                        for period, values in periods.items()
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

    st.subheader("Piyasa Verileri")
    market_rows = {
        "Alis / Satis": f"{_format_number(s.get('bid'))} / {_format_number(s.get('ask'))}",
        "Onceki Kapanis": _format_number(s.get("previous_close")),
        "Acilis": _format_number(s.get("open")),
        "Gun Araligi": f"{_format_number(s.get('day_low'))} - {_format_number(s.get('day_high'))}",
        "52 Hafta": f"{_format_number(s.get('fifty_two_week_low'))} - {_format_number(s.get('fifty_two_week_high'))}",
        "Ortalama Hacim (3 Ay)": _format_large_value(s.get("average_volume_3m")),
        "1 Yillik Degisim": _format_percent(s.get("year_change_pct")),
        "Adil Deger": _format_number(s.get("calculated_value")) if s.get("calculated_value") else "Goster",
        "Adil Deger Degisimi": "Goster",
        "Sonraki Kazanc Tarihi": _format_timestamp(s.get("earnings_date")),
    }
    st.dataframe([{"Metrik": key, "Deger": value} for key, value in market_rows.items()], hide_index=True, use_container_width=True)


def _format_number(value):
    return f"{float(value):,.2f}" if value is not None else "Goster"


def _format_percent(value, ratio=1):
    return f"{float(value) * ratio:.2f}%" if value is not None else "Goster"


def _format_large_value(value):
    if value is None:
        return "Goster"
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:,.2f} B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f} M"
    return f"{value:,.0f}"


def _format_timestamp(value):
    if not value:
        return "Goster"
    try:
        from datetime import datetime
        return datetime.fromtimestamp(float(value)).strftime("%d %b %Y")
    except (TypeError, ValueError, OSError):
        return "Goster"


def _render_user_view(symbol, user_view, current_price):
    st.subheader("Benim Gorusum")
    st.caption("Bu alan sadece senin yorumun ve hedefin icin tutulur.")
    signal_options = ["Izle", "AL", "SAT", "Evi Barki Sat"]
    current_signal = user_view.get("personal_signal", "Izle")
    signal_index = signal_options.index(current_signal) if current_signal in signal_options else 0
    opinion = st.text_area("Kendi yorumun", value=user_view.get("opinion", ""), height=150, key=f"opinion_{symbol}")
    col1, col2 = st.columns(2)
    with col1:
        personal_signal = st.selectbox("Kisisel sinyal", signal_options, index=signal_index, key=f"signal_{symbol}")
    with col2:
        target_value = user_view.get("price_target")
        target = st.number_input("Kendi hedef fiyatin", min_value=0.0, value=float(target_value or current_price or 0), step=0.10, key=f"target_{symbol}")
    if st.button("Gorusumu Kaydet", type="primary", key=f"save_view_{symbol}"):
        db.save_stock_user_view(symbol, opinion, personal_signal, target or None)
        st.success("Kisisel gorusun kaydedildi.")


def _render_price_chart(symbol, period, tech_result=None):
    history = bist.get_history(symbol, period)
    if history is not None and not history.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=history.index, open=history["Open"],
            high=history["High"], low=history["Low"],
            close=history["Close"], name="Fiyat"))
        if tech_result:
            if tech_result.get("ma20_series") is not None and not tech_result["ma20_series"].empty:
                fig.add_trace(go.Scatter(
                    x=history.index, y=tech_result["ma20_series"],
                    name="MA20", line=dict(color="yellow", width=1)))
            if tech_result.get("ma50_series") is not None and not tech_result["ma50_series"].empty:
                fig.add_trace(go.Scatter(
                    x=history.index, y=tech_result["ma50_series"],
                    name="MA50", line=dict(color="blue", width=1)))
            if tech_result.get("ma200_series") is not None and not tech_result["ma200_series"].empty:
                fig.add_trace(go.Scatter(
                    x=history.index, y=tech_result["ma200_series"],
                    name="MA200", line=dict(color="red", width=1)))
        fig.update_layout(title=f"{symbol} Fiyat Grafigi", template="plotly_dark", height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gecmis fiyat verisi alinamadi.")
