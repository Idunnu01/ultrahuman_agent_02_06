"""
Intervention effectiveness tracking with rigorous statistical analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
from sqlalchemy import and_

from app.models import (User, Metric, Intervention, InterventionEffectiveness,
                       StatisticalBaseline, SystemLog)
from utils.database import db, db_transaction
from utils.stats_utils import (StatisticalTests, EffectSizeCalculator,
                              StatisticalValidator, ConfidenceIntervals)
from utils.cache import cache_user_data
from services.statistical_analyzer import StatisticalAnalyzer

logger = logging.getLogger(__name__)

class InterventionTracker:
    """Track and analyze the effectiveness of health interventions with statistical rigor"""

    def __init__(self):
        self.analyzer = StatisticalAnalyzer()
        self.min_sample_size = 7  # Minimum days for analysis
        self.significance_alpha = 0.05
        self.minimum_effect_size = 0.2  # Small effect size threshold

        # Intervention categories and their typical effects
        self.intervention_categories = {
            'supplement': {
                'typical_onset_days': 3,
                'full_effect_days': 14,
                'expected_metrics': ['sleep_score', 'hrv', 'recovery']
            },
            'sleep_hygiene': {
                'typical_onset_days': 1,
                'full_effect_days': 7,
                'expected_metrics': ['sleep_score', 'sleep_efficiency', 'hrv']
            },
            'exercise': {
                'typical_onset_days': 1,
                'full_effect_days': 21,
                'expected_metrics': ['hrv', 'recovery', 'heart_rate']
            },
            'nutrition': {
                'typical_onset_days': 2,
                'full_effect_days': 10,
                'expected_metrics': ['sleep_score', 'hrv', 'recovery']
            },
            'stress_management': {
                'typical_onset_days': 1,
                'full_effect_days': 14,
                'expected_metrics': ['hrv', 'stress', 'recovery']
            }
        }

    def start_intervention(self, user_id: str, intervention_data: Dict) -> Dict:
        """Start tracking a new intervention"""
        try:
            logger.info(f"Starting intervention tracking for user {user_id}: {intervention_data.get('name')}")

            # Validate user exists and is active
            user = User.query.get(user_id)
            if not user or not user.is_active:
                return {'error': 'User not found or inactive'}

            # Validate intervention data
            validation_result = self._validate_intervention_data(intervention_data)
            if not validation_result['is_valid']:
                return {'error': f'Validation failed: {validation_result["errors"]}'}

            # Check for overlapping interventions
            overlap_check = self._check_intervention_overlap(user_id, intervention_data)
            if overlap_check['has_overlap']:
                logger.warning(f"Overlapping interventions detected for user {user_id}")
                # Continue but flag for analysis

            # Create intervention record
            with db_transaction():
                intervention = Intervention(
                    user_id=user_id,
                    name=intervention_data['name'],
                    description=intervention_data.get('description', ''),
                    category=intervention_data.get('category', 'general'),
                    started_at=datetime.utcnow(),
                    target_metrics=intervention_data.get('target_metrics', []),
                    parameters=intervention_data.get('parameters', {}),
                    is_active=True
                )

                db.session.add(intervention)
                db.session.flush()  # Get intervention ID

                # Establish baseline measurements
                baseline_result = self._establish_intervention_baseline(user_id, intervention)

                if 'error' in baseline_result:
                    logger.warning(f"Baseline establishment failed: {baseline_result['error']}")
                    # Continue anyway - baseline can be established later

                intervention_id = intervention.id

            # Log intervention start
            self._log_intervention_event(
                user_id, intervention_id, 'started',
                {'baseline_result': baseline_result}
            )

            return {
                'success': True,
                'intervention_id': intervention_id,
                'started_at': intervention.started_at.isoformat(),
                'baseline_established': 'error' not in baseline_result,
                'overlap_warning': overlap_check['has_overlap'],
                'expected_results_timeline': self._get_expected_timeline(intervention_data.get('category', 'general'))
            }

        except Exception as e:
            logger.error(f"Failed to start intervention for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def end_intervention(self, user_id: str, intervention_id: int,
                        reason: str = 'completed') -> Dict:
        """End an intervention and calculate its effectiveness"""
        try:
            logger.info(f"Ending intervention {intervention_id} for user {user_id}")

            # Get intervention
            intervention = Intervention.query.filter_by(
                id=intervention_id, user_id=user_id, is_active=True
            ).first()

            if not intervention:
                return {'error': 'Active intervention not found'}

            # Calculate duration
            duration = datetime.utcnow() - intervention.started_at

            if duration.days < 1:
                return {
                    'error': 'Intervention too short for analysis',
                    'minimum_duration': '1 day',
                    'actual_duration': f'{duration.total_seconds()/3600:.1f} hours'
                }

            # Calculate effectiveness
            effectiveness_result = self.calculate_effectiveness(intervention)

            # Update intervention record
            with db_transaction():
                intervention.ended_at = datetime.utcnow()
                intervention.is_active = False
                intervention.effectiveness_scores = effectiveness_result.get('effectiveness_scores', {})
                intervention.confidence_scores = effectiveness_result.get('confidence_scores', {})

                # Store detailed effectiveness analysis
                if 'effectiveness_analysis' in effectiveness_result:
                    for metric_type, analysis in effectiveness_result['effectiveness_analysis'].items():
                        effectiveness_record = InterventionEffectiveness(
                            intervention_id=intervention_id,
                            metric_type=metric_type,
                            before_mean=analysis.get('before_mean'),
                            before_std=analysis.get('before_std'),
                            after_mean=analysis.get('after_mean'),
                            after_std=analysis.get('after_std'),
                            t_statistic=analysis.get('t_statistic'),
                            t_p_value=analysis.get('t_p_value'),
                            wilcoxon_statistic=analysis.get('wilcoxon_statistic'),
                            wilcoxon_p_value=analysis.get('wilcoxon_p_value'),
                            cohens_d=analysis.get('cohens_d'),
                            trend_change_point=intervention.started_at,
                            trend_slope_before=analysis.get('trend_slope_before'),
                            trend_slope_after=analysis.get('trend_slope_after'),
                            overall_confidence=analysis.get('overall_confidence'),
                            sample_size_before=analysis.get('sample_size_before'),
                            sample_size_after=analysis.get('sample_size_after')
                        )
                        db.session.add(effectiveness_record)

            # Log intervention end
            self._log_intervention_event(
                user_id, intervention_id, 'ended',
                {'reason': reason, 'effectiveness_summary': effectiveness_result.get('summary', {})}
            )

            return {
                'success': True,
                'intervention_id': intervention_id,
                'duration_days': duration.days,
                'ended_at': intervention.ended_at.isoformat(),
                'effectiveness_analysis': effectiveness_result,
                'summary': self._generate_effectiveness_summary(effectiveness_result)
            }

        except Exception as e:
            logger.error(f"Failed to end intervention {intervention_id}: {str(e)}")
            return {'error': str(e)}

    def calculate_effectiveness(self, intervention: Intervention) -> Dict:
        """Calculate statistical effectiveness of an intervention"""
        try:
            logger.info(f"Calculating effectiveness for intervention {intervention.id}")

            # Define analysis periods
            before_period = timedelta(days=14)  # 2 weeks before
            after_period = datetime.utcnow() - intervention.started_at

            # Minimum analysis period
            if after_period.days < self.min_sample_size:
                return {
                    'error': f'Insufficient intervention period: {after_period.days} days (minimum: {self.min_sample_size})',
                    'recommendation': 'Continue intervention for more reliable analysis'
                }

            # Get target metrics or use defaults
            target_metrics = intervention.target_metrics
            if not target_metrics:
                category_info = self.intervention_categories.get(intervention.category, {})
                target_metrics = category_info.get('expected_metrics', ['hrv', 'sleep_score', 'recovery'])

            effectiveness_results = {
                'intervention_id': intervention.id,
                'analysis_date': datetime.utcnow().isoformat(),
                'analysis_periods': {
                    'before_days': before_period.days,
                    'after_days': after_period.days,
                    'intervention_start': intervention.started_at.isoformat()
                },
                'target_metrics': target_metrics,
                'effectiveness_analysis': {},
                'effectiveness_scores': {},
                'confidence_scores': {},
                'summary': {}
            }

            # Analyze each target metric
            for metric_type in target_metrics:
                try:
                    metric_analysis = self._analyze_metric_effectiveness(
                        intervention.user_id, metric_type, intervention.started_at,
                        before_period, after_period
                    )

                    if 'error' not in metric_analysis:
                        effectiveness_results['effectiveness_analysis'][metric_type] = metric_analysis

                        # Extract effectiveness score
                        effectiveness_score = self._calculate_effectiveness_score(metric_analysis)
                        effectiveness_results['effectiveness_scores'][metric_type] = effectiveness_score

                        # Extract confidence score
                        confidence_score = self._calculate_confidence_score(metric_analysis)
                        effectiveness_results['confidence_scores'][metric_type] = confidence_score
                    else:
                        logger.warning(f"Metric {metric_type} analysis failed: {metric_analysis['error']}")

                except Exception as e:
                    logger.error(f"Failed to analyze metric {metric_type}: {str(e)}")
                    continue

            # Generate overall summary
            effectiveness_results['summary'] = self._generate_overall_summary(effectiveness_results)

            # Check for confounding factors
            confounding_analysis = self._analyze_confounding_factors(
                intervention.user_id, intervention.started_at, after_period
            )
            effectiveness_results['confounding_analysis'] = confounding_analysis

            return effectiveness_results

        except Exception as e:
            logger.error(f"Effectiveness calculation failed: {str(e)}")
            return {'error': str(e)}

    def _analyze_metric_effectiveness(self, user_id: str, metric_type: str,
                                    intervention_start: datetime,
                                    before_period: timedelta, after_period: timedelta) -> Dict:
        """Analyze effectiveness for a specific metric"""
        try:
            # Define time windows
            before_start = intervention_start - before_period
            before_end = intervention_start
            after_start = intervention_start
            after_end = intervention_start + after_period

            # Get before data
            before_metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.metric_type == metric_type,
                    Metric.timestamp >= before_start,
                    Metric.timestamp < before_end
                )
            ).order_by(Metric.timestamp).all()

            # Get after data
            after_metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.metric_type == metric_type,
                    Metric.timestamp >= after_start,
                    Metric.timestamp <= after_end
                )
            ).order_by(Metric.timestamp).all()

            if len(before_metrics) < 3 or len(after_metrics) < 3:
                return {
                    'error': f'Insufficient data: {len(before_metrics)} before, {len(after_metrics)} after (minimum: 3 each)',
                    'data_availability': {
                        'before_count': len(before_metrics),
                        'after_count': len(after_metrics)
                    }
                }

            # Extract values
            before_values = np.array([m.value for m in before_metrics])
            after_values = np.array([m.value for m in after_metrics])

            # Remove any NaN values
            before_values = before_values[~np.isnan(before_values)]
            after_values = after_values[~np.isnan(after_values)]

            if len(before_values) < 3 or len(after_values) < 3:
                return {'error': 'Insufficient clean data after removing invalid values'}

            # Comprehensive statistical analysis
            analysis = {
                'metric_type': metric_type,
                'sample_sizes': {
                    'before': len(before_values),
                    'after': len(after_values)
                },
                'descriptive_stats': {
                    'before': {
                        'mean': float(np.mean(before_values)),
                        'median': float(np.median(before_values)),
                        'std': float(np.std(before_values, ddof=1)),
                        'min': float(np.min(before_values)),
                        'max': float(np.max(before_values))
                    },
                    'after': {
                        'mean': float(np.mean(after_values)),
                        'median': float(np.median(after_values)),
                        'std': float(np.std(after_values, ddof=1)),
                        'min': float(np.min(after_values)),
                        'max': float(np.max(after_values))
                    }
                }
            }

            # Calculate change
            mean_change = analysis['descriptive_stats']['after']['mean'] - analysis['descriptive_stats']['before']['mean']
            percent_change = (mean_change / analysis['descriptive_stats']['before']['mean']) * 100 if analysis['descriptive_stats']['before']['mean'] != 0 else 0

            analysis['change_analysis'] = {
                'absolute_change': float(mean_change),
                'percent_change': float(percent_change),
                'direction': 'improvement' if mean_change > 0 else 'decline' if mean_change < 0 else 'no_change'
            }

            # Statistical tests
            statistical_tests = StatisticalTests.paired_comparison(before_values, after_values)
            analysis['statistical_tests'] = statistical_tests

            # Effect size calculations
            cohens_d = EffectSizeCalculator.cohens_d(after_values, before_values)
            hedges_g = EffectSizeCalculator.hedges_g(after_values, before_values)

            analysis['effect_size'] = {
                'cohens_d': float(cohens_d),
                'hedges_g': float(hedges_g),
                'interpretation': EffectSizeCalculator.interpret_effect_size(cohens_d),
                'magnitude': 'large' if abs(cohens_d) >= 0.8 else 'medium' if abs(cohens_d) >= 0.5 else 'small' if abs(cohens_d) >= 0.2 else 'negligible'
            }

            # Trend analysis
            trend_analysis = self._analyze_intervention_trends(
                before_values, after_values,
                [m.timestamp for m in before_metrics],
                [m.timestamp for m in after_metrics],
                intervention_start
            )
            analysis['trend_analysis'] = trend_analysis

            # Clinical significance
            clinical_significance = self._assess_clinical_significance(
                metric_type, mean_change, percent_change, analysis['descriptive_stats']['before']['mean']
            )
            analysis['clinical_significance'] = clinical_significance

            # Overall confidence assessment
            analysis['overall_confidence'] = self._calculate_analysis_confidence(analysis)

            return analysis

        except Exception as e:
            logger.error(f"Metric effectiveness analysis failed for {metric_type}: {str(e)}")
            return {'error': str(e)}

    def _analyze_intervention_trends(self, before_values: np.ndarray, after_values: np.ndarray,
                                   before_timestamps: List, after_timestamps: List,
                                   intervention_start: datetime) -> Dict:
        """Analyze trends before and after intervention"""
        try:
            from scipy.stats import linregress

            trend_analysis = {}

            # Before intervention trend
            if len(before_values) >= 3:
                before_days = [(ts - before_timestamps[0]).days for ts in before_timestamps]
                slope_before, intercept_before, r_value_before, p_value_before, _ = linregress(before_days, before_values)

                trend_analysis['before_intervention'] = {
                    'slope': float(slope_before),
                    'r_squared': float(r_value_before**2),
                    'p_value': float(p_value_before),
                    'trend_direction': 'improving' if slope_before > 0 else 'declining' if slope_before < 0 else 'stable',
                    'significance': p_value_before < 0.05
                }

            # After intervention trend
            if len(after_values) >= 3:
                after_days = [(ts - intervention_start).days for ts in after_timestamps]
                slope_after, intercept_after, r_value_after, p_value_after, _ = linregress(after_days, after_values)

                trend_analysis['after_intervention'] = {
                    'slope': float(slope_after),
                    'r_squared': float(r_value_after**2),
                    'p_value': float(p_value_after),
                    'trend_direction': 'improving' if slope_after > 0 else 'declining' if slope_after < 0 else 'stable',
                    'significance': p_value_after < 0.05
                }

            # Trend change analysis
            if 'before_intervention' in trend_analysis and 'after_intervention' in trend_analysis:
                slope_change = trend_analysis['after_intervention']['slope'] - trend_analysis['before_intervention']['slope']
                trend_analysis['trend_change'] = {
                    'slope_change': float(slope_change),
                    'improvement': slope_change > 0,
                    'magnitude': 'large' if abs(slope_change) > 1 else 'medium' if abs(slope_change) > 0.5 else 'small'
                }

            return trend_analysis

        except Exception as e:
            logger.warning(f"Trend analysis failed: {str(e)}")
            return {'error': str(e)}

    def _assess_clinical_significance(self, metric_type: str, absolute_change: float,
                                    percent_change: float, baseline_mean: float) -> Dict:
        """Assess clinical significance of the change"""
        try:
            # Define clinically meaningful changes for different metrics
            clinical_thresholds = {
                'hrv': {'absolute': 5, 'percent': 10},  # 5ms or 10% change
                'sleep_score': {'absolute': 5, 'percent': 8},  # 5 points or 8% change
                'heart_rate': {'absolute': 3, 'percent': 5},  # 3 bpm or 5% change
                'recovery': {'absolute': 10, 'percent': 12},  # 10 points or 12% change
                'sleep_efficiency': {'absolute': 3, 'percent': 5},  # 3% or 5% change
                'temperature': {'absolute': 0.2, 'percent': 1}  # 0.2°C or 1% change
            }

            threshold = clinical_thresholds.get(metric_type, {'absolute': baseline_mean * 0.1, 'percent': 10})

            is_clinically_significant = (
                abs(absolute_change) >= threshold['absolute'] or
                abs(percent_change) >= threshold['percent']
            )

            return {
                'is_clinically_significant': is_clinically_significant,
                'absolute_threshold': threshold['absolute'],
                'percent_threshold': threshold['percent'],
                'absolute_change': absolute_change,
                'percent_change': percent_change,
                'interpretation': self._interpret_clinical_significance(
                    is_clinically_significant, absolute_change, metric_type
                )
            }

        except Exception as e:
            logger.warning(f"Clinical significance assessment failed: {str(e)}")
            return {'error': str(e)}

    def _interpret_clinical_significance(self, is_significant: bool, change: float, metric_type: str) -> str:
        """Interpret clinical significance result"""
        if not is_significant:
            return f"Change in {metric_type} is not clinically meaningful"

        direction = "improvement" if change > 0 else "decline"
        magnitude = "substantial" if abs(change) > 10 else "moderate"

        return f"Clinically meaningful {magnitude} {direction} in {metric_type}"

    def _calculate_effectiveness_score(self, analysis: Dict) -> float:
        """Calculate overall effectiveness score (0-100)"""
        try:
            if 'error' in analysis:
                return 0.0

            score_components = []

            # Statistical significance component (0-30 points)
            statistical_tests = analysis.get('statistical_tests', {})
            if statistical_tests.get('t_test', {}).get('significant', False):
                score_components.append(20)
            elif statistical_tests.get('wilcoxon', {}).get('significant', False):
                score_components.append(15)
            else:
                score_components.append(0)

            # Effect size component (0-40 points)
            effect_size = analysis.get('effect_size', {})
            cohens_d = abs(effect_size.get('cohens_d', 0))

            if cohens_d >= 0.8:  # Large effect
                score_components.append(40)
            elif cohens_d >= 0.5:  # Medium effect
                score_components.append(25)
            elif cohens_d >= 0.2:  # Small effect
                score_components.append(15)
            else:
                score_components.append(0)

            # Clinical significance component (0-20 points)
            clinical_sig = analysis.get('clinical_significance', {})
            if clinical_sig.get('is_clinically_significant', False):
                score_components.append(20)
            else:
                score_components.append(5)

            # Trend improvement component (0-10 points)
            trend_analysis = analysis.get('trend_analysis', {})
            trend_change = trend_analysis.get('trend_change', {})
            if trend_change.get('improvement', False):
                score_components.append(10)
            else:
                score_components.append(0)

            total_score = sum(score_components)
            return float(min(100, max(0, total_score)))

        except Exception as e:
            logger.warning(f"Effectiveness score calculation failed: {str(e)}")
            return 0.0

    def _calculate_confidence_score(self, analysis: Dict) -> float:
        """Calculate confidence in the analysis (0-100)"""
        try:
            if 'error' in analysis:
                return 0.0

            confidence_components = []

            # Sample size component (0-30 points)
            sample_sizes = analysis.get('sample_sizes', {})
            min_sample = min(sample_sizes.get('before', 0), sample_sizes.get('after', 0))

            if min_sample >= 14:
                confidence_components.append(30)
            elif min_sample >= 7:
                confidence_components.append(20)
            elif min_sample >= 3:
                confidence_components.append(10)
            else:
                confidence_components.append(0)

            # Statistical power component (0-25 points)
            statistical_tests = analysis.get('statistical_tests', {})
            p_value = statistical_tests.get('t_test', {}).get('p_value', 1.0)

            if p_value < 0.01:
                confidence_components.append(25)
            elif p_value < 0.05:
                confidence_components.append(20)
            elif p_value < 0.1:
                confidence_components.append(10)
            else:
                confidence_components.append(0)

            # Effect size certainty (0-25 points)
            effect_size = analysis.get('effect_size', {})
            cohens_d = abs(effect_size.get('cohens_d', 0))

            if cohens_d >= 0.5:
                confidence_components.append(25)
            elif cohens_d >= 0.2:
                confidence_components.append(15)
            else:
                confidence_components.append(5)

            # Data quality component (0-20 points)
            # Based on sample balance and completeness
            before_size = sample_sizes.get('before', 0)
            after_size = sample_sizes.get('after', 0)

            if before_size > 0 and after_size > 0:
                balance_ratio = min(before_size, after_size) / max(before_size, after_size)
                if balance_ratio >= 0.7:
                    confidence_components.append(20)
                elif balance_ratio >= 0.5:
                    confidence_components.append(15)
                else:
                    confidence_components.append(10)
            else:
                confidence_components.append(0)

            total_confidence = sum(confidence_components)
            return float(min(100, max(0, total_confidence)))

        except Exception as e:
            logger.warning(f"Confidence score calculation failed: {str(e)}")
            return 0.0

    def _calculate_analysis_confidence(self, analysis: Dict) -> float:
        """Calculate overall confidence in the analysis results"""
        try:
            # This is a simplified version - full implementation would consider:
            # - Sample size adequacy
            # - Statistical power
            # - Effect size consistency
            # - Data quality metrics

            confidence_factors = []

            # Sample size factor
            sample_sizes = analysis.get('sample_sizes', {})
            min_sample = min(sample_sizes.get('before', 0), sample_sizes.get('after', 0))
            sample_factor = min(1.0, min_sample / 14)  # 14 days ideal
            confidence_factors.append(sample_factor)

            # Statistical significance factor
            statistical_tests = analysis.get('statistical_tests', {})
            if statistical_tests.get('t_test', {}).get('significant', False):
                confidence_factors.append(1.0)
            else:
                confidence_factors.append(0.5)

            # Effect size factor
            effect_size = analysis.get('effect_size', {})
            cohens_d = abs(effect_size.get('cohens_d', 0))
            effect_factor = min(1.0, cohens_d / 0.8)  # 0.8 is large effect
            confidence_factors.append(effect_factor)

            overall_confidence = np.mean(confidence_factors)
            return float(overall_confidence)

        except Exception as e:
            logger.warning(f"Analysis confidence calculation failed: {str(e)}")
            return 0.5

    def _generate_overall_summary(self, effectiveness_results: Dict) -> Dict:
        """Generate overall summary of intervention effectiveness"""
        try:
            effectiveness_scores = effectiveness_results.get('effectiveness_scores', {})
            confidence_scores = effectiveness_results.get('confidence_scores', {})

            if not effectiveness_scores:
                return {'overall_assessment': 'insufficient_data'}

            # Calculate averages
            avg_effectiveness = np.mean(list(effectiveness_scores.values()))
            avg_confidence = np.mean(list(confidence_scores.values()))

            # Count significant results
            significant_metrics = 0
            total_metrics = 0

            for metric_type, analysis in effectiveness_results.get('effectiveness_analysis', {}).items():
                total_metrics += 1
                statistical_tests = analysis.get('statistical_tests', {})
                if statistical_tests.get('t_test', {}).get('significant', False):
                    significant_metrics += 1

            # Overall assessment
            if avg_effectiveness >= 70 and avg_confidence >= 70:
                overall_assessment = 'highly_effective'
            elif avg_effectiveness >= 50 and avg_confidence >= 60:
                overall_assessment = 'moderately_effective'
            elif avg_effectiveness >= 30:
                overall_assessment = 'minimally_effective'
            else:
                overall_assessment = 'not_effective'

            return {
                'overall_assessment': overall_assessment,
                'average_effectiveness_score': float(avg_effectiveness),
                'average_confidence_score': float(avg_confidence),
                'metrics_with_significant_improvement': significant_metrics,
                'total_metrics_analyzed': total_metrics,
                'success_rate': significant_metrics / total_metrics if total_metrics > 0 else 0,
                'recommendation': self._generate_recommendation(overall_assessment, avg_confidence)
            }

        except Exception as e:
            logger.error(f"Overall summary generation failed: {str(e)}")
            return {'overall_assessment': 'analysis_failed', 'error': str(e)}

    def _generate_recommendation(self, assessment: str, confidence: float) -> str:
        """Generate recommendation based on assessment"""
        if assessment == 'highly_effective' and confidence >= 70:
            return "Continue intervention - strong evidence of effectiveness"
        elif assessment == 'moderately_effective' and confidence >= 60:
            return "Continue intervention with monitoring - moderate evidence of effectiveness"
        elif assessment == 'minimally_effective':
            return "Consider modifying intervention parameters or trying alternatives"
        elif confidence < 50:
            return "Continue intervention longer for more reliable assessment"
        else:
            return "Consider discontinuing intervention - limited evidence of effectiveness"

    def _analyze_confounding_factors(self, user_id: str, intervention_start: datetime,
                                   intervention_period: timedelta) -> Dict:
        """Analyze potential confounding factors during intervention period"""
        try:
            # Look for other interventions during the same period
            overlapping_interventions = Intervention.query.filter(
                and_(
                    Intervention.user_id == user_id,
                    Intervention.started_at <= intervention_start + intervention_period,
                    Intervention.ended_at >= intervention_start,
                    Intervention.started_at != intervention_start  # Exclude current intervention
                )
            ).all()

            confounding_analysis = {
                'overlapping_interventions': len(overlapping_interventions),
                'confounding_details': []
            }

            for intervention in overlapping_interventions:
                confounding_analysis['confounding_details'].append({
                    'intervention_name': intervention.name,
                    'category': intervention.category,
                    'overlap_start': max(intervention.started_at, intervention_start).isoformat(),
                    'overlap_end': min(intervention.ended_at or datetime.utcnow(),
                                     intervention_start + intervention_period).isoformat()
                })

            # Analyze lifestyle changes (simplified)
            # In a full implementation, this would analyze changes in:
            # - Sleep patterns
            # - Exercise routines
            # - Stress levels
            # - Travel/schedule disruptions

            confounding_analysis['assessment'] = (
                'high_confounding' if len(overlapping_interventions) > 1 else
                'moderate_confounding' if len(overlapping_interventions) == 1 else
                'low_confounding'
            )

            return confounding_analysis

        except Exception as e:
            logger.warning(f"Confounding factor analysis failed: {str(e)}")
            return {'error': str(e)}

    def _validate_intervention_data(self, intervention_data: Dict) -> Dict:
        """Validate intervention data before starting"""
        validation_result = {'is_valid': True, 'errors': [], 'warnings': []}

        # Required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in intervention_data or not intervention_data[field]:
                validation_result['errors'].append(f'Missing required field: {field}')
                validation_result['is_valid'] = False

        # Validate category
        if 'category' in intervention_data:
            category = intervention_data['category']
            if category not in self.intervention_categories:
                validation_result['warnings'].append(f'Unknown intervention category: {category}')

        # Validate target metrics
        if 'target_metrics' in intervention_data:
            target_metrics = intervention_data['target_metrics']
            if not isinstance(target_metrics, list):
                validation_result['errors'].append('target_metrics must be a list')
                validation_result['is_valid'] = False

        return validation_result

    def _check_intervention_overlap(self, user_id: str, intervention_data: Dict) -> Dict:
        """Check for overlapping interventions"""
        try:
            # Get active interventions
            active_interventions = Intervention.query.filter_by(
                user_id=user_id, is_active=True
            ).all()

            overlap_info = {
                'has_overlap': len(active_interventions) > 0,
                'overlapping_interventions': []
            }

            for intervention in active_interventions:
                overlap_info['overlapping_interventions'].append({
                    'id': intervention.id,
                    'name': intervention.name,
                    'category': intervention.category,
                    'started_at': intervention.started_at.isoformat(),
                    'target_metrics': intervention.target_metrics
                })

            return overlap_info

        except Exception as e:
            logger.warning(f"Overlap check failed: {str(e)}")
            return {'has_overlap': False, 'error': str(e)}

    def _establish_intervention_baseline(self, user_id: str, intervention: Intervention) -> Dict:
        """Establish baseline measurements before intervention"""
        try:
            # Get baseline period (2 weeks before intervention)
            baseline_end = intervention.started_at
            baseline_start = baseline_end - timedelta(days=14)

            target_metrics = intervention.target_metrics or ['hrv', 'sleep_score', 'recovery']

            baseline_data = {}
            for metric_type in target_metrics:
                metrics = Metric.query.filter(
                    and_(
                        Metric.user_id == user_id,
                        Metric.metric_type == metric_type,
                        Metric.timestamp >= baseline_start,
                        Metric.timestamp < baseline_end
                    )
                ).all()

                if metrics:
                    values = np.array([m.value for m in metrics])
                    values = values[~np.isnan(values)]  # Remove NaN

                    if len(values) >= 3:
                        baseline_data[metric_type] = {
                            'mean': float(np.mean(values)),
                            'std': float(np.std(values, ddof=1)),
                            'median': float(np.median(values)),
                            'sample_size': len(values),
                            'date_range': {
                                'start': baseline_start.isoformat(),
                                'end': baseline_end.isoformat()
                            }
                        }

            if not baseline_data:
                return {'error': 'No baseline data available for target metrics'}

            return {
                'success': True,
                'baseline_data': baseline_data,
                'baseline_period_days': 14
            }

        except Exception as e:
            logger.error(f"Baseline establishment failed: {str(e)}")
            return {'error': str(e)}

    def _get_expected_timeline(self, category: str) -> Dict:
        """Get expected timeline for intervention effects"""
        category_info = self.intervention_categories.get(category, {
            'typical_onset_days': 3,
            'full_effect_days': 14,
            'expected_metrics': ['hrv', 'sleep_score']
        })

        return {
            'expected_onset_days': category_info['typical_onset_days'],
            'expected_full_effect_days': category_info['full_effect_days'],
            'primary_metrics': category_info['expected_metrics'],
            'minimum_trial_period': max(category_info['full_effect_days'], 14)
        }

    def _log_intervention_event(self, user_id: str, intervention_id: int,
                              event_type: str, context: Dict):
        """Log intervention-related events"""
        try:
            log_entry = SystemLog(
                user_id=user_id,
                level='INFO',
                source='intervention_tracker',
                message=f"Intervention {intervention_id} {event_type}",
                context={
                    'intervention_id': intervention_id,
                    'event_type': event_type,
                    **context
                }
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to log intervention event: {str(e)}")

    def _generate_effectiveness_summary(self, effectiveness_result: Dict) -> str:
        """Generate human-readable effectiveness summary"""
        try:
            summary = effectiveness_result.get('summary', {})
            assessment = summary.get('overall_assessment', 'unknown')
            confidence = summary.get('average_confidence_score', 0)

            assessment_text = {
                'highly_effective': 'Highly Effective',
                'moderately_effective': 'Moderately Effective',
                'minimally_effective': 'Minimally Effective',
                'not_effective': 'Not Effective',
                'insufficient_data': 'Insufficient Data'
            }.get(assessment, 'Unknown')

            return f"{assessment_text} (Confidence: {confidence:.0f}%)"

        except Exception:
            return "Analysis summary unavailable"

    @cache_user_data(expire_seconds=1800)
    def get_user_intervention_history(self, user_id: str, limit: int = 10) -> Dict:
        """Get user's intervention history with effectiveness summaries"""
        try:
            interventions = Intervention.query.filter_by(user_id=user_id)\
                .order_by(Intervention.started_at.desc())\
                .limit(limit).all()

            intervention_history = []
            for intervention in interventions:
                intervention_data = {
                    'id': intervention.id,
                    'name': intervention.name,
                    'category': intervention.category,
                    'started_at': intervention.started_at.isoformat(),
                    'ended_at': intervention.ended_at.isoformat() if intervention.ended_at else None,
                    'is_active': intervention.is_active,
                    'duration_days': (intervention.ended_at - intervention.started_at).days if intervention.ended_at else None,
                    'effectiveness_scores': intervention.effectiveness_scores,
                    'confidence_scores': intervention.confidence_scores,
                    'target_metrics': intervention.target_metrics
                }

                intervention_history.append(intervention_data)

            return {
                'user_id': user_id,
                'total_interventions': len(intervention_history),
                'active_interventions': sum(1 for i in intervention_history if i['is_active']),
                'intervention_history': intervention_history
            }

        except Exception as e:
            logger.error(f"Failed to get intervention history for user {user_id}: {str(e)}")
            return {'error': str(e)}