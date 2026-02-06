#!/usr/bin/env python3
"""
Test script for the new lifestyle logging system
"""

def test_lifestyle_parsing():
    """Test the SMS parsing functionality"""

    print("🧪 TESTING LIFESTYLE LOGGING SYSTEM")
    print("=" * 50)

    try:
        from services.metrics_service import MetricsService

        service = MetricsService()

        # Test messages to parse
        test_messages = [
            # Meal events
            "meal chicken 7pm",
            "meal salmon 6:30pm",
            "meal breakfast 8am",

            # Supplement events
            "supplement magnesium 400mg 10pm",
            "supplement vitamin 1000iu 9am",
            "supplement fish oil",

            # Exercise events
            "exercise running 45min 6am",
            "workout gym 90min",
            "activity walking 30min",

            # Sleep events
            "sleep 11pm",
            "sleep bedtime",
            "sleep at 10:30pm",

            # Drink events
            "drink coffee 9am",
            "drink water 16oz 2pm",
            "drank tea 4pm"
        ]

        print("🔍 TESTING SMS PARSER:")
        print("-" * 30)

        for message in test_messages:
            print(f"\n📱 Testing: '{message}'")

            # Test parsing
            try:
                event_type, details, timestamp = service._parse_lifestyle_sms(message)
                print(f"✅ Parsed successfully:")
                print(f"   Event Type: {event_type}")
                print(f"   Details: {details}")
                print(f"   Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                print(f"❌ Parsing failed: {e}")

        print("\n" + "=" * 50)
        print("🎯 TESTING FULL SMS PROCESSING:")
        print("=" * 50)

        # Test full processing with a few examples
        test_full_messages = [
            "meal chicken 7pm",
            "supplement magnesium 400mg 10pm",
            "exercise running 30min 6am"
        ]

        for message in test_full_messages:
            print(f"\n📨 Full Processing Test: '{message}'")

            try:
                # Use a test user ID
                result = service.process_sms_input("test_user", message)

                if result.get('success'):
                    print(f"✅ Success!")
                    insights = result.get('immediate_insights', {}).get('insights', [])
                    if insights:
                        print(f"💬 Response: {insights[0].get('message', 'No message')}")
                    print(f"📊 Events processed: {result.get('events_processed', 0)}")
                    print(f"📈 Metrics created: {result.get('metrics_created', 0)}")
                else:
                    print(f"❌ Failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"❌ Processing error: {e}")
                import traceback
                traceback.print_exc()

        print("\n🎉 TESTING COMPLETE!")

    except Exception as e:
        print(f"❌ Error setting up test: {e}")
        import traceback
        traceback.print_exc()

def show_testing_instructions():
    """Show how to test via SMS"""

    print("\n📱 HOW TO TEST VIA SMS:")
    print("=" * 30)
    print()
    print("1. **Upload the updated file** to PythonAnywhere:")
    print("   - Upload: services/metrics_service.py")
    print("   - Restart your web app")
    print()
    print("2. **Text these examples** to your SMS number:")
    print()

    examples = [
        ("meal chicken 7pm", "Logs a chicken meal at 7 PM"),
        ("supplement magnesium 400mg 10pm", "Logs magnesium supplement at 10 PM"),
        ("exercise running 30min 6am", "Logs 30-min run at 6 AM"),
        ("drink coffee 9am", "Logs coffee (caffeine) at 9 AM"),
        ("sleep 11pm", "Logs sleep time at 11 PM")
    ]

    for sms, description in examples:
        print(f"   📝 '{sms}'")
        print(f"      → {description}")
        print()

    print("3. **Expected Responses:**")
    print("   ✅ 'Meal logged successfully! Food: chicken at 7:00 PM'")
    print("   ✅ 'Supplement logged successfully! Supplement: magnesium (400mg) at 10:00 PM'")
    print("   ✅ 'Activity logged successfully! Activity: running (30 min) at 6:00 AM'")
    print()

    print("4. **Verify Storage** on PythonAnywhere:")
    print("   ```python")
    print("   python check_production_data.py")
    print("   ```")
    print("   Look for new metrics like:")
    print("   • meal_timing")
    print("   • supplement_intake")
    print("   • exercise_duration")
    print()

    print("5. **Test Correlations** (after logging events for a few days):")
    print("   📝 'How does coffee timing affect my sleep?'")
    print("   📝 'Does magnesium improve my HRV?'")
    print("   📝 'What's the correlation between exercise and recovery?'")

if __name__ == "__main__":
    test_lifestyle_parsing()
    show_testing_instructions()