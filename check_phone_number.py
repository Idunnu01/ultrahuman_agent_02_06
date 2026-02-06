#!/usr/bin/env python3
"""
Check if phone number was updated in database
"""

import sys
import os

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def check_phone_number():
    """Check current phone number in database"""

    print("📞 CHECKING USER PHONE NUMBER")
    print("=" * 40)

    try:
        from app import create_app
        app = create_app()

        with app.app_context():
            from app.models import User

            # Check user_7000
            user = User.query.filter_by(id='user_7000').first()

            if user:
                print(f"   ✅ Found user: {user.id}")
                print(f"   📱 Current phone: {user.phone_number}")

                if user.phone_number == '+15875452951':
                    print("   🎉 Phone number is correctly set to +15875452951!")
                    print("   ✅ SMS system ready for testing")
                    return True
                else:
                    print("   ⚠️ Phone number is NOT +15875452951")
                    print("   🔧 Need to update phone number")
                    return False
            else:
                print("   ❌ User user_7000 not found")

                # Show all users
                all_users = User.query.all()
                print(f"   📋 Available users ({len(all_users)}):")
                for u in all_users:
                    print(f"      - {u.id}: {u.phone_number}")
                return False

    except Exception as e:
        print(f"   ❌ Database check failed: {str(e)}")

        if "Access denied" in str(e):
            print("   💡 Database connection issue - use MySQL console instead")
            print()
            print("   🔧 ALTERNATIVE: Check via PythonAnywhere MySQL Console")
            print("   1. Go to PythonAnywhere Dashboard → Databases")
            print("   2. Click 'Open MySQL console' for bphlite$ultrahuman_agent")
            print("   3. Run: SELECT id, phone_number FROM users WHERE id = 'user_7000';")
            print("   4. If phone is not +15875452951, run:")
            print("      UPDATE users SET phone_number = '+15875452951' WHERE id = 'user_7000';")

        return False

def update_phone_sql():
    """Show SQL commands to update phone number"""

    print()
    print("📝 SQL COMMANDS TO UPDATE PHONE NUMBER")
    print("=" * 40)
    print()
    print("Copy these commands into PythonAnywhere MySQL console:")
    print()
    print("-- Check current phone number")
    print("SELECT id, phone_number FROM users WHERE id = 'user_7000';")
    print()
    print("-- Update phone number")
    print("UPDATE users SET phone_number = '+15875452951' WHERE id = 'user_7000';")
    print()
    print("-- Verify update")
    print("SELECT id, phone_number FROM users WHERE id = 'user_7000';")
    print()
    print("🎯 Expected result: phone_number should show +15875452951")

if __name__ == '__main__':
    success = check_phone_number()

    if not success:
        update_phone_sql()

    print()
    print("🚀 NEXT STEPS AFTER PHONE UPDATE:")
    print("1. Configure Twilio webhook: https://bphlite.pythonanywhere.com/webhook/sms")
    print("2. Send test SMS from +15875452951: 'Hello, how are you?'")
    print("3. Expect ChatGPT response!")