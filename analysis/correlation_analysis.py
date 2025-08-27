"""
Advanced correlation analysis for discovering relationships between health metrics
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau
from scipy.signal import correlate
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional, Union
import logging
from itertools import combinations

try:
    from minepy import MINE
    MINEPY_AVAILABLE = True
except ImportError:
    MINEPY_AVAILABLE = False
    logging.warning("minepy not available - MIC analysis will be skipped")

from utils.stats_utils import StatisticalValidator, ConfidenceIntervals
from utils.cache import cache_statistical_analysis

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """Advanced correlation analysis using multiple statistical methods"""

    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.min_sample_size = 10
        self.correlation_methods = {
            'pearson': self._pearson_correlation,
            'spearman': self._spearman_correlation,
            'kendall': self._kendall_correlation,
            'mutual_information': self._mutual_information,
            'cross_correlation': self._cross_correlation
        }

        if MINEPY_AVAILABLE:
            self.correlation_methods['mic'] = self._mic_correlation

    @cache_statistical_analysis(expire_seconds=3600)
    def analyze_correlations(self, data: Dict, methods: Optional[List[str]] = None,
                           include_lagged: bool = True, max_lag: int = 24) -> Dict:
        """
        Comprehensive correlation analysis between all metric pairs

        Args:
            data: Dictionary with metric_type -> {'values': array, 'timestamps': array}
            methods: List of correlation methods to use
            include_lagged: Whether to include time-lagged correlations
            max_lag: Maximum lag in hours for cross-correlation

        Returns:
            Dictionary with correlation results
        """
        try:
            if methods is None:
                methods = ['pearson', 'spearman', 'kendall', 'mutual_information']
                if MINEPY_AVAILABLE:
                    methods.append('mic')

            # Prepare data matrix
            aligned_data = self._align_time_series(data)

            if not aligned_data or len(aligned_data['timestamps']) < self.min_sample_size:
                return {'error': 'Insufficient aligned data for correlation analysis'}

            metric_names = list(aligned_data['metrics'].keys())

            # Initialize results
            results = {
                'data_summary': {
                    'metric_types': metric_names,
                    'sample_size': len(aligned_data['timestamps']),
                    'time_range': {
                        'start': aligned_data['timestamps'][0].isoformat(),
                        'end': aligned_data['timestamps'][-1].isoformat()
                    }
                },
                'pairwise_correlations': {},
                'correlation_matrix': {},
                'significant_relationships': [],
                'network_analysis': {}
            }

            if include_lagged:
                results['lagged_correlations'] = {}

            # Analyze all metric pairs
            for i, metric1 in enumerate(metric_names):
                for j, metric2 in enumerate(metric_names[i+1:], i+1):
                    pair_key = f"{metric1}_vs_{metric2}"

                    # Get data for this pair
                    data1 = aligned_data['metrics'][metric1]
                    data2 = aligned_data['metrics'][metric2]

                    # Run correlation analysis
                    pair_results = self._analyze_metric_pair(
                        data1, data2, metric1, metric2, methods
                    )

                    results['pairwise_correlations'][pair_key] = pair_results

                    # Time-lagged analysis if requested
                    if include_lagged:
                        lag_results = self._analyze_lagged_correlation(
                            data1, data2, metric1, metric2, max_lag
                        )
                        results['lagged_correlations'][pair_key] = lag_results

                    # Check for significance
                    if self._is_significant_relationship(pair_results):
                        results['significant_relationships'].append({
                            'metric_pair': pair_key,
                            'primary_correlation': pair_results.get('pearson', {}),
                            'significance_level': self.significance_level,
                            'methods_significant': self._count_significant_methods(pair_results)
                        })

            # Create correlation matrices
            results['correlation_matrix'] = self._create_correlation_matrices(
                aligned_data, metric_names, methods
            )

            # Network analysis
            results['network_analysis'] = self._perform_network_analysis(
                results['pairwise_correlations'], metric_names
            )

            # Apply multiple testing correction
            results = self._apply_multiple_testing_correction(results)

            return results

        except Exception as e:
            logger.error(f"Correlation analysis failed: {str(e)}")
            return {'error': str(e)}

    def _align_time_series(self, data: Dict) -> Optional[Dict]:
        """Align time series data to common timestamps - FIXED VERSION"""
        try:
            if not data:
                return None

            # Find all unique timestamps across all metrics
            all_timestamps = set()
            for metric_type, metric_data in data.items():
                if 'timestamps' in metric_data and metric_data['timestamps']:
                    all_timestamps.update(metric_data['timestamps'])

            if not all_timestamps:
                logger.warning("No timestamps found in any metric data")
                return None

            # Sort timestamps
            sorted_timestamps = sorted(all_timestamps)

            # Instead of creating a rigid hourly grid, use actual data timestamps
            # and interpolate missing values more intelligently

            aligned_metrics = {}
            valid_data_count = {}

            for metric_type, metric_data in data.items():
                if 'values' not in metric_data or 'timestamps' not in metric_data:
                    continue

                values = np.array(metric_data['values'])
                timestamps = pd.to_datetime(metric_data['timestamps'])

                if len(values) == 0:
                    continue

                # Create time series
                series = pd.Series(values, index=timestamps)
                series = series.sort_index()

                # Remove duplicates, keeping last value
                series = series[~series.index.duplicated(keep='last')]

                # Reindex to common timestamps using nearest neighbor interpolation
                common_index = pd.to_datetime(sorted_timestamps)

                # Use reindex with method='nearest' and limit interpolation
                aligned_series = series.reindex(common_index, method='nearest', tolerance=pd.Timedelta('6H'))

                # Only keep data where we have reasonable interpolation
                aligned_metrics[metric_type] = aligned_series.values
                valid_data_count[metric_type] = (~np.isnan(aligned_series.values)).sum()

            if not aligned_metrics:
                logger.warning("No metrics could be aligned")
                return None

            # Find metrics with sufficient data (at least 10 points)
            sufficient_metrics = {
                metric: values for metric, values in aligned_metrics.items()
                if valid_data_count[metric] >= 10
            }

            if len(sufficient_metrics) < 2:
                logger.warning(f"Insufficient metrics for correlation: {len(sufficient_metrics)} metrics with enough data")
                return None

            # Find timestamps where we have data for at least 2 metrics
            min_metrics_threshold = 2
            valid_mask = np.zeros(len(sorted_timestamps), dtype=bool)

            for i in range(len(sorted_timestamps)):
                non_nan_count = sum(
                    1 for values in sufficient_metrics.values()
                    if i < len(values) and not np.isnan(values[i])
                )
                valid_mask[i] = non_nan_count >= min_metrics_threshold

            if not np.any(valid_mask):
                logger.warning("No timestamps with sufficient metric overlap found")
                return None

            # Filter to valid timestamps and metrics
            valid_timestamps = pd.to_datetime(sorted_timestamps)[valid_mask]

            final_metrics = {}
            for metric_type, values in sufficient_metrics.items():
                valid_values = values[valid_mask]
                # Final check - remove this metric if too many NaN values remain
                if (~np.isnan(valid_values)).sum() >= 5:  # At least 5 valid points
                    final_metrics[metric_type] = valid_values

            if len(final_metrics) < 2:
                logger.warning("Insufficient metrics remain after filtering")
                return None

            logger.info(f"Successfully aligned {len(final_metrics)} metrics with {len(valid_timestamps)} timestamps")

            return {
                'timestamps': valid_timestamps,
                'metrics': final_metrics
            }

        except Exception as e:
            logger.error(f"Time series alignment failed: {str(e)}")
            return None



    def _analyze_metric_pair(self, data1: np.ndarray, data2: np.ndarray,
                           metric1: str, metric2: str, methods: List[str]) -> Dict:
        """Analyze correlation between a pair of metrics"""
        try:
            # Validate data
            if len(data1) != len(data2) or len(data1) < self.min_sample_size:
                return {'error': 'Insufficient or mismatched data'}

            # Remove any remaining NaN values
            valid_mask = ~(np.isnan(data1) | np.isnan(data2))
            clean_data1 = data1[valid_mask]
            clean_data2 = data2[valid_mask]

            if len(clean_data1) < self.min_sample_size:
                return {'error': 'Insufficient clean data after NaN removal'}

            pair_results = {
                'sample_size': len(clean_data1),
                'data_quality': {
                    'valid_points': len(clean_data1),
                    'total_points': len(data1),
                    'completeness': len(clean_data1) / len(data1)
                }
            }

            # Run each correlation method
            for method in methods:
                if method in self.correlation_methods:
                    try:
                        method_result = self.correlation_methods[method](clean_data1, clean_data2)
                        pair_results[method] = method_result
                    except Exception as e:
                        logger.warning(f"Method {method} failed for {metric1} vs {metric2}: {str(e)}")
                        pair_results[method] = {'error': str(e)}

            return pair_results

        except Exception as e:
            logger.error(f"Metric pair analysis failed: {str(e)}")
            return {'error': str(e)}

    def _pearson_correlation(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """Calculate Pearson correlation with confidence intervals"""
        try:
            r, p_value = pearsonr(x, y)

            # Calculate confidence interval
            ci_lower, ci_upper = ConfidenceIntervals.correlation_ci(r, len(x))

            # Effect size interpretation
            effect_size = self._interpret_correlation_strength(abs(r))

            return {
                'correlation': float(r),
                'p_value': float(p_value),
                'significant': p_value < self.significance_level,
                'confidence_interval': {
                    'lower': float(ci_lower),
                    'upper': float(ci_upper),
                    'confidence_level': 0.95
                },
                'effect_size': effect_size,
                'sample_size': len(x)
            }

        except Exception as e:
            return {'error': str(e)}

    def _spearman_correlation(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """Calculate Spearman rank correlation"""
        try:
            rho, p_value = spearmanr(x, y)

            effect_size = self._interpret_correlation_strength(abs(rho))

            return {
                'correlation': float(rho),
                'p_value': float(p_value),
                'significant': p_value < self.significance_level,
                'effect_size': effect_size,
                'sample_size': len(x),
                'method': 'spearman_rank'
            }

        except Exception as e:
            return {'error': str(e)}

    def _kendall_correlation(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """Calculate Kendall's tau correlation"""
        try:
            tau, p_value = kendalltau(x, y)

            effect_size = self._interpret_correlation_strength(abs(tau))

            return {
                'correlation': float(tau),
                'p_value': float(p_value),
                'significant': p_value < self.significance_level,
                'effect_size': effect_size,
                'sample_size': len(x),
                'method': 'kendall_tau'
            }

        except Exception as e:
            return {'error': str(e)}

    def _mutual_information(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """Calculate mutual information (non-linear dependence)"""
        try:
            # Reshape for sklearn
            x_reshaped = x.reshape(-1, 1)

            # Calculate mutual information
            mi_score = mutual_info_regression(x_reshaped, y, random_state=42)[0]

            # Normalize MI score (approximate)
            normalized_mi = min(1.0, mi_score / (0.5 * (np.var(x) + np.var(y))))

            # No p-value for MI, use effect size interpretation
            effect_size = self._interpret_mi_strength(normalized_mi)

            return {
                'mutual_information': float(mi_score),
                'normalized_mi': float(normalized_mi),
                'effect_size': effect_size,
                'sample_size': len(x),
                'method': 'mutual_information'
            }

        except Exception as e:
            return {'error': str(e)}

    def _mic_correlation(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """Calculate Maximal Information Coefficient (if available)"""
        try:
            if not MINEPY_AVAILABLE:
                return {'error': 'minepy package not available'}

            mine = MINE()
            mine.compute_score(x, y)

            mic_score = mine.mic()
            effect_size = self._interpret_mi_strength(mic_score)

            return {
                'mic_score': float(mic_score),
                'effect_size': effect_size,
                'sample_size': len(x),
                'method': 'maximal_information_coefficient'
            }

        except Exception as e:
            return {'error': str(e)}

    def _cross_correlation(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """Calculate cross-correlation to find optimal lag"""
        try:
            # Standardize the signals
            x_std = (x - np.mean(x)) / (np.std(x) + 1e-8)
            y_std = (y - np.mean(y)) / (np.std(y) + 1e-8)

            # Calculate cross-correlation
            cross_corr = correlate(x_std, y_std, mode='full')

            # Calculate lags (in array indices)
            lags = np.arange(-len(y) + 1, len(x))

            # Find peak correlation and its lag
            max_corr_idx = np.argmax(np.abs(cross_corr))
            max_correlation = cross_corr[max_corr_idx]
            optimal_lag = lags[max_corr_idx]

            # Normalize correlation
            normalized_corr = max_correlation / len(x)

            return {
                'max_correlation': float(normalized_corr),
                'optimal_lag': int(optimal_lag),
                'lag_hours': int(optimal_lag),  # Assuming hourly data
                'effect_size': self._interpret_correlation_strength(abs(normalized_corr)),
                'sample_size': len(x),
                'method': 'cross_correlation'
            }

        except Exception as e:
            return {'error': str(e)}

    def _analyze_lagged_correlation(self, data1: np.ndarray, data2: np.ndarray,
                                  metric1: str, metric2: str, max_lag: int) -> Dict:
        """Analyze time-lagged correlations"""
        try:
            lag_results = {
                'max_lag_hours': max_lag,
                'correlations_by_lag': {},
                'optimal_lag': 0,
                'max_correlation': 0.0
            }

            # Test different lags
            for lag in range(-max_lag, max_lag + 1):
                try:
                    if lag == 0:
                        # No lag - standard correlation
                        x, y = data1, data2
                    elif lag > 0:
                        # Positive lag: data2 lagged behind data1
                        if lag >= len(data1):
                            continue
                        x, y = data1[:-lag], data2[lag:]
                    else:
                        # Negative lag: data1 lagged behind data2
                        abs_lag = abs(lag)
                        if abs_lag >= len(data2):
                            continue
                        x, y = data1[abs_lag:], data2[:-abs_lag]

                    if len(x) < self.min_sample_size:
                        continue

                    # Calculate Pearson correlation for this lag
                    r, p_value = pearsonr(x, y)

                    lag_results['correlations_by_lag'][lag] = {
                        'correlation': float(r),
                        'p_value': float(p_value),
                        'sample_size': len(x),
                        'significant': p_value < self.significance_level
                    }

                    # Track maximum correlation
                    if abs(r) > abs(lag_results['max_correlation']):
                        lag_results['max_correlation'] = float(r)
                        lag_results['optimal_lag'] = lag

                except Exception as e:
                    logger.warning(f"Lag {lag} analysis failed: {str(e)}")
                    continue

            # Interpretation of optimal lag
            if lag_results['optimal_lag'] != 0:
                if lag_results['optimal_lag'] > 0:
                    lag_results['interpretation'] = f"{metric2} follows {metric1} by {lag_results['optimal_lag']} hours"
                else:
                    lag_results['interpretation'] = f"{metric1} follows {metric2} by {abs(lag_results['optimal_lag'])} hours"
            else:
                lag_results['interpretation'] = f"{metric1} and {metric2} are synchronized"

            return lag_results

        except Exception as e:
            logger.error(f"Lagged correlation analysis failed: {str(e)}")
            return {'error': str(e)}

    def _create_correlation_matrices(self, aligned_data: Dict, metric_names: List[str],
                                   methods: List[str]) -> Dict:
        """Create correlation matrices for different methods"""
        try:
            matrices = {}
            n_metrics = len(metric_names)

            for method in methods:
                if method == 'cross_correlation':
                    continue  # Skip cross-correlation for matrix

                # Initialize matrix
                correlation_matrix = np.eye(n_metrics)  # Identity matrix
                p_value_matrix = np.zeros((n_metrics, n_metrics))

                # Fill upper triangle
                for i in range(n_metrics):
                    for j in range(i + 1, n_metrics):
                        metric1 = metric_names[i]
                        metric2 = metric_names[j]

                        data1 = aligned_data['metrics'][metric1]
                        data2 = aligned_data['metrics'][metric2]

                        try:
                            if method in self.correlation_methods:
                                result = self.correlation_methods[method](data1, data2)

                                if 'correlation' in result:
                                    corr_value = result['correlation']
                                elif 'mic_score' in result:
                                    corr_value = result['mic_score']
                                elif 'normalized_mi' in result:
                                    corr_value = result['normalized_mi']
                                else:
                                    corr_value = 0.0

                                correlation_matrix[i, j] = corr_value
                                correlation_matrix[j, i] = corr_value

                                # P-value if available
                                if 'p_value' in result:
                                    p_value_matrix[i, j] = result['p_value']
                                    p_value_matrix[j, i] = result['p_value']

                        except Exception as e:
                            logger.warning(f"Matrix calculation failed for {metric1} vs {metric2}: {str(e)}")
                            continue

                matrices[method] = {
                    'correlation_matrix': correlation_matrix.tolist(),
                    'p_value_matrix': p_value_matrix.tolist() if np.any(p_value_matrix) else None,
                    'metric_labels': metric_names
                }

            return matrices

        except Exception as e:
            logger.error(f"Correlation matrix creation failed: {str(e)}")
            return {}

    def _perform_network_analysis(self, pairwise_correlations: Dict, metric_names: List[str]) -> Dict:
        """Perform network analysis to identify hubs and clusters"""
        try:
            # Create adjacency matrix based on significant correlations
            n_metrics = len(metric_names)
            adjacency_matrix = np.zeros((n_metrics, n_metrics))

            metric_to_idx = {metric: i for i, metric in enumerate(metric_names)}

            # Fill adjacency matrix
            for pair_key, pair_data in pairwise_correlations.items():
                if 'error' in pair_data:
                    continue

                metrics = pair_key.split('_vs_')
                if len(metrics) != 2:
                    continue

                metric1, metric2 = metrics
                if metric1 not in metric_to_idx or metric2 not in metric_to_idx:
                    continue

                i, j = metric_to_idx[metric1], metric_to_idx[metric2]

                # Use Pearson correlation as edge weight if significant
                pearson_data = pair_data.get('pearson', {})
                if pearson_data.get('significant', False):
                    correlation = abs(pearson_data.get('correlation', 0))
                    adjacency_matrix[i, j] = correlation
                    adjacency_matrix[j, i] = correlation

            # Calculate network metrics
            network_metrics = {
                'adjacency_matrix': adjacency_matrix.tolist(),
                'metric_labels': metric_names,
                'node_metrics': {},
                'network_density': self._calculate_network_density(adjacency_matrix),
                'clusters': self._identify_clusters(adjacency_matrix, metric_names)
            }

            # Calculate node-level metrics
            for i, metric in enumerate(metric_names):
                # Degree centrality (number of significant connections)
                degree = np.sum(adjacency_matrix[i] > 0.3)  # Threshold for meaningful correlation

                # Strength centrality (sum of correlation weights)
                strength = np.sum(adjacency_matrix[i])

                # Betweenness centrality (simplified)
                betweenness = self._calculate_betweenness_centrality(adjacency_matrix, i)

                network_metrics['node_metrics'][metric] = {
                    'degree_centrality': int(degree),
                    'strength_centrality': float(strength),
                    'betweenness_centrality': float(betweenness),
                    'hub_score': float(degree * strength)  # Combined metric
                }

            # Identify hubs (nodes with high connectivity)
            hub_scores = [metrics['hub_score'] for metrics in network_metrics['node_metrics'].values()]
            if hub_scores:
                hub_threshold = np.percentile(hub_scores, 75)  # Top 25%
                hubs = [metric for metric, metrics in network_metrics['node_metrics'].items()
                       if metrics['hub_score'] >= hub_threshold]
                network_metrics['identified_hubs'] = hubs

            return network_metrics

        except Exception as e:
            logger.error(f"Network analysis failed: {str(e)}")
            return {}

    def _calculate_network_density(self, adjacency_matrix: np.ndarray) -> float:
        """Calculate network density (proportion of possible edges that exist)"""
        try:
            n = adjacency_matrix.shape[0]
            if n <= 1:
                return 0.0

            # Count edges (above threshold)
            threshold = 0.3  # Minimum correlation to consider as edge
            edges = np.sum(adjacency_matrix > threshold) / 2  # Divide by 2 for undirected graph

            # Maximum possible edges
            max_edges = n * (n - 1) / 2

            density = edges / max_edges if max_edges > 0 else 0.0
            return float(density)

        except Exception:
            return 0.0

    def _identify_clusters(self, adjacency_matrix: np.ndarray, metric_names: List[str]) -> List[Dict]:
        """Identify clusters using simple community detection"""
        try:
            # Simple clustering based on correlation strength
            threshold = 0.5  # Strong correlation threshold
            strong_connections = adjacency_matrix > threshold

            n = len(metric_names)
            visited = [False] * n
            clusters = []

            def dfs(node, cluster):
                visited[node] = True
                cluster.append(metric_names[node])

                for neighbor in range(n):
                    if not visited[neighbor] and strong_connections[node, neighbor]:
                        dfs(neighbor, cluster)

            # Find connected components
            for i in range(n):
                if not visited[i]:
                    cluster = []
                    dfs(i, cluster)
                    if len(cluster) > 1:  # Only include clusters with multiple nodes
                        # Calculate cluster cohesion
                        cluster_indices = [metric_names.index(metric) for metric in cluster]
                        submatrix = adjacency_matrix[np.ix_(cluster_indices, cluster_indices)]
                        cohesion = np.mean(submatrix[submatrix > 0]) if np.any(submatrix > 0) else 0.0

                        clusters.append({
                            'metrics': cluster,
                            'size': len(cluster),
                            'cohesion': float(cohesion),
                            'interpretation': self._interpret_cluster(cluster)
                        })

            return clusters

        except Exception as e:
            logger.warning(f"Cluster identification failed: {str(e)}")
            return []

    def _calculate_betweenness_centrality(self, adjacency_matrix: np.ndarray, node: int) -> float:
        """Simplified betweenness centrality calculation"""
        try:
            # For small networks, use a simplified version
            # Count how many shortest paths go through this node
            n = adjacency_matrix.shape[0]

            if n <= 3:
                return 0.0

            # Simple proxy: average of connections to different components
            node_connections = adjacency_matrix[node]
            non_zero_connections = np.sum(node_connections > 0.3)

            # Normalize by possible connections
            max_connections = n - 1
            betweenness = non_zero_connections / max_connections if max_connections > 0 else 0.0

            return float(betweenness)

        except Exception:
            return 0.0

    def _interpret_cluster(self, cluster_metrics: List[str]) -> str:
        """Provide interpretation for identified clusters"""
        try:
            # Define metric categories
            sleep_metrics = {'sleep_score', 'sleep_efficiency', 'deep_sleep_percentage', 'rem_sleep_percentage'}
            recovery_metrics = {'hrv', 'recovery', 'heart_rate'}
            activity_metrics = {'steps', 'calories_burned', 'active_minutes', 'exercise_duration'}
            physiological_metrics = {'temperature', 'heart_rate', 'hrv'}

            cluster_set = set(cluster_metrics)

            # Check for common patterns
            if cluster_set.issubset(sleep_metrics):
                return "Sleep quality cluster"
            elif cluster_set.issubset(recovery_metrics):
                return "Recovery and autonomic function cluster"
            elif cluster_set.issubset(activity_metrics):
                return "Physical activity cluster"
            elif cluster_set.intersection(sleep_metrics) and cluster_set.intersection(recovery_metrics):
                return "Sleep-recovery interaction cluster"
            elif len(cluster_set.intersection(physiological_metrics)) >= 2:
                return "Physiological markers cluster"
            else:
                return f"Mixed cluster ({len(cluster_metrics)} metrics)"

        except Exception:
            return "Uncharacterized cluster"

    def _apply_multiple_testing_correction(self, results: Dict) -> Dict:
        """Apply multiple testing correction to p-values"""
        try:
            # Collect all p-values
            p_values = []
            p_value_sources = []

            for pair_key, pair_data in results.get('pairwise_correlations', {}).items():
                for method, method_data in pair_data.items():
                    if isinstance(method_data, dict) and 'p_value' in method_data:
                        p_values.append(method_data['p_value'])
                        p_value_sources.append((pair_key, method))

            if not p_values:
                return results

            # Apply Benjamini-Hochberg FDR correction
            corrected_results = StatisticalValidator.apply_multiple_testing_correction(
                p_values, method='fdr_bh'
            )

            # Update results with corrected p-values
            corrected_p_values = corrected_results['corrected_p_values']
            rejected_hypotheses = corrected_results['rejected_hypotheses']

            for i, (pair_key, method) in enumerate(p_value_sources):
                if pair_key in results['pairwise_correlations']:
                    if method in results['pairwise_correlations'][pair_key]:
                        method_data = results['pairwise_correlations'][pair_key][method]
                        method_data['p_value_corrected'] = corrected_p_values[i]
                        method_data['significant_corrected'] = rejected_hypotheses[i]

            # Update significant relationships based on corrected p-values
            updated_significant = []
            for rel in results.get('significant_relationships', []):
                pair_key = rel['metric_pair']
                if pair_key in results['pairwise_correlations']:
                    pearson_data = results['pairwise_correlations'][pair_key].get('pearson', {})
                    if pearson_data.get('significant_corrected', False):
                        rel['multiple_testing_corrected'] = True
                        updated_significant.append(rel)

            results['significant_relationships'] = updated_significant
            results['multiple_testing_correction'] = {
                'method': 'benjamini_hochberg_fdr',
                'original_significant': len([p for p in p_values if p < self.significance_level]),
                'corrected_significant': sum(rejected_hypotheses),
                'alpha_level': self.significance_level
            }

            return results

        except Exception as e:
            logger.warning(f"Multiple testing correction failed: {str(e)}")
            return results

    def _is_significant_relationship(self, pair_results: Dict) -> bool:
        """Check if a metric pair has significant correlation"""
        try:
            # Check Pearson correlation first
            pearson_data = pair_results.get('pearson', {})
            if pearson_data.get('significant', False):
                return True

            # Check other methods
            for method_name, method_data in pair_results.items():
                if isinstance(method_data, dict) and method_data.get('significant', False):
                    return True

            return False

        except Exception:
            return False

    def _count_significant_methods(self, pair_results: Dict) -> int:
        """Count how many methods found significant correlation"""
        try:
            count = 0
            for method_name, method_data in pair_results.items():
                if isinstance(method_data, dict) and method_data.get('significant', False):
                    count += 1
            return count

        except Exception:
            return 0

    def _interpret_correlation_strength(self, correlation: float) -> str:
        """Interpret correlation strength"""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            return 'very_strong'
        elif abs_corr >= 0.6:
            return 'strong'
        elif abs_corr >= 0.4:
            return 'moderate'
        elif abs_corr >= 0.2:
            return 'weak'
        else:
            return 'negligible'

    def _interpret_mi_strength(self, mi_score: float) -> str:
        """Interpret mutual information strength"""
        if mi_score >= 0.7:
            return 'very_strong'
        elif mi_score >= 0.5:
            return 'strong'
        elif mi_score >= 0.3:
            return 'moderate'
        elif mi_score >= 0.1:
            return 'weak'
        else:
            return 'negligible'

def calculate_partial_correlation(data: Dict, target_metric1: str, target_metric2: str,
                                control_metrics: List[str]) -> Dict:
    """Calculate partial correlation controlling for other variables"""
    try:
        # This would require pingouin or similar library for proper implementation
        # For now, providing a simplified version using multiple regression residuals

        if target_metric1 not in data or target_metric2 not in data:
            return {'error': 'Target metrics not found in data'}

        # Get target variables
        y1 = np.array(data[target_metric1]['values'])
        y2 = np.array(data[target_metric2]['values'])

        # Get control variables
        control_data = []
        for control_metric in control_metrics:
            if control_metric in data:
                control_data.append(np.array(data[control_metric]['values']))

        if not control_data:
            # No control variables - return simple correlation
            r, p_value = pearsonr(y1, y2)
            return {
                'partial_correlation': float(r),
                'p_value': float(p_value),
                'controlled_variables': control_metrics,
                'method': 'simple_correlation_no_controls'
            }

        # Align data lengths
        min_length = min(len(y1), len(y2), min(len(x) for x in control_data))
        y1 = y1[:min_length]
        y2 = y2[:min_length]
        control_matrix = np.array([x[:min_length] for x in control_data]).T

        # Remove NaN values
        valid_mask = ~(np.isnan(y1) | np.isnan(y2) | np.any(np.isnan(control_matrix), axis=1))
        y1_clean = y1[valid_mask]
        y2_clean = y2[valid_mask]
        control_clean = control_matrix[valid_mask]

        if len(y1_clean) < 10:
            return {'error': 'Insufficient clean data for partial correlation'}

        # Calculate residuals after regressing out control variables
        from sklearn.linear_model import LinearRegression

        # Regress y1 on control variables
        reg1 = LinearRegression()
        reg1.fit(control_clean, y1_clean)
        y1_residuals = y1_clean - reg1.predict(control_clean)

        # Regress y2 on control variables
        reg2 = LinearRegression()
        reg2.fit(control_clean, y2_clean)
        y2_residuals = y2_clean - reg2.predict(control_clean)

        # Calculate correlation of residuals
        partial_r, partial_p = pearsonr(y1_residuals, y2_residuals)

        return {
            'partial_correlation': float(partial_r),
            'p_value': float(partial_p),
            'significant': partial_p < 0.05,
            'controlled_variables': control_metrics,
            'method': 'regression_residuals',
            'sample_size': len(y1_clean)
        }

    except Exception as e:
        logger.error(f"Partial correlation calculation failed: {str(e)}")
        return {'error': str(e)}

def detect_correlation_changes_over_time(data: Dict, metric1: str, metric2: str,
                                       window_size: int = 7) -> Dict:
    """Detect how correlation between metrics changes over time"""
    try:
        if metric1 not in data or metric2 not in data:
            return {'error': 'Metrics not found in data'}

        values1 = np.array(data[metric1]['values'])
        values2 = np.array(data[metric2]['values'])
        timestamps = pd.to_datetime(data[metric1]['timestamps'])

        if len(values1) != len(values2) or len(values1) < window_size * 2:
            return {'error': 'Insufficient data for temporal correlation analysis'}

        # Calculate rolling correlations
        rolling_correlations = []
        time_points = []

        for i in range(window_size, len(values1) - window_size + 1):
            window_data1 = values1[i-window_size:i+window_size]
            window_data2 = values2[i-window_size:i+window_size]

            # Remove any NaN values
            valid_mask = ~(np.isnan(window_data1) | np.isnan(window_data2))
            clean_data1 = window_data1[valid_mask]
            clean_data2 = window_data2[valid_mask]

            if len(clean_data1) >= 5:  # Minimum sample size
                try:
                    corr, _ = pearsonr(clean_data1, clean_data2)
                    rolling_correlations.append(corr)
                    time_points.append(timestamps.iloc[i])
                except Exception:
                    rolling_correlations.append(np.nan)
                    time_points.append(timestamps.iloc[i])

        # Analyze correlation stability
        rolling_correlations = np.array(rolling_correlations)
        valid_correlations = rolling_correlations[~np.isnan(rolling_correlations)]

        if len(valid_correlations) == 0:
            return {'error': 'No valid correlations calculated'}

        correlation_stability = {
            'mean_correlation': float(np.mean(valid_correlations)),
            'std_correlation': float(np.std(valid_correlations)),
            'min_correlation': float(np.min(valid_correlations)),
            'max_correlation': float(np.max(valid_correlations)),
            'correlation_range': float(np.max(valid_correlations) - np.min(valid_correlations)),
            'stability_score': 1.0 - (np.std(valid_correlations) / (np.mean(np.abs(valid_correlations)) + 1e-8)),
            'rolling_correlations': rolling_correlations.tolist(),
            'time_points': [t.isoformat() for t in time_points],
            'window_size_days': window_size
        }

        # Interpret stability
        if correlation_stability['stability_score'] > 0.8:
            correlation_stability['interpretation'] = 'Very stable correlation over time'
        elif correlation_stability['stability_score'] > 0.6:
            correlation_stability['interpretation'] = 'Moderately stable correlation'
        elif correlation_stability['stability_score'] > 0.4:
            correlation_stability['interpretation'] = 'Variable correlation over time'
        else:
            correlation_stability['interpretation'] = 'Highly variable or inconsistent correlation'

        return correlation_stability

    except Exception as e:
        logger.error(f"Temporal correlation analysis failed: {str(e)}")
        return {'error': str(e)}

def find_correlation_networks(correlation_matrix: np.ndarray, metric_names: List[str],
                            threshold: float = 0.5) -> Dict:
    """Find correlation networks and communities"""
    try:
        # Create adjacency matrix based on correlation threshold
        adjacency = np.abs(correlation_matrix) >= threshold

        # Remove diagonal (self-correlations)
        np.fill_diagonal(adjacency, False)

        n_metrics = len(metric_names)
        visited = [False] * n_metrics
        networks = []

        def dfs_network(node, network):
            visited[node] = True
            network.append(node)

            for neighbor in range(n_metrics):
                if not visited[neighbor] and adjacency[node, neighbor]:
                    dfs_network(neighbor, network)

        # Find connected components (correlation networks)
        for i in range(n_metrics):
            if not visited[i]:
                network = []
                dfs_network(i, network)

                if len(network) > 1:  # Only include networks with multiple metrics
                    network_metrics = [metric_names[j] for j in network]

                    # Calculate network statistics
                    network_indices = np.array(network)
                    submatrix = correlation_matrix[np.ix_(network_indices, network_indices)]

                    # Remove diagonal and calculate mean correlation
                    mask = ~np.eye(len(network), dtype=bool)
                    network_correlations = submatrix[mask]

                    networks.append({
                        'metrics': network_metrics,
                        'size': len(network_metrics),
                        'mean_correlation': float(np.mean(np.abs(network_correlations))),
                        'max_correlation': float(np.max(np.abs(network_correlations))),
                        'min_correlation': float(np.min(np.abs(network_correlations))),
                        'density': float(np.sum(np.abs(submatrix) >= threshold) / (len(network) * (len(network) - 1))),
                        'interpretation': _interpret_network(network_metrics)
                    })

        return {
            'correlation_threshold': threshold,
            'networks_found': len(networks),
            'networks': networks,
            'largest_network_size': max([net['size'] for net in networks]) if networks else 0,
            'total_metrics_in_networks': sum([net['size'] for net in networks]),
            'isolated_metrics': [metric_names[i] for i in range(n_metrics) if not any(i in net for net in networks)]
        }

    except Exception as e:
        logger.error(f"Correlation network analysis failed: {str(e)}")
        return {'error': str(e)}

def _interpret_network(network_metrics: List[str]) -> str:
    """Interpret what a correlation network represents"""
    try:
        # Define metric categories
        categories = {
            'sleep': ['sleep_score', 'sleep_efficiency', 'deep_sleep_percentage', 'rem_sleep_percentage'],
            'recovery': ['hrv', 'recovery', 'heart_rate'],
            'activity': ['steps', 'calories_burned', 'active_minutes', 'exercise_duration'],
            'physiological': ['temperature', 'heart_rate', 'hrv'],
            'lifestyle': ['meal_timing', 'supplement_intake', 'stress_level']
        }

        network_set = set(network_metrics)
        category_matches = {}

        for category, metrics in categories.items():
            overlap = len(network_set.intersection(set(metrics)))
            if overlap > 0:
                category_matches[category] = overlap

        if not category_matches:
            return f"Mixed network ({len(network_metrics)} metrics)"

        # Find dominant category
        dominant_category = max(category_matches, key=category_matches.get)
        overlap_count = category_matches[dominant_category]

        if overlap_count >= len(network_metrics) * 0.7:  # 70% or more from one category
            return f"{dominant_category.title()} network"
        elif len(category_matches) == 2:
            categories_list = list(category_matches.keys())
            return f"{categories_list[0].title()}-{categories_list[1]} interaction network"
        else:
            return f"Multi-domain network (primarily {dominant_category})"

    except Exception:
        return "Uncharacterized network"

def calculate_dynamic_correlations(data: Dict, metric1: str, metric2: str,
                                 time_windows: List[str] = None) -> Dict:
    """Calculate correlations across different time windows"""
    try:
        if time_windows is None:
            time_windows = ['1D', '3D', '7D', '14D', '30D']  # 1 day to 30 days

        if metric1 not in data or metric2 not in data:
            return {'error': 'Metrics not found in data'}

        values1 = np.array(data[metric1]['values'])
        values2 = np.array(data[metric2]['values'])
        timestamps = pd.to_datetime(data[metric1]['timestamps'])

        # Create DataFrame for easier manipulation
        df = pd.DataFrame({
            'timestamp': timestamps,
            'metric1': values1,
            'metric2': values2
        }).set_index('timestamp')

        dynamic_results = {
            'metric_pair': f"{metric1}_vs_{metric2}",
            'time_windows': {},
            'correlation_evolution': [],
            'stability_analysis': {}
        }

        # Calculate correlations for each time window
        for window in time_windows:
            try:
                # Resample data to the specified window
                resampled = df.resample(window).mean().dropna()

                if len(resampled) < 3:
                    continue

                # Calculate correlation
                corr, p_value = pearsonr(resampled['metric1'], resampled['metric2'])

                dynamic_results['time_windows'][window] = {
                    'correlation': float(corr),
                    'p_value': float(p_value),
                    'significant': p_value < 0.05,
                    'sample_size': len(resampled),
                    'time_resolution': window
                }

            except Exception as e:
                logger.warning(f"Dynamic correlation calculation failed for window {window}: {str(e)}")
                continue

        # Analyze correlation evolution over time (monthly rolling windows)
        if len(df) > 30:  # Need at least 30 data points
            window_size = min(30, len(df) // 3)  # Monthly windows or 1/3 of data

            for i in range(window_size, len(df) - window_size, window_size // 2):
                window_data = df.iloc[i-window_size:i+window_size]

                if len(window_data.dropna()) >= 10:
                    try:
                        clean_data = window_data.dropna()
                        corr, _ = pearsonr(clean_data['metric1'], clean_data['metric2'])

                        dynamic_results['correlation_evolution'].append({
                            'time_point': window_data.index[len(window_data)//2].isoformat(),
                            'correlation': float(corr),
                            'window_size': window_size
                        })
                    except Exception:
                        continue

        # Stability analysis
        if dynamic_results['correlation_evolution']:
            correlations = [point['correlation'] for point in dynamic_results['correlation_evolution']]
            dynamic_results['stability_analysis'] = {
                'mean_correlation': float(np.mean(correlations)),
                'correlation_volatility': float(np.std(correlations)),
                'min_correlation': float(np.min(correlations)),
                'max_correlation': float(np.max(correlations)),
                'correlation_trend': 'increasing' if correlations[-1] > correlations[0] else 'decreasing'
            }

        return dynamic_results

    except Exception as e:
        logger.error(f"Dynamic correlation analysis failed: {str(e)}")
        return {'error': str(e)}