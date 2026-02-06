#!/usr/bin/env python3
"""
Check data ingestion status and available metrics
"""

import sys
import os
sys.path.append('.')

def check_data_status():
    """Check what data has been ingested and is available"""

    print("📊 CHECKING DATA INGESTION STATUS")
    print("=" * 50)

    from app import create_app
    from app.models import User, Metric
    from services.metrics_service import MetricsService
    from utils.database import db
    from datetime import datetime, timedelta

    app = create_app()

    with app.app_context():
        print("🔍 1. CHECKING USERS")
        print("-" * 20)

        users = db.session.query(User).all()
        print(f"Total users: {len(users)}")

        for user in users:
            print(f"👤 User: {user.id}")
            print(f"   📱 Phone: {user.phone_number}")
            print(f"   🆔 UH User ID: {user.ultrahuman_user_id}")
            print(f"   ⚡ Active: {user.is_active}")
            print()

        if not users:
            print("❌ No users found! You need to register a user first.")
            return

        # Check metrics for each user
        for user in users:
            print(f"📈 2. METRICS FOR USER: {user.id}")
            print("-" * 30)

            # Get metrics count by type
            metrics_query = db.session.query(
                Metric.metric_type,
                db.func.count(Metric.id).label('count'),
                db.func.min(Metric.timestamp).label('earliest'),
                db.func.max(Metric.timestamp).label('latest')
            ).filter(
                Metric.user_id == user.id
            ).group_by(Metric.metric_type).all()

            if not metrics_query:
                print(f"❌ No metrics found for user {user.id}")
                print("   💡 This explains why queries return 'no data'")
                print()
                continue

            print(f"✅ Found {len(metrics_query)} metric types:")

            for metric_type, count, earliest, latest in metrics_query:
                days_span = (latest - earliest).days if earliest and latest else 0
                print(f"   📊 {metric_type}:")
                print(f"      📈 Count: {count}")
                print(f"      🕐 Range: {earliest} → {latest}")
                print(f"      📅 Days: {days_span}")
                print()

            # Check recent metrics (last 7 days)
            print(f"🕐 3. RECENT METRICS (Last 7 days) - {user.id}")
            print("-" * 40)

            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_metrics = db.session.query(
                Metric.metric_type,
                db.func.count(Metric.id).label('count'),
                db.func.max(Metric.timestamp).label('latest')
            ).filter(
                Metric.user_id == user.id,
                Metric.timestamp >= recent_cutoff
            ).group_by(Metric.metric_type).all()

            if recent_metrics:
                print(f"✅ Recent data available ({len(recent_metrics)} types):")
                for metric_type, count, latest in recent_metrics:
                    hours_ago = (datetime.utcnow() - latest).total_seconds() / 3600
                    print(f"   📊 {metric_type}: {count} points (latest: {hours_ago:.1f}h ago)")
            else:
                print("❌ No recent metrics (last 7 days)")
                print("   💡 This explains the 'no data' responses")
            print()

            # Test metrics service
            print(f"🔧 4. TESTING METRICS SERVICE - {user.id}")
            print("-" * 35)

            metrics_service = MetricsService()

            # Test availability check
            try:
                availability = metrics_service.get_available_metrics_for_user(user.id, days_back=7)
                if 'error' in availability:
                    print(f"❌ Availability check failed: {availability['error']}")
                else:
                    available_metrics = availability.get('available_metrics', {})
                    print(f"✅ Available metrics: {list(available_metrics.keys())}")

                    for metric_name, info in available_metrics.items():
                        print(f"   📊 {metric_name}: {info['count']} points, {info['days_covered']} days")
            except Exception as e:
                print(f"❌ Availability check error: {e}")

            # Test specific metric query
            print(f"\n🎯 5. TESTING HEART RATE QUERY - {user.id}")
            print("-" * 35)

            try:
                # Test heart rate aggregation
                hr_result = metrics_service.fetch_metrics_aggregate(
                    user.id, 'heart_rate', 'average',
                    (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                    datetime.now().strftime("%Y-%m-%d")
                )

                if hr_result is not None:
                    print(f"✅ Heart rate average: {hr_result:.1f} bpm")
                else:
                    print("❌ No heart rate data found")

                    # Try enhanced lookup
                    enhanced_result = metrics_service.enhanced_lookup.fetch_metrics_aggregate_enhanced(
                        user.id, 'heart_rate', 'average',
                        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                        datetime.now().strftime("%Y-%m-%d")
                    )

                    if enhanced_result and enhanced_result.get('success'):
                        print(f"✅ Enhanced lookup found: {enhanced_result.get('value', 'N/A')}")
                    else:
                        print("❌ Enhanced lookup also failed")
                        print(f"   Debug: {enhanced_result}")

            except Exception as e:
                print(f"❌ Heart rate query failed: {e}")

            print()

        print("🔍 6. DATA SYNC RECOMMENDATIONS")
        print("-" * 35)

        if not any(len(users) > 0 and db.session.query(Metric).filter(Metric.user_id == user.id).first() for user in users):
            print("❌ NO DATA FOUND - Possible Issues:")
            print("   1. Ultrahuman API not configured")
            print("   2. Data sync never ran")
            print("   3. API credentials invalid")
            print("   4. User not properly registered")
            print()
            print("💡 Next Steps:")
            print("   1. Check environment variables (ULTRAHUMAN_API_KEY)")
            print("   2. Run manual data sync")
            print("   3. Check API connectivity")
        else:
            print("✅ Some data found - Check recent sync status")

        print("\n🏁 DATA STATUS CHECK COMPLETED")
        print("=" * 50)

if __name__ == "__main__":
    try:
        check_data_status()
    except Exception as e:
        print(f"\n💥 Data check failed: {e}")
        import traceback
        traceback.print_exc()