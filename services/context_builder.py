"""
Rich context generation service for enhanced health insights
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
from sqlalchemy import and_

from app.models import (User, Metric, Intervention, Alert, DailyReport,
                       StatisticalBaseline, Correlation)
from utils.database import db
from utils.cache import cache_user_data
from services.statistical_analyzer import StatisticalAnalyzer

logger = logging.getLogger(__name__)

class ContextBuilder:
    """Build rich contextual information for enhanced health insights"""

    def __init__(self):
        self.analyzer = StatisticalAnalyzer()

        # Context categories and their importance weights
        self.context_categories = {
            'temporal': 0.25,      # Time-based patterns
            'behavioral': 0.25,    # User behavior patterns
            'environmental': 0.15, # External factors
            'physiological': 0.20, # Body state indicators
            'intervention': 0.15   # Active interventions
        }

        # Circadian rhythm patterns
        self.circadian_phases = {
            'early_morning': (5, 8),    # 5-8 AM
            'morning': (8, 12),         # 8 AM - 12 PM
            'afternoon': (12, 17),      # 12-5 PM
            'evening': (17, 21),        # 5-9 PM
            'night': (21, 24),          # 9 PM - 12 AM
            'late_night': (0, 5)        # 12-5 AM
        }

    @cache_user_data(expire_seconds=1800)
    def build_comprehensive_context(self, user_id: str,
                                  timeframe: timedelta = timedelta(days=7),
                                  focus_metrics: Optional[List[str]] = None) -> Dict:
        """Build comprehensive context for a user's health data"""
        try:
            logger.info(f"Building comprehensive context for user {user_id}")

            # Get user information
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}

            # Initialize context structure
            context = {
                'user_id': user_id,
                'context_generated_at': datetime.utcnow().isoformat(),
                'timeframe_days': timeframe.days,
                'user_profile': self._build_user_profile(user),
                'temporal_context': {},
                'behavioral_context': {},
                'environmental_context': {},
                'physiological_context': {},
                'intervention_context': {},
                'contextual_insights': [],
                'context_confidence': 0.0
            }

            # Build each context category
            context['temporal_context'] = self._build_temporal_context(user_id, timeframe)
            context['behavioral_context'] = self._build_behavioral_context(user_id, timeframe)
            context['environmental_context'] = self._build_environmental_context(user_id, timeframe)
            context['physiological_context'] = self._build_physiological_context(user_id, timeframe, focus_metrics)
            context['intervention_context'] = self._build_intervention_context(user_id, timeframe)

            # Generate contextual insights
            context['contextual_insights'] = self._generate_contextual_insights(context)

            # Calculate overall context confidence
            context['context_confidence'] = self._calculate_context_confidence(context)

            return context

        except Exception as e:
            logger.error(f"Context building failed for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def _build_user_profile(self, user: User) -> Dict:
        """Build user profile context"""
        try:
            # Calculate user tenure
            tenure_days = (datetime.utcnow() - user.onboarded_at).days

            # Get total data points
            total_metrics = Metric.query.filter_by(user_id=user.id).count()

            # Determine user engagement level
            if tenure_days > 0:
                avg_daily_metrics = total_metrics / tenure_days
                if avg_daily_metrics >= 10:
                    engagement_level = 'high'
                elif avg_daily_metrics >= 5:
                    engagement_level = 'medium'
                else:
                    engagement_level = 'low'
            else:
                engagement_level = 'new'

            return {
                'user_id': user.id,
                'timezone': user.timezone,
                'onboarded_at': user.onboarded_at.isoformat(),
                'tenure_days': tenure_days,
                'total_data_points': total_metrics,
                'engagement_level': engagement_level,
                'preferences': user.preferences,
                'data_quality_score': min(1.0, avg_daily_metrics / 15) if tenure_days > 0 else 0.0
            }

        except Exception as e:
            logger.warning(f"User profile building failed: {str(e)}")
            return {}

    def _build_temporal_context(self, user_id: str, timeframe: timedelta) -> Dict:
        """Build temporal context including circadian and weekly patterns"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timeframe

            # Get metrics in timeframe
            metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.timestamp >= start_time,
                    Metric.timestamp <= end_time
                )
            ).all()

            if not metrics:
                return {'error': 'No data in timeframe'}

            # Group by time patterns
            temporal_patterns = {
                'circadian_patterns': self._analyze_circadian_patterns(metrics),
                'weekly_patterns': self._analyze_weekly_patterns(metrics),
                'data_frequency': self._analyze_data_frequency(metrics),
                'recent_trends': self._analyze_recent_trends(metrics),
                'seasonal_indicators': self._detect_seasonal_indicators(metrics)
            }

            return temporal_patterns

        except Exception as e:
            logger.warning(f"Temporal context building failed: {str(e)}")
            return {'error': str(e)}

    def _analyze_circadian_patterns(self, metrics: List) -> Dict:
        """Analyze circadian rhythm patterns in data"""
        try:
            # Group metrics by hour of day
            hourly_patterns = {}

            for metric in metrics:
                hour = metric.timestamp.hour
                metric_type = metric.metric_type

                if metric_type not in hourly_patterns:
                    hourly_patterns[metric_type] = {}

                if hour not in hourly_patterns[metric_type]:
                    hourly_patterns[metric_type][hour] = []

                hourly_patterns[metric_type][hour].append(metric.value)

            # Calculate statistics for each hour
            circadian_stats = {}
            for metric_type, hour_data in hourly_patterns.items():
                circadian_stats[metric_type] = {}

                for hour, values in hour_data.items():
                    if len(values) >= 2:
                        circadian_stats[metric_type][hour] = {
                            'mean': float(np.mean(values)),
                            'std': float(np.std(values)),
                            'count': len(values),
                            'phase': self._get_circadian_phase(hour)
                        }

            # Identify peak performance times
            peak_times = self._identify_peak_times(circadian_stats)

            return {
                'hourly_patterns': circadian_stats,
                'peak_performance_times': peak_times,
                'circadian_regularity': self._calculate_circadian_regularity(circadian_stats)
            }

        except Exception as e:
            logger.warning(f"Circadian pattern analysis failed: {str(e)}")
            return {}

    def _analyze_weekly_patterns(self, metrics: List) -> Dict:
        """Analyze weekly patterns in data"""
        try:
            # Group by day of week (0=Monday, 6=Sunday)
            daily_patterns = {}

            for metric in metrics:
                day_of_week = metric.timestamp.weekday()
                metric_type = metric.metric_type

                if metric_type not in daily_patterns:
                    daily_patterns[metric_type] = {}

                if day_of_week not in daily_patterns[metric_type]:
                    daily_patterns[metric_type][day_of_week] = []

                daily_patterns[metric_type][day_of_week].append(metric.value)

            # Calculate weekly statistics
            weekly_stats = {}
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            for metric_type, day_data in daily_patterns.items():
                weekly_stats[metric_type] = {}

                for day_num, values in day_data.items():
                    if len(values) >= 2:
                        day_name = day_names[day_num]
                        weekly_stats[metric_type][day_name] = {
                            'mean': float(np.mean(values)),
                            'std': float(np.std(values)),
                            'count': len(values),
                            'day_type': 'weekend' if day_num >= 5 else 'weekday'
                        }

            # Identify weekend vs weekday differences
            weekend_differences = self._analyze_weekend_differences(weekly_stats)

            return {
                'daily_patterns': weekly_stats,
                'weekend_vs_weekday': weekend_differences,
                'weekly_consistency': self._calculate_weekly_consistency(weekly_stats)
            }

        except Exception as e:
            logger.warning(f"Weekly pattern analysis failed: {str(e)}")
            return {}

    def _build_behavioral_context(self, user_id: str, timeframe: timedelta) -> Dict:
        """Build behavioral context from lifestyle data"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timeframe

            # Get lifestyle events (meals, supplements, activities)
            lifestyle_metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.timestamp >= start_time,
                    Metric.metric_type.in_(['meal_timing', 'supplement_intake', 'exercise_duration', 'stress_level'])
                )
            ).all()

            behavioral_patterns = {
                'meal_patterns': self._analyze_meal_patterns(lifestyle_metrics),
                'supplement_adherence': self._analyze_supplement_adherence(lifestyle_metrics),
                'exercise_habits': self._analyze_exercise_habits(lifestyle_metrics),
                'stress_patterns': self._analyze_stress_patterns(lifestyle_metrics),
                'lifestyle_consistency': 0.0
            }

            # Calculate overall lifestyle consistency
            behavioral_patterns['lifestyle_consistency'] = self._calculate_lifestyle_consistency(
                behavioral_patterns
            )

            return behavioral_patterns

        except Exception as e:
            logger.warning(f"Behavioral context building failed: {str(e)}")
            return {}

    def _build_environmental_context(self, user_id: str, timeframe: timedelta) -> Dict:
        """Build environmental context (travel, schedule changes, etc.)"""
        try:
            # This is a simplified version - in practice, you might integrate with:
            # - Weather APIs
            # - Calendar APIs
            # - Travel detection
            # - Sleep environment data

            end_time = datetime.utcnow()
            start_time = end_time - timeframe

            # Detect data irregularities that might indicate environmental changes
            metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.timestamp >= start_time
                )
            ).all()

            environmental_indicators = {
                'data_collection_irregularities': self._detect_collection_irregularities(metrics),
                'potential_travel_periods': self._detect_potential_travel(metrics),
                'schedule_disruptions': self._detect_schedule_disruptions(metrics),
                'environmental_stability_score': 0.0
            }

            # Calculate environmental stability
            environmental_indicators['environmental_stability_score'] = self._calculate_environmental_stability(
                environmental_indicators
            )

            return environmental_indicators

        except Exception as e:
            logger.warning(f"Environmental context building failed: {str(e)}")
            return {}

    def _build_physiological_context(self, user_id: str, timeframe: timedelta,
                                   focus_metrics: Optional[List[str]] = None) -> Dict:
        """Build physiological context from health metrics"""
        try:
            # Get baseline statistics for comparison
            baselines = {}
            available_metrics = ['hrv', 'sleep_score', 'heart_rate', 'temperature', 'recovery']

            if focus_metrics:
                available_metrics = focus_metrics

            for metric_type in available_metrics:
                baseline = self.analyzer._get_baseline_statistics(user_id, metric_type)
                if baseline:
                    baselines[metric_type] = baseline

            # Get recent data for trend analysis
            recent_analysis = self.analyzer.run_comprehensive_analysis(user_id, timeframe)

            physiological_context = {
                'current_baselines': baselines,
                'recent_trends': recent_analysis.get('trend_analysis', {}),
                'anomaly_frequency': self._calculate_anomaly_frequency(recent_analysis),
                'metric_correlations': recent_analysis.get('correlation_analysis', {}),
                'physiological_coherence': self._assess_physiological_coherence(baselines, recent_analysis),
                'recovery_patterns': self._analyze_recovery_patterns(user_id, timeframe)
            }

            return physiological_context

        except Exception as e:
            logger.warning(f"Physiological context building failed: {str(e)}")
            return {}

    def _build_intervention_context(self, user_id: str, timeframe: timedelta) -> Dict:
        """Build context about active and recent interventions"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timeframe

            # Get active interventions
            active_interventions = Intervention.query.filter(
                and_(
                    Intervention.user_id == user_id,
                    Intervention.is_active == True
                )
            ).all()

            # Get recently ended interventions
            recent_interventions = Intervention.query.filter(
                and_(
                    Intervention.user_id == user_id,
                    Intervention.ended_at >= start_time,
                    Intervention.ended_at <= end_time
                )
            ).all()

            intervention_context = {
                'active_interventions': self._summarize_interventions(active_interventions),
                'recent_interventions': self._summarize_interventions(recent_interventions),
                'intervention_overlap': len(active_interventions) > 1,
                'intervention_burden': self._calculate_intervention_burden(active_interventions),
                'expected_effects': self._predict_intervention_effects(active_interventions)
            }

            return intervention_context

        except Exception as e:
            logger.warning(f"Intervention context building failed: {str(e)}")
            return {}

    def _generate_contextual_insights(self, context: Dict) -> List[Dict]:
        """Generate insights based on comprehensive context"""
        try:
            insights = []

            # Temporal insights
            temporal_ctx = context.get('temporal_context', {})
            if 'circadian_patterns' in temporal_ctx:
                circadian_insights = self._extract_circadian_insights(temporal_ctx['circadian_patterns'])
                insights.extend(circadian_insights)

            # Behavioral insights
            behavioral_ctx = context.get('behavioral_context', {})
            if behavioral_ctx:
                behavioral_insights = self._extract_behavioral_insights(behavioral_ctx)
                insights.extend(behavioral_insights)

            # Physiological insights
            physiological_ctx = context.get('physiological_context', {})
            if physiological_ctx:
                physio_insights = self._extract_physiological_insights(physiological_ctx)
                insights.extend(physio_insights)

            # Intervention insights
            intervention_ctx = context.get('intervention_context', {})
            if intervention_ctx:
                intervention_insights = self._extract_intervention_insights(intervention_ctx)
                insights.extend(intervention_insights)

            # Cross-domain insights
            cross_insights = self._extract_cross_domain_insights(context)
            insights.extend(cross_insights)

            # Sort by importance/confidence
            insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)

            return insights[:10]  # Return top 10 insights

        except Exception as e:
            logger.warning(f"Contextual insight generation failed: {str(e)}")
            return []

    def _get_circadian_phase(self, hour: int) -> str:
        """Get circadian phase for given hour"""
        for phase, (start, end) in self.circadian_phases.items():
            if start <= hour < end:
                return phase
        return 'unknown'

    def _identify_peak_times(self, circadian_stats: Dict) -> Dict:
        """Identify peak performance times for each metric"""
        peak_times = {}

        try:
            for metric_type, hour_data in circadian_stats.items():
                if not hour_data:
                    continue

                # Find hour with highest mean value (assuming higher is better for most metrics)
                peak_hour = max(hour_data.keys(), key=lambda h: hour_data[h]['mean'])
                peak_phase = self._get_circadian_phase(peak_hour)

                peak_times[metric_type] = {
                    'peak_hour': peak_hour,
                    'peak_phase': peak_phase,
                    'peak_value': hour_data[peak_hour]['mean'],
                    'consistency': 1.0 - (hour_data[peak_hour]['std'] / hour_data[peak_hour]['mean'])
                }

        except Exception as e:
            logger.warning(f"Peak time identification failed: {str(e)}")

        return peak_times

    def _calculate_circadian_regularity(self, circadian_stats: Dict) -> float:
        """Calculate how regular the circadian patterns are"""
        try:
            if not circadian_stats:
                return 0.0

            regularity_scores = []

            for metric_type, hour_data in circadian_stats.items():
                if len(hour_data) < 6:  # Need data from at least 6 hours
                    continue

                # Calculate coefficient of variation across hours
                means = [data['mean'] for data in hour_data.values()]
                mean_of_means = np.mean(means)
                std_of_means = np.std(means)

                if mean_of_means > 0:
                    cv = std_of_means / mean_of_means
                    regularity = max(0.0, 1.0 - cv)  # Lower CV = higher regularity
                    regularity_scores.append(regularity)

            return float(np.mean(regularity_scores)) if regularity_scores else 0.0

        except Exception as e:
            logger.warning(f"Circadian regularity calculation failed: {str(e)}")
            return 0.0

    def _calculate_context_confidence(self, context: Dict) -> float:
        """Calculate overall confidence in the context analysis"""
        try:
            confidence_factors = []

            # Data quality factor
            user_profile = context.get('user_profile', {})
            data_quality = user_profile.get('data_quality_score', 0)
            confidence_factors.append(data_quality)

            # Temporal context confidence
            temporal_ctx = context.get('temporal_context', {})
            if temporal_ctx and 'error' not in temporal_ctx:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.2)

            # Behavioral context confidence
            behavioral_ctx = context.get('behavioral_context', {})
            if behavioral_ctx and 'error' not in behavioral_ctx:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.3)

            # Physiological context confidence
            physio_ctx = context.get('physiological_context', {})
            if physio_ctx and 'error' not in physio_ctx:
                confidence_factors.append(0.9)
            else:
                confidence_factors.append(0.4)

            overall_confidence = np.mean(confidence_factors)
            return float(overall_confidence)

        except Exception as e:
            logger.warning(f"Context confidence calculation failed: {str(e)}")
            return 0.5

    # Additional helper methods (simplified implementations)

    def _analyze_meal_patterns(self, lifestyle_metrics: List) -> Dict:
        """Analyze meal timing patterns"""
        meal_metrics = [m for m in lifestyle_metrics if m.metric_type == 'meal_timing']

        if not meal_metrics:
            return {'no_data': True}

        meal_times = [m.value for m in meal_metrics]

        return {
            'average_meal_time': float(np.mean(meal_times)),
            'meal_timing_consistency': float(1.0 - np.std(meal_times) / 24),
            'meal_frequency': len(meal_metrics) / 7,  # Assuming 7-day timeframe
            'late_meals': sum(1 for t in meal_times if t >= 20)  # After 8 PM
        }

    def _analyze_supplement_adherence(self, lifestyle_metrics: List) -> Dict:
        """Analyze supplement adherence patterns"""
        supplement_metrics = [m for m in lifestyle_metrics if m.metric_type == 'supplement_intake']

        if not supplement_metrics:
            return {'no_data': True}

        total_days = 7  # Assuming 7-day timeframe
        supplement_days = len(set(m.timestamp.date() for m in supplement_metrics))

        return {
            'adherence_rate': supplement_days / total_days,
            'total_supplements': len(supplement_metrics),
            'consistent_timing': len(supplement_metrics) > 0
        }

    def _analyze_exercise_habits(self, lifestyle_metrics: List) -> Dict:
        """Analyze exercise patterns"""
        exercise_metrics = [m for m in lifestyle_metrics if m.metric_type == 'exercise_duration']

        if not exercise_metrics:
            return {'no_data': True}

        durations = [m.value for m in exercise_metrics]

        return {
            'total_exercise_sessions': len(exercise_metrics),
            'average_duration': float(np.mean(durations)),
            'exercise_frequency': len(exercise_metrics) / 7,
            'exercise_consistency': float(1.0 - np.std(durations) / np.mean(durations)) if len(durations) > 1 else 1.0
        }

    def _extract_circadian_insights(self, circadian_data: Dict) -> List[Dict]:
        """Extract insights from circadian patterns"""
        insights = []

        peak_times = circadian_data.get('peak_performance_times', {})
        for metric, peak_info in peak_times.items():
            if peak_info.get('consistency', 0) > 0.7:
                insights.append({
                    'type': 'circadian_peak',
                    'metric': metric,
                    'message': f"Your {metric} peaks consistently during {peak_info['peak_phase']} ({peak_info['peak_hour']}:00)",
                    'confidence': peak_info['consistency'],
                    'actionable': True,
                    'recommendation': f"Schedule important activities during your {metric} peak time"
                })

        return insights

    def _extract_behavioral_insights(self, behavioral_data: Dict) -> List[Dict]:
        """Extract insights from behavioral patterns"""
        insights = []

        meal_patterns = behavioral_data.get('meal_patterns', {})
        if 'late_meals' in meal_patterns and meal_patterns['late_meals'] > 2:
            insights.append({
                'type': 'meal_timing',
                'message': f"You had {meal_patterns['late_meals']} late meals this week",
                'confidence': 0.8,
                'actionable': True,
                'recommendation': "Try eating dinner before 8 PM for better sleep quality"
            })

        return insights

    def _extract_cross_domain_insights(self, context: Dict) -> List[Dict]:
        """Extract insights that span multiple context domains"""
        insights = []

        # Example: correlate meal timing with sleep quality
        behavioral_ctx = context.get('behavioral_context', {})
        physiological_ctx = context.get('physiological_context', {})

        if behavioral_ctx and physiological_ctx:
            insights.append({
                'type': 'cross_domain',
                'message': "Analyzing relationships between your behavior and physiology",
                'confidence': 0.6,
                'actionable': False,
                'recommendation': "Continue tracking for more personalized insights"
            })

        return insights