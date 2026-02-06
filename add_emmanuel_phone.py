#!/usr/bin/env python3
"""
Add +15875452951 to Apostle Emmanuel's phone numbers
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

def add_emmanuel_phone():
    """Add +15875452951 to user_7000 (Apostle Emmanuel)"""

    try:
        from app import create_app
        from app.models import User
        from utils.database import db

        app = create_app()
        with app.app_context():
            # Find Apostle Emmanuel
            user = User.query.filter_by(id='user_7000').first()

            if not user:
                print("❌ User user_7000 (Apostle Emmanuel) not found!")
                return False

            name = user.preferences.get('name', 'No name') if user.preferences else 'No name'
            print(f"Found user: {user.id} ({name})")
            print(f"Primary phone: {user.phone_number}")

            # Get current additional phones
            current_additional = user.preferences.get('additional_phone_numbers', []) if user.preferences else []
            print(f"Current additional phones: {current_additional}")

            new_phone = "+15875452951"

            if new_phone == user.phone_number:
                print(f"❌ {new_phone} is already the primary phone number.")
                return False

            if new_phone in current_additional:
                print(f"❌ {new_phone} is already in additional phone numbers.")
                return False

            # Add to additional phones
            if not user.preferences:
                user.preferences = {}

            additional_phones = user.preferences.get('additional_phone_numbers', [])
            additional_phones.append(new_phone)
            user.preferences['additional_phone_numbers'] = additional_phones

            # Update database
            db.session.commit()

            print(f"\n✅ Successfully added {new_phone} to {user.id} ({name})")
            print(f"\n📱 Apostle Emmanuel's authorized phone numbers:")
            print(f"   Primary: {user.phone_number}")
            for i, phone in enumerate(user.preferences['additional_phone_numbers'], 1):
                print(f"   Additional {i}: {phone}")

            total_phones = 1 + len(user.preferences['additional_phone_numbers'])
            print(f"\n🎯 Total authorized phones: {total_phones}")

            print(f"\n✅ SMS Access for Apostle Emmanuel:")
            print(f"   Text from {user.phone_number} → access user_7000 data")
            print(f"   Text from {new_phone} → access user_7000 data")

            return True

    except Exception as e:
        print(f"❌ Error adding phone number: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ADDING +15875452951 TO APOSTLE EMMANUEL")
    print("=" * 60)
    add_emmanuel_phone()