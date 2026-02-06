#!/usr/bin/env python3
"""
Test with completely fresh report using unique date
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_fresh_report():
    """Generate report with unique date to test fixes"""

    try:
        from app import create_app
        from app.models import DailyReport
        from tasks.daily_report import generate_daily_report
        from datetime import datetime, timedelta
        from utils.database import db

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            print("🧪 Testing Fresh Report Generation")
            print("=" * 50)

            # Use a far future date to ensure no conflicts
            future_date = datetime.now() + timedelta(days=30)
            test_date = future_date.strftime('%Y-%m-%d')

            print(f"📅 Generating fresh report for {test_date}...")

            # First, make sure this date doesn't exist
            existing = DailyReport.query.filter_by(
                user_id=user_id,
                report_date=test_date
            ).first()

            if existing:
                print(f"🗑️ Deleting existing report for {test_date}...")
                db.session.delete(existing)
                db.session.commit()

            # Generate fresh report
            result = generate_daily_report(user_id, test_date)

            print(f"📊 Result: {result}")

            if result and result.get('success'):
                report_id = result.get('report_id')

                if report_id:
                    # Get the newly created report
                    new_report = db.session.get(DailyReport, report_id)

                    if new_report and new_report.sms_content:
                        print(f"\n📱 FRESH REPORT SMS CONTENT ({len(new_report.sms_content)} chars):")
                        print("=" * 60)
                        print(new_report.sms_content)
                        print("=" * 60)

                        # Check if fix worked
                        if "You are composing a concise SMS" in new_report.sms_content:
                            print("❌ STILL BROKEN: Shows prompt instructions!")
                            print("🔍 The LLM service is still returning prompts instead of responses")
                            return False
                        else:
                            print("✅ SUCCESS: Proper SMS content generated!")
                            print("🎉 Fix is working - no more prompt instructions!")
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

def check_fallback_sms_directly():
    """Test the fallback SMS generation function directly"""

    try:
        from tasks.daily_report import _generate_fallback_sms

        print(f"\n🧪 Testing Fallback SMS Function Directly...")

        # Test with sample data
        sample_insights = [
            {"insight": "Your sleep quality improved this week", "confidence": 0.85}
        ]

        sample_recommendations = [
            {"recommendation": "Try morning sunlight exposure", "confidence": 0.9}
        ]

        fallback_sms = _generate_fallback_sms(sample_insights, sample_recommendations)

        print(f"📱 Direct Fallback SMS ({len(fallback_sms)} chars):")
        print("=" * 50)
        print(fallback_sms)
        print("=" * 50)

        if "You are composing" not in fallback_sms:
            print("✅ Fallback function works correctly")
            return True
        else:
            print("❌ Fallback function still broken")
            return False

    except Exception as e:
        print(f"❌ Direct test failed: {str(e)}")
        return False

def diagnose_sms_generation_flow():
    """Diagnose where the SMS generation is breaking"""

    try:
        from services.llm_service import SMSLLMService

        print(f"\n🔍 Diagnosing SMS Generation Flow...")

        llm_service = SMSLLMService()

        # Test the exact flow from daily reports
        test_prompt = "Generate health insight SMS from: sleep_quality improved, hrv stable"

        print(f"📝 Testing prompt: {test_prompt[:50]}...")

        response = llm_service.generate_sms_response(test_prompt, max_length=306)

        if response and hasattr(response, 'content'):
            content = response.content
            print(f"📱 LLM Response ({len(content)} chars):")
            print("=" * 40)
            print(content)
            print("=" * 40)

            if "You are composing" in content:
                print("❌ LLM service is returning prompts instead of responses!")
                print("🔍 This means the LLM API calls are failing silently")
                return False
            else:
                print("✅ LLM service working correctly")
                return True
        else:
            print("❌ No response from LLM service")
            return False

    except Exception as e:
        print(f"❌ Diagnosis failed: {str(e)}")
        return False

if __name__ == '__main__':
    print("🧪 Fresh Report Test - Complete Diagnosis")

    # Test each component
    fallback_ok = check_fallback_sms_directly()
    llm_ok = diagnose_sms_generation_flow()

    if fallback_ok and llm_ok:
        print(f"\n🔄 Both components work - testing fresh report...")
        fresh_ok = test_fresh_report()

        if fresh_ok:
            print(f"\n🎉 COMPLETE SUCCESS!")
            print(f"✅ All fixes working - SMS generation restored")
        else:
            print(f"\n⚠️ Components work individually but report still fails")
            print(f"💡 Issue may be in daily report logic")
    else:
        print(f"\n🔍 Component Issues Found:")
        print(f"   Fallback SMS: {'✅' if fallback_ok else '❌'}")
        print(f"   LLM Service: {'✅' if llm_ok else '❌'}")

        if not llm_ok:
            print(f"\n💡 Root Cause: LLM service returning prompts instead of responses")
            print(f"💡 This means API calls are failing and returning the input prompt")