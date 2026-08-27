"""分类 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from auth import get_current_user
from schemas import CategoryCreate, CategoryOut
from services import categories as cat_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    type_filter: Optional[str] = Query(None, alias="type"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return cat_service.list_categories(db, user["user_id"], type_filter=type_filter)


@router.post("", response_model=CategoryOut)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return cat_service.create_category(db, user["user_id"], data)


@router.delete("/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    ok = cat_service.delete_category(db, cat_id, user["user_id"])
    if not ok:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"ok": True}
