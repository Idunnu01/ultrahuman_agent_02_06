"""
Advanced trend analysis for health metrics using time series methods
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import linregress, kendalltau
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.arima.model import ARIMA
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime, timedelta

try:
    import ruptures as rpt
    RUPTURES_AVAILABLE = True
except ImportError:
    RUPTURES_AVAILABLE = False
    logging.warning("ruptures not available - change point detection will be limited")

from utils.stats_utils import StatisticalValidator, ConfidenceIntervals
from utils.cache import cache_statistical_analysis

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Advanced trend analysis using multiple statistical and ML methods"""

    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.min_sample_size = 10

        self.trend_methods = {
            'linear_regression': self._linear_trend_analysis,
            'mann_kendall': self._mann_kendall_trend,
            'seasonal_decomposition': self._seasonal_trend_analysis,
            'change_point_detection': self._change_point_detection,
            'autocorrelation': self._autocorrelation_analysis
        }

    def compute(self, user_id: int, query_text: str) -> Dict:
        """
        Compute method for compatibility with metrics service

        Args:
            user_id: User ID
            query_text: Query text to analyze

        Returns:
            Dictionary with trend analysis results
        """
        try:
            # Import here to avoid circular imports
            from services.metrics_service import MetricsService

            # Get metrics data for the user
            metrics_service = MetricsService()

            # Extract metric types from query
            metric_types = []
            query_lower = query_text.lower()

            # Define metric synonyms for trend queries
            metric_patterns = {
                'heart_rate': ['heart rate', 'rhr', 'resting heart rate'],
                'hrv': ['hrv', 'heart rate variability'],
                'sleep_score': ['sleep', 'sleep score', 'sleep quality'],
                'recovery': ['recovery', 'recovery score'],
                'temperature': ['temperature', 'temp', 'body temperature'],
                'glucose': ['glucose', 'blood sugar']
            }

            for metric_type, patterns in metric_patterns.items():
                if any(pattern in query_lower for pattern in patterns):
                    metric_types.append(metric_type)

            if not metric_types:
                # Default to common metrics if none specified
                metric_types = ['heart_rate', 'hrv', 'sleep_score']

            # Get data for analysis
            data = {}
            for metric_type in metric_types:
                try:
                    # Get last 30 days of data
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=30)

                    metrics = metrics_service.get_user_metrics(
                        user_id, metric_type, start_date, end_date
                    )

                    if metrics and len(metrics) >= 3:
                        values = [m.value for m in metrics if m.value is not None]
                        timestamps = [m.timestamp for m in metrics if m.value is not None]

                        if len(values) >= 3:
                            data[metric_type] = {
                                'values': values,
                                'timestamps': timestamps
                            }
                except Exception as e:
                    logger.warning(f"Failed to get {metric_type} data: {str(e)}")
                    continue

            if not data:
                return {
                    "success": False,
                    "error": "No sufficient data found for trend analysis",
                    "insight": "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."
                }

            # Perform trend analysis
            results = self.analyze_trends(data)

            if 'error' in results:
                return {
                    "success": False,
                    "error": results['error'],
                    "insight": "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."
                }

            # Generate insight from results
            insight = self._generate_trend_insight(results, query_text)

            return {
                "success": True,
                "results": results,
                "insight": insight
            }

        except Exception as e:
            logger.error(f"Trend compute failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "insight": "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."
            }

    @cache_statistical_analysis(expire_seconds=1800)
    def analyze_trends(self, data: Dict, methods: Optional[List[str]] = None,
                      include_forecasting: bool = True) -> Dict:
        """
        Comprehensive trend analysis for time series data

        Args:
            data: Dictionary with metric_type -> {'values': array, 'timestamps': array}
            methods: List of trend analysis methods to use
            include_forecasting: Whether to include trend forecasting

        Returns:
            Dictionary with trend analysis results
        """
        try:
            if methods is None:
                methods = ['linear_regression', 'mann_kendall', 'seasonal_decomposition']
                if RUPTURES_AVAILABLE:
                    methods.append('change_point_detection')

            results = {
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'methods_used': methods,
                'trend_analysis': {},
                'overall_trends': {},
                'significant_trends': []
            }

            # Analyze trends for each metric
            for metric_type, metric_data in data.items():
                try:
                    metric_results = self._analyze_metric_trends(
                        metric_data, metric_type, methods, include_forecasting
                    )

                    if 'error' not in metric_results:
                        results['trend_analysis'][metric_type] = metric_results

                        # Extract overall trend summary
                        overall_trend = self._summarize_metric_trend(metric_results)
                        results['overall_trends'][metric_type] = overall_trend

                        # Check for significant trends
                        if self._is_significant_trend(metric_results):
                            results['significant_trends'].append({
                                'metric': metric_type,
                                'trend_direction': overall_trend['direction'],
                                'strength': overall_trend['strength'],
                                'confidence': overall_trend['confidence']
                            })
                    else:
                        logger.warning(f"Trend analysis failed for {metric_type}: {metric_results['error']}")

                except Exception as e:
                    logger.error(f"Failed to analyze trends for {metric_type}: {str(e)}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Trend analysis failed: {str(e)}")
            return {'error': str(e)}

    def _analyze_metric_trends(self, metric_data: Dict, metric_type: str,
                             methods: List[str], include_forecasting: bool) -> Dict:
        """Analyze trends for a specific metric"""
        try:
            values = np.array(metric_data['values'])
            timestamps = pd.to_datetime(metric_data['timestamps'])

            # Remove NaN values
            valid_mask = ~np.isnan(values)
            clean_values = values[valid_mask]
            clean_timestamps = timestamps[valid_mask]

            if len(clean_values) < self.min_sample_size:
                return {'error': f'Insufficient data: {len(clean_values)} points (minimum: {self.min_sample_size})'}

            # Prepare time series
            time_series = pd.Series(clean_values, index=clean_timestamps)
            time_series = time_series.sort_index()

            metric_results = {
                'metric_type': metric_type,
                'sample_size': len(clean_values),
                'time_range': {
                    'start': clean_timestamps.min().isoformat(),
                    'end': clean_timestamps.max().isoformat(),
                    'duration_days': (clean_timestamps.max() - clean_timestamps.min()).days
                },
                'data_quality': {
                    'completeness': len(clean_values) / len(values),
                    'temporal_consistency': self._calculate_temporal_consistency(clean_timestamps)
                }
            }

            # Run each trend analysis method
            for method in methods:
                if method in self.trend_methods:
                    try:
                        method_result = self.trend_methods[method](time_series, clean_values, clean_timestamps)
                        metric_results[method] = method_result
                    except Exception as e:
                        logger.warning(f"Method {method} failed for {metric_type}: {str(e)}")
                        metric_results[method] = {'error': str(e)}

            # Add forecasting if requested
            if include_forecasting:
                forecast_result = self._generate_trend_forecast(time_series)
                metric_results['forecasting'] = forecast_result

            return metric_results

        except Exception as e:
            logger.error(f"Metric trend analysis failed: {str(e)}")
            return {'error': str(e)}

    def _linear_trend_analysis(self, time_series: pd.Series, values: np.ndarray,
                             timestamps: pd.DatetimeIndex) -> Dict:
        """Linear regression trend analysis"""
        try:
            # Convert timestamps to days from start
            start_time = timestamps.min()
            days_elapsed = (timestamps - start_time).total_seconds() / 86400

            # Linear regression
            slope, intercept, r_value, p_value, std_err = linregress(days_elapsed, values)

            # Confidence interval for slope
            n = len(values)
            t_val = stats.t.ppf(0.975, n-2)  # 95% confidence
            slope_ci = t_val * std_err

            # Trend direction and strength
            trend_direction = self._classify_trend_direction(slope, p_value)
            trend_strength = self._classify_trend_strength(abs(r_value))

            return {
                'slope': float(slope),
                'slope_per_day': float(slope),
                'slope_per_week': float(slope * 7),
                'slope_per_month': float(slope * 30),
                'intercept': float(intercept),
                'r_value': float(r_value),
                'r_squared': float(r_value**2),
                'p_value': float(p_value),
                'standard_error': float(std_err),
                'slope_confidence_interval': {
                    'lower': float(slope - slope_ci),
                    'upper': float(slope + slope_ci)
                },
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'is_significant': p_value < self.significance_level,
                'method': 'linear_regression'
            }

        except Exception as e:
            return {'error': str(e)}

    def _mann_kendall_trend(self, time_series: pd.Series, values: np.ndarray,
                           timestamps: pd.DatetimeIndex) -> Dict:
        """Mann-Kendall trend test (non-parametric)"""
        try:
            # Use Kendall's tau as proxy for Mann-Kendall
            n = len(values)
            time_indices = np.arange(n)

            tau, p_value = kendalltau(time_indices, values)

            # Trend direction
            if p_value < self.significance_level:
                if tau > 0:
                    trend_direction = 'increasing'
                elif tau < 0:
                    trend_direction = 'decreasing'
                else:
                    trend_direction = 'no_trend'
            else:
                trend_direction = 'no_significant_trend'

            # Trend strength based on tau magnitude
            trend_strength = self._classify_trend_strength(abs(tau))

            return {
                'kendall_tau': float(tau),
                'p_value': float(p_value),
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'is_significant': p_value < self.significance_level,
                'sample_size': n,
                'method': 'mann_kendall'
            }

        except Exception as e:
            return {'error': str(e)}

    def _seasonal_trend_analysis(self, time_series: pd.Series, values: np.ndarray,
                                timestamps: pd.DatetimeIndex) -> Dict:
        """Seasonal decomposition trend analysis"""
        try:
            # Determine appropriate period
            duration_days = (timestamps.max() - timestamps.min()).days

            if duration_days >= 14:
                period = 7  # Weekly seasonality
            elif duration_days >= 6:
                period = min(3, len(values) // 3)
            else:
                return {'error': 'Insufficient data for seasonal decomposition'}

            if len(time_series) < 2 * period:
                return {'error': f'Insufficient data for period {period}: need at least {2 * period} points'}

            # Resample to regular intervals if needed
            if len(time_series) > period * 2:
                # Create regular time grid
                freq = self._determine_frequency(time_series)
                regular_series = time_series.resample(freq).mean().fillna(method='ffill').fillna(method='bfill')
            else:
                regular_series = time_series

            # Seasonal decomposition
            try:
                decomposition = seasonal_decompose(
                    regular_series,
                    model='additive',
                    period=period,
                    extrapolate_trend='freq'
                )

                # Extract trend component
                trend_component = decomposition.trend.dropna()

                if len(trend_component) < 3:
                    return {'error': 'Insufficient trend data from decomposition'}

                # Analyze trend component
                trend_values = trend_component.values
                trend_times = np.arange(len(trend_values))

                slope, intercept, r_value, p_value, std_err = linregress(trend_times, trend_values)

                # Seasonal strength
                seasonal_component = decomposition.seasonal
                seasonal_strength = np.std(seasonal_component) / np.std(regular_series) if np.std(regular_series) > 0 else 0

                return {
                    'trend_slope': float(slope),
                    'trend_r_squared': float(r_value**2),
                    'trend_p_value': float(p_value),
                    'seasonal_strength': float(seasonal_strength),
                    'period_used': period,
                    'trend_direction': self._classify_trend_direction(slope, p_value),
                    'has_seasonality': seasonal_strength > 0.1,
                    'decomposition_success': True,
                    'method': 'seasonal_decomposition'
                }

            except Exception as decomp_error:
                # Fallback to simple moving average trend
                window = min(period, len(regular_series) // 3)
                if window >= 2:
                    moving_avg = regular_series.rolling(window=window, center=True).mean()
                    trend_component = moving_avg.dropna()

                    if len(trend_component) >= 3:
                        trend_values = trend_component.values
                        trend_times = np.arange(len(trend_values))
                        slope, _, r_value, p_value, _ = linregress(trend_times, trend_values)

                        return {
                            'trend_slope': float(slope),
                            'trend_r_squared': float(r_value**2),
                            'trend_p_value': float(p_value),
                            'trend_direction': self._classify_trend_direction(slope, p_value),
                            'method': 'moving_average_fallback',
                            'window_size': window,
                            'decomposition_success': False,
                            'fallback_reason': str(decomp_error)
                        }

                return {'error': f'Seasonal decomposition failed: {str(decomp_error)}'}

        except Exception as e:
            return {'error': str(e)}

    def _change_point_detection(self, time_series: pd.Series, values: np.ndarray,
                               timestamps: pd.DatetimeIndex) -> Dict:
        """Change point detection analysis"""
        try:
            if not RUPTURES_AVAILABLE:
                return {'error': 'ruptures package not available'}

            # Use Binary Segmentation for change point detection
            model = rpt.Binseg(model="rbf").fit(values)

            # Detect change points
            penalty = max(1, len(values) * 0.05)  # Adaptive penalty
            change_points = model.predict(pen=penalty)

            # Remove the last point (end of series)
            if change_points and change_points[-1] == len(values):
                change_points = change_points[:-1]

            change_point_results = {
                'change_points_detected': len(change_points),
                'change_point_indices': change_points,
                'change_point_timestamps': [],
                'segment_trends': [],
                'method': 'change_point_detection'
            }

            # Convert indices to timestamps
            for cp_idx in change_points:
                if cp_idx < len(timestamps):
                    change_point_results['change_point_timestamps'].append(
                        timestamps[cp_idx].isoformat()
                    )

            # Analyze trends in each segment
            segments = [0] + change_points + [len(values)]

            for i in range(len(segments) - 1):
                start_idx = segments[i]
                end_idx = segments[i + 1]

                if end_idx - start_idx >= 3:  # Minimum segment size
                    segment_values = values[start_idx:end_idx]
                    segment_times = np.arange(len(segment_values))

                    slope, _, r_value, p_value, _ = linregress(segment_times, segment_values)

                    change_point_results['segment_trends'].append({
                        'segment': i + 1,
                        'start_index': start_idx,
                        'end_index': end_idx,
                        'slope': float(slope),
                        'r_squared': float(r_value**2),
                        'p_value': float(p_value),
                        'trend_direction': self._classify_trend_direction(slope, p_value)
                    })

            return change_point_results

        except Exception as e:
            return {'error': str(e)}

    def _autocorrelation_analysis(self, time_series: pd.Series, values: np.ndarray,
                                 timestamps: pd.DatetimeIndex) -> Dict:
        """Autocorrelation analysis for trend patterns"""
        try:
            # Calculate autocorrelation function
            max_lags = min(20, len(values) // 4)

            if max_lags < 2:
                return {'error': 'Insufficient data for autocorrelation analysis'}

            autocorrelations = acf(values, nlags=max_lags, fft=True)

            # Calculate partial autocorrelation
            partial_autocorr = pacf(values, nlags=max_lags)

            # Find significant lags
            n = len(values)
            confidence_bound = 1.96 / np.sqrt(n)  # 95% confidence

            significant_lags = []
            for lag in range(1, len(autocorrelations)):
                if abs(autocorrelations[lag]) > confidence_bound:
                    significant_lags.append({
                        'lag': lag,
                        'autocorrelation': float(autocorrelations[lag]),
                        'is_significant': True
                    })

            # Trend persistence measure
            trend_persistence = np.mean([abs(autocorrelations[i]) for i in range(1, min(6, len(autocorrelations)))])

            return {
                'autocorrelations': autocorrelations.tolist(),
                'partial_autocorrelations': partial_autocorr.tolist(),
                'significant_lags': significant_lags,
                'trend_persistence': float(trend_persistence),
                'confidence_bound': float(confidence_bound),
                'max_autocorr_lag': int(np.argmax(np.abs(autocorrelations[1:]))) + 1,
                'max_autocorr_value': float(np.max(np.abs(autocorrelations[1:]))),
                'method': 'autocorrelation'
            }

        except Exception as e:
            return {'error': str(e)}

    def _generate_trend_forecast(self, time_series: pd.Series, periods: int = 7) -> Dict:
        """Generate trend-based forecast"""
        try:
            if len(time_series) < 10:
                return {'error': 'Insufficient data for forecasting'}

            # Simple linear extrapolation
            values = time_series.values
            time_indices = np.arange(len(values))

            # Fit linear trend
            slope, intercept, r_value, p_value, std_err = linregress(time_indices, values)

            # Generate forecast points
            future_indices = np.arange(len(values), len(values) + periods)
            forecast_values = slope * future_indices + intercept

            # Calculate prediction intervals
            residuals = values - (slope * time_indices + intercept)
            residual_std = np.std(residuals)

            # 95% prediction interval
            t_val = stats.t.ppf(0.975, len(values) - 2)
            prediction_interval = t_val * residual_std * np.sqrt(1 + 1/len(values))

            return {
                'forecast_values': forecast_values.tolist(),
                'forecast_periods': periods,
                'trend_slope': float(slope),
                'trend_r_squared': float(r_value**2),
                'prediction_interval': float(prediction_interval),
                'forecast_bounds': {
                    'lower': (forecast_values - prediction_interval).tolist(),
                    'upper': (forecast_values + prediction_interval).tolist()
                },
                'forecast_confidence': float(r_value**2),
                'method': 'linear_extrapolation'
            }

        except Exception as e:
            return {'error': str(e)}

    def _calculate_temporal_consistency(self, timestamps: pd.DatetimeIndex) -> float:
        """Calculate temporal consistency of data collection"""
        try:
            if len(timestamps) < 2:
                return 1.0

            # Calculate time differences in hours
            time_diffs = np.diff(timestamps).astype('timedelta64[h]').astype(float)

            if len(time_diffs) == 0:
                return 1.0

            # Coefficient of variation (lower = more consistent)
            mean_diff = np.mean(time_diffs)
            std_diff = np.std(time_diffs)

            if mean_diff == 0:
                return 1.0

            cv = std_diff / mean_diff
            consistency_score = max(0.0, 1.0 - cv / 2.0)  # Normalize

            return float(consistency_score)

        except Exception:
            return 0.5

    def _determine_frequency(self, time_series: pd.Series) -> str:
        """Determine appropriate resampling frequency"""
        try:
            time_diff = time_series.index.to_series().diff().median()
            hours = time_diff.total_seconds() / 3600

            if hours <= 1:
                return 'H'  # Hourly
            elif hours <= 6:
                return '6H'  # 6-hourly
            elif hours <= 12:
                return '12H'  # 12-hourly
            else:
                return 'D'  # Daily

        except Exception:
            return 'D'  # Default to daily

    def _classify_trend_direction(self, slope: float, p_value: float) -> str:
        """Classify trend direction based on slope and significance"""
        if p_value >= self.significance_level:
            return 'no_significant_trend'

        if slope > 0:
            return 'increasing'
        elif slope < 0:
            return 'decreasing'
        else:
            return 'stable'

    def _classify_trend_strength(self, magnitude: float) -> str:
        """Classify trend strength based on correlation or tau magnitude"""
        if magnitude >= 0.7:
            return 'very_strong'
        elif magnitude >= 0.5:
            return 'strong'
        elif magnitude >= 0.3:
            return 'moderate'
        elif magnitude >= 0.1:
            return 'weak'
        else:
            return 'negligible'

    def _summarize_metric_trend(self, metric_results: Dict) -> Dict:
        """Summarize overall trend for a metric"""
        try:
            # Priority order for trend methods
            method_priority = ['linear_regression', 'mann_kendall', 'seasonal_decomposition']

            primary_result = None
            for method in method_priority:
                if method in metric_results and 'error' not in metric_results[method]:
                    primary_result = metric_results[method]
                    break

            if not primary_result:
                return {'direction': 'unknown', 'strength': 'unknown', 'confidence': 0.0}

            # Extract trend information
            if 'trend_direction' in primary_result:
                direction = primary_result['trend_direction']
            else:
                direction = 'unknown'

            if 'trend_strength' in primary_result:
                strength = primary_result['trend_strength']
            elif 'r_squared' in primary_result:
                strength = self._classify_trend_strength(np.sqrt(primary_result['r_squared']))
            else:
                strength = 'unknown'

            # Calculate confidence
            if 'p_value' in primary_result:
                confidence = 1.0 - primary_result['p_value']
            elif 'r_squared' in primary_result:
                confidence = primary_result['r_squared']
            else:
                confidence = 0.5

            return {
                'direction': direction,
                'strength': strength,
                'confidence': float(confidence),
                'primary_method': primary_result.get('method', 'unknown')
            }

        except Exception as e:
            logger.warning(f"Trend summary failed: {str(e)}")
            return {'direction': 'unknown', 'strength': 'unknown', 'confidence': 0.0}

    def _is_significant_trend(self, metric_results: Dict) -> bool:
        """Check if metric has statistically significant trend"""
        try:
            # Check linear regression
            if 'linear_regression' in metric_results:
                lr_result = metric_results['linear_regression']
                if 'error' not in lr_result and lr_result.get('is_significant', False):
                    return True

            # Check Mann-Kendall
            if 'mann_kendall' in metric_results:
                mk_result = metric_results['mann_kendall']
                if 'error' not in mk_result and mk_result.get('is_significant', False):
                    return True

            return False

        except Exception:
            return False

    def _generate_trend_insight(self, results: Dict, query_text: str) -> str:
        """Generate human-readable insight from trend analysis results"""
        try:
            significant_trends = results.get('significant_trends', [])
            overall_trends = results.get('overall_trends', {})

            if not significant_trends:
                return "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."

            insights = []
            for trend in significant_trends:
                metric = trend['metric']
                direction = trend['direction']
                strength = trend['strength']
                confidence = trend.get('confidence', 0)

                if direction == 'increasing':
                    trend_desc = f"{metric.replace('_', ' ').title()} is trending upward"
                elif direction == 'decreasing':
                    trend_desc = f"{metric.replace('_', ' ').title()} is trending downward"
                else:
                    trend_desc = f"{metric.replace('_', ' ').title()} shows no clear trend"

                if strength in ['strong', 'very_strong'] and confidence > 0.7:
                    trend_desc += f" with {strength} confidence"

                insights.append(trend_desc)

            if insights:
                base_insight = ". ".join(insights) + "."

                # Add contextual advice based on query
                if 'improving' in query_text.lower() or 'better' in query_text.lower():
                    if any('upward' in insight for insight in insights):
                        base_insight += " This indicates positive improvement."
                    else:
                        base_insight += " Consider reviewing your habits for potential improvements."

                return base_insight
            else:
                return "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."

        except Exception as e:
            logger.warning(f"Failed to generate trend insight: {str(e)}")
            return "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."