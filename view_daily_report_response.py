#!/usr/bin/env python3
"""
View the actual daily report response that was generated and sent
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def view_latest_daily_report():
    """View the complete daily report response"""

    print("📋 VIEWING YOUR ACTUAL 4 AM DAILY REPORT")
    print("=" * 60)

    try:
        from app import create_app
        from app.models import DailyReport

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            # Get the latest report
            latest_report = DailyReport.query.filter_by(
                user_id=user_id
            ).order_by(DailyReport.id.desc()).first()

            if not latest_report:
                print(f"❌ No reports found for {user_id}")
                return False

            print(f"📊 Report Details:")
            print(f"   Report ID: {latest_report.id}")
            print(f"   Date: {latest_report.report_date}")
            print(f"   Generated: {latest_report.generated_at}")
            print(f"   SMS Sent: {'✅ YES' if latest_report.sms_sent else '❌ NO'}")
            if latest_report.sms_sent_at:
                print(f"   SMS Sent At: {latest_report.sms_sent_at}")

            # Show the SMS content that was actually sent
            print(f"\n📱 ACTUAL SMS SENT TO YOUR PHONE:")
            print("=" * 60)
            if latest_report.sms_content:
                print(latest_report.sms_content)
                print("=" * 60)
                print(f"Length: {len(latest_report.sms_content)} characters")

                # SMS parts calculation
                if len(latest_report.sms_content) > 160:
                    parts = (len(latest_report.sms_content) + 159) // 160
                    print(f"📤 Sent as {parts} SMS parts to {latest_report.user.phone_number}")
                else:
                    print(f"📤 Single SMS to {latest_report.user.phone_number}")
            else:
                print("❌ No SMS content found")

            # Show detailed insights
            if latest_report.insights:
                print(f"\n🧠 DETAILED INSIGHTS GENERATED:")
                print("-" * 40)
                insights = latest_report.insights

                if isinstance(insights, list):
                    for i, insight in enumerate(insights, 1):
                        if isinstance(insight, dict):
                            print(f"{i}. {insight.get('insight', insight)}")
                        else:
                            print(f"{i}. {insight}")
                elif isinstance(insights, dict):
                    if 'key_insights' in insights:
                        print("📍 Key Insights:")
                        for i, insight in enumerate(insights['key_insights'], 1):
                            print(f"   {i}. {insight}")

                    if 'recommendations' in insights:
                        print("\n💡 Recommendations:")
                        for i, rec in enumerate(insights['recommendations'], 1):
                            print(f"   {i}. {rec}")

                    if 'statistical_summary' in insights:
                        print("\n📊 Statistical Summary:")
                        stats = insights['statistical_summary']
                        for key, value in stats.items():
                            print(f"   {key}: {value}")
                else:
                    print(f"Raw insights: {insights}")

            # Show correlations found
            if latest_report.correlations:
                print(f"\n🔗 CORRELATIONS DISCOVERED:")
                print("-" * 40)
                correlations = latest_report.correlations

                if isinstance(correlations, dict):
                    for metric_pair, data in correlations.items():
                        if isinstance(data, dict):
                            correlation = data.get('correlation', 'N/A')
                            p_value = data.get('p_value', 'N/A')
                            sample_size = data.get('sample_size', 'N/A')
                            print(f"🔍 {metric_pair}:")
                            print(f"   Correlation: {correlation}")
                            print(f"   P-value: {p_value}")
                            print(f"   Sample size: {sample_size}")
                        else:
                            print(f"🔍 {metric_pair}: {data}")
                else:
                    print(f"Raw correlations: {correlations}")

            # Show trends
            if latest_report.trends:
                print(f"\n📈 TRENDS ANALYZED:")
                print("-" * 40)
                trends = latest_report.trends

                if isinstance(trends, dict):
                    for metric, trend_data in trends.items():
                        print(f"📊 {metric}:")
                        if isinstance(trend_data, dict):
                            for key, value in trend_data.items():
                                print(f"   {key}: {value}")
                        else:
                            print(f"   {trend_data}")
                else:
                    print(f"Raw trends: {trends}")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def view_recent_reports_summary():
    """View summary of recent reports"""

    print(f"\n📊 RECENT REPORTS SUMMARY:")
    print("-" * 40)

    try:
        from app import create_app
        from app.models import DailyReport

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            # Get last 5 reports
            recent_reports = DailyReport.query.filter_by(
                user_id=user_id
            ).order_by(DailyReport.id.desc()).limit(5).all()

            for report in recent_reports:
                status = "📱 SENT" if report.sms_sent else "❌ NOT SENT"
                sms_length = len(report.sms_content) if report.sms_content else 0
                print(f"📋 {report.report_date} | ID: {report.id} | {status} | {sms_length} chars")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = view_latest_daily_report()

    if success:
        view_recent_reports_summary()
        print(f"\n✅ This shows your actual 4 AM report!")
        print(f"📱 The SMS content above is exactly what was sent to your phone")
        print(f"🧠 The insights show the AI analysis behind the report")
    else:
        print(f"\n❌ Could not retrieve report details")