# 抱布记 · Design Documents

> 各模块的详细设计。Agent 根据此层生成实现细节。

---

## D0 — 整体架构

```
┌─────────────────────────────────────────────────────┐
│                   微信小程序                         │
│  ┌─────────────────────────────────────────────┐   │
│  │              pages/                          │   │
│  │  login / main / index / record / history    │   │
│  │  settings / category / import-bill          │   │
│  │  fitness/ (5 pages)                         │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │              utils/                          │   │
│  │  api.js (HTTP客户端)                         │   │
│  │  storage.js (本地缓存)                       │   │
│  │  config.js (常量配置)                        │   │
│  │  init.js / migrations.js                    │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────┬────────────────────────────┘
                       │ HTTP REST API
                       ▼
┌─────────────────────────────────────────────────────┐
│                 FastAPI 后端                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ routers/ │  │ services/│  │ models.py        │  │
│  │ (薄层)   │→ │ (业务逻辑)│  │ (ORM 映射)       │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│                      │                              │
│                      ▼                              │
│  ┌──────────────────────────────────────────────┐  │
│  │           database.py + SQLite               │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## D1 — 后端架构设计

### 分层规则

| 层 | 职责 | 禁止事项 |
|----|------|---------|
| `routers/` | 接收请求，参数校验，调用 service，返回响应 | 不包含业务逻辑，不直接操作 DB |
| `services/` | 业务逻辑，数据库操作，数据聚合 | 不处理 HTTP 细节，不构造响应体 |
| `models.py` | SQLAlchemy ORM 映射 | 不包含业务逻辑 |
| `schemas.py` | Pydantic 数据模型 | 不随业务变化频繁变动 |

### 目录结构（重构后）

```
backend/
├── main.py              # 入口，中间件，路由注册
├── database.py          # SQLAlchemy 引擎配置
├── models.py            # ORM 模型
├── schemas.py           # Pydantic 模型
├── auth.py              # JWT 工具函数
├── routers/             # API 路由（薄层）
│   ├── __init__.py
│   ├── auth.py
│   ├── bills.py
│   ├── categories.py
│   ├── fitness.py
│   ├── stats.py
│   ├── settings.py
│   └── data.py
├── services/            # 业务逻辑层（新增）
│   ├── __init__.py
│   ├── bills.py
│   ├── categories.py
│   ├── fitness.py
│   ├── stats.py
│   ├── settings.py
│   └── data.py
├── tests/               # 测试
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_bills.py
│   └── test_stats.py
├── .env
├── .env.example
├── requirements.txt
├── baobaoji.db
└── backups/
```

### 服务层设计原则

1. **一个 service 对应一个资源**：`services/bills.py` 只管账单
2. **service 函数返回模型对象或原始数据**：不构造响应体
3. **service 处理所有数据库交互**：router 层只负责调用
4. **复用数据库 session**：通过 `get_db()` 注入

### 示例：service 层模式

```python
# services/bills.py
from sqlalchemy.orm import Session
from models import Bill
from schemas import BillCreate

def list_bills(db: Session, user_id: int, **filters) -> list[Bill]:
    q = db.query(Bill).filter(Bill.user_id == user_id)
    # 应用筛选...
    return q.order_by(...).offset(...).limit(...).all()

def create_bill(db: Session, user_id: int, data: BillCreate) -> Bill:
    bill = Bill(user_id=user_id, **data.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill
```

```python
# routers/bills.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from services.bills import list_bills, create_bill
from schemas import BillCreate, BillOut

router = APIRouter(prefix="/api/bills", tags=["bills"])

@router.get("", response_model=list[BillOut])
def get_bills(..., db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return list_bills(db, user["user_id"], ...)

@router.post("", response_model=BillOut)
def add_bill(data: BillCreate, ...):
    return create_bill(db, user["user_id"], data)
```

---

## D2 — 统计逻辑迁移

### 现状问题

`stats.py` 路由直接从数据库取账单，然后在 Python 里聚合计算。数据量大时性能差。

### 设计决策

**月度统计**：保留在 Python 层聚合（数据量小，SQL 聚合复杂）
**今日统计**：保留在 Python 层聚合（同上）

**不做 SQL 聚合的原因**：
1. SQLite 对于几百条数据，Python 聚合和 SQL 聚合性能差异可忽略
2. SQL 聚合代码更复杂，不利于维护
3. 分类统计需要 join categories 表获取颜色，Python 层更灵活

### 但要做的是：把聚合逻辑从 router 移到 service

```python
# services/stats.py
def get_monthly_stats(db: Session, user_id: int, year: int, month: int) -> dict:
    # 查询账单
    # 聚合计算
    # 返回 dict，不含 ORM 对象
```

---

## D3 — 前端架构设计

### 现状问题

1. `storage.js` 618 行，记账和健身混在一起
2. `moduleManager.js` 已注册但从未被使用（死代码）
3. `config.js` 默认分类与后端重复
4. 多个页面重复工具函数（formatDate、calcStats 等）

### 重构策略

#### 3.1 清理死代码

- 删除 `moduleManager.js`（未使用）
- 删除 `modules/` 目录（未集成）
- `storage.js` 保留但精简（只保留记账相关）

#### 3.2 统一工具函数

创建 `utils/helpers.js`：
```javascript
// utils/helpers.js
function formatDate(date) { ... }
function formatAmount(num) { ... }
function getPaymentName(method) { ... }
function groupByDate(items) { ... }
```

所有页面引用 `helpers.js`，删除各自重复的实现。

#### 3.3 统一默认分类

**单一数据源**：默认分类只在后端 `routers/categories.py` 定义。

前端 `config.js` 删除默认分类，改为从 API 加载。

如果前端需要静态展示（如 quick select），使用 emoji 硬编码，不包含 id/name 等业务字段。

#### 3.4 删除 storage.js 中的健身逻辑

`storage.js` 中健身相关函数删除，因为健身数据只走云端 API，不需要本地缓存。

---

## D4 — 数据模型

### 保持不变

以下模型和字段不变，保证 API 兼容性：

```
User      (id, username, password_hash, created_at)
Bill      (id, user_id, type, amount, category_id, category_name,
           payment_method, remark, date, time, created_at)
Category  (id, user_id, type, name, icon, color, is_custom, sort_order)
FitnessRecord (id, user_id, exercise_type, duration_minutes,
               calories, date, time, note)
Settings  (id, user_id, monthly_budget,
           fitness_daily_goal_minutes, fitness_daily_goal_calories)
```

### 索引保持不变

- `ix_bills_user_date` (user_id, date)
- `ix_categories_user_type` (user_id, type)
- `ix_fitness_user_date` (user_id, date)

---

## D5 — 安全设计

### 现状

JWT 密码写在 `.env`，默认值 `"baobaoji-secret-key-change-in-production"` 已在 README 中暴露。

### 修复计划

1. `.env.example` 明确标注"必须修改"
2. README 删除默认密钥值
3. 添加请求频率限制（防止暴力破解）

---

## D6 — 测试策略

### 现状

15 个测试全部通过，覆盖认证、账单 CRUD、统计。

### 重构后要求

- 所有现有测试必须通过
- service 层新增单元测试（独立于 router）
- 不减少任何现有测试覆盖率

---

## D7 — 重构执行顺序

```
Phase 1: 后端 service 层
  1.1 创建 services/ 目录和 __init__.py
  1.2 抽取 bills service
  1.3 抽取 categories service
  1.4 抽取 fitness service
  1.5 抽取 stats service
  1.6 抽取 settings service
  1.7 抽取 data service
  1.8 更新所有 router 使用 service
  1.9 运行测试，确保全部通过

Phase 2: 前端清理
  2.1 删除 moduleManager.js 和 modules/ 目录
  2.2 创建 utils/helpers.js
  2.3 迁移所有页面的工具函数
  2.4 清理 storage.js（删除健身逻辑）
  2.5 统一默认分类来源（后端唯一）
  2.6 测试小程序运行正常

Phase 3: 安全加固
  3.1 更新 .env.example
  3.2 更新 README（删除默认密钥）
  3.3 添加请求频率限制
```

---

*最后更新：2026-08-27*
