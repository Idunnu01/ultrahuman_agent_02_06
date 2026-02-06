#!/usr/bin/env python3
"""
Quick test for trend analysis
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def quick_trend_test():
    """Quick test of trend analysis"""

    print("❓ Question: What's my heart rate trend over time?")
    print("=" * 60)

    from app import create_app
    from services.sms_health_analyzer import SMSHealthAnalyzer

    app = create_app()

    with app.app_context():
        analyzer = SMSHealthAnalyzer()

        user_id = 'user_7000'  # Your user ID
        question = "What's my heart rate trend over time?"

        response = analyzer.analyze_question(question, user_id)

        if response:
            print(response)

if __name__ == '__main__':
    quick_trend_test()