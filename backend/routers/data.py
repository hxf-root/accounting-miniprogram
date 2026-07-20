from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Bill, Category, FitnessRecord, Settings
from auth import get_current_user
from pydantic import BaseModel, Field
from typing import Any

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/export")
def export_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    categories = [
        {"id": c.id, "type": c.type, "name": c.name, "icon": c.icon,
         "color": c.color, "is_custom": c.is_custom, "sort_order": c.sort_order}
        for c in db.query(Category).filter(Category.user_id == user["user_id"]).all()
    ]
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
    return {
        "version": 2,
        "categories": categories,
        "bills": bills,
        "fitness": fitness,
        "settings": settings_data,
    }


class ImportData(BaseModel):
    categories: list[dict[str, Any]] | None = None
    bills: list[dict[str, Any]] = Field(default_factory=list)
    fitness: list[dict[str, Any]] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


@router.post("/import")
def import_data(data: ImportData, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    db.query(Bill).filter(Bill.user_id == uid).delete()
    db.query(FitnessRecord).filter(FitnessRecord.user_id == uid).delete()

    category_id_map = {}
    if data.categories is not None:
        db.query(Category).filter(Category.user_id == uid).delete()
        for item in data.categories:
            old_id = item.get("id")
            payload = {k: v for k, v in item.items() if k in (
                "type", "name", "icon", "color", "is_custom", "sort_order"
            )}
            category = Category(user_id=uid, **payload)
            db.add(category)
            db.flush()
            if old_id is not None:
                category_id_map[old_id] = category.id

    for b in data.bills:
        payload = {k: v for k, v in b.items() if k in (
            "type", "amount", "category_id", "category_name", "payment_method", "remark", "date", "time"
        )}
        if payload.get("category_id") in category_id_map:
            payload["category_id"] = category_id_map[payload["category_id"]]
        db.add(Bill(user_id=uid, **payload))
    for r in data.fitness:
        db.add(FitnessRecord(user_id=uid, **{k: v for k, v in r.items() if k in (
            "exercise_type", "duration_minutes", "calories", "date", "time", "note"
        )}))

    if data.settings:
        s = db.query(Settings).filter(Settings.user_id == uid).first()
        if not s:
            s = Settings(user_id=uid)
            db.add(s)
        for k, v in data.settings.items():
            if k in ("monthly_budget", "fitness_daily_goal_minutes", "fitness_daily_goal_calories"):
                setattr(s, k, v)

    db.commit()
    return {
        "ok": True,
        "categories": len(data.categories) if data.categories is not None else None,
        "bills": len(data.bills),
        "fitness": len(data.fitness),
    }


@router.delete("")
def clear_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    uid = user["user_id"]
    db.query(Bill).filter(Bill.user_id == uid).delete()
    db.query(FitnessRecord).filter(FitnessRecord.user_id == uid).delete()
    db.query(Category).filter(Category.user_id == uid).delete()
    db.query(Settings).filter(Settings.user_id == uid).delete()
    db.commit()
    return {"ok": True}
