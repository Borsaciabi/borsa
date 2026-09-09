import streamlit as st
import requests

from data.fetchers.kap_news_fetcher import KapNewsFetcher
from data.fetchers.pay_tedbirleri_fetcher import PayTedbirleriFetcher


@st.cache_data(ttl=300, max_entries=20)
def load_kap_news(symbol=None):
    return KapNewsFetcher().fetch(symbol=symbol, limit=50 if symbol else 80)


@st.cache_data(ttl=300, max_entries=20)
def load_pay_tedbirleri(symbol=None):
    return PayTedbirleriFetcher().fetch(symbol=symbol)


def refresh_news_sources():
    """Refresh KAP and Halk Yatirim data once when an app session opens."""
    load_kap_news.clear()
    load_pay_tedbirleri.clear()
    load_kap_news()
    load_pay_tedbirleri()


def render_pay_tedbirleri(symbol=None, limit=100):
    title = f"{symbol} Pay Tedbirleri" if symbol else "Aktif Pay Tedbirleri"
    st.subheader(title)
    try:
        measures = load_pay_tedbirleri(symbol)[:limit]
    except (requests.RequestException, ValueError) as exc:
        st.warning(f"Pay tedbirleri yuklenemedi: {exc}")
        return

    if not measures:
        st.info(f"{symbol or 'Piyasa'} icin aktif pay tedbiri bulunmadi.")
        return

    for item in measures:
        remaining = item["days_remaining"]
        remaining_text = f"{remaining} gun kaldi" if remaining is not None else "Kalan gun bilgisi yok"
        with st.container(border=True):
            st.markdown(f"**{item['symbol']}** — **{remaining_text}**")
            st.write(f"Tedbir: {item['message']}")
            st.caption(
                f"Baslangic: {item['start_date']} | Bitis: {item['end_date']}"
            )
    st.link_button("Halk Yatirim pay tedbirleri", PayTedbirleriFetcher.URL)


def render_news(symbol=None, limit=20, title="KAP Haberleri"):
    st.subheader(title)
    st.caption("KAP bildirimi: son 3 gün")
    try:
        news = load_kap_news(symbol)[:limit]
    except (requests.RequestException, ValueError) as exc:
        st.warning(f"KAP haberleri yuklenemedi: {exc}")
        return

    if not news:
        st.info(f"{symbol or 'Piyasa'} icin KAP haberi bulunamadi.")
    else:
        for item in news:
            heading = item["title"]
            if item["stock_codes"]:
                heading = f'{heading} ({item["stock_codes"]})'
            with st.expander(f'{item["publish_date"]} - {heading}'):
                if item["company"]:
                    st.write(f"**Sirket:** {item['company']}")
                if item["subject"]:
                    st.write(f"**Konu:** {item["subject"]}")
                st.link_button("KAP bildirimini ac", item["url"])

    st.divider()
    render_pay_tedbirleri(symbol=symbol)
