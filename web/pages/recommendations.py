import pandas as pd
import requests
import streamlit as st

from data.fetchers.model_portfolio_fetcher import ModelPortfolioFetcher, rank_common_recommendations


@st.cache_data(ttl=900, max_entries=2)
def load_model_portfolios():
    return ModelPortfolioFetcher().fetch_all()


def render_recommendations():
    st.title("Öneri Sistemi")
    st.caption("Model portföy ve analist tavsiyeleri kaynaklarının ortak sembol sıralaması")
    try:
        sources = load_model_portfolios()
    except (requests.RequestException, ValueError) as exc:
        st.error(f"Öneri kaynakları yüklenemedi: {exc}")
        return

    ranked = rank_common_recommendations(sources)
    common_symbols = ", ".join(item["symbol"] for item in ranked if item["source_count"] >= 2)
    rows = []
    for source in sources:
        rows.append({
            "Kaynak": source["source"],
            "Önerilen Hisse": len(source["records"]),
            "Hisseler": ", ".join(item["symbol"] for item in source["records"]),
            "Son Güncelleme": source["updated_at"],
            "Durum": "Aktif" if source["available"] else "Erişilemedi",
            "Bağlantı": source["url"],
            "Ortak Önerilenler": common_symbols or "Henüz ortak sembol yok",
        })
    st.subheader("Kaynaklar")
    st.dataframe(
        pd.DataFrame(rows),
        column_config={"Bağlantı": st.column_config.LinkColumn()},
        hide_index=True,
        width="stretch",
    )

    if not ranked:
        st.warning("Kaynaklardan hisse önerisi alınamadı.")
        return
    st.subheader("Ortak önerilen hisseler")
    st.caption("Sıralama, erişilebilen kaynakların kaçında yer aldığına göre yapılır.")
    available_count = sum(source["available"] for source in sources)
    frame = pd.DataFrame(ranked)
    frame["Kaynak Sayısı"] = frame.pop("source_count").map(lambda value: f"{value}/{available_count}")
    frame = frame.rename(columns={"symbol": "Hisse"})
    frame["Ortak öneri sırası"] = range(1, len(frame) + 1)
    frame = frame[["Ortak öneri sırası", "Hisse", "Kaynak Sayısı"]]
    st.dataframe(frame, hide_index=True, width="stretch")
