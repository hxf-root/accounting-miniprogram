from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Bill, FitnessRecord, Settings
from auth import get_current_user
from pydantic import BaseModel
from typing import Any

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/export")
def export_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    bills = [
        {"id": b.id, "type": b.type, "amount": b.amount, "category_id": b.category_id,
         "category_name": b.category_name, "payment_method": b.payment_method,
         "remark": b.remark, "date": b.date, "time": b.time}
        for b in db.query(Bill).filter(Bill.user_id == user["user_id"]).all()
    ]
    fitness = [
        {"id": r.id, "exercise_type": r.exercise_type, "duration_minutes": r.duration_minutes,
         "calories": r.calories, "date": r.date, "time": r.time, "note": r.note}
        for r in db.query(FitnessRecord).filter(FitnessRecord.user_id == user["user_id"]).all()
    ]
    settings = db.query(Settings).filter(Settings.user_id == user["user_id"]).first()
    settings_data = {
        "monthly_budget": settings.monthly_budget if settings else 0,
        "fitness_daily_goal_minutes": settings.fitness_daily_goal_minutes if settings else 30,
        "fitness_daily_goal_calories": settings.fitness_daily_goal_calories if settings else 300,
    }
    return {"bills": bills, "fitness": fitness, "settings": settings_data}


class ImportData(BaseModel):
    bills: list[dict[str, Any]] = []
    fitness: list[dict[str, Any]] = []
    settings: dict[str, Any] = {}


@router.post("/import")
def import_data(data: ImportData, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    # 清空旧数据
    db.query(Bill).filter(Bill.user_id == uid).delete()
    db.query(FitnessRecord).filter(FitnessRecord.user_id == uid).delete()

    for b in data.bills:
        db.add(Bill(user_id=uid, **{k: v for k, v in b.items() if k in (
            "type", "amount", "category_id", "category_name", "payment_method", "remark", "date", "time"
        )}))
    for r in data.fitness:
        db.add(FitnessRecord(user_id=uid, **{k: v for k, v in r.items() if k in (
            "exercise_type", "duration_minutes", "calories", "date", "time", "note"
        )}))

    s = db.query(Settings).filter(Settings.user_id == uid).first()
    if data.settings and s:
        for k, v in data.settings.items():
            if hasattr(s, k):
                setattr(s, k, v)

    db.commit()
    return {"ok": True, "bills": len(data.bills), "fitness": len(data.fitness)}
