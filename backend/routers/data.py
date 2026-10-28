"""数据导入导出 API 路由层（薄层，委托给 service）"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from schemas import ImportData
from services import data as data_service

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/export")
def export_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return data_service.export_data(db, user["user_id"])


@router.post("/import")
def import_data(data: ImportData, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return data_service.import_data(db, user["user_id"], data)


@router.delete("")
def clear_data(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    # Until source pausing and in-flight job fencing exist, clearing can cause
    # an authorized worker to reimport deleted data immediately afterward.
    raise HTTPException(status_code=503, detail="暂不能清空数据：同步暂停和删除保护尚未完成")
