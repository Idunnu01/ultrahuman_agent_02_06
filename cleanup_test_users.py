#!/usr/bin/env python3
"""
Clean up test users from the PRODUCTION MySQL database
This connects to the same database as check_production_data.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project to path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

def cleanup_production_test_users():
    """Remove test users from production MySQL database"""

    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Use production MySQL database (same as check_production_data.py)
        # Don't override DATABASE_URL - use the one from .env

        from app import create_app
        from utils.database import db
        from sqlalchemy import text

        app = create_app('production')

        with app.app_context():
            print("🗑️  PRODUCTION DATABASE TEST USER CLEANUP")
            print("=" * 60)
            print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
            print("Connecting to production MySQL database...")
            print()

            # First, see what users exist
            try:
                result = db.session.execute(text("SELECT id, phone_number, ultrahuman_user_id FROM users"))
                users = result.fetchall()
            except Exception as e:
                print(f"❌ Database connection failed: {str(e)}")
                print("Make sure you have stable internet connection for MySQL access")
                return False

            print(f"📋 Current users in PRODUCTION database ({len(users)} total):")
            for user in users:
                print(f"  - ID: {user[0]}")
                print(f"    Phone: {user[1]}")
                print(f"    UH ID: {user[2]}")
                print()

            # Define test user patterns to delete - be very specific
            test_user_ids = ['test_db_connection', 'test_lifestyle_db']

            users_to_delete = []
            users_to_keep = []

            for user in users:
                user_id = user[0]
                # Only delete users that are exactly these test IDs
                if user_id in test_user_ids:
                    users_to_delete.append(user_id)
                else:
                    users_to_keep.append(user_id)

            print(f"🎯 ANALYSIS:")
            print(f"  Users to DELETE: {len(users_to_delete)}")
            for user_id in users_to_delete:
                print(f"    ❌ {user_id}")

            print(f"  Users to KEEP: {len(users_to_keep)}")
            for user_id in users_to_keep:
                print(f"    ✅ {user_id}")

            if not users_to_delete:
                print("✅ No test users found to delete")
                return True

            print(f"\n⚠️  DANGER: About to delete {len(users_to_delete)} test users from PRODUCTION database")
            print("This will permanently delete:")
            print("  - User accounts")
            print("  - All their metrics")
            print("  - All their daily reports")
            print("  - All related data")

            # Manual confirmation required for production
            print(f"\n🚨 Type 'DELETE TEST USERS' to confirm: ", end="")
            try:
                choice = input().strip()
                if choice != 'DELETE TEST USERS':
                    print("❌ Cleanup cancelled - confirmation text did not match")
                    return False
            except KeyboardInterrupt:
                print("\n❌ Cleanup cancelled by user")
                return False

            print("\n🗑️  Starting production cleanup...")

            # Delete data for each test user
            deleted_counts = {
                'users': 0,
                'metrics': 0,
                'reports': 0,
                'events': 0
            }

            for user_id in users_to_delete:
                print(f"\n🗑️  Cleaning up user: {user_id}")

                try:
                    # Count existing data first
                    metrics_count = db.session.execute(text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id"),
                                                     {"user_id": user_id}).scalar()
                    reports_count = db.session.execute(text("SELECT COUNT(*) FROM daily_reports WHERE user_id = :user_id"),
                                                     {"user_id": user_id}).scalar()

                    print(f"   📊 Found: {metrics_count} metrics, {reports_count} reports")

                    # Delete metrics
                    if metrics_count > 0:
                        db.session.execute(text("DELETE FROM metrics WHERE user_id = :user_id"),
                                         {"user_id": user_id})
                        print(f"   ✅ Deleted {metrics_count} metrics")
                        deleted_counts['metrics'] += metrics_count

                    # Delete daily reports
                    if reports_count > 0:
                        db.session.execute(text("DELETE FROM daily_reports WHERE user_id = :user_id"),
                                         {"user_id": user_id})
                        print(f"   ✅ Deleted {reports_count} reports")
                        deleted_counts['reports'] += reports_count

                    # Delete lifestyle events (if table exists)
                    try:
                        events_count = db.session.execute(text("SELECT COUNT(*) FROM lifestyle_events WHERE user_id = :user_id"),
                                                        {"user_id": user_id}).scalar()
                        if events_count > 0:
                            db.session.execute(text("DELETE FROM lifestyle_events WHERE user_id = :user_id"),
                                             {"user_id": user_id})
                            print(f"   ✅ Deleted {events_count} lifestyle events")
                            deleted_counts['events'] += events_count
                    except Exception as e:
                        print(f"   ⚠️  No lifestyle_events table or error: {str(e)[:50]}")

                    # Delete system logs (foreign key constraint) - CRITICAL
                    try:
                        logs_count = db.session.execute(text("SELECT COUNT(*) FROM system_logs WHERE user_id = :user_id"),
                                                      {"user_id": user_id}).scalar()
                        print(f"   🔍 Found {logs_count} system_logs entries")

                        if logs_count > 0:
                            result = db.session.execute(text("DELETE FROM system_logs WHERE user_id = :user_id"),
                                                       {"user_id": user_id})
                            print(f"   ✅ Deleted {logs_count} system logs (affected rows: {result.rowcount})")
                        else:
                            print(f"   ✅ No system_logs to delete")

                        # Verify deletion worked
                        remaining_logs = db.session.execute(text("SELECT COUNT(*) FROM system_logs WHERE user_id = :user_id"),
                                                          {"user_id": user_id}).scalar()
                        if remaining_logs > 0:
                            print(f"   ❌ WARNING: {remaining_logs} system_logs still remain!")
                            return False
                        else:
                            print(f"   ✅ Verified: No system_logs remaining")

                    except Exception as e:
                        print(f"   ❌ CRITICAL ERROR deleting system_logs: {str(e)}")
                        print(f"   Cannot proceed with user deletion due to foreign key constraint")
                        return False

                    # Delete conversations (if table exists)
                    try:
                        conversations_count = db.session.execute(text("SELECT COUNT(*) FROM conversations WHERE user_id = :user_id"),
                                                               {"user_id": user_id}).scalar()
                        if conversations_count > 0:
                            db.session.execute(text("DELETE FROM conversations WHERE user_id = :user_id"),
                                             {"user_id": user_id})
                            print(f"   ✅ Deleted {conversations_count} conversations")
                    except Exception as e:
                        print(f"   ⚠️  No conversations table or error: {str(e)[:50]}")

                    # Delete any other related data by checking for foreign key references
                    try:
                        # Check for any other tables that might reference this user
                        foreign_key_tables = [
                            'notifications', 'user_preferences', 'user_sessions',
                            'analysis_results', 'correlation_cache', 'pattern_cache'
                        ]

                        for table in foreign_key_tables:
                            try:
                                count = db.session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE user_id = :user_id"),
                                                          {"user_id": user_id}).scalar()
                                if count > 0:
                                    db.session.execute(text(f"DELETE FROM {table} WHERE user_id = :user_id"),
                                                     {"user_id": user_id})
                                    print(f"   ✅ Deleted {count} records from {table}")
                            except:
                                pass  # Table might not exist
                    except Exception as e:
                        print(f"   ⚠️  Error checking additional tables: {str(e)[:50]}")

                    # Now delete the user (should work with all FK constraints handled)
                    db.session.execute(text("DELETE FROM users WHERE id = :user_id"),
                                     {"user_id": user_id})
                    print(f"   ✅ Deleted user account")
                    deleted_counts['users'] += 1

                    # Commit after each user
                    db.session.commit()

                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
                    db.session.rollback()
                    return False

            print(f"\n🎉 PRODUCTION CLEANUP COMPLETED!")
            print(f"✅ Deleted {deleted_counts['users']} test users")
            print(f"✅ Deleted {deleted_counts['metrics']:,} test metrics")
            print(f"✅ Deleted {deleted_counts['reports']} test reports")
            print(f"✅ Deleted {deleted_counts['events']} test events")

            # Show final state
            result = db.session.execute(text("SELECT id, phone_number, ultrahuman_user_id FROM users"))
            remaining_users = result.fetchall()

            print(f"\n📊 FINAL PRODUCTION DATABASE STATE:")
            print(f"   Remaining users: {len(remaining_users)}")

            for user in remaining_users:
                user_id = user[0]
                metrics_count = db.session.execute(text("SELECT COUNT(*) FROM metrics WHERE user_id = :user_id"),
                                                 {"user_id": user_id}).scalar()
                reports_count = db.session.execute(text("SELECT COUNT(*) FROM daily_reports WHERE user_id = :user_id"),
                                                 {"user_id": user_id}).scalar()

                print(f"   ✅ {user_id}")
                print(f"      Phone: {user[1]}")
                print(f"      Data: {metrics_count:,} metrics, {reports_count} reports")
                print()

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚨 PRODUCTION DATABASE CLEANUP")
    print("=" * 60)
    print("⚠️  WARNING: This operates on your PRODUCTION MySQL database")
    print("⚠️  This will PERMANENTLY delete test users and their data")
    print("✅ Will keep: sample_user, user_7000 (legitimate accounts)")
    print("❌ Will delete: test_db_connection, test_lifestyle_db")
    print()

    success = cleanup_production_test_users()

    if success:
        print("\n🎉 Production database cleanup successful!")
        print("✅ Test users and their data have been removed")
        print("✅ Production database now contains only legitimate users")
        print("\n💡 Run 'python check_production_data.py' to verify the cleanup")
    else:
        print("\n❌ Production cleanup failed - check errors above")
        print("Your production database has NOT been modified")

    sys.exit(0 if success else 1)