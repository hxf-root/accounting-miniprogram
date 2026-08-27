"""账单业务逻辑层"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List

from models import Bill
from schemas import BillCreate, BillUpdate


def list_bills(
    db: Session,
    user_id: int,
    type_filter: Optional[str] = None,
    payment: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> List[Bill]:
    q = db.query(Bill).filter(Bill.user_id == user_id)
    if type_filter:
        q = q.filter(Bill.type == type_filter)
    if payment:
        q = q.filter(Bill.payment_method == payment)
    if date_from:
        q = q.filter(Bill.date >= date_from)
    if date_to:
        q = q.filter(Bill.date <= date_to)
    q = q.order_by(desc(Bill.date), desc(Bill.time), desc(Bill.id))
    return q.offset((page - 1) * page_size).limit(page_size).all()


def count_bills(
    db: Session,
    user_id: int,
    type_filter: Optional[str] = None,
    payment: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> int:
    q = db.query(Bill).filter(Bill.user_id == user_id)
    if type_filter:
        q = q.filter(Bill.type == type_filter)
    if payment:
        q = q.filter(Bill.payment_method == payment)
    if date_from:
        q = q.filter(Bill.date >= date_from)
    if date_to:
        q = q.filter(Bill.date <= date_to)
    return q.count()


def create_bill(db: Session, user_id: int, data: BillCreate) -> Bill:
    bill = Bill(user_id=user_id, **data.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def update_bill(db: Session, bill_id: int, user_id: int, data: BillUpdate) -> Optional[Bill]:
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user_id).first()
    if not bill:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(bill, k, v)
    db.commit()
    db.refresh(bill)
    return bill


def delete_bill(db: Session, bill_id: int, user_id: int) -> bool:
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user_id).first()
    if not bill:
        return False
    db.delete(bill)
    db.commit()
    return True
