from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Category
from schemas import CategoryCreate, CategoryOut
from auth import get_current_user

router = APIRouter(prefix="/api/categories", tags=["categories"])

DEFAULT_EXPENSE = [
    {"name": "餐饮", "icon": "🍜", "color": "#e86a6a"},
    {"name": "交通", "icon": "🚇", "color": "#5cb8a0"},
    {"name": "购物", "icon": "🛒", "color": "#f0a85c"},
    {"name": "娱乐", "icon": "🎮", "color": "#b8a9c9"},
    {"name": "居家", "icon": "🏠", "color": "#f0d68a"},
    {"name": "美妆", "icon": "💄", "color": "#e8a0c8"},
    {"name": "教育", "icon": "📚", "color": "#6ba3d6"},
    {"name": "医疗", "icon": "💊", "color": "#e87a7a"},
    {"name": "宠物", "icon": "🐱", "color": "#a8dcc4"},
    {"name": "通讯", "icon": "📱", "color": "#7a9ec4"},
    {"name": "服饰", "icon": "👔", "color": "#c8a0d8"},
    {"name": "其他", "icon": "📦", "color": "#a0b8af"},
]

DEFAULT_INCOME = [
    {"name": "工资", "icon": "💼", "color": "#5ba87f"},
    {"name": "兼职", "icon": "💻", "color": "#6ba3d6"},
    {"name": "红包", "icon": "🧧", "color": "#e86a6a"},
    {"name": "理财", "icon": "📈", "color": "#f0a85c"},
    {"name": "其他", "icon": "📦", "color": "#a0b8af"},
]


def _ensure_defaults(db: Session, user_id: int):
    existing = db.query(Category).filter(Category.user_id == user_id).count()
    if existing > 0:
        return
    for i, c in enumerate(DEFAULT_EXPENSE):
        db.add(Category(user_id=user_id, type="expense", sort_order=i, **c))
    for i, c in enumerate(DEFAULT_INCOME):
        db.add(Category(user_id=user_id, type="income", sort_order=i, **c))
    db.commit()


@router.get("", response_model=list[CategoryOut])
def list_categories(type_filter: str | None = None, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    _ensure_defaults(db, user["user_id"])
    q = db.query(Category).filter(Category.user_id == user["user_id"])
    if type_filter:
        q = q.filter(Category.type == type_filter)
    return q.order_by(Category.sort_order).all()


@router.post("", response_model=CategoryOut)
def create_category(data: CategoryCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    cat = Category(user_id=user["user_id"], is_custom=True, **data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    cat = db.query(Category).filter(Category.id == cat_id, Category.user_id == user["user_id"]).first()
    if not cat:
        raise HTTPException(404, "分类不存在")
    if not cat.is_custom:
        raise HTTPException(400, "默认分类不可删除")
    db.delete(cat)
    db.commit()
    return {"ok": True}
