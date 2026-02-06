#!/usr/bin/env python3
"""
Set sample_user to use email alias: adewusiemmanuel+sample@gmail.com
"""

import mysql.connector

def connect_to_db():
    return mysql.connector.connect(
        host='bphlite.mysql.pythonanywhere-services.com',
        user='bphlite',
        password='Opeyemi992!',
        database='bphlite$default'
    )

def set_email_alias():
    print("Setting Email Alias for sample_user")
    print("=" * 40)

    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Show current state
        cursor.execute("SELECT id, ultrahuman_user_id FROM users ORDER BY id")
        users = cursor.fetchall()

        print("BEFORE:")
        for user in users:
            print(f"  {user['id']}: {user['ultrahuman_user_id']}")

        # Update sample_user to use alias
        alias_email = 'adewusiemmanuel+sample@gmail.com'
        print(f"\nUpdating sample_user to use alias: {alias_email}")

        cursor.execute("UPDATE users SET ultrahuman_user_id = %s WHERE id = 'sample_user'", (alias_email,))
        conn.commit()
        print("✅ sample_user updated with email alias")

        # Verify
        cursor.execute("SELECT id, ultrahuman_user_id FROM users ORDER BY id")
        final_users = cursor.fetchall()

        print(f"\nAFTER:")
        for user in final_users:
            print(f"  {user['id']}: {user['ultrahuman_user_id']}")

        print(f"\n📧 EMAIL CONFIGURATION:")
        print(f"  sample_user: adewusiemmanuel+sample@gmail.com → +15875452951")
        print(f"  user_7000: adewusiemmanuel@gmail.com → +17807293140")

        print(f"\n✅ BENEFITS:")
        print(f"  • Both emails deliver to same Gmail inbox")
        print(f"  • Both emails work with Ultrahuman API")
        print(f"  • Database sees them as different (unique constraint satisfied)")
        print(f"  • Dual phone SMS access maintained")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    set_email_alias()
    print(f"\n🚀 NEXT STEP: Test the sync!")
    print(f"python3.10 hourly_sync.py")