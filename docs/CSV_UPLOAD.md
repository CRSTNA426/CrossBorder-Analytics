# CSV 数据导入指南

无需 API 权限，用 CSV 文件导入你的真实店铺数据。

---

## 快速开始（3 步）

### 1. 创建 CSV 文件

在 `csv_data/` 目录下创建 CSV 文件，命名规则：

```
{平台代码}_{日期}.csv
```

**示例：**
```
csv_data/
├── amazon_2026-06-14.csv
├── amazon_2026-06-15.csv
├── amazon_2026-06-16.csv
├── tiktok_2026-06-16.csv
└── shopee_2026-06-16.csv
```

### 2. CSV 文件格式

两列：`metric_key`（指标标识）和 `value`（数值）

**Amazon 示例** (`amazon_2026-06-16.csv`)：
```csv
metric_key,value
gmv,18450.0
orders,892
acos,28.5
roas,3.51
sessions,8432
conversion_rate,10.6
buy_box_pct,92.3
refund_rate,4.8
avg_order_value,20.68
inventory_days,12.5
fulfillable_qty,3250
inbound_qty,1200
ad_spend,4580.0
cogs,5535.0
fba_fees,2767.5
referral_fee,2767.5
net_profit,2800.0
ad_sales,16070.0
refund_amount,885.6
daily_sales,260.0
```

**TikTok Shop 示例** (`tiktok_2026-06-16.csv`)：
```csv
metric_key,value
gmv,9200.0
orders,380
video_views,12500
live_views,6500
content_gmv,6800.0
shop_gmv,2400.0
affiliate_gmv,1800.0
affiliate_orders,72
tt_ads_spend,2100.0
tt_ads_roas,3.24
tt_ads_ctr,2.1
shop_score,4.6
penalty_points,1
avg_shipping_time,38.5
return_rate,3.2
refund_rate,4.5
net_profit,1850.0
cogs,2070.0
```

**Shopee 示例** (`shopee_2026-06-16.csv`)：
```csv
metric_key,value
gmv,7500.0
orders,350
cod_orders,160
cod_rate,45.7
chat_response_rate,88.5
chat_response_time,8.2
shop_rating,4.5
nfr_rate,4.2
cancel_rate,5.8
late_shipment_rate,4.1
shopee_ads_spend,1200.0
shopee_ads_roas,6.25
flash_sale_gmv,1500.0
voucher_usage_rate,22.5
logistics_cost,1050.0
first_attempt_delivery_rate,72.3
net_profit,2200.0
return_rate,3.8
```

### 3. 配置并导入

```bash
# 1. 编辑 .env
DATA_SOURCE=csv
CSV_DATA_PATH=./csv_data/

# 2. 运行同步
python backend/sync.py --date 2026-06-16
```

---

## 如何从店铺后台导出数据

### Amazon Seller Central

1. 登录 Seller Central → **数据报告** → **业务报告**
2. 选择日期范围 → 下载 CSV
3. 复制对应列的值到 CrossBorder CSV 模板

**字段对应关系：**
| Amazon 报告字段 | metric_key |
|----------------|-----------|
| Ordered product sales | gmv |
| Total order items | orders |
| Average sales per order item | avg_order_value |
| Unit session percentage | conversion_rate |

> ⚠️ Amazon 不直接提供 `acos`、`cogs`、`fba_fees` 在同一个报表中。需要从**广告报告**和**付款报告**分别导出后合并。

### TikTok Shop Seller Center

1. 登录 Seller Center → **数据** → **经营分析**
2. 选择日期 → 导出数据
3. 手动计算 `content_gmv = 短视频GMV + 直播GMV + 达人GMV`

### Shopee Seller Center

1. 登录 Seller Center → **数据中心** → **销售概况**
2. 选择日期 → 下载报表
3. COD、聊聊回复率 在 **客服表现** 页面单独导出

---

## 批量导入

如果你有历史数据需要批量导入：

```bash
# 导入最近 30 天（需将所有 CSV 放好）
python backend/sync.py --all
```

---

## CSV vs API 对比

| 特性 | CSV 导入 | 平台 API |
|------|---------|----------|
| 门槛 | 零 | 需企业资质 + 审核 |
| 速度 | 手动导出 | 自动同步 |
| 数据粒度 | 取决于导出报表 | API 提供的所有字段 |
| 适合 | 个人卖家 / 快速验证 | 专业卖家 / 长期运营 |
| 推荐 | 先从这里开始！ | 跑通后升级 |
