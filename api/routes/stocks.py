from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from data.fetchers.bist_fetcher import BistFetcher
from config.constants import BIST_100, BIST_30

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])
bist = BistFetcher()


@router.get("")
def list_stocks():
    return {"stocks": BIST_100, "count": len(BIST_100)}


@router.get("/bist30")
def list_bist30():
    return {"stocks": BIST_30, "count": len(BIST_30)}


@router.get("/{symbol}")
def get_stock(symbol: str):
    info = bist.get_info(symbol)
    if not info:
        return {"error": f"{symbol} icin veri bulunamadi"}
    return info


@router.get("/{symbol}/history")
def get_stock_history(symbol: str, period: str = "1y"):
    history = bist.get_history(symbol, period)
    if history is None:
        return {"error": f"{symbol} icin gecmis veri bulunamadi"}
    return {
        "symbol": symbol,
        "period": period,
        "data": history.to_dict(orient="records"),
    }


@router.get("/{symbol}/balance-sheet")
def get_balance_sheet(symbol: str):
    bs = bist.get_balance_sheet(symbol)
    if bs is None:
        return {"error": f"{symbol} icin bilanco bulunamadi"}
    return {
        "symbol": symbol,
        "data": bs.to_dict(),
    }
