# CrossBorder Analytics

**跨境电商多平台运营看板系统** — 一站式监控 Amazon / TikTok Shop / Shopee 核心运营指标。

---

## 在线演示

启动后访问 `http://localhost:8000`，选择平台即可查看看板：

- 🛒 **Amazon** — GMV, 订单, ACoS, 库存预警, FBA 利润
- 🎵 **TikTok Shop** — 短视频/直播 GMV, 达人带货, 店铺评分
- 🛍️ **Shopee** — COD 占比, 聊聊回复率, NFR, 闪购

---

## 核心功能

- ✅ **多平台支持** — Amazon / TikTok Shop / Shopee，一键切换
- ✅ **自定义指标** — 公式编辑器（支持四则运算），实时计算
- ✅ **库存预警** — 可售天数自动标红/黄/绿
- ✅ **趋势图表** — ECharts 折线图，30 天趋势一览
- ✅ **数据接入** — Mock 模拟 / CSV 导入 / 平台 API（预留）
- ✅ **公式引擎** — 循环依赖检测、除零保护、语法验证
- ✅ **指标管理** — 软删除 + 恢复 + 彻底删除

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ / FastAPI / SQLAlchemy / SQLite |
| 前端 | 原生 JS / ECharts 5.x / 无框架 |
| 公式引擎 | asteval + 自定义词法分析 |
| 数据适配 | 可插拔 Adapter 架构 |

---

## 快速开始

```bash
git clone https://github.com/CRSTNA426/CrossBorder-Analytics.git
cd CrossBorder-Analytics
pip install -r requirements.txt
```

### 方式 A：干净启动（用于接入真实店铺数据）

```bash
python run.py --init-only
# 访问 http://localhost:8000
# 看板为空，点击「📤 导入数据」上传 CSV 即可开始
```

首次启动后所有数据结构就绪（3 平台 + 56 指标），但**不含任何业务数据**。适合从零开始导入自己的店铺 CSV。

### 方式 B：演示模式（带 30 天模拟数据）

```bash
python run.py --seed
# 访问 http://localhost:8000
# 可直接查看 Amazon / TikTok / Shopee 完整演示数据
```

生成 30 天逼真模拟数据（2026-05-18 → 2026-06-16），包含业务关联逻辑（周末上浮、广告异常、库存预警、违规扣分、闪购峰值等）。适合截图、演示、探索功能。

> 💡 不带参数直接运行 `python run.py` 会智能判断：数据库不存在则自动走方式 A，存在则直接启动。

---

## 接入真实店铺数据

### 方式 1：CSV 导入（推荐，零门槛）

无需 API 权限。从店铺后台导出数据为 CSV，一键导入。

👉 详见 **[docs/CSV_UPLOAD.md](docs/CSV_UPLOAD.md)**

```bash
# 1. 编辑 .env
cp .env.example .env
# 修改: DATA_SOURCE=csv

# 2. 准备 CSV 文件
mkdir csv_data
# 放入 amazon_2026-06-16.csv 等文件

# 3. 同步数据
python backend/sync.py --date 2026-06-16
```

### 方式 2：Amazon SP-API

需要 Amazon 专业销售账户 + 开发者账号。审核周期约 2-4 周。

👉 详见 **[docs/API_SETUP.md#amazon](docs/API_SETUP.md)**

### 方式 3：TikTok Shop Partner API

需要 TikTok Shop 商家账号。审核周期约 1-2 周。

👉 详见 **[docs/API_SETUP.md#tiktok](docs/API_SETUP.md)**

### 方式 4：Shopee Open Platform API

需要 Shopee 卖家账号。审核周期约 1-3 天（最快）。

👉 详见 **[docs/API_SETUP.md#shopee](docs/API_SETUP.md)**

---

## 项目结构

```
CrossBorder-Analytics/
├── run.py                          # 一键启动（seed + server）
├── requirements.txt
├── .env.example                    # API 配置模板
├── README.md
├── backend/
│   ├── main.py                     # FastAPI 入口 + 静态文件
│   ├── database.py                 # SQLite 连接
│   ├── models.py                   # 7 张表 ORM 模型
│   ├── schemas.py                  # Pydantic 请求/响应
│   ├── seed.py                     # 初始化数据（3 平台 × 30 天）
│   ├── formula_engine.py           # 公式解析 + 循环检测
│   ├── sync.py                     # 数据同步脚本
│   ├── adapters/
│   │   └── __init__.py             # 数据源适配层
│   └── routers/
│       ├── platforms.py            # 平台 API
│       ├── metrics.py              # 指标 CRUD + 软删除
│       ├── dashboards.py           # 看板 + 组件
│       └── data.py                 # 看板数据 + 趋势
├── frontend/
│   ├── index.html                  # 主页面
│   ├── css/main.css                # 样式（暗色主题）
│   └── js/
│       ├── api.js                  # API 封装
│       ├── app.js                  # 主控制器
│       ├── chart-renderer.js       # ECharts 图表
│       └── formula-editor.js       # 公式编辑器
├── docs/
│   ├── API_SETUP.md                # API 申请指南
│   └── CSV_UPLOAD.md               # CSV 导入指南
└── data/
    └── crossborder.db              # SQLite 数据库（自动生成）
```

---

## API 文档

启动服务器后访问 `http://localhost:8000/docs` 查看 Swagger UI。

### 主要端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/platforms` | 获取所有平台 |
| GET | `/api/platforms/{id}/metrics` | 获取平台所有指标 |
| POST | `/api/metrics` | 创建自定义指标 |
| POST | `/api/metrics/validate-formula` | 验证公式 |
| DELETE | `/api/metrics/{id}` | 软删除自定义指标 |
| POST | `/api/metrics/{id}/restore` | 恢复已删除指标 |
| POST | `/api/dashboards` | 创建看板 |
| GET | `/api/data?dashboard_id=1&date=2026-06-16` | 获取看板数据 |
| GET | `/api/data/trend?dashboard_id=1&metric_keys=gmv,acos&days=30` | 获取趋势 |

---

## 数据同步

```bash
# 单日同步
python backend/sync.py --date 2026-06-16

# 指定平台
python backend/sync.py --date 2026-06-16 --platform amazon

# 批量同步 30 天
python backend/sync.py --all

# 使用 cron 定时同步（每天凌晨 1 点）
# 0 1 * * * cd /path/to/project && python backend/sync.py
```

---

## 待实现（Contributions Welcome）

- [ ] Amazon SP-API Adapter 真实实现
- [ ] TikTok Shop Partner API Adapter 真实实现
- [ ] Shopee Open Platform API Adapter 真实实现
- [ ] 用户认证系统（多用户）
- [ ] 数据导出（PDF / Excel）
- [ ] 告警通知（钉钉 / 飞书 / 邮件）
- [ ] 移动端 PWA 适配

---

## License

MIT
