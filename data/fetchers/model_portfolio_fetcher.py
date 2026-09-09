import json
import re
from collections import Counter
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class ModelPortfolioFetcher:
    SOURCES = {
        "Halk Yatırım": "https://hlyaos.halkyatirim.com.tr/ModelPortfoy",
        "Fintables": "https://fintables.com/analist-tavsiyeleri",
        "Ak Yatırım": "https://www.akyatirim.com.tr/tr/raporlarimiz/model-portfoy",
        "A1 Capital": "https://a1capital.com.tr/model-portfoy/",
        "Garanti BBVA Yatırım": "https://www.garantibbvayatirim.com.tr/arastirma-raporlari/model-portfoy",
    }
    HEADERS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "tr-TR,tr;q=0.9"}
    DATE_FORMATS = ("%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y")
    SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,6}$")

    def fetch_all(self):
        return [
            self._fetch_halk(),
            self._fetch_fintables(),
            self._fetch_ak(),
            self._fetch_a1(),
            self._fetch_garanti(),
        ]

    def _fetch_halk(self):
        source = "Halk Yatırım"
        try:
            soup = self._soup(self.SOURCES[source])
            records = []
            for table in soup.find_all("table"):
                headers = self._cells(table.find("tr"))
                if "Sembol" not in headers or "Gir.Tarih" not in headers:
                    continue
                symbol_index = headers.index("Sembol")
                date_index = headers.index("Gir.Tarih")
                for row in table.select("tbody tr"):
                    cells = self._cells(row)
                    if len(cells) > max(symbol_index, date_index) and self._symbol(cells[symbol_index]):
                        records.append({"symbol": self._symbol(cells[symbol_index]), "date": cells[date_index]})
                if records:
                    break
            return self._result(source, records)
        except Exception as exc:
            return self._failed(source, exc)

    def _fetch_ak(self):
        source = "Ak Yatırım"
        url = "https://www.akyatirim.com.tr/umbraco/surface/api/ModelPortfoyView?son_donem=true&gecikmeli_fiyat=true"
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=30)
            response.raise_for_status()
            payload = response.json()
            records = self._find_records(payload)
            return self._result(source, records, self.SOURCES[source])
        except Exception as exc:
            return self._failed(source, exc)

    def _fetch_a1(self):
        source = "A1 Capital"
        try:
            soup = self._soup(self.SOURCES[source])
            records = []
            for table in soup.find_all("table"):
                headers = self._cells(table.find("tr"))
                if not headers or headers[0] != "Hisse":
                    continue
                for row in table.select("tbody tr"):
                    cells = self._cells(row)
                    if len(cells) >= 2 and self._symbol(cells[0]):
                        records.append({"symbol": self._symbol(cells[0]), "date": cells[1]})
                if records:
                    break
            return self._result(source, records)
        except Exception as exc:
            return self._failed(source, exc)

    def _fetch_fintables(self):
        return self._fetch_page_source("Fintables")

    def _fetch_garanti(self):
        return self._fetch_page_source("Garanti BBVA Yatırım")

    def _fetch_page_source(self, source):
        try:
            response = requests.get(self.SOURCES[source], headers=self.HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            if source == "Garanti BBVA Yatırım":
                return self._failed(source, "Model portfoy listesi sayfada herkese acik degil")
            text = soup.get_text(" ", strip=True)
            records = [{"symbol": symbol, "date": ""} for symbol in self._symbols(text)]
            return self._result(source, records)
        except Exception as exc:
            return self._failed(source, exc)

    def _result(self, source, records, url=None):
        unique = {}
        for record in records:
            symbol = self._symbol(record.get("symbol", ""))
            if symbol:
                unique[symbol] = {"symbol": symbol, "date": record.get("date", "")}
        dates = [self._parse_date(item["date"]) for item in unique.values()]
        dates = [value for value in dates if value]
        return {
            "source": source,
            "url": url or self.SOURCES[source],
            "updated_at": max(dates).strftime("%d.%m.%Y") if dates else "Sayfada belirtilmemiş",
            "records": list(unique.values()),
            "available": True,
        }

    def _failed(self, source, error):
        return {
            "source": source,
            "url": self.SOURCES[source],
            "updated_at": "-",
            "records": [],
            "available": False,
            "error": str(error),
        }

    def _soup(self, url):
        response = requests.get(url, headers=self.HEADERS, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    @classmethod
    def _find_records(cls, payload):
        if isinstance(payload, dict):
            for key in ("hisses", "data", "datas", "Data"):
                if key in payload:
                    records = cls._find_records(payload[key])
                    if records:
                        return records
            return []
        if not isinstance(payload, list):
            return []
        result = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            symbol = item.get("sembol") or item.get("symbol") or item.get("kod")
            if symbol:
                result.append({
                    "symbol": symbol,
                    "date": (
                        item.get("portfoy_giris_tarihi")
                        or item.get("son_fiyat_tarihi_gecikmeli")
                        or item.get("giris_tarihi")
                        or item.get("girisTarihi")
                        or ""
                    ),
                })
            else:
                result.extend(cls._find_records(item))
        return result

    @staticmethod
    def _cells(row):
        if row is None:
            return []
        return [cell.get_text(" ", strip=True) for cell in row.select("th,td")]

    @classmethod
    def _symbol(cls, value):
        value = str(value or "").strip().upper()
        return value if cls.SYMBOL_RE.match(value) else None

    @classmethod
    def _symbols(cls, text):
        return [value for value in re.findall(r"\b[A-Z0-9]{3,6}\b", text) if cls._symbol(value)]

    @classmethod
    def _parse_date(cls, value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", ""))
        except ValueError:
            pass
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(str(value).strip(), fmt)
            except ValueError:
                continue
        return None


def rank_common_recommendations(sources):
    counts = Counter()
    for source in sources:
        counts.update({record["symbol"] for record in source["records"]})
    return [
        {"symbol": symbol, "source_count": count}
        for symbol, count in counts.most_common()
    ]
