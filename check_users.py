#!/usr/bin/env python3
"""
Quick script to check registered users in the database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import User
from utils.database import db

def check_users():
    """Check all registered users"""
    app = create_app()

    with app.app_context():
        print("\n" + "="*60)
        print("📱 REGISTERED USERS")
        print("="*60)

        users = User.query.all()

        if not users:
            print("\n❌ No users found in database!")
            print("\nTo register yourself, run:")
            print("python register_user.py")
            return

        for i, user in enumerate(users, 1):
            print(f"\n👤 User {i}:")
            print(f"   User ID: {user.id}")
            print(f"   Phone Number: {user.phone_number}")
            print(f"   Ultrahuman ID: {user.ultrahuman_user_id}")
            print(f"   Timezone: {user.timezone}")
            print(f"   Active: {'✅ Yes' if user.is_active else '❌ No'}")
            print(f"   Registered: {user.onboarded_at}")

            # Check for additional phone numbers
            if user.preferences and 'additional_phone_numbers' in user.preferences:
                additional = user.preferences['additional_phone_numbers']
                if additional:
                    print(f"   Additional phones: {', '.join(additional)}")

        print("\n" + "="*60)
        print(f"Total users: {len(users)}")
        print("="*60 + "\n")

if __name__ == "__main__":
    try:
        check_users()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure your database is configured correctly in .env")
        import traceback
        traceback.print_exc()
