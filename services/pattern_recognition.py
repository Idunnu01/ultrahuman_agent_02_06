"""
Machine learning pattern recognition service for health data
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist
import warnings
warnings.filterwarnings('ignore')
from app.models import User, Metric, Pattern
from utils.database import db
from utils.cache import cache_statistical_analysis
from services.statistical_analyzer import StatisticalAnalyzer
logger = logging.getLogger(__name__)
class PatternRecognizer:
    """Advanced pattern recognition using machine learning techniques"""
    def __init__(self):
        self.analyzer = StatisticalAnalyzer()
        self.min_samples = 20  # Minimum data points for pattern recognition
        # Pattern types and their characteristics
        self.pattern_types = {
            'behavioral_cluster': {
                'methods': ['kmeans', 'dbscan'],
                'features': ['temporal', 'lifestyle', 'metrics'],
                'min_confidence': 0.6
            },
            'temporal_sequence': {
                'methods': ['sequence_mining', 'state_transitions'],
                'features': ['temporal', 'metrics'],
                'min_confidence': 0.7
            },
            'response_pattern': {
                'methods': ['intervention_response', 'correlation_patterns'],
                'features': ['interventions', 'metrics', 'lifestyle'],
                'min_confidence': 0.8
            },
            'anomaly_pattern': {
                'methods': ['isolation_forest', 'outlier_clustering'],
                'features': ['metrics', 'temporal'],
                'min_confidence': 0.75
            }
        }
    @cache_statistical_analysis(expire_seconds=3600)
    def discover_patterns(self, user_id: str, timeframe: timedelta = timedelta(days=30),
                         pattern_types: Optional[List[str]] = None) -> Dict:
        """Discover patterns in user's health data using ML techniques"""
        try:
            logger.info(f"Starting pattern discovery for user {user_id}")
            # Get user data
            user_data = self.analyzer._get_user_data(user_id, timeframe)
            if not user_data:
                return {'error': 'No user data available'}
            # Prepare feature matrix
            feature_matrix = self._prepare_feature_matrix(user_data)
            if feature_matrix is None or len(feature_matrix) < self.min_samples:
                return {'error': f'Insufficient data for pattern recognition (need {self.min_samples}, got {len(feature_matrix) if feature_matrix is not None else 0})'}
            # Initialize results
            pattern_results = {
                'user_id': user_id,
                'analysis_timeframe': timeframe.days,
                'discovered_patterns': {},
                'pattern_summary': {},
                'recommendations': [],
                'confidence_scores': {}
            }
            # Select pattern types to analyze
            if pattern_types is None:
                pattern_types = ['behavioral_cluster', 'temporal_sequence', 'anomaly_pattern']
            # Discover each pattern type
            for pattern_type in pattern_types:
                if pattern_type in self.pattern_types:
                    try:
                        pattern_result = self._discover_pattern_type(
                            user_id, pattern_type, feature_matrix, user_data
                        )
                        if 'error' not in pattern_result:
                            pattern_results['discovered_patterns'][pattern_type] = pattern_result
                            # Calculate confidence
                            confidence = self._calculate_pattern_confidence(pattern_result)
                            pattern_results['confidence_scores'][pattern_type] = confidence
                            # Store significant patterns in database
                            if confidence >= self.pattern_types[pattern_type]['min_confidence']:
                                self._store_pattern(user_id, pattern_type, pattern_result, confidence)
                    except Exception as e:
                        logger.warning(f"Pattern discovery failed for {pattern_type}: {str(e)}")
                        continue
            # Generate pattern summary
            pattern_results['pattern_summary'] = self._generate_pattern_summary(pattern_results)
            # Generate recommendations based on patterns
            pattern_results['recommendations'] = self._generate_pattern_recommendations(pattern_results)
            return pattern_results
        except Exception as e:
            logger.error(f"Pattern discovery failed for user {user_id}: {str(e)}")
            return {'error': str(e)}
    def _prepare_feature_matrix(self, user_data: Dict) -> Optional[np.ndarray]:
        """Prepare feature matrix for ML algorithms"""
        try:
            # Find common timestamps across all metrics
            all_timestamps = set()
            for metric_type, data in user_data.items():
                all_timestamps.update(data['timestamps'])
            if not all_timestamps:
                return None
            # Sort timestamps
            sorted_timestamps = sorted(all_timestamps)
            # Create feature matrix
            features = []
            feature_names = []
            # Metric values
            for metric_type, data in user_data.items():
                values = np.array(data['values'])
                timestamps = pd.to_datetime(data['timestamps'])
                # Create time series and interpolate to common grid
                ts = pd.Series(values, index=timestamps)
                # Resample to hourly data
                hourly_ts = ts.resample('H').mean()
                # Interpolate missing values
                hourly_ts = hourly_ts.interpolate(method='linear').fillna(method='bfill').fillna(method='ffill')
                features.append(hourly_ts.values)
                feature_names.append(f"{metric_type}_value")
            # Temporal features
            datetime_index = pd.date_range(start=min(sorted_timestamps), end=max(sorted_timestamps), freq='H')
            # Hour of day (cyclical encoding)
            hour_sin = np.sin(2 * np.pi * datetime_index.hour / 24)
            hour_cos = np.cos(2 * np.pi * datetime_index.hour / 24)
            features.extend([hour_sin, hour_cos])
            feature_names.extend(['hour_sin', 'hour_cos'])
            # Day of week (cyclical encoding)
            dow_sin = np.sin(2 * np.pi * datetime_index.dayofweek / 7)
            dow_cos = np.cos(2 * np.pi * datetime_index.dayofweek / 7)
            features.extend([dow_sin, dow_cos])
            feature_names.extend(['dow_sin', 'dow_cos'])
            # Combine features
            if not features:
                return None
            # Find minimum length to ensure all features have same length
            min_length = min(len(f) for f in features)
            feature_matrix = np.column_stack([f[:min_length] for f in features])
            # Remove rows with NaN values
            valid_mask = ~np.any(np.isnan(feature_matrix), axis=1)
            feature_matrix = feature_matrix[valid_mask]
            if len(feature_matrix) == 0:
                return None
            return feature_matrix
        except Exception as e:
            logger.error(f"Feature matrix preparation failed: {str(e)}")
            return None
    def _discover_pattern_type(self, user_id: str, pattern_type: str,
                             feature_matrix: np.ndarray, user_data: Dict) -> Dict:
        """Discover patterns of a specific type"""
        try:
            if pattern_type == 'behavioral_cluster':
                return self._discover_behavioral_clusters(feature_matrix, user_data)
            elif pattern_type == 'temporal_sequence':
                return self._discover_temporal_sequences(feature_matrix, user_data)
            elif pattern_type == 'anomaly_pattern':
                return self._discover_anomaly_patterns(feature_matrix, user_data)
            elif pattern_type == 'response_pattern':
                return self._discover_response_patterns(user_id, feature_matrix, user_data)
            else:
                return {'error': f'Unknown pattern type: {pattern_type}'}
        except Exception as e:
            logger.error(f"Pattern type discovery failed for {pattern_type}: {str(e)}")
            return {'error': str(e)}
    def _discover_behavioral_clusters(self, feature_matrix: np.ndarray, user_data: Dict) -> Dict:
        """Discover behavioral clusters using unsupervised learning"""
        try:
            # Standardize features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(feature_matrix)
            # Determine optimal number of clusters
            optimal_clusters = self._find_optimal_clusters(scaled_features)
            # K-means clustering
            kmeans = KMeans(n_clusters=optimal_clusters, random_state=42, n_init=10)
            kmeans_labels = kmeans.fit_predict(scaled_features)
            # DBSCAN clustering
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            dbscan_labels = dbscan.fit_predict(scaled_features)
            # Hierarchical clustering
            hierarchical = AgglomerativeClustering(n_clusters=optimal_clusters)
            hierarchical_labels = hierarchical.fit_predict(scaled_features)
            # Calculate silhouette scores
            kmeans_silhouette = silhouette_score(scaled_features, kmeans_labels) if len(set(kmeans_labels)) > 1 else 0
            dbscan_silhouette = silhouette_score(scaled_features, dbscan_labels) if len(set(dbscan_labels)) > 1 and -1 not in dbscan_labels else 0
            hierarchical_silhouette = silhouette_score(scaled_features, hierarchical_labels) if len(set(hierarchical_labels)) > 1 else 0
            # Choose best clustering method
            best_method = 'kmeans'
            best_labels = kmeans_labels
            best_score = kmeans_silhouette
            if dbscan_silhouette > best_score:
                best_method = 'dbscan'
                best_labels = dbscan_labels
                best_score = dbscan_silhouette
            if hierarchical_silhouette > best_score:
                best_method = 'hierarchical'
                best_labels = hierarchical_labels
                best_score = hierarchical_silhouette
            # Analyze clusters
            cluster_analysis = self._analyze_clusters(scaled_features, best_labels, user_data)
            return {
                'method': best_method,
                'n_clusters': len(set(best_labels)) - (1 if -1 in best_labels else 0),
                'silhouette_score': float(best_score),
                'cluster_labels': best_labels.tolist(),
                'cluster_analysis': cluster_analysis,
                'cluster_characteristics': self._characterize_clusters(scaled_features, best_labels)
            }
        except Exception as e:
            logger.error(f"Behavioral cluster discovery failed: {str(e)}")
            return {'error': str(e)}
    def _discover_temporal_sequences(self, feature_matrix: np.ndarray, user_data: Dict) -> Dict:
        """Discover temporal sequences and patterns"""
        try:
            # Create sequences of consecutive time points
            sequence_length = min(24, len(feature_matrix) // 4)  # 24-hour sequences or 1/4 of data
            if sequence_length < 3:
                return {'error': 'Insufficient data for sequence analysis'}
            # Extract sequences
            sequences = []
            for i in range(len(feature_matrix) - sequence_length + 1):
                sequence = feature_matrix[i:i + sequence_length]
                sequences.append(sequence.flatten())
            if not sequences:
                return {'error': 'No sequences extracted'}
            sequences = np.array(sequences)
            # Cluster sequences to find common patterns
            scaler = StandardScaler()
            scaled_sequences = scaler.fit_transform(sequences)
            # Use K-means to find sequence patterns
            n_patterns = min(5, len(sequences) // 3)
            if n_patterns < 2:
                return {'error': 'Insufficient sequences for pattern analysis'}
            kmeans = KMeans(n_clusters=n_patterns, random_state=42, n_init=10)
            sequence_labels = kmeans.fit_predict(scaled_sequences)
            # Analyze sequence patterns
            pattern_analysis = {}
            for pattern_id in range(n_patterns):
                pattern_mask = sequence_labels == pattern_id
                pattern_sequences = sequences[pattern_mask]
                if len(pattern_sequences) > 0:
                    pattern_analysis[f'pattern_{pattern_id}'] = {
                        'frequency': int(np.sum(pattern_mask)),
                        'mean_sequence': np.mean(pattern_sequences, axis=0).tolist(),
                        'sequence_length': sequence_length,
                        'variability': float(np.std(pattern_sequences))
                    }
            return {
                'sequence_length': sequence_length,
                'n_patterns': n_patterns,
                'pattern_labels': sequence_labels.tolist(),
                'pattern_analysis': pattern_analysis,
                'temporal_regularity': self._calculate_temporal_regularity(sequence_labels)
            }
        except Exception as e:
            logger.error(f"Temporal sequence discovery failed: {str(e)}")
            return {'error': str(e)}
    def _discover_anomaly_patterns(self, feature_matrix: np.ndarray, user_data: Dict) -> Dict:
        """Discover anomaly patterns using ML techniques"""
        try:
            # Standardize features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(feature_matrix)
            # Isolation Forest for anomaly detection
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            anomaly_labels = iso_forest.fit_predict(scaled_features)
            anomaly_scores = iso_forest.decision_function(scaled_features)
            # Find anomalous points
            anomaly_indices = np.where(anomaly_labels == -1)[0]
            if len(anomaly_indices) == 0:
                return {'error': 'No anomalies detected'}
            # Cluster anomalies to find patterns
            if len(anomaly_indices) >= 3:
                anomaly_features = scaled_features[anomaly_indices]
                # Use DBSCAN to cluster anomalies
                dbscan = DBSCAN(eps=0.5, min_samples=2)
                anomaly_clusters = dbscan.fit_predict(anomaly_features)
                # Analyze anomaly clusters
                anomaly_pattern_analysis = {}
                unique_clusters = set(anomaly_clusters)
                for cluster_id in unique_clusters:
                    if cluster_id != -1:  # Ignore noise points
                        cluster_mask = anomaly_clusters == cluster_id
                        cluster_indices = anomaly_indices[cluster_mask]
                        anomaly_pattern_analysis[f'anomaly_cluster_{cluster_id}'] = {
                            'size': int(np.sum(cluster_mask)),
                            'anomaly_indices': cluster_indices.tolist(),
                            'mean_anomaly_score': float(np.mean(anomaly_scores[cluster_indices])),
                            'pattern_characteristics': self._characterize_anomaly_cluster(
                                scaled_features[cluster_indices]
                            )
                        }
            else:
                anomaly_pattern_analysis = {'insufficient_anomalies': True}
            return {
                'total_anomalies': len(anomaly_indices),
                'anomaly_rate': len(anomaly_indices) / len(feature_matrix),
                'anomaly_indices': anomaly_indices.tolist(),
                'anomaly_scores': anomaly_scores.tolist(),
                'anomaly_patterns': anomaly_pattern_analysis
            }
        except Exception as e:
            logger.error(f"Anomaly pattern discovery failed: {str(e)}")
            return {'error': str(e)}
    def _discover_response_patterns(self, user_id: str, feature_matrix: np.ndarray, user_data: Dict) -> Dict:
        """Discover patterns in response to interventions"""
        try:
            from app.models import Intervention
            # Get interventions for the user
            interventions = Intervention.query.filter_by(user_id=user_id).all()
            if not interventions:
                return {'error': 'No interventions found for response pattern analysis'}
            response_patterns = {}
            for intervention in interventions:
                if not intervention.started_at:
                    continue
                # Find metrics around intervention start
                intervention_patterns = self._analyze_intervention_response_pattern(
                    intervention, user_data, feature_matrix
                )
                if 'error' not in intervention_patterns:
                    response_patterns[f'intervention_{intervention.id}'] = intervention_patterns
            if not response_patterns:
                return {'error': 'No intervention response patterns found'}
            # Identify common response patterns across interventions
            common_patterns = self._identify_common_response_patterns(response_patterns)
            return {
                'individual_responses': response_patterns,
                'common_patterns': common_patterns,
                'response_consistency': self._calculate_response_consistency(response_patterns)
            }
        except Exception as e:
            logger.error(f"Response pattern discovery failed: {str(e)}")
            return {'error': str(e)}
    def _find_optimal_clusters(self, data: np.ndarray, max_clusters: int = 8) -> int:
        """Find optimal number of clusters using elbow method"""
        try:
            if len(data) < 4:
                return 2
            max_clusters = min(max_clusters, len(data) // 2)
            inertias = []
            silhouette_scores = []
            for k in range(2, max_clusters + 1):
                try:
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                    labels = kmeans.fit_predict(data)
                    inertias.append(kmeans.inertia_)
                    if len(set(labels)) > 1:
                        sil_score = silhouette_score(data, labels)
                        silhouette_scores.append(sil_score)
                    else:
                        silhouette_scores.append(0)
                except Exception:
                    break
            if not silhouette_scores:
                return 2
            # Find k with highest silhouette score
            optimal_k = np.argmax(silhouette_scores) + 2
            return optimal_k
        except Exception as e:
            logger.warning(f"Optimal cluster finding failed: {str(e)}")
            return 3  # Default
    def _analyze_clusters(self, features: np.ndarray, labels: np.ndarray, user_data: Dict) -> Dict:
        """Analyze characteristics of discovered clusters"""
        try:
            unique_labels = set(labels)
            if -1 in unique_labels:
                unique_labels.remove(-1)  # Remove noise cluster from DBSCAN
            cluster_analysis = {}
            for cluster_id in unique_labels:
                cluster_mask = labels == cluster_id
                cluster_features = features[cluster_mask]
                if len(cluster_features) > 0:
                    cluster_analysis[f'cluster_{cluster_id}'] = {
                        'size': int(np.sum(cluster_mask)),
                        'percentage': float(np.sum(cluster_mask) / len(labels) * 100),
                        'centroid': np.mean(cluster_features, axis=0).tolist(),
                        'std': np.std(cluster_features, axis=0).tolist(),
                        'compactness': float(np.mean(np.sum((cluster_features - np.mean(cluster_features, axis=0))**2, axis=1)))
                    }
            return cluster_analysis
        except Exception as e:
            logger.warning(f"Cluster analysis failed: {str(e)}")
            return {}
    def _characterize_clusters(self, features: np.ndarray, labels: np.ndarray) -> Dict:
        """Characterize clusters with interpretable descriptions"""
        try:
            unique_labels = set(labels)
            if -1 in unique_labels:
                unique_labels.remove(-1)
            characteristics = {}
            # Calculate global statistics for comparison
            global_mean = np.mean(features, axis=0)
            global_std = np.std(features, axis=0)
            for cluster_id in unique_labels:
                cluster_mask = labels == cluster_id
                cluster_features = features[cluster_mask]
                if len(cluster_features) > 0:
                    cluster_mean = np.mean(cluster_features, axis=0)
                    # Compare to global statistics
                    deviations = (cluster_mean - global_mean) / (global_std + 1e-8)
                    # Identify significant deviations (> 1 std)
                    significant_features = np.where(np.abs(deviations) > 1.0)[0]
                    characteristics[f'cluster_{cluster_id}'] = {
                        'distinctive_features': significant_features.tolist(),
                        'feature_deviations': deviations.tolist(),
                        'interpretation': self._interpret_cluster_characteristics(deviations)
                    }
            return characteristics
        except Exception as e:
            logger.warning(f"Cluster characterization failed: {str(e)}")
            return {}
    def _interpret_cluster_characteristics(self, deviations: np.ndarray) -> str:
        """Generate human-readable interpretation of cluster characteristics"""
        try:
            # This is a simplified interpretation - in practice, you'd map
            # feature indices to meaningful metric names and create rich descriptions
            high_features = np.where(deviations > 1.0)[0]
            low_features = np.where(deviations < -1.0)[0]
            if len(high_features) > len(low_features):
                return f"High activity pattern (elevated features: {len(high_features)})"
            elif len(low_features) > len(high_features):
                return f"Low activity pattern (reduced features: {len(low_features)})"
            else:
                return "Balanced pattern"
        except Exception:
            return "Pattern characteristics unclear"
    def _calculate_pattern_confidence(self, pattern_result: Dict) -> float:
        """Calculate confidence score for discovered pattern"""
        try:
            confidence_factors = []
            # Silhouette score (for clustering methods)
            if 'silhouette_score' in pattern_result:
                silhouette = pattern_result['silhouette_score']
                confidence_factors.append(min(1.0, max(0.0, (silhouette + 1) / 2)))  # Normalize -1,1 to 0,1
            # Pattern frequency/support
            if 'cluster_analysis' in pattern_result:
                cluster_analysis = pattern_result['cluster_analysis']
                if cluster_analysis:
                    # Use largest cluster as indicator of pattern strength
                    cluster_sizes = [info.get('size', 0) for info in cluster_analysis.values()]
                    if cluster_sizes:
                        max_cluster_size = max(cluster_sizes)
                        total_points = sum(cluster_sizes)
                        if total_points > 0:
                            confidence_factors.append(max_cluster_size / total_points)
            # Temporal regularity (for sequence patterns)
            if 'temporal_regularity' in pattern_result:
                confidence_factors.append(pattern_result['temporal_regularity'])
            # Response consistency (for intervention patterns)
            if 'response_consistency' in pattern_result:
                confidence_factors.append(pattern_result['response_consistency'])
            # Default confidence if no specific factors
            if not confidence_factors:
                confidence_factors.append(0.5)
            return float(np.mean(confidence_factors))
        except Exception as e:
            logger.warning(f"Pattern confidence calculation failed: {str(e)}")
            return 0.5
    def _store_pattern(self, user_id: str, pattern_type: str, pattern_result: Dict, confidence: float):
        """Store discovered pattern in database"""
        try:
            # Extract metrics involved
            metrics_involved = []
            if 'cluster_analysis' in pattern_result:
                metrics_involved = ['hrv', 'sleep_score', 'heart_rate']  # Simplified
            # Create pattern signature
            pattern_signature = {
                'type': pattern_type,
                'confidence': confidence,
                'characteristics': pattern_result.get('cluster_characteristics', {}),
                'analysis_summary': {
                    'method': pattern_result.get('method', 'unknown'),
                    'n_clusters': pattern_result.get('n_clusters', 0),
                    'silhouette_score': pattern_result.get('silhouette_score', 0)
                }
            }
            # Create pattern record
            pattern = Pattern(
                user_id=user_id,
                pattern_type=pattern_type,
                metrics_involved=metrics_involved,
                pattern_signature=pattern_signature,
                confidence_score=confidence,
                support_count=pattern_result.get('cluster_analysis', {}).get('cluster_0', {}).get('size', 0),
                discovered_at=datetime.utcnow(),
                last_observed=datetime.utcnow(),
                model_method=pattern_result.get('method', 'unknown'),
                model_parameters={}
            )
            db.session.add(pattern)
            db.session.commit()
            logger.info(f"Pattern stored for user {user_id}: {pattern_type} (confidence: {confidence:.2f})")
        except Exception as e:
            logger.error(f"Pattern storage failed: {str(e)}")
            db.session.rollback()
    def _generate_pattern_summary(self, pattern_results: Dict) -> Dict:
        """Generate summary of all discovered patterns"""
        try:
            discovered_patterns = pattern_results.get('discovered_patterns', {})
            confidence_scores = pattern_results.get('confidence_scores', {})
            summary = {
                'total_patterns_discovered': len(discovered_patterns),
                'high_confidence_patterns': 0,
                'pattern_types_found': list(discovered_patterns.keys()),
                'overall_pattern_strength': 0.0,
                'most_confident_pattern': None
            }
            if confidence_scores:
                # Count high confidence patterns
                summary['high_confidence_patterns'] = sum(
                    1 for conf in confidence_scores.values() if conf >= 0.7
                )
                # Calculate overall strength
                summary['overall_pattern_strength'] = float(np.mean(list(confidence_scores.values())))
                # Find most confident pattern
                most_confident = max(confidence_scores.items(), key=lambda x: x[1])
                summary['most_confident_pattern'] = {
                    'type': most_confident[0],
                    'confidence': most_confident[1]
                }
            return summary
        except Exception as e:
            logger.warning(f"Pattern summary generation failed: {str(e)}")
            return {}
    def _generate_pattern_recommendations(self, pattern_results: Dict) -> List[Dict]:
        """Generate actionable recommendations based on discovered patterns"""
        try:
            recommendations = []
            discovered_patterns = pattern_results.get('discovered_patterns', {})
            confidence_scores = pattern_results.get('confidence_scores', {})
            for pattern_type, pattern_data in discovered_patterns.items():
                confidence = confidence_scores.get(pattern_type, 0)
                if confidence >= 0.7:  # High confidence patterns only
                    if pattern_type == 'behavioral_cluster':
                        recommendations.append({
                            'type': 'behavioral_optimization',
                            'message': f"Strong behavioral patterns identified with {confidence:.1%} confidence",
                            'actionable': True,
                            'recommendation': "Leverage your consistent patterns to optimize health outcomes",
                            'confidence': confidence
                        })
                    elif pattern_type == 'temporal_sequence':
                        recommendations.append({
                            'type': 'timing_optimization',
                            'message': f"Consistent temporal patterns detected",
                            'actionable': True,
                            'recommendation': "Align interventions with your natural rhythms for better results",
                            'confidence': confidence
                        })
                    elif pattern_type == 'anomaly_pattern':
                        recommendations.append({
                            'type': 'anomaly_awareness',
                            'message': f"Recurring anomaly patterns found",
                            'actionable': True,
                            'recommendation': "Monitor these patterns to identify early warning signs",
                            'confidence': confidence
                        })
            return recommendations
        except Exception as e:
            logger.warning(f"Pattern recommendation generation failed: {str(e)}")
            return []
    # Helper methods (simplified implementations)
    def _calculate_temporal_regularity(self, sequence_labels: np.ndarray) -> float:
        """Calculate temporal regularity score"""
        try:
            # Simple regularity measure based on pattern repetition
            unique_patterns, counts = np.unique(sequence_labels, return_counts=True)
            if len(unique_patterns) <= 1:
                return 0.0
            # Entropy-based regularity (lower entropy = higher regularity)
            probabilities = counts / np.sum(counts)
            entropy = -np.sum(probabilities * np.log2(probabilities))
            max_entropy = np.log2(len(unique_patterns))
            regularity = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0
            return float(regularity)
        except Exception:
            return 0.0
    def _analyze_intervention_response_pattern(self, intervention, user_data: Dict, feature_matrix: np.ndarray) -> Dict:
        """Analyze response pattern for specific intervention"""
        try:
            # This is a simplified implementation
            # In practice, you'd analyze metrics before/after intervention start
            return {
                'intervention_id': intervention.id,
                'intervention_name': intervention.name,
                'response_detected': True,
                'response_strength': 0.6,  # Placeholder
                'response_timing': 'immediate'  # Placeholder
            }
        except Exception as e:
            return {'error': str(e)}
    def _identify_common_response_patterns(self, response_patterns: Dict) -> Dict:
        """Identify common patterns across interventions"""
        try:
            # Simplified implementation
            return {
                'common_response_timing': 'immediate',
                'consistent_responder': True,
                'response_variability': 0.3
            }
        except Exception:
            return {}
    def _calculate_response_consistency(self, response_patterns: Dict) -> float:
        """Calculate consistency of intervention responses"""
        try:
            if not response_patterns:
                return 0.0
            # Simplified consistency calculation
            response_strengths = []
            for pattern in response_patterns.values():
                if 'response_strength' in pattern:
                    response_strengths.append(pattern['response_strength'])
            if not response_strengths:
                return 0.0
            # Lower standard deviation = higher consistency
            consistency = 1.0 - (np.std(response_strengths) / np.mean(response_strengths)) if np.mean(response_strengths) > 0 else 0.0
            return float(max(0.0, min(1.0, consistency)))
        except Exception:
            return 0.0
    def _characterize_anomaly_cluster(self, anomaly_features: np.ndarray) -> Dict:
        """Characterize an anomaly cluster"""
        try:
            return {
                'cluster_size': len(anomaly_features),
                'mean_deviation': float(np.mean(np.abs(anomaly_features))),
                'max_deviation': float(np.max(np.abs(anomaly_features))),
                'anomaly_type': 'outlier_cluster'
            }
        except Exception:
            return {}