#!/usr/bin/env python3
"""
Check recently ingested sleep data to see what fields are actually populated
"""

import sys
import os
import json
from datetime import datetime, timedelta

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def check_recent_sleep_data():
    """Check the most recent sleep data that was just ingested"""

    print("🔍 CHECKING RECENTLY INGESTED SLEEP DATA")
    print("=" * 60)

    from app import create_app
    from app.models import Metric
    from sqlalchemy import desc

    app = create_app()

    with app.app_context():
        user_id = 'user_7000'

        # Get the most recent sleep data (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        recent_sleep = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.metric_type == 'sleep_score',
            Metric.timestamp >= cutoff_time
        ).order_by(desc(Metric.timestamp)).limit(3).all()

        print(f"🛌 Recent sleep records (last 24h): {len(recent_sleep)}")
        print()

        if not recent_sleep:
            print("❌ No recent sleep data found")

            # Check all sleep data
            all_sleep = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'sleep_score'
            ).order_by(desc(Metric.timestamp)).limit(3).all()

            print(f"📊 Total sleep records: {len(all_sleep)}")
            recent_sleep = all_sleep

        for i, record in enumerate(recent_sleep):
            print(f"🌙 Sleep Record {i+1}:")
            print(f"   Timestamp: {record.timestamp}")
            print(f"   Value: {record.value}")
            print(f"   Source: {record.source}")

            # Examine meta_data in detail
            if record.meta_data:
                print(f"   Meta_data structure:")
                print(f"   {json.dumps(record.meta_data, indent=6, default=str)}")

                # Check for any non-None values
                non_none_fields = []
                def check_nested(obj, path=""):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            if value is not None:
                                if isinstance(value, dict):
                                    check_nested(value, current_path)
                                else:
                                    non_none_fields.append(f"{current_path}: {value}")

                check_nested(record.meta_data)

                if non_none_fields:
                    print(f"   ✅ Non-None fields:")
                    for field in non_none_fields:
                        print(f"      • {field}")
                else:
                    print(f"   ❌ All metadata fields are None")
            else:
                print(f"   ❌ No meta_data")

            print()

        # Check if there are other sleep-related metrics that might have timing data
        print("🔍 OTHER SLEEP-RELATED METRICS:")
        print("=" * 40)

        sleep_related_types = Metric.query.filter(
            Metric.user_id == user_id,
            Metric.timestamp >= cutoff_time
        ).filter(
            Metric.metric_type.like('%sleep%') |
            Metric.metric_type.like('%bed%') |
            Metric.metric_type.like('%rem%') |
            Metric.metric_type.like('%deep%')
        ).with_entities(Metric.metric_type).distinct().all()

        for metric_type in sleep_related_types:
            count = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric_type[0],
                Metric.timestamp >= cutoff_time
            ).count()
            print(f"   • {metric_type[0]}: {count} records")

            # Show a sample
            sample = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric_type[0],
                Metric.timestamp >= cutoff_time
            ).first()

            if sample:
                print(f"     Sample value: {sample.value}")
                if sample.meta_data:
                    print(f"     Sample metadata: {sample.meta_data}")

        print("\n💡 ANALYSIS:")
        if any(record.meta_data and any(v is not None for v in record.meta_data.values() if v != {}) for record in recent_sleep):
            print("✅ Some metadata exists - need to check if timing fields are in raw_data")
        else:
            print("❌ All metadata is None - API not returning detailed sleep data")
            print("   This explains why bedtime questions can't be answered")

if __name__ == '__main__':
    check_recent_sleep_data()