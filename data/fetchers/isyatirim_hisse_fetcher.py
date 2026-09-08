import json
import pandas as pd
from typing import Optional, Dict, List
from datetime import date, timedelta

try:
    from isyatirimhisse import fetch_stock_data, fetch_financials
except ImportError:
    fetch_stock_data = None
    fetch_financials = None


class IsYatirimHisseFetcher:
    """isyatirimhisse kutuphanesi ile toplu veri ceker."""

    def __init__(self):
        self._cache_stock = {}
        self._cache_fin = {}

    @property
    def available(self) -> bool:
        return fetch_stock_data is not None and fetch_financials is not None

    def fetch_all_stock_data(self, symbols: List[str], start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Tum hisselerin fiyat/piyasa degeri verisini toplu ceker."""
        if not self.available:
            return pd.DataFrame()
        end = date.today()
        start = end - timedelta(days=365)
        start_date = start_date or start.strftime("%d-%m-%Y")
        end_date = end_date or end.strftime("%d-%m-%Y")
        try:
            df = fetch_stock_data(symbols=symbols, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            print(f"[IsYatirimHisse] Hisse verisi hatasi: {e}")
            return pd.DataFrame()

    def fetch_financials(self, symbols: List[str], start_year: int, end_year: int) -> pd.DataFrame:
        """Tum hisselerin finansal tablo verisini ceker."""
        if not self.available:
            return pd.DataFrame()
        try:
            df = fetch_financials(symbols=symbols, start_year=start_year, end_year=end_year, financial_group='1')
            return df
        except Exception as e:
            print(f"[IsYatirimHisse] Finansal tablo hatasi: {e}")
            return pd.DataFrame()

    def extract_fundamentals(self, fin_df: pd.DataFrame, symbols: List[str]) -> Dict[str, Dict]:
        """Extract the latest available period and retain all available periods."""
        results = {}

        for code in symbols:
            stock_fin = fin_df[fin_df['SYMBOL'] == code]
            if stock_fin.empty:
                continue

            data = {}

            # The library returns columns such as 2026/3, 2026/6, etc.
            period_cols = [c for c in stock_fin.columns if str(c)[:4].isdigit()]
            if not period_cols:
                continue
            available_periods = [
                col for col in period_cols if stock_fin[col].notna().any()
            ]
            if not available_periods:
                continue
            latest_period = available_periods[-1]

            def number(value):
                if pd.isna(value):
                    return None
                if isinstance(value, str):
                    value = value.replace(".", "").replace(",", ".").strip()
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None

            def item_value(row):
                return number(row[latest_period])

            periods = {}
            for period in available_periods:
                period_values = {}
                for _, row in stock_fin.iterrows():
                    value = number(row[period])
                    if value is not None:
                        item_code = str(row["FINANCIAL_ITEM_CODE"])
                        item_name = str(row.get("FINANCIAL_ITEM_NAME_TR", "")).lower()
                        key = item_code
                        if item_code == "2OA" or "ödenmiş sermaye" in item_name:
                            key = "paid_in_capital"
                        elif item_code == "2ODB" or "özkaynak" in item_name:
                            key = "total_equity"
                        elif item_code == "3L" or "net kâr" in item_name or "net kar" in item_name:
                            key = "net_income"
                        period_values[key] = value
                periods[str(period)] = period_values

            # Codes are kept for compatibility; descriptions cover variations
            # between financial groups and future library releases.
            for _, row in stock_fin.iterrows():
                item_code = str(row["FINANCIAL_ITEM_CODE"])
                item_name = str(row.get("FINANCIAL_ITEM_NAME_TR", "")).lower()
                val = item_value(row)
                if val is None:
                    continue
                if item_code == "2AA":
                    data["short_term_debt"] = val
                elif item_code == "2BA":
                    data["long_term_debt"] = val
                elif item_code == "1AA":
                    data["cash"] = val
                elif item_code == "3ZD":
                    data["eps"] = val
                elif item_code == "2OA" or "ödenmiş sermaye" in item_name:
                    data["paid_in_capital"] = val
                elif item_code == "2ODB" or "özkaynak" in item_name:
                    data["total_equity"] = val
                elif item_code == "3C":
                    data["revenue"] = val
                elif item_code == "3L" or "net kâr" in item_name or "net kar" in item_name:
                    data["net_income"] = val

            data["financial_period"] = str(latest_period)
            data["financial_periods"] = json.dumps(periods, ensure_ascii=False)

            # Net borc hesapla: kisa vadeli + uzun vadeli - nakit
            st_debt = data.get('short_term_debt', 0) or 0
            lt_debt = data.get('long_term_debt', 0) or 0
            cash = data.get('cash', 0) or 0
            data['net_debt'] = st_debt + lt_debt - cash
            data['net_debt_mn'] = data['net_debt'] / 1e6

            results[code] = data

        return results

    def fetch_and_extract(self, symbols: List[str], start_year: int = None, end_year: int = None) -> Dict[str, Dict]:
        """Fetch library data once and return normalized fundamentals per symbol."""
        if not self.available or not symbols:
            return {}

        stock_df = self.fetch_all_stock_data(symbols)
        financial_df = self.fetch_financials(
            symbols,
            start_year or date.today().year - 2,
            end_year or date.today().year,
        )
        result = self.extract_stock_info(stock_df)
        financials = self.extract_fundamentals(financial_df, symbols)
        for code, values in financials.items():
            result.setdefault(code, {}).update(values)
        return result

    def extract_stock_info(self, stock_df: pd.DataFrame) -> Dict[str, Dict]:
        """Hisse verisinden piyasa degeri ve toplam hisseyi cikarir."""
        results = {}

        if stock_df.empty:
            return results

        for _, row in stock_df.iterrows():
            code = row.get('HGDG_HS_KODU', '')
            if not code:
                continue

            def number(*names):
                for name in names:
                    value = row.get(name, 0)
                    if pd.notna(value) and value not in ("", None):
                        try:
                            return float(str(value).replace(".", "").replace(",", "."))
                        except (TypeError, ValueError):
                            continue
                return 0.0

            price = number("HGDG_KAPANIS", "KAPANIS", "CLOSING")
            mcap = number("PD", "PIYASA_DEGERI", "MARKET_CAP")
            shares = number("SERMAYE", "SERMAYE_MIKTARI", "TOTAL_SHARES")

            results[code] = {
                'last_price': price,
                'market_cap': mcap,
                'market_cap_mn': mcap / 1e6 if mcap else 0,
                'total_shares': shares,
            }

        return results
