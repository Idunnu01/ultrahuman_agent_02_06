#!/usr/bin/env python3.11
"""
PythonAnywhere scheduled task runner for data synchronization
Run this hourly
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

def run_data_sync():
    """Sync Ultrahuman data for all users"""
    try:
        # Import after setting up path
        from app import create_app
        from app.models import User
        from tasks.data_ingestion import sync_ultrahuman_data
        from utils.database import db

        # Create app context
        app = create_app()

        with app.app_context():
            print(f"Starting data sync at {datetime.utcnow()}")

            # Get all active users
            active_users = User.query.filter_by(is_active=True).all()

            if not active_users:
                print("No active users found")
                return

            results = {
                'total_users': len(active_users),
                'successful': 0,
                'failed': 0,
                'total_metrics': 0,
                'errors': []
            }

            # Sync data for each user
            for user in active_users:
                try:
                    print(f"Syncing data for user {user.id}")

                    # Run sync directly (no Celery on PythonAnywhere)
                    result = sync_ultrahuman_data(user.id, days_back=1)

                    if result.get('success'):
                        results['successful'] += 1
                        metrics_count = result.get('metrics_inserted', 0)
                        results['total_metrics'] += metrics_count
                        print(f"✅ Synced {metrics_count} metrics for user {user.id}")
                    else:
                        results['failed'] += 1
                        error_msg = result.get('error', 'Unknown error')
                        results['errors'].append(f"User {user.id}: {error_msg}")
                        print(f"❌ Sync failed for user {user.id}: {error_msg}")

                except Exception as e:
                    results['failed'] += 1
                    error_msg = str(e)
                    results['errors'].append(f"User {user.id}: {error_msg}")
                    print(f"❌ Exception for user {user.id}: {error_msg}")

            # Print summary
            success_rate = results['successful'] / results['total_users'] if results['total_users'] > 0 else 0
            print(f"\n📊 Data Sync Summary:")
            print(f"Total users: {results['total_users']}")
            print(f"Successful: {results['successful']}")
            print(f"Failed: {results['failed']}")
            print(f"Success rate: {success_rate:.1%}")
            print(f"Total metrics synced: {results['total_metrics']}")

            if results['errors']:
                print(f"\n❌ Errors:")
                for error in results['errors']:
                    print(f"  - {error}")

            print(f"Data sync completed at {datetime.utcnow()}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR in data sync: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_data_sync()