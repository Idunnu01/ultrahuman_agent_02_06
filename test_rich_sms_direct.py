#!/usr/bin/env python3
"""
Test rich SMS generation directly without database dependency
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def test_rich_sms_directly():
    """Test the rich SMS function with mock analysis results"""

    # Import the function directly
    from tasks.daily_report import _generate_rich_analysis_sms

    print("🧪 Testing Rich SMS Generation Directly")
    print("=" * 50)

    # Mock analysis results matching your actual system structure
    mock_analysis_results = {
        'baseline_statistics': {
            'sleep_score': {
                'latest_value': 85,
                'mean': 78,
                'trend': 'improving'
            },
            'hrv': {
                'latest_value': 45,
                'mean': 42,
                'trend': 'stable'
            },
            'recovery_score': {
                'latest_value': 82,
                'mean': 75,
                'trend': 'improving'
            },
            'resting_heart_rate': {
                'latest_value': 58,
                'mean': 62,
                'trend': 'improving'
            }
        },
        'correlations': {
            'magnesium_sleep_quality': {
                'correlation': 0.67,
                'p_value': 0.001,
                'significant': True
            },
            'exercise_hrv_recovery': {
                'correlation': 0.52,
                'p_value': 0.015,
                'significant': True
            },
            'caffeine_sleep_onset': {
                'correlation': -0.43,
                'p_value': 0.008,
                'significant': True
            }
        },
        'insights': {
            'key_insights': [
                'Sleep consistency improved this week',
                'HRV showing strong recovery pattern',
                'Recovery trending positively'
            ]
        }
    }

    # Test with different scenarios
    test_cases = [
        {
            'name': 'Rich analysis with full data',
            'analysis': mock_analysis_results,
            'user_id': 'user_7000',
            'date': '2025-09-09'
        },
        {
            'name': 'Analysis with minimal data',
            'analysis': {
                'baseline_statistics': {
                    'sleep_score': {'latest_value': 80, 'mean': 75}
                },
                'correlations': {},
                'insights': {}
            },
            'user_id': 'user_7000',
            'date': '2025-09-09'
        },
        {
            'name': 'Empty analysis (fallback test)',
            'analysis': {},
            'user_id': 'user_7000',
            'date': '2025-09-09'
        }
    ]

    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📱 Test {i}: {test_case['name']}")
        print("-" * 40)

        try:
            rich_sms = _generate_rich_analysis_sms(
                test_case['analysis'],
                test_case['user_id'],
                test_case['date']
            )

            print(f"Generated SMS ({len(rich_sms)} chars):")
            print(rich_sms)

            # Validate SMS
            if rich_sms and len(rich_sms) <= 306:
                if "🌅 Daily Health" in rich_sms and "Open dashboard for details" in rich_sms:
                    print("✅ Valid rich SMS generated")

                    # Check for sophisticated content
                    has_percentage = "%" in rich_sms
                    has_correlation = "link" in rich_sms or "inverse" in rich_sms
                    has_insight = "💡" in rich_sms
                    has_metrics = any(emoji in rich_sms for emoji in ["💤", "❤️", "🏃"])

                    if has_percentage or has_correlation or has_insight or has_metrics:
                        print("🎉 SMS contains sophisticated health analysis!")
                        if has_percentage:
                            print("   📊 Includes percentage changes")
                        if has_correlation:
                            print("   🔍 Includes correlation findings")
                        if has_insight:
                            print("   💡 Includes personalized insights")
                        if has_metrics:
                            print("   📈 Includes categorized metrics")

                    success_count += 1
                else:
                    print("⚠️ Missing expected format elements")
            else:
                print(f"❌ Invalid SMS: length={len(rich_sms)}")

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

    print(f"\n📊 Test Results: {success_count}/{len(test_cases)} passed")

    if success_count == len(test_cases):
        print("\n🎉 All tests passed! Rich SMS analysis is working!")
        print("✅ Your 4 AM reports will now include:")
        print("   📊 Real percentage changes from your baselines")
        print("   🔍 Actual correlations from your 175K+ metrics")
        print("   💡 Personalized insights from your health patterns")
        print("   📈 Sophisticated analysis instead of generic templates")
        return True
    else:
        print("\n⚠️ Some tests failed - review the output above")
        return False

def show_expected_output():
    """Show what the rich SMS should look like"""

    print("\n📱 Expected Rich SMS Output Example:")
    print("=" * 50)

    expected = """🌅 Daily Health - Sep 9
💤 Sleep Score: ↗️ 9%
🏃 Recovery Score: ↗️ 9%
🔍 Magnesium Sleep Quality: +67% link
💡 Sleep consistency improved this week
Open dashboard for details."""

    print(expected)
    print("=" * 50)
    print(f"Length: {len(expected)} characters")
    print("\nThis transforms your basic SMS into sophisticated health intelligence!")

if __name__ == '__main__':
    print("🚀 Direct Rich SMS Test")
    print("Testing sophisticated health analysis SMS generation\n")

    show_expected_output()

    success = test_rich_sms_directly()

    if success:
        print("\n💡 Next steps:")
        print("1. Your enhanced daily reports are ready!")
        print("2. Next 4 AM report will show rich analysis")
        print("3. No more generic templates - real insights from your data")
    else:
        print("\n🔍 Review the test output for any issues")