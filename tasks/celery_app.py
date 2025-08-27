"""
Celery configuration and task orchestration for background processing
"""

from celery import Celery
from celery.schedules import crontab
import os
import logging
from kombu import Queue

logger = logging.getLogger(__name__)

def make_celery(app=None):
    """Create Celery instance with Flask app context"""

    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    celery = Celery(
        'ultrahuman_agent',
        broker=redis_url,
        backend=redis_url,
        include=[
            'tasks.daily_report',
            'tasks.data_ingestion',
            'tasks.maintenance'
        ]
    )

    # Configure Celery
    celery.conf.update(
        # Task serialization
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,

        # Task routing
        task_routes={
            'tasks.daily_report.*': {'queue': 'reports'},
            'tasks.data_ingestion.*': {'queue': 'data_sync'},
            'tasks.maintenance.*': {'queue': 'maintenance'},
            'tasks.analysis.*': {'queue': 'analysis'},
        },

        # Queue configuration
        task_default_queue='default',
        task_queues=(
            Queue('default', routing_key='default'),
            Queue('reports', routing_key='reports'),
            Queue('data_sync', routing_key='data_sync'),
            Queue('maintenance', routing_key='maintenance'),
            Queue('analysis', routing_key='analysis'),
            Queue('urgent', routing_key='urgent'),
        ),

        # Worker configuration
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,

        # Task execution
        task_soft_time_limit=300,  # 5 minutes
        task_time_limit=600,       # 10 minutes hard limit
        task_max_retries=3,
        task_default_retry_delay=60,

        # Results
        result_expires=3600,       # 1 hour
        result_backend_transport_options={
            'master_name': 'mymaster'
        },

        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,

        # Beat schedule for periodic tasks
        beat_schedule={
            # Daily reports at 4 AM UTC
            'generate-daily-reports': {
                'task': 'tasks.daily_report.generate_all_daily_reports',
                'schedule': crontab(hour=4, minute=0),
                'options': {'queue': 'reports'}
            },

            # Hourly data sync
            'sync-ultrahuman-data': {
                'task': 'tasks.data_ingestion.sync_all_users_data',
                'schedule': crontab(minute=0),
                'options': {'queue': 'data_sync'}
            },

            # Real-time data processing (every 15 minutes)
            'process-recent-data': {
                'task': 'tasks.data_ingestion.process_recent_data',
                'schedule': crontab(minute='*/15'),
                'options': {'queue': 'data_sync'}
            },

            # Statistical analysis updates (every 6 hours)
            'update-statistical-baselines': {
                'task': 'tasks.maintenance.update_statistical_baselines',
                'schedule': crontab(hour='*/6', minute=30),
                'options': {'queue': 'analysis'}
            },

            # Daily maintenance at 2 AM
            'daily-maintenance': {
                'task': 'tasks.maintenance.daily_cleanup',
                'schedule': crontab(hour=2, minute=0),
                'options': {'queue': 'maintenance'}
            },

            # Weekly model retraining on Sundays at 3 AM
            'weekly-model-training': {
                'task': 'tasks.maintenance.retrain_ml_models',
                'schedule': crontab(hour=3, minute=0, day_of_week=0),
                'options': {'queue': 'analysis'}
            },

            # Cache warming every 4 hours
            'warm-user-caches': {
                'task': 'tasks.maintenance.warm_user_caches',
                'schedule': crontab(minute=0, hour='*/4'),
                'options': {'queue': 'maintenance'}
            },

            # Health checks every 30 minutes
            'system-health-check': {
                'task': 'tasks.maintenance.system_health_check',
                'schedule': crontab(minute='*/30'),
                'options': {'queue': 'maintenance'}
            }
        }
    )

    # Initialize Flask app context if provided
    if app:
        class ContextTask(celery.Task):
            """Make celery tasks work with Flask app context"""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery

# Create the Celery instance
celery_app = make_celery()

# Task decorators and utilities

def retry_on_failure(max_retries=3, countdown=60):
    """Decorator for automatic task retry on failure"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                if func.request.retries < max_retries:
                    logger.warning(f"Task {func.name} failed, retrying in {countdown}s: {str(exc)}")
                    raise func.retry(countdown=countdown, exc=exc)
                else:
                    logger.error(f"Task {func.name} failed after {max_retries} retries: {str(exc)}")
                    raise
        return wrapper
    return decorator

def log_task_execution(func):
    """Decorator to log task execution"""
    def wrapper(*args, **kwargs):
        task_name = func.name
        logger.info(f"Starting task: {task_name}")

        try:
            result = func(*args, **kwargs)
            logger.info(f"Task completed successfully: {task_name}")
            return result
        except Exception as e:
            logger.error(f"Task failed: {task_name} - {str(e)}")
            raise

    return wrapper

# Task monitoring and management utilities

def get_active_tasks():
    """Get list of active tasks"""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        return active_tasks
    except Exception as e:
        logger.error(f"Failed to get active tasks: {str(e)}")
        return {}

def get_task_stats():
    """Get task execution statistics"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get task stats: {str(e)}")
        return {}

def purge_queue(queue_name):
    """Purge all tasks from a specific queue"""
    try:
        celery_app.control.purge()
        logger.info(f"Purged queue: {queue_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to purge queue {queue_name}: {str(e)}")
        return False

def cancel_task(task_id):
    """Cancel a specific task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Cancelled task: {task_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {str(e)}")
        return False

def get_queue_length(queue_name):
    """Get the number of tasks in a queue"""
    try:
        with celery_app.connection() as conn:
            queue = conn.SimpleQueue(queue_name)
            return queue.qsize()
    except Exception as e:
        logger.error(f"Failed to get queue length for {queue_name}: {str(e)}")
        return -1

# Health monitoring for Celery workers

@celery_app.task(bind=True, queue='maintenance')
def heartbeat_task(self):
    """Heartbeat task to monitor worker health"""
    try:
        from datetime import datetime
        from utils.cache import cache

        worker_id = self.request.hostname
        timestamp = datetime.utcnow().isoformat()

        # Store heartbeat in cache
        cache.set(f"worker_heartbeat:{worker_id}", timestamp, expire=300)

        return {
            'worker_id': worker_id,
            'timestamp': timestamp,
            'status': 'healthy'
        }
    except Exception as e:
        logger.error(f"Heartbeat task failed: {str(e)}")
        raise

def check_worker_health():
    """Check health of all workers"""
    try:
        from datetime import datetime, timedelta
        from utils.cache import cache

        inspect = celery_app.control.inspect()
        registered_workers = inspect.registered()

        if not registered_workers:
            return {'status': 'no_workers', 'workers': []}

        worker_status = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)

        for worker_name in registered_workers.keys():
            heartbeat = cache.get(f"worker_heartbeat:{worker_name}")

            if heartbeat:
                heartbeat_time = datetime.fromisoformat(heartbeat)
                is_healthy = heartbeat_time > cutoff_time
            else:
                is_healthy = False

            worker_status.append({
                'worker_id': worker_name,
                'is_healthy': is_healthy,
                'last_heartbeat': heartbeat
            })

        overall_healthy = all(w['is_healthy'] for w in worker_status)

        return {
            'status': 'healthy' if overall_healthy else 'degraded',
            'workers': worker_status,
            'total_workers': len(worker_status),
            'healthy_workers': sum(1 for w in worker_status if w['is_healthy'])
        }

    except Exception as e:
        logger.error(f"Worker health check failed: {str(e)}")
        return {'status': 'error', 'error': str(e)}

# Delayed SMS task for scheduled messages
@celery_app.task(bind=True, queue='default')
def send_delayed_sms(self, user_id, phone_number, message, message_type='general'):
    """Send SMS message (used for scheduled/delayed messages)"""
    try:
        from services.sms_service import SMSService

        sms_service = SMSService()
        result = sms_service.send_sms(user_id, phone_number, message, message_type)

        if not result['success']:
            logger.error(f"Delayed SMS failed for user {user_id}: {result['error']}")
            raise Exception(result['error'])

        return result

    except Exception as e:
        logger.error(f"Delayed SMS task failed: {str(e)}")
        if self.request.retries < 3:
            raise self.retry(countdown=300, exc=e)  # Retry after 5 minutes
        raise

# Task result utilities

def get_task_result(task_id, timeout=30):
    """Get result of a task with timeout"""
    try:
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_app)
        return result.get(timeout=timeout)

    except Exception as e:
        logger.error(f"Failed to get task result for {task_id}: {str(e)}")
        return None

def is_task_complete(task_id):
    """Check if a task is complete"""
    try:
        from celery.result import AsyncResult

        result = AsyncResult(task_id, app=celery_app)
        return result.ready()

    except Exception as e:
        logger.error(f"Failed to check task status for {task_id}: {str(e)}")
        return False

# Configuration for different deployment environments

def configure_for_production():
    """Production-specific Celery configuration"""
    celery_app.conf.update(
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        worker_log_level='INFO',
        worker_hijack_root_logger=False,
        worker_max_memory_per_child=200000,  # 200MB
        task_soft_time_limit=900,   # 15 minutes
        task_time_limit=1200,       # 20 minutes
    )

def configure_for_development():
    """Development-specific Celery configuration"""
    celery_app.conf.update(
        task_always_eager=False,  # Set to True to execute tasks synchronously
        task_eager_propagates=True,
        worker_log_level='DEBUG',
        task_soft_time_limit=60,   # 1 minute
        task_time_limit=120,       # 2 minutes
    )

# Apply environment-specific configuration
if os.getenv('FLASK_ENV') == 'production':
    configure_for_production()
else:
    configure_for_development()