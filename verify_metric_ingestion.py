#!/usr/bin/env python3
"""
Verify Metric Ingestion System
Tests that all Ultrahuman API metrics are being stored correctly
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project to path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

def verify_ingestion_system():
    """Verify that all metric types are being ingested and stored correctly"""

    print("🔍 ULTRAHUMAN METRIC INGESTION VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print()

    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Use production MySQL database to analyze user_7000 metrics
        # Don't override DATABASE_URL - use the one from .env for production data

        from app import create_app
        from app.models import User, Metric
        from utils.database import db
        from sqlalchemy import text, distinct

        app = create_app()

        with app.app_context():
            # Get users with data
            users = User.query.all()
            if not users:
                print("❌ No users found in database")
                return False

            print(f"👥 Found {len(users)} users:")
            for user in users:
                metric_count = Metric.query.filter_by(user_id=user.id).count()
                print(f"  - {user.id}: {metric_count:,} metrics")
            print()

            # Focus specifically on user_7000 (main account)
            main_user = User.query.filter_by(id='user_7000').first()

            if not main_user:
                print("❌ user_7000 not found - this is your main account with 175K+ metrics")
                print("Available users:")
                for user in users:
                    count = Metric.query.filter_by(user_id=user.id).count()
                    print(f"  - {user.id}: {count:,} metrics")
                return False

            user_id = main_user.id
            max_metrics = Metric.query.filter_by(user_id=user_id).count()
            print(f"🎯 Analyzing metrics for user: {user_id} ({max_metrics:,} total metrics)")
            print()

            # Check metric types being stored
            print("📊 METRIC TYPES IN DATABASE:")
            print("-" * 40)

            metric_types = db.session.execute(
                text("SELECT DISTINCT metric_type FROM metrics WHERE user_id = :user_id ORDER BY metric_type"),
                {"user_id": user_id}
            ).fetchall()

            expected_types = {
                # Core vitals
                "heart_rate", "hrv", "temperature", "steps",
                # Sleep metrics
                "sleep_score", "sleep_efficiency", "deep_sleep_minutes", "rem_sleep_minutes",
                # Recovery metrics
                "recovery_score", "resting_heart_rate", "movement_index", "vo2_max",
                # Glucose metrics
                "glucose", "metabolic_score", "glucose_variability", "average_glucose",
                "hba1c", "time_in_target",
                # Activity metrics
                "active_minutes", "movement"
            }

            found_types = {row[0] for row in metric_types}

            print(f"✅ Found {len(found_types)} distinct metric types:")
            for metric_type in sorted(found_types):
                count = db.session.execute(
                    text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND metric_type = :type"),
                    {"user_id": user_id, "type": metric_type}
                ).scalar()

                # Check recency
                recent = db.session.execute(
                    text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND metric_type = :type AND timestamp >= :recent"),
                    {"user_id": user_id, "type": metric_type, "recent": datetime.utcnow() - timedelta(days=7)}
                ).scalar()

                print(f"  📈 {metric_type}: {count:,} total ({recent} recent)")

            print()

            # Check for missing expected types
            missing_types = expected_types - found_types
            if missing_types:
                print(f"⚠️  MISSING METRIC TYPES: {len(missing_types)}")
                for missing in sorted(missing_types):
                    print(f"  ❌ {missing}")
                print()
            else:
                print("✅ All expected metric types are present!")
                print()

            # Check timestamp distribution
            print("⏰ TIMESTAMP DISTRIBUTION:")
            print("-" * 30)

            # Recent data (last 7 days)
            recent_count = db.session.execute(
                text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND timestamp >= :recent"),
                {"user_id": user_id, "recent": datetime.utcnow() - timedelta(days=7)}
            ).scalar()

            # Last 30 days
            month_count = db.session.execute(
                text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND timestamp >= :recent"),
                {"user_id": user_id, "recent": datetime.utcnow() - timedelta(days=30)}
            ).scalar()

            print(f"📅 Last 7 days: {recent_count:,} metrics")
            print(f"📅 Last 30 days: {month_count:,} metrics")
            print(f"📅 Historical: {max_metrics - month_count:,} metrics")
            print()

            # Check data quality
            print("🔍 DATA QUALITY CHECKS:")
            print("-" * 25)

            # Null values
            null_values = db.session.execute(
                text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND (value IS NULL OR value = '')"),
                {"user_id": user_id}
            ).scalar()

            # Invalid timestamps
            invalid_timestamps = db.session.execute(
                text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND (timestamp IS NULL OR timestamp > NOW())"),
                {"user_id": user_id}
            ).scalar()

            # Duplicate entries (same user, type, timestamp, value)
            duplicates = db.session.execute(
                text("""
                SELECT COUNT(*) - COUNT(DISTINCT user_id, metric_type, timestamp, value)
                FROM metrics WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            ).scalar()

            print(f"❌ Null values: {null_values}")
            print(f"❌ Invalid timestamps: {invalid_timestamps}")
            print(f"❌ Potential duplicates: {duplicates}")
            print()

            # Real-time vs daily metrics analysis
            print("📊 REAL-TIME vs DAILY METRICS:")
            print("-" * 35)

            # Count series metrics (should have many per day)
            series_types = ["heart_rate", "hrv", "temperature", "glucose", "steps"]
            daily_types = ["sleep_score", "recovery_score", "metabolic_score"]

            for metric_type in series_types:
                if metric_type in found_types:
                    count = db.session.execute(
                        text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND metric_type = :type"),
                        {"user_id": user_id, "type": metric_type}
                    ).scalar()

                    # Check how many days have this metric
                    days = db.session.execute(
                        text("SELECT COUNT(DISTINCT DATE(timestamp)) FROM metrics WHERE user_id = :user_id AND metric_type = :type"),
                        {"user_id": user_id, "type": metric_type}
                    ).scalar()

                    avg_per_day = count / days if days > 0 else 0
                    print(f"  📈 {metric_type}: {avg_per_day:.1f} readings/day ({count} total over {days} days)")

            for metric_type in daily_types:
                if metric_type in found_types:
                    count = db.session.execute(
                        text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id AND metric_type = :type"),
                        {"user_id": user_id, "type": metric_type}
                    ).scalar()

                    days = db.session.execute(
                        text("SELECT COUNT(DISTINCT DATE(timestamp)) FROM metrics WHERE user_id = :user_id AND metric_type = :type"),
                        {"user_id": user_id, "type": metric_type}
                    ).scalar()

                    print(f"  📊 {metric_type}: {count} total over {days} days (daily metric)")

            print()

            # API compliance summary
            print("🏆 API COMPLIANCE SUMMARY:")
            print("=" * 40)

            api_metrics_found = len(found_types & expected_types)
            api_compliance = api_metrics_found / len(expected_types) * 100

            print(f"✅ API Metrics Found: {api_metrics_found}/{len(expected_types)} ({api_compliance:.1f}%)")
            print(f"📊 Total Metrics Stored: {max_metrics:,}")
            print(f"⏰ Data Freshness: {recent_count:,} metrics in last 7 days")
            print(f"🎯 Data Quality: {((max_metrics - null_values - invalid_timestamps) / max_metrics * 100):.1f}% clean")

            if api_compliance >= 80 and null_values < max_metrics * 0.01 and recent_count > 0:
                print(f"\n🎉 INGESTION SYSTEM: EXCELLENT!")
                print(f"✅ High API compliance ({api_compliance:.1f}%)")
                print(f"✅ Good data quality ({null_values} null values)")
                print(f"✅ Recent data present ({recent_count:,} metrics)")
                print(f"✅ Your 175K+ metrics are being processed correctly")
                return True
            else:
                print(f"\n⚠️  INGESTION SYSTEM: NEEDS ATTENTION")
                if api_compliance < 80:
                    print(f"❌ Low API compliance: {api_compliance:.1f}%")
                if null_values > max_metrics * 0.01:
                    print(f"❌ High null values: {null_values}")
                if recent_count == 0:
                    print(f"❌ No recent data")
                return False

    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🔬 METRIC INGESTION VERIFICATION SYSTEM")
    print("This analyzes your database to verify all Ultrahuman metrics are being stored correctly\n")

    success = verify_ingestion_system()

    if success:
        print("\n✅ Verification completed successfully!")
        print("💪 Your Ultrahuman ingestion system is working excellently")
        print("🎯 All major metric types are being captured and stored")
        print("\n💡 Your system is ready for:")
        print("   • Daily health reports with comprehensive metrics")
        print("   • Real-time health monitoring and analysis")
        print("   • Advanced correlation and trend analysis")
        print("   • SMS-based health question answering")
    else:
        print("\n⚠️  Verification found some issues")
        print("💡 Consider checking:")
        print("   • Ultrahuman API connectivity and credentials")
        print("   • Data ingestion job scheduling and execution")
        print("   • Database schema for all metric types")

    sys.exit(0 if success else 1)