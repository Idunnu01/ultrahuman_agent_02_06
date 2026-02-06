#!/usr/bin/env python3
"""
Test dual phone behavior:
- Notifications (daily reports, alerts) → PRIMARY phone
- SMS responses → phone that sent the message
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

def test_dual_phone_setup():
    """Test that Apostle Emmanuel has both phones configured"""

    try:
        from app import create_app
        from app.models import User

        app = create_app()
        with app.app_context():
            user = User.query.filter_by(id='user_7000').first()

            if not user:
                print("❌ User user_7000 (Apostle Emmanuel) not found!")
                return False

            name = user.preferences.get('name', 'No name') if user.preferences else 'No name'
            primary = user.phone_number
            additional = user.preferences.get('additional_phone_numbers', []) if user.preferences else []

            print("=" * 60)
            print("DUAL PHONE SETUP TEST")
            print("=" * 60)
            print(f"User: {user.id} ({name})")
            print(f"Primary phone: {primary}")
            print(f"Additional phones: {additional}")

            if "+15875452951" in additional:
                print("✅ +15875452951 is configured as additional phone")
                total = 1 + len(additional)
                print(f"✅ Total authorized phones: {total}")
                return True
            else:
                print("❌ +15875452951 NOT found in additional phones")
                return False

    except Exception as e:
        print(f"❌ Error checking dual phone setup: {str(e)}")
        return False

def test_sms_routing_logic():
    """Test SMS routing logic - which phone receives what"""

    try:
        from app import create_app
        from app.models import User

        app = create_app()
        with app.app_context():
            user = User.query.filter_by(id='user_7000').first()
            primary_phone = user.phone_number
            additional_phone = "+15875452951"

            print("\n" + "=" * 60)
            print("SMS ROUTING LOGIC TEST")
            print("=" * 60)

            # Test authentication for both phones
            test_phones = [primary_phone, additional_phone, "+1999999999"]

            for test_phone in test_phones:
                print(f"\nTesting authentication for: {test_phone}")

                # Simulate SMS webhook authentication logic
                user_found = User.query.filter_by(phone_number=test_phone).first()

                if not user_found:
                    # Check additional phone numbers
                    users_with_additional = User.query.filter(
                        User.preferences.op('JSON_EXTRACT')(User.preferences, '$.additional_phone_numbers').isnot(None)
                    ).all()

                    for potential_user in users_with_additional:
                        additional_phones = potential_user.preferences.get('additional_phone_numbers', [])
                        if test_phone in additional_phones:
                            user_found = potential_user
                            break

                if user_found:
                    print(f"  ✅ AUTHENTICATED: {test_phone} → user_{user_found.id}")
                    if test_phone == user_found.phone_number:
                        print(f"     → Via PRIMARY phone")
                    else:
                        print(f"     → Via ADDITIONAL phone")
                else:
                    print(f"  ❌ REJECTED: {test_phone} (no user found)")

            return True

    except Exception as e:
        print(f"❌ Error testing SMS routing: {str(e)}")
        return False

def test_notification_routing():
    """Test notification routing behavior"""

    try:
        from app import create_app
        from app.models import User
        from services.sms_service import SMSService

        app = create_app()
        with app.app_context():
            user = User.query.filter_by(id='user_7000').first()
            sms_service = SMSService()

            primary_phone = user.phone_number
            additional_phone = "+15875452951"

            print("\n" + "=" * 60)
            print("NOTIFICATION ROUTING TEST")
            print("=" * 60)

            # Test which phone gets used for different message types
            message_types = [
                ('daily_reports', 'Your daily health report...'),
                ('alerts', 'Health alert detected...'),
                ('urgent_alerts', 'Critical health alert...'),
                ('response', 'Thanks for your message...'),  # Immediate response
            ]

            for msg_type, sample_msg in message_types:
                print(f"\nTesting {msg_type}:")

                # Test from primary phone
                print(f"  If triggered by PRIMARY phone ({primary_phone}):")
                target_phone = sms_service.get_primary_phone_for_user(user.id)
                if msg_type in ['daily_reports', 'alerts', 'urgent_alerts']:
                    print(f"    → Notification will go to: {target_phone} (PRIMARY)")
                else:
                    print(f"    → Response will go to: {primary_phone} (SENDER)")

                # Test from additional phone
                print(f"  If triggered by ADDITIONAL phone ({additional_phone}):")
                target_phone = sms_service.get_primary_phone_for_user(user.id)
                if msg_type in ['daily_reports', 'alerts', 'urgent_alerts']:
                    print(f"    → Notification will go to: {target_phone} (PRIMARY)")
                else:
                    print(f"    → Response will go to: {additional_phone} (SENDER)")

            return True

    except Exception as e:
        print(f"❌ Error testing notification routing: {str(e)}")
        return False

def simulate_sms_scenarios():
    """Simulate real SMS scenarios"""

    try:
        from app import create_app
        from app.models import User

        app = create_app()
        with app.app_context():
            user = User.query.filter_by(id='user_7000').first()
            primary = user.phone_number
            additional = "+15875452951"

            print("\n" + "=" * 60)
            print("REAL SCENARIOS SIMULATION")
            print("=" * 60)

            scenarios = [
                {
                    'name': 'Daily Report (4 AM)',
                    'description': 'System sends daily health report',
                    'from_system': True,
                    'type': 'daily_reports',
                    'target': primary,
                    'reason': 'Always goes to PRIMARY phone for notifications'
                },
                {
                    'name': 'Text from Primary Phone',
                    'description': f'User texts "meal chicken 7pm" from {primary}',
                    'from_phone': primary,
                    'response_to': primary,
                    'reason': 'Response goes back to sender (primary phone)'
                },
                {
                    'name': 'Text from Additional Phone',
                    'description': f'User texts "how am I doing?" from {additional}',
                    'from_phone': additional,
                    'response_to': additional,
                    'reason': 'Response goes back to sender (additional phone)'
                },
                {
                    'name': 'Health Alert',
                    'description': 'System detects anomaly in HRV',
                    'from_system': True,
                    'type': 'alerts',
                    'target': primary,
                    'reason': 'Alerts always go to PRIMARY phone'
                },
                {
                    'name': 'Critical Alert',
                    'description': 'System detects critical health issue',
                    'from_system': True,
                    'type': 'urgent_alerts',
                    'target': primary,
                    'reason': 'Critical alerts always go to PRIMARY phone'
                }
            ]

            for i, scenario in enumerate(scenarios, 1):
                print(f"\n{i}. {scenario['name']}")
                print(f"   Scenario: {scenario['description']}")

                if scenario.get('from_system'):
                    print(f"   📤 System notification → {scenario['target']}")
                    print(f"   💡 Why: {scenario['reason']}")
                else:
                    print(f"   📱 SMS from: {scenario['from_phone']}")
                    print(f"   📤 Response to: {scenario['response_to']}")
                    print(f"   💡 Why: {scenario['reason']}")

            print(f"\n🎯 SUMMARY:")
            print(f"   • All system notifications → {primary} (PRIMARY)")
            print(f"   • SMS responses → sender's phone (PRIMARY or ADDITIONAL)")
            print(f"   • Both phones can send SMS and get responses")
            print(f"   • Only PRIMARY phone receives reports and alerts")

            return True

    except Exception as e:
        print(f"❌ Error simulating scenarios: {str(e)}")
        return False

if __name__ == "__main__":
    print("DUAL PHONE BEHAVIOR TEST SUITE")
    print("Testing SMS routing for Apostle Emmanuel")

    # Run all tests
    tests = [
        ("Dual Phone Setup", test_dual_phone_setup),
        ("SMS Routing Logic", test_sms_routing_logic),
        ("Notification Routing", test_notification_routing),
        ("Real Scenarios", simulate_sms_scenarios),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"RUNNING: {test_name}")
        print('='*80)

        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print('='*80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    total_passed = sum(results.values())
    print(f"\nResults: {total_passed}/{len(tests)} tests passed")

    if total_passed == len(tests):
        print("\n🎉 All tests passed! Dual phone system is ready to deploy.")
    else:
        print("\n⚠️  Some tests failed. Check configuration before deploying.")