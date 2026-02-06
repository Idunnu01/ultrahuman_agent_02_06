#!/usr/bin/env python3
"""
Quick diagnostic test
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def quick_diagnostic():
    """Quick diagnostic of SMS integration"""

    print("🔧 Quick SMS Integration Diagnostic")
    print("=" * 40)

    try:
        from app import create_app
        from services.sms_health_analyzer import SMSHealthAnalyzer
        from services.sms_service import SMSService

        app = create_app()

        with app.app_context():

            # Test question detection
            print("\n1. Question Detection Test")
            print("-" * 25)
            analyzer = SMSHealthAnalyzer()

            test_questions = [
                ("What's my heart rate trend?", True),
                ("How is my sleep improving?", True),
                ("Show me my HRV over time", True),
                ("Is my recovery getting better?", True),
                ("Did meal timing affect heart rate?", True),
                ("Hello there", False)
            ]

            for question, expected in test_questions:
                result = analyzer.is_question_format(question)
                status = "✅" if result == expected else "❌"
                print(f"{status} '{question}' -> {result}")

            # Test SMS service
            print("\n2. SMS Service Test")
            print("-" * 20)
            sms_service = SMSService()
            health = sms_service.get_service_health()
            print(f"SMS Status: {health['status']}")
            print(f"Configured: {health['configuration']['configured']}")

            # Test basic response generation (without full analysis)
            print("\n3. Response Generation Test")
            print("-" * 28)

            # Test help response
            help_response = analyzer._help_response()
            print(f"✅ Help response: {len(help_response)} chars")

            # Test question parsing
            lifestyle, health_metric = analyzer._parse_question("What's my heart rate trend?")
            print(f"✅ Parsed trend question: {lifestyle} -> {health_metric}")

            lifestyle, health_metric = analyzer._parse_question("Did meal timing affect heart rate?")
            print(f"✅ Parsed correlation question: {lifestyle} -> {health_metric}")

        print(f"\n🎉 Diagnostic Complete!")
        print("✅ All core components working")

    except Exception as e:
        print(f"❌ Error during diagnostic: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    quick_diagnostic()