"""数据导入导出业务逻辑层"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel

from models import Bill, FitnessRecord, Settings


class ImportData(BaseModel):
    bills: List[Dict[str, Any]] = []
    fitness: List[Dict[str, Any]] = []
    settings: Dict[str, Any] = {}


def export_data(db: Session, user_id: int) -> Dict[str, Any]:
    bills = [
        {
            "id": b.id, "type": b.type, "amount": b.amount,
            "category_id": b.category_id, "category_name": b.category_name,
            "payment_method": b.payment_method, "remark": b.remark,
            "date": b.date, "time": b.time,
        }
        for b in db.query(Bill).filter(Bill.user_id == user_id).all()
    ]
    fitness = [
        {
            "id": r.id, "exercise_type": r.exercise_type,
            "duration_minutes": r.duration_minutes, "calories": r.calories,
            "date": r.date, "time": r.time, "note": r.note,
        }
        for r in db.query(FitnessRecord).filter(FitnessRecord.user_id == user_id).all()
    ]
    settings_obj = db.query(Settings).filter(Settings.user_id == user_id).first()
    settings_data = {
        "monthly_budget": settings_obj.monthly_budget if settings_obj else 0,
        "fitness_daily_goal_minutes": settings_obj.fitness_daily_goal_minutes if settings_obj else 30,
        "fitness_daily_goal_calories": settings_obj.fitness_daily_goal_calories if settings_obj else 300,
    }
    return {"bills": bills, "fitness": fitness, "settings": settings_data}


def import_data(db: Session, user_id: int, data: ImportData) -> Dict[str, Any]:
    # 清空旧数据
    db.query(Bill).filter(Bill.user_id == user_id).delete()
    db.query(FitnessRecord).filter(FitnessRecord.user_id == user_id).delete()

    for b in data.bills:
        db.add(Bill(
            user_id=user_id,
            type=b.get("type"),
            amount=b.get("amount"),
            category_id=b.get("category_id"),
            category_name=b.get("category_name"),
            payment_method=b.get("payment_method", "wechat"),
            remark=b.get("remark", ""),
            date=b.get("date"),
            time=b.get("time"),
        ))
    for r in data.fitness:
        db.add(FitnessRecord(
            user_id=user_id,
            exercise_type=r.get("exercise_type"),
            duration_minutes=r.get("duration_minutes"),
            calories=r.get("calories", 0),
            date=r.get("date"),
            time=r.get("time"),
            note=r.get("note", ""),
        ))

    s = db.query(Settings).filter(Settings.user_id == user_id).first()
    if data.settings and s:
        for k, v in data.settings.items():
            if hasattr(s, k):
                setattr(s, k, v)

    db.commit()
    return {"ok": True, "bills": len(data.bills), "fitness": len(data.fitness)}
