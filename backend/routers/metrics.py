"""Metric API router — CRUD for custom metrics, formula validation."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Metric, CustomMetricDependency, DashboardWidget
from schemas import (
    MetricOut, MetricCreate, MetricUpdate,
    FormulaValidateRequest, FormulaValidateResponse,
)
from formula_engine import (
    validate_formula, evaluate_formula, extract_variables, detect_cycle,
)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _get_available_keys(platform_id: int, db: Session) -> set[str]:
    """Get all available metric keys for a platform (built-in keys + existing custom keys)."""
    metrics = db.query(Metric).filter(
        Metric.platform_id == platform_id,
        Metric.is_deleted == False,
    ).all()
    return {m.key for m in metrics}


def _get_existing_dependencies(db: Session) -> dict[str, set[str]]:
    """Get dependency graph from all custom metrics."""
    deps = {}
    custom_metrics = db.query(Metric).filter(
        Metric.is_builtin == False,
        Metric.is_deleted == False,
        Metric.formula.isnot(None),
    ).all()
    for cm in custom_metrics:
        if cm.formula:
            deps[cm.key] = set(extract_variables(cm.formula))
    return deps


# ── Static routes (must come BEFORE dynamic /{metric_id} routes) ──

@router.get("/deleted", response_model=list[MetricOut])
def list_deleted_metrics(platform_id: int = Query(...), db: Session = Depends(get_db)):
    """List soft-deleted custom metrics for a platform."""
    metrics = db.query(Metric).filter(
        Metric.platform_id == platform_id,
        Metric.is_builtin == False,
        Metric.is_deleted == True,
    ).all()
    return metrics


@router.post("/validate-formula", response_model=FormulaValidateResponse)
def validate_formula_endpoint(body: FormulaValidateRequest, db: Session = Depends(get_db)):
    """Validate a formula and return sample result."""
    available = _get_available_keys(body.platform_id, db)
    valid, error, variables = validate_formula(body.formula, available)

    if not valid:
        return FormulaValidateResponse(valid=False, error=error, variables=variables)

    # Try sample calculation with mock values = 100
    mock_values = {v: 100.0 for v in variables}
    sample = evaluate_formula(body.formula, mock_values)

    return FormulaValidateResponse(
        valid=True,
        variables=variables,
        sample_result=round(sample, 2) if sample is not None else None,
        sample_unit="(基于模拟值 100 计算)",
    )


# ── Dynamic routes ─────────────────────────────────────────────

@router.post("", response_model=MetricOut, status_code=201)
def create_metric(body: MetricCreate, db: Session = Depends(get_db)):
    """Create a user custom metric."""
    if not body.key.startswith("custom_"):
        raise HTTPException(400, "自定义指标的 key 必须以 'custom_' 开头")

    existing = db.query(Metric).filter(
        Metric.platform_id == body.platform_id,
        Metric.key == body.key,
        Metric.is_deleted == False,
    ).first()
    if existing:
        raise HTTPException(400, f"指标 key '{body.key}' 已存在")

    available = _get_available_keys(body.platform_id, db)
    valid, error, variables = validate_formula(body.formula, available)
    if not valid:
        raise HTTPException(400, error)

    existing_deps = _get_existing_dependencies(db)
    cycle = detect_cycle(body.key, variables, existing_deps)
    if cycle:
        raise HTTPException(400, f"检测到循环依赖: {' → '.join(cycle)}")

    metric = Metric(
        platform_id=body.platform_id,
        name=body.name,
        key=body.key,
        description=body.description,
        category="custom",
        data_type=body.data_type,
        unit=body.unit,
        is_builtin=False,
        is_default=False,
        default_widget_type="kpi",
        formula=body.formula,
        created_by=1,
    )
    db.add(metric)
    db.flush()

    for var in variables:
        dep = CustomMetricDependency(
            custom_metric_id=metric.id,
            depends_on_metric_key=var,
        )
        db.add(dep)

    db.commit()
    db.refresh(metric)
    return metric


@router.put("/{metric_id}", response_model=MetricOut)
def update_metric(metric_id: int, body: MetricUpdate, db: Session = Depends(get_db)):
    """Update a custom metric (formula, name, unit)."""
    metric = db.query(Metric).filter(
        Metric.id == metric_id,
        Metric.is_builtin == False,
        Metric.is_deleted == False,
    ).first()
    if not metric:
        raise HTTPException(404, "自定义指标不存在")

    if body.name is not None:
        metric.name = body.name
    if body.unit is not None:
        metric.unit = body.unit
    if body.description is not None:
        metric.description = body.description

    if body.formula is not None:
        available = _get_available_keys(metric.platform_id, db)
        available.discard(metric.key)

        valid, error, variables = validate_formula(body.formula, available)
        if not valid:
            raise HTTPException(400, error)

        existing_deps = _get_existing_dependencies(db)
        existing_deps.pop(metric.key, None)
        cycle = detect_cycle(metric.key, variables, existing_deps)
        if cycle:
            raise HTTPException(400, f"检测到循环依赖: {' → '.join(cycle)}")

        metric.formula = body.formula

        db.query(CustomMetricDependency).filter(
            CustomMetricDependency.custom_metric_id == metric.id
        ).delete()
        for var in variables:
            dep = CustomMetricDependency(
                custom_metric_id=metric.id,
                depends_on_metric_key=var,
            )
            db.add(dep)

    db.commit()
    db.refresh(metric)
    return metric


@router.delete("/{metric_id}")
def soft_delete_metric(metric_id: int, db: Session = Depends(get_db)):
    """Soft-delete a custom metric."""
    metric = db.query(Metric).filter(
        Metric.id == metric_id,
        Metric.is_builtin == False,
        Metric.is_deleted == False,
    ).first()
    if not metric:
        raise HTTPException(404, "自定义指标不存在")

    widget_count = db.query(DashboardWidget).filter(
        DashboardWidget.metric_id == metric_id,
        DashboardWidget.is_deleted == False,
    ).count()
    if widget_count > 0:
        raise HTTPException(400, f"该指标正在 {widget_count} 个看板组件中使用，请先从看板移除后再删除")

    metric.is_deleted = True
    db.commit()
    return {"message": "指标已删除（软删除）", "metric_id": metric_id}


@router.post("/{metric_id}/restore", response_model=MetricOut)
def restore_metric(metric_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted custom metric."""
    metric = db.query(Metric).filter(
        Metric.id == metric_id,
        Metric.is_builtin == False,
        Metric.is_deleted == True,
    ).first()
    if not metric:
        raise HTTPException(404, "未找到已删除的自定义指标")

    conflict = db.query(Metric).filter(
        Metric.platform_id == metric.platform_id,
        Metric.key == metric.key,
        Metric.is_deleted == False,
    ).first()
    if conflict:
        raise HTTPException(400, f"无法恢复：指标 key '{metric.key}' 已被占用")

    metric.is_deleted = False
    db.commit()
    db.refresh(metric)
    return metric


@router.delete("/{metric_id}/permanent")
def permanent_delete_metric(metric_id: int, db: Session = Depends(get_db)):
    """Permanently delete a custom metric and its dependencies."""
    metric = db.query(Metric).filter(
        Metric.id == metric_id,
        Metric.is_builtin == False,
    ).first()
    if not metric:
        raise HTTPException(404, "自定义指标不存在")

    if not metric.is_deleted:
        raise HTTPException(400, "请先软删除该指标，再执行彻底删除")

    db.query(CustomMetricDependency).filter(
        CustomMetricDependency.custom_metric_id == metric_id
    ).delete()

    db.query(DashboardWidget).filter(
        DashboardWidget.metric_id == metric_id
    ).delete()

    db.delete(metric)
    db.commit()
    return {"message": "指标已彻底删除", "metric_id": metric_id}
