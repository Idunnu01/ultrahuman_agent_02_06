#!/usr/bin/env python3
"""
Debug why single SMS events are failing
"""

import sys
import os
import re
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_parsing_only():
    """Test just the parsing without database operations"""

    print("🔍 Testing SMS Event Parsing Only (No Database)")
    print("="*50)

    # Test message
    test_message = "supplement magnesium 400mg at 10pm"
    print(f"📱 Test message: '{test_message}'")
    print()

    # Test basic detection
    print("1️⃣  Testing _is_lifestyle_event detection...")

    def _is_lifestyle_event(message: str) -> bool:
        # Copy the exact logic from the service
        question_patterns = r'\b(what|how|is there|show me|correlation|relationship|trend|pattern|anomal)\b'
        if re.search(question_patterns, message, re.I):
            return False

        lifestyle_patterns = [
            r'\bmeal\s+\w+',
            r'\bsupplement\s+',
            r'\bworkout\s+\w+',
            r'\bexercise\s+',
            r'\bactivity\s+',
            r'\bdrink\s+',
            r'\bsleep\s+\d+:\d+',
            r'\bsleep\s+\w+\s+to\s+',
            r'\balcohol\s+\w+',
            r'\bcaffeine\s+\w+',
            r'\bmood\s+\w+',
            r'\bstress\s+\w+'
        ]

        return any(re.search(pattern, message, re.I) for pattern in lifestyle_patterns)

    is_lifestyle = _is_lifestyle_event(test_message.lower())
    print(f"   Result: {is_lifestyle} ✅" if is_lifestyle else f"   Result: {is_lifestyle} ❌")

    if not is_lifestyle:
        print("❌ ISSUE FOUND: Message not detected as lifestyle event!")
        return False

    # Test supplement pattern matching
    print("\n2️⃣  Testing supplement pattern matching...")

    text_lower = test_message.lower()
    supplement_patterns = [
        r'supplement\s+(\w+)(\d+(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',
        r'supplement\s+(\w+)\s+(\d+(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',
        r'supplement\s+(\w+)\s*(\d+\s*(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))?',
        r'supplement\s+(\w+)\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))',
        r'supplement\s+(\w+)$'
    ]

    found_match = False
    for i, pattern in enumerate(supplement_patterns):
        match = re.search(pattern, text_lower)
        if match:
            print(f"   Pattern {i+1} matched: {match.groups()}")
            found_match = True
            break

    if not found_match:
        print("❌ ISSUE FOUND: No supplement patterns matched!")
        return False
    else:
        print("   ✅ Supplement pattern matched successfully")

    # Test time parsing
    print("\n3️⃣  Testing time parsing...")
    time_str = "10pm"

    def _parse_time_string(time_str, reference_time):
        if not time_str:
            return reference_time

        time_str = time_str.lower().strip()

        # Handle "XYpm" or "XYam" format
        am_pm_match = re.match(r'(\d{1,2})(?::(\d{2}))?(am|pm)', time_str)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            minute = int(am_pm_match.group(2)) if am_pm_match.group(2) else 0
            am_pm = am_pm_match.group(3)

            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0

            try:
                return reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            except ValueError:
                return reference_time

        return reference_time

    current_time = datetime.now()
    parsed_time = _parse_time_string(time_str, current_time)

    print(f"   Input: '{time_str}'")
    print(f"   Parsed time: {parsed_time.strftime('%I:%M %p')}")
    print("   ✅ Time parsing works")

    print("\n✅ All parsing components work individually!")
    return True

def test_direct_service_parsing():
    """Test the actual service parsing method"""

    print("\n🔍 Testing MetricsService Parsing Directly")
    print("="*45)

    try:
        from services.metrics_service import MetricsService

        service = MetricsService()
        test_message = "supplement magnesium 400mg at 10pm"

        print(f"📱 Test message: '{test_message}'")

        # Test _is_lifestyle_event
        print("\n1️⃣  Testing service._is_lifestyle_event...")
        is_lifestyle = service._is_lifestyle_event(test_message.lower())
        print(f"   Result: {is_lifestyle}")

        if not is_lifestyle:
            print("❌ Service doesn't detect it as lifestyle event!")
            return False

        # Test _parse_lifestyle_sms
        print("\n2️⃣  Testing service._parse_lifestyle_sms...")
        try:
            event_type, details, timestamp = service._parse_lifestyle_sms(test_message)
            print(f"   Event type: {event_type}")
            print(f"   Details: {details}")
            print(f"   Timestamp: {timestamp}")
            print("   ✅ Parsing successful")
            return True
        except Exception as e:
            print(f"   ❌ Parsing failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_production_logs():
    """Check what might be happening in production"""

    print("\n🔍 Checking Production Behavior")
    print("="*35)

    # The error message suggests the pattern isn't matching
    # Let's check if there might be encoding or formatting issues

    test_messages = [
        "supplement magnesium 400mg at 10pm",
        "supplement magnesium 400mg 10pm",
        "supplement magnesium400mg at 10pm",
        "supplement magnesium400mg 10pm",
        "supplement magnesium 400 mg at 10pm"
    ]

    print("Testing various message formats...")

    try:
        from services.metrics_service import MetricsService
        service = MetricsService()

        for i, msg in enumerate(test_messages, 1):
            print(f"\n{i}. '{msg}'")
            is_lifestyle = service._is_lifestyle_event(msg.lower())
            print(f"   Detected as lifestyle: {is_lifestyle}")

            if is_lifestyle:
                try:
                    event_type, details, timestamp = service._parse_lifestyle_sms(msg)
                    print(f"   ✅ Parsed: {event_type} - {details}")
                except Exception as e:
                    print(f"   ❌ Parse failed: {e}")

    except Exception as e:
        print(f"❌ Production check failed: {e}")

if __name__ == "__main__":
    print("🚀 Debugging Single SMS Event Failure")
    print("="*50)

    # Run tests
    tests = [
        ("Basic Parsing Components", test_parsing_only),
        ("Direct Service Parsing", test_direct_service_parsing),
        ("Production Format Check", check_production_logs)
    ]

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        result = test_func()
        if not result:
            print(f"\n❌ {test_name} FAILED - This might be the issue!")
        else:
            print(f"\n✅ {test_name} PASSED")