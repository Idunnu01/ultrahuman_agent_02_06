#!/usr/bin/env python3
"""
Test script to verify conversational responses work correctly
"""

def test_conversational_responses():
    """Test the new conversational response handling"""
    try:
        from services.metrics_service import MetricsService

        print("🧪 TESTING CONVERSATIONAL RESPONSES")
        print("=" * 50)

        metrics_service = MetricsService()

        test_messages = [
            "Hello",
            "Hi there",
            "Thank you",
            "Thanks so much",
            "Bye",
            "How is my temperature today?",  # Should NOT be conversational
        ]

        for message in test_messages:
            print(f"\n📨 Testing: '{message}'")

            # Test the conversational detection directly
            is_conversational, response = metrics_service._is_conversational_message(message)

            if is_conversational:
                print(f"✅ Detected as conversational")
                print(f"💬 Response: {response}")
            else:
                print(f"❌ Not detected as conversational (will go to regular processing)")

                # Test full SMS processing
                result = metrics_service.process_sms_input("test_user", message)
                if result.get('conversational_response'):
                    print(f"🔄 Full processing returned conversational response")
                    insights = result.get('immediate_insights', {}).get('insights', [])
                    if insights:
                        print(f"💬 Response: {insights[0].get('message', 'No message')}")
                else:
                    print(f"🔄 Full processing used regular logic")

            print("-" * 40)

        print("\n🎉 CONVERSATIONAL TESTING COMPLETE!")
        print("\nExpected behavior:")
        print("- 'Hello', 'Hi there' → Greeting responses")
        print("- 'Thank you', 'Thanks so much' → Thank you responses")
        print("- 'Bye' → Goodbye responses")
        print("- 'How is my temperature today?' → Regular health query processing")

    except Exception as e:
        print(f"❌ Error testing conversational responses: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_conversational_responses()