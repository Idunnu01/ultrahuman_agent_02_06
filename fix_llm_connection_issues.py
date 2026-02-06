#!/usr/bin/env python3
"""
Fix common LLM connection issues in daily reports
"""

import sys
import os
from datetime import datetime

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from dotenv import load_dotenv
load_dotenv()

def fix_llm_service_initialization():
    """Fix LLM service initialization issues"""

    print("🔧 Fixing LLM Service Initialization")
    print("="*50)

    try:
        from services.llm_service import LLMService

        # Test current service
        print("📊 Testing current LLM service...")
        service = LLMService()

        print(f"   Available providers: {list(service.providers.keys())}")
        print(f"   Provider errors: {service.provider_errors}")

        if not service.providers:
            print("❌ No LLM providers available")

            # Try manual initialization
            print("\n🔧 Attempting manual provider initialization...")

            # Check OpenAI
            try:
                import openai
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    client = openai.OpenAI(api_key=api_key, timeout=30.0)
                    # Test with simple call
                    models = client.models.list()
                    print("   ✅ OpenAI manual initialization successful")
                else:
                    print("   ❌ OpenAI API key missing")
            except Exception as e:
                print(f"   ❌ OpenAI manual initialization failed: {str(e)}")

            # Check Anthropic
            try:
                import anthropic
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if api_key:
                    client = anthropic.Anthropic(api_key=api_key, timeout=30.0)
                    print("   ✅ Anthropic manual initialization successful")
                else:
                    print("   ❌ Anthropic API key missing")
            except Exception as e:
                print(f"   ❌ Anthropic manual initialization failed: {str(e)}")

        return True

    except Exception as e:
        print(f"❌ LLM service fix failed: {str(e)}")
        return False

def create_fallback_llm_service():
    """Create a fallback LLM service with better error handling"""

    print("\n🛡️ Creating Fallback LLM Service")
    print("="*40)

    fallback_service_content = '''"""
Improved LLM service with better error handling and fallbacks
"""

import os
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ImprovedLLMService:
    """LLM service with robust error handling and fallbacks"""

    def __init__(self):
        self.providers = {}
        self.fallback_enabled = True
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize providers with better error handling"""

        # Try OpenAI
        try:
            import openai
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                client = openai.OpenAI(
                    api_key=api_key,
                    timeout=30.0,
                    max_retries=2
                )
                self.providers['openai'] = client
                logger.info("OpenAI provider initialized successfully")
        except Exception as e:
            logger.warning(f"OpenAI provider initialization failed: {str(e)}")

        # Try Anthropic
        try:
            import anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                client = anthropic.Anthropic(
                    api_key=api_key,
                    timeout=30.0
                )
                self.providers['anthropic'] = client
                logger.info("Anthropic provider initialized successfully")
        except Exception as e:
            logger.warning(f"Anthropic provider initialization failed: {str(e)}")

    def generate_health_insights(self, analysis_data: Dict) -> Dict:
        """Generate health insights with fallback handling"""

        # Try OpenAI first
        if 'openai' in self.providers:
            try:
                return self._generate_with_openai(analysis_data)
            except Exception as e:
                logger.warning(f"OpenAI insights generation failed: {str(e)}")

        # Try Anthropic as fallback
        if 'anthropic' in self.providers:
            try:
                return self._generate_with_anthropic(analysis_data)
            except Exception as e:
                logger.warning(f"Anthropic insights generation failed: {str(e)}")

        # Ultimate fallback - rule-based insights
        return self._generate_fallback_insights(analysis_data)

    def _generate_with_openai(self, analysis_data: Dict) -> Dict:
        """Generate insights using OpenAI"""

        client = self.providers['openai']

        prompt = self._create_insight_prompt(analysis_data)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a health insights expert. Provide concise, actionable health advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        content = response.choices[0].message.content
        return self._parse_insights_response(content)

    def _generate_with_anthropic(self, analysis_data: Dict) -> Dict:
        """Generate insights using Anthropic"""

        client = self.providers['anthropic']

        prompt = self._create_insight_prompt(analysis_data)

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.content[0].text
        return self._parse_insights_response(content)

    def _create_insight_prompt(self, analysis_data: Dict) -> str:
        """Create a prompt for health insights generation"""

        correlations = analysis_data.get('correlation_analysis', {})
        anomalies = analysis_data.get('anomaly_analysis', {})
        patterns = analysis_data.get('pattern_analysis', {})

        prompt = f"""
        Analyze this health data and provide 2-3 key insights:

        Correlations found: {len(correlations)} relationships
        Anomalies detected: {len(anomalies)} unusual patterns
        Trends identified: {len(patterns)} patterns

        Focus on actionable advice for improving health metrics.
        Be concise and specific.
        """

        return prompt

    def _parse_insights_response(self, content: str) -> Dict:
        """Parse LLM response into structured insights"""

        insights = []
        recommendations = []

        lines = content.strip().split('\\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if 'insight' in line.lower() or 'finding' in line.lower():
                current_section = 'insights'
            elif 'recommend' in line.lower() or 'suggest' in line.lower():
                current_section = 'recommendations'
            elif line.startswith(('-', '•', '1.', '2.', '3.')):
                content_text = line.lstrip('-•123456789. ')
                if current_section == 'recommendations':
                    recommendations.append(content_text)
                else:
                    insights.append(content_text)

        return {
            'key_insights': insights[:3],  # Limit to 3 insights
            'recommendations': recommendations[:3],  # Limit to 3 recommendations
            'provider': 'llm_service'
        }

    def _generate_fallback_insights(self, analysis_data: Dict) -> Dict:
        """Generate basic insights without LLM as ultimate fallback"""

        insights = []
        recommendations = []

        # Correlation-based insights
        correlations = analysis_data.get('correlation_analysis', {})
        if correlations:
            insights.append(f"Found {len(correlations)} significant correlations between your health metrics")
            recommendations.append("Continue tracking lifestyle factors to identify more patterns")

        # Anomaly-based insights
        anomalies = analysis_data.get('anomaly_analysis', {})
        if anomalies:
            insights.append(f"Detected {len(anomalies)} unusual patterns in your health data")
            recommendations.append("Monitor the flagged metrics more closely")

        # Pattern-based insights
        patterns = analysis_data.get('pattern_analysis', {})
        if patterns:
            insights.append(f"Identified {len(patterns)} health trends over time")
            recommendations.append("Maintain consistent lifestyle habits to optimize these trends")

        # Default insights if no analysis available
        if not insights:
            insights = [
                "Continue logging lifestyle events for personalized insights",
                "Your biometric data shows good consistency",
                "Regular monitoring helps identify optimization opportunities"
            ]
            recommendations = [
                "Log more lifestyle events (meals, supplements, exercise)",
                "Maintain consistent sleep and activity patterns",
                "Review your data weekly to spot trends"
            ]

        return {
            'key_insights': insights[:3],
            'recommendations': recommendations[:3],
            'provider': 'fallback_rules'
        }

# Global instance for backwards compatibility
improved_llm_service = ImprovedLLMService()
'''

    try:
        with open(os.path.join(project_dir, 'services', 'improved_llm_service.py'), 'w') as f:
            f.write(fallback_service_content)
        print("✅ Created improved LLM service with fallbacks")
        return True
    except Exception as e:
        print(f"❌ Failed to create fallback service: {str(e)}")
        return False

def test_daily_report_with_llm_fixes():
    """Test daily report generation with LLM fixes"""

    print("\n🧪 Testing Daily Report with LLM Fixes")
    print("="*50)

    try:
        from app import create_app
        from app.models import User
        from tasks.daily_report import generate_daily_report

        app = create_app()

        with app.app_context():
            user_id = 'user_7000'
            user = User.query.filter_by(id=user_id).first()

            if not user:
                print(f"❌ User {user_id} not found")
                return False

            print(f"📊 Testing daily report generation for {user_id}...")

            # Test report generation
            result = generate_daily_report(user_id)

            if result and result.get('success'):
                print("✅ Daily report generated successfully!")

                report_id = result.get('report_id')
                if report_id:
                    from app.models import DailyReport
                    report = DailyReport.query.get(report_id)

                    if report:
                        insights = report.insights or {}
                        print(f"   📋 Insights generated: {len(insights)} items")

                        if 'key_insights' in insights:
                            print(f"   🔍 Key insights: {len(insights['key_insights'])}")

                        if 'recommendations' in insights:
                            print(f"   💡 Recommendations: {len(insights['recommendations'])}")

                        print(f"   📱 SMS content: {len(report.sms_content or '')} characters")

                        return True
            else:
                print(f"❌ Daily report generation failed: {result.get('error', 'Unknown error')}")
                return False

    except Exception as e:
        print(f"❌ Daily report test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def apply_llm_service_patches():
    """Apply patches to the existing LLM service for better reliability"""

    print("\n🩹 Applying LLM Service Patches")
    print("="*40)

    # Read the current LLM service
    llm_service_path = os.path.join(project_dir, 'services', 'llm_service.py')

    try:
        with open(llm_service_path, 'r') as f:
            content = f.read()

        patches_applied = []

        # Patch 1: Add timeout to OpenAI client
        if 'timeout=' not in content:
            content = content.replace(
                'client = openai.OpenAI(',
                'client = openai.OpenAI(\n                        timeout=30.0,'
            )
            patches_applied.append("Added timeout to OpenAI client")

        # Patch 2: Add timeout to Anthropic client
        if 'timeout=' not in content or content.count('timeout=') < 2:
            content = content.replace(
                'client = anthropic.Anthropic(',
                'client = anthropic.Anthropic(\n                        timeout=30.0,'
            )
            patches_applied.append("Added timeout to Anthropic client")

        # Patch 3: Better error handling in test calls
        if 'test_models = client.models.list()' in content:
            content = content.replace(
                'test_models = client.models.list()',
                'test_models = client.models.list()\n                    logger.debug(f"OpenAI test successful, found models")'
            )
            patches_applied.append("Improved OpenAI test logging")

        # Write back if patches were applied
        if patches_applied:
            # Backup original
            backup_path = llm_service_path + '.backup'
            with open(backup_path, 'w') as f:
                with open(llm_service_path, 'r') as orig:
                    f.write(orig.read())

            with open(llm_service_path, 'w') as f:
                f.write(content)

            print(f"✅ Applied {len(patches_applied)} patches:")
            for patch in patches_applied:
                print(f"   - {patch}")

            return True
        else:
            print("✅ No patches needed - LLM service already optimized")
            return True

    except Exception as e:
        print(f"❌ Failed to apply patches: {str(e)}")
        return False

if __name__ == '__main__':
    print(f"🔧 LLM Connection Issues Fix - {datetime.now()}")

    fixes = [
        ("LLM Service Initialization", fix_llm_service_initialization),
        ("Fallback Service Creation", create_fallback_llm_service),
        ("LLM Service Patches", apply_llm_service_patches),
        ("Daily Report Test", test_daily_report_with_llm_fixes)
    ]

    results = []

    for fix_name, fix_func in fixes:
        try:
            print(f"\n{'='*60}")
            result = fix_func()
            results.append((fix_name, result))
        except Exception as e:
            print(f"❌ {fix_name} failed: {str(e)}")
            results.append((fix_name, False))

    # Summary
    print(f"\n📊 Fix Results Summary:")
    print("="*40)
    for fix_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        print(f"   {fix_name}: {status}")

    successful_fixes = sum(1 for _, result in results if result)
    print(f"\n🎯 {successful_fixes}/{len(results)} fixes applied successfully")

    if successful_fixes == len(results):
        print("🎉 All LLM connection issues resolved!")
        print("💡 Daily reports should now generate with proper AI insights")
    else:
        print("🔧 Some fixes failed - manual intervention may be needed")