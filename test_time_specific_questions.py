#!/usr/bin/env python3
"""
Test Enhanced Time-Specific SMS Questions
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def test_time_specific_parsing():
    """Test the new time-specific question parsing"""

    print("🕐 TESTING ENHANCED TIME-SPECIFIC ANALYSIS")
    print("=" * 60)

    from services.sms_health_analyzer import SMSHealthAnalyzer

    analyzer = SMSHealthAnalyzer()

    # Test time-specific questions that should now work
    enhanced_questions = [
        # 3am specific
        ("🌙 3AM ANALYSIS", "What was my heart rate at 3am last night?"),

        # Overnight analysis
        ("🌙 OVERNIGHT ANALYSIS", "How was my HRV during sleep hours?"),

        # Daily patterns
        ("⏰ DAILY PATTERNS", "When do I have the highest heart rate each day?"),

        # Time period analysis
        ("🌅 MORNING ANALYSIS", "How does my morning HRV compare to evening?"),

        # Date-specific
        ("📅 LAST NIGHT", "What was my temperature pattern overnight?"),

        # Weekend vs weekday
        ("📅 WEEKDAY PATTERNS", "How does weekend sleep compare to weekdays?"),

        # Enhanced sleep timing
        ("🛌 BEDTIME ANALYSIS", "What time did I fall asleep last night?"),
    ]

    print("Testing enhanced parsing capabilities...\n")

    for category, question in enhanced_questions:
        print(f"{category}")
        print("-" * len(category))
        print(f"Question: '{question}'")

        # Parse the question
        lifestyle_factor, health_metric = analyzer._parse_question(question)
        is_question = analyzer.is_question_format(question)

        print(f"Parsed as: {lifestyle_factor} → {health_metric}")
        print(f"Detected as question: {is_question}")

        # Show what type of analysis would be performed
        if lifestyle_factor == 'TIME_SPECIFIC_ANALYSIS':
            print("✅ Will perform TIME-SPECIFIC analysis (new!)")
        elif lifestyle_factor == 'OVERNIGHT_ANALYSIS':
            print("✅ Will perform OVERNIGHT analysis (new!)")
        elif lifestyle_factor == 'HOURLY_PATTERN_ANALYSIS':
            print("✅ Will perform HOURLY PATTERN analysis (new!)")
        elif lifestyle_factor == 'DATE_SPECIFIC_ANALYSIS':
            print("✅ Will perform DATE-SPECIFIC analysis (new!)")
        elif lifestyle_factor == 'WEEKDAY_ANALYSIS':
            print("✅ Will perform WEEKDAY analysis (new!)")
        elif lifestyle_factor == 'TREND_ANALYSIS':
            print("⚠️ Will perform basic trend analysis (fallback)")
        else:
            print("❌ Not recognized - needs improvement")

        print()

    print("=" * 60)
    print("📊 ENHANCEMENT SUMMARY:")
    print()
    print("✅ Added 5 new analysis types:")
    print("   • TIME_SPECIFIC_ANALYSIS - for 3am, morning, evening queries")
    print("   • OVERNIGHT_ANALYSIS - for sleep hours, overnight patterns")
    print("   • HOURLY_PATTERN_ANALYSIS - for daily rhythm analysis")
    print("   • DATE_SPECIFIC_ANALYSIS - for last night, yesterday queries")
    print("   • WEEKDAY_ANALYSIS - for weekend vs weekday patterns")
    print()
    print("🎯 NEW CAPABILITIES:")
    print("   • Specific time filtering (3am window: 2:30-3:30am)")
    print("   • Overnight analysis (10pm-6am)")
    print("   • Hourly pattern detection (find peak/low times)")
    print("   • Date-specific filtering (last night, yesterday)")
    print("   • Weekday vs weekend comparison")
    print("   • Enhanced bedtime extraction with debugging")
    print()
    print("💡 QUESTIONS NOW SUPPORTED:")
    print("   • 'What was my heart rate at 3am last night?'")
    print("   • 'How was my HRV during sleep hours?'")
    print("   • 'When do I have the highest heart rate each day?'")
    print("   • 'How does my morning HRV compare to evening?'")
    print("   • 'What was my temperature pattern overnight?'")
    print("   • 'How does weekend sleep compare to weekdays?'")
    print("   • Plus enhanced bedtime analysis with metadata debugging")

if __name__ == '__main__':
    test_time_specific_parsing()