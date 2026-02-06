#!/usr/bin/env python3
"""
Basic LLM Test - Check OpenAI API connection and basic functionality
"""

import sys
import os
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_basic_llm():
    """Test basic LLM functionality without function calling"""

    print("🧪 BASIC LLM CONNECTION TEST")
    print("=" * 50)

    # Check API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False

    print(f"✅ API Key found: ...{openai_key[-8:]}")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)

        # Simple test call
        print("🔍 Testing OpenAI API connection...")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use cheaper model for testing
            messages=[
                {"role": "system", "content": "You are a helpful health assistant."},
                {"role": "user", "content": "Say 'Hello! I'm working correctly.' if you can see this message."}
            ],
            max_tokens=50,
            temperature=0.5,
            timeout=30  # Add explicit timeout
        )

        content = response.choices[0].message.content
        print(f"✅ OpenAI Response: {content}")

        # Test with a health question (no function calling)
        print("\\n💓 Testing health question processing...")

        health_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a health assistant. The user might ask about heart rate, sleep, or other health metrics.
                    Respond helpfully but note that you don't have access to their actual health data in this test."""
                },
                {"role": "user", "content": "What was my heart rate at 3am?"}
            ],
            max_tokens=100,
            temperature=0.7,
            timeout=30
        )

        health_content = health_response.choices[0].message.content
        print(f"✅ Health Question Response: {health_content}")

        print("\\n🎉 BASIC LLM TEST PASSED")
        print("   OpenAI API is working correctly")
        print("   Ready for function calling integration")

        return True

    except Exception as e:
        print(f"❌ OpenAI API Error: {str(e)}")

        if "api_key" in str(e).lower():
            print("💡 Issue: API key problem")
            print("   - Check your OpenAI API key")
            print("   - Verify billing/credits")
        elif "model" in str(e).lower():
            print("💡 Issue: Model access problem")
            print("   - Try different model (gpt-3.5-turbo)")
            print("   - Check API permissions")
        else:
            print("💡 Issue: Connection or other error")
            print("   - Check internet connection")
            print("   - Verify OpenAI service status")

        return False

if __name__ == '__main__':
    success = test_basic_llm()
    if success:
        print("\\n🚀 Next: Run test_llm_phase1.py for full function calling test")
    else:
        print("\\n🔧 Fix basic connectivity first before proceeding")