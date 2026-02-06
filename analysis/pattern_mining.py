"""
Advanced pattern mining algorithms for health data analysis
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
import logging
from collections import defaultdict, Counter
from itertools import combinations
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from scipy import stats

try:
    from mlxtend.frequent_patterns import apriori, association_rules
    from mlxtend.preprocessing import TransactionEncoder
    MLXTEND_AVAILABLE = True
except ImportError:
    MLXTEND_AVAILABLE = False
    logging.warning("mlxtend not available - frequent pattern mining will be limited")

try:
    from dtaidistance import dtw
    DTW_AVAILABLE = True
except ImportError:
    DTW_AVAILABLE = False
    logging.warning("dtaidistance not available - DTW analysis will be skipped")

from utils.cache import cache_statistical_analysis
from utils.stats_utils import StatisticalValidator

logger = logging.getLogger(__name__)

class PatternMiner:
    """Advanced pattern mining for health data sequences and associations"""

    def __init__(self):
        self.min_support = 0.1  # Minimum support for frequent patterns
        self.min_confidence = 0.6  # Minimum confidence for association rules
        self.min_pattern_length = 2
        self.max_pattern_length = 5

    @cache_statistical_analysis(expire_seconds=3600)
    def discover_patterns(self, user_data: Dict, pattern_types: Optional[List[str]] = None) -> Dict:
        """
        Discover patterns in user health data

        Args:
            user_data: Dictionary with metric_type -> {'values': array, 'timestamps': array}
            pattern_types: List of pattern types to discover

        Returns:
            Dictionary with discovered patterns
        """
        try:
            if pattern_types is None:
                pattern_types = ['temporal', 'sequential', 'associative', 'behavioral']

            pattern_results = {
                'discovery_timestamp': datetime.utcnow().isoformat(),
                'data_summary': self._summarize_input_data(user_data),
                'patterns_discovered': {},
                'pattern_confidence': {},
                'actionable_insights': []
            }

            # Convert data to suitable formats
            processed_data = self._preprocess_data_for_mining(user_data)

            if not processed_data:
                return {'error': 'Insufficient data for pattern mining'}

            # Discover different types of patterns
            for pattern_type in pattern_types:
                try:
                    if pattern_type == 'temporal':
                        patterns = self._discover_temporal_patterns(processed_data)
                    elif pattern_type == 'sequential':
                        patterns = self._discover_sequential_patterns(processed_data)
                    elif pattern_type == 'associative':
                        patterns = self._discover_associative_patterns(processed_data)
                    elif pattern_type == 'behavioral':
                        patterns = self._discover_behavioral_patterns(processed_data)
                    else:
                        continue

                    if patterns and 'error' not in patterns:
                        pattern_results['patterns_discovered'][pattern_type] = patterns

                        # Calculate confidence for discovered patterns
                        confidence = self._calculate_pattern_confidence(patterns, processed_data)
                        pattern_results['pattern_confidence'][pattern_type] = confidence

                except Exception as e:
                    logger.warning(f"Pattern discovery failed for {pattern_type}: {str(e)}")
                    continue

            # Generate actionable insights
            pattern_results['actionable_insights'] = self._generate_actionable_insights(
                pattern_results['patterns_discovered']
            )

            return pattern_results

        except Exception as e:
            logger.error(f"Pattern discovery failed: {str(e)}")
            return {'error': str(e)}

    def _summarize_input_data(self, user_data: Dict) -> Dict:
        """Summarize input data for pattern mining"""
        try:
            summary = {
                'total_metrics': len(user_data),
                'metrics_list': list(user_data.keys()),
                'total_data_points': 0,
                'time_span_days': 0
            }

            all_timestamps = []
            for metric_type, data in user_data.items():
                if 'values' in data:
                    summary['total_data_points'] += len(data['values'])
                if 'timestamps' in data:
                    all_timestamps.extend(data['timestamps'])

            if all_timestamps:
                min_time = min(all_timestamps)
                max_time = max(all_timestamps)
                summary['time_span_days'] = (max_time - min_time).days

            return summary

        except Exception as e:
            logger.warning(f"Data summary failed: {str(e)}")
            return {}

    def _preprocess_data_for_mining(self, user_data: Dict) -> Optional[Dict]:
        """Preprocess data for pattern mining"""
        try:
            if not user_data:
                return None

            processed = {
                'time_series': {},
                'events': [],
                'metrics_matrix': [],
                'timestamps': [],
                'metric_names': []
            }

            # Align time series data
            all_timestamps = []
            for metric_type, data in user_data.items():
                if 'timestamps' in data:
                    all_timestamps.extend(data['timestamps'])

            if not all_timestamps:
                return None

            # Create common time grid (hourly)
            min_time = min(all_timestamps)
            max_time = max(all_timestamps)
            time_grid = pd.date_range(start=min_time, end=max_time, freq='h')

            # Align each metric to time grid
            aligned_data = {}
            for metric_type, data in user_data.items():
                if 'values' not in data or 'timestamps' not in data:
                    continue

                values = np.array(data['values'])
                timestamps = pd.to_datetime(data['timestamps'])

                # Create time series and resample
                series = pd.Series(values, index=timestamps)
                resampled = series.resample('h').mean()
                aligned = resampled.reindex(time_grid)

                # Forward fill missing values
                aligned = aligned.ffill().bfill()
                aligned_data[metric_type] = aligned.values

            if not aligned_data:
                return None

            # Create metrics matrix
            metric_names = list(aligned_data.keys())
            metrics_matrix = np.array([aligned_data[metric] for metric in metric_names]).T

            # Remove rows with any NaN values
            valid_mask = ~np.any(np.isnan(metrics_matrix), axis=1)
            metrics_matrix = metrics_matrix[valid_mask]
            valid_timestamps = time_grid[valid_mask]

            if len(metrics_matrix) < 10:
                return None

            processed.update({
                'time_series': aligned_data,
                'metrics_matrix': metrics_matrix,
                'timestamps': valid_timestamps,
                'metric_names': metric_names
            })

            return processed

        except Exception as e:
            logger.error(f"Data preprocessing failed: {str(e)}")
            return None

    def _discover_temporal_patterns(self, processed_data: Dict) -> Dict:
        """Discover temporal patterns (circadian, weekly, etc.)"""
        try:
            temporal_patterns = {
                'circadian_patterns': {},
                'weekly_patterns': {}
            }

            timestamps = processed_data['timestamps']
            metrics_matrix = processed_data['metrics_matrix']
            metric_names = processed_data['metric_names']

            for i, metric_name in enumerate(metric_names):
                metric_values = metrics_matrix[:, i]

                # Circadian patterns (24-hour cycle)
                hourly_data = pd.DataFrame({
                    'hour': timestamps.hour,
                    'value': metric_values
                })
                hourly_pattern = hourly_data.groupby('hour')['value'].agg(['mean', 'std', 'count'])

                # Find peak and trough hours
                peak_hour = hourly_pattern['mean'].idxmax()
                trough_hour = hourly_pattern['mean'].idxmin()

                temporal_patterns['circadian_patterns'][metric_name] = {
                    'hourly_means': hourly_pattern['mean'].to_dict(),
                    'peak_hour': int(peak_hour),
                    'trough_hour': int(trough_hour),
                    'amplitude': float(hourly_pattern['mean'].max() - hourly_pattern['mean'].min()),
                    'consistency_score': self._calculate_pattern_consistency(hourly_pattern['std'].values)
                }

                # Weekly patterns
                weekly_data = pd.DataFrame({
                    'dow': timestamps.dayofweek,  # 0=Monday, 6=Sunday
                    'value': metric_values
                })
                weekly_pattern = weekly_data.groupby('dow')['value'].agg(['mean', 'std', 'count'])

                temporal_patterns['weekly_patterns'][metric_name] = {
                    'daily_means': weekly_pattern['mean'].to_dict(),
                    'weekend_effect': self._calculate_weekend_effect(weekly_pattern['mean']),
                    'most_stable_day': int(weekly_pattern['std'].idxmin()),
                    'most_variable_day': int(weekly_pattern['std'].idxmax())
                }

            return temporal_patterns

        except Exception as e:
            logger.error(f"Temporal pattern discovery failed: {str(e)}")
            return {'error': str(e)}

    def _discover_sequential_patterns(self, processed_data: Dict) -> Dict:
        """Discover sequential patterns in metric changes"""
        try:
            sequential_patterns = {
                'change_patterns': {},
                'lead_lag_relationships': {}
            }

            metrics_matrix = processed_data['metrics_matrix']
            metric_names = processed_data['metric_names']

            # Find lead-lag relationships
            sequential_patterns['lead_lag_relationships'] = self._find_lead_lag_relationships(
                metrics_matrix, metric_names
            )

            return sequential_patterns

        except Exception as e:
            logger.error(f"Sequential pattern discovery failed: {str(e)}")
            return {'error': str(e)}

    def _discover_associative_patterns(self, processed_data: Dict) -> Dict:
        """Discover associative patterns between different metrics"""
        try:
            associative_patterns = {
                'metric_associations': {},
                'threshold_associations': {}
            }

            # Simplified implementation for now
            metrics_matrix = processed_data['metrics_matrix']
            metric_names = processed_data['metric_names']

            # Calculate correlations as basic associations
            for i, metric1 in enumerate(metric_names):
                for j, metric2 in enumerate(metric_names[i+1:], i+1):
                    corr_coef = np.corrcoef(metrics_matrix[:, i], metrics_matrix[:, j])[0, 1]

                    if abs(corr_coef) > 0.3:
                        pair_key = f"{metric1}_vs_{metric2}"
                        associative_patterns['metric_associations'][pair_key] = {
                            'correlation': float(corr_coef),
                            'strength': 'strong' if abs(corr_coef) > 0.7 else 'moderate'
                        }

            return associative_patterns

        except Exception as e:
            logger.error(f"Associative pattern discovery failed: {str(e)}")
            return {'error': str(e)}

    def _discover_behavioral_patterns(self, processed_data: Dict) -> Dict:
        """Discover behavioral patterns using clustering"""
        try:
            behavioral_patterns = {
                'behavioral_clusters': {}
            }

            metrics_matrix = processed_data['metrics_matrix']
            metric_names = processed_data['metric_names']
            timestamps = processed_data['timestamps']

            # Create daily profiles
            daily_data = []
            daily_timestamps = []

            # Group data by day
            df = pd.DataFrame(metrics_matrix, columns=metric_names, index=timestamps)
            daily_groups = df.groupby(df.index.date)

            for date, day_data in daily_groups:
                if len(day_data) >= 12:  # At least 12 hours of data
                    # Calculate daily statistics
                    daily_stats = []
                    for metric in metric_names:
                        daily_stats.extend([
                            day_data[metric].mean(),
                            day_data[metric].std(),
                            day_data[metric].max(),
                            day_data[metric].min()
                        ])

                    daily_data.append(daily_stats)
                    daily_timestamps.append(date)

            if len(daily_data) < 5:
                return {'error': 'Insufficient daily data for behavioral analysis'}

            daily_matrix = np.array(daily_data)

            # Standardize features
            scaler = StandardScaler()
            scaled_daily = scaler.fit_transform(daily_matrix)

            # Perform clustering
            optimal_clusters = self._find_optimal_clusters(scaled_daily)

            if optimal_clusters > 1:
                kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
                cluster_labels = kmeans.fit_predict(scaled_daily)

                behavioral_patterns['behavioral_clusters'] = {
                    'n_clusters': optimal_clusters,
                    'cluster_sizes': [int(np.sum(cluster_labels == i)) for i in range(optimal_clusters)]
                }

            return behavioral_patterns

        except Exception as e:
            logger.error(f"Behavioral pattern discovery failed: {str(e)}")
            return {'error': str(e)}

    def _find_lead_lag_relationships(self, metrics_matrix: np.ndarray,
                                   metric_names: List[str], max_lag: int = 12) -> Dict:
        """Find lead-lag relationships between metrics"""
        try:
            relationships = {}

            for i, metric1 in enumerate(metric_names):
                for j, metric2 in enumerate(metric_names[i+1:], i+1):
                    series1 = metrics_matrix[:, i]
                    series2 = metrics_matrix[:, j]

                    best_lag = 0
                    best_correlation = 0

                    # Test different lags
                    for lag in range(-max_lag, max_lag + 1):
                        if lag == 0:
                            continue

                        if lag > 0:
                            # series1 leads series2
                            if lag >= len(series1):
                                continue
                            corr_data1 = series1[:-lag]
                            corr_data2 = series2[lag:]
                        else:
                            # series2 leads series1
                            abs_lag = abs(lag)
                            if abs_lag >= len(series2):
                                continue
                            corr_data1 = series1[abs_lag:]
                            corr_data2 = series2[:-abs_lag]

                        if len(corr_data1) < 10:
                            continue

                        correlation = np.corrcoef(corr_data1, corr_data2)[0, 1]

                        if abs(correlation) > abs(best_correlation):
                            best_correlation = correlation
                            best_lag = lag

                    if abs(best_correlation) > 0.3:  # Significant correlation
                        pair_key = f"{metric1}_vs_{metric2}"
                        relationships[pair_key] = {
                            'correlation': float(best_correlation),
                            'optimal_lag_hours': best_lag,
                            'interpretation': self._interpret_lead_lag(metric1, metric2, best_lag, best_correlation)
                        }

            return relationships

        except Exception as e:
            logger.error(f"Lead-lag analysis failed: {str(e)}")
            return {}

    def _calculate_pattern_consistency(self, std_values: np.ndarray) -> float:
        """Calculate how consistent a pattern is"""
        try:
            if len(std_values) == 0:
                return 0.0

            # Lower standard deviation = higher consistency
            mean_std = np.mean(std_values)
            max_possible_std = np.max(std_values) if np.max(std_values) > 0 else 1

            consistency = 1.0 - (mean_std / max_possible_std)
            return float(max(0.0, min(1.0, consistency)))

        except Exception:
            return 0.5

    def _calculate_weekend_effect(self, daily_means: pd.Series) -> Dict:
        """Calculate weekend vs weekday effect"""
        try:
            # Monday=0, Sunday=6
            weekday_mean = daily_means[[0, 1, 2, 3, 4]].mean()  # Mon-Fri
            weekend_mean = daily_means[[5, 6]].mean()  # Sat-Sun

            effect_size = weekend_mean - weekday_mean
            effect_percentage = (effect_size / weekday_mean) * 100 if weekday_mean != 0 else 0

            return {
                'weekday_mean': float(weekday_mean),
                'weekend_mean': float(weekend_mean),
                'effect_size': float(effect_size),
                'effect_percentage': float(effect_percentage),
                'pattern': 'weekend_higher' if effect_size > 0 else 'weekend_lower' if effect_size < 0 else 'no_effect'
            }

        except Exception:
            return {'pattern': 'unknown'}

    def _find_optimal_clusters(self, data: np.ndarray, max_clusters: int = 8) -> int:
        """Find optimal number of clusters using elbow method"""
        try:
            if len(data) < 4:
                return 1

            max_clusters = min(max_clusters, len(data) // 2)
            inertias = []

            for k in range(1, max_clusters + 1):
                kmeans = KMeans(n_clusters=k, random_state=42)
                kmeans.fit(data)
                inertias.append(kmeans.inertia_)

            # Find elbow point
            if len(inertias) < 3:
                return 2

            # Calculate rate of change
            changes = [inertias[i-1] - inertias[i] for i in range(1, len(inertias))]

            # Find the point where the rate of change decreases significantly
            for i in range(1, len(changes)):
                if changes[i] < changes[i-1] * 0.5:  # 50% decrease in improvement
                    return i + 1

            return min(3, max_clusters)

        except Exception:
            return 2

    def _interpret_lead_lag(self, metric1: str, metric2: str, lag: int, correlation: float) -> str:
        """Interpret lead-lag relationship"""
        try:
            direction = "positive" if correlation > 0 else "negative"
            strength = "strong" if abs(correlation) > 0.6 else "moderate"

            if lag > 0:
                return f"{strength} {direction} relationship: {metric1} leads {metric2} by {lag} hours"
            else:
                return f"{strength} {direction} relationship: {metric2} leads {metric1} by {abs(lag)} hours"

        except Exception:
            return "Unknown relationship"

    def _calculate_pattern_confidence(self, patterns: Dict, processed_data: Dict) -> float:
        """Calculate confidence score for discovered patterns"""
        try:
            confidence_factors = []

            # Sample size factor
            sample_size = len(processed_data.get('metrics_matrix', []))
            size_factor = min(1.0, sample_size / 100)  # 100 samples = full confidence
            confidence_factors.append(size_factor)

            # Pattern consistency factor
            if 'circadian_patterns' in patterns:
                consistency_scores = []
                for metric_data in patterns['circadian_patterns'].values():
                    consistency_scores.append(metric_data.get('consistency_score', 0.5))

                if consistency_scores:
                    avg_consistency = np.mean(consistency_scores)
                    confidence_factors.append(avg_consistency)

            overall_confidence = np.mean(confidence_factors) if confidence_factors else 0.5
            return float(overall_confidence)

        except Exception:
            return 0.5

    def _generate_actionable_insights(self, patterns: Dict) -> List[Dict]:
        """Generate actionable insights from discovered patterns"""
        try:
            insights = []

            # Temporal pattern insights
            if 'temporal' in patterns:
                temporal = patterns['temporal']

                if 'circadian_patterns' in temporal:
                    for metric, pattern_data in temporal['circadian_patterns'].items():
                        peak_hour = pattern_data.get('peak_hour')
                        trough_hour = pattern_data.get('trough_hour')

                        if peak_hour is not None and trough_hour is not None:
                            insights.append({
                                'type': 'circadian_optimization',
                                'metric': metric,
                                'insight': f"{metric} peaks at {peak_hour}:00 and is lowest at {trough_hour}:00",
                                'recommendation': f"Schedule activities around {metric} patterns for optimization"
                            })

            return insights

        except Exception as e:
            logger.error(f"Insight generation failed: {str(e)}")
            return []