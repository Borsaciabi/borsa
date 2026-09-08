import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, List


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


class KapFetcher:
    """kap.org.tr'den fiili dolasimdaki pay verisini ceker."""

    URL = "https://kap.org.tr/tr/tumKalemler/kpy41_acc5_fiili_dolasimdaki_pay"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9",
    }

    def __init__(self):
        self._all_data = None

    def fetch_all(self) -> List[Dict]:
        """Tum hisselerin fiili dolasim verisini ceker."""
        try:
            resp = requests.get(self.URL, headers=self.HEADERS, timeout=30)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            results = []

            # SSR tablosunu bul
            ssr_container = soup.find("div", id="S:3")
            if ssr_container:
                table = ssr_container.find("table", class_="table-fixed")
                if table:
                    tbody = table.find("tbody")
                    if tbody:
                        rows = tbody.find_all("tr")
                        for row in rows:
                            cells = row.find_all("td")
                            if len(cells) >= 4:
                                company_name_tag = cells[0].find("a")
                                company_name = (
                                    company_name_tag.get_text(strip=True)
                                    if company_name_tag
                                    else cells[0].get_text(strip=True)
                                )
                                stock_code = cells[1].get_text(strip=True)
                                floating_shares = parse_turkish_number(
                                    cells[2].get_text(strip=True)
                                )
                                floating_ratio = parse_turkish_number(
                                    cells[3].get_text(strip=True)
                                )

                                results.append({
                                    "company_name": company_name,
                                    "stock_code": stock_code,
                                    "floating_shares": floating_shares,
                                    "floating_ratio_pct": floating_ratio,
                                })

            self._all_data = results
            return results

        except Exception as e:
            print(f"[KapFetcher] Hata: {e}")
            return []

    def get_float_data(self, symbol: str) -> Optional[Dict]:
        """Tekil hissenin fiili dolasim verisini ceker."""
        if not self._all_data:
            self.fetch_all()

        for item in self._all_data or []:
            if item["stock_code"].upper() == symbol.upper():
                return {
                    "floating_shares": item["floating_shares"],
                    "float_rate": item["floating_ratio_pct"],
                }

        return None
