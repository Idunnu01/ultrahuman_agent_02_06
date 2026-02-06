#!/usr/bin/env python3
"""
Show just the latest 4 AM report content - memory efficient
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def show_latest_report():
    """Show just the most recent report to avoid memory issues"""

    try:
        from app import create_app
        from app.models import DailyReport

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            print("📋 LATEST 4 AM REPORT for user_7000")
            print("=" * 50)

            # Get just the most recent report by ID (most efficient)
            latest_report = DailyReport.query.filter_by(
                user_id=user_id
            ).order_by(DailyReport.id.desc()).first()

            if not latest_report:
                print(f"❌ No reports found for {user_id}")
                return False

            print(f"📊 Report ID: {latest_report.id}")
            print(f"📅 Generated: {latest_report.generated_at}")
            print(f"📱 SMS Status: {'✅ SENT' if latest_report.sms_sent else '❌ NOT SENT'}")

            # Show the actual SMS content (this is what goes out at 4 AM)
            if latest_report.sms_content:
                print(f"\n📱 4 AM SMS MESSAGE ({len(latest_report.sms_content)} chars):")
                print("=" * 60)
                print(latest_report.sms_content)
                print("=" * 60)

                # SMS analysis
                if len(latest_report.sms_content) > 160:
                    parts = (len(latest_report.sms_content) + 159) // 160
                    print(f"📤 Will be sent as {parts} SMS parts")
                else:
                    print(f"📤 Single SMS message")
            else:
                print(f"\n❌ No SMS content in latest report")

            # Show insights summary (without complex parsing)
            if latest_report.insights:
                print(f"\n🧠 INSIGHTS INCLUDED:")
                insights = latest_report.insights

                if isinstance(insights, dict):
                    if 'key_insights' in insights:
                        key_insights = insights['key_insights']
                        print(f"   🔍 Key Insights: {len(key_insights)} found")
                        for i, insight in enumerate(key_insights[:3], 1):
                            print(f"      {i}. {insight}")

                    if 'recommendations' in insights:
                        recs = insights['recommendations']
                        print(f"   💡 Recommendations: {len(recs)} found")
                        for i, rec in enumerate(recs[:3], 1):
                            print(f"      {i}. {rec}")
                else:
                    print(f"   📋 Insights data type: {type(insights).__name__}")
            else:
                print(f"\n❌ No insights in latest report")

            # Show correlations count only
            if latest_report.correlations:
                if isinstance(latest_report.correlations, dict):
                    print(f"\n🔗 CORRELATIONS: {len(latest_report.correlations)} found")
                else:
                    print(f"\n🔗 CORRELATIONS: Data available")
            else:
                print(f"\n❌ No correlations in latest report")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def show_report_summary():
    """Quick summary without complex queries"""

    try:
        from app import create_app
        from app.models import DailyReport

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            # Simple count query
            total_count = DailyReport.query.filter_by(user_id=user_id).count()
            print(f"\n📊 SUMMARY:")
            print(f"   Total reports for {user_id}: {total_count}")

            return True

    except Exception as e:
        print(f"❌ Summary error: {str(e)}")
        return False

if __name__ == '__main__':
    success = show_latest_report()

    if success:
        show_report_summary()
        print(f"\n✅ This is what your 4 AM system generates!")
        print(f"💡 The SMS content above is exactly what would be sent to your phone")
    else:
        print(f"\n❌ Could not retrieve latest report")