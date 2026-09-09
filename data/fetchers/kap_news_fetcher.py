import json
from datetime import date, timedelta

import requests


class KapNewsFetcher:
    """KAP'in son ODA bildirimlerini okur."""

    API_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
    WARMUP_URL = "https://www.kap.org.tr/tr/bildirim-sorgu"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "tr-TR,tr;q=0.9",
    }

    def fetch(self, symbol=None, days=3, limit=50):
        """Return latest KAP disclosures, optionally filtered by stock code."""
        today = date.today()
        payload = {
            "fromDate": (today - timedelta(days=days)).isoformat(),
            "toDate": today.isoformat(),
            "disclosureClass": "ODA",
            "subjectList": [],
            "mkkMemberOidList": [],
            "inactiveMkkMemberOidList": [],
            "bdkMemberOidList": [],
            "fromSrc": False,
            "disclosureIndexList": [],
        }
        session = requests.Session()
        session.headers.update(self.HEADERS)
        session.get(self.WARMUP_URL, timeout=10)
        response = session.post(self.API_URL, json=payload, timeout=35)
        response.raise_for_status()
        records = json.loads(response.content.decode("utf-8"))
        if not isinstance(records, list):
            raise ValueError("KAP haber servisi beklenmeyen veri dondu")

        symbol = symbol.strip().upper() if symbol else None
        result = []
        for record in records:
            codes = self._stock_codes(record)
            if symbol and symbol not in codes:
                continue
            index = record.get("disclosureIndex")
            if not index:
                continue
            result.append({
                "title": (record.get("summary") or "KAP bildirimi").strip(),
                "company": (record.get("kapTitle") or "").strip(),
                "stock_codes": ", ".join(codes),
                "subject": (record.get("subject") or "").strip(),
                "publish_date": record.get("publishDate") or "",
                "url": f"https://www.kap.org.tr/tr/Bildirim/{index}",
            })
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _stock_codes(record):
        values = []
        for field in ("stockCodes", "relatedStocks"):
            raw = record.get(field) or ""
            values.extend(code.strip().upper() for code in raw.split(",") if code.strip())
        return list(dict.fromkeys(values))
