"""设置 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from schemas import SettingsOut, SettingsUpdate
from services import settings as settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return settings_service.get_settings(db, user["user_id"])


@router.put("", response_model=SettingsOut)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return settings_service.update_settings(db, user["user_id"], data)
