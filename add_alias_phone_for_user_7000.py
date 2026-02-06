#!/usr/bin/env python3
"""
Add alias phone number for user_7000 so both numbers can interact with the same data
"""

import sys
import os

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def add_alias_phone_for_user_7000():
    """Add alias phone so both numbers can access user_7000 data"""

    try:
        from app import create_app
        from app.models import User
        from utils.database import db

        app = create_app()

        with app.app_context():
            old_phone = '+15875452951'
            new_phone = '+17807293140'
            main_user_id = 'user_7000'
            alias_user_id = 'user_7000_alias'

            print("📱 Setting up dual phone access for user_7000")
            print("=" * 50)

            # Check current user_7000
            main_user = User.query.filter_by(id=main_user_id).first()
            if not main_user:
                print(f"❌ Main user {main_user_id} not found")
                return False

            print(f"✅ Main user_7000:")
            print(f"   Phone: {main_user.phone_number}")
            print(f"   Active: {main_user.is_active}")

            # Check if old phone already exists
            existing_old_phone_user = User.query.filter_by(phone_number=old_phone).first()
            if existing_old_phone_user:
                print(f"✅ Old phone {old_phone} already assigned to: {existing_old_phone_user.id}")
                return True

            # Check if alias user already exists
            existing_alias = User.query.filter_by(id=alias_user_id).first()
            if existing_alias:
                print(f"✅ Alias user {alias_user_id} already exists")
                print(f"   Phone: {existing_alias.phone_number}")
                return True

            # Create alias user with old phone number
            print(f"\n🔄 Creating alias user for old phone number...")

            alias_user = User(
                id=alias_user_id,
                ultrahuman_user_id=main_user.ultrahuman_user_id,  # Same UH ID so same data
                phone_number=old_phone,
                is_active=True,
                timezone=main_user.timezone,
                onboarded_at=main_user.onboarded_at
            )

            db.session.add(alias_user)
            db.session.commit()

            print(f"✅ Created alias user successfully!")
            print(f"   ID: {alias_user_id}")
            print(f"   Phone: {old_phone}")
            print(f"   UH ID: {alias_user.ultrahuman_user_id}")

            # Verify setup
            print(f"\n📋 Verification:")
            all_users = User.query.filter(
                User.ultrahuman_user_id == main_user.ultrahuman_user_id
            ).all()

            print(f"   Users with same UH data:")
            for user in all_users:
                print(f"     {user.id}: {user.phone_number}")

            print(f"\n🎉 Setup Complete!")
            print(f"📱 You can now text from either:")
            print(f"   • {new_phone} (main user_7000)")
            print(f"   • {old_phone} (alias user_7000_alias)")
            print(f"🔗 Both access the same health data via UH ID: {main_user.ultrahuman_user_id}")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sms_interaction():
    """Show how SMS interaction will work"""

    print(f"\n📲 SMS Interaction Setup:")
    print("=" * 40)

    try:
        from app import create_app
        from app.models import User

        app = create_app()

        with app.app_context():
            # Check both users
            main_user = User.query.filter_by(id='user_7000').first()
            alias_user = User.query.filter_by(id='user_7000_alias').first()

            if main_user and alias_user:
                print(f"✅ Both users ready:")
                print(f"   user_7000: {main_user.phone_number}")
                print(f"   user_7000_alias: {alias_user.phone_number}")
                print(f"   Same UH ID: {main_user.ultrahuman_user_id == alias_user.ultrahuman_user_id}")

                print(f"\n📱 SMS Usage:")
                print(f"   Text from {main_user.phone_number}:")
                print(f"     'supplement magnesium 400mg 8am' → logged to user_7000")
                print(f"   Text from {alias_user.phone_number}:")
                print(f"     'supplement magnesium 400mg 8am' → logged to user_7000_alias")
                print(f"   📊 Reports will show data from BOTH users (same UH account)")

                print(f"\n📋 Daily Reports:")
                print(f"   • user_7000 gets reports at 4 AM to {main_user.phone_number}")
                print(f"   • user_7000_alias can interact but won't get duplicate reports")

            return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = add_alias_phone_for_user_7000()

    if success:
        test_sms_interaction()

        print(f"\n🎯 Next Steps:")
        print(f"   1. Test SMS from {'+17807293140'} (main)")
        print(f"   2. Test SMS from {'+15875452951'} (alias)")
        print(f"   3. Both should access the same health data")
        print(f"   4. Daily reports sent to main number only")
    else:
        print(f"\n❌ Setup failed - check database connection")