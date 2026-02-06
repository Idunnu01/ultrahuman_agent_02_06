#!/usr/bin/env python3
"""
Verify which version of code is running on PythonAnywhere
Run this on PythonAnywhere to check if the updates were deployed
"""

def check_regex_patterns():
    """Check if the new regex patterns are in place"""
    try:
        from services.metrics_service import MetricsService
        import re

        print("🔍 CHECKING REGEX PATTERNS")
        print("=" * 40)

        service = MetricsService()
        test_message = "average heart rate last 7 days"

        # Test the method
        is_structured = service._is_structured_health_query(test_message.lower())

        print(f"Test query: '{test_message}'")
        print(f"_is_structured_health_query result: {'✅ TRUE' if is_structured else '❌ FALSE'}")

        if is_structured:
            print("✅ NEW REGEX PATTERNS ARE DEPLOYED")
            return True
        else:
            print("❌ OLD REGEX PATTERNS - NEED TO DEPLOY UPDATED metrics_service.py")
            return False

    except Exception as e:
        print(f"❌ Error checking patterns: {e}")
        return False

def check_rate_limits():
    """Check if rate limits are removed"""
    try:
        import inspect
        from services.sms_service import SMSService

        print("\n🔍 CHECKING RATE LIMITS")
        print("=" * 40)

        # Check the source code of the send_sms method
        sms_service = SMSService()
        send_sms_source = inspect.getsource(sms_service.send_sms)

        if "Rate limits removed" in send_sms_source:
            print("✅ RATE LIMITS REMOVED - NEW CODE DEPLOYED")
            return True
        elif "_check_rate_limit" in send_sms_source and "Rate limits removed" not in send_sms_source:
            print("❌ RATE LIMITS STILL ACTIVE - NEED TO DEPLOY UPDATED sms_service.py")
            return False
        else:
            print("⚠️  UNCLEAR - CHECK sms_service.py manually")
            return False

    except Exception as e:
        print(f"❌ Error checking rate limits: {e}")
        return False

def check_webhook_error_handling():
    """Check if proper SMS error handling is in webhook"""
    try:
        from app import create_app
        import inspect

        print("\n🔍 CHECKING WEBHOOK ERROR HANDLING")
        print("=" * 40)

        app = create_app()

        # Get the webhook function
        with app.app_context():
            # Check if we can find the sms_webhook function
            webhook_rules = [rule for rule in app.url_map.iter_rules() if '/webhook/sms' in rule.rule]

            if webhook_rules:
                print("✅ SMS webhook route found")

                # Try to get the view function
                endpoint = webhook_rules[0].endpoint
                view_func = app.view_functions.get(endpoint)

                if view_func:
                    source = inspect.getsource(view_func)
                    if "ACTUALLY CHECK SMS SERVICE RESPONSE" in source or "sms_result.get('success')" in source:
                        print("✅ NEW WEBHOOK ERROR HANDLING DEPLOYED")
                        return True
                    else:
                        print("❌ OLD WEBHOOK CODE - NEED TO DEPLOY UPDATED app/__init__.py")
                        return False
                else:
                    print("⚠️  Could not inspect webhook function")
                    return False
            else:
                print("❌ SMS webhook route not found!")
                return False

    except Exception as e:
        print(f"❌ Error checking webhook: {e}")
        return False

def test_full_flow():
    """Test the complete SMS processing flow"""
    try:
        from services.metrics_service import MetricsService

        print("\n🧪 TESTING FULL SMS PROCESSING FLOW")
        print("=" * 40)

        service = MetricsService()
        result = service.process_sms_input("sample_user", "average heart rate last 7 days")

        success = result.get('success', False)
        insights = result.get('immediate_insights', {}).get('insights', [])

        print(f"Success: {success}")
        print(f"Insights count: {len(insights)}")

        if insights:
            first_insight = insights[0]
            insight_type = first_insight.get('type', 'unknown')
            message = first_insight.get('message', '')[:100]

            print(f"Response type: {insight_type}")
            print(f"Message preview: {message}...")

            if insight_type == 'structured_query':
                print("✅ STRUCTURED QUERY PROCESSING WORKING")
                return True
            elif insight_type in ['lifestyle', 'general']:
                print("❌ FALLING BACK TO GENERIC PROCESSING")
                return False
            else:
                print(f"⚠️  UNEXPECTED RESPONSE TYPE: {insight_type}")
                return False
        else:
            print("❌ NO INSIGHTS RETURNED")
            return False

    except Exception as e:
        print(f"❌ Error testing flow: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 DEPLOYMENT VERIFICATION SCRIPT")
    print("=" * 50)
    print("Run this on PythonAnywhere to check deployment status")
    print()

    checks = [
        ("Regex Patterns", check_regex_patterns),
        ("Rate Limits", check_rate_limits),
        ("Webhook Error Handling", check_webhook_error_handling),
        ("Full Flow Test", test_full_flow)
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            results.append((check_name, False))

    print("\n📋 DEPLOYMENT STATUS SUMMARY")
    print("=" * 50)

    all_passed = True
    for check_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 ALL CHECKS PASSED - DEPLOYMENT SUCCESSFUL!")
        print("Your SMS should now provide detailed statistical analysis.")
    else:
        print("\n⚠️  SOME CHECKS FAILED - DEPLOYMENT INCOMPLETE")
        print("Please upload the missing updated files to PythonAnywhere.")
        print("\nFiles to update:")
        for check_name, passed in results:
            if not passed:
                if "Regex" in check_name:
                    print("  - services/metrics_service.py")
                elif "Rate" in check_name:
                    print("  - services/sms_service.py")
                elif "Webhook" in check_name:
                    print("  - app/__init__.py")