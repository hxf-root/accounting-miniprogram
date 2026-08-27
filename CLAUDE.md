# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

"抱布记" — 全栈微信小程序，覆盖**记账理财**与**健身记录**两大模块。

- **前端**: 微信小程序原生（WXML + WXSS + JS），无 npm 构建
- **后端**: Python FastAPI + SQLAlchemy ORM + SQLite
- **部署**: systemd 服务 + Makefile 管理

线上后端地址: `https://xuefei.art/api/baobaoji`

## 运行方式

### 后端

```bash
cd backend
pip install -r requirements.txt
python main.py          # → http://0.0.0.0:8089，文档 http://0.0.0.0:8089/docs
```

或者用 Makefile（自动创建 venv）:

```bash
make start              # 前台启动
make start-d            # 后台 daemon
make test               # 运行测试
make install            # 安装依赖
make deploy             # git pull + install + 重启服务
make backup             # 备份 SQLite 数据库
```

### 前端

用微信开发者工具打开项目根目录即可，无需构建。AppID: `wxe71d9fa12da3a855`（也可用测试号）。

## 架构

```
小程序前端 (WXML/WXSS/JS)          FastAPI 后端 (Python)
─────────────────────────         ─────────────────────
modules/  → 模块声明              backend/
pages/    → 13 个页面              ├─ main.py        入口 + CORS + 全局异常处理
utils/    → 工具库                 ├─ database.py    SQLAlchemy + SQLite 配置
  api.js       HTTP 客户端         ├─ models.py      5 个数据模型
  config.js    常量/默认分类        ├─ schemas.py     Pydantic schema
  storage.js   本地存储服务         ├─ auth.py        JWT 认证 (python-jose + bcrypt)
  calorieCalculator.js  卡路里     ├─ routers/       7 个路由模块
  moduleManager.js      模块管理      ├─ auth.py       注册/登录
  init.js      初始化                  ├─ bills.py      账单 CRUD
  migrations.js 数据迁移               ├─ categories.py 分类管理
                                       ├─ fitness.py    健身记录
                                       ├─ stats.py      统计
                                       ├─ settings.py   用户设置
                                       └─ data.py       导入/导出
         HTTP REST API               └─ tests/        15 个 pytest 测试
              ↓
         SQLite (baobaoji.db)

部署: deploy/baobaoji.service (systemd) + deploy/deploy.sh
```

### 模块系统

前端通过 `modules/*/manifest.js` 声明模块，由 `utils/moduleManager.js`（单例）统一注册。当前模块:
- **accounting**: 记账 (record, history, category, import)
- **fitness**: 健身 (record, analytics, history, goal)

### 数据模型（后端 5 个表）

| 模型 | 表名 | 关键字段 |
|------|------|---------|
| User | `users` | id, username, password_hash, created_at |
| Bill | `bills` | user_id, type(expense/income), amount, category_name, payment_method, date, time |
| Category | `categories` | user_id, type, name, icon, color, is_custom, sort_order |
| FitnessRecord | `fitness_records` | user_id, exercise_type, duration_minutes, calories, date, time |
| Settings | `settings` | user_id(unique), monthly_budget, fitness_daily_goal_minutes/calories |

### 页面路由

Tab 栏（4 项）: `pages/main/main`（模块）| `pages/index/index`（记账）| `pages/fitness/index`（健身）| `pages/settings/settings`（我的）

其他页面: login, record, history, category, import-bill, fitness/analytics, fitness/history, fitness/settings

### API 接口

所有需认证的接口 Header 中传 `Authorization: Bearer <token>`。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| GET/POST | `/api/bills` | 账单列表/创建 |
| PUT/DELETE | `/api/bills/:id` | 更新/删除 |
| GET/POST | `/api/categories` | 分类列表/创建 |
| DELETE | `/api/categories/:id` | 删除分类 |
| GET/POST | `/api/fitness/records` | 健身记录列表/创建 |
| DELETE | `/api/fitness/records/:id` | 删除 |
| GET | `/api/stats/monthly` | 月度统计 |
| GET | `/api/stats/today` | 今日统计 |
| GET/PUT | `/api/settings` | 获取/更新设置 |
| GET/POST/DELETE | `/api/data/export` `/api/data/import` `/api/data` | 数据导出、导入与清空 |
| GET | `/api/health` | 健康检查（含 uptime、database 状态） |

### 认证机制

JWT (HS256)，默认 720 小时过期。`SECRET_KEY`、`JWT_EXPIRE_HOURS` 等通过 `.env` 配置，`backend/.env.example` 包含所有可配置项。

### 主题色

主色 `#5cb8a0`，支出红 `#FF6B6B`，收入绿 `#00B894`，背景 `#f0f6f3`。
毛玻璃卡片: `rgba(255,255,255,0.7)` backdrop-filter。
