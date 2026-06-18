# 抱布记 📒 — 个人记账 + 健身小程序

一款全栈微信小程序，覆盖**记账理财**与**健身记录**两大生活模块。  
前端基于微信小程序原生框架，后端基于 FastAPI + SQLite，数据云端存储，多端同步。

> **AppID**: `wxe71d9fa12da3a855`  
> **UI 风格**: 毛玻璃绿 — 柔和、通透、护眼

---

## ✨ 功能特性

### 📊 记账模块

| 页面 | 功能 |
|------|------|
| **首页/仪表盘** | 本月收支概览、支出占比饼图、预算进度、最近记录 |
| **记账** | 自建数字键盘、收支分类选择、支付方式（微信/支付宝/现金/银行卡/信用卡）、备注+常用标签、日期时间选择 |
| **明细** | 日期分组展示、TOP统计栏、筛选（类型/支付方式/时间范围）、左滑编辑/删除 |
| **分类管理** | 支出/收入分类切换、添加自定义分类（图标+颜色）、编辑/删除/重置默认 |
| **导入账单** | 按自然月查看并批量导入账单记录 |

### 💪 健身模块

| 页面 | 功能 |
|------|------|
| **今日运动** | 今日运动统计概览 |
| **运动记录** | 运动类型选择、时长、卡路里计算 |
| **运动分析** | 周期统计视图 |
| **历史记录** | 历史运动数据回顾 |
| **设置** | 每日运动目标配置 |

### ⚙️ 通用

- **用户登录/注册** — 简单账号密码，JWT 认证
- **设置** — 月预算、每日健身目标、数据导出/导入、清空数据
- **数据同步** — 所有数据存储在云端，换手机不丢

---

## 🏗️ 架构

```
┌──────────────────────────────┐
│     微信小程序（前端）          │
│  WXML + WXSS + JS（原生）     │
│  utils/api.js → HTTP 调用     │
└──────────┬───────────────────┘
           │ HTTP (REST API)
           ▼
┌──────────────────────────────┐
│    FastAPI 后端（本机服务器）    │
│  localhost:8089               │
│                              │
│  ┌─ routers/ ─────────────┐  │
│  │ auth bills categories  │  │
│  │ fitness stats settings │  │
│  │ data                   │  │
│  └────────────────────────┘  │
│         │                    │
│         ▼                    │
│  SQLite (baobaoji.db)        │
└──────────────────────────────┘
```

### 后端 API 路由

| 路由 | 说明 |
|------|------|
| `POST /api/auth/register` | 注册 |
| `POST /api/auth/login` | 登录（返回 JWT） |
| `GET /api/bills` | 账单列表（支持筛选分页） |
| `POST /api/bills` | 创建账单 |
| `PUT /api/bills/:id` | 更新账单 |
| `DELETE /api/bills/:id` | 删除账单 |
| `GET /api/categories` | 分类列表 |
| `POST /api/categories` | 创建分类 |
| `DELETE /api/categories/:id` | 删除分类 |
| `GET /api/stats/monthly` | 月度统计 |
| `GET /api/stats/today` | 今日统计 |
| `GET /api/fitness/records` | 健身记录列表 |
| `POST /api/fitness/records` | 创建健身记录 |
| `DELETE /api/fitness/records/:id` | 删除健身记录 |
| `GET/PUT /api/settings` | 用户设置 |
| `GET /api/data/export` | 数据导出 |
| `POST /api/data/import` | 数据导入 |
| `GET /api/health` | 健康检查 |

---

## 🎨 设计系统

### 配色

| 角色 | 色值 | 用途 |
|------|------|------|
| **主色调** | `#5cb8a0` | 品牌主色、强调色 |
| **主色亮** | `#7cccb8` | 渐变、装饰 |
| **背景** | `#f0f6f3` | 页面背景 |
| **卡片** | `rgba(255,255,255,0.7)` | 毛玻璃卡片 |
| **支出** | `#FF6B6B` | 支出标识 |
| **收入** | `#00B894` | 收入标识 |

### 组件

- 毛玻璃（glass-card）卡片组件
- 自建数字键盘
- 横向滚动分类选择器
- 下拉刷新支持
- 自定义导航栏

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| **前端框架** | 微信小程序原生（WXML / WXSS / JS） |
| **后端框架** | Python FastAPI |
| **数据库** | SQLAlchemy + SQLite |
| **认证** | JWT（python-jose） |
| **密码** | bcrypt（passlib） |
| **运行环境** | Uvicorn |

---

## 🚀 快速开始

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python main.py
# → 服务运行在 http://localhost:8089
```

API 默认监听 `0.0.0.0:8089`，首次启动自动创建 SQLite 数据库 `baobaoji.db`。

### 2. 导入小程序

1. 打开微信开发者工具
2. 导入项目，选择本项目根目录
3. AppID 填写 `wxe71d9fa12da3a855`（或你的测试号）
4. 修改 `utils/api.js` 中的 `BASE_URL` 指向你的后端地址
5. 点击编译运行

### 3. Nginx 反向代理（可选）

后端已在服务器通过 nginx 代理到 `/api/baobaoji/` 路径：

```nginx
location /api/baobaoji/ {
    rewrite ^/api/baobaoji/(.*)$ /$1 break;
    proxy_pass http://127.0.0.1:8089;
}
```

---

## 📁 项目结构

```
accounting-miniprogram/
├── app.js                    # 应用入口
├── app.json                  # 应用配置（13个页面）
├── app.wxss                  # 全局样式（CSS变量、毛玻璃组件）
├── sitemap.json
├── project.config.json
│
├── backend/                  # FastAPI 后端
│   ├── main.py               # 服务入口
│   ├── database.py           # SQLAlchemy 数据库配置
│   ├── models.py             # 数据模型（User/Bill/Category/FitnessRecord/Settings）
│   ├── schemas.py            # Pydantic 数据模式
│   ├── auth.py               # JWT 认证工具
│   ├── routers/              # API 路由
│   │   ├── auth.py
│   │   ├── bills.py
│   │   ├── categories.py
│   │   ├── fitness.py
│   │   ├── stats.py
│   │   ├── settings.py
│   │   └── data.py
│   └── requirements.txt
│
├── pages/                    # 前端页面（13个）
│   ├── login/                # 登录/注册
│   ├── main/                 # 模块总览首页
│   ├── index/                # 记账仪表盘
│   ├── record/               # 记账输入
│   ├── history/              # 账单明细
│   ├── settings/             # 设置
│   ├── category/             # 分类管理
│   ├── import-bill/          # 导入账单
│   └── fitness/              # 健身模块（4个页面）
│       ├── index/
│       ├── record/
│       ├── analytics/
│       └── history/
│
├── modules/                  # 模块声明
│   ├── accounting/manifest.js
│   └── fitness/manifest.js
│
├── utils/                    # 工具库
│   ├── api.js                # API 客户端
│   ├── config.js             # 配置常量
│   ├── storage.js            # 本地存储
│   ├── init.js               # 初始化
│   ├── migrations.js          # 数据迁移
│   ├── moduleManager.js      # 模块管理器
│   └── calorieCalculator.js  # 卡路里计算器
│
└── images/                   # Tab 图标
    ├── home.png / home-active.png
    ├── list.png / list-active.png
    ├── user.png / user-active.png
```

---

## 🔄 数据模型

### User
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String(50) | 用户名（唯一） |
| password_hash | String(128) | bcrypt 哈希 |
| created_at | DateTime | 注册时间 |

### Bill
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 所属用户 |
| type | String(10) | expense / income |
| amount | Float | 金额 |
| category_id | Integer | 分类 ID |
| category_name | String(50) | 分类名称 |
| payment_method | String(20) | wechat/alipay/cash/bankcard/credit |
| remark | Text | 备注 |
| date | String(10) | 日期 2026-06-15 |
| time | String(5) | 时间 12:30 |

### Category
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 所属用户 |
| type | String(10) | expense / income |
| name | String(50) | 分类名称 |
| icon | String(10) | Emoji 图标 |
| color | String(20) | 颜色值 |
| is_custom | Boolean | 是否自定义 |
| sort_order | Integer | 排序 |

### FitnessRecord
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 所属用户 |
| exercise_type | String(50) | 运动类型 |
| duration_minutes | Integer | 时长（分钟） |
| calories | Integer | 消耗卡路里 |
| date | String(10) | 日期 |
| time | String(5) | 时间 |
| note | Text | 备注 |

---

## 📄 License

MIT
