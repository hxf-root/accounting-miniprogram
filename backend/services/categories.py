"""分类业务逻辑层"""

from sqlalchemy.orm import Session
from typing import Optional, List

from models import Category
from schemas import CategoryCreate

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


def list_categories(db: Session, user_id: int, type_filter: Optional[str] = None) -> List[Category]:
    _ensure_defaults(db, user_id)
    q = db.query(Category).filter(Category.user_id == user_id)
    if type_filter:
        q = q.filter(Category.type == type_filter)
    return q.order_by(Category.sort_order).all()


def create_category(db: Session, user_id: int, data: CategoryCreate) -> Category:
    cat = Category(user_id=user_id, is_custom=True, **data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def delete_category(db: Session, cat_id: int, user_id: int) -> bool:
    cat = db.query(Category).filter(Category.id == cat_id, Category.user_id == user_id).first()
    if not cat:
        return False
    if not cat.is_custom:
        return False
    db.delete(cat)
    db.commit()
    return True
