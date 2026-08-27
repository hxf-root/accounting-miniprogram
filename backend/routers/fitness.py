"""健身 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from auth import get_current_user
from schemas import FitnessCreate, FitnessOut
from services import fitness as fitness_service

router = APIRouter(prefix="/api/fitness", tags=["fitness"])


@router.get("/records", response_model=list[FitnessOut])
def list_fitness(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return fitness_service.list_records(
        db, user["user_id"],
        date_from=date_from, date_to=date_to,
        page=page, page_size=page_size,
    )


@router.post("/records", response_model=FitnessOut)
def create_fitness(data: FitnessCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return fitness_service.create_record(db, user["user_id"], data)


@router.delete("/records/{record_id}")
def delete_fitness(record_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ok = fitness_service.delete_record(db, record_id, user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"ok": True}
