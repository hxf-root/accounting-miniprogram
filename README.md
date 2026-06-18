# 抱布记 📒 — 个人记账 + 健身小程序

一款全栈微信小程序，覆盖**记账理财**与**健身记录**两大生活模块。  
前端基于微信小程序原生框架（WXML + WXSS + JS），后端基于 **FastAPI + SQLAlchemy + SQLite**，数据云端存储，多端同步。

> **AppID**: `wxe71d9fa12da3a855`  
> **UI 风格**: 毛玻璃绿 — 柔和、通透、护眼  
> **线上后端**: `http://81.70.209.199:8089`

---

## 📱 页面总览

共 **13 个页面**，底部 4 个 Tab：

| Tab | 页面路径 | 说明 |
|-----|---------|------|
| 模块 | `pages/main/main` | 双模块（记账/健身）总览入口 |
| 记账 | `pages/index/index` | 记账仪表盘 |
| 健身 | `pages/fitness/index` | 健身首页 |
| 我的 | `pages/settings/settings` | 全局设置 |

### 📊 记账模块

| 页面 | 功能 |
|------|------|
| **首页/仪表盘** | 本月收支概览、支出占比饼图、预算进度、最近记录 |
| **记账** | 自建数字键盘、收支分类选择、5 种支付方式、备注+常用标签、日期时间选择 |
| **明细** | 日期分组展示、TOP 统计栏、筛选（类型/支付方式/时间范围）、左滑编辑/删除 |
| **分类管理** | 支出/收入分类切换、添加自定义分类（图标+颜色）、编辑/删除/重置默认 |
| **导入账单** | 按自然月查看并批量导入账单记录 |

### 💪 健身模块

| 页面 | 功能 |
|------|------|
| **今日运动** | 今日运动统计概览（时长/卡路里/次数 vs 目标） |
| **运动记录** | 运动类型选择（跑步/游泳/骑行/瑜伽等）、时长/卡路里自动计算 |
| **运动分析** | 周期统计视图（周/月/年），按类型分布 |
| **历史记录** | 历史运动数据回顾，按日期分组 |
| **设置** | 每日运动目标（时长/卡路里）配置 |

### 🔐 通用

| 页面 | 功能 |
|------|------|
| **登录/注册** | 简单账号密码 + JWT 认证 |
| **设置** | 月预算、每日健身目标、数据导出/导入、清空数据 |

---

## 🏗️ 架构

```
┌──────────────────────────────────────────┐
│          微信小程序（前端）                  │
│  WXML + WXSS + JS（原生框架）              │
│                                          │
│  ┌─ utils/ ──────────────────────────┐  │
│  │ api.js        API 客户端（HTTP）    │  │
│  │ config.js     默认分类/常量配置      │  │
│  │ storage.js    本地存储服务          │  │
│  │ moduleManager.js  模块注册管理器    │  │
│  │ init.js       应用初始化+数据迁移    │  │
│  │ migrations.js 数据结构版本迁移      │  │
│  │ calorieCalculator.js  卡路里计算引擎 │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌─ modules/ ────────────────────────┐  │
│  │ accounting/manifest.js  记账模块声明 │  │
│  │ fitness/manifest.js     健身模块声明 │  │
│  └────────────────────────────────────┘  │
└────────────────┬─────────────────────────┘
                 │ HTTP (REST API)
                 ▼
┌──────────────────────────────────────────┐
│       FastAPI 后端（本机服务器）             │
│       127.0.0.1:8089                      │
│                                          │
│  ┌─ routers/ ────────────────────────┐  │
│  │ auth.py      登录/注册/JWT        │  │
│  │ bills.py     账单 CRUD + 筛选     │  │
│  │ categories.py 分类 CRUD + 重置    │  │
│  │ fitness.py   健身记录 CRUD        │  │
│  │ stats.py     月度/今日统计        │  │
│  │ settings.py  用户设置读写         │  │
│  │ data.py      数据导出/导入        │  │
│  └────────────────────────────────────┘  │
│         │                                │
│         ▼                                │
│  ┌─ models.py ──────────────────────┐  │
│  │ User / Bill / Category /         │  │
│  │ FitnessRecord / Settings         │  │
│  │ └── SQLite (baobaoji.db)         │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

### 模块化架构

采用轻量模块注册机制，`ModuleManager` 管理功能模块生命周期：

```js
// 模块声明示例（modules/accounting/manifest.js）
{
  id: 'accounting',       // 模块 ID
  name: '记账',           // 显示名称
  icon: '💰',             // 图标
  color: '#4ECDC4',       // 主题色
  version: '1.0.0',       // 模块版本
  capabilities: ['record', 'history', 'category', 'import'],
  pages: [                // 模块包含的页面列表
    { id: 'home',     name: '首页', path: '/pages/index/index' },
    { id: 'record',   name: '记录', path: '/pages/record/record' },
    { id: 'history',  name: '明细', path: '/pages/history/history' },
    { id: 'category', name: '分类', path: '/pages/category/category' },
    { id: 'import',   name: '导入', path: '/pages/import-bill/import-bill' }
  ]
}
```

当前注册模块：
- **accounting**（记账）— 💰 主题色 `#4ECDC4`
- **fitness**（健身）— 💪 主题色 `#FF6B6B`

---

## 🔌 API 接口

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册（username + password） |
| POST | `/api/auth/login` | 登录，返回 JWT Token |

### 账单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/bills` | 账单列表（支持 type/payment_method/日期筛选 + 分页） |
| POST | `/api/bills` | 创建账单 |
| PUT | `/api/bills/:id` | 更新账单 |
| DELETE | `/api/bills/:id` | 删除账单 |

### 分类

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/categories` | 分类列表（?type=expense\|income） |
| POST | `/api/categories` | 创建分类 |
| DELETE | `/api/categories/:id` | 删除分类 |

### 健身

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/fitness/records` | 健身记录列表（支持日期筛选+分页） |
| POST | `/api/fitness/records` | 创建健身记录 |
| DELETE | `/api/fitness/records/:id` | 删除健身记录 |

### 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats/monthly` | 月度统计（?year=&month=） |
| GET | `/api/stats/today` | 今日统计 |

### 设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取用户设置 |
| PUT | `/api/settings` | 更新用户设置 |

### 数据导入导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/data/export` | 导出全部数据（JSON） |
| POST | `/api/data/import` | 导入数据 |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 服务健康检查 |

所有需要认证的接口在 Header 中传递 `Authorization: Bearer <token>`。

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

### 默认支出分类

🍔 餐饮 · 🚗 交通 · 🛍️ 购物 · 🎬 娱乐 · 🏠 居住 · 🏥 医疗 · 📚 教育 · 📦 其他

### 默认收入分类

💰 工资 · 🎁 奖金 · 📈 理财 · ⏰ 兼职 · ✉️ 礼金 · 📦 其他

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| **前端框架** | 微信小程序原生（WXML / WXSS / JS） |
| **后端框架** | Python FastAPI (uvicorn) |
| **数据库** | SQLAlchemy ORM + SQLite |
| **认证** | JWT（python-jose） |
| **密码** | bcrypt（passlib） |
| **运行环境** | Linux (Tencent Cloud) + Uvicorn |
| **反向代理** | nginx → `/api/baobaoji/` |

---

## 🚀 快速开始

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python main.py
# → 服务运行在 http://0.0.0.0:8089
```

首次启动自动创建 SQLite 数据库 `baobaoji.db`。

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

小程序中 `BASE_URL` 改为 `https://你的域名/api/baobaoji` 即可通过 nginx 访问后端。

---

## 📁 项目结构

```
accounting-miniprogram/
├── app.js                     # 应用入口
├── app.json                   # 应用配置（13个页面 + 4个Tab）
├── app.wxss                   # 全局样式（CSS变量、毛玻璃组件）
├── sitemap.json
├── project.config.json        # 开发者工具配置（lib 3.14.2）
│
├── backend/                   # FastAPI 后端
│   ├── main.py                # 服务入口 + CORS + 路由注册
│   ├── database.py            # SQLAlchemy 数据库配置
│   ├── models.py              # 5个数据模型
│   ├── schemas.py             # Pydantic 数据模式
│   ├── auth.py                # JWT 认证工具
│   ├── routers/               # API 路由（7个模块）
│   │   ├── auth.py
│   │   ├── bills.py
│   │   ├── categories.py
│   │   ├── fitness.py
│   │   ├── stats.py
│   │   ├── settings.py
│   │   └── data.py
│   └── requirements.txt
│
├── pages/                     # 前端页面（13个）
│   ├── login/                 # 登录/注册
│   ├── main/                  # 模块总览首页
│   ├── index/                 # 记账仪表盘
│   ├── record/                # 记账输入
│   ├── history/               # 账单明细
│   ├── settings/              # 全局设置
│   ├── category/              # 分类管理
│   ├── import-bill/           # 导入账单
│   └── fitness/               # 健身模块（5个页面）
│       ├── index/             # 今日运动首页
│       ├── record/            # 运动记录
│       ├── analytics/         # 运动分析
│       ├── history/           # 历史记录
│       └── settings/          # 健身目标设置
│
├── modules/                   # 模块声明
│   ├── accounting/manifest.js # 记账模块注册
│   └── fitness/manifest.js    # 健身模块注册
│
├── utils/                     # 工具库
│   ├── api.js                 # API 客户端（HTTP 请求封装）
│   ├── config.js              # 配置常量（默认分类、存储键名）
│   ├── storage.js             # 本地存储服务（wx.setStorageSync 封装）
│   ├── init.js                # 应用初始化
│   ├── migrations.js          # 数据迁移（Schema v1→v2）
│   ├── moduleManager.js       # 模块管理器（注册/卸载/页面管理）
│   └── calorieCalculator.js   # 卡路里计算引擎（基于MET代谢当量）
│
└── images/                    # Tab 图标
    ├── home.png / home-active.png
    ├── list.png / list-active.png
    └── user.png / user-active.png
```

---

## 🗃️ 数据模型

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
| type | String(10) | `expense` / `income` |
| amount | Float | 金额 |
| category_id | Integer | 分类 ID |
| category_name | String(50) | 分类名称 |
| payment_method | String(20) | wechat / alipay / cash / bankcard / credit |
| remark | Text | 备注 |
| date | String(10) | 日期 `2026-06-15` |
| time | String(5) | 时间 `12:30` |

### Category

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 所属用户 |
| type | String(10) | `expense` / `income` |
| name | String(50) | 分类名称 |
| icon | String(10) | Emoji 图标 |
| color | String(20) | 颜色值 |
| is_custom | Boolean | 是否自定义 |
| sort_order | Integer | 排序序号 |

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

### Settings

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 所属用户（唯一） |
| monthly_budget | Float | 月预算 |
| fitness_daily_goal_minutes | Integer | 每日运动目标时长（默认 30 分钟） |
| fitness_daily_goal_calories | Integer | 每日运动目标卡路里（默认 300 kcal） |

---

## 🔄 数据存储与同步

### 云端（后端 SQLite）

所有核心数据存储在服务器的 `baobaoji.db` 中，通过 REST API 读写。换手机登录同一账号，数据自动同步。

### 本地缓存（微信 Storage）

前端通过 `utils/storage.js` 封装 `wx.setStorageSync`，提供离线友好的本地缓存服务（含账单/分类/设置/健身数据的 CRUD 操作），当前 Schema 版本为 **v2**。

### 数据迁移

`utils/migrations.js` 管理 localStorage 的数据结构版本升级，启动时自动检查并执行增量迁移。

### 卡路里计算

`utils/calorieCalculator.js` 基于 ACSM（美国运动医学学会）MET 代谢当量标准，针对跑步、游泳、骑行、俯卧撑等运动支持**根据速度/个数动态调整 MET 值**，使卡路里估算更精准。

### 数据导入导出

支持 JSON 格式全量导出/导入，方便备份和迁移。

---

## ⚙️ 微信开发者工具配置

- 基础库：`3.14.2`
- 编译选项：ES6+、增强编译、上传代码压缩
- 自定义导航栏：`navigationStyle: "custom"`
- 懒加载：`lazyCodeLoading: "requiredComponents"`
- TabBar 4 个：模块 / 记账 / 健身 / 我的

---

## 📄 License

MIT
