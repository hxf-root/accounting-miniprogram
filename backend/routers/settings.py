from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Settings
from schemas import SettingsOut, SettingsUpdate
from auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _ensure_settings(db: Session, user_id: int):
    s = db.query(Settings).filter(Settings.user_id == user_id).first()
    if not s:
        s = Settings(user_id=user_id)
        db.add(s)
        db.commit()


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    _ensure_settings(db, user["user_id"])
    s = db.query(Settings).filter(Settings.user_id == user["user_id"]).first()
    return s


@router.put("", response_model=SettingsOut)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    _ensure_settings(db, user["user_id"])
    s = db.query(Settings).filter(Settings.user_id == user["user_id"]).first()
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s
