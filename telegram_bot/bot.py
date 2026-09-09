import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from config.settings import TELEGRAM_BOT_TOKEN
from analysis.value_analysis import ValueAnalyzer
from analysis.technical_analysis import TechnicalAnalyzer
from data.fetchers.bist_fetcher import BistFetcher
from data.database.db_manager import DBManager
from data.cache.preloader import DataPreloader
from config.constants import BIST_100

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

analyzer = ValueAnalyzer()
tech_analyzer = TechnicalAnalyzer()
bist = BistFetcher()
db = DBManager()
preloader = DataPreloader()

WAITING_STOCK_CODE = 0
WAITING_BUY_DETAILS = 1
WAITING_SELL_DETAILS = 2
WAITING_ALERT_DETAILS = 3


def telegram_user(update: Update):
    telegram_id = update.effective_user.id if update.effective_user else None
    return db.get_user_by_telegram_id(telegram_id) if telegram_id else None


async def require_login(update: Update):
    user = telegram_user(update)
    if not user or not user.get("is_active", 1):
        await update.effective_message.reply_text(
            "Bu islemi kullanmak icin Telegram hesabinizi sisteme baglayin.\n"
            "/kayit kullaniciadi sifre\n"
            "veya\n"
            "/giris kullaniciadi sifre"
        )
        return None
    return user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = telegram_user(update)
    login_text = (
        f"Bagli kullanici: {user['username']}"
        if user and user.get("is_active", 1)
        else "Telegram hesabi bagli degil. /giris veya /kayit kullanin."
    )
    keyboard = [
        [InlineKeyboardButton("Portfoyum", callback_data="portfolio")],
        [InlineKeyboardButton("Deger Analizi", callback_data="value_menu")],
        [InlineKeyboardButton("Teknik Analiz", callback_data="tech_menu")],
        [InlineKeyboardButton("Piyasa Ozeti", callback_data="market")],
        [InlineKeyboardButton("Fiyatlari Guncelle", callback_data="price_update")],
        [InlineKeyboardButton("Alarm Kur", callback_data="alert_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Borsa Analiz Bot'a Hosgeldin!\n\n{login_text}\n\n"
        "Komutlar:\n"
        "/deger THYAO - Deger analizi\n"
        "/sorgu THYAO - Teknik analiz\n"
        "/portfoy - Portfoy goruntule\n"
        "/durum - Portfoy toplam durumunu goruntule\n"
        "/alis THYAO 250 100 - Alis kaydet (fiyat, miktar)\n"
        "/satis THYAO 300 50 - Satis kaydet\n"
        "/alarm THYAO > 250 - Alarm kur\n"
        "/piyasa - Piyasa ozeti\n"
        "/fiyat - Tum hisse fiyatlarini yenile\n"
        "/hisse_fiyat THYAO - Tek hisse fiyatini yenile\n"
        "/yardim - Bu mesaj\n\n"
        "Butonlari da kullanabilirsiniz:",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Komutlar:\n"
        "/deger THYAO - Deger analizi\n"
        "/sorgu THYAO - Teknik analiz\n"
        "/portfoy - Portfoy goruntule\n"
        "/durum - Portfoy toplam durumunu goruntule\n"
        "/alis THYAO 250 100 - Alis kaydet\n"
        "/satis THYAO 300 50 - Satis kaydet\n"
        "/alarm THYAO > 250 - Alarm kur\n"
        "/alarm_list - Alarmlari listele\n"
        "/piyasa - Piyasa ozeti\n"
        "/fiyat - Tum hisse fiyatlarini yenile\n"
        "/hisse_fiyat THYAO - Tek hisse fiyatini yenile\n"
    )


async def update_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tum fiyatlari yeniler; temel ve degerleme verilerine dokunmaz."""
    message = update.effective_message
    if not await require_login(update):
        return
    await message.reply_text(
        "Fiyat guncellemesi basladi. Sadece fiyat, degisim ve hacim yenileniyor..."
    )
    try:
        before = preloader.load_cache_with_backup()
        old_count = len(before)
        data = await asyncio.to_thread(preloader.update_prices_only)
        updated = sum(1 for symbol, item in data.items() if item.get("last_price"))
        await message.reply_text(
            f"Fiyat guncellemesi tamamlandi.\n"
            f"Guncellenen: {updated}/{old_count or len(data)} hisse\n"
            f"Temel veriler ve kisisel gorusler degistirilmedi."
        )
    except Exception as e:
        logger.exception("Telegram fiyat guncelleme hatasi")
        await message.reply_text(f"Fiyat guncelleme hatasi: {e}")


async def update_single_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tek bir hissenin fiyatini anlik kaynaktan ceker."""
    message = update.effective_message
    if not await require_login(update):
        return
    if not context.args:
        await message.reply_text("Ornek: /fiyat THYAO")
        return

    symbol = context.args[0].upper()
    await message.reply_text(f"{symbol} fiyati sorgulaniyor...")
    try:
        price_data = await asyncio.to_thread(preloader.update_single_price, symbol)
        if not price_data or not price_data.get("last_price"):
            await message.reply_text(f"{symbol} icin fiyat bulunamadi.")
            return

        price = price_data.get("last_price", 0) or 0
        change = price_data.get("change_pct", 0) or 0
        volume = price_data.get("volume", 0) or 0
        await message.reply_text(
            f"{symbol} fiyat bilgisi\n"
            f"Son fiyat: {price:.2f} TL\n"
            f"Degisim: %{change:+.2f}\n"
            f"Hacim: {volume:,.0f}\n\n"
            f"Bu komut sadece fiyat verisini yeniler."
        )
    except Exception as e:
        logger.exception("Tekil fiyat sorgu hatasi")
        await message.reply_text(f"{symbol} fiyat sorgusunda hata: {e}")


async def value_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_login(update):
        return
    if not context.args:
        await update.message.reply_text("Ornek: /deger THYAO")
        return

    symbol = context.args[0].upper()
    await update.message.reply_text(f"{symbol} icin deger analizi yapiliyor...")

    try:
        # Once cache'den dene
        if preloader.is_cache_valid(3600):
            data = preloader.load_cache()
            s = data.get(symbol, {})
            if s and s.get('last_price', 0) > 0:
                result = {
                    "symbol": symbol,
                    "description": s.get("company_name", ""),
                    "current_price": s.get("last_price", 0),
                    "change_pct": s.get("change_pct", 0),
                    "volume": s.get("volume", 0),
                    "market_cap": s.get("market_cap", 0),
                    "market_cap_mn": s.get("market_cap_mn", 0),
                    "net_debt": s.get("net_debt", 0),
                    "net_debt_mn": s.get("net_debt_mn", 0),
                    "float_rate": s.get("float_rate", 0),
                    "total_shares": s.get("total_shares", 0),
                    "floating_shares": s.get("floating_shares", 0),
                    "calculated_value": s.get("calculated_value", 0),
                    "ratio": s.get("ratio", 0),
                    "signal": s.get("signal", ""),
                    "signal_emoji": "",
                    "signal_color": "",
                    "expected_return": s.get("expected_return", 0),
                    "pe": s.get("pe"),
                    "pb": s.get("pb"),
                }
            else:
                result = None
        else:
            result = None

        # Cache yoksa veya bossa canli cek
        if not result:
            result = analyzer.analyze(symbol)
        if result:
            text = (
                f"{'='*40}\n"
                f"  {result['symbol']} - DEGER ANALIZI\n"
                f"{'='*40}\n\n"
                f"  Son Fiyat:        {result['current_price']:.2f} TL\n"
                f"  Piyasa Degeri:    {result['market_cap_mn']:,.1f} M TL\n"
                f"  Net Borc:         {result['net_debt_mn']:,.1f} M TL\n"
                f"  Fiili Dolasim:    %{result.get('float_rate', 0)}\n\n"
                f"  {'='*36}\n"
                f"  HESAPLANAN DEGER:  {result['calculated_value']:.2f} TL\n"
                f"  ORAN:              {result['ratio']:.2f}\n"
                f"  {'='*36}\n\n"
                f"  SINYAL: {result['signal_emoji']} {result['signal']}\n"
                f"  Kar Beklentisi:   %{result['expected_return']:.1f}\n\n"
                f"  F/K: {result['pe']:.1f}  |  PD/DD: {result['pb']:.2f}\n"
                f"  Teknik ortalamalar icin /sorgu {symbol} komutunu kullanin.\n"
            )
            await update.message.reply_text(text)
        else:
            await update.message.reply_text(f"{symbol} icin veri bulunamadi.")
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")


async def technical_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_login(update):
        return
    if not context.args:
        await update.message.reply_text("Ornek: /sorgu THYAO")
        return

    symbol = context.args[0].upper()
    await update.message.reply_text(f"{symbol} icin teknik analiz yapiliyor...")

    try:
        result = tech_analyzer.analyze(symbol)
        if result:
            text = (
                f"{'='*40}\n"
                f"  {result['symbol']} - TEKNIK ANALIZ\n"
                f"{'='*40}\n\n"
                f"  Fiyat:            {result['current_price']:.2f} TL\n"
                f"  RSI(14):          {result['rsi']:.1f}\n"
                f"  MACD:             {result['macd']:.4f}\n"
                f"  MACD Signal:      {result['macd_signal']:.4f}\n\n"
                f"  MA20:  {result['ma20']:.2f}\n"
                f"  MA50:  {result['ma50']:.2f}\n"
                f"  MA200: {result['ma200']:.2f}\n\n"
                f"  Fiyat/MA200:  %{result['price_vs_ma200']:.1f}\n"
                f"  Fiyat/MA50:   %{result['price_vs_ma50']:.1f}\n\n"
                f"  Hacim: {result['volume']:,.0f}\n"
                f"  Hacim Ort(20): {result['volume_avg_20']:,.0f}\n"
            )
            await update.message.reply_text(text)
        else:
            await update.message.reply_text(f"{symbol} icin veri bulunamadi.")
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")


async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_login(update)
    if not user:
        return

    trades = db.get_portfolio(user["id"])
    if not trades:
        await update.effective_message.reply_text("Portfoyde hisse bulunmuyor.")
        return

    data = preloader.load_cache_with_backup()
    grouped = {}
    for trade in trades:
        symbol = trade["stock_code"].upper()
        item = grouped.setdefault(symbol, {"buy_qty": 0, "sell_qty": 0, "buy_total": 0.0, "sell_total": 0.0, "fees": 0.0})
        quantity = trade.get("quantity") or 0
        fees = trade.get("fees") or 0
        item["fees"] += fees
        if trade.get("transaction_type") == "BUY":
            item["buy_qty"] += quantity
            item["buy_total"] += (trade.get("buy_price") or 0) * quantity
        else:
            item["sell_qty"] += quantity
            item["sell_total"] += (trade.get("sell_price") or 0) * quantity

    total_value = 0.0
    total_cost = 0.0
    total_profit = 0.0
    lines = []
    for symbol, item in sorted(grouped.items()):
        net_qty = item["buy_qty"] - item["sell_qty"]
        current_price = (data.get(symbol, {}) or {}).get("last_price") or 0
        current_value = net_qty * current_price if net_qty > 0 else 0
        profit = item["sell_total"] + current_value - item["buy_total"] - item["fees"]
        avg_buy = item["buy_total"] / item["buy_qty"] if item["buy_qty"] else 0
        marker = "AL" if net_qty > 0 else "SAT"
        total_value += current_value
        total_cost += item["buy_total"]
        total_profit += profit
        lines.append(
            f"{marker} {symbol} | {net_qty} adet | "
            f"Ort {avg_buy:.2f} | Son {current_price:.2f} | "
            f"K/Z {profit:+,.2f} TL"
        )

    profit_sign = "+" if total_profit >= 0 else ""
    text = (
        "PORTFOYUM\n" + "=" * 34 + "\n"
        f"Toplam Deger: {total_value:,.2f} TL\n"
        f"Toplam Maliyet: {total_cost:,.2f} TL\n"
        f"Toplam K/Z: {profit_sign}{total_profit:,.2f} TL\n\n"
        + "\n".join(lines)
    )
    await update.effective_message.reply_text(text)


async def portfolio_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Portfoyun sadece toplam durumunu gosterir."""
    user = await require_login(update)
    if not user:
        return

    trades = db.get_portfolio(user["id"])
    if not trades:
        await update.effective_message.reply_text("Portfoyde hisse bulunmuyor.")
        return

    data = preloader.load_cache_with_backup()
    grouped = {}
    for trade in trades:
        symbol = trade["stock_code"].upper()
        item = grouped.setdefault(
            symbol,
            {"buy_qty": 0, "sell_qty": 0, "buy_total": 0.0, "sell_total": 0.0, "fees": 0.0},
        )
        quantity = trade.get("quantity") or 0
        item["fees"] += trade.get("fees") or 0
        if trade.get("transaction_type") == "BUY":
            item["buy_qty"] += quantity
            item["buy_total"] += (trade.get("buy_price") or 0) * quantity
        else:
            item["sell_qty"] += quantity
            item["sell_total"] += (trade.get("sell_price") or 0) * quantity

    total_value = 0.0
    total_cost = 0.0
    total_profit = 0.0
    for symbol, item in grouped.items():
        net_qty = item["buy_qty"] - item["sell_qty"]
        current_price = (data.get(symbol, {}) or {}).get("last_price") or 0
        current_value = net_qty * current_price if net_qty > 0 else 0
        total_value += current_value
        total_cost += item["buy_total"]
        total_profit += (
            item["sell_total"] + current_value - item["buy_total"] - item["fees"]
        )

    await update.effective_message.reply_text(
        "PORTFOY DURUMU\n"
        + "=" * 24
        + "\n"
        f"Toplam Deger: {total_value:,.2f} TL\n"
        f"Toplam Maliyet: {total_cost:,.2f} TL\n"
        f"Toplam Kar/Zarar: {total_profit:+,.2f} TL"
    )


async def buy_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_login(update)
    if not user:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Ornek: /alis THYAO 250 100\n(fiyat, miktar)")
        return

    symbol = context.args[0].upper()
    try:
        price = float(context.args[1])
        quantity = int(context.args[2])
    except ValueError:
        await update.message.reply_text("Fiyat ve miktar sayi olmali.")
        return

    from datetime import date
    db.add_trade(
        user_id=user["id"],
        stock_code=symbol,
        buy_date=str(date.today()),
        buy_price=price,
        quantity=quantity,
        transaction_type="BUY",
    )
    await update.message.reply_text(
        f"{symbol} alisi kaydedildi!\n"
        f"Fiyat: {price:.2f} TL x {quantity} adet"
    )


async def sell_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_login(update)
    if not user:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Ornek: /satis THYAO 300 50\n(fiyat, miktar)")
        return

    symbol = context.args[0].upper()
    try:
        price = float(context.args[1])
        quantity = int(context.args[2])
    except ValueError:
        await update.message.reply_text("Fiyat ve miktar sayi olmali.")
        return

    from datetime import date
    db.sell_stock(
        user_id=user["id"],
        stock_code=symbol,
        sell_date=str(date.today()),
        sell_price=price,
        quantity=quantity,
    )
    await update.message.reply_text(
        f"{symbol} satisi kaydedildi!\n"
        f"Fiyat: {price:.2f} TL x {quantity} adet"
    )


async def set_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_login(update)
    if not user:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Ornek: /alarm THYAO > 250\nveya: /alarm THYAO < 100")
        return

    symbol = context.args[0].upper()
    operator = context.args[1]
    try:
        target = float(context.args[2])
    except ValueError:
        await update.message.reply_text("Hedef deger sayi olmali.")
        return

    alert_type = "PRICE_ABOVE" if operator == ">" else "PRICE_BELOW"

    db.add_alert(user["id"], symbol, alert_type, target)
    await update.message.reply_text(
        f"{symbol} icin alarm kuruldu!\n"
        f"Tur: {alert_type}\n"
        f"Hedef: {target:.2f} TL"
    )


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await require_login(update)
    if not user:
        return

    alerts = db.get_active_alerts(user["id"])
    if not alerts:
        await update.effective_message.reply_text("Aktif alarm bulunmuyor.")
        return

    text = "AKTIF ALARMLAR\n" + "="*30 + "\n"
    for a in alerts:
        status = "Tetiklendi" if a["triggered"] else "Aktif"
        text += f"\n{a['stock_code']} - {a['alert_type']}: {a['target_value']} TL [{status}]\n"
    await update.effective_message.reply_text(text)


async def market_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_login(update):
        return
    await update.effective_message.reply_text("Piyasa ozeti hazirlaniyor...")

    text = "PIYASA OZETI\n" + "="*30 + "\n\n"

    # Cache'den oku
    if preloader.is_cache_valid(3600):
        data = preloader.load_cache()
        watchlist = ["THYAO", "GARAN", "AKBNK", "SISE", "ASELS"]
        for symbol in watchlist:
            s = data.get(symbol, {})
            if s and s.get('last_price', 0) > 0:
                text += (
                    f"{symbol}: {s['last_price']:.2f} TL "
                    f"({s.get('change_pct', 0):+.1f}%)\n"
                )
            else:
                text += f"{symbol}: Veri yok\n"
    else:
        for symbol in ["THYAO", "GARAN", "AKBNK", "SISE", "ASELS"]:
            info = bist.get_info(symbol)
            if info:
                text += (
                    f"{symbol}: {info.get('last', 'N/A')} TL "
                    f"({info.get('change_percent', 0):+.1f}%)\n"
                )

    await update.effective_message.reply_text(text)


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Ornek: /kayit kullaniciadi sifre")
        return

    username = context.args[0]
    password = context.args[1]

    from auth.password import hash_password
    user = db.create_user(username, f"{username}@telegram.local", hash_password(password))
    if user:
        linked = db.link_telegram(user["id"], update.effective_user.id, update.effective_user.username or "")
        if linked:
            await update.message.reply_text(f"Kayit ve Telegram eslestirmesi basarili! Kullanici: {username}")
        else:
            await update.message.reply_text("Kayit yapildi ancak Telegram hesabi baska bir kullaniciya bagli.")
    else:
        await update.message.reply_text("Kayit basarisiz. Kullanici adi zaten mevcut olabilir.")


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Ornek: /giris kullaniciadi sifre")
        return

    username = context.args[0]
    password = context.args[1]

    from auth.password import verify_password
    user = db.get_user_by_username(username)
    if user and user.get("is_active", 1) and verify_password(password, user["password_hash"]):
        if not db.link_telegram(user["id"], update.effective_user.id, update.effective_user.username or ""):
            await update.message.reply_text("Bu Telegram hesabi baska bir kullaniciya bagli.")
            return
        db.update_last_login(user["id"])
        await update.message.reply_text(f"Giris basarili! Hosgeldin {username}")
    elif user and not user.get("is_active", 1):
        await update.message.reply_text("Bu hesap pasif durumda. Yoneticiyle iletisime gecin.")
    else:
        await update.message.reply_text("Kullanici adi veya sifre hatali.")


async def configure_command_menu(application: Application):
    """Telegram uygulamasinin yerel komut menusunu tanimlar."""
    await application.bot.set_my_commands([
        ("start", "Ana menu"),
        ("yardim", "Komutlari goster"),
        ("fiyat", "Tum hisse fiyatlarini yenile"),
        ("hisse_fiyat", "Tek hisse fiyatini yenile"),
        ("deger", "Deger analizi"),
        ("sorgu", "Teknik analiz"),
        ("piyasa", "Piyasa ozeti"),
        ("portfoy", "Portfoyu goster"),
        ("durum", "Portfoy durumunu goster"),
        ("alis", "Alis kaydet"),
        ("satis", "Satis kaydet"),
        ("alarm", "Fiyat alarmi kur"),
        ("alarm_list", "Alarmlari listele"),
        ("kayit", "Kayit ol"),
        ("giris", "Giris yap"),
    ])


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "portfolio":
        await portfolio(update, context)
    elif query.data == "market":
        await market_overview(update, context)
    elif query.data == "price_update":
        await update_prices(update, context)
    elif query.data.startswith("value_"):
        await query.edit_message_text("Deger analizi icin: /deger HISSEKODU")
    elif query.data.startswith("tech_"):
        await query.edit_message_text("Teknik analiz icin: /sorgu HISSEKODU")
    elif query.data.startswith("alert_"):
        await query.edit_message_text("Alarm icin: /alarm HISSEKODU > FIYAT")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN ayarlanmamis!")
        print("Lutfen .env dosyasinda TELEGRAM_BOT_TOKEN ayarlayin.")
        return

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(configure_command_menu)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yardim", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("deger", value_analysis))
    app.add_handler(CommandHandler("sorgu", technical_analysis))
    app.add_handler(CommandHandler("portfoy", portfolio))
    app.add_handler(CommandHandler("durum", portfolio_status))
    app.add_handler(CommandHandler("alis", buy_stock))
    app.add_handler(CommandHandler("satis", sell_stock))
    app.add_handler(CommandHandler("alarm", set_alert))
    app.add_handler(CommandHandler("alarm_list", list_alerts))
    app.add_handler(CommandHandler("piyasa", market_overview))
    app.add_handler(CommandHandler("fiyat", update_prices))
    app.add_handler(CommandHandler("fiyat_guncelle", update_prices))
    app.add_handler(CommandHandler("hisse_fiyat", update_single_price))
    app.add_handler(CommandHandler("kayit", register))
    app.add_handler(CommandHandler("giris", login))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("Telegram bot baslatiliyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
