"""
Multi-provider LLM service for intelligent health insights generation
"""

import openai
import anthropic
import together
import requests
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from utils.cache import cache_result
import os

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"
    OLLAMA = "ollama"

@dataclass
class LLMResponse:
    content: str
    provider: LLMProvider
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    confidence_score: Optional[float] = None

class LLMService:
    """Multi-provider LLM service with intelligent routing and fallbacks"""

    def __init__(self):
        self.providers = {}
        self._initialize_providers()

        # Model configurations
        self.model_configs = {
            LLMProvider.OPENAI: {
                'primary': 'gpt-4-turbo-preview',
                'fallback': 'gpt-3.5-turbo',
                'cost_per_1k_input': 0.01,
                'cost_per_1k_output': 0.03
            },
            LLMProvider.ANTHROPIC: {
                'primary': 'claude-3-opus-20240229',
                'fallback': 'claude-3-haiku-20240307',
                'cost_per_1k_input': 0.015,
                'cost_per_1k_output': 0.075
            },
            LLMProvider.TOGETHER: {
                'primary': 'meta-llama/Llama-2-70b-chat-hf',
                'fallback': 'meta-llama/Llama-2-13b-chat-hf',
                'cost_per_1k_input': 0.0008,
                'cost_per_1k_output': 0.0008
            },
            LLMProvider.OLLAMA: {
                'primary': 'llama2:70b',
                'fallback': 'llama2:13b',
                'cost_per_1k_input': 0.0,  # Self-hosted
                'cost_per_1k_output': 0.0
            }
        }

    def _initialize_providers(self):
        """Initialize available LLM providers"""
        try:
            # OpenAI
            if os.getenv('OPENAI_API_KEY'):
                self.providers[LLMProvider.OPENAI] = openai.OpenAI(
                    api_key=os.getenv('OPENAI_API_KEY')
                )
                logger.info("OpenAI provider initialized")

            # Anthropic
            if os.getenv('ANTHROPIC_API_KEY'):
                self.providers[LLMProvider.ANTHROPIC] = anthropic.Anthropic(
                    api_key=os.getenv('ANTHROPIC_API_KEY')
                )
                logger.info("Anthropic provider initialized")

            # Together.ai
            if os.getenv('TOGETHER_API_KEY'):
                together.api_key = os.getenv('TOGETHER_API_KEY')
                self.providers[LLMProvider.TOGETHER] = together
                logger.info("Together.ai provider initialized")

            # Ollama
            ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            try:
                # Test Ollama connectivity
                response = requests.get(f"{ollama_base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    self.providers[LLMProvider.OLLAMA] = {
                        'base_url': ollama_base_url
                    }
                    logger.info("Ollama provider initialized")
            except requests.RequestException:
                logger.warning("Ollama not available")

        except Exception as e:
            logger.error(f"Provider initialization failed: {str(e)}")

    def _select_provider(self, task_type: str = "general", prefer_local: bool = False) -> LLMProvider:
        """Intelligently select the best provider for the task"""
        available_providers = list(self.providers.keys())

        if not available_providers:
            raise RuntimeError("No LLM providers available")

        # Preference order based on task type
        if task_type == "analysis" and LLMProvider.ANTHROPIC in available_providers:
            return LLMProvider.ANTHROPIC  # Claude excels at analysis
        elif task_type == "creative" and LLMProvider.OPENAI in available_providers:
            return LLMProvider.OPENAI  # GPT-4 good for creative tasks
        elif prefer_local and LLMProvider.OLLAMA in available_providers:
            return LLMProvider.OLLAMA  # For privacy-sensitive tasks
        elif LLMProvider.TOGETHER in available_providers:
            return LLMProvider.TOGETHER  # Cost-effective option
        else:
            return available_providers[0]  # Fallback to first available

    def _call_openai(self, prompt: str, model: str, temperature: float = 0.1) -> LLMResponse:
        """Call OpenAI API"""
        try:
            client = self.providers[LLMProvider.OPENAI]

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=2000
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            # Estimate cost
            config = self.model_configs[LLMProvider.OPENAI]
            cost = (response.usage.prompt_tokens * config['cost_per_1k_input'] / 1000 +
                   response.usage.completion_tokens * config['cost_per_1k_output'] / 1000)

            return LLMResponse(
                content=content,
                provider=LLMProvider.OPENAI,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost
            )

        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise

    def _call_anthropic(self, prompt: str, model: str, temperature: float = 0.1) -> LLMResponse:
        """Call Anthropic API"""
        try:
            client = self.providers[LLMProvider.ANTHROPIC]

            response = client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Estimate cost
            config = self.model_configs[LLMProvider.ANTHROPIC]
            cost = (response.usage.input_tokens * config['cost_per_1k_input'] / 1000 +
                   response.usage.output_tokens * config['cost_per_1k_output'] / 1000)

            return LLMResponse(
                content=content,
                provider=LLMProvider.ANTHROPIC,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost
            )

        except Exception as e:
            logger.error(f"Anthropic API call failed: {str(e)}")
            raise

    def _call_together(self, prompt: str, model: str, temperature: float = 0.1) -> LLMResponse:
        """Call Together.ai API"""
        try:
            together_client = self.providers[LLMProvider.TOGETHER]

            response = together_client.Complete.create(
                prompt=prompt,
                model=model,
                max_tokens=2000,
                temperature=temperature
            )

            content = response['output']['choices'][0]['text']
            tokens_used = response['output']['usage']['total_tokens']

            # Estimate cost
            config = self.model_configs[LLMProvider.TOGETHER]
            cost = tokens_used * config['cost_per_1k_input'] / 1000

            return LLMResponse(
                content=content,
                provider=LLMProvider.TOGETHER,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost
            )

        except Exception as e:
            logger.error(f"Together.ai API call failed: {str(e)}")
            raise

    def _call_ollama(self, prompt: str, model: str, temperature: float = 0.1) -> LLMResponse:
        """Call local Ollama API"""
        try:
            ollama_config = self.providers[LLMProvider.OLLAMA]
            base_url = ollama_config['base_url']

            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False
                },
                timeout=60
            )

            response.raise_for_status()
            result = response.json()

            return LLMResponse(
                content=result['response'],
                provider=LLMProvider.OLLAMA,
                model=model,
                tokens_used=None,  # Ollama doesn't return token count
                cost_estimate=0.0
            )

        except Exception as e:
            logger.error(f"Ollama API call failed: {str(e)}")
            raise

    @cache_result(expire_seconds=3600, key_prefix="llm_")
    def generate_response(self, prompt: str, task_type: str = "general",
                         provider: Optional[LLMProvider] = None,
                         temperature: float = 0.1, use_fallback: bool = True) -> LLMResponse:
        """Generate response using the best available provider"""

        # Select provider if not specified
        if provider is None:
            provider = self._select_provider(task_type)

        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not available")

        # Get model configuration
        config = self.model_configs[provider]
        primary_model = config['primary']
        fallback_model = config['fallback']

        # Try primary model first
        try:
            if provider == LLMProvider.OPENAI:
                return self._call_openai(prompt, primary_model, temperature)
            elif provider == LLMProvider.ANTHROPIC:
                return self._call_anthropic(prompt, primary_model, temperature)
            elif provider == LLMProvider.TOGETHER:
                return self._call_together(prompt, primary_model, temperature)
            elif provider == LLMProvider.OLLAMA:
                return self._call_ollama(prompt, primary_model, temperature)

        except Exception as e:
            logger.warning(f"Primary model {primary_model} failed: {str(e)}")

            if use_fallback:
                try:
                    logger.info(f"Trying fallback model {fallback_model}")
                    if provider == LLMProvider.OPENAI:
                        return self._call_openai(prompt, fallback_model, temperature)
                    elif provider == LLMProvider.ANTHROPIC:
                        return self._call_anthropic(prompt, fallback_model, temperature)
                    elif provider == LLMProvider.TOGETHER:
                        return self._call_together(prompt, fallback_model, temperature)
                    elif provider == LLMProvider.OLLAMA:
                        return self._call_ollama(prompt, fallback_model, temperature)

                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {str(fallback_error)}")

                    # Try different provider as last resort
                    if len(self.providers) > 1:
                        other_providers = [p for p in self.providers.keys() if p != provider]
                        for other_provider in other_providers:
                            try:
                                logger.info(f"Trying alternative provider {other_provider}")
                                return self.generate_response(prompt, task_type, other_provider, temperature, False)
                            except Exception as alt_error:
                                logger.warning(f"Alternative provider {other_provider} failed: {str(alt_error)}")
                                continue

            # If all attempts failed
            raise Exception(f"All LLM providers failed for prompt: {prompt[:100]}...")

    def generate_health_insight(self, metrics_data: Dict, statistical_analysis: Dict,
                              user_context: Dict) -> LLMResponse:
        """Generate personalized health insights from data"""

        prompt = self._build_health_insight_prompt(metrics_data, statistical_analysis, user_context)

        return self.generate_response(
            prompt=prompt,
            task_type="analysis",
            temperature=0.1
        )

    def generate_daily_report(self, daily_summary: Dict, insights: List[Dict],
                            recommendations: List[str]) -> LLMResponse:
        """Generate daily SMS report"""

        prompt = self._build_daily_report_prompt(daily_summary, insights, recommendations)

        return self.generate_response(
            prompt=prompt,
            task_type="creative",
            temperature=0.2
        )

    def analyze_intervention_effectiveness(self, intervention_data: Dict,
                                         statistical_results: Dict) -> LLMResponse:
        """Analyze and explain intervention effectiveness"""

        prompt = self._build_intervention_analysis_prompt(intervention_data, statistical_results)

        return self.generate_response(
            prompt=prompt,
            task_type="analysis",
            temperature=0.1
        )

    def _build_health_insight_prompt(self, metrics_data: Dict, statistical_analysis: Dict,
                                   user_context: Dict) -> str:
        """Build prompt for health insight generation"""

        prompt = f"""
As an expert health data scientist, analyze the following health metrics and provide actionable insights:

METRICS DATA:
{json.dumps(metrics_data, indent=2)}

STATISTICAL ANALYSIS:
{json.dumps(statistical_analysis, indent=2)}

USER CONTEXT:
{json.dumps(user_context, indent=2)}

Provide insights in the following format:

STATISTICAL SUMMARY:
- Key findings with confidence scores
- Notable patterns or anomalies
- Correlation insights

HEALTH INTERPRETATION:
- What the data indicates about the user's health
- Potential causes or contributing factors
- Areas of concern or improvement

ACTIONABLE RECOMMENDATIONS:
- Specific, evidence-based suggestions
- Priority level for each recommendation
- Expected impact and timeline

CONFIDENCE ASSESSMENT:
- Overall confidence in the analysis (0-100%)
- Limitations of the current data
- Suggestions for better data collection

Keep the response scientific but accessible, focusing on actionable insights.
"""
        return prompt

    def _build_daily_report_prompt(self, daily_summary: Dict, insights: List[Dict],
                                 recommendations: List[str]) -> str:
        """Build prompt for daily SMS report"""

        prompt = f"""
Create a concise, motivating daily health report for SMS delivery (max 160 characters).

DAILY SUMMARY:
{json.dumps(daily_summary, indent=2)}

KEY INSIGHTS:
{json.dumps(insights, indent=2)}

RECOMMENDATIONS:
{json.dumps(recommendations, indent=2)}

Requirements:
- Keep it under 160 characters for SMS
- Start with the most important insight
- Include one actionable recommendation
- Use encouraging, positive tone
- Include relevant emoji for engagement
- Be specific with numbers when impactful

Example format: "🔥 HRV up 15% this week! Sleep quality improving. Focus: 20min evening walk for even better recovery. Keep it up! 💪"
"""
        return prompt

    def _build_intervention_analysis_prompt(self, intervention_data: Dict,
                                          statistical_results: Dict) -> str:
        """Build prompt for intervention effectiveness analysis"""

        prompt = f"""
Analyze the effectiveness of a health intervention using statistical evidence:

INTERVENTION DETAILS:
{json.dumps(intervention_data, indent=2)}

STATISTICAL RESULTS:
{json.dumps(statistical_results, indent=2)}

Provide analysis in this format:

EFFECTIVENESS ASSESSMENT:
- Overall effectiveness rating (1-10)
- Statistical confidence level
- Effect size interpretation

DETAILED FINDINGS:
- Which metrics showed significant improvement
- Timeline of changes observed
- Comparison to baseline patterns

MECHANISMS:
- Likely biological/physiological explanations
- Why this intervention worked (or didn't)
- Individual vs population-level factors

FUTURE RECOMMENDATIONS:
- Continue, modify, or discontinue intervention
- Optimization suggestions
- Monitoring recommendations

Base all conclusions on the statistical evidence provided. Be clear about confidence levels and limitations.
"""
        return prompt

    def get_provider_status(self) -> Dict:
        """Get status of all LLM providers"""
        status = {}

        for provider_type in LLMProvider:
            if provider_type in self.providers:
                status[provider_type.value] = {
                    'available': True,
                    'primary_model': self.model_configs[provider_type]['primary'],
                    'fallback_model': self.model_configs[provider_type]['fallback']
                }
            else:
                status[provider_type.value] = {
                    'available': False,
                    'reason': 'Not configured or unreachable'
                }

        return status

    def estimate_cost(self, prompt: str, provider: LLMProvider) -> float:
        """Estimate cost for a given prompt and provider"""
        try:
            # Rough token estimation (4 chars = 1 token)
            estimated_tokens = len(prompt) // 4

            config = self.model_configs[provider]
            estimated_cost = estimated_tokens * config['cost_per_1k_input'] / 1000

            return estimated_cost

        except Exception as e:
            logger.warning(f"Cost estimation failed: {str(e)}")
            return 0.0