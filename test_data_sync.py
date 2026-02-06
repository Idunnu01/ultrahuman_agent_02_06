#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import User, Metric
from tasks.data_ingestion import sync_ultrahuman_data

def test_data_sync():
    app = create_app()
    with app.app_context():
        # Check users
        users = User.query.all()
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"  - {user.id}: {user.preferences.get('name', 'No name')}")

        # Check existing metrics
        metrics = Metric.query.limit(10).all()
        print(f"\nFound {len(metrics)} existing metrics:")
        for metric in metrics:
            print(f"  - {metric.user_id}: {metric.metric_type} = {metric.value} ({metric.timestamp})")

        # Comprehensive backfill for all users
        print(f"\n" + "="*80)
        print("COMPREHENSIVE 90-DAY BACKFILL FOR ALL USERS")
        print("="*80)

        successful_syncs = 0
        total_new_metrics = 0

        for user in users:
            print(f"\n🚀 Processing user: {user.id}...")
            try:
                result = sync_ultrahuman_data(user.id, days_back=90)
                if result.get('success'):
                    metrics_inserted = result.get('metrics_inserted', 0)
                    total_new_metrics += metrics_inserted
                    successful_syncs += 1
                    print(f"✅ {user.id}: {metrics_inserted:,} metrics inserted")
                else:
                    print(f"❌ {user.id}: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"❌ {user.id}: Exception - {str(e)}")

        print(f"\n" + "="*80)
        print("BACKFILL SUMMARY")
        print("="*80)
        print(f"Successful syncs: {successful_syncs}/{len(users)}")
        print(f"Total new metrics: {total_new_metrics:,}")

        # Final metrics count
        final_metrics = Metric.query.limit(10).all()
        total_count = Metric.query.count()
        print(f"Total metrics now in database: {total_count:,}")

        print(f"\nSample of latest metrics:")
        for metric in final_metrics:
            print(f"  - {metric.user_id}: {metric.metric_type} = {metric.value} ({metric.timestamp})")

if __name__ == "__main__":
    test_data_sync()