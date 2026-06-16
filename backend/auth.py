import datetime
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "baobaoji-secret-key-change-in-production"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = cred.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"user_id": payload["user_id"], "username": payload["username"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")
