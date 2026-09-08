from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date
from data.database.db_manager import DBManager
from auth.dependencies import get_current_user, require_admin
from portfolio.excel_importer import ExcelImporter
import os
import tempfile

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])
db = DBManager()


class BuyRequest(BaseModel):
    stock_code: str
    buy_date: date
    buy_price: float
    quantity: int
    fees: float = 0
    notes: str = ""
    user_id: int | None = None


class SellRequest(BaseModel):
    stock_code: str
    sell_date: date
    sell_price: float
    quantity: int
    fees: float = 0
    user_id: int | None = None


@router.get("")
def get_portfolio(current_user=Depends(get_current_user)):
    user_id = current_user["id"]
    positions = db.get_active_positions(user_id)
    trades = db.get_portfolio(user_id)
    return {
        "positions": positions,
        "trades": trades,
    }


@router.post("/buy")
def buy_stock(req: BuyRequest, current_user=Depends(get_current_user)):
    db.add_trade(
        user_id=current_user["id"],
        stock_code=req.stock_code.upper(),
        buy_date=str(req.buy_date),
        buy_price=req.buy_price,
        quantity=req.quantity,
        transaction_type="BUY",
        fees=req.fees,
        notes=req.notes,
    )
    return {"message": f"{req.stock_code} alisi basariyla kaydedildi"}


@router.post("/sell")
def sell_stock(req: SellRequest, current_user=Depends(get_current_user)):
    db.sell_stock(
        user_id=current_user["id"],
        stock_code=req.stock_code.upper(),
        sell_date=str(req.sell_date),
        sell_price=req.sell_price,
        quantity=req.quantity,
        fees=req.fees,
    )
    return {"message": f"{req.stock_code} satisi basariyla kaydedildi"}


@router.get("/positions")
def get_positions(current_user=Depends(get_current_user)):
    return db.get_active_positions(current_user["id"])


@router.get("/admin/all")
def get_all_portfolios(_admin=Depends(require_admin)):
    """Return every user's active portfolio for administrators only."""
    portfolios = []
    for user in db.get_all_users():
        portfolios.append({
            "user_id": user["id"],
            "username": user["username"],
            "positions": db.get_active_positions(user["id"]),
        })
    return {"portfolios": portfolios}


@router.delete("/all")
def delete_all_portfolio(current_user=Depends(get_current_user)):
    """Tum portfoy islemlerini siler."""
    db.delete_all_portfolio(current_user["id"])
    return {"message": "Tum portfoy silindi"}


@router.post("/import-excel")
async def import_excel(file: UploadFile = File(...), current_user=Depends(get_current_user)):
    """Excel/CSV dosyasindan portfoy verisi import eder."""
    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Yalnizca .xlsx, .xls veya .csv dosyalari desteklenir")

    content = await file.read()
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        importer = ExcelImporter()
        if suffix == ".csv":
            records = importer.import_from_csv(tmp_path)
        else:
            records = importer.import_from_excel(tmp_path)

        if not records:
            raise HTTPException(status_code=400, detail="Dosyadan veri okunamadi veya dosya bos")

        imported = 0
        for rec in records:
            if rec["quantity"] > 0:
                db.add_trade(
                    user_id=current_user["id"],
                    stock_code=rec["stock_code"],
                    buy_date=rec.get("buy_date", str(date.today())),
                    buy_price=rec.get("buy_price", 0),
                    quantity=rec["quantity"],
                    transaction_type="BUY",
                )
                imported += 1

        return {
            "message": f"{imported} adet hisse basariyla import edildi",
            "imported": imported,
            "records": records,
        }
    finally:
        os.unlink(tmp_path)
