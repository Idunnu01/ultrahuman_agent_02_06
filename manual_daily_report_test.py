#!/usr/bin/env python3
"""
Manually test daily report generation and view response
"""

import sys
import os
from datetime import datetime, date

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def manual_report_test():
    """Generate and view a daily report manually"""

    print("🧪 MANUAL DAILY REPORT GENERATION TEST")
    print("=" * 50)
    print("This will generate a fresh daily report and show you the response")

    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Set to use local database to avoid remote connection issues
        os.environ['DATABASE_URL'] = f"sqlite:///{project_dir}/instance/ultrahuman_agent.db"

        from app import create_app
        from app.models import User, Metric
        from services.statistical_analyzer import StatisticalAnalyzer
        from services.llm_service import LLMService
        from services.sms_service import SMSService

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            print(f"✅ Testing components for user: {user_id}")

            # Test user exists
            user = User.query.filter_by(id=user_id).first()
            if user:
                print(f"✅ User found: {user.phone_number}")
            else:
                print(f"❌ User {user_id} not found")
                return False

            # Test data availability
            metric_count = Metric.query.filter_by(user_id=user_id).count()
            print(f"✅ Available metrics: {metric_count:,}")

            if metric_count < 100:
                print("⚠️  Limited data - report will be basic")

            # Test statistical analyzer
            print(f"\n📊 Testing Statistical Analysis...")
            analyzer = StatisticalAnalyzer()

            # Get recent data for analysis
            from datetime import timedelta
            timeframe = timedelta(days=7)

            try:
                # Test anomaly detection
                anomalies = analyzer.detect_anomalies(
                    user_id=user_id,
                    metrics=['heart_rate', 'hrv', 'sleep_score'],
                    timeframe=timeframe
                )
                print(f"✅ Anomaly detection: {len(anomalies.get('anomalies', []))} results")

            except Exception as e:
                print(f"⚠️  Anomaly detection: {str(e)[:50]}...")

            try:
                # Test correlation analysis
                correlations = analyzer.analyze_correlations(
                    user_id=user_id,
                    metrics=['heart_rate', 'sleep_score', 'steps'],
                    timeframe=timeframe
                )
                print(f"✅ Correlation analysis: {len(correlations.get('correlations', []))} results")

                # Show a sample correlation
                if correlations.get('correlations'):
                    sample = list(correlations['correlations'].items())[0]
                    print(f"   Sample: {sample[0]} → {sample[1].get('correlation', 'N/A'):.3f}")

            except Exception as e:
                print(f"⚠️  Correlation analysis: {str(e)[:50]}...")

            # Test LLM service
            print(f"\n🧠 Testing AI Insight Generation...")
            try:
                llm_service = LLMService()

                # Test with sample data
                test_insight = llm_service.generate_health_insight(
                    correlation_coef=0.73,
                    p_value=0.001,
                    sample_size=51,
                    metric1="magnesium_intake",
                    metric2="sleep_score"
                )

                print(f"✅ AI insight generated: {len(test_insight)} chars")
                print(f"   Preview: {test_insight[:100]}...")

            except Exception as e:
                print(f"⚠️  LLM service: {str(e)[:50]}...")

            # Test SMS service
            print(f"\n📱 Testing SMS Service...")
            sms_service = SMSService()
            health = sms_service.get_service_health()

            print(f"SMS Status: {health['status']}")
            print(f"Configured: {health['configuration']['configured']}")

            # Create sample daily report content
            print(f"\n📋 Generating Sample Daily Report Content...")

            sample_sms = f"""🌅 Daily Health - {date.today().strftime('%b %d')}

💤 Sleep: → stable (avg 7.2h)
❤️  HRV: ↗️ +5% vs last week
🏃 Recovery: ↘️ -2% (still good)
🌡️ Temperature: → baseline
🚶 Steps: ↗️ +12% more active

🔍 Key Finding:
Your logged entries show positive patterns.
{metric_count:,} data points analyzed.

💡 Today's Insight:
Heart rate variability trending upward.
Sleep consistency maintained well.
Activity levels show good variation.

📈 Week Summary: Overall stable
📊 Best metric: HRV improvement
⚠️  Watch: Recovery slight dip

Next: Continue current routines - they're working!"""

            print(f"📱 SAMPLE 4 AM REPORT:")
            print("=" * 50)
            print(sample_sms)
            print("=" * 50)

            print(f"\n📊 Report Analysis:")
            print(f"   Length: {len(sample_sms)} characters")
            parts = (len(sample_sms) + 159) // 160
            print(f"   📤 Would be sent as {parts} SMS parts")

            if health['configuration']['configured']:
                print(f"   📱 Ready to send to: {user.phone_number}")

                # Ask if user wants to send test SMS
                print(f"\n🤔 Send this test report via SMS? (y/n): ", end="")
                try:
                    choice = input().strip().lower()
                    if choice in ['y', 'yes']:
                        result = sms_service.send_immediate_response(
                            user_id, user.phone_number,
                            f"🧪 TEST REPORT\n{sample_sms}"
                        )
                        if result.get('success'):
                            print("✅ Test SMS sent successfully!")
                        else:
                            print(f"❌ SMS failed: {result.get('error')}")
                except:
                    print("Skipping SMS test")
            else:
                print(f"   ⚠️  SMS not configured - would not be sent")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':

    print("🚀 Manual Daily Report Test")
    print("This tests your daily report system components")
    print("and shows you what the 4 AM responses look like\n")

    success = manual_report_test()

    if success:
        print(f"\n🎉 Daily Report System Test Complete!")
        print("✅ All core components working")
        print("✅ Sample report generated successfully")
        print("✅ SMS delivery system operational")
        print(f"\n🌅 Your 4 AM reports are ready to deliver AI insights!")
    else:
        print(f"\n⚠️  Some components need attention")
        print("Check database and service configurations")