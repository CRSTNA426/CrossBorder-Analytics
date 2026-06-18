"""
CSV Upload API — Parse seller center exports and import into daily_data.
"""
import csv
import io
import re
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from models import Platform, Metric, DailyData
from config.csv_mapping import match_columns, PLATFORM_MAPPINGS

router = APIRouter(prefix="/api", tags=["upload"])

# ── Helpers ────────────────────────────────────────────────────

def _parse_date(raw: str) -> Optional[date]:
    """Try multiple date formats. Returns date or None."""
    raw = raw.strip()
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _safe_float(raw: str) -> Optional[float]:
    """Parse a string to float, stripping $ and commas."""
    raw = raw.strip().replace('$', '').replace(',', '').replace('%', '')
    if not raw or raw == '-' or raw.lower() == 'n/a':
        return None
    try:
        return float(raw)
    except ValueError:
        return None


# ── Preview Endpoint (header only, no data commit) ────────────

@router.post("/upload-csv/preview")
async def upload_csv_preview(
    platform_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Preview CSV column mapping without importing data.
    Only parses the header row and returns which columns will be mapped.
    """
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(404, "平台不存在")

    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "仅支持 CSV 文件格式 (.csv)")

    content = await file.read()
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            text = content.decode('gbk')
        except UnicodeDecodeError:
            raise HTTPException(400, "无法解析文件编码，请保存为 UTF-8 格式")

    lines = text.strip().split('\n')
    if len(lines) < 1:
        raise HTTPException(400, "CSV 文件为空")

    # Parse header
    header = next(csv.reader(io.StringIO(lines[0])), [])
    csv_columns = [h.strip() for h in header if h.strip()]

    # Detect date column
    date_col = None
    for col in csv_columns:
        if col.strip().lower() in ('date', '日期', 'data_date', 'order_date', 'report_date'):
            date_col = col
            break

    col_mapping = match_columns(csv_columns, platform.code)

    # Count data rows
    data_rows = len(lines) - 1

    # Get metric display names
    metrics = db.query(Metric).filter(
        Metric.platform_id == platform_id,
        Metric.is_builtin == True,
    ).all()
    metric_names = {m.key: m.name for m in metrics}

    mapping_with_names = {}
    for csv_col, metric_key in col_mapping.items():
        mapping_with_names[csv_col] = {
            "metric_key": metric_key,
            "metric_name": metric_names.get(metric_key, metric_key),
        }

    return {
        "platform": platform.name,
        "platform_code": platform.code,
        "csv_columns": csv_columns,
        "date_column": date_col,
        "column_mapping": mapping_with_names,
        "unmapped_columns": [c for c in csv_columns if c not in col_mapping and c != date_col],
        "data_rows": data_rows,
    }


# ── Import Endpoint (commits data) ────────────────────────────

@router.post("/upload-csv")
async def upload_csv(
    platform_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a CSV file exported from a seller center.
    Auto-matches column names to metric keys. Upserts into daily_data.

    CSV requirements:
      - Must have a 'date' column (or 'Date', '日期')
      - Other columns are auto-matched via csv_mapping.py
      - Rows with unparseable dates are skipped and reported
    """
    # Validate platform
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(404, "平台不存在")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "仅支持 CSV 文件格式 (.csv)")

    # Read file
    content = await file.read()
    try:
        text = content.decode('utf-8-sig')  # handle BOM
    except UnicodeDecodeError:
        try:
            text = content.decode('gbk')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except UnicodeDecodeError:
                raise HTTPException(400, "无法解析文件编码，请保存为 UTF-8 格式")

    # Parse CSV
    try:
        reader = csv.DictReader(io.StringIO(text))
    except Exception:
        raise HTTPException(400, "CSV 格式解析失败，请检查文件是否完整")

    csv_columns = reader.fieldnames or []
    if not csv_columns:
        raise HTTPException(400, "CSV 文件为空或缺少表头")

    # Detect date column
    date_col = None
    for col in csv_columns:
        cl = col.strip().lower()
        if cl in ('date', '日期', 'data_date', 'date_time', 'order_date', 'report_date'):
            date_col = col
            break
    if not date_col:
        raise HTTPException(400, f"缺少日期列。CSV 必须包含 'date' 或 '日期' 列。当前列: {', '.join(csv_columns)}")

    # Match columns to metric keys
    col_mapping = match_columns(csv_columns, platform.code)
    if not col_mapping:
        raise HTTPException(
            400,
            f"未识别到任何已知字段。\n"
            f"当前列: {', '.join(csv_columns)}\n"
            f"请参考 docs/CSV_UPLOAD.md 中的字段名要求"
        )

    # Get metric key → id mapping
    metrics = db.query(Metric).filter(
        Metric.platform_id == platform_id,
        Metric.is_builtin == True,
    ).all()
    metric_id_map = {m.key: m.id for m in metrics}

    # Process rows
    total = 0
    inserted = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):  # line 2 onwards (after header)
        # Parse date
        raw_date = (row.get(date_col) or '').strip()
        if not raw_date:
            skipped += 1
            errors.append(f"第 {row_num} 行: 日期为空，已跳过")
            continue

        row_date = _parse_date(raw_date)
        if not row_date:
            skipped += 1
            errors.append(f"第 {row_num} 行: 日期格式无法识别 '{raw_date}'，已跳过")
            continue

        # Parse each mapped column
        for csv_col, metric_key in col_mapping.items():
            raw_val = (row.get(csv_col) or '').strip()
            if not raw_val:
                continue  # skip empty cells

            value = _safe_float(raw_val)
            if value is None:
                errors.append(f"第 {row_num} 行, 列 '{csv_col}': 数值格式无法解析 '{raw_val}'，已跳过")
                continue

            total += 1
            mid = metric_id_map.get(metric_key)
            if not mid:
                skipped += 1
                continue

            # Upsert
            existing = db.query(DailyData).filter(
                DailyData.platform_id == platform_id,
                DailyData.date == row_date,
                DailyData.metric_key == metric_key,
            ).first()

            if existing:
                existing.value = value
                updated += 1
            else:
                db.add(DailyData(
                    platform_id=platform_id,
                    date=row_date,
                    metric_key=metric_key,
                    value=value,
                ))
                inserted += 1

    db.commit()

    # Determine the date range imported
    imported_dates: set[str] = set()
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        raw = (row.get(date_col) or '').strip()
        d = _parse_date(raw)
        if d:
            imported_dates.add(d.isoformat())

    return {
        "success": True,
        "platform": platform.name,
        "platform_code": platform.code,
        "total_cells": total,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:20],  # limit error messages
        "error_count": len(errors),
        "column_mapping": {k: v for k, v in col_mapping.items()},
        "imported_dates": sorted(imported_dates),
        "imported_date_count": len(imported_dates),
    }
