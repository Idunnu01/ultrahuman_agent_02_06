#!/usr/bin/env python3
"""
Historical backfill from December 2024 to present
Collects all available historical data with real-time granularity
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import User, Metric
from tasks.data_ingestion import backfill_user_data
from datetime import datetime, date

def historical_backfill():
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("COMPREHENSIVE HISTORICAL BACKFILL - DECEMBER 2024 TO PRESENT")
        print("=" * 80)

        # Get all users
        users = User.query.all()
        print(f"Found {len(users)} users:")
        for user in users:
            name = user.preferences.get('name', 'No name') if user.preferences else 'No name'
            print(f"  - {user.id}: {name}")

        # Current metrics count
        total_metrics_before = Metric.query.count()
        print(f"\nCurrent metrics count: {total_metrics_before:,}")

        # Date range for backfill
        start_date = "2024-12-01"  # December 1, 2024
        end_date = datetime.now().date().isoformat()  # Today

        print(f"\nBackfill date range:")
        print(f"  Start: {start_date}")
        print(f"  End: {end_date}")
        print(f"  Days: {(datetime.now().date() - datetime.strptime(start_date, '%Y-%m-%d').date()).days}")

        print(f"\n" + "="*80)
        print("STARTING HISTORICAL BACKFILL")
        print("="*80)

        successful_syncs = 0
        failed_syncs = 0
        total_new_metrics = 0

        for user in users:
            print(f"\n🚀 Processing user: {user.id}")
            print("-" * 60)

            try:
                print(f"Backfilling from {start_date} to {end_date}...")
                result = backfill_user_data(user.id, start_date, end_date)

                if result.get('success'):
                    metrics_processed = result.get('total_metrics_processed', 0)
                    total_new_metrics += metrics_processed
                    successful_syncs += 1

                    print(f"✅ SUCCESS: {user.id}")
                    print(f"   Metrics processed: {metrics_processed:,}")
                    print(f"   Chunks processed: {result.get('chunks_processed', 0)}")

                    errors = result.get('errors', [])
                    if errors:
                        print(f"   ⚠️  {len(errors)} chunk errors (partial data)")
                        for error in errors[:3]:  # Show first 3 errors
                            print(f"     - {error.get('date_range', '')}: {error.get('error', '')}")

                else:
                    failed_syncs += 1
                    error = result.get('error', 'Unknown error')
                    print(f"❌ FAILED: {user.id}")
                    print(f"   Error: {error}")

            except Exception as e:
                failed_syncs += 1
                print(f"❌ EXCEPTION: {user.id}")
                print(f"   Error: {str(e)}")
                import traceback
                traceback.print_exc()

        # Final summary
        print("\n" + "=" * 80)
        print("HISTORICAL BACKFILL SUMMARY")
        print("=" * 80)

        total_metrics_after = Metric.query.count()
        actual_new_metrics = total_metrics_after - total_metrics_before

        print(f"Users processed: {len(users)}")
        print(f"Successful syncs: {successful_syncs}")
        print(f"Failed syncs: {failed_syncs}")
        print(f"Expected new metrics: {total_new_metrics:,}")
        print(f"Actual new metrics: {actual_new_metrics:,}")
        print(f"Database before: {total_metrics_before:,}")
        print(f"Database after: {total_metrics_after:,}")

        if actual_new_metrics > 0:
            growth_pct = (actual_new_metrics / max(total_metrics_before, 1)) * 100
            print(f"Growth: {actual_new_metrics:,} new metrics ({growth_pct:.1f}% increase)")

        print(f"\nDate range covered: December 1, 2024 to {end_date}")
        days_covered = (datetime.now().date() - datetime.strptime(start_date, '%Y-%m-%d').date()).days
        if actual_new_metrics > 0:
            avg_per_day = actual_new_metrics / days_covered
            print(f"Average: {avg_per_day:.1f} metrics per day")

        if successful_syncs > 0:
            print("\n✅ Historical backfill completed successfully!")
            print("\nYour system now has:")
            print(f"  • Complete data from December 2024 to present")
            print(f"  • {total_metrics_after:,} total data points")
            print(f"  • Real-time granular data (not daily summaries)")
            print(f"  • {days_covered} days of historical coverage")

            print("\nNext steps:")
            print("1. Update your cron job to use test_data_sync.py")
            print("2. Monitor hourly collection going forward")
            print("3. Your analytics now have complete historical context!")

        else:
            print("\n❌ No successful backfills completed.")
            print("Check the errors above and your API credentials.")

        return successful_syncs, actual_new_metrics

if __name__ == "__main__":
    historical_backfill()