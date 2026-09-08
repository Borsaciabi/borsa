from fastapi import APIRouter
from analysis.value_analysis import ValueAnalyzer
from analysis.technical_analysis import TechnicalAnalyzer

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])
value_analyzer = ValueAnalyzer()
tech_analyzer = TechnicalAnalyzer()


@router.get("/value/{symbol}")
def analyze_value(symbol: str):
    result = value_analyzer.analyze(symbol.upper())
    if not result:
        return {"error": f"{symbol} icin deger analizi yapilamadi"}
    return result


@router.get("/value/batch")
def analyze_value_batch(symbols: str):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    results = value_analyzer.analyze_batch(symbol_list)
    return {"results": results, "count": len(results)}


@router.get("/technical/{symbol}")
def analyze_technical(symbol: str):
    result = tech_analyzer.analyze(symbol.upper())
    if not result:
        return {"error": f"{symbol} icin teknik analiz yapilamadi"}
    return {
        "symbol": result["symbol"],
        "current_price": result["current_price"],
        "ma20": result["ma20"],
        "ma50": result["ma50"],
        "ma200": result["ma200"],
        "rsi": result["rsi"],
        "macd": result["macd"],
        "macd_signal": result["macd_signal"],
        "macd_histogram": result["macd_histogram"],
        "bb_upper": result["bb_upper"],
        "bb_middle": result["bb_middle"],
        "bb_lower": result["bb_lower"],
        "volume": result["volume"],
        "volume_avg_20": result["volume_avg_20"],
        "price_vs_ma200": result["price_vs_ma200"],
        "price_vs_ma50": result["price_vs_ma50"],
    }
