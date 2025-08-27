"""
Advanced anomaly detection algorithms for health metrics
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EllipticEnvelope
from statsmodels.tsa.seasonal import seasonal_decompose
from typing import Dict, List, Tuple, Optional, Union
import logging
from utils.stats_utils import RobustStatistics, StatisticalValidator
from utils.cache import cache_statistical_analysis

logger = logging.getLogger(__name__)

# Optional imports with fallbacks
try:
    import pywt
    WAVELETS_AVAILABLE = True
except ImportError:
    WAVELETS_AVAILABLE = False
    logging.warning("PyWavelets not available - wavelet analysis disabled")

try:
    from minepy import MINE
    MINEPY_AVAILABLE = True
except ImportError:
    MINEPY_AVAILABLE = False
    logging.warning("minepy not available - MIC analysis disabled")

class AnomalyDetector:
    """Comprehensive anomaly detection using multiple statistical and ML methods"""

    def __init__(self, contamination_rate: float = 0.1):
        self.contamination_rate = contamination_rate
        self.methods = {
            'z_score': self._z_score_detection,
            'modified_z_score': self._modified_z_score_detection,
            'isolation_forest': self._isolation_forest_detection,
            'local_outlier_factor': self._lof_detection,
            'elliptic_envelope': self._elliptic_envelope_detection,
            'seasonal_decomposition': self._seasonal_anomaly_detection,
            'statistical_process_control': self._spc_detection
        }

    @cache_statistical_analysis(expire_seconds=1800)
    def detect_anomalies(self, data: Union[pd.DataFrame, np.ndarray],
                        timestamps: Optional[List] = None,
                        methods: Optional[List[str]] = None,
                        confidence_threshold: float = 0.95) -> Dict:
        """
        Detect anomalies using multiple methods and return ensemble results

        Args:
            data: Input data (univariate or multivariate)
            timestamps: Optional timestamps for time series analysis
            methods: List of methods to use (None = all methods)
            confidence_threshold: Confidence threshold for anomaly detection

        Returns:
            Dictionary with anomaly scores, classifications, and method details
        """
        try:
            # Prepare data
            if isinstance(data, pd.DataFrame):
                data_array = data.values
            else:
                data_array = np.array(data)

            if data_array.ndim == 1:
                data_array = data_array.reshape(-1, 1)

            # Validate data quality
            validation = StatisticalValidator.validate_sample_size(data_array)
            if not validation['is_sufficient']:
                logger.warning(f"Insufficient data for robust anomaly detection: {validation['sample_size']} samples")

            # Select methods
            if methods is None:
                methods = ['z_score', 'modified_z_score', 'isolation_forest', 'local_outlier_factor']

            # Run anomaly detection methods
            method_results = {}
            anomaly_scores = np.zeros(len(data_array))

            for method_name in methods:
                if method_name in self.methods:
                    try:
                        method_func = self.methods[method_name]
                        if method_name == 'seasonal_decomposition' and timestamps is not None:
                            result = method_func(data_array, timestamps)
                        else:
                            result = method_func(data_array)

                        method_results[method_name] = result

                        # Aggregate scores (normalize to 0-1 range)
                        normalized_scores = self._normalize_scores(result['anomaly_scores'])
                        anomaly_scores += normalized_scores

                    except Exception as e:
                        logger.warning(f"Anomaly detection method {method_name} failed: {str(e)}")
                        continue

            # Calculate ensemble scores
            if len(method_results) > 0:
                anomaly_scores /= len(method_results)
            else:
                raise ValueError("No anomaly detection methods succeeded")

            # Determine anomaly threshold
            threshold = np.percentile(anomaly_scores, (1 - self.contamination_rate) * 100)
            anomalies = anomaly_scores > threshold

            # Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(
                method_results, anomaly_scores, confidence_threshold
            )

            # Identify severe anomalies (multiple methods agree)
            severe_anomalies = self._identify_severe_anomalies(method_results, threshold=0.7)

            results = {
                'anomaly_scores': anomaly_scores.tolist(),
                'anomalies': anomalies.tolist(),
                'severe_anomalies': severe_anomalies.tolist(),
                'confidence_scores': confidence_scores.tolist(),
                'threshold': float(threshold),
                'method_results': method_results,
                'detection_summary': {
                    'total_points': len(data_array),
                    'anomalies_detected': int(np.sum(anomalies)),
                    'severe_anomalies': int(np.sum(severe_anomalies)),
                    'anomaly_rate': float(np.mean(anomalies)),
                    'methods_used': list(method_results.keys())
                }
            }

            return results

        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            return {
                'error': str(e),
                'anomaly_scores': [],
                'anomalies': [],
                'confidence_scores': []
            }

    def _z_score_detection(self, data: np.ndarray) -> Dict:
        """Standard Z-score anomaly detection"""
        try:
            if data.shape[1] > 1:
                # Multivariate: use Mahalanobis distance
                mean = np.mean(data, axis=0)
                cov = np.cov(data.T)
                cov_inv = np.linalg.pinv(cov)

                z_scores = []
                for point in data:
                    diff = point - mean
                    mahal_dist = np.sqrt(diff.T @ cov_inv @ diff)
                    z_scores.append(mahal_dist)

                z_scores = np.array(z_scores)
            else:
                # Univariate Z-score
                mean = np.mean(data)
                std = np.std(data, ddof=1)
                if std == 0:
                    z_scores = np.zeros(len(data))
                else:
                    z_scores = np.abs((data.flatten() - mean) / std)

            # Convert to anomaly scores (higher = more anomalous)
            anomaly_scores = np.tanh(z_scores / 3.0)  # Normalize to 0-1 range

            return {
                'anomaly_scores': anomaly_scores,
                'z_scores': z_scores,
                'threshold': 3.0,
                'method': 'z_score'
            }

        except Exception as e:
            logger.error(f"Z-score detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _modified_z_score_detection(self, data: np.ndarray) -> Dict:
        """Modified Z-score using Median Absolute Deviation (robust to outliers)"""
        try:
            if data.shape[1] > 1:
                # For multivariate data, apply to each dimension
                anomaly_scores = np.zeros(len(data))
                for i in range(data.shape[1]):
                    column_data = data[:, i]
                    modified_z = [RobustStatistics.modified_z_score(column_data, val) for val in column_data]
                    anomaly_scores += np.abs(modified_z)
                anomaly_scores /= data.shape[1]  # Average across dimensions
            else:
                # Univariate modified Z-score
                data_flat = data.flatten()
                modified_z_scores = [RobustStatistics.modified_z_score(data_flat, val) for val in data_flat]
                anomaly_scores = np.abs(modified_z_scores)

            # Normalize to 0-1 range
            anomaly_scores = np.tanh(anomaly_scores / 3.5)

            return {
                'anomaly_scores': anomaly_scores,
                'modified_z_scores': modified_z_scores if data.shape[1] == 1 else None,
                'threshold': 3.5,
                'method': 'modified_z_score'
            }

        except Exception as e:
            logger.error(f"Modified Z-score detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _isolation_forest_detection(self, data: np.ndarray) -> Dict:
        """Isolation Forest anomaly detection (good for multivariate data)"""
        try:
            # Scale data for better performance
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data)

            # Initialize Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.contamination_rate,
                random_state=42,
                n_estimators=100
            )

            # Fit and predict
            anomaly_labels = iso_forest.fit_predict(scaled_data)
            anomaly_scores = iso_forest.decision_function(scaled_data)

            # Convert to 0-1 range (higher = more anomalous)
            anomaly_scores = (anomaly_scores.max() - anomaly_scores) / (anomaly_scores.max() - anomaly_scores.min())

            return {
                'anomaly_scores': anomaly_scores,
                'anomaly_labels': anomaly_labels,  # -1 = anomaly, 1 = normal
                'method': 'isolation_forest'
            }

        except Exception as e:
            logger.error(f"Isolation Forest detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _lof_detection(self, data: np.ndarray) -> Dict:
        """Local Outlier Factor detection"""
        try:
            # Scale data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data)

            # Determine optimal number of neighbors
            n_neighbors = min(20, max(5, len(data) // 10))

            # Initialize LOF
            lof = LocalOutlierFactor(
                n_neighbors=n_neighbors,
                contamination=self.contamination_rate
            )

            # Fit and predict
            anomaly_labels = lof.fit_predict(scaled_data)
            lof_scores = -lof.negative_outlier_factor_  # Convert to positive scores

            # Normalize to 0-1 range
            if lof_scores.max() > lof_scores.min():
                anomaly_scores = (lof_scores - lof_scores.min()) / (lof_scores.max() - lof_scores.min())
            else:
                anomaly_scores = np.zeros_like(lof_scores)

            return {
                'anomaly_scores': anomaly_scores,
                'lof_scores': lof_scores,
                'anomaly_labels': anomaly_labels,
                'n_neighbors': n_neighbors,
                'method': 'local_outlier_factor'
            }

        except Exception as e:
            logger.error(f"LOF detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _elliptic_envelope_detection(self, data: np.ndarray) -> Dict:
        """Elliptic Envelope anomaly detection (assumes Gaussian distribution)"""
        try:
            # Only works well with sufficient data
            if len(data) < 10:
                return {'anomaly_scores': np.zeros(len(data)), 'error': 'Insufficient data'}

            # Scale data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data)

            # Initialize Elliptic Envelope
            elliptic_env = EllipticEnvelope(
                contamination=self.contamination_rate,
                random_state=42
            )

            # Fit and predict
            anomaly_labels = elliptic_env.fit_predict(scaled_data)

            # Calculate Mahalanobis distances as anomaly scores
            distances = elliptic_env.mahalanobis(scaled_data)

            # Normalize to 0-1 range
            if distances.max() > distances.min():
                anomaly_scores = (distances - distances.min()) / (distances.max() - distances.min())
            else:
                anomaly_scores = np.zeros_like(distances)

            return {
                'anomaly_scores': anomaly_scores,
                'mahalanobis_distances': distances,
                'anomaly_labels': anomaly_labels,
                'method': 'elliptic_envelope'
            }

        except Exception as e:
            logger.error(f"Elliptic Envelope detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _seasonal_anomaly_detection(self, data: np.ndarray, timestamps: List) -> Dict:
        """Seasonal decomposition-based anomaly detection for time series"""
        try:
            if data.shape[1] > 1:
                # For multivariate, analyze each dimension separately
                all_anomaly_scores = []

                for i in range(data.shape[1]):
                    series_data = data[:, i]
                    result = self._detect_seasonal_anomalies_univariate(series_data, timestamps)
                    all_anomaly_scores.append(result['anomaly_scores'])

                # Combine anomaly scores across dimensions
                anomaly_scores = np.mean(all_anomaly_scores, axis=0)
            else:
                result = self._detect_seasonal_anomalies_univariate(data.flatten(), timestamps)
                anomaly_scores = result['anomaly_scores']

            return {
                'anomaly_scores': anomaly_scores,
                'method': 'seasonal_decomposition'
            }

        except Exception as e:
            logger.error(f"Seasonal anomaly detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _detect_seasonal_anomalies_univariate(self, data: np.ndarray, timestamps: List) -> Dict:
        """Helper for univariate seasonal anomaly detection"""
        try:
            # Create time series
            ts_data = pd.Series(data, index=pd.to_datetime(timestamps))

            # Determine period (assume daily data, look for weekly patterns)
            period = min(7, len(data) // 3)

            if len(data) < 2 * period:
                # Fallback to simple residual analysis
                mean_val = np.mean(data)
                residuals = np.abs(data - mean_val)
                anomaly_scores = residuals / (np.std(residuals) + 1e-8)
                return {'anomaly_scores': np.tanh(anomaly_scores / 3.0)}

            # Seasonal decomposition
            decomposition = seasonal_decompose(ts_data, model='additive', period=period, extrapolate_trend='freq')

            # Calculate residuals (actual - trend - seasonal)
            residuals = decomposition.resid.fillna(0)

            # Detect anomalies in residuals
            residual_std = np.std(residuals)
            if residual_std == 0:
                anomaly_scores = np.zeros(len(data))
            else:
                z_scores = np.abs(residuals) / residual_std
                anomaly_scores = np.tanh(z_scores / 3.0)

            return {
                'anomaly_scores': anomaly_scores,
                'residuals': residuals.values,
                'trend': decomposition.trend.fillna(method='bfill').fillna(method='ffill').values,
                'seasonal': decomposition.seasonal.values,
                'period': period
            }

        except Exception as e:
            logger.error(f"Univariate seasonal detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _spc_detection(self, data: np.ndarray) -> Dict:
        """Statistical Process Control (SPC) anomaly detection"""
        try:
            if data.shape[1] > 1:
                # For multivariate, use T² statistic (Hotelling's T²)
                mean_vec = np.mean(data, axis=0)
                cov_matrix = np.cov(data.T)
                cov_inv = np.linalg.pinv(cov_matrix)

                t_squared_scores = []
                for point in data:
                    diff = point - mean_vec
                    t_squared = diff.T @ cov_inv @ diff
                    t_squared_scores.append(t_squared)

                t_squared_scores = np.array(t_squared_scores)

                # Control limits (approximate)
                ucl = np.percentile(t_squared_scores, 99.7)  # 3-sigma equivalent
                anomaly_scores = t_squared_scores / (ucl + 1e-8)

            else:
                # Univariate SPC using moving statistics
                data_flat = data.flatten()
                window_size = min(10, len(data_flat) // 3)

                if window_size < 3:
                    # Fallback to simple Z-score
                    return self._z_score_detection(data)

                # Calculate moving mean and standard deviation
                moving_mean = pd.Series(data_flat).rolling(window=window_size, center=True).mean()
                moving_std = pd.Series(data_flat).rolling(window=window_size, center=True).std()

                # Fill NaN values
                moving_mean = moving_mean.fillna(method='bfill').fillna(method='ffill')
                moving_std = moving_std.fillna(method='bfill').fillna(method='ffill')

                # Calculate control limits (3-sigma)
                ucl = moving_mean + 3 * moving_std
                lcl = moving_mean - 3 * moving_std

                # Calculate anomaly scores based on distance from control limits
                anomaly_scores = np.zeros(len(data_flat))
                for i, value in enumerate(data_flat):
                    if value > ucl.iloc[i]:
                        anomaly_scores[i] = (value - ucl.iloc[i]) / moving_std.iloc[i]
                    elif value < lcl.iloc[i]:
                        anomaly_scores[i] = (lcl.iloc[i] - value) / moving_std.iloc[i]

                # Normalize
                anomaly_scores = np.tanh(anomaly_scores / 3.0)

            return {
                'anomaly_scores': anomaly_scores,
                'method': 'statistical_process_control'
            }

        except Exception as e:
            logger.error(f"SPC detection failed: {str(e)}")
            return {'anomaly_scores': np.zeros(len(data)), 'error': str(e)}

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        """Normalize anomaly scores to 0-1 range"""
        try:
            scores = np.array(scores)
            if len(scores) == 0:
                return scores

            min_score = np.min(scores)
            max_score = np.max(scores)

            if max_score > min_score:
                return (scores - min_score) / (max_score - min_score)
            else:
                return np.zeros_like(scores)

        except Exception as e:
            logger.warning(f"Score normalization failed: {str(e)}")
            return np.zeros_like(scores)

    def _calculate_confidence_scores(self, method_results: Dict, ensemble_scores: np.ndarray,
                                   threshold: float) -> np.ndarray:
        """Calculate confidence scores for anomaly detection"""
        try:
            n_methods = len(method_results)
            if n_methods == 0:
                return np.zeros_like(ensemble_scores)

            # Count how many methods agree on each point being anomalous
            agreement_scores = np.zeros(len(ensemble_scores))

            for method_name, result in method_results.items():
                method_scores = self._normalize_scores(result['anomaly_scores'])
                method_threshold = np.percentile(method_scores, (1 - self.contamination_rate) * 100)
                agreement_scores += (method_scores > method_threshold).astype(float)

            # Normalize agreement to 0-1 range
            confidence_scores = agreement_scores / n_methods

            # Boost confidence for extreme scores
            extreme_boost = np.tanh(ensemble_scores * 2)
            confidence_scores = np.minimum(1.0, confidence_scores + 0.3 * extreme_boost)

            return confidence_scores

        except Exception as e:
            logger.warning(f"Confidence calculation failed: {str(e)}")
            return np.ones_like(ensemble_scores) * 0.5

    def _identify_severe_anomalies(self, method_results: Dict, threshold: float = 0.7) -> np.ndarray:
        """Identify severe anomalies where multiple methods agree"""
        try:
            if not method_results:
                return np.array([])

            n_points = len(list(method_results.values())[0]['anomaly_scores'])
            agreement_count = np.zeros(n_points)

            for method_name, result in method_results.items():
                scores = self._normalize_scores(result['anomaly_scores'])
                method_threshold = np.percentile(scores, (1 - self.contamination_rate) * 100)
                agreement_count += (scores > method_threshold).astype(float)

            # Require majority agreement for severe anomalies
            min_agreement = max(2, len(method_results) * threshold)
            severe_anomalies = agreement_count >= min_agreement

            return severe_anomalies

        except Exception as e:
            logger.warning(f"Severe anomaly identification failed: {str(e)}")
            return np.zeros(len(list(method_results.values())[0]['anomaly_scores']), dtype=bool)

def detect_contextual_anomalies(data: pd.DataFrame, context_columns: List[str],
                              target_column: str) -> Dict:
    """Detect contextual anomalies where behavior is unusual given context"""
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        # Prepare features and target
        X = data[context_columns].values
        y = data[target_column].values

        # Train model to predict target based on context
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_train, y_train)

        # Predict for all data
        predictions = rf_model.predict(X)
        residuals = np.abs(y - predictions)

        # Calculate anomaly scores based on prediction errors
        residual_threshold = np.percentile(residuals, 95)
        anomaly_scores = np.minimum(1.0, residuals / residual_threshold)

        return {
            'anomaly_scores': anomaly_scores.tolist(),
            'predictions': predictions.tolist(),
            'residuals': residuals.tolist(),
            'feature_importance': dict(zip(context_columns, rf_model.feature_importances_)),
            'model_score': rf_model.score(X_test, y_test)
        }

    except Exception as e:
        logger.error(f"Contextual anomaly detection failed: {str(e)}")
        return {'error': str(e), 'anomaly_scores': []}

def analyze_anomaly_patterns(anomalies: np.ndarray, timestamps: List,
                           data: np.ndarray) -> Dict:
    """Analyze patterns in detected anomalies"""
    try:
        if len(anomalies) == 0 or not any(anomalies):
            return {'no_anomalies': True}

        anomaly_indices = np.where(anomalies)[0]
        timestamps_dt = pd.to_datetime(timestamps)

        # Temporal patterns
        anomaly_times = timestamps_dt[anomaly_indices]
        hourly_pattern = anomaly_times.hour.value_counts().to_dict()
        daily_pattern = anomaly_times.day_name().value_counts().to_dict()

        # Clustering of anomalies
        time_diffs = np.diff(anomaly_indices)
        clustered_anomalies = np.sum(time_diffs <= 3)  # Anomalies within 3 time steps

        # Magnitude analysis
        anomaly_values = data[anomaly_indices] if data.ndim == 1 else data[anomaly_indices, :]

        patterns = {
            'total_anomalies': len(anomaly_indices),
            'anomaly_rate': len(anomaly_indices) / len(data),
            'clustered_anomalies': int(clustered_anomalies),
            'temporal_patterns': {
                'hourly_distribution': hourly_pattern,
                'daily_distribution': daily_pattern
            },
            'magnitude_stats': {
                'mean': float(np.mean(anomaly_values)) if anomaly_values.size > 0 else 0,
                'std': float(np.std(anomaly_values)) if anomaly_values.size > 0 else 0,
                'min': float(np.min(anomaly_values)) if anomaly_values.size > 0 else 0,
                'max': float(np.max(anomaly_values)) if anomaly_values.size > 0 else 0
            }
        }

        return patterns

    except Exception as e:
        logger.error(f"Anomaly pattern analysis failed: {str(e)}")
        return {'error': str(e)}