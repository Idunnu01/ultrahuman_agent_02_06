"""
Flask API Routes for Ultrahuman Lifestyle Agent
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from app.models import User, Metric, Alert, DailyReport, Intervention
from services.metrics_service import MetricsService
from services.alert_service import AlertService
from services.learning_service import LearningService
from services.statistical_analyzer import StatisticalAnalyzer
from services.intervention_tracker import InterventionTracker
from tasks.data_ingestion import sync_ultrahuman_data
from tasks.daily_report import generate_daily_report
from utils.database import db
import logging

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'Ultrahuman Lifestyle Agent',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }

@main_bp.route('/users', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['user_id', 'ultrahuman_user_id', 'phone_number']
        for field in required_fields:
            if not data.get(field):
                return {'error': f'Missing required field: {field}'}, 400

        # Check if user already exists
        existing_user = User.query.filter_by(id=data['user_id']).first()
        if existing_user:
            return {'error': 'User already exists'}, 400

        # Create new user
        user = User(
            id=data['user_id'],
            ultrahuman_user_id=data['ultrahuman_user_id'],
            phone_number=data['phone_number'],
            timezone=data.get('timezone', 'UTC'),
            preferences=data.get('preferences', {})
        )

        db.session.add(user)
        db.session.commit()

        # Trigger initial data sync
        sync_ultrahuman_data.delay(user.id)

        return {
            'message': 'User registered successfully',
            'user_id': user.id
        }, 201

    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        db.session.rollback()
        return {'error': 'Internal server error'}, 500

@main_bp.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information"""
    user = User.query.get_or_404(user_id)

    return {
        'user_id': user.id,
        'ultrahuman_user_id': user.ultrahuman_user_id,
        'phone_number': user.phone_number,
        'timezone': user.timezone,
        'onboarded_at': user.onboarded_at.isoformat(),
        'preferences': user.preferences,
        'is_active': user.is_active
    }

@main_bp.route('/users/<user_id>/metrics', methods=['GET'])
def get_metrics(user_id):
    """Get user metrics with optional filtering"""
    user = User.query.get_or_404(user_id)

    # Query parameters
    metric_type = request.args.get('metric_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))

    # Build query
    query = Metric.query.filter_by(user_id=user_id)

    if metric_type:
        query = query.filter_by(metric_type=metric_type)

    if start_date:
        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(Metric.timestamp >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(Metric.timestamp <= end_dt)

    metrics = query.order_by(Metric.timestamp.desc()).limit(limit).all()

    return {
        'metrics': [{
            'id': m.id,
            'metric_type': m.metric_type,
            'value': m.value,
            'unit': m.unit,
            'timestamp': m.timestamp.isoformat(),
            'z_score': m.z_score,
            'anomaly_score': m.anomaly_score,
            'percentile_rank': m.percentile_rank,
            'meta_data': m.meta_data
        } for m in metrics]
    }

@main_bp.route('/users/<user_id>/analysis', methods=['POST'])
def run_analysis(user_id):
    """Run comprehensive statistical analysis for a user"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        analysis_type = data.get('analysis_type', 'comprehensive')
        metrics = data.get('metrics', [])
        timeframe_days = data.get('timeframe_days', 30)

        analyzer = StatisticalAnalyzer()

        if analysis_type == 'anomaly':
            results = analyzer.detect_anomalies(
                user_id=user_id,
                metrics=metrics,
                timeframe=timedelta(days=timeframe_days)
            )
        elif analysis_type == 'correlation':
            results = analyzer.analyze_correlations(
                user_id=user_id,
                metrics=metrics,
                timeframe=timedelta(days=timeframe_days)
            )
        elif analysis_type == 'trend':
            results = analyzer.analyze_trends(
                user_id=user_id,
                metrics=metrics,
                timeframe=timedelta(days=timeframe_days)
            )
        else:  # comprehensive
            results = analyzer.run_comprehensive_analysis(
                user_id=user_id,
                timeframe=timedelta(days=timeframe_days)
            )

        return {
            'analysis_type': analysis_type,
            'user_id': user_id,
            'timeframe_days': timeframe_days,
            'results': results,
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error running analysis for user {user_id}: {str(e)}")
        return {'error': 'Analysis failed'}, 500

@main_bp.route('/users/<user_id>/interventions', methods=['GET'])
def get_interventions(user_id):
    """Get user interventions"""
    user = User.query.get_or_404(user_id)

    interventions = Intervention.query.filter_by(user_id=user_id)\
        .order_by(Intervention.started_at.desc()).all()

    return {
        'interventions': [{
            'id': i.id,
            'name': i.name,
            'description': i.description,
            'category': i.category,
            'started_at': i.started_at.isoformat(),
            'ended_at': i.ended_at.isoformat() if i.ended_at else None,
            'is_active': i.is_active,
            'target_metrics': i.target_metrics,
            'effectiveness_scores': i.effectiveness_scores,
            'confidence_scores': i.confidence_scores
        } for i in interventions]
    }

@main_bp.route('/users/<user_id>/interventions', methods=['POST'])
def create_intervention(user_id):
    """Create a new intervention"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        intervention = Intervention(
            user_id=user_id,
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', 'general'),
            started_at=datetime.utcnow(),
            target_metrics=data.get('target_metrics', []),
            parameters=data.get('parameters', {})
        )

        db.session.add(intervention)
        db.session.commit()

        return {
            'message': 'Intervention created successfully',
            'intervention_id': intervention.id
        }, 201

    except Exception as e:
        logger.error(f"Error creating intervention for user {user_id}: {str(e)}")
        db.session.rollback()
        return {'error': 'Failed to create intervention'}, 500

@main_bp.route('/users/<user_id>/interventions/<int:intervention_id>/end', methods=['POST'])
def end_intervention(user_id, intervention_id):
    """End an active intervention and calculate effectiveness"""
    try:
        user = User.query.get_or_404(user_id)
        intervention = Intervention.query.filter_by(
            id=intervention_id, user_id=user_id
        ).first_or_404()

        if not intervention.is_active:
            return {'error': 'Intervention is already ended'}, 400

        # End the intervention
        intervention.ended_at = datetime.utcnow()
        intervention.is_active = False

        # Calculate effectiveness
        tracker = InterventionTracker()
        effectiveness = tracker.calculate_effectiveness(intervention)

        intervention.effectiveness_scores = effectiveness.get('effectiveness_scores', {})
        intervention.confidence_scores = effectiveness.get('confidence_scores', {})

        db.session.commit()

        return {
            'message': 'Intervention ended successfully',
            'effectiveness_analysis': effectiveness
        }

    except Exception as e:
        logger.error(f"Error ending intervention {intervention_id}: {str(e)}")
        db.session.rollback()
        return {'error': 'Failed to end intervention'}, 500

@main_bp.route('/users/<user_id>/alerts', methods=['GET'])
def get_alerts(user_id):
    """Get user alerts"""
    user = User.query.get_or_404(user_id)

    # Query parameters
    severity = request.args.get('severity')
    alert_type = request.args.get('alert_type')
    unresolved_only = request.args.get('unresolved_only', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 50))

    query = Alert.query.filter_by(user_id=user_id)

    if severity:
        query = query.filter_by(severity=severity)

    if alert_type:
        query = query.filter_by(alert_type=alert_type)

    if unresolved_only:
        query = query.filter_by(is_resolved=False)

    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

    return {
        'alerts': [{
            'id': a.id,
            'alert_type': a.alert_type,
            'severity': a.severity,
            'title': a.title,
            'message': a.message,
            'metrics_involved': a.metrics_involved,
            'statistical_summary': a.statistical_summary,
            'confidence_score': a.confidence_score,
            'created_at': a.created_at.isoformat(),
            'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None,
            'is_resolved': a.is_resolved
        } for a in alerts]
    }

@main_bp.route('/users/<user_id>/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(user_id, alert_id):
    """Mark an alert as resolved"""
    user = User.query.get_or_404(user_id)
    alert = Alert.query.filter_by(id=alert_id, user_id=user_id).first_or_404()

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()

    db.session.commit()

    return {'message': 'Alert resolved successfully'}

@main_bp.route('/users/<user_id>/reports', methods=['GET'])
def get_reports(user_id):
    """Get daily reports for a user"""
    user = User.query.get_or_404(user_id)

    # Query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 30))

    query = DailyReport.query.filter_by(user_id=user_id)

    if start_date:
        start_dt = datetime.fromisoformat(start_date).date()
        query = query.filter(DailyReport.report_date >= start_dt)

    if end_date:
        end_dt = datetime.fromisoformat(end_date).date()
        query = query.filter(DailyReport.report_date <= end_dt)

    reports = query.order_by(DailyReport.report_date.desc()).limit(limit).all()

    return {
        'reports': [{
            'id': r.id,
            'report_date': r.report_date.isoformat(),
            'insights': r.insights,
            'anomalies': r.anomalies,
            'correlations': r.correlations,
            'trends': r.trends,
            'predictions': r.predictions,
            'recommendations': r.recommendations,
            'statistical_summary': r.statistical_summary,
            'confidence_scores': r.confidence_scores,
            'generated_at': r.generated_at.isoformat(),
            'sms_sent': r.sms_sent,
            'sms_sent_at': r.sms_sent_at.isoformat() if r.sms_sent_at else None
        } for r in reports]
    }

@main_bp.route('/users/<user_id>/reports/generate', methods=['POST'])
def generate_report_manual(user_id):
    """Manually generate a daily report"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json() or {}

        report_date = data.get('report_date')
        if report_date:
            report_date = datetime.fromisoformat(report_date).date()
        else:
            report_date = datetime.utcnow().date()

        # Check if report already exists
        existing_report = DailyReport.query.filter_by(
            user_id=user_id, report_date=report_date
        ).first()

        if existing_report and not data.get('force_regenerate', False):
            return {'error': 'Report already exists for this date'}, 400

        # Generate report
        task = generate_daily_report.delay(user_id, report_date.isoformat())

        return {
            'message': 'Report generation started',
            'task_id': task.id,
            'report_date': report_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating manual report for user {user_id}: {str(e)}")
        return {'error': 'Failed to generate report'}, 500

@main_bp.route('/users/<user_id>/sync', methods=['POST'])
def sync_data_manual(user_id):
    """Manually trigger data sync from Ultrahuman"""
    try:
        user = User.query.get_or_404(user_id)

        # Trigger data sync
        task = sync_ultrahuman_data.delay(user_id)

        return {
            'message': 'Data sync started',
            'task_id': task.id
        }

    except Exception as e:
        logger.error(f"Error triggering manual sync for user {user_id}: {str(e)}")
        return {'error': 'Failed to start data sync'}, 500

@main_bp.route('/users/<user_id>/learning/status', methods=['GET'])
def get_learning_status(user_id):
    """Get learning system status for a user"""
    try:
        user = User.query.get_or_404(user_id)

        learning_service = LearningService()
        status = learning_service.get_learning_status(user_id)

        return status

    except Exception as e:
        logger.error(f"Error getting learning status for user {user_id}: {str(e)}")
        return {'error': 'Failed to get learning status'}, 500

@main_bp.route('/users/<user_id>/preferences', methods=['PUT'])
def update_preferences(user_id):
    """Update user preferences"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        # Update preferences
        user.preferences.update(data.get('preferences', {}))

        # Update other fields if provided
        if 'timezone' in data:
            user.timezone = data['timezone']

        if 'phone_number' in data:
            user.phone_number = data['phone_number']

        db.session.commit()

        return {
            'message': 'Preferences updated successfully',
            'preferences': user.preferences
        }

    except Exception as e:
        logger.error(f"Error updating preferences for user {user_id}: {str(e)}")
        db.session.rollback()
        return {'error': 'Failed to update preferences'}, 500

@main_bp.route('/admin/stats', methods=['GET'])
def get_system_stats():
    """Get system-wide statistics (admin endpoint)"""
    try:
        stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'total_metrics': Metric.query.count(),
            'metrics_last_24h': Metric.query.filter(
                Metric.timestamp >= datetime.utcnow() - timedelta(days=1)
            ).count(),
            'active_interventions': Intervention.query.filter_by(is_active=True).count(),
            'unresolved_alerts': Alert.query.filter_by(is_resolved=False).count(),
            'reports_generated_today': DailyReport.query.filter_by(
                report_date=datetime.utcnow().date()
            ).count()
        }

        return stats

    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return {'error': 'Failed to get system stats'}, 500

@main_bp.route('/webhook/ultrahuman', methods=['POST'])
def ultrahuman_webhook():
    """Webhook endpoint for real-time Ultrahuman data"""
    try:
        data = request.get_json()

        # Validate webhook signature if configured
        # signature = request.headers.get('X-Ultrahuman-Signature')
        # if not validate_webhook_signature(data, signature):
        #     return {'error': 'Invalid signature'}, 401

        user_id = data.get('user_id')
        if not user_id:
            return {'error': 'Missing user_id'}, 400

        # Process incoming data
        metrics_service = MetricsService()
        processed_data = metrics_service.process_webhook_data(data)

        # Check for immediate alerts
        alert_service = AlertService()
        alert_service.check_real_time_alerts(user_id, processed_data)

        return {'message': 'Webhook processed successfully'}

    except Exception as e:
        logger.error(f"Error processing Ultrahuman webhook: {str(e)}")
        return {'error': 'Webhook processing failed'}, 500