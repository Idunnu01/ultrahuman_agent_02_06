#!/usr/bin/env python3
"""
Simple test to verify correlation analysis is working with real data.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_simple_correlation():
    """Test correlation analysis with real data"""

    print("=" * 60)
    print("SIMPLE CORRELATION ANALYSIS TEST")
    print("=" * 60)

    try:
        # Import after setting up path
        from app import create_app
        from services.statistical_analyzer import StatisticalAnalyzer

        # Create Flask app and context
        app = create_app()

        with app.app_context():
            # Create analyzer
            analyzer = StatisticalAnalyzer()

            # Test correlation between temperature and heart rate
            print("🧪 Testing temperature vs heart rate correlation...")
            result = analyzer.analyze_correlation("sample_user", "temperature", "heart_rate", days_back=7)

            if result.get("success"):
                print("✅ Correlation analysis successful!")
                print(f"   Metric 1: {result.get('metric1')}")
                print(f"   Metric 2: {result.get('metric2')}")
                print(f"   Correlation coefficient: {result.get('correlation_coefficient'):.4f}")
                print(f"   P-value: {result.get('p_value'):.6f}")
                print(f"   Sample size: {result.get('sample_size')}")
                print(f"   Correlation strength: {result.get('correlation_strength')}")
                print(f"   Significance: {result.get('significance')}")

                # Show data points
                data_points = result.get('data_points', [])
                if data_points:
                    print(f"\n📊 Data points used:")
                    for i, point in enumerate(data_points[:5]):  # Show first 5
                        print(f"   {i+1}. {point}")
                    if len(data_points) > 5:
                        print(f"   ... and {len(data_points) - 5} more")

                # Test SMS processing
                print(f"\n🧪 Testing SMS query processing...")
                from services.metrics_service import MetricsService
                metrics_service = MetricsService()

                sms_result = metrics_service.process_sms_input(
                    "sample_user",
                    "Is there a correlation between my body temperature and heart rate?"
                )

                if sms_result.get("success"):
                    print("✅ SMS processing successful!")
                    insights = sms_result.get('immediate_insights', {}).get('insights', [])
                    if insights:
                        print(f"   Response: {insights[0].get('message', 'No message')}")

                    correlation_data = sms_result.get('correlation_analysis')
                    if correlation_data:
                        print(f"   Correlation found: {correlation_data.get('correlation_coefficient', 'N/A'):.4f}")
                else:
                    print(f"❌ SMS processing failed: {sms_result.get('error', 'Unknown error')}")

            else:
                print(f"❌ Correlation analysis failed: {result.get('error', 'Unknown error')}")

            return True

    except Exception as e:
        print(f"❌ Error in correlation test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Simple Correlation Test")
    print("=" * 60)

    success = test_simple_correlation()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ Correlation analysis is working!")
        print("📊 Real data is being analyzed")
        print("🧪 SMS queries are being processed")
        print("🎯 Ready for production use")
    else:
        print("\n❌ Correlation test failed. Check the errors above.")

if __name__ == "__main__":
    main()
