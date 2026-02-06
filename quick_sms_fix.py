#!/usr/bin/env python3
"""
Quick SMS Fix - Force local processing when OpenAI connection fails
This ensures you get actual health data instead of generic responses
"""

def patch_metrics_service():
    """Patch the metrics service to prioritize local processing"""

    print("🔧 PATCHING METRICS SERVICE FOR RELIABLE SMS RESPONSES")
    print("=" * 60)

    # Read the current metrics service
    with open('/home/bphlite/ultrahuman_agent/services/metrics_service.py', 'r') as f:
        content = f.read()

    # Check if already patched
    if "# QUICK_SMS_FIX_APPLIED" in content:
        print("✅ Metrics service already patched")
        return

    # Find the _handle_metric_query_nlp method
    target = """        try:
            from services.llm_service import SMSLLMService

            # Create a structured query string for the LLM service
            structured_query = f"{parsed_query.aggregation} {parsed_query.metric_type.replace('_', ' ')} last {parsed_query.time_period_days} days"

            llm_service = SMSLLMService()
            response = llm_service.handle_structured_health_query(structured_query, user_id)"""

    replacement = """        try:
            # QUICK_SMS_FIX_APPLIED - Always try local processing first for reliable responses
            logger.info(f"🎯 Attempting local processing first for: {parsed_query.metric_type} {parsed_query.aggregation}")

            # Try local processing first (more reliable than OpenAI on PythonAnywhere)
            local_result = self._handle_metric_query_local_nlp(user_id, parsed_query)

            if local_result and local_result.get('success'):
                insights = local_result.get('immediate_insights', {}).get('insights', [])
                if insights and 'no data' not in insights[0].get('message', '').lower():
                    logger.info(f"✅ Local processing succeeded for {parsed_query.metric_type}")
                    return local_result

            # Only try LLM if local processing failed
            from services.llm_service import SMSLLMService

            # Create a structured query string for the LLM service
            structured_query = f"{parsed_query.aggregation} {parsed_query.metric_type.replace('_', ' ')} last {parsed_query.time_period_days} days"

            llm_service = SMSLLMService()
            response = llm_service.handle_structured_health_query(structured_query, user_id)"""

    if target in content:
        # Apply the patch
        patched_content = content.replace(target, replacement)

        # Write back to file
        with open('/home/bphlite/ultrahuman_agent/services/metrics_service.py', 'w') as f:
            f.write(patched_content)

        print("✅ Metrics service patched successfully!")
        print("📊 Local processing will now be prioritized for reliable data responses")
        print("🔄 This ensures actual health data instead of generic fallbacks")

        return True
    else:
        print("❌ Could not find target code to patch")
        return False

def test_patched_system():
    """Test the patched system"""

    print("\n🧪 TESTING PATCHED SYSTEM")
    print("=" * 40)

    try:
        from app import create_app
        from services.metrics_service import MetricsService
        from app.models import User

        app = create_app()

        with app.app_context():
            metrics_service = MetricsService()
            user = User.query.filter_by(id='sample_user').first()

            if not user:
                print("❌ No user found")
                return

            # Test the failing query
            test_query = "what's my avg HR over past week"
            print(f"🧪 Testing: '{test_query}'")

            result = metrics_service.process_sms_input(user.id, test_query)

            if result.get('success'):
                insights = result.get('immediate_insights', {}).get('insights', [])
                if insights:
                    message = insights[0].get('message', '')
                    print(f"📩 Response: {message}")

                    if 'bpm' in message or '87.85' in message:
                        print("🎉 SUCCESS! Now returning actual heart rate data!")
                        return True
                    else:
                        print("⚠️ Still getting generic response")
                        return False

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 QUICK SMS FIX - FORCE LOCAL PROCESSING")
    print("=" * 70)
    print("This patch ensures reliable SMS responses with actual health data")
    print("=" * 70)

    # Apply the patch
    success = patch_metrics_service()

    if success:
        # Test the patched system
        test_success = test_patched_system()

        if test_success:
            print("\n🎉 PATCH SUCCESSFUL!")
            print("📱 Your SMS queries should now return actual health data!")
            print("🔄 Try SMS again: 'what's my avg HR over past week'")
        else:
            print("\n⚠️ Patch applied but may need manual verification")
    else:
        print("\n❌ Patch failed - may need manual adjustment")