#!/usr/bin/env python3
"""
Test if your system properly handles duplicates without cleanup
Usage: python test_duplicates.py --user-id sample_user
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# Load environment
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from app import create_app
from app.models import Metric
from utils.database import db
from tasks.data_ingestion import backfill_user_data

def count_metrics_for_day(user_id: str, date_str: str) -> dict:
    """Count metrics for a specific day"""
    app = create_app()
    with app.app_context():
        # Parse date string to datetime range
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        metrics = db.session.query(Metric).filter(
            Metric.user_id == user_id,
            db.func.date(Metric.timestamp) == target_date
        ).all()

        by_type = {}
        for m in metrics:
            by_type[m.metric_type] = by_type.get(m.metric_type, 0) + 1

        return {
            "total": len(metrics),
            "by_type": by_type,
            "date": date_str
        }

def test_duplicate_prevention(user_id: str, test_date: str):
    """Test if re-running ingestion creates duplicates"""

    print(f"🧪 Testing Duplicate Prevention for {user_id} on {test_date}")
    print("=" * 60)

    # Step 1: Count metrics before re-ingestion
    print("1️⃣  Counting metrics BEFORE re-ingestion...")
    before_stats = count_metrics_for_day(user_id, test_date)

    if before_stats["total"] == 0:
        print(f"   ℹ️  No existing data for {test_date}. Running initial ingestion...")
    else:
        print(f"   📊 Found {before_stats['total']} existing metrics:")
        for metric_type, count in sorted(before_stats["by_type"].items()):
            print(f"      • {metric_type}: {count}")

    # Step 2: Run ingestion for the same day
    print(f"\n2️⃣  Running ingestion for {test_date}...")
    # backfill_user_data expects end_date to be exclusive, so add 1 day
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(test_date, "%Y-%m-%d")
    end_dt = start_dt + timedelta(days=1)
    end_date_str = end_dt.strftime("%Y-%m-%d")

    result = backfill_user_data(user_id, test_date, end_date_str)

    if not result.get("success"):
        print(f"   ❌ Ingestion failed: {result.get('error')}")
        return False

    print(f"   ✅ Ingestion completed: {result.get('total_metrics_processed', 0)} metrics processed")

    # Step 3: Count metrics after re-ingestion
    print("\n3️⃣  Counting metrics AFTER re-ingestion...")
    after_stats = count_metrics_for_day(user_id, test_date)

    print(f"   📊 Found {after_stats['total']} metrics:")
    for metric_type, count in sorted(after_stats["by_type"].items()):
        print(f"      • {metric_type}: {count}")

    # Step 4: Compare results
    print(f"\n4️⃣  Duplicate Analysis:")
    print(f"   Records before: {before_stats['total']}")
    print(f"   Records after:  {after_stats['total']}")

    if before_stats["total"] == 0:
        print("   ✅ Initial ingestion completed successfully")
        return True
    elif before_stats["total"] == after_stats["total"]:
        print("   ✅ NO DUPLICATES CREATED - Your upsert is working!")

        # Check if any new metric types were added
        old_types = set(before_stats["by_type"].keys())
        new_types = set(after_stats["by_type"].keys())
        added_types = new_types - old_types

        if added_types:
            print(f"   🎉 NEW METRIC TYPES ADDED: {', '.join(sorted(added_types))}")
            for metric_type in sorted(added_types):
                count = after_stats["by_type"][metric_type]
                print(f"      + {metric_type}: {count}")

        # Check if any counts changed (updates)
        updated_types = []
        for metric_type in old_types.intersection(new_types):
            if before_stats["by_type"][metric_type] != after_stats["by_type"][metric_type]:
                updated_types.append(metric_type)
                old_count = before_stats["by_type"][metric_type]
                new_count = after_stats["by_type"][metric_type]
                print(f"   🔄 UPDATED: {metric_type}: {old_count} → {new_count}")

        return True
    else:
        print(f"   ⚠️  POTENTIAL DUPLICATES: {after_stats['total'] - before_stats['total']} extra records")

        # Show which types increased
        for metric_type in after_stats["by_type"]:
            old_count = before_stats["by_type"].get(metric_type, 0)
            new_count = after_stats["by_type"][metric_type]
            if new_count > old_count:
                print(f"      📈 {metric_type}: {old_count} → {new_count} (+{new_count - old_count})")

        return False

def check_unique_constraints():
    """Check what unique constraints exist on the metrics table"""
    app = create_app()
    with app.app_context():
        # This would need to be customized based on your database setup
        try:
            result = db.session.execute("""
                SHOW INDEX FROM metrics WHERE Non_unique = 0
            """).fetchall()

            print("🔒 Unique Constraints on metrics table:")
            if result:
                for row in result:
                    print(f"   • {row}")
            else:
                print("   ⚠️  No unique constraints found")
                print("   💡 Consider adding: UNIQUE(user_id, metric_type, timestamp)")
        except Exception as e:
            print(f"   ❌ Could not check constraints: {e}")

def main():
    parser = argparse.ArgumentParser(description="Test duplicate prevention")
    parser.add_argument("--user-id", default="sample_user", help="User ID to test")
    parser.add_argument("--date", default="2023-12-22", help="Date to test (YYYY-MM-DD)")
    parser.add_argument("--check-constraints", action="store_true", help="Check database constraints")

    args = parser.parse_args()

    if args.check_constraints:
        check_unique_constraints()
        return

    # Test duplicate prevention
    success = test_duplicate_prevention(args.user_id, args.date)

    print(f"\n" + "=" * 60)
    if success:
        print("🎉 CONCLUSION: Your duplicate prevention is working!")
        print("💡 You can safely re-run ingestion without cleanup")
        print("   The new glucose metrics should be added automatically")
    else:
        print("⚠️  CONCLUSION: Duplicates may be created")
        print("💡 Consider cleanup before re-ingestion, or check your upsert logic")

if __name__ == "__main__":
    main()