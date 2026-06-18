"""
Seed script: populates initial platforms, built-in metrics,
and 30 days of simulated daily_data for each platform.

Platform-specific logic:
  - Amazon: marketplace ads, FBA, inventory
  - TikTok Shop: content commerce (short videos, live, affiliate)
  - Shopee: Southeast Asia (COD, chat, flash sales)
"""
import random
import math
from datetime import date, timedelta
from database import SessionLocal, engine, Base
from models import Platform, Metric, User, DailyData


# ═══════════════════════════════════════════════════════════════
#  METRIC DEFINITIONS
# ═══════════════════════════════════════════════════════════════

AMAZON_METRICS = [
    # (key, name, category, data_type, unit, is_default, widget_type, formula_or_none)
    ("gmv",             "订单销售额",   "overview",    "currency",   "USD", True,  "kpi",   None),
    ("orders",          "订单量",       "overview",    "number",     "单",  True,  "kpi",   None),
    ("acos",            "广告销售成本比","traffic",     "percentage", "%",   True,  "kpi",   "ad_spend / ad_sales * 100"),
    ("roas",            "广告回报率",   "traffic",     "percentage", "倍",  False, "kpi",   "ad_sales / ad_spend"),
    ("sessions",        "访问量",       "traffic",     "number",     "次",  False, "line",  None),
    ("conversion_rate", "转化率",       "conversion",  "percentage", "%",   False, "kpi",   "orders / sessions * 100"),
    ("buy_box_pct",     "购物车占比",   "conversion",  "percentage", "%",   False, "kpi",   None),
    ("refund_rate",     "退款率",       "order",       "percentage", "%",   True,  "kpi",   "refund_amount / gmv * 100"),
    ("avg_order_value", "平均客单价",   "order",       "currency",   "USD", False, "kpi",   "gmv / orders"),
    ("inventory_days",  "可售天数",     "inventory",   "number",     "天",  True,  "kpi",   None),
    ("fulfillable_qty", "可售库存",     "inventory",   "number",     "件",  False, "kpi",   None),
    ("inbound_qty",     "在途库存",     "inventory",   "number",     "件",  False, "kpi",   None),
    ("ad_spend",        "广告花费",     "profit",      "currency",   "USD", False, "kpi",   None),
    ("cogs",            "商品成本",     "profit",      "currency",   "USD", False, "kpi",   None),
    ("fba_fees",        "FBA配送费",   "profit",      "currency",   "USD", False, "kpi",   None),
    ("referral_fee",    "平台佣金",     "profit",      "currency",   "USD", False, "kpi",   "gmv * 0.15"),
    ("net_profit",      "净利润",       "profit",      "currency",   "USD", True,  "kpi",   "gmv*(1-refund_rate/100) - cogs - fba_fees - referral_fee - ad_spend"),
    ("ad_sales",        "广告销售额",   "traffic",      "currency",   "USD", False, "kpi",   None),
    ("refund_amount",   "退款金额",     "order",        "currency",   "USD", False, "kpi",   None),
    ("daily_sales",     "日均销量",     "inventory",    "number",     "件",  False, "kpi",   None),
]


TIKTOK_METRICS = [
    # Overview
    ("gmv",             "订单销售额",     "overview",    "currency",   "USD", True,  "kpi",   None),
    ("orders",          "订单量",         "overview",    "number",     "单",  True,  "kpi",   None),
    # Content (core for TikTok)
    ("video_views",     "短视频播放量",   "content",     "number",     "次",  True,  "line",  None),
    ("live_views",      "直播间观看人次", "content",     "number",     "次",  True,  "line",  None),
    ("content_gmv",     "内容带货GMV",    "content",     "currency",   "USD", True,  "kpi",   None),
    ("shop_gmv",        "店铺自然GMV",    "content",     "currency",   "USD", False, "kpi",   None),
    ("affiliate_gmv",   "达人带货GMV",    "content",     "currency",   "USD", False, "kpi",   None),
    ("affiliate_orders","达人带货订单",   "content",     "number",     "单",  False, "kpi",   None),
    # Traffic
    ("tt_ads_spend",    "TikTok Ads花费", "traffic",     "currency",   "USD", True,  "kpi",   None),
    ("tt_ads_roas",     "TikTok Ads ROAS","traffic",     "percentage", "倍",  False, "kpi",   "content_gmv / tt_ads_spend"),
    ("tt_ads_ctr",      "广告点击率",     "traffic",     "percentage", "%",   False, "kpi",   None),
    # Shop health
    ("shop_score",      "店铺评分",       "conversion",  "number",     "分",  True,  "kpi",   None),
    ("penalty_points",  "违规扣分",       "order",       "number",     "分",  False, "kpi",   None),
    # Logistics
    ("avg_shipping_time","平均发货时效",  "inventory",   "number",     "小时", False, "kpi",   None),
    # Orders
    ("return_rate",     "退货率",         "order",       "percentage", "%",   True,  "kpi",   None),
    ("refund_rate",     "退款率",         "order",       "percentage", "%",   True,  "kpi",   None),
    # Profit
    ("net_profit",      "净利润",         "profit",      "currency",   "USD", True,  "kpi",   None),
    # (18th row: placeholder for future expansion / helper)
    ("cogs",            "商品成本",       "profit",      "currency",   "USD", False, "kpi",   None),
]


SHOPEE_METRICS = [
    # Overview
    ("gmv",                     "订单销售额",       "overview",    "currency",   "USD", True,  "kpi",   None),
    ("orders",                  "订单量",           "overview",    "number",     "单",  True,  "kpi",   None),
    # COD (core for Southeast Asia)
    ("cod_orders",              "货到付款订单",     "order",       "number",     "单",  True,  "kpi",   None),
    ("cod_rate",                "COD占比",          "order",       "percentage", "%",   False, "kpi",   "cod_orders / orders * 100"),
    # Chat (Shopee core)
    ("chat_response_rate",      "聊聊回复率",       "conversion",  "percentage", "%",   True,  "kpi",   None),
    ("chat_response_time",      "平均回复时长",     "conversion",  "number",     "分钟", False, "kpi",   None),
    # Shop health
    ("shop_rating",             "店铺评分",         "conversion",  "number",     "分",  True,  "kpi",   None),
    ("nfr_rate",                "不履约率",         "order",       "percentage", "%",   True,  "kpi",   None),
    ("cancel_rate",             "取消率",           "order",       "percentage", "%",   False, "kpi",   None),
    ("late_shipment_rate",      "迟发货率",         "inventory",   "percentage", "%",   False, "kpi",   None),
    # Ads
    ("shopee_ads_spend",        "Shopee Ads花费",   "traffic",     "currency",   "USD", True,  "kpi",   None),
    ("shopee_ads_roas",         "Shopee Ads ROAS",  "traffic",     "percentage", "倍",  False, "kpi",   "gmv / shopee_ads_spend"),
    # Activities
    ("flash_sale_gmv",          "闪购GMV",          "content",     "currency",   "USD", False, "kpi",   None),
    ("voucher_usage_rate",      "优惠券使用率",     "content",     "percentage", "%",   False, "kpi",   None),
    # Logistics
    ("logistics_cost",          "物流成本",         "profit",      "currency",   "USD", False, "kpi",   None),
    ("first_attempt_delivery_rate","一次派送成功率", "inventory",   "percentage", "%",   False, "kpi",   None),
    # Profit
    ("net_profit",              "净利润",           "profit",      "currency",   "USD", True,  "kpi",   None),
    # Return/refund
    ("return_rate",             "退货率",           "order",       "percentage", "%",   True,  "kpi",   None),
]


PLATFORM_METRIC_MAP = {
    "amazon": AMAZON_METRICS,
    "tiktok": TIKTOK_METRICS,
    "shopee": SHOPEE_METRICS,
}


# ═══════════════════════════════════════════════════════════════
#  HELPER
# ═══════════════════════════════════════════════════════════════

def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


# ═══════════════════════════════════════════════════════════════
#  AMAZON DATA GENERATOR (unchanged, kept for completeness)
# ═══════════════════════════════════════════════════════════════

def generate_amazon_daily_data(platform_id: int, start: date, end: date):
    """Generate realistic Amazon daily data for 30 days."""
    records = []
    current = start
    while current <= end:
        is_weekend = _is_weekend(current)
        weekend_mult = 1.2 if is_weekend else 1.0

        sessions = int(random.randint(4000, 12000) * weekend_mult)
        orders = int(random.randint(800, 1500) * weekend_mult)
        gmv = round(random.uniform(15000, 25000) * weekend_mult, 2)
        conversion_rate = round(orders / sessions * 100, 2)
        refund_rate = round(random.uniform(2, 8), 2)
        refund_amount = round(gmv * refund_rate / 100, 2)
        avg_order_value = round(gmv / orders, 2)

        ad_spend = round(random.uniform(3000, 8000), 2)
        ad_sales = round(random.uniform(10000, 20000) * weekend_mult, 2)
        acos = round(ad_spend / ad_sales * 100, 2)
        roas = round(ad_sales / ad_spend, 2)

        if random.random() < 0.06:
            acos = round(random.uniform(38, 42), 2)
            ad_spend = round(ad_spend * 1.3, 2)

        buy_box_pct = round(random.uniform(85, 99), 2)
        cogs = round(gmv * random.uniform(0.25, 0.40), 2)
        fba_fees = round(gmv * random.uniform(0.10, 0.20), 2)
        referral_fee = round(gmv * 0.15, 2)

        net_profit = round(
            gmv * (1 - refund_rate / 100) - cogs - fba_fees - referral_fee - ad_spend, 2
        )

        daily_sales = round(orders * random.uniform(0.8, 1.2), 1)
        fulfillable_qty = int(random.randint(1000, 8000))
        inventory_days = round(fulfillable_qty / daily_sales, 1) if daily_sales > 0 else 0
        inbound_qty = int(random.randint(500, 3000))

        data_points = {
            "gmv": gmv, "orders": orders, "acos": acos, "roas": roas,
            "sessions": sessions, "conversion_rate": conversion_rate,
            "buy_box_pct": buy_box_pct, "refund_rate": refund_rate,
            "avg_order_value": avg_order_value, "inventory_days": inventory_days,
            "fulfillable_qty": fulfillable_qty, "inbound_qty": inbound_qty,
            "ad_spend": ad_spend, "cogs": cogs, "fba_fees": fba_fees,
            "referral_fee": referral_fee, "net_profit": net_profit,
            "ad_sales": ad_sales, "refund_amount": refund_amount,
            "daily_sales": daily_sales,
        }

        for key, value in data_points.items():
            records.append(DailyData(
                platform_id=platform_id, date=current,
                metric_key=key, value=value,
            ))
        current += timedelta(days=1)
    return records


# ═══════════════════════════════════════════════════════════════
#  TIKTOK SHOP DATA GENERATOR (content e-commerce)
# ═══════════════════════════════════════════════════════════════

def generate_tiktok_daily_data(platform_id: int, start: date, end: date):
    """
    TikTok Shop logic:
      - Content GMV = video_gmv (30%) + live_gmv (50%) + affiliate_gmv (20%)
      - shop_gmv = organic store traffic
      - gmv = content_gmv + shop_gmv
      - Penalty when shop_score < 4.5
      - Shipping > 48h triggers penalty points
    """
    records = []
    current = start
    while current <= end:
        is_weekend = _is_weekend(current)
        wm = 1.25 if is_weekend else 1.0   # TikTok traffic surges on weekends

        # ── Content metrics ──────────────────────────────────
        video_views = int(random.randint(5000, 15000) * wm)
        live_views = int(random.randint(2000, 8000) * wm)

        # Content-commerce GMV breakdown
        video_gmv = round(random.uniform(1500, 5000) * wm, 2)
        live_gmv = round(random.uniform(3000, 10000) * wm, 2)
        affiliate_gmv = round(random.uniform(1000, 4000) * wm, 2)
        content_gmv = round(video_gmv + live_gmv + affiliate_gmv, 2)

        shop_gmv = round(random.uniform(2000, 6000) * wm, 2)
        gmv = round(content_gmv + shop_gmv, 2)  # total platform GMV

        orders = int(gmv / random.uniform(18, 35))
        affiliate_orders = int(affiliate_gmv / random.uniform(18, 30))

        # ── Ads ───────────────────────────────────────────────
        tt_ads_spend = round(random.uniform(800, 3500) * wm, 2)
        tt_ads_roas = round(content_gmv / tt_ads_spend, 2) if tt_ads_spend > 0 else 0
        tt_ads_ctr = round(random.uniform(0.8, 3.5), 2)

        # ── Shop health ───────────────────────────────────────
        shop_score = round(random.uniform(4.2, 4.9), 2)
        # Low score → more penalty points
        if shop_score < 4.5:
            penalty_points = int(random.randint(2, 8))
        else:
            penalty_points = int(random.randint(0, 2))

        # ── Logistics ─────────────────────────────────────────
        # Shipping time: 24-72h.  Platform requires ≤48h
        avg_shipping_time = round(random.uniform(24, 72), 1)
        if avg_shipping_time > 48:
            penalty_points += int(random.randint(1, 3))

        # ── Order quality ─────────────────────────────────────
        return_rate = round(random.uniform(2, 7), 2)
        refund_rate = round(random.uniform(2, 8), 2)
        # Correlation: refund_rate tends higher when shop_score is low
        if shop_score < 4.5:
            refund_rate = round(refund_rate * random.uniform(1.1, 1.6), 2)

        # ── Profit ────────────────────────────────────────────
        cogs = round(gmv * random.uniform(0.22, 0.35), 2)
        logistics = round(gmv * 0.08, 2)
        net_profit = round(
            gmv * (1 - refund_rate / 100) - cogs - logistics - tt_ads_spend, 2
        )

        data_points = {
            "gmv": gmv, "orders": orders,
            "video_views": video_views, "live_views": live_views,
            "content_gmv": content_gmv, "shop_gmv": shop_gmv,
            "affiliate_gmv": affiliate_gmv, "affiliate_orders": affiliate_orders,
            "tt_ads_spend": tt_ads_spend, "tt_ads_roas": tt_ads_roas,
            "tt_ads_ctr": tt_ads_ctr,
            "shop_score": shop_score, "penalty_points": penalty_points,
            "avg_shipping_time": avg_shipping_time,
            "return_rate": return_rate, "refund_rate": refund_rate,
            "net_profit": net_profit,
            "cogs": cogs,
        }

        for key, value in data_points.items():
            records.append(DailyData(
                platform_id=platform_id, date=current,
                metric_key=key, value=value,
            ))
        current += timedelta(days=1)
    return records


# ═══════════════════════════════════════════════════════════════
#  SHOPEE DATA GENERATOR (Southeast Asia e-commerce)
# ═══════════════════════════════════════════════════════════════

def generate_shopee_daily_data(platform_id: int, start: date, end: date):
    """
    Shopee logic:
      - COD orders: 30-60% of total (varies by market)
      - Chat response rate < 80% → shop penalty
      - NFR (Non-Fulfillment Rate) > 5% → warning
      - Late shipment > 5% → penalty
      - Flash sale: 1-2 peak days per week (2-3x normal)
      - First-attempt delivery: 60-85% (address issues in SEA)
    """
    records = []
    current = start
    while current <= end:
        is_weekend = _is_weekend(current)
        wm = 1.15 if is_weekend else 1.0
        day_of_week = current.weekday()  # 0=Mon … 6=Sun

        # ── Core ──────────────────────────────────────────────
        gmv = round(random.uniform(6000, 16000) * wm, 2)
        orders = int(gmv / random.uniform(10, 25))
        return_rate = round(random.uniform(2, 7), 2)
        refund_rate = round(random.uniform(2, 8), 2)

        # ── COD (cash on delivery) ────────────────────────────
        # COD share varies: MY/PH ~40-60%, SG ~15-30%, ID ~30-50%
        cod_pct = random.uniform(0.30, 0.60)
        cod_orders = int(orders * cod_pct)
        cod_rate = round(cod_pct * 100, 1)

        # ── Chat (Shopee "聊聊") ──────────────────────────────
        chat_response_rate = round(random.uniform(70, 95), 1)
        chat_response_time = round(random.uniform(3, 30), 1)  # minutes
        # Low response → shop penalty (correlation)
        shop_rating = round(random.uniform(4.0, 4.8), 2)
        if chat_response_rate < 80:
            shop_rating = round(min(shop_rating, random.uniform(4.0, 4.4)), 2)

        # ── NFR / Cancel ──────────────────────────────────────
        cancel_rate = round(random.uniform(2, 10), 2)
        nfr_rate = round(cancel_rate + refund_rate * random.uniform(0.3, 0.7), 2)
        late_shipment_rate = round(random.uniform(3, 12), 2)

        # ── Ads ───────────────────────────────────────────────
        shopee_ads_spend = round(random.uniform(500, 2500) * wm, 2)
        shopee_ads_roas = round(gmv / shopee_ads_spend, 2) if shopee_ads_spend > 0 else 0

        # ── Flash sale ────────────────────────────────────────
        # 1-2 peak days per week (Wed/Fri are common flash sale days)
        is_flash_day = (day_of_week in (2, 4)) and (random.random() < 0.5)
        if is_flash_day:
            flash_sale_gmv = round(gmv * random.uniform(0.25, 0.45), 2)
        else:
            flash_sale_gmv = round(gmv * random.uniform(0.05, 0.15), 2)

        voucher_usage_rate = round(random.uniform(8, 30), 1)

        # ── Logistics ─────────────────────────────────────────
        logistics_cost = round(gmv * random.uniform(0.08, 0.18), 2)
        first_attempt_delivery_rate = round(random.uniform(60, 85), 1)

        # ── Profit ────────────────────────────────────────────
        cogs = round(gmv * 0.30, 2)
        commission = round(gmv * random.uniform(0.05, 0.06), 2)
        net_profit = round(
            gmv * (1 - refund_rate / 100) - cogs - logistics_cost - shopee_ads_spend - commission, 2
        )

        data_points = {
            "gmv": gmv, "orders": orders,
            "cod_orders": cod_orders, "cod_rate": cod_rate,
            "chat_response_rate": chat_response_rate,
            "chat_response_time": chat_response_time,
            "shop_rating": shop_rating, "nfr_rate": nfr_rate,
            "cancel_rate": cancel_rate,
            "late_shipment_rate": late_shipment_rate,
            "shopee_ads_spend": shopee_ads_spend,
            "shopee_ads_roas": shopee_ads_roas,
            "flash_sale_gmv": flash_sale_gmv,
            "voucher_usage_rate": voucher_usage_rate,
            "logistics_cost": logistics_cost,
            "first_attempt_delivery_rate": first_attempt_delivery_rate,
            "net_profit": net_profit,
            "return_rate": return_rate,
        }

        for key, value in data_points.items():
            records.append(DailyData(
                platform_id=platform_id, date=current,
                metric_key=key, value=value,
            ))
        current += timedelta(days=1)
    return records


# ═══════════════════════════════════════════════════════════════
#  SCHEMA INIT (empty structure, no business data)
# ═══════════════════════════════════════════════════════════════

def init_schema():
    """
    Create empty database structure:
      - Drop & recreate all tables
      - Insert 3 platforms (Amazon / TikTok Shop / Shopee)
      - Insert 56 built-in metric definitions
      - Insert default admin user
      - NO daily_data (business data) is generated
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # 1. Create default user
        user = User(username="admin")
        db.add(user)
        db.flush()

        # 2. Create platforms
        platforms_data = [
            ("Amazon", "amazon", "🛒", "Amazon marketplace analytics"),
            ("TikTok Shop", "tiktok", "🎵", "TikTok Shop analytics"),
            ("Shopee", "shopee", "🛍️", "Shopee marketplace analytics"),
        ]
        platform_map = {}
        for name, code, icon, desc in platforms_data:
            p = Platform(name=name, code=code, icon=icon, description=desc)
            db.add(p)
            db.flush()
            platform_map[code] = p

        # 3. Create built-in metrics for each platform
        total_metrics = 0
        for code, metric_list in PLATFORM_METRIC_MAP.items():
            pid = platform_map[code].id
            for (key, name, cat, dtype, unit, is_def, wtype, formula) in metric_list:
                m = Metric(
                    platform_id=pid,
                    name=name,
                    key=key,
                    category=cat,
                    data_type=dtype,
                    unit=unit,
                    is_builtin=True,
                    is_default=is_def,
                    default_widget_type=wtype,
                    formula=formula,
                    created_by=None,
                )
                db.add(m)
                total_metrics += 1

        db.commit()

        print(f"[Init] Schema created successfully")
        print(f"   Platforms: {len(platform_map)}")
        print(f"   Built-in metrics: {total_metrics}")
        print(f"   Daily data: 0 rows (no business data)")
        print(f"   Default user: admin (id=1)")
        print(f"   Run 'python run.py --seed' to generate 30 days of demo data")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Schema init failed: {e}")
        raise
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
#  MOCK DATA SEED (generates 30 days of demo data)
# ═══════════════════════════════════════════════════════════════

def seed_mock_data():
    """
    Generate 30 days of simulated daily_data (2026-05-18 → 2026-06-16).
    Calls init_schema() first if tables don't exist.
    """
    # Ensure schema exists
    from sqlalchemy import inspect
    insp = inspect(engine)
    if not insp.has_table("platforms"):
        print("[Seed] Tables not found, running init_schema() first...")
        init_schema()

    db = SessionLocal()

    try:
        # Get platform IDs
        platforms = db.query(Platform).all()
        platform_map = {p.code: p.id for p in platforms}

        start_date = date(2026, 5, 18)
        end_date = date(2026, 6, 16)

        # Amazon
        amazon_id = platform_map["amazon"]
        amazon_records = generate_amazon_daily_data(amazon_id, start_date, end_date)
        db.add_all(amazon_records)

        # TikTok Shop
        tiktok_id = platform_map["tiktok"]
        tiktok_records = generate_tiktok_daily_data(tiktok_id, start_date, end_date)
        db.add_all(tiktok_records)

        # Shopee
        shopee_id = platform_map["shopee"]
        shopee_records = generate_shopee_daily_data(shopee_id, start_date, end_date)
        db.add_all(shopee_records)

        db.commit()

        total = len(amazon_records) + len(tiktok_records) + len(shopee_records)
        print(f"[Seed] 30 days of mock data generated")
        print(f"   Amazon:  {len(amazon_records)} rows")
        print(f"   TikTok:  {len(tiktok_records)} rows")
        print(f"   Shopee:  {len(shopee_records)} rows")
        print(f"   Total:   {total} rows")
        print(f"   Date range: {start_date} -> {end_date}")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Seed failed: {e}")
        raise
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
#  BACKWARD-COMPATIBLE ALIAS
# ═══════════════════════════════════════════════════════════════

# Keep for any old code that may still call seed_all()
seed_all = seed_mock_data


if __name__ == "__main__":
    import sys
    if "--init" in sys.argv:
        init_schema()
    else:
        seed_mock_data()

