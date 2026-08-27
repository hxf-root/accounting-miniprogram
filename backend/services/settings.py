"""设置业务逻辑层"""

from sqlalchemy.orm import Session
from typing import Optional

from models import Settings
from schemas import SettingsUpdate


def _ensure_settings(db: Session, user_id: int):
    s = db.query(Settings).filter(Settings.user_id == user_id).first()
    if not s:
        s = Settings(user_id=user_id)
        db.add(s)
        db.commit()


def get_settings(db: Session, user_id: int) -> Settings:
    _ensure_settings(db, user_id)
    return db.query(Settings).filter(Settings.user_id == user_id).first()


def update_settings(db: Session, user_id: int, data: SettingsUpdate) -> Settings:
    _ensure_settings(db, user_id)
    s = db.query(Settings).filter(Settings.user_id == user_id).first()
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s
