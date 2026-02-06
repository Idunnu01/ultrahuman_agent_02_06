#!/usr/bin/env python3
"""Test the lifestyle event detection"""
import re

def _is_lifestyle_event(message: str) -> bool:
    # First check if this looks like a question/analysis request (not a logging event)
    question_patterns = r'\b(what|how|is there|show me|correlation|relationship|trend|pattern|anomal)\b'
    if re.search(question_patterns, message, re.I):
        return False

    # Now check for actual lifestyle event patterns (more specific)
    lifestyle_patterns = [
        r'\bmeal\s+\w+',          # "meal chicken", "meal pasta"
        r'\bsupplement\s+',       # "supplement magnesium 400mg at 10pm" - match any supplement
        r'\bworkout\s+\w+',       # "workout cardio", "workout 30min"
        r'\bexercise\s+',         # "exercise running 30min 6am" - match any exercise
        r'\bactivity\s+',         # "activity swimming 1hr" - match any activity
        r'\bdrink\s+',            # "drink coffee 16oz 9am" - match any drink
        r'\bsleep\s+\d+:\d+',     # "sleep 23:30", "sleep 11pm"
        r'\bsleep\s+\w+\s+to\s+', # "sleep 11pm to 7am"
        r'\balcohol\s+\w+',       # "alcohol wine", "alcohol beer"
        r'\bcaffeine\s+\w+',      # "caffeine coffee", "caffeine 2pm"
        r'\bmood\s+\w+',          # "mood anxious", "mood happy"
        r'\bstress\s+\w+'         # "stress high", "stress work"
    ]

    for pattern in lifestyle_patterns:
        if re.search(pattern, message, re.I):
            print(f"✅ MATCHED pattern: {pattern}")
            return True

    print("❌ No patterns matched")
    return False

if __name__ == "__main__":
    test_messages = [
        "supplement magnesium 400mg at 10pm",
        "meal salmon 7pm",
        "exercise running 30min 6am",
        "drink coffee 16oz 9am",
        "what is my sleep score?"  # Should NOT match (question)
    ]

    for msg in test_messages:
        print(f"\nTesting: '{msg}'")
        result = _is_lifestyle_event(msg.lower())
        print(f"Result: {result}")
