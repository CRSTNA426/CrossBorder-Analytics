# 接入真实店铺 API — 配置指南

本文档说明如何申请各电商平台的 API 权限，将 CrossBorder Analytics 从模拟数据升级为真实店铺看板。

---

## 方式选择

| 方式 | 门槛 | 周期 | 推荐场景 |
|------|------|------|---------|
| **CSV 导入** | 零门槛 | 即时 | 个人卖家、快速上手 |
| **Amazon SP-API** | 企业资质 | 2-4 周 | Amazon 店铺≥3 个月 |
| **TikTok Shop API** | 商家账号 | 1-2 周 | TikTok Shop 活跃卖家 |
| **Shopee Open API** | 卖家账号 | 1-3 天 | Shopee 卖家 |

> 💡 **建议：先用 CSV 导入跑通流程，后续再申请 API 实现自动化。**

---

## Amazon SP-API（Selling Partner API）

### 前置条件

1. **Amazon 专业销售账户**（Professional Seller Account）
   - 月费 $39.99，需要有活跃店铺
   - 个人卖家账户（Individual）不提供 API 权限

2. **注册 Amazon 开发者账号**
   - 访问 [developer.amazon.com](https://developer.amazon.com)
   - 使用与 Seller Central 相同的邮箱注册
   - 完成开发者资料填写

3. **创建 SP-API 应用**
   - 进入 Developer Console → Create App
   - 选择 "SP-API" 类型
   - 填写应用信息（名称、描述、用途说明）
   - 提交审核（通常 1-2 周）

4. **获取 LWA 凭证**
   - App 审核通过后，获取：
     - **LWA Client ID**（即 Access Key）
     - **LWA Client Secret**（即 Secret Key）
   - 授权你的 Seller Central 账号 → 获取 **Refresh Token**

### 费用

- SP-API 本身免费
- 部分高频 API 有调用额度限制（通常 1 req/s）
- 超出额度需要购买

### 配置到 CrossBorder

```bash
# 编辑 .env 文件
DATA_SOURCE=amazon_spapi
AMAZON_ACCESS_KEY=你的LWA_Client_ID
AMAZON_SECRET_KEY=你的LWA_Client_Secret
AMAZON_REFRESH_TOKEN=你的Refresh_Token
AMAZON_MARKETPLACE_ID=ATVPDKIKX0DER  # US 站
```

### 需要实现的 API 端点

开发者实现 `AmazonSpApiAdapter.fetch_daily_data()` 时需要调用：

| SP-API Endpoint | 获取的指标 |
|-----------------|-----------|
| `/sales/v1/orderMetrics` | gmv, orders, avg_order_value |
| `/finances/v0/orders` | ad_spend, cogs, fba_fees, referral_fee |
| `/fba/inventory/v1/summaries` | fulfillable_qty, inbound_qty, inventory_days |
| `/productPricing/v0/competitivePrice` | buy_box_pct |

推荐使用 [python-amazon-sp-api](https://github.com/saleweaver/python-amazon-sp-api) 库。

---

## TikTok Shop Partner API

### 前置条件

1. **TikTok Shop 商家账号**
   - 在 TikTok Shop Seller Center 有活跃店铺
   - 完成商家认证

2. **申请 Partner API 权限**
   - 访问 [partner.tiktokshop.com](https://partner.tiktokshop.com)
   - 注册成为开发者
   - 创建应用 → 选择 "Partner App"
   - 填写应用用途、回调 URL
   - 提交审核（1-2 周）

3. **获取凭证**
   - 审核通过后获取：
     - **Partner Key**（App Key）
     - **Partner Secret**（App Secret）
   - 在 Seller Center 授权你的应用 → 获取 **Shop ID**

### 配置到 CrossBorder

```bash
DATA_SOURCE=tiktok
TIKTOK_PARTNER_KEY=你的Partner_Key
TIKTOK_PARTNER_SECRET=你的Partner_Secret
TIKTOK_SHOP_ID=你的Shop_ID
```

### 需要实现的 API 端点

| API Endpoint | 获取的指标 |
|-------------|-----------|
| `/api/orders/search` | gmv, orders |
| `/api/shop/performance` | shop_score, penalty_points, return_rate |
| `/api/content/metrics` | video_views, live_views, content_gmv |
| `/api/ads/report` | tt_ads_spend, tt_ads_roas, tt_ads_ctr |
| `/api/logistics/shipping` | avg_shipping_time |

API 签名方式：HMAC-SHA256，详见 TikTok 官方文档。

---

## Shopee Open Platform API

### 前置条件

1. **Shopee 卖家中心账号**
   - 在 shopee.cn / shopee.sg 等站点有店铺

2. **注册 Open Platform**
   - 访问 [open.shopee.com](https://open.shopee.com)
   - 使用卖家账号登录
   - 创建应用 → 获取 **Partner ID** 和 **Partner Key**
   - 审核通常 1-3 天

3. **获取 Shop ID**
   - 在 Seller Center → 店铺设置 → 店铺信息 中查看

### 配置到 CrossBorder

```bash
DATA_SOURCE=shopee
SHOPEE_PARTNER_ID=你的Partner_ID
SHOPEE_PARTNER_KEY=你的Partner_Key
SHOPEE_SHOP_ID=你的Shop_ID
```

### 需要实现的 API 端点

| API Endpoint | 获取的指标 |
|-------------|-----------|
| `/api/v2/order/get_order_list` | gmv, orders, cod_orders, cod_rate |
| `/api/v2/shop/get_performance` | shop_rating, nfr_rate, cancel_rate, chat_response_rate |
| `/api/v2/logistics/get_shipping_parameter` | late_shipment_rate, first_attempt_delivery_rate |
| `/api/v2/ads/get_report` | shopee_ads_spend, shopee_ads_roas |
| `/api/v2/marketing/get_flash_sale` | flash_sale_gmv |
| `/api/v2/payment/get_escrow_detail` | net_profit, logistics_cost |

API 签名方式：HMAC-SHA256，使用 Partner Key 对请求参数签名。

---

## 常见问题

**Q: 我只有个人卖家账号，能接 API 吗？**
A: Amazon 需要专业账号。可以先用 CSV 导入你的手工导出数据。TikTok Shop 和 Shopee 门槛较低，个人卖家也能申请。

**Q: API 调用要钱吗？**
A: 三个平台的 API 本身免费，但有调用频率限制（通常 1000 次/小时）。数据量大可能需要购买额度。

**Q: 多久能看到数据？**
A: CSV 导入即时生效。Amazon SP-API 审核 2-4 周。TikTok 1-2 周。Shopee 1-3 天。

**Q: 可以同时接多个平台吗？**
A: 可以。每个平台在 .env 中独立配置。系统支持多平台看板。
