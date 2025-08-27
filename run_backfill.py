#!/usr/bin/env python3
"""
Backfill Ultrahuman data for a single day or a date range.
- Loads .env BEFORE importing the app
- Works with the Partner API mapping you just added
- Splits long ranges into <=90 day windows
"""

from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path
import os
import sys
import time
import argparse
from typing import Tuple
from utils.database import db


# 1) Load env first so app/services see the keys
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# Optional sanity prints (comment out if noisy)
print("BASE:", os.getenv("ULTRAHUMAN_API_BASE"))
print("KEY present?", bool(os.getenv("ULTRAHUMAN_API_KEY")))
print("UH_EMAIL:", os.getenv("UH_EMAIL"))

# 2) Now import app + task
from app import create_app
from app.models import User
from tasks.data_ingestion import backfill_user_data

MAX_WINDOW_DAYS = 90

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill Ultrahuman metrics."
    )
    p.add_argument("--user-id", default="sample_user",
                   help="User.id in your DB (default: sample_user)")
    group = p.add_mutually_exclusive_group(required=False)
    group.add_argument("--day", help="YYYY-MM-DD (single day)")
    group.add_argument("--start", help="YYYY-MM-DD (inclusive start)")
    p.add_argument("--end", help="YYYY-MM-DD (exclusive end). Required if --start is used.")
    p.add_argument("--sleep", type=float, default=2.0,
                   help="Seconds to sleep between windows (default: 2.0)")
    return p.parse_args()

def to_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()

def windows(start_d: date, end_d: date) -> Tuple[date, date]:
    """Yield [win_start, win_end) windows up to MAX_WINDOW_DAYS."""
    cur = start_d
    while cur < end_d:
        nxt = min(cur + timedelta(days=MAX_WINDOW_DAYS), end_d)
        yield cur, nxt
        cur = nxt

def main():
    args = parse_args()

    # Resolve date range
    if args.day:
        start_d = to_date(args.day)
        end_d = start_d + timedelta(days=1)  # exclusive
    elif args.start and args.end:
        start_d = to_date(args.start)
        end_d = to_date(args.end)
    else:
        # default: yesterday
        end_d = date.today()
        start_d = end_d - timedelta(days=1)

    if start_d >= end_d:
        print({"error": "Invalid date range: start must be before end",
               "start": start_d.isoformat(), "end": end_d.isoformat()})
        sys.exit(2)

    app = create_app()

    total_metrics = 0
    total_chunks = 0
    all_errors = []

    with app.app_context():
        # Sanity: user exists & active?
        u = db.session.get(User, args.user_id)
        if not u:
            print({"error": f"User {args.user_id} not found."})
            sys.exit(1)
        if hasattr(u, "is_active") and not u.is_active:
            print({"error": f"User {args.user_id} is inactive."})
            sys.exit(1)

        print(f"Backfill: user={args.user_id}  {start_d.isoformat()} → {end_d.isoformat()}")

        # Break the whole range into <=90d windows; each window is internally chunked to 7d by backfill_user_data
        for win_start, win_end in windows(start_d, end_d):
            res = backfill_user_data(
                args.user_id,
                win_start.isoformat(),
                win_end.isoformat()
            )
            # Print each window’s outcome
            print({"window": [win_start.isoformat(), win_end.isoformat()], **res})

            if res.get("success"):
                total_metrics += int(res.get("total_metrics_processed", 0))
                total_chunks  += int(res.get("chunks_processed", 0))
                if res.get("errors"):
                    all_errors.extend(res["errors"])
            else:
                all_errors.append({"date_range": f"{win_start}..{win_end}", "error": res.get("error", "unknown")})

            # Respect rate limits between windows
            time.sleep(max(0.0, float(args.sleep)))

    # Final summary
    summary = {
        "success": True,
        "user_id": args.user_id,
        "date_range": {"start": start_d.isoformat(), "end": end_d.isoformat()},
        "total_metrics_processed": total_metrics,
        "windows_processed": len(list(windows(start_d, end_d))),
        "chunks_processed": total_chunks,
        "errors": all_errors,
        "completed_at": datetime.utcnow().isoformat()
    }
    print(summary)

if __name__ == "__main__":
    main()
