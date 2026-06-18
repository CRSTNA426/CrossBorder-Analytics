"""Data API router — dashboard data queries, trends, computed custom metrics."""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Dashboard, DashboardWidget, Metric, DailyData
from formula_engine import evaluate_formula, extract_variables

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("")
def get_dashboard_data(
    dashboard_id: int = Query(...),
    target_date: str = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    """Get all metric values for a dashboard on a specific date (including computed custom metrics)."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(404, "看板不存在")

    if target_date:
        try:
            query_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "日期格式错误，应为 YYYY-MM-DD")
    else:
        # Default to latest available date
        latest = db.query(DailyData.date).filter(
            DailyData.platform_id == dashboard.platform_id
        ).order_by(DailyData.date.desc()).first()
        query_date = latest[0] if latest else date.today()

    # Get all visible widgets
    widgets = db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dashboard_id,
        DashboardWidget.is_deleted == False,
        DashboardWidget.is_visible == True,
    ).all()

    if not widgets:
        return {
            "dashboard_id": dashboard_id,
            "date": query_date.isoformat(),
            "platform": dashboard.platform.name if dashboard.platform else "",
            "metrics": [],
        }

    metric_ids = [w.metric_id for w in widgets]
    metrics = db.query(Metric).filter(Metric.id.in_(metric_ids)).all()
    metric_map = {m.id: m for m in metrics}

    # First pass: get all built-in metric raw values from daily_data
    raw_values: dict[str, float | None] = {}
    builtin_keys = set()
    for m in metrics:
        if m.is_builtin:
            builtin_keys.add(m.key)

    # Also fetch raw values for built-in keys referenced by custom metric formulas
    for m in metrics:
        if not m.is_builtin and m.formula:
            for var in extract_variables(m.formula):
                # Check if this variable is a built-in key
                var_metric = db.query(Metric).filter(
                    Metric.platform_id == dashboard.platform_id,
                    Metric.key == var,
                    Metric.is_builtin == True,
                ).first()
                if var_metric:
                    builtin_keys.add(var)

    if builtin_keys:
        rows = db.query(DailyData).filter(
            DailyData.platform_id == dashboard.platform_id,
            DailyData.date == query_date,
            DailyData.metric_key.in_(builtin_keys),
        ).all()
        for row in rows:
            raw_values[row.metric_key] = row.value

    # Second pass: compute custom metrics using formula engine
    # Do this iteratively in case custom metrics depend on other custom metrics
    computed_values: dict[str, float | None] = dict(raw_values)
    custom_metrics = [m for m in metrics if not m.is_builtin and m.formula]
    max_iterations = 10  # safety against deep dependency chains

    for _ in range(max_iterations):
        updated = False
        for cm in custom_metrics:
            if cm.key in computed_values:
                continue
            variables = extract_variables(cm.formula)
            if all(v in computed_values for v in variables):
                vals = {v: computed_values[v] for v in variables}
                result = evaluate_formula(cm.formula, vals)
                computed_values[cm.key] = result
                updated = True
        if not updated:
            break

    # Build response
    result_metrics = []
    for w in widgets:
        m = metric_map.get(w.metric_id)
        if not m:
            continue
        value = computed_values.get(m.key)

        result_metrics.append({
            "metric_key": m.key,
            "name": m.name,
            "value": value,
            "data_type": m.data_type,
            "unit": m.unit,
            "category": m.category,
            "widget_type": w.widget_type,
        })

    platform_name = dashboard.platform.name if dashboard.platform else ""

    return {
        "dashboard_id": dashboard_id,
        "date": query_date.isoformat(),
        "platform": platform_name,
        "metrics": result_metrics,
    }


@router.get("/trend")
def get_trend_data(
    dashboard_id: int = Query(...),
    metric_keys: str = Query(..., description="Comma-separated metric keys"),
    days: int = Query(30),
    db: Session = Depends(get_db),
):
    """Get time-series trend data for specified metric keys."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(404, "看板不存在")

    keys = [k.strip() for k in metric_keys.split(",") if k.strip()]
    if not keys:
        raise HTTPException(400, "至少需要一个指标 key")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    # Get metrics and classify
    all_metrics = db.query(Metric).filter(
        Metric.platform_id == dashboard.platform_id,
        Metric.key.in_(keys),
    ).all()
    metric_map = {m.key: m for m in all_metrics}

    builtin_keys = [k for k in keys if k in metric_map and metric_map[k].is_builtin]
    custom_keys = [k for k in keys if k in metric_map and not metric_map[k].is_builtin]

    # Fetch raw data
    rows = db.query(DailyData).filter(
        DailyData.platform_id == dashboard.platform_id,
        DailyData.date >= start_date,
        DailyData.date <= end_date,
        DailyData.metric_key.in_(builtin_keys),
    ).order_by(DailyData.date).all()

    # Organize by date
    date_values: dict[str, dict[str, float | None]] = {}
    for row in rows:
        d = row.date.isoformat()
        if d not in date_values:
            date_values[d] = {}
        date_values[d][row.metric_key] = row.value

    # Compute custom metrics per date
    if custom_keys:
        for d_str, vals in date_values.items():
            computed = dict(vals)
            for ck in custom_keys:
                cm = metric_map.get(ck)
                if not cm or not cm.formula:
                    continue
                variables = extract_variables(cm.formula)
                if all(v in computed for v in variables):
                    var_vals = {v: computed[v] for v in variables}
                    result = evaluate_formula(cm.formula, var_vals)
                    computed[ck] = result
            date_values[d_str] = {k: computed.get(k) for k in keys}

    # Build points
    points = []
    current = start_date
    while current <= end_date:
        d_str = current.isoformat()
        vals = date_values.get(d_str, {})
        points.append({
            "date": d_str,
            "values": {k: vals.get(k) for k in keys},
        })
        current += timedelta(days=1)

    return {
        "dashboard_id": dashboard_id,
        "metric_keys": keys,
        "days": days,
        "points": points,
    }
