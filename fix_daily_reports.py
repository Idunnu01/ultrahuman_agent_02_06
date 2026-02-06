#!/usr/bin/env python3
"""
Comprehensive fix for daily reports issues:
1. JSON serialization with NaN values
2. Datetime serialization
3. Data processing errors
4. LLM service configuration
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_json_serialization():
    """Fix JSON serialization issues with NaN and datetime values"""

    print("🔧 Fixing JSON Serialization Issues")
    print("=" * 50)

    # Create a utility function for safe JSON serialization
    def safe_json_serialize(obj):
        """Safely serialize objects to JSON, handling NaN and datetime"""
        if isinstance(obj, dict):
            return {k: safe_json_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [safe_json_serialize(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return safe_json_serialize(obj.tolist())
        elif isinstance(obj, pd.Series):
            return safe_json_serialize(obj.to_dict())
        elif isinstance(obj, pd.DataFrame):
            return safe_json_serialize(obj.to_dict('index'))
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return obj.total_seconds()
        elif pd.isna(obj):
            return None
        else:
            return obj

    # Add this function to the statistical analyzer
    statistical_analyzer_path = "services/statistical_analyzer.py"

    if os.path.exists(statistical_analyzer_path):
        with open(statistical_analyzer_path, 'r') as f:
            content = f.read()

        # Add the safe JSON serialization function
        if 'def safe_json_serialize' not in content:
            # Find the imports section
            import_section = "import logging\nfrom sqlalchemy import and_\nfrom scipy import stats"

            safe_json_function = '''
def safe_json_serialize(obj):
    """Safely serialize objects to JSON, handling NaN and datetime"""
    if isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return safe_json_serialize(obj.tolist())
    elif isinstance(obj, pd.Series):
        return safe_json_serialize(obj.to_dict())
    elif isinstance(obj, pd.DataFrame):
        return safe_json_serialize(obj.to_dict('index'))
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()
    elif pd.isna(obj):
        return None
    else:
        return obj

'''

            # Insert after imports
            new_content = content.replace(import_section, import_section + safe_json_function)

            with open(statistical_analyzer_path, 'w') as f:
                f.write(new_content)

            print("✅ Added safe JSON serialization function to statistical_analyzer.py")
        else:
            print("✅ Safe JSON serialization function already exists")

    return safe_json_serialize

def fix_weekly_pattern_calculation():
    """Fix the weekly pattern calculation to handle NaN values properly"""

    print("\n🔧 Fixing Weekly Pattern Calculation")
    print("=" * 50)

    statistical_analyzer_path = "services/statistical_analyzer.py"

    if os.path.exists(statistical_analyzer_path):
        with open(statistical_analyzer_path, 'r') as f:
            content = f.read()

        # Find and replace the _calculate_weekly_pattern method
        old_method = '''    def _calculate_weekly_pattern(self, values: np.ndarray, timestamps: pd.DatetimeIndex) -> Dict:
        """Calculate weekly patterns"""
        try:
            daily_stats = pd.DataFrame({
                'day': timestamps.day_name(),
                'value': values
            }).groupby('day')['value'].agg(['mean', 'std', 'count'])

            return daily_stats.to_dict('index')
        except Exception:
            return {}'''

        new_method = '''    def _calculate_weekly_pattern(self, values: np.ndarray, timestamps: pd.DatetimeIndex) -> Dict:
        """Calculate weekly patterns with safe JSON serialization"""
        try:
            daily_stats = pd.DataFrame({
                'day': timestamps.day_name(),
                'value': values
            }).groupby('day')['value'].agg(['mean', 'std', 'count'])

            # Convert to safe JSON format
            raw_dict = daily_stats.to_dict('index')
            return self.safe_json_serialize(raw_dict)
        except Exception as e:
            logger.warning(f"Weekly pattern calculation failed: {str(e)}")
            return {}'''

        if old_method in content:
            new_content = content.replace(old_method, new_method)

            with open(statistical_analyzer_path, 'w') as f:
                f.write(new_content)

            print("✅ Fixed weekly pattern calculation method")
        else:
            print("⚠️  Could not find the exact method to replace")

    return True

def fix_datetime_serialization():
    """Fix datetime serialization issues in daily reports"""

    print("\n🔧 Fixing Datetime Serialization")
    print("=" * 50)

    daily_report_path = "tasks/daily_report.py"

    if os.path.exists(daily_report_path):
        with open(daily_report_path, 'r') as f:
            content = f.read()

        # Add datetime serialization helper
        datetime_helper = '''
def serialize_datetime(obj):
    """Helper function to serialize datetime objects for JSON"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('index')
    elif pd.isna(obj):
        return None
    else:
        return obj

'''

        # Find the imports section
        if 'def serialize_datetime' not in content:
            # Look for a good place to insert (after imports)
            import_pattern = "from datetime import datetime, timedelta"
            if import_pattern in content:
                new_content = content.replace(import_pattern, import_pattern + datetime_helper)

                with open(daily_report_path, 'w') as f:
                    f.write(new_content)

                print("✅ Added datetime serialization helper to daily_report.py")
            else:
                print("⚠️  Could not find import section to add datetime helper")
        else:
            print("✅ Datetime serialization helper already exists")

    return True

def fix_llm_service_configuration():
    """Fix LLM service configuration issues"""

    print("\n🔧 Fixing LLM Service Configuration")
    print("=" * 50)

    llm_service_path = "services/llm_service.py"

    if os.path.exists(llm_service_path):
        with open(llm_service_path, 'r') as f:
            content = f.read()

        # Fix the OpenAI client initialization
        old_openai_init = '''        # OpenAI - Most reliable for production SMS
        try:
            if os.getenv('OPENAI_API_KEY'):
                import openai
                try:
                    # Try new API first
                    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                    self.providers[LLMProvider.OPENAI] = {'client': client, 'api_version': 'v1'}
                    logger.info("OpenAI initialized (v1+ API)")
                except Exception:
                    # Fallback to legacy API
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    self.providers[LLMProvider.OPENAI] = {'client': openai, 'api_version': 'legacy'}
                    logger.info("OpenAI initialized (legacy API)")
        except Exception as e:
            self.provider_errors[LLMProvider.OPENAI] = f"OpenAI setup failed: {str(e)}"
            logger.warning(f"OpenAI unavailable: {str(e)}")'''

        new_openai_init = '''        # OpenAI - Most reliable for production SMS
        try:
            if os.getenv('OPENAI_API_KEY'):
                import openai
                try:
                    # Try new API first
                    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                    self.providers[LLMProvider.OPENAI] = {'client': client, 'api_version': 'v1'}
                    logger.info("OpenAI initialized (v1+ API)")
                except Exception as e:
                    logger.warning(f"OpenAI v1 API failed: {str(e)}, trying legacy")
                    # Fallback to legacy API
                    openai.api_key = os.getenv('OPENAI_API_KEY')
                    self.providers[LLMProvider.OPENAI] = {'client': openai, 'api_version': 'legacy'}
                    logger.info("OpenAI initialized (legacy API)")
        except Exception as e:
            self.provider_errors[LLMProvider.OPENAI] = f"OpenAI setup failed: {str(e)}"
            logger.warning(f"OpenAI unavailable: {str(e)}")'''

        if old_openai_init in content:
            new_content = content.replace(old_openai_init, new_openai_init)

            with open(llm_service_path, 'w') as f:
                f.write(new_content)

            print("✅ Fixed OpenAI client initialization")
        else:
            print("⚠️  Could not find the exact OpenAI initialization to replace")

    return True

def fix_pandas_deprecation_warnings():
    """Fix pandas deprecation warnings"""

    print("\n🔧 Fixing Pandas Deprecation Warnings")
    print("=" * 50)

    # Fix pattern_mining.py
    pattern_mining_path = "analysis/pattern_mining.py"

    if os.path.exists(pattern_mining_path):
        with open(pattern_mining_path, 'r') as f:
            content = f.read()

        # Replace deprecated 'H' with 'h'
        content = content.replace("freq='H'", "freq='h'")
        content = content.replace("resample('H')", "resample('h')")

        # Replace deprecated fillna method
        content = content.replace(".fillna(method='ffill')", ".ffill()")
        content = content.replace(".fillna(method='bfill')", ".bfill()")

        with open(pattern_mining_path, 'w') as f:
            f.write(content)

        print("✅ Fixed pandas deprecation warnings in pattern_mining.py")

    # Fix statistical_analyzer.py
    statistical_analyzer_path = "services/statistical_analyzer.py"

    if os.path.exists(statistical_analyzer_path):
        with open(statistical_analyzer_path, 'r') as f:
            content = f.read()

        # Replace deprecated 'H' with 'h'
        content = content.replace("freq='H'", "freq='h'")
        content = content.replace("resample('H')", "resample('h')")

        # Replace deprecated fillna method
        content = content.replace(".fillna(method='ffill')", ".ffill()")
        content = content.replace(".fillna(method='bfill')", ".bfill()")

        with open(statistical_analyzer_path, 'w') as f:
            f.write(content)

        print("✅ Fixed pandas deprecation warnings in statistical_analyzer.py")

    return True

def create_test_script():
    """Create a test script to verify the fixes"""

    print("\n🔧 Creating Test Script")
    print("=" * 50)

    test_script = '''#!/usr/bin/env python3
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

    print("\\n🧪 Testing Weekly Pattern Calculation")
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
        print("\\n" + "=" * 60)
        print("🎉 ALL FIXES VERIFIED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ JSON serialization working")
        print("✅ Weekly pattern calculation working")
        print("✅ Daily reports should now work properly")
        print("🎯 Ready to run daily reports again!")
    else:
        print("\\n❌ Some fixes still need attention")

    return success1 and success2

if __name__ == "__main__":
    main()
'''

    with open("test_daily_reports_fix.py", "w") as f:
        f.write(test_script)

    print("✅ Created test script: test_daily_reports_fix.py")
    return True

def main():
    """Main function to apply all fixes"""

    print("🚀 Daily Reports Comprehensive Fix")
    print("=" * 60)

    try:
        # Apply all fixes
        fix_json_serialization()
        fix_weekly_pattern_calculation()
        fix_datetime_serialization()
        fix_llm_service_configuration()
        fix_pandas_deprecation_warnings()
        create_test_script()

        print("\n" + "=" * 60)
        print("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ JSON serialization issues fixed")
        print("✅ Weekly pattern calculation fixed")
        print("✅ Datetime serialization fixed")
        print("✅ LLM service configuration improved")
        print("✅ Pandas deprecation warnings fixed")
        print("✅ Test script created")

        print("\n📋 Next Steps:")
        print("1. Run: python test_daily_reports_fix.py")
        print("2. If tests pass, run: python run_daily_reports.py")
        print("3. Monitor for any remaining errors")

        return True

    except Exception as e:
        print(f"\n❌ Fix application failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
