#!/usr/bin/env python3
"""
Test Enhanced System - Full integration test of NLP + Enhanced Metrics
Tests with REAL data from your production database
"""

import sys
import os
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.append('.')

def test_enhanced_system_complete():
    """Complete test of the enhanced system with real data"""

    print("🚀 TESTING ENHANCED SYSTEM - COMPLETE INTEGRATION")
    print("=" * 70)

    try:
        from app import create_app
        from services.metrics_service import MetricsService
        from enhanced_metric_lookup import EnhancedMetricLookup

        app = create_app()

        with app.app_context():
            print("✅ Flask app context created")

            # Initialize services
            metrics_service = MetricsService()
            enhanced_lookup = EnhancedMetricLookup()

            print("✅ Services initialized")

            # Get real users from your database
            from app.models import User
            users = User.query.all()
            test_user = users[0] if users else None

            if not test_user:
                print("❌ No users found")
                return False

            print(f"📱 Testing with user: {test_user.id} ({test_user.phone_number})")

            # 1. Test Enhanced Lookup - Check Available Metrics
            print(f"\n🔍 STEP 1: ENHANCED LOOKUP - AVAILABLE METRICS")
            print("=" * 50)

            available_metrics = enhanced_lookup.get_available_metrics_for_user(test_user.id, days_back=7)
            print(f"Found {len(available_metrics)} available metrics:")

            for metric_name, info in available_metrics.items():
                print(f"  ✅ {metric_name}: {info['count']} records")
                print(f"     📊 {info['stats']['average']} {info['unit']} (avg)")
                print(f"     📅 {info['date_range']['latest'][:10]} (latest)")

            # 2. Test Enhanced Aggregation
            print(f"\n🧮 STEP 2: ENHANCED AGGREGATION TESTING")
            print("=" * 50)

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            # Test key metrics that showed recent data
            test_cases = [
                ("heart_rate", "average"),
                ("heart_rate", "min"),
                ("heart_rate", "max"),
                ("hrv", "average"),
                ("temperature", "average"),
                ("sleep_score", "average"),
                ("steps", "sum"),
                ("active_minutes", "sum"),
                ("recovery", "average"),
                ("vo2_max", "latest")
            ]

            successful_queries = 0

            for metric, aggregation in test_cases:
                try:
                    result = metrics_service.fetch_metrics_aggregate(
                        test_user.id, metric, aggregation, start_str, end_str
                    )

                    if result is not None:
                        # Get unit info
                        metric_info = enhanced_lookup.get_metric_info(metric)
                        unit = metric_info["unit"] if metric_info else "units"

                        print(f"  ✅ {metric} ({aggregation}): {result:.2f} {unit}")
                        successful_queries += 1
                    else:
                        print(f"  ❌ {metric} ({aggregation}): No data found")

                except Exception as e:
                    print(f"  ❌ {metric} ({aggregation}): ERROR - {str(e)}")

            print(f"\n📊 Aggregation Success Rate: {successful_queries}/{len(test_cases)} ({successful_queries/len(test_cases)*100:.1f}%)")

            # 3. Test NLP Integration with Enhanced Data
            print(f"\n🧠 STEP 3: NLP + ENHANCED DATA INTEGRATION")
            print("=" * 50)

            # The queries that were failing before - should now work!
            nlp_test_queries = [
                "what's my avg HR over past week",
                "average heart rate last 7 days",
                "how was my heart rate recently",
                "show me my HRV this week",
                "what's my temperature been like lately",
                "how many steps yesterday",
                "what's my recovery score today",
                "highest heart rate last week"
            ]

            nlp_successful = 0

            for query in nlp_test_queries:
                print(f"\n🧪 Testing: '{query}'")

                try:
                    result = metrics_service.process_sms_input(test_user.id, query)

                    if result.get('success'):
                        insights = result.get('immediate_insights', {}).get('insights', [])

                        if insights:
                            insight = insights[0]
                            message = insight.get('message', 'No message')
                            insight_type = insight.get('type', 'unknown')

                            if insight_type.startswith('nlp_') and 'no data available' not in message.lower():
                                print(f"   ✅ SUCCESS: {message[:100]}...")
                                nlp_successful += 1
                            elif 'no data available' in message.lower():
                                print(f"   ⚠️ NLP PARSED BUT NO DATA: {message[:100]}...")
                            else:
                                print(f"   ❓ LEGACY PROCESSING: {message[:100]}...")
                        else:
                            print(f"   ❌ No insights returned")
                    else:
                        print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")

                except Exception as e:
                    print(f"   ❌ ERROR: {str(e)}")

            print(f"\n🧠 NLP Success Rate: {nlp_successful}/{len(nlp_test_queries)} ({nlp_successful/len(nlp_test_queries)*100:.1f}%)")

            # 4. Summary
            print(f"\n📋 FINAL SUMMARY")
            print("=" * 30)
            print(f"✅ Available Metrics: {len(available_metrics)}")
            print(f"✅ Successful Aggregations: {successful_queries}/{len(test_cases)}")
            print(f"✅ Successful NLP Queries: {nlp_successful}/{len(nlp_test_queries)}")

            overall_success = (successful_queries > len(test_cases) * 0.5 and
                             nlp_successful > len(nlp_test_queries) * 0.5)

            if overall_success:
                print(f"\n🎉 ENHANCED SYSTEM IS WORKING!")
                print(f"   Your NLP queries should now return actual health data")
                print(f"   instead of generic responses!")
            else:
                print(f"\n⚠️ System needs more work")
                print(f"   Check the error messages above for issues to resolve")

            return overall_success

    except Exception as e:
        print(f"❌ Enhanced system test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_failing_query():
    """Test the specific query that was failing"""

    print(f"\n🎯 SPECIFIC QUERY TEST")
    print("=" * 40)

    try:
        from app import create_app
        from services.metrics_service import MetricsService
        from app.models import User

        app = create_app()

        with app.app_context():
            metrics_service = MetricsService()
            user = User.query.first()

            if not user:
                print("❌ No user found")
                return

            # Test the exact query that was failing
            failing_query = "what's my avg HR over past week"

            print(f"🧪 Testing exact failing query: '{failing_query}'")

            result = metrics_service.process_sms_input(user.id, failing_query)

            if result.get('success'):
                insights = result.get('immediate_insights', {}).get('insights', [])

                if insights:
                    insight = insights[0]
                    message = insight.get('message', '')

                    print(f"📩 Response: {message}")

                    # Check if it's using NLP processing
                    if insight.get('type', '').startswith('nlp_'):
                        print(f"✅ Using NLP processing!")

                        if 'nlp_parsing' in insight:
                            parsing_info = insight['nlp_parsing']
                            print(f"🎯 Parsed as: {parsing_info.get('parsed_metric')} {parsing_info.get('parsed_aggregation')}")
                            print(f"📅 Date range: {parsing_info.get('start_date')} to {parsing_info.get('end_date')}")

                        if 'no data available' not in message.lower():
                            print(f"🎉 SUCCESS: Query returned actual data!")
                        else:
                            print(f"⚠️ NLP works but no data found - check database")
                    else:
                        print(f"❌ Still using legacy processing")
                else:
                    print(f"❌ No insights in response")
            else:
                print(f"❌ Query failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Specific query test failed: {str(e)}")

if __name__ == "__main__":
    print("🧪 ENHANCED SYSTEM INTEGRATION TEST")
    print("=" * 80)

    success = test_enhanced_system_complete()
    test_specific_failing_query()

    if success:
        print(f"\n🎉 INTEGRATION SUCCESSFUL!")
        print(f"✅ Your enhanced system combines:")
        print(f"   - Proven date parsing from old deployment")
        print(f"   - Comprehensive metric mapping")
        print(f"   - Rich database with 345k+ records")
        print(f"   - Natural language understanding")
        print(f"\n📱 Ready for production SMS testing!")
    else:
        print(f"\n❌ Integration needs fixes - check error messages above")