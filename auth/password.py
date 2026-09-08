import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, h = hashed_password.split("$", 1)
        check = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt.encode(), 100000)
        return check.hex() == h
    except Exception:
        return False
