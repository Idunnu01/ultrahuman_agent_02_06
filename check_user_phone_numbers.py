#!/usr/bin/env python3
"""
Check user phone numbers for SMS issues
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def check_user_phone_numbers():
    """Check all user phone numbers for validity"""

    print("📱 Checking User Phone Numbers")
    print("="*50)

    try:
        from app import create_app
        from app.models import User

        app = create_app()

        with app.app_context():
            users = User.query.all()

            print(f"📊 Found {len(users)} users")

            phone_issues = []
            valid_users = []

            for user in users:
                print(f"\n👤 User: {user.id}")
                print(f"   Phone: {user.phone_number}")
                print(f"   Active: {user.is_active}")
                print(f"   Created: {user.created_at}")

                # Check phone number validity
                phone_valid = True
                issues = []

                if not user.phone_number:
                    issues.append("No phone number")
                    phone_valid = False
                elif not user.phone_number.startswith('+'):
                    issues.append("Phone number missing country code (+)")
                    phone_valid = False
                elif len(user.phone_number) < 10:
                    issues.append("Phone number too short")
                    phone_valid = False
                elif not user.phone_number[1:].replace('-', '').replace(' ', '').isdigit():
                    issues.append("Phone number contains non-numeric characters")
                    phone_valid = False

                # Check if it's a test number
                test_numbers = ['+1234567890', '+0000000000', '+1111111111']
                if user.phone_number in test_numbers:
                    issues.append("Test phone number (won't receive real SMS)")

                if phone_valid and user.is_active:
                    valid_users.append(user)
                    print(f"   ✅ Valid phone number")
                else:
                    phone_issues.append((user, issues))
                    print(f"   ❌ Issues: {', '.join(issues)}")

            # Summary
            print(f"\n📊 Phone Number Summary:")
            print(f"   Total users: {len(users)}")
            print(f"   Valid phone numbers: {len(valid_users)}")
            print(f"   Users with issues: {len(phone_issues)}")

            if phone_issues:
                print(f"\n⚠️ Users with phone number issues:")
                for user, issues in phone_issues:
                    print(f"   {user.id}: {', '.join(issues)}")

            # Check for SMS-ready users
            sms_ready_users = [u for u in valid_users if u.phone_number not in test_numbers]
            print(f"\n📱 SMS-ready users: {len(sms_ready_users)}")

            for user in sms_ready_users:
                print(f"   {user.id}: {user.phone_number}")

            return len(phone_issues) == 0

    except Exception as e:
        print(f"❌ Error checking phone numbers: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def suggest_phone_fixes():
    """Suggest fixes for common phone number issues"""

    print(f"\n🔧 Suggested Fixes for Phone Number Issues:")
    print("="*50)

    print(f"1. **Test User Phone Numbers**:")
    print(f"   - Change test numbers to real numbers for SMS delivery")
    print(f"   - Format: +1XXXXXXXXXX (US) or +44XXXXXXXXX (UK)")

    print(f"\n2. **Missing Country Codes**:")
    print(f"   - Add '+1' prefix for US numbers")
    print(f"   - Add appropriate country code for international numbers")

    print(f"\n3. **Invalid Characters**:")
    print(f"   - Remove spaces, dashes, parentheses")
    print(f"   - Keep only '+' prefix and digits")

    print(f"\n4. **SMS Testing**:")
    print(f"   - Use your own phone number for initial testing")
    print(f"   - Verify Twilio account SMS capabilities")

    return True

if __name__ == '__main__':
    print(f"📱 User Phone Number Check")

    success = check_user_phone_numbers()
    suggest_phone_fixes()

    if success:
        print(f"\n✅ All phone numbers are valid!")
    else:
        print(f"\n⚠️ Some phone numbers need fixing for SMS delivery")