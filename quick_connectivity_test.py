#!/usr/bin/env python3
"""
Test OpenAI on upgraded PythonAnywhere account
"""

import os
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

def test_upgraded_pythonanywhere():
    """Test OpenAI connection on upgraded PythonAnywhere"""

    print("🚀 TESTING UPGRADED PYTHONANYWHERE OPENAI")
    print("=" * 50)
    print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Clean the API key first
    print("🔧 STEP 1: Clean API Key")
    print("-" * 30)

    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        # Clean the key aggressively
        clean_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')

        print(f"   🔍 Original length: {len(api_key)}")
        print(f"   ✨ Cleaned length: {len(clean_key)}")
        print(f"   🔑 Clean key preview: {clean_key[:30]}...")

        # Update environment
        os.environ['OPENAI_API_KEY'] = clean_key

    else:
        print("   ❌ No API key found")
        return False

    print()

    # Test OpenAI with various configurations
    print("🤖 STEP 2: OpenAI Connection Tests")
    print("-" * 30)

    try:
        from openai import OpenAI

        # Test 1: Basic connection with clean key
        try:
            print("   🔍 Test 1: Basic connection...")
            client = OpenAI(api_key=clean_key, timeout=60)

            start_time = time.time()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say hello briefly."}
                ],
                max_tokens=20
            )
            duration = time.time() - start_time

            result = response.choices[0].message.content
            print(f"   ✅ SUCCESS! ({duration:.1f}s): {result}")

            return True

        except Exception as e:
            print(f"   ❌ Basic test failed: {str(e)}")

        # Test 2: Different model
        try:
            print("   🔍 Test 2: Different model...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            result = response.choices[0].message.content
            print(f"   ✅ GPT-4o-mini works: {result}")
            return True

        except Exception as e:
            print(f"   ❌ GPT-4o-mini failed: {str(e)}")

        # Test 3: Minimal request
        try:
            print("   🔍 Test 3: Minimal request...")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5
            )
            result = response.choices[0].message.content
            print(f"   ✅ Minimal request works: {result}")
            return True

        except Exception as e:
            print(f"   ❌ Minimal request failed: {str(e)}")

            # Show detailed error info
            print(f"   🔍 Error type: {type(e).__name__}")
            print(f"   📝 Full error: {str(e)}")

    except ImportError as e:
        print(f"   ❌ OpenAI import failed: {str(e)}")

    print()

    # Network diagnostics
    print("🌐 STEP 3: Network Diagnostics")
    print("-" * 30)

    try:
        import requests

        # Test OpenAI API endpoint directly
        try:
            headers = {
                'Authorization': f'Bearer {clean_key}',
                'Content-Type': 'application/json'
            }

            # Simple API test
            test_data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                json=test_data,
                headers=headers,
                timeout=30
            )

            print(f"   📊 HTTP Status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                message = result['choices'][0]['message']['content']
                print(f"   ✅ Direct API call works: {message}")
                return True
            else:
                print(f"   ❌ API Error: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Direct API test failed: {str(e)}")

    except ImportError:
        print("   ⚠️ requests not available")

    return False

def test_sms_system():
    """Test the complete SMS system"""

    print()
    print("📱 STEP 4: SMS System Test")
    print("-" * 30)

    try:
        import sys
        import os

        # Add project path
        project_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, project_dir)

        from services.llm_chat_analyzer_pa import LLMChatAnalyzer

        analyzer = LLMChatAnalyzer()
        print("   ✅ LLM Analyzer initialized")

        # Test with clean key
        test_message = "Hello, I'm testing my health assistant"

        print(f"   🔍 Testing message: '{test_message}'")
        start_time = time.time()

        response = analyzer.analyze_message(test_message, "user_7000")
        duration = time.time() - start_time

        print(f"   ⏱️ Response time: {duration:.1f}s")
        print(f"   📏 Response length: {len(response)} chars")
        print(f"   📱 Preview: {response[:100]}...")

        if response and "Connection error" not in response:
            print("   ✅ SMS System working perfectly!")
            return True
        else:
            print("   ❌ SMS System has connection issues")
            return False

    except Exception as e:
        print(f"   ❌ SMS System test failed: {str(e)}")
        return False

if __name__ == '__main__':
    openai_works = test_upgraded_pythonanywhere()

    if openai_works:
        sms_works = test_sms_system()

        if sms_works:
            print("\n🎉 PERFECT! YOUR CHATGPT SMS SYSTEM IS FULLY OPERATIONAL!")
            print()
            print("🚀 READY FOR LIVE TESTING:")
            print("1. Configure Twilio webhook: https://bphlite.pythonanywhere.com/webhook/sms")
            print("2. Send SMS from +15875452951")
            print("3. Try: 'Hello, how are you?'")
            print("4. Try: 'What was my heart rate at 3am last night?'")
            print("5. Expect intelligent ChatGPT responses!")
        else:
            print("\n⚠️ OpenAI works but SMS system needs adjustment")
    else:
        print("\n❌ OpenAI connection still has issues on upgraded PythonAnywhere")
        print("Let's troubleshoot further...")