"""SQLAlchemy ORM models for CrossBorder Analytics."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from database import Base


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    icon = Column(String(200), default="")
    description = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    metrics = relationship("Metric", back_populates="platform", lazy="dynamic")
    dashboards = relationship("Dashboard", back_populates="platform")
    daily_data = relationship("DailyData", back_populates="platform")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    name = Column(String(100), nullable=False)
    key = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    category = Column(String(50), default="custom")  # overview|traffic|conversion|inventory|profit|custom
    data_type = Column(String(20), default="number")   # number|percentage|currency
    unit = Column(String(20), default="")
    is_builtin = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    default_widget_type = Column(String(20), default="kpi")  # kpi|line|bar|pie|table
    formula = Column(String(1000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)

    platform = relationship("Platform", back_populates="metrics")
    creator = relationship("User", back_populates="custom_metrics", foreign_keys=[created_by])
    widgets = relationship("DashboardWidget", back_populates="metric")
    dependencies = relationship(
        "CustomMetricDependency",
        back_populates="custom_metric",
        foreign_keys="CustomMetricDependency.custom_metric_id"
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dashboards = relationship("Dashboard", back_populates="user")
    custom_metrics = relationship("Metric", back_populates="creator", foreign_keys=[Metric.created_by])


class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    layout_json = Column(Text, default='{"widgets":[]}')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="dashboards")
    platform = relationship("Platform", back_populates="dashboards")
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=False)
    metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    position = Column(Integer, default=0)
    widget_type = Column(String(20), default="kpi")
    width = Column(Integer, default=3)
    height = Column(Integer, default=1)
    config_json = Column(Text, default="{}")
    is_visible = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    dashboard = relationship("Dashboard", back_populates="widgets")
    metric = relationship("Metric", back_populates="widgets")


class DailyData(Base):
    __tablename__ = "daily_data"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    date = Column(Date, nullable=False)
    metric_key = Column(String(100), nullable=False)
    value = Column(Float, nullable=True)
    notes = Column(String(500), default="")

    platform = relationship("Platform", back_populates="daily_data")


class CustomMetricDependency(Base):
    __tablename__ = "custom_metric_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    custom_metric_id = Column(Integer, ForeignKey("metrics.id"), nullable=False)
    depends_on_metric_key = Column(String(100), nullable=False)

    custom_metric = relationship(
        "Metric",
        back_populates="dependencies",
        foreign_keys=[custom_metric_id]
    )
