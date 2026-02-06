#!/usr/bin/env python3
"""
Test the real-time data mapping without database dependency
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from services.metrics_service import MetricsService

def test_real_time_mapping():
    """Test the new real-time data mapping functionality"""

    # Sample data similar to your old system
    sample_response = {
        "data": {
            "metric_data": [
                {
                    "type": "hr",
                    "object": {
                        "values": [
                            {"timestamp": 1725321600, "value": 72.0},
                            {"timestamp": 1725321660, "value": 74.0},
                            {"timestamp": 1725321720, "value": 71.0}
                        ],
                        "avg": 72.3,
                        "day_start_timestamp": 1725321600
                    }
                },
                {
                    "type": "hrv",
                    "object": {
                        "values": [
                            {"timestamp": 1725321600, "value": 42.0},
                            {"timestamp": 1725321660, "value": 45.0},
                            {"timestamp": 1725321720, "value": 41.0}
                        ],
                        "avg": 42.7,
                        "day_start_timestamp": 1725321600
                    }
                },
                {
                    "type": "temp",
                    "object": {
                        "values": [
                            {"timestamp": 1725321600, "value": 33.2},
                            {"timestamp": 1725321660, "value": 33.4},
                            {"timestamp": 1725321720, "value": 33.1}
                        ],
                        "day_start_timestamp": 1725321600
                    }
                },
                {
                    "type": "steps",
                    "object": {
                        "values": [
                            {"timestamp": 1725321600, "value": 150.0},
                            {"timestamp": 1725321660, "value": 200.0},
                            {"timestamp": 1725321720, "value": 175.0}
                        ],
                        "day_start_timestamp": 1725321600
                    }
                },
                {
                    "type": "Sleep",
                    "object": {
                        "hr_graph": {
                            "data": [
                                {"timestamp": 1725285600, "value": 60.0},
                                {"timestamp": 1725285660, "value": 58.0},
                                {"timestamp": 1725285720, "value": 62.0}
                            ]
                        },
                        "hrv_graph": {
                            "data": [
                                {"timestamp": 1725285600, "value": 48.0},
                                {"timestamp": 1725285660, "value": 50.0},
                                {"timestamp": 1725285720, "value": 47.0}
                            ]
                        },
                        "temp_graph": {
                            "data": [
                                {"timestamp": 1725285600, "value": 32.8},
                                {"timestamp": 1725285660, "value": 32.9},
                                {"timestamp": 1725285720, "value": 32.7}
                            ]
                        }
                    }
                }
            ]
        }
    }

    # Test the mapping
    service = MetricsService()
    result = service._map_partner_to_internal(sample_response)

    print("=== REAL-TIME DATA MAPPING TEST ===")
    print(f"Sleep data points: {len(result.get('sleep', []))}")
    print(f"Activity data points: {len(result.get('activity', []))}")
    print(f"HRV data points: {len(result.get('hrv', []))}")
    print(f"Recovery data points: {len(result.get('recovery', []))}")
    print(f"Series data points: {len(result.get('series', []))}")

    print("\n=== SERIES DATA BREAKDOWN ===")
    series_by_type = {}
    for item in result.get('series', []):
        metric_type = item.get('metric_type')
        series_by_type[metric_type] = series_by_type.get(metric_type, 0) + 1

    for metric_type, count in series_by_type.items():
        print(f"{metric_type}: {count} time-series points")

    print("\n=== SAMPLE SERIES DATA ===")
    for item in result.get('series', [])[:5]:  # Show first 5
        print(f"• {item['metric_type']}: {item['value']} {item['unit']} @ {item['timestamp']}")

    print("\n=== COMPARISON: OLD vs NEW ===")
    print("OLD SYSTEM:")
    print("- Daily aggregates only (e.g., 1 heart_rate value per day)")
    print("- Timestamps at midnight (2025-09-02 00:00:00)")
    print("- Lost granular patterns")

    print("\nNEW SYSTEM:")
    print(f"- Real-time data points: {len(result.get('series', []))} individual readings")
    print("- Actual timestamps from device")
    print("- Preserves intraday patterns and variability")

    return result

if __name__ == "__main__":
    test_real_time_mapping()