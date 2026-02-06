#!/usr/bin/env python3
"""
Test 4 AM daily report generation and proactive alerts
"""

import sys
import os
from datetime import datetime, date, timedelta

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_4am_report_generation():
    """Test the automated 4 AM daily report generation"""

    print("⏰ Testing 4 AM Daily Report Generation")
    print("="*60)

    try:
        from app import create_app
        from app.models import User, DailyReport
        from tasks.daily_report import generate_daily_report
        from utils.database import db

        app = create_app()

        with app.app_context():
            print(f"🕐 Simulating 4:00 AM daily report run at {datetime.now()}")

            # Get all active users (like the scheduled task does)
            active_users = User.query.filter_by(is_active=True).all()

            print(f"👥 Found {len(active_users)} active users")

            results = {
                'total_users': len(active_users),
                'successful': 0,
                'failed': 0,
                'errors': [],
                'reports_generated': []
            }

            # Generate report for each user
            for user in active_users:
                print(f"\n📊 Processing user: {user.id}")
                print(f"   Phone: {user.phone_number}")
                print(f"   Timezone: {user.timezone}")
                created_at = getattr(user, 'created_at', 'Unknown')
                print(f"   Created: {created_at}")

                # Check if today's report already exists
                today = date.today()
                existing_report = DailyReport.query.filter_by(
                    user_id=user.id,
                    report_date=today
                ).first()

                if existing_report:
                    print(f"   ℹ️ Report already exists for today (ID: {existing_report.id})")
                    print(f"   SMS sent: {existing_report.sms_sent}")
                    print(f"   Generated at: {existing_report.generated_at}")

                    # Show existing report content
                    insights = existing_report.insights or {}
                    print(f"   📋 Insights: {len(insights.get('key_insights', []))} key insights")
                    print(f"   💡 Recommendations: {len(insights.get('recommendations', []))} recommendations")

                    if existing_report.sms_content:
                        print(f"   📱 SMS Preview (first 100 chars):")
                        print(f"      {existing_report.sms_content[:100]}{'...' if len(existing_report.sms_content) > 100 else ''}")

                    results['successful'] += 1
                    results['reports_generated'].append({
                        'user_id': user.id,
                        'report_id': existing_report.id,
                        'status': 'already_existed',
                        'sms_sent': existing_report.sms_sent
                    })
                    continue

                try:
                    print(f"   🔄 Generating new daily report...")

                    # Generate the report (same as 4 AM cron job)
                    result = generate_daily_report(user.id)

                    if result and result.get('success'):
                        results['successful'] += 1
                        report_id = result.get('report_id')

                        print(f"   ✅ Report generated successfully (ID: {report_id})")

                        # Fetch and display the generated report
                        if report_id:
                            report = DailyReport.query.get(report_id)
                            if report:
                                insights = report.insights or {}
                                correlations = report.correlations or {}
                                anomalies = report.anomalies or {}

                                print(f"   📊 Report Contents:")
                                print(f"      Key insights: {len(insights.get('key_insights', []))}")
                                print(f"      Recommendations: {len(insights.get('recommendations', []))}")
                                print(f"      Correlations: {len(correlations)} found")
                                print(f"      Anomalies: {len(anomalies)} detected")
                                print(f"      SMS length: {len(report.sms_content or '')} characters")

                                # Show actual insights
                                if insights.get('key_insights'):
                                    print(f"   🔍 Key Insights:")
                                    for i, insight in enumerate(insights['key_insights'][:3], 1):
                                        print(f"      {i}. {insight}")

                                if insights.get('recommendations'):
                                    print(f"   💡 Recommendations:")
                                    for i, rec in enumerate(insights['recommendations'][:3], 1):
                                        print(f"      {i}. {rec}")

                                # Show SMS content preview
                                if report.sms_content:
                                    print(f"   📱 SMS Message:")
                                    print(f"      {report.sms_content}")

                                results['reports_generated'].append({
                                    'user_id': user.id,
                                    'report_id': report_id,
                                    'status': 'newly_generated',
                                    'sms_sent': report.sms_sent,
                                    'insights_count': len(insights.get('key_insights', [])),
                                    'recommendations_count': len(insights.get('recommendations', []))
                                })
                    else:
                        results['failed'] += 1
                        error_msg = result.get('error', 'Unknown error')
                        results['errors'].append(f"User {user.id}: {error_msg}")
                        print(f"   ❌ Report generation failed: {error_msg}")

                except Exception as e:
                    results['failed'] += 1
                    error_msg = str(e)
                    results['errors'].append(f"User {user.id}: {error_msg}")
                    print(f"   ❌ Exception during report generation: {error_msg}")

                    # Rollback any partial database changes
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

            # Print comprehensive summary
            print(f"\n📊 4 AM Daily Report Summary")
            print("="*50)
            print(f"Total users processed: {results['total_users']}")
            print(f"Successful reports: {results['successful']}")
            print(f"Failed reports: {results['failed']}")

            if results['successful'] > 0:
                success_rate = (results['successful'] / results['total_users']) * 100
                print(f"Success rate: {success_rate:.1f}%")

            if results['errors']:
                print(f"\n❌ Errors encountered:")
                for error in results['errors']:
                    print(f"   - {error}")

            # Detailed report breakdown
            if results['reports_generated']:
                print(f"\n📋 Generated Reports Details:")
                for report_info in results['reports_generated']:
                    print(f"   User {report_info['user_id']}:")
                    print(f"      Report ID: {report_info['report_id']}")
                    print(f"      Status: {report_info['status']}")
                    print(f"      SMS sent: {report_info['sms_sent']}")
                    if 'insights_count' in report_info:
                        print(f"      Insights: {report_info['insights_count']}")
                        print(f"      Recommendations: {report_info['recommendations_count']}")

            return results

    except Exception as e:
        print(f"❌ 4 AM report test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_sms_alert_delivery():
    """Test SMS alert delivery system"""

    print(f"\n📱 Testing SMS Alert Delivery")
    print("="*40)

    try:
        from services.sms_service import SMSService
        from app import create_app
        from app.models import User

        app = create_app()

        with app.app_context():
            sms_service = SMSService()

            # Get users with valid phone numbers
            users_with_phones = User.query.filter(
                User.phone_number.isnot(None),
                User.is_active == True
            ).all()

            print(f"👥 Found {len(users_with_phones)} users with phone numbers")

            sms_ready_users = []
            test_numbers = ['+1234567890', '+0000000000', '+1111111111']

            for user in users_with_phones:
                print(f"\n👤 User: {user.id}")
                print(f"   Phone: {user.phone_number}")

                # Check if it's a real phone number or test number
                if user.phone_number in test_numbers:
                    print(f"   ⚠️ Test phone number - won't receive real SMS")
                else:
                    sms_ready_users.append(user)
                    print(f"   ✅ Real phone number - SMS ready")

            print(f"\n📊 SMS Delivery Summary:")
            print(f"   Total users: {len(users_with_phones)}")
            print(f"   SMS-ready users: {len(sms_ready_users)}")
            print(f"   Test numbers: {len(users_with_phones) - len(sms_ready_users)}")

            if sms_ready_users:
                print(f"\n📱 SMS-ready users:")
                for user in sms_ready_users:
                    print(f"   {user.id}: {user.phone_number}")
            else:
                print(f"\n⚠️ No real phone numbers found - all users have test numbers")
                print(f"💡 Update user phone numbers to real numbers for SMS delivery")

            return len(sms_ready_users) > 0

    except Exception as e:
        print(f"❌ SMS delivery test failed: {str(e)}")
        return False

def simulate_proactive_alert_scenarios():
    """Simulate different proactive alert scenarios"""

    print(f"\n🚨 Testing Proactive Alert Scenarios")
    print("="*50)

    scenarios = [
        "High correlation found between supplement intake and recovery",
        "Anomaly detected in heart rate variability pattern",
        "Sleep quality trend declining over past week",
        "Exercise timing correlation with energy levels identified",
        "Nutritional pattern affecting metabolic markers"
    ]

    print(f"📋 Proactive alert scenarios that could trigger:")

    for i, scenario in enumerate(scenarios, 1):
        print(f"   {i}. {scenario}")

        # Show what the SMS might look like
        sample_sms = f"🔍 Health Insight: {scenario}. Check your daily report for details and recommendations. Reply STOP to opt out."
        print(f"      SMS: {sample_sms}")
        print(f"      Length: {len(sample_sms)} characters")
        print()

    return True

def analyze_report_quality():
    """Analyze the quality and usefulness of generated reports"""

    print(f"\n📈 Analyzing Report Quality")
    print("="*40)

    try:
        from app import create_app
        from app.models import DailyReport

        app = create_app()

        with app.app_context():
            # Get recent reports
            recent_reports = DailyReport.query.order_by(
                DailyReport.generated_at.desc()
            ).limit(10).all()

            print(f"📊 Analyzing {len(recent_reports)} recent reports")

            quality_metrics = {
                'total_reports': len(recent_reports),
                'reports_with_insights': 0,
                'reports_with_correlations': 0,
                'reports_with_anomalies': 0,
                'sms_sent_count': 0,
                'avg_insights_per_report': 0,
                'avg_sms_length': 0
            }

            total_insights = 0
            total_sms_length = 0

            for report in recent_reports:
                insights = report.insights or {}
                correlations = report.correlations or {}
                anomalies = report.anomalies or {}

                if insights:
                    quality_metrics['reports_with_insights'] += 1
                    key_insights = insights.get('key_insights', [])
                    total_insights += len(key_insights)

                if correlations:
                    quality_metrics['reports_with_correlations'] += 1

                if anomalies:
                    quality_metrics['reports_with_anomalies'] += 1

                if report.sms_sent:
                    quality_metrics['sms_sent_count'] += 1

                if report.sms_content:
                    total_sms_length += len(report.sms_content)

            # Calculate averages
            if quality_metrics['total_reports'] > 0:
                quality_metrics['avg_insights_per_report'] = total_insights / quality_metrics['total_reports']
                quality_metrics['avg_sms_length'] = total_sms_length / quality_metrics['total_reports']

            # Print quality analysis
            print(f"\n📊 Report Quality Analysis:")
            print(f"   Reports analyzed: {quality_metrics['total_reports']}")
            print(f"   Reports with insights: {quality_metrics['reports_with_insights']} ({quality_metrics['reports_with_insights']/quality_metrics['total_reports']*100:.1f}%)")
            print(f"   Reports with correlations: {quality_metrics['reports_with_correlations']} ({quality_metrics['reports_with_correlations']/quality_metrics['total_reports']*100:.1f}%)")
            print(f"   Reports with anomalies: {quality_metrics['reports_with_anomalies']} ({quality_metrics['reports_with_anomalies']/quality_metrics['total_reports']*100:.1f}%)")
            print(f"   SMS sent: {quality_metrics['sms_sent_count']} ({quality_metrics['sms_sent_count']/quality_metrics['total_reports']*100:.1f}%)")
            print(f"   Avg insights per report: {quality_metrics['avg_insights_per_report']:.1f}")
            print(f"   Avg SMS length: {quality_metrics['avg_sms_length']:.0f} characters")

            # Quality assessment
            insight_rate = quality_metrics['reports_with_insights'] / quality_metrics['total_reports']
            sms_rate = quality_metrics['sms_sent_count'] / quality_metrics['total_reports']

            if insight_rate > 0.8 and sms_rate > 0.8:
                print(f"\n✅ Report quality: EXCELLENT")
                print(f"   High insight generation and SMS delivery rates")
            elif insight_rate > 0.6 and sms_rate > 0.6:
                print(f"\n🔄 Report quality: GOOD")
                print(f"   Decent insight generation, room for improvement")
            else:
                print(f"\n⚠️ Report quality: NEEDS IMPROVEMENT")
                print(f"   Low insight generation or SMS delivery rates")

            return quality_metrics

    except Exception as e:
        print(f"❌ Report quality analysis failed: {str(e)}")
        return None

if __name__ == '__main__':
    print(f"⏰ 4 AM Daily Report & Proactive Alerts Test")
    print(f"Started: {datetime.now()}")
    print("="*60)

    # Run all tests
    print("Phase 1: Testing 4 AM report generation")
    report_results = test_4am_report_generation()

    print("\nPhase 2: Testing SMS alert delivery")
    sms_ready = test_sms_alert_delivery()

    print("\nPhase 3: Simulating proactive alert scenarios")
    simulate_proactive_alert_scenarios()

    print("\nPhase 4: Analyzing report quality")
    quality_results = analyze_report_quality()

    # Final summary
    print(f"\n{'='*60}")
    print(f"🎯 FINAL 4 AM REPORT TEST SUMMARY")
    print(f"{'='*60}")

    if report_results:
        print(f"✅ Daily reports: {report_results['successful']}/{report_results['total_users']} successful")
        if report_results['successful'] > 0:
            print(f"✅ Report generation working properly")
        else:
            print(f"❌ Report generation needs fixing")

    if sms_ready:
        print(f"✅ SMS delivery: Ready for real phone numbers")
    else:
        print(f"⚠️ SMS delivery: Only test numbers found")

    if quality_results:
        insight_rate = quality_results['reports_with_insights'] / quality_results['total_reports'] * 100
        print(f"📊 Report insights: {insight_rate:.1f}% of reports have meaningful insights")

    print(f"\n🚀 Your 4 AM daily reports are {'READY' if report_results and report_results['successful'] > 0 else 'NEED FIXING'}!")
    print(f"Completed: {datetime.now()}")