#!/usr/bin/env python3
"""
Test SMS health question answering
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_sms_questions():
    """Test SMS question answering with your data"""

    print("🧪 Testing SMS Health Question Answering")
    print("=" * 50)

    from app import create_app
    from services.sms_health_analyzer import SMSHealthAnalyzer

    app = create_app()

    with app.app_context():
        analyzer = SMSHealthAnalyzer()

        test_questions = [
            # Correlation/Comparison Analysis
            "Did my meal timing affect my heart rate?",
            "How does magnesium impact my HRV?",
            "Does exercise correlate with recovery?",
            "Did supplements affect sleep score?",
            "What about temperature and heart rate?",

            # Trend Analysis Questions
            "What's my heart rate trend over time?",
            "How is my sleep score trending?",
            "Show me my HRV average over time",
            "Is my recovery improving?",
            "What's my weekly heart rate average?",
            "How has my temperature been trending?",
            "Show me my steps trend",
            "Is my activity getting better over time?",

            # NEW: Sleep-Specific Questions (Deep Sleep & REM)
            "How much deep sleep did I get last night?",
            "What's my REM sleep pattern this week?",
            "How is my deep sleep trending over time?",
            "What time did I fall asleep last night?",
            "How long was my total sleep time yesterday?",
            "What's my sleep efficiency been like?",
            "Did I get enough REM sleep this week?",
            "How does my deep sleep compare to last week?",
            "What time do I usually wake up?",
            "How consistent are my sleep times?",
            "What's my average bedtime this month?",
            "How much light sleep vs deep sleep do I get?",
            "Is my sleep quality improving over time?",
            "What nights had the best REM sleep?",
            "How does weekend sleep compare to weekdays?",

            # Time-Based Analysis Questions
            "What was my heart rate at 3am last night?",
            "How was my HRV during sleep hours?",
            "What's my temperature pattern overnight?",
            "When do I have the highest heart rate each day?",
            "How does my morning HRV compare to evening?",
            "What time of day are my steps highest?",
            "How does my recovery vary by day of week?",
            "What's my heart rate pattern during sleep?"
        ]

        user_id = 'user_7000'  # Your user ID

        for question in test_questions:
            print(f"\n❓ Question: {question}")
            print("=" * 60)

            response = analyzer.analyze_question(question, user_id)

            # Now responses are returned as strings, so print them
            if response:
                print(response)
                print("=" * 60)

if __name__ == '__main__':
    test_sms_questions()
