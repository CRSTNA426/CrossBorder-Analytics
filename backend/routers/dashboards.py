"""Dashboard API router."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Dashboard, DashboardWidget, Metric, Platform
from schemas import (
    DashboardCreate, DashboardOut, WidgetCreate, WidgetUpdate, WidgetOut, LayoutUpdate,
)

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


@router.post("", response_model=DashboardOut, status_code=201)
def create_dashboard(body: DashboardCreate, db: Session = Depends(get_db)):
    """Create a new dashboard with optional pre-selected metrics."""
    # Verify platform exists
    platform = db.query(Platform).filter(Platform.id == body.platform_id).first()
    if not platform:
        raise HTTPException(404, "平台不存在")

    dashboard = Dashboard(
        user_id=1,  # default user
        name=body.name,
        platform_id=body.platform_id,
    )
    db.add(dashboard)
    db.flush()

    # Add widgets for pre-selected metrics
    if body.metric_ids:
        for i, mid in enumerate(body.metric_ids):
            metric = db.query(Metric).filter(Metric.id == mid, Metric.is_deleted == False).first()
            if not metric:
                continue
            widget = DashboardWidget(
                dashboard_id=dashboard.id,
                metric_id=mid,
                position=i,
                widget_type=metric.default_widget_type or "kpi",
                width=3,
                height=1,
            )
            db.add(widget)

    db.commit()
    db.refresh(dashboard)
    return _load_dashboard(dashboard.id, db)


@router.get("", response_model=list[DashboardOut])
def list_dashboards(db: Session = Depends(get_db)):
    """List all dashboards for the default user."""
    dashboards = db.query(Dashboard).filter(Dashboard.user_id == 1).all()
    return [_load_dashboard(d.id, db) for d in dashboards]


@router.get("/{dashboard_id}", response_model=DashboardOut)
def get_dashboard(dashboard_id: int, db: Session = Depends(get_db)):
    """Get dashboard detail with widgets."""
    return _load_dashboard(dashboard_id, db)


@router.put("/{dashboard_id}/layout")
def update_layout(dashboard_id: int, body: LayoutUpdate, db: Session = Depends(get_db)):
    """Save widget layout/order."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(404, "看板不存在")
    dashboard.layout_json = body.layout_json
    dashboard.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "布局已保存"}


@router.post("/{dashboard_id}/widgets", response_model=WidgetOut, status_code=201)
def add_widget(dashboard_id: int, body: WidgetCreate, db: Session = Depends(get_db)):
    """Add a widget to the dashboard."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(404, "看板不存在")

    metric = db.query(Metric).filter(Metric.id == body.metric_id, Metric.is_deleted == False).first()
    if not metric:
        raise HTTPException(404, "指标不存在")

    # Check if already added
    existing = db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dashboard_id,
        DashboardWidget.metric_id == body.metric_id,
        DashboardWidget.is_deleted == False,
    ).first()
    if existing:
        raise HTTPException(400, "该指标已添加到看板")

    widget = DashboardWidget(
        dashboard_id=dashboard_id,
        metric_id=body.metric_id,
        position=body.position,
        widget_type=body.widget_type or metric.default_widget_type,
        width=body.width,
        height=body.height,
        config_json=body.config_json,
    )
    db.add(widget)
    db.commit()
    db.refresh(widget)
    return _load_widget(widget, db)


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetOut)
def update_widget(dashboard_id: int, widget_id: int, body: WidgetUpdate, db: Session = Depends(get_db)):
    """Update a widget (type, position, size, config, visibility)."""
    widget = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.dashboard_id == dashboard_id,
        DashboardWidget.is_deleted == False,
    ).first()
    if not widget:
        raise HTTPException(404, "组件不存在")

    if body.widget_type is not None:
        widget.widget_type = body.widget_type
    if body.position is not None:
        widget.position = body.position
    if body.width is not None:
        widget.width = body.width
    if body.height is not None:
        widget.height = body.height
    if body.config_json is not None:
        widget.config_json = body.config_json
    if body.is_visible is not None:
        widget.is_visible = body.is_visible

    db.commit()
    db.refresh(widget)
    return _load_widget(widget, db)


@router.delete("/{dashboard_id}/widgets/{widget_id}")
def remove_widget(dashboard_id: int, widget_id: int, db: Session = Depends(get_db)):
    """Soft-delete a widget from the dashboard."""
    widget = db.query(DashboardWidget).filter(
        DashboardWidget.id == widget_id,
        DashboardWidget.dashboard_id == dashboard_id,
        DashboardWidget.is_deleted == False,
    ).first()
    if not widget:
        raise HTTPException(404, "组件不存在")

    widget.is_deleted = True
    db.commit()
    return {"message": "组件已从看板移除"}


def _load_widget(widget: DashboardWidget, db: Session) -> dict:
    """Load widget with metric relationship."""
    metric = db.query(Metric).filter(Metric.id == widget.metric_id).first()
    result = {
        "id": widget.id,
        "dashboard_id": widget.dashboard_id,
        "metric_id": widget.metric_id,
        "position": widget.position,
        "widget_type": widget.widget_type,
        "width": widget.width,
        "height": widget.height,
        "config_json": widget.config_json,
        "is_visible": widget.is_visible,
        "is_deleted": widget.is_deleted,
        "metric": None,
    }
    if metric:
        result["metric"] = {
            "id": metric.id,
            "platform_id": metric.platform_id,
            "name": metric.name,
            "key": metric.key,
            "description": metric.description or "",
            "category": metric.category,
            "data_type": metric.data_type,
            "unit": metric.unit,
            "is_builtin": metric.is_builtin,
            "is_default": metric.is_default,
            "default_widget_type": metric.default_widget_type,
            "formula": metric.formula,
            "is_deleted": metric.is_deleted,
            "created_at": None,
        }
    return result


def _load_dashboard(dashboard_id: int, db: Session) -> dict:
    """Load a full dashboard with widgets and platform."""
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    if not dashboard:
        raise HTTPException(404, "看板不存在")

    platform = db.query(Platform).filter(Platform.id == dashboard.platform_id).first()
    widgets = db.query(DashboardWidget).filter(
        DashboardWidget.dashboard_id == dashboard_id,
        DashboardWidget.is_deleted == False,
    ).order_by(DashboardWidget.position).all()

    return {
        "id": dashboard.id,
        "user_id": dashboard.user_id,
        "name": dashboard.name,
        "platform_id": dashboard.platform_id,
        "layout_json": dashboard.layout_json,
        "created_at": dashboard.created_at.isoformat() if dashboard.created_at else None,
        "updated_at": dashboard.updated_at.isoformat() if dashboard.updated_at else None,
        "platform": {
            "id": platform.id,
            "name": platform.name,
            "code": platform.code,
            "icon": platform.icon,
            "description": platform.description,
            "created_at": platform.created_at.isoformat() if platform.created_at else None,
        } if platform else None,
        "widgets": [_load_widget(w, db) for w in widgets],
    }
