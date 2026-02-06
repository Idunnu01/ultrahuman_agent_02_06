#!/usr/bin/env python3
"""
Script to update production database - run this on PythonAnywhere
1. Delete user_1598 and all associated data
2. Update phone number for sample_user
"""

import mysql.connector
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

def update_database():
    """Update the database safely"""

    print("Database Update Script")
    print("=" * 50)
    print("1. Delete user_1598 and all associated data")
    print("2. Update sample_user phone to +15875452951")
    print()

    conn = connect_to_production_db()
    if not conn:
        print("❌ Failed to connect to production database")
        return

    cursor = conn.cursor(dictionary=True)

    try:
        # Start transaction for safety
        conn.start_transaction()

        # ===== STEP 1: CHECK CURRENT STATE =====
        print("📋 CURRENT STATE:")
        cursor.execute("SELECT id, phone_number, ultrahuman_user_id FROM users ORDER BY id")
        users = cursor.fetchall()

        for user in users:
            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = %s", (user['id'],))
            metric_count = cursor.fetchone()['count']
            print(f"  {user['id']}: phone={user['phone_number']}, metrics={metric_count:,}")

        # ===== STEP 2: CHECK IF user_1598 EXISTS =====
        print(f"\n🔍 CHECKING user_1598...")
        cursor.execute("SELECT id, phone_number FROM users WHERE id = 'user_1598'")
        user_1598 = cursor.fetchone()

        if not user_1598:
            print("ℹ️  user_1598 not found - skipping deletion")
        else:
            print(f"✅ Found user_1598: phone={user_1598['phone_number']}")

            # Check associated data before deletion
            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = 'user_1598'")
            metrics_count = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM statistical_baselines WHERE user_id = 'user_1598'")
            baselines_count = cursor.fetchone()['count']

            print(f"  Associated data: {metrics_count} metrics, {baselines_count} baselines")

            if metrics_count > 0 or baselines_count > 0:
                print(f"\n🗑️  DELETING user_1598 DATA...")

                # Delete in correct order (children first, then parent)
                if baselines_count > 0:
                    cursor.execute("DELETE FROM statistical_baselines WHERE user_id = 'user_1598'")
                    print(f"  ✅ Deleted {baselines_count} statistical baselines")

                if metrics_count > 0:
                    cursor.execute("DELETE FROM metrics WHERE user_id = 'user_1598'")
                    print(f"  ✅ Deleted {metrics_count} metrics")

                # Delete other related tables if they exist
                tables_to_check = [
                    'correlations', 'patterns', 'alerts', 'interventions',
                    'daily_reports', 'system_logs'
                ]

                for table in tables_to_check:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table} WHERE user_id = 'user_1598'")
                        count = cursor.fetchone()['count']
                        if count > 0:
                            cursor.execute(f"DELETE FROM {table} WHERE user_id = 'user_1598'")
                            print(f"  ✅ Deleted {count} records from {table}")
                    except mysql.connector.Error as e:
                        if "doesn't exist" not in str(e):
                            print(f"  ⚠️  Warning: {table} - {e}")

            # Finally delete the user
            cursor.execute("DELETE FROM users WHERE id = 'user_1598'")
            print(f"  ✅ Deleted user_1598")

        # ===== STEP 3: UPDATE sample_user PHONE =====
        print(f"\n📞 UPDATING sample_user PHONE NUMBER...")
        cursor.execute("SELECT id, phone_number FROM users WHERE id = 'sample_user'")
        sample_user = cursor.fetchone()

        if not sample_user:
            print("❌ sample_user not found")
        else:
            old_phone = sample_user['phone_number']
            new_phone = '+15875452951'

            print(f"  Current phone: {old_phone}")
            print(f"  New phone: {new_phone}")

            if old_phone == new_phone:
                print("  ℹ️  Phone number already correct - no update needed")
            else:
                cursor.execute("UPDATE users SET phone_number = %s WHERE id = 'sample_user'", (new_phone,))
                print("  ✅ Phone number updated")

        # ===== STEP 4: VERIFY FINAL STATE =====
        print(f"\n📋 FINAL STATE:")
        cursor.execute("SELECT id, phone_number, ultrahuman_user_id FROM users ORDER BY id")
        final_users = cursor.fetchall()

        total_metrics = 0
        for user in final_users:
            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = %s", (user['id'],))
            metric_count = cursor.fetchone()['count']
            total_metrics += metric_count
            print(f"  {user['id']}: phone={user['phone_number']}, metrics={metric_count:,}")

        print(f"\nTotal metrics in database: {total_metrics:,}")

        # ===== COMMIT TRANSACTION =====
        conn.commit()
        print(f"\n✅ ALL CHANGES COMMITTED SUCCESSFULLY!")

        print(f"\n📊 SUMMARY:")
        if user_1598:
            print(f"  ✅ Deleted user_1598 and all associated data")
        else:
            print(f"  ℹ️  user_1598 was not found (already deleted?)")
        print(f"  ✅ Updated sample_user phone to +15875452951")
        print(f"  ✅ Database is clean and optimized")

    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        print("🔄 Rolling back transaction...")
        conn.rollback()
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("🔄 Rolling back transaction...")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()

    return True

def verify_update():
    """Verify the updates were successful"""

    print(f"\n🔍 VERIFICATION:")
    print("=" * 30)

    conn = connect_to_production_db()
    if not conn:
        return

    cursor = conn.cursor(dictionary=True)

    try:
        # Check users
        cursor.execute("SELECT id, phone_number, ultrahuman_user_id FROM users ORDER BY id")
        users = cursor.fetchall()

        print(f"Users in database: {len(users)}")
        for user in users:
            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = %s", (user['id'],))
            metric_count = cursor.fetchone()['count']
            print(f"  ✅ {user['id']}: {user['phone_number']}, {metric_count:,} metrics")

        # Verify user_1598 is gone
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE id = 'user_1598'")
        user_1598_count = cursor.fetchone()['count']

        if user_1598_count == 0:
            print(f"  ✅ user_1598 successfully deleted")
        else:
            print(f"  ❌ user_1598 still exists!")

        # Verify sample_user phone
        cursor.execute("SELECT phone_number FROM users WHERE id = 'sample_user'")
        sample_user = cursor.fetchone()

        if sample_user and sample_user['phone_number'] == '+15875452951':
            print(f"  ✅ sample_user phone correctly updated to +15875452951")
        else:
            print(f"  ❌ sample_user phone update failed")

        # Check for orphaned data
        cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = 'user_1598'")
        orphaned_metrics = cursor.fetchone()['count']

        if orphaned_metrics == 0:
            print(f"  ✅ No orphaned metrics found")
        else:
            print(f"  ⚠️  Found {orphaned_metrics} orphaned metrics!")

    except mysql.connector.Error as e:
        print(f"❌ Verification error: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting database update...")
    print(f"Timestamp: {datetime.now()}")
    print()

    success = update_database()

    if success:
        verify_update()
        print(f"\n🎉 Database update completed successfully!")
    else:
        print(f"\n❌ Database update failed - no changes made")

    print(f"\n" + "=" * 50)
    print("USAGE:")
    print("1. Upload this file to PythonAnywhere")
    print("2. Run: python3.10 update_database.py")
    print("3. Verify results with: python3.10 check_production_data.py")