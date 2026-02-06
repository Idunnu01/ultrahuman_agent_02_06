#!/usr/bin/env python3
"""
Check Current Database Structure and Available Data
Compare with old system's comprehensive metric mapping
"""

import sys
import os
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.append('.')

def check_database_structure():
    """Check what's currently in the database"""

    print("🔍 CHECKING CURRENT DATABASE STRUCTURE")
    print("=" * 60)

    try:
        from app import create_app
        from app.models import User, Metric, SystemLog
        from utils.database import db
        from sqlalchemy import text

        # Create Flask app context
        app = create_app()

        with app.app_context():
            print("✅ Flask app context created")

            # 1. Check Users
            print("\n👥 USERS:")
            users = User.query.all()
            print(f"Total users: {len(users)}")
            for user in users[:5]:  # Show first 5
                print(f"  - {user.id}: {user.phone_number} (onboarded: {user.onboarded_at})")

            # 2. Check Metrics - General Stats
            print("\n📊 METRICS OVERVIEW:")
            total_metrics = Metric.query.count()
            print(f"Total metric records: {total_metrics}")

            # 3. Check what metric types exist
            print("\n📋 AVAILABLE METRIC TYPES:")
            metric_types = db.session.query(Metric.metric_type).distinct().all()
            metric_types = [m[0] for m in metric_types]
            print(f"Found {len(metric_types)} metric types:")
            for metric_type in sorted(metric_types):
                count = Metric.query.filter_by(metric_type=metric_type).count()
                print(f"  - {metric_type}: {count} records")

            # 4. Check recent data for each metric type
            print(f"\n🕐 RECENT DATA (last 7 days):")
            week_ago = datetime.now() - timedelta(days=7)

            for metric_type in sorted(metric_types):
                recent_count = Metric.query.filter(
                    Metric.metric_type == metric_type,
                    Metric.timestamp >= week_ago
                ).count()

                if recent_count > 0:
                    latest = Metric.query.filter_by(metric_type=metric_type).order_by(
                        Metric.timestamp.desc()
                    ).first()

                    print(f"  - {metric_type}: {recent_count} records (latest: {latest.value} on {latest.timestamp.date()})")
                else:
                    print(f"  - {metric_type}: No recent data")

            # 5. Check data distribution by user
            print(f"\n👤 DATA BY USER:")
            if users:
                for user in users[:3]:  # Check first 3 users
                    user_metrics = Metric.query.filter_by(user_id=user.id).count()
                    if user_metrics > 0:
                        print(f"\n  User {user.id} ({user.phone_number}):")

                        user_metric_types = db.session.query(Metric.metric_type).filter_by(
                            user_id=user.id
                        ).distinct().all()

                        for metric_type, in user_metric_types:
                            count = Metric.query.filter_by(
                                user_id=user.id,
                                metric_type=metric_type
                            ).count()

                            latest = Metric.query.filter_by(
                                user_id=user.id,
                                metric_type=metric_type
                            ).order_by(Metric.timestamp.desc()).first()

                            if latest:
                                print(f"    - {metric_type}: {count} records (latest: {latest.value} on {latest.timestamp.date()})")
                    else:
                        print(f"  User {user.id}: No metrics data")

            # 6. Check database schema
            print(f"\n🗄️ DATABASE SCHEMA:")

            # Get table info
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Tables: {tables}")

            # Check Metric table structure
            print(f"\n📋 METRICS TABLE STRUCTURE:")
            if 'metrics' in table_names:
                columns = inspector.get_columns('metrics')
                for col in columns:
                    print(f"  - {col['name']}: {col['type']} {'(nullable)' if col['nullable'] else '(required)'}")
            else:
                print("  ❌ metrics table not found")

            # 7. Compare with old system
            print(f"\n🔄 COMPARISON WITH OLD SYSTEM:")

            old_system_metrics = [
                "steps", "movement_index", "recovery_index", "hrv", "sleep_rhr",
                "avg_sleep_hrv", "vo2_max", "night_rhr", "temp", "hr", "active_minutes",
                "total_sleep_seconds", "sleep_efficiency", "sleep_score", "avg_hrv",
                "deep_sleep", "light_sleep", "rem_sleep", "glucose", "hba1c"
            ]

            current_metrics = set(metric_types)
            old_metrics = set(old_system_metrics)

            common_metrics = current_metrics.intersection(old_metrics)
            missing_metrics = old_metrics - current_metrics
            new_metrics = current_metrics - old_metrics

            print(f"  ✅ Common metrics: {len(common_metrics)}")
            for metric in sorted(common_metrics):
                print(f"    - {metric}")

            print(f"  ❌ Missing from old system: {len(missing_metrics)}")
            for metric in sorted(missing_metrics):
                print(f"    - {metric}")

            print(f"  🆕 New in current system: {len(new_metrics)}")
            for metric in sorted(new_metrics):
                print(f"    - {metric}")

            return {
                'users': len(users),
                'total_metrics': total_metrics,
                'metric_types': metric_types,
                'recent_data_available': recent_count > 0,
                'tables': tables
            }

    except Exception as e:
        print(f"❌ Database check failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def check_aggregation_capability():
    """Check if current aggregation methods work"""

    print(f"\n🧮 TESTING CURRENT AGGREGATION METHODS")
    print("=" * 50)

    try:
        from app import create_app
        from services.metrics_service import MetricsService
        from app.models import User

        app = create_app()

        with app.app_context():
            metrics_service = MetricsService()

            # Get a test user
            user = User.query.first()
            if not user:
                print("❌ No users found in database")
                return

            print(f"Testing with user: {user.id}")

            # Test different metrics and aggregations
            test_cases = [
                ("heart_rate", "average", "2025-08-25", "2025-09-04"),
                ("hrv", "average", "2025-08-25", "2025-09-04"),
                ("sleep_score", "average", "2025-08-25", "2025-09-04"),
                ("temperature", "average", "2025-08-25", "2025-09-04"),
                ("recovery", "max", "2025-08-25", "2025-09-04"),
            ]

            print(f"\n🧪 TESTING AGGREGATIONS:")
            for metric_key, agg, start_date, end_date in test_cases:
                try:
                    result = metrics_service.fetch_metrics_aggregate(
                        user.id, metric_key, agg, start_date, end_date
                    )

                    if result is not None:
                        print(f"  ✅ {metric_key} ({agg}): {result}")
                    else:
                        print(f"  ❌ {metric_key} ({agg}): No data")

                except Exception as e:
                    print(f"  ❌ {metric_key} ({agg}): Error - {str(e)}")

    except Exception as e:
        print(f"❌ Aggregation test failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 DATABASE STRUCTURE & DATA CHECK")
    print("=" * 70)

    db_info = check_database_structure()

    if db_info:
        check_aggregation_capability()

        print(f"\n📋 SUMMARY:")
        print(f"  - Users: {db_info['users']}")
        print(f"  - Total metrics: {db_info['total_metrics']}")
        print(f"  - Metric types: {len(db_info['metric_types'])}")
        print(f"  - Database tables: {len(db_info['tables'])}")

        if db_info['total_metrics'] > 0:
            print(f"\n✅ Database has data - ready for enhancement!")
        else:
            print(f"\n⚠️ Database appears empty - may need data ingestion first")
    else:
        print(f"\n❌ Database check failed - check connection and models")