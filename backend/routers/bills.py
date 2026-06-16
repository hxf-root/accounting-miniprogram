from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from database import get_db
from models import Bill
from schemas import BillCreate, BillUpdate, BillOut
from auth import get_current_user

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.get("", response_model=list[BillOut])
def list_bills(
    type_filter: Optional[str] = Query(None, alias="type"),
    payment: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    q = db.query(Bill).filter(Bill.user_id == user["user_id"])
    if type_filter:
        q = q.filter(Bill.type == type_filter)
    if payment:
        q = q.filter(Bill.payment_method == payment)
    if date_from:
        q = q.filter(Bill.date >= date_from)
    if date_to:
        q = q.filter(Bill.date <= date_to)
    q = q.order_by(desc(Bill.date), desc(Bill.time), desc(Bill.id))
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.post("", response_model=BillOut)
def create_bill(data: BillCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    bill = Bill(user_id=user["user_id"], **data.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


@router.put("/{bill_id}", response_model=BillOut)
def update_bill(bill_id: int, data: BillUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user["user_id"]).first()
    if not bill:
        raise HTTPException(404, "账单不存在")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(bill, k, v)
    db.commit()
    db.refresh(bill)
    return bill


@router.delete("/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user["user_id"]).first()
    if not bill:
        raise HTTPException(404, "账单不存在")
    db.delete(bill)
    db.commit()
    return {"ok": True}
