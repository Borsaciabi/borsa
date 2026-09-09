import streamlit as st
import requests
import pandas as pd
from web.ui_styles import render_signed_dataframe

API_URL = "http://localhost:8000"


def _get_user_id():
    user = st.session_state.get("user")
    if user:
        return user.get("id")
    return None


def _auth_headers():
    token = st.session_state.get("auth_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get_prices_fast():
    """Cache'den veya mynet'ten hizli fiyat cek."""
    prices = {}

    # Once session cache'den dene
    cached = st.session_state.get("portfolio_prices", {})
    if cached:
        return cached

    # Sonra dashboard cache'den dene
    stock_data = st.session_state.get("stock_data", {})
    for code, s in stock_data.items():
        p = s.get("last_price", 0)
        if p and p > 0:
            prices[code] = p

    if prices:
        st.session_state.portfolio_prices = prices

    return prices


def _get_daily_changes():
    """Portfoy hisseleri icin piyasa verisindeki gunluk degisim oranlarini al."""
    changes = st.session_state.get("portfolio_changes", {}).copy()
    stock_data = st.session_state.get("stock_data", {})
    for code, stock in stock_data.items():
        change = stock.get("change_pct")
        if change is not None:
            try:
                changes[code] = float(change)
            except (TypeError, ValueError):
                continue
    return changes


def _refresh_prices():
    """Mynet'ten tum fiyatlari cek."""
    try:
        from data.fetchers.mynet_fetcher import MynetFetcher
        mynet = MynetFetcher()
        all_stocks = mynet.fetch_all()
        prices = {}
        changes = {}
        for s in all_stocks:
            prices[s["stock_code"]] = s["last_price"]
            if s.get("change_pct") is not None:
                changes[s["stock_code"]] = s["change_pct"]
        st.session_state.portfolio_prices = prices
        st.session_state.portfolio_changes = changes
        return prices
    except Exception as e:
        st.warning(f"Fiyat guncellenemedi: {e}")
        return {}


def render_portfolio():
    st.title("Portfoy Yonetimi")
    if not st.session_state.get("user"):
        st.info("Kendi portfoyunuzu görmek ve oluşturmak için önce giriş yapın.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["Portfoyum", "Alis Kaydi", "Satis Kaydi", "Excel Aktarim"])

    with tab1:
        _show_portfolio()

    with tab2:
        _buy_form()

    with tab3:
        _sell_form()

    with tab4:
        _import_excel()


def _show_portfolio():
    try:
        resp = requests.get(
            f"{API_URL}/api/portfolio",
            headers=_auth_headers(),
            timeout=5,
        )
        if resp.status_code != 200:
            st.info("Portfoy bos veya API baglantisi kurulamadi.")
            return

        data = resp.json()
        positions = data.get("positions", [])

        if not positions:
            st.info("Henuz portfoyde hisse bulunmuyor.")
            return

        # Ust bilgi ve butonlar
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.write(f"**{len(positions)} hisse** portfoyde")
        with col2:
            if st.button("Fiyatlari Guncelle", type="primary", key="btn_refresh"):
                _refresh_prices()
                st.rerun()
        with col3:
            if st.button("Tum Portfoy Sil", type="secondary", key="btn_delete_all"):
                st.session_state["confirm_delete_all"] = True
                st.rerun()

        # Silme onayi
        if st.session_state.get("confirm_delete_all"):
            st.warning("Tum portfoy silinecek! Emin misiniz?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Evet, Sil", type="primary", key="btn_confirm_del"):
                    try:
                        r = requests.delete(
                            f"{API_URL}/api/portfolio/all",
                            headers=_auth_headers(),
                            timeout=5,
                        )
                        if r.status_code == 200:
                            st.success("Tum portfoy silindi!")
                            st.session_state["confirm_delete_all"] = False
                            st.rerun()
                        else:
                            st.error(r.json().get("detail", "Silinemedi"))
                    except Exception as e:
                        st.warning(f"Hata: {e}")
            with c2:
                if st.button("Iptal", key="btn_cancel_del"):
                    st.session_state["confirm_delete_all"] = False
                    st.rerun()

        # Fiyatlari al
        prices = _get_prices_fast()
        daily_changes = _get_daily_changes()
        position_by_code = {pos["stock_code"]: pos for pos in positions}

        selected_codes = st.multiselect(
            "Hisseleri secin",
            options=list(position_by_code),
            format_func=lambda code: f"{code} ({position_by_code[code]['net_quantity']} adet)",
            key="portfolio_selected_codes",
            help="Secilen hisseleri tek seferde silebilir veya mevcut fiyatla tamamen satabilirsiniz.",
        )
        if selected_codes:
            action_col, sell_date_col, fee_col = st.columns([1.4, 1.2, 1])
            with action_col:
                action = st.selectbox(
                    "Toplu islem",
                    ["Secilenleri sil", "Secilenleri tamamen sat"],
                    key="portfolio_bulk_action",
                )
            with sell_date_col:
                bulk_sell_date = st.date_input("Satis tarihi", key="portfolio_bulk_sell_date")
            with fee_col:
                bulk_fees = st.number_input(
                    "Hisse basi komisyon (TL)",
                    min_value=0.0,
                    step=0.01,
                    key="portfolio_bulk_fees",
                )
            delete_confirmed = True
            if action == "Secilenleri sil":
                delete_confirmed = st.checkbox(
                    "Secilen hisselerin tum islem kayitlarini silmeyi onayliyorum",
                    key="portfolio_delete_confirmed",
                )
            if st.button("Secilenlere uygula", type="primary", key="portfolio_bulk_apply"):
                if action == "Secilenleri sil":
                    if not delete_confirmed:
                        st.warning("Silme islemi icin onay kutusunu isaretleyin.")
                        return
                    _delete_selected_stocks(selected_codes)
                else:
                    _sell_selected_stocks(
                        selected_codes,
                        position_by_code,
                        prices,
                        bulk_sell_date,
                        bulk_fees,
                    )
                st.rerun()

        # Tablo
        rows = []
        toplam_deger = 0
        toplam_maliyet = 0

        for pos in positions:
            symbol = pos["stock_code"]
            qty = pos["net_quantity"]
            avg_price = pos["avg_buy_price"]

            current_price = prices.get(symbol, avg_price)
            if not current_price or current_price <= 0:
                current_price = avg_price

            deger = current_price * qty
            maliyet = avg_price * qty
            kar = deger - maliyet
            kar_pct = ((current_price / avg_price) - 1) * 100 if avg_price > 0 else 0

            toplam_deger += deger
            toplam_maliyet += maliyet

            rows.append({
                "Hisse": symbol,
                "Miktar": qty,
                "Ort. Alis": f"{avg_price:.2f}",
                "Guncel Fiyat": f"{current_price:.2f}",
                "Gunluk Degisim": f"%{daily_changes.get(symbol, 0):+.2f}",
                "Deger": f"{deger:,.2f}",
                "Kar/Zarar": f"{kar:+,.2f}",
                "Kar %": f"%{kar_pct:+.1f}",
            })

        render_signed_dataframe(
            pd.DataFrame(rows),
            ["Gunluk Degisim", "Kar/Zarar", "Kar %"],
            width="stretch",
        )

        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Deger", f"{toplam_deger:,.2f} TL")
        with col2:
            st.metric("Toplam Maliyet", f"{toplam_maliyet:,.2f} TL")
        with col3:
            toplam_kar = toplam_deger - toplam_maliyet
            st.metric("Toplam Kar/Zarar", f"{toplam_kar:+,.2f} TL")

    except Exception as e:
        st.warning(f"Portfoy yuklenemedi: {e}")


def _delete_selected_stocks(stock_codes):
    try:
        failures = []
        for code in stock_codes:
            response = requests.delete(
                f"{API_URL}/api/portfolio/{code}",
                headers=_auth_headers(),
                timeout=5,
            )
            if response.status_code != 200:
                failures.append(response.json().get("detail", code))
        if failures:
            st.error(f"Silinemeyen hisseler: {', '.join(failures)}")
        else:
            st.success(f"{len(stock_codes)} hisse portfoyden silindi.")
    except Exception as exc:
        st.warning(f"Toplu silme basarisiz: {exc}")


def _sell_selected_stocks(selected_codes, positions, prices, sell_date, fees):
    sell_prices = {}
    for code in selected_codes:
        price = prices.get(code) or positions[code].get("avg_buy_price", 0)
        if not price or price <= 0:
            st.error(f"{code} icin satis fiyati bulunamadi.")
            return
        sell_prices[code] = price
    try:
        response = requests.post(
            f"{API_URL}/api/portfolio/sell-many",
            json={
                "stock_codes": selected_codes,
                "sell_date": str(sell_date),
                "sell_prices": sell_prices,
                "fees": fees,
            },
            headers=_auth_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            st.success(response.json()["message"])
        else:
            st.error(response.json().get("detail", "Toplu satis basarisiz"))
    except Exception as exc:
        st.warning(f"Toplu satis basarisiz: {exc}")


def _buy_form():
    st.subheader("Hisse Alis Kaydi")
    stock_code = st.text_input("Hisse Kodu", key="buy_code")
    buy_date = st.date_input("Alis Tarihi", key="buy_date")
    buy_price = st.number_input("Alis Fiyati (TL)", min_value=0.0, step=0.01, key="buy_price")
    quantity = st.number_input("Miktar", min_value=1, step=1, key="buy_qty")
    fees = st.number_input("Komisyon (TL)", min_value=0.0, step=0.01, key="buy_fees")
    notes = st.text_input("Notlar", key="buy_notes")

    if st.button("Alis Kaydet", type="primary"):
        try:
            resp = requests.post(
                f"{API_URL}/api/portfolio/buy",
                json={
                    "stock_code": stock_code,
                    "buy_date": str(buy_date),
                    "buy_price": buy_price,
                    "quantity": quantity,
                    "fees": fees,
                    "notes": notes,
                },
                headers=_auth_headers(),
                timeout=5,
            )
            if resp.status_code == 200:
                st.success(resp.json()["message"])
            else:
                st.error(resp.json().get("detail", "Kayit basarisiz"))
        except Exception as e:
            st.warning(f"API baglantisi kurulamadi: {e}")


def _sell_form():
    st.subheader("Hisse Satis Kaydi")
    stock_code = st.text_input("Hisse Kodu", key="sell_code")
    sell_date = st.date_input("Satis Tarihi", key="sell_date")
    sell_price = st.number_input("Satis Fiyati (TL)", min_value=0.0, step=0.01, key="sell_price")
    quantity = st.number_input("Miktar", min_value=1, step=1, key="sell_qty")
    fees = st.number_input("Komisyon (TL)", min_value=0.0, step=0.01, key="sell_fees")

    if st.button("Satis Kaydet", type="primary"):
        try:
            resp = requests.post(
                f"{API_URL}/api/portfolio/sell",
                json={
                    "stock_code": stock_code,
                    "sell_date": str(sell_date),
                    "sell_price": sell_price,
                    "quantity": quantity,
                    "fees": fees,
                },
                headers=_auth_headers(),
                timeout=5,
            )
            if resp.status_code == 200:
                st.success(resp.json()["message"])
            else:
                st.error(resp.json().get("detail", "Kayit basarisiz"))
        except Exception as e:
            st.warning(f"API baglantisi kurulamadi: {e}")


def _import_excel():
    st.subheader("Excel/CSV'den Portfoy Aktar")
    st.markdown("""
    **Beklenen sutunlar:**
    - `hisse` (zorunlu): Hisse kodu (orn: THYAO)
    - `alis_fiyati` (istege bagli): Alis fiyati
    - `miktar` (istege bagli): Hisse adedi
    """)

    uploaded_file = st.file_uploader(
        "Excel veya CSV dosyasi yukleyin",
        type=["xlsx", "xls", "csv"],
        key="import_file",
    )

    if uploaded_file and st.button("Aktar", type="primary"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
        try:
            resp = requests.post(
                f"{API_URL}/api/portfolio/import-excel",
                files=files,
                headers=_auth_headers(),
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                st.success(data["message"])
                if data.get("records"):
                    st.dataframe(pd.DataFrame(data["records"]), use_container_width=True)
            else:
                st.error(resp.json().get("detail", "Aktarim basarisiz"))
        except Exception as e:
            st.warning(f"API baglantisi kurulamadi: {e}")
