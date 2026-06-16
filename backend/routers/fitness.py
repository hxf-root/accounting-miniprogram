from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import FitnessRecord
from schemas import FitnessCreate, FitnessOut
from auth import get_current_user

router = APIRouter(prefix="/api/fitness", tags=["fitness"])


@router.get("/records", response_model=list[FitnessOut])
def list_fitness(
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(FitnessRecord).filter(FitnessRecord.user_id == user["user_id"])
    if date_from:
        q = q.filter(FitnessRecord.date >= date_from)
    if date_to:
        q = q.filter(FitnessRecord.date <= date_to)
    q = q.order_by(desc(FitnessRecord.date), desc(FitnessRecord.time), desc(FitnessRecord.id))
    return q.offset((page - 1) * page_size).limit(page_size).all()


@router.post("/records", response_model=FitnessOut)
def create_fitness(data: FitnessCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    record = FitnessRecord(user_id=user["user_id"], **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/records/{record_id}")
def delete_fitness(record_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    record = db.query(FitnessRecord).filter(
        FitnessRecord.id == record_id, FitnessRecord.user_id == user["user_id"]
    ).first()
    if not record:
        raise HTTPException(404, "记录不存在")
    db.delete(record)
    db.commit()
    return {"ok": True}
