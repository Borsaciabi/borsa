import streamlit as st
import plotly.graph_objects as go
from analysis.value_analysis import ValueAnalyzer
from data.cache.preloader import DataPreloader

analyzer = ValueAnalyzer()


def _get_data():
    data = st.session_state.get("stock_data", {})
    if not data:
        loader = DataPreloader()
        if loader.is_cache_valid(3600):
            data = loader.load_cache()
        if not data:
            data = loader.load_all()
        st.session_state.stock_data = data
    return data


def render_value_analysis():
    st.title("Deger Analizi")
    st.markdown("**Formul:** `(Piyasa Degeri - Net Borc) x (Fiili Oran / 100) / Fiili Dolasimdaki Hisse`")

    data = _get_data()
    if not data:
        st.warning("Veri yuklenemedi.")
        return

    all_codes = sorted(data.keys())

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.selectbox("Hisse Secin", all_codes, index=all_codes.index("THYAO") if "THYAO" in all_codes else 0)
    with col2:
        st.write("")
        st.write("")
        analyze_btn = st.button("Analiz Et", type="primary")

    if analyze_btn:
        _display_cached_result(data, symbol)

    # Hizli tablo
    st.divider()
    st.subheader("Tum Hisseler - Hizli Deger Analizi")
    rows = []
    for code, s in data.items():
        cv = s.get("calculated_value", 0) or 0
        if cv > 0:
            rows.append({
                "Kod": code,
                "Sirket": (s.get("company_name", "") or "")[:25],
                "Fiyat (TL)": s.get("last_price", 0) or 0,
                "Hesap. Deger": cv,
                "Oran": s.get("ratio", 0) or 0,
                "Kar %": s.get("expected_return", 0) or 0,
                "Sinyal": s.get("signal", ""),
            })
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows).sort_values("Oran", ascending=True)
        st.dataframe(df, use_container_width=True, height=500)


def _display_cached_result(data: dict, symbol: str):
    s = data.get(symbol, {})
    if not s:
        st.warning(f"{symbol} icin veri bulunamadi")
        return

    price = s.get("last_price", 0) or 0
    mcap = s.get("market_cap_mn", 0) or 0
    ndebt = s.get("net_debt_mn", 0) or 0
    frate = s.get("float_rate", 0) or 0
    fshares = s.get("floating_shares", 0) or 0
    calc_val = s.get("calculated_value", 0) or 0
    ratio = s.get("ratio", 0) or 0
    exp_ret = s.get("expected_return", 0) or 0
    signal = s.get("signal", "")
    change = s.get("change_pct", 0) or 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Son Fiyat", f"{price:.2f} TL", f"{change:+.2f}%")
    with col2:
        st.metric("Hesaplanan Deger", f"{calc_val:.2f} TL")
    with col3:
        st.metric("Oran", f"{ratio:.2f}")
    with col4:
        st.metric("Sinyal", signal)

    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Temel Bilgiler")
        for k, v in {
            "Sirket": s.get("company_name", ""),
            "Piyasa Degeri": f"{mcap:,.1f} M TL",
            "Net Borc": f"{ndebt:,.1f} M TL",
            "Fiili Dolasim": f"%{frate}",
            "Toplam Hisse": f"{s.get('total_shares', 0):,.0f}",
            "Fiili Dolasim Hisse": f"{fshares:,.0f}",
        }.items():
            st.write(f"**{k}:** {v}")

    with col_right:
        st.subheader("Hesaplama Detayi")
        for k, v in {
            "Hesaplanan Deger": f"{calc_val:.2f} TL",
            "Guncel Fiyat": f"{price:.2f} TL",
            "Oran (Fiyat/Deger)": f"{ratio:.2f}",
            "Kar Beklentisi": f"%{exp_ret:+.1f}",
            "Sinyal": signal,
        }.items():
            st.write(f"**{k}:** {v}")

    st.subheader("Fiyat Grafigi")
    from data.fetchers.bist_fetcher import BistFetcher
    bist = BistFetcher()
    history = bist.get_history(symbol, "1y")
    if history is not None and not history.empty:
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=history.index, open=history["Open"],
            high=history["High"], low=history["Low"],
            close=history["Close"], name="Fiyat"))
        fig.update_layout(title=f"{symbol} - 1 Yillik Fiyat Grafigi", template="plotly_dark", height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gecmis fiyat verisi alinamadi.")
