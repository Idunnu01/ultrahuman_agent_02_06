#!/usr/bin/env python3
"""
Enhanced Metric Lookup - Combines old system's comprehensive mapping with current SQLAlchemy setup
Bridges the gap between your old SQL Server system and current MySQL implementation
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy import func, text, and_, or_
from app.models import Metric, User
from utils.database import db

logger = logging.getLogger(__name__)

class EnhancedMetricLookup:
    """Enhanced metric lookup system combining old system capabilities with current database"""

    def __init__(self):
        # Enhanced metric mapping based on your old system but adapted for current schema
        self.comprehensive_metric_map = {
            # Heart Rate metrics
            "heart_rate": {
                "primary_types": ["heart_rate", "resting_heart_rate", "hr"],
                "fallback_types": ["avg_heart_rate", "sleep_hr"],
                "unit": "bpm",
                "description": "Heart rate measurements"
            },
            "resting_heart_rate": {
                "primary_types": ["resting_heart_rate", "sleep_rhr", "night_rhr"],
                "fallback_types": ["heart_rate"],
                "unit": "bpm",
                "description": "Resting heart rate"
            },

            # HRV metrics
            "hrv": {
                "primary_types": ["hrv", "heart_rate_variability"],
                "fallback_types": ["avg_sleep_hrv", "sleep_hrv"],
                "unit": "ms",
                "description": "Heart rate variability"
            },
            "avg_sleep_hrv": {
                "primary_types": ["avg_sleep_hrv", "sleep_hrv"],
                "fallback_types": ["hrv"],
                "unit": "ms",
                "description": "Average HRV during sleep"
            },

            # Sleep metrics
            "sleep_score": {
                "primary_types": ["sleep_score"],
                "fallback_types": ["total_sleep_score", "sleep_quality"],
                "unit": "score",
                "description": "Overall sleep quality score"
            },
            "sleep_efficiency": {
                "primary_types": ["sleep_efficiency"],
                "fallback_types": ["sleep_score"],
                "unit": "%",
                "description": "Sleep efficiency percentage"
            },
            "total_sleep_seconds": {
                "primary_types": ["total_sleep_seconds", "sleep_duration"],
                "fallback_types": ["duration_seconds"],
                "unit": "seconds",
                "description": "Total sleep duration"
            },
            "time_in_bed_seconds": {
                "primary_types": ["time_in_bed_seconds"],
                "fallback_types": ["total_sleep_seconds"],
                "unit": "seconds",
                "description": "Time spent in bed"
            },

            # Sleep stages (like your old system)
            "deep_sleep": {
                "primary_types": ["deep_sleep_seconds", "deep_sleep_minutes"],
                "fallback_types": ["deep_sleep_percentage"],
                "unit": "seconds",
                "description": "Deep sleep duration"
            },
            "light_sleep": {
                "primary_types": ["light_sleep_seconds", "light_sleep_minutes"],
                "fallback_types": ["light_sleep_percentage"],
                "unit": "seconds",
                "description": "Light sleep duration"
            },
            "rem_sleep": {
                "primary_types": ["rem_sleep_seconds", "rem_sleep_minutes"],
                "fallback_types": ["rem_sleep_percentage"],
                "unit": "seconds",
                "description": "REM sleep duration"
            },
            "awake_stage": {
                "primary_types": ["awake_seconds", "awake_minutes"],
                "fallback_types": ["awake_percentage"],
                "unit": "seconds",
                "description": "Time awake during sleep period"
            },

            # Recovery and wellness
            "recovery": {
                "primary_types": ["recovery", "recovery_score", "recovery_index"],
                "fallback_types": ["readiness", "wellness_score"],
                "unit": "score",
                "description": "Recovery readiness score"
            },
            "movement_index": {
                "primary_types": ["movement_index", "activity_score"],
                "fallback_types": ["active_minutes"],
                "unit": "index",
                "description": "Movement activity index"
            },

            # Temperature
            "temperature": {
                "primary_types": ["temperature", "body_temperature", "temp"],
                "fallback_types": ["skin_temperature"],
                "unit": "°C",
                "description": "Body temperature"
            },

            # Activity metrics
            "steps": {
                "primary_types": ["steps", "step_count"],
                "fallback_types": ["daily_steps"],
                "unit": "steps",
                "description": "Step count"
            },
            "active_minutes": {
                "primary_types": ["active_minutes", "activity_minutes"],
                "fallback_types": ["movement_minutes"],
                "unit": "minutes",
                "description": "Active minutes"
            },
            "calories_burned": {
                "primary_types": ["calories_burned", "calories"],
                "fallback_types": ["energy_expenditure"],
                "unit": "kcal",
                "description": "Calories burned"
            },

            # Fitness metrics
            "vo2_max": {
                "primary_types": ["vo2_max", "vo2max"],
                "fallback_types": ["cardio_fitness"],
                "unit": "ml/kg/min",
                "description": "VO2 max fitness level"
            },

            # Stress
            "stress": {
                "primary_types": ["stress", "stress_index", "stress_score"],
                "fallback_types": ["hrv_stress"],
                "unit": "index",
                "description": "Stress level index"
            },

            # Metabolic metrics (like your old system)
            "glucose": {
                "primary_types": ["glucose", "blood_glucose"],
                "fallback_types": ["average_glucose"],
                "unit": "mg/dL",
                "description": "Blood glucose level"
            },
            "average_glucose": {
                "primary_types": ["average_glucose", "glucose_average"],
                "fallback_types": ["glucose"],
                "unit": "mg/dL",
                "description": "Average blood glucose"
            },
            "glucose_variability": {
                "primary_types": ["glucose_variability", "glycemic_variability"],
                "fallback_types": [],
                "unit": "CV%",
                "description": "Glucose variability"
            },
            "hba1c": {
                "primary_types": ["hba1c", "a1c"],
                "fallback_types": [],
                "unit": "%",
                "description": "Hemoglobin A1C"
            },
            "time_in_target": {
                "primary_types": ["time_in_target", "time_in_range"],
                "fallback_types": [],
                "unit": "%",
                "description": "Time in target glucose range"
            },
            "metabolic_score": {
                "primary_types": ["metabolic_score"],
                "fallback_types": ["glucose_score"],
                "unit": "score",
                "description": "Metabolic health score"
            }
        }

        # Sleep component scores (like your old system)
        self.sleep_component_scores = {
            "timing_score": ["timing_score", "sleep_timing"],
            "temperature_score": ["temperature_score", "sleep_temperature"],
            "restoration_time_score": ["restoration_time_score", "restoration_score"],
            "restfulness_score": ["restfulness_score"],
            "hr_drop_score": ["hr_drop_score", "heart_rate_drop"],
            "consistency_score": ["consistency_score", "sleep_consistency"],
            "total_sleep_score": ["total_sleep_score", "sleep_duration_score"],
            "efficiency_score": ["efficiency_score", "sleep_efficiency_score"]
        }

    def fetch_metrics_enhanced(self, user_id: str, metric_name: str,
                              start: Optional[datetime] = None,
                              end: Optional[datetime] = None,
                              limit: Optional[int] = None) -> List[Tuple[datetime, float]]:
        """
        Enhanced version of your old fetch_metrics function
        Returns list of (timestamp, value) tuples sorted descending
        """
        try:
            # Get metric configuration
            metric_config = self.comprehensive_metric_map.get(metric_name)
            if not metric_config:
                # Try sleep component scores
                if metric_name in self.sleep_component_scores:
                    metric_types = self.sleep_component_scores[metric_name]
                else:
                    # Fallback to original name
                    metric_types = [metric_name]
            else:
                # Use primary types first, then fallbacks
                metric_types = metric_config["primary_types"] + metric_config["fallback_types"]

            # Build query
            query = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type.in_(metric_types),
                Metric.value.isnot(None)
            )

            # Add date filters
            if start:
                query = query.filter(Metric.timestamp >= start)
            if end:
                query = query.filter(Metric.timestamp < end)

            # Order by timestamp descending (like your old system)
            query = query.order_by(Metric.timestamp.desc())

            # Apply limit
            if limit:
                query = query.limit(limit)

            # Execute and return tuples
            results = query.all()
            return [(metric.timestamp, float(metric.value)) for metric in results]

        except Exception as e:
            logger.error(f"Enhanced fetch_metrics failed for {metric_name}: {str(e)}")
            return []

    def fetch_metrics_aggregate_enhanced(self, user_id: str, metric_name: str,
                                       aggregation: str, start_date: str,
                                       end_date: str) -> Optional[float]:
        """
        Enhanced aggregation with comprehensive metric mapping
        """
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date

            # Get metric types to search
            metric_config = self.comprehensive_metric_map.get(metric_name)
            if metric_config:
                # Try primary types first
                primary_result = self._try_aggregation(
                    user_id, metric_config["primary_types"], aggregation, start_dt, end_dt
                )
                if primary_result is not None:
                    return primary_result

                # Fallback to secondary types
                if metric_config["fallback_types"]:
                    return self._try_aggregation(
                        user_id, metric_config["fallback_types"], aggregation, start_dt, end_dt
                    )
            else:
                # Try sleep component scores
                if metric_name in self.sleep_component_scores:
                    metric_types = self.sleep_component_scores[metric_name]
                    return self._try_aggregation(user_id, metric_types, aggregation, start_dt, end_dt)

                # Last resort - try the metric name directly
                return self._try_aggregation(user_id, [metric_name], aggregation, start_dt, end_dt)

            return None

        except Exception as e:
            logger.error(f"Enhanced aggregation failed for {metric_name}: {str(e)}")
            return None

    def _try_aggregation(self, user_id: str, metric_types: List[str],
                        aggregation: str, start_dt: datetime, end_dt: datetime) -> Optional[float]:
        """Try aggregation with specific metric types"""
        try:
            query = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type.in_(metric_types),
                Metric.timestamp >= start_dt,
                Metric.timestamp < end_dt,
                Metric.value.isnot(None)
            )

            if aggregation == "average":
                result = query.with_entities(func.avg(Metric.value)).scalar()
            elif aggregation == "min":
                result = query.with_entities(func.min(Metric.value)).scalar()
            elif aggregation == "max":
                result = query.with_entities(func.max(Metric.value)).scalar()
            elif aggregation == "sum":
                result = query.with_entities(func.sum(Metric.value)).scalar()
            elif aggregation == "latest":
                latest_metric = query.order_by(Metric.timestamp.desc()).first()
                result = latest_metric.value if latest_metric else None
            elif aggregation == "count":
                result = query.count()
            else:
                logger.warning(f"Unknown aggregation type: {aggregation}")
                return None

            return float(result) if result is not None else None

        except Exception as e:
            logger.error(f"Aggregation attempt failed: {str(e)}")
            return None

    def get_available_metrics_for_user(self, user_id: str,
                                     days_back: int = 30) -> Dict[str, Dict]:
        """
        Get available metrics for a user (like your old system's comprehensive view)
        """
        try:
            # Get cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Query all metric types for user in the time period
            available_metrics = db.session.query(
                Metric.metric_type,
                func.count(Metric.id).label('count'),
                func.min(Metric.timestamp).label('earliest'),
                func.max(Metric.timestamp).label('latest'),
                func.avg(Metric.value).label('avg_value'),
                func.min(Metric.value).label('min_value'),
                func.max(Metric.value).label('max_value')
            ).filter(
                Metric.user_id == user_id,
                Metric.timestamp >= cutoff_date,
                Metric.value.isnot(None)
            ).group_by(Metric.metric_type).all()

            result = {}
            for metric in available_metrics:
                # Find the enhanced mapping for this metric type
                enhanced_name = None
                unit = "units"
                description = f"{metric.metric_type} measurements"

                for name, config in self.comprehensive_metric_map.items():
                    if metric.metric_type in config["primary_types"] + config["fallback_types"]:
                        enhanced_name = name
                        unit = config["unit"]
                        description = config["description"]
                        break

                result[enhanced_name or metric.metric_type] = {
                    "raw_type": metric.metric_type,
                    "count": metric.count,
                    "date_range": {
                        "earliest": metric.earliest.isoformat(),
                        "latest": metric.latest.isoformat()
                    },
                    "stats": {
                        "average": round(float(metric.avg_value), 2),
                        "min": round(float(metric.min_value), 2),
                        "max": round(float(metric.max_value), 2)
                    },
                    "unit": unit,
                    "description": description
                }

            return result

        except Exception as e:
            logger.error(f"Get available metrics failed: {str(e)}")
            return {}

    def get_metric_info(self, metric_name: str) -> Optional[Dict]:
        """Get information about a specific metric"""
        config = self.comprehensive_metric_map.get(metric_name)
        if config:
            return {
                "name": metric_name,
                "primary_types": config["primary_types"],
                "fallback_types": config["fallback_types"],
                "unit": config["unit"],
                "description": config["description"]
            }

        # Check sleep component scores
        if metric_name in self.sleep_component_scores:
            return {
                "name": metric_name,
                "primary_types": self.sleep_component_scores[metric_name],
                "fallback_types": [],
                "unit": "score",
                "description": f"{metric_name.replace('_', ' ').title()}"
            }

        return None

# Test function
def test_enhanced_lookup():
    """Test the enhanced lookup system"""

    print("🧪 TESTING ENHANCED METRIC LOOKUP")
    print("=" * 50)

    try:
        from app import create_app

        app = create_app()
        with app.app_context():

            lookup = EnhancedMetricLookup()

            # Get first user for testing
            user = User.query.first()
            if not user:
                print("❌ No users found")
                return

            print(f"Testing with user: {user.id}")

            # Test available metrics
            print(f"\n📊 AVAILABLE METRICS:")
            available = lookup.get_available_metrics_for_user(user.id)

            for metric_name, info in available.items():
                print(f"  ✅ {metric_name}: {info['count']} records ({info['unit']})")
                print(f"     📈 Stats: avg={info['stats']['average']}, min={info['stats']['min']}, max={info['stats']['max']}")
                print(f"     📅 Range: {info['date_range']['earliest'][:10]} to {info['date_range']['latest'][:10]}")

            # Test enhanced aggregation
            print(f"\n🧮 TESTING ENHANCED AGGREGATION:")
            test_metrics = ["heart_rate", "hrv", "sleep_score", "temperature"]
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            for metric in test_metrics:
                result = lookup.fetch_metrics_aggregate_enhanced(
                    user.id, metric, "average",
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )

                if result is not None:
                    info = lookup.get_metric_info(metric)
                    unit = info["unit"] if info else "units"
                    print(f"  ✅ {metric}: {result:.2f} {unit}")
                else:
                    print(f"  ❌ {metric}: No data")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_lookup()