"""
Insight Engine — Rule-based operational insights (no AI).
Evaluates dashboard data against business rules and returns actionable cards + composite score.
"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Dashboard, DashboardWidget, DailyData, Metric

router = APIRouter(prefix="/api", tags=["insights"])


def _get_value(db: Session, platform_id: int, key: str, target_date: date) -> float | None:
    row = db.query(DailyData).filter(
        DailyData.platform_id == platform_id,
        DailyData.date == target_date,
        DailyData.metric_key == key,
    ).first()
    return row.value if row else None


def _get_prev_value(db: Session, platform_id: int, key: str, target_date: date) -> float | None:
    """Get previous day's value."""
    prev = target_date - timedelta(days=1)
    return _get_value(db, platform_id, key, prev)


def _get_prev_n_values(db: Session, platform_id: int, key: str, end_date: date, n: int) -> list[float | None]:
    """Get last N days of values (including end_date)."""
    start = end_date - timedelta(days=n - 1)
    rows = db.query(DailyData).filter(
        DailyData.platform_id == platform_id,
        DailyData.date >= start,
        DailyData.date <= end_date,
        DailyData.metric_key == key,
    ).order_by(DailyData.date).all()
    vals = {r.date: r.value for r in rows}
    result = []
    d = start
    while d <= end_date:
        result.append(vals.get(d))
        d += timedelta(days=1)
    return result


@router.get("/insights")
def get_insights(
    dashboard_id: int = Query(...),
    target_date: str = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    """
    Generate rule-based operational insights for a dashboard on a given date.
    Includes: inventory risk, ad anomaly, profit drop, GMV growth, composite score.
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(404, "看板不存在")

    platform_id = dashboard.platform_id

    if target_date:
        try:
            query_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "日期格式错误，应为 YYYY-MM-DD")
    else:
        latest = db.query(DailyData.date).filter(
            DailyData.platform_id == platform_id
        ).order_by(DailyData.date.desc()).first()
        query_date = latest[0] if latest else date.today()

    yesterday = query_date - timedelta(days=1)

    # ── Fetch core metrics ──────────────────────────────────────
    gmv = _get_value(db, platform_id, "gmv", query_date)
    prev_gmv = _get_value(db, platform_id, "gmv", yesterday)

    orders = _get_value(db, platform_id, "orders", query_date)

    inv_days = _get_value(db, platform_id, "inventory_days", query_date)
    fulfillable = _get_value(db, platform_id, "fulfillable_qty", query_date)
    daily_sales = _get_value(db, platform_id, "daily_sales", query_date)

    acos = _get_value(db, platform_id, "acos", query_date)
    prev_acos = _get_value(db, platform_id, "acos", yesterday)

    net_profit = _get_value(db, platform_id, "net_profit", query_date)
    prev_profit = _get_value(db, platform_id, "net_profit", yesterday)

    refund_rate = _get_value(db, platform_id, "refund_rate", query_date)
    ad_spend = _get_value(db, platform_id, "ad_spend", query_date)

    # Check if there is any data at all
    has_data = any(v is not None for v in [gmv, orders, inv_days, acos, net_profit])
    if not has_data:
        return {"insights": [], "score": None, "date": query_date.isoformat(), "empty": True}

    insights = []

    # ═══════════════════════════════════════════════════════════
    #  RULE 1: Inventory Risk  (库存风险)
    # ═══════════════════════════════════════════════════════════
    if inv_days is not None and inv_days < 7:
        suggest = 0
        if daily_sales is not None and daily_sales > 0 and fulfillable is not None:
            gap = max(0, daily_sales * 30 - fulfillable)
            suggest = int(gap)
        else:
            suggest = 500  # fallback

        insights.append({
            "id": "inventory_risk",
            "title": "⚠️ 库存告急",
            "content": f"可售天数仅 {inv_days} 天，预计 {inv_days} 天后断货。建议立即补货 {suggest} 件，优先安排海运/空运。",
            "priority": "high",
            "color": "red",
        })

    # ═══════════════════════════════════════════════════════════
    #  RULE 2: Ad Anomaly  (广告异常)
    # ═══════════════════════════════════════════════════════════
    if acos is not None and acos > 35:
        # Check if ACoS rose for 2 consecutive days
        acos_vals = _get_prev_n_values(db, platform_id, "acos", query_date, 3)
        rising = False
        if acos_vals and len(acos_vals) >= 3:
            valid = [v for v in acos_vals if v is not None]
            if len(valid) >= 2 and all(
                valid[i] < valid[i + 1] for i in range(len(valid) - 1)
            ):
                rising = True

        if rising or acos > 40:  # trigger even without 2-day trend if very high
            insights.append({
                "id": "ad_anomaly",
                "title": "🔥 广告异常",
                "content": (
                    f"ACoS{' 连续上涨至' if rising else ' 高达'} {acos}%，"
                    f"可能原因：素材疲劳 / 竞价过高 / 竞品加大投放。"
                    f"建议：暂停低效广告组，测试新创意，调整出价策略。"
                ),
                "priority": "medium",
                "color": "orange",
            })

    # ═══════════════════════════════════════════════════════════
    #  RULE 3: Profit Drop  (利润下滑)
    # ═══════════════════════════════════════════════════════════
    if net_profit is not None and prev_profit is not None and prev_profit > 0:
        drop_pct = round((prev_profit - net_profit) / prev_profit * 100, 1)
        if drop_pct > 20:
            # Determine likely cause
            cause_parts = []
            if refund_rate is not None:
                prev_refund = _get_value(db, platform_id, "refund_rate", yesterday)
                if prev_refund is not None and refund_rate > prev_refund:
                    cause_parts.append("退款率上升")
            if ad_spend is not None:
                prev_spend = _get_value(db, platform_id, "ad_spend", yesterday)
                if prev_spend is not None and ad_spend > prev_spend:
                    cause_parts.append("广告花费增加")
            if not cause_parts:
                cause_parts.append("综合成本上升")

            insights.append({
                "id": "profit_drop",
                "title": "💸 利润下滑",
                "content": (
                    f"净利润环比下降 {drop_pct}%，"
                    f"主要原因：{' / '.join(cause_parts)}。"
                    f"建议：检查退款率趋势、优化广告投放、审查成本结构。"
                ),
                "priority": "high",
                "color": "red",
            })

    # ═══════════════════════════════════════════════════════════
    #  RULE 4: GMV Growth  (增长亮点)
    # ═══════════════════════════════════════════════════════════
    if gmv is not None and prev_gmv is not None and prev_gmv > 0:
        growth_pct = round((gmv - prev_gmv) / prev_gmv * 100, 1)
        if growth_pct > 15:
            insights.append({
                "id": "gmv_growth",
                "title": "🚀 增长亮点",
                "content": (
                    f"GMV 环比增长 {growth_pct}%，"
                    f"建议：加大主力 SKU 库存和广告投入，抓住增长窗口期。"
                ),
                "priority": "low",
                "color": "green",
            })

    # ═══════════════════════════════════════════════════════════
    #  RULE 5: Composite Score  (综合经营评分)
    # ═══════════════════════════════════════════════════════════
    score = None
    if inv_days is not None or acos is not None or net_profit is not None:
        # Inventory health: 0-30 points (>=14d → 30, <7 → 0, linear)
        inv_score = 0
        if inv_days is not None:
            if inv_days >= 14:
                inv_score = 30
            elif inv_days < 7:
                inv_score = 0
            else:
                inv_score = round((inv_days - 7) / (14 - 7) * 30, 1)

        # Ad efficiency: 0-30 points (<=25% → 30, >40% → 0, linear)
        ad_score = 0
        if acos is not None:
            if acos <= 25:
                ad_score = 30
            elif acos > 40:
                ad_score = 0
            else:
                ad_score = round((40 - acos) / (40 - 25) * 30, 1)

        # Profit level: 0-40 points (>=20% margin → 40, <0 → 0, linear)
        profit_score = 0
        if net_profit is not None and gmv is not None and gmv > 0:
            margin = net_profit / gmv * 100
            if margin >= 20:
                profit_score = 40
            elif margin < 0:
                profit_score = 0
            else:
                profit_score = round(margin / 20 * 40, 1)

        total = round(inv_score + ad_score + profit_score, 1)

        if total >= 80:
            rating = "优秀"
        elif total >= 60:
            rating = "良好"
        else:
            rating = "需关注"

        score = {
            "total": total,
            "inventory": inv_score,
            "ad": ad_score,
            "profit": profit_score,
            "rating": rating,
        }

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(key=lambda i: priority_order.get(i.get("priority", "low"), 99))

    return {
        "insights": insights,
        "score": score,
        "date": query_date.isoformat(),
        "empty": False,
    }
