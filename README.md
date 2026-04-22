# 工作日誌 Work Journal

以 **Flask + SQLite** 為後端、**Vue 3 + FullCalendar + Element Plus** 為前端的網頁版工作日誌系統。員工可於週曆上拖拉時段、填寫專案或個人工作事項；管理者可建立專案、設定時薪與預算；系統自動計算人力成本並產生報表。

---

## 功能總覽

- **週曆拖拉填寫**：FullCalendar 週視圖，拖拉選取時段即建立工作記錄；可拖拉拉長/縮短或移動時段
- **專案 / 個人事項二擇一**：每筆記錄歸屬於一個「專案」或「個人類別」（例：內部會議、教育訓練）
- **三種角色**：
  - `employee` 員工：CRUD 自己的記錄（預設只能改過去 7 天內）
  - `manager` 主管：員工功能 + 查看同部門成員的週曆與月度統計
  - `admin` 管理者：維護部門、員工、專案、類別；全公司報表
- **雙軌成本計算**：
  - 員工時薪 × 工時 → 人力成本
  - 對照專案預算 → 預算使用率
- **報表**：專案預算 vs 實際成本（bar）、個人工時分布（pie）、部門月度工時與成本（bar + table）

## 技術棧

| 層 | 套件 |
| --- | --- |
| 後端 | Flask 3、Flask-SQLAlchemy、Flask-JWT-Extended、Flask-CORS、bcrypt |
| 資料庫 | SQLite（開發；可切 PostgreSQL） |
| 前端 | Vue 3、Vite、Pinia、Vue Router、Element Plus、axios |
| 日曆 | FullCalendar（timeGrid + interaction plugin） |
| 圖表 | ECharts / vue-echarts |

## 專案結構

```
journal/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # create_app 工廠
│   │   ├── config.py
│   │   ├── extensions.py        # db, jwt, migrate, cors
│   │   ├── models.py            # Department / User / Project / ProjectMember / PersonalCategory / TimeEntry
│   │   ├── permissions.py       # role_required 裝飾器
│   │   ├── seed.py              # 初始化範例資料
│   │   └── routes/
│   │       ├── auth.py          # /api/auth/*
│   │       ├── users.py         # /api/users/*
│   │       ├── departments.py   # /api/departments/*
│   │       ├── projects.py      # /api/projects/*
│   │       ├── categories.py    # /api/categories/*
│   │       ├── entries.py       # /api/entries/*  ← 核心
│   │       └── reports.py       # /api/reports/*
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
└── frontend/
    ├── src/
    │   ├── api/                 # axios + 各 endpoint 封裝
    │   ├── stores/auth.js       # Pinia auth store
    │   ├── router/index.js      # 角色守衛
    │   ├── layouts/MainLayout.vue
    │   ├── components/EntryDialog.vue
    │   └── views/
    │       ├── LoginView.vue
    │       ├── CalendarView.vue        # 我的週曆
    │       ├── TeamCalendarView.vue    # 部門週曆 (manager/admin)
    │       ├── ReportsView.vue         # 報表
    │       ├── ProjectsView.vue        # 專案管理 (admin)
    │       ├── UsersView.vue           # 員工管理 (admin)
    │       ├── DepartmentsView.vue     # 部門管理 (admin)
    │       └── CategoriesView.vue      # 個人類別 (admin)
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## 安裝與啟動

### 前置需求

- Python 3.10+（測試版本：3.11）
- Node.js 18+（測試版本：22）

### 1. 後端

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env      # 必要時修改 SECRET_KEY / JWT_SECRET_KEY

python -m app.seed          # 建立 SQLite 資料庫並填入範例資料
python run.py               # 啟動於 http://localhost:5000
```

### 2. 前端

```powershell
cd frontend
npm install
npm run dev                 # 啟動於 http://localhost:5173
```

開啟瀏覽器進入 <http://localhost:5173>。Vite dev server 會將 `/api/*` 代理到 Flask。

### 預設帳號（由 seed 建立）

| 帳號 | 密碼 | 角色 | 說明 |
| --- | --- | --- | --- |
| `admin` | `admin123` | 管理者 | 可管理所有資料與報表 |
| `manager1` | `manager123` | 主管 | 工程部主管，可看同部門週曆 |
| `emp1` | `emp123` | 員工 | 工程部 |
| `emp2` | `emp123` | 員工 | 工程部 |
| `emp3` | `emp123` | 員工 | 設計部 |

## 使用流程

1. 以 `admin` 登入 → 到「員工管理」設定員工時薪、到「專案管理」新增專案與預算並指派成員
2. 員工登入後於「我的週曆」上**拖拉時段**即可建立工作記錄；選擇「專案」或「個人事項」
3. 主管到「部門週曆」檢視下屬工時分布
4. 任何人都可到「報表」看自己的月度工時；主管/管理者可看部門/專案成本

## 核心資料模型

```
Department (id, name, manager_id)
User       (id, username, full_name, role, department_id, hourly_rate, is_active)
Project    (id, code, name, budget, status, color, dates)
ProjectMember (project_id, user_id)
PersonalCategory (id, name, color)
TimeEntry  (id, user_id, project_id?, category_id?, title, start_time, end_time)
            # 限制：project_id XOR category_id 必須二擇一
            # 限制：end_time > start_time
            # 同一 user_id 不允許時段重疊（API 層檢查）
```

## 主要 API

| Method | Path | 說明 | 權限 |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | 登入換取 JWT | 公開 |
| GET | `/api/auth/me` | 取得目前使用者 | 登入 |
| GET/POST/PATCH/DELETE | `/api/users` | 員工 CRUD | admin（GET manager 可看同部門） |
| GET/POST/PATCH/DELETE | `/api/departments` | 部門 CRUD | admin（GET 所有登入者） |
| GET/POST/PATCH/DELETE | `/api/projects` | 專案 CRUD；GET `?mine=1` 可篩 | admin 寫，其他唯讀 |
| GET/POST/PATCH/DELETE | `/api/categories` | 個人類別 CRUD | admin 寫，其他唯讀 |
| GET | `/api/entries?from=&to=&user_id=&scope=team` | 時段查詢（角色過濾） | 登入 |
| POST/PATCH/DELETE | `/api/entries/:id` | 時段 CRUD（重疊檢查） | 自己 / admin |
| GET | `/api/reports/project-cost` | 專案成本 vs 預算 | admin / manager |
| GET | `/api/reports/user-hours?user_id=&month=YYYY-MM` | 個人月結 | 登入（本人或上級） |
| GET | `/api/reports/department-summary?dept_id=&month=` | 部門月結 | admin / manager |

## 預設規則（可於 `backend/app/routes/entries.py` 調整）

- `EDIT_PAST_DAYS = 7`：員工僅能編輯最近 7 天內的記錄，管理者可編輯全部
- 不允許時段重疊（同一人）
- 起訖時間以後端本地時區儲存；前端送出 `YYYY-MM-DDTHH:mm:ss`

## 生產部署提醒

- 修改 `.env` 中的 `SECRET_KEY`、`JWT_SECRET_KEY`
- 將 `DATABASE_URL` 切換為 PostgreSQL 並執行 `flask db migrate`
- 前端執行 `npm run build` 後將 `dist/` 交由 Nginx 靜態服務，`/api/*` 反向代理到 Flask（Gunicorn/uwsgi）
