#!/usr/bin/env python3
"""
Debug correlation query detection - FIXED VERSION.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def debug_correlation_detection():
    """Debug the correlation query detection logic"""

    print("=" * 60)
    print("DEBUGGING CORRELATION QUERY DETECTION")
    print("=" * 60)

    try:
        # Import after setting up path
        from app import create_app
        from services.metrics_service import MetricsService

        # Create Flask app and context
        app = create_app()

        # Test queries
        test_queries = [
            "Is there a correlation between my body temperature and heart rate?",
            "What's the relationship between my sleep score and heart rate?",
            "How does my HRV correlate with recovery?",
            "Is there a correlation between temperature and sleep score?",
            "What's the relationship between my heart rate and recovery?"
        ]

        with app.app_context():  # MOVED THE CONTEXT HERE
            # Create metrics service inside app context
            metrics_service = MetricsService()

            for i, query in enumerate(test_queries, 1):
                print(f"\n🧪 TEST {i}: {query}")
                print("-" * 60)

                # Test correlation detection
                is_correlation = metrics_service._is_correlation_query(query.lower())
                print(f"   Is correlation query: {is_correlation}")

                # Test metric extraction
                metrics = metrics_service._extract_metrics_from_message(query.lower())
                print(f"   Extracted metrics: {metrics}")

                # Test full processing (now inside app context)
                result = metrics_service.process_sms_input("sample_user", query)
                print(f"   Processing result: {result.get('success', False)}")

                if result.get('success'):
                    correlation_data = result.get('correlation_analysis')
                    if correlation_data:
                        print(f"   ✅ Correlation analysis found!")
                        print(f"      Metric 1: {correlation_data.get('metric1', 'N/A')}")
                        print(f"      Metric 2: {correlation_data.get('metric2', 'N/A')}")
                        print(f"      Correlation: {correlation_data.get('correlation_coefficient', 'N/A')}")
                        print(f"      P-value: {correlation_data.get('p_value', 'N/A')}")
                        print(f"      Sample size: {correlation_data.get('sample_size', 'N/A')}")
                        print(f"      Strength: {correlation_data.get('correlation_strength', 'N/A')}")
                        print(f"      Significance: {correlation_data.get('significance', 'N/A')}")

                        # Show some data points
                        data_points = correlation_data.get('data_points', [])
                        if data_points:
                            print(f"      Data points (first 3):")
                            for i, point in enumerate(data_points[:3]):
                                print(f"        {i+1}. {point}")
                            if len(data_points) > 3:
                                print(f"        ... and {len(data_points) - 3} more")
                    else:
                        print(f"   ❌ No correlation analysis in result")

                        # Check what type of response we got
                        insights = result.get('immediate_insights', {}).get('insights', [])
                        if insights:
                            print(f"   📝 Response type: {insights[0].get('type', 'unknown')}")
                            print(f"   📝 Response message: {insights[0].get('message', 'N/A')}")
                else:
                    print(f"   ❌ Processing failed: {result.get('error', 'Unknown error')}")

        return True  # Success

    except Exception as e:
        print(f"❌ Error debugging correlation detection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Correlation Detection Debug")
    print("=" * 60)

    success = debug_correlation_detection()

    if success:
        print("\n" + "=" * 60)
        print("DEBUG SUMMARY:")
        print("=" * 60)
        print("✅ Debug complete")
        print("🔍 Check the output above to see what's happening")
    else:
        print("\n❌ Debug failed. Check the errors above.")

if __name__ == "__main__":
    main()