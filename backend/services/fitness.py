"""健身记录业务逻辑层"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List

from models import FitnessRecord
from schemas import FitnessCreate


def list_records(
    db: Session,
    user_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> List[FitnessRecord]:
    q = db.query(FitnessRecord).filter(FitnessRecord.user_id == user_id)
    if date_from:
        q = q.filter(FitnessRecord.date >= date_from)
    if date_to:
        q = q.filter(FitnessRecord.date <= date_to)
    q = q.order_by(desc(FitnessRecord.date), desc(FitnessRecord.time), desc(FitnessRecord.id))
    return q.offset((page - 1) * page_size).limit(page_size).all()


def create_record(db: Session, user_id: int, data: FitnessCreate) -> FitnessRecord:
    record = FitnessRecord(user_id=user_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record_id: int, user_id: int) -> bool:
    record = db.query(FitnessRecord).filter(
        FitnessRecord.id == record_id, FitnessRecord.user_id == user_id
    ).first()
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
