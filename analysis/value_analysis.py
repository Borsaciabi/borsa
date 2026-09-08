from typing import Optional, Dict, Tuple
from data.fetchers.bist_fetcher import BistFetcher


class ValueAnalyzer:
    """
    Kullanicinin ozel formulu ile deger analizi.

    Formul:
        Hesaplanan Deger = (Piyasa Degeri - Net Borc) x (Fiili Oran / 100)
                          / Fiili Dolasimdaki Hisse Sayisi

        Oran = Son Fiyat / Hesaplanan Deger

    Sinyal Tablosu:
        ORAN > 3,00        -> "Hemen SAT"
        ORAN > 1,50        -> "SAT"
        ORAN > 0,99        -> "Kafana Gore"
        ORAN > 0,70        -> "AL"
        ORAN > 0,000001    -> "Evi Barki Sat"
        ORAN < 0           -> "Borclu"
    """

    SIGNAL_THRESHOLDS = [
        (3.0, "Hemen SAT", "[!]", "red"),
        (1.5, "SAT", "[-]", "orange"),
        (0.99, "Kafana Gore", "[~]", "yellow"),
        (0.70, "AL", "[+]", "green"),
        (0.000001, "Evi Barki Sat", "[++]", "blue"),
        (-float("inf"), "Borclu", "[X]", "gray"),
    ]

    def __init__(self):
        self.bist = BistFetcher()

    def calculate_value(
        self,
        market_cap: float,
        net_debt: float,
        float_ratio: float,
        float_shares: float,
    ) -> float:
        """
        Hesaplanan Deger = (Piyasa Degeri - Net Borc) x (Fiili Oran / 100)
                          / Fiili Dolasimdaki Hisse Sayisi
        """
        enterprise_value = (market_cap - net_debt) * (float_ratio / 100)
        if float_shares == 0:
            return 0.0
        return enterprise_value / float_shares

    def get_signal(self, current_price: float, calculated_value: float) -> Tuple[str, str, str]:
        """Son Fiyat / Hesaplanan Deger oranina gore sinyal uretir."""
        if calculated_value == 0:
            return "Deger Giriniz", "[?]", "white"

        ratio = current_price / calculated_value

        for threshold, signal_name, emoji, color in self.SIGNAL_THRESHOLDS:
            if ratio > threshold:
                return signal_name, emoji, color

        return "Deger Giriniz", "[?]", "white"

    def get_ratio(self, current_price: float, calculated_value: float) -> float:
        """Son Fiyat / Hesaplanan Deger orani."""
        if calculated_value == 0:
            return 0.0
        return current_price / calculated_value

    def get_expected_return(
        self, current_price: float, calculated_value: float
    ) -> float:
        """Kar beklentisi yuzdesini hesaplar."""
        if current_price == 0:
            return 0.0
        return ((calculated_value - current_price) / current_price) * 100

    def analyze(self, symbol: str) -> Optional[Dict]:
        """Tekil hisse icin kapsamli deger analizi yapar."""
        info = self.bist.get_company_info(symbol)
        if not info:
            return None

        current_price = info.get("last_price", 0) or 0
        market_cap = info.get("market_cap", 0) or 0
        net_debt = info.get("net_debt", 0) or 0
        float_rate = info.get("float_rate", 0) or 0
        float_shares = info.get("floating_shares", 0) or 0
        total_shares = info.get("total_shares", 0) or 0

        # Deger hesapla
        calculated_value = self.calculate_value(
            market_cap, net_debt, float_rate, float_shares
        )

        # Sinyal uret
        signal, emoji, color = self.get_signal(current_price, calculated_value)

        # Oran hesapla
        ratio = self.get_ratio(current_price, calculated_value)

        # Kar beklentisi
        expected_return = self.get_expected_return(current_price, calculated_value)

        return {
            "symbol": symbol,
            "description": info.get("company_name", ""),
            "current_price": current_price,
            "change_pct": info.get("change_pct", 0),
            "volume": info.get("volume", 0),
            "market_cap": market_cap,
            "market_cap_mn": market_cap / 1e6 if market_cap else 0,
            "net_debt": net_debt,
            "net_debt_mn": net_debt / 1e6 if net_debt else 0,
            "float_rate": float_rate,
            "total_shares": total_shares,
            "floating_shares": float_shares,
            "calculated_value": calculated_value,
            "ratio": ratio,
            "signal": signal,
            "signal_emoji": emoji,
            "signal_color": color,
            "expected_return": expected_return,
            "pe": info.get("pe"),
            "pb": info.get("pb"),
        }

    def analyze_batch(self, symbols: list) -> list:
        """Birden fazla hisse icin analiz yapar."""
        results = []
        for symbol in symbols:
            result = self.analyze(symbol)
            if result:
                results.append(result)
        return results
