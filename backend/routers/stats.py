from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Bill, FitnessRecord, Category
from schemas import MonthlyStats, CategoryStats
from auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/monthly")
def monthly_stats(year: int, month: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    prefix = f"{year}-{month:02d}"
    bills = db.query(Bill).filter(
        Bill.user_id == user["user_id"],
        Bill.date.like(f"{prefix}%"),
    ).all()
    expense = sum(b.amount for b in bills if b.type == "expense")
    income = sum(b.amount for b in bills if b.type == "income")

    # 分类统计（支出）
    cat_totals = {}
    for b in bills:
        if b.type == "expense":
            cat_totals[b.category_name] = cat_totals.get(b.category_name, 0) + b.amount

    cat_stats = []
    for name, amt in sorted(cat_totals.items(), key=lambda x: -x[1]):
        pct = round(amt / expense * 100, 1) if expense > 0 else 0
        cat = db.query(Category).filter(
            Category.user_id == user["user_id"],
            Category.name == name,
            Category.type == "expense",
        ).first()
        cat_stats.append({
            "category_name": name,
            "amount": round(amt, 2),
            "percentage": pct,
            "color": cat.color if cat else "#5cb8a0",
        })

    # 健身统计
    fitness_records = db.query(FitnessRecord).filter(
        FitnessRecord.user_id == user["user_id"],
        FitnessRecord.date.like(f"{prefix}%"),
    ).all()
    total_minutes = sum(r.duration_minutes for r in fitness_records)
    total_calories = sum(r.calories for r in fitness_records)

    return {
        "expense": round(expense, 2),
        "income": round(income, 2),
        "balance": round(income - expense, 2),
        "category_stats": cat_stats,
        "bill_count": len([b for b in bills if b.type == "expense"]),
        "fitness_minutes": total_minutes,
        "fitness_calories": total_calories,
        "fitness_count": len(fitness_records),
    }


@router.get("/today")
def today_stats(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    from datetime import date
    today = date.today().isoformat()
    bills = db.query(Bill).filter(
        Bill.user_id == user["user_id"],
        Bill.date == today,
    ).all()
    expense = sum(b.amount for b in bills if b.type == "expense")
    income = sum(b.amount for b in bills if b.type == "income")

    fitness = db.query(FitnessRecord).filter(
        FitnessRecord.user_id == user["user_id"],
        FitnessRecord.date == today,
    ).all()
    minutes = sum(r.duration_minutes for r in fitness)
    calories = sum(r.calories for r in fitness)

    return {
        "expense": round(expense, 2),
        "income": round(income, 2),
        "fitness_minutes": minutes,
        "fitness_calories": calories,
    }
