#!/usr/bin/env python3
"""
Comprehensive Data Sync Fix - Diagnose and resolve sync issues
"""

import sys
import os
from datetime import datetime, timedelta

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def fix_data_sync():
    """Diagnose and fix data sync issues"""

    print("🔧 COMPREHENSIVE DATA SYNC FIX")
    print("=" * 60)

    from app import create_app
    from app.models import Metric
    from tasks.data_ingestion import sync_ultrahuman_data
    from services.metrics_service import MetricsService
    from sqlalchemy import desc

    app = create_app()

    with app.app_context():
        user_id = 'user_7000'

        print("1️⃣ CHECKING CURRENT DATA STATUS")
        print("-" * 40)

        # Get most recent data
        most_recent = Metric.query.filter(
            Metric.user_id == user_id
        ).order_by(desc(Metric.timestamp)).first()

        if most_recent:
            hours_since = (datetime.utcnow() - most_recent.timestamp).total_seconds() / 3600
            print(f"   📊 Most recent data: {most_recent.metric_type}")
            print(f"   🕐 Timestamp: {most_recent.timestamp}")
            print(f"   ⏰ Age: {hours_since:.1f} hours ago")

        # Check last 24h data count
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_count = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.timestamp >= last_24h
        ).count()
        print(f"   📈 Metrics in last 24h: {recent_count}")

        print(f"\n2️⃣ RUNNING MANUAL SYNC (3 days)")
        print("-" * 40)

        try:
            sync_result = sync_ultrahuman_data(user_id, days_back=3)
            print(f"   ✅ Sync completed!")
            print(f"   📊 Result: {sync_result}")

            if sync_result.get('metrics_inserted', 0) > 0:
                print(f"   🎉 NEW DATA: {sync_result['metrics_inserted']} metrics added")
            else:
                print(f"   ⚠️ No new data inserted")

        except Exception as e:
            print(f"   ❌ Sync failed: {str(e)}")
            print(f"   🔍 This may indicate API or connection issues")

        print(f"\n3️⃣ TESTING ULTRAHUMAN API DIRECTLY")
        print("-" * 40)

        try:
            metrics_service = MetricsService()

            # Test API fetch
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)

            print(f"   🌐 Testing API fetch for last 24 hours...")
            api_result = metrics_service.fetch_ultrahuman_data(user_id, start_date, end_date)

            if 'error' in api_result:
                print(f"   ❌ API Error: {api_result['error']}")
            else:
                print(f"   ✅ API responded successfully")

                # Check what metrics were returned
                metrics = api_result.get('metrics', {})
                for metric_type, data_points in metrics.items():
                    print(f"   📊 {metric_type}: {len(data_points)} points")

                if not any(len(points) > 0 for points in metrics.values()):
                    print(f"   ⚠️ API returned no data points")
                    print(f"   💡 This suggests:")
                    print(f"      • Device not syncing to Ultrahuman")
                    print(f"      • API permissions issue")
                    print(f"      • No activity in last 24h")

        except Exception as e:
            print(f"   ❌ API test failed: {str(e)}")

        print(f"\n4️⃣ CHECKING FOR DATA GAPS")
        print("-" * 40)

        # Check for gaps in key metrics
        key_metrics = ['heart_rate', 'hrv', 'temperature', 'steps']

        for metric in key_metrics:
            recent_data = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric,
                Metric.timestamp >= last_24h
            ).order_by(desc(Metric.timestamp)).limit(3).all()

            if recent_data:
                latest_time = recent_data[0].timestamp
                gap_hours = (datetime.utcnow() - latest_time).total_seconds() / 3600
                print(f"   📊 {metric}: {len(recent_data)} recent points, latest {gap_hours:.1f}h ago")
            else:
                print(f"   ❌ {metric}: No recent data")

        print(f"\n5️⃣ HOURLY SYNC DIAGNOSIS")
        print("-" * 40)

        # Check if the issue is with hourly sync logic
        print(f"   🔍 Analyzing why hourly sync says 'no new metrics'...")

        # Test the same date range as hourly sync
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        existing_today = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.timestamp >= datetime.combine(today, datetime.min.time())
        ).count()

        existing_yesterday = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.timestamp >= datetime.combine(yesterday, datetime.min.time()),
            Metric.timestamp < datetime.combine(today, datetime.min.time())
        ).count()

        print(f"   📅 Today's data points: {existing_today}")
        print(f"   📅 Yesterday's data points: {existing_yesterday}")

        if existing_today == 0 and existing_yesterday == 0:
            print(f"   💡 No recent data suggests device sync issue")
        elif existing_today > 100:
            print(f"   💡 Lots of today's data - hourly sync may be working")

        print(f"\n6️⃣ RECOMMENDATIONS")
        print("-" * 40)

        if most_recent and hours_since > 24:
            print(f"   🔧 IMMEDIATE ACTIONS:")
            print(f"   1. Check if your Ultrahuman device is syncing")
            print(f"   2. Open Ultrahuman app and force sync")
            print(f"   3. Verify API credentials are working")
            print(f"   4. Check device battery and connectivity")

        print(f"\n   ⚙️ MONITORING ACTIONS:")
        print(f"   1. Run this script daily to monitor sync health")
        print(f"   2. Check hourly sync logs for errors")
        print(f"   3. Set up alerts for data gaps > 6 hours")

        # Test SMS questions with current data
        print(f"\n7️⃣ TESTING SMS QUESTIONS WITH CURRENT DATA")
        print("-" * 40)

        try:
            from services.sms_health_analyzer import SMSHealthAnalyzer
            analyzer = SMSHealthAnalyzer()

            test_question = "What was my heart rate at 3am?"
            print(f"   🧪 Testing: '{test_question}'")

            response = analyzer.analyze_question(test_question, user_id)

            if "❌" not in response and "No data" not in response:
                print(f"   ✅ SMS questions work with current data!")
                print(f"   📱 Response preview: {response.split(chr(10))[0][:50]}...")
            else:
                print(f"   ⚠️ SMS questions need fresher data")

        except Exception as e:
            print(f"   ❌ SMS test failed: {str(e)}")

        print(f"\n🏁 SYNC FIX COMPLETED")
        print("=" * 60)

if __name__ == '__main__':
    fix_data_sync()