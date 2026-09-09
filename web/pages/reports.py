import streamlit as st
import requests
import pandas as pd
from config.constants import BIST_100, BIST_30
from data.cache.preloader import DataPreloader
from data.database.db_manager import DBManager

API_URL = "http://localhost:8000"


def _number_or_zero(value):
    """Normalize nullable database values before comparisons and formatting."""
    if value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _format_report_value(value):
    value = _number_or_zero(value)
    return f"{value:,.1f}" if value else "-"


def _signed_report_style(value):
    try:
        numeric = float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return ""
    if numeric > 0:
        return "color: #7ef2b5; background-color: rgba(22, 163, 74, .16); font-weight: 600"
    if numeric < 0:
        return "color: #ff9aa8; background-color: rgba(220, 38, 38, .16); font-weight: 600"
    return "color: #b5c2d0"


def render_reports():
    st.title("Rapor Merkezi")
    st.caption("Hisse raporlari, degerleme ciktilari ve veri kalitesini tek yerden yonetin.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Hisse Raporu", "Deger Analizi Excel", "Gunluk Piyasa", "Veri Durumu"
    ])

    with tab1:
        _stock_report()

    with tab2:
        _value_excel()

    with tab3:
        _daily_report()

    with tab4:
        _data_status_report()


def _stock_report():
    st.subheader("Tekil Hisse PDF Raporu")
    symbol = st.selectbox("Hisse Secin", BIST_100, key="rpt_stock")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("PDF Rapor Indir", type="primary", key="btn_pdf"):
            try:
                resp = requests.get(f"{API_URL}/api/reports/stock/{symbol}/pdf", timeout=30)
                if resp.status_code == 200:
                    st.download_button(
                        label="PDF Indir",
                        data=resp.content,
                        file_name=f"{symbol}_rapor.pdf",
                        mime="application/pdf",
                    )
                    st.success("PDF olusturuldu!")
                else:
                    st.error("PDF olusturulamadi")
            except Exception as e:
                st.warning(f"Rapor olusturulamadi: {e}")

    with col2:
        if st.button("Excel Rapor Indir", type="primary", key="btn_excel"):
            try:
                resp = requests.get(f"{API_URL}/api/reports/stock/{symbol}/excel", timeout=30)
                if resp.status_code == 200:
                    st.download_button(
                        label="Excel Indir",
                        data=resp.content,
                        file_name=f"{symbol}_analiz.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    st.success("Excel olusturuldu!")
                else:
                    st.error("Excel olusturulamadi")
            except Exception as e:
                st.warning(f"Rapor olusturulamadi: {e}")


def _value_excel():
    st.subheader("Coklu Deger Analizi Excel")
    symbols = st.multiselect(
        "Hisse Secin",
        BIST_100,
        default=["THYAO", "GARAN", "AKBNK"],
        key="rpt_multi",
    )

    if st.button("Excel Rapor Olustur", type="primary", key="btn_multi_excel"):
        if len(symbols) < 1:
            st.warning("En az 1 hisse secin")
            return

        symbol_str = ",".join(symbols)
        try:
            resp = requests.get(
                f"{API_URL}/api/reports/value/excel",
                params={"symbols": symbol_str},
                timeout=30,
            )
            if resp.status_code == 200:
                st.download_button(
                    label="Excel Indir",
                    data=resp.content,
                    file_name="deger_analizi.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.success("Excel olusturuldu!")
            else:
                st.error("Excel olusturulamadi")
        except Exception as e:
            st.warning(f"Rapor olusturulamadi: {e}")


def _daily_report():
    st.subheader("Gunluk Piyasa Raporu (PDF)")
    st.write("BIST'teki onemli hisseler icin gunluk analiz raporu.")

    if st.button("Gunluk Rapor Olustur", type="primary", key="btn_daily"):
        try:
            resp = requests.get(f"{API_URL}/api/reports/daily/pdf", timeout=60)
            if resp.status_code == 200:
                st.download_button(
                    label="PDF Indir",
                    data=resp.content,
                    file_name="gunluk_piyasa_raporu.pdf",
                    mime="application/pdf",
                )
                st.success("Gunluk rapor olusturuldu!")
            else:
                st.error("Rapor olusturulamadi")
        except Exception as e:
            st.warning(f"Rapor olusturulamadi: {e}")


def _data_status_report():
    user = st.session_state.get("user")
    if not isinstance(user, dict) or user.get("role") != "admin":
        st.warning("Veri durumu ve veri kaynaklari sadece admin kullanicilara aciktir.")
        return

    st.subheader("Veritabani Veri Durumu")
    st.caption("Bu ekran stock_master ve stock_market_data tablolarindaki kayitlari gosterir.")
    if st.button("Veri Durumunu Guncelle", type="primary", key="refresh_data_status"):
        with st.spinner("Veritabani ve cache verileri yenileniyor..."):
            loader = DataPreloader()
            fresh_data = loader.load_all()
            if fresh_data:
                st.session_state.stock_data = fresh_data
                st.session_state.cache_time = loader.get_cache_time()
        st.rerun()

    db_rows = DBManager().get_all_stock_market_data()
    if not db_rows:
        st.info("Veritabaninda piyasa verisi bulunmuyor. Veri Durumunu Guncelle butonunu kullanin.")
        return

    # stock_master may still contain the original seeded BIST list. The
    # current market universe is the KAP fiili dolasim set, identified by its
    # persisted floating-share data.
    data = {}
    for row in db_rows:
        if not row.get("symbol"):
            continue
        if (row.get("floating_shares") or 0) <= 0 or (row.get("float_rate") or 0) <= 0:
            continue
        current = data.get(row["symbol"])
        row_score = sum(
            row.get(field) is not None
            for field in ("total_equity", "paid_in_capital", "net_income", "financial_period")
        )
        current_score = sum(
            current.get(field) is not None
            for field in ("total_equity", "paid_in_capital", "net_income", "financial_period")
        ) if current else -1
        if current is None or row_score > current_score:
            data[row["symbol"]] = row
    report_rows = list(data.values())
    total = len(report_rows)

    cache_time = st.session_state.get("cache_time", "Veritabani kaydi")
    st.info(f"Son cache guncelleme: {cache_time} | KAP fiili dolasim hissesi: {total}")
    if len(db_rows) != total:
        st.caption(
            f"Stock master tablosunda {len(db_rows)} kayit bulunuyor; "
            "rapor sayisi yalnizca KAP fiili dolasim verisi bulunan hisseleri kapsar."
        )
    db = DBManager()
    tables = db.get_database_tables()
    if tables:
        selected_table = st.selectbox(
            "Veritabani tablosu",
            tables,
            key="admin_database_table",
            help="Secilen tablonun ilk 200 satiri admin kullanicilara gosterilir.",
        )
        table_rows = db.get_table_rows(selected_table, limit=200)
        st.caption(f"{selected_table}: {len(table_rows)} satir gosteriliyor (en fazla 200)")
        if table_rows:
            st.dataframe(pd.DataFrame(table_rows), hide_index=True)
        else:
            st.info("Bu tabloda henuz kayit bulunmuyor.")

    latest_recorded = max(
        (row.get("recorded_at") or "" for row in report_rows),
        default="Bilinmiyor",
    )
    source_time = f"Son veritabani kaydi: {latest_recorded}"

    # Ozet istatistikler
    has_price = sum(1 for s in report_rows if (s.get("last_price") or 0) > 0)
    has_mcap = sum(1 for s in report_rows if (s.get("market_cap") or 0) > 0)
    has_ndebt = sum(1 for s in report_rows if s.get("net_debt") is not None)
    has_float = sum(1 for s in report_rows if (s.get("floating_shares") or 0) > 0)
    has_analysis = sum(1 for s in report_rows if (s.get("calculated_value") or 0) > 0)
    has_signal = sum(
        1 for s in report_rows
        if s.get("signal") and s["signal"] not in ["Veri Yetersiz", "Deger Giriniz"]
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Fiyat Verisi", f"{has_price} / {total}",
            help=f"Kaynak: Mynet. {source_time}",
        )
    with col2:
        st.metric(
            "Piyasa Degeri", f"{has_mcap} / {total}",
            help=f"Kaynak: isyatirimhisse / Is Yatirim. {source_time}",
        )
    with col3:
        st.metric(
            "Deger Analizi", f"{has_analysis} / {total}",
            help=f"Kaynak: sistem hesaplamasi; girdiler KAP + Is Yatirim + Mynet. {source_time}",
        )

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric(
            "Net Borc", f"{has_ndebt} / {total}",
            help=f"Kaynak: isyatirimhisse finansal tablolar veya Is Yatirim sirket verisi. {source_time}",
        )
    with col5:
        st.metric(
            "Fiili Dolasim (KAP)", f"{has_float} / {total}",
            help=f"Kaynak: KAP fiili dolasim paylari. https://kap.org.tr/tr/tumKalemler/kpy41_acc5_fiili_dolasimdaki_pay. {source_time}",
        )
    with col6:
        st.metric(
            "Sinyal Uretmis", f"{has_signal} / {total}",
            help=f"Kaynak: sistem hesaplamasi; son fiyat / hesaplanan deger oranindan uretilir. {source_time}",
        )

    col7, col8, col9 = st.columns(3)
    with col7:
        has_total_shares = sum(1 for s in report_rows if (s.get("total_shares") or 0) > 0)
        st.metric(
            "Toplam Hisse", f"{has_total_shares} / {total}",
            help=f"Kaynak: KAP fiili dolasim verisi ve isyatirimhisse sermaye verisi. {source_time}",
        )
    with col8:
        has_volume = sum(1 for s in report_rows if (s.get("volume") or 0) > 0)
        st.metric(
            "Hacim Verisi", f"{has_volume} / {total}",
            help=f"Kaynak: Mynet fiyat veri servisi. {source_time}",
        )
    with col9:
        has_valuation = sum(1 for s in report_rows if s.get("pe") is not None or s.get("pb") is not None)
        st.metric(
            "F/K veya PD/DD", f"{has_valuation} / {total}",
            help=f"Kaynak: isyatirimhisse / Is Yatirim finansal verileri. {source_time}",
        )

    st.divider()

    # Filtre
    filter_options = [
        "Tumu",
        "Sadece Deger Analizi Olanlar",
        "Sadece Eksik Verili Olanlar",
        "Sadece Fiyat Verisi Olanlar",
        "Sadece Piyasa Degeri Olanlar",
        "Sadece Net Borc Olanlar",
        "Sadece AL Sinyali",
        "Sadece SAT Sinyali",
        "Sadece Kafana Gore",
        "BIST 30",
        "BIST 100",
    ]
    filter_choice = st.selectbox("Filtre", filter_options, key="data_status_filter")

    # Tablo
    rows = []
    for code, s in data.items():
        price = _number_or_zero(s.get("last_price"))
        mcap = _number_or_zero(s.get("market_cap")) / 1_000_000
        raw_ndebt = s.get("net_debt")
        ndebt = _number_or_zero(raw_ndebt) / 1_000_000 if raw_ndebt is not None else None
        frate = _number_or_zero(s.get("float_rate"))
        fshares = _number_or_zero(s.get("floating_shares"))
        volume = _number_or_zero(s.get("volume"))
        total_shares = _number_or_zero(s.get("total_shares"))
        change_pct = _number_or_zero(s.get("change_pct"))
        calc_val = _number_or_zero(s.get("calculated_value"))
        signal = s.get("signal", "")
        pe = s.get("pe")
        pb = s.get("pb")

        has_p = price > 0
        has_m = mcap > 0
        has_n = ndebt is not None
        has_f = fshares > 0
        has_c = calc_val > 0
        has_s = signal not in ["", "Veri Yetersiz", "Deger Giriniz"]

        # Filtre
        if filter_choice == "Sadece Deger Analizi Olanlar" and not has_c:
            continue
        elif filter_choice == "Sadece Eksik Verili Olanlar" and (has_p and has_m and has_f):
            continue
        elif filter_choice == "Sadece Fiyat Verisi Olanlar" and not has_p:
            continue
        elif filter_choice == "Sadece Piyasa Degeri Olanlar" and not has_m:
            continue
        elif filter_choice == "Sadece Net Borc Olanlar" and not has_n:
            continue
        elif filter_choice == "Sadece AL Sinyali" and signal != "AL":
            continue
        elif filter_choice == "Sadece SAT Sinyali" and signal != "SAT":
            continue
        elif filter_choice == "Sadece Kafana Gore" and signal != "Kafana Gore":
            continue
        elif filter_choice == "BIST 30" and code not in BIST_30:
            continue
        elif filter_choice == "BIST 100" and code not in BIST_100:
            continue

        rows.append({
            "Kod": code,
            "Sirket": (s.get("company_name", "") or "")[:30],
            "Fiyat (TL)": f"{price:.2f}" if has_p else "-",
            "Degisim (%)": f"{change_pct:+.2f}" if has_p else "-",
            "Yon": "▲" if s.get('change_direction') == 'up' else ("▼" if s.get('change_direction') == 'down' else "-"),
            "Hacim (TL)": f"{volume:,.0f}" if volume > 0 else "-",
            "Piyasa Degeri (mn)": f"{mcap:,.1f}" if has_m else "-",
            "Net Borc (mn)": f"{ndebt:,.1f}" if has_n else "-",
            "Toplam Hisse": f"{total_shares:,.0f}" if total_shares > 0 else "-",
            "Ozkaynaklar": _format_report_value(s.get("total_equity")),
            "Odenmis Sermaye": _format_report_value(s.get("paid_in_capital")),
            "Net Kar": _format_report_value(s.get("net_income")),
            "Bilanco Donemi": s.get("financial_period") or "-",
            "Fiili Dolasim (%)": f"{frate:.2f}" if has_f else "-",
            "Fiili Hisse": f"{fshares:,.0f}" if has_f else "-",
            "F/K (PE)": f"{pe:.2f}" if pe else "-",
            "PD/DD (PB)": f"{pb:.4f}" if pb else "-",
            "Hesap. Deger (TL)": f"{calc_val:.2f}" if has_c else "-",
            "Oran (Fiyat/Deger)": f"{s.get('ratio', 0):.4f}" if has_c else "-",
            "Kar Beklentisi (%)": f"{s.get('expected_return', 0):+.2f}" if has_c else "-",
            "Sinyal": signal if has_s else "-",
            "Veri Kaynagi": s.get("source") or "Kayit yok",
            "Veri Zamanı": s.get("recorded_at") or "-",
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(
            df.style.map(_signed_report_style, subset=[
                "Degisim (%)", "Net Borc (mn)", "Net Kar", "Kar Beklentisi (%)"
            ]),
            use_container_width=True,
            height=600,
            column_config={
                "Veri Kaynagi": st.column_config.TextColumn(
                    "Veri Kaynagi",
                    help="Bu satirin veritabanina yazildigi kaynak. Uzerine gelerek aciklamayi gorebilirsiniz.",
                ),
                "Veri Zamanı": st.column_config.TextColumn(
                    "Veri Zamanı",
                    help="Verinin veritabanina son yazilma zamani.",
                ),
            },
        )
        st.info(f"{len(rows)} hisse gosteriliyor")

        # Excel'e indir
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tum Hisseler')
            ws = writer.sheets['Tum Hisseler']
            # Kolon genislikleri
            for col_idx, col in enumerate(df.columns, 1):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                ws.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else 'A' + chr(64 + col_idx - 26)].width = min(max_len, 25)
        st.download_button(
            label="Tum Verileri Excel'e Indir",
            data=output.getvalue(),
            file_name="tum_veriler.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("Filtreye uygun hisse bulunamadi.")
