from typing import Optional, Dict
import pandas as pd
from data.fetchers.mynet_fetcher import MynetFetcher
from data.fetchers.isyatirim_fetcher import IsYatirimFetcher
from data.fetchers.kap_fetcher import KapFetcher


class BistFetcher:
    """
    BIST verilerini ceken ana sinif.
    Veri kaynaklari:
    - Fiyat: finans.mynet.com
    - Piyasa Degeri + Net Borc: isyatirim.com.tr
    - Fiili Dolasim: kap.org.tr + isyatirim.com.tr
    """

    def __init__(self):
        self.mynet = MynetFetcher()
        self.isyatirim = IsYatirimFetcher()
        self.kap = KapFetcher()

    def get_price(self, symbol: str) -> Optional[float]:
        """Anlik fiyati finans.mynet.com'dan ceker."""
        data = self.mynet.get_price(symbol)
        if data:
            return data.get("last_price")
        return None

    def get_price_data(self, symbol: str) -> Optional[Dict]:
        """Fiyat, degisim, hacim verisini finans.mynet.com'dan ceker."""
        return self.mynet.get_price(symbol)

    def get_all_prices(self) -> list:
        """Tum hisselerin anlik fiyatlarini ceker."""
        return self.mynet.fetch_all()

    def get_market_cap(self, symbol: str) -> Optional[float]:
        """Piyasa degerini isyatirim.com.tr'den ceker (TL olarak)."""
        return self.isyatirim.get_market_cap(symbol)

    def get_net_debt(self, symbol: str) -> Optional[float]:
        """Net borcu isyatirim.com.tr'den ceker (TL olarak)."""
        return self.isyatirim.get_net_debt(symbol)

    def get_float_data(self, symbol: str) -> Optional[Dict]:
        """
        Fiili dolasim verisini ceker.
        Oncelik: kap.org.tr -> isyatirim.com.tr
        """
        # Once KAP'tan dene
        kap_data = self.kap.get_float_data(symbol)
        if kap_data and kap_data.get("floating_shares", 0) > 0:
            return kap_data

        # KAP yoksa isyatirim'dan
        isy_data = self.isyatirim.get_float_data(symbol)
        if isy_data:
            return {
                "floating_shares": isy_data.get("floating_shares", 0),
                "float_rate": isy_data.get("float_rate", 0),
            }

        return None

    def get_history(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """yfinance ile gecmis fiyat verisini ceker."""
        import yfinance as yf
        period_map = {
            "6ay": "6mo", "1y": "1y", "2y": "2y", "5y": "5y",
            "6mo": "6mo", "3mo": "3mo", "3y": "3y", "10y": "10y",
        }
        yf_period = period_map.get(period, "1y")
        try:
            ticker = yf.Ticker(f"{symbol}.IS")
            hist = ticker.history(period=yf_period)
            if hist is not None and not hist.empty:
                return hist
        except Exception:
            pass
        return None

    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """Tum sirket bilgilerini birlestirir."""
        price_data = self.get_price_data(symbol)
        company_data = self.isyatirim.get_company_data(symbol)
        float_data = self.get_float_data(symbol)

        if not price_data and not company_data:
            return None

        result = {
            "symbol": symbol,
            "last_price": price_data.get("last_price", 0) if price_data else 0,
            "change_pct": price_data.get("change_pct", 0) if price_data else 0,
            "volume": price_data.get("volume", 0) if price_data else 0,
            "company_name": price_data.get("company_name", "") if price_data else "",
        }

        if company_data:
            result["market_cap"] = company_data.get("market_cap_mn_tl", 0) * 1_000_000
            result["market_cap_mn"] = company_data.get("market_cap_mn_tl", 0)
            result["net_debt"] = company_data.get("net_debt_mn_tl", 0) * 1_000_000
            result["net_debt_mn"] = company_data.get("net_debt_mn_tl", 0)
            result["pe"] = company_data.get("pe")
            result["pb"] = company_data.get("pb")
            result["total_shares"] = company_data.get("total_shares", 0)

        if float_data:
            result["float_rate"] = float_data.get("float_rate", 0)
            result["floating_shares"] = float_data.get("floating_shares", 0)

        return result
