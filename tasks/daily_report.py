"""
Daily report generation tasks - the core 4 AM intelligence delivery
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import logging

from app.models import User, DailyReport
from services.statistical_analyzer import StatisticalAnalyzer
from services.llm_service import LLMService
from services.sms_service import SMSService
from services.learning_service import LearningService
from utils.database import db

logger = logging.getLogger(__name__)

def generate_daily_report(user_id: str, report_date: str = None) -> Dict:
    """Generate daily health report for a specific user"""
    # Keep all the existing logic, just remove Celery decorators

def generate_daily_report(user_id: str, report_date: str = None) -> Dict:
    """Generate daily health report for a specific user"""

    try:
        # Parse report date
        if report_date:
            target_date = datetime.fromisoformat(report_date).date()
        else:
            target_date = datetime.utcnow().date()

        logger.info(f"Generating daily report for user {user_id}, date {target_date}")

        # Get user
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return {'error': f'User {user_id} not found or inactive'}

        # Check if report already exists
        existing_report = DailyReport.query.filter_by(
            user_id=user_id, report_date=target_date
        ).first()

        if existing_report and existing_report.sms_sent:
            logger.info(f"Report already exists and sent for user {user_id}, date {target_date}")
            return {'status': 'already_exists', 'report_id': existing_report.id}

        # Initialize services
        analyzer = StatisticalAnalyzer()
        llm_service = LLMService()
        sms_service = SMSService()
        learning_service = LearningService()

        # 1. Run comprehensive statistical analysis
        analysis_timeframe = timedelta(days=7)  # Analyze last 7 days
        analysis_results = analyzer.run_comprehensive_analysis(user_id, analysis_timeframe)

        if 'error' in analysis_results:
            logger.error(f"Statistical analysis failed for user {user_id}: {analysis_results['error']}")
            return {'error': f"Analysis failed: {analysis_results['error']}"}

        # 2. Extract key insights
        insights = _extract_key_insights(analysis_results)

        # 3. Generate personalized recommendations
        recommendations = _generate_recommendations(user_id, analysis_results, learning_service)

        # 4. Create daily summary
        daily_summary = _create_daily_summary(analysis_results, target_date)

        # 5. Generate LLM-powered insights
        llm_insights = llm_service.generate_health_insight(
            metrics_data=daily_summary,
            statistical_analysis=analysis_results,
            user_context=_get_user_context(user)
        )

        # 6. Create SMS report
        sms_content = llm_service.generate_daily_report(
            daily_summary=daily_summary,
            insights=insights,
            recommendations=recommendations
        )

        # 7. Store report in database
        report_data = {
            'insights': insights,
            'anomalies': analysis_results.get('anomaly_detection', {}),
            'correlations': analysis_results.get('correlation_analysis', {}),
            'trends': analysis_results.get('trend_analysis', {}),
            'predictions': _generate_predictions(user_id, analysis_results),
            'recommendations': recommendations
        }

        statistical_summary = {
            'confidence_score': analysis_results.get('confidence_assessments', {}).get('overall_confidence', 0.5),
            'data_quality': analysis_results.get('data_summary', {}).get('data_quality', {}),
            'analysis_methods': list(analysis_results.keys())
        }

        confidence_scores = {
            'overall': analysis_results.get('confidence_assessments', {}).get('overall_confidence', 0.5),
            'insights': _calculate_insight_confidence(insights),
            'recommendations': _calculate_recommendation_confidence(recommendations)
        }

        # Create or update report
        if existing_report:
            report = existing_report
        else:
            report = DailyReport(
                user_id=user_id,
                report_date=target_date
            )
            db.session.add(report)

        # Update report data
        report.insights = report_data['insights']
        report.anomalies = report_data['anomalies']
        report.correlations = report_data['correlations']
        report.trends = report_data['trends']
        report.predictions = report_data['predictions']
        report.recommendations = report_data['recommendations']
        report.statistical_summary = statistical_summary
        report.confidence_scores = confidence_scores
        report.sms_content = sms_content.content if hasattr(sms_content, 'content') else str(sms_content)
        report.generated_at = datetime.utcnow()

        db.session.commit()

        # 8. Send SMS report
        sms_result = sms_service.send_daily_report(
            user_id=user_id,
            phone_number=user.phone_number,
            report_content=report.sms_content
        )

        # Update SMS delivery status
        if sms_result['success']:
            report.sms_sent = True
            report.sms_sent_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"Daily report generated and sent successfully for user {user_id}")

            # Update learning system
            learning_service.record_report_generation(user_id, report_data, sms_result)

            return {
                'status': 'success',
                'report_id': report.id,
                'sms_sent': True,
                'sms_message_id': sms_result.get('message_id'),
                'insights_count': len(insights),
                'confidence_score': confidence_scores['overall']
            }
        else:
            logger.error(f"SMS delivery failed for user {user_id}: {sms_result['error']}")
            return {
                'status': 'partial_success',
                'report_id': report.id,
                'sms_sent': False,
                'sms_error': sms_result['error'],
                'insights_count': len(insights)
            }

    except Exception as e:
        logger.error(f"Daily report generation failed for user {user_id}: {str(e)}")

        # Log the error for debugging
        
        return {'error': str(e), 'user_id': user_id}

def generate_all_daily_reports(self) -> Dict:
    """Generate daily reports for all active users (4 AM task)"""

    try:
        logger.info("Starting daily report generation for all users")

        # Get all active users
        active_users = User.query.filter_by(is_active=True).all()

        if not active_users:
            logger.info("No active users found")
            return {'status': 'no_users', 'processed': 0}

        # Process each user
        results = {
            'total_users': len(active_users),
            'successful': 0,
            'failed': 0,
            'partial_success': 0,
            'errors': []
        }

        for user in active_users:
            try:
                # Generate report asynchronously for each user
                task_result = generate_daily_report.delay(user.id)

                # Wait for completion (with timeout)
                result = task_result.get(timeout=300)  # 5 minute timeout per user

                if result.get('status') == 'success':
                    results['successful'] += 1
                elif result.get('status') == 'partial_success':
                    results['partial_success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'user_id': user.id,
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                logger.error(f"Failed to generate report for user {user.id}: {str(e)}")
                results['failed'] += 1
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        # Log summary
        success_rate = results['successful'] / results['total_users'] if results['total_users'] > 0 else 0
        logger.info(f"Daily reports completed: {results['successful']}/{results['total_users']} successful ({success_rate:.1%})")

        return results

    except Exception as e:
        logger.error(f"Bulk daily report generation failed: {str(e)}")
        return {'error': str(e), 'status': 'failed'}

def _extract_key_insights(analysis_results: Dict) -> List[Dict]:
    """Extract key insights from statistical analysis"""
    try:
        insights = []

        # Extract anomaly insights
        anomaly_results = analysis_results.get('anomaly_detection', {})
        for metric_type, anomaly_data in anomaly_results.items():
            if isinstance(anomaly_data, dict) and 'detection_summary' in anomaly_data:
                summary = anomaly_data['detection_summary']
                if summary.get('anomalies_detected', 0) > 0:
                    insights.append({
                        'type': 'anomaly',
                        'metric': metric_type,
                        'message': f"Detected {summary['anomalies_detected']} anomalies in {metric_type}",
                        'severity': 'high' if summary.get('severe_anomalies', 0) > 0 else 'medium',
                        'confidence': summary.get('confidence_score', 0.5),
                        'details': anomaly_data.get('anomaly_details', [])
                    })

        # Extract correlation insights
        correlation_results = analysis_results.get('correlation_analysis', {})
        significant_correlations = correlation_results.get('significant_relationships', [])
        for correlation in significant_correlations[:3]:  # Top 3
            insights.append({
                'type': 'correlation',
                'metrics': correlation['metric_pair'],
                'message': f"{correlation['strength']} correlation found between {correlation['metric_pair']}",
                'severity': 'medium',
                'confidence': 1 - correlation.get('p_value', 0.5),
                'correlation_value': correlation['correlation']
            })

        # Extract trend insights
        trend_results = analysis_results.get('trend_analysis', {})
        for metric_type, trend_data in trend_results.items():
            if isinstance(trend_data, dict) and 'linear_trend' in trend_data:
                trend = trend_data['linear_trend']
                if trend.get('significant', False) and trend.get('strength', 0) > 0.3:
                    insights.append({
                        'type': 'trend',
                        'metric': metric_type,
                        'message': f"{metric_type} shows {trend['direction']} trend",
                        'severity': 'medium',
                        'confidence': 1 - trend.get('p_value', 0.5),
                        'direction': trend['direction'],
                        'strength': trend['strength']
                    })

        # Sort by confidence and return top insights
        insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return insights[:5]  # Top 5 insights

    except Exception as e:
        logger.error(f"Failed to extract insights: {str(e)}")
        return []

def _generate_recommendations(user_id: str, analysis_results: Dict, learning_service) -> List[Dict]:
    """Generate personalized recommendations based on analysis"""
    try:
        recommendations = []

        # Get user learning context
        user_profile = learning_service.get_user_profile(user_id)

        # Anomaly-based recommendations
        anomaly_results = analysis_results.get('anomaly_detection', {})
        for metric_type, anomaly_data in anomaly_results.items():
            if isinstance(anomaly_data, dict) and anomaly_data.get('detection_summary', {}).get('anomalies_detected', 0) > 0:
                recommendations.append({
                    'type': 'anomaly_response',
                    'metric': metric_type,
                    'recommendation': f"Monitor {metric_type} closely and consider lifestyle adjustments",
                    'priority': 'high',
                    'confidence': 0.8,
                    'category': 'monitoring'
                })

        # Trend-based recommendations
        trend_results = analysis_results.get('trend_analysis', {})
        for metric_type, trend_data in trend_results.items():
            if isinstance(trend_data, dict) and 'linear_trend' in trend_data:
                trend = trend_data['linear_trend']
                if trend.get('significant', False):
                    if trend['direction'] == 'declining':
                        recommendations.append({
                            'type': 'trend_improvement',
                            'metric': metric_type,
                            'recommendation': f"Focus on improving {metric_type} - consider targeted interventions",
                            'priority': 'medium',
                            'confidence': 1 - trend.get('p_value', 0.5),
                            'category': 'improvement'
                        })
                    elif trend['direction'] == 'improving':
                        recommendations.append({
                            'type': 'trend_maintenance',
                            'metric': metric_type,
                            'recommendation': f"Great progress on {metric_type} - maintain current habits",
                            'priority': 'low',
                            'confidence': 1 - trend.get('p_value', 0.5),
                            'category': 'maintenance'
                        })

        # Correlation-based recommendations
        correlation_results = analysis_results.get('correlation_analysis', {})
        significant_correlations = correlation_results.get('significant_relationships', [])
        for correlation in significant_correlations[:2]:  # Top 2
            recommendations.append({
                'type': 'correlation_leverage',
                'metrics': correlation['metric_pair'],
                'recommendation': f"Leverage the connection between {correlation['metric_pair']} for optimization",
                'priority': 'medium',
                'confidence': 1 - correlation.get('p_value', 0.5),
                'category': 'optimization'
            })

        # Personalized recommendations based on learning
        if user_profile:
            personalized_recs = learning_service.generate_personalized_recommendations(
                user_id, analysis_results, user_profile
            )
            recommendations.extend(personalized_recs)

        # Sort by priority and confidence
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        recommendations.sort(
            key=lambda x: (priority_order.get(x.get('priority', 'low'), 1), x.get('confidence', 0)),
            reverse=True
        )

        return recommendations[:3]  # Top 3 recommendations

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {str(e)}")
        return []

def _create_daily_summary(analysis_results: Dict, target_date: date) -> Dict:
    """Create summary of daily metrics and key statistics"""
    try:
        data_summary = analysis_results.get('data_summary', {})
        baseline_stats = analysis_results.get('baseline_statistics', {})

        summary = {
            'date': target_date.isoformat(),
            'metrics_analyzed': list(baseline_stats.keys()),
            'data_points_analyzed': data_summary.get('total_data_points', 0),
            'analysis_period_days': data_summary.get('overall_date_range', {}).get('total_duration_days', 0),
            'key_statistics': {}
        }

        # Add key statistics for each metric
        for metric_type, stats in baseline_stats.items():
            if isinstance(stats, dict) and 'mean' in stats:
                summary['key_statistics'][metric_type] = {
                    'current_baseline': stats['mean'],
                    'variability': stats.get('std', 0),
                    'trend': 'stable',  # Will be updated from trend analysis
                    'percentile_position': 50  # Default to median
                }

        # Update with trend information
        trend_results = analysis_results.get('trend_analysis', {})
        for metric_type, trend_data in trend_results.items():
            if metric_type in summary['key_statistics'] and isinstance(trend_data, dict):
                if 'linear_trend' in trend_data:
                    summary['key_statistics'][metric_type]['trend'] = trend_data['linear_trend'].get('direction', 'stable')

        return summary

    except Exception as e:
        logger.error(f"Failed to create daily summary: {str(e)}")
        return {'date': target_date.isoformat(), 'error': str(e)}

def _get_user_context(user: User) -> Dict:
    """Get user context for personalized analysis"""
    try:
        return {
            'user_id': user.id,
            'timezone': user.timezone,
            'onboarded_days': (datetime.utcnow() - user.onboarded_at).days,
            'preferences': user.preferences,
            'phone_number_region': user.phone_number[:3] if user.phone_number else None
        }
    except Exception as e:
        logger.error(f"Failed to get user context: {str(e)}")
        return {}

def _generate_predictions(user_id: str, analysis_results: Dict) -> Dict:
    """Generate predictions for next-day metrics"""
    try:
        predictions = {}

        # Simple trend-based predictions
        trend_results = analysis_results.get('trend_analysis', {})
        for metric_type, trend_data in trend_results.items():
            if isinstance(trend_data, dict) and 'linear_trend' in trend_data:
                trend = trend_data['linear_trend']

                # Predict next day value based on trend
                slope = trend.get('slope', 0)
                intercept = trend.get('intercept', 0)
                r_squared = trend.get('r_squared', 0)

                # Assume next day is day N+1
                days_elapsed = analysis_results.get('data_summary', {}).get('overall_date_range', {}).get('total_duration_days', 0)
                next_day_prediction = intercept + slope * (days_elapsed + 1)

                predictions[metric_type] = {
                    'predicted_value': float(next_day_prediction),
                    'confidence': float(r_squared),
                    'prediction_method': 'linear_trend',
                    'trend_direction': trend.get('direction', 'stable')
                }

        return predictions

    except Exception as e:
        logger.error(f"Failed to generate predictions: {str(e)}")
        return {}

def _calculate_insight_confidence(insights: List[Dict]) -> float:
    """Calculate overall confidence score for insights"""
    try:
        if not insights:
            return 0.0

        confidences = [insight.get('confidence', 0.5) for insight in insights]
        return float(np.mean(confidences))

    except Exception:
        return 0.5

def _calculate_recommendation_confidence(recommendations: List[Dict]) -> float:
    """Calculate overall confidence score for recommendations"""
    try:
        if not recommendations:
            return 0.0

        confidences = [rec.get('confidence', 0.5) for rec in recommendations]
        return float(np.mean(confidences))

    except Exception:
        return 0.5