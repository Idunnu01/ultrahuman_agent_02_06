#!/usr/bin/env python3
"""
Debug SMS webhook processing vs direct processing
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from services.metrics_service import MetricsService
    from app.models import SystemLog
    from utils.database import db
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def check_recent_logs():
    """Check recent system logs for errors"""

    app = create_app()

    with app.app_context():
        print("📋 CHECKING RECENT SYSTEM LOGS:")
        print("=" * 35)
        print()

        # Get recent error logs
        recent_logs = SystemLog.query.filter(
            SystemLog.level.in_(['ERROR', 'WARNING']),
            SystemLog.created_at >= datetime.utcnow().replace(hour=21, minute=0)  # Since 9 PM today
        ).order_by(SystemLog.created_at.desc()).limit(10).all()

        if recent_logs:
            for log in recent_logs:
                timestamp = log.created_at.strftime("%H:%M:%S")
                print(f"🔍 [{timestamp}] {log.level}: {log.source}")
                print(f"   Message: {log.message}")
                if log.context:
                    print(f"   Context: {log.context}")
                print()
        else:
            print("✅ No recent error logs found")
            print()

def test_sms_vs_direct():
    """Compare SMS webhook vs direct processing"""

    app = create_app()

    with app.app_context():
        print("🔄 SMS WEBHOOK vs DIRECT PROCESSING COMPARISON:")
        print("=" * 55)
        print()

        service = MetricsService()
        test_message = "supplement magnesium 400mg 10pm"
        user_id = "user_7000"

        print("🧪 DIRECT PROCESSING TEST:")
        print("-" * 25)

        try:
            result_direct = service.process_sms_input(user_id, test_message)
            print(f"✅ Direct result: {result_direct}")

            if result_direct.get('success'):
                insights = result_direct.get('immediate_insights', {}).get('insights', [])
                if insights:
                    print(f"💬 Direct message: {insights[0].get('message')}")
            else:
                print(f"❌ Direct error: {result_direct.get('error')}")

        except Exception as e:
            print(f"❌ Direct exception: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("📱 SIMULATING SMS WEBHOOK:")
        print("-" * 25)

        # Simulate how the SMS webhook might process this
        try:
            # This is typically what happens in the webhook
            print("1. Webhook receives SMS")
            print("2. Creates MetricsService instance")
            print("3. Calls process_sms_input")

            # Test if there are any differences in how webhook calls this
            webhook_service = MetricsService()
            webhook_result = webhook_service.process_sms_input(user_id, test_message)

            print(f"✅ Webhook simulation result: {webhook_result}")

            if webhook_result.get('success'):
                insights = webhook_result.get('immediate_insights', {}).get('insights', [])
                if insights:
                    print(f"💬 Webhook message: {insights[0].get('message')}")
            else:
                print(f"❌ Webhook error: {webhook_result.get('error')}")

        except Exception as e:
            print(f"❌ Webhook simulation exception: {e}")
            import traceback
            traceback.print_exc()

def check_web_app_reload():
    """Check if web app needs to be reloaded"""

    print("🔄 WEB APP RELOAD CHECK:")
    print("=" * 25)
    print()

    print("🔍 POSSIBLE ISSUES:")
    print("1. **Web app cache**: Old code still loaded in memory")
    print("2. **Import cache**: Python import cache needs clearing")
    print("3. **File upload**: Wrong file uploaded or upload failed")
    print("4. **Webhook delay**: SMS webhook using cached version")
    print()

    print("🔧 SOLUTIONS TO TRY:")
    print("1. **Force restart web app** on PythonAnywhere:")
    print("   • Go to Web tab → Click 'Reload' button")
    print("   • Wait for full restart (may take 30+ seconds)")
    print()
    print("2. **Clear Python cache** (if needed):")
    print("   • In console: rm -rf __pycache__ services/__pycache__")
    print("   • Then restart web app again")
    print()
    print("3. **Verify file upload**:")
    print("   • Check services/metrics_service.py shows recent timestamp")
    print("   • Search for '_extract_numeric_dosage' in the file")
    print()
    print("4. **Test immediately after restart**:")
    print("   • Wait 1-2 minutes after web app reload")
    print("   • Then test SMS again")
    print()

def show_working_vs_failing():
    """Show the difference between working vs failing"""

    print("📊 WORKING vs FAILING COMPARISON:")
    print("=" * 35)
    print()

    print("✅ CONSOLE TEST (WORKING):")
    print("   Input: 'supplement magnesium 400mg 10pm'")
    print("   Result: ✅ Supplement logged successfully! Supplement: magnesium (400mg) at 10:00 PM")
    print("   Metrics: 2 created (generic + specific)")
    print()

    print("❌ SMS WEBHOOK (FAILING):")
    print("   Input: 'supplement magnesium 400mg 10pm'")
    print("   Result: ❌ Couldn't process. Try: 'meal [food] [time]' or 'supplement [name] [dose] [time]'")
    print("   Metrics: 0 created")
    print()

    print("🤔 THIS SUGGESTS:")
    print("   • Code works correctly when called directly")
    print("   • SMS webhook is using an older version of the code")
    print("   • Web app restart may not have taken effect")
    print("   • There's a caching issue preventing new code from loading")
    print()

if __name__ == "__main__":
    try:
        check_recent_logs()
        test_sms_vs_direct()
        print()
        check_web_app_reload()
        print()
        show_working_vs_failing()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()