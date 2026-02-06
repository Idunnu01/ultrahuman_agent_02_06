#!/usr/bin/env python3
"""
Script to delete test users from production database
Run this on PythonAnywhere
"""

import mysql.connector
import sys
from datetime import datetime

def connect_to_production_db():
    """Connect to the production MySQL database"""

    db_config = {
        'host': 'bphlite.mysql.pythonanywhere-services.com',
        'user': 'bphlite',
        'password': 'Opeyemi992!',
        'database': 'bphlite$default'
    }

    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def delete_test_users():
    """Delete the 4 test users and all their associated data"""

    # List of test user IDs to delete
    test_user_ids = [
        'test_user_1acb026a',
        'test_user_c22bcfed',
        'test_user_f6f81aba',
        'test_user_fc6cc669'
    ]

    print("🗑️  DELETING TEST USERS FROM PRODUCTION DATABASE")
    print("=" * 60)
    print(f"Users to delete: {test_user_ids}")
    print()

    # Safety confirmation
    confirm = input("⚠️  Are you sure you want to DELETE these users? (type 'DELETE' to confirm): ")
    if confirm != 'DELETE':
        print("❌ Operation cancelled")
        return

    conn = connect_to_production_db()
    if not conn:
        print("❌ Failed to connect to production database")
        return

    cursor = conn.cursor()

    try:
        # Start transaction
        conn.start_transaction()

        deleted_count = 0

        for user_id in test_user_ids:
            print(f"\n🔍 Checking user: {user_id}")

            # Check if user exists
            cursor.execute("SELECT id, phone_number FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                print(f"   ⚠️  User {user_id} not found, skipping")
                continue

            print(f"   ✅ Found user: {user[0]} (phone: {user[1]})")

            # Count associated data before deletion
            data_counts = {}

            # Check metrics
            cursor.execute("SELECT COUNT(*) FROM metrics WHERE user_id = %s", (user_id,))
            data_counts['metrics'] = cursor.fetchone()[0]

            # Check other tables that might have user data
            tables_to_check = [
                'statistical_baselines', 'correlations', 'interventions',
                'patterns', 'alerts', 'daily_reports', 'ml_models',
                'system_logs', 'conversations'
            ]

            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = %s", (user_id,))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        data_counts[table] = count
                except mysql.connector.Error:
                    # Table might not exist, skip
                    pass

            # Display what will be deleted
            if data_counts:
                print(f"   📊 Associated data to delete:")
                for table, count in data_counts.items():
                    print(f"      - {table}: {count} records")
            else:
                print(f"   📊 No associated data found")

            # Delete associated data first (handle foreign key constraints properly)
            # Order matters - delete child tables first
            tables_to_clean = [
                'system_logs', 'ml_models', 'daily_reports',
                'alerts', 'patterns', 'interventions', 'correlations',
                'statistical_baselines', 'metrics', 'conversations'
            ]

            # Disable foreign key checks temporarily for this connection
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            for table in tables_to_clean:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE user_id = %s", (user_id,))
                    deleted_rows = cursor.rowcount
                    if deleted_rows > 0:
                        print(f"   🗑️  Deleted {deleted_rows} records from {table}")
                except mysql.connector.Error as e:
                    # Table might not exist or have user_id column
                    print(f"   ⚠️  Could not delete from {table}: {e}")

            # Re-enable foreign key checks
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            # Finally delete the user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            if cursor.rowcount > 0:
                print(f"   ✅ Deleted user: {user_id}")
                deleted_count += 1
            else:
                print(f"   ❌ Failed to delete user: {user_id}")

        # Commit transaction
        conn.commit()

        print(f"\n🎉 DELETION COMPLETE!")
        print(f"✅ Successfully deleted {deleted_count} test users")
        print(f"⏰ Completed at: {datetime.now()}")

        # Verify deletion by checking remaining users
        print(f"\n🔍 VERIFYING REMAINING USERS:")
        cursor.execute("SELECT id, phone_number FROM users ORDER BY id")
        remaining_users = cursor.fetchall()

        print(f"Remaining users: {len(remaining_users)}")
        for user in remaining_users:
            print(f"  - {user[0]} (phone: {user[1]})")

    except mysql.connector.Error as e:
        # Rollback on error
        conn.rollback()
        print(f"❌ Error during deletion: {e}")
        print("🔄 Transaction rolled back - no changes made")

    finally:
        cursor.close()
        conn.close()

def list_users_only():
    """Just list all users without deleting anything"""

    print("👥 CURRENT USERS IN PRODUCTION DATABASE")
    print("=" * 50)

    conn = connect_to_production_db()
    if not conn:
        return

    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, phone_number, ultrahuman_user_id, onboarded_at FROM users ORDER BY id")
        users = cursor.fetchall()

        print(f"Total users: {len(users)}")
        for user in users:
            print(f"  - {user[0]}")
            print(f"    Phone: {user[1]}")
            print(f"    UH ID: {user[2]}")
            print(f"    Onboarded: {user[3]}")
            print()

    except mysql.connector.Error as e:
        print(f"❌ Error: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_users_only()
    else:
        delete_test_users()

    print("\n" + "=" * 60)
    print("USAGE:")
    print("  python delete_test_users.py        # Delete test users")
    print("  python delete_test_users.py --list # Just list users")
    print("")
    print("⚠️  SAFETY NOTES:")
    print("- This script only deletes users starting with 'test_user_'")
    print("- It will ask for confirmation before deleting")
    print("- It deletes ALL associated data (metrics, reports, etc.)")
    print("- Run with --list first to verify current users")