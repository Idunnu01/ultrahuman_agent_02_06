#!/usr/bin/env python3
"""
Standalone sync script that mimics run_data_sync.py but for a specific user.
This bypasses all Flask dependencies.
"""

import sys
import os
from datetime import datetime

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def standalone_sync(user_id):
    """Standalone sync for a specific user"""
    try:
        # Import after setting up path
        from app import create_app
        from app.models import User
        from tasks.data_ingestion import sync_ultrahuman_data
        from utils.database import db

        # Create app context
        app = create_app()

        with app.app_context():
            print(f"Starting standalone sync at {datetime.utcnow()}")
            print(f"Target user: {user_id}")

            # Get user
            user = User.query.filter_by(id=user_id).first()
            if not user:
                print(f"❌ User '{user_id}' not found in database")
                return False

            print(f"✅ Found user: {user.id}")
            print(f"   Ultrahuman ID: {user.ultrahuman_user_id}")
            print(f"   Phone: {user.phone_number}")
            print(f"   Active: {user.is_active}")
            print()

            # Use only 2 days back
            days_back = 30

            print(f"Using days back: {days_back} days")

            # Run sync
            print(f"Calling sync_ultrahuman_data for user: {user_id}")
            result = sync_ultrahuman_data(user_id, days_back=days_back)

            print(f"Sync result: {result}")

            if result.get('success'):
                metrics_count = result.get('metrics_inserted', 0)
                print(f"✅ Successfully synced {metrics_count} metrics for user {user_id}")
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"❌ Sync failed: {error_msg}")
                return False

    except Exception as e:
        print(f"❌ CRITICAL ERROR in standalone sync: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    user_id = "sample_user"

    print("=" * 60)
    print("STANDALONE ULTRAHUMAN SYNC")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print("=" * 60)

    # Run the standalone sync
    success = standalone_sync(user_id)

    if success:
        print("\n✅ Standalone sync completed successfully!")
        print("\nNext steps:")
        print("1. Check your data: python simple_data_check.py")
        print("2. Test correlation analysis with your real data")
    else:
        print("\n❌ Standalone sync failed. Check the errors above.")

if __name__ == "__main__":
    main()
