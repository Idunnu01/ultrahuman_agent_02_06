"""
Predictive modeling and forecasting for health metrics
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from scipy import stats
from typing import Dict, List, Tuple, Optional, Union
import logging
from datetime import datetime, timedelta

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logging.warning("statsmodels not available - advanced time series forecasting limited")

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logging.warning("tensorflow not available - LSTM forecasting not available")

from utils.cache import cache_statistical_analysis

logger = logging.getLogger(__name__)

class HealthForecaster:
    """Advanced forecasting engine for health metrics using multiple ML approaches"""

    def __init__(self):
        self.models = {
            'linear_regression': self._linear_forecast,
            'random_forest': self._random_forest_forecast,
            'gradient_boosting': self._gradient_boosting_forecast,
            'ensemble': self._ensemble_forecast
        }

        if STATSMODELS_AVAILABLE:
            self.models['arima'] = self._arima_forecast
            self.models['exponential_smoothing'] = self._exponential_smoothing_forecast

        if TENSORFLOW_AVAILABLE:
            self.models['lstm'] = self._lstm_forecast

        self.feature_engineering_methods = [
            'time_features',
            'lag_features',
            'rolling_statistics',
            'cyclical_features'
        ]

    @cache_statistical_analysis(expire_seconds=3600)
    def generate_forecasts(self, data: Dict, target_metric: str,
                          forecast_horizon: int = 7, models: Optional[List[str]] = None) -> Dict:
        """
        Generate forecasts for a target metric using multiple models

        Args:
            data: Dictionary with metric_type -> {'values': array, 'timestamps': array}
            target_metric: The metric to forecast
            forecast_horizon: Number of periods to forecast ahead
            models: List of models to use (None = all available)

        Returns:
            Dictionary with forecast results
        """
        try:
            if target_metric not in data:
                return {'error': f'Target metric {target_metric} not found in data'}

            if models is None:
                models = ['linear_regression', 'random_forest', 'ensemble']
                if STATSMODELS_AVAILABLE:
                    models.append('arima')
                if TENSORFLOW_AVAILABLE:
                    models.append('lstm')

            # Prepare data
            prepared_data = self._prepare_forecasting_data(data, target_metric)

            if 'error' in prepared_data:
                return prepared_data

            forecast_results = {
                'target_metric': target_metric,
                'forecast_horizon': forecast_horizon,
                'data_summary': prepared_data['data_summary'],
                'forecasts': {},
                'model_performance': {},
                'ensemble_forecast': {},
                'confidence_intervals': {},
                'forecast_timestamp': datetime.utcnow().isoformat()
            }

            # Generate forecasts with each model
            successful_forecasts = {}

            for model_name in models:
                if model_name in self.models:
                    try:
                        logger.info(f"Generating {model_name} forecast for {target_metric}")

                        model_result = self.models[model_name](
                            prepared_data, forecast_horizon
                        )

                        if 'error' not in model_result:
                            forecast_results['forecasts'][model_name] = model_result['forecast']
                            forecast_results['model_performance'][model_name] = model_result['performance']

                            if 'confidence_interval' in model_result:
                                forecast_results['confidence_intervals'][model_name] = model_result['confidence_interval']

                            successful_forecasts[model_name] = model_result
                        else:
                            logger.warning(f"Model {model_name} failed: {model_result['error']}")

                    except Exception as e:
                        logger.error(f"Model {model_name} error: {str(e)}")
                        continue

            # Create ensemble forecast if multiple models succeeded
            if len(successful_forecasts) >= 2:
                ensemble_result = self._create_ensemble_forecast(successful_forecasts, forecast_horizon)
                forecast_results['ensemble_forecast'] = ensemble_result

            # Add forecast evaluation
            forecast_results['evaluation'] = self._evaluate_forecast_quality(
                successful_forecasts, prepared_data
            )

            return forecast_results

        except Exception as e:
            logger.error(f"Forecasting failed: {str(e)}")
            return {'error': str(e)}

    def _prepare_forecasting_data(self, data: Dict, target_metric: str) -> Dict:
        """Prepare data for forecasting models"""
        try:
            target_data = data[target_metric]
            values = np.array(target_data['values'])
            timestamps = pd.to_datetime(target_data['timestamps'])

            # Remove NaN values
            valid_mask = ~np.isnan(values)
            clean_values = values[valid_mask]
            clean_timestamps = timestamps[valid_mask]

            if len(clean_values) < 14:
                return {'error': f'Insufficient data for forecasting: {len(clean_values)} points (minimum: 14)'}

            # Create time series
            time_series = pd.Series(clean_values, index=clean_timestamps)
            time_series = time_series.sort_index()

            # Generate features
            feature_matrix = self._engineer_features(data, target_metric, time_series)

            prepared_data = {
                'target_series': time_series,
                'target_values': clean_values,
                'timestamps': clean_timestamps,
                'feature_matrix': feature_matrix,
                'data_summary': {
                    'sample_size': len(clean_values),
                    'date_range': {
                        'start': clean_timestamps.min().isoformat(),
                        'end': clean_timestamps.max().isoformat()
                    },
                    'basic_stats': {
                        'mean': float(np.mean(clean_values)),
                        'std': float(np.std(clean_values)),
                        'min': float(np.min(clean_values)),
                        'max': float(np.max(clean_values))
                    }
                }
            }

            return prepared_data

        except Exception as e:
            return {'error': str(e)}

    def _engineer_features(self, data: Dict, target_metric: str, target_series: pd.Series) -> pd.DataFrame:
        """Engineer features for forecasting models"""
        try:
            features_df = pd.DataFrame(index=target_series.index)

            # Time-based features
            features_df['hour'] = target_series.index.hour
            features_df['day_of_week'] = target_series.index.dayofweek
            features_df['day_of_month'] = target_series.index.day
            features_df['month'] = target_series.index.month

            # Cyclical encoding
            features_df['hour_sin'] = np.sin(2 * np.pi * features_df['hour'] / 24)
            features_df['hour_cos'] = np.cos(2 * np.pi * features_df['hour'] / 24)
            features_df['dow_sin'] = np.sin(2 * np.pi * features_df['day_of_week'] / 7)
            features_df['dow_cos'] = np.cos(2 * np.pi * features_df['day_of_week'] / 7)

            # Lag features
            for lag in [1, 2, 3, 7]:
                if len(target_series) > lag:
                    features_df[f'lag_{lag}'] = target_series.shift(lag)

            # Rolling statistics
            for window in [3, 7]:
                if len(target_series) > window:
                    features_df[f'rolling_mean_{window}'] = target_series.rolling(window=window).mean()
                    features_df[f'rolling_std_{window}'] = target_series.rolling(window=window).std()

            # Add other metrics as features
            for metric_type, metric_data in data.items():
                if metric_type == target_metric:
                    continue

                try:
                    other_values = np.array(metric_data['values'])
                    other_timestamps = pd.to_datetime(metric_data['timestamps'])

                    # Remove NaN
                    valid_mask = ~np.isnan(other_values)
                    other_clean_values = other_values[valid_mask]
                    other_clean_timestamps = other_timestamps[valid_mask]

                    if len(other_clean_values) > 0:
                        other_series = pd.Series(other_clean_values, index=other_clean_timestamps)

                        # Align to target series timestamps
                        aligned_series = other_series.reindex(target_series.index, method='nearest')
                        features_df[f'{metric_type}_value'] = aligned_series

                        # Add lag of other metric
                        if len(aligned_series) > 1:
                            features_df[f'{metric_type}_lag1'] = aligned_series.shift(1)

                except Exception as e:
                    logger.warning(f"Failed to add {metric_type} as feature: {str(e)}")
                    continue

            # Fill missing values
            features_df = features_df.fillna(method='ffill').fillna(method='bfill')

            return features_df

        except Exception as e:
            logger.error(f"Feature engineering failed: {str(e)}")
            return pd.DataFrame()

    def _linear_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """Linear regression forecast"""
        try:
            target_series = prepared_data['target_series']
            feature_matrix = prepared_data['feature_matrix']

            if feature_matrix.empty:
                # Simple linear trend forecast
                time_values = np.arange(len(target_series))
                target_values = target_series.values

                # Fit linear trend
                slope, intercept, r_value, p_value, std_err = stats.linregress(time_values, target_values)

                # Generate forecast
                future_times = np.arange(len(target_series), len(target_series) + forecast_horizon)
                forecast_values = slope * future_times + intercept

                # Calculate prediction intervals
                residuals = target_values - (slope * time_values + intercept)
                residual_std = np.std(residuals)

                return {
                    'forecast': forecast_values.tolist(),
                    'performance': {
                        'r_squared': float(r_value**2),
                        'rmse': float(residual_std),
                        'method': 'simple_linear_trend'
                    },
                    'confidence_interval': {
                        'lower': (forecast_values - 1.96 * residual_std).tolist(),
                        'upper': (forecast_values + 1.96 * residual_std).tolist()
                    }
                }

            # Use features for multivariate linear regression
            X = feature_matrix.dropna()
            y = target_series.loc[X.index]

            if len(X) < 10:
                return {'error': 'Insufficient data after feature engineering'}

            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Fit model
            model = Ridge(alpha=1.0)
            model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = model.predict(X_test_scaled)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)

            # Generate forecast (simplified - assumes last features repeat)
            last_features = X.iloc[-1].values.reshape(1, -1)
            last_features_scaled = scaler.transform(last_features)

            forecast_values = []
            for _ in range(forecast_horizon):
                pred = model.predict(last_features_scaled)[0]
                forecast_values.append(pred)

            return {
                'forecast': forecast_values,
                'performance': {
                    'rmse': float(rmse),
                    'r_squared': float(r2),
                    'mae': float(mean_absolute_error(y_test, y_pred)),
                    'method': 'multivariate_linear_regression'
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _random_forest_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """Random Forest forecast"""
        try:
            target_series = prepared_data['target_series']
            feature_matrix = prepared_data['feature_matrix']

            if feature_matrix.empty:
                return {'error': 'No features available for Random Forest'}

            X = feature_matrix.dropna()
            y = target_series.loc[X.index]

            if len(X) < 10:
                return {'error': 'Insufficient data for Random Forest'}

            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            # Fit Random Forest
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)

            # Feature importance
            feature_importance = dict(zip(X.columns, model.feature_importances_))

            # Generate forecast
            last_features = X.iloc[-1].values.reshape(1, -1)
            forecast_values = []

            for _ in range(forecast_horizon):
                pred = model.predict(last_features)[0]
                forecast_values.append(pred)

            return {
                'forecast': forecast_values,
                'performance': {
                    'rmse': float(rmse),
                    'r_squared': float(r2),
                    'mae': float(mean_absolute_error(y_test, y_pred)),
                    'feature_importance': feature_importance,
                    'method': 'random_forest'
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _gradient_boosting_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """Gradient Boosting forecast"""
        try:
            target_series = prepared_data['target_series']
            feature_matrix = prepared_data['feature_matrix']

            if feature_matrix.empty:
                return {'error': 'No features available for Gradient Boosting'}

            X = feature_matrix.dropna()
            y = target_series.loc[X.index]

            if len(X) < 10:
                return {'error': 'Insufficient data for Gradient Boosting'}

            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            # Fit Gradient Boosting
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)

            # Generate forecast
            last_features = X.iloc[-1].values.reshape(1, -1)
            forecast_values = []

            for _ in range(forecast_horizon):
                pred = model.predict(last_features)[0]
                forecast_values.append(pred)

            return {
                'forecast': forecast_values,
                'performance': {
                    'rmse': float(rmse),
                    'r_squared': float(r2),
                    'mae': float(mean_absolute_error(y_test, y_pred)),
                    'method': 'gradient_boosting'
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _arima_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """ARIMA time series forecast"""
        try:
            if not STATSMODELS_AVAILABLE:
                return {'error': 'statsmodels not available'}

            target_series = prepared_data['target_series']

            if len(target_series) < 20:
                return {'error': 'Insufficient data for ARIMA (minimum: 20 points)'}

            # Simple ARIMA(1,1,1) model
            try:
                model = ARIMA(target_series, order=(1, 1, 1))
                fitted_model = model.fit()

                # Generate forecast
                forecast_result = fitted_model.forecast(steps=forecast_horizon)
                forecast_values = forecast_result.tolist()

                # Get confidence intervals
                conf_int = fitted_model.get_forecast(steps=forecast_horizon).conf_int()

                return {
                    'forecast': forecast_values,
                    'performance': {
                        'aic': float(fitted_model.aic),
                        'bic': float(fitted_model.bic),
                        'method': 'arima_111'
                    },
                    'confidence_interval': {
                        'lower': conf_int.iloc[:, 0].tolist(),
                        'upper': conf_int.iloc[:, 1].tolist()
                    }
                }

            except Exception as arima_error:
                # Fallback to simpler model
                logger.warning(f"ARIMA(1,1,1) failed, trying simpler model: {str(arima_error)}")

                try:
                    model = ARIMA(target_series, order=(0, 1, 1))
                    fitted_model = model.fit()

                    forecast_result = fitted_model.forecast(steps=forecast_horizon)
                    forecast_values = forecast_result.tolist()

                    return {
                        'forecast': forecast_values,
                        'performance': {
                            'aic': float(fitted_model.aic),
                            'bic': float(fitted_model.bic),
                            'method': 'arima_011_fallback'
                        }
                    }

                except Exception as fallback_error:
                    return {'error': f'ARIMA failed: {str(fallback_error)}'}

        except Exception as e:
            return {'error': str(e)}

    def _exponential_smoothing_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """Exponential smoothing forecast"""
        try:
            if not STATSMODELS_AVAILABLE:
                return {'error': 'statsmodels not available'}

            target_series = prepared_data['target_series']

            if len(target_series) < 10:
                return {'error': 'Insufficient data for exponential smoothing'}

            # Simple exponential smoothing
            model = ETSModel(target_series, error='add', trend='add', seasonal=None)
            fitted_model = model.fit()

            # Generate forecast
            forecast_result = fitted_model.forecast(steps=forecast_horizon)
            forecast_values = forecast_result.tolist()

            return {
                'forecast': forecast_values,
                'performance': {
                    'aic': float(fitted_model.aic),
                    'method': 'exponential_smoothing'
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _lstm_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """LSTM neural network forecast"""
        try:
            if not TENSORFLOW_AVAILABLE:
                return {'error': 'tensorflow not available'}

            target_values = prepared_data['target_values']

            if len(target_values) < 30:
                return {'error': 'Insufficient data for LSTM (minimum: 30 points)'}

            # Prepare sequences
            sequence_length = 10
            X, y = self._create_lstm_sequences(target_values, sequence_length)

            if len(X) < 10:
                return {'error': 'Insufficient sequences for LSTM training'}

            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Build LSTM model
            model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(sequence_length, 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])

            model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')

            # Train model
            model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=0)

            # Evaluate
            y_pred = model.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            # Generate forecast
            last_sequence = target_values[-sequence_length:].reshape(1, sequence_length, 1)
            forecast_values = []

            for _ in range(forecast_horizon):
                pred = model.predict(last_sequence, verbose=0)[0, 0]
                forecast_values.append(float(pred))

                # Update sequence for next prediction
                last_sequence = np.roll(last_sequence, -1, axis=1)
                last_sequence[0, -1, 0] = pred

            return {
                'forecast': forecast_values,
                'performance': {
                    'rmse': float(rmse),
                    'method': 'lstm'
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _create_lstm_sequences(self, data: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X, y = [], []
        for i in range(len(data) - sequence_length):
            X.append(data[i:(i + sequence_length)])
            y.append(data[i + sequence_length])

        X = np.array(X).reshape(-1, sequence_length, 1)
        y = np.array(y)

        return X, y

    def _ensemble_forecast(self, prepared_data: Dict, forecast_horizon: int) -> Dict:
        """Ensemble forecast combining multiple models"""
        try:
            # Run multiple models
            models_to_use = ['linear_regression', 'random_forest']
            if STATSMODELS_AVAILABLE:
                models_to_use.append('arima')

            individual_forecasts = {}
            weights = {}

            for model_name in models_to_use:
                if model_name in self.models:
                    try:
                        result = self.models[model_name](prepared_data, forecast_horizon)
                        if 'error' not in result:
                            individual_forecasts[model_name] = result['forecast']

                            # Weight based on performance (inverse of RMSE)
                            rmse = result['performance'].get('rmse', 1.0)
                            weights[model_name] = 1.0 / (rmse + 1e-8)
                    except Exception:
                        continue

            if len(individual_forecasts) < 2:
                return {'error': 'Insufficient models for ensemble'}

            # Normalize weights
            total_weight = sum(weights.values())
            normalized_weights = {k: v/total_weight for k, v in weights.items()}

            # Create weighted ensemble
            ensemble_forecast = np.zeros(forecast_horizon)

            for model_name, forecast in individual_forecasts.items():
                weight = normalized_weights[model_name]
                ensemble_forecast += weight * np.array(forecast)

            return {
                'forecast': ensemble_forecast.tolist(),
                'performance': {
                    'ensemble_weights': normalized_weights,
                    'models_used': list(individual_forecasts.keys()),
                    'method': 'weighted_ensemble'
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def _create_ensemble_forecast(self, successful_forecasts: Dict, forecast_horizon: int) -> Dict:
        """Create ensemble from successful individual forecasts"""
        try:
            forecasts = []
            weights = []
            model_names = []

            for model_name, result in successful_forecasts.items():
                forecasts.append(result['forecast'])

                # Weight based on R² or inverse RMSE
                performance = result['performance']
                if 'r_squared' in performance:
                    weight = performance['r_squared']
                elif 'rmse' in performance:
                    weight = 1.0 / (performance['rmse'] + 1e-8)
                else:
                    weight = 1.0

                weights.append(weight)
                model_names.append(model_name)

            # Normalize weights
            weights = np.array(weights)
            weights = weights / np.sum(weights)

            # Create weighted average
            ensemble_forecast = np.average(forecasts, axis=0, weights=weights)

            return {
                'forecast': ensemble_forecast.tolist(),
                'weights': dict(zip(model_names, weights.tolist())),
                'models_used': model_names,
                'method': 'ensemble'
            }

        except Exception as e:
            logger.error(f"Ensemble creation failed: {str(e)}")
            return {'error': str(e)}

    def _evaluate_forecast_quality(self, successful_forecasts: Dict, prepared_data: Dict) -> Dict:
        """Evaluate overall forecast quality"""
        try:
            evaluation = {
                'models_successful': len(successful_forecasts),
                'average_performance': {},
                'best_model': None,
                'forecast_confidence': 'medium'
            }

            if not successful_forecasts:
                evaluation['forecast_confidence'] = 'low'
                return evaluation

            # Calculate average performance metrics
            rmse_values = []
            r2_values = []

            best_r2 = -1
            best_model = None

            for model_name, result in successful_forecasts.items():
                performance = result['performance']

                if 'rmse' in performance:
                    rmse_values.append(performance['rmse'])

                if 'r_squared' in performance:
                    r2_values.append(performance['r_squared'])

                    if performance['r_squared'] > best_r2:
                        best_r2 = performance['r_squared']
                        best_model = model_name

            if rmse_values:
                evaluation['average_performance']['mean_rmse'] = float(np.mean(rmse_values))

            if r2_values:
                evaluation['average_performance']['mean_r_squared'] = float(np.mean(r2_values))

                # Determine confidence based on R²
                mean_r2 = np.mean(r2_values)
                if mean_r2 >= 0.7:
                    evaluation['forecast_confidence'] = 'high'
                elif mean_r2 >= 0.4:
                    evaluation['forecast_confidence'] = 'medium'
                else:
                    evaluation['forecast_confidence'] = 'low'

            evaluation['best_model'] = best_model

            return evaluation

        except Exception as e:
            logger.error(f"Forecast evaluation failed: {str(e)}")
            return {'error': str(e)}