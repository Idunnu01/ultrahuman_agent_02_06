"""
System maintenance tasks for database cleanup, model retraining, and optimization
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import os
import pickle
from sqlalchemy import and_, func

from app.models import (User, Metric, Alert, DailyReport, SystemLog,
                       StatisticalBaseline, Correlation, Pattern, MLModel)
from utils.database import db, cleanup_old_data, get_table_stats, optimize_database
from utils.cache import cleanup_expired_cache, warm_user_cache
from services.statistical_analyzer import StatisticalAnalyzer
from services.pattern_recognition import PatternRecognizer

logger = logging.getLogger(__name__)

def daily_cleanup(retention_days: int = 90) -> Dict:
    """Daily maintenance: cleanup old data, optimize database, update statistics"""
    try:
        logger.info("Starting daily cleanup and maintenance")

        maintenance_results = {
            'cleanup_timestamp': datetime.utcnow().isoformat(),
            'data_cleanup': {},
            'database_optimization': {},
            'cache_cleanup': {},
            'statistics_update': {},
            'errors': []
        }

        # 1. Clean up old data
        try:
            deleted_count = cleanup_old_data(retention_days)
            maintenance_results['data_cleanup'] = {
                'retention_days': retention_days,
                'records_deleted': deleted_count,
                'status': 'completed'
            }
            logger.info(f"Data cleanup completed: {deleted_count} old records removed")
        except Exception as e:
            error_msg = f"Data cleanup failed: {str(e)}"
            logger.error(error_msg)
            maintenance_results['errors'].append(error_msg)

        # 2. Optimize database
        try:
            optimize_database()
            maintenance_results['database_optimization'] = {
                'vacuum_analyze': 'completed',
                'index_rebuild': 'completed',
                'status': 'completed'
            }
            logger.info("Database optimization completed")
        except Exception as e:
            error_msg = f"Database optimization failed: {str(e)}"
            logger.error(error_msg)
            maintenance_results['errors'].append(error_msg)

        # 3. Clean up expired cache entries
        try:
            expired_count = cleanup_expired_cache()
            maintenance_results['cache_cleanup'] = {
                'expired_entries_removed': expired_count,
                'status': 'completed'
            }
            logger.info(f"Cache cleanup completed: {expired_count} expired entries removed")
        except Exception as e:
            error_msg = f"Cache cleanup failed: {str(e)}"
            logger.error(error_msg)
            maintenance_results['errors'].append(error_msg)

        # 4. Update system statistics
        try:
            stats_result = update_system_statistics()
            maintenance_results['statistics_update'] = stats_result
            logger.info("System statistics updated")
        except Exception as e:
            error_msg = f"Statistics update failed: {str(e)}"
            logger.error(error_msg)
            maintenance_results['errors'].append(error_msg)

        # 5. Log maintenance completion
        log_maintenance_event('daily_cleanup', maintenance_results)

        logger.info("Daily cleanup and maintenance completed")
        return maintenance_results

    except Exception as e:
        logger.error(f"Daily cleanup failed: {str(e)}")
        return {'error': str(e), 'timestamp': datetime.utcnow().isoformat()}

def update_statistical_baselines() -> Dict:
    """Update statistical baselines for all active users"""
    try:
        logger.info("Starting statistical baseline updates")

        # Get all active users
        active_users = User.query.filter_by(is_active=True).all()

        if not active_users:
            return {'message': 'No active users found', 'updated': 0}

        results = {
            'total_users': len(active_users),
            'successful_updates': 0,
            'failed_updates': 0,
            'baselines_updated': 0,
            'errors': []
        }

        analyzer = StatisticalAnalyzer()

        for user in active_users:
            try:
                # Get recent data (last 30 days)
                user_data = analyzer._get_user_data(user.id, timedelta(days=30))

                if not user_data:
                    continue

                # Update baselines for each metric type
                baseline_result = analyzer._update_baseline_statistics(user.id, user_data)

                if 'error' not in baseline_result:
                    results['successful_updates'] += 1
                    results['baselines_updated'] += len(baseline_result)
                    logger.debug(f"Updated baselines for user {user.id}: {len(baseline_result)} metrics")
                else:
                    results['failed_updates'] += 1
                    results['errors'].append(f"User {user.id}: {baseline_result['error']}")

            except Exception as e:
                results['failed_updates'] += 1
                results['errors'].append(f"User {user.id}: {str(e)}")
                logger.error(f"Baseline update failed for user {user.id}: {str(e)}")

        success_rate = results['successful_updates'] / results['total_users'] if results['total_users'] > 0 else 0
        logger.info(f"Baseline updates completed: {results['successful_updates']}/{results['total_users']} users ({success_rate:.1%})")

        return results

    except Exception as e:
        logger.error(f"Statistical baseline update failed: {str(e)}")
        return {'error': str(e)}

def retrain_ml_models() -> Dict:
    """Retrain ML models for pattern recognition and predictions"""
    try:
        logger.info("Starting ML model retraining")

        # Get users with sufficient data for model training
        min_data_points = 100  # Minimum data points needed for training

        users_with_data = db.session.query(User.id).join(Metric).group_by(User.id).having(
            func.count(Metric.id) >= min_data_points
        ).all()

        if not users_with_data:
            return {'message': 'No users with sufficient data for model training', 'models_trained': 0}

        results = {
            'eligible_users': len(users_with_data),
            'models_trained': 0,
            'models_failed': 0,
            'model_performance': {},
            'errors': []
        }

        pattern_recognizer = PatternRecognizer()

        for user_tuple in users_with_data:
            user_id = user_tuple[0]

            try:
                # Train pattern recognition models
                pattern_results = pattern_recognizer.discover_patterns(
                    user_id, timeframe=timedelta(days=60)
                )

                if 'error' not in pattern_results:
                    # Store model performance metrics
                    confidence_scores = pattern_results.get('confidence_scores', {})
                    if confidence_scores:
                        avg_confidence = np.mean(list(confidence_scores.values()))
                        results['model_performance'][user_id] = {
                            'pattern_confidence': avg_confidence,
                            'patterns_discovered': len(confidence_scores),
                            'training_date': datetime.utcnow().isoformat()
                        }

                    results['models_trained'] += 1
                    logger.debug(f"Model trained for user {user_id}")
                else:
                    results['models_failed'] += 1
                    results['errors'].append(f"User {user_id}: {pattern_results['error']}")

            except Exception as e:
                results['models_failed'] += 1
                results['errors'].append(f"User {user_id}: {str(e)}")
                logger.error(f"Model training failed for user {user_id}: {str(e)}")

        # Train global models (simplified implementation)
        try:
            global_model_result = train_global_prediction_models()
            results['global_models'] = global_model_result
        except Exception as e:
            results['errors'].append(f"Global model training failed: {str(e)}")

        success_rate = results['models_trained'] / results['eligible_users'] if results['eligible_users'] > 0 else 0
        logger.info(f"Model retraining completed: {results['models_trained']}/{results['eligible_users']} users ({success_rate:.1%})")

        return results

    except Exception as e:
        logger.error(f"ML model retraining failed: {str(e)}")
        return {'error': str(e)}

def warm_user_caches() -> Dict:
    """Warm up caches for active users"""
    try:
        logger.info("Starting cache warming for active users")

        # Get active users with recent activity
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        active_users = User.query.filter(
            and_(
                User.is_active == True,
                User.id.in_(
                    db.session.query(Metric.user_id).filter(
                        Metric.timestamp >= cutoff_time
                    ).distinct()
                )
            )
        ).all()

        results = {
            'total_users': len(active_users),
            'caches_warmed': 0,
            'cache_errors': 0,
            'errors': []
        }

        for user in active_users:
            try:
                warm_user_cache(user.id)
                results['caches_warmed'] += 1
                logger.debug(f"Cache warmed for user {user.id}")

            except Exception as e:
                results['cache_errors'] += 1
                results['errors'].append(f"User {user.id}: {str(e)}")
                logger.warning(f"Cache warming failed for user {user.id}: {str(e)}")

        logger.info(f"Cache warming completed: {results['caches_warmed']}/{results['total_users']} users")
        return results

    except Exception as e:
        logger.error(f"Cache warming failed: {str(e)}")
        return {'error': str(e)}

def system_health_check() -> Dict:
    """Comprehensive system health check"""
    try:
        logger.info("Starting system health check")

        health_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'metrics': {},
            'alerts': []
        }

        # 1. Database health
        try:
            db_stats = get_table_stats()

            # Test database connectivity
            db.session.execute('SELECT 1')

            health_results['components']['database'] = {
                'status': 'healthy',
                'table_stats': db_stats,
                'connection': 'active'
            }

        except Exception as e:
            health_results['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_results['overall_status'] = 'degraded'
            health_results['alerts'].append('Database connectivity issues detected')

        # 2. Cache health
        try:
            from utils.cache import cache

            # Test cache connectivity
            test_key = f"health_check_{datetime.utcnow().timestamp()}"
            cache.set(test_key, 'test_value', expire=60)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)

            cache_status = 'healthy' if retrieved_value == 'test_value' else 'degraded'

            health_results['components']['cache'] = {
                'status': cache_status,
                'test_result': retrieved_value == 'test_value'
            }

        except Exception as e:
            health_results['components']['cache'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_results['alerts'].append('Cache system issues detected')

        # 3. SMS service health
        try:
            from services.sms_service import SMSService

            sms_service = SMSService()
            sms_test = sms_service.test_connectivity()

            health_results['components']['sms_service'] = {
                'status': 'healthy' if sms_test['success'] else 'degraded',
                'test_result': sms_test
            }

            if not sms_test['success']:
                health_results['alerts'].append('SMS service connectivity issues')

        except Exception as e:
            health_results['components']['sms_service'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_results['alerts'].append('SMS service initialization failed')

        # 4. LLM service health
        try:
            from services.llm_service import LLMService

            llm_service = LLMService()
            llm_status = llm_service.get_provider_status()

            available_providers = sum(1 for status in llm_status.values() if status['available'])
            total_providers = len(llm_status)

            health_results['components']['llm_service'] = {
                'status': 'healthy' if available_providers > 0 else 'degraded',
                'available_providers': available_providers,
                'total_providers': total_providers,
                'provider_status': llm_status
            }

            if available_providers == 0:
                health_results['alerts'].append('No LLM providers available')

        except Exception as e:
            health_results['components']['llm_service'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_results['alerts'].append('LLM service initialization failed')

        # 5. Data flow metrics
        try:
            # Check recent data ingestion
            recent_metrics = Metric.query.filter(
                Metric.timestamp >= datetime.utcnow() - timedelta(hours=24)
            ).count()

            # Check recent alerts
            recent_alerts = Alert.query.filter(
                Alert.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()

            # Check recent reports
            recent_reports = DailyReport.query.filter(
                DailyReport.generated_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()

            health_results['metrics'] = {
                'metrics_last_24h': recent_metrics,
                'alerts_last_24h': recent_alerts,
                'reports_last_24h': recent_reports,
                'active_users': User.query.filter_by(is_active=True).count()
            }

            # Alert if no data flow
            if recent_metrics == 0:
                health_results['alerts'].append('No metric data ingested in last 24 hours')
                health_results['overall_status'] = 'degraded'

        except Exception as e:
            health_results['metrics'] = {'error': str(e)}
            health_results['alerts'].append('Data flow metrics unavailable')

        # 6. System resource check (simplified)
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent

            health_results['components']['system_resources'] = {
                'status': 'healthy',
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent
            }

            # Alert on high resource usage
            if cpu_percent > 90:
                health_results['alerts'].append('High CPU usage detected')
            if memory_percent > 90:
                health_results['alerts'].append('High memory usage detected')
            if disk_percent > 90:
                health_results['alerts'].append('High disk usage detected')

        except ImportError:
            # psutil not available - skip resource monitoring
            health_results['components']['system_resources'] = {
                'status': 'monitoring_unavailable',
                'note': 'psutil not installed'
            }
        except Exception as e:
            health_results['components']['system_resources'] = {
                'status': 'error',
                'error': str(e)
            }

        # Determine overall status
        if health_results['alerts']:
            if any('unhealthy' in str(comp) for comp in health_results['components'].values()):
                health_results['overall_status'] = 'unhealthy'
            else:
                health_results['overall_status'] = 'degraded'

        logger.info(f"System health check completed: {health_results['overall_status']}")

        # Log health check results
        log_maintenance_event('system_health_check', health_results)

        return health_results

    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }

def update_system_statistics() -> Dict:
    """Update and calculate system-wide statistics"""
    try:
        logger.info("Updating system statistics")

        # Calculate user engagement statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()

        # Calculate data ingestion statistics
        last_24h = datetime.utcnow() - timedelta(hours=24)
        last_7d = datetime.utcnow() - timedelta(days=7)
        last_30d = datetime.utcnow() - timedelta(days=30)

        metrics_24h = Metric.query.filter(Metric.timestamp >= last_24h).count()
        metrics_7d = Metric.query.filter(Metric.timestamp >= last_7d).count()
        metrics_30d = Metric.query.filter(Metric.timestamp >= last_30d).count()

        # Calculate alert statistics
        alerts_24h = Alert.query.filter(Alert.created_at >= last_24h).count()
        unresolved_alerts = Alert.query.filter_by(is_resolved=False).count()

        # Calculate report statistics
        reports_24h = DailyReport.query.filter(DailyReport.generated_at >= last_24h).count()
        sms_success_rate = _calculate_sms_success_rate()

        # Calculate intervention statistics
        active_interventions = Intervention.query.filter_by(is_active=True).count()

        statistics = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_engagement': {
                'total_users': total_users,
                'active_users': active_users,
                'active_user_percentage': (active_users / total_users * 100) if total_users > 0 else 0
            },
            'data_ingestion': {
                'metrics_last_24h': metrics_24h,
                'metrics_last_7d': metrics_7d,
                'metrics_last_30d': metrics_30d,
                'daily_average': metrics_7d / 7 if metrics_7d > 0 else 0
            },
            'alert_system': {
                'alerts_last_24h': alerts_24h,
                'unresolved_alerts': unresolved_alerts,
                'alert_rate': (alerts_24h / active_users) if active_users > 0 else 0
            },
            'reporting_system': {
                'reports_generated_24h': reports_24h,
                'sms_success_rate': sms_success_rate,
                'coverage': (reports_24h / active_users * 100) if active_users > 0 else 0
            },
            'intervention_tracking': {
                'active_interventions': active_interventions,
                'intervention_rate': (active_interventions / active_users) if active_users > 0 else 0
            }
        }

        logger.info("System statistics updated successfully")
        return statistics

    except Exception as e:
        logger.error(f"System statistics update failed: {str(e)}")
        return {'error': str(e)}

def train_global_prediction_models() -> Dict:
    """Train global prediction models using aggregated user data"""
    try:
        logger.info("Training global prediction models")

        # This is a simplified implementation
        # In practice, you would:
        # 1. Aggregate anonymized data from all users
        # 2. Train population-level models
        # 3. Store models for use in predictions

        # Get aggregated data (last 60 days)
        cutoff_date = datetime.utcnow() - timedelta(days=60)

        # Aggregate metrics by type
        metric_types = ['hrv', 'sleep_score', 'heart_rate', 'recovery']
        model_results = {}

        for metric_type in metric_types:
            try:
                # Get data for this metric type
                metrics = Metric.query.filter(
                    and_(
                        Metric.metric_type == metric_type,
                        Metric.timestamp >= cutoff_date
                    )
                ).all()

                if len(metrics) < 100:  # Need minimum data
                    continue

                # Prepare features (simplified)
                values = np.array([m.value for m in metrics])
                timestamps = pd.to_datetime([m.timestamp for m in metrics])

                # Create simple features
                hours = timestamps.hour.values
                days_of_week = timestamps.dayofweek.values

                # Train a simple model (placeholder)
                from sklearn.ensemble import RandomForestRegressor
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import mean_squared_error, r2_score

                # Features: hour, day of week, previous values
                X = np.column_stack([hours, days_of_week])
                y = values

                if len(X) > 20:  # Minimum for train/test split
                    X_train, X_test, y_train, y_test = train_test_split(
                        X, y, test_size=0.2, random_state=42
                    )

                    # Train model
                    model = RandomForestRegressor(n_estimators=50, random_state=42)
                    model.fit(X_train, y_train)

                    # Evaluate
                    y_pred = model.predict(X_test)
                    mse = mean_squared_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)

                    # Store model results
                    model_results[metric_type] = {
                        'model_type': 'random_forest',
                        'training_samples': len(X_train),
                        'test_samples': len(X_test),
                        'mse': float(mse),
                        'r2_score': float(r2),
                        'feature_importance': model.feature_importances_.tolist(),
                        'trained_at': datetime.utcnow().isoformat()
                    }

                    # Save model (simplified - in practice, use proper model storage)
                    model_record = MLModel(
                        user_id='global',  # Global model
                        model_type='predictor',
                        target_metric=metric_type,
                        algorithm='random_forest',
                        hyperparameters={'n_estimators': 50},
                        feature_columns=['hour', 'day_of_week'],
                        training_score=float(r2),
                        validation_score=float(r2),
                        test_score=float(r2),
                        feature_importance={'hour': model.feature_importances_[0], 'day_of_week': model.feature_importances_[1]},
                        version=1,
                        is_active=True
                    )

                    db.session.add(model_record)

            except Exception as e:
                logger.warning(f"Global model training failed for {metric_type}: {str(e)}")
                continue

        db.session.commit()

        logger.info(f"Global model training completed: {len(model_results)} models trained")

        return {
            'models_trained': len(model_results),
            'model_results': model_results,
            'training_completed_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Global model training failed: {str(e)}")
        db.session.rollback()
        return {'error': str(e)}

def _calculate_sms_success_rate() -> float:
    """Calculate SMS delivery success rate"""
    try:
        # Get recent SMS attempts from system logs
        last_7d = datetime.utcnow() - timedelta(days=7)

        sms_logs = SystemLog.query.filter(
            and_(
                SystemLog.source == 'sms_service',
                SystemLog.created_at >= last_7d
            )
        ).all()

        if not sms_logs:
            return 0.0

        successful_sends = 0
        total_attempts = 0

        for log in sms_logs:
            if log.context and 'status' in log.context:
                total_attempts += 1
                if log.context['status'] == 'sent':
                    successful_sends += 1

        return (successful_sends / total_attempts) if total_attempts > 0 else 0.0

    except Exception as e:
        logger.warning(f"SMS success rate calculation failed: {str(e)}")
        return 0.0

def log_maintenance_event(event_type: str, event_data: Dict):
    """Log maintenance events to system logs"""
    try:
        log_entry = SystemLog(
            user_id=None,  # System-level event
            level='INFO',
            source='maintenance',
            message=f"Maintenance event: {event_type}",
            context={
                'event_type': event_type,
                'event_data': event_data,
                'maintenance_timestamp': datetime.utcnow().isoformat()
            }
        )

        db.session.add(log_entry)
        db.session.commit()

    except Exception as e:
        logger.error(f"Failed to log maintenance event: {str(e)}")

def archive_old_data(archive_days: int = 365) -> Dict:
    """Archive very old data to reduce database size"""
    try:
        logger.info(f"Starting data archival for data older than {archive_days} days")

        cutoff_date = datetime.utcnow() - timedelta(days=archive_days)

        # Count records to be archived
        old_metrics = Metric.query.filter(Metric.timestamp < cutoff_date).count()
        old_alerts = Alert.query.filter(
            and_(
                Alert.created_at < cutoff_date,
                Alert.is_resolved == True
            )
        ).count()

        archive_results = {
            'cutoff_date': cutoff_date.isoformat(),
            'metrics_to_archive': old_metrics,
            'alerts_to_archive': old_alerts,
            'archived': False,
            'archive_path': None
        }

        # In a full implementation, you would:
        # 1. Export data to archive files
        # 2. Verify archive integrity
        # 3. Delete from main database
        # 4. Store archive metadata

        logger.info(f"Data archival analysis completed: {old_metrics} metrics, {old_alerts} alerts eligible")

        return archive_results

    except Exception as e:
        logger.error(f"Data archival failed: {str(e)}")
        return {'error': str(e)}

# Convenience function for PythonAnywhere scheduled tasks
def run_maintenance(task_type: str = 'daily') -> Dict:
    """Run maintenance tasks - entry point for scheduled tasks"""
    try:
        if task_type == 'daily':
            return daily_cleanup()
        elif task_type == 'baselines':
            return update_statistical_baselines()
        elif task_type == 'models':
            return retrain_ml_models()
        elif task_type == 'cache':
            return warm_user_caches()
        elif task_type == 'health':
            return system_health_check()
        else:
            return {'error': f'Unknown maintenance task type: {task_type}'}

    except Exception as e:
        logger.error(f"Maintenance task {task_type} failed: {str(e)}")
        return {'error': str(e), 'task_type': task_type}