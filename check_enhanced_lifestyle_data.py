#!/usr/bin/env python3
"""
Check the enhanced lifestyle data with specific tracking
"""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from app.models import User, Metric
    from utils.database import db
    import json
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this on PythonAnywhere in your project directory")
    sys.exit(1)

def check_lifestyle_data_after_enhancement():
    """Check lifestyle data after the enhancement"""

    app = create_app()

    with app.app_context():
        print("🔍 ENHANCED LIFESTYLE DATA CHECK")
        print("=" * 50)
        print()

        # Get users
        users = User.query.filter_by(is_active=True).all()
        print(f"👥 Checking {len(users)} active users")
        print()

        # Look for recent lifestyle events (last 24 hours)
        since = datetime.utcnow() - timedelta(hours=24)

        for user in users:
            print(f"👤 **USER: {user.id}**")
            print("-" * 40)

            # Get all recent metrics
            recent_metrics = Metric.query.filter(
                Metric.user_id == user.id,
                Metric.timestamp >= since,
                Metric.source == 'user_input'  # Only lifestyle events
            ).order_by(Metric.timestamp.desc()).all()

            if not recent_metrics:
                print("   No recent lifestyle events found")
                print()
                continue

            print(f"   📊 Found {len(recent_metrics)} recent lifestyle events")
            print()

            # Group by metric type
            metrics_by_type = {}
            for metric in recent_metrics:
                metric_type = metric.metric_type
                if metric_type not in metrics_by_type:
                    metrics_by_type[metric_type] = []
                metrics_by_type[metric_type].append(metric)

            # Show each metric type
            for metric_type, metrics in metrics_by_type.items():
                print(f"   📈 **{metric_type.upper().replace('_', ' ')}**")

                for metric in metrics:
                    timestamp_str = metric.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"      • Value: {metric.value} {metric.unit or ''}")
                    print(f"        Time: {timestamp_str}")

                    # Show metadata if available
                    if metric.meta_data:
                        try:
                            if isinstance(metric.meta_data, str):
                                meta = json.loads(metric.meta_data)
                            else:
                                meta = metric.meta_data

                            # Show key details
                            if 'supplement_name' in meta:
                                print(f"        Supplement: {meta['supplement_name']}")
                            if 'food_name' in meta:
                                print(f"        Food: {meta['food_name']}")
                            if 'activity_type' in meta:
                                print(f"        Activity: {meta['activity_type']}")
                            if 'drink_type' in meta:
                                print(f"        Drink: {meta['drink_type']}")
                            if 'dosage_raw' in meta:
                                print(f"        Dosage: {meta['dosage_raw']}")

                        except Exception as e:
                            print(f"        Metadata error: {e}")

                    print()

            print()

def check_specific_metrics():
    """Look for the new specific metric types we created"""

    app = create_app()

    with app.app_context():
        print("🎯 LOOKING FOR NEW SPECIFIC METRICS")
        print("=" * 40)
        print()

        # Look for supplement-specific metrics
        supplement_metrics = Metric.query.filter(
            Metric.metric_type.like('%_intake'),
            Metric.metric_type != 'supplement_intake',  # Exclude generic
            Metric.source == 'user_input'
        ).order_by(Metric.timestamp.desc()).limit(20).all()

        if supplement_metrics:
            print("💊 SUPPLEMENT-SPECIFIC METRICS FOUND:")
            for metric in supplement_metrics:
                supplement_name = metric.metric_type.replace('_intake', '')
                timestamp_str = metric.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   ✅ {supplement_name}: {metric.value} {metric.unit} at {timestamp_str}")
            print()
        else:
            print("❌ No supplement-specific metrics found yet")
            print()

        # Look for food-specific metrics
        food_metrics = Metric.query.filter(
            Metric.metric_type.like('%_consumption'),
            Metric.source == 'user_input'
        ).order_by(Metric.timestamp.desc()).limit(20).all()

        if food_metrics:
            print("🍽️  FOOD-SPECIFIC METRICS FOUND:")
            for metric in food_metrics:
                food_name = metric.metric_type.replace('_consumption', '')
                timestamp_str = metric.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   ✅ {food_name}: {metric.value} {metric.unit} at {timestamp_str}")
            print()
        else:
            print("❌ No food-specific metrics found yet")
            print()

        # Look for exercise-specific metrics
        exercise_metrics = Metric.query.filter(
            Metric.metric_type.like('%_duration'),
            Metric.metric_type != 'exercise_duration',  # Exclude generic
            Metric.source == 'user_input'
        ).order_by(Metric.timestamp.desc()).limit(20).all()

        if exercise_metrics:
            print("🏃 EXERCISE-SPECIFIC METRICS FOUND:")
            for metric in exercise_metrics:
                exercise_name = metric.metric_type.replace('_duration', '')
                timestamp_str = metric.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(f"   ✅ {exercise_name}: {metric.value} {metric.unit} at {timestamp_str}")
            print()
        else:
            print("❌ No exercise-specific metrics found yet")
            print()

def show_test_instructions():
    """Show how to test the enhanced tracking"""

    print("📋 HOW TO TEST ENHANCED TRACKING:")
    print("=" * 35)
    print()

    print("1. **Upload Updated File** (if you haven't already):")
    print("   • Upload services/metrics_service.py to PythonAnywhere")
    print("   • Restart your web app")
    print()

    print("2. **Test These SMS Messages:**")
    test_messages = [
        ("supplement magnesium 400mg 10pm", "Creates magnesium_intake metric"),
        ("meal salmon 7pm", "Creates salmon_consumption metric"),
        ("exercise running 30min 6am", "Creates running_duration metric"),
        ("drink coffee 16oz 9am", "Creates coffee_consumption + caffeine_intake metrics")
    ]

    for msg, result in test_messages:
        print(f"   📱 '{msg}'")
        print(f"      → {result}")
        print()

    print("3. **Run This Script Again** to see the new metrics:")
    print("   python3.10 check_enhanced_lifestyle_data.py")
    print()

    print("4. **Try Specific Correlation Queries:**")
    queries = [
        "Does magnesium improve my sleep score?",
        "How does running duration affect my HRV?",
        "Does coffee timing correlate with my heart rate?"
    ]

    for query in queries:
        print(f"   📝 '{query}'")
    print()

def check_current_metrics_overview():
    """Show overview of current metrics"""

    app = create_app()

    with app.app_context():
        print("📊 CURRENT METRICS OVERVIEW:")
        print("=" * 30)
        print()

        # Count different metric types
        metric_counts = db.session.query(
            Metric.metric_type,
            db.func.count(Metric.id).label('count'),
            db.func.max(Metric.timestamp).label('latest')
        ).filter(
            Metric.source == 'user_input'
        ).group_by(
            Metric.metric_type
        ).order_by(
            db.func.count(Metric.id).desc()
        ).all()

        if metric_counts:
            print("🔍 USER INPUT METRICS:")
            for metric_type, count, latest in metric_counts:
                latest_str = latest.strftime("%Y-%m-%d %H:%M") if latest else "N/A"
                print(f"   • {metric_type}: {count} records (latest: {latest_str})")
            print()
        else:
            print("❌ No user input metrics found")
            print()

if __name__ == "__main__":
    try:
        check_current_metrics_overview()
        check_lifestyle_data_after_enhancement()
        check_specific_metrics()
        show_test_instructions()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()