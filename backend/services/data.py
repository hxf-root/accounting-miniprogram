"""数据导入导出业务逻辑层"""

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from models import Bill, FitnessRecord, Settings, Category, Memory
from schemas import ImportData


def export_data(db: Session, user_id: int) -> Dict[str, Any]:
    categories = [
        {"id": c.id, "type": c.type, "name": c.name, "icon": c.icon,
         "color": c.color, "is_custom": c.is_custom, "sort_order": c.sort_order}
        for c in db.query(Category).filter(Category.user_id == user_id).all()
    ]
    bills = [
        {"id": b.id, "type": b.type, "amount": b.amount, "category_id": b.category_id,
         "category_name": b.category_name, "payment_method": b.payment_method,
         "remark": b.remark, "date": b.date, "time": b.time}
        for b in db.query(Bill).filter(Bill.user_id == user_id).all()
    ]
    fitness = [
        {"id": r.id, "exercise_type": r.exercise_type, "duration_minutes": r.duration_minutes,
         "calories": r.calories, "date": r.date, "time": r.time, "note": r.note}
        for r in db.query(FitnessRecord).filter(FitnessRecord.user_id == user_id).all()
    ]
    settings_obj = db.query(Settings).filter(Settings.user_id == user_id).first()
    settings_data = {
        "monthly_budget": settings_obj.monthly_budget if settings_obj else 0,
        "fitness_daily_goal_minutes": settings_obj.fitness_daily_goal_minutes if settings_obj else 30,
        "fitness_daily_goal_calories": settings_obj.fitness_daily_goal_calories if settings_obj else 300,
    }
    memories = [{"source": m.source, "source_id": m.source_id, "occurred_at": m.occurred_at,
                 "text": m.text, "hidden": m.hidden}
                for m in db.query(Memory).filter(Memory.user_id == user_id).all()]
    return {
        "version": 2,
        "memories": memories,
        "categories": categories,
        "bills": bills,
        "fitness": fitness,
        "settings": settings_data,
    }


def import_data(db: Session, user_id: int, data: ImportData) -> Dict[str, Any]:
    # 清空旧数据
    db.query(Bill).filter(Bill.user_id == user_id).delete()
    db.query(FitnessRecord).filter(FitnessRecord.user_id == user_id).delete()

    category_id_map = {}
    if data.categories is not None:
        db.query(Category).filter(Category.user_id == user_id).delete()
        for item in data.categories:
            old_id = item.get("id")
            payload = {k: v for k, v in item.items() if k in (
                "type", "name", "icon", "color", "is_custom", "sort_order"
            )}
            category = Category(user_id=user_id, **payload)
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
        db.add(Bill(user_id=user_id, **payload))

    for r in data.fitness:
        db.add(FitnessRecord(user_id=user_id, **{k: v for k, v in r.items() if k in (
            "exercise_type", "duration_minutes", "calories", "date", "time", "note"
        )}))

    if data.memories is not None:
        db.query(Memory).filter(Memory.user_id == user_id).delete()
        for m in data.memories:
            db.add(Memory(user_id=user_id, source=m.source, source_id=m.source_id,
                          occurred_at=m.occurred_at.isoformat(timespec="microseconds"),
                          text=m.text, hidden=m.hidden))

    if data.settings:
        s = db.query(Settings).filter(Settings.user_id == user_id).first()
        if not s:
            s = Settings(user_id=user_id)
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


def clear_data(db: Session, user_id: int) -> bool:
    db.query(Memory).filter(Memory.user_id == user_id).delete()
    db.query(Bill).filter(Bill.user_id == user_id).delete()
    db.query(FitnessRecord).filter(FitnessRecord.user_id == user_id).delete()
    db.query(Category).filter(Category.user_id == user_id).delete()
    db.query(Settings).filter(Settings.user_id == user_id).delete()
    db.commit()
    return True
