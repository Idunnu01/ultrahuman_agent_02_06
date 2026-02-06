#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import User

def check_registered_users():
    app = create_app()
    with app.app_context():
        users = User.query.all()
        print("Registered Users:")
        print("=" * 40)
        for user in users:
            print(f"ID: {user.id}")
            print(f"Phone: '{user.phone_number}'")
            print(f"Name: {user.preferences.get('name', 'N/A')}")
            print("-" * 20)

if __name__ == "__main__":
    check_registered_users()