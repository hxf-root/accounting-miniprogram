import datetime
import os
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from identity.sessions import is_session_token, resolve as resolve_session
from models import AccountAuthEpoch, User

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be configured")
ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "720"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, username: str, db: Session) -> str:
    row = db.query(AccountAuthEpoch).filter_by(user_id=user_id).first()
    payload = {
        "auth_epoch": row.epoch if row else 0,
        "user_id": user_id,
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(security),
                     db: Session = Depends(get_db)) -> dict:
    if cred is None:
        raise HTTPException(
            status_code=401,
            detail="未提供登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = cred.credentials
    if is_session_token(token):
        user_id = resolve_session(db, token)
        user = db.query(User).filter_by(id=user_id).first() if user_id else None
        if user is None:
            raise HTTPException(status_code=401, detail="无效的登录凭证", headers={"WWW-Authenticate": "Bearer"})
        return {"user_id": user.id, "username": user.username}
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require_exp": True})
        user_id, username = payload["user_id"], payload["username"]
        token_epoch = payload.get("auth_epoch", 0)
        if (isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0
                or not isinstance(username, str) or isinstance(token_epoch, bool)
                or not isinstance(token_epoch, int) or token_epoch < 0):
            raise JWTError('invalid credentials')
        user = db.query(User).filter_by(id=user_id, username=username).first()
        row = db.query(AccountAuthEpoch).filter_by(user_id=user_id).first()
        if user is None or token_epoch != (row.epoch if row else 0):
            raise JWTError('invalid credentials')
        return {"user_id": user_id, "username": username}
    except (JWTError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
