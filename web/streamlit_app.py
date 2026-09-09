import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from pages.investing_dashboard import render_investing_dashboard
from pages.stock_detail import render_stock_detail
from pages.value_analysis import render_value_analysis
from pages.portfolio import render_portfolio
from pages.comparison import render_comparison
from pages.alerts import render_alerts
from pages.reports import render_reports
from pages.admin_panel import render_admin_panel
from pages.news import render_news

st.set_page_config(
    page_title="BIST Analiz Platformu",
    page_icon="📈",
    layout="wide",
)
st.set_option("client.showSidebarNavigation", False)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --navy: #08111f;
        --navy-soft: #101d31;
        --panel: #12243b;
        --panel-light: #18304d;
        --line: rgba(148, 163, 184, .18);
        --text: #e8f0f7;
        --muted: #91a4b8;
        --mint: #35d0ba;
        --blue: #65a8ff;
        --danger: #ff7184;
    }
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--text);
    }
    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(53, 208, 186, .11), transparent 28rem),
            radial-gradient(circle at 95% 5%, rgba(101, 168, 255, .10), transparent 30rem),
            var(--navy);
    }
    [data-testid="stHeader"] { background: rgba(8, 17, 31, .82); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c192b 0%, #08111f 100%);
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stMarkdown { color: var(--muted); }
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: -.035em;
        color: var(--text);
    }
    h1 { font-size: clamp(2rem, 4vw, 3.2rem) !important; }
    h2 { font-size: 1.65rem !important; }
    h3 { font-size: 1.2rem !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted); }
    .stButton > button, .stDownloadButton > button {
        border: 1px solid rgba(53, 208, 186, .36);
        border-radius: 9px;
        background: linear-gradient(135deg, rgba(53, 208, 186, .18), rgba(101, 168, 255, .15));
        color: var(--text);
        font-weight: 600;
        transition: all .18s ease;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        border-color: var(--mint);
        color: #fff;
        transform: translateY(-1px);
        box-shadow: 0 8px 24px rgba(53, 208, 186, .14);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1bb89f, #3186db);
        border: 0;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(18, 36, 59, .94), rgba(16, 29, 49, .94));
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 12px 28px rgba(0, 0, 0, .14);
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--text); font-family: 'Space Grotesk', sans-serif; }
    [data-baseweb="tab-list"] { gap: .45rem; border-bottom: 1px solid var(--line); }
    [data-baseweb="tab"] { color: var(--muted); padding: .75rem 1rem; }
    [aria-selected="true"][data-baseweb="tab"] { color: var(--mint); }
    [data-testid="stExpander"] {
        background: rgba(18, 36, 59, .58);
        border: 1px solid var(--line);
        border-radius: 12px;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
    }
    .app-brand {
        padding: 1.1rem 1rem 1.35rem;
        margin-bottom: .7rem;
        border-bottom: 1px solid var(--line);
    }
    .app-brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        margin-right: .55rem;
        border-radius: 11px;
        background: linear-gradient(135deg, var(--mint), var(--blue));
        color: var(--navy);
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
    }
    .app-brand-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.05rem; font-weight: 700; }
    .app-brand-subtitle { margin-top: .35rem; color: var(--muted); font-size: .75rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "stock_data" not in st.session_state:
    st.session_state.stock_data = {}
if "page" not in st.session_state:
    st.session_state.page = "Piyasa Dashboard"
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


def _restore_saved_login():
    """Restore a remembered login only after validating its token with the API."""
    saved_token = st.query_params.get("remember_token")
    if st.session_state.user or not saved_token:
        return
    try:
        response = requests.get(
            f"{API_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {saved_token}"},
            timeout=10,
        )
        if response.ok:
            result = response.json()
            result["access_token"] = saved_token
            st.session_state.user = result
            st.session_state.auth_token = saved_token
        else:
            st.query_params.pop("remember_token", None)
    except requests.RequestException:
        # A temporary API outage must not turn into a fake logged-in state.
        st.session_state.user = None
        st.session_state.auth_token = None


def _current_user():
    user = st.session_state.get("user")
    return user if isinstance(user, dict) else None


def _hidden_admin_entry():
    try:
        return st.query_params.get("site") == "mahmut"
    except Exception:
        return False


def _login_panel(hidden_admin=False):
    user = _current_user()
    if user:
        st.sidebar.markdown(
            f'<div class="app-brand"><span class="app-brand-mark">B</span>'
            f'<span class="app-brand-title">Borsa Analiz</span>'
            f'<div class="app-brand-subtitle">Merhaba, {user["username"]}</div></div>',
            unsafe_allow_html=True,
        )
        st.sidebar.success(f"Giris: {user['username']} ({user.get('role', 'user')})")
        if st.sidebar.button("Cikis Yap", key="logout_button", use_container_width=True):
            st.session_state.user = None
            st.session_state.auth_token = None
            st.query_params.pop("remember_token", None)
            st.session_state.page = "Piyasa Dashboard"
            st.rerun()
        return

    title = "Yonetici Girisi" if hidden_admin else "Kullanici Girisi"
    st.sidebar.markdown(
        '<div class="app-brand"><span class="app-brand-mark">B</span>'
        '<span class="app-brand-title">Borsa Analiz</span>'
        '<div class="app-brand-subtitle">Piyasa verilerini sade ve anlaşılır takip edin</div></div>',
        unsafe_allow_html=True,
    )
    with st.sidebar.expander(title, expanded=hidden_admin):
        with st.form("login_form"):
            username = st.text_input("Kullanici adi")
            password = st.text_input("Sifre", type="password")
            remember_me = st.checkbox("Beni hatirla", value=True)
            submitted = st.form_submit_button("Giris Yap", use_container_width=True)
        if submitted:
            try:
                response = requests.post(
                    f"{API_URL}/api/auth/login",
                    json={"username": username, "password": password},
                    timeout=10,
                )
                if response.status_code == 200:
                    result = response.json()
                    if hidden_admin and result.get("role") != "admin":
                        st.error("Bu alan sadece yoneticiler icindir.")
                    else:
                        st.session_state.user = result
                        st.session_state.auth_token = result["access_token"]
                        if remember_me:
                            st.query_params["remember_token"] = result["access_token"]
                        else:
                            st.query_params.pop("remember_token", None)
                        st.session_state.page = "Admin Paneli" if hidden_admin else "Kullanici Paneli"
                        st.rerun()
                else:
                    st.error(response.json().get("detail", "Giris basarisiz"))
            except requests.RequestException as exc:
                st.error(f"API baglantisi kurulamadi: {exc}")

    with st.sidebar.expander("Yeni kullanici kaydi"):
        with st.form("register_form"):
            new_username = st.text_input("Kullanici adi", key="register_username")
            new_email = st.text_input("E-posta", key="register_email")
            new_password = st.text_input("Sifre", type="password", key="register_password")
            register_submitted = st.form_submit_button("Kayit ol", use_container_width=True)
        if register_submitted:
            if len(new_password) < 6:
                st.error("Sifre en az 6 karakter olmali.")
            else:
                try:
                    response = requests.post(
                        f"{API_URL}/api/auth/register",
                        json={
                            "username": new_username.strip(),
                            "email": new_email.strip(),
                            "password": new_password,
                        },
                        timeout=10,
                    )
                    if response.ok:
                        result = response.json()
                        st.session_state.user = result
                        st.session_state.auth_token = result["access_token"]
                        st.query_params["remember_token"] = result["access_token"]
                        st.session_state.page = "Kullanici Paneli"
                        st.rerun()
                    else:
                        st.error(response.json().get("detail", "Kayit basarisiz"))
                except requests.RequestException as exc:
                    st.error(f"API baglantisi kurulamadi: {exc}")

    with st.sidebar.expander("Kullanici adi / sifre hatirlatma"):
        recovery_email = st.text_input("Kayitli e-posta", key="recovery_email")
        recovery_col1, recovery_col2 = st.columns(2)
        with recovery_col1:
            if st.button("Kullanici adimi bul", key="recover_username"):
                try:
                    response = requests.post(
                        f"{API_URL}/api/auth/forgot-username",
                        json={"email": recovery_email},
                        timeout=10,
                    )
                    if response.ok:
                        st.success(f"Kullanici adiniz: {response.json()['username']}")
                    else:
                        st.error(response.json().get("detail", "Kullanici bulunamadi"))
                except requests.RequestException as exc:
                    st.error(f"API baglantisi kurulamadi: {exc}")
        with recovery_col2:
            if st.button("Sifremi yenile", key="reset_password"):
                st.session_state.show_password_reset = True

        if st.session_state.get("show_password_reset"):
            reset_password = st.text_input("Yeni sifre", type="password", key="recovery_password")
            if st.button("Yeni sifreyi kaydet", key="save_reset_password"):
                try:
                    response = requests.post(
                        f"{API_URL}/api/auth/reset-password",
                        json={"email": recovery_email, "new_password": reset_password},
                        timeout=10,
                    )
                    if response.ok:
                        st.success("Sifreniz yenilendi. Yeni sifrenizle giris yapabilirsiniz.")
                        st.session_state.show_password_reset = False
                    else:
                        st.error(response.json().get("detail", "Sifre yenilenemedi"))
                except requests.RequestException as exc:
                    st.error(f"API baglantisi kurulamadi: {exc}")


def _render_user_panel():
    user = st.session_state.get("user")
    if not user:
        st.title("Kullanici Paneli")
        st.info("Kullanici panelini kullanmak icin sol menuden giris yapin.")
        return
    st.title("Kullanici Paneli")
    st.write(f"Hos geldin, **{user['username']}**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rol", user.get("role", "user"))
    with col2:
        st.metric("Kullanici ID", user.get("user_id", "-"))
    with col3:
        st.metric("Durum", "Aktif")
    st.caption("Portfoy, alarmlar ve raporlar soldaki bolumlerden kullanilabilir.")

hidden_admin = _hidden_admin_entry()
_restore_saved_login()
_login_panel(hidden_admin=hidden_admin)

if st.sidebar.button("BIST Analiz", key="home_button", use_container_width=True):
    st.session_state.page = "Piyasa Dashboard"
    st.rerun()

menu = [
    "Piyasa Dashboard",
    "Kullanici Paneli",
    "Hisse Detay",
    "Deger Analizi",
    "Karsilastirma",
    "Portfoy",
    "Alarmlar",
    "Raporlar",
    "KAP Haberleri",
]
current_user = _current_user()
if current_user and current_user.get("role") == "admin":
    menu.append("Admin Paneli")
if not current_user:
    menu = ["Piyasa Dashboard", "KAP Haberleri"]
if st.session_state.page not in menu:
    st.session_state.page = "Piyasa Dashboard"
st.session_state.page = st.sidebar.radio(
    "Bolum sec",
    menu,
    index=menu.index(st.session_state.page),
)
page = st.session_state.page

if page == "Piyasa Dashboard":
    render_investing_dashboard()
elif page == "Kullanici Paneli":
    _render_user_panel()
elif page == "Hisse Detay":
    render_stock_detail()
elif page == "Deger Analizi":
    render_value_analysis()
elif page == "Karsilastirma":
    render_comparison()
elif page == "Portfoy":
    if current_user:
        render_portfolio()
    else:
        st.info("Portfoy olusturmak icin kayit olun veya giris yapin.")
elif page == "Alarmlar":
    render_alerts()
elif page == "Raporlar":
    render_reports()
elif page == "KAP Haberleri":
    render_news()
elif page == "Admin Paneli":
    if current_user and current_user.get("role") == "admin":
        render_admin_panel()
    else:
        st.error("Admin yetkisi gerekiyor.")
