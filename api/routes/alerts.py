from fastapi import APIRouter, Depends
from pydantic import BaseModel
from data.database.db_manager import DBManager
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])
db = DBManager()


class AlertRequest(BaseModel):
    stock_code: str
    alert_type: str
    target_value: float
    user_id: int | None = None


@router.get("")
def get_alerts(current_user=Depends(get_current_user)):
    return db.get_active_alerts(current_user["id"])


@router.post("")
def create_alert(req: AlertRequest, current_user=Depends(get_current_user)):
    db.add_alert(
        user_id=current_user["id"],
        stock_code=req.stock_code.upper(),
        alert_type=req.alert_type,
        target_value=req.target_value,
    )
    return {"message": f"{req.stock_code} icin alarm kuruldu"}


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, current_user=Depends(get_current_user)):
    db.delete_alert(alert_id, current_user["id"])
    return {"message": "Alarm silindi"}
