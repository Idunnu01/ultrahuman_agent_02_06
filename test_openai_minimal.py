#!/usr/bin/env python3
"""
Minimal OpenAI API test to isolate the 'proxies' error
Run this on PythonAnywhere to diagnose the issue
"""

import os
import sys

def test_openai_imports():
    """Test OpenAI package imports"""
    print("🔍 TESTING OPENAI IMPORTS")
    print("=" * 40)

    try:
        import openai
        print(f"✅ OpenAI imported successfully")
        print(f"📦 OpenAI version: {openai.__version__ if hasattr(openai, '__version__') else 'unknown'}")

        # Check what's available
        print(f"🔧 OpenAI attributes: {[attr for attr in dir(openai) if not attr.startswith('_')]}")

        return openai
    except Exception as e:
        print(f"❌ OpenAI import failed: {e}")
        return None

def test_openai_client_creation():
    """Test OpenAI client creation with different approaches"""
    print("\n🔍 TESTING OPENAI CLIENT CREATION")
    print("=" * 40)

    openai = test_openai_imports()
    if not openai:
        return None

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return None

    print(f"🔑 API Key found: {api_key[:20]}...")

    # Method 1: Basic initialization
    try:
        print("\n🧪 Method 1: Basic OpenAI() initialization")
        client = openai.OpenAI(api_key=api_key)
        print("✅ Basic initialization successful")
        return client
    except Exception as e:
        print(f"❌ Basic initialization failed: {e}")

    # Method 2: With explicit parameters
    try:
        print("\n🧪 Method 2: Explicit parameters")
        client = openai.OpenAI(
            api_key=api_key,
            timeout=30.0
        )
        print("✅ Explicit parameters successful")
        return client
    except Exception as e:
        print(f"❌ Explicit parameters failed: {e}")

    # Method 3: Using environment variable
    try:
        print("\n🧪 Method 3: Environment variable")
        os.environ['OPENAI_API_KEY'] = api_key
        client = openai.OpenAI()
        print("✅ Environment variable successful")
        return client
    except Exception as e:
        print(f"❌ Environment variable failed: {e}")

    return None

def test_openai_api_call(client):
    """Test a simple API call"""
    print("\n🔍 TESTING OPENAI API CALL")
    print("=" * 40)

    if not client:
        print("❌ No client available for testing")
        return False

    try:
        # Try a simple model list call first
        print("🧪 Testing models.list()...")
        models = client.models.list()
        print(f"✅ Models list successful: {len(models.data)} models found")

        # Try a simple chat completion
        print("🧪 Testing simple chat completion...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print(f"✅ Chat completion successful: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

def diagnose_environment():
    """Diagnose the Python environment"""
    print("\n🔍 ENVIRONMENT DIAGNOSIS")
    print("=" * 40)

    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Python path: {sys.path[0]}")

    # Check for HTTP proxy settings
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    for var in proxy_vars:
        value = os.getenv(var)
        if value:
            print(f"🌐 {var}: {value}")

    # Check installed packages related to HTTP
    try:
        import requests
        print(f"📦 Requests version: {requests.__version__}")
    except:
        print("❌ Requests not available")

    try:
        import httpx
        print(f"📦 HTTPX version: {httpx.__version__}")
    except:
        print("❌ HTTPX not available")

def main():
    print("🚨 OPENAI API DIAGNOSTICS")
    print("=" * 50)
    print("Run this on PythonAnywhere to diagnose the 'proxies' error")
    print()

    # Diagnose environment first
    diagnose_environment()

    # Test OpenAI client creation
    client = test_openai_client_creation()

    # Test API call if client works
    if client:
        success = test_openai_api_call(client)

        if success:
            print("\n🎉 DIAGNOSIS: OpenAI API working correctly!")
            print("The issue might be in how your LLM service initializes the client.")
        else:
            print("\n⚠️  DIAGNOSIS: Client creates but API calls fail")
            print("Check API key permissions and network connectivity.")
    else:
        print("\n❌ DIAGNOSIS: OpenAI client creation failing")
        print("This is likely the source of your 'proxies' error.")

    print("\n📋 RECOMMENDATIONS:")
    if not client:
        print("1. Check OpenAI package version: pip show openai")
        print("2. Try upgrading: pip install --upgrade openai")
        print("3. Check for conflicting HTTP libraries")
        print("4. Clear any proxy settings in environment")
    else:
        print("1. OpenAI client works - issue is in LLM service code")
        print("2. Check how SMSLLMService initializes the client")
        print("3. Add more specific error handling in your service")

if __name__ == "__main__":
    main()