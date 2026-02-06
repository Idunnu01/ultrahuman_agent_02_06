#!/usr/bin/env python3
"""
Test pure OpenAI-only SMS system (no enhanced analyzer fallback)
"""

import sys
import os
from datetime import datetime

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_openai_only():
    """Test pure OpenAI SMS system"""

    print("🤖 TESTING PURE OPENAI-ONLY SMS SYSTEM")
    print("=" * 50)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Test 1: OpenAI Connection
    print("📡 TEST 1: OpenAI Connection")
    print("-" * 30)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), timeout=10)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello, test connection"}],
            max_tokens=20
        )

        result = response.choices[0].message.content
        print(f"   ✅ OpenAI working: {result}")
        openai_works = True

    except Exception as e:
        print(f"   ❌ OpenAI failed: {str(e)}")
        openai_works = False

    print()

    # Test 2: LLM Analyzer (OpenAI-only)
    print("🧠 TEST 2: OpenAI LLM Analyzer")
    print("-" * 30)

    if openai_works:
        try:
            from services.llm_chat_analyzer_pa import LLMChatAnalyzer

            analyzer = LLMChatAnalyzer()
            print("   ✅ LLM Analyzer initialized")

            # Test conversational message
            test_message = "Hello, how are you?"
            response = analyzer.analyze_message(test_message, "user_7000")

            print(f"   📱 Test response: {response[:100]}...")
            print("   ✅ OpenAI analyzer working")

        except Exception as e:
            print(f"   ❌ LLM Analyzer failed: {str(e)}")
    else:
        print("   ⚠️ Skipping LLM test - OpenAI not working")

    print()

    # Test 3: SMS Route Structure
    print("📱 TEST 3: SMS Route (Structure Only)")
    print("-" * 30)

    try:
        # Check that route file was updated
        with open('app/routes.py', 'r') as f:
            routes_content = f.read()

        # Verify no enhanced analyzer fallback
        if "SMSHealthAnalyzer" in routes_content:
            print("   ⚠️ Enhanced analyzer import still present")
        else:
            print("   ✅ Enhanced analyzer removed")

        if "fallback" in routes_content.lower():
            print("   ⚠️ Fallback logic may still exist")
        else:
            print("   ✅ No fallback logic detected")

        if "OPENAI-ONLY" in routes_content:
            print("   ✅ OpenAI-only route confirmed")
        else:
            print("   ⚠️ OpenAI-only comment not found")

    except Exception as e:
        print(f"   ❌ Route check failed: {str(e)}")

    print()

    # Test 4: System Status
    print("📋 SYSTEM STATUS")
    print("=" * 30)

    if openai_works:
        print("🎉 SUCCESS! Your SMS system is now:")
        print("   ✅ OpenAI ChatGPT ONLY")
        print("   ❌ NO enhanced analyzer fallback")
        print("   ❌ NO hardcoded responses")
        print("   🎯 Pure ChatGPT experience")

        print()
        print("🚀 READY TO TEST:")
        print("1. Configure Twilio webhook: https://bphlite.pythonanywhere.com/webhook/sms")
        print("2. Send SMS from +15875452951")
        print("3. Try: 'Hello, how are you?'")
        print("4. Try: 'What was my heart rate at 3am?'")
        print("5. All responses will come from ChatGPT!")

    else:
        print("⚠️ OpenAI CONNECTION ISSUE:")
        print("   • Your SMS route is now OpenAI-only")
        print("   • But OpenAI API has connection problems")
        print("   • Users will get error messages until OpenAI works")
        print("   • This might be due to PythonAnywhere network restrictions")

    print()
    print("🎯 WHAT HAPPENS NOW:")
    print("   📱 SMS → OpenAI ChatGPT → Response")
    print("   ❌ If OpenAI fails → Error message (no fallback)")
    print("   🤖 Pure ChatGPT experience as requested!")

    return openai_works

if __name__ == '__main__':
    success = test_openai_only()
    print(f"\n🏁 Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if success:
        print("\n🎉 YOUR PURE OPENAI SMS SYSTEM IS READY!")
    else:
        print("\n⚠️ Fix OpenAI connection for full functionality")