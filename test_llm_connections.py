#!/usr/bin/env python3
"""
Test LLM service connections and diagnose issues
"""

import sys
import os
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def test_direct_api_connections():
    """Test direct API connections without the service wrapper"""

    print("🔍 Testing Direct LLM API Connections")
    print("="*60)

    # Test OpenAI
    print("\n🤖 Testing OpenAI API:")
    try:
        import openai
        print("   ✅ openai package imported successfully")

        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"   ✅ API key found: {api_key[:10]}...{api_key[-4:]}")

            try:
                client = openai.OpenAI(api_key=api_key)
                print("   ✅ OpenAI client created")

                # Test with a simple model list call
                models = client.models.list()
                model_count = len(list(models))
                print(f"   ✅ Models retrieved: {model_count} models available")

                # Test with a simple completion
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Test connection. Reply with: OK"}],
                    max_tokens=5,
                    temperature=0
                )

                if response.choices[0].message.content:
                    print(f"   ✅ API test successful: {response.choices[0].message.content.strip()}")
                    return True

            except Exception as e:
                print(f"   ❌ OpenAI API test failed: {str(e)}")
                return False

        else:
            print("   ❌ No OPENAI_API_KEY found in environment")
            return False

    except ImportError as e:
        print(f"   ❌ openai package not available: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ OpenAI connection test failed: {str(e)}")
        return False

def test_anthropic_connection():
    """Test Anthropic API connection"""

    print("\n🧠 Testing Anthropic API:")
    try:
        import anthropic
        print("   ✅ anthropic package imported successfully")

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            print(f"   ✅ API key found: {api_key[:15]}...{api_key[-4:]}")

            try:
                client = anthropic.Anthropic(api_key=api_key)
                print("   ✅ Anthropic client created")

                # Test with a simple message
                response = client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Test connection. Reply with: OK"}]
                )

                if response.content[0].text:
                    print(f"   ✅ API test successful: {response.content[0].text.strip()}")
                    return True

            except Exception as e:
                print(f"   ❌ Anthropic API test failed: {str(e)}")
                return False

        else:
            print("   ❌ No ANTHROPIC_API_KEY found in environment")
            return False

    except ImportError as e:
        print(f"   ❌ anthropic package not available: {str(e)}")
        return False
    except Exception as e:
        print(f"   ❌ Anthropic connection test failed: {str(e)}")
        return False

def test_llm_service_wrapper():
    """Test the LLM service wrapper"""

    print("\n🔧 Testing LLM Service Wrapper:")
    try:
        from services.llm_service import LLMService

        service = LLMService()
        print(f"   ✅ LLMService instantiated")
        print(f"   Available providers: {list(service.providers.keys())}")
        print(f"   Provider errors: {service.provider_errors}")

        # Test health insights generation
        test_data = {
            'correlations': {'heart_rate_vs_steps': {'correlation': 0.5, 'p_value': 0.01}},
            'anomalies': {'heart_rate': {'detected': True, 'severity': 'moderate'}},
            'patterns': {'sleep_score': {'trend': 'improving'}}
        }

        print("\n   🔍 Testing health insights generation...")
        insights = service.generate_health_insights(test_data)

        if insights and 'error' not in insights:
            print(f"   ✅ Health insights generated successfully")
            print(f"   Key insights: {len(insights.get('key_insights', []))}")
            print(f"   Recommendations: {len(insights.get('recommendations', []))}")
            return True
        else:
            print(f"   ❌ Health insights failed: {insights.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"   ❌ LLM Service test failed: {str(e)}")
        return False

def test_network_connectivity():
    """Test basic network connectivity to API endpoints"""

    print("\n🌐 Testing Network Connectivity:")

    endpoints = [
        ("OpenAI", "https://api.openai.com/v1/models"),
        ("Anthropic", "https://api.anthropic.com/v1/messages")
    ]

    import requests

    for name, endpoint in endpoints:
        try:
            # Simple HEAD request to test connectivity
            response = requests.head(endpoint, timeout=10)
            if response.status_code in [200, 401, 405]:  # 401 is expected without auth
                print(f"   ✅ {name} API endpoint reachable (status: {response.status_code})")
            else:
                print(f"   ⚠️ {name} API endpoint responded with status: {response.status_code}")
        except requests.exceptions.ConnectTimeout:
            print(f"   ❌ {name} API endpoint: Connection timeout")
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ {name} API endpoint: Connection error - {str(e)}")
        except Exception as e:
            print(f"   ❌ {name} API endpoint test failed: {str(e)}")

def diagnose_common_issues():
    """Diagnose common LLM connection issues"""

    print("\n🔍 Diagnosing Common Issues:")

    # Check Python environment
    print(f"   Python version: {sys.version}")

    # Check package versions
    packages_to_check = ['openai', 'anthropic', 'requests']
    for package_name in packages_to_check:
        try:
            package = __import__(package_name)
            version = getattr(package, '__version__', 'Unknown')
            print(f"   ✅ {package_name}: {version}")
        except ImportError:
            print(f"   ❌ {package_name}: Not installed")

    # Check environment variables
    env_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: Set ({len(value)} chars)")
        else:
            print(f"   ❌ {var}: Not set")

    # Check for proxy or network restrictions
    print(f"   HTTP_PROXY: {os.getenv('HTTP_PROXY', 'Not set')}")
    print(f"   HTTPS_PROXY: {os.getenv('HTTPS_PROXY', 'Not set')}")

if __name__ == '__main__':
    print(f"🚀 LLM Connection Diagnostics - {datetime.now()}")

    # Run all tests
    tests = [
        ("Network Connectivity", test_network_connectivity),
        ("OpenAI Direct API", test_direct_api_connections),
        ("Anthropic Direct API", test_anthropic_connection),
        ("LLM Service Wrapper", test_llm_service_wrapper),
        ("System Diagnostics", diagnose_common_issues)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results.append((test_name, False))

    # Summary
    print(f"\n📊 Test Results Summary:")
    print("="*40)
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")

    successful_tests = sum(1 for _, result in results if result)
    print(f"\n🎯 {successful_tests}/{len(results)} tests passed")

    if successful_tests == len(results):
        print("🎉 All LLM connections working properly!")
    else:
        print("🔧 Some LLM connections need fixing")