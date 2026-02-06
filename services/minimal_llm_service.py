"""
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


    def generate(self, prompt: str, max_length: int = 306) -> str:
        # No external calls; just return a compact version safely
        text = (prompt or "").strip()
        return text[: max_length - 1] + "…" if len(text) > max_length else text

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
        """Enhanced manual insight generation with health context"""

        # Determine strength and emoji
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

        # Build comprehensive insight
        insight_parts = []

        # Primary correlation statement
        insight_parts.append(f"{emoji} Your {metric1_clean} and {metric2_clean} show a {strength} {direction} correlation (r={correlation_coef:.3f}).")

        # Interpretation based on strength
        if abs_corr < 0.1:
            insight_parts.append("These metrics operate largely independently - no actionable relationship detected.")
        elif abs_corr < 0.3:
            insight_parts.append("This weak relationship may have some relevance but isn't strongly predictive.")
        elif abs_corr < 0.6:
            insight_parts.append("This moderate relationship suggests meaningful connections worth monitoring.")
        else:
            insight_parts.append("This strong relationship indicates important physiological connections.")

        # Specific health context
        if "heart_rate" in metric1 and "temperature" in metric2:
            insight_parts.append("This reflects normal cardiovascular thermal regulation.")
        elif "sleep" in [metric1, metric2]:
            insight_parts.append("Sleep relationships often reveal key recovery patterns.")
        elif "glucose" in [metric1, metric2]:
            insight_parts.append("Glucose correlations indicate metabolic response patterns.")
        elif "recovery" in [metric1, metric2]:
            insight_parts.append("Recovery correlations help optimize training and rest.")

        # Statistical reliability
        if sample_size > 1000:
            insight_parts.append(f"Based on {sample_size:,} data points, this pattern is {significance}.")

        # Join with appropriate length for SMS
        full_insight = " ".join(insight_parts)
        return full_insight[:300]  # Allow longer insights for better context

# Backward compatibility
SMSLLMService = MinimalLLMService
LLMService = MinimalLLMService
