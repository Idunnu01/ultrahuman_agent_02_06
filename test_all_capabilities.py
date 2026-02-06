#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def test_all_sms_capabilities():
    """Comprehensive test of all SMS health monitoring capabilities"""

    print("🧪 COMPREHENSIVE SMS HEALTH ANALYSIS TESTING")
    print("=" * 60)

    from app import create_app
    from services.metrics_service import MetricsService
    from services.llm_service import SMSLLMService

    app = create_app()

    with app.app_context():
        metrics_service = MetricsService()
        llm_service = SMSLLMService()

        # Test user (replace with your actual user ID)
        test_user_id = "user_7000"  # Update this to your actual user ID

        print(f"Testing with user: {test_user_id}")
        print(f"Available LLM providers: {list(llm_service.providers.keys())}")
        print()

        # 1. CORRELATION ANALYSIS TESTS
        print("🔍 1. CORRELATION ANALYSIS")
        correlation_queries = [
            "correlation between heart rate and sleep score",
            "heart rate vs sleep score last week",
            "how are HRV and stress related",
            "relationship between steps and calories burned"
        ]

        for query in correlation_queries:
            print(f"   Query: '{query}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                if result and result.get('success'):
                    insights = extract_insights(result)
                    print(f"   ✅ Response: {insights[:100]}...")
                else:
                    print(f"   ⚠️  No insights generated")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            print()

        # 2. TREND ANALYSIS TESTS
        print("📈 2. TREND ANALYSIS")
        trend_queries = [
            "heart rate trend over past month",
            "how has my sleep score changed this week",
            "HRV trend last 2 weeks",
            "stress levels trending"
        ]

        for query in trend_queries:
            print(f"   Query: '{query}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                insights = extract_insights(result)
                print(f"   📊 Response: {insights[:100]}...")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            print()

        # 3. METRIC AGGREGATION TESTS
        print("📊 3. METRIC AGGREGATIONS")
        aggregation_queries = [
            "what's my average heart rate this week",
            "max HRV last month",
            "minimum sleep score past week",
            "latest recovery score",
            "total steps yesterday"
        ]

        for query in aggregation_queries:
            print(f"   Query: '{query}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                insights = extract_insights(result)
                print(f"   📋 Response: {insights[:100]}...")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            print()

        # 4. HEALTH ADVICE (NON-DATA QUERIES)
        print("🏥 4. GENERAL HEALTH ADVICE")
        health_queries = [
            "how do I lower my heart rate",
            "tips for better sleep",
            "how to improve HRV",
            "ways to reduce stress naturally",
            "best foods for heart health"
        ]

        for query in health_queries:
            print(f"   Query: '{query}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                insights = extract_insights(result)
                print(f"   💡 Response: {insights[:100]}...")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            print()

        # 5. COMPARATIVE ANALYSIS
        print("⚖️  5. COMPARATIVE ANALYSIS")
        comparison_queries = [
            "compare my heart rate this week vs last week",
            "sleep quality today vs yesterday",
            "HRV this month vs last month"
        ]

        for query in comparison_queries:
            print(f"   Query: '{query}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                insights = extract_insights(result)
                print(f"   ⚖️  Response: {insights[:100]}...")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            print()

        # 6. PATTERN & ANOMALY DETECTION
        print("🔍 6. PATTERN & ANOMALY DETECTION")
        pattern_queries = [
            "any unusual patterns in my data",
            "detect anomalies in heart rate",
            "find patterns in my sleep data",
            "outliers in my metrics"
        ]

        for query in pattern_queries:
            print(f"   Query: '{query}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                insights = extract_insights(result)
                print(f"   🔍 Response: {insights[:100]}...")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}...")
            print()

        # 7. ERROR HANDLING TESTS
        print("⚠️  7. ERROR HANDLING")
        error_queries = [
            "invalid metric xyz",
            "correlation between nonexistent metrics",
            "data from year 2030",
            ""  # empty query
        ]

        for query in error_queries:
            print(f"   Query: '{query or '(empty)'}'")
            try:
                result = process_query_safe(metrics_service, test_user_id, query)
                insights = extract_insights(result)
                print(f"   🛡️  Response: {insights[:100]}...")
            except Exception as e:
                print(f"   🛡️  Handled gracefully: {str(e)[:50]}...")
            print()

        print("✅ COMPREHENSIVE TESTING COMPLETED")
        print("=" * 60)

def process_query_safe(metrics_service, user_id, query):
    """Safely process a query with timeout protection"""
    try:
        # Use a shorter timeout for testing
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Query processing timeout")

        # Set a 30-second timeout for each query
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)

        try:
            result = metrics_service.process_sms_input(user_id, query)
            return result
        finally:
            signal.alarm(0)  # Disable the alarm

    except TimeoutError:
        return {"success": False, "error": "Query timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_insights(result):
    """Extract insight messages from result"""
    if not result:
        return "No result"

    if not result.get('success'):
        return f"Failed: {result.get('error', 'Unknown error')}"

    immediate_insights = result.get('immediate_insights', {})
    insights = immediate_insights.get('insights', [])

    if insights:
        messages = []
        for insight in insights:
            message = insight.get('message', '')
            if message:
                messages.append(message)

        if messages:
            return ' | '.join(messages)

    return "Success but no insights generated"

if __name__ == "__main__":
    try:
        test_all_sms_capabilities()
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed: {str(e)}")
        import traceback
        traceback.print_exc()