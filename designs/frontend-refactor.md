# 抱布记 · 前端重构设计

> 前端代码清理和设计统一。

---

## F1 — 文件清理

### 删除文件

| 文件 | 原因 |
|------|------|
| `utils/moduleManager.js` | 已注册但从未使用，死代码 |
| `modules/accounting/manifest.js` | 未集成，死代码 |
| `modules/fitness/manifest.js` | 未集成，死代码 |
| `pages/import-bill/` | 导入功能实际未使用（用户直接用 API 导入） |

### 保留文件

所有其他文件保留，只做结构调整。

---

## F2 — helpers.js 工具库

新建 `utils/helpers.js`，集中所有页面重复的工具函数：

```javascript
// utils/helpers.js

/**
 * 格式化日期为 YYYY-MM-DD
 */
function formatDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * 格式化金额（保留两位小数）
 */
function formatAmount(num) {
  if (num === undefined || num === null) return '0.00'
  return Number(num).toFixed(2)
}

/**
 * 支付方式中文映射
 */
const PAYMENT_NAMES = {
  wechat: '微信',
  alipay: '支付宝',
  cash: '现金',
  bankcard: '银行卡',
  credit: '信用卡',
  other: '其他',
}

function getPaymentName(method) {
  return PAYMENT_NAMES[method] || method || ''
}

/**
 * 按日期分组账单
 */
function groupByDate(bills) {
  const map = {}
  ;(bills || []).forEach(b => {
    const d = b.date || ''
    if (!map[d]) {
      map[d] = { date: d, bills: [], expense: 0, income: 0 }
    }
    const amt = parseFloat(b.amount) || 0
    map[d].bills.push(b)
    if (b.type === 'expense') map[d].expense += amt
    else map[d].income += amt
  })
  return Object.values(map)
    .map(g => ({
      ...g,
      expense: parseFloat(g.expense.toFixed(2)),
      income: parseFloat(g.income.toFixed(2)),
    }))
    .sort((a, b) => b.date.localeCompare(a.date))
}

/**
 * 计算预算百分比
 */
function calcBudgetPercent(budget, expense) {
  if (!budget || budget <= 0 || !expense || expense <= 0) return 0
  return Math.min(100, Math.round((expense / budget) * 100))
}

/**
 * 计算统计（账单列表 → 统计对象）
 */
function calcStats(bills) {
  let totalExpense = 0
  let totalIncome = 0
  for (const bill of bills) {
    const amount = Number(bill.amount) || 0
    if (bill.type === 'expense') totalExpense += amount
    else if (bill.type === 'income') totalIncome += amount
  }
  return {
    totalCount: bills.length,
    totalExpense: totalExpense.toFixed(2),
    totalIncome: totalIncome.toFixed(2),
    totalExpenseNum: totalExpense,
    totalIncomeNum: totalIncome,
  }
}

module.exports = {
  formatDate,
  formatAmount,
  getPaymentName,
  groupByDate,
  calcBudgetPercent,
  calcStats,
}
```

---

## F3 — 页面重构清单

### pages/main/main.js

- [ ] 删除 `formatAmount` 本地实现，改用 `helpers.formatAmount`
- [ ] 删除 `setGreeting` 本地实现，移至 helpers（或保留，因为是页面特有逻辑）

### pages/index/index.js

- [ ] 删除 `getPaymentMethodName`，改用 `helpers.getPaymentName`
- [ ] 删除 `buildBudgetData` 中的重复计算，使用 `helpers.calcBudgetPercent`

### pages/history/history.js

- [ ] 删除 `initDates`、`_fmtDate`，改用 `helpers.formatDate`
- [ ] 删除 `_groupByDate`，改用 `helpers.groupByDate`
- [ ] 删除 `formatDateDisplay`，保留（页面特有格式化）
- [ ] 删除 `getPaymentMethodName`，改用 `helpers.getPaymentName`

### pages/record/record.js

- [ ] 删除 `initDateTime`、`_fmtDate`、`_fmtTime`，改用 `helpers.formatDate`

### pages/fitness/index.js

- [ ] 删除 `formatDate`、`formatISO`，改用 `helpers.formatDate`

### pages/fitness/analytics.js

- [ ] 删除 `formatDate`、`getRangeDates` 中的重复逻辑，使用 `helpers.formatDate`

### pages/settings/settings.js

- [ ] 删除 `formatDate`，改用 `helpers.formatDate`
- [ ] 删除 `calcStats`，改用 `helpers.calcStats`
- [ ] 删除 `calcBudgetPercent`，改用 `helpers.calcBudgetPercent`

---

## F4 — storage.js 清理

删除健身相关逻辑（健身数据不缓存本地）：

```javascript
// 删除以下内容：
// - fitnessService 整个对象
// - STORAGE_KEYS.FITNESS_ACTIVITIES
// - STORAGE_KEYS.FITNESS_GOALS
// - 所有健身相关的 get/set 方法
```

只保留记账相关：
- `billService`
- `categoryService`
- `settingsService`
- `dataService`

---

## F5 — 默认分类统一

**当前问题**：默认分类在两个地方定义：
1. `backend/routers/categories.py`（Python 列表）
2. `utils/config.js`（JS 对象）

**决策**：以后端为唯一数据源。

**前端修改**：
- 删除 `config.js` 中的 `defaultExpenseCategories` 和 `defaultIncomeCategories`
- 前端所有分类数据从 `/api/categories` 接口获取
- `init.js` 不再需要合并本地默认分类

---

## F6 — 最终目录结构

```
accounting-miniprogram/
├── app.js
├── app.json
├── app.wxss
├── sitemap.json
├── project.config.json
│
├── pages/
│   ├── login/           # 不变
│   ├── main/            # 不变
│   ├── index/           # 不变
│   ├── record/          # 不变
│   ├── history/         # 不变
│   ├── settings/        # 不变
│   ├── category/        # 不变
│   └── fitness/         # 不变（5个页面）
│
├── utils/
│   ├── api.js           # 不变
│   ├── config.js        # 精简（删除默认分类）
│   ├── helpers.js       # 新增（统一工具函数）
│   ├── storage.js       # 精简（删除健身逻辑）
│   ├── init.js          # 微调（适配新 config）
│   ├── migrations.js    # 不变
│   └── calorieCalculator.js  # 不变
│
├── images/              # 不变
├── backend/             # 见 D1
├── designs/             # 新增（设计文档）
├── motivation.md        # 新增
└── README.md
```

---

*最后更新：2026-08-27*
