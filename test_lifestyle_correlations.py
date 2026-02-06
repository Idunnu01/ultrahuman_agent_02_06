#!/usr/bin/env python3
"""
Test correlation queries with lifestyle data
"""

def show_correlation_examples():
    """Show example correlation queries to test"""

    print("🔗 LIFESTYLE CORRELATION EXAMPLES")
    print("=" * 40)
    print()

    print("Once you have lifestyle events stored, try these SMS queries:")
    print()

    # Meal correlations
    print("🍽️  MEAL TIMING CORRELATIONS:")
    meal_queries = [
        "How does meal timing affect my sleep?",
        "Does eating late correlate with poor sleep score?",
        "What's the relationship between dinner time and HRV?",
        "How do meals affect my glucose levels?"
    ]
    for query in meal_queries:
        print(f"   📝 '{query}'")
    print()

    # Supplement correlations
    print("💊 SUPPLEMENT CORRELATIONS:")
    supplement_queries = [
        "Does magnesium improve my sleep score?",
        "How does vitamin D affect my recovery?",
        "What's the correlation between supplements and HRV?",
        "Do my supplements affect my stress levels?"
    ]
    for query in supplement_queries:
        print(f"   📝 '{query}'")
    print()

    # Exercise correlations
    print("🏃 EXERCISE CORRELATIONS:")
    exercise_queries = [
        "How does exercise duration affect my recovery?",
        "Does morning exercise improve my HRV?",
        "What's the relationship between workouts and sleep?",
        "How does running correlate with my resting heart rate?"
    ]
    for query in exercise_queries:
        print(f"   📝 '{query}'")
    print()

    # Caffeine correlations
    print("☕ CAFFEINE CORRELATIONS:")
    caffeine_queries = [
        "How does coffee timing affect my sleep?",
        "Does caffeine correlate with my stress levels?",
        "What's the relationship between coffee and HRV?",
        "How does morning coffee affect my heart rate?"
    ]
    for query in caffeine_queries:
        print(f"   📝 '{query}'")
    print()

def show_data_requirements():
    """Show how much data is needed for good correlations"""

    print("📊 DATA REQUIREMENTS FOR CORRELATIONS:")
    print("=" * 40)
    print()

    print("✅ MINIMUM DATA NEEDED:")
    print("   • At least 7-10 data points for basic correlation")
    print("   • 14+ days recommended for reliable patterns")
    print("   • 30+ days for robust statistical analysis")
    print()

    print("🎯 WHAT TO LOG CONSISTENTLY:")
    print("   • Meal times (especially dinner)")
    print("   • Supplement timing and dosage")
    print("   • Exercise duration and timing")
    print("   • Coffee/caffeine intake")
    print("   • Sleep timing")
    print()

    print("📈 CORRELATION STRENGTH:")
    print("   • r > 0.7: Strong correlation")
    print("   • r > 0.5: Moderate correlation")
    print("   • r > 0.3: Weak but meaningful correlation")
    print("   • r < 0.3: Very weak correlation")
    print()

def show_sample_lifestyle_logs():
    """Show examples of good lifestyle logging"""

    print("📝 SAMPLE LIFESTYLE LOGGING ROUTINE:")
    print("=" * 35)
    print()

    print("🌅 MORNING (6-10 AM):")
    morning_logs = [
        "exercise running 30min 6am",
        "drink coffee 9am",
        "supplement vitamin D 1000IU 9am"
    ]
    for log in morning_logs:
        print(f"   📱 '{log}'")
    print()

    print("🌞 AFTERNOON (12-5 PM):")
    afternoon_logs = [
        "meal lunch salad 1pm",
        "drink water 16oz 2pm",
        "supplement magnesium 200mg 3pm"
    ]
    for log in afternoon_logs:
        print(f"   📱 '{log}'")
    print()

    print("🌙 EVENING (6-11 PM):")
    evening_logs = [
        "meal dinner chicken 7pm",
        "supplement magnesium 400mg 10pm",
        "sleep 11pm"
    ]
    for log in evening_logs:
        print(f"   📱 '{log}'")
    print()

    print("💡 CONSISTENCY TIPS:")
    print("   • Log at the same times daily")
    print("   • Use similar food descriptions")
    print("   • Include timing even if approximate")
    print("   • Be specific with supplements (dosage)")
    print()

if __name__ == "__main__":
    show_correlation_examples()
    print()
    show_data_requirements()
    print()
    show_sample_lifestyle_logs()

    print("🚀 NEXT STEPS:")
    print("1. First run: python check_lifestyle_events.py")
    print("2. Confirm your meal event was stored")
    print("3. Log more lifestyle events over several days")
    print("4. Then try correlation queries via SMS")
    print("5. Build up 1-2 weeks of data for best results")