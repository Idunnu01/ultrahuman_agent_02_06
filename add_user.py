#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import User
from utils.database import db
from datetime import datetime

def create_user(phone, email, name):
    """Create a single user"""
    # Check if user already exists
    existing_user = User.query.filter_by(phone_number=phone).first()
    if existing_user:
        print(f"✅ User already exists: ID {existing_user.id} ({existing_user.phone_number})")
        return existing_user

    # Generate user ID from phone number
    user_id = f"user_{abs(hash(phone)) % 10000}"

    # Create new user (only using fields that exist in the model)
    user = User(
        id=user_id,
        phone_number=phone,
        ultrahuman_user_id=f"uh_{abs(hash(phone)) % 100000}",  # Generate Ultrahuman ID
        timezone='UTC',
        onboarded_at=datetime.utcnow(),
        preferences={"name": name, "email": email},  # Store name/email in preferences JSON
        is_active=True
    )

    db.session.add(user)
    db.session.commit()

    print(f"✅ User created successfully!")
    print(f"   ID: {user.id}")
    print(f"   Phone: {user.phone_number}")
    print(f"   Name: {user.preferences.get('name', 'N/A')}")
    print(f"   Email: {user.preferences.get('email', 'N/A')}")
    print()
    return user

def add_user():
    app = create_app()
    with app.app_context():
        # Add multiple users
        users_to_add = [
            {
                "phone": "+15875452951",
                "email": "idunnu.okunola@gmail.com",
                "name": "Idunnu"
            },
            {
                "phone": "+17807293140",
                "email": "adewusiemmanuel@gmail.com",
                "name": "Apostle Emmanuel"
            }
        ]

        print("Adding users to database...")
        print("=" * 40)

        for user_data in users_to_add:
            create_user(
                phone=user_data["phone"],
                email=user_data["email"],
                name=user_data["name"]
            )

        print("All users processed!")

if __name__ == "__main__":
    add_user()