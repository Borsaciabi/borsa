from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from auth.password import hash_password, verify_password
from auth.jwt_handler import create_access_token
from data.database.db_manager import DBManager
from auth.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["Auth"])
db = DBManager()


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UsernameRecoveryRequest(BaseModel):
    email: str


class PasswordResetRequest(BaseModel):
    email: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str = "user"


def _token_response(user):
    token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        username=user["username"],
        role=user.get("role", "user"),
    )


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    existing = db.get_user_by_username(req.username)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Bu kullanici adi zaten mevcut",
        )
    hashed = hash_password(req.password)
    user = db.create_user(req.username, req.email, hashed)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Kayit basarisiz. E-posta veya kullanici adi zaten kullaniliyor olabilir.",
        )
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = db.get_user_by_username(req.username)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Kullanici adi veya sifre hatali",
        )
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Kullanici adi veya sifre hatali",
        )
    if not user.get("is_active", 1):
        raise HTTPException(
            status_code=403,
            detail="Hesabiniz pasif durumda. Yoneticiyle iletisime gecin.",
        )
    db.update_last_login(user["id"])
    return _token_response(user)


@router.post("/forgot-username")
def forgot_username(req: UsernameRecoveryRequest):
    user = db.get_user_by_email(req.email.strip().lower())
    if not user:
        raise HTTPException(status_code=404, detail="Bu e-posta ile kayitli kullanici bulunamadi")
    return {"username": user["username"]}


@router.post("/reset-password")
def reset_password(req: PasswordResetRequest):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Sifre en az 6 karakter olmali")
    user = db.get_user_by_email(req.email.strip().lower())
    if not user:
        raise HTTPException(status_code=404, detail="Bu e-posta ile kayitli kullanici bulunamadi")
    db.change_password(user["id"], hash_password(req.new_password))
    return {"message": "Sifreniz basariyla yenilendi"}


@router.get("/me", response_model=TokenResponse)
def current_user(user=Depends(get_current_user)):
    """Validate a saved session and return the current user."""
    return _token_response(user)


@router.post("/link-telegram")
def link_telegram(telegram_id: int, telegram_username: str,
                  user_id: int = Query(default=1)):
    db.link_telegram(user_id, telegram_id, telegram_username)
    return {"message": "Telegram hesabi basariyla baglandi"}


class AdminUserAction(BaseModel):
    user_id: int


class AdminRoleAction(BaseModel):
    user_id: int
    role: str


class AdminPasswordAction(BaseModel):
    user_id: int
    new_password: str


@router.get("/admin/users")
def admin_list_users(_admin=Depends(require_admin)):
    users = db.get_all_users()
    return {"users": users, "total": len(users)}


@router.get("/admin/users/{user_id}")
def admin_user_detail(user_id: int, _admin=Depends(require_admin)):
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    portfolio = db.get_portfolio(user_id)
    alerts = db.get_active_alerts(user_id)
    return {
        "user": user,
        "portfolio_trades": portfolio,
        "active_alerts": alerts,
        "active_positions": db.get_active_positions(user_id),
    }


@router.get("/admin/stats")
def admin_stats(_admin=Depends(require_admin)):
    users = db.get_all_users()
    return {
        "total_users": len(users),
        "active_users": sum(1 for u in users if u.get("is_active")),
        "admin_users": sum(1 for u in users if u.get("role") == "admin"),
    }


@router.post("/admin/role")
def admin_set_role(req: AdminRoleAction, _admin=Depends(require_admin)):
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Gecersiz rol")
    db.set_user_role(req.user_id, req.role)
    return {"message": f"Kullanici rolu '{req.role}' olarak guncellendi"}


@router.post("/admin/toggle-active")
def admin_toggle_active(req: AdminUserAction, _admin=Depends(require_admin)):
    user = db.get_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    new_status = 0 if user.get("is_active", 1) else 1
    db.set_user_active(req.user_id, new_status)
    return {"message": f"Kullanici {'aktif' if new_status else 'pasif'} yapildi"}


@router.post("/admin/delete")
def admin_delete_user(req: AdminUserAction, _admin=Depends(require_admin)):
    user = db.get_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    if user.get("role") == "admin":
        raise HTTPException(status_code=400, detail="Admin kullanicisi silinemez")
    db.delete_user(req.user_id)
    return {"message": "Kullanici basariyla silindi"}


@router.post("/admin/reset-password")
def admin_reset_password(req: AdminPasswordAction, _admin=Depends(require_admin)):
    hashed = hash_password(req.new_password)
    db.change_password(req.user_id, hashed)
    return {"message": "Sifre basariyla sifirlandi"}
