"""
SMS service for delivering daily health reports and alerts
"""

from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import re
from utils.cache import RateLimiter
from app.models import User, SystemLog
from utils.database import db

logger = logging.getLogger(__name__)

class SMSService:
    """SMS delivery service with rate limiting and delivery tracking"""

    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')

        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
            self.is_configured = True
            logger.info("SMS service initialized with Twilio")
        else:
            self.client = None
            self.is_configured = False
            logger.warning("SMS service not configured - missing Twilio credentials")

        # Rate limits (per user)
        self.rate_limits = {
            'daily_reports': {'limit': 1, 'window': 86400},      # 1 per day
            'alerts': {'limit': 5, 'window': 3600},              # 5 per hour
            'urgent_alerts': {'limit': 10, 'window': 86400},     # 10 per day
            'total_daily': {'limit': 15, 'window': 86400}        # 15 total per day
        }

    def _validate_phone_number(self, phone_number: str) -> str:
        """Validate and format phone number"""
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone_number)

        # Add country code if missing (assume US)
        if len(digits_only) == 10:
            digits_only = '1' + digits_only
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            pass  # Already has country code
        else:
            raise ValueError(f"Invalid phone number format: {phone_number}")

        return f"+{digits_only}"

    def _check_rate_limit(self, user_id: str, message_type: str) -> bool:
        """Check if user is within rate limits for message type"""
        if message_type not in self.rate_limits:
            return True

        limit_config = self.rate_limits[message_type]
        rate_key = f"sms_rate:{user_id}:{message_type}"

        is_allowed = RateLimiter.is_allowed(
            rate_key,
            limit_config['limit'],
            limit_config['window']
        )

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {user_id}, type {message_type}")

        return is_allowed

    def _log_sms_attempt(self, user_id: str, phone_number: str, message: str,
                        status: str, error: Optional[str] = None) -> None:
        """Log SMS delivery attempt"""
        try:
            log_entry = SystemLog(
                user_id=user_id,
                level='INFO' if status == 'sent' else 'ERROR',
                source='sms_service',
                message=f"SMS {status} to {phone_number[:8]}***",
                context={
                    'message_length': len(message),
                    'status': status,
                    'error': error,
                    'phone_number_masked': phone_number[:8] + '***'
                }
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log SMS attempt: {str(e)}")

    def send_sms(self, user_id: str, phone_number: str, message: str,
                 message_type: str = 'general', priority: str = 'normal') -> Dict:
        """Send SMS with rate limiting and error handling"""

        if not self.is_configured:
            error_msg = "SMS service not configured"
            self._log_sms_attempt(user_id, phone_number, message, 'failed', error_msg)
            return {
                'success': False,
                'error': error_msg,
                'message_id': None
            }

        try:
            # Validate phone number
            formatted_phone = self._validate_phone_number(phone_number)

            # Check rate limits (skip for urgent alerts)
            if priority != 'urgent' and not self._check_rate_limit(user_id, message_type):
                error_msg = f"Rate limit exceeded for {message_type}"
                self._log_sms_attempt(user_id, formatted_phone, message, 'rate_limited', error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'message_id': None
                }

            # Check total daily limit
            if not self._check_rate_limit(user_id, 'total_daily'):
                error_msg = "Daily SMS limit exceeded"
                self._log_sms_attempt(user_id, formatted_phone, message, 'daily_limit_exceeded', error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'message_id': None
                }

            # Truncate message if too long
            if len(message) > 1600:  # SMS limit
                message = message[:1597] + "..."
                logger.warning(f"Message truncated for user {user_id}")

            # Send SMS via Twilio
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=formatted_phone
            )

            self._log_sms_attempt(user_id, formatted_phone, message, 'sent')

            logger.info(f"SMS sent successfully to user {user_id}, message_id: {twilio_message.sid}")

            return {
                'success': True,
                'message_id': twilio_message.sid,
                'status': twilio_message.status,
                'error': None
            }

        except ValueError as e:
            error_msg = f"Invalid phone number: {str(e)}"
            self._log_sms_attempt(user_id, phone_number, message, 'invalid_phone', error_msg)
            return {
                'success': False,
                'error': error_msg,
                'message_id': None
            }

        except TwilioException as e:
            error_msg = f"Twilio error: {str(e)}"
            self._log_sms_attempt(user_id, phone_number, message, 'twilio_error', error_msg)
            logger.error(f"Twilio SMS failed for user {user_id}: {str(e)}")
            return {
                'success': False,
                'error': error_msg,
                'message_id': None
            }

        except Exception as e:
            error_msg = f"SMS service error: {str(e)}"
            self._log_sms_attempt(user_id, phone_number, message, 'service_error', error_msg)
            logger.error(f"SMS service error for user {user_id}: {str(e)}")
            return {
                'success': False,
                'error': error_msg,
                'message_id': None
            }

    def send_daily_report(self, user_id: str, phone_number: str, report_content: str) -> Dict:
        """Send daily health report SMS"""
        return self.send_sms(
            user_id=user_id,
            phone_number=phone_number,
            message=report_content,
            message_type='daily_reports',
            priority='normal'
        )

    def send_alert(self, user_id: str, phone_number: str, alert_message: str,
                   severity: str = 'medium') -> Dict:
        """Send health alert SMS"""
        priority = 'urgent' if severity in ['high', 'critical'] else 'normal'
        message_type = 'urgent_alerts' if priority == 'urgent' else 'alerts'

        # Add severity indicator to message
        severity_emoji = {
            'low': '💡',
            'medium': '⚠️',
            'high': '🚨',
            'critical': '🆘'
        }

        prefixed_message = f"{severity_emoji.get(severity, '📊')} {alert_message}"

        return self.send_sms(
            user_id=user_id,
            phone_number=phone_number,
            message=prefixed_message,
            message_type=message_type,
            priority=priority
        )

    def send_intervention_update(self, user_id: str, phone_number: str,
                               intervention_name: str, effectiveness_summary: str) -> Dict:
        """Send intervention effectiveness update"""
        message = f"📈 {intervention_name} update: {effectiveness_summary}"

        return self.send_sms(
            user_id=user_id,
            phone_number=phone_number,
            message=message,
            message_type='alerts',
            priority='normal'
        )

    def send_welcome_message(self, user_id: str, phone_number: str) -> Dict:
        """Send welcome message to new users"""
        welcome_message = (
            "🏥 Welcome to Ultrahuman Lifestyle Agent! Your personalized health insights start tomorrow at 4 AM. "
            "We'll analyze your data using advanced statistics and send you actionable daily reports. Let's optimize your health! 💪"
        )

        return self.send_sms(
            user_id=user_id,
            phone_number=phone_number,
            message=welcome_message,
            message_type='general',
            priority='normal'
        )

    def get_delivery_status(self, message_id: str) -> Optional[Dict]:
        """Get delivery status of a sent message"""
        if not self.is_configured or not message_id:
            return None

        try:
            message = self.client.messages(message_id).fetch()

            return {
                'message_id': message.sid,
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'date_sent': message.date_sent,
                'date_updated': message.date_updated,
                'price': message.price,
                'price_unit': message.price_unit
            }

        except TwilioException as e:
            logger.error(f"Failed to get message status for {message_id}: {str(e)}")
            return None

    def get_remaining_rate_limit(self, user_id: str, message_type: str) -> int:
        """Get remaining messages allowed for user and message type"""
        if message_type not in self.rate_limits:
            return 999  # No limit for unknown types

        limit_config = self.rate_limits[message_type]
        rate_key = f"sms_rate:{user_id}:{message_type}"

        return RateLimiter.get_remaining(rate_key, limit_config['limit'])

    def bulk_send_daily_reports(self, user_reports: List[Dict]) -> Dict:
        """Send daily reports to multiple users efficiently"""
        results = {
            'total_users': len(user_reports),
            'successful_sends': 0,
            'failed_sends': 0,
            'rate_limited': 0,
            'errors': []
        }

        for user_report in user_reports:
            try:
                user_id = user_report['user_id']
                phone_number = user_report['phone_number']
                message = user_report['message']

                result = self.send_daily_report(user_id, phone_number, message)

                if result['success']:
                    results['successful_sends'] += 1
                elif 'rate limit' in result.get('error', '').lower():
                    results['rate_limited'] += 1
                else:
                    results['failed_sends'] += 1
                    results['errors'].append({
                        'user_id': user_id,
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                results['failed_sends'] += 1
                results['errors'].append({
                    'user_id': user_report.get('user_id', 'unknown'),
                    'error': str(e)
                })

        logger.info(f"Bulk SMS completed: {results['successful_sends']}/{results['total_users']} sent successfully")
        return results

    def format_health_message(self, insights: List[str], recommendations: List[str],
                            metrics_summary: Dict) -> str:
        """Format health data into a concise SMS message"""
        try:
            # Start with most important insight
            top_insight = insights[0] if insights else "Health data analyzed"

            # Add key metric if significant
            metric_text = ""
            if metrics_summary:
                for metric, data in metrics_summary.items():
                    if data.get('significant_change', False):
                        change = data.get('percent_change', 0)
                        direction = "📈" if change > 0 else "📉"
                        metric_text = f" {metric.upper()}: {direction}{abs(change):.0f}%"
                        break

            # Add top recommendation
            rec_text = ""
            if recommendations:
                rec_text = f" Next: {recommendations[0]}"

            # Combine and truncate if needed
            message = f"{top_insight}{metric_text}{rec_text}"

            if len(message) > 155:  # Leave room for emojis
                message = message[:152] + "..."

            return message

        except Exception as e:
            logger.error(f"Message formatting failed: {str(e)}")
            return "📊 Your health analysis is ready. Check the app for details."

    def schedule_delayed_message(self, user_id: str, phone_number: str, message: str,
                               delay_minutes: int, message_type: str = 'general') -> Dict:
        """Schedule a message to be sent after a delay (for follow-ups)"""
        # This would typically integrate with Celery for delayed tasks
        # For now, we'll create a placeholder that could be implemented

        try:
            from tasks.celery_app import send_delayed_sms

            # Schedule the task
            eta = datetime.utcnow() + timedelta(minutes=delay_minutes)
            task = send_delayed_sms.apply_async(
                args=[user_id, phone_number, message, message_type],
                eta=eta
            )

            return {
                'success': True,
                'task_id': task.id,
                'scheduled_for': eta.isoformat(),
                'message': 'SMS scheduled successfully'
            }

        except Exception as e:
            logger.error(f"Failed to schedule delayed SMS: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_scheduled_message(self, task_id: str) -> Dict:
        """Cancel a scheduled SMS message"""
        try:
            from celery import current_app

            # Revoke the scheduled task
            current_app.control.revoke(task_id, terminate=True)

            return {
                'success': True,
                'message': 'Scheduled SMS cancelled'
            }

        except Exception as e:
            logger.error(f"Failed to cancel scheduled SMS {task_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_user_sms_stats(self, user_id: str, days: int = 30) -> Dict:
        """Get SMS statistics for a user over specified days"""
        try:
            from datetime import datetime, timedelta

            start_date = datetime.utcnow() - timedelta(days=days)

            # Query system logs for SMS activity
            sms_logs = SystemLog.query.filter(
                SystemLog.user_id == user_id,
                SystemLog.source == 'sms_service',
                SystemLog.created_at >= start_date
            ).all()

            # Analyze logs
            stats = {
                'total_attempts': len(sms_logs),
                'successful_sends': 0,
                'failed_sends': 0,
                'rate_limited': 0,
                'daily_reports': 0,
                'alerts': 0,
                'last_sent': None,
                'error_types': {}
            }

            for log in sms_logs:
                context = log.context or {}
                status = context.get('status', 'unknown')

                if status == 'sent':
                    stats['successful_sends'] += 1
                elif 'rate_limited' in status or 'limit_exceeded' in status:
                    stats['rate_limited'] += 1
                else:
                    stats['failed_sends'] += 1
                    error_type = context.get('error', 'unknown_error')
                    stats['error_types'][error_type] = stats['error_types'].get(error_type, 0) + 1

                # Count message types (approximate based on log messages)
                if 'daily report' in log.message.lower():
                    stats['daily_reports'] += 1
                elif 'alert' in log.message.lower():
                    stats['alerts'] += 1

                # Track most recent send
                if status == 'sent' and (stats['last_sent'] is None or log.created_at > stats['last_sent']):
                    stats['last_sent'] = log.created_at

            # Calculate success rate
            if stats['total_attempts'] > 0:
                stats['success_rate'] = stats['successful_sends'] / stats['total_attempts']
            else:
                stats['success_rate'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"Failed to get SMS stats for user {user_id}: {str(e)}")
            return {
                'total_attempts': 0,
                'successful_sends': 0,
                'failed_sends': 0,
                'success_rate': 0.0,
                'error': str(e)
            }

    def test_connectivity(self) -> Dict:
        """Test SMS service connectivity and configuration"""
        if not self.is_configured:
            return {
                'success': False,
                'error': 'SMS service not configured',
                'details': {
                    'account_sid_configured': bool(self.account_sid),
                    'auth_token_configured': bool(self.auth_token),
                    'phone_number_configured': bool(self.phone_number)
                }
            }

        try:
            # Test by fetching account info
            account = self.client.api.accounts(self.account_sid).fetch()

            return {
                'success': True,
                'account_status': account.status,
                'account_name': account.friendly_name,
                'phone_number': self.phone_number,
                'rate_limits': self.rate_limits
            }

        except TwilioException as e:
            return {
                'success': False,
                'error': f"Twilio connectivity test failed: {str(e)}",
                'account_sid': self.account_sid[:8] + '***' if self.account_sid else None
            }

    def get_service_health(self) -> Dict:
        """Get overall health status of SMS service"""
        health_status = {
            'service_name': 'SMS Service',
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'configuration': {
                'provider': 'Twilio',
                'configured': self.is_configured,
                'phone_number': self.phone_number[-4:] if self.phone_number else None
            },
            'rate_limits': self.rate_limits,
            'connectivity': self.test_connectivity()
        }

        # Determine overall status
        if not self.is_configured:
            health_status['status'] = 'misconfigured'
        elif not health_status['connectivity']['success']:
            health_status['status'] = 'unhealthy'

        return health_status


# Utility functions for SMS templates

def create_anomaly_alert_message(metric_name: str, current_value: float,
                                baseline_mean: float, z_score: float,
                                severity: str) -> str:
    """Create formatted anomaly alert message"""

    emoji_map = {
        'low': '💡',
        'medium': '⚠️',
        'high': '🚨',
        'critical': '🆘'
    }

    emoji = emoji_map.get(severity, '📊')
    direction = "high" if current_value > baseline_mean else "low"

    return (f"{emoji} {metric_name.upper()} anomaly detected: "
            f"{current_value:.1f} ({z_score:.1f}σ {direction}). "
            f"Monitor closely and consider intervention.")

def create_correlation_insight_message(metric1: str, metric2: str,
                                     correlation: float, confidence: float) -> str:
    """Create formatted correlation insight message"""

    strength = "strong" if abs(correlation) > 0.7 else "moderate" if abs(correlation) > 0.4 else "weak"
    direction = "positive" if correlation > 0 else "negative"

    return (f"📈 Found {strength} {direction} link between {metric1} & {metric2} "
            f"(r={correlation:.2f}, {confidence:.0f}% confidence). Use this to optimize both!")

def create_trend_alert_message(metric_name: str, trend_direction: str,
                             trend_strength: float, days: int) -> str:
    """Create formatted trend alert message"""

    emoji = "📈" if trend_direction == "improving" else "📉"
    strength_desc = "strong" if trend_strength > 0.7 else "moderate" if trend_strength > 0.4 else "slight"

    return (f"{emoji} {metric_name.upper()} showing {strength_desc} {trend_direction} trend "
            f"over {days} days (R²={trend_strength:.2f}). Keep it up!")

def create_intervention_success_message(intervention_name: str,
                                      primary_metric: str, improvement: float,
                                      confidence: float) -> str:
    """Create formatted intervention success message"""

    return (f"🎯 {intervention_name} working! {primary_metric} improved {improvement:.1f}% "
            f"({confidence:.0f}% confidence). Continue for best results! 💪")

def truncate_message_smartly(message: str, max_length: int = 160) -> str:
    """Intelligently truncate SMS message while preserving meaning"""

    if len(message) <= max_length:
        return message

    # Try to truncate at sentence boundaries first
    sentences = message.split('. ')
    if len(sentences) > 1:
        truncated = sentences[0] + '.'
        if len(truncated) <= max_length - 3:
            return truncated + "..."

    # Fallback to character truncation
    return message[:max_length - 3] + "..."