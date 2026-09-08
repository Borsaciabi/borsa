import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from data.fetchers.bist_fetcher import BistFetcher


class TechnicalAnalyzer:
    """200 gunluk teknik analiz yapan sinif."""

    def __init__(self):
        self.bist = BistFetcher()

    def calculate_ma(self, prices: pd.Series, window: int) -> pd.Series:
        """Hareketli ortalama hesaplar."""
        return prices.rolling(window=window).mean()

    def calculate_ema(self, prices: pd.Series, span: int) -> pd.Series:
        """Ustel hareketli ortalama hesaplar."""
        return prices.ewm(span=span, adjust=False).mean()

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index) hesaplar."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(
        self, prices: pd.Series,
        fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, pd.Series]:
        """MACD hesaplar."""
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

    def calculate_bollinger_bands(
        self, prices: pd.Series, window: int = 20, num_std: float = 2.0
    ) -> Dict[str, pd.Series]:
        """Bollinger Bantları hesaplar."""
        ma = self.calculate_ma(prices, window)
        std = prices.rolling(window=window).std()
        upper = ma + (num_std * std)
        lower = ma - (num_std * std)
        return {"upper": upper, "middle": ma, "lower": lower}

    def calculate_volume_avg(self, volume: pd.Series, window: int) -> pd.Series:
        """Hacim ortalaması hesaplar."""
        return volume.rolling(window=window).mean()

    def analyze(self, symbol: str, period: str = "1y") -> Optional[Dict]:
        """Kapsamlı teknik analiz yapar."""
        history = self.bist.get_history(symbol, period)
        if history is None or history.empty:
            return None

        close = history["Close"]
        volume = history["Volume"]

        # Hareketli ortalamalar
        ma20 = self.calculate_ma(close, 20)
        ma50 = self.calculate_ma(close, 50)
        ma200 = self.calculate_ma(close, 200)

        # RSI
        rsi = self.calculate_rsi(close)

        # MACD
        macd = self.calculate_macd(close)

        # Bollinger Bantları
        bb = self.calculate_bollinger_bands(close)

        # Hacim ortalaması
        vol_avg_20 = self.calculate_volume_avg(volume, 20)
        vol_avg_200 = self.calculate_volume_avg(volume, 200)

        # Son degerler
        current_price = close.iloc[-1]
        current_volume = volume.iloc[-1]

        return {
            "symbol": symbol,
            "current_price": current_price,
            "ma20": ma20.iloc[-1] if len(ma20) > 0 else None,
            "ma50": ma50.iloc[-1] if len(ma50) > 0 else None,
            "ma200": ma200.iloc[-1] if len(ma200) > 0 else None,
            "rsi": rsi.iloc[-1] if len(rsi) > 0 else None,
            "macd": macd["macd"].iloc[-1] if len(macd["macd"]) > 0 else None,
            "macd_signal": macd["signal"].iloc[-1] if len(macd["signal"]) > 0 else None,
            "macd_histogram": macd["histogram"].iloc[-1] if len(macd["histogram"]) > 0 else None,
            "bb_upper": bb["upper"].iloc[-1] if len(bb["upper"]) > 0 else None,
            "bb_middle": bb["middle"].iloc[-1] if len(bb["middle"]) > 0 else None,
            "bb_lower": bb["lower"].iloc[-1] if len(bb["lower"]) > 0 else None,
            "volume": current_volume,
            "volume_avg_20": vol_avg_20.iloc[-1] if len(vol_avg_20) > 0 else None,
            "volume_avg_200": vol_avg_200.iloc[-1] if len(vol_avg_200) > 0 else None,
            "price_vs_ma200": ((current_price / ma200.iloc[-1]) - 1) * 100 if len(ma200) > 0 and ma200.iloc[-1] > 0 else None,
            "price_vs_ma50": ((current_price / ma50.iloc[-1]) - 1) * 100 if len(ma50) > 0 and ma50.iloc[-1] > 0 else None,
            "price_history": close,
            "volume_history": volume,
            "ma20_series": ma20,
            "ma50_series": ma50,
            "ma200_series": ma200,
            "bb_upper_series": bb["upper"],
            "bb_lower_series": bb["lower"],
        }
