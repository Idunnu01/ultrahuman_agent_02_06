#!/usr/bin/env python3
"""
List all users and their information
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def list_all_users():
    """List all users with their key information"""

    try:
        from app import create_app
        from app.models import User, DailyReport, Metric

        app = create_app()

        with app.app_context():
            print("👥 ALL USERS IN SYSTEM")
            print("="*50)

            # Get all users
            users = User.query.all()

            if not users:
                print("❌ No users found")
                return False

            print(f"Found {len(users)} users:\n")

            for i, user in enumerate(users, 1):
                print(f"{i}. USER: {user.id}")
                print(f"   📱 Phone: {user.phone_number}")
                print(f"   ✅ Active: {user.is_active}")
                print(f"   🌍 Timezone: {user.timezone}")

                # Check attributes safely
                if hasattr(user, 'ultrahuman_user_id'):
                    print(f"   🔗 UH ID: {user.ultrahuman_user_id}")

                # Quick metrics check
                try:
                    has_metrics = Metric.query.filter_by(user_id=user.id).first() is not None
                    print(f"   📊 Has Metrics: {'YES' if has_metrics else 'NO'}")
                except:
                    print(f"   📊 Has Metrics: Unknown")

                # Quick reports check
                try:
                    report_count = DailyReport.query.filter_by(user_id=user.id).count()
                    print(f"   📋 Reports: {report_count}")
                except:
                    print(f"   📋 Reports: Unknown")

                # SMS status
                test_numbers = ['+1234567890', '+0000000000', '+1111111111']
                if user.phone_number and user.phone_number not in test_numbers and user.is_active:
                    print(f"   📲 SMS Ready: ✅ YES")
                else:
                    print(f"   📲 SMS Ready: ❌ NO")

                print()

            # Summary
            active_count = sum(1 for u in users if u.is_active)
            phone_count = sum(1 for u in users if u.phone_number)
            sms_ready = sum(1 for u in users if u.is_active and u.phone_number and u.phone_number not in ['+1234567890', '+0000000000', '+1111111111'])

            print("📊 SUMMARY:")
            print(f"   Total users: {len(users)}")
            print(f"   Active users: {active_count}")
            print(f"   Users with phones: {phone_count}")
            print(f"   SMS-ready users: {sms_ready}")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    list_all_users()