#!/usr/bin/env python3
"""
Check the date range of data in the MySQL database.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def check_data_range():
    """Check the date range of data in MySQL database"""

    print("=" * 60)
    print("CHECKING DATA RANGE IN MYSQL DATABASE")
    print("=" * 60)

    try:
        # Import after setting up path
        from app import create_app
        from app.models import User, Metric
        from utils.database import db
        from sqlalchemy import func

        # Create app context
        app = create_app()

        with app.app_context():
            user_id = "sample_user"

            print(f"User ID: {user_id}")
            print()

            # Get user
            user = User.query.filter_by(id=user_id).first()
            if not user:
                print(f"❌ User '{user_id}' not found in MySQL database")
                return False

            print(f"✅ Found user: {user.id}")
            print(f"   Ultrahuman ID: {user.ultrahuman_user_id}")
            print()

            # Get overall date range
            overall_range = db.session.query(
                func.min(Metric.timestamp).label('earliest'),
                func.max(Metric.timestamp).label('latest'),
                func.count(Metric.id).label('total_metrics')
            ).filter_by(user_id=user_id).first()

            print(f"📊 OVERALL DATA RANGE:")
            print(f"   Total metrics: {overall_range.total_metrics}")
            print(f"   Earliest data: {overall_range.earliest}")
            print(f"   Latest data: {overall_range.latest}")

            if overall_range.earliest and overall_range.latest:
                date_range = overall_range.latest - overall_range.earliest
                print(f"   Date span: {date_range.days} days")
            print()

            # Get date range by metric type
            print(f"📈 DATA RANGE BY METRIC TYPE:")

            metric_ranges = db.session.query(
                Metric.metric_type,
                func.min(Metric.timestamp).label('earliest'),
                func.max(Metric.timestamp).label('latest'),
                func.count(Metric.id).label('count')
            ).filter_by(user_id=user_id).group_by(Metric.metric_type).order_by(func.count(Metric.id).desc()).all()

            for metric_type, earliest, latest, count in metric_ranges:
                print(f"  {metric_type}:")
                print(f"    Count: {count} data points")
                print(f"    Range: {earliest} to {latest}")
                if earliest and latest:
                    date_span = (latest - earliest).days
                    print(f"    Span: {date_span} days")
                print()

            # Check recent data (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_metrics = db.session.query(
                Metric.metric_type,
                func.count(Metric.id).label('count')
            ).filter(
                Metric.user_id == user_id,
                Metric.timestamp >= thirty_days_ago
            ).group_by(Metric.metric_type).order_by(func.count(Metric.id).desc()).all()

            print(f"📅 RECENT DATA (Last 30 days):")
            total_recent = 0
            for metric_type, count in recent_metrics:
                print(f"  {metric_type}: {count} data points")
                total_recent += count
            print(f"  Total recent: {total_recent} data points")
            print()

            # Check data availability for correlation
            print(f"🔍 CORRELATION DATA AVAILABILITY:")

            # Check last 7 days for correlation
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            correlation_metrics = db.session.query(
                Metric.metric_type,
                func.count(Metric.id).label('count')
            ).filter(
                Metric.user_id == user_id,
                Metric.timestamp >= seven_days_ago,
                Metric.metric_type.in_(['temperature', 'sleep_score', 'heart_rate', 'hrv', 'recovery'])
            ).group_by(Metric.metric_type).all()

            correlation_data = {metric_type: count for metric_type, count in correlation_metrics}

            print(f"  Last 7 days:")
            for metric_type in ['temperature', 'sleep_score', 'heart_rate', 'hrv', 'recovery']:
                count = correlation_data.get(metric_type, 0)
                status = "✅" if count >= 3 else "❌"
                print(f"    {status} {metric_type}: {count} points")

            return True

    except Exception as e:
        print(f"❌ Error checking data range: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Data Range Check")
    print("=" * 60)

    success = check_data_range()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ Data range analysis complete")
        print("📊 You can now see the full scope of your data")
        print("🧪 Ready for correlation analysis testing")
    else:
        print("\n❌ Failed to check data range. Check the errors above.")

if __name__ == "__main__":
    main()
