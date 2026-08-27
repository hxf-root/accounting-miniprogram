"""统计 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from services import stats as stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/monthly")
def monthly_stats(year: int, month: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return stats_service.get_monthly_stats(db, user["user_id"], year, month)


@router.get("/today")
def today_stats(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return stats_service.get_today_stats(db, user["user_id"])
