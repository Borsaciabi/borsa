import streamlit as st
from data.cache.preloader import DataPreloader
import plotly.graph_objects as go


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


def render_comparison():
    st.title("Hisse Karsilastirma")

    data = _get_data()
    if not data:
        st.warning("Veri yuklenemedi.")
        return

    all_codes = sorted(data.keys())
    symbols = st.multiselect(
        "Hisse Secin (2-5 arasi)",
        all_codes,
        default=["THYAO", "GARAN", "AKBNK"],
        max_selections=5,
    )

    if st.button("Karsilastir", type="primary") and len(symbols) >= 2:
        _display_comparison(data, symbols)


def _display_comparison(data: dict, symbols: list):
    st.subheader("Karsilastirma Tablosu")

    rows = []
    for sym in symbols:
        s = data.get(sym, {})
        if not s:
            continue
        rows.append({
            "Hisse": sym,
            "Sirket": (s.get("company_name", "") or "")[:20],
            "Fiyat (TL)": f"{s.get('last_price', 0) or 0:.2f}",
            "Deger (TL)": f"{s.get('calculated_value', 0) or 0:.2f}",
            "Oran": f"{s.get('ratio', 0) or 0:.2f}",
            "Sinyal": s.get("signal", ""),
            "Kar %": f"%{s.get('expected_return', 0) or 0:+.1f}",
            "Piyasa Deg (mn)": f"{s.get('market_cap_mn', 0) or 0:,.0f}",
            "F/K": f"{s.get('pe', 'N/A')}" if s.get("pe") else "N/A",
            "PD/DD": f"{s.get('pb', 'N/A')}" if s.get("pb") else "N/A",
        })

    if rows:
        import pandas as pd
        st.table(pd.DataFrame(rows))

    # Bar grafigi
    st.subheader("Deger vs Fiyat Karsilastirmasi")
    filtered_data = [(sym, data.get(sym, {})) for sym in symbols if data.get(sym)]
    if filtered_data:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Guncel Fiyat",
            x=[sym for sym, _ in filtered_data],
            y=[s.get("last_price", 0) or 0 for _, s in filtered_data],
        ))
        fig.add_trace(go.Bar(
            name="Hesaplanan Deger",
            x=[sym for sym, _ in filtered_data],
            y=[s.get("calculated_value", 0) or 0 for _, s in filtered_data],
        ))
        fig.update_layout(barmode="group", template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Radar grafik
    st.subheader("Radar Karsilastirmasi")
    valid = [(sym, s) for sym, s in filtered_data if (s.get("calculated_value", 0) or 0) > 0]
    if valid:
        categories = ["Fiyat", "Deger", "Kar %"]
        fig_radar = go.Figure()
        for sym, s in valid:
            values = [
                abs(s.get("last_price", 0) or 0),
                abs(s.get("calculated_value", 0) or 0),
                abs(s.get("expected_return", 0) or 0),
            ]
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]], theta=categories + [categories[0]],
                fill="toself", name=sym,
            ))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark", height=500)
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Radar grafigi icin yeterli veri bulunamadi.")
