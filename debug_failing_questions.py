#!/usr/bin/env python3
"""
Debug the 3 failing questions
"""

from services.sms_health_analyzer import SMSHealthAnalyzer

analyzer = SMSHealthAnalyzer()

failing_questions = [
    "How many steps am I taking daily?",
    "Show me my time in target",
    "How are my active minutes?"
]

print("🔍 Debugging failing questions:")
print("=" * 40)

for question in failing_questions:
    print(f"\nQuestion: '{question}'")

    # Test parsing
    lifestyle_factor, health_metric = analyzer._parse_question(question)
    print(f"  Parse result: {lifestyle_factor} → {health_metric}")

    # Test question detection
    is_question = analyzer.is_question_format(question)
    print(f"  Is question: {is_question}")

    # Check individual components
    question_lower = question.lower()

    # Check trend indicators
    trend_indicators = [
        'trend', 'trending', 'average', 'over time', 'weekly', 'monthly',
        'improving', 'getting better', 'getting worse', 'show me my',
        'what\'s my', 'how is my', 'is my', 'what is my', 'show me',
        'how many', 'how are my', 'how long', 'how much'
    ]

    has_trend = any(indicator in question_lower for indicator in trend_indicators)
    print(f"  Has trend indicator: {has_trend}")

    # Check health terms
    health_terms = [
        'heart rate', 'hrv', 'sleep', 'recovery', 'temperature', 'hr',
        'deep sleep', 'rem sleep', 'rem', 'light sleep', 'sleep efficiency',
        'total sleep', 'sleep time', 'bedtime', 'wake up', 'wake time', 'fall asleep',
        'glucose', 'blood sugar', 'metabolic score', 'metabolism', 'hba1c',
        'resting heart rate', 'rhr', 'vo2 max', 'vo2', 'fitness', 'movement', 'motion',
        'steps', 'active minutes', 'time in target'
    ]

    has_health = any(term in question_lower for term in health_terms)
    print(f"  Has health term: {has_health}")

    print(f"  Should be supported: {has_trend and has_health}")