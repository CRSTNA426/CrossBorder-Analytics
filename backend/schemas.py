"""Pydantic request/response schemas."""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Platform ────────────────────────────────────────────────────
class PlatformOut(BaseModel):
    id: int
    name: str
    code: str
    icon: str = ""
    description: str = ""
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Metric ──────────────────────────────────────────────────────
class MetricOut(BaseModel):
    id: int
    platform_id: int
    name: str
    key: str
    description: str = ""
    category: str = "custom"
    data_type: str = "number"
    unit: str = ""
    is_builtin: bool = True
    is_default: bool = False
    default_widget_type: str = "kpi"
    formula: Optional[str] = None
    is_deleted: bool = False
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MetricCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    key: str = Field(..., min_length=1, max_length=100, pattern=r"^custom_\w+$")
    formula: str = Field(..., min_length=1, max_length=1000)
    data_type: str = Field("number", pattern="^(number|percentage|currency)$")
    unit: str = Field("", max_length=20)
    platform_id: int
    description: str = ""


class MetricUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    formula: Optional[str] = Field(None, max_length=1000)
    unit: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None


class FormulaValidateRequest(BaseModel):
    formula: str
    platform_id: int


class FormulaValidateResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    variables: list[str] = []
    sample_result: Optional[float] = None
    sample_unit: Optional[str] = None


# ── Dashboard ───────────────────────────────────────────────────
class WidgetCreate(BaseModel):
    metric_id: int
    position: int = 0
    widget_type: str = "kpi"
    width: int = 3
    height: int = 1
    config_json: str = "{}"


class WidgetUpdate(BaseModel):
    widget_type: Optional[str] = None
    position: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    config_json: Optional[str] = None
    is_visible: Optional[bool] = None


class WidgetOut(BaseModel):
    id: int
    dashboard_id: int
    metric_id: int
    position: int
    widget_type: str
    width: int
    height: int
    config_json: str = "{}"
    is_visible: bool = True
    is_deleted: bool = False
    metric: Optional[MetricOut] = None

    model_config = {"from_attributes": True}


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    platform_id: int
    metric_ids: list[int] = []


class DashboardOut(BaseModel):
    id: int
    user_id: int
    name: str
    platform_id: int
    layout_json: str = '{"widgets":[]}'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    platform: Optional[PlatformOut] = None
    widgets: list[WidgetOut] = []

    model_config = {"from_attributes": True}


class LayoutUpdate(BaseModel):
    layout_json: str


# ── Data ────────────────────────────────────────────────────────
class MetricDataPoint(BaseModel):
    metric_key: str
    name: str
    value: Optional[float]
    data_type: str
    unit: str
    category: str
    widget_type: str


class DashboardDataResponse(BaseModel):
    dashboard_id: int
    date: str
    platform: str
    metrics: list[MetricDataPoint]


class TrendPoint(BaseModel):
    date: str
    values: dict[str, Optional[float]]


class TrendResponse(BaseModel):
    dashboard_id: int
    metric_keys: list[str]
    days: int
    points: list[TrendPoint]
