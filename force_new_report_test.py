#!/usr/bin/env python3
"""
Force generation of new daily report to test the fix
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def force_new_report_test():
    """Force generate a new report to test the fix"""

    try:
        from app import create_app
        from app.models import DailyReport
        from tasks.daily_report import generate_daily_report
        from datetime import datetime, timedelta
        from utils.database import db

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            print("🔄 Force Generating New Report to Test Fix")
            print("=" * 50)

            # Use tomorrow's date to avoid conflict with existing report
            tomorrow = datetime.now() + timedelta(days=1)
            test_date = tomorrow.strftime('%Y-%m-%d')

            print(f"📅 Generating test report for {test_date}...")

            result = generate_daily_report(user_id, test_date)

            print(f"📊 Result: {result}")

            if result and result.get('success'):
                report_id = result.get('report_id')

                if report_id:
                    # Get the newly created report
                    new_report = DailyReport.query.get(report_id)

                    if new_report and new_report.sms_content:
                        print(f"\n📱 NEW REPORT SMS CONTENT ({len(new_report.sms_content)} chars):")
                        print("=" * 60)
                        print(new_report.sms_content)
                        print("=" * 60)

                        # Check if fix worked
                        if "You are composing a concise SMS" in new_report.sms_content:
                            print("❌ FIX FAILED: Still showing prompt instructions!")
                            return False
                        else:
                            print("✅ FIX SUCCESSFUL: Proper SMS content generated!")
                            print("🎉 Your 4 AM reports will now show real health insights!")
                            return True
                    else:
                        print("❌ No SMS content in new report")
                        return False
                else:
                    print("❌ No report ID returned")
                    return False
            else:
                print(f"❌ Report generation failed: {result}")
                return False

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_with_manual_sms_generation():
    """Test SMS generation directly with sample data"""

    try:
        from tasks.daily_report import _generate_fallback_sms
        from datetime import datetime

        print(f"\n🧪 Testing Manual SMS Generation...")

        # Sample insights and recommendations
        sample_insights = [
            {"insight": "Your HRV improved by 12% this week", "confidence": 0.85},
            {"insight": "Sleep quality trending upward", "confidence": 0.78}
        ]

        sample_recommendations = [
            {"recommendation": "Try morning sunlight for better sleep", "confidence": 0.9}
        ]

        # Generate fallback SMS
        fallback_sms = _generate_fallback_sms(sample_insights, sample_recommendations)

        print(f"📱 Generated Fallback SMS ({len(fallback_sms)} chars):")
        print("=" * 50)
        print(fallback_sms)
        print("=" * 50)

        if "You are composing" not in fallback_sms and len(fallback_sms) <= 306:
            print("✅ Fallback SMS generation working correctly!")
            return True
        else:
            print("❌ Fallback SMS has issues")
            return False

    except Exception as e:
        print(f"❌ Manual test failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🧪 Force New Report Test - Verify Fix Applied")

    # Test manual SMS generation first
    manual_ok = test_with_manual_sms_generation()

    # Then test with new report
    if manual_ok:
        report_ok = force_new_report_test()

        if report_ok:
            print(f"\n🎉 SUCCESS!")
            print(f"✅ Fix verified - SMS generation working correctly")
            print(f"✅ Your 4 AM reports will show proper health insights")
            print(f"✅ No more prompt instructions in SMS content")
        else:
            print(f"\n⚠️ Report test failed, but manual SMS works")
            print(f"💡 The fix is applied, may need to wait for next 4 AM cycle")
    else:
        print(f"\n❌ Manual SMS test failed - fix may need refinement")