import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict


def parse_turkish_number(text: str) -> float:
    """Turk sayi formatini float'a cevirir."""
    if not text or text.strip() in ("A/D", "-", "", "N/A"):
        return 0.0
    cleaned = text.strip().replace(".", "").replace(",", ".")
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class IsYatirimFetcher:
    """isyatirim.com.tr'den piyasa degeri ve net borcu ceker."""

    BASE_URL = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9",
    }

    def __init__(self):
        self._cache = {}

    def get_company_data(self, symbol: str) -> Optional[Dict]:
        """
        Sirket karti sayfasindan veri ceker:
        - Piyasa Degeri (mn TL)
        - Net Borc (mn TL)
        - Halka Aciklik Orani (%)
        - Sermaye (mn TL) -> Toplam Hisse
        """
        if symbol in self._cache:
            return self._cache[symbol]

        try:
            url = f"{self.BASE_URL}/sirket-karti.aspx?hisse={symbol}"
            resp = requests.get(url, headers=self.HEADERS, timeout=30)
            resp.encoding = "windows-1254"
            soup = BeautifulSoup(resp.text, "html.parser")

            result = {"symbol": symbol}

            # Cari Degerler tablosundan veri cek
            for th in soup.find_all("th"):
                label = th.get_text(strip=True)
                td = th.find_next_sibling("td")
                if not td:
                    continue
                value_text = td.get_text(strip=True)

                if "Halka" in label and "Oran" in label:
                    result["float_rate_pct"] = parse_turkish_number(value_text)

                elif "Piyasa" in label and "eri" in label:
                    result["market_cap_text"] = value_text
                    val = value_text.replace("mnTL", "").replace("mn $", "").strip()
                    result["market_cap_mn_tl"] = parse_turkish_number(val)

                elif "Net" in label and "Bor" in label:
                    result["net_debt_text"] = value_text
                    val = value_text.replace("mnTL", "").replace("mn $", "").strip()
                    result["net_debt_mn_tl"] = parse_turkish_number(val)

                elif label.startswith("F/K"):
                    result["pe"] = parse_turkish_number(value_text)

                elif "PD/DD" in label:
                    result["pb"] = parse_turkish_number(value_text)

            # Sermaye (Odenmis Sermaye) - Mali Tablo'dan
            sermaye_row = soup.find("tr", attrs={"data-kodu": "2OA"})
            if sermaye_row:
                td_current = sermaye_row.find("td", class_="data-ozkaynak_1")
                if td_current:
                    result["capital_mn_tl"] = parse_turkish_number(
                        td_current.get_text(strip=True)
                    )

            # Toplam hisse = Sermaye (mn TL) * 1,000,000 (BIST itibari deger 1 TL)
            capital_mn = result.get("capital_mn_tl", 0)
            if capital_mn:
                result["total_shares"] = int(capital_mn * 1_000_000)

            # Fiili dolasim hisse = Toplam Hisse * Halka Aciklik / 100
            float_rate = result.get("float_rate_pct", 0)
            total_shares = result.get("total_shares", 0)
            if total_shares and float_rate:
                result["floating_shares"] = int(total_shares * float_rate / 100)

            self._cache[symbol] = result
            return result

        except Exception as e:
            print(f"[IsYatirimFetcher] {symbol} hatasi: {e}")
            return None

    def get_market_cap(self, symbol: str) -> Optional[float]:
        """Piyasa degerini mn TL olarak ceker."""
        data = self.get_company_data(symbol)
        if data:
            return data.get("market_cap_mn_tl", 0) * 1_000_000  # TL'ye cevir
        return None

    def get_net_debt(self, symbol: str) -> Optional[float]:
        """Net borcu mn TL olarak ceker."""
        data = self.get_company_data(symbol)
        if data:
            return data.get("net_debt_mn_tl", 0) * 1_000_000  # TL'ye cevir
        return None

    def get_float_data(self, symbol: str) -> Optional[Dict]:
        """Fiili dolasim orani ve adedini ceker."""
        data = self.get_company_data(symbol)
        if data:
            return {
                "float_rate": data.get("float_rate_pct", 0),
                "total_shares": data.get("total_shares", 0),
                "floating_shares": data.get("floating_shares", 0),
            }
        return None
