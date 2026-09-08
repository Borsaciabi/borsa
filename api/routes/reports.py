from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from auth.dependencies import get_current_user
from reports.generators.pdf_generator import PDFGenerator
from reports.generators.excel_generator import ExcelGenerator
from data.database.db_manager import DBManager
from typing import Optional

router = APIRouter(prefix="/api/reports", tags=["Reports"])
pdf_gen = PDFGenerator()
excel_gen = ExcelGenerator()
db = DBManager()


@router.get("/stock/{symbol}/pdf")
def get_stock_pdf(symbol: str):
    path = pdf_gen.generate_stock_report(symbol.upper())
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{symbol}_rapor.pdf",
    )


@router.get("/stock/{symbol}/excel")
def get_stock_excel(symbol: str):
    path = excel_gen.generate_value_report([symbol.upper()])
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{symbol}_analiz.xlsx",
    )


@router.get("/value/excel")
def get_value_excel(symbols: str = Query(..., description="Hisse kodlari virgullu")):
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    path = excel_gen.generate_value_report(symbol_list)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="deger_analizi.xlsx",
    )


@router.get("/daily/pdf")
def get_daily_report():
    path = pdf_gen.generate_daily_market_report()
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="gunluk_piyasa_raporu.pdf",
    )


@router.get("/portfolio/pdf")
def get_portfolio_pdf(user_id: int = Query(default=1)):
    positions = db.get_active_positions(user_id)
    path = pdf_gen.generate_portfolio_report(user_id, positions)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="portfoy_raporu.pdf",
    )


@router.get("/portfolio/excel")
def get_portfolio_excel(user_id: int = Query(default=1)):
    positions = db.get_active_positions(user_id)
    path = excel_gen.generate_portfolio_report(positions)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="portfoy_raporu.xlsx",
    )
