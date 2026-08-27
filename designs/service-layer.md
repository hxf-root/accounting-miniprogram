# 抱布记 · Service 层设计

> 后端业务逻辑的详细设计。Router 层薄，Service 层厚。

---

## S1 — Services 包结构

```
services/
├── __init__.py        # 导出所有 service
├── bills.py           # 账单 CRUD + 筛选
├── categories.py      # 分类 CRUD + 默认初始化
├── fitness.py         # 健身记录 CRUD
├── stats.py           # 月度/今日统计聚合
├── settings.py        # 用户设置读写
└── data.py            # 数据导入导出
```

---

## S2 — bills service

### 函数签名

```python
# services/bills.py
from sqlalchemy.orm import Session
from models import Bill
from schemas import BillCreate, BillUpdate
from typing import Optional, List

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
    """返回账单列表（ORM 对象）"""

def count_bills(
    db: Session,
    user_id: int,
    **filters,
) -> int:
    """返回符合条件的总数"""

def create_bill(
    db: Session,
    user_id: int,
    data: BillCreate,
) -> Bill:
    """创建账单，返回 ORM 对象"""

def update_bill(
    db: Session,
    bill_id: int,
    user_id: int,
    data: BillUpdate,
) -> Optional[Bill]:
    """更新账单，返回更新后的对象或 None"""

def delete_bill(
    db: Session,
    bill_id: int,
    user_id: int,
) -> bool:
    """删除账单，返回是否成功"""
```

### 实现要点

- 所有查询加 `Bill.user_id == user_id` 过滤，防止越权
- 更新使用 `exclude_unset=True`，只更新提供的字段
- 删除前检查所有权

---

## S3 — categories service

### 函数签名

```python
# services/categories.py
from sqlalchemy.orm import Session
from models import Category
from schemas import CategoryCreate
from typing import List, Optional

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

def list_categories(
    db: Session,
    user_id: int,
    type_filter: Optional[str] = None,
) -> List[Category]:
    """返回分类列表，首次调用自动初始化默认分类"""

def create_category(
    db: Session,
    user_id: int,
    data: CategoryCreate,
) -> Category:
    """创建自定义分类"""

def delete_category(
    db: Session,
    cat_id: int,
    user_id: int,
) -> bool:
    """删除分类（仅自定义分类可删除）"""
```

### 实现要点

- `_ensure_defaults()` 在 `list_categories` 中调用
- 默认分类判断逻辑：`existing = db.query(Category).filter(Category.user_id == user_id).count()`
- 删除时检查 `is_custom` 字段

---

## S4 — fitness service

### 函数签名

```python
# services/fitness.py
from sqlalchemy.orm import Session
from models import FitnessRecord
from schemas import FitnessCreate
from typing import List, Optional

def list_records(
    db: Session,
    user_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> List[FitnessRecord]:
    """返回健身记录列表"""

def create_record(
    db: Session,
    user_id: int,
    data: FitnessCreate,
) -> FitnessRecord:
    """创建健身记录"""

def delete_record(
    db: Session,
    record_id: int,
    user_id: int,
) -> bool:
    """删除健身记录"""
```

---

## S5 — stats service

### 函数签名

```python
# services/stats.py
from sqlalchemy.orm import Session
from models import Bill, FitnessRecord
from typing import Dict, Any, List

def get_monthly_stats(
    db: Session,
    user_id: int,
    year: int,
    month: int,
) -> Dict[str, Any]:
    """
    返回月度统计：
    {
        "expense": float,
        "income": float,
        "balance": float,
        "category_stats": List[dict],
        "bill_count": int,
        "fitness_minutes": int,
        "fitness_calories": int,
        "fitness_count": int,
    }
    """

def get_today_stats(
    db: Session,
    user_id: int,
) -> Dict[str, Any]:
    """
    返回今日统计：
    {
        "expense": float,
        "income": float,
        "fitness_minutes": int,
        "fitness_calories": int,
    }
    """
```

### 聚合逻辑（从 router 迁移）

```python
# stats service 内部实现
def _get_bills_range(db, user_id, start, end):
    return db.query(Bill).filter(
        Bill.user_id == user_id,
        Bill.date >= start,
        Bill.date < end,
    ).all()

def _aggregate_bills(bills):
    expense = sum(b.amount for b in bills if b.type == "expense")
    income = sum(b.amount for b in bills if b.type == "income")
    
    # 分类统计
    cat_totals = {}
    for b in bills:
        if b.type == "expense":
            cat_totals[b.category_name] = cat_totals.get(b.category_name, 0) + b.amount
    
    return expense, income, cat_totals
```

---

## S6 — settings service

### 函数签名

```python
# services/settings.py
from sqlalchemy.orm import Session
from models import Settings
from schemas import SettingsUpdate
from typing import Optional

def get_settings(
    db: Session,
    user_id: int,
) -> Settings:
    """获取用户设置，不存在则创建默认"""

def update_settings(
    db: Session,
    user_id: int,
    data: SettingsUpdate,
) -> Settings:
    """更新用户设置"""
```

---

## S7 — data service

### 函数签名

```python
# services/data.py
from sqlalchemy.orm import Session
from models import Bill, FitnessRecord, Settings
from typing import Dict, Any, List
from pydantic import BaseModel

class ImportData(BaseModel):
    bills: List[Dict[str, Any]] = []
    fitness: List[Dict[str, Any]] = []
    settings: Dict[str, Any] = {}

def export_data(
    db: Session,
    user_id: int,
) -> Dict[str, Any]:
    """导出全部数据"""

def import_data(
    db: Session,
    user_id: int,
    data: ImportData,
) -> Dict[str, Any]:
    """
    导入数据（清空旧数据后写入）
    返回 {"ok": True, "bills": N, "fitness": M}
    """
```

---

## S8 — Router 层瘦身

每个 router 变为：

```python
# 重构前（业务逻辑在 router）
@router.get("")
def list_bills(..., db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    q = db.query(Bill).filter(...)
    # ... 大量业务逻辑 ...
    return items

# 重构后（router 只做参数传递）
@router.get("", response_model=list[BillOut])
def list_bills(..., db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return services.bills.list_bills(db, user["user_id"], ...)
```

---

*最后更新：2026-08-27*
