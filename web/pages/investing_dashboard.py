import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data.cache.preloader import DataPreloader
from data.fetchers.bist_fetcher import BistFetcher

bist = BistFetcher()

SIGNAL_ORDER = ["Evi Barki Sat", "AL", "Kafana Gore", "SAT", "Hemen SAT", "Veri Yetersiz"]
SIGNAL_COLORS = {
    "Evi Barki Sat": "#00C853", "AL": "#00E676", "Kafana Gore": "#FFD600",
    "SAT": "#FF9100", "Hemen SAT": "#FF1744", "Veri Yetersiz": "#9E9E9E",
}


def render_investing_dashboard():
    loader = DataPreloader()
    current_user = st.session_state.get("user")
    if not isinstance(current_user, dict):
        current_user = {}

    data = st.session_state.get("stock_data", {})
    cache_time = st.session_state.get("cache_time", "Bilinmiyor")

    if not data:
        with st.spinner("Veriler yukleniyor... (ilk acilista ~2-3 dk surebilir)"):
            if loader.is_cache_valid(3600):
                data = loader.load_cache()
            if not data:
                data = loader.load_all()
            st.session_state.stock_data = data
            st.session_state.cache_time = loader.get_cache_time()
            cache_time = st.session_state.cache_time

    col_title, col_refresh, col_price = st.columns([4, 1, 1])
    with col_title:
        st.title("Piyasa Panosu")
        st.caption("BIST hisselerini fiyat, deger ve sinyal bazinda tek ekranda takip edin.")
        st.caption(f"Son guncelleme: {cache_time} | Toplam hisse: {len(data)}")
    with col_refresh:
        if current_user.get("role") == "admin":
            st.write("")
            st.write("")
            if st.button("Verileri Guncelle", key="refresh_main"):
                with st.spinner("Guncelleniyor..."):
                    fresh_data = loader.load_all()
                    if fresh_data:
                        st.session_state.stock_data = fresh_data
                        st.session_state.cache_time = loader.get_cache_time()
                st.rerun()
            if st.button("2026 Bilancolarini Guncelle", key="refresh_financials"):
                with st.spinner("Is Yatirim'dan 2026 bilancolari cekiliyor..."):
                    updated = loader.update_financials(
                        symbols=["ISCTR"],
                        start_year=2026,
                        end_year=2026,
                    )
                    if updated:
                        st.session_state.stock_data.update(updated)
                        st.success(f"ISCTR bilancosu guncellendi ({len(updated)} kayit).")
                    else:
                        st.warning("2026 icin Is Yatirim'da yayinlanmis bilanço verisi bulunamadi.")
                st.rerun()
        else:
            st.caption("Temel veri guncellemesi admin yetkisindedir")
    with col_price:
        st.write("")
        st.write("")
        # Fiyat guncelleme durumu
        try:
            resp = requests.get("http://localhost:8000/api/price-updater/status", timeout=2)
            if resp.status_code == 200:
                updater_status = resp.json()
                is_running = updater_status.get("running", False)
                last_update = updater_status.get("last_update", None)
                total_updates = updater_status.get("total_updates", 0)

                if is_running:
                    st.success(f"Fiyat Otomatik: Aktif ({total_updates} guncelleme)")
                else:
                    st.warning("Fiyat Otomatik: Pasif")

                if last_update:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(last_update)
                        st.caption(f"Son fiyat: {dt.strftime('%H:%M')}")
                    except:
                        pass
            else:
                st.info("Fiyat servisi: API baglantisi yok")
        except:
            st.info("Fiyat servisi: API baglantisi yok")

        if st.session_state.get("auth_token") and st.button("Fiyat Guncelle", key="refresh_prices"):
            with st.spinner("Fiyatlar guncelleniyor... (Mynet)"):
                try:
                    resp = requests.post(
                        "http://localhost:8000/api/price-updater/update",
                        headers={"Authorization": f"Bearer {st.session_state.auth_token}"},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        fresh_data = loader.load_cache_with_backup()
                        if fresh_data:
                            st.session_state.stock_data = fresh_data
                            st.session_state.cache_time = loader.get_cache_time()
                        st.success("Fiyatlar guncellendi!")
                    else:
                        st.error("Fiyat guncelleme basarisiz!")
                except Exception as e:
                    # API calismiyorsa dogrudan guncelle
                    loader.update_prices_only()
                    fresh_data = loader.get_all_data()
                    if fresh_data:
                        st.session_state.stock_data = fresh_data
                        st.session_state.cache_time = loader.get_cache_time()
                    st.success("Fiyatlar guncellendi (dogrudan)!")
            st.rerun()
        elif not st.session_state.get("auth_token"):
            st.caption("Fiyat guncellemek icin kayit olun veya giris yapin")

    _render_market_summary(data)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Tum Hisseler", "AL/SAT Onerileri", "Deger Analizi",
        "En Iyiler / En Kotuler", "Hisse Detay"
    ])

    with tab1:
        _render_all_stocks_table(data)
    with tab2:
        _render_al_sat_recommendations(data)
    with tab3:
        _render_value_analysis_table(data)
    with tab4:
        _render_top_movers(data)
    with tab5:
        _render_stock_detail(data)


def _render_market_summary(data: dict):
    stocks = list(data.values())
    total_mcap = sum(s.get("market_cap_mn", 0) or 0 for s in stocks)
    up = sum(1 for s in stocks if (s.get("change_pct", 0) or 0) > 0)
    down = sum(1 for s in stocks if (s.get("change_pct", 0) or 0) < 0)
    changes = [s.get("change_pct", 0) or 0 for s in stocks if s.get("change_pct") is not None]
    avg_change = sum(changes) / len(changes) if changes else 0

    signals = {}
    for s in stocks:
        sig = s.get("signal", "Veri Yetersiz")
        signals[sig] = signals.get(sig, 0) + 1

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Toplam Piyasa Degeri", f"{total_mcap:,.0f} mn TL")
    with col2:
        st.metric("Yukselen", f"{up}")
    with col3:
        st.metric("Dusen", f"{down}")
    with col4:
        st.metric("Ort. Degisim", f"%{avg_change:+.2f}")
    with col5:
        al_count = signals.get("AL", 0) + signals.get("Evi Barki Sat", 0)
        sat_count = signals.get("SAT", 0) + signals.get("Hemen SAT", 0)
        st.metric("AL Sinyali", f"{al_count}", f"SAT: {sat_count}")
    st.divider()


def _render_all_stocks_table(data: dict):
    st.subheader("Tum BIST Hisseleri")

    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Hisse Ara (Kod veya Ad)", key="search_all_v2")
    with col2:
        signal_filter = st.selectbox("Sinyal Filtresi",
            ["Tumu", "AL", "Evi Barki Sat", "Kafana Gore", "SAT", "Hemen SAT", "Veri Yetersiz"],
            key="signal_filter_v2")
    with col3:
        sort_by = st.selectbox("Sirala",
            ["Piyasa Degeri", "Degisim %", "Hacim", "Fiyat", "Oran"],
            key="sort_by_v2")

    rows = []
    total_count = len(data)
    for code, s in data.items():
        if search:
            q = search.upper()
            name = (s.get("company_name", "") or "").upper()
            if q not in code.upper() and q not in name:
                continue
        if signal_filter != "Tumu" and s.get("signal") != signal_filter:
            continue
        rows.append({
            "Kod": code,
            "Sirket": (s.get("company_name", "") or "")[:30],
            "Fiyat (TL)": s.get("last_price", 0) or 0,
            "Degisim (%)": s.get("change_pct", 0) or 0,
            "Hacim": s.get("volume", 0) or 0,
            "Piyasa Deg (mn)": s.get("market_cap_mn", 0) or 0,
            "F/D (%)": s.get("float_rate", 0) or 0,
            "Hesap. Deger": s.get("calculated_value", 0) or 0,
            "Oran": s.get("ratio", 0) or 0,
            "Kar %": s.get("expected_return", 0) or 0,
            "Sinyal": s.get("signal", ""),
        })

    if rows:
        df = pd.DataFrame(rows)
        sort_map = {
            "Piyasa Degeri": "Piyasa Deg (mn)", "Degisim %": "Degisim (%)",
            "Hacim": "Hacim", "Fiyat": "Fiyat (TL)", "Oran": "Oran",
        }
        sort_col = sort_map.get(sort_by, "Piyasa Deg (mn)")
        df = df.sort_values(sort_col, ascending=False)
        st.dataframe(df, use_container_width=True, height=600)
        st.info(f"{len(rows)} / {total_count} hisse gosteriliyor")
    else:
        st.warning("Arama kriterlerinize uygun hisse bulunamadi.")


def _render_al_sat_recommendations(data: dict):
    st.subheader("AL / SAT Oneri Sistemi")
    st.markdown("""
    **Formul:** `(Piyasa Degeri - Net Borc) x (Fiili Oran / 100) / Fiili Dolasim Hisse Sayisi`
    **Oran:** `Son Fiyat / Hesaplanan Deger`
    """)

    results = []
    for code, s in data.items():
        price = s.get("last_price", 0) or 0
        mcap = s.get("market_cap_mn", 0) or 0
        ndebt = s.get("net_debt_mn", 0) or 0
        frate = s.get("float_rate", 0) or 0
        fshares = s.get("floating_shares", 0) or 0
        vol = s.get("volume", 0) or 0
        change = s.get("change_pct", 0) or 0

        if price <= 0 or mcap <= 0 or fshares <= 0:
            continue

        calc_val = ((mcap - ndebt * 1_000_000) * (frate / 100)) / fshares if fshares > 0 else 0
        if calc_val <= 0:
            continue
        ratio = price / calc_val
        exp_ret = ((calc_val - price) / price) * 100

        # Kapsamli skor hesaplama
        score = 0

        # Oran skoru (0-40)
        if ratio < 0.5:
            score += 40
        elif ratio < 0.7:
            score += 35
        elif ratio < 1.0:
            score += 25
        elif ratio < 1.5:
            score += 10
        elif ratio > 3.0:
            score -= 10

        # Kar beklentisi skoru (0-25)
        if exp_ret > 150:
            score += 25
        elif exp_ret > 100:
            score += 20
        elif exp_ret > 50:
            score += 15
        elif exp_ret > 20:
            score += 10
        elif exp_ret > 0:
            score += 5

        # Degisim skoru (0-15)
        if change > 5:
            score += 15
        elif change > 2:
            score += 10
        elif change > 0:
            score += 5
        elif change < -5:
            score -= 5

        # Hacim skoru (0-10)
        if vol > 100_000_000:
            score += 10
        elif vol > 50_000_000:
            score += 7
        elif vol > 10_000_000:
            score += 3

        # Buyukluk skoru (0-10)
        if mcap > 100_000:
            score += 10
        elif mcap > 50_000:
            score += 7
        elif mcap > 10_000:
            score += 3

        # Sinyal
        if ratio > 3:
            signal = "Hemen SAT"
        elif ratio > 1.5:
            signal = "SAT"
        elif ratio > 0.99:
            signal = "Kafana Gore"
        elif ratio > 0.7:
            signal = "AL"
        elif ratio > 0.000001:
            signal = "Evi Barki Sat"
        else:
            signal = "Veri Yetersiz"

        # Oneri belirle
        score = max(0, min(score, 100))
        if score >= 75:
            oneri = "GUCLEN AL"
            oneri_color = "#00E676"
        elif score >= 55:
            oneri = "AL"
            oneri_color = "#00C853"
        elif score >= 35:
            oneri = "IZLE"
            oneri_color = "#FFD600"
        elif score >= 15:
            oneri = "SAT"
            oneri_color = "#FF9100"
        else:
            oneri = "GUCLEN SAT"
            oneri_color = "#FF1744"

        results.append({
            "Kod": code,
            "Sirket": (s.get("company_name", "") or "")[:25],
            "Fiyat": price,
            "Hesap. Deger": round(calc_val, 2),
            "Oran": round(ratio, 2),
            "Kar %": round(exp_ret, 1),
            "Degisim %": round(change, 2),
            "Hacim": vol,
            "Piyasa Deg (mn)": round(mcap),
            "Skor": score,
            "Oneri": oneri,
            "Sinyal": signal,
        })

    if not results:
        st.warning("Deger analizi yapilacak hisse bulunamadi.")
        return

    # Filtreler
    col1, col2, col3 = st.columns(3)
    with col1:
        min_score = st.slider("Minimum Skor", 0, 100, 40, key="min_score_al")
    with col2:
        oneri_filter = st.selectbox("Oneri Filtresi",
            ["Tumu", "GUCLEN AL", "AL", "IZLE", "SAT", "GUCLEN SAT"], key="oneri_filter")
    with col3:
        sort_by = st.selectbox("Sirala",
            ["Skor (Yuksek)", "Kar Beklentisi", "Oran (Dusen)", "Piyasa Degeri"],
            key="sort_al")

    filtered = [r for r in results if r["Skor"] >= min_score]
    if oneri_filter != "Tumu":
        filtered = [r for r in filtered if r["Oneri"] == oneri_filter]

    sort_funcs = {
        "Skor (Yuksek)": lambda x: x["Skor"],
        "Kar Beklentisi": lambda x: x["Kar %"],
        "Oran (Dusen)": lambda x: -x["Oran"],
        "Piyasa Degeri": lambda x: x["Piyasa Deg (mn)"],
    }
    filtered.sort(key=sort_funcs.get(sort_by, lambda x: x["Skor"]), reverse=True)

    # GUCLEN AL bolumu
    guclen_al = [r for r in filtered if r["Oneri"] in ["GUCLEN AL", "AL"]]
    if guclen_al:
        st.markdown(f"### Gucel AL Onerileri ({len(guclen_al)} hisse)")
        for r in guclen_al[:15]:
            c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1, 1, 1, 1])
            with c1:
                st.markdown(f"**{r['Kod']}** - {r['Sirket']}")
            with c2:
                st.write(f"Fiyat: {r['Fiyat']:.2f}")
            with c3:
                st.write(f"Deger: {r['Hesap. Deger']:.2f}")
            with c4:
                st.write(f"Oran: {r['Oran']:.2f}")
            with c5:
                st.write(f"Kar: %{r['Kar %']:+.1f}")
            with c6:
                st.write(f"Skor: {r['Skor']}")
            with c7:
                st.markdown(f":green[**{r['Oneri']}**]")
        st.divider()
    else:
        st.info("Su an gucel AL onerisi bulunmuyor.")

    # Tablo
    st.markdown("### Tum Sonuclar")
    st.dataframe(pd.DataFrame(filtered), use_container_width=True, height=500)


def _render_value_analysis_table(data: dict):
    st.subheader("Deger Analizi Tablosu")
    st.markdown("**Formul:** `(Piyasa Degeri - Net Borc) x (Fiili Oran / 100) / Fiili Dolasim Hisse`")

    rows = []
    for code, s in data.items():
        cv = s.get("calculated_value", 0) or 0
        if cv > 0:
            rows.append({
                "Kod": code,
                "Sirket": (s.get("company_name", "") or "")[:25],
                "Fiyat (TL)": s.get("last_price", 0) or 0,
                "Piyasa Deg (mn)": s.get("market_cap_mn", 0) or 0,
                "Net Borc (mn)": s.get("net_debt_mn", 0) or 0,
                "F/D (%)": s.get("float_rate", 0) or 0,
                "Fiili Hisse": s.get("floating_shares", 0) or 0,
                "Hesap. Deger (TL)": cv,
                "Oran": s.get("ratio", 0) or 0,
                "Sinyal": s.get("signal", ""),
                "Kar (%)": s.get("expected_return", 0) or 0,
            })

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values("Oran", ascending=True)
        st.dataframe(df, use_container_width=True, height=600)
    else:
        st.warning("Deger analizi yapilacak hisse bulunamadi.")


def _render_top_movers(data: dict):
    col1, col2 = st.columns(2)
    stocks = [s for s in data.values() if s.get("change_pct") is not None]

    with col1:
        st.subheader("En Cok Yukselenler")
        top_up = sorted(stocks, key=lambda x: x.get("change_pct", 0), reverse=True)[:15]
        if top_up:
            rows = [{"Kod": s["stock_code"], "Fiyat": f"{s.get('last_price', 0):.2f}",
                      "Degisim": f"%{s.get('change_pct', 0):+.2f}", "Sinyal": s.get("signal", "")} for s in top_up]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with col2:
        st.subheader("En Cok Dusenler")
        top_down = sorted(stocks, key=lambda x: x.get("change_pct", 0))[:15]
        if top_down:
            rows = [{"Kod": s["stock_code"], "Fiyat": f"{s.get('last_price', 0):.2f}",
                      "Degisim": f"%{s.get('change_pct', 0):+.2f}", "Sinyal": s.get("signal", "")} for s in top_down]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    st.subheader("AL Sinyali Verenler")
    al_stocks = [s for s in data.values() if s.get("signal") in ["AL", "Evi Barki Sat"]]
    if al_stocks:
        rows = [{"Kod": s["stock_code"], "Fiyat": f"{s.get('last_price', 0):.2f}",
                  "Hesap. Deger": f"{s.get('calculated_value', 0):.2f}",
                  "Oran": f"{s.get('ratio', 0):.2f}",
                  "Kar %": f"%{s.get('expected_return', 0):+.1f}",
                  "Sinyal": s.get("signal", "")} for s in
                 sorted(al_stocks, key=lambda x: x.get("expected_return", 0), reverse=True)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.warning("Su an AL sinyali veren hisse bulunmuyor.")


def _render_stock_detail(data: dict):
    st.subheader("Hisse Detay")
    symbols = sorted(list(data.keys()))
    default_idx = symbols.index("THYAO") if "THYAO" in symbols else 0
    selected = st.selectbox("Hisse Secin", symbols, index=default_idx)

    if not selected:
        return

    s = data.get(selected, {})
    if not s:
        st.warning(f"{selected} icin veri bulunamadi")
        return

    st.markdown(f"## {selected} - {s.get('company_name', '')}")
    
    price = s.get('last_price', 0)
    change = s.get('change_pct', 0)
    
    # Ust Bilgi Cubugu - Mynet Benzeri
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Son Fiyat", f"{price:.2f} TL", f"{change:+.2f}%")
    with col2:
        vol = s.get('volume', 0)
        st.metric("Hacim", f"{vol/1e6:,.1f} Mn" if vol > 1e6 else f"{vol:,.0f}")
    with col3:
        st.metric("Hesap. Deger", f"{s.get('calculated_value', 0):.2f} TL")
    with col4:
        st.metric("Oran", f"{s.get('ratio', 0):.2f}")
    with col5:
        st.metric("F/K", f"{s.get('pe', 0):.2f}" if s.get('pe') else "N/A")
    with col6:
        st.metric("PD/DD", f"{s.get('pb', 0):.2f}" if s.get('pb') else "N/A")
    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Temel Bilgiler")
        for k, v in {
            "Piyasa Degeri": f"{s.get('market_cap_mn', 0):,.1f} mn TL",
            "Net Borc": f"{s.get('net_debt_mn', 0):,.1f} mn TL",
            "Fiili Dolasim": f"%{s.get('float_rate', 0)}",
            "Toplam Hisse": f"{s.get('total_shares', 0):,.0f}",
            "Fiili Dolasim Hisse": f"{s.get('floating_shares', 0):,.0f}",
            "Hacim": f"{s.get('volume', 0):,.0f}",
        }.items():
            st.write(f"**{k}:** {v}")

    with col_right:
        st.subheader("Deger Analizi")
        for k, v in {
            "Son Fiyat": f"{s.get('last_price', 0):.2f} TL",
            "Hesaplanan Deger": f"{s.get('calculated_value', 0):.2f} TL",
            "Oran (Fiyat/Deger)": f"{s.get('ratio', 0):.2f}",
            "Kar Beklentisi": f"%{s.get('expected_return', 0):+.1f}",
            "Sinyal": s.get("signal", ""),
        }.items():
            st.write(f"**{k}:** {v}")

    # Grafikler
    period = st.selectbox("Donem", ["6ay", "1y", "2y", "5y"], index=1, key="detail_period")
    history = bist.get_history(selected, period)

    if history is not None and not history.empty:
        close = history["Close"]
        high = history["High"]
        low = history["Low"]

        # Teknik degerler hesapla
        rsi_val = None
        macd_val = None
        sig_val = None
        bb_upper = None
        bb_lower = None
        if len(close) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            rsi_val = rsi_series.iloc[-1]
        if len(close) >= 26:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_val = macd_line.iloc[-1]
            sig_val = signal_line.iloc[-1]
        if len(close) >= 20:
            ma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_upper = (ma20 + 2 * std20).iloc[-1]
            bb_lower = (ma20 - 2 * std20).iloc[-1]
        fib_levels = {}
        if len(high) >= 20:
            max_p = high.max()
            min_p = low.min()
            d = max_p - min_p
            fib_levels = {
                "%23.6": max_p - 0.236 * d,
                "%38.2": max_p - 0.382 * d,
                "%50.0": max_p - 0.500 * d,
                "%61.8": max_p - 0.618 * d,
            }

        # GRAFIK + TABLO YAN YANA
        col_chart, col_table = st.columns([3, 2])

        with col_table:
            st.markdown("### Piyasa Bilgileri")
            import pandas as pd
            
            piyasa = pd.DataFrame({
                "": ["Son Fiyat", "Alis", "Satis", "Gunluk Degisim", "Acilis",
                     "Onceki Kapanis", "Gunluk Hacim (Lot)", "Gunluk Hacim (TL)",
                     "Piyasa Degeri", "Net Borc"],
                "Deger": [
                    f"{price:.2f} TL",
                    f"{s.get('last_price', 0):.2f} TL",
                    f"{s.get('last_price', 0):.2f} TL",
                    f"{change:+.2f}%",
                    f"{price:.2f} TL",
                    f"{s.get('last_price', 0) / (1 + change/100) if change != 0 else price:.2f} TL",
                    f"{s.get('volume', 0):,.0f}",
                    f"{s.get('volume', 0) * price:,.0f} TL",
                    f"{s.get('market_cap_mn', 0):,.1f} mn TL",
                    f"{s.get('net_debt_mn', 0):,.1f} mn TL",
                ]
            })
            st.dataframe(piyasa, use_container_width=True, hide_index=True)

            st.markdown("### Hisse Yapisi")
            hisse = pd.DataFrame({
                "": ["Toplam Hisse", "Fiili Dolasim", "Fiyat Adimi"],
                "Deger": [
                    f"{s.get('total_shares', 0):,.0f}",
                    f"%{s.get('float_rate', 0)}",
                    "0.02 TL",
                ]
            })
            st.dataframe(hisse, use_container_width=True, hide_index=True)

            st.markdown("### Degerleme")
            degerleme = pd.DataFrame({
                "": ["Son Fiyat", "Hesap. Deger", "Oran (F/D)", "Kar Beklentisi",
                     "F/K (PE)", "PD/DD (PB)", "Sinyal"],
                "Deger": [
                    f"{price:.2f} TL",
                    f"{s.get('calculated_value', 0):.2f} TL",
                    f"{s.get('ratio', 0):.2f}",
                    f"%{s.get('expected_return', 0):+.1f}",
                    f"{s.get('pe', 0):.2f}" if s.get('pe') else "N/A",
                    f"{s.get('pb', 0):.2f}" if s.get('pb') else "N/A",
                    s.get("signal", ""),
                ]
            })
            st.dataframe(degerleme, use_container_width=True, hide_index=True)

            st.markdown("### Teknik Degerler")
            teknik = pd.DataFrame({
                "": ["RSI (14)", "MACD", "Signal", "BB Ust", "BB Alt"],
                "Deger": [
                    f"{rsi_val:.1f}" if rsi_val else "N/A",
                    f"{macd_val:.4f}" if macd_val else "N/A",
                    f"{sig_val:.4f}" if sig_val else "N/A",
                    f"{bb_upper:.2f}" if bb_upper else "N/A",
                    f"{bb_lower:.2f}" if bb_lower else "N/A",
                ]
            })
            st.dataframe(teknik, use_container_width=True, hide_index=True)

            if fib_levels:
                st.markdown("### Fibonacci Seviyeleri")
                fib_df = pd.DataFrame({
                    "Seviye": list(fib_levels.keys()),
                    "Fiyat": [f"{v:.2f} TL" for v in fib_levels.values()],
                })
                st.dataframe(fib_df, use_container_width=True, hide_index=True)

        with col_chart:
            # 1. Fiyat Grafigi + MA + Bollinger
            st.subheader("Fiyat + Bollinger + MA")
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=history.index, open=history["Open"], high=history["High"],
                low=history["Low"], close=history["Close"], name="Fiyat"))
            for ma_len, color in [(20, "yellow"), (50, "blue"), (200, "red")]:
                if len(close) >= ma_len:
                    ma = close.rolling(ma_len).mean()
                    fig.add_trace(go.Scatter(x=history.index, y=ma,
                                              name=f"MA{ma_len}", line=dict(color=color, width=1)))
            if len(close) >= 20:
                ma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                fig.add_trace(go.Scatter(x=history.index, y=ma20 + 2 * std20,
                                          name="BB Ust", line=dict(color="cyan", width=1, dash="dash")))
                fig.add_trace(go.Scatter(x=history.index, y=ma20 - 2 * std20,
                                          name="BB Alt", line=dict(color="cyan", width=1, dash="dash"),
                                          fill="tonexty", fillcolor="rgba(0,255,255,0.05)"))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

            # 2. RSI
            if rsi_val:
                st.subheader(f"RSI (14): {rsi_val:.1f}")
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=history.index, y=rsi_series, name="RSI", line=dict(color="purple", width=2)))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
                fig_rsi.add_hline(y=50, line_dash="dot", line_color="gray")
                fig_rsi.update_layout(template="plotly_dark", height=180, yaxis=dict(range=[0, 100]), margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_rsi, use_container_width=True)

            # 3. MACD
            if macd_val:
                st.subheader(f"MACD: {macd_val:.4f}")
                histogram = macd_line - signal_line
                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(x=history.index, y=macd_line, name="MACD", line=dict(color="blue", width=2)))
                fig_macd.add_trace(go.Scatter(x=history.index, y=signal_line, name="Signal", line=dict(color="orange", width=1)))
                colors = ["green" if v >= 0 else "red" for v in histogram]
                fig_macd.add_trace(go.Bar(x=history.index, y=histogram, name="Histogram", marker_color=colors))
                fig_macd.add_hline(y=0, line_color="gray")
                fig_macd.update_layout(template="plotly_dark", height=200, margin=dict(l=0, r=0, t=30, b=0))
                st.plotly_chart(fig_macd, use_container_width=True)

            # 4. Hacim
            st.subheader("Hacim")
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Bar(x=history.index, y=history["Volume"], name="Hacim",
                                      marker_color=["green" if c >= o else "red"
                                                    for c, o in zip(history["Close"], history["Open"])]))
            if len(history["Volume"]) >= 20:
                vol_ma = history["Volume"].rolling(20).mean()
                fig_vol.add_trace(go.Scatter(x=history.index, y=vol_ma, name="20G Ort",
                                              line=dict(color="yellow", width=1)))
            fig_vol.update_layout(template="plotly_dark", height=180, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_vol, use_container_width=True)
    else:
        st.info("Gecmis fiyat verisi alinamadi.")
