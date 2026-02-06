#!/usr/bin/env python3
"""
Debug the specific OpenAI issue in LLM analyzer
"""

import sys
import os
import time
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def debug_llm_analyzer():
    """Debug what's causing the LLM analyzer to fail"""

    print("🔍 DEBUGGING LLM ANALYZER OPENAI ISSUE")
    print("=" * 50)

    # Test 1: Direct OpenAI call (we know this works)
    print("📡 TEST 1: Direct OpenAI Call")
    print("-" * 30)

    try:
        from openai import OpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        clean_key = api_key.strip().replace('\n', '').replace('\r', '').replace(' ', '')

        client = OpenAI(api_key=clean_key, timeout=30)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=20
        )

        print(f"   ✅ Direct OpenAI works: {response.choices[0].message.content}")

    except Exception as e:
        print(f"   ❌ Direct OpenAI failed: {str(e)}")
        return

    print()

    # Test 2: LLM Analyzer initialization
    print("🧠 TEST 2: LLM Analyzer Components")
    print("-" * 30)

    try:
        from services.llm_chat_analyzer_pa import LLMChatAnalyzer

        analyzer = LLMChatAnalyzer()
        print("   ✅ LLM Analyzer created")
        print(f"   📊 Available functions: {len(analyzer.available_functions)}")
        print(f"   🔧 Function schemas: {len(analyzer.function_schemas)}")

    except Exception as e:
        print(f"   ❌ LLM Analyzer init failed: {str(e)}")
        return

    print()

    # Test 3: Replicate the exact call that's failing
    print("🎯 TEST 3: Replicate LLM Analyzer Call")
    print("-" * 30)

    try:
        # This replicates the exact call in _analyze_message_pa_optimized
        user_id = 'user_7000'
        message = "Hello, how are you?"

        print(f"   🔍 Testing message: '{message}'")
        print(f"   👤 User ID: {user_id}")

        # Replicate the system prompt
        system_prompt = f"""You are a health assistant analyzing Ultrahuman data via SMS.
User: {user_id}
Keep responses under 1000 chars. Use available functions for health data."""

        print(f"   📝 System prompt length: {len(system_prompt)} chars")

        # Make the exact same call as the LLM analyzer
        start_time = time.time()

        response = analyzer.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            tools=[{"type": "function", "function": schema} for schema in analyzer.function_schemas[:3]],
            tool_choice="auto",
            temperature=0.5,
            max_tokens=800,
            timeout=analyzer.default_timeout
        )

        duration = time.time() - start_time

        message_response = response.choices[0].message

        print(f"   ✅ LLM call succeeded! ({duration:.1f}s)")
        print(f"   📱 Response: {message_response.content[:80]}...")

        if message_response.tool_calls:
            print(f"   🔧 Tool calls detected: {len(message_response.tool_calls)}")
            for tool_call in message_response.tool_calls:
                print(f"      - {tool_call.function.name}")
        else:
            print("   💬 Direct response (no tool calls)")

    except Exception as e:
        print(f"   ❌ Replicated call failed: {str(e)}")
        print(f"   🔍 Error type: {type(e).__name__}")
        print(f"   📝 Full error: {str(e)}")

        # Check specific error conditions
        if "timeout" in str(e).lower():
            print("   💡 This is a timeout issue - try increasing timeout")
        elif "connection" in str(e).lower():
            print("   💡 This is a connection issue - network problem")
        elif "rate" in str(e).lower():
            print("   💡 This is a rate limiting issue")
        elif "function" in str(e).lower():
            print("   💡 This might be a function schema issue")

        return

    print()

    # Test 4: Test the analyze_message method directly
    print("🎪 TEST 4: Full analyze_message Method")
    print("-" * 30)

    try:
        print("   🔍 Calling analyzer.analyze_message()...")

        start_time = time.time()
        final_response = analyzer.analyze_message("Hello, how are you?", user_id)
        duration = time.time() - start_time

        print(f"   ⏱️ Total time: {duration:.1f}s")
        print(f"   📏 Response length: {len(final_response)} chars")
        print(f"   📱 Final response: {final_response}")

        if "🤖 ChatGPT" in final_response:
            print("   ⚠️ Error response detected - there's still an issue")
        else:
            print("   ✅ analyze_message working correctly!")

    except Exception as e:
        print(f"   ❌ analyze_message failed: {str(e)}")

    print()
    print("🎯 CONCLUSION:")
    print("This will show exactly where the OpenAI call is failing")

if __name__ == '__main__':
    debug_llm_analyzer()