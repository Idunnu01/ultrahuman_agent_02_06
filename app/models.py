"""
Database Models for Ultrahuman Lifestyle Agent
"""

from datetime import datetime, timedelta
from sqlalchemy import JSON
from utils.database import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(50), primary_key=True)
    ultrahuman_user_id = db.Column(db.String(100), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    timezone = db.Column(db.String(50), default='UTC')
    onboarded_at = db.Column(db.DateTime, default=datetime.utcnow)
    preferences = db.Column(JSON, default=dict)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    metrics = db.relationship('Metric', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    interventions = db.relationship('Intervention', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('DailyReport', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.id}>'

class Metric(db.Model):
    __tablename__ = 'metrics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # hrv, sleep_score, etc.
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, nullable=False)
    source = db.Column(db.String(50), default='ultrahuman')
    meta_data = db.Column(JSON, default=dict)

    # Statistical fields
    z_score = db.Column(db.Float)
    anomaly_score = db.Column(db.Float)
    percentile_rank = db.Column(db.Float)

    # Indexes and constraints
    __table_args__ = (
        db.Index('idx_user_metric_timestamp', 'user_id', 'metric_type', 'timestamp'),
        db.Index('idx_timestamp', 'timestamp'),
        db.Index('idx_user_timestamp', 'user_id', 'timestamp'),
        # ADD THIS UNIQUE CONSTRAINT
        db.UniqueConstraint('user_id', 'metric_type', 'timestamp', name='unique_user_metric_timestamp'),
    )

    def __repr__(self):
        return f'<Metric {self.metric_type}:{self.value} at {self.timestamp}>'

class StatisticalBaseline(db.Model):
    __tablename__ = 'statistical_baselines'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)

    # Statistical measures
    mean = db.Column(db.Float, nullable=False)
    median = db.Column(db.Float, nullable=False)
    std = db.Column(db.Float, nullable=False)
    mad = db.Column(db.Float)  # Median Absolute Deviation
    q1 = db.Column(db.Float, nullable=False)
    q3 = db.Column(db.Float, nullable=False)
    iqr = db.Column(db.Float, nullable=False)

    # Time-based statistics
    circadian_pattern = db.Column(JSON)  # 24-hour pattern
    weekly_pattern = db.Column(JSON)     # 7-day pattern
    seasonal_components = db.Column(JSON)

    # Sample information
    sample_size = db.Column(db.Integer, nullable=False)
    confidence_interval = db.Column(JSON)  # 95% CI
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_user_metric_baseline', 'user_id', 'metric_type'),
    )

class Correlation(db.Model):
    __tablename__ = 'correlations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    metric1 = db.Column(db.String(50), nullable=False)
    metric2 = db.Column(db.String(50), nullable=False)

    # Different correlation methods
    pearson_r = db.Column(db.Float)
    pearson_p = db.Column(db.Float)
    spearman_r = db.Column(db.Float)
    spearman_p = db.Column(db.Float)
    kendall_tau = db.Column(db.Float)
    kendall_p = db.Column(db.Float)
    mic_score = db.Column(db.Float)  # Maximal Information Coefficient

    # Cross-correlation analysis
    max_cross_corr = db.Column(db.Float)
    optimal_lag_minutes = db.Column(db.Integer)

    # Time scale and sample info
    time_scale = db.Column(db.String(20))  # hourly, daily, weekly
    sample_size = db.Column(db.Integer)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_user_correlation', 'user_id', 'metric1', 'metric2'),
    )

class Intervention(db.Model):
    __tablename__ = 'interventions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # sleep, nutrition, exercise, etc.

    # Timeline
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    # Tracking
    target_metrics = db.Column(JSON)  # Metrics we expect this to affect
    parameters = db.Column(JSON)      # Intervention-specific parameters

    # Statistical effectiveness
    effectiveness_scores = db.Column(JSON)  # By metric
    confidence_scores = db.Column(JSON)

    def __repr__(self):
        return f'<Intervention {self.name} for {self.user_id}>'

class InterventionEffectiveness(db.Model):
    __tablename__ = 'intervention_effectiveness'

    id = db.Column(db.Integer, primary_key=True)
    intervention_id = db.Column(db.Integer, db.ForeignKey('interventions.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)

    # Before/after statistics
    before_mean = db.Column(db.Float)
    before_std = db.Column(db.Float)
    after_mean = db.Column(db.Float)
    after_std = db.Column(db.Float)

    # Statistical tests
    t_statistic = db.Column(db.Float)
    t_p_value = db.Column(db.Float)
    wilcoxon_statistic = db.Column(db.Float)
    wilcoxon_p_value = db.Column(db.Float)

    # Effect size
    cohens_d = db.Column(db.Float)

    # Trend analysis
    trend_change_point = db.Column(db.DateTime)
    trend_slope_before = db.Column(db.Float)
    trend_slope_after = db.Column(db.Float)

    # Confidence
    overall_confidence = db.Column(db.Float)
    sample_size_before = db.Column(db.Integer)
    sample_size_after = db.Column(db.Integer)

    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Pattern(db.Model):
    __tablename__ = 'patterns'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    pattern_type = db.Column(db.String(50), nullable=False)  # cluster, anomaly, trend
    metrics_involved = db.Column(JSON, nullable=False)

    # Pattern characteristics
    pattern_signature = db.Column(JSON)  # The actual pattern data
    frequency = db.Column(db.String(20))  # how often it occurs
    duration = db.Column(db.Interval)     # typical duration

    # Statistical significance
    confidence_score = db.Column(db.Float)
    support_count = db.Column(db.Integer)  # How many times observed

    # Discovery information
    discovered_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_observed = db.Column(db.DateTime)

    # ML model information
    model_method = db.Column(db.String(50))  # kmeans, dbscan, etc.
    model_parameters = db.Column(JSON)

class Alert(db.Model):
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # anomaly, correlation, trend
    severity = db.Column(db.String(20))  # low, medium, high, critical

    # Alert content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    metrics_involved = db.Column(JSON)

    # Statistical context
    statistical_summary = db.Column(JSON)  # z-scores, p-values, etc.
    confidence_score = db.Column(db.Float)

    # Status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    is_resolved = db.Column(db.Boolean, default=False)

    # Delivery tracking
    sms_sent = db.Column(db.Boolean, default=False)
    sms_sent_at = db.Column(db.DateTime)

class DailyReport(db.Model):
    __tablename__ = 'daily_reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    report_date = db.Column(db.Date, nullable=False)

    # Report content
    insights = db.Column(JSON, nullable=False)     # Key insights
    anomalies = db.Column(JSON)                    # Detected anomalies
    correlations = db.Column(JSON)                 # Strong correlations found
    trends = db.Column(JSON)                       # Trend analysis
    predictions = db.Column(JSON)                  # Next-day predictions
    recommendations = db.Column(JSON)              # Actionable recommendations

    # Statistical summary
    statistical_summary = db.Column(JSON)
    confidence_scores = db.Column(JSON)

    # Delivery
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    sms_content = db.Column(db.Text)
    sms_sent = db.Column(db.Boolean, default=False)
    sms_sent_at = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_user_date', 'user_id', 'report_date'),
    )

class MLModel(db.Model):
    __tablename__ = 'ml_models'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # predictor, classifier, etc.
    target_metric = db.Column(db.String(50), nullable=False)

    # Model information
    algorithm = db.Column(db.String(50), nullable=False)  # random_forest, lstm, etc.
    hyperparameters = db.Column(JSON)
    feature_columns = db.Column(JSON)

    # Performance metrics
    training_score = db.Column(db.Float)
    validation_score = db.Column(db.Float)
    test_score = db.Column(db.Float)
    feature_importance = db.Column(JSON)

    # Model versioning
    version = db.Column(db.Integer, default=1)
    trained_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Model storage (for lightweight models, use model_data; for larger ones, store externally)
    model_data = db.Column(db.LargeBinary)  # Pickled model for small models
    model_path = db.Column(db.String(200))  # External storage path for large models

class SystemLog(db.Model):
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'))
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR
    source = db.Column(db.String(50), nullable=False)  # Module/service name
    message = db.Column(db.Text, nullable=False)

    # Context
    context = db.Column(JSON)  # Additional context data
    execution_time_ms = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_user_level_created', 'user_id', 'level', 'created_at'),
        db.Index('idx_source_created', 'source', 'created_at'),
    )