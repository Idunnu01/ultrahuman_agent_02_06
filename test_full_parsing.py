#!/usr/bin/env python3
"""
Test the full parsing flow to identify the exact issue
"""
import re
from datetime import datetime

def _parse_time_string(time_str: str, reference_time: datetime) -> datetime:
    """Parse time string into datetime"""
    if not time_str:
        return reference_time

    time_str = time_str.lower().strip()

    # Handle special cases
    if time_str in ['bedtime', 'night']:
        return reference_time.replace(hour=22, minute=0, second=0, microsecond=0)
    elif time_str in ['morning']:
        return reference_time.replace(hour=8, minute=0, second=0, microsecond=0)
    elif time_str in ['evening']:
        return reference_time.replace(hour=19, minute=0, second=0, microsecond=0)
    elif time_str in ['breakfast']:
        return reference_time.replace(hour=8, minute=0, second=0, microsecond=0)
    elif time_str in ['lunch']:
        return reference_time.replace(hour=12, minute=0, second=0, microsecond=0)
    elif time_str in ['dinner']:
        return reference_time.replace(hour=19, minute=0, second=0, microsecond=0)

    # Parse specific times like "7pm", "6:30am", "22:00"
    time_match = re.match(r'(\d{1,2})(?::(\d{2}))?(am|pm)?', time_str)

    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        period = time_match.group(3)

        # Handle AM/PM
        if period:
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0

        # Validate hour and minute
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If parsing fails, return reference time
    return reference_time

def _parse_lifestyle_sms(text: str, current_time: datetime = None):
    """Parse SMS text into structured lifestyle event data with improved regex patterns"""
    text_lower = text.lower().strip()
    if current_time is None:
        current_time = datetime.utcnow()

    print(f"Parsing: '{text}' -> '{text_lower}'")
    print(f"Current time: {current_time}")
    print()

    # Parse supplement events - IMPROVED with multiple flexible patterns
    supplement_patterns = [
        # Pattern 1: "supplement magnesium400mg 10pm" (no spaces) - FIXED
        r'supplement\s+(\w+)(\d+(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',

        # Pattern 2: "supplement magnesium 400mg 10pm" (with spaces)
        r'supplement\s+(\w+)\s+(\d+(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',

        # Pattern 3: More flexible with optional "at"
        r'supplement\s+(\w+)\s*(\d+\s*(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))?',

        # Pattern 4: Just supplement name and time (no dosage)
        r'supplement\s+(\w+)\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))',

        # Pattern 5: Just supplement name (no dosage or time)
        r'supplement\s+(\w+)$'
    ]

    for i, pattern in enumerate(supplement_patterns):
        print(f"Testing pattern {i+1}: {pattern}")
        supplement_match = re.search(pattern, text_lower)
        if supplement_match:
            print(f"✅ MATCH! Groups: {supplement_match.groups()}")
            groups = supplement_match.groups()

            if i < 3:  # Patterns with dosage
                name = groups[0]
                dosage = groups[1] if len(groups) > 1 and groups[1] else "unknown"
                time_str = groups[2] if len(groups) > 2 and groups[2] else None
            elif i == 3:  # Pattern with name and time, no dosage
                name = groups[0]
                dosage = "unknown"
                time_str = groups[1] if len(groups) > 1 and groups[1] else None
            else:  # Pattern with just name
                name = groups[0]
                dosage = "unknown"
                time_str = None

            print(f"Extracted: name='{name}', dosage='{dosage}', time_str='{time_str}'")

            event_timestamp = _parse_time_string(time_str, current_time) if time_str else current_time
            print(f"Parsed timestamp: {event_timestamp}")

            details = {
                'name': name,
                'dosage': dosage,
                'parsed_from_sms': True,
                'original_text': text,
                'enhanced_tracking': True
            }

            print(f"Final details: {details}")
            return 'supplement', details, event_timestamp
        else:
            print(f"❌ No match")
        print()

    # Default fallback
    print("❌ NO PATTERNS MATCHED - using fallback")
    return 'meal', {'food': 'unknown', 'parsed_from_sms': True, 'original_text': text}, current_time

if __name__ == "__main__":
    try:
        text = "supplement magnesium 400mg at 10pm"
        event_type, details, timestamp = _parse_lifestyle_sms(text)
        print("✅ SUCCESS!")
        print(f"Event type: {event_type}")
        print(f"Details: {details}")
        print(f"Timestamp: {timestamp}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()