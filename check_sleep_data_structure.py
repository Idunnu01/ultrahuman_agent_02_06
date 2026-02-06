#!/usr/bin/env python3
"""
Check what sleep data structure is actually available in the database
"""

import sys
import os
from datetime import datetime, timedelta

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def check_sleep_data():
    """Check actual sleep data structure in database"""

    print("🔍 CHECKING SLEEP DATA STRUCTURE")
    print("=" * 50)

    from app import create_app
    from app.models import Metric
    from sqlalchemy import text

    app = create_app()

    with app.app_context():
        user_id = 'user_7000'

        # Check what sleep-related metric types exist
        print("📊 Sleep-related metric types in database:")
        result = Metric.query.with_entities(Metric.metric_type).filter(
            Metric.user_id == user_id,
            Metric.metric_type.like('%sleep%')
        ).distinct().all()

        sleep_types = [r[0] for r in result]
        for sleep_type in sorted(sleep_types):
            count = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == sleep_type
            ).count()
            print(f"  • {sleep_type}: {count} records")

        print(f"\n🛌 Recent sleep_score records (last 5):")
        recent_sleep = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.metric_type == 'sleep_score'
        ).order_by(Metric.timestamp.desc()).limit(5).all()

        for record in recent_sleep:
            print(f"  📅 {record.timestamp.strftime('%Y-%m-%d %H:%M')} - Score: {record.value}")
            # Check if there are any additional fields stored
            if hasattr(record, 'meta_data') and record.meta_data:
                print(f"      Meta_data: {record.meta_data}")
            elif hasattr(record, 'metadata') and record.metadata:
                print(f"      Metadata: {record.metadata}")
            else:
                print(f"      Meta_data: None")

        print(f"\n🔍 Sample sleep_score record details:")
        if recent_sleep:
            sample = recent_sleep[0]
            print(f"  ID: {sample.id}")
            print(f"  User ID: {sample.user_id}")
            print(f"  Metric Type: {sample.metric_type}")
            print(f"  Value: {sample.value}")
            print(f"  Unit: {sample.unit}")
            print(f"  Timestamp: {sample.timestamp}")
            print(f"  Source: {sample.source}")
            if hasattr(sample, 'meta_data'):
                print(f"  Meta_data type: {type(sample.meta_data)}")
                print(f"  Meta_data content: {sample.meta_data}")

            # Check all available fields
            print(f"\n🔍 All available fields:")
            for attr in dir(sample):
                if not attr.startswith('_') and not callable(getattr(sample, attr)):
                    try:
                        value = getattr(sample, attr)
                        print(f"    {attr}: {value}")
                    except Exception as e:
                        print(f"    {attr}: <error accessing: {e}>")

        # Check if there are any other sleep-related fields in the database
        print(f"\n🗃️ All metric types containing 'sleep' or timing info:")
        all_types = Metric.query.with_entities(Metric.metric_type).filter(
            Metric.user_id == user_id
        ).distinct().all()

        sleep_related = []
        for type_tuple in all_types:
            metric_type = type_tuple[0]
            if any(keyword in metric_type.lower() for keyword in ['sleep', 'bed', 'wake', 'onset', 'efficiency', 'rem', 'deep']):
                count = Metric.query.filter(
                    Metric.user_id == user_id,
                    Metric.metric_type == metric_type
                ).count()
                sleep_related.append((metric_type, count))

        if sleep_related:
            print("Sleep-related metrics found:")
            for metric_type, count in sorted(sleep_related):
                print(f"  • {metric_type}: {count} records")
        else:
            print("  Only generic sleep_score found")

        print(f"\n💡 ANALYSIS:")
        if any('deep_sleep' in t for t, _ in sleep_related):
            print("  ✅ Deep sleep data available - can show actual deep sleep minutes")
        else:
            print("  ❌ No deep_sleep_minutes - need to extract from sleep_score metadata or API")

        if any('bedtime' in t.lower() or 'onset' in t.lower() for t, _ in sleep_related):
            print("  ✅ Bedtime/onset data available - can show actual sleep times")
        else:
            print("  ❌ No bedtime/onset data - timestamps in sleep_score may indicate sleep period")
            print("  💡 The timestamp on sleep_score might represent when sleep analysis was done,")
            print("     not when you actually fell asleep. Need to check Ultrahuman API response structure.")

if __name__ == '__main__':
    check_sleep_data()