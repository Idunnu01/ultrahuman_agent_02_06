#!/usr/bin/env python3
"""
Update phone number for user_7000 in production database
Run this on PythonAnywhere
"""

import mysql.connector

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

def update_user_phone():
    """Update sample_user phone number to dummy number"""

    user_id = "sample_user"
    new_phone = "+15551234567"  # Dummy number for sample_user

    print(f"📱 UPDATING PHONE NUMBER FOR {user_id}")
    print("=" * 50)

    conn = connect_to_production_db()
    if not conn:
        print("❌ Failed to connect to production database")
        return

    cursor = conn.cursor()

    try:
        # Check current phone
        cursor.execute("SELECT phone_number FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            print(f"❌ User {user_id} not found")
            return

        old_phone = result[0]
        print(f"Current phone: {old_phone}")
        print(f"New phone: {new_phone}")

        # Confirm change
        confirm = input("\n⚠️  Confirm phone number update? (type 'UPDATE' to confirm): ")
        if confirm != 'UPDATE':
            print("❌ Operation cancelled")
            return

        # Update phone number
        cursor.execute("UPDATE users SET phone_number = %s WHERE id = %s", (new_phone, user_id))

        if cursor.rowcount > 0:
            conn.commit()
            print(f"✅ Successfully updated phone number for {user_id}")
            print(f"   Old: {old_phone}")
            print(f"   New: {new_phone}")
        else:
            print(f"❌ No rows updated for user {user_id}")

    except mysql.connector.Error as e:
        conn.rollback()
        print(f"❌ Error updating phone number: {e}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    update_user_phone()