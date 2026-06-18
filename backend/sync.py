#!/usr/bin/env python
"""
Data Sync Service — Pulls store data from active adapter and writes to daily_data.

Usage:
    python sync.py                    # Sync yesterday's data for all platforms
    python sync.py --date 2026-06-15  # Sync a specific date
    python sync.py --platform amazon  # Sync only one platform
    python sync.py --all              # Sync all 30 days (useful for re-seeding)
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import SessionLocal
from models import Platform, Metric, DailyData
from adapters import get_adapter


def sync_data(target_date: date, platform_code: str | None = None):
    """
    Fetch data from the active adapter and write to daily_data table.

    Upsert logic: if a row for (platform_id, date, metric_key) already exists,
    update its value. Otherwise insert a new row.
    """
    db = SessionLocal()
    adapter = get_adapter()

    try:
        # Determine which platforms to sync
        query = db.query(Platform)
        if platform_code:
            query = query.filter(Platform.code == platform_code)
        platforms = query.all()

        if not platforms:
            print(f"[Sync] No platforms found. Run `python run.py --seed-only` first.")
            return

        total_inserted = 0
        total_updated = 0

        for platform in platforms:
            print(f"\n[Sync] Platform: {platform.name} ({platform.code})")
            print(f"       Adapter: {adapter.name()}")
            print(f"       Date:    {target_date}")

            try:
                data = adapter.fetch_daily_data(platform.id, target_date)
            except NotImplementedError as e:
                print(f"       [SKIP] Adapter not implemented: {e}")
                continue
            except FileNotFoundError as e:
                print(f"       [SKIP] {e}")
                continue
            except Exception as e:
                print(f"       [ERROR] {e}")
                continue

            if not data:
                print(f"       [WARN] No data returned")
                continue

            # Get metric key→id mapping for this platform
            metrics = db.query(Metric).filter(
                Metric.platform_id == platform.id,
                Metric.is_builtin == True,
            ).all()
            metric_map = {m.key: m.id for m in metrics}

            inserted = 0
            updated = 0
            skipped = 0

            for metric_key, value in data.items():
                if metric_key not in metric_map:
                    skipped += 1
                    continue

                # Upsert
                existing = db.query(DailyData).filter(
                    DailyData.platform_id == platform.id,
                    DailyData.date == target_date,
                    DailyData.metric_key == metric_key,
                ).first()

                if existing:
                    existing.value = value
                    updated += 1
                else:
                    db.add(DailyData(
                        platform_id=platform.id,
                        date=target_date,
                        metric_key=metric_key,
                        value=value,
                    ))
                    inserted += 1

            db.commit()
            print(f"       Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
            total_inserted += inserted
            total_updated += updated

        print(f"\n[Sync] Complete. Total: {total_inserted} inserted, {total_updated} updated")

    except Exception as e:
        db.rollback()
        print(f"[Sync] FAILED: {e}")
        raise
    finally:
        db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CrossBorder Data Sync Service")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date (YYYY-MM-DD). Default: yesterday")
    parser.add_argument("--platform", type=str, default=None,
                        help="Platform code to sync (amazon, tiktok, shopee)")
    parser.add_argument("--all", action="store_true",
                        help="Sync all 30 days (useful for re-seeding)")
    args = parser.parse_args()

    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = date.today() - timedelta(days=1)

    if args.all:
        # Sync 30 days
        start = date.today() - timedelta(days=30)
        current = start
        while current <= target_date:
            sync_data(current, args.platform)
            current += timedelta(days=1)
    else:
        sync_data(target_date, args.platform)


if __name__ == "__main__":
    main()
