import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import schedule
import logging
from data.database.db_manager import DBManager
from data.fetchers.bist_fetcher import BistFetcher
from analysis.value_analysis import ValueAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = DBManager()
bist = BistFetcher()
analyzer = ValueAnalyzer()


def check_price_alerts():
    """Tum aktif fiyat alarmlarini kontrol eder."""
    alerts = db.get_active_alerts()
    for alert in alerts:
        if alert["triggered"]:
            continue

        symbol = alert["stock_code"]
        alert_type = alert["alert_type"]
        target = alert["target_value"]

        price = bist.get_price(symbol)
        if price is None:
            continue

        triggered = False
        if alert_type == "PRICE_ABOVE" and price >= target:
            triggered = True
        elif alert_type == "PRICE_BELOW" and price <= target:
            triggered = True

        if triggered:
            db.trigger_alert(alert["id"])
            user = db.get_user_by_id(alert["user_id"])
            if user and user.get("telegram_id"):
                _send_telegram_alert(user["telegram_id"], symbol, alert_type, price, target)
            logger.info(f"Alarm tetiklendi: {symbol} {alert_type} {target} (Fiyat: {price})")


def check_value_alerts():
    """Deger analizi sinyallerini kontrol eder."""
    watchlist = db.get_watchlist(user_id=None)
    for item in watchlist:
        symbol = item["stock_code"]
        result = analyzer.analyze(symbol)
        if result and result["signal"] in ["Hemen SAT", "Evi Barki Sat"]:
            user = db.get_user_by_id(item["user_id"])
            if user and user.get("telegram_id"):
                _send_telegram_value_alert(
                    user["telegram_id"], symbol,
                    result["signal"], result["calculated_value"],
                    result["current_price"]
                )


def _send_telegram_alert(telegram_id, symbol, alert_type, current_price, target):
    """Telegram'a alarm bildirimi gonderir."""
    try:
        from telegram import Bot
        from config.settings import TELEGRAM_BOT_TOKEN

        if not TELEGRAM_BOT_TOKEN:
            return

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        text = (
            f"ALARM TETIKLENDI!\n\n"
            f"Hisse: {symbol}\n"
            f"Tur: {alert_type}\n"
            f"Hedef: {target:.2f} TL\n"
            f"Guncel Fiyat: {current_price:.2f} TL\n"
        )
        import asyncio
        asyncio.run(bot.send_message(chat_id=telegram_id, text=text))
    except Exception as e:
        logger.error(f"Telegram bildirim hatasi: {e}")


def _send_telegram_value_alert(telegram_id, symbol, signal, calculated_value, current_price):
    """Telegram'a deger analizi bildirimi gonderir."""
    try:
        from telegram import Bot
        from config.settings import TELEGRAM_BOT_TOKEN

        if not TELEGRAM_BOT_TOKEN:
            return

        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        text = (
            f"DEGER ANALIZI SINYALI!\n\n"
            f"Hisse: {symbol}\n"
            f"Sinyal: {signal}\n"
            f"Hesaplanan Deger: {calculated_value:.2f} TL\n"
            f"Guncel Fiyat: {current_price:.2f} TL\n"
        )
        import asyncio
        asyncio.run(bot.send_message(chat_id=telegram_id, text=text))
    except Exception as e:
        logger.error(f"Telegram bildirim hatasi: {e}")


def main():
    logger.info("Alarm kontrolcusu baslatildi.")
    schedule.every(5).minutes.do(check_price_alerts)
    schedule.every(30).minutes.do(check_value_alerts)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
