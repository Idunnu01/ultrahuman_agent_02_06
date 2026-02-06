#!/usr/bin/env python3
"""
Comprehensive Lifestyle Correlation Analyzer
Analyzes how ALL lifestyle events (supplements, meals, drinks, exercise) affect biometrics
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import text
import json

class LifestyleCorrelationAnalyzer:
    """Analyzes correlations between all lifestyle events and biometric outcomes"""

    def __init__(self):
        self.lifestyle_event_types = [
            'supplement_intake',
            'meal_timing',
            'activity_duration',
            'alcohol_consumption',
            'caffeine_intake',
            'exercise_intensity'
        ]

        self.biometric_metrics = [
            'sleep_score',
            'hrv_score',
            'heart_rate',
            'deep_sleep_minutes',
            'rem_sleep_minutes',
            'recovery_score',
            'stress_score'
        ]

        # Time lags to test (in hours)
        self.lag_periods = [1, 2, 4, 6, 8, 12, 16, 24, 48]

    def analyze_all_lifestyle_correlations(self, user_id: str, days_back: int = 30) -> Dict:
        """
        Comprehensive analysis of ALL lifestyle events vs biometric outcomes
        """
        from app import create_app
        from utils.database import db

        app = create_app()
        with app.app_context():

            # Get ALL lifestyle events
            lifestyle_data = self._get_lifestyle_events(db, user_id, days_back)

            # Get ALL biometric data
            biometric_data = self._get_biometric_data(db, user_id, days_back)

            if not lifestyle_data or not biometric_data:
                return {"error": "Insufficient data for correlation analysis"}

            # Convert to DataFrames
            lifestyle_df = self._process_lifestyle_data(lifestyle_data)
            biometric_df = self._process_biometric_data(biometric_data)

            # Analyze all combinations
            correlations = self._calculate_all_correlations(lifestyle_df, biometric_df)

            # Generate insights
            insights = self._generate_lifestyle_insights(correlations)

            return {
                'analysis_period_days': days_back,
                'lifestyle_events_analyzed': len(lifestyle_data),
                'biometric_points_analyzed': len(biometric_data),
                'top_correlations': correlations[:10],  # Top 10 strongest
                'insights': insights,
                'recommendations': self._generate_recommendations(correlations)
            }

    def analyze_specific_lifestyle_event(self, user_id: str, event_type: str, event_value: str = None, days_back: int = 30) -> Dict:
        """
        Analyze how a specific lifestyle event affects biometrics
        Examples:
        - analyze_specific_lifestyle_event('user_7000', 'supplement', 'magnesium')
        - analyze_specific_lifestyle_event('user_7000', 'meal', 'chicken')
        - analyze_specific_lifestyle_event('user_7000', 'exercise', 'running')
        - analyze_specific_lifestyle_event('user_7000', 'drink', 'coffee')
        """
        from app import create_app
        from utils.database import db

        app = create_app()
        with app.app_context():

            # Get specific lifestyle events
            if event_type == 'supplement':
                metric_type = f'{event_value}_intake' if event_value else 'supplement_intake'
            elif event_type == 'meal':
                metric_type = f'{event_value}_consumption' if event_value else 'meal_timing'
            elif event_type == 'exercise':
                metric_type = 'activity_duration'
            elif event_type == 'drink':
                if event_value in ['coffee', 'tea']:
                    metric_type = 'caffeine_intake'
                elif event_value in ['wine', 'beer', 'alcohol']:
                    metric_type = 'alcohol_consumption'
                else:
                    metric_type = 'fluid_intake'
            else:
                metric_type = f'{event_type}_{event_value}' if event_value else event_type

            # Query specific events
            event_query = text("""
                SELECT timestamp, value, unit, meta_data
                FROM metrics
                WHERE user_id = :user_id
                    AND (metric_type = :metric_type OR metric_type LIKE :pattern)
                    AND timestamp >= DATE_SUB(NOW(), INTERVAL :days DAY)
                ORDER BY timestamp
            """)

            events = db.session.execute(event_query, {
                'user_id': user_id,
                'metric_type': metric_type,
                'pattern': f'%{event_value}%' if event_value else f'{event_type}%',
                'days': days_back
            }).fetchall()

            if len(events) < 3:
                return {"error": f"Need at least 3 {event_type} events for correlation analysis. Found: {len(events)}"}

            # Get biometric data
            biometric_data = self._get_biometric_data(db, user_id, days_back)

            # Analyze correlations
            correlations = self._analyze_event_vs_biometrics(events, biometric_data, event_type, event_value)

            return {
                'event_type': event_type,
                'event_value': event_value,
                'events_analyzed': len(events),
                'correlations': correlations,
                'summary': self._generate_event_summary(event_type, event_value, correlations)
            }

    def _get_lifestyle_events(self, db, user_id: str, days_back: int) -> List:
        """Get all lifestyle events from database"""
        query = text("""
            SELECT metric_type, timestamp, value, unit, meta_data
            FROM metrics
            WHERE user_id = :user_id
                AND timestamp >= DATE_SUB(NOW(), INTERVAL :days DAY)
                AND (
                    metric_type LIKE '%_intake' OR
                    metric_type LIKE '%_consumption' OR
                    metric_type LIKE '%activity%' OR
                    metric_type = 'meal_timing' OR
                    meta_data LIKE '%"event_type"%'
                )
            ORDER BY timestamp
        """)

        return db.session.execute(query, {
            'user_id': user_id,
            'days': days_back
        }).fetchall()

    def _get_biometric_data(self, db, user_id: str, days_back: int) -> List:
        """Get biometric data from Ultrahuman"""
        query = text("""
            SELECT metric_type, timestamp, value, unit
            FROM metrics
            WHERE user_id = :user_id
                AND metric_type IN (
                    'sleep_score', 'hrv_score', 'heart_rate',
                    'deep_sleep_minutes', 'rem_sleep_minutes',
                    'recovery_score', 'stress_score', 'resting_heart_rate'
                )
                AND timestamp >= DATE_SUB(NOW(), INTERVAL :days DAY)
            ORDER BY timestamp
        """)

        return db.session.execute(query, {
            'user_id': user_id,
            'days': days_back
        }).fetchall()

    def _process_lifestyle_data(self, lifestyle_data) -> pd.DataFrame:
        """Convert lifestyle events to DataFrame with categories"""
        processed = []

        for event in lifestyle_data:
            # Parse event details
            event_category = self._categorize_lifestyle_event(event.metric_type, event.meta_data)

            processed.append({
                'timestamp': event.timestamp,
                'category': event_category['category'],
                'subcategory': event_category['subcategory'],
                'value': event.value,
                'intensity': self._calculate_event_intensity(event_category, event.value)
            })

        return pd.DataFrame(processed)

    def _categorize_lifestyle_event(self, metric_type: str, meta_data: str) -> Dict:
        """Categorize lifestyle events into meaningful groups"""
        try:
            meta = json.loads(meta_data) if meta_data else {}
        except:
            meta = {}

        if 'supplement' in metric_type:
            return {'category': 'supplement', 'subcategory': metric_type.replace('_intake', '')}
        elif 'consumption' in metric_type:
            return {'category': 'food', 'subcategory': metric_type.replace('_consumption', '')}
        elif 'activity' in metric_type or 'exercise' in metric_type:
            return {'category': 'exercise', 'subcategory': meta.get('type', 'general')}
        elif 'meal_timing' in metric_type:
            return {'category': 'meal', 'subcategory': meta.get('food', 'general')}
        elif 'alcohol' in metric_type:
            return {'category': 'alcohol', 'subcategory': 'consumption'}
        elif 'caffeine' in metric_type:
            return {'category': 'caffeine', 'subcategory': 'consumption'}
        else:
            return {'category': 'other', 'subcategory': metric_type}

    def _calculate_event_intensity(self, event_category: Dict, value: float) -> str:
        """Calculate relative intensity of events"""
        category = event_category['category']

        if category == 'exercise':
            if value >= 45:
                return 'high'
            elif value >= 20:
                return 'moderate'
            else:
                return 'light'
        elif category == 'supplement':
            return 'standard'  # Most supplements are standard dose
        elif category in ['alcohol', 'caffeine']:
            if value >= 2:
                return 'high'
            elif value >= 1:
                return 'moderate'
            else:
                return 'light'
        else:
            return 'standard'

    def _calculate_all_correlations(self, lifestyle_df: pd.DataFrame, biometric_df: pd.DataFrame) -> List[Dict]:
        """Calculate correlations between all lifestyle events and biometrics"""
        correlations = []

        # Group lifestyle events by category and subcategory
        for (category, subcategory), group in lifestyle_df.groupby(['category', 'subcategory']):

            # Test against each biometric
            for metric in biometric_df['metric_type'].unique():
                metric_data = biometric_df[biometric_df['metric_type'] == metric]

                # Test different time lags
                for lag_hours in self.lag_periods:
                    correlation = self._calculate_lagged_correlation(group, metric_data, lag_hours)

                    if correlation is not None and abs(correlation) > 0.1:  # Only significant correlations
                        correlations.append({
                            'lifestyle_category': category,
                            'lifestyle_item': subcategory,
                            'biometric': metric,
                            'correlation': correlation,
                            'lag_hours': lag_hours,
                            'strength': self._get_correlation_strength(correlation),
                            'events_count': len(group)
                        })

        # Sort by absolute correlation strength
        return sorted(correlations, key=lambda x: abs(x['correlation']), reverse=True)

    def _calculate_lagged_correlation(self, lifestyle_events, biometric_data, lag_hours) -> Optional[float]:
        """Calculate correlation with time lag"""
        try:
            # Create daily aggregates for lifestyle events
            lifestyle_daily = lifestyle_events.set_index('timestamp').resample('D').agg({
                'value': 'sum',
                'intensity': lambda x: 'high' if 'high' in x.values else ('moderate' if 'moderate' in x.values else 'light')
            })

            # Shift biometric data by lag
            biometric_shifted = biometric_data.copy()
            biometric_shifted['shifted_timestamp'] = biometric_shifted['timestamp'] - timedelta(hours=lag_hours)
            biometric_daily = biometric_shifted.set_index('shifted_timestamp').resample('D').mean()

            # Align and correlate
            aligned = pd.merge(
                lifestyle_daily[['value']],
                biometric_daily[['value']],
                left_index=True,
                right_index=True,
                suffixes=('_lifestyle', '_biometric')
            )

            if len(aligned) < 3:
                return None

            return aligned['value_lifestyle'].corr(aligned['value_biometric'])

        except Exception:
            return None

    def _get_correlation_strength(self, correlation: float) -> str:
        """Convert correlation to strength description"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.7:
            return "Very Strong"
        elif abs_corr >= 0.5:
            return "Strong"
        elif abs_corr >= 0.3:
            return "Moderate"
        elif abs_corr >= 0.1:
            return "Weak"
        else:
            return "Very Weak"

    def _generate_lifestyle_insights(self, correlations: List[Dict]) -> List[str]:
        """Generate human-readable insights from correlations"""
        insights = []

        # Top positive correlations
        positive_corrs = [c for c in correlations if c['correlation'] > 0.3][:3]
        for corr in positive_corrs:
            direction = "improves" if corr['correlation'] > 0 else "decreases"
            insights.append(
                f"{corr['lifestyle_item'].title()} {direction} {corr['biometric'].replace('_', ' ')} "
                f"({corr['strength']} correlation: r={corr['correlation']:.3f}) "
                f"with {corr['lag_hours']}-hour delay"
            )

        # Top negative correlations (things that hurt performance)
        negative_corrs = [c for c in correlations if c['correlation'] < -0.3][:2]
        for corr in negative_corrs:
            insights.append(
                f"{corr['lifestyle_item'].title()} negatively impacts {corr['biometric'].replace('_', ' ')} "
                f"(r={corr['correlation']:.3f}) {corr['lag_hours']} hours later"
            )

        return insights

    def _generate_recommendations(self, correlations: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Find best performers
        best_supplements = [c for c in correlations if c['lifestyle_category'] == 'supplement' and c['correlation'] > 0.4]
        best_foods = [c for c in correlations if c['lifestyle_category'] == 'food' and c['correlation'] > 0.3]
        best_exercises = [c for c in correlations if c['lifestyle_category'] == 'exercise' and c['correlation'] > 0.3]

        if best_supplements:
            supp = best_supplements[0]
            recommendations.append(f"Continue {supp['lifestyle_item']} supplementation - it strongly improves {supp['biometric']}")

        if best_foods:
            food = best_foods[0]
            recommendations.append(f"Eat more {food['lifestyle_item']} - positive correlation with {food['biometric']}")

        if best_exercises:
            exercise = best_exercises[0]
            recommendations.append(f"Keep up {exercise['lifestyle_item']} - boosts {exercise['biometric']}")

        # Find worst performers to avoid
        worst = [c for c in correlations if c['correlation'] < -0.4][:2]
        for w in worst:
            recommendations.append(f"Consider reducing {w['lifestyle_item']} - negatively affects {w['biometric']}")

        return recommendations

# Convenience functions for SMS integration
def analyze_supplement_effect(user_id: str, supplement_name: str, days_back: int = 14) -> Dict:
    """Quick supplement analysis for SMS queries"""
    analyzer = LifestyleCorrelationAnalyzer()
    return analyzer.analyze_specific_lifestyle_event(user_id, 'supplement', supplement_name, days_back)

def analyze_food_effect(user_id: str, food_name: str, days_back: int = 14) -> Dict:
    """Quick food analysis for SMS queries"""
    analyzer = LifestyleCorrelationAnalyzer()
    return analyzer.analyze_specific_lifestyle_event(user_id, 'meal', food_name, days_back)

def analyze_exercise_effect(user_id: str, exercise_type: str = None, days_back: int = 14) -> Dict:
    """Quick exercise analysis for SMS queries"""
    analyzer = LifestyleCorrelationAnalyzer()
    return analyzer.analyze_specific_lifestyle_event(user_id, 'exercise', exercise_type, days_back)

def get_comprehensive_lifestyle_analysis(user_id: str, days_back: int = 30) -> Dict:
    """Complete lifestyle correlation analysis"""
    analyzer = LifestyleCorrelationAnalyzer()
    return analyzer.analyze_all_lifestyle_correlations(user_id, days_back)

if __name__ == '__main__':
    # Test comprehensive analysis
    result = get_comprehensive_lifestyle_analysis('user_7000', days_back=21)
    print("Comprehensive Analysis:", result)

    # Test specific analyses
    magnesium_result = analyze_supplement_effect('user_7000', 'magnesium')
    print("\nMagnesium Analysis:", magnesium_result)

    chicken_result = analyze_food_effect('user_7000', 'chicken')
    print("\nChicken Analysis:", chicken_result)

    exercise_result = analyze_exercise_effect('user_7000', 'running')
    print("\nExercise Analysis:", exercise_result)