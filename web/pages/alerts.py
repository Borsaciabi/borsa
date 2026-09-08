import streamlit as st
import requests

API_URL = "http://localhost:8000"

ALERT_TYPE_MAP = {
    "Fiyat Uzerinde": "PRICE_ABOVE",
    "Fiyat Altinda": "PRICE_BELOW",
    "Hacim Ykselis": "VOLUME_SPIKE",
    "RSI Asiri Satim": "RSI_OVERSOLD",
    "RSI Asiri Alim": "RSI_OVERBOUGHT",
}

ALERT_TYPE_REVERSE = {v: k for k, v in ALERT_TYPE_MAP.items()}


def _get_user_id():
    user = st.session_state.get("user")
    if user:
        return user.get("id")
    return None


def _auth_headers():
    token = st.session_state.get("auth_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def render_alerts():
    st.title("Alarm Yonetimi")
    if not st.session_state.get("user"):
        st.info("Kendi alarmlarınızı görmek ve oluşturmak için önce giriş yapın.")
        return

    tab1, tab2 = st.tabs(["Aktif Alarmlar", "Yeni Alarm Kur"])

    with tab1:
        _show_alerts()

    with tab2:
        _create_alert()


def _show_alerts():
    user_id = _get_user_id()
    try:
        resp = requests.get(
            f"{API_URL}/api/alerts",
            headers=_auth_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            alerts = resp.json()
            if alerts:
                for alert in alerts:
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                    with col1:
                        st.write(f"**{alert['stock_code']}**")
                    with col2:
                        tr_type = ALERT_TYPE_REVERSE.get(alert["alert_type"], alert["alert_type"])
                        st.write(f"{tr_type}: {alert['target_value']}")
                    with col3:
                        status = "Tetiklendi" if alert["triggered"] else "Aktif"
                        st.write(status)
                    with col4:
                        if st.button("Sil", key=f"del_{alert['id']}"):
                            requests.delete(
                                f"{API_URL}/api/alerts/{alert['id']}",
                                headers=_auth_headers(),
                            )
                            st.rerun()
                    st.divider()
            else:
                st.info("Henuz alarm bulunmuyor.")
        else:
            st.info("Alarm sistemi hazir.")
    except Exception as e:
        st.warning(f"Alarm listesi yuklenemedi: {e}")


def _create_alert():
    user_id = _get_user_id()
    st.subheader("Yeni Alarm Kur")
    stock_code = st.text_input("Hisse Kodu", key="alert_code")
    alert_type_tr = st.selectbox("Alarm Turu", list(ALERT_TYPE_MAP.keys()))
    alert_type = ALERT_TYPE_MAP[alert_type_tr]
    target_value = st.number_input("Hedef Deger", min_value=0.0, step=0.01, key="alert_target")

    if st.button("Alarm Kur", type="primary"):
        try:
            resp = requests.post(
                f"{API_URL}/api/alerts",
                json={
                    "stock_code": stock_code,
                    "alert_type": alert_type,
                    "target_value": target_value,
                },
                headers=_auth_headers(),
                timeout=10,
            )
            if resp.status_code == 200:
                st.success(resp.json()["message"])
            else:
                st.error(resp.json().get("detail", "Alarm kurulamadi"))
        except Exception as e:
            st.warning(f"API baglantisi kurulamadi: {e}")
