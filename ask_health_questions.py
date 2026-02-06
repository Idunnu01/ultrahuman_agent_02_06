#!/usr/bin/env python3
"""
Interactive health question answering using real data
"""

import sys
import os
import numpy as np
from scipy.stats import pearsonr, ttest_ind
from datetime import datetime, timedelta
import re

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def ask_health_question(question, user_id='user_7000'):
    """Answer specific health questions using real data"""

    print(f"❓ Question: {question}")
    print("=" * 60)

    try:
        from app import create_app
        from app.models import Metric, db

        app = create_app()

        with app.app_context():
            # Parse the question to identify metrics
            lifestyle_factor, health_metric = parse_question(question)

            if not lifestyle_factor or not health_metric:
                print("❌ Couldn't understand the question format")
                print("💡 Try questions like:")
                print("   • 'Did my meal timing affect my heart rate?'")
                print("   • 'How does magnesium intake impact my HRV?'")
                print("   • 'Does supplement intake correlate with sleep score?'")
                return

            print(f"🔍 Analyzing: {lifestyle_factor} → {health_metric}")
            print()

            # Get data for both metrics
            lifestyle_data = get_metric_data(user_id, lifestyle_factor, days=60)
            health_data = get_metric_data(user_id, health_metric, days=60)

            if not lifestyle_data or not health_data:
                print(f"❌ Insufficient data for analysis")
                print(f"   {lifestyle_factor}: {len(lifestyle_data) if lifestyle_data else 0} readings")
                print(f"   {health_metric}: {len(health_data) if health_data else 0} readings")
                return

            print(f"📊 Data availability:")
            print(f"   {lifestyle_factor}: {len(lifestyle_data)} readings")
            print(f"   {health_metric}: {len(health_data)} readings")
            print()

            # Analyze the relationship
            analyze_relationship(lifestyle_factor, lifestyle_data, health_metric, health_data)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def parse_question(question):
    """Parse question to extract lifestyle factor and health metric"""

    question_lower = question.lower()

    # Map common terms to database metric names
    lifestyle_mappings = {
        'meal timing': 'meal_timing',
        'meal': 'meal_timing',
        'dinner': 'meal_timing',
        'eating': 'meal_timing',
        'magnesium': 'magnesium_intake',
        'supplement': 'supplement_intake',
        'supplements': 'supplement_intake',
        'exercise': 'exercise_duration',
        'workout': 'exercise_duration',
        'activity': 'active_minutes',
        'steps': 'steps',
        'walking': 'steps'
    }

    health_mappings = {
        'heart rate': 'heart_rate',
        'hr': 'heart_rate',
        'hrv': 'hrv',
        'heart rate variability': 'hrv',
        'sleep': 'sleep_score',
        'sleep score': 'sleep_score',
        'sleep quality': 'sleep_score',
        'recovery': 'recovery',
        'temperature': 'temperature',
        'temp': 'temperature',
        'resting heart rate': 'night_rhr',
        'rhr': 'night_rhr'
    }

    lifestyle_factor = None
    health_metric = None

    # Find lifestyle factor
    for term, metric in lifestyle_mappings.items():
        if term in question_lower:
            lifestyle_factor = metric
            break

    # Find health metric
    for term, metric in health_mappings.items():
        if term in question_lower:
            health_metric = metric
            break

    return lifestyle_factor, health_metric

def get_metric_data(user_id, metric_type, days=60):
    """Get metric data for specified time period"""

    try:
        from app.models import Metric, db

        cutoff_date = datetime.now() - timedelta(days=days)

        data = db.session.query(Metric.value, Metric.timestamp).filter(
            Metric.user_id == user_id,
            Metric.metric_type == metric_type,
            Metric.timestamp >= cutoff_date
        ).order_by(Metric.timestamp).all()

        return [(float(d[0]), d[1]) for d in data]

    except Exception as e:
        print(f"Error getting {metric_type} data: {e}")
        return []

def analyze_relationship(lifestyle_factor, lifestyle_data, health_metric, health_data):
    """Analyze relationship between lifestyle factor and health metric"""

    print("🧪 Statistical Analysis:")
    print("=" * 25)

    try:
        # Method 1: Direct correlation if enough overlapping data
        correlation_result = analyze_correlation(lifestyle_data, health_data)

        # Method 2: Compare health metric on days with/without lifestyle factor
        comparison_result = analyze_comparison(lifestyle_factor, lifestyle_data, health_metric, health_data)

        # Method 3: Time-based analysis
        temporal_result = analyze_temporal_relationship(lifestyle_factor, lifestyle_data, health_metric, health_data)

        # Generate insights
        generate_insights(lifestyle_factor, health_metric, correlation_result, comparison_result, temporal_result)

    except Exception as e:
        print(f"Analysis error: {e}")

def analyze_correlation(lifestyle_data, health_data):
    """Analyze direct correlation between metrics"""

    try:
        if len(lifestyle_data) < 5 or len(health_data) < 5:
            return None

        # Align data by date
        lifestyle_dict = {}
        for value, timestamp in lifestyle_data:
            date_key = timestamp.date()
            lifestyle_dict[date_key] = lifestyle_dict.get(date_key, []) + [value]

        health_dict = {}
        for value, timestamp in health_data:
            date_key = timestamp.date()
            health_dict[date_key] = health_dict.get(date_key, []) + [value]

        # Get common dates
        common_dates = set(lifestyle_dict.keys()) & set(health_dict.keys())

        if len(common_dates) < 5:
            return None

        lifestyle_values = []
        health_values = []

        for date in common_dates:
            lifestyle_values.append(np.mean(lifestyle_dict[date]))
            health_values.append(np.mean(health_dict[date]))

        correlation, p_value = pearsonr(lifestyle_values, health_values)

        return {
            'correlation': correlation,
            'p_value': p_value,
            'sample_size': len(common_dates),
            'significant': p_value < 0.05
        }

    except Exception as e:
        return None

def analyze_comparison(lifestyle_factor, lifestyle_data, health_metric, health_data):
    """Compare health metric on days with/without lifestyle factor"""

    try:
        # Get dates with lifestyle factor
        lifestyle_dates = set([d[1].date() for d in lifestyle_data])

        # Split health data into with/without lifestyle factor
        with_lifestyle = []
        without_lifestyle = []

        for value, timestamp in health_data:
            date = timestamp.date()
            if date in lifestyle_dates:
                with_lifestyle.append(value)
            else:
                without_lifestyle.append(value)

        if len(with_lifestyle) < 3 or len(without_lifestyle) < 3:
            return None

        # Statistical comparison
        with_mean = np.mean(with_lifestyle)
        without_mean = np.mean(without_lifestyle)

        t_stat, p_value = ttest_ind(with_lifestyle, without_lifestyle)

        return {
            'with_mean': with_mean,
            'without_mean': without_mean,
            'difference': with_mean - without_mean,
            'percent_change': ((with_mean - without_mean) / without_mean) * 100,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'with_count': len(with_lifestyle),
            'without_count': len(without_lifestyle)
        }

    except Exception as e:
        return None

def analyze_temporal_relationship(lifestyle_factor, lifestyle_data, health_metric, health_data):
    """Analyze temporal relationship (e.g., health metric after lifestyle event)"""

    try:
        # Look at health metric in hours after lifestyle event
        temporal_effects = []

        for lifestyle_value, lifestyle_time in lifestyle_data:
            # Find health measurements within 24 hours after lifestyle event
            health_after = []

            for health_value, health_time in health_data:
                time_diff = (health_time - lifestyle_time).total_seconds() / 3600  # hours
                if 0 <= time_diff <= 24:  # Within 24 hours after
                    health_after.append(health_value)

            if health_after:
                temporal_effects.append({
                    'lifestyle_value': lifestyle_value,
                    'health_avg': np.mean(health_after),
                    'health_count': len(health_after)
                })

        if len(temporal_effects) < 3:
            return None

        return {
            'effects': temporal_effects,
            'count': len(temporal_effects)
        }

    except Exception as e:
        return None

def generate_insights(lifestyle_factor, health_metric, correlation_result, comparison_result, temporal_result):
    """Generate human-readable insights"""

    print("💡 Key Insights:")
    print("=" * 15)

    insights_found = False

    # Correlation insights
    if correlation_result and not np.isnan(correlation_result['correlation']):
        corr = correlation_result['correlation']
        strength = get_correlation_strength(abs(corr))
        direction = "positive" if corr > 0 else "negative"

        print(f"📊 Correlation Analysis:")
        print(f"   {strength} {direction} correlation: {corr:+.3f}")
        print(f"   Statistical significance: {'✅ Yes' if correlation_result['significant'] else '❌ No'}")
        print(f"   Based on {correlation_result['sample_size']} overlapping days")

        if correlation_result['significant']:
            effect_size = abs(corr) * 100
            direction_word = "improves" if corr > 0 else "reduces"
            print(f"   💡 {lifestyle_factor.replace('_', ' ').title()} {direction_word} {health_metric.replace('_', ' ')} by ~{effect_size:.0f}%")

        insights_found = True
        print()

    # Comparison insights
    if comparison_result:
        print(f"📈 Comparison Analysis:")
        print(f"   With {lifestyle_factor.replace('_', ' ')}: {comparison_result['with_mean']:.2f}")
        print(f"   Without {lifestyle_factor.replace('_', ' ')}: {comparison_result['without_mean']:.2f}")
        print(f"   Difference: {comparison_result['difference']:+.2f} ({comparison_result['percent_change']:+.1f}%)")
        print(f"   Statistical significance: {'✅ Yes' if comparison_result['significant'] else '❌ No'}")

        if comparison_result['significant']:
            if comparison_result['difference'] > 0:
                print(f"   💡 {lifestyle_factor.replace('_', ' ').title()} appears to IMPROVE {health_metric.replace('_', ' ')}")
            else:
                print(f"   💡 {lifestyle_factor.replace('_', ' ').title()} appears to REDUCE {health_metric.replace('_', ' ')}")

        insights_found = True
        print()

    # Temporal insights
    if temporal_result and temporal_result['count'] > 0:
        print(f"⏱️ Temporal Analysis:")
        print(f"   Found {temporal_result['count']} instances to analyze")

        avg_effect = np.mean([e['health_avg'] for e in temporal_result['effects']])
        print(f"   Average {health_metric.replace('_', ' ')} after {lifestyle_factor.replace('_', ' ')}: {avg_effect:.2f}")

        insights_found = True
        print()

    if not insights_found:
        print("⚠️ No significant relationships found with current data")
        print("💡 This could be due to:")
        print("   • Limited overlapping data points")
        print("   • Need longer time period for analysis")
        print("   • Relationship may exist but be too subtle to detect")

def get_correlation_strength(r):
    """Get human-readable correlation strength"""
    if r >= 0.7:
        return "Very Strong"
    elif r >= 0.5:
        return "Strong"
    elif r >= 0.3:
        return "Moderate"
    elif r >= 0.1:
        return "Weak"
    else:
        return "Very Weak"

def interactive_mode():
    """Interactive question-asking mode"""

    print("🤔 Interactive Health Question Assistant")
    print("=" * 45)
    print()
    print("Ask questions about your health data relationships!")
    print()
    print("Example questions:")
    print("• 'Did my meal timing affect my heart rate?'")
    print("• 'How does magnesium intake impact my HRV?'")
    print("• 'Does supplement intake correlate with sleep score?'")
    print("• 'Did exercise affect my recovery?'")
    print()

    while True:
        question = input("Your question (or 'quit' to exit): ").strip()

        if question.lower() in ['quit', 'exit', 'q']:
            break

        if not question:
            continue

        print()
        ask_health_question(question)
        print("\n" + "="*60 + "\n")

def main():
    print("🚀 Health Data Question Assistant")
    print("Using your 175K+ real health metrics")
    print("=" * 50)

    # Pre-defined interesting questions to test
    test_questions = [
        "Did my meal timing affect my heart rate?",
        "How does supplement intake impact my HRV?",
        "Does magnesium intake correlate with sleep score?",
        "Did my activity level affect my recovery?"
    ]

    print("🧪 Testing with sample questions:")
    print()

    for question in test_questions:
        ask_health_question(question)
        print("\n" + "="*60 + "\n")

    # Interactive mode
    interactive_mode()

if __name__ == '__main__':
    main()