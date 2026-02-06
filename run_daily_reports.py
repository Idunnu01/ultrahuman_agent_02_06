#!/usr/bin/env python3.11
"""
PythonAnywhere scheduled task runner for daily reports
Run this at 4:00 AM UTC daily
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

def run_daily_reports():
    """Generate daily reports for all users"""
    try:
        # Import after setting up path
        from app import create_app
        from app.models import User
        from tasks.daily_report import generate_daily_report
        from utils.database import db

        # Create app context
        app = create_app()

        with app.app_context():
            print(f"Starting daily reports generation at {datetime.utcnow()}")

            # Get all active users
            active_users = User.query.filter_by(is_active=True).all()

            if not active_users:
                print("No active users found")
                return

            results = {
                'total_users': len(active_users),
                'successful': 0,
                'failed': 0,
                'errors': []
            }

            # Generate report for each user
            for user in active_users:
                try:
                    print(f"Generating report for user {user.id}")

                    # Since we can't use Celery on PythonAnywhere, run directly
                    result = generate_daily_report(user.id) or {}

                    status = result.get('status')
                    is_success = bool(result.get('success'))
                    already_exists = status == 'already_exists'
                    has_report = result.get('report_id') is not None and not result.get('error')

                    if is_success or already_exists or has_report:
                        results['successful'] += 1
                        if already_exists:
                            print(f"✅ Report already existed for user {user.id} (id={result.get('report_id')})")
                        else:
                            print(f"✅ Report generated for user {user.id} (id={result.get('report_id')})")
                    else:
                        results['failed'] += 1
                        # Show full payload for debugging when no explicit error is present
                        error_msg = result.get('error')
                        if not error_msg:
                            error_msg = f"No 'success' flag; payload={result}"
                        results['errors'].append(f"User {user.id}: {error_msg}")
                        print(f"❌ Report failed for user {user.id}: {error_msg}")


                except Exception as e:
                    results['failed'] += 1
                    error_msg = str(e)
                    results['errors'].append(f"User {user.id}: {error_msg}")
                    print(f"❌ Exception for user {user.id}: {error_msg}")

                    # Handle database session rollback
                    try:
                        db.session.rollback()
                    except Exception as rollback_error:
                        print(f"⚠️ Session rollback failed: {str(rollback_error)}")

            # Print summary
            success_rate = results['successful'] / results['total_users'] if results['total_users'] > 0 else 0
            print(f"\n📊 Daily Reports Summary:")
            print(f"Total users: {results['total_users']}")
            print(f"Successful: {results['successful']}")
            print(f"Failed: {results['failed']}")
            print(f"Success rate: {success_rate:.1%}")

            if results['errors']:
                print(f"\n❌ Errors:")
                for error in results['errors']:
                    print(f"  - {error}")

            print(f"Daily reports completed at {datetime.utcnow()}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR in daily reports: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_daily_reports()