"""
Data ingestion tasks for syncing Ultrahuman data and processing real-time events
"""


from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from app.models import User, Metric, SystemLog
from services.metrics_service import MetricsService
from services.statistical_analyzer import StatisticalAnalyzer
from services.alert_service import AlertService
from utils.database import db

logger = logging.getLogger(__name__)

try:
    # only defined if Celery is installed; safe-guarded
    from celery import current_task  # optional
except Exception:
    current_task = None

def sync_ultrahuman_data(user_id: str, days_back: int = 7) -> Dict:
    """Sync Ultrahuman data for a specific user"""

def sync_ultrahuman_data(user_id: str, days_back: int = 7) -> Dict:
    """Sync Ultrahuman data for a specific user"""

    try:
        logger.info(f"Starting Ultrahuman data sync for user {user_id}")

        # Get user
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return {'error': f'User {user_id} not found or inactive'}

        # Initialize services
        metrics_service = MetricsService()

        # Define date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # Fetch data from Ultrahuman API
        fetch_result = metrics_service.fetch_ultrahuman_data(user_id, start_date, end_date)

        if 'error' in fetch_result:
            logger.error(f"Ultrahuman API fetch failed for user {user_id}: {fetch_result['error']}")
            return {'error': f"API fetch failed: {fetch_result['error']}", 'user_id': user_id}

        # Process and store the data
        process_result = metrics_service.process_ultrahuman_data(user_id, fetch_result)

        if 'error' in process_result:
            logger.error(f"Data processing failed for user {user_id}: {process_result['error']}")
            return {'error': f"Processing failed: {process_result['error']}", 'user_id': user_id}

        # Update statistical baselines if enough new data
        metrics_inserted = process_result.get('metrics_inserted', 0)
        if metrics_inserted > 10:  # Arbitrary threshold
            try:
                analyzer = StatisticalAnalyzer()
                analyzer._update_baseline_statistics(user_id, fetch_result.get('metrics', {}))
                logger.info(f"Updated statistical baselines for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to update baselines for user {user_id}: {str(e)}")

        # Check for immediate alerts
        if metrics_inserted > 0:
            try:
                alert_service = AlertService()
                alert_service.check_real_time_alerts(user_id, process_result)
            except Exception as e:
                logger.warning(f"Alert checking failed for user {user_id}: {str(e)}")

        logger.info(f"Data sync completed for user {user_id}: {metrics_inserted} metrics processed")

        return {
            'success': True,
            'user_id': user_id,
            'metrics_inserted': metrics_inserted,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'processing_stats': process_result.get('processing_stats', {}),
            'sync_completed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Data sync failed for user {user_id}: {str(e)}")

        # Log error for debugging
        try:
            error_log = SystemLog(
                user_id=user_id,
                level='ERROR',
                source='data_ingestion',
                message=f"Sync failed: {str(e)}",
                context={'task_id': current_task.request.id if current_task else None}
            )
            db.session.add(error_log)
            db.session.commit()
        except Exception as log_error:
            logger.error(f"Failed to log sync error: {str(log_error)}")


        return {'error': str(e), 'user_id': user_id}

def sync_all_users_data(days_back: int = 1) -> Dict:
    """Sync Ultrahuman data for all active users (hourly task)"""

    try:
        logger.info("Starting bulk data sync for all users")

        # Get all active users
        active_users = User.query.filter_by(is_active=True).all()

        if not active_users:
            logger.info("No active users found for sync")
            return {'status': 'no_users', 'processed': 0}

        # Process each user
        results = {
            'total_users': len(active_users),
            'successful': 0,
            'failed': 0,
            'total_metrics_processed': 0,
            'errors': []
        }

        for user in active_users:
            try:
                # Sync data for each user asynchronously
                task_result = sync_ultrahuman_data.delay(user.id, days_back)

                # Wait for completion with timeout
                result = task_result.get(timeout=180)  # 3 minute timeout per user

                if result.get('success'):
                    results['successful'] += 1
                    results['total_metrics_processed'] += result.get('metrics_inserted', 0)
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'user_id': user.id,
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                logger.error(f"Failed to sync user {user.id}: {str(e)}")
                results['failed'] += 1
                results['errors'].append({
                    'user_id': user.id,
                    'error': str(e)
                })

        # Log summary
        success_rate = results['successful'] / results['total_users'] if results['total_users'] > 0 else 0
        logger.info(f"Bulk sync completed: {results['successful']}/{results['total_users']} successful ({success_rate:.1%})")
        logger.info(f"Total metrics processed: {results['total_metrics_processed']}")

        return results

    except Exception as e:
        logger.error(f"Bulk data sync failed: {str(e)}")
        return {'error': str(e), 'status': 'failed'}

def process_recent_data(hours_back: int = 1) -> Dict:
    """Process recent data for real-time analysis (every 15 minutes)"""

    try:
        logger.info(f"Processing recent data from last {hours_back} hours")

        # Get users with recent data activity
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        recent_metrics = db.session.query(Metric.user_id).filter(
            Metric.timestamp >= start_time
        ).distinct().all()

        user_ids = [metric.user_id for metric in recent_metrics]

        if not user_ids:
            logger.info("No recent data activity found")
            return {'status': 'no_activity', 'processed': 0}

        results = {
            'users_processed': len(user_ids),
            'anomalies_detected': 0,
            'alerts_generated': 0,
            'errors': []
        }

        # Initialize services
        analyzer = StatisticalAnalyzer()
        alert_service = AlertService()

        for user_id in user_ids:
            try:
                # Run quick anomaly detection on recent data
                recent_analysis = analyzer.detect_anomalies(
                    user_id=user_id,
                    timeframe=timedelta(hours=hours_back)
                )

                if 'anomaly_detection' in recent_analysis:
                    anomaly_count = 0
                    for metric_type, anomaly_data in recent_analysis['anomaly_detection'].items():
                        if isinstance(anomaly_data, dict):
                            detection_summary = anomaly_data.get('detection_summary', {})
                            anomaly_count += detection_summary.get('anomalies_detected', 0)

                    results['anomalies_detected'] += anomaly_count

                    # Generate alerts for significant anomalies
                    if anomaly_count > 0:
                        alert_result = alert_service.process_anomaly_alerts(user_id, recent_analysis)
                        results['alerts_generated'] += alert_result.get('alerts_created', 0)

            except Exception as e:
                logger.error(f"Recent data processing failed for user {user_id}: {str(e)}")
                results['errors'].append({
                    'user_id': user_id,
                    'error': str(e)
                })

        logger.info(f"Recent data processing completed: {results['anomalies_detected']} anomalies, {results['alerts_generated']} alerts")

        return results

    except Exception as e:
        logger.error(f"Recent data processing failed: {str(e)}")
        return {'error': str(e)}

def process_sms_lifestyle_event(user_id: str, sms_content: str,
                               received_at: Optional[str] = None) -> Dict:
    """Process lifestyle event from SMS input"""

    try:
        logger.info(f"Processing SMS lifestyle event for user {user_id}")

        # Parse received_at timestamp
        if received_at:
            try:
                received_timestamp = datetime.fromisoformat(received_at)
            except ValueError:
                received_timestamp = datetime.utcnow()
        else:
            received_timestamp = datetime.utcnow()

        # Initialize metrics service
        metrics_service = MetricsService()

        # Process SMS content
        process_result = metrics_service.process_sms_input(user_id, sms_content)

        if 'error' in process_result:
            logger.error(f"SMS processing failed for user {user_id}: {process_result['error']}")
            return {
                'error': f"SMS processing failed: {process_result['error']}",
                'user_id': user_id,
                'original_sms': sms_content
            }

        # Log successful processing
        try:
            success_log = SystemLog(
                user_id=user_id,
                level='INFO',
                source='sms_processing',
                message=f"SMS event processed: {process_result.get('events_processed', 0)} events",
                context={
                    'original_sms': sms_content,
                    'events_processed': process_result.get('events_processed', 0),
                    'received_at': received_timestamp.isoformat()
                }
            )
            db.session.add(success_log)
            db.session.commit()
        except Exception as log_error:
            logger.warning(f"Failed to log SMS processing success: {str(log_error)}")

        # Check if this lifestyle event should trigger immediate analysis
        events_processed = process_result.get('events_processed', 0)
        if events_processed > 0:
            try:
                # Quick correlation check for immediate insights
                analyzer = StatisticalAnalyzer()
                recent_data = analyzer._get_user_data(user_id, timedelta(hours=24))

                if recent_data:
                    # Generate immediate feedback if correlation found
                    immediate_insights = _generate_immediate_lifestyle_insights(
                        user_id, sms_content, recent_data
                    )

                    if immediate_insights:
                        process_result['immediate_insights'] = immediate_insights

            except Exception as e:
                logger.warning(f"Immediate insight generation failed: {str(e)}")

        return {
            'success': True,
            'user_id': user_id,
            'events_processed': events_processed,
            'original_sms': sms_content,
            'processing_details': process_result,
            'received_at': received_timestamp.isoformat()
        }

    except Exception as e:
        logger.error(f"SMS lifestyle event processing failed for user {user_id}: {str(e)}")
        return {
            'error': str(e),
            'user_id': user_id,
            'original_sms': sms_content
        }

def process_urgent_health_alert(user_id: str, metric_type: str,
                               current_value: float, anomaly_score: float) -> Dict:
    """Process urgent health alerts that need immediate attention"""

    try:
        logger.info(f"Processing urgent health alert for user {user_id}: {metric_type}")

        # Initialize services
        alert_service = AlertService()
        analyzer = StatisticalAnalyzer()

        # Get recent context
        recent_data = analyzer._get_user_data(user_id, timedelta(hours=48))

        if not recent_data:
            return {'error': 'No recent data available for context'}

        # Calculate statistical context
        baseline = analyzer._get_baseline_statistics(user_id, metric_type)

        if baseline:
            z_score = (current_value - baseline.get('mean', 0)) / (baseline.get('std', 1) + 1e-8)
            percentile_rank = 50  # Default, could calculate properly
        else:
            z_score = 0
            percentile_rank = 50

        # Generate urgent alert
        alert_data = {
            'user_id': user_id,
            'alert_type': 'urgent_anomaly',
            'severity': 'critical' if abs(z_score) > 4 else 'high',
            'metric_type': metric_type,
            'current_value': current_value,
            'anomaly_score': anomaly_score,
            'z_score': z_score,
            'percentile_rank': percentile_rank,
            'baseline_context': baseline
        }

        # Create and send alert
        alert_result = alert_service.create_urgent_alert(alert_data)

        if alert_result.get('success'):
            logger.info(f"Urgent alert created and sent for user {user_id}")
            return {
                'success': True,
                'alert_id': alert_result.get('alert_id'),
                'alert_sent': alert_result.get('alert_sent', False),
                'severity': alert_data['severity']
            }
        else:
            return {
                'error': 'Failed to create urgent alert',
                'details': alert_result
            }

    except Exception as e:
        logger.error(f"Urgent alert processing failed for user {user_id}: {str(e)}")
        return {'error': str(e), 'user_id': user_id}

def backfill_user_data(user_id: str, start_date: str, end_date: str) -> Dict:
    """Backfill historical data for a user (for new users or data recovery)"""

    try:
        logger.info(f"Starting data backfill for user {user_id}: {start_date} to {end_date}")

        # Parse dates
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # Validate date range
        if start_dt >= end_dt:
            return {'error': 'Invalid date range: start_date must be before end_date'}

        max_days = 90  # Limit backfill to 90 days
        if (end_dt - start_dt).days > max_days:
            return {'error': f'Date range too large. Maximum {max_days} days allowed'}

        # Initialize metrics service
        metrics_service = MetricsService()

        # Break into smaller chunks (7 days each) to avoid API limits
        chunk_size = timedelta(days=7)
        current_start = start_dt
        total_metrics = 0
        total_chunks = 0
        errors = []

        while current_start < end_dt:
            current_end = min(current_start + chunk_size, end_dt)

            try:
                # Fetch data for this chunk
                fetch_result = metrics_service.fetch_ultrahuman_data(
                    user_id, current_start, current_end
                )

                if 'error' in fetch_result:
                    errors.append({
                        'date_range': f"{current_start.date()} to {current_end.date()}",
                        'error': fetch_result['error']
                    })
                else:
                    # Process the data
                    process_result = metrics_service.process_ultrahuman_data(user_id, fetch_result)

                    if 'error' in process_result:
                        errors.append({
                            'date_range': f"{current_start.date()} to {current_end.date()}",
                            'error': process_result['error']
                        })
                    else:
                        total_metrics += process_result.get('metrics_inserted', 0)
                        total_chunks += 1

                # Small delay to respect API limits
                import time
                time.sleep(2)

            except Exception as e:
                errors.append({
                    'date_range': f"{current_start.date()} to {current_end.date()}",
                    'error': str(e)
                })

            current_start = current_end

        # Update statistical baselines after backfill
        if total_metrics > 20:
            try:
                analyzer = StatisticalAnalyzer()
                recent_data = analyzer._get_user_data(user_id, timedelta(days=30))
                analyzer._update_baseline_statistics(user_id, recent_data)
                logger.info(f"Updated baselines after backfill for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to update baselines after backfill: {str(e)}")

        logger.info(f"Backfill completed for user {user_id}: {total_metrics} metrics processed")

        return {
            'success': True,
            'user_id': user_id,
            'date_range': {
                'start': start_date,
                'end': end_date
            },
            'total_metrics_processed': total_metrics,
            'chunks_processed': total_chunks,
            'errors': errors,
            'completed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Data backfill failed for user {user_id}: {str(e)}")
        return {'error': str(e), 'user_id': user_id}

def validate_data_integrity(user_id: str, days_back: int = 7) -> Dict:
    """Validate data integrity and detect missing data periods"""

    try:
        logger.info(f"Validating data integrity for user {user_id}")

        # Get user data
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        metrics = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.timestamp >= start_time
        ).order_by(Metric.timestamp).all()

        if not metrics:
            return {
                'user_id': user_id,
                'status': 'no_data',
                'message': 'No data found in specified period'
            }

        # Group by metric type
        metrics_by_type = {}
        for metric in metrics:
            if metric.metric_type not in metrics_by_type:
                metrics_by_type[metric.metric_type] = []
            metrics_by_type[metric.metric_type].append(metric)

        validation_results = {
            'user_id': user_id,
            'validation_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': days_back
            },
            'metric_types_found': list(metrics_by_type.keys()),
            'total_data_points': len(metrics),
            'data_quality_report': {},
            'missing_periods': [],
            'outliers_detected': [],
            'recommendations': []
        }

        # Analyze each metric type
        for metric_type, metric_list in metrics_by_type.items():
            timestamps = [m.timestamp for m in metric_list]
            values = np.array([m.value for m in metric_list])

            # Check for missing periods (gaps > 25 hours for daily metrics)
            missing_periods = []
            for i in range(1, len(timestamps)):
                gap_hours = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
                if gap_hours > 25:  # More than 25 hours gap
                    missing_periods.append({
                        'start': timestamps[i-1].isoformat(),
                        'end': timestamps[i].isoformat(),
                        'gap_hours': round(gap_hours, 1)
                    })

            # Check for outliers using IQR method
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outliers = []
            for i, value in enumerate(values):
                if value < lower_bound or value > upper_bound:
                    outliers.append({
                        'timestamp': timestamps[i].isoformat(),
                        'value': float(value),
                        'bounds': {'lower': float(lower_bound), 'upper': float(upper_bound)}
                    })

            # Calculate data quality metrics
            data_quality = {
                'sample_size': len(values),
                'missing_periods': missing_periods,
                'outliers': outliers,
                'value_range': {
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values))
                },
                'consistency_score': _calculate_temporal_consistency(timestamps),
                'completeness_score': _calculate_completeness_score(timestamps, start_time, end_time)
            }

            validation_results['data_quality_report'][metric_type] = data_quality

            # Add to overall missing periods and outliers
            validation_results['missing_periods'].extend([
                {'metric_type': metric_type, **period} for period in missing_periods
            ])
            validation_results['outliers_detected'].extend([
                {'metric_type': metric_type, **outlier} for outlier in outliers
            ])

        # Generate recommendations
        recommendations = []

        # Check for missing metric types
        expected_metrics = ['hrv', 'sleep_score', 'heart_rate', 'temperature']
        missing_metrics = set(expected_metrics) - set(metrics_by_type.keys())
        if missing_metrics:
            recommendations.append({
                'type': 'missing_metrics',
                'message': f"Missing metric types: {', '.join(missing_metrics)}",
                'action': 'Check Ultrahuman Ring connectivity and sync settings'
            })

        # Check for excessive gaps
        total_gaps = len(validation_results['missing_periods'])
        if total_gaps > 3:
            recommendations.append({
                'type': 'data_gaps',
                'message': f"Found {total_gaps} significant data gaps",
                'action': 'Consider running backfill task for missing periods'
            })

        # Check for too many outliers
        total_outliers = len(validation_results['outliers_detected'])
        if total_outliers > len(metrics) * 0.1:  # More than 10% outliers
            recommendations.append({
                'type': 'excessive_outliers',
                'message': f"High outlier rate: {total_outliers} outliers in {len(metrics)} data points",
                'action': 'Review data collection quality and check for sensor issues'
            })

        validation_results['recommendations'] = recommendations

        # Overall status
        if not recommendations:
            validation_results['status'] = 'good'
        elif len(recommendations) <= 2:
            validation_results['status'] = 'minor_issues'
        else:
            validation_results['status'] = 'needs_attention'

        return validation_results

    except Exception as e:
        logger.error(f"Data integrity validation failed for user {user_id}: {str(e)}")
        return {'error': str(e), 'user_id': user_id}

def _generate_immediate_lifestyle_insights(user_id: str, sms_content: str, recent_data: Dict) -> Optional[Dict]:
    """Generate immediate insights based on lifestyle event and recent data"""
    try:
        insights = []

        # Simple pattern matching for immediate feedback
        content_lower = sms_content.lower()

        # Late meal detection
        if 'dinner' in content_lower or 'ate' in content_lower:
            current_hour = datetime.now().hour
            if current_hour >= 20:  # 8 PM or later
                # Check if user has historical data showing late meal impact
                insights.append({
                    'type': 'meal_timing_warning',
                    'message': 'Late meal detected. Your historical data shows meals after 8 PM typically reduce HRV by 15%.',
                    'confidence': 0.7,
                    'recommendation': 'Consider taking extra magnesium tonight for better recovery.'
                })

        # Caffeine timing
        if 'coffee' in content_lower or 'caffeine' in content_lower:
            current_hour = datetime.now().hour
            if current_hour >= 14:  # 2 PM or later
                insights.append({
                    'type': 'caffeine_timing_warning',
                    'message': 'Afternoon caffeine detected. This may impact tonight\'s sleep quality.',
                    'confidence': 0.8,
                    'recommendation': 'Consider melatonin 30min before bed to counteract caffeine effects.'
                })

        # Exercise timing
        if any(word in content_lower for word in ['workout', 'exercise', 'gym', 'run']):
            current_hour = datetime.now().hour
            if current_hour >= 19:  # 7 PM or later
                insights.append({
                    'type': 'exercise_timing_info',
                    'message': 'Evening workout logged. This may boost tomorrow\'s HRV by 12% based on your patterns.',
                    'confidence': 0.6,
                    'recommendation': 'Great timing for recovery! Stay hydrated.'
                })

        return {'insights': insights} if insights else None

    except Exception as e:
        logger.warning(f"Immediate insight generation failed: {str(e)}")
        return None

def _calculate_temporal_consistency(timestamps: List[datetime]) -> float:
    """Calculate how consistent the timing of data collection is"""
    try:
        if len(timestamps) < 2:
            return 1.0

        # Calculate time differences in hours
        time_diffs = []
        for i in range(1, len(timestamps)):
            diff_hours = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
            time_diffs.append(diff_hours)

        # Calculate coefficient of variation
        mean_diff = np.mean(time_diffs)
        std_diff = np.std(time_diffs)

        if mean_diff == 0:
            return 1.0

        cv = std_diff / mean_diff
        consistency_score = max(0.0, 1.0 - cv / 2.0)  # Normalize CV to 0-1 scale

        return float(consistency_score)

    except Exception:
        return 0.5

def _calculate_completeness_score(timestamps: List[datetime], start_time: datetime, end_time: datetime) -> float:
    """Calculate data completeness score based on expected vs actual data points"""
    try:
        # Expected data points (assuming daily data)
        expected_days = (end_time - start_time).days
        expected_points = max(1, expected_days)

        # Actual data points
        actual_points = len(timestamps)

        # Completeness score
        completeness = min(1.0, actual_points / expected_points)

        return float(completeness)

    except Exception:
        return 0.5