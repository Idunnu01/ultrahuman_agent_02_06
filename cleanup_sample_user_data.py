#!/usr/bin/env python3
"""
Clean up sample_user data to reduce database size and memory issues
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def cleanup_sample_user_data():
    """Clean up sample_user data while keeping the user record"""

    try:
        from app import create_app
        from app.models import User, Metric, DailyReport
        from utils.database import db

        app = create_app()

        with app.app_context():
            sample_user_id = 'sample_user'

            print("🧹 Cleaning up sample_user data")
            print("=" * 50)

            # Check if sample_user exists
            sample_user = User.query.filter_by(id=sample_user_id).first()
            if not sample_user:
                print(f"❌ sample_user not found")
                return False

            print(f"✅ Found sample_user:")
            print(f"   Phone: {sample_user.phone_number}")
            print(f"   UH ID: {sample_user.ultrahuman_user_id}")
            print(f"   Active: {sample_user.is_active}")

            # Count existing data (only models we're sure exist)
            print(f"\n📊 Current data for sample_user:")

            metrics_count = Metric.query.filter_by(user_id=sample_user_id).count()
            reports_count = DailyReport.query.filter_by(user_id=sample_user_id).count()

            print(f"   📊 Metrics: {metrics_count}")
            print(f"   📋 Daily Reports: {reports_count}")

            total_records = metrics_count + reports_count
            print(f"   📈 Total Records: {total_records}")

            if total_records == 0:
                print(f"\n✅ sample_user already has no data")
                return True

            # Confirm deletion
            print(f"\n⚠️ This will DELETE all data for sample_user:")
            print(f"   ❌ {metrics_count} metrics")
            print(f"   ❌ {reports_count} daily reports")
            print(f"   ✅ KEEP the user record itself")

            # Delete data in batches to avoid memory issues
            print(f"\n🗑️ Deleting sample_user data...")

            # Delete metrics in batches
            if metrics_count > 0:
                print(f"   Deleting {metrics_count} metrics...")
                batch_size = 1000
                while True:
                    metrics_batch = Metric.query.filter_by(user_id=sample_user_id).limit(batch_size).all()
                    if not metrics_batch:
                        break
                    for metric in metrics_batch:
                        db.session.delete(metric)
                    db.session.commit()
                    print(f"     Deleted batch of {len(metrics_batch)} metrics")

            # Delete daily reports
            if reports_count > 0:
                print(f"   Deleting {reports_count} daily reports...")
                reports = DailyReport.query.filter_by(user_id=sample_user_id).all()
                for report in reports:
                    db.session.delete(report)
                db.session.commit()

            # Verify cleanup
            print(f"\n✅ Cleanup complete! Verifying...")

            new_metrics_count = Metric.query.filter_by(user_id=sample_user_id).count()
            new_reports_count = DailyReport.query.filter_by(user_id=sample_user_id).count()

            print(f"📊 After cleanup:")
            print(f"   📊 Metrics: {new_metrics_count}")
            print(f"   📋 Daily Reports: {new_reports_count}")

            # Confirm user still exists
            user_still_exists = User.query.filter_by(id=sample_user_id).first()
            if user_still_exists:
                print(f"✅ sample_user record preserved")
            else:
                print(f"❌ ERROR: sample_user record was deleted!")

            return True

    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_final_database_stats():
    """Show final database statistics"""

    try:
        from app import create_app
        from app.models import User, Metric, DailyReport

        app = create_app()

        with app.app_context():
            print(f"\n📊 FINAL DATABASE STATS")
            print("=" * 40)

            users = User.query.all()
            print(f"👥 Total Users: {len(users)}")

            for user in users:
                metric_count = Metric.query.filter_by(user_id=user.id).count()
                report_count = DailyReport.query.filter_by(user_id=user.id).count()
                print(f"   {user.id}: {metric_count} metrics, {report_count} reports")

            total_metrics = Metric.query.count()
            total_reports = DailyReport.query.count()

            print(f"\n📈 Database Totals:")
            print(f"   📊 Total Metrics: {total_metrics}")
            print(f"   📋 Total Reports: {total_reports}")

            return True

    except Exception as e:
        print(f"❌ Error getting stats: {str(e)}")
        return False

if __name__ == '__main__':
    print(f"🧹 Sample User Data Cleanup")
    print(f"This will remove all data for sample_user but keep the user record")

    success = cleanup_sample_user_data()

    if success:
        show_final_database_stats()
        print(f"\n🎉 Cleanup successful!")
        print(f"✅ sample_user data removed - should reduce memory issues")
        print(f"✅ sample_user record preserved for future use")
    else:
        print(f"\n❌ Cleanup failed - check database connection")