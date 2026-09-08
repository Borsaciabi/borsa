import pandas as pd
from typing import List, Dict
from datetime import datetime


class ExcelImporter:
    """Excel'den portfoy verisi aktaran sinif."""

    EXPECTED_COLUMNS = {
        "hisse": ["hisse", "kod", "stock", "symbol", "hissekodu", "hisse_kodu"],
        "alis_fiyati": ["alis", "alis_fiyati", "alisfiyati", "buy_price", "alis_fiyat", "maliyet", "fiyat", "price"],
        "miktar": ["miktar", "adet", "lot", "quantity", "qty"],
    }

    def parse_turkish_number(self, val) -> float:
        """Turk sayi formatini float'a cevirir."""
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            cleaned = val.strip().replace(".", "").replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        return 0.0

    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Excel sutunlarini otomatik algilar."""
        col_map = {}
        df_cols = [c.lower().strip() for c in df.columns]

        for target_key, possible_names in self.EXPECTED_COLUMNS.items():
            for i, col in enumerate(df_cols):
                if col in possible_names:
                    col_map[target_key] = df.columns[i]
                    break

        return col_map

    def import_from_excel(self, file_path: str) -> List[Dict]:
        """Excel dosyasindan portfoy verisi okur."""
        try:
            # Excel dosyasini oku
            df = pd.read_excel(file_path, engine="openpyxl")

            if df.empty:
                return []

            # Sutunlari algila
            col_map = self.detect_columns(df)

            if "hisse" not in col_map:
                raise ValueError(
                    "Excel dosyasinda 'hisse' sutunu bulunamadi. "
                    "Sutun basliklari: " + ", ".join(df.columns.tolist())
                )

            results = []
            for _, row in df.iterrows():
                stock_code = str(row[col_map["hisse"]]).strip().upper()
                if not stock_code or stock_code == "NAN":
                    continue

                buy_price = 0.0
                if "alis_fiyati" in col_map:
                    buy_price = self.parse_turkish_number(row[col_map["alis_fiyati"]])

                quantity = 0
                if "miktar" in col_map:
                    quantity = int(self.parse_turkish_number(row[col_map["miktar"]]))

                # Eger satis fiyati varsa
                sell_price = 0.0
                for sell_col in ["satis", "satisfiyati", "sell_price", "satis_fiyat"]:
                    if sell_col in [c.lower() for c in df.columns]:
                        for orig_col in df.columns:
                            if orig_col.lower() == sell_col:
                                sell_price = self.parse_turkish_number(row[orig_col])
                                break

                # Tarih
                buy_date = datetime.now().strftime("%Y-%m-%d")
                for date_col in ["tarih", "date", "alis_tarihi", "buy_date"]:
                    if date_col in [c.lower() for c in df.columns]:
                        for orig_col in df.columns:
                            if orig_col.lower() == date_col:
                                val = row[orig_col]
                                if isinstance(val, datetime):
                                    buy_date = val.strftime("%Y-%m-%d")
                                elif isinstance(val, str):
                                    buy_date = val
                                break

                results.append({
                    "stock_code": stock_code,
                    "buy_price": buy_price,
                    "quantity": quantity,
                    "sell_price": sell_price,
                    "buy_date": buy_date,
                })

            return results

        except Exception as e:
            print(f"[ExcelImporter] Hata: {e}")
            return []

    def import_from_csv(self, file_path: str) -> List[Dict]:
        """CSV dosyasindan portfoy verisi okur."""
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return []

            col_map = self.detect_columns(df)

            if "hisse" not in col_map:
                raise ValueError("CSV dosyasinda 'hisse' sutunu bulunamadi")

            results = []
            for _, row in df.iterrows():
                stock_code = str(row[col_map["hisse"]]).strip().upper()
                if not stock_code or stock_code == "NAN":
                    continue

                buy_price = 0.0
                if "alis_fiyati" in col_map:
                    buy_price = self.parse_turkish_number(row[col_map["alis_fiyati"]])

                quantity = 0
                if "miktar" in col_map:
                    quantity = int(self.parse_turkish_number(row[col_map["miktar"]]))

                results.append({
                    "stock_code": stock_code,
                    "buy_price": buy_price,
                    "quantity": quantity,
                    "sell_price": 0.0,
                    "buy_date": datetime.now().strftime("%Y-%m-%d"),
                })

            return results

        except Exception as e:
            print(f"[ExcelImporter] CSV Hata: {e}")
            return []
