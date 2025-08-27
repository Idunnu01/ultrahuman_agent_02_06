"""
Statistical analysis service - the core intelligence engine
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
from sqlalchemy import and_

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

def _detect_change_points(self, data):
    if not RUPTURES_AVAILABLE:
        logger.warning("Change point detection not available - using simple method")
        # Fallback to simple change detection
        return self._simple_change_detection(data)

    # Original ruptures code
    model = ruptures.Binseg(model="rbf").fit(data)
    return model.predict(pen=10)

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
                user_data[metric_type]['timestamps'] = pd.to_datetime(user_data[metric_type]['timestamps'])

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
                missing_ratio = np.sum(np.isnan(values)) / len(values) if len(values) > 0 else 1.0
                summary['data_quality'][metric_type] = {
                    'completeness': 1.0 - missing_ratio,
                    'n_points': int(n_points),
                    'variance': float(np.var(values[~np.isnan(values)])) if np.any(~np.isnan(values)) else 0.0
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
                clean_values = values[~np.isnan(values)]

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
                            'timestamp': timestamps.iloc[original_idx].isoformat(),
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


    def _run_standard_correlation_analysis(self, aligned_data: Dict, user_id: str) -> Dict:
        """Run the standard correlation analysis when alignment succeeds"""
        # This is the existing correlation analysis logic
        # Move the current correlation analysis code here
        return self.correlation_analyzer.analyze_correlations(
            data=aligned_data,
            methods=['pearson', 'spearman', 'kendall']
        )

    def _analyze_correlations_comprehensive(self, user_id: str, user_data: Dict) -> Dict:
        """Comprehensive correlation analysis between all metric pairs - IMPROVED VERSION"""
        try:
            # First try the standard alignment approach
            aligned_data = self.correlation_analyzer._align_time_series(user_data)

            if aligned_data and len(aligned_data.get('metrics', {})) >= 2:
                # Use the standard correlation analysis
                return self._run_standard_correlation_analysis(aligned_data, user_id)
            else:
                # Fall back to simple pairwise correlation
                logger.info(f"Standard alignment failed for user {user_id}, using fallback method")
                return self._simple_correlation_fallback(user_id, user_data)

        except Exception as e:
            logger.error(f"Correlation analysis failed for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def _analyze_trends_comprehensive(self, user_id: str, user_data: Dict) -> Dict:
        """Comprehensive trend analysis for all metrics"""
        try:
            trend_results = {}

            for metric_type, data in user_data.items():
                values = data['values']
                timestamps = data['timestamps']

                # Clean data
                clean_mask = ~np.isnan(values)
                clean_values = values[clean_mask]
                clean_timestamps = timestamps[clean_mask]

                if len(clean_values) < 7:
                    trend_results[metric_type] = {'error': 'Insufficient data for trend analysis'}
                    continue

                # Convert timestamps to days from start
                start_time = clean_timestamps.min()
                days_elapsed = (clean_timestamps - start_time).dt.total_seconds() / 86400

                # Linear trend analysis
                from scipy.stats import linregress
                slope, intercept, r_value, p_value, std_err = linregress(days_elapsed, clean_values)

                # Mann-Kendall trend test (non-parametric)
                from scipy.stats import kendalltau
                tau, mk_p_value = kendalltau(days_elapsed, clean_values)

                # Change point detection
                change_points = self._detect_change_points(clean_values, clean_timestamps)

                # Seasonal decomposition
                seasonal_analysis = self._analyze_seasonality(clean_values, clean_timestamps)

                # Trend strength assessment
                trend_strength = abs(r_value)
                trend_direction = "improving" if slope > 0 else "declining" if slope < 0 else "stable"

                trend_result = {
                    'linear_trend': {
                        'slope': float(slope),
                        'intercept': float(intercept),
                        'r_squared': float(r_value**2),
                        'p_value': float(p_value),
                        'standard_error': float(std_err),
                        'direction': trend_direction,
                        'strength': trend_strength,
                        'significant': p_value < self.significance_alpha
                    },
                    'mann_kendall_test': {
                        'tau': float(tau),
                        'p_value': float(mk_p_value),
                        'significant': mk_p_value < self.significance_alpha,
                        'trend_present': mk_p_value < self.significance_alpha and abs(tau) > 0.1
                    },
                    'change_points': change_points,
                    'seasonal_analysis': seasonal_analysis,
                    'trend_interpretation': self._interpret_trend(slope, r_value, p_value)
                }

                trend_results[metric_type] = trend_result

            return trend_results

        except Exception as e:
            logger.error(f"Comprehensive trend analysis failed: {str(e)}")
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
            time_bins = pd.date_range(start=start_time, end=end_time, freq='H')

            # Aggregate data into hourly bins
            aggregated_data = {}
            for metric_type, data in user_data.items():
                values = data['values']
                timestamps = data['timestamps']

                # Create time series and resample
                ts = pd.Series(values, index=timestamps)
                hourly_data = ts.resample('H').mean().reindex(time_bins)

                # Forward fill missing values
                hourly_data = hourly_data.fillna(method='ffill').fillna(method='bfill')

                aggregated_data[metric_type] = hourly_data.values
                feature_matrix.append(hourly_data.values)

            if not feature_matrix:
                return {'error': 'No data for pattern recognition'}

            # Transpose so each row is a time point
            feature_matrix = np.array(feature_matrix).T

            # Remove rows with NaN
            valid_mask = ~np.any(np.isnan(feature_matrix), axis=1)
            clean_matrix = feature_matrix[valid_mask]

            if len(clean_matrix) < 10:
                return {'error': 'Insufficient clean data for pattern recognition'}

            # 1. Behavioral clustering
            try:
                # Standardize features
                from sklearn.preprocessing import StandardScaler
                scaler = StandardScaler()
                scaled_matrix = scaler.fit_transform(clean_matrix)

                # K-means clustering
                n_clusters = min(5, len(clean_matrix) // 10)
                if n_clusters >= 2:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                    cluster_labels = kmeans.fit_predict(scaled_matrix)

                    # DBSCAN for density-based clustering
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

                # Hour of day patterns
                hourly_patterns = {}
                for i, metric_type in enumerate(aggregated_data.keys()):
                    metric_values = clean_matrix[:, i]
                    hour_groups = pd.DataFrame({
                        'hour': valid_times.hour,
                        'value': metric_values
                    }).groupby('hour')['value'].agg(['mean', 'std', 'count'])

                    hourly_patterns[metric_type] = hour_groups.to_dict('index')

                # Day of week patterns
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
                values = np.array(data.get('values', []))
                valid_values = values[~np.isnan(values)] if len(values) > 0 else []

                correlation_results['data_availability'][metric_type] = {
                    'total_points': len(values),
                    'valid_points': len(valid_values),
                    'date_range': {
                        'start': min(data.get('timestamps', [])).isoformat() if data.get('timestamps') else None,
                        'end': max(data.get('timestamps', [])).isoformat() if data.get('timestamps') else None
                    } if data.get('timestamps') else None
                }

            # Try pairwise correlations with whatever data we have
            for i, metric1 in enumerate(metric_types):
                for j, metric2 in enumerate(metric_types[i+1:], i+1):
                    pair_key = f"{metric1}_vs_{metric2}"

                    try:
                        data1 = user_data[metric1]
                        data2 = user_data[metric2]

                        # Get overlapping timestamps
                        ts1 = set(data1.get('timestamps', []))
                        ts2 = set(data2.get('timestamps', []))
                        common_ts = ts1.intersection(ts2)

                        if len(common_ts) < 5:  # Need at least 5 common points
                            correlation_results['simple_correlations'][pair_key] = {
                                'error': f'Insufficient overlapping data: {len(common_ts)} common timestamps'
                            }
                            continue

                        # Extract values for common timestamps
                        common_ts_list = sorted(list(common_ts))

                        ts1_to_idx = {ts: i for i, ts in enumerate(data1['timestamps'])}
                        ts2_to_idx = {ts: i for i, ts in enumerate(data2['timestamps'])}

                        values1 = []
                        values2 = []

                        for ts in common_ts_list:
                            if ts in ts1_to_idx and ts in ts2_to_idx:
                                idx1 = ts1_to_idx[ts]
                                idx2 = ts2_to_idx[ts]

                                if (idx1 < len(data1['values']) and idx2 < len(data2['values']) and
                                    not np.isnan(data1['values'][idx1]) and not np.isnan(data2['values'][idx2])):
                                    values1.append(data1['values'][idx1])
                                    values2.append(data2['values'][idx2])

                        if len(values1) >= 5:
                            # Calculate correlation
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
                clean_values = values[~np.isnan(values)]

                if len(clean_values) < 10:
                    continue

                # Test for normality
                normality_result = StatisticalValidator.check_normality(clean_values)

                # Test against baseline (if available)
                baseline = self._get_baseline_statistics('dummy', metric_type)  # Simplified for demo

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

            # Overall confidence score
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

            # Extract key anomalies
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

            # Extract significant correlations
            correlation_results = analysis_results.get('correlation_analysis', {})
            significant_relationships = correlation_results.get('significant_relationships', [])
            for relationship in significant_relationships:
                insights['significant_correlations'].append({
                    'metrics': relationship['metric_pair'],
                    'strength': relationship['strength'],
                    'correlation': relationship['correlation']
                })

            # Extract trends
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
        """Store baseline statistics in database"""
        try:
            baseline = StatisticalBaseline.query.filter_by(
                user_id=user_id, metric_type=metric_type
            ).first()

            if baseline:
                # Update existing
                for key, value in stats.items():
                    if hasattr(baseline, key) and key != 'last_updated':
                        setattr(baseline, key, value)
                baseline.last_updated = datetime.utcnow()
            else:
                # Create new
                baseline = StatisticalBaseline(
                    user_id=user_id,
                    metric_type=metric_type,
                    **{k: v for k, v in stats.items() if k != 'last_updated'}
                )
                db.session.add(baseline)

            db.session.commit()

        except Exception as e:
            logger.error(f"Failed to store baseline statistics: {str(e)}")
            db.session.rollback()

    def _calculate_circadian_pattern(self, values: np.ndarray, timestamps: pd.DatetimeIndex) -> Dict:
        """Calculate circadian (24-hour) patterns"""
        try:
            hourly_stats = pd.DataFrame({
                'hour': timestamps.hour,
                'value': values
            }).groupby('hour')['value'].agg(['mean', 'std', 'count'])

            return hourly_stats.to_dict('index')
        except Exception:
            return {}

    def _calculate_weekly_pattern(self, values: np.ndarray, timestamps: pd.DatetimeIndex) -> Dict:
        """Calculate weekly patterns"""
        try:
            daily_stats = pd.DataFrame({
                'day': timestamps.day_name(),
                'value': values
            }).groupby('day')['value'].agg(['mean', 'std', 'count'])

            return daily_stats.to_dict('index')
        except Exception:
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