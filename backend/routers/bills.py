"""账单 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from auth import get_current_user
from schemas import BillCreate, BillUpdate, BillOut
from services import bills as bill_service

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
    return bill_service.list_bills(
        db, user["user_id"],
        type_filter=type_filter, payment=payment,
        date_from=date_from, date_to=date_to,
        page=page, page_size=page_size,
    )


@router.post("", response_model=BillOut)
def create_bill(data: BillCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return bill_service.create_bill(db, user["user_id"], data)


@router.put("/{bill_id}", response_model=BillOut)
def update_bill(bill_id: int, data: BillUpdate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    result = bill_service.update_bill(db, bill_id, user["user_id"], data)
    if not result:
        raise HTTPException(status_code=404, detail="账单不存在")
    return result


@router.delete("/{bill_id}")
def delete_bill(bill_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ok = bill_service.delete_bill(db, bill_id, user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="账单不存在")
    return {"ok": True}
