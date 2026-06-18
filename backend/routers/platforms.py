"""Platform API router."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Platform, Metric
from schemas import PlatformOut, MetricOut

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformOut])
def list_platforms(db: Session = Depends(get_db)):
    return db.query(Platform).all()


@router.get("/{platform_id}", response_model=PlatformOut)
def get_platform(platform_id: int, db: Session = Depends(get_db)):
    return db.query(Platform).filter(Platform.id == platform_id).first()


@router.get("/{platform_id}/metrics", response_model=list[MetricOut])
def get_platform_metrics(platform_id: int, db: Session = Depends(get_db)):
    """Get all available metrics for a platform (built-in + user custom, not deleted)."""
    metrics = db.query(Metric).filter(
        Metric.platform_id == platform_id,
        Metric.is_deleted == False,
    ).all()
    return metrics


@router.get("/{platform_id}/default-metrics", response_model=list[MetricOut])
def get_default_metrics(platform_id: int, db: Session = Depends(get_db)):
    """Get the default-display built-in metrics for a platform."""
    metrics = db.query(Metric).filter(
        Metric.platform_id == platform_id,
        Metric.is_builtin == True,
        Metric.is_default == True,
        Metric.is_deleted == False,
    ).all()
    return metrics
