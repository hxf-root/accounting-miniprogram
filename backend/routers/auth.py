from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, TokenResponse
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(
        token=create_token(user.id, user.username),
        username=user.username,
        user_id=user.id,
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    return TokenResponse(
        token=create_token(user.id, user.username),
        username=user.username,
        user_id=user.id,
    )
