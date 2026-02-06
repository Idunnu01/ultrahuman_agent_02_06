#!/usr/bin/env python3
"""
Test to diagnose and fix the LLM provider issue.
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(project_dir, '.env'))

def test_llm_fix():
    """Test and fix LLM provider initialization"""

    print("=" * 60)
    print("LLM PROVIDER DIAGNOSIS AND FIX")
    print("=" * 60)

    try:
        # Check environment variables
        print("🔍 Checking environment variables...")
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        together_key = os.getenv('TOGETHER_API_KEY')

        print(f"   OpenAI API Key: {'✅ Set' if openai_key else '❌ Not set'}")
        print(f"   Anthropic API Key: {'✅ Set' if anthropic_key else '❌ Not set'}")
        print(f"   Together API Key: {'✅ Set' if together_key else '❌ Not set'}")
        print()

        # Test direct OpenAI initialization
        print("🧪 Testing direct OpenAI initialization...")
        try:
            import openai
            print(f"   OpenAI version: {openai.__version__}")

            if openai_key:
                # Try different initialization methods
                print("   Testing OpenAI client creation...")

                # Method 1: Direct initialization
                try:
                    client1 = openai.OpenAI(api_key=openai_key)
                    print("   ✅ Method 1 (direct) - Success")
                except Exception as e:
                    print(f"   ❌ Method 1 failed: {str(e)}")

                # Method 2: With explicit parameters
                try:
                    client2 = openai.OpenAI(
                        api_key=openai_key,
                        base_url="https://api.openai.com/v1"
                    )
                    print("   ✅ Method 2 (with base_url) - Success")
                except Exception as e:
                    print(f"   ❌ Method 2 failed: {str(e)}")

                # Method 3: Legacy method
                try:
                    openai.api_key = openai_key
                    print("   ✅ Method 3 (legacy) - Success")
                except Exception as e:
                    print(f"   ❌ Method 3 failed: {str(e)}")

        except ImportError as e:
            print(f"   ❌ OpenAI not installed: {str(e)}")
        except Exception as e:
            print(f"   ❌ OpenAI test failed: {str(e)}")

        print()

        # Test LLM service initialization
        print("🧪 Testing LLM service initialization...")
        try:
            from services.llm_service import LLMService, LLMProvider

            llm_service = LLMService()
            print(f"   Available providers: {list(llm_service.providers.keys())}")

            if LLMProvider.OPENAI in llm_service.providers:
                print("   ✅ OpenAI provider available")

                # Test a simple prompt
                print("   Testing simple prompt...")
                try:
                    response = llm_service.generate_response(
                        prompt="Hello, this is a test message.",
                        task_type="general",
                        provider=LLMProvider.OPENAI,
                        temperature=0.1
                    )
                    print(f"   ✅ LLM response successful: {response.content[:100]}...")
                except Exception as e:
                    print(f"   ❌ LLM response failed: {str(e)}")
            else:
                print("   ❌ OpenAI provider not available")

        except Exception as e:
            print(f"   ❌ LLM service test failed: {str(e)}")

        print()

        # Test correlation insight generation
        print("🧪 Testing correlation insight generation...")
        try:
            from services.metrics_service import MetricsService

            metrics_service = MetricsService()

            # Test correlation processing
            test_result = metrics_service.process_sms_input(
                "sample_user",
                "Is there a correlation between my heart rate and recovery?"
            )

            if test_result.get('success'):
                insights = test_result.get('immediate_insights', {}).get('insights', [])
                if insights:
                    print("   ✅ Correlation insight generated:")
                    print(f"   Message: {insights[0].get('message', 'No message')}")
                else:
                    print("   ❌ No insights generated")
            else:
                print(f"   ❌ Correlation processing failed: {test_result.get('error')}")

        except Exception as e:
            print(f"   ❌ Correlation test failed: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ Error in LLM fix test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("LLM Fix Test")
    print("=" * 60)

    success = test_llm_fix()

    if success:
        print("\n" + "=" * 60)
        print("SUMMARY:")
        print("=" * 60)
        print("✅ LLM provider diagnosis complete")
        print("🔍 Check the output above for issues")
        print("🔧 Ready to implement fixes")
    else:
        print("\n❌ LLM fix test failed. Check the errors above.")

if __name__ == "__main__":
    main()
