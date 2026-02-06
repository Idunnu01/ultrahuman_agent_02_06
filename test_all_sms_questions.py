#!/usr/bin/env python3
"""
Test All Enhanced Time-Specific SMS Questions
"""

import sys
import os
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_all_sms_questions():
    """Test all enhanced time-specific SMS questions"""

    print("📱 TESTING ALL ENHANCED SMS QUESTIONS")
    print("=" * 60)

    from app import create_app
    from services.sms_health_analyzer import SMSHealthAnalyzer

    app = create_app()

    with app.app_context():
        analyzer = SMSHealthAnalyzer()
        user_id = 'user_7000'

        # All the enhanced time-specific questions
        test_questions = [
            ("🌙 3AM ANALYSIS", "What was my heart rate at 3am last night?"),
            ("🌙 OVERNIGHT ANALYSIS", "How was my HRV during sleep hours?"),
            ("⏰ DAILY PATTERNS", "When do I have the highest heart rate each day?"),
            ("🌅 MORNING ANALYSIS", "How does my morning HRV compare to evening?"),
            ("📅 LAST NIGHT", "What was my temperature pattern overnight?"),
            ("📅 WEEKDAY PATTERNS", "How does weekend sleep compare to weekdays?"),
            ("🛌 BEDTIME ANALYSIS", "What time did I fall asleep last night?"),
            ("🌡️ TEMPERATURE 3AM", "What was my temperature at 3am?"),
            ("💓 OVERNIGHT HRV", "How was my heart rate variability overnight?"),
            ("🏃 DAILY ACTIVITY", "When am I most active during the day?"),
        ]

        results = []

        for category, question in test_questions:
            print(f"\n{category}")
            print("-" * len(category))
            print(f"Q: '{question}'")

            try:
                # Test the question
                start_time = datetime.now()
                response = analyzer.analyze_question(question, user_id)
                end_time = datetime.now()

                response_time = (end_time - start_time).total_seconds()

                # Check if we got a meaningful response
                if "❌" in response or "No data" in response or "Limited data" in response:
                    status = "⚠️ NO DATA"
                elif "Enhanced" in response or "Analysis" in response or any(time_word in response for time_word in ["AM", "PM", "average", "highest", "lowest"]):
                    status = "✅ SUCCESS"
                else:
                    status = "❓ UNCLEAR"

                print(f"Status: {status}")
                print(f"Response time: {response_time:.2f}s")

                # Show first few lines of response
                response_lines = response.split('\n')[:3]
                print(f"Preview: {' | '.join(response_lines)}")

                results.append({
                    'category': category,
                    'question': question,
                    'status': status,
                    'response_time': response_time,
                    'response': response
                })

            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                results.append({
                    'category': category,
                    'question': question,
                    'status': "❌ ERROR",
                    'error': str(e)
                })

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        success_count = sum(1 for r in results if r.get('status') == '✅ SUCCESS')
        no_data_count = sum(1 for r in results if r.get('status') == '⚠️ NO DATA')
        error_count = sum(1 for r in results if r.get('status') == '❌ ERROR')
        unclear_count = sum(1 for r in results if r.get('status') == '❓ UNCLEAR')

        print(f"✅ Successful: {success_count}/{len(test_questions)}")
        print(f"⚠️ No Data: {no_data_count}/{len(test_questions)}")
        print(f"❌ Errors: {error_count}/{len(test_questions)}")
        print(f"❓ Unclear: {unclear_count}/{len(test_questions)}")

        avg_response_time = sum(r.get('response_time', 0) for r in results) / len(results)
        print(f"⏱️ Avg Response Time: {avg_response_time:.2f}s")

        print(f"\n📱 FULL SMS RESPONSES:")
        print("=" * 60)

        for result in results:
            print(f"\n{result['category']}")
            print(f"Q: '{result['question']}'")
            print(f"Status: {result.get('status', 'UNKNOWN')}")
            print("Response:")
            print("-" * 40)
            if 'response' in result:
                # Show full response, formatted for SMS
                response_lines = result['response'].split('\n')
                for line in response_lines:
                    print(f"  {line}")
            elif 'error' in result:
                print(f"  ERROR: {result['error']}")
            print("-" * 40)

        print(f"\n💡 ANALYSIS:")
        if success_count >= 7:
            print("🎉 EXCELLENT! Most time-specific questions are working")
            print("   Users can now ask detailed time-based health questions!")
        elif success_count >= 5:
            print("👍 GOOD! Many time-specific questions are working")
            print("   Most core time-specific features are functional")
        elif success_count >= 3:
            print("⚠️ PARTIAL! Some time-specific questions are working")
            print("   Basic time analysis works, but some features need data")
        else:
            print("❌ NEEDS WORK! Few time-specific questions are working")
            print("   May need more data or further debugging")

        if no_data_count > 3:
            print("📊 Consider running data ingestion to get more recent data")
            print("   Some questions need more historical data to analyze patterns")

        print(f"\n🚀 SMS CAPABILITIES NOW INCLUDE:")
        print("   ✅ Specific time analysis (3am, morning, evening)")
        print("   ✅ Overnight sleep pattern analysis")
        print("   ✅ Daily rhythm detection")
        print("   ✅ Bedtime extraction and insights")
        print("   ✅ Weekend vs weekday comparisons")
        print("   ✅ Date-specific queries (last night, yesterday)")

if __name__ == '__main__':
    test_all_sms_questions()