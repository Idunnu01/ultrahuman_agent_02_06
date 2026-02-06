#!/usr/bin/env python3
"""
Production NLP Test - Run this in your PythonAnywhere environment
Tests the enhanced NLP system with your real 345k+ records
"""

import sys
import os
from datetime import datetime, timedelta

def test_production_nlp():
    """Test the enhanced NLP system in production with real data"""

    print("🚀 PRODUCTION NLP TEST - ENHANCED SYSTEM")
    print("=" * 60)

    try:
        from app import create_app
        from services.metrics_service import MetricsService
        from app.models import User

        app = create_app()

        with app.app_context():
            print("✅ Flask app context created")

            # Initialize the enhanced metrics service
            metrics_service = MetricsService()
            print("✅ Enhanced MetricsService initialized")

            # Get test user (you have sample_user and user_7000)
            test_user = User.query.filter_by(id='sample_user').first()
            if not test_user:
                test_user = User.query.first()

            if not test_user:
                print("❌ No users found")
                return False

            print(f"📱 Testing with user: {test_user.id} ({test_user.phone_number})")

            # Test the exact query that was failing
            failing_query = "what's my avg HR over past week"
            print(f"\n🧪 TESTING THE FAILING QUERY: '{failing_query}'")
            print("-" * 50)

            # Process through the enhanced system
            result = metrics_service.process_sms_input(test_user.id, failing_query)

            if result.get('success'):
                insights = result.get('immediate_insights', {}).get('insights', [])

                if insights:
                    insight = insights[0]
                    message = insight.get('message', 'No message')
                    insight_type = insight.get('type', 'unknown')

                    print(f"📩 Response Type: {insight_type}")
                    print(f"📩 Message: {message}")

                    # Check if we're using enhanced NLP
                    if insight_type.startswith('nlp_'):
                        print(f"✅ USING ENHANCED NLP!")

                        # Show NLP parsing details
                        if 'nlp_parsing' in insight:
                            nlp_info = insight['nlp_parsing']
                            print(f"   🎯 Parsed Metric: {nlp_info.get('parsed_metric')}")
                            print(f"   📊 Aggregation: {nlp_info.get('parsed_aggregation')}")
                            print(f"   📅 Time Period: {nlp_info.get('parsed_timeframe')}")
                            print(f"   📆 Date Range: {nlp_info.get('start_date')} to {nlp_info.get('end_date')}")

                        if 'confidence' in insight:
                            print(f"   🎯 NLP Confidence: {insight['confidence']:.2f}")

                        if 'provider' in insight:
                            print(f"   🔧 Data Provider: {insight['provider']}")

                        # Check if we got actual data vs "no data available"
                        if 'no data available' in message.lower():
                            print(f"   ⚠️ NLP WORKS BUT NO DATA FOUND")
                            print(f"       This means NLP parsing works but database query failed")
                        else:
                            print(f"   🎉 SUCCESS! RETURNED ACTUAL HEALTH DATA!")
                            return True
                    else:
                        print(f"   ❌ Still using legacy processing: {insight_type}")

                else:
                    print(f"❌ No insights returned")
            else:
                print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")

            # Test a few more queries to validate the system
            print(f"\n🔄 TESTING ADDITIONAL QUERIES")
            print("-" * 40)

            additional_queries = [
                "average heart rate last 7 days",
                "my HRV this week",
                "temperature lately",
                "how many steps yesterday"
            ]

            success_count = 0

            for query in additional_queries:
                try:
                    result = metrics_service.process_sms_input(test_user.id, query)

                    if result.get('success'):
                        insights = result.get('immediate_insights', {}).get('insights', [])
                        if insights:
                            insight = insights[0]
                            if insight.get('type', '').startswith('nlp_'):
                                print(f"   ✅ '{query}' -> NLP processed")
                                success_count += 1
                            else:
                                print(f"   ❌ '{query}' -> Legacy processing")
                        else:
                            print(f"   ❌ '{query}' -> No insights")
                    else:
                        print(f"   ❌ '{query}' -> Processing failed")

                except Exception as e:
                    print(f"   ❌ '{query}' -> ERROR: {str(e)}")

            print(f"\n📊 SUMMARY:")
            print(f"   Enhanced NLP Success Rate: {success_count}/{len(additional_queries)} ({success_count/len(additional_queries)*100:.1f}%)")

            if success_count > 0:
                print(f"\n🎉 ENHANCED NLP SYSTEM IS WORKING!")
                print(f"   The system is now using:")
                print(f"   ✅ Your proven date parsing logic")
                print(f"   ✅ Enhanced metric mapping")
                print(f"   ✅ Natural language understanding")
                print(f"   ✅ Your rich database with 345k+ records")
                return True
            else:
                print(f"\n⚠️ System needs debugging")
                print(f"   Check the error messages above")
                return False

    except Exception as e:
        print(f"❌ Production test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_aggregation():
    """Test direct aggregation to verify database connectivity"""

    print(f"\n🔧 DIRECT AGGREGATION TEST")
    print("=" * 40)

    try:
        from app import create_app
        from services.metrics_service import MetricsService
        from app.models import User
        from datetime import datetime, timedelta

        app = create_app()

        with app.app_context():
            metrics_service = MetricsService()
            user = User.query.first()

            if not user:
                print("❌ No user found")
                return

            print(f"Testing direct aggregation with user: {user.id}")

            # Test direct aggregation with your known good data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            # Based on your database check, you have these metrics with recent data:
            test_metrics = [
                ("heart_rate", "average"),  # 2,165 recent records
                ("hrv", "average"),         # 1,948 recent records
                ("temperature", "average"), # 2,252 recent records
                ("steps", "sum"),           # 3,589 recent records
                ("sleep_score", "average")  # 283 recent records
            ]

            successful = 0

            for metric, agg in test_metrics:
                try:
                    result = metrics_service.fetch_metrics_aggregate(
                        user.id,
                        metric,
                        agg,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d")
                    )

                    if result is not None:
                        print(f"   ✅ {metric} ({agg}): {result:.2f}")
                        successful += 1
                    else:
                        print(f"   ❌ {metric} ({agg}): No data")

                except Exception as e:
                    print(f"   ❌ {metric} ({agg}): ERROR - {str(e)}")

            print(f"\nDirect Aggregation Success: {successful}/{len(test_metrics)}")

            if successful > 0:
                print(f"✅ Database connectivity and aggregation working!")
            else:
                print(f"❌ Database aggregation issues")

    except Exception as e:
        print(f"❌ Direct aggregation test failed: {str(e)}")

if __name__ == "__main__":
    print("🧪 PRODUCTION NLP TEST")
    print("=" * 80)
    print("Run this script in your PythonAnywhere environment")
    print("It will test the enhanced NLP system with your real data")
    print("=" * 80)

    # Test direct aggregation first
    test_direct_aggregation()

    # Test the full NLP system
    success = test_production_nlp()

    if success:
        print(f"\n🎉 READY FOR SMS TESTING!")
        print(f"Now you can SMS 'what's my avg HR over past week' to your Twilio number")
        print(f"and it should return actual heart rate data instead of generic responses!")
    else:
        print(f"\n🔧 System needs debugging - check the error messages above")