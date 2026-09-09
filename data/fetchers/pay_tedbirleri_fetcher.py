from datetime import datetime

import requests
from bs4 import BeautifulSoup


class PayTedbirleriFetcher:
    """Halk Yatirim'in aktif pay tedbirlerini okur."""

    URL = "https://hlyaos.halkyatirim.com.tr/PayTedbirleri"

    def fetch(self, symbol=None):
        response = requests.get(
            self.URL,
            headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "tr-TR,tr;q=0.9"},
            timeout=30,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.select_one("#SelectAllWebGrid")
        if table is None:
            raise ValueError("Pay tedbirleri tablosu bulunamadi")

        wanted = symbol.strip().upper() if symbol else None
        result = []
        for row in table.select("tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if len(cells) < 7:
                continue
            code = cells[1].upper()
            if wanted and code != wanted:
                continue
            result.append(
                {
                    "symbol": code,
                    "start_date": self._date(cells[2]),
                    "end_date": self._date(cells[3]),
                    "days_remaining": self._integer(cells[4]),
                    "message": cells[5],
                    "source_date": cells[6],
                    "url": self.URL,
                }
            )
        return result

    @staticmethod
    def _date(value):
        try:
            return datetime.strptime(value, "%d-%m-%Y").date().isoformat()
        except ValueError:
            return value

    @staticmethod
    def _integer(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
