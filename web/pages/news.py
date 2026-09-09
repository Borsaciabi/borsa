import streamlit as st
import requests

from data.fetchers.kap_news_fetcher import KapNewsFetcher


@st.cache_data(ttl=300, max_entries=20)
def load_kap_news(symbol=None):
    return KapNewsFetcher().fetch(symbol=symbol, limit=50 if symbol else 80)


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
        return

    for item in news:
        heading = item["title"]
        if item["stock_codes"]:
            heading = f'{heading} ({item["stock_codes"]})'
        with st.expander(f'{item["publish_date"]} - {heading}'):
            if item["company"]:
                st.write(f"**Sirket:** {item['company']}")
            if item["subject"]:
                st.write(f"**Konu:** {item['subject']}")
            st.link_button("KAP bildirimini ac", item["url"])
