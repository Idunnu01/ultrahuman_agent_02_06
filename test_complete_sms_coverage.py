#!/usr/bin/env python3
"""
Test complete SMS metric coverage - all metric types
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def test_complete_coverage():
    """Test SMS analyzer coverage for all metric types"""

    print("🧪 Testing Complete SMS Metric Coverage")
    print("=" * 50)

    from services.sms_health_analyzer import SMSHealthAnalyzer

    analyzer = SMSHealthAnalyzer()

    # Test questions covering ALL available metrics
    comprehensive_questions = [
        # Core vitals
        "What's my heart rate trend over time?",
        "How is my HRV trending?",
        "Show me my temperature average",
        "How many steps am I taking daily?",

        # Sleep metrics
        "How much deep sleep did I get?",
        "What's my REM sleep pattern?",
        "How is my sleep efficiency?",
        "What's my sleep score trending?",

        # Recovery metrics
        "How is my recovery score?",
        "What's my resting heart rate trend?",
        "Show me my VO2 max over time",
        "How is my movement index?",

        # Glucose/Metabolic metrics
        "What's my glucose trend?",
        "How is my blood sugar?",
        "Show me my metabolic score",
        "What's my HbA1c trending?",
        "How is my glucose variability?",
        "What's my average glucose?",
        "Show me my time in target",

        # Activity metrics
        "How are my active minutes?",
        "What's my movement trend?",
        "How is my motion tracking?",

        # Correlation questions
        "Did meal timing affect my glucose?",
        "How does exercise impact my recovery?",
        "Does supplement intake correlate with HRV?",
        "What about movement and heart rate?",

        # Sleep-specific questions
        "What time did I fall asleep?",
        "When do I usually wake up?",
        "How long was my total sleep?",
        "What's my bedtime pattern?"
    ]

    supported_count = 0
    total_count = len(comprehensive_questions)

    print("Testing comprehensive metric coverage...")
    print()

    for question in comprehensive_questions:
        lifestyle_factor, health_metric = analyzer._parse_question(question)
        is_question = analyzer.is_question_format(question)

        if lifestyle_factor and health_metric and is_question:
            status = "✅ SUPPORTED"
            supported_count += 1
        elif (lifestyle_factor == 'TREND_ANALYSIS' and health_metric) and is_question:
            status = "✅ SUPPORTED"
            supported_count += 1
        else:
            status = "❌ NOT SUPPORTED"

        print(f"{status} '{question}'")
        if lifestyle_factor or health_metric:
            print(f"         → {lifestyle_factor} → {health_metric}")
        print()

    # Calculate coverage
    coverage_pct = (supported_count / total_count) * 100

    print("=" * 60)
    print(f"📊 SMS ANALYZER COVERAGE SUMMARY:")
    print(f"   Supported: {supported_count}/{total_count} ({coverage_pct:.1f}%)")
    print(f"   Missing: {total_count - supported_count}")

    if coverage_pct >= 90:
        print(f"✅ EXCELLENT coverage!")
    elif coverage_pct >= 80:
        print(f"✅ GOOD coverage")
    else:
        print(f"⚠️ Coverage needs improvement")

    print()
    print("🎯 Available metric types now supported:")
    print("   • Core vitals: heart_rate, hrv, temperature, steps")
    print("   • Sleep: sleep_score, deep_sleep, rem_sleep, sleep_efficiency")
    print("   • Recovery: recovery_score, resting_heart_rate, vo2_max, movement_index")
    print("   • Glucose: glucose, metabolic_score, glucose_variability, hba1c, time_in_target")
    print("   • Activity: active_minutes, movement")
    print("   • Sleep timing: bedtime, wake_time, sleep_onset analysis")

if __name__ == '__main__':
    test_complete_coverage()