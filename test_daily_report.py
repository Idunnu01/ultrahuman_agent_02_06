#!/usr/bin/env python3
"""
Test daily report generation locally
"""

import sys
import os
from datetime import datetime, date

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_daily_report_generation():
    """Test daily report generation for your user"""

    print("🧪 Testing Daily Report Generation")
    print("="*50)

    try:
        from app import create_app
        from app.models import User, DailyReport
        from tasks.daily_report import generate_daily_report
        from utils.database import db

        app = create_app()

        with app.app_context():
            print(f"✅ App context established")

            # Test with your user
            user_id = 'user_7000'
            user = User.query.filter_by(id=user_id).first()

            if not user:
                print(f"❌ User {user_id} not found")
                return False

            print(f"✅ Found user: {user.id}")
            print(f"   Phone: {user.phone_number}")
            print(f"   Active: {user.is_active}")

            # Check existing reports
            today = date.today()
            existing_report = DailyReport.query.filter_by(
                user_id=user_id,
                report_date=today
            ).first()

            if existing_report:
                print(f"📊 Existing report found for today:")
                print(f"   Report ID: {existing_report.id}")
                print(f"   Generated: {existing_report.generated_at}")
                print(f"   SMS sent: {existing_report.sms_sent}")

                # Show report content preview
                insights = existing_report.insights or {}
                if insights:
                    print(f"   Insights preview: {str(insights)[:100]}...")

                return True

            # Generate new report
            print(f"🔄 Generating new daily report for {user_id}...")

            result = generate_daily_report(user_id)

            print(f"\n📊 Generation Result:")
            print(f"   Success: {result.get('success')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Report ID: {result.get('report_id')}")
            print(f"   Error: {result.get('error', 'None')}")

            if result.get('success'):
                # Fetch the generated report
                report_id = result.get('report_id')
                if report_id:
                    report = DailyReport.query.get(report_id)
                    if report:
                        print(f"\n✅ Report Generated Successfully!")
                        print(f"   Insights: {len(report.insights or {})} items")
                        print(f"   SMS Content: {len(report.sms_content or '')} characters")

                        # Show SMS preview
                        if report.sms_content:
                            print(f"\n📱 SMS Preview:")
                            print(report.sms_content[:200] + "..." if len(report.sms_content) > 200 else report.sms_content)

                        return True

            print(f"❌ Report generation failed")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_report_data_availability():
    """Check if there's enough data for meaningful reports"""

    print("\n🔍 Checking Data Availability for Reports")
    print("="*50)

    try:
        from app import create_app
        from app.models import User, Metric
        from utils.database import db
        from datetime import datetime, timedelta

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            # Check recent data (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)

            recent_metrics = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.timestamp >= week_ago
            ).all()

            print(f"📊 Data Summary (last 7 days):")
            print(f"   Total metrics: {len(recent_metrics)}")

            # Group by type
            metric_types = {}
            for metric in recent_metrics:
                metric_type = metric.metric_type
                if metric_type not in metric_types:
                    metric_types[metric_type] = 0
                metric_types[metric_type] += 1

            print(f"   Unique metric types: {len(metric_types)}")

            for metric_type, count in sorted(metric_types.items()):
                print(f"     {metric_type}: {count} entries")

            # Check for lifestyle events
            lifestyle_events = [m for m in recent_metrics if any(keyword in m.metric_type for keyword in ['intake', 'consumption', 'timing', 'activity'])]

            print(f"\n🍽️ Lifestyle Events: {len(lifestyle_events)}")

            return len(recent_metrics) > 0

    except Exception as e:
        print(f"❌ Error checking data: {str(e)}")
        return False

if __name__ == '__main__':
    print(f"Starting daily report test at {datetime.now()}")

    # Check data first
    has_data = test_report_data_availability()

    if has_data:
        # Test report generation
        success = test_daily_report_generation()

        if success:
            print(f"\n🎉 Daily report testing successful!")
            print(f"Your 4:00 AM reports should work properly.")
        else:
            print(f"\n🔧 Daily report testing failed - needs debugging.")
    else:
        print(f"\n⚠️ Not enough data for meaningful reports yet.")
        print(f"Continue logging lifestyle events for better reports.")