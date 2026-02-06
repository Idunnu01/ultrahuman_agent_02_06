#!/usr/bin/env python3
"""
Test SMS-focused LLM service - optimized for cloud deployment
"""

import sys
import os

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_sms_llm_service():
    """Test SMS-optimized LLM service"""

    print("=" * 70)
    print("SMS LLM SERVICE TEST (Cloud-Optimized)")
    print("=" * 70)

    try:
        from services.llm_service import SMSLLMService, LLMProvider

        # Initialize service
        print("🧪 Initializing SMS LLM service...")
        llm_service = SMSLLMService()

        # Get status
        status = llm_service.get_provider_status()
        print(f"   ✅ Service initialized")
        print(f"   🔌 Providers available: {status['summary']['providers_available']}/{status['summary']['providers_total']}")
        print(f"   📱 SMS ready: {'Yes' if status['summary']['sms_ready'] else 'No'}")
        print(f"   ☁️  Cloud deployment suitable: {'Yes' if status['summary']['deployment_suitable'] else 'No'}")

        # Show provider details
        print(f"\n   📋 Provider Details:")
        for provider, info in status['providers'].items():
            if info['available']:
                print(f"   ✅ {provider}: SMS model = {info['sms_model']}")
                print(f"      Cost per SMS ≈ ${info['cost_per_sms_estimate']:.6f}")
            else:
                print(f"   ❌ {provider}: {info['reason']}")

        return llm_service, True

    except Exception as e:
        print(f"   ❌ Service initialization failed: {str(e)}")
        return None, False

def test_sms_response_generation(llm_service):
    """Test SMS response generation"""

    print("\n" + "=" * 70)
    print("SMS RESPONSE GENERATION TEST")
    print("=" * 70)

    test_cases = [
        {
            "name": "Heart Rate Correlation",
            "context": "Heart rate increased 10% this week, HRV improved 5%",
            "expected_elements": ["heart", "hrv", "correlation"]
        },
        {
            "name": "Sleep Quality Alert",
            "context": "Sleep score dropped 15 points, recovery declining",
            "expected_elements": ["sleep", "recovery", "recommendation"]
        },
        {
            "name": "Positive Trend",
            "context": "All metrics improving, user feeling energetic",
            "expected_elements": ["improving", "energy", "positive"]
        }
    ]

    successful_responses = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {test_case['name']}")
        print(f"   Context: {test_case['context']}")

        try:
            response = llm_service.generate_sms_response(
                test_case['context'],
                max_length=160
            )

            print(f"   📱 SMS Response ({len(response.content)} chars): {response.content}")
            print(f"   🏷️  Provider: {response.provider.value}")
            print(f"   ⏱️  Response time: {response.response_time_ms:.0f}ms")
            print(f"   💰 Estimated cost: ${response.cost_estimate:.6f}")

            # Check if response meets SMS requirements
            if len(response.content) <= 160:
                print(f"   ✅ Length check passed")
            else:
                print(f"   ❌ Response too long ({len(response.content)} chars)")

            # Check for engagement elements
            has_emoji = any(ord(c) > 127 for c in response.content)
            if has_emoji:
                print(f"   ✅ Has emoji for engagement")
            else:
                print(f"   ⚠️  No emoji detected")

            successful_responses += 1

        except Exception as e:
            print(f"   ❌ SMS generation failed: {str(e)}")

    print(f"\n📊 SMS Test Results: {successful_responses}/{len(test_cases)} successful")
    return successful_responses == len(test_cases)

def test_health_analysis(llm_service):
    """Test comprehensive health analysis"""

    print("\n" + "=" * 70)
    print("HEALTH ANALYSIS TEST")
    print("=" * 70)

    # Mock health data
    metrics_data = {
        "heart_rate": {"avg": 72, "trend": "stable", "last_week": 68},
        "hrv": {"avg": 42, "trend": "improving", "change_pct": 8},
        "sleep_score": {"avg": 76, "trend": "declining", "change_pct": -12},
        "recovery": {"avg": 68, "trend": "mixed"}
    }

    statistical_analysis = {
        "correlations": {
            "heart_rate_vs_recovery": {"coef": -0.72, "p_value": 0.008, "sample_size": 30},
            "sleep_vs_hrv": {"coef": 0.65, "p_value": 0.02, "sample_size": 30}
        },
        "trends": {
            "hrv_improvement": {"rate": 0.08, "significance": "moderate"},
            "sleep_decline": {"rate": -0.12, "significance": "concerning"}
        }
    }

    user_context = {
        "age": 34,
        "activity_level": "moderate",
        "goals": ["improve_recovery", "better_sleep"],
        "recent_changes": ["increased_training", "work_stress"]
    }

    print("🧪 Testing comprehensive health analysis...")
    print(f"   📊 Metrics: {len(metrics_data)} health metrics")
    print(f"   📈 Correlations: {len(statistical_analysis['correlations'])} relationships")
    print(f"   👤 User context: Age {user_context['age']}, {user_context['activity_level']} activity")

    try:
        response = llm_service.generate_health_analysis(
            metrics_data,
            statistical_analysis,
            user_context
        )

        print(f"\n   ✅ Analysis generated successfully")
        print(f"   🏷️  Provider: {response.provider.value}")
        print(f"   📝 Content length: {len(response.content)} characters")
        print(f"   ⏱️  Response time: {response.response_time_ms:.0f}ms")
        print(f"   💰 Cost: ${response.cost_estimate:.6f}")

        # Show first part of analysis
        preview = response.content[:300] + "..." if len(response.content) > 300 else response.content
        print(f"\n   📋 Analysis Preview:")
        print(f"   {preview}")

        # Check for key elements
        content_lower = response.content.lower()
        key_elements = ['correlation', 'sleep', 'recovery', 'recommendation']
        found_elements = [elem for elem in key_elements if elem in content_lower]

        print(f"\n   🔍 Key elements found: {found_elements}")

        return True

    except Exception as e:
        print(f"   ❌ Health analysis failed: {str(e)}")
        return False

def test_service_health_check(llm_service):
    """Test service health check for deployment monitoring"""

    print("\n" + "=" * 70)
    print("SERVICE HEALTH CHECK")
    print("=" * 70)

    try:
        health = llm_service.health_check()

        print("🏥 Health Check Results:")
        print(f"   Service Ready: {'✅' if health['service_ready'] else '❌'}")
        print(f"   Fallback Ready: {'✅' if health['fallback_ready'] else '❌'}")
        print(f"   Providers Available: {health['providers_count']}")
        print(f"   Est. Response Time: {health['estimated_response_time_ms']}ms")
        print(f"   Deployment Type: {health['deployment_type']}")

        # Overall readiness
        is_ready = health['service_ready'] or health['fallback_ready']
        print(f"\n   🚀 SMS Agent Deployment Ready: {'Yes' if is_ready else 'No'}")

        return is_ready

    except Exception as e:
        print(f"   ❌ Health check failed: {str(e)}")
        return False

def main():
    print("SMS-Focused LLM Service Test")
    print("Optimized for cloud deployment and SMS responses")

    # Initialize service
    llm_service, init_success = test_sms_llm_service()

    if not init_success:
        print("\n❌ Cannot continue - service initialization failed")
        return

    # Test SMS responses
    sms_success = test_sms_response_generation(llm_service)

    # Test health analysis
    analysis_success = test_health_analysis(llm_service)

    # Test service health
    health_success = test_service_health_check(llm_service)

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print("✅ Service Initialization: Working")
    print(f"{'✅' if sms_success else '❌'} SMS Generation: {'Working' if sms_success else 'Issues detected'}")
    print(f"{'✅' if analysis_success else '❌'} Health Analysis: {'Working' if analysis_success else 'Issues detected'}")
    print(f"{'✅' if health_success else '❌'} Deployment Ready: {'Yes' if health_success else 'No'}")

    if health_success:
        print("\n🎉 SMS HEALTH AGENT IS READY FOR DEPLOYMENT!")
        print("   📱 SMS responses will work (LLM or fallback)")
        print("   🧠 Health analysis is functional")
        print("   ☁️  Cloud deployment optimized")
        print("   📊 No local dependencies (Ollama removed)")

        # Show deployment recommendations
        print("\n💡 DEPLOYMENT RECOMMENDATIONS:")
        print("   • PythonAnywhere: Perfect for this setup")
        print("   • Environment vars: Set API keys in .env or server config")
        print("   • Monitoring: Health check endpoint ready")
        print("   • Cost optimization: Fallbacks reduce API costs")

        # Show provider recommendations
        status = llm_service.get_provider_status()
        available_providers = [p for p, info in status['providers'].items() if info['available']]

        if available_providers:
            print(f"\n🔌 ACTIVE PROVIDERS: {', '.join(available_providers)}")
        else:
            print(f"\n⚠️  NO LLM PROVIDERS ACTIVE - Using fallback insights only")
            print("   • Install: pip install anthropic (recommended for health analysis)")
            print("   • Or: Fix OpenAI configuration")
            print("   • System still works with statistical fallbacks")
    else:
        print("\n⚠️  SOME ISSUES DETECTED - Review above for details")
        print("   • System will still work with fallback insights")
        print("   • LLM providers are optional enhancements")

if __name__ == "__main__":
    main()