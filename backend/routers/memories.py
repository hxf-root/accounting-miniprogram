"""私人回忆基础接口；自动采集和媒体文件另行实现。"""
from datetime import datetime, timezone

from sqlalchemy import and_, or_
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Memory, MemorySuppression
from schemas import MemoryCreate

router = APIRouter(prefix="/api/memories", tags=["memories"])


class MemoryVisibility(BaseModel):
    hidden: bool


def serialize(item):
    return {"id": item.id, "source": item.source, "source_id": item.source_id,
            "occurred_at": item.occurred_at, "text": item.text, "hidden": item.hidden}


@router.post("", status_code=201)
def create_memory(data: MemoryCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if data.source != 'manual':
        raise HTTPException(status_code=403, detail='来源记录只能由同步服务导入')
    if data.source_id and db.query(MemorySuppression).filter_by(
        user_id=user["user_id"], source=data.source, source_id=data.source_id
    ).first():
        raise HTTPException(status_code=409, detail="记录此前已删除，无法重新导入")
    item = Memory(user_id=user["user_id"], source=data.source, source_id=data.source_id,
                  occurred_at=data.occurred_at.isoformat(timespec="microseconds"), text=data.text, hidden=data.hidden)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该来源记录已存在")
    db.refresh(item)
    return serialize(item)


@router.get("")
def list_memories(include_hidden: bool = False, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0), before: datetime | None = None,
                  before_id: int | None = Query(None, ge=1), db: Session = Depends(get_db),
                  user: dict = Depends(get_current_user)):
    if (before is None) != (before_id is None) or (before is not None and (before.utcoffset() is None or offset)):
        raise HTTPException(status_code=422, detail="分页游标需要带时区的时间与记录 ID，且不能与 offset 同用")
    query = db.query(Memory).filter(Memory.user_id == user["user_id"])
    if before is not None:
        stamp = before.astimezone(timezone.utc).isoformat(timespec="microseconds")
        query = query.filter(or_(Memory.occurred_at < stamp,
                                 and_(Memory.occurred_at == stamp, Memory.id < before_id)))
    if not include_hidden:
        query = query.filter(Memory.hidden.is_(False))
    items = query.order_by(Memory.occurred_at.desc(), Memory.id.desc()).offset(offset).limit(limit).all()
    return [serialize(item) for item in items]


def get_owned(db, user_id, memory_id):
    item = db.query(Memory).filter(Memory.id == memory_id, Memory.user_id == user_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="记录不存在")
    return item


@router.patch("/{memory_id}")
def set_visibility(memory_id: int, data: MemoryVisibility, db: Session = Depends(get_db),
                   user: dict = Depends(get_current_user)):
    item = get_owned(db, user["user_id"], memory_id)
    item.hidden = data.hidden
    db.commit()
    return serialize(item)


@router.delete("/{memory_id}")
def delete_memory(memory_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    item = get_owned(db, user["user_id"], memory_id)
    if item.source != "manual" and item.source_id:
        if not db.query(MemorySuppression).filter_by(user_id=user["user_id"], source=item.source, source_id=item.source_id).first():
            db.add(MemorySuppression(user_id=user["user_id"], source=item.source, source_id=item.source_id))
    db.delete(item)
    db.commit()
    return {"ok": True}
