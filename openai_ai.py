#!/usr/bin/env python3
"""
Diagnose and fix OpenAI installation issues
"""
import sys
import subprocess
import pkg_resources
import importlib

def check_openai_installation():
    """Check OpenAI installation details"""
    print("🔍 Diagnosing OpenAI installation...")

    try:
        import openai
        print(f"✅ OpenAI imported successfully")
        print(f"📍 Location: {openai.__file__}")
        print(f"📦 Version: {openai.__version__}")

        # Check what's available in the openai module
        print("\n📋 Available OpenAI classes:")
        openai_attrs = [attr for attr in dir(openai) if not attr.startswith('_')]
        for attr in sorted(openai_attrs):
            obj = getattr(openai, attr)
            if isinstance(obj, type):
                print(f"   - {attr} (class)")

        # Try to create a client
        print("\n🧪 Testing OpenAI client creation...")
        try:
            client = openai.OpenAI(api_key="test-key")
            print("✅ OpenAI client created successfully")
            return True
        except Exception as e:
            print(f"❌ Client creation failed: {str(e)}")
            return False

    except ImportError as e:
        print(f"❌ OpenAI import failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def check_conflicting_packages():
    """Check for conflicting packages"""
    print("\n🔍 Checking for conflicting packages...")

    conflicting_packages = [
        'openai-python',
        'openai-api',
        'openai-client'
    ]

    installed_packages = [pkg.project_name.lower() for pkg in pkg_resources.working_set]

    conflicts = [pkg for pkg in conflicting_packages if pkg in installed_packages]

    if conflicts:
        print(f"⚠️  Found conflicting packages: {conflicts}")
        print("💡 Consider uninstalling these packages")
        return True
    else:
        print("✅ No conflicting packages found")
        return False

def fix_openai_installation():
    """Attempt to fix OpenAI installation"""
    print("\n🔧 Attempting to fix OpenAI installation...")

    try:
        # First, try to uninstall any conflicting packages
        conflicting_packages = ['openai-python', 'openai-api', 'openai-client']
        for package in conflicting_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', package, '-y'],
                                    capture_output=True)
                print(f"   🗑️  Removed {package}")
            except subprocess.CalledProcessError:
                pass  # Package wasn't installed

        # Uninstall current OpenAI
        print("   🗑️  Uninstalling current OpenAI...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'uninstall', 'openai', '-y'],
                            capture_output=True)

        # Clear any cached imports
        if 'openai' in sys.modules:
            del sys.modules['openai']

        # Reinstall OpenAI
        print("   📦 Installing OpenAI 1.3.5...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'openai==1.3.5'],
                            capture_output=True)

        # Test the installation
        print("   🧪 Testing new installation...")
        importlib.invalidate_caches()
        import openai

        client = openai.OpenAI(api_key="test-key")
        print("✅ OpenAI installation fixed successfully!")
        return True

    except Exception as e:
        print(f"❌ Fix attempt failed: {str(e)}")
        return False

def manual_fix_suggestions():
    """Provide manual fix suggestions"""
    print("\n💡 Manual fix suggestions:")
    print("1. Complete reinstall:")
    print("   pip uninstall openai openai-python openai-api openai-client -y")
    print("   pip install openai==1.3.5")
    print()
    print("2. If still having issues, try:")
    print("   pip cache purge")
    print("   pip install --no-cache-dir openai==1.3.5")
    print()
    print("3. Alternative: Use a different provider:")
    print("   pip install anthropic  # Claude (excellent for analysis)")
    print("   pip install together   # Cost-effective option")

def test_alternative_providers():
    """Test alternative LLM providers"""
    print("\n🧪 Testing alternative providers...")

    # Test Anthropic
    try:
        import anthropic
        client = anthropic.Anthropic(api_key="test-key")
        print("✅ Anthropic available and working")
    except ImportError:
        print("📦 Anthropic not installed (pip install anthropic)")
    except Exception as e:
        print(f"⚠️  Anthropic import issue: {str(e)}")

    # Test Together
    try:
        import together
        print("✅ Together.ai available")
    except ImportError:
        print("📦 Together.ai not installed (pip install together)")
    except Exception as e:
        print(f"⚠️  Together.ai import issue: {str(e)}")

def main():
    print("=" * 70)
    print("OPENAI INSTALLATION DIAGNOSTICS & FIX")
    print("=" * 70)

    # Step 1: Check current installation
    openai_working = check_openai_installation()

    # Step 2: Check for conflicts
    has_conflicts = check_conflicting_packages()

    if not openai_working:
        # Step 3: Attempt automatic fix
        print("\n" + "=" * 50)
        print("ATTEMPTING AUTOMATIC FIX")
        print("=" * 50)

        fix_success = fix_openai_installation()

        if not fix_success:
            manual_fix_suggestions()

    # Step 4: Test alternatives
    test_alternative_providers()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if openai_working:
        print("✅ OpenAI is working correctly")
    else:
        print("❌ OpenAI needs to be fixed")
        print("💡 Your health insight system will still work with fallback insights")
        print("💡 Consider installing Anthropic for better LLM capabilities")

if __name__ == "__main__":
    main()