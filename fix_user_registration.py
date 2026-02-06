#!/usr/bin/env python3
"""
Fix user registration issue and create the user directly in the database.
"""

import sqlite3
import os
from datetime import datetime

def check_and_fix_user():
    """Check database and fix user registration"""

    db_path = "instance/ultrahuman_agent.db"

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    print("=" * 60)
    print("FIXING USER REGISTRATION")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    user_id = "adewusiemmanuel@gmail.com"
    phone_number = "+15875452951"
    ultrahuman_user_id = "adewusiemmanuel@gmail.com"

    print(f"User ID: {user_id}")
    print(f"Phone: {phone_number}")
    print(f"Ultrahuman ID: {ultrahuman_user_id}")
    print()

    # Check if user already exists
    cursor.execute("SELECT id, phone_number, ultrahuman_user_id, is_active FROM users WHERE id = ?", (user_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        print(f"✅ User already exists:")
        print(f"   ID: {existing_user[0]}")
        print(f"   Phone: {existing_user[1]}")
        print(f"   Ultrahuman ID: {existing_user[2]}")
        print(f"   Active: {existing_user[3]}")

        # Check if there are any constraint issues
        cursor.execute("SELECT COUNT(*) FROM users WHERE ultrahuman_user_id = ?", (ultrahuman_user_id,))
        count = cursor.fetchone()[0]
        print(f"   Users with same ultrahuman_user_id: {count}")

        if count > 1:
            print("⚠️  Multiple users with same ultrahuman_user_id found!")
            cursor.execute("SELECT id, phone_number FROM users WHERE ultrahuman_user_id = ?", (ultrahuman_user_id,))
            duplicates = cursor.fetchall()
            for dup in duplicates:
                print(f"     - {dup[0]} (phone: {dup[1]})")

        return True

    # Check for any existing users with the same ultrahuman_user_id
    cursor.execute("SELECT id, phone_number FROM users WHERE ultrahuman_user_id = ?", (ultrahuman_user_id,))
    duplicates = cursor.fetchall()

    if duplicates:
        print(f"⚠️  Found {len(duplicates)} existing user(s) with ultrahuman_user_id '{ultrahuman_user_id}':")
        for dup in duplicates:
            print(f"   - {dup[0]} (phone: {dup[1]})")

        # Ask if we should update the existing user
        print("\nOptions:")
        print("1. Update existing user to use your email as ID")
        print("2. Create new user with different ultrahuman_user_id")
        print("3. Skip user creation")

        choice = input("\nEnter choice (1-3): ").strip()

        if choice == "1":
            # Update the first duplicate to use the new user_id
            update_user_id = duplicates[0][0]
            cursor.execute("UPDATE users SET id = ? WHERE id = ?", (user_id, update_user_id))
            print(f"✅ Updated user {update_user_id} to use ID: {user_id}")
            conn.commit()
            return True
        elif choice == "2":
            # Create new user with different ultrahuman_user_id
            ultrahuman_user_id = f"{user_id}_uh"
            print(f"Using ultrahuman_user_id: {ultrahuman_user_id}")
        elif choice == "3":
            print("Skipping user creation")
            return False
        else:
            print("Invalid choice, skipping")
            return False

    # Create new user
    print("Creating new user...")

    try:
        cursor.execute("""
            INSERT INTO users (id, ultrahuman_user_id, phone_number, timezone, onboarded_at, preferences, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            ultrahuman_user_id,
            phone_number,
            'UTC',
            datetime.utcnow(),
            '{"real_user": true}',
            1
        ))

        conn.commit()
        print(f"✅ Successfully created user: {user_id}")
        return True

    except sqlite3.IntegrityError as e:
        print(f"❌ Database constraint error: {e}")
        print("This might be due to:")
        print("  - Duplicate user ID")
        print("  - Duplicate ultrahuman_user_id")
        print("  - Missing required fields")
        return False
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False
    finally:
        conn.close()

def show_all_users():
    """Show all users in the database"""

    print("\n" + "=" * 60)
    print("ALL USERS IN DATABASE")
    print("=" * 60)

    db_path = "instance/ultrahuman_agent.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, phone_number, ultrahuman_user_id, is_active, onboarded_at FROM users")
    users = cursor.fetchall()

    for i, user in enumerate(users, 1):
        print(f"{i}. User: {user[0]}")
        print(f"   Phone: {user[1]}")
        print(f"   Ultrahuman ID: {user[2]}")
        print(f"   Active: {user[3]}")
        print(f"   Onboarded: {user[4]}")
        print()

    conn.close()

if __name__ == "__main__":
    print("User Registration Fix")
    print("=" * 60)

    # Show current users
    show_all_users()

    # Fix user registration
    success = check_and_fix_user()

    if success:
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. ✅ User registration fixed")
        print("2. 📊 Now you can backfill your data:")
        print("   python run_backfill.py --user-id adewusiemmanuel@gmail.com --start 2024-10-01 --end 2025-08-28")
        print("3. 🧪 Test correlation analysis with your real data")
    else:
        print("\n❌ User registration failed. Please check the errors above.")
