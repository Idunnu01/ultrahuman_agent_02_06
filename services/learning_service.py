"""
Passive learning service that evolves system intelligence based on user patterns
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
import json
from collections import defaultdict, Counter

from app.models import User, Metric, DailyReport, Intervention, Pattern, MLModel
from utils.database import db, db_transaction
from utils.cache import cache_user_data
from services.statistical_analyzer import StatisticalAnalyzer
from analysis.pattern_mining import PatternMiner

logger = logging.getLogger(__name__)

class LearningService:
    """Passive learning system that improves personalization over time"""

    def __init__(self):
        self.analyzer = StatisticalAnalyzer()
        self.pattern_miner = PatternMiner()

        # Learning parameters
        self.min_learning_days = 7
        self.pattern_confidence_threshold = 0.7
        self.adaptation_rate = 0.1  # How quickly to adapt to new patterns

        # User profile evolution stages
        self.learning_stages = {
            'initialization': {'days': 7, 'focus': 'baseline_establishment'},
            'pattern_discovery': {'days': 21, 'focus': 'pattern_identification'},
            'personalization': {'days': 60, 'focus': 'custom_recommendations'},
            'optimization': {'days': 180, 'focus': 'fine_tuning'},
            'mastery': {'days': 365, 'focus': 'predictive_insights'}
        }

    def get_learning_status(self, user_id: str) -> Dict:
        """Get current learning status for a user"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}

            # Calculate days since onboarding
            days_active = (datetime.utcnow() - user.onboarded_at).days

            # Determine current learning stage
            current_stage = self._determine_learning_stage(days_active)

            # Get learning metrics
            learning_metrics = self._calculate_learning_metrics(user_id, days_active)

            # Get personalization score
            personalization_score = self._calculate_personalization_score(user_id)

            return {
                'user_id': user_id,
                'days_active': days_active,
                'current_stage': current_stage,
                'learning_metrics': learning_metrics,
                'personalization_score': personalization_score,
                'recommendations_evolution': self._analyze_recommendation_evolution(user_id),
                'next_milestone': self._get_next_milestone(current_stage, days_active)
            }

        except Exception as e:
            logger.error(f"Failed to get learning status for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get comprehensive user profile for personalized insights"""
        try:
            # Get from cache first
            cached_profile = self._get_cached_profile(user_id)
            if cached_profile:
                return cached_profile

            # Build profile from scratch
            profile = self._build_user_profile(user_id)

            # Cache the profile
            self._cache_user_profile(user_id, profile)

            return profile

        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {str(e)}")
            return None

    def record_report_generation(self, user_id: str, report_data: Dict, sms_result: Dict):
        """Record successful report generation for learning"""
        try:
            # Extract key information for learning
            learning_data = {
                'timestamp': datetime.utcnow(),
                'insights_count': len(report_data.get('insights', [])),
                'recommendations_count': len(report_data.get('recommendations', [])),
                'sms_delivered': sms_result.get('success', False),
                'confidence_score': report_data.get('confidence_scores', {}).get('overall', 0.5)
            }

            # Update user's learning metrics
            self._update_learning_metrics(user_id, 'report_generated', learning_data)

            # Analyze report effectiveness
            self._analyze_report_effectiveness(user_id, report_data)

        except Exception as e:
            logger.error(f"Failed to record report generation for user {user_id}: {str(e)}")

    def generate_personalized_recommendations(self, user_id: str, analysis_results: Dict,
                                            user_profile: Dict) -> List[Dict]:
        """Generate personalized recommendations based on user profile and current analysis"""
        try:
            recommendations = []

            # Get user's historical preferences
            preferences = user_profile.get('preferences', {})
            learning_stage = user_profile.get('learning_stage', 'initialization')

            # Get user's response patterns
            response_patterns = user_profile.get('response_patterns', {})

            # Generate recommendations based on learning stage
            if learning_stage == 'initialization':
                recommendations.extend(self._generate_baseline_recommendations(analysis_results))

            elif learning_stage == 'pattern_discovery':
                recommendations.extend(self._generate_pattern_based_recommendations(
                    analysis_results, user_profile
                ))

            elif learning_stage in ['personalization', 'optimization', 'mastery']:
                recommendations.extend(self._generate_advanced_recommendations(
                    analysis_results, user_profile, response_patterns
                ))

            # Filter and rank recommendations
            filtered_recommendations = self._filter_recommendations(
                recommendations, preferences, response_patterns
            )

            # Add personalization metadata
            for rec in filtered_recommendations:
                rec['personalization_level'] = learning_stage
                rec['user_specific'] = True
                rec['learning_confidence'] = user_profile.get('confidence_score', 0.5)

            return filtered_recommendations[:3]  # Top 3 personalized recommendations

        except Exception as e:
            logger.error(f"Failed to generate personalized recommendations: {str(e)}")
            return []

    def update_user_learning(self, user_id: str, interaction_data: Dict):
        """Update user learning based on interactions"""
        try:
            interaction_type = interaction_data.get('type')

            if interaction_type == 'sms_response':
                self._process_sms_interaction(user_id, interaction_data)
            elif interaction_type == 'intervention_started':
                self._process_intervention_interaction(user_id, interaction_data)
            elif interaction_type == 'recommendation_followed':
                self._process_recommendation_feedback(user_id, interaction_data)

            # Update user profile
            self._update_user_profile(user_id)

        except Exception as e:
            logger.error(f"Failed to update user learning: {str(e)}")

    def _determine_learning_stage(self, days_active: int) -> str:
        """Determine current learning stage based on days active"""
        for stage, config in self.learning_stages.items():
            if days_active <= config['days']:
                return stage
        return 'mastery'

    def _calculate_learning_metrics(self, user_id: str, days_active: int) -> Dict:
        """Calculate learning progress metrics"""
        try:
            metrics = {
                'data_richness': 0.0,
                'pattern_stability': 0.0,
                'intervention_responsiveness': 0.0,
                'engagement_consistency': 0.0
            }

            # Data richness - how much data we have
            total_metrics = Metric.query.filter_by(user_id=user_id).count()
            expected_metrics = days_active * 10  # Expect ~10 metrics per day
            metrics['data_richness'] = min(1.0, total_metrics / expected_metrics) if expected_metrics > 0 else 0

            # Pattern stability - how consistent patterns are
            patterns = Pattern.query.filter_by(user_id=user_id).all()
            if patterns:
                confidence_scores = [p.confidence_score for p in patterns if p.confidence_score]
                metrics['pattern_stability'] = np.mean(confidence_scores) if confidence_scores else 0.0

            # Intervention responsiveness - how well interventions work
            interventions = Intervention.query.filter_by(user_id=user_id).all()
            if interventions:
                effectiveness_scores = []
                for intervention in interventions:
                    if intervention.effectiveness_scores:
                        avg_effectiveness = np.mean(list(intervention.effectiveness_scores.values()))
                        effectiveness_scores.append(avg_effectiveness)

                metrics['intervention_responsiveness'] = np.mean(effectiveness_scores) if effectiveness_scores else 0.0

            # Engagement consistency - how regularly user provides data
            recent_reports = DailyReport.query.filter(
                DailyReport.user_id == user_id,
                DailyReport.generated_at >= datetime.utcnow() - timedelta(days=30)
            ).count()

            metrics['engagement_consistency'] = min(1.0, recent_reports / 30)

            return metrics

        except Exception as e:
            logger.error(f"Learning metrics calculation failed: {str(e)}")
            return {'error': str(e)}

    def _calculate_personalization_score(self, user_id: str) -> float:
        """Calculate overall personalization score"""
        try:
            learning_metrics = self._calculate_learning_metrics(user_id, 30)  # Last 30 days

            if 'error' in learning_metrics:
                return 0.5

            # Weight different factors
            weights = {
                'data_richness': 0.3,
                'pattern_stability': 0.3,
                'intervention_responsiveness': 0.2,
                'engagement_consistency': 0.2
            }

            weighted_score = sum(
                learning_metrics.get(metric, 0) * weight
                for metric, weight in weights.items()
            )

            return float(weighted_score)

        except Exception:
            return 0.5

    def _build_user_profile(self, user_id: str) -> Dict:
        """Build comprehensive user profile"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}

            days_active = (datetime.utcnow() - user.onboarded_at).days

            profile = {
                'user_id': user_id,
                'days_active': days_active,
                'learning_stage': self._determine_learning_stage(days_active),
                'preferences': user.preferences or {},
                'confidence_score': self._calculate_personalization_score(user_id),
                'metric_preferences': self._analyze_metric_preferences(user_id),
                'response_patterns': self._analyze_response_patterns(user_id),
                'intervention_history': self._summarize_intervention_history(user_id),
                'behavioral_patterns': self._extract_behavioral_patterns(user_id),
                'personal_baselines': self._get_personal_baselines(user_id),
                'last_updated': datetime.utcnow()
            }

            return profile

        except Exception as e:
            logger.error(f"User profile building failed: {str(e)}")
            return {}

    def _analyze_metric_preferences(self, user_id: str) -> Dict:
        """Analyze which metrics user cares about most"""
        try:
            # Analyze which metrics appear most in successful interventions
            interventions = Intervention.query.filter_by(user_id=user_id).all()

            metric_focus = Counter()
            metric_success = defaultdict(list)

            for intervention in interventions:
                target_metrics = intervention.target_metrics or []
                effectiveness_scores = intervention.effectiveness_scores or {}

                for metric in target_metrics:
                    metric_focus[metric] += 1

                    if metric in effectiveness_scores:
                        metric_success[metric].append(effectiveness_scores[metric])

            # Calculate preferences based on focus and success
            preferences = {}
            for metric, count in metric_focus.items():
                avg_success = np.mean(metric_success[metric]) if metric_success[metric] else 0.5
                preference_score = (count / max(metric_focus.values())) * avg_success
                preferences[metric] = float(preference_score)

            return preferences

        except Exception as e:
            logger.error(f"Metric preference analysis failed: {str(e)}")
            return {}

    def _analyze_response_patterns(self, user_id: str) -> Dict:
        """Analyze user's response patterns to different types of recommendations"""
        try:
            # This would analyze how user responds to different recommendation types
            # For now, return a placeholder structure

            response_patterns = {
                'recommendation_types': {
                    'behavioral_change': {'success_rate': 0.7, 'attempts': 5},
                    'supplement': {'success_rate': 0.8, 'attempts': 3},
                    'timing_optimization': {'success_rate': 0.6, 'attempts': 4},
                    'lifestyle_modification': {'success_rate': 0.5, 'attempts': 6}
                },
                'communication_preferences': {
                    'detail_level': 'moderate',  # brief, moderate, detailed
                    'motivation_style': 'positive',  # positive, challenge, neutral
                    'frequency_preference': 'daily'  # daily, weekly, as_needed
                },
                'intervention_preferences': {
                    'preferred_categories': ['supplement', 'sleep_hygiene'],
                    'avoided_categories': ['intense_exercise'],
                    'typical_duration_days': 14
                }
            }

            return response_patterns

        except Exception as e:
            logger.error(f"Response pattern analysis failed: {str(e)}")
            return {}

    def _summarize_intervention_history(self, user_id: str) -> Dict:
        """Summarize user's intervention history for learning"""
        try:
            interventions = Intervention.query.filter_by(user_id=user_id).all()

            history = {
                'total_interventions': len(interventions),
                'successful_interventions': 0,
                'avg_duration_days': 0,
                'most_effective_category': None,
                'intervention_timeline': []
            }

            if not interventions:
                return history

            durations = []
            category_effectiveness = defaultdict(list)

            for intervention in interventions:
                # Calculate duration
                if intervention.ended_at:
                    duration = (intervention.ended_at - intervention.started_at).days
                    durations.append(duration)

                # Track effectiveness by category
                if intervention.effectiveness_scores:
                    avg_effectiveness = np.mean(list(intervention.effectiveness_scores.values()))
                    category_effectiveness[intervention.category].append(avg_effectiveness)

                    if avg_effectiveness > 0.6:  # Consider 60%+ as successful
                        history['successful_interventions'] += 1

                # Add to timeline
                history['intervention_timeline'].append({
                    'name': intervention.name,
                    'category': intervention.category,
                    'started': intervention.started_at.isoformat(),
                    'ended': intervention.ended_at.isoformat() if intervention.ended_at else None,
                    'effectiveness': avg_effectiveness if intervention.effectiveness_scores else None
                })

            # Calculate averages
            if durations:
                history['avg_duration_days'] = int(np.mean(durations))

            # Find most effective category
            if category_effectiveness:
                category_avgs = {
                    cat: np.mean(scores) for cat, scores in category_effectiveness.items()
                }
                history['most_effective_category'] = max(category_avgs, key=category_avgs.get)

            return history

        except Exception as e:
            logger.error(f"Intervention history summarization failed: {str(e)}")
            return {}

    def _extract_behavioral_patterns(self, user_id: str) -> Dict:
        """Extract learned behavioral patterns"""
        try:
            # Get recent user data for pattern analysis
            user_data = self.analyzer._get_user_data(user_id, timedelta(days=60))

            if not user_data:
                return {}

            # Use pattern miner to discover patterns
            patterns = self.pattern_miner.discover_patterns(user_data, ['temporal', 'behavioral'])

            # Extract key behavioral insights
            behavioral_patterns = {
                'circadian_preferences': {},
                'weekly_patterns': {},
                'response_to_changes': {},
                'stability_metrics': {}
            }

            if 'patterns_discovered' in patterns:
                discovered = patterns['patterns_discovered']

                # Extract circadian preferences
                if 'temporal' in discovered:
                    temporal = discovered['temporal']
                    if 'circadian_patterns' in temporal:
                        for metric, pattern_data in temporal['circadian_patterns'].items():
                            behavioral_patterns['circadian_preferences'][metric] = {
                                'peak_hour': pattern_data.get('peak_hour'),
                                'trough_hour': pattern_data.get('trough_hour'),
                                'consistency': pattern_data.get('consistency_score', 0)
                            }

                # Extract weekly patterns
                if 'temporal' in discovered and 'weekly_patterns' in discovered['temporal']:
                    for metric, pattern_data in discovered['temporal']['weekly_patterns'].items():
                        behavioral_patterns['weekly_patterns'][metric] = pattern_data

            return behavioral_patterns

        except Exception as e:
            logger.error(f"Behavioral pattern extraction failed: {str(e)}")
            return {}

    def _get_personal_baselines(self, user_id: str) -> Dict:
        """Get user's personal baselines for all metrics"""
        try:
            baselines = {}

            baseline_records = db.session.query(
                self.analyzer.StatisticalBaseline
            ).filter_by(user_id=user_id).all()

            for baseline in baseline_records:
                baselines[baseline.metric_type] = {
                    'mean': baseline.mean,
                    'std': baseline.std,
                    'median': baseline.median,
                    'q1': baseline.q1,
                    'q3': baseline.q3,
                    'sample_size': baseline.sample_size,
                    'last_updated': baseline.last_updated.isoformat() if baseline.last_updated else None
                }

            return baselines

        except Exception as e:
            logger.error(f"Personal baselines retrieval failed: {str(e)}")
            return {}

    def _generate_baseline_recommendations(self, analysis_results: Dict) -> List[Dict]:
        """Generate basic recommendations for new users"""
        recommendations = [
            {
                'type': 'baseline_establishment',
                'category': 'general',
                'recommendation': 'Continue logging lifestyle events to establish personal patterns',
                'priority': 'high',
                'confidence': 0.8,
                'reasoning': 'Building personal baseline for future comparisons'
            },
            {
                'type': 'data_consistency',
                'category': 'general',
                'recommendation': 'Maintain consistent Ultrahuman Ring usage for accurate analysis',
                'priority': 'medium',
                'confidence': 0.9,
                'reasoning': 'Consistent data collection improves analysis quality'
            }
        ]

        return recommendations

    def _generate_pattern_based_recommendations(self, analysis_results: Dict,
                                              user_profile: Dict) -> List[Dict]:
        """Generate recommendations based on discovered patterns"""
        recommendations = []

        # Analyze discovered patterns
        behavioral_patterns = user_profile.get('behavioral_patterns', {})

        # Circadian optimization recommendations
        circadian_prefs = behavioral_patterns.get('circadian_preferences', {})
        for metric, prefs in circadian_prefs.items():
            if prefs.get('consistency', 0) > 0.7:  # High consistency
                peak_hour = prefs.get('peak_hour')
                if peak_hour:
                    recommendations.append({
                        'type': 'circadian_optimization',
                        'category': 'timing',
                        'recommendation': f'Schedule important activities around {peak_hour}:00 when your {metric} peaks',
                        'priority': 'medium',
                        'confidence': prefs['consistency'],
                        'reasoning': f'Your {metric} consistently peaks at {peak_hour}:00'
                    })

        return recommendations

    def _generate_advanced_recommendations(self, analysis_results: Dict,
                                         user_profile: Dict, response_patterns: Dict) -> List[Dict]:
        """Generate advanced personalized recommendations"""
        recommendations = []

        # Get user's most effective intervention categories
        intervention_history = user_profile.get('intervention_history', {})
        most_effective = intervention_history.get('most_effective_category')

        if most_effective:
            recommendations.append({
                'type': 'personalized_intervention',
                'category': most_effective,
                'recommendation': f'Consider another {most_effective} intervention based on your success history',
                'priority': 'high',
                'confidence': 0.85,
                'reasoning': f'{most_effective} interventions have been most effective for you'
            })

        # Personalized timing recommendations
        metric_preferences = user_profile.get('metric_preferences', {})
        if metric_preferences:
            top_metric = max(metric_preferences, key=metric_preferences.get)
            recommendations.append({
                'type': 'metric_focus',
                'category': 'optimization',
                'recommendation': f'Focus on optimizing {top_metric} - your most responsive metric',
                'priority': 'medium',
                'confidence': metric_preferences[top_metric],
                'reasoning': f'You show strongest response patterns for {top_metric}'
            })

        return recommendations

    def _filter_recommendations(self, recommendations: List[Dict],
                              preferences: Dict, response_patterns: Dict) -> List[Dict]:
        """Filter and rank recommendations based on user preferences"""
        try:
            # Score each recommendation
            scored_recommendations = []

            for rec in recommendations:
                score = rec.get('confidence', 0.5)

                # Boost score based on user preferences
                rec_category = rec.get('category', 'general')
                if rec_category in preferences:
                    score *= (1 + preferences[rec_category])

                # Adjust based on response patterns
                rec_type = rec.get('type', 'general')
                response_data = response_patterns.get('recommendation_types', {}).get(rec_type, {})
                success_rate = response_data.get('success_rate', 0.5)
                score *= success_rate

                rec['final_score'] = score
                scored_recommendations.append(rec)

            # Sort by score and return top recommendations
            scored_recommendations.sort(key=lambda x: x['final_score'], reverse=True)

            return scored_recommendations

        except Exception as e:
            logger.error(f"Recommendation filtering failed: {str(e)}")
            return recommendations

    def _analyze_recommendation_evolution(self, user_id: str) -> Dict:
        """Analyze how recommendations have evolved over time"""
        try:
            # Get historical daily reports
            reports = DailyReport.query.filter_by(user_id=user_id)\
                .order_by(DailyReport.report_date.desc())\
                .limit(30).all()

            if not reports:
                return {'evolution': 'no_data'}

            evolution = {
                'total_reports': len(reports),
                'recommendation_diversity': 0,
                'personalization_trend': 'stable',
                'confidence_trend': 'stable'
            }

            # Analyze recommendation types over time
            recommendation_types = []
            confidence_scores = []

            for report in reports:
                recommendations = report.recommendations or []
                for rec in recommendations:
                    if isinstance(rec, dict):
                        recommendation_types.append(rec.get('type', 'unknown'))
                        confidence_scores.append(rec.get('confidence', 0.5))

            # Calculate diversity
            unique_types = len(set(recommendation_types))
            evolution['recommendation_diversity'] = unique_types

            # Analyze confidence trend
            if len(confidence_scores) >= 10:
                recent_confidence = np.mean(confidence_scores[:len(confidence_scores)//2])
                older_confidence = np.mean(confidence_scores[len(confidence_scores)//2:])

                if recent_confidence > older_confidence + 0.1:
                    evolution['confidence_trend'] = 'improving'
                elif recent_confidence < older_confidence - 0.1:
                    evolution['confidence_trend'] = 'declining'

            return evolution

        except Exception as e:
            logger.error(f"Recommendation evolution analysis failed: {str(e)}")
            return {'evolution': 'analysis_failed'}

    def _get_next_milestone(self, current_stage: str, days_active: int) -> Dict:
        """Get next learning milestone for user"""
        try:
            stage_order = list(self.learning_stages.keys())
            current_index = stage_order.index(current_stage)

            if current_index < len(stage_order) - 1:
                next_stage = stage_order[current_index + 1]
                next_stage_config = self.learning_stages[next_stage]
                days_until_next = next_stage_config['days'] - days_active

                return {
                    'next_stage': next_stage,
                    'days_until_next': max(0, days_until_next),
                    'focus': next_stage_config['focus'],
                    'description': self._get_stage_description(next_stage)
                }
            else:
                return {
                    'next_stage': 'mastery_complete',
                    'days_until_next': 0,
                    'focus': 'continuous_optimization',
                    'description': 'You\'ve reached full system mastery!'
                }

        except Exception:
            return {'next_stage': 'unknown'}

    def _get_stage_description(self, stage: str) -> str:
        """Get description for learning stage"""
        descriptions = {
            'initialization': 'Building your personal health baseline',
            'pattern_discovery': 'Discovering your unique health patterns',
            'personalization': 'Customizing insights specifically for you',
            'optimization': 'Fine-tuning recommendations for maximum impact',
            'mastery': 'Providing predictive insights and advanced optimization'
        }

        return descriptions.get(stage, 'Learning about your health patterns')

    def _get_cached_profile(self, user_id: str) -> Optional[Dict]:
        """Get cached user profile"""
        try:
            from utils.cache import cache
            cached_data = cache.get(f"user_profile:{user_id}")

            if cached_data and isinstance(cached_data, dict):
                # Check if cache is fresh (less than 24 hours old)
                last_updated = cached_data.get('last_updated')
                if last_updated:
                    last_updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    if datetime.utcnow() - last_updated_dt < timedelta(hours=24):
                        return cached_data

            return None

        except Exception:
            return None

    def _cache_user_profile(self, user_id: str, profile: Dict):
        """Cache user profile"""
        try:
            from utils.cache import cache

            # Add timestamp
            profile['last_updated'] = datetime.utcnow().isoformat()

            # Cache for 24 hours
            cache.set(f"user_profile:{user_id}", profile, expire=86400)

        except Exception as e:
            logger.warning(f"Failed to cache user profile: {str(e)}")

    def _update_learning_metrics(self, user_id: str, event_type: str, event_data: Dict):
        """Update learning metrics based on events"""
        try:
            # This would update internal learning metrics
            # For now, just log the event
            logger.info(f"Learning event for user {user_id}: {event_type}")

        except Exception as e:
            logger.error(f"Learning metrics update failed: {str(e)}")

    def _analyze_report_effectiveness(self, user_id: str, report_data: Dict):
        """Analyze effectiveness of generated reports"""
        try:
            # Analyze which types of insights are most common
            insights = report_data.get('insights', [])
            recommendations = report_data.get('recommendations', [])

            # Track insight types
            insight_types = [insight.get('type') for insight in insights if isinstance(insight, dict)]

            # Track recommendation categories
            rec_categories = [rec.get('category') for rec in recommendations if isinstance(rec, dict)]

            # Store analysis for future personalization
            analysis = {
                'insight_types': insight_types,
                'recommendation_categories': rec_categories,
                'total_insights': len(insights),
                'total_recommendations': len(recommendations),
                'timestamp': datetime.utcnow().isoformat()
            }

            # This would be stored in a learning database
            logger.debug(f"Report effectiveness analysis: {analysis}")

        except Exception as e:
            logger.error(f"Report effectiveness analysis failed: {str(e)}")

    def _process_sms_interaction(self, user_id: str, interaction_data: Dict):
        """Process SMS interaction for learning"""
        try:
            sms_content = interaction_data.get('content', '')
            response_time = interaction_data.get('response_time_minutes', 0)

            # Analyze interaction patterns
            interaction_analysis = {
                'content_length': len(sms_content),
                'response_time_minutes': response_time,
                'interaction_type': self._classify_sms_content(sms_content),
                'timestamp': datetime.utcnow().isoformat()
            }

            # Update user engagement patterns
            self._update_engagement_patterns(user_id, interaction_analysis)

        except Exception as e:
            logger.error(f"SMS interaction processing failed: {str(e)}")

    def _process_intervention_interaction(self, user_id: str, interaction_data: Dict):
        """Process intervention interaction for learning"""
        try:
            intervention_type = interaction_data.get('intervention_type')
            user_initiated = interaction_data.get('user_initiated', False)

            # Learn about user's intervention preferences
            learning_data = {
                'intervention_type': intervention_type,
                'user_initiated': user_initiated,
                'timestamp': datetime.utcnow().isoformat()
            }

            self._update_intervention_preferences(user_id, learning_data)

        except Exception as e:
            logger.error(f"Intervention interaction processing failed: {str(e)}")

    def _process_recommendation_feedback(self, user_id: str, interaction_data: Dict):
        """Process recommendation feedback for learning"""
        try:
            recommendation_type = interaction_data.get('recommendation_type')
            followed = interaction_data.get('followed', False)
            effectiveness = interaction_data.get('effectiveness_score', 0.5)

            # Update recommendation effectiveness tracking
            feedback_data = {
                'recommendation_type': recommendation_type,
                'followed': followed,
                'effectiveness': effectiveness,
                'timestamp': datetime.utcnow().isoformat()
            }

            self._update_recommendation_effectiveness(user_id, feedback_data)

        except Exception as e:
            logger.error(f"Recommendation feedback processing failed: {str(e)}")

    def _update_user_profile(self, user_id: str):
        """Update user profile based on new learning"""
        try:
            # Rebuild and cache updated profile
            updated_profile = self._build_user_profile(user_id)
            self._cache_user_profile(user_id, updated_profile)

        except Exception as e:
            logger.error(f"User profile update failed: {str(e)}")

    def _classify_sms_content(self, content: str) -> str:
        """Classify SMS content type"""
        content_lower = content.lower()

        if any(word in content_lower for word in ['meal', 'ate', 'dinner', 'lunch']):
            return 'meal_logging'
        elif any(word in content_lower for word in ['supplement', 'vitamin', 'pill']):
            return 'supplement_logging'
        elif any(word in content_lower for word in ['workout', 'exercise', 'gym']):
            return 'activity_logging'
        elif any(word in content_lower for word in ['help', 'how', 'what']):
            return 'help_request'
        else:
            return 'general'

    def _update_engagement_patterns(self, user_id: str, interaction_analysis: Dict):
        """Update user engagement patterns"""
        try:
            # This would update engagement tracking in the database
            # For now, just log the pattern
            logger.debug(f"Engagement pattern update for {user_id}: {interaction_analysis}")

        except Exception as e:
            logger.error(f"Engagement pattern update failed: {str(e)}")

    def _update_intervention_preferences(self, user_id: str, learning_data: Dict):
        """Update intervention preferences"""
        try:
            # This would update intervention preference tracking
            logger.debug(f"Intervention preference update for {user_id}: {learning_data}")

        except Exception as e:
            logger.error(f"Intervention preference update failed: {str(e)}")

    def _update_recommendation_effectiveness(self, user_id: str, feedback_data: Dict):
        """Update recommendation effectiveness tracking"""
        try:
            # This would update recommendation effectiveness tracking
            logger.debug(f"Recommendation effectiveness update for {user_id}: {feedback_data}")

        except Exception as e:
            logger.error(f"Recommendation effectiveness update failed: {str(e)}")

def analyze_user_learning_trajectory(user_id: str, days: int = 90) -> Dict:
    """Analyze user's learning trajectory over time"""
    try:
        # Get historical reports to analyze learning progression
        reports = DailyReport.query.filter(
            DailyReport.user_id == user_id,
            DailyReport.generated_at >= datetime.utcnow() - timedelta(days=days)
        ).order_by(DailyReport.generated_at).all()

        if not reports:
            return {'error': 'No reports available for trajectory analysis'}

        trajectory = {
            'total_reports': len(reports),
            'confidence_progression': [],
            'insight_complexity_progression': [],
            'personalization_progression': [],
            'learning_velocity': 0.0
        }

        # Analyze progression over time
        for report in reports:
            confidence_scores = report.confidence_scores or {}
            overall_confidence = confidence_scores.get('overall', 0.5)
            trajectory['confidence_progression'].append(overall_confidence)

            # Count insights as a proxy for complexity
            insights = report.insights or []
            trajectory['insight_complexity_progression'].append(len(insights))

        # Calculate learning velocity (rate of improvement)
        if len(trajectory['confidence_progression']) > 1:
            confidence_values = trajectory['confidence_progression']
            x = np.arange(len(confidence_values))
            slope, _, _, _, _ = np.polyfit(x, confidence_values, 1, full=True)[:5]
            trajectory['learning_velocity'] = float(slope[0]) if len(slope) > 0 else 0.0

        return trajectory

    except Exception as e:
        logger.error(f"Learning trajectory analysis failed: {str(e)}")
        return {'error': str(e)}