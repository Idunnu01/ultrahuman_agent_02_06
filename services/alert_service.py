"""
Intelligent alert generation service for health anomalies and patterns
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging

from app.models import User, Alert, Metric, StatisticalBaseline
from utils.database import db
from services.sms_service import SMSService, create_anomaly_alert_message, create_correlation_insight_message
from services.statistical_analyzer import StatisticalAnalyzer
from analysis.anomaly_detection import AnomalyDetector
from utils.cache import RateLimiter

logger = logging.getLogger(__name__)

class AlertService:
    """Intelligent alert generation with priority-based notifications"""

    def __init__(self):
        self.sms_service = SMSService()
        self.analyzer = StatisticalAnalyzer()
        self.anomaly_detector = AnomalyDetector()

        # Alert thresholds
        self.alert_thresholds = {
            'critical': {'z_score': 4.0, 'anomaly_score': 0.9, 'confidence': 0.9},
            'high': {'z_score': 3.0, 'anomaly_score': 0.7, 'confidence': 0.8},
            'medium': {'z_score': 2.5, 'anomaly_score': 0.5, 'confidence': 0.7},
            'low': {'z_score': 2.0, 'anomaly_score': 0.3, 'confidence': 0.6}
        }

        # Alert rate limits (per user per time period)
        self.rate_limits = {
            'critical': {'limit': 3, 'window_hours': 24},
            'high': {'limit': 5, 'window_hours': 24},
            'medium': {'limit': 8, 'window_hours': 24},
            'low': {'limit': 10, 'window_hours': 24}
        }

    def check_real_time_alerts(self, user_id: str, processed_data: Dict) -> Dict:
        """Check for real-time alerts based on newly processed data"""
        try:
            logger.info(f"Checking real-time alerts for user {user_id}")

            alerts_generated = []

            # Get recent metrics for analysis
            recent_metrics = self.analyzer.get_recent_metrics(user_id, hours=2)

            if not recent_metrics:
                return {'alerts_generated': 0, 'message': 'No recent data for alert checking'}

            # Check each metric for anomalies
            for metric_type, metric_data in recent_metrics.items():
                try:
                    # Skip if insufficient data
                    if len(metric_data) < 2:
                        continue

                    # Get latest value
                    latest_metric = metric_data[0]  # Most recent
                    current_value = latest_metric['value']
                    timestamp = latest_metric['timestamp']

                    # Check for anomalies
                    anomaly_result = self._check_metric_anomaly(
                        user_id, metric_type, current_value, timestamp
                    )

                    if anomaly_result.get('is_anomaly', False):
                        alert_result = self._generate_anomaly_alert(
                            user_id, metric_type, anomaly_result
                        )

                        if alert_result.get('success'):
                            alerts_generated.append(alert_result)

                except Exception as e:
                    logger.warning(f"Alert check failed for metric {metric_type}: {str(e)}")
                    continue

            # Check for correlation alerts
            correlation_alerts = self._check_correlation_alerts(user_id, recent_metrics)
            alerts_generated.extend(correlation_alerts)

            return {
                'alerts_generated': len(alerts_generated),
                'alerts': alerts_generated,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Real-time alert checking failed for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def _check_metric_anomaly(self, user_id: str, metric_type: str,
                            current_value: float, timestamp: str) -> Dict:
        """Check if a metric value is anomalous"""
        try:
            # Get baseline statistics
            baseline = self.analyzer._get_baseline_statistics(user_id, metric_type)

            if not baseline:
                return {'is_anomaly': False, 'reason': 'No baseline available'}

            # Calculate z-score
            mean = baseline.get('mean', 0)
            std = baseline.get('std', 1)

            if std == 0:
                return {'is_anomaly': False, 'reason': 'Zero standard deviation'}

            z_score = abs(current_value - mean) / std

            # Determine severity
            severity = self._determine_anomaly_severity(z_score)

            if severity == 'none':
                return {'is_anomaly': False, 'z_score': z_score}

            # Additional context
            percentile_rank = self._calculate_percentile_rank(
                user_id, metric_type, current_value
            )

            return {
                'is_anomaly': True,
                'severity': severity,
                'z_score': z_score,
                'percentile_rank': percentile_rank,
                'current_value': current_value,
                'baseline_mean': mean,
                'baseline_std': std,
                'timestamp': timestamp,
                'metric_type': metric_type
            }

        except Exception as e:
            logger.error(f"Anomaly check failed: {str(e)}")
            return {'is_anomaly': False, 'error': str(e)}

    def _determine_anomaly_severity(self, z_score: float) -> str:
        """Determine severity based on z-score"""
        abs_z = abs(z_score)

        if abs_z >= self.alert_thresholds['critical']['z_score']:
            return 'critical'
        elif abs_z >= self.alert_thresholds['high']['z_score']:
            return 'high'
        elif abs_z >= self.alert_thresholds['medium']['z_score']:
            return 'medium'
        elif abs_z >= self.alert_thresholds['low']['z_score']:
            return 'low'
        else:
            return 'none'

    def _generate_anomaly_alert(self, user_id: str, metric_type: str,
                              anomaly_data: Dict) -> Dict:
        """Generate and send anomaly alert"""
        try:
            severity = anomaly_data['severity']

            # Check rate limits
            if not self._check_alert_rate_limit(user_id, severity):
                return {
                    'success': False,
                    'reason': 'Rate limit exceeded',
                    'severity': severity
                }

            # Create alert message
            alert_message = create_anomaly_alert_message(
                metric_name=metric_type,
                current_value=anomaly_data['current_value'],
                baseline_mean=anomaly_data['baseline_mean'],
                z_score=anomaly_data['z_score'],
                severity=severity
            )

            # Store alert in database
            alert = Alert(
                user_id=user_id,
                alert_type='anomaly',
                severity=severity,
                title=f'{metric_type.upper()} Anomaly Detected',
                message=alert_message,
                metrics_involved=[metric_type],
                statistical_summary={
                    'z_score': anomaly_data['z_score'],
                    'percentile_rank': anomaly_data.get('percentile_rank'),
                    'current_value': anomaly_data['current_value'],
                    'baseline_mean': anomaly_data['baseline_mean']
                },
                confidence_score=self._calculate_alert_confidence(anomaly_data)
            )

            db.session.add(alert)
            db.session.flush()

            # Send SMS for high priority alerts
            sms_sent = False
            if severity in ['critical', 'high']:
                user = User.query.get(user_id)
                if user:
                    sms_result = self.sms_service.send_alert(
                        user_id=user_id,
                        phone_number=user.phone_number,
                        alert_message=alert_message,
                        severity=severity
                    )

                    if sms_result['success']:
                        alert.sms_sent = True
                        alert.sms_sent_at = datetime.utcnow()
                        sms_sent = True

            db.session.commit()

            logger.info(f"Anomaly alert generated for user {user_id}: {metric_type} {severity}")

            return {
                'success': True,
                'alert_id': alert.id,
                'severity': severity,
                'sms_sent': sms_sent,
                'message': alert_message
            }

        except Exception as e:
            logger.error(f"Anomaly alert generation failed: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def _check_correlation_alerts(self, user_id: str, recent_metrics: Dict) -> List[Dict]:
        """Check for correlation-based alerts"""
        try:
            correlation_alerts = []

            # Get recent correlations from analysis
            correlation_results = self.analyzer._analyze_correlations_comprehensive(
                user_id, recent_metrics
            )

            significant_relationships = correlation_results.get('significant_relationships', [])

            for relationship in significant_relationships:
                # Check if this is a newly discovered correlation
                correlation_strength = abs(relationship.get('primary_correlation', {}).get('correlation', 0))

                if correlation_strength >= 0.7:  # Strong correlation threshold
                    alert_result = self._generate_correlation_alert(user_id, relationship)
                    if alert_result.get('success'):
                        correlation_alerts.append(alert_result)

            return correlation_alerts

        except Exception as e:
            logger.warning(f"Correlation alert checking failed: {str(e)}")
            return []

    def _generate_correlation_alert(self, user_id: str, relationship: Dict) -> Dict:
        """Generate correlation discovery alert"""
        try:
            # Check rate limits for medium priority
            if not self._check_alert_rate_limit(user_id, 'medium'):
                return {'success': False, 'reason': 'Rate limit exceeded'}

            correlation_data = relationship.get('primary_correlation', {})
            correlation_value = correlation_data.get('correlation', 0)
            confidence = 1 - correlation_data.get('p_value', 0.5)

            # Extract metric names
            metric_pair = relationship['metric_pair']
            metric1, metric2 = metric_pair.split('_vs_')

            # Create alert message
            alert_message = create_correlation_insight_message(
                metric1=metric1,
                metric2=metric2,
                correlation=correlation_value,
                confidence=confidence * 100
            )

            # Store alert
            alert = Alert(
                user_id=user_id,
                alert_type='correlation',
                severity='medium',
                title='New Correlation Discovered',
                message=alert_message,
                metrics_involved=[metric1, metric2],
                statistical_summary={
                    'correlation': correlation_value,
                    'p_value': correlation_data.get('p_value'),
                    'metric_pair': metric_pair
                },
                confidence_score=confidence
            )

            db.session.add(alert)
            db.session.commit()

            return {
                'success': True,
                'alert_id': alert.id,
                'type': 'correlation',
                'severity': 'medium',
                'message': alert_message
            }

        except Exception as e:
            logger.error(f"Correlation alert generation failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def create_urgent_alert(self, alert_data: Dict) -> Dict:
        """Create urgent alert for critical health events"""
        try:
            user_id = alert_data['user_id']

            # Generate urgent alert message
            metric_type = alert_data['metric_type']
            current_value = alert_data['current_value']
            z_score = alert_data.get('z_score', 0)

            alert_message = f"🆘 URGENT: {metric_type.upper()} at critical level: {current_value:.1f} ({z_score:.1f}σ deviation). Seek medical attention if symptoms present."

            # Create alert record
            alert = Alert(
                user_id=user_id,
                alert_type='urgent_anomaly',
                severity='critical',
                title=f'URGENT: Critical {metric_type.upper()} Alert',
                message=alert_message,
                metrics_involved=[metric_type],
                statistical_summary={
                    'z_score': z_score,
                    'current_value': current_value,
                    'anomaly_score': alert_data.get('anomaly_score', 0),
                    'baseline_context': alert_data.get('baseline_context', {})
                },
                confidence_score=alert_data.get('confidence', 0.9)
            )

            db.session.add(alert)
            db.session.flush()

            # Send immediate SMS
            user = User.query.get(user_id)
            sms_sent = False

            if user:
                sms_result = self.sms_service.send_alert(
                    user_id=user_id,
                    phone_number=user.phone_number,
                    alert_message=alert_message,
                    severity='critical'
                )

                if sms_result['success']:
                    alert.sms_sent = True
                    alert.sms_sent_at = datetime.utcnow()
                    sms_sent = True

            db.session.commit()

            logger.warning(f"URGENT alert created for user {user_id}: {metric_type}")

            return {
                'success': True,
                'alert_id': alert.id,
                'alert_sent': sms_sent,
                'severity': 'critical'
            }

        except Exception as e:
            logger.error(f"Urgent alert creation failed: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def process_anomaly_alerts(self, user_id: str, analysis_results: Dict) -> Dict:
        """Process anomaly detection results and generate appropriate alerts"""
        try:
            alerts_created = 0
            anomaly_results = analysis_results.get('anomaly_detection', {})

            for metric_type, anomaly_data in anomaly_results.items():
                if isinstance(anomaly_data, dict) and 'detection_summary' in anomaly_data:
                    detection_summary = anomaly_data['detection_summary']

                    if detection_summary.get('anomalies_detected', 0) > 0:
                        # Check for severe anomalies
                        severe_anomalies = detection_summary.get('severe_anomalies', 0)

                        if severe_anomalies > 0:
                            # Generate high priority alert
                            alert_result = self._create_severity_alert(
                                user_id, metric_type, anomaly_data, 'high'
                            )
                            if alert_result.get('success'):
                                alerts_created += 1
                        elif detection_summary.get('anomalies_detected', 0) >= 2:
                            # Multiple anomalies - medium priority
                            alert_result = self._create_severity_alert(
                                user_id, metric_type, anomaly_data, 'medium'
                            )
                            if alert_result.get('success'):
                                alerts_created += 1

            return {
                'alerts_created': alerts_created,
                'user_id': user_id
            }

        except Exception as e:
            logger.error(f"Anomaly alert processing failed: {str(e)}")
            return {'alerts_created': 0, 'error': str(e)}

    def _create_severity_alert(self, user_id: str, metric_type: str,
                             anomaly_data: Dict, severity: str) -> Dict:
        """Create alert with specified severity"""
        try:
            # Check rate limits
            if not self._check_alert_rate_limit(user_id, severity):
                return {'success': False, 'reason': 'Rate limit exceeded'}

            detection_summary = anomaly_data.get('detection_summary', {})
            anomalies_count = detection_summary.get('anomalies_detected', 0)

            # Create appropriate message
            if severity == 'high':
                title = f"High Priority: {metric_type.upper()} Anomalies"
                message = f"⚠️ Detected {anomalies_count} significant {metric_type} anomalies. Monitor closely and consider intervention."
            else:
                title = f"{metric_type.upper()} Pattern Alert"
                message = f"📊 Multiple {metric_type} anomalies detected ({anomalies_count}). Review recent lifestyle changes."

            # Store alert
            alert = Alert(
                user_id=user_id,
                alert_type='pattern_anomaly',
                severity=severity,
                title=title,
                message=message,
                metrics_involved=[metric_type],
                statistical_summary=detection_summary,
                confidence_score=detection_summary.get('confidence_score', 0.7)
            )

            db.session.add(alert)
            db.session.flush()

            # Send SMS for high priority
            sms_sent = False
            if severity == 'high':
                user = User.query.get(user_id)
                if user:
                    sms_result = self.sms_service.send_alert(
                        user_id=user_id,
                        phone_number=user.phone_number,
                        alert_message=message,
                        severity=severity
                    )

                    if sms_result['success']:
                        alert.sms_sent = True
                        alert.sms_sent_at = datetime.utcnow()
                        sms_sent = True

            db.session.commit()

            return {
                'success': True,
                'alert_id': alert.id,
                'sms_sent': sms_sent
            }

        except Exception as e:
            logger.error(f"Severity alert creation failed: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    def _check_alert_rate_limit(self, user_id: str, severity: str) -> bool:
        """Check if user is within rate limits for alert type"""
        try:
            limit_config = self.rate_limits.get(severity, {'limit': 5, 'window_hours': 24})

            rate_key = f"alert_rate:{user_id}:{severity}"
            window_seconds = limit_config['window_hours'] * 3600

            return RateLimiter.is_allowed(
                rate_key,
                limit_config['limit'],
                window_seconds
            )

        except Exception as e:
            logger.warning(f"Rate limit check failed: {str(e)}")
            return True  # Allow on error

    def _calculate_percentile_rank(self, user_id: str, metric_type: str, value: float) -> float:
        """Calculate percentile rank of value in user's historical data"""
        try:
            # Get recent historical data
            recent_data = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric_type,
                Metric.timestamp >= datetime.utcnow() - timedelta(days=30)
            ).all()

            if len(recent_data) < 10:
                return 50.0  # Default to median

            values = np.array([m.value for m in recent_data])
            values = values[~np.isnan(values)]

            if len(values) == 0:
                return 50.0

            from scipy.stats import percentileofscore
            percentile_rank = percentileofscore(values, value)

            return float(percentile_rank)

        except Exception as e:
            logger.warning(f"Percentile rank calculation failed: {str(e)}")
            return 50.0

    def _calculate_alert_confidence(self, anomaly_data: Dict) -> float:
        """Calculate confidence score for alert"""
        try:
            z_score = abs(anomaly_data.get('z_score', 0))

            # Higher z-score = higher confidence
            if z_score >= 4.0:
                return 0.95
            elif z_score >= 3.0:
                return 0.85
            elif z_score >= 2.5:
                return 0.75
            else:
                return 0.65

        except Exception:
            return 0.7

    def get_user_alerts(self, user_id: str, days: int = 7,
                       severity: Optional[str] = None,
                       unresolved_only: bool = False) -> Dict:
        """Get alerts for a user with filtering options"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)

            query = Alert.query.filter(
                Alert.user_id == user_id,
                Alert.created_at >= start_time
            )

            if severity:
                query = query.filter(Alert.severity == severity)

            if unresolved_only:
                query = query.filter(Alert.is_resolved == False)

            alerts = query.order_by(Alert.created_at.desc()).all()

            alert_summary = {
                'total_alerts': len(alerts),
                'by_severity': {},
                'by_type': {},
                'unresolved_count': 0,
                'alerts': []
            }

            for alert in alerts:
                # Count by severity
                severity_key = alert.severity
                alert_summary['by_severity'][severity_key] = alert_summary['by_severity'].get(severity_key, 0) + 1

                # Count by type
                type_key = alert.alert_type
                alert_summary['by_type'][type_key] = alert_summary['by_type'].get(type_key, 0) + 1

                # Count unresolved
                if not alert.is_resolved:
                    alert_summary['unresolved_count'] += 1

                # Add to list
                alert_summary['alerts'].append({
                    'id': alert.id,
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                    'message': alert.message,
                    'created_at': alert.created_at.isoformat(),
                    'is_resolved': alert.is_resolved,
                    'confidence_score': alert.confidence_score,
                    'metrics_involved': alert.metrics_involved
                })

            return alert_summary

        except Exception as e:
            logger.error(f"Failed to get alerts for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def resolve_alert(self, user_id: str, alert_id: int) -> Dict:
        """Mark an alert as resolved"""
        try:
            alert = Alert.query.filter_by(
                id=alert_id, user_id=user_id
            ).first()

            if not alert:
                return {'error': 'Alert not found'}

            if alert.is_resolved:
                return {'message': 'Alert already resolved'}

            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()

            db.session.commit()

            return {
                'success': True,
                'alert_id': alert_id,
                'resolved_at': alert.resolved_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {str(e)}")
            return {'error': str(e)}

    def get_alert_statistics(self, user_id: str, days: int = 30) -> Dict:
        """Get alert statistics for a user"""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)

            alerts = Alert.query.filter(
                Alert.user_id == user_id,
                Alert.created_at >= start_time
            ).all()

            stats = {
                'period_days': days,
                'total_alerts': len(alerts),
                'severity_breakdown': {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0
                },
                'type_breakdown': {},
                'resolution_stats': {
                    'resolved': 0,
                    'unresolved': 0,
                    'resolution_rate': 0.0
                },
                'alert_frequency': 0.0,
                'most_frequent_metric': None
            }

            metric_counts = {}

            for alert in alerts:
                # Severity breakdown
                stats['severity_breakdown'][alert.severity] += 1

                # Type breakdown
                alert_type = alert.alert_type
                stats['type_breakdown'][alert_type] = stats['type_breakdown'].get(alert_type, 0) + 1

                # Resolution stats
                if alert.is_resolved:
                    stats['resolution_stats']['resolved'] += 1
                else:
                    stats['resolution_stats']['unresolved'] += 1

                # Metric frequency
                for metric in alert.metrics_involved or []:
                    metric_counts[metric] = metric_counts.get(metric, 0) + 1

            # Calculate resolution rate
            if len(alerts) > 0:
                stats['resolution_stats']['resolution_rate'] = stats['resolution_stats']['resolved'] / len(alerts)

            # Calculate alert frequency (alerts per day)
            stats['alert_frequency'] = len(alerts) / days if days > 0 else 0

            # Most frequent metric
            if metric_counts:
                stats['most_frequent_metric'] = max(metric_counts, key=metric_counts.get)

            return stats

        except Exception as e:
            logger.error(f"Failed to get alert statistics for user {user_id}: {str(e)}")
            return {'error': str(e)}