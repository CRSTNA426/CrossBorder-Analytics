#!/usr/bin/env python
"""
CrossBorder Analytics — One-click startup.

Usage:
    python run.py                  # Auto: init if no DB, else start
    python run.py --init-only      # Create empty schema, no demo data
    python run.py --seed           # Init schema + 30 days mock data
    python run.py --no-seed        # Skip init, just start server
    python run.py --sync           # Data sync only, no server
    python run.py --sync --date 2026-06-16

Modes:
    --init-only   Drop & create tables + platforms + metrics.  NO business data.
                  Recommended for fresh clone / real data import.

    --seed        Full demo: init schema + 30 days of realistic mock data.
                  Use for screenshots, demos, or exploring features.

    --no-seed     Start server immediately. Assumes DB already exists.
"""
import sys
import os
import io

# Fix Unicode output on Windows (skip on Render / non-TTY)
if sys.stdout.isatty() and os.name == 'nt':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

DB_PATH = os.getenv("DATABASE_URL", "")
if not DB_PATH:
    DB_PATH = os.path.join(os.path.dirname(__file__), "data", "crossborder.db")


def db_exists() -> bool:
    return os.path.isfile(DB_PATH)


def main():
    args = set(sys.argv[1:])

    # ── Sync mode (no server) ──────────────────────────────────
    if "--sync" in args:
        sync_args = []
        argv = sys.argv[1:]
        for i, arg in enumerate(argv):
            if arg == "--date" and i + 1 < len(argv):
                sync_args.extend(["--date", argv[i + 1]])
            elif arg in ("--all", "--platform"):
                if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                    sync_args.extend([arg, argv[i + 1]])
                else:
                    sync_args.append(arg)

        print("[Sync] Running data sync...")
        from sync import main as sync_main
        sys.argv = ["sync.py"] + sync_args
        sync_main()
        return

    # ── Render mode (production) ────────────────────────────────
    is_render = "--render" in args

    # ── Determine init mode ────────────────────────────────────
    if "--init-only" in args or is_render:
        print("[Init] Creating empty schema (no business data)...")
        from seed import init_schema
        init_schema()
        print()
    elif "--seed" in args:
        print("[Seed] Generating 30 days of mock data...")
        from seed import seed_mock_data
        seed_mock_data()
        print()
    elif "--no-seed" in args:
        pass
    else:
        if db_exists():
            print("[Info] Database found, starting server...")
        else:
            print("[Init] No database found — creating empty schema")
            print("[Init] Run 'python run.py --seed' later for demo data")
            from seed import init_schema
            init_schema()
            print()

    # ── Start server ───────────────────────────────────────────
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = "0.0.0.0"
    print(f"[Start] CrossBorder Analytics API at http://{host}:{port}")
    print(f"[Docs]  http://{host}:{port}/docs")
    if not db_exists():
        print("[Hint]  No data yet — use '📤 导入数据' in the UI or 'python run.py --seed'")

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=not is_render,  # disable reload in production
        reload_dirs=[os.path.join(os.path.dirname(__file__), "backend")] if not is_render else None,
    )


if __name__ == "__main__":
    main()
