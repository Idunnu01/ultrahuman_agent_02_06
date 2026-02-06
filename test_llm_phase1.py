#!/usr/bin/env python3
"""
Test Script for Phase 1: Core LLM Integration
Test the ChatGPT-like natural language processing for health questions
"""

import sys
import os
from datetime import datetime, timedelta

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_llm_phase1():
    """Comprehensive test of Phase 1 LLM integration"""

    print("🧪 TESTING PHASE 1: CORE LLM INTEGRATION")
    print("=" * 60)

    from app import create_app
    from services.llm_chat_analyzer import LLMChatAnalyzer

    app = create_app()

    with app.app_context():
        user_id = 'user_7000'

        # Check environment setup
        print("🔧 ENVIRONMENT CHECK")
        print("-" * 40)

        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            print(f"   ✅ OpenAI API Key: Present (ends with ...{openai_key[-8:]})")
        else:
            print(f"   ❌ OpenAI API Key: Missing")
            print(f"      Add OPENAI_API_KEY to your .env file")
            return

        # Initialize the LLM analyzer
        print(f"\\n🤖 INITIALIZING LLM ANALYZER")
        print("-" * 40)

        try:
            analyzer = LLMChatAnalyzer()
            print(f"   ✅ LLMChatAnalyzer initialized successfully")
            print(f"   📊 Available functions: {len(analyzer.available_functions)}")
            print(f"   🔧 Function schemas: {len(analyzer.function_schemas)}")
        except Exception as e:
            print(f"   ❌ Initialization failed: {str(e)}")
            return

        # Test messages - natural language health questions
        test_messages = [
            # Specific time queries
            ("🌙 3AM Analysis", "What was my heart rate at 3am last night?"),
            ("🌅 Morning Pattern", "How's my morning heart rate compared to evening?"),

            # Sleep analysis
            ("😴 Sleep Quality", "How did I sleep last night?"),
            ("🛌 Bedtime Pattern", "What time do I usually go to bed?"),

            # General health trends
            ("💓 Heart Rate Trends", "Show me my heart rate trends this week"),
            ("📈 HRV Analysis", "How is my HRV doing?"),

            # Comparative analysis
            ("📅 Weekend vs Weekday", "How does my weekend sleep compare to weekdays?"),
            ("🏃 Activity Patterns", "When am I most active during the day?"),

            # Conversational/natural language
            ("💬 Natural Question", "I've been feeling tired lately, what does my data show?"),
            ("🤔 General Wellness", "How's my overall health been this week?"),
        ]

        results = []
        successful_tests = 0
        total_response_time = 0

        for i, (category, message) in enumerate(test_messages, 1):
            print(f"\\n{category} ({i}/{len(test_messages)})")
            print("-" * len(category))
            print(f"Question: '{message}'")

            try:
                start_time = datetime.now()
                response = analyzer.analyze_message(message, user_id)
                end_time = datetime.now()

                response_time = (end_time - start_time).total_seconds()
                total_response_time += response_time

                # Check response quality
                if response and len(response) > 20:
                    if "error" in response.lower() and "technical difficulties" in response.lower():
                        status = "⚠️ ERROR RESPONSE"
                    elif "function" in response.lower() or "available" in response.lower():
                        status = "🔧 FUNCTION ISSUE"
                    elif any(word in response.lower() for word in ["heart rate", "sleep", "hrv", "analysis", "data", "average"]):
                        status = "✅ SUCCESS"
                        successful_tests += 1
                    else:
                        status = "❓ UNCLEAR"
                else:
                    status = "❌ NO RESPONSE"

                print(f"Status: {status}")
                print(f"Response time: {response_time:.2f}s")
                print(f"Response length: {len(response)} characters")

                # Show response preview
                response_preview = response.replace('\\n', ' | ')[:100]
                print(f"Preview: {response_preview}...")

                results.append({
                    'category': category,
                    'message': message,
                    'status': status,
                    'response_time': response_time,
                    'response_length': len(response),
                    'response': response
                })

            except Exception as e:
                print(f"❌ ERROR: {str(e)}")
                results.append({
                    'category': category,
                    'message': message,
                    'status': "❌ EXCEPTION",
                    'error': str(e)
                })

        # Test function calling directly
        print(f"\\n🔧 DIRECT FUNCTION TESTING")
        print("-" * 40)

        function_tests = [
            ("Recent HR Data", "get_recent_health_data", {"metric_types": ["heart_rate"], "hours_back": 24}),
            ("Sleep Analysis", "get_sleep_analysis", {"analysis_type": "bedtime", "days_back": 7}),
            ("Activity Patterns", "get_activity_patterns", {"pattern_type": "daily_rhythm"}),
        ]

        function_results = {}

        for test_name, function_name, args in function_tests:
            try:
                args['user_id'] = user_id
                if function_name in analyzer.available_functions:
                    result = analyzer.available_functions[function_name](**args)

                    if isinstance(result, dict) and 'error' not in result:
                        status = "✅ SUCCESS"
                        function_results[function_name] = "working"
                    else:
                        status = "⚠️ DATA ISSUE"
                        function_results[function_name] = "data_issue"

                    print(f"   {test_name}: {status}")
                    print(f"      Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
                else:
                    print(f"   {test_name}: ❌ Function not found")
                    function_results[function_name] = "missing"

            except Exception as e:
                print(f"   {test_name}: ❌ Error: {str(e)[:50]}...")
                function_results[function_name] = "error"

        # Summary
        print(f"\\n" + "=" * 60)
        print("📊 PHASE 1 TEST RESULTS SUMMARY")
        print("=" * 60)

        success_rate = (successful_tests / len(test_messages)) * 100
        avg_response_time = total_response_time / len(test_messages)

        print(f"✅ Successful responses: {successful_tests}/{len(test_messages)} ({success_rate:.1f}%)")
        print(f"⏱️ Average response time: {avg_response_time:.2f}s")

        # Function status
        working_functions = sum(1 for status in function_results.values() if status == "working")
        print(f"🔧 Working functions: {working_functions}/{len(function_tests)}")

        # Analysis
        print(f"\\n💡 PHASE 1 ANALYSIS:")
        if success_rate >= 80:
            print("🎉 EXCELLENT! Phase 1 LLM integration is working very well")
            print("   Users can now ask natural language health questions!")
        elif success_rate >= 60:
            print("👍 GOOD! Phase 1 is mostly working, some fine-tuning needed")
            print("   Core functionality is operational")
        elif success_rate >= 40:
            print("⚠️ PARTIAL! Phase 1 has issues that need addressing")
            print("   Some natural language processing is working")
        else:
            print("❌ NEEDS WORK! Phase 1 requires significant debugging")
            print("   LLM integration is not functioning properly")

        # Show detailed results for debugging
        print(f"\\n📱 DETAILED RESPONSE ANALYSIS:")
        print("=" * 60)

        for result in results:
            print(f"\\n{result['category']}")
            print(f"Q: '{result['message']}'")
            print(f"Status: {result.get('status', 'UNKNOWN')}")

            if 'response' in result:
                # Show first 200 chars of response
                response_snippet = result['response'][:200].replace('\\n', ' ')
                print(f"Response: {response_snippet}...")
            elif 'error' in result:
                print(f"Error: {result['error']}")
            print("-" * 40)

        print(f"\\n🚀 NEXT STEPS:")
        if success_rate >= 70:
            print("✅ Phase 1 is ready! Proceed to Phase 2: Enhanced Logging & Context Memory")
            print("   • Conversation history tracking")
            print("   • Smart meal/supplement logging")
            print("   • Context-aware responses")
        else:
            print("🔧 Debug Phase 1 issues first:")
            print("   • Check OpenAI API key and billing")
            print("   • Verify function calling is working")
            print("   • Test with simpler queries")
            print("   • Check database connectivity")

        return {
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'working_functions': working_functions,
            'total_functions': len(function_tests),
            'detailed_results': results
        }

if __name__ == '__main__':
    test_llm_phase1()