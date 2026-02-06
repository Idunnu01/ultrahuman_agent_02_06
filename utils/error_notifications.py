"""
Error Notification System
Sends SMS when critical errors occur (perfect for single-user monitoring)
"""

import os
import logging
from functools import wraps
from datetime import datetime, timedelta
import traceback

logger = logging.getLogger(__name__)

# Configuration
ERROR_NOTIFICATION_PHONE = os.getenv('ERROR_NOTIFICATION_PHONE')  # Your phone number
ERROR_COOLDOWN_MINUTES = 60  # Don't spam - max 1 error SMS per hour per function

# Track last notification time per function to prevent spam
_last_notifications = {}


def notify_on_error(user_friendly_name=None):
    """
    Decorator that sends SMS when a function errors

    Usage:
        @notify_on_error("Data Sync")
        def sync_data():
            ...

    Args:
        user_friendly_name: Human-readable name for the function (shown in SMS)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log the error
                logger.error(f"❌ {func.__name__} failed: {str(e)}", exc_info=True)

                # Send SMS notification (with cooldown to prevent spam)
                _send_error_notification(
                    function_name=user_friendly_name or func.__name__,
                    error=e,
                    traceback_str=traceback.format_exc()
                )

                # Re-raise the exception
                raise

        return wrapper
    return decorator


def _send_error_notification(function_name: str, error: Exception, traceback_str: str):
    """
    Send error notification via SMS

    Args:
        function_name: Name of the function that failed
        error: The exception that occurred
        traceback_str: Full traceback string
    """
    # Skip if no phone number configured
    if not ERROR_NOTIFICATION_PHONE:
        logger.warning("ERROR_NOTIFICATION_PHONE not set - cannot send error SMS")
        return

    # Check cooldown to prevent spam
    now = datetime.utcnow()
    cooldown_key = function_name

    if cooldown_key in _last_notifications:
        last_time = _last_notifications[cooldown_key]
        if now - last_time < timedelta(minutes=ERROR_COOLDOWN_MINUTES):
            logger.info(f"Skipping error notification for {function_name} (cooldown active)")
            return

    try:
        # Import here to avoid circular imports
        from services.sms_service import SMSService

        sms_service = SMSService()

        # Create concise error message for SMS
        error_message = f"""🚨 App Error Alert

Function: {function_name}
Time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC

Error: {str(error)[:150]}

Check logs for details.
"""

        # Send SMS
        result = sms_service.send_sms(
            user_id="system_error",
            phone_number=ERROR_NOTIFICATION_PHONE,
            message=error_message,
            message_type='urgent_alerts',
            priority='urgent'
        )

        if result['success']:
            logger.info(f"✅ Error notification sent for {function_name}")
            # Update last notification time
            _last_notifications[cooldown_key] = now
        else:
            logger.error(f"Failed to send error notification: {result.get('error')}")

    except Exception as notification_error:
        # Don't fail if notification fails
        logger.error(f"Error sending notification: {str(notification_error)}")


def send_system_alert(message: str, severity: str = 'medium'):
    """
    Manually send a system alert via SMS

    Args:
        message: Alert message
        severity: 'low', 'medium', 'high', 'critical'

    Example:
        send_system_alert("Database backup failed!", severity='high')
    """
    if not ERROR_NOTIFICATION_PHONE:
        logger.warning("ERROR_NOTIFICATION_PHONE not set - cannot send alert")
        return

    try:
        from services.sms_service import SMSService

        severity_emoji = {
            'low': '💡',
            'medium': '⚠️',
            'high': '🚨',
            'critical': '🆘'
        }

        emoji = severity_emoji.get(severity, '📊')
        alert_message = f"{emoji} System Alert\n\n{message}\n\nTime: {datetime.utcnow().strftime('%H:%M:%S')} UTC"

        sms_service = SMSService()
        result = sms_service.send_sms(
            user_id="system_alert",
            phone_number=ERROR_NOTIFICATION_PHONE,
            message=alert_message,
            message_type='urgent_alerts' if severity in ['high', 'critical'] else 'alerts',
            priority='urgent' if severity in ['high', 'critical'] else 'normal'
        )

        if result['success']:
            logger.info(f"✅ System alert sent: {message[:50]}")
        else:
            logger.error(f"Failed to send alert: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error sending system alert: {str(e)}")


def check_system_health_and_alert():
    """
    Check system health and send alert if issues detected

    Can be called manually or scheduled via cron
    """
    issues = []

    # Check database connectivity
    try:
        from app import create_app
        from utils.database import db

        app = create_app()
        with app.app_context():
            db.engine.execute("SELECT 1")
    except Exception as e:
        issues.append(f"Database: {str(e)[:50]}")

    # Check disk space
    try:
        import shutil
        disk_usage = shutil.disk_usage(".")
        used_percent = (disk_usage.used / disk_usage.total) * 100

        if used_percent > 90:
            issues.append(f"Disk: {used_percent:.0f}% full")
    except Exception as e:
        issues.append(f"Disk check failed: {str(e)[:30]}")

    # Check log file size
    try:
        import os
        log_file = "logs/ultrahuman_agent.log"
        if os.path.exists(log_file):
            log_size_mb = os.path.getsize(log_file) / (1024 * 1024)
            if log_size_mb > 100:  # Log > 100MB
                issues.append(f"Log file: {log_size_mb:.0f}MB")
    except:
        pass

    # Send alert if issues found
    if issues:
        message = "System health check:\n" + "\n".join(f"• {issue}" for issue in issues)
        send_system_alert(message, severity='high')
        return False
    else:
        logger.info("✅ System health check passed")
        return True


# Example usage in tasks
if __name__ == "__main__":
    # Test error notification
    print("Testing error notification system...")

    @notify_on_error("Test Function")
    def test_function():
        raise ValueError("This is a test error!")

    try:
        test_function()
    except ValueError:
        print("Error caught and notification sent (check your phone!)")

    # Test system alert
    send_system_alert("This is a test system alert", severity='low')
