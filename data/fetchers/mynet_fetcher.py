import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, List


def parse_turkish_number(text: str) -> float:
    """Turk sayi formatini float'a cevirir. Orn: 4.907,3 -> 4907.3"""
    if not text or text.strip() in ("A/D", "-", "", "N/A"):
        return 0.0
    cleaned = text.strip().replace(".", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class MynetFetcher:
    """finans.mynet.com'dan anlik fiyat ve degisim verisi ceker."""

    URL = "https://finans.mynet.com/borsa/hisseler/"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    def __init__(self):
        self._cache = {}
        self._all_stocks = None

    def fetch_all(self) -> List[Dict]:
        """Tum BIST hisselerinin anlik fiyatlarini ceker."""
        try:
            resp = requests.get(self.URL, headers=self.HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            table = soup.select_one("table.finans-data-table")
            if not table:
                return []

            rows = table.select("tbody.tbody-type-default tr")
            stocks = []

            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                name_link = cols[0].select_one("a.ft-name")
                if not name_link:
                    continue

                stock_code = name_link.contents[0].strip()
                company_span = name_link.select_one("span.hide-m")
                company_name = company_span.get_text(strip=True) if company_span else ""

                last_price = parse_turkish_number(cols[1].get_text(strip=True))

                change_span = cols[2].select_one("span.ft-change")
                change_pct = 0.0
                direction = "flat"
                if change_span:
                    change_text = change_span.get_text(strip=True)
                    pct_str = re.sub(r"[▲▼%\s]", "", change_text)
                    change_pct = float(pct_str.replace(",", ".")) if pct_str else 0.0
                    classes = change_span.get("class", [])
                    if "is-up" in classes:
                        direction = "up"
                    elif "is-down" in classes:
                        direction = "down"

                volume = parse_turkish_number(cols[3].get_text(strip=True))

                stocks.append({
                    "stock_code": stock_code,
                    "company_name": company_name,
                    "last_price": last_price,
                    "change_pct": change_pct,
                    "change_direction": direction,
                    "volume": volume,
                })

            self._all_stocks = stocks
            return stocks

        except Exception as e:
            print(f"[MynetFetcher] Hata: {e}")
            return []

    def get_price(self, symbol: str) -> Optional[Dict]:
        """Tekil hisse fiyati ceker."""
        if not self._all_stocks:
            self.fetch_all()

        for stock in self._all_stocks or []:
            if stock["stock_code"].upper() == symbol.upper():
                return stock

        return None

    def get_prices_batch(self, symbols: list) -> Dict[str, Dict]:
        """Coklu hisse fiyati ceker."""
        if not self._all_stocks:
            self.fetch_all()

        result = {}
        for stock in self._all_stocks or []:
            if stock["stock_code"].upper() in [s.upper() for s in symbols]:
                result[stock["stock_code"]] = stock

        return result
