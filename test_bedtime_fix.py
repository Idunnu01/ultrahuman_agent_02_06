#!/usr/bin/env python3
"""
Test the fixed bedtime analysis
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_bedtime_fix():
    """Test that bedtime questions now work with actual bedtime data"""

    print("🛌 TESTING FIXED BEDTIME ANALYSIS")
    print("=" * 50)

    from app import create_app
    from services.sms_health_analyzer import SMSHealthAnalyzer

    app = create_app()

    with app.app_context():
        analyzer = SMSHealthAnalyzer()
        user_id = 'user_7000'

        # Test bedtime question
        question = "What time did I fall asleep last night?"

        print(f"📱 Question: '{question}'")
        print()
        print("🔍 Processing...")

        response = analyzer.analyze_question(question, user_id)

        print("📋 RESPONSE:")
        print("=" * 20)
        print(response)

        print("\n" + "=" * 50)
        print("💡 EXPECTED IMPROVEMENT:")
        print("   ✅ Should now show actual bedtime: 9:33 PM")
        print("   ✅ Should use precise bedtime_full timestamp")
        print("   ✅ Should provide bedtime insights and averages")

if __name__ == '__main__':
    test_bedtime_fix()