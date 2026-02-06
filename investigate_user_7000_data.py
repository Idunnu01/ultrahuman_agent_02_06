#!/usr/bin/env python3
"""
Investigate user_7000 data issues - timestamps, sync, and correlation data
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def investigate_user_data():
    """Deep dive into user_7000 data to find timestamp and sync issues"""

    print("🔍 Investigating user_7000 Data Issues")
    print("="*60)

    try:
        from app import create_app
        from app.models import User, Metric
        from utils.database import db

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'

            # Get all metrics for user_7000
            all_metrics = Metric.query.filter_by(user_id=user_id).order_by(Metric.timestamp.desc()).all()

            print(f"📊 TOTAL METRICS FOR {user_id}: {len(all_metrics)}")

            if not all_metrics:
                print("❌ No metrics found - this explains the timestamp issue!")
                return

            # Analyze timestamp patterns
            print(f"\n🕐 TIMESTAMP ANALYSIS:")

            # Check date range
            timestamps = [m.timestamp for m in all_metrics if m.timestamp]
            if timestamps:
                earliest = min(timestamps)
                latest = max(timestamps)
                print(f"   Date range: {earliest.date()} to {latest.date()}")
                print(f"   Time span: {(latest - earliest).days} days")
            else:
                print("   ❌ No valid timestamps found!")

            # Group by metric type
            print(f"\n📈 METRICS BY TYPE:")
            metric_types = {}
            timestamp_issues = {}

            for metric in all_metrics:
                metric_type = metric.metric_type
                if metric_type not in metric_types:
                    metric_types[metric_type] = []

                metric_info = {
                    'id': metric.id,
                    'value': metric.value,
                    'timestamp': metric.timestamp,
                    'timestamp_type': type(metric.timestamp).__name__,
                    'source': metric.source
                }
                metric_types[metric_type].append(metric_info)

                # Check for timestamp issues
                if not metric.timestamp:
                    if metric_type not in timestamp_issues:
                        timestamp_issues[metric_type] = []
                    timestamp_issues[metric_type].append(f"Metric {metric.id} has NULL timestamp")
                elif not isinstance(metric.timestamp, datetime):
                    if metric_type not in timestamp_issues:
                        timestamp_issues[metric_type] = []
                    timestamp_issues[metric_type].append(f"Metric {metric.id} timestamp is {type(metric.timestamp)}, not datetime")

            # Show metrics by type with counts and recent examples
            for metric_type, metrics_list in sorted(metric_types.items()):
                print(f"\n   {metric_type}: {len(metrics_list)} entries")

                # Show recent entries
                recent = sorted(metrics_list, key=lambda x: x['timestamp'] or datetime.min, reverse=True)[:3]
                for i, metric in enumerate(recent):
                    timestamp_str = metric['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if metric['timestamp'] else 'NULL'
                    print(f"     {i+1}. ID:{metric['id']} Value:{metric['value']} Time:{timestamp_str} Source:{metric['source']}")

            # Show timestamp issues
            if timestamp_issues:
                print(f"\n❌ TIMESTAMP ISSUES FOUND:")
                for metric_type, issues in timestamp_issues.items():
                    print(f"   {metric_type}:")
                    for issue in issues[:3]:  # Show first 3 issues
                        print(f"     - {issue}")

            # Check for lifestyle vs biometric data balance
            print(f"\n🍽️ LIFESTYLE vs BIOMETRIC DATA:")

            lifestyle_keywords = ['intake', 'consumption', 'timing', 'supplement', 'meal', 'activity']
            biometric_keywords = ['heart_rate', 'hrv', 'sleep', 'temperature', 'recovery', 'stress']

            lifestyle_metrics = [m for m in all_metrics if any(kw in m.metric_type for kw in lifestyle_keywords)]
            biometric_metrics = [m for m in all_metrics if any(kw in m.metric_type for kw in biometric_keywords)]

            print(f"   Lifestyle events: {len(lifestyle_metrics)}")
            print(f"   Biometric data: {len(biometric_metrics)}")

            if len(lifestyle_metrics) == 0:
                print("   ⚠️ No lifestyle events found - correlation analysis impossible")
            elif len(biometric_metrics) == 0:
                print("   ⚠️ No biometric data found - correlation analysis impossible")
            elif len(lifestyle_metrics) < 3:
                print("   ⚠️ Too few lifestyle events for meaningful correlations")
            elif len(biometric_metrics) < 10:
                print("   ⚠️ Too few biometric points for meaningful correlations")
            else:
                print("   ✅ Sufficient data for correlation analysis")

            # Check recent data (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_metrics = [m for m in all_metrics if m.timestamp and m.timestamp >= week_ago]

            print(f"\n📅 RECENT DATA (last 7 days): {len(recent_metrics)} metrics")

            if recent_metrics:
                recent_types = {}
                for m in recent_metrics:
                    if m.metric_type not in recent_types:
                        recent_types[m.metric_type] = 0
                    recent_types[m.metric_type] += 1

                for metric_type, count in sorted(recent_types.items()):
                    print(f"   {metric_type}: {count}")
            else:
                print("   ❌ No recent data found!")

            # Test correlation analysis specifically
            print(f"\n🔗 TESTING CORRELATION ANALYSIS:")
            test_correlation_analysis(user_id)

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_correlation_analysis(user_id):
    """Test the correlation analysis that's failing"""

    try:
        from analysis.correlation_analysis import CorrelationAnalyzer
        from app.models import Metric
        from datetime import datetime, timedelta

        analyzer = CorrelationAnalyzer()

        # Test with different time periods
        periods = [7, 14, 30]

        for days in periods:
            try:
                print(f"\n   Testing {days}-day correlation analysis...")

                # Get recent metrics for the user
                cutoff_date = datetime.now() - timedelta(days=days)
                recent_metrics = Metric.query.filter(
                    Metric.user_id == user_id,
                    Metric.timestamp >= cutoff_date
                ).all()

                print(f"      Found {len(recent_metrics)} metrics in last {days} days")

                if len(recent_metrics) < 10:
                    print(f"   ⚠️ {days}-day analysis: insufficient data ({len(recent_metrics)} metrics)")
                    continue

                # Prepare data for correlation analysis
                data = {}
                for metric in recent_metrics:
                    if metric.metric_type not in data:
                        data[metric.metric_type] = {'values': [], 'timestamps': []}
                    data[metric.metric_type]['values'].append(metric.value)
                    data[metric.metric_type]['timestamps'].append(metric.timestamp)

                print(f"      Organized into {len(data)} metric types")

                # Run correlation analysis
                results = analyzer.analyze_correlations(data)

                if results and 'error' not in results:
                    significant_rels = results.get('significant_relationships', [])
                    print(f"   ✅ {days}-day analysis succeeded: {len(significant_rels)} significant correlations found")

                    if significant_rels:
                        top_correlation = significant_rels[0]
                        pair = top_correlation.get('metric_pair', 'Unknown')
                        corr_data = top_correlation.get('primary_correlation', {})
                        corr_value = corr_data.get('correlation', 0)
                        print(f"      Top correlation: {pair} (r={corr_value:.3f})")

                elif results and 'error' in results:
                    print(f"   ❌ {days}-day analysis failed: {results['error']}")
                else:
                    print(f"   ⚠️ {days}-day analysis returned no results")

            except Exception as e:
                print(f"   ❌ {days}-day analysis failed: {str(e)}")

    except Exception as e:
        print(f"   ❌ Correlation analysis setup failed: {str(e)}")

def check_ultrahuman_sync():
    """Check if Ultrahuman data is syncing"""

    print(f"\n🔄 CHECKING ULTRAHUMAN SYNC:")

    try:
        from services.metrics_service import MetricsService

        service = MetricsService()

        # Check if we can fetch data from Ultrahuman
        print(f"   Testing Ultrahuman API connection...")

        # This would test the API but we'll check for typical Ultrahuman metric types instead
        from app import create_app
        from app.models import Metric
        from utils.database import db

        app = create_app()
        with app.app_context():
            ultrahuman_metrics = Metric.query.filter_by(user_id='user_7000', source='ultrahuman').all()

            print(f"   Ultrahuman-sourced metrics: {len(ultrahuman_metrics)}")

            if ultrahuman_metrics:
                types = set(m.metric_type for m in ultrahuman_metrics)
                print(f"   Ultrahuman metric types: {', '.join(sorted(types))}")

                latest = max(ultrahuman_metrics, key=lambda x: x.timestamp or datetime.min)
                print(f"   Latest Ultrahuman data: {latest.timestamp}")
            else:
                print(f"   ❌ No Ultrahuman data found - sync may not be working")

                # Check for any biometric-looking data regardless of source
                biometric_patterns = ['heart_rate', 'hrv', 'sleep', 'temperature', 'recovery']
                biometric_data = Metric.query.filter(
                    Metric.user_id == 'user_7000'
                ).filter(
                    db.or_(*[Metric.metric_type.like(f'%{pattern}%') for pattern in biometric_patterns])
                ).all()

                print(f"   Biometric-type metrics (any source): {len(biometric_data)}")

    except Exception as e:
        print(f"   ❌ Sync check failed: {str(e)}")

if __name__ == '__main__':
    investigate_user_data()
    check_ultrahuman_sync()

    print(f"\n🎯 NEXT STEPS:")
    print(f"1. If no metrics found → Check data ingestion")
    print(f"2. If timestamp issues → Fix datetime serialization")
    print(f"3. If no biometric data → Fix Ultrahuman sync")
    print(f"4. If insufficient data → Continue logging lifestyle events")