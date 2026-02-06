#!/usr/bin/env python3
"""
Run all diagnostics and fixes for LLM and SMS issues
"""

import sys
import os
import subprocess
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def run_script(script_name, description):
    """Run a Python script and capture results"""

    print(f"\n🚀 {description}")
    print("="*60)

    try:
        result = subprocess.run(
            [sys.executable, script_name],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ Script completed successfully")
            return True
        else:
            print(f"❌ Script failed with exit code: {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Script timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Failed to run script: {str(e)}")
        return False

def main():
    print(f"🔧 Ultrahuman Agent Diagnostics & Fixes")
    print(f"Started: {datetime.now()}")
    print("="*60)

    scripts_to_run = [
        ("test_llm_connections.py", "Testing LLM API Connections"),
        ("fix_llm_connection_issues.py", "Fixing LLM Connection Issues"),
        ("check_user_phone_numbers.py", "Checking User Phone Numbers"),
        ("test_daily_report.py", "Testing Daily Report Generation"),
        ("test_correlation_improvements.py", "Verifying Correlation Analysis Fixes")
    ]

    results = []

    for script, description in scripts_to_run:
        script_path = os.path.join(project_dir, script)

        if os.path.exists(script_path):
            success = run_script(script, description)
            results.append((description, success))
        else:
            print(f"⚠️ Script not found: {script}")
            results.append((description, False))

    # Final Summary
    print(f"\n{'='*60}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for _, result in results if result)
    total = len(results)

    print(f"✅ Successful operations: {successful}/{total}")
    print(f"❌ Failed operations: {total - successful}/{total}")

    for description, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {description}")

    if successful == total:
        print(f"\n🎉 ALL SYSTEMS WORKING!")
        print(f"✅ LLM connections verified")
        print(f"✅ Correlation analysis optimized")
        print(f"✅ Phone numbers validated")
        print(f"✅ Daily reports functional")
        print(f"\n🚀 Your Ultrahuman Agent is fully operational!")
    else:
        print(f"\n⚠️ Some issues remain - check individual script outputs above")
        print(f"🔧 Manual intervention may be needed for failed operations")

    print(f"\nCompleted: {datetime.now()}")

if __name__ == '__main__':
    main()