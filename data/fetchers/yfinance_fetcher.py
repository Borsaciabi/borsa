import yfinance as yf
import pandas as pd
from typing import Optional, Dict


class YFinanceFetcher:
    """yfinance ile yedek veri ceken sinif."""

    def get_ticker(self, symbol: str):
        return yf.Ticker(f"{symbol}.IS")

    def get_info(self, symbol: str) -> Optional[Dict]:
        try:
            ticker = self.get_ticker(symbol)
            info = ticker.info
            return {
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "market_cap": info.get("marketCap"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "float_shares": info.get("floatShares"),
                "book_value": info.get("bookValue"),
                "pb": info.get("priceToBook"),
                "pe": info.get("trailingPE"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                "enterprise_value": info.get("enterpriseValue"),
                "eps": info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "revenue": info.get("totalRevenue"),
                "net_income": info.get("netIncomeToCommon"),
            }
        except Exception as e:
            print(f"[YFinanceFetcher] {symbol} hatasi: {e}")
            return None

    def get_history(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        try:
            ticker = self.get_ticker(symbol)
            return ticker.history(period=period)
        except Exception as e:
            print(f"[YFinanceFetcher] {symbol} gecmis hatasi: {e}")
            return None

    def get_income_stmt(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            ticker = self.get_ticker(symbol)
            return ticker.income_stmt
        except Exception:
            return None

    def get_balance_sheet(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            ticker = self.get_ticker(symbol)
            return ticker.balance_sheet
        except Exception:
            return None
