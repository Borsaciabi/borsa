import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"


def _render_all_portfolios(headers):
    st.subheader("Kullanici Portfoyleri")
    try:
        response = requests.get(
            f"{API_URL}/api/portfolio/admin/all",
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200:
            st.error(response.json().get("detail", "Portfoyler alinamadi."))
            return
        portfolios = response.json().get("portfolios", [])
        for portfolio in portfolios:
            positions = portfolio.get("positions", [])
            with st.expander(f"{portfolio['username']} ({len(positions)} pozisyon)"):
                if positions:
                    st.dataframe(pd.DataFrame(positions), use_container_width=True)
                else:
                    st.info("Bu kullanicinin aktif portfoyu bos.")
    except requests.RequestException as exc:
        st.error(f"Portfoy API hatasi: {exc}")


def render_admin_panel():
    st.title("Admin Paneli - Kullanici Yonetimi")
    token = st.session_state.get("auth_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Istatistikler
    try:
        stats_resp = requests.get(f"{API_URL}/api/auth/admin/stats", headers=headers, timeout=10)
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Kullanici", stats["total_users"])
            with col2:
                st.metric("Aktif Kullanici", stats["active_users"])
            with col3:
                st.metric("Admin Sayisi", stats["admin_users"])
    except Exception:
        pass

    st.divider()
    _render_all_portfolios(headers)
    st.divider()

    # Kullanici listesi
    try:
        resp = requests.get(f"{API_URL}/api/auth/admin/users", headers=headers, timeout=10)
        if resp.status_code == 200:
            users = resp.json()["users"]
            if users:
                st.subheader("Tum Kullanicilar")

                rows = []
                for u in users:
                    rows.append({
                        "ID": u["id"],
                        "Kullanici Adi": u["username"],
                        "E-posta": u.get("email", ""),
                        "Rol": u.get("role", "user"),
                        "Durum": "Aktif" if u.get("is_active") else "Pasif",
                        "Telegram": u.get("telegram_username", "-"),
                        "Kayit": u.get("created_at", "")[:10],
                        "Son Giris": (u.get("last_login") or "-")[:16],
                    })

                df = pd.DataFrame(rows)

                def highlight_role(val):
                    if val == "admin":
                        return "background-color: #d4edda; font-weight: bold"
                    return ""

                def highlight_status(val):
                    if val == "Pasif":
                        return "background-color: #f8d7da"
                    return ""

                styled = df.style.map(highlight_role, subset=["Rol"]).map(highlight_status, subset=["Durum"])
                st.dataframe(styled, use_container_width=True, height=400)

                st.divider()

                # Kullanici islemleri
                st.subheader("Kullanici Islemi")
                user_options = {u["username"]: u["id"] for u in users}
                selected_user = st.selectbox("Kullanici Sec", list(user_options.keys()))
                selected_id = user_options[selected_user]
                selected_data = next((u for u in users if u["id"] == selected_id), {})

                with st.expander("Secili kullanici detaylari", expanded=True):
                    try:
                        detail_resp = requests.get(
                            f"{API_URL}/api/auth/admin/users/{selected_id}",
                            headers=headers,
                            timeout=10,
                        )
                        if detail_resp.status_code == 200:
                            detail = detail_resp.json()
                            detail_user = detail["user"]
                            d1, d2, d3, d4 = st.columns(4)
                            d1.metric("Portfoy islemi", len(detail["portfolio_trades"]))
                            d2.metric("Aktif pozisyon", len(detail["active_positions"]))
                            d3.metric("Aktif alarm", len(detail["active_alerts"]))
                            d4.metric("Telegram", "Bagli" if detail_user.get("telegram_id") else "Bagli degil")
                            st.json({
                                "id": detail_user["id"],
                                "username": detail_user["username"],
                                "email": detail_user.get("email"),
                                "role": detail_user.get("role"),
                                "is_active": detail_user.get("is_active"),
                                "created_at": detail_user.get("created_at"),
                                "last_login": detail_user.get("last_login"),
                                "telegram_username": detail_user.get("telegram_username"),
                            })
                        else:
                            st.error(detail_resp.json().get("detail", "Kullanici detayi alinamadi"))
                    except requests.RequestException as exc:
                        st.error(f"Kullanici detay API hatasi: {exc}")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write("**Rol Degistir**")
                    new_role = "admin" if selected_data.get("role") == "user" else "user"
                    role_label = "User Yap" if new_role == "user" else "Admin Yap"
                    if st.button(role_label, key="btn_role"):
                        resp = requests.post(
                            f"{API_URL}/api/auth/admin/role",
                            json={"user_id": selected_id, "role": new_role},
                            headers=headers,
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            st.success(resp.json()["message"])
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Hata"))

                with col2:
                    st.write("**Durum Degistir**")
                    active_label = "Pasif Yap" if selected_data.get("is_active") else "Aktif Yap"
                    if st.button(active_label, key="btn_active"):
                        resp = requests.post(
                            f"{API_URL}/api/auth/admin/toggle-active",
                            json={"user_id": selected_id},
                            headers=headers,
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            st.success(resp.json()["message"])
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Hata"))

                with col3:
                    st.write("**Sifre Sifirla**")
                    new_pass = st.text_input("Yeni Sifre", type="password", key="admin_new_pass")
                    if st.button("Sifreyi Sifirla", key="btn_pass") and new_pass:
                        resp = requests.post(
                            f"{API_URL}/api/auth/admin/reset-password",
                            json={"user_id": selected_id, "new_password": new_pass},
                            headers=headers,
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            st.success(resp.json()["message"])
                        else:
                            st.error(resp.json().get("detail", "Hata"))

                # Kullanici silme
                st.divider()
                st.subheader("Kullanici Sil")
                if selected_data.get("role") == "admin":
                    st.warning("Admin kullanicisi silinemez.")
                else:
                    if st.button(f"{selected_user} Kullanisisini Sil", type="primary", key="btn_delete"):
                        resp = requests.post(
                            f"{API_URL}/api/auth/admin/delete",
                            json={"user_id": selected_id},
                            headers=headers,
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            st.success(resp.json()["message"])
                            st.rerun()
                        else:
                            st.error(resp.json().get("detail", "Hata"))
            else:
                st.info("Henuz kullanici bulunmuyor.")
        else:
            st.error("Kullanici listesi alinamadi.")
    except Exception as e:
        st.error(f"API hatasi: {e}")
