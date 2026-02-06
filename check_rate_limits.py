#!/usr/bin/env python3
"""
Check Twilio account limits and recent message status
"""

import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def check_twilio_limits():
    """Check Twilio account usage and limits"""

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')

    if not account_sid or not auth_token:
        print("❌ Missing Twilio credentials")
        return

    print("📊 TWILIO RATE LIMIT CHECK")
    print("=" * 40)

    try:
        # Check account info
        print("🔍 Checking account info...")
        account_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
        response = requests.get(account_url, auth=(account_sid, auth_token))

        if response.status_code == 200:
            account_data = response.json()
            print(f"✅ Account Status: {account_data.get('status')}")
            print(f"✅ Account Type: {account_data.get('type')}")
        else:
            print(f"❌ Account check failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Error checking account: {str(e)}")

    try:
        # Check recent messages (last 24 hours)
        print("\n📨 Checking recent messages...")
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        messages_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        params = {
            'DateSent>': yesterday.strftime('%Y-%m-%d'),
            'PageSize': 50
        }

        response = requests.get(messages_url, auth=(account_sid, auth_token), params=params)

        if response.status_code == 200:
            messages_data = response.json()
            messages = messages_data.get('messages', [])

            print(f"✅ Total messages in last 24h: {len(messages)}")

            # Count by status
            status_counts = {}
            your_phone = '+15875452951'

            print(f"\n📱 Messages to/from your phone ({your_phone}):")
            your_messages = 0

            for msg in messages:
                status = msg.get('status')
                status_counts[status] = status_counts.get(status, 0) + 1

                # Check messages involving your phone
                if msg.get('to') == your_phone or msg.get('from') == your_phone:
                    your_messages += 1
                    direction = "→" if msg.get('to') == your_phone else "←"
                    print(f"  {direction} {msg.get('date_sent')}: {msg.get('status')} - {msg.get('body', '')[:30]}...")

            print(f"\n📊 Message Status Summary:")
            for status, count in status_counts.items():
                print(f"  {status}: {count}")

            print(f"\n🎯 Your phone messages: {your_messages}")

            # Check for failed messages
            failed_statuses = ['failed', 'undelivered', 'rejected']
            failed_count = sum(status_counts.get(status, 0) for status in failed_statuses)

            if failed_count > 0:
                print(f"⚠️  Failed messages: {failed_count}")
            else:
                print("✅ No failed messages")

        else:
            print(f"❌ Messages check failed: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error checking messages: {str(e)}")

def check_app_rate_limits():
    """Check your app's internal rate limits"""
    print("\n🚀 APP RATE LIMIT CHECK")
    print("=" * 40)

    # The error from logs was:
    # "Rate limit exceeded for user sample_user, type total_daily"

    print("From your logs, the issue is:")
    print("❌ 'Rate limit exceeded for user sample_user, type total_daily'")
    print()
    print("This is from YOUR app's internal rate limiting, not Twilio!")
    print()
    print("Possible solutions:")
    print("1. Check your MetricsService rate limiting logic")
    print("2. Reset daily limits for test user")
    print("3. Increase rate limits for testing")
    print("4. Check database rate limit records")

if __name__ == "__main__":
    check_twilio_limits()
    check_app_rate_limits()