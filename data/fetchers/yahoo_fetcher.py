import yfinance as yf
from typing import Optional, Dict, List


class YahooFetcher:
    """Yahoo Finance'dan temel veri ceker."""

    def __init__(self):
        self._cache = {}

    def get_company_data(self, symbol: str) -> Optional[Dict]:
        """Tekil hisse icin temel veri ceker."""
        if symbol in self._cache:
            return self._cache[symbol]

        try:
            ticker = yf.Ticker(f"{symbol}.IS")
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                return None

            market_cap = info.get("marketCap", 0) or 0
            total_debt = info.get("totalDebt", 0) or 0
            total_cash = info.get("totalCash", 0) or 0
            shares = info.get("sharesOutstanding", 0) or 0
            float_shares = info.get("floatShares", 0) or 0
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")

            result = {
                "symbol": symbol,
                "market_cap_tl": market_cap,
                "market_cap_mn": market_cap / 1e6 if market_cap else 0,
                "total_debt_tl": total_debt,
                "total_debt_mn": total_debt / 1e6 if total_debt else 0,
                "total_cash_tl": total_cash,
                "total_cash_mn": total_cash / 1e6 if total_cash else 0,
                "net_debt_tl": total_debt - total_cash,
                "net_debt_mn": (total_debt - total_cash) / 1e6 if total_debt else 0,
                "total_shares": shares,
                "floating_shares": float_shares,
                "float_rate": float_shares / shares * 100 if shares else 0,
                "pe": pe,
                "pb": pb,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "bid": info.get("bid"),
                "ask": info.get("ask"),
                "previous_close": info.get("previousClose"),
                "open": info.get("open"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "average_volume_3m": info.get("averageVolume").__float__() if info.get("averageVolume") else None,
                "year_change_pct": (info.get("52WeekChange") or 0) * 100,
                "eps": info.get("trailingEps"),
                "revenue": info.get("totalRevenue"),
                "net_income": info.get("netIncomeToCommon"),
                "dividend_rate": info.get("dividendRate"),
                "dividend_yield": info.get("dividendYield"),
                "return_on_assets": info.get("returnOnAssets"),
                "return_on_equity": info.get("returnOnEquity"),
                "gross_margin": info.get("grossMargins"),
                "ebitda": info.get("ebitda"),
                "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
                "beta": info.get("beta"),
                "book_value": info.get("bookValue"),
                "earnings_date": info.get("earningsTimestamp"),
            }

            self._cache[symbol] = result
            return result

        except Exception:
            return None

    def get_batch_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Coklu hisse icin toplu veri ceker."""
        results = {}
        for symbol in symbols:
            data = self.get_company_data(symbol)
            if data:
                results[symbol] = data
        return results

    def get_market_cap(self, symbol: str) -> Optional[float]:
        data = self.get_company_data(symbol)
        return data.get("market_cap_tl") if data else None

    def get_net_debt(self, symbol: str) -> Optional[float]:
        data = self.get_company_data(symbol)
        return data.get("net_debt_tl") if data else None

    def get_float_data(self, symbol: str) -> Optional[Dict]:
        data = self.get_company_data(symbol)
        if data:
            return {
                "float_rate": data.get("float_rate", 0),
                "total_shares": data.get("total_shares", 0),
                "floating_shares": data.get("floating_shares", 0),
            }
        return None
