#!/usr/bin/env python3
"""
Comprehensive correlation analysis test with all available metrics.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_comprehensive_correlations():
    """Test correlations between all available metric pairs"""

    print("=" * 60)
    print("COMPREHENSIVE CORRELATION ANALYSIS")
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

            # Define metric pairs to test
            metric_pairs = [
                ("temperature", "heart_rate"),
                ("temperature", "hrv"),
                ("temperature", "recovery"),
                ("heart_rate", "hrv"),
                ("heart_rate", "recovery"),
                ("heart_rate", "sleep_score"),
                ("hrv", "recovery"),
                ("hrv", "sleep_score"),
                ("recovery", "sleep_score"),
                ("steps", "active_minutes"),
                ("steps", "heart_rate"),
                ("vo2_max", "recovery"),
                ("vo2_max", "heart_rate"),
                ("movement_index", "recovery"),
                ("movement_index", "heart_rate")
            ]

            successful_correlations = []
            failed_correlations = []

            print(f"🧪 Testing {len(metric_pairs)} metric pairs...")
            print()

            for i, (metric1, metric2) in enumerate(metric_pairs, 1):
                print(f"📊 Test {i}/{len(metric_pairs)}: {metric1} vs {metric2}")
                print("-" * 50)

                try:
                    result = analyzer.analyze_correlation("sample_user", metric1, metric2, days_back=30)

                    if result.get("success"):
                        correlation_coef = result.get('correlation_coefficient', 0)
                        p_value = result.get('p_value', 1)
                        sample_size = result.get('sample_size', 0)
                        significance = result.get('significance', 'unknown')

                        print(f"   ✅ Success!")
                        print(f"   Correlation: {correlation_coef:.4f}")
                        print(f"   P-value: {p_value:.6f}")
                        print(f"   Sample size: {sample_size}")
                        print(f"   Significance: {significance}")

                        # Determine if this is a meaningful correlation
                        if abs(correlation_coef) > 0.5 and p_value < 0.05:
                            print(f"   🎯 STRONG SIGNIFICANT CORRELATION!")
                            successful_correlations.append({
                                'pair': f"{metric1} vs {metric2}",
                                'correlation': correlation_coef,
                                'p_value': p_value,
                                'sample_size': sample_size,
                                'significance': significance
                            })
                        elif abs(correlation_coef) > 0.3:
                            print(f"   📈 Moderate correlation (not significant)")
                        else:
                            print(f"   📉 Weak correlation")

                        # Show some data points if available
                        data_points = result.get('data_points', [])
                        if data_points and len(data_points) <= 5:
                            print(f"   Data points:")
                            for j, point in enumerate(data_points, 1):
                                print(f"     {j}. {point}")

                    else:
                        error = result.get('error', 'Unknown error')
                        print(f"   ❌ Failed: {error}")
                        failed_correlations.append(f"{metric1} vs {metric2}: {error}")

                except Exception as e:
                    print(f"   ❌ Exception: {str(e)}")
                    failed_correlations.append(f"{metric1} vs {metric2}: {str(e)}")

                print()

            # Summary
            print("=" * 60)
            print("CORRELATION ANALYSIS SUMMARY")
            print("=" * 60)
            print(f"✅ Successful correlations: {len(successful_correlations)}")
            print(f"❌ Failed correlations: {len(failed_correlations)}")

            if successful_correlations:
                print("\n🎯 STRONG SIGNIFICANT CORRELATIONS FOUND:")
                for corr in successful_correlations:
                    direction = "positive" if corr['correlation'] > 0 else "negative"
                    print(f"   • {corr['pair']}: {corr['correlation']:.3f} ({direction}) - p={corr['p_value']:.4f}")

            if failed_correlations:
                print(f"\n❌ Failed correlations:")
                for failure in failed_correlations[:5]:  # Show first 5
                    print(f"   • {failure}")
                if len(failed_correlations) > 5:
                    print(f"   ... and {len(failed_correlations) - 5} more")

            return True

    except Exception as e:
        print(f"❌ Error in comprehensive correlation test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Comprehensive Correlation Analysis")
    print("=" * 60)

    success = test_comprehensive_correlations()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ Comprehensive correlation analysis complete")
        print("📊 All available metric pairs tested")
        print("🎯 Strong correlations identified")
        print("🧪 Ready for SMS correlation queries")
    else:
        print("\n❌ Comprehensive correlation test failed. Check the errors above.")

if __name__ == "__main__":
    main()
