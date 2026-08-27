# 抱布记 · 实施计划

> 基于 motivation + design，分阶段执行。每阶段一个 commit。

---

## Phase 1: 后端 Service 层

### Task 1.1 — 创建 services 包

**文件**：
- Create: `backend/services/__init__.py`
- Create: `backend/services/bills.py`
- Create: `backend/services/categories.py`
- Create: `backend/services/fitness.py`
- Create: `backend/services/stats.py`
- Create: `backend/services/settings.py`
- Create: `backend/services/data.py`

**内容**：从对应 router 迁移业务逻辑，保持函数签名兼容。

**验证**：`cd backend && python -m pytest tests/ -v` 全部通过

---

### Task 1.2 — 迁移 bills service

**source**：`backend/routers/bills.py`
**target**：`backend/services/bills.py`

迁移内容：
- `list_bills()` 函数（含筛选、分页逻辑）
- `create_bill()` 函数
- `update_bill()` 函数
- `delete_bill()` 函数

router 变为：
```python
from services.bills import list_bills, create_bill, update_bill, delete_bill

@router.get("")
def get_bills(...):
    return list_bills(db, user["user_id"], ...)
```

**验证**：运行测试 `test_bills.py`

---

### Task 1.3 — 迁移 categories service

**source**：`backend/routers/categories.py`
**target**：`backend/services/categories.py`

迁移内容：
- `DEFAULT_EXPENSE` 和 `DEFAULT_INCOME` 常量
- `_ensure_defaults()` 函数
- `list_categories()` 函数
- `create_category()` 函数
- `delete_category()` 函数

**验证**：运行测试

---

### Task 1.4 — 迁移 fitness service

**source**：`backend/routers/fitness.py`
**target**：`backend/services/fitness.py`

迁移内容：
- `list_fitness()` 函数
- `create_fitness()` 函数
- `delete_fitness()` 函数

**验证**：新增测试 `tests/test_fitness.py`

---

### Task 1.5 — 迁移 stats service

**source**：`backend/routers/stats.py`
**target**：`backend/services/stats.py`

迁移内容：
- `monthly_stats()` 函数的核心逻辑（Python 聚合部分）
- `today_stats()` 函数的核心逻辑

**注意**：SQL 查询部分保留在 service，聚合计算也移到 service。

**验证**：运行测试 `test_stats.py`

---

### Task 1.6 — 迁移 settings service

**source**：`backend/routers/settings.py`
**target**：`backend/services/settings.py`

迁移内容：
- `_ensure_settings()` 函数
- `get_settings()` 函数
- `update_settings()` 函数

**验证**：新增测试

---

### Task 1.7 — 迁移 data service

**source**：`backend/routers/data.py`
**target**：`backend/services/data.py`

迁移内容：
- `export_data()` 函数
- `import_data()` 函数

**验证**：新增测试

---

### Task 1.8 — 瘦身 router 层

更新所有 router 文件，移除业务逻辑，只保留：
- FastAPI 装饰器
- 参数解析
- 调用 service 函数
- 返回结果

**验证**：全量测试通过

---

## Phase 2: 前端清理

### Task 2.1 — 创建 helpers.js

**文件**：Create `utils/helpers.js`

内容：见 `designs/frontend-refactor.md` F2 节

---

### Task 2.2 — 清理 storage.js

**文件**：Edit `utils/storage.js`

删除：
- `fitnessService` 整个对象
- `STORAGE_KEYS.FITNESS_ACTIVITIES`
- `STORAGE_KEYS.FITNESS_GOALS`
- 所有健身相关的 get/set 方法

保留：
- `safeStorage`
- `billService`
- `categoryService`
- `settingsService`
- `dataService`

---

### Task 2.3 — 精简 config.js

**文件**：Edit `utils/config.js`

删除：
- `defaultExpenseCategories`
- `defaultIncomeCategories`

保留：
- `STORAGE_KEYS`
- `APP_CONFIG`
- `SCHEMA_VERSION`

---

### Task 2.4 — 删除死代码

**删除**：
- `utils/moduleManager.js`
- `modules/accounting/manifest.js`
- `modules/fitness/manifest.js`
- `pages/import-bill/` 目录

---

### Task 2.5 — 更新 init.js

**文件**：Edit `utils/init.js`

删除合并默认分类的逻辑（因为 config.js 不再有默认分类）

---

### Task 2.6 — 更新各页面使用 helpers

**文件**：
- Edit `pages/main/main.js`
- Edit `pages/index/index.js`
- Edit `pages/history/history.js`
- Edit `pages/record/record.js`
- Edit `pages/fitness/index.js`
- Edit `pages/fitness/analytics.js`
- Edit `pages/settings/settings.js`

每个页面：
1. 引入 `const { formatAmount, getPaymentName, ... } = require('../../utils/helpers.js')`
2. 删除本地重复的工具函数
3. 调用改为 `helpers.xxx()` 或直接解构调用

---

## Phase 3: 安全加固

### Task 3.1 — 更新 .env.example

**文件**：Edit `backend/.env.example`

添加注释，明确标注必须修改的值。

---

### Task 3.2 — 更新 README

**文件**：Edit `README.md`

删除默认 JWT 密钥值。

---

### Task 3.3 — 添加请求频率限制

**文件**：Edit `backend/main.py`

添加简单的 IP 级限流（可选，如果时间允许）。

---

## 执行顺序

```
Phase 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8
    ↓ 测试全部通过
Phase 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6
    ↓ 小程序编译正常
Phase 3.1 → 3.2 → 3.3
    ↓ git add && git commit
```

---

## 验收标准

1. 后端测试 15+ 个全部通过
2. 小程序无编译错误
3. API 接口行为与重构前完全一致
4. 数据无损（手动验证：导入测试数据，确认都能读取）
5. git log 每阶段一个 commit

---

*最后更新：2026-08-27*
