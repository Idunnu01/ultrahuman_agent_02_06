#!/usr/bin/env python3
"""
Chunked historical backfill from December 2024 to present
Breaks large date ranges into 90-day chunks to respect API limits
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import User, Metric
from tasks.data_ingestion import backfill_user_data
from datetime import datetime, timedelta

def chunked_historical_backfill():
    app = create_app()
    with app.app_context():
        print("=" * 80)
        print("CHUNKED HISTORICAL BACKFILL - DECEMBER 2024 TO PRESENT")
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

        # Date range setup
        start_date = datetime.strptime("2024-12-01", "%Y-%m-%d").date()
        end_date = datetime.now().date()
        total_days = (end_date - start_date).days

        print(f"\nTotal date range:")
        print(f"  Start: {start_date}")
        print(f"  End: {end_date}")
        print(f"  Total days: {total_days}")

        # Calculate chunks (90 days each)
        chunk_size = 85  # Use 85 days to be safe
        chunks = []
        current_start = start_date

        while current_start < end_date:
            current_end = min(current_start + timedelta(days=chunk_size), end_date)
            chunks.append({
                'start': current_start.isoformat(),
                'end': current_end.isoformat(),
                'days': (current_end - current_start).days
            })
            current_start = current_end + timedelta(days=1)

        print(f"\nBreaking into {len(chunks)} chunks:")
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}: {chunk['start']} to {chunk['end']} ({chunk['days']} days)")

        print(f"\n" + "="*80)
        print("STARTING CHUNKED HISTORICAL BACKFILL")
        print("="*80)

        total_successful_chunks = 0
        total_failed_chunks = 0
        total_new_metrics = 0

        for user in users:
            print(f"\n🚀 Processing user: {user.id}")
            print("-" * 60)

            user_successful = 0
            user_failed = 0
            user_metrics = 0

            for i, chunk in enumerate(chunks, 1):
                print(f"\n  📅 Chunk {i}/{len(chunks)}: {chunk['start']} to {chunk['end']}")

                try:
                    result = backfill_user_data(user.id, chunk['start'], chunk['end'])

                    if result.get('success'):
                        metrics_processed = result.get('total_metrics_processed', 0)
                        user_metrics += metrics_processed
                        user_successful += 1
                        total_successful_chunks += 1

                        print(f"    ✅ SUCCESS: {metrics_processed:,} metrics")

                        # Show chunk errors if any
                        errors = result.get('errors', [])
                        if errors:
                            print(f"    ⚠️  {len(errors)} sub-chunk errors")

                    else:
                        user_failed += 1
                        total_failed_chunks += 1
                        error = result.get('error', 'Unknown error')
                        print(f"    ❌ FAILED: {error}")

                except Exception as e:
                    user_failed += 1
                    total_failed_chunks += 1
                    print(f"    ❌ EXCEPTION: {str(e)}")

                # Small delay between chunks to be nice to API
                if i < len(chunks):  # Don't delay after last chunk
                    import time
                    print(f"    😴 Waiting 5 seconds before next chunk...")
                    time.sleep(5)

            # User summary
            total_new_metrics += user_metrics
            print(f"\n  📊 User {user.id} Summary:")
            print(f"     Successful chunks: {user_successful}/{len(chunks)}")
            print(f"     Total metrics: {user_metrics:,}")

            if user_successful > 0:
                coverage = (user_successful / len(chunks)) * 100
                print(f"     Coverage: {coverage:.1f}%")

        # Final summary
        print("\n" + "=" * 80)
        print("CHUNKED HISTORICAL BACKFILL SUMMARY")
        print("=" * 80)

        total_metrics_after = Metric.query.count()
        actual_new_metrics = total_metrics_after - total_metrics_before

        print(f"Users processed: {len(users)}")
        print(f"Total chunks: {len(chunks) * len(users)}")
        print(f"Successful chunks: {total_successful_chunks}")
        print(f"Failed chunks: {total_failed_chunks}")
        print(f"Expected new metrics: {total_new_metrics:,}")
        print(f"Actual new metrics: {actual_new_metrics:,}")
        print(f"Database before: {total_metrics_before:,}")
        print(f"Database after: {total_metrics_after:,}")

        if actual_new_metrics > 0:
            growth_pct = (actual_new_metrics / max(total_metrics_before, 1)) * 100
            print(f"Growth: {actual_new_metrics:,} new metrics ({growth_pct:.1f}% increase)")

            avg_per_day = actual_new_metrics / total_days
            print(f"Average: {avg_per_day:.1f} metrics per day")

            success_rate = (total_successful_chunks / (len(chunks) * len(users))) * 100
            print(f"Success rate: {success_rate:.1f}%")

        print(f"\nDate range covered: {start_date} to {end_date} ({total_days} days)")

        if actual_new_metrics > 0:
            print("\n✅ Historical backfill completed!")
            print("\nYour system now has:")
            print(f"  • Historical data from December 2024")
            print(f"  • {total_metrics_after:,} total data points")
            print(f"  • Real-time granular data (not daily summaries)")
            print(f"  • {total_days} days of coverage")

            print("\nNext steps:")
            print("1. Update your cron job to: python test_data_sync.py")
            print("2. Monitor ongoing hourly collection")
            print("3. Enjoy comprehensive historical analytics!")

        else:
            print("\n❌ No new metrics collected.")
            print("Check API credentials and user configuration.")

        return total_successful_chunks, actual_new_metrics

if __name__ == "__main__":
    chunked_historical_backfill()