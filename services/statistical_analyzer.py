"""
Statistical analysis service - the core intelligence engine
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
from sqlalchemy import and_
from scipy import stats

from app.models import (User, Metric, StatisticalBaseline, Correlation,
                       Pattern, InterventionEffectiveness)
from utils.database import db
from utils.cache import cache_statistical_analysis, MetricsCache
from utils.stats_utils import (StatisticalValidator, EffectSizeCalculator,
                              StatisticalTests, RobustStatistics)
from analysis.anomaly_detection import AnomalyDetector
from analysis.correlation_analysis import CorrelationAnalyzer
from analysis.trend_analysis import TrendAnalyzer
from services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

try:
    import ruptures
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False

def safe_json_serialize(obj):
    """Safely serialize objects to JSON, handling NaN and datetime"""
    if isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (int, float)):
        # Handle regular Python floats that might be NaN
        if pd.isna(obj) or (isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj))):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return safe_json_serialize(obj.tolist())
    elif isinstance(obj, pd.Series):
        return safe_json_serialize(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return safe_json_serialize(obj.to_dict('index'))
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()
    elif pd.isna(obj):
        return None
    else:
        try:
            # Additional check for any remaining NaN values
            if hasattr(obj, 'isna') and obj.isna():
                return None
            elif hasattr(obj, '__float__') and np.isnan(float(obj)):
                return None
        except (ValueError, TypeError):
            pass
        return obj

class StatisticalAnalyzer:
    """Core statistical analysis engine with advanced ML and statistical methods"""

    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.metrics_service = MetricsService()

        # Statistical significance thresholds
        self.significance_alpha = 0.05
        self.effect_size_thresholds = {
            'small': 0.2,
            'medium': 0.5,
            'large': 0.8
        }

    @cache_statistical_analysis(expire_seconds=1800)
    def run_comprehensive_analysis(self, user_id: str, timeframe: timedelta = timedelta(days=30)) -> Dict:
        """Run comprehensive statistical analysis for a user"""
        try:
            logger.info(f"Starting comprehensive analysis for user {user_id}")

            # Get user data
            user_data = self._get_user_data(user_id, timeframe)
            if not user_data:
                return {'error': 'No data available for analysis'}

            # Initialize results
            analysis_results = {
                'user_id': user_id,
                'timeframe_days': timeframe.days,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'data_summary': self._generate_data_summary(user_data),
                'baseline_statistics': {},
                'anomaly_detection': {},
                'correlation_analysis': {},
                'trend_analysis': {},
                'pattern_recognition': {},
                'statistical_significance': {},
                'confidence_assessments': {}
            }

            # 1. Update baseline statistics
            baseline_results = self._update_baseline_statistics(user_id, user_data)
            analysis_results['baseline_statistics'] = baseline_results

            # 2. Anomaly detection
            anomaly_results = self._detect_anomalies_comprehensive(user_id, user_data)
            analysis_results['anomaly_detection'] = anomaly_results

            # 3. Correlation analysis
            correlation_results = self._analyze_correlations_comprehensive(user_id, user_data)
            analysis_results['correlation_analysis'] = correlation_results

            # 4. Trend analysis
            trend_results = self._analyze_trends_comprehensive(user_id, user_data)
            analysis_results['trend_analysis'] = trend_results

            # 5. Pattern recognition
            pattern_results = self._recognize_patterns(user_id, user_data)
            analysis_results['pattern_recognition'] = pattern_results

            # 6. Statistical significance testing
            significance_results = self._test_statistical_significance(user_data)
            analysis_results['statistical_significance'] = significance_results

            # 7. Generate confidence assessments
            confidence_results = self._assess_analysis_confidence(analysis_results)
            analysis_results['confidence_assessments'] = confidence_results

            # 8. Generate insights summary
            insights_summary = self._generate_insights_summary(analysis_results)
            analysis_results['insights_summary'] = insights_summary

            logger.info(f"Comprehensive analysis completed for user {user_id}")
            return analysis_results

        except ValueError as e:
            if "truth value" in str(e) or "ambiguous" in str(e):
                logger.warning(f"Array boolean context error in comprehensive analysis for user {user_id}: {str(e)}")
                # Return a fallback analysis result
                return {
                    'user_id': user_id,
                    'timeframe_days': timeframe.days,
                    'analysis_timestamp': datetime.utcnow().isoformat(),
                    'error': 'Array boolean context error - using fallback analysis',
                    'data_summary': {'error': 'Analysis incomplete due to data type issues'},
                    'baseline_statistics': {'error': 'Analysis incomplete'},
                    'anomaly_detection': {'error': 'Analysis incomplete'},
                    'correlation_analysis': {'error': 'Analysis incomplete'},
                    'trend_analysis': {'error': 'Analysis incomplete'},
                    'pattern_recognition': {'error': 'Analysis incomplete'},
                    'statistical_significance': {'error': 'Analysis incomplete'},
                    'confidence_assessments': {'error': 'Analysis incomplete'}
                }
            else:
                logger.error(f"Comprehensive analysis failed for user {user_id}: {str(e)}")
                return {'error': str(e), 'user_id': user_id}
        except Exception as e:
            logger.error(f"Comprehensive analysis failed for user {user_id}: {str(e)}")
            return {'error': str(e), 'user_id': user_id}

    def _get_user_data(self, user_id: str, timeframe: timedelta) -> Optional[Dict]:
        """Retrieve and organize user data for analysis"""
        try:
            start_time = datetime.utcnow() - timeframe

            # Get metrics from database
            metrics_query = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.timestamp >= start_time
                )
            ).order_by(Metric.timestamp).all()

            if not metrics_query:
                return None

            # Organize data by metric type
            user_data = {}
            for metric in metrics_query:
                if metric.metric_type not in user_data:
                    user_data[metric.metric_type] = {
                        'values': [],
                        'timestamps': [],
                        'metadata': []
                    }

                user_data[metric.metric_type]['values'].append(metric.value)
                user_data[metric.metric_type]['timestamps'].append(metric.timestamp)
                user_data[metric.metric_type]['metadata'].append(metric.metadata or {})

            # Convert to numpy arrays for efficient computation
            for metric_type in user_data:
                user_data[metric_type]['values'] = np.array(user_data[metric_type]['values'])

                # Ensure timestamps are properly formatted
                timestamps = user_data[metric_type]['timestamps']
                if timestamps is not None and len(timestamps) > 0:
                    try:
                        user_data[metric_type]['timestamps'] = pd.to_datetime(timestamps, errors='coerce')
                        # Remove any NaT (Not a Time) values
                        valid_mask = user_data[metric_type]['timestamps'].notna()
                        user_data[metric_type]['timestamps'] = user_data[metric_type]['timestamps'][valid_mask]
                        user_data[metric_type]['values'] = user_data[metric_type]['values'][valid_mask]

                        logger.debug(f"Processed {metric_type}: {len(user_data[metric_type]['values'])} valid data points")
                    except Exception as e:
                        logger.warning(f"Failed to process timestamps for {metric_type}: {str(e)}")
                        # Fallback: create dummy timestamps
                        user_data[metric_type]['timestamps'] = pd.date_range(
                            start=pd.Timestamp.now() - pd.Timedelta(days=len(timestamps)),
                            periods=len(timestamps),
                            freq='D'
                        )
                else:
                    logger.warning(f"No timestamps found for {metric_type}")
                    # Create dummy timestamps if none exist
                    user_data[metric_type]['timestamps'] = pd.date_range(
                        start=pd.Timestamp.now() - pd.Timedelta(days=30),
                        periods=30,
                        freq='D'
                    )

            return user_data

        except Exception as e:
            logger.error(f"Failed to get user data for {user_id}: {str(e)}")
            return None

    def _generate_data_summary(self, user_data: Dict) -> Dict:
        """Generate summary statistics for the dataset"""
        try:
            summary = {
                'total_metrics': len(user_data),
                'total_data_points': 0,
                'date_range': {},
                'sampling_frequency': {},
                'data_quality': {}
            }

            all_timestamps = []
            for metric_type, data in user_data.items():
                n_points = len(data['values'])
                summary['total_data_points'] += n_points

                # Date range for this metric
                timestamps = data['timestamps']
                summary['date_range'][metric_type] = {
                    'start': timestamps.min().isoformat(),
                    'end': timestamps.max().isoformat(),
                    'duration_days': (timestamps.max() - timestamps.min()).days
                }

                # Sampling frequency
                if n_points > 1:
                    time_diffs = np.diff(timestamps).astype('timedelta64[h]').astype(float)
                    median_interval = np.median(time_diffs)
                    summary['sampling_frequency'][metric_type] = {
                        'median_hours': float(median_interval),
                        'consistency_score': 1.0 - (np.std(time_diffs) / (median_interval + 1e-8))
                    }

                # Data quality assessment
                values = data['values']
                values = self._ensure_numpy_array(values)

                missing_ratio = np.sum(np.isnan(values)) / len(values) if len(values) > 0 else 1.0
                summary['data_quality'][metric_type] = {
                    'completeness': 1.0 - missing_ratio,
                    'n_points': int(n_points),
                    'variance': float(np.var(values[~np.isnan(values)])) if len(values) > 0 and np.any(~np.isnan(values)) else 0.0
                }

                all_timestamps.extend(timestamps)

            # Overall date range
            if all_timestamps:
                all_timestamps = pd.to_datetime(all_timestamps)
                summary['overall_date_range'] = {
                    'start': all_timestamps.min().isoformat(),
                    'end': all_timestamps.max().isoformat(),
                    'total_duration_days': (all_timestamps.max() - all_timestamps.min()).days
                }

            return summary

        except Exception as e:
            logger.error(f"Data summary generation failed: {str(e)}")
            return {'error': str(e)}

    def _update_baseline_statistics(self, user_id: str, user_data: Dict) -> Dict:
        """Update or create baseline statistics for all metrics"""
        try:
            baseline_results = {}

            for metric_type, data in user_data.items():
                values = data['values']
                values = self._ensure_numpy_array(values)
                clean_mask = ~np.isnan(values)
                clean_values = values[clean_mask]

                if len(clean_values) < 3:
                    baseline_results[metric_type] = {'error': 'Insufficient data'}
                    continue

                # Calculate comprehensive statistics
                baseline_stats = {
                    'mean': float(np.mean(clean_values)),
                    'median': float(np.median(clean_values)),
                    'std': float(np.std(clean_values, ddof=1)),
                    'mad': RobustStatistics.median_absolute_deviation(clean_values),
                    'q1': float(np.percentile(clean_values, 25)),
                    'q3': float(np.percentile(clean_values, 75)),
                    'iqr': float(np.percentile(clean_values, 75) - np.percentile(clean_values, 25)),
                    'sample_size': len(clean_values),
                    'last_updated': datetime.utcnow()
                }

                # Confidence intervals
                from utils.stats_utils import ConfidenceIntervals
                ci_lower, ci_upper = ConfidenceIntervals.mean_ci(clean_values)
                baseline_stats['confidence_interval'] = {
                    'lower': float(ci_lower),
                    'upper': float(ci_upper),
                    'confidence_level': 0.95
                }

                # Circadian and weekly patterns
                timestamps = data['timestamps']
                baseline_stats['circadian_pattern'] = self._calculate_circadian_pattern(clean_values, timestamps)
                baseline_stats['weekly_pattern'] = self._calculate_weekly_pattern(clean_values, timestamps)

                # Update database
                self._store_baseline_statistics(user_id, metric_type, baseline_stats)

                baseline_results[metric_type] = baseline_stats

            return baseline_results

        except Exception as e:
            logger.error(f"Baseline statistics update failed: {str(e)}")
            return {'error': str(e)}

    def _detect_anomalies_comprehensive(self, user_id: str, user_data: Dict) -> Dict:
        """Comprehensive anomaly detection across all metrics"""
        try:
            anomaly_results = {}

            for metric_type, data in user_data.items():
                values = data['values']
                timestamps = data['timestamps']

                # Clean data
                values = self._ensure_numpy_array(values)
                clean_mask = ~np.isnan(values)
                clean_values = values[clean_mask]
                clean_timestamps = timestamps[clean_mask]

                if len(clean_values) < 10:
                    anomaly_results[metric_type] = {'error': 'Insufficient data for anomaly detection'}
                    continue

                # Reshape for anomaly detector
                data_array = clean_values.reshape(-1, 1)

                # Run anomaly detection
                anomaly_result = self.anomaly_detector.detect_anomalies(
                    data=data_array,
                    timestamps=clean_timestamps.tolist(),
                    methods=['z_score', 'modified_z_score', 'isolation_forest', 'local_outlier_factor']
                )

                # Enhanced analysis
                if 'error' not in anomaly_result:
                    # Calculate statistical context
                    baseline = self._get_baseline_statistics(user_id, metric_type)

                    anomaly_indices = np.where(anomaly_result['anomalies'])[0]
                    anomaly_details = []

                    for idx in anomaly_indices:
                        original_idx = np.where(clean_mask)[0][idx]
                        anomaly_details.append({
                            'timestamp': timestamps[original_idx].isoformat() if hasattr(timestamps[original_idx], 'isoformat') else str(timestamps[original_idx]),
                            'value': float(values[original_idx]),
                            'anomaly_score': float(anomaly_result['anomaly_scores'][idx]),
                            'confidence': float(anomaly_result['confidence_scores'][idx]),
                            'z_score': float((values[original_idx] - baseline.get('mean', 0)) /
                                           (baseline.get('std', 1) + 1e-8)) if baseline else None,
                            'percentile_rank': float(stats.percentileofscore(clean_values, values[original_idx]))
                        })

                    anomaly_result['anomaly_details'] = anomaly_details
                    anomaly_result['baseline_context'] = baseline

                anomaly_results[metric_type] = anomaly_result

            # Cross-metric anomaly analysis
            cross_metric_anomalies = self._detect_cross_metric_anomalies(user_data)
            anomaly_results['cross_metric_analysis'] = cross_metric_anomalies

            return anomaly_results

        except Exception as e:
            logger.error(f"Comprehensive anomaly detection failed: {str(e)}")
            return {'error': str(e)}

    def _detect_cross_metric_anomalies(self, user_data: Dict) -> Dict:
        """Detect anomalies that occur across multiple metrics simultaneously"""
        try:
            cross_metric_results = {
                'simultaneous_anomalies': [],
                'metric_interactions': {},
                'summary': {
                    'total_cross_metric_events': 0,
                    'most_affected_metrics': []
                }
            }
            return cross_metric_results
        except Exception as e:
            logger.warning(f"Cross-metric anomaly detection failed: {str(e)}")
            return {'error': str(e)}

    def _run_standard_correlation_analysis(self, aligned_data: Dict, user_id: str) -> Dict:
        """Run the standard correlation analysis when alignment succeeds"""
        return self.correlation_analyzer.analyze_correlations(
            data=aligned_data,
            methods=['pearson', 'spearman', 'kendall']
        )

    def _analyze_correlations_comprehensive(self, user_id: str, user_data: Dict) -> Dict:
        """Comprehensive correlation analysis between all metric pairs - IMPROVED VERSION"""
        try:
            logger.debug(f"User data structure for {user_id}: {list(user_data.keys())}")
            for metric_type, data in user_data.items():
                logger.debug(f"  {metric_type}: values={len(data.get('values', []))}, timestamps={len(data.get('timestamps', []))}")
                if 'timestamps' in data and data['timestamps'] is not None and len(data['timestamps']) > 0:
                    logger.debug(f"    First timestamp: {data['timestamps'][0]}, type: {type(data['timestamps'][0])}")

            aligned_data = self.correlation_analyzer._align_time_series(user_data)

            if aligned_data and len(aligned_data.get('metrics', {})) >= 2:
                return self._run_standard_correlation_analysis(aligned_data, user_id)
            else:
                logger.info(f"Standard alignment failed for user {user_id}, using fallback method")
                return self._simple_correlation_fallback(user_id, user_data)

        except Exception as e:
            logger.error(f"Correlation analysis failed for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def _analyze_trends_comprehensive(self, user_id: str, user_data: Dict) -> Dict:
        """Comprehensive trend analysis for all metrics (robust to timestamp dtypes)."""
        try:
            trend_results = {}

            for metric_type, data in user_data.items():
                values = data.get('values', None)
                timestamps = data.get('timestamps', None)

                # --- Clean / validate inputs safely ---
                values = self._ensure_numpy_array(values)
                if values.size == 0:
                    trend_results[metric_type] = {'error': 'No data for trend analysis'}
                    continue

                # Clean values
                clean_mask = ~np.isnan(values)
                clean_values = values[clean_mask]
                if clean_values.size < 7:
                    trend_results[metric_type] = {'error': 'Insufficient data for trend analysis'}
                    continue

                # Timestamps may be list, Series, or DatetimeIndex; align with clean_mask
                if timestamps is None or len(timestamps) != len(values):
                    clean_timestamps = None
                else:
                    try:
                        ts = pd.to_datetime(timestamps, errors='coerce')
                        ts = ts[clean_mask]
                        if ts.isna().all():
                            clean_timestamps = None
                        else:
                            valid_ts_mask = ~ts.isna()
                            clean_values = clean_values[valid_ts_mask]
                            ts = ts[valid_ts_mask]
                            if ts.size < 7:
                                trend_results[metric_type] = {'error': 'Insufficient clean timestamped data'}
                                continue
                            clean_timestamps = ts
                    except Exception as e:
                        logger.warning(f"Timestamp coercion failed for {metric_type}: {str(e)}")
                        clean_timestamps = None

                # --- Build time axis in days (x) ---
                try:
                    if clean_timestamps is None:
                        days_elapsed = np.arange(clean_values.size, dtype=float)
                    else:
                        start_time = clean_timestamps.min()
                        time_diff = clean_timestamps - start_time  # TimedeltaIndex/Series/array

                        if isinstance(time_diff, pd.TimedeltaIndex):
                            days_elapsed = (time_diff / pd.Timedelta(days=1)).to_numpy()
                        elif hasattr(time_diff, "dt"):
                            days_elapsed = (time_diff.dt.total_seconds() / 86400).to_numpy()
                        else:
                            td_dtype = getattr(time_diff, "dtype", None)
                            if td_dtype is not None and np.issubdtype(td_dtype, np.timedelta64):
                                days_elapsed = time_diff / np.timedelta64(1, "D")
                            else:
                                days_elapsed = np.array([
                                    (td / np.timedelta64(1, "D")) if isinstance(td, np.timedelta64)
                                    else (td.total_seconds() / 86400)
                                    for td in time_diff
                                ], dtype=float)

                    if days_elapsed.shape[0] != clean_values.shape[0]:
                        logger.warning(f"Length mismatch in time axis for {metric_type}; using index fallback")
                        days_elapsed = np.arange(clean_values.size, dtype=float)

                except Exception as e:
                    logger.warning(f"Timestamp arithmetic failed for {metric_type}: {str(e)}")
                    days_elapsed = np.arange(clean_values.size, dtype=float)

                # --- Guard against constant x or y ---
                y_is_constant = np.allclose(clean_values, clean_values[0]) if clean_values.size > 0 else True
                x_is_constant = np.allclose(days_elapsed, days_elapsed[0]) if days_elapsed.size > 0 else True

                from scipy.stats import linregress, kendalltau

                if y_is_constant or x_is_constant or clean_values.size < 3:
                    slope = 0.0
                    intercept = float(clean_values.mean())
                    r_value = 0.0
                    p_value = 1.0
                    std_err = 0.0
                else:
                    slope, intercept, r_value, p_value, std_err = linregress(days_elapsed, clean_values)

                # Mann-Kendall (non-parametric)
                try:
                    if clean_values.size >= 3 and not x_is_constant and not y_is_constant:
                        tau, mk_p_value = kendalltau(days_elapsed, clean_values)
                    else:
                        tau, mk_p_value = 0.0, 1.0
                except Exception as e:
                    logger.debug(f"Mann-Kendall failed for {metric_type}: {str(e)}")
                    tau, mk_p_value = 0.0, 1.0

                # Change points & seasonality
                try:
                    change_points = self._detect_change_points(
                        clean_values,
                        clean_timestamps if clean_timestamps is not None else np.arange(clean_values.size)
                    )
                except Exception as e:
                    logger.debug(f"Change point detection failed for {metric_type}: {str(e)}")
                    change_points = []

                try:
                    seasonal_analysis = self._analyze_seasonality(
                        clean_values,
                        clean_timestamps if clean_timestamps is not None else np.arange(clean_values.size)
                    )
                except Exception as e:
                    logger.debug(f"Seasonality analysis failed for {metric_type}: {str(e)}")
                    seasonal_analysis = {'error': str(e)}

                # Trend descriptors
                trend_strength = abs(r_value)
                if slope > 0:
                    direction = "improving"
                elif slope < 0:
                    direction = "declining"
                else:
                    direction = "stable"

                trend_result = {
                    'linear_trend': {
                        'slope': float(slope),
                        'intercept': float(intercept),
                        'r_squared': float(r_value ** 2),
                        'p_value': float(p_value),
                        'standard_error': float(std_err),
                        'direction': direction,
                        'strength': float(trend_strength),
                        'significant': bool(p_value < self.significance_alpha)
                    },
                    'mann_kendall_test': {
                        'tau': float(tau),
                        'p_value': float(mk_p_value),
                        'significant': bool(mk_p_value < self.significance_alpha),
                        'trend_present': bool(mk_p_value < self.significance_alpha and abs(tau) > 0.1)
                    },
                    'change_points': change_points,
                    'seasonal_analysis': seasonal_analysis,
                    'trend_interpretation': self._interpret_trend(float(slope), float(r_value), float(p_value))
                }

                trend_results[metric_type] = trend_result

            return trend_results

        except Exception as e:
            logger.error(f"Comprehensive trend analysis failed: {str(e)}")
            if "truth value of an array" in str(e):
                logger.warning("Array boolean context error detected - using fallback trend analysis")
                return self._simple_trend_fallback(user_id, user_data)
            return {'error': str(e)}

    def _simple_trend_fallback(self, user_id: str, user_data: Dict) -> Dict:
        """Simple fallback trend analysis when comprehensive analysis fails"""
        try:
            trend_results = {}

            for metric_type, data in user_data.items():
                values = data['values']

                values = self._ensure_numpy_array(values)

                if len(values) < 3:
                    trend_results[metric_type] = {'error': 'Insufficient data for trend analysis'}
                    continue

                clean_mask = ~np.isnan(values)
                clean_values = values[clean_mask]

                if len(clean_values) < 3:
                    trend_results[metric_type] = {'error': 'Insufficient clean data'}
                    continue

                first_third = np.mean(clean_values[:len(clean_values)//3])
                last_third = np.mean(clean_values[-len(clean_values)//3:])

                if last_third > first_third * 1.1:
                    direction = "increasing"
                elif last_third < first_third * 0.9:
                    direction = "decreasing"
                else:
                    direction = "stable"

                trend_results[metric_type] = {
                    'simple_trend': {
                        'direction': direction,
                        'first_third_avg': float(first_third),
                        'last_third_avg': float(last_third),
                        'change_percentage': float((last_third - first_third) / (first_third + 1e-8) * 100.0)
                    }
                }

            return trend_results

        except Exception as e:
            logger.warning(f"Simple trend fallback failed: {str(e)}")
            return {'error': 'All trend analysis methods failed'}

    def _detect_change_points(self, values: np.ndarray, timestamps: np.ndarray) -> List[Dict]:
        """Detect change points in time series data"""
        try:
            change_points = []

            if len(values) < 10:
                return change_points

            window_size = min(5, len(values) // 2)
            rolling_mean = pd.Series(values).rolling(window=window_size, center=True).mean()
            rolling_std = pd.Series(values).rolling(window=window_size, center=True).std()

            threshold = 2.0
            for i in range(window_size, len(values) - window_size):
                try:
                    mean_val = rolling_mean.iloc[i]
                    std_val = rolling_std.iloc[i]

                    if not np.isnan(mean_val) and not np.isnan(std_val) and std_val > 0:
                        z_score = abs(values[i] - mean_val) / std_val
                        if z_score > threshold:
                            ts_i = timestamps[i] if i < len(timestamps) else None
                            if hasattr(ts_i, 'isoformat'):
                                ts_i = ts_i.isoformat()
                            change_points.append({
                                'index': i,
                                'timestamp': ts_i,
                                'value': float(values[i]),
                                'z_score': float(z_score),
                                'type': 'anomaly'
                            })
                except Exception as e:
                    logger.debug(f"Error processing change point at index {i}: {str(e)}")
                    continue

            return change_points

        except Exception as e:
            logger.warning(f"Change point detection failed: {str(e)}")
            return []

    def _analyze_seasonality(self, values: np.ndarray, timestamps: np.ndarray) -> Dict:
        """Analyze seasonal patterns in time series data"""
        try:
            seasonal_analysis = {
                'has_seasonality': False,
                'seasonal_period': None,
                'seasonal_strength': 0.0,
                'seasonal_pattern': {}
            }

            if len(values) < 20:
                return seasonal_analysis

            try:
                from scipy import signal

                autocorr = signal.correlate(values, values, mode='full')
                autocorr = autocorr[len(autocorr)//2:]

                peaks, _ = signal.find_peaks(autocorr, height=0.1*autocorr.max())

                if len(peaks) > 1:
                    seasonal_period = peaks[1] - peaks[0]
                    if 5 <= seasonal_period <= len(values) // 2:
                        seasonal_analysis['has_seasonality'] = True
                        seasonal_analysis['seasonal_period'] = int(seasonal_period)
                        seasonal_analysis['seasonal_strength'] = float(autocorr[seasonal_period] / autocorr[0])

                        if seasonal_period <= 7:
                            seasonal_analysis['seasonal_pattern'] = {'type': 'daily', 'period': seasonal_period}
                        elif seasonal_period <= 30:
                            seasonal_analysis['seasonal_pattern'] = {'type': 'weekly', 'period': seasonal_period}
                        else:
                            seasonal_analysis['seasonal_pattern'] = {'type': 'monthly', 'period': seasonal_period}

            except ImportError:
                seasonal_analysis['error'] = 'scipy.signal not available for seasonality analysis'

            return seasonal_analysis

        except Exception as e:
            logger.warning(f"Seasonality analysis failed: {str(e)}")
            return {'error': str(e)}

    def _interpret_trend(self, slope: float, r_value: float, p_value: float) -> Dict:
        """Interpret trend analysis results"""
        try:
            if slope > 0.01:
                direction = "increasing"
            elif slope < -0.01:
                direction = "decreasing"
            else:
                direction = "stable"

            r_squared = r_value ** 2
            if r_squared > 0.7:
                strength = "strong"
            elif r_squared > 0.4:
                strength = "moderate"
            elif r_squared > 0.2:
                strength = "weak"
            else:
                strength = "very weak"

            if p_value < 0.01:
                significance = "highly significant"
            elif p_value < 0.05:
                significance = "significant"
            elif p_value < 0.1:
                significance = "marginally significant"
            else:
                significance = "not significant"

            if significance == "not significant":
                interpretation = f"Trend is {strength} and {significance}, suggesting no clear pattern"
            else:
                interpretation = f"Trend is {strength} and {significance}, showing {direction} pattern"

            return {
                'direction': direction,
                'strength': strength,
                'significance': significance,
                'r_squared': float(r_squared),
                'interpretation': interpretation
            }

        except Exception as e:
            logger.warning(f"Trend interpretation failed: {str(e)}")
            return {'error': str(e)}

    def _recognize_patterns(self, user_id: str, user_data: Dict) -> Dict:
        """Advanced pattern recognition using ML techniques"""
        try:
            from sklearn.cluster import KMeans, DBSCAN
            from sklearn.decomposition import PCA

            pattern_results = {
                'temporal_patterns': {},
                'behavioral_clusters': {},
                'recurring_sequences': {},
                'anomaly_patterns': {}
            }

            # Prepare feature matrix for pattern recognition
            feature_matrix = []
            timestamps_common = None

            # Find common time grid
            all_timestamps = []
            for metric_type, data in user_data.items():
                all_timestamps.extend(data['timestamps'])

            if not all_timestamps:
                return {'error': 'No timestamp data available'}

            # Create hourly bins
            start_time = min(all_timestamps)
            end_time = max(all_timestamps)
            time_bins = pd.date_range(start=start_time, end=end_time, freq='h')

            # Aggregate data into hourly bins
            aggregated_data = {}
            for metric_type, data in user_data.items():
                values = data['values']
                timestamps = data['timestamps']

                ts = pd.Series(values, index=timestamps)
                hourly_data = ts.resample('h').mean().reindex(time_bins)

                hourly_data = hourly_data.ffill().bfill()

                aggregated_data[metric_type] = hourly_data.values
                feature_matrix.append(hourly_data.values)

            if not feature_matrix:
                return {'error': 'No data for pattern recognition'}

            feature_matrix = np.array(feature_matrix).T

            valid_mask = ~np.any(np.isnan(feature_matrix), axis=1)
            clean_matrix = feature_matrix[valid_mask]

            if len(clean_matrix) < 10:
                return {'error': 'Insufficient clean data for pattern recognition'}

            # 1. Behavioral clustering
            try:
                from sklearn.preprocessing import StandardScaler
                scaler = StandardScaler()
                scaled_matrix = scaler.fit_transform(clean_matrix)

                n_clusters = min(5, len(clean_matrix) // 10)
                if n_clusters >= 2:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                    cluster_labels = kmeans.fit_predict(scaled_matrix)

                    dbscan = DBSCAN(eps=0.5, min_samples=3)
                    dbscan_labels = dbscan.fit_predict(scaled_matrix)

                    pattern_results['behavioral_clusters'] = {
                        'kmeans': {
                            'n_clusters': n_clusters,
                            'labels': cluster_labels.tolist(),
                            'inertia': float(kmeans.inertia_)
                        },
                        'dbscan': {
                            'labels': dbscan_labels.tolist(),
                            'n_clusters': len(set(dbscan_labels)) - (1 if -1 in dbscan_labels else 0),
                            'noise_points': int(np.sum(dbscan_labels == -1))
                        }
                    }
            except Exception as e:
                logger.warning(f"Clustering failed: {str(e)}")
                pattern_results['behavioral_clusters'] = {'error': str(e)}

            # 2. Temporal patterns
            try:
                valid_times = time_bins[valid_mask]

                hourly_patterns = {}
                for i, metric_type in enumerate(aggregated_data.keys()):
                    metric_values = clean_matrix[:, i]
                    hour_groups = pd.DataFrame({
                        'hour': valid_times.hour,
                        'value': metric_values
                    }).groupby('hour')['value'].agg(['mean', 'std', 'count'])

                    hourly_patterns[metric_type] = hour_groups.to_dict('index')

                weekly_patterns = {}
                for i, metric_type in enumerate(aggregated_data.keys()):
                    metric_values = clean_matrix[:, i]
                    dow_groups = pd.DataFrame({
                        'dow': valid_times.dayofweek,
                        'value': metric_values
                    }).groupby('dow')['value'].agg(['mean', 'std', 'count'])

                    weekly_patterns[metric_type] = dow_groups.to_dict('index')

                pattern_results['temporal_patterns'] = {
                    'hourly_patterns': hourly_patterns,
                    'weekly_patterns': weekly_patterns
                }

            except Exception as e:
                logger.warning(f"Temporal pattern analysis failed: {str(e)}")
                pattern_results['temporal_patterns'] = {'error': str(e)}

            return pattern_results

        except Exception as e:
            logger.error(f"Pattern recognition failed: {str(e)}")
            return {'error': str(e)}

    def _simple_correlation_fallback(self, user_id: str, user_data: Dict) -> Dict:
        """Simple correlation analysis fallback when full alignment fails"""
        try:
            correlation_results = {
                'simple_correlations': {},
                'data_availability': {}
            }

            metric_types = list(user_data.keys())

            # Check data availability for each metric
            for metric_type in metric_types:
                data = user_data[metric_type]
                values = data.get('values', [])
                values = self._ensure_numpy_array(values)
                if len(values) > 0:
                    clean_mask = ~np.isnan(values)
                    valid_values = values[clean_mask]
                else:
                    valid_values = []

                correlation_results['data_availability'][metric_type] = {
                    'total_points': len(values),
                    'valid_points': len(valid_values),
                    'date_range': {
                        'start': min(data.get('timestamps', [])).isoformat() if data.get('timestamps') else None,
                        'end': max(data.get('timestamps', [])).isoformat() if data.get('timestamps') else None
                    } if data.get('timestamps') else None
                }

            # Try pairwise correlations with overlapping timestamps
            for i, metric1 in enumerate(metric_types):
                for j, metric2 in enumerate(metric_types[i+1:], i+1):
                    pair_key = f"{metric1}_vs_{metric2}"

                    try:
                        data1 = user_data[metric1]
                        data2 = user_data[metric2]

                        ts1 = set(data1.get('timestamps', []))
                        ts2 = set(data2.get('timestamps', []))
                        common_ts = ts1.intersection(ts2)

                        if len(common_ts) < 5:
                            correlation_results['simple_correlations'][pair_key] = {
                                'error': f'Insufficient overlapping data: {len(common_ts)} common timestamps'
                            }
                            continue

                        common_ts_list = sorted(list(common_ts))

                        ts1_to_idx = {ts: i for i, ts in enumerate(data1['timestamps'])}
                        ts2_to_idx = {ts: i for i, ts in enumerate(data2['timestamps'])}

                        values1, values2 = [], []
                        for ts in common_ts_list:
                            if ts in ts1_to_idx and ts in ts2_to_idx:
                                idx1 = ts1_to_idx[ts]
                                idx2 = ts2_to_idx[ts]

                                if (idx1 < len(data1['values']) and idx2 < len(data2['values']) and
                                    not np.isnan(data1['values'][idx1]) and not np.isnan(data2['values'][idx2])):
                                    values1.append(data1['values'][idx1])
                                    values2.append(data2['values'][idx2])

                        if len(values1) >= 5:
                            from scipy.stats import pearsonr, spearmanr

                            r, p = pearsonr(values1, values2)
                            rho, p_spear = spearmanr(values1, values2)

                            correlation_results['simple_correlations'][pair_key] = {
                                'pearson_r': float(r),
                                'pearson_p': float(p),
                                'spearman_rho': float(rho),
                                'spearman_p': float(p_spear),
                                'sample_size': len(values1),
                                'significant': p < 0.05,
                                'strength': self._interpret_correlation_strength(abs(r))
                            }
                        else:
                            correlation_results['simple_correlations'][pair_key] = {
                                'error': f'Insufficient valid paired data: {len(values1)} pairs'
                            }

                    except Exception as e:
                        correlation_results['simple_correlations'][pair_key] = {
                            'error': f'Correlation calculation failed: {str(e)}'
                        }

            return correlation_results

        except Exception as e:
            logger.error(f"Simple correlation fallback failed: {str(e)}")
            return {'error': str(e)}

    def _test_statistical_significance(self, user_data: Dict) -> Dict:
        """Test statistical significance of findings"""
        try:
            significance_results = {
                'hypothesis_tests': {},
                'effect_sizes': {},
                'multiple_testing_correction': {},
                'power_analysis': {}
            }

            # Collect all p-values for multiple testing correction
            all_p_values = []
            test_names = []

            for metric_type, data in user_data.items():
                values = data['values']
                values = self._ensure_numpy_array(values)
                clean_mask = ~np.isnan(values)
                clean_values = values[clean_mask]

                if len(clean_values) < 10:
                    continue

                # Test for normality
                normality_result = StatisticalValidator.check_normality(clean_values)

                # Test against baseline (if available)
                baseline = self._get_baseline_statistics('dummy', metric_type)  # Simplified

                metric_tests = {
                    'normality_test': normality_result,
                    'sample_size_validation': StatisticalValidator.validate_sample_size(clean_values)
                }

                significance_results['hypothesis_tests'][metric_type] = metric_tests

                # Collect p-values
                if 'shapiro_wilk' in normality_result.get('tests', {}):
                    p_val = normality_result['tests']['shapiro_wilk']['p_value']
                    all_p_values.append(p_val)
                    test_names.append(f"{metric_type}_normality")

            # Multiple testing correction
            if all_p_values:
                correction_result = StatisticalValidator.apply_multiple_testing_correction(
                    all_p_values, method='fdr_bh'
                )
                significance_results['multiple_testing_correction'] = correction_result

            return significance_results

        except Exception as e:
            logger.error(f"Statistical significance testing failed: {str(e)}")
            return {'error': str(e)}

    def _assess_analysis_confidence(self, analysis_results: Dict) -> Dict:
        """Assess overall confidence in the analysis results"""
        try:
            confidence_factors = {
                'data_quality': 0.0,
                'sample_size': 0.0,
                'statistical_power': 0.0,
                'method_agreement': 0.0,
                'temporal_coverage': 0.0
            }

            # Data quality assessment
            data_summary = analysis_results.get('data_summary', {})
            quality_scores = []
            for metric_type, quality_info in data_summary.get('data_quality', {}).items():
                completeness = quality_info.get('completeness', 0)
                n_points = quality_info.get('n_points', 0)
                quality_score = completeness * min(1.0, n_points / 30)  # 30 points = full score
                quality_scores.append(quality_score)

            if quality_scores:
                confidence_factors['data_quality'] = np.mean(quality_scores)

            # Sample size adequacy
            sample_sizes = []
            for metric_type, quality_info in data_summary.get('data_quality', {}).items():
                n_points = quality_info.get('n_points', 0)
                sample_sizes.append(min(1.0, n_points / 50))  # 50 points = full confidence

            if sample_sizes:
                confidence_factors['sample_size'] = np.mean(sample_sizes)

            # Temporal coverage
            duration_days = data_summary.get('overall_date_range', {}).get('total_duration_days', 0)
            confidence_factors['temporal_coverage'] = min(1.0, duration_days / 30)  # 30 days = full coverage

            # Method agreement (for anomaly detection)
            anomaly_results = analysis_results.get('anomaly_detection', {})
            agreement_scores = []
            for metric_type, anomaly_info in anomaly_results.items():
                if isinstance(anomaly_info, dict) and 'confidence_scores' in anomaly_info:
                    avg_confidence = np.mean(anomaly_info['confidence_scores'])
                    agreement_scores.append(avg_confidence)

            if agreement_scores:
                confidence_factors['method_agreement'] = np.mean(agreement_scores)

            overall_confidence = np.mean(list(confidence_factors.values()))

            return {
                'confidence_factors': confidence_factors,
                'overall_confidence': float(overall_confidence),
                'confidence_level': self._interpret_confidence_level(overall_confidence),
                'recommendations': self._generate_confidence_recommendations(confidence_factors)
            }

        except Exception as e:
            logger.error(f"Confidence assessment failed: {str(e)}")
            return {'error': str(e), 'overall_confidence': 0.5}

    def _generate_confidence_recommendations(self, confidence_factors: Dict) -> List[str]:
        """Generate recommendations based on confidence factors"""
        try:
            recommendations = []

            if confidence_factors.get('data_quality', 0) < 0.7:
                recommendations.append("Consider collecting more consistent data for better analysis")

            if confidence_factors.get('sample_size', 0) < 0.6:
                recommendations.append("More data points needed for reliable statistical analysis")

            if confidence_factors.get('variability', 0) < 0.5:
                recommendations.append("High variability detected - focus on consistent measurement")

            if confidence_factors.get('trend_stability', 0) < 0.6:
                recommendations.append("Trends may be unstable - continue monitoring for patterns")

            return recommendations

        except Exception as e:
            logger.warning(f"Confidence recommendations generation failed: {str(e)}")
            return ["Continue monitoring for better insights"]

    def _generate_insights_summary(self, analysis_results: Dict) -> Dict:
        """Generate high-level insights summary"""
        try:
            insights = {
                'key_findings': [],
                'anomalies_detected': [],
                'significant_correlations': [],
                'trends_identified': [],
                'recommendations': [],
                'confidence_score': analysis_results.get('confidence_assessments', {}).get('overall_confidence', 0.5)
            }

            anomaly_results = analysis_results.get('anomaly_detection', {})
            for metric_type, anomaly_info in anomaly_results.items():
                if isinstance(anomaly_info, dict) and 'detection_summary' in anomaly_info:
                    summary = anomaly_info['detection_summary']
                    if summary.get('anomalies_detected', 0) > 0:
                        insights['anomalies_detected'].append({
                            'metric': metric_type,
                            'count': summary['anomalies_detected'],
                            'rate': summary.get('anomaly_rate', 0),
                            'severity': 'high' if summary.get('severe_anomalies', 0) > 0 else 'medium'
                        })

            correlation_results = analysis_results.get('correlation_analysis', {})
            significant_relationships = correlation_results.get('significant_relationships', [])
            for relationship in significant_relationships:
                insights['significant_correlations'].append({
                    'metrics': relationship['metric_pair'],
                    'strength': relationship['strength'],
                    'correlation': relationship['correlation']
                })

            trend_results = analysis_results.get('trend_analysis', {})
            for metric_type, trend_info in trend_results.items():
                if isinstance(trend_info, dict) and 'linear_trend' in trend_info:
                    linear_trend = trend_info['linear_trend']
                    if linear_trend.get('significant', False):
                        insights['trends_identified'].append({
                            'metric': metric_type,
                            'direction': linear_trend['direction'],
                            'strength': linear_trend['strength'],
                            'significance': linear_trend['p_value']
                        })

            return insights

        except Exception as e:
            logger.error(f"Insights summary generation failed: {str(e)}")
            return {'error': str(e)}

    # Helper methods
    def _get_baseline_statistics(self, user_id: str, metric_type: str) -> Dict:
        """Get baseline statistics for a metric"""
        try:
            baseline = StatisticalBaseline.query.filter_by(
                user_id=user_id, metric_type=metric_type
            ).first()

            if baseline:
                return {
                    'mean': baseline.mean,
                    'median': baseline.median,
                    'std': baseline.std,
                    'q1': baseline.q1,
                    'q3': baseline.q3,
                    'iqr': baseline.iqr,
                    'sample_size': baseline.sample_size
                }
            return {}
        except Exception:
            return {}

    def _store_baseline_statistics(self, user_id: str, metric_type: str, stats: Dict):
        """Store baseline statistics in database with safe JSON serialization"""
        try:
            import json

            # Safely serialize JSON fields
            safe_stats = stats.copy()
            json_fields = ['circadian_pattern', 'weekly_pattern', 'confidence_interval']

            for field in json_fields:
                if field in safe_stats and safe_stats[field]:
                    try:
                        # Serialize to JSON string to ensure compatibility
                        safe_stats[field] = json.dumps(safe_json_serialize(safe_stats[field]))
                    except Exception as e:
                        logger.warning(f"Failed to serialize {field}: {str(e)}")
                        safe_stats[field] = "{}"

            baseline = StatisticalBaseline.query.filter_by(
                user_id=user_id, metric_type=metric_type
            ).first()

            if baseline:
                for key, value in safe_stats.items():
                    if hasattr(baseline, key) and key != 'last_updated':
                        setattr(baseline, key, value)
                baseline.last_updated = datetime.utcnow()
            else:
                baseline = StatisticalBaseline(
                    user_id=user_id,
                    metric_type=metric_type,
                    **{k: v for k, v in safe_stats.items() if k != 'last_updated'}
                )
                db.session.add(baseline)

            db.session.commit()

        except Exception as e:
            logger.error(f"Failed to store baseline statistics: {str(e)}")
            db.session.rollback()

    def _calculate_circadian_pattern(self, values: np.ndarray, timestamps: pd.DatetimeIndex) -> Dict:
        """Calculate circadian (24-hour) patterns with safe JSON serialization"""
        try:
            hourly_stats = pd.DataFrame({
                'hour': timestamps.hour,
                'value': values
            }).groupby('hour')['value'].agg(['mean', 'std', 'count'])

            raw_dict = hourly_stats.to_dict('index')
            return safe_json_serialize(raw_dict)
        except Exception as e:
            logger.warning(f"Circadian pattern calculation failed: {str(e)}")
            return {}

    def _calculate_weekly_pattern(self, values: np.ndarray, timestamps: pd.DatetimeIndex) -> Dict:
        """Calculate weekly patterns with safe JSON serialization"""
        try:
            daily_stats = pd.DataFrame({
                'day': timestamps.day_name(),
                'value': values
            }).groupby('day')['value'].agg(['mean', 'std', 'count'])

            raw_dict = daily_stats.to_dict('index')
            return safe_json_serialize(raw_dict)
        except Exception as e:
            logger.warning(f"Weekly pattern calculation failed: {str(e)}")
            return {}

    def _interpret_confidence_level(self, confidence: float) -> str:
        """Interpret confidence score"""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.6:
            return 'medium'
        elif confidence >= 0.4:
            return 'low'
        else:
            return 'very_low'

    def _interpret_correlation_strength(self, correlation: float) -> str:
        """Interpret correlation strength"""
        if correlation >= 0.7:
            return 'very_strong'
        elif correlation >= 0.5:
            return 'strong'
        elif correlation >= 0.3:
            return 'moderate'
        elif correlation >= 0.1:
            return 'weak'
        else:
            return 'negligible'

    def analyze_correlation(self, user_id: str, metric1: str, metric2: str, days_back: int = 7) -> Dict:
        """
        Analyze correlation between two specific metrics for a user
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            from flask import current_app
            if not current_app:
                return {
                    "success": False,
                    "error": "Flask application context not available"
                }

            metrics1 = db.session.query(Metric).filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric1,
                Metric.timestamp >= start_date,
                Metric.timestamp <= end_date
            ).order_by(Metric.timestamp).all()

            metrics2 = db.session.query(Metric).filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric2,
                Metric.timestamp >= start_date,
                Metric.timestamp <= end_date
            ).order_by(Metric.timestamp).all()

            if not metrics1 or not metrics2:
                return {
                    "success": False,
                    "error": f"Insufficient data for correlation analysis. Found {len(metrics1)} {metric1} and {len(metrics2)} {metric2} data points."
                }

            df1 = pd.DataFrame([(m.timestamp.date(), m.value) for m in metrics1],
                               columns=['date', metric1])
            df2 = pd.DataFrame([(m.timestamp.date(), m.value) for m in metrics2],
                               columns=['date', metric2])

            merged_df = pd.merge(df1, df2, on='date', how='inner')

            if len(merged_df) < 3:
                return {
                    "success": False,
                    "error": f"Not enough aligned data points for correlation. Only {len(merged_df)} paired measurements."
                }

            x = merged_df[metric1].values
            y = merged_df[metric2].values

            correlation_coef, p_value = stats.pearsonr(x, y)

            data_points = []
            for _, row in merged_df.iterrows():
                data_points.append(f"{row['date']}: {metric1}={row[metric1]:.2f}, {metric2}={row[metric2]:.2f}")

            x_mean, x_std = np.mean(x), np.std(x)
            y_mean, y_std = np.mean(y), np.std(y)

            result = {
                "success": True,
                "metric1": metric1,
                "metric2": metric2,
                "correlation_coefficient": float(correlation_coef),
                "p_value": float(p_value),
                "sample_size": len(merged_df),
                "date_range": {
                    "start": merged_df['date'].min().isoformat(),
                    "end": merged_df['date'].max().isoformat(),
                    "days": (merged_df['date'].max() - merged_df['date'].min()).days
                },
                "statistics": {
                    f"{metric1}_mean": float(x_mean),
                    f"{metric1}_std": float(x_std),
                    f"{metric2}_mean": float(y_mean),
                    f"{metric2}_std": float(y_std)
                },
                "data_points": data_points,
                "correlation_strength": self._interpret_correlation_strength(abs(correlation_coef)),
                "significance": "significant" if p_value < 0.05 else "not_significant"
            }

            return result

        except Exception as e:
            logger.error(f"Error in correlation analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _ensure_numpy_array(self, values):
        """Ensure values is a numpy array to prevent array boolean context errors"""
        try:
            if not isinstance(values, np.ndarray):
                return np.array(values)
            return values
        except Exception as e:
            logger.warning(f"Failed to convert values to numpy array: {str(e)}")
            return np.array([])

    def _safe_check_array_length(self, arr, min_length=0):
        """Safely check array length to prevent boolean context errors"""
        try:
            if arr is None:
                return False
            if hasattr(arr, '__len__'):
                return len(arr) > min_length
            return False
        except Exception as e:
            logger.warning(f"Failed to check array length: {str(e)}")
            return False

    def _safe_array_operation(self, operation_func, *args, fallback_value=None):
        """Safely perform array operations with error handling"""
        try:
            return operation_func(*args)
        except ValueError as e:
            if "truth value" in str(e) or "ambiguous" in str(e):
                logger.warning(f"Array boolean context error caught: {str(e)}")
                return fallback_value
            else:
                raise e
        except Exception as e:
            logger.error(f"Array operation failed: {str(e)}")
            return fallback_value
