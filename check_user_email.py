#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

def check_user_emails():
    """Check what Ultrahuman emails/IDs each user has configured"""

    try:
        from app import create_app
        from app.models import User
        from services.metrics_service import MetricsService

        app = create_app()
        with app.app_context():
            users = User.query.all()
            print("=" * 80)
            print("USER ULTRAHUMAN EMAIL CONFIGURATION")
            print("=" * 80)

            service = MetricsService()

            for user in users:
                name = user.preferences.get('name', 'No name') if user.preferences else 'No name'
                print(f"\nUser: {user.id} ({name})")
                print(f"  ultrahuman_user_id: {user.ultrahuman_user_id}")
                print(f"  phone_number: {user.phone_number}")

                if user.preferences:
                    print(f"  preferences: {user.preferences}")

                # Test what email the service would use
                resolved_email = service._resolve_uh_email(user)
                print(f"  → Resolved email for API: {resolved_email}")

                # Check if this is the same as global setting
                global_email = os.getenv("UH_EMAIL")
                if resolved_email == global_email:
                    print(f"  ⚠️  Using global email setting (all users will get same data)")
                else:
                    print(f"  ✅ Using user-specific email")

            print(f"\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Global UH_EMAIL setting: {os.getenv('UH_EMAIL')}")
            print(f"Total users: {len(users)}")

            # Count how many users have unique emails
            unique_emails = set()
            for user in users:
                email = service._resolve_uh_email(user)
                if email:
                    unique_emails.add(email)

            print(f"Unique Ultrahuman emails: {len(unique_emails)}")
            print(f"Email addresses: {list(unique_emails)}")

            if len(unique_emails) == 1:
                print("\n⚠️  WARNING: All users share the same Ultrahuman email!")
                print("   This means data collection only works for one person.")
                print("\n💡 SOLUTIONS:")
                print("   1. Add individual ultrahuman_user_id for each user")
                print("   2. Or add 'ultrahuman_email' to user preferences")
                print("   3. Or this is intentional (family/team sharing one account)")
            else:
                print(f"\n✅ Multi-user setup detected ({len(unique_emails)} unique emails)")

    except Exception as e:
        print(f"Error checking user emails: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_user_emails()