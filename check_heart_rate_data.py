#!/usr/bin/env python3
"""
Check if heart rate data exists in the database
"""

def check_sample_data():
    """Check what data exists for sample_user"""

    try:
        from app import create_app
        from app.models import Metric
        from utils.database import db
        from datetime import datetime, timedelta

        # Create Flask app context
        app = create_app()

        with app.app_context():
            print("🔍 CHECKING HEART RATE DATA FOR SAMPLE_USER")
            print("=" * 50)

            # Check last 7 days of data
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            print(f"📅 Date range: {start_date.date()} to {end_date.date()}")

            # Query heart rate data
            heart_rate_data = Metric.query.filter(
                Metric.user_id == 'sample_user',
                Metric.metric_type == 'heart_rate',
                Metric.timestamp >= start_date,
                Metric.timestamp <= end_date
            ).all()

            print(f"💓 Heart rate records found: {len(heart_rate_data)}")

            if heart_rate_data:
                print("\nSample records:")
                for record in heart_rate_data[:5]:
                    print(f"  📊 {record.timestamp}: {record.value} {record.unit}")

                # Calculate average
                values = [float(record.value) for record in heart_rate_data]
                average = sum(values) / len(values)
                print(f"\n📈 Average heart rate: {average:.1f} bpm")
            else:
                print("❌ No heart rate data found!")

                # Check what data does exist
                all_data = Metric.query.filter(
                    Metric.user_id == 'sample_user'
                ).limit(10).all()

                print(f"\n🔍 Total records for sample_user: {Metric.query.filter(Metric.user_id == 'sample_user').count()}")

                if all_data:
                    print("\nSample of available data:")
                    for record in all_data:
                        print(f"  📊 {record.metric_type}: {record.value} ({record.timestamp.date()})")
                else:
                    print("❌ NO DATA AT ALL for sample_user!")

                    # Check if any users exist
                    from app.models import User
                    users = User.query.all()
                    print(f"\n👥 Users in database: {len(users)}")
                    for user in users:
                        print(f"  - {user.id} ({user.phone_number})")

    except Exception as e:
        print(f"❌ Error checking data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_sample_data()