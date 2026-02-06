#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from services.metrics_service import MetricsService, INTENT_PATTERNS
import re

def debug_correlation_processing():
    app = create_app()
    with app.app_context():
        service = MetricsService()

        test_queries = [
            "What relationship is between my heart rate and sleep",
            "Correlation between heart rate and sleep",
            "Is there a correlation between my heart rate and sleep?"
        ]

        print("Debugging Correlation Processing:")
        print("=" * 60)

        for query in test_queries:
            print(f"\nQuery: '{query}'")
            print("-" * 40)

            msg_lc = query.lower()

            # Test 1: Intent detection
            print("1. Intent Detection:")
            for intent_name, pattern in INTENT_PATTERNS.items():
                if pattern.search(msg_lc):
                    print(f"   ✅ Matches {intent_name}: {pattern.pattern}")
                else:
                    print(f"   ❌ No match {intent_name}")

            # Test 2: Correlation-specific check
            print("\n2. Correlation-Specific Checks:")
            is_correlation = service._is_correlation_query(msg_lc)
            print(f"   _is_correlation_query(): {is_correlation}")

            # Test 3: Lifestyle event check (should be False)
            print("\n3. Lifestyle Event Check:")
            is_lifestyle = service._is_lifestyle_event(msg_lc)
            print(f"   _is_lifestyle_event(): {is_lifestyle}")

            # Test 4: Full processing
            print("\n4. Full Processing:")
            try:
                result = service.process_sms_input("user_1598", query)
                print(f"   Success: {result.get('success')}")
                if result.get('success'):
                    insights = (result.get('immediate_insights', {}) or {}).get('insights', [])
                    if insights:
                        print(f"   Response: {insights[0].get('message', 'No message')[:100]}...")
                else:
                    print(f"   Error: {result.get('error', 'Unknown error')}")

            except Exception as e:
                print(f"   Exception: {str(e)}")
                import traceback
                traceback.print_exc()

            print("\n" + "="*40)

if __name__ == "__main__":
    debug_correlation_processing()