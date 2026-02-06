#!/usr/bin/env python3
"""
Fix Phone Number Script
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_phone_number():
    """Fix the phone number for the sample user"""

    print("🔧 Fixing Phone Number for Sample User")
    print("=" * 50)

    try:
        # Override database URL to use MySQL (production database)
        os.environ['DATABASE_URL'] = 'mysql://bphlite:Opeyemi992!@bphlite.mysql.pythonanywhere-services.com/bphlite$default'

        from app import create_app
        from app.models import User
        from utils.database import db

        # Create app context
        app = create_app()

        with app.app_context():
            # Check current user
            user = User.query.get('sample_user')
            if user:
                print(f"📱 Current phone number: {user.phone_number}")

                # Update to correct phone number
                correct_phone = "+15875452951"
                user.phone_number = correct_phone

                # Commit the change
                db.session.commit()

                print(f"✅ Phone number updated to: {correct_phone}")

                # Verify the change
                user = User.query.get('sample_user')
                print(f"🔍 Verification - Phone number: {user.phone_number}")

            else:
                print("❌ User 'sample_user' not found")
                return False

    except Exception as e:
        print(f"❌ Error fixing phone number: {str(e)}")
        return False

    print("\n🎯 Phone number fix completed!")
    return True

if __name__ == "__main__":
    success = fix_phone_number()
    if success:
        print("\n🚀 Ready to test daily reports with correct phone number!")
    else:
        print("\n❌ Phone number fix failed")
        sys.exit(1)
