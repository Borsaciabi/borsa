import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from data.database.models import init_db
from auth.dependencies import get_current_user
from auth.routes import router as auth_router
from api.routes.stocks import router as stocks_router
from api.routes.portfolio import router as portfolio_router
from api.routes.analysis import router as analysis_router
from api.routes.alerts import router as alerts_router
from api.routes.reports import router as reports_router

app = FastAPI(
    title="Python Borsa API",
    description="BIST Hisse Analiz ve Portfoy Yonetim Sistemi",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def register_router_flat(router):
    for route in router.routes:
        app.router.routes.append(route)


register_router_flat(auth_router)
register_router_flat(stocks_router)
register_router_flat(portfolio_router)
register_router_flat(analysis_router)
register_router_flat(alerts_router)
register_router_flat(reports_router)

# Global PriceUpdater
# Free plan'da Always-on task yok, PriceUpdater calismaz
# Manuel guncelleme icin /api/price-updater/update endpoint'i kullanilir
price_updater = None
IS_FREE_PLAN = os.getenv("PYTHONANYWHERE_DOMAIN") and not os.getenv("PYTHONANYWHERE_PLAN", "").startswith("merge")


@app.on_event("startup")
def startup():
    global price_updater
    init_db()
    from data.database.db_manager import DBManager
    db = DBManager()
    admin = db.ensure_admin("admin", "admin123", "admin@borsa.local")
    if admin:
        print(f"Admin kullanici hazir: admin / admin123")

    stock_count = len(db.get_all_stocks())
    if stock_count == 0:
        db.seed_default_stocks()
        print("BIST hisse listesi stock_master tablosuna eklendi")

    # PriceUpdater - sadece ucretli planda (Hacker/Always-on task)
    if not IS_FREE_PLAN:
        try:
            from data.cache.price_updater import PriceUpdater
            from config.settings import PRICE_UPDATE_MINUTES, BACKUP_ENABLED
            price_updater = PriceUpdater(interval_minutes=PRICE_UPDATE_MINUTES, backup_enabled=BACKUP_ENABLED)
            price_updater.start()
            print("PriceUpdater baslatildi (Hacker plan)")
        except Exception as e:
            print(f"PriceUpdater baslatilamadi: {e}")
    else:
        print("Free plan: PriceUpdater devre disi (manuel guncelleme ile)")


@app.get("/", response_class=HTMLResponse)
def root():
    html = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BIST Borsa Analiz Platformu</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #0d0d2b 100%);
                color: #e0e0e0;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            .container {
                text-align: center;
                padding: 40px 20px;
                max-width: 800px;
            }
            h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                background: linear-gradient(90deg, #00C853, #00E676, #69F0AE);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                font-size: 1.1em;
                color: #888;
                margin-bottom: 40px;
            }
            .cards {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .card {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px;
                padding: 25px 20px;
                text-decoration: none;
                color: #e0e0e0;
                transition: all 0.3s ease;
            }
            .card:hover {
                background: rgba(0,200,83,0.1);
                border-color: #00C853;
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(0,200,83,0.2);
            }
            .card-icon {
                font-size: 2em;
                margin-bottom: 12px;
            }
            .card-title {
                font-size: 1.1em;
                font-weight: 600;
                margin-bottom: 6px;
            }
            .card-desc {
                font-size: 0.85em;
                color: #999;
            }
            .status {
                background: rgba(255,255,255,0.05);
                border-radius: 8px;
                padding: 15px 25px;
                display: inline-block;
                margin-top: 10px;
            }
            .status-dot {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #00C853;
                margin-right: 8px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>BIST Hisse Analiz Platformu</h1>
            <p class="subtitle">Gerçek Zamanlı Hisse Analizi, Değerleme ve Portföy Yönetimi</p>

            <div class="cards">
                <a href="/dashboard" class="card">
                    <div class="card-icon">📈</div>
                    <div class="card-title">Dashboard</div>
                    <div class="card-desc">Piyasa analizi, AL/SAT sinyalleri, hisse detayları</div>
                </a>
                <a href="/docs" class="card">
                    <div class="card-icon">📖</div>
                    <div class="card-title">API Docs</div>
                    <div class="card-desc">FastAPISwagger dokümantasyonu</div>
                </a>
                <a href="/api/stocks" class="card">
                    <div class="card-icon">💹</div>
                    <div class="card-title">Hisse Verileri</div>
                    <div class="card-desc">Tüm BIST hisselerinin anlık verileri</div>
                </a>
                <a href="/api/price-updater/status" class="card">
                    <div class="card-icon">🔄</div>
                    <div class="card-title">Fiyat Durumu</div>
                    <div class="card-desc">Otomatik fiyat güncelleme servisi</div>
                </a>
            </div>

            <div class="status">
                <span class="status-dot"></span>
                Sistem Aktif - Fiyatlar manuel olarak guncellenir
                <br><small style="color:#666;">Free plan: Manuel guncelleme icin Dashboard'daki butonu kullanin</small>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    import os
    host = os.getenv("PYTHONANYWHERE_DOMAIN", "localhost:8501")
    if "localhost" in host:
        streamlit_url = f"http://{host}"
    else:
        streamlit_url = f"https://{host}"

    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - BIST Analiz</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', sans-serif;
                background: #0a0a1a;
                color: #e0e0e0;
            }}
            .navbar {{
                background: rgba(255,255,255,0.05);
                padding: 10px 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            .navbar a {{
                color: #00C853;
                text-decoration: none;
                margin-left: 15px;
                font-size: 0.9em;
            }}
            .navbar a:hover {{ text-decoration: underline; }}
            .navbar-title {{
                font-weight: 600;
                color: #00C853;
            }}
            iframe {{
                width: 100%;
                height: calc(100vh - 50px);
                border: none;
            }}
        </style>
    </head>
    <body>
        <div class="navbar">
            <span class="navbar-title">BIST Analiz Platformu</span>
            <div>
                <a href="/">Ana Sayfa</a>
                <a href="/docs">API</a>
                <a href="/dashboard" target="_self">Dashboard</a>
            </div>
        </div>
        <iframe src="{streamlit_url}" id="streamlit-frame"></iframe>
        <script>
            // Streamlit yuklenemezse uyari goster
            document.getElementById('streamlit-frame').onerror = function() {{
                document.body.innerHTML += '<div style="padding:40px;text-align:center;"><h2>Dashboard yuklenemedi</h2><p>Streamlit calisiyor olmali.</p><p>Durumu kontrol edin: <a href="/api/price-updater/status" style="color:#00C853;">/api/price-updater/status</a></p></div>';
            }};
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/site/mahmut")
def hidden_admin_login():
    return RedirectResponse(url="http://localhost:8501/?site=mahmut", status_code=307)


@app.get("/api/price-updater/status")
def price_updater_status():
    if price_updater:
        return price_updater.get_status()
    return {"running": False, "error": "PriceUpdater baslatilmamis"}


@app.post("/api/price-updater/update")
def price_updater_force_update(_user=Depends(get_current_user)):
    """Manuel olarak hemen fiyat guncellemesi yapar."""
    try:
        from data.cache.preloader import DataPreloader
        loader = DataPreloader()
        loader.update_prices_only()
        return {"message": "Fiyat guncelleme tamamlandi", "total_stocks": len(loader.get_all_data())}
    except Exception as e:
        return {"error": f"Guncelleme hatasi: {str(e)}"}
