#!/usr/bin/env python3
"""
Debug OpenAI Connection Issues
"""

import sys
import os
import requests
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def debug_openai_connection():
    """Debug OpenAI connection issues step by step"""

    print("🔍 DEBUGGING OPENAI CONNECTION")
    print("=" * 50)

    # Check API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    print(f"✅ API Key found: {openai_key[:8]}...{openai_key[-8:]}")
    print(f"   Length: {len(openai_key)} characters")

    # Check if key looks valid (should start with sk-)
    if not openai_key.startswith('sk-'):
        print("⚠️ API key doesn't start with 'sk-' - might be invalid format")
    else:
        print("✅ API key format looks correct")

    # Test basic internet connectivity
    print("\n🌐 Testing internet connectivity...")
    try:
        response = requests.get('https://httpbin.org/status/200', timeout=10)
        if response.status_code == 200:
            print("✅ Internet connection working")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"❌ Internet connection failed: {str(e)}")
        return False

    # Test OpenAI API endpoint accessibility
    print("\n🔗 Testing OpenAI API endpoint accessibility...")
    try:
        # Just test if we can reach the endpoint (not authenticated)
        response = requests.get('https://api.openai.com/v1/models', timeout=10)
        if response.status_code == 401:
            print("✅ OpenAI API endpoint accessible (got auth error as expected)")
        elif response.status_code == 200:
            print("✅ OpenAI API endpoint accessible")
        else:
            print(f"⚠️ Unexpected response from OpenAI: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach OpenAI API: {str(e)}")
        return False

    # Test authenticated request
    print("\n🔑 Testing authenticated OpenAI request...")
    try:
        headers = {
            'Authorization': f'Bearer {openai_key}',
            'Content-Type': 'application/json'
        }

        # Test with a simple models list request
        response = requests.get(
            'https://api.openai.com/v1/models',
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            print("✅ Authentication successful!")
            models_data = response.json()
            model_count = len(models_data.get('data', []))
            print(f"   Found {model_count} available models")

            # Check if GPT-4 is available
            model_ids = [model['id'] for model in models_data.get('data', [])]
            gpt4_models = [m for m in model_ids if 'gpt-4' in m]
            gpt35_models = [m for m in model_ids if 'gpt-3.5' in m]

            print(f"   GPT-4 models: {len(gpt4_models)}")
            print(f"   GPT-3.5 models: {len(gpt35_models)}")

            return True

        elif response.status_code == 401:
            print("❌ Authentication failed - invalid API key")
            print("   Check your OpenAI API key")
        elif response.status_code == 429:
            print("❌ Rate limited or quota exceeded")
            print("   Check your OpenAI billing and usage")
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

        if "timeout" in str(e).lower():
            print("   Issue: Request timeout - try again or check connection")
        elif "ssl" in str(e).lower():
            print("   Issue: SSL/TLS problem - check certificates")
        elif "connection" in str(e).lower():
            print("   Issue: Connection problem - check firewall/proxy")

    # Test with OpenAI Python client
    print("\n🐍 Testing OpenAI Python client...")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)

        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'test successful' if you can see this"}
            ],
            max_tokens=10,
            timeout=30
        )

        content = response.choices[0].message.content
        print(f"✅ OpenAI client working! Response: {content}")

        return True

    except Exception as e:
        print(f"❌ OpenAI client failed: {str(e)}")

        # Specific error handling
        error_str = str(e).lower()
        if "api key" in error_str:
            print("   Issue: API key problem")
        elif "rate limit" in error_str or "quota" in error_str:
            print("   Issue: Rate limit or billing issue")
        elif "timeout" in error_str:
            print("   Issue: Request timeout")
        elif "connection" in error_str:
            print("   Issue: Network connection problem")
        else:
            print("   Issue: Unknown error")

    print("\n🔧 TROUBLESHOOTING STEPS:")
    print("1. Verify your OpenAI API key is correct")
    print("2. Check OpenAI billing/credits at platform.openai.com")
    print("3. Try a different network connection")
    print("4. Check if there are any firewall/proxy restrictions")
    print("5. Wait a few minutes and try again (temporary issue)")

    return False

if __name__ == '__main__':
    success = debug_openai_connection()
    if success:
        print("\n🎉 OpenAI connection is working! You can proceed with LLM testing.")
    else:
        print("\n⚠️ OpenAI connection issues detected. Fix these first.")