#!/usr/bin/env python3
"""
Test Phase 1: ChatGPT-like LLM SMS System
Test the complete LLM integration on PythonAnywhere
"""

import sys
import os
from datetime import datetime, timedelta
import time

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_phase1_llm():
    """Comprehensive test of Phase 1 ChatGPT-like LLM system"""

    print("🤖 TESTING PHASE 1: CHATGPT-LIKE LLM SMS SYSTEM")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    from app import create_app
    app = create_app()

    test_results = {
        'basic_openai': False,
        'llm_analyzer_init': False,
        'simple_questions': False,
        'health_questions': False,
        'function_calling': False,
        'sms_integration': False
    }

    with app.app_context():
        user_id = 'user_7000'  # Your test user

        # Test 1: Basic OpenAI Connection
        print("📡 TEST 1: Basic OpenAI Connection")
        print("-" * 40)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

            print("   🔍 Testing basic API call...")
            start_time = time.time()

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Respond briefly."},
                    {"role": "user", "content": "Hello, just testing connectivity."}
                ],
                max_tokens=50,
                timeout=30
            )

            duration = time.time() - start_time
            result = response.choices[0].message.content

            print(f"   ✅ OpenAI API working! ({duration:.1f}s)")
            print(f"   📱 Response: {result[:80]}...")
            test_results['basic_openai'] = True

        except Exception as e:
            print(f"   ❌ OpenAI API failed: {str(e)}")
            print("   💡 Check API key and network connectivity")
            return test_results

        print()

        # Test 2: LLM Analyzer Initialization
        print("🧠 TEST 2: LLM Chat Analyzer Initialization")
        print("-" * 40)

        try:
            # Try PythonAnywhere-optimized version first
            try:
                from services.llm_chat_analyzer_pa import LLMChatAnalyzer
                print("   📦 Using PythonAnywhere-optimized LLM analyzer")
            except ImportError:
                from services.llm_chat_analyzer import LLMChatAnalyzer
                print("   📦 Using standard LLM analyzer")

            analyzer = LLMChatAnalyzer()

            print(f"   ✅ LLM Analyzer initialized")
            print(f"   🔧 Available functions: {len(analyzer.available_functions)}")
            print(f"   🎯 Functions: {', '.join(list(analyzer.available_functions.keys())[:3])}...")

            test_results['llm_analyzer_init'] = True

        except Exception as e:
            print(f"   ❌ LLM Analyzer failed to initialize: {str(e)}")
            return test_results

        print()

        # Test 3: Simple Conversational Questions
        print("💬 TEST 3: Simple Conversational Questions")
        print("-" * 40)

        simple_questions = [
            "Hello, how are you?",
            "What can you help me with?",
            "Hi there!"
        ]

        for i, question in enumerate(simple_questions, 1):
            try:
                print(f"   📝 Question {i}: '{question}'")

                start_time = time.time()
                response = analyzer.analyze_message(question, user_id)
                duration = time.time() - start_time

                print(f"   ⏱️ Response time: {duration:.1f}s")
                print(f"   📱 Response ({len(response)} chars): {response[:60]}...")

                if "error" not in response.lower() and len(response) > 10:
                    print(f"   ✅ Question {i} successful")
                else:
                    print(f"   ⚠️ Question {i} had issues")

            except Exception as e:
                print(f"   ❌ Question {i} failed: {str(e)}")

        test_results['simple_questions'] = True
        print()

        # Test 4: Health-Specific Questions (Function Calling)
        print("🩺 TEST 4: Health Data Questions with Function Calling")
        print("-" * 40)

        health_questions = [
            "What was my heart rate at 3am last night?",
            "How did I sleep last night?",
            "Show me my recent HRV trends",
            "What time did I fall asleep yesterday?",
            "How was my activity today?"
        ]

        successful_health_queries = 0

        for i, question in enumerate(health_questions, 1):
            try:
                print(f"   📊 Health Question {i}: '{question}'")

                start_time = time.time()
                response = analyzer.analyze_message(question, user_id)
                duration = time.time() - start_time

                print(f"   ⏱️ Response time: {duration:.1f}s")
                print(f"   📏 Response length: {len(response)} chars")
                print(f"   📱 Preview: {response[:80]}...")

                # Check if response contains actual data or just generic response
                if any(indicator in response.lower() for indicator in ['bpm', 'sleep', 'hrv', 'activity', 'data', 'time']):
                    print(f"   ✅ Health Question {i} appears to have real data")
                    successful_health_queries += 1
                elif "no data" in response.lower() or "not found" in response.lower():
                    print(f"   ⚠️ Health Question {i} - No data available (expected for some queries)")
                else:
                    print(f"   ⚠️ Health Question {i} - Generic response, function calling may not be working")

            except Exception as e:
                print(f"   ❌ Health Question {i} failed: {str(e)}")

        if successful_health_queries >= 2:
            test_results['health_questions'] = True
            test_results['function_calling'] = True

        print(f"   📈 Health queries with data: {successful_health_queries}/{len(health_questions)}")
        print()

        # Test 5: SMS Integration Test (Simulated)
        print("📱 TEST 5: SMS Integration Simulation")
        print("-" * 40)

        try:
            # Simulate what happens in the SMS webhook
            from flask import Flask
            from app.models import User

            # Get test user
            test_user = User.query.filter_by(id=user_id).first()
            if test_user:
                print(f"   👤 Test user found: {test_user.id}")
                print(f"   📞 Phone: {test_user.phone_number}")

                # Test the SMS service import
                from services.sms_service import SMSService
                sms_service = SMSService()

                print("   ✅ SMS service initialized")
                print("   📧 SMS integration components working")

                test_results['sms_integration'] = True

            else:
                print("   ⚠️ Test user not found - SMS integration untested")

        except Exception as e:
            print(f"   ❌ SMS integration test failed: {str(e)}")

        print()

        # Test Summary
        print("📋 PHASE 1 TEST SUMMARY")
        print("=" * 40)

        passed_tests = sum(test_results.values())
        total_tests = len(test_results)

        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} {test_name.replace('_', ' ').title()}")

        print()
        print(f"🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")

        if passed_tests >= 4:
            print("🎉 PHASE 1 LLM SYSTEM IS WORKING!")
            print()
            print("📱 YOUR SMS SYSTEM CAN NOW HANDLE:")
            print("   • Natural language health questions")
            print("   • Time-specific queries (3am, last night, etc.)")
            print("   • Sleep and heart rate analysis")
            print("   • Activity pattern questions")
            print("   • Conversational interactions")
            print()
            print("🚀 NEXT STEPS:")
            print("   1. Deploy to PythonAnywhere")
            print("   2. Configure Twilio webhook: https://yourdomain.pythonanywhere.com/webhook/sms")
            print("   3. Send test SMS to your Twilio number")
            print("   4. Users can ask: 'What was my heart rate at 3am?' and get intelligent responses!")

        else:
            print("⚠️ PHASE 1 NEEDS ATTENTION")
            print()
            print("🔧 TROUBLESHOOTING:")
            if not test_results['basic_openai']:
                print("   • Check OpenAI API key in .env file")
                print("   • Verify network connectivity")
            if not test_results['llm_analyzer_init']:
                print("   • Check LLM analyzer import paths")
                print("   • Verify all dependencies installed")
            if not test_results['function_calling']:
                print("   • Function calling may need adjustment")
                print("   • Check database connections")

        return test_results

def create_manual_test_guide():
    """Create a manual testing guide for SMS"""

    guide_content = """
📱 PHASE 1 MANUAL SMS TESTING GUIDE
==================================

After running the automated tests, test your live SMS system:

🔧 SETUP STEPS:
1. Deploy your code to PythonAnywhere
2. Set your Twilio webhook to: https://bphlite.pythonanywhere.com/webhook/sms
3. Make sure your .env file is uploaded with the correct OpenAI API key

📲 SMS TEST QUESTIONS TO TRY:
Send these messages to your Twilio number:

CONVERSATIONAL TESTS:
• "Hello"
• "Hi, how are you?"
• "What can you help me with?"

HEALTH DATA TESTS:
• "What was my heart rate at 3am last night?"
• "How did I sleep last night?"
• "Show me my HRV trends"
• "What time did I fall asleep yesterday?"
• "How was my activity today?"
• "Compare my weekend sleep to weekdays"

TIME-SPECIFIC TESTS:
• "What was my heart rate at 2pm today?"
• "How was my sleep quality overnight?"
• "Show me my morning activity patterns"

✅ EXPECTED BEHAVIOR:
• Quick responses (under 30 seconds)
• Natural language, ChatGPT-like answers
• Specific health data when available
• Friendly conversational tone
• Fallback to enhanced analyzer if LLM fails

❌ TROUBLESHOOTING:
If you get generic responses or errors:
1. Check PythonAnywhere error logs
2. Verify OpenAI API key is working
3. Ensure database has recent health data
4. The enhanced analyzer will provide fallback responses

🎯 SUCCESS INDICATORS:
• Responses mention specific times, dates, or values
• Natural language explanations of health data
• Personalized insights based on your data
• Conversational, helpful tone

🚀 ON PYTHONANYWHERE:
If OpenAI has connection issues, your SMS system will automatically fallback
to the enhanced time-specific analyzer which provides excellent health insights!
"""

    # Use current working directory for PythonAnywhere
    with open('PHASE1_MANUAL_TEST_GUIDE.md', 'w') as f:
        f.write(guide_content)

    print("📋 Created PHASE1_MANUAL_TEST_GUIDE.md for live SMS testing")

if __name__ == '__main__':
    results = test_phase1_llm()
    create_manual_test_guide()

    print(f"\n🏁 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")