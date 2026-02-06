#!/usr/bin/env python3
"""
Check data in the MySQL database (PythonAnywhere).
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

def check_mysql_data():
    """Check data in MySQL database"""

    print("=" * 60)
    print("CHECKING MYSQL DATABASE (PYTHONANYWHERE)")
    print("=" * 60)

    try:
        # Import after setting up path
        from app import create_app
        from app.models import User, Metric
        from utils.database import db

        # Create app context
        app = create_app()

        with app.app_context():
            user_id = "sample_user"

            print(f"User ID: {user_id}")
            print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")
            print()

            # Get user
            user = User.query.filter_by(id=user_id).first()
            if not user:
                print(f"❌ User '{user_id}' not found in MySQL database")
                return False

            print(f"✅ Found user: {user.id}")
            print(f"   Ultrahuman ID: {user.ultrahuman_user_id}")
            print(f"   Phone: {user.phone_number}")
            print(f"   Active: {user.is_active}")
            print()

            # Get all metrics for this user
            metrics = Metric.query.filter_by(user_id=user_id).all()
            print(f"Total metrics in MySQL: {len(metrics)}")

            if len(metrics) == 0:
                print("❌ No metrics found in MySQL database")
                return False

            # Group metrics by type
            by_type = {}
            for metric in metrics:
                by_type.setdefault(metric.metric_type, []).append(metric)

            print(f"\nMetrics by type:")
            for metric_type, metric_list in by_type.items():
                print(f"  {metric_type}:")
                print(f"    Count: {len(metric_list)}")
                if metric_list:
                    values = [m.value for m in metric_list]
                    print(f"    Range: {min(values):.1f} - {max(values):.1f}")
                    print(f"    Average: {sum(values)/len(values):.1f}")
                    print(f"    Latest: {max(metric_list, key=lambda x: x.timestamp).timestamp}")

            # Check recent data (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_metrics = [m for m in metrics if m.timestamp >= seven_days_ago]

            print(f"\nRecent data (last 7 days): {len(recent_metrics)} metrics")

            # Check correlation readiness
            print(f"\nChecking data for correlation analysis:")

            # Temperature data
            temp_metrics = [m for m in recent_metrics if m.metric_type == 'temperature']
            print(f"  Temperature data (last 7 days): {len(temp_metrics)} points")

            # Sleep data
            sleep_metrics = [m for m in recent_metrics if m.metric_type == 'sleep_score']
            print(f"  Sleep data (last 7 days): {len(sleep_metrics)} points")

            # Heart rate data
            hr_metrics = [m for m in recent_metrics if m.metric_type == 'heart_rate']
            print(f"  Heart rate data (last 7 days): {len(hr_metrics)} points")

            print(f"\nCorrelation Analysis Readiness:")
            if len(temp_metrics) >= 3 and len(sleep_metrics) >= 3:
                print(f"  ✅ Temperature + Sleep: Ready for correlation")
                print(f"    Temperature: {len(temp_metrics)} points")
                print(f"    Sleep: {len(sleep_metrics)} points")
            else:
                print(f"  ❌ Temperature + Sleep: Not enough data for correlation")
                print(f"    Temperature: {len(temp_metrics)} points (need at least 3)")
                print(f"    Sleep: {len(sleep_metrics)} points (need at least 3)")

            if len(temp_metrics) >= 3 and len(hr_metrics) >= 3:
                print(f"  ✅ Temperature + Heart Rate: Ready for correlation")
                print(f"    Temperature: {len(temp_metrics)} points")
                print(f"    Heart Rate: {len(hr_metrics)} points")
            else:
                print(f"  ❌ Temperature + Heart Rate: Not enough data for correlation")
                print(f"    Temperature: {len(temp_metrics)} points (need at least 3)")
                print(f"    Heart Rate: {len(hr_metrics)} points (need at least 3)")

            return True

    except Exception as e:
        print(f"❌ Error checking MySQL data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("MySQL Database Check")
    print("=" * 60)

    success = check_mysql_data()

    if success:
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. ✅ Data found in MySQL database")
        print("2. 🧪 Test correlation analysis with your real data")
        print("3. 📱 Send SMS queries to test correlation insights")
    else:
        print("\n❌ Failed to check MySQL data. Check the errors above.")

if __name__ == "__main__":
    main()
