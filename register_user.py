#!/usr/bin/env python3
"""
Script to register your actual user account for testing correlations with real data
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def register_user():
    """Register your actual user account"""

    print("Registering your actual user account...")
    print("=" * 50)

    try:
        from app import create_app
        from app.models import User
        from utils.database import db

        # Initialize the app context
        app = create_app()

        with app.app_context():
            # Your actual user details
            user_id = "adewusiemmanuel@gmail.com"
            phone_number = "+15875452951"  # Replace with your actual phone
            # Prefer UH_EMAIL from env as Ultrahuman identifier if available
            ultrahuman_user_id = os.getenv("UH_EMAIL", user_id)

            print(f"User ID: {user_id}")
            print(f"Phone: {phone_number}")
            print(f"Ultrahuman ID (from UH_EMAIL): {ultrahuman_user_id}")

            # Check if user already exists
            existing_user = User.query.filter_by(id=user_id).first()
            if existing_user:
                print(f"✅ User {user_id} already exists!")
                print(f"   Phone: {existing_user.phone_number}")
                print(f"   Ultrahuman ID: {existing_user.ultrahuman_user_id}")
                print(f"   Active: {existing_user.is_active}")
                return existing_user

            # Create new user
            new_user = User(
                id=user_id,
                ultrahuman_user_id=ultrahuman_user_id,
                phone_number=phone_number,
                timezone='UTC',
                preferences={'real_user': True}
            )

            try:
                db.session.add(new_user)
                db.session.commit()
                print(f"✅ Successfully registered user: {user_id}")
                return new_user
            except Exception as e:
                print(f"❌ Failed to register user: {str(e)}")
                db.session.rollback()
                return None

    except Exception as e:
        print(f"Error registering user: {str(e)}")
        return None

def check_environment():
    """Check if environment is properly configured"""

    print("\nChecking environment configuration...")
    print("=" * 50)

    # Updated env var names per your credentials
    required_vars = [
        'UH_AUTH_KEY',           # Ultrahuman auth token
        'ULTRAHUMAN_API_BASE',   # API base URL
        'UH_EMAIL'               # Ultrahuman account email/identifier
    ]

    print("Required environment variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'TOKEN' in var or 'AUTH' in var:
                print(f"  ✅ {var}: {'*' * 10} (present)")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set")

    print("\nTo set these variables:")
    print("1. Create a .env file in your project root")
    print("2. Add your Ultrahuman API credentials:")
    print("   UH_AUTH_KEY=your_api_key_here")
    print("   ULTRAHUMAN_API_BASE=https://api.ultrahuman.com")
    print("   UH_EMAIL=your_ultrahuman_email@example.com")

def show_next_steps():
    """Show next steps after registration"""

    print("\n" + "=" * 50)
    print("NEXT STEPS:")
    print("=" * 50)

    print("1. ✅ Register your user account (run this script)")
    print("2. 🔧 Update the script with your actual details (if needed):")
    print("   - Replace the phone number with your real phone")
    print("   - Ensure UH_EMAIL in your .env matches your Ultrahuman account")
    print("3. 🔑 Set up your environment variables (.env file)")
    print("4. 📊 Run data sync to fetch your metrics:")
    print("   python run_backfill.py --user-id adewusiemmanuel@gmail.com --day 2025-08-28")
    print("5. 🧪 Test correlation analysis with your real data")

    print("\nExample .env file:")
    print("UH_AUTH_KEY=your_actual_api_key")
    print("ULTRAHUMAN_API_BASE=https://api.ultrahuman.com")
    print("UH_EMAIL=adewusiemmanuel@gmail.com")

if __name__ == "__main__":
    print("User Registration for Correlation Testing")
    print("=" * 50)

    check_environment()

    print("\n" + "=" * 50)
    print("IMPORTANT: Review details before registering!")
    print("=" * 50)
    print("Configured phone number: +15875452951")
    print("Ultrahuman ID source: UH_EMAIL from .env")

    # Uncomment to perform registration after confirming env is set correctly
    user = register_user()

    show_next_steps()
