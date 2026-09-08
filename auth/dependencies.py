from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.jwt_handler import decode_access_token
from data.database.db_manager import DBManager

security = HTTPBearer()
db = DBManager()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz veya suresi dolmus token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token icerisinde kullanici bulunamadi",
        )
    user = db.get_user_by_id(int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici bulunamadi",
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabiniz pasif durumda",
        )
    return user


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin yetkisi gerekiyor",
        )
    return user
