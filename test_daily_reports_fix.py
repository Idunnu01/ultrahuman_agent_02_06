#!/usr/bin/env python3
"""
Test script to verify the daily reports fixes
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_json_serialization():
    """Test JSON serialization with various data types"""

    print("🧪 Testing JSON Serialization")
    print("=" * 40)

    # Test data with potential issues
    test_data = {
        'normal_value': 42,
        'nan_value': np.nan,
        'inf_value': np.inf,
        'datetime_value': datetime.now(),
        'timedelta_value': timedelta(hours=2),
        'numpy_array': np.array([1, 2, 3]),
        'pandas_series': pd.Series([1, 2, np.nan, 4]),
        'nested_dict': {
            'inner_nan': np.nan,
            'inner_inf': np.inf
        }
    }

    try:
        # Test the safe serialization
        from services.statistical_analyzer import safe_json_serialize

        serialized = safe_json_serialize(test_data)
        json_str = json.dumps(serialized, indent=2)

        print("✅ JSON serialization successful!")
        print(f"📏 Serialized length: {len(json_str)} characters")
        print("📊 Sample of serialized data:")
        print(json.dumps(serialized, indent=2)[:500] + "...")

        return True

    except Exception as e:
        print(f"❌ JSON serialization failed: {str(e)}")
        return False

def test_weekly_pattern():
    """Test weekly pattern calculation"""

    print("\n🧪 Testing Weekly Pattern Calculation")
    print("=" * 40)

    try:
        # Create test data
        dates = pd.date_range('2024-01-01', periods=7, freq='D')
        values = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0])

        from services.statistical_analyzer import StatisticalAnalyzer

        analyzer = StatisticalAnalyzer()
        pattern = analyzer._calculate_weekly_pattern(values, dates)

        print("✅ Weekly pattern calculation successful!")
        print(f"📊 Pattern keys: {list(pattern.keys())}")

        # Test JSON serialization
        json_str = json.dumps(pattern, indent=2)
        print(f"📏 JSON length: {len(json_str)} characters")

        return True

    except Exception as e:
        print(f"❌ Weekly pattern test failed: {str(e)}")
        return False

def main():
    print("Daily Reports Fix Verification")
    print("=" * 60)

    success1 = test_json_serialization()
    success2 = test_weekly_pattern()

    if success1 and success2:
        print("\n" + "=" * 60)
        print("🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ JSON serialization working")
        print("✅ Weekly pattern calculation working")
        print("✅ Daily reports should now work properly")
        print("🎯 Ready to run daily reports again!")
    else:
        print("\n❌ Some fixes still need attention")

    return success1 and success2

if __name__ == "__main__":
    main()
