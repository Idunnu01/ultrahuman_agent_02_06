#!/usr/bin/env python3
"""
Fix user_7000's Ultrahuman ID to use proper email
"""

import mysql.connector

def connect_to_db():
    return mysql.connector.connect(
        host='bphlite.mysql.pythonanywhere-services.com',
        user='bphlite',
        password='Opeyemi992!',
        database='bphlite$default'
    )

def fix_user_7000():
    print("Fixing user_7000 Ultrahuman ID")
    print("=" * 40)

    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check current state
        cursor.execute("SELECT id, ultrahuman_user_id, phone_number FROM users ORDER BY id")
        users = cursor.fetchall()

        print("Current users:")
        for user in users:
            print(f"  {user['id']}: UH_ID={user['ultrahuman_user_id']}, Phone={user['phone_number']}")

        # Check if user_7000 exists
        cursor.execute("SELECT id, ultrahuman_user_id FROM users WHERE id = 'user_7000'")
        user_7000 = cursor.fetchone()

        if not user_7000:
            print("\n❌ user_7000 not found")
            return

        current_uh_id = user_7000['ultrahuman_user_id']
        print(f"\nCurrent user_7000 UH ID: {current_uh_id}")

        if current_uh_id == 'uh_7000':
            print("❌ user_7000 has invalid Ultrahuman ID (uh_7000)")
            print("\nOptions to fix:")
            print("1. Set to same email as sample_user (adewusiemmanuel@gmail.com)")
            print("2. Deactivate user_7000 (set is_active = 0)")
            print("3. Delete user_7000 and all data")

            # Since user_7000 has the same data as sample_user, it's likely duplicate
            # Let's check the data overlap
            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = 'user_7000'")
            user_7000_metrics = cursor.fetchone()['count']

            cursor.execute("SELECT COUNT(*) as count FROM metrics WHERE user_id = 'sample_user'")
            sample_user_metrics = cursor.fetchone()['count']

            print(f"\nData comparison:")
            print(f"  sample_user: {sample_user_metrics:,} metrics")
            print(f"  user_7000: {user_7000_metrics:,} metrics")

            if user_7000_metrics > 0:
                # Check if they have similar data (likely duplicates)
                cursor.execute("""
                    SELECT metric_type, COUNT(*) as count
                    FROM metrics
                    WHERE user_id = 'user_7000'
                    GROUP BY metric_type
                    ORDER BY count DESC
                    LIMIT 5
                """)
                user_7000_breakdown = cursor.fetchall()

                print(f"\nuser_7000 top metrics:")
                for metric in user_7000_breakdown:
                    print(f"  {metric['metric_type']}: {metric['count']:,}")

                # User wants to keep user_7000 active with same email for dual phone access
                print(f"\n🔧 FIXING: Set user_7000 to use same email as sample_user")
                print("This will:")
                print("  ✅ Enable API sync for user_7000")
                print("  ✅ Allow both phone numbers to access the same data")
                print("  ✅ Keep both users active")

                # Set user_7000 to use the same email as sample_user
                new_email = 'adewusiemmanuel@gmail.com'
                cursor.execute("UPDATE users SET ultrahuman_user_id = %s WHERE id = 'user_7000'", (new_email,))
                conn.commit()

                print(f"\n✅ Updated user_7000 Ultrahuman ID to: {new_email}")

                # Verify the change
                cursor.execute("SELECT id, ultrahuman_user_id, phone_number, is_active FROM users ORDER BY id")
                final_users = cursor.fetchall()
                print(f"\nFinal user configuration:")
                for user in final_users:
                    status = "ACTIVE" if user['is_active'] else "INACTIVE"
                    print(f"  {user['id']}: {user['ultrahuman_user_id']}, {user['phone_number']}, {status}")

        else:
            print(f"✅ user_7000 already has valid email: {current_uh_id}")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_user_7000()