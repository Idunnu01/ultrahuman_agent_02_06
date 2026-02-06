#!/usr/bin/env python3
"""
Test comprehensive specific lifestyle tracking for all event types
"""

def show_comprehensive_tracking():
    """Show what comprehensive specific tracking enables"""

    print("🎯 COMPREHENSIVE SPECIFIC LIFESTYLE TRACKING")
    print("=" * 60)
    print()

    print("✅ NOW TRACKS SPECIFIC:")
    print("• Supplement names (magnesium, vitamin D, fish oil, etc.)")
    print("• Food types (chicken, salmon, oats, etc.)")
    print("• Exercise types (running, cycling, yoga, etc.)")
    print("• Drink types (coffee, tea, water, etc.)")
    print("• With dosages, amounts, and timing")
    print()

def show_before_after_examples():
    """Show before vs after for all lifestyle categories"""

    print("📊 BEFORE vs AFTER TRACKING:")
    print("=" * 30)
    print()

    examples = [
        {
            "category": "💊 SUPPLEMENTS",
            "input": "supplement magnesium 400mg 10pm",
            "before": "supplement_intake: 1.0 boolean",
            "after": [
                "magnesium_intake: 400.0 mg",
                "supplement_intake: 1.0 boolean"
            ],
            "queries": [
                "Does magnesium improve my sleep score?",
                "What's the optimal magnesium dosage for my HRV?"
            ]
        },
        {
            "category": "🍽️  MEALS",
            "input": "meal chicken 7pm",
            "before": "meal_timing: 19.0 hour_of_day",
            "after": [
                "meal_timing: 19.0 hour_of_day",
                "chicken_consumption: 1.0 boolean"
            ],
            "queries": [
                "How does chicken affect my recovery?",
                "Does protein timing correlate with my sleep?"
            ]
        },
        {
            "category": "🏃 EXERCISE",
            "input": "exercise running 45min 6am",
            "before": "exercise_duration: 45.0 minutes",
            "after": [
                "exercise_duration: 45.0 minutes",
                "running_duration: 45.0 minutes"
            ],
            "queries": [
                "How does running duration affect my HRV?",
                "Does morning running improve my recovery?"
            ]
        },
        {
            "category": "☕ DRINKS",
            "input": "drink coffee 16oz 9am",
            "before": "No specific tracking",
            "after": [
                "coffee_consumption: 16.0 oz",
                "caffeine_intake: 190.0 mg"  # 95mg * 2 cups
            ],
            "queries": [
                "How does coffee timing affect my sleep?",
                "What's the correlation between caffeine and heart rate?"
            ]
        }
    ]

    for example in examples:
        print(f"{example['category']}")
        print(f"   📱 Input: '{example['input']}'")
        print(f"   ❌ Before: {example['before']}")
        print(f"   ✅ After:")
        for metric in example['after']:
            print(f"      • {metric}")
        print(f"   🔍 New Queries Possible:")
        for query in example['queries']:
            print(f"      📝 '{query}'")
        print()

def show_advanced_correlations():
    """Show advanced correlation possibilities"""

    print("🔬 ADVANCED CORRELATION POSSIBILITIES:")
    print("=" * 40)
    print()

    correlations = [
        {
            "category": "🥗 FOOD-SPECIFIC ANALYSIS",
            "examples": [
                "Does salmon consumption improve my omega-3 levels?",
                "How does chicken vs beef affect my recovery?",
                "Does oatmeal timing correlate with my glucose stability?",
                "What's the relationship between spinach and my iron levels?"
            ]
        },
        {
            "category": "🏋️ EXERCISE-SPECIFIC ANALYSIS",
            "examples": [
                "Does yoga improve my HRV more than running?",
                "How does cycling duration affect my leg recovery?",
                "Does weight training correlate with my testosterone?",
                "What's the optimal swimming frequency for my cardiovascular health?"
            ]
        },
        {
            "category": "☕ BEVERAGE-SPECIFIC ANALYSIS",
            "examples": [
                "Does green tea improve my antioxidant levels?",
                "How does coffee timing affect my cortisol?",
                "Does herbal tea improve my sleep quality?",
                "What's the correlation between water intake and my hydration markers?"
            ]
        },
        {
            "category": "🔄 COMBINATION ANALYSIS",
            "examples": [
                "Does coffee + magnesium affect my sleep differently?",
                "How does running + protein timing affect my recovery?",
                "Does fish oil + exercise improve my inflammation markers?",
                "What's the synergy between yoga + meditation on my stress levels?"
            ]
        }
    ]

    for corr in correlations:
        print(f"**{corr['category']}**")
        for example in corr['examples']:
            print(f"   📝 '{example}'")
        print()

def show_sample_specific_logging():
    """Show sample specific logging routine"""

    print("📝 SAMPLE SPECIFIC LOGGING ROUTINE:")
    print("=" * 35)
    print()

    daily_routine = [
        {
            "time": "🌅 6:00 AM - Morning",
            "logs": [
                "exercise running 30min 6am",
                "drink water 16oz 6:30am"
            ]
        },
        {
            "time": "☀️ 8:00 AM - Breakfast",
            "logs": [
                "meal oats 8am",
                "supplement vitamin D 2000IU 8am",
                "drink coffee 12oz 8am"
            ]
        },
        {
            "time": "🌞 12:00 PM - Lunch",
            "logs": [
                "meal salmon 12pm",
                "supplement omega-3 1000mg 12pm",
                "drink green tea 8oz 12pm"
            ]
        },
        {
            "time": "🌇 7:00 PM - Dinner",
            "logs": [
                "meal chicken 7pm",
                "drink water 20oz 7pm"
            ]
        },
        {
            "time": "🌙 10:00 PM - Evening",
            "logs": [
                "supplement magnesium 400mg 10pm",
                "supplement melatonin 3mg 10:30pm"
            ]
        }
    ]

    for routine in daily_routine:
        print(f"**{routine['time']}**")
        for log in routine['logs']:
            print(f"   📱 '{log}'")
        print()

def show_database_metrics():
    """Show what metrics will be created"""

    print("🗄️  DATABASE METRICS CREATED:")
    print("=" * 30)
    print()

    metric_categories = [
        {
            "category": "Supplement-Specific",
            "metrics": [
                "magnesium_intake: 400.0 mg",
                "vitamin_d_intake: 2000.0 IU",
                "omega_3_intake: 1000.0 mg",
                "melatonin_intake: 3.0 mg"
            ]
        },
        {
            "category": "Food-Specific",
            "metrics": [
                "oats_consumption: 1.0 boolean",
                "salmon_consumption: 1.0 boolean",
                "chicken_consumption: 1.0 boolean"
            ]
        },
        {
            "category": "Exercise-Specific",
            "metrics": [
                "running_duration: 30.0 minutes",
                "yoga_duration: 45.0 minutes",
                "cycling_duration: 60.0 minutes"
            ]
        },
        {
            "category": "Drink-Specific",
            "metrics": [
                "water_consumption: 16.0 oz",
                "coffee_consumption: 12.0 oz",
                "caffeine_intake: 114.0 mg",
                "green_tea_consumption: 8.0 oz"
            ]
        }
    ]

    for category in metric_categories:
        print(f"📊 **{category['category']}:**")
        for metric in category['metrics']:
            print(f"   • {metric}")
        print()

if __name__ == "__main__":
    show_comprehensive_tracking()
    print()
    show_before_after_examples()
    print()
    show_advanced_correlations()
    print()
    show_sample_specific_logging()
    print()
    show_database_metrics()

    print("🚀 DEPLOYMENT STEPS:")
    print("1. Upload updated services/metrics_service.py to PythonAnywhere")
    print("2. Restart your web app")
    print("3. Test comprehensive tracking:")
    print("   📱 'supplement magnesium 400mg 10pm'")
    print("   📱 'meal chicken 7pm'")
    print("   📱 'exercise running 30min 6am'")
    print("   📱 'drink coffee 16oz 9am'")
    print("4. Check database for specific metrics")
    print("5. Try specific queries:")
    print("   📝 'Does magnesium improve my sleep?'")
    print("   📝 'How does running affect my HRV?'")
    print("   📝 'Does coffee timing correlate with my heart rate?'")