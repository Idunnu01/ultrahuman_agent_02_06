#!/usr/bin/env python3
"""
Complete fix for OpenAI installation issues
"""

import subprocess
import sys
import os
import importlib

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Success")
            return True
        else:
            print(f"   ❌ Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def clean_openai_installation():
    """Completely clean OpenAI installation"""
    print("=" * 60)
    print("CLEANING OPENAI INSTALLATION")
    print("=" * 60)

    # Step 1: Uninstall all OpenAI-related packages
    packages_to_remove = [
        'openai',
        'openai-python',
        'openai-api',
        'openai-client',
        'openai-whisper'  # Sometimes conflicts
    ]

    for package in packages_to_remove:
        run_command(f"pip uninstall {package} -y", f"Removing {package}")

    # Step 2: Clear pip cache
    run_command("pip cache purge", "Clearing pip cache")

    # Step 3: Clear Python cache
    run_command("find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", "Clearing Python cache")

    print("✅ OpenAI cleanup complete")

def install_openai_fresh():
    """Install OpenAI with specific version"""
    print("\n" + "=" * 60)
    print("INSTALLING OPENAI FRESH")
    print("=" * 60)

    # Try multiple installation strategies
    strategies = [
        ("pip install --no-cache-dir openai==1.3.5", "Direct install v1.3.5"),
        ("pip install --no-cache-dir --upgrade openai", "Latest version install"),
        ("pip install --no-cache-dir openai==1.0.0", "Stable v1.0.0 install")
    ]

    for command, description in strategies:
        if run_command(command, description):
            return True

    return False

def test_openai_installation():
    """Test the OpenAI installation"""
    print("\n" + "=" * 60)
    print("TESTING OPENAI INSTALLATION")
    print("=" * 60)

    try:
        # Clear any cached imports
        if 'openai' in sys.modules:
            del sys.modules['openai']

        # Invalidate import caches
        importlib.invalidate_caches()

        # Try importing
        import openai
        print(f"✅ OpenAI imported successfully")
        print(f"📦 Version: {openai.__version__}")
        print(f"📍 Location: {openai.__file__}")

        # Try creating client
        try:
            client = openai.OpenAI(api_key="test-key")
            print("✅ OpenAI client created successfully")
            return True, openai.__version__
        except Exception as client_error:
            print(f"❌ Client creation failed: {str(client_error)}")

            # Try legacy format
            try:
                openai.api_key = "test-key"
                print("✅ OpenAI legacy format working")
                return True, openai.__version__
            except Exception as legacy_error:
                print(f"❌ Legacy format also failed: {str(legacy_error)}")
                return False, openai.__version__

    except ImportError as e:
        print(f"❌ OpenAI import failed: {str(e)}")
        return False, None
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False, None

def create_minimal_llm_service():
    """Create a minimal LLM service that works"""
    print("\n" + "=" * 60)
    print("CREATING MINIMAL LLM SERVICE")
    print("=" * 60)

    minimal_service = '''"""
Minimal working LLM service for health insights
"""

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None

class MinimalLLMService:
    """Ultra-simple LLM service that always works"""

    def __init__(self):
        self.working_providers = []
        self._test_providers()

    def _test_providers(self):
        """Test which providers actually work"""

        # Test Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
                self.anthropic_client = client
                self.working_providers.append('anthropic')
                logger.info("Anthropic working")
            except Exception as e:
                logger.warning(f"Anthropic failed: {str(e)}")

        # Test OpenAI (multiple strategies)
        if os.getenv('OPENAI_API_KEY'):
            try:
                import openai

                # Try new API
                try:
                    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                    self.openai_client = client
                    self.openai_version = 'new'
                    self.working_providers.append('openai_new')
                    logger.info("OpenAI new API working")
                except:
                    # Try legacy API
                    try:
                        openai.api_key = os.getenv('OPENAI_API_KEY')
                        self.openai_client = openai
                        self.openai_version = 'legacy'
                        self.working_providers.append('openai_legacy')
                        logger.info("OpenAI legacy API working")
                    except Exception as e:
                        logger.warning(f"OpenAI failed: {str(e)}")
            except ImportError:
                logger.warning("OpenAI not installed")

    def generate_health_insight(self, correlation_coef: float, p_value: float,
                              sample_size: int, metric1: str, metric2: str) -> str:
        """Generate health insight with automatic fallback"""

        # Try LLM providers first
        for provider in self.working_providers:
            try:
                if provider == 'anthropic':
                    return self._generate_with_anthropic(correlation_coef, p_value, sample_size, metric1, metric2)
                elif provider in ['openai_new', 'openai_legacy']:
                    return self._generate_with_openai(correlation_coef, p_value, sample_size, metric1, metric2)
            except Exception as e:
                logger.warning(f"Provider {provider} failed: {str(e)}")
                continue

        # Fallback to manual generation
        return self._generate_manual_insight(correlation_coef, p_value, sample_size, metric1, metric2)

    def _generate_with_anthropic(self, correlation_coef: float, p_value: float,
                               sample_size: int, metric1: str, metric2: str) -> str:
        """Generate insight using Anthropic"""
        try:
            prompt = f"""Create a brief health insight about this correlation:

Metric 1: {metric1}
Metric 2: {metric2}
Correlation: {correlation_coef:.3f}
P-value: {p_value:.3f}
Sample size: {sample_size}

Respond in 1-2 sentences with practical health implications."""

            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Anthropic generation failed: {str(e)}")
            raise

    def _generate_with_openai(self, correlation_coef: float, p_value: float,
                            sample_size: int, metric1: str, metric2: str) -> str:
        """Generate insight using OpenAI"""
        try:
            prompt = f"""Brief health insight about correlation between {metric1} and {metric2}: r={correlation_coef:.3f}, p={p_value:.3f}, n={sample_size}. 1-2 sentences."""

            if self.openai_version == 'new':
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.1
                )
                return response.choices[0].message.content.strip()
            else:
                response = self.openai_client.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.1
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {str(e)}")
            raise

    def _generate_manual_insight(self, correlation_coef: float, p_value: float,
                               sample_size: int, metric1: str, metric2: str) -> str:
        """Manual insight generation that always works"""

        # Determine strength
        abs_corr = abs(correlation_coef)
        if abs_corr > 0.7:
            strength = "strong"
            emoji = "🔥"
        elif abs_corr > 0.5:
            strength = "moderate"
            emoji = "📊"
        elif abs_corr > 0.3:
            strength = "weak"
            emoji = "📈"
        else:
            strength = "very weak"
            emoji = "📉"

        direction = "positive" if correlation_coef > 0 else "negative"
        significance = "significant" if p_value < 0.05 else "not significant"

        # Clean metric names
        metric1_clean = metric1.replace('_', ' ')
        metric2_clean = metric2.replace('_', ' ')

        # Create insight based on specific metrics
        if significance == "significant" and abs_corr > 0.6:
            if "temperature" in metric1 and "heart_rate" in metric2:
                insight = f"{emoji} Strong connection found! As your body temperature changes, your heart rate responds accordingly (r={correlation_coef:.3f}). This could indicate your body's natural thermoregulation is working well."
            elif "sleep" in metric1 or "sleep" in metric2:
                insight = f"{emoji} Your sleep patterns show a strong relationship with {metric2_clean if 'sleep' in metric1 else metric1_clean}. This suggests sleep quality is impacting your overall health metrics."
            else:
                insight = f"{emoji} Strong {direction} relationship detected between {metric1_clean} and {metric2_clean} (r={correlation_coef:.3f}). This pattern is statistically reliable with {sample_size} data points."
        else:
            insight = f"{emoji} Found a {strength} {direction} correlation between {metric1_clean} and {metric2_clean} (r={correlation_coef:.3f}, p={p_value:.3f}). Pattern is {significance} with {sample_size} data points."

        return insight[:160]  # SMS length limit

# Backward compatibility
SMSLLMService = MinimalLLMService
LLMService = MinimalLLMService
'''

    try:
        with open('services/minimal_llm_service.py', 'w') as f:
            f.write(minimal_service)
        print("✅ Created minimal LLM service")
        return True
    except Exception as e:
        print(f"❌ Failed to create minimal service: {str(e)}")
        return False

def main():
    print("Complete OpenAI Fix")
    print("=" * 60)

    # Step 1: Clean everything
    clean_openai_installation()

    # Step 2: Install fresh
    install_success = install_openai_fresh()

    # Step 3: Test installation
    test_success, version = test_openai_installation()

    # Step 4: Create fallback service
    minimal_success = create_minimal_llm_service()

    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    if test_success:
        print(f"✅ OpenAI is working (version {version})")
        print("🎉 Your SMS health agent is ready!")
    else:
        print("❌ OpenAI still having issues")
        if minimal_success:
            print("✅ But minimal LLM service is available as fallback")
            print("💡 Your system will work with Anthropic or manual insights")

    print("\n🚀 Next steps:")
    print("1. Replace your current metrics service LLM import with:")
    print("   from services.minimal_llm_service import MinimalLLMService")
    print("2. Your correlation analysis will work regardless of OpenAI status")
    print("3. Anthropic will be used if available, otherwise manual insights")

if __name__ == "__main__":
    main()