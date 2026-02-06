#!/usr/bin/env python3
"""
Add temporary endpoint to test LLM service directly
Add this to your Flask routes for testing
"""

def create_llm_test_endpoint():
    """
    Add this route to your app/routes.py to test LLM service:
    """

    route_code = '''
@main_bp.route('/test/llm', methods=['GET'])
def test_llm_service():
    """Test LLM service configuration"""
    try:
        from services.minimal_llm_service import MinimalLLMService

        llm = MinimalLLMService()

        # Test with sample correlation data
        insight = llm.generate_health_insight(
            correlation_coef=-0.023,
            p_value=0.000,
            sample_size=174914,
            metric1="heart_rate",
            metric2="temperature"
        )

        return {
            "llm_working": True,
            "working_providers": llm.working_providers,
            "insight": insight,
            "environment_vars": {
                "openai_key_present": bool(os.getenv('OPENAI_API_KEY')),
                "anthropic_key_present": bool(os.getenv('ANTHROPIC_API_KEY')),
                "together_key_present": bool(os.getenv('TOGETHER_API_KEY'))
            }
        }

    except Exception as e:
        return {
            "llm_working": False,
            "error": str(e),
            "environment_vars": {
                "openai_key_present": bool(os.getenv('OPENAI_API_KEY')),
                "anthropic_key_present": bool(os.getenv('ANTHROPIC_API_KEY')),
                "together_key_present": bool(os.getenv('TOGETHER_API_KEY'))
            }
        }, 500
'''

    print("🔧 ADD THIS ROUTE TO YOUR app/routes.py:")
    print("=" * 50)
    print(route_code)
    print("=" * 50)
    print("\n📡 Then test at: https://health-bphlite.pythonanywhere.com/test/llm")
    print("\n🎯 This will show:")
    print("  • Which API keys are available")
    print("  • Which LLM providers are working")
    print("  • Sample LLM-generated insight")

def create_quick_fix():
    """Create a quick fix for the LLM fallback"""

    improved_fallback = '''
def _generate_manual_insight(self, correlation_coef: float, p_value: float,
                           sample_size: int, metric1: str, metric2: str) -> str:
    """Enhanced fallback when LLM providers fail"""

    r = correlation_coef
    abs_r = abs(r)

    # Strength interpretation
    if abs_r > 0.7:
        strength = "strong"
    elif abs_r > 0.4:
        strength = "moderate"
    elif abs_r > 0.1:
        strength = "weak"
    else:
        strength = "very weak"

    direction = "positive" if r > 0 else "negative"
    significance = "significant" if p_value < 0.05 else "not significant"

    # Create meaningful insight
    metric1_clean = metric1.replace('_', ' ')
    metric2_clean = metric2.replace('_', ' ')

    insight = f"📊 Your {metric1_clean} and {metric2_clean} show a {strength} {direction} correlation (r={r:.3f})."

    if abs_r < 0.1:
        insight += f" This suggests these metrics operate largely independently in your data."
    elif abs_r < 0.3:
        insight += f" This indicates a {strength} relationship that may have some practical relevance."
    else:
        insight += f" This indicates a meaningful relationship worth monitoring."

    insight += f" Based on {sample_size:,} data points over your tracking period, this pattern is {significance}."

    if metric1 == "heart_rate" and metric2 == "temperature":
        insight += " This reflects normal thermoregulatory responses in your cardiovascular system."
    elif "sleep" in [metric1, metric2]:
        insight += " Sleep relationships often reveal important recovery patterns."
    elif "glucose" in [metric1, metric2]:
        insight += " Glucose correlations can indicate metabolic response patterns."

    return insight
'''

    print("\n🔧 IMPROVED FALLBACK CODE:")
    print("=" * 50)
    print("Replace the _generate_manual_insight method in MinimalLLMService with:")
    print(improved_fallback)

if __name__ == "__main__":
    print("🚀 LLM SERVICE QUICK FIXES")
    print("=" * 60)

    create_llm_test_endpoint()
    create_quick_fix()

    print("\n🎯 IMMEDIATE ACTIONS:")
    print("1. Add test endpoint to check API key availability")
    print("2. Set environment variables on PythonAnywhere")
    print("3. Test with: https://health-bphlite.pythonanywhere.com/test/llm")
    print("4. Send correlation SMS to verify improvement")

    print(f"\n📱 EXPECTED RESULT:")
    print("Instead of: 'r=-0.023, p=0.000, 174914 data points'")
    print("You'll get: 'Your heart rate and temperature show a very weak negative correlation...'")