import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import json


class WebScraper:
    """Web sitelerinden temel analiz verileri ceken sinif."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        })

    def get_bigpara_stock(self, symbol: str) -> Optional[Dict]:
        """bigpara.hurriyet.com.tr'den hisse verisi ceker."""
        try:
            url = f"https://bigpara.hurriyet.com.tr/borsa/hisse-fiyatlari/{symbol.lower()}/"
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "lxml")

            # Fiyat bilgisi
            price_elem = soup.find("span", {"id": "csrf_token"})
            # Simplified extraction
            data = {"source": "bigpara", "symbol": symbol}

            # Tablolardan veri cek
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        val = cells[1].get_text(strip=True)
                        data[key] = val

            return data
        except Exception as e:
            print(f"[WebScraper] bigpara {symbol} hatasi: {e}")
            return None

    def get_bilancoveri_data(self, symbol: str) -> Optional[Dict]:
        """bilancoveri.com'dan finansal veri ceker."""
        try:
            url = f"https://bilancoveri.com/{symbol.lower()}"
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "lxml")

            data = {"source": "bilancoveri", "symbol": symbol}

            # Tablolardan veri cek
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        val = cells[1].get_text(strip=True)
                        data[key] = val

            return data
        except Exception as e:
            print(f"[WebScraper] bilancoveri {symbol} hatasi: {e}")
            return None

    def get_mynet_stock(self, symbol: str) -> Optional[Dict]:
        """finans.mynet.com'dan hisse verisi ceker."""
        try:
            url = f"https://finans.mynet.com/borsa/hisseler/{symbol.lower()}/"
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.content, "lxml")

            data = {"source": "mynet", "symbol": symbol}

            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        val = cells[1].get_text(strip=True)
                        data[key] = val

            return data
        except Exception as e:
            print(f"[WebScraper] mynet {symbol} hatasi: {e}")
            return None

    def get_all_fundamentals(self, symbol: str) -> Dict:
        """Tum kaynaklardan temel verileri toplar."""
        result = {"symbol": symbol}

        bigpara = self.get_bigpara_stock(symbol)
        if bigpara:
            result["bigpara"] = bigpara

        bilancoveri = self.get_bilancoveri_data(symbol)
        if bilancoveri:
            result["bilancoveri"] = bilancoveri

        mynet = self.get_mynet_stock(symbol)
        if mynet:
            result["mynet"] = mynet

        return result
