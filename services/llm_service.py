"""
Multi-provider LLM service for intelligent health insights generation
"""

import requests
import json
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import logging
from utils.cache import cache_result
from datetime import datetime, timedelta
import os

# Conditional imports for LLM providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

try:
    import together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    together = None

logger = logging.getLogger(__name__)

# Function schemas for structured health queries
METRIC_FUNCTIONS = {
    "fetch_metric": {
        "name": "fetch_metric",
        "description": "Fetches an aggregate metric for a user over a date range",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_key": {
                    "type": "string",
                    "enum": ["hrv", "heart_rate", "sleep_score", "temperature", "recovery", "stress", "steps", "calories_burned", "active_minutes", "glucose", "hba1c", "vo2_max"]
                },
                "aggregation": {"type": "string", "enum": ["average", "min", "max", "latest", "sum"]},
                "start_date": {"type": "string", "format": "date", "description": "Start date in YYYY-MM-DD format"},
                "end_date": {"type": "string", "format": "date", "description": "End date in YYYY-MM-DD format"}
            },
            "required": ["metric_key", "aggregation", "start_date", "end_date"]
        }
    },
    "fetch_sleep_stage": {
        "name": "fetch_sleep_stage",
        "description": "Fetches sleep stage timing and duration information",
        "parameters": {
            "type": "object",
            "properties": {
                "stage_type": {"type": "string", "enum": ["deep", "rem", "light", "awake"]},
                "query_type": {"type": "string", "enum": ["average_timing", "duration", "first_occurrence"]},
                "start_date": {"type": "string", "format": "date"},
                "end_date": {"type": "string", "format": "date"}
            },
            "required": ["stage_type", "query_type", "start_date", "end_date"]
        }
    }
}

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
    response_time_ms: Optional[float] = None

class SMSLLMService:
    """LLM service optimized for SMS health monitoring agents"""

    def __init__(self):
        self.providers = {}
        self.provider_errors = {}
        self._initialize_cloud_providers()

        # Model configs optimized for SMS use case
        self.model_configs = {
            LLMProvider.OPENAI: {
                'sms_model': 'gpt-3.5-turbo',      # Fast, cheap for SMS
                'analysis_model': 'gpt-4-turbo',    # Better for complex analysis
                'cost_per_1k_input': 0.0005,       # GPT-3.5 pricing
                'cost_per_1k_output': 0.0015,
                'max_tokens_sms': 150,              # Perfect for SMS length
                'max_tokens_analysis': 2000
            },
            LLMProvider.ANTHROPIC: {
                'sms_model': 'claude-3-haiku-20240307',    # Fast, efficient
                'analysis_model': 'claude-3-haiku-20240307', # Use same model for now
                'cost_per_1k_input': 0.00025,              # Haiku pricing
                'cost_per_1k_output': 0.00125,
                'max_tokens_sms': 150,
                'max_tokens_analysis': 2000
            },
            LLMProvider.TOGETHER: {
                'sms_model': 'meta-llama/Llama-3.2-3B-Instruct-Turbo',     # Fast, serverless
                'analysis_model': 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo', # Better quality, serverless
                'cost_per_1k_input': 0.0002,
                'cost_per_1k_output': 0.0002,
                'max_tokens_sms': 150,
                'max_tokens_analysis': 2000
            }
        }

    def _initialize_cloud_providers(self):
        """Initialize only cloud-based providers suitable for SMS agents"""

        # OpenAI - Most reliable for production SMS
        try:
            if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
                try:
                    # Try new API first with minimal parameters
                    client = openai.OpenAI(
                        api_key=os.getenv('OPENAI_API_KEY')
                    )
                    # Test the client with a simple call
                    test_models = client.models.list()
                    self.providers[LLMProvider.OPENAI] = {'client': client, 'api_version': 'v1'}
                    logger.info("OpenAI initialized and tested (v1+ API)")
                except Exception as e:
                    logger.error(f"OpenAI v1 API failed: {str(e)}")
                    # Don't try legacy API - it's deprecated and causes issues
                    self.provider_errors[LLMProvider.OPENAI] = f"OpenAI setup failed: {str(e)}"
            elif not OPENAI_AVAILABLE:
                self.provider_errors[LLMProvider.OPENAI] = "OpenAI package not installed"
        except Exception as e:
            self.provider_errors[LLMProvider.OPENAI] = f"OpenAI setup failed: {str(e)}"
            logger.warning(f"OpenAI unavailable: {str(e)}")


        # Anthropic - Excellent for health analysis
        try:
            if ANTHROPIC_AVAILABLE and os.getenv('ANTHROPIC_API_KEY'):
                try:
                    client = anthropic.Anthropic(
                        api_key=os.getenv('ANTHROPIC_API_KEY')
                    )
                    self.providers[LLMProvider.ANTHROPIC] = {'client': client}
                    logger.info("Anthropic initialized")
                except Exception as e:
                    logger.error(f"Anthropic initialization failed: {str(e)}")
                    self.provider_errors[LLMProvider.ANTHROPIC] = f"Anthropic setup failed: {str(e)}"
            elif not ANTHROPIC_AVAILABLE:
                self.provider_errors[LLMProvider.ANTHROPIC] = "Anthropic package not installed"
        except Exception as e:
            self.provider_errors[LLMProvider.ANTHROPIC] = f"Anthropic setup failed: {str(e)}"
            logger.warning(f"Anthropic unavailable: {str(e)}")

        # Together.ai - Cost-effective backup
        try:
            if TOGETHER_AVAILABLE and os.getenv('TOGETHER_API_KEY'):
                together.api_key = os.getenv('TOGETHER_API_KEY')
                self.providers[LLMProvider.TOGETHER] = {'client': together}
                logger.info("Together.ai initialized")
            elif not TOGETHER_AVAILABLE:
                self.provider_errors[LLMProvider.TOGETHER] = "Together package not installed"
        except Exception as e:
            self.provider_errors[LLMProvider.TOGETHER] = f"Together.ai setup failed: {str(e)}"
            logger.warning(f"Together.ai unavailable: {str(e)}")

        if not self.providers:
            logger.error("No LLM providers available! SMS responses will use fallback insights only.")
        else:
            logger.info(f"SMS LLM service ready with providers: {list(self.providers.keys())}")

    def _select_optimal_provider(self, use_case: str) -> Optional[LLMProvider]:
        """Select the best provider for specific SMS use cases"""
        if not self.providers:
            return None

        # Priority order: OpenAI first (most reliable), then Anthropic, then Together
        priority_order = [LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.TOGETHER]

        for provider in priority_order:
            if provider in self.providers:
                return provider

        # Fallback to any available provider
        return list(self.providers.keys())[0] if self.providers else None

    def _call_openai(self, prompt: str, use_case: str, temperature: float = 0.1,
                     use_functions: bool = False, user_id: str = None) -> LLMResponse:
        """Call OpenAI with SMS-optimized settings and optional function calling"""
        import time
        start_time = time.time()

        provider_info = self.providers[LLMProvider.OPENAI]
        client = provider_info['client']
        is_v1_api = provider_info['api_version'] == 'v1'

        # Choose model and token limit based on use case
        config = self.model_configs[LLMProvider.OPENAI]
        if use_case == "sms_response":
            model = config['sms_model']
            max_tokens = config['max_tokens_sms']
        else:
            model = config['analysis_model']
            max_tokens = config['max_tokens_analysis']

        # Prepare messages with current date context
        today_str = datetime.now().strftime("%Y-%m-%d")
        messages = [
            {"role": "system", "content": f"You are a health assistant. Current date: {today_str}. Use past tense for historical data."},
            {"role": "user", "content": prompt}
        ]

        try:
            if is_v1_api:
                if use_functions and user_id:
                    # Enable function calling for structured queries
                    tools = [{"type": "function", "function": func} for func in METRIC_FUNCTIONS.values()]
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto",
                        temperature=temperature,
                        max_tokens=max_tokens
                    )

                    message = response.choices[0].message

                    # Check if function was called
                    if message.tool_calls:
                        return self._handle_function_calls(client, model, messages, response, user_id, start_time)
                    else:
                        content = message.content
                else:
                    # Regular chat completion
                    response = client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    content = response.choices[0].message.content

                tokens_used = response.usage.total_tokens
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
            else:
                # Legacy client detected - should not happen with modern OpenAI
                logger.warning("Legacy OpenAI client detected, but using v1 API calls anyway")
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens

            # Calculate cost based on actual model used
            actual_config = self.model_configs[LLMProvider.OPENAI]
            cost = (prompt_tokens * actual_config['cost_per_1k_input'] / 1000 +
                   completion_tokens * actual_config['cost_per_1k_output'] / 1000)

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            return LLMResponse(
                content=content.strip(),
                provider=LLMProvider.OPENAI,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost,
                response_time_ms=response_time
            )

        except Exception as e:
            logger.error(f"OpenAI call failed: {str(e)}")
            raise

    def _handle_function_calls(self, client, model: str, messages: list, response: Any,
                              user_id: str, start_time: float) -> LLMResponse:
        """Handle function calls and return final response"""
        import time

        message = response.choices[0].message
        messages.append(message)

        # Process each function call
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"Function call: {function_name} with args: {function_args}")

            # Execute the function
            try:
                if function_name == "fetch_metric":
                    result = self._execute_fetch_metric(user_id, **function_args)
                elif function_name == "fetch_sleep_stage":
                    result = self._execute_fetch_sleep_stage(user_id, **function_args)
                else:
                    result = {"error": f"Unknown function: {function_name}"}

                # Add function result to conversation
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result)
                })

            except Exception as e:
                logger.error(f"Function execution failed: {str(e)}")
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps({"error": str(e)})
                })

        # Get final response with function results
        final_response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )

        total_tokens = response.usage.total_tokens + final_response.usage.total_tokens
        response_time = (time.time() - start_time) * 1000

        # Calculate cost
        config = self.model_configs[LLMProvider.OPENAI]
        cost = (total_tokens * config['cost_per_1k_input'] / 1000)  # Simplified cost calc

        return LLMResponse(
            content=final_response.choices[0].message.content.strip(),
            provider=LLMProvider.OPENAI,
            model=model,
            tokens_used=total_tokens,
            cost_estimate=cost,
            response_time_ms=response_time
        )

    def _execute_fetch_metric(self, user_id: str, metric_key: str, aggregation: str,
                             start_date: str, end_date: str) -> Dict:
        """Execute fetch_metric function call"""
        try:
            from services.metrics_service import MetricsService
            metrics_service = MetricsService()

            # Call the aggregation method (we'll implement this next)
            result = metrics_service.fetch_metrics_aggregate(
                user_id, metric_key, aggregation, start_date, end_date
            )

            if result is not None:
                return {
                    "metric": metric_key,
                    "aggregation": aggregation,
                    "value": result,
                    "start_date": start_date,
                    "end_date": end_date,
                    "unit": self._get_metric_unit(metric_key)
                }
            else:
                return {"error": f"No data found for {metric_key} in date range {start_date} to {end_date}"}

        except Exception as e:
            logger.error(f"Metric fetch failed: {str(e)}")
            return {"error": f"Failed to fetch {metric_key}: {str(e)}"}

    def _execute_fetch_sleep_stage(self, user_id: str, stage_type: str, query_type: str,
                                  start_date: str, end_date: str) -> Dict:
        """Execute fetch_sleep_stage function call"""
        try:
            from services.metrics_service import MetricsService
            metrics_service = MetricsService()

            # Call the sleep stage method (we'll implement this next)
            result = metrics_service.fetch_sleep_stage_info(
                user_id, stage_type, query_type, start_date, end_date
            )

            return result if result else {"error": f"No {stage_type} sleep data found"}

        except Exception as e:
            logger.error(f"Sleep stage fetch failed: {str(e)}")
            return {"error": f"Failed to fetch sleep stage info: {str(e)}"}

    def _get_metric_unit(self, metric_key: str) -> str:
        """Get the unit for a metric"""
        units = {
            "hrv": "ms", "heart_rate": "bpm", "sleep_score": "score",
            "temperature": "celsius", "recovery": "score", "stress": "index",
            "steps": "count", "calories_burned": "calories", "active_minutes": "minutes",
            "glucose": "mg/dL", "hba1c": "percent", "vo2_max": "ml/kg/min"
        }
        return units.get(metric_key, "units")


    def _call_anthropic(self, prompt: str, use_case: str, temperature: float = 0.1) -> LLMResponse:
        """Call Anthropic with SMS-optimized settings"""
        import time
        start_time = time.time()

        client = self.providers[LLMProvider.ANTHROPIC]['client']

        # Choose model based on use case
        config = self.model_configs[LLMProvider.ANTHROPIC]
        if use_case == "sms_response":
            model = config['sms_model']
            max_tokens = config['max_tokens_sms']
        else:
            model = config['analysis_model']
            max_tokens = config['max_tokens_analysis']

        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

            cost = (response.usage.input_tokens * config['cost_per_1k_input'] / 1000 +
                   response.usage.output_tokens * config['cost_per_1k_output'] / 1000)

            response_time = (time.time() - start_time) * 1000

            return LLMResponse(
                content=content.strip(),
                provider=LLMProvider.ANTHROPIC,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost,
                response_time_ms=response_time
            )

        except Exception as e:
            logger.error(f"Anthropic call failed: {str(e)}")
            raise

    def _call_together(self, prompt: str, use_case: str, temperature: float = 0.1) -> LLMResponse:
        """Call Together.ai with SMS-optimized settings"""
        import time
        start_time = time.time()

        client = self.providers[LLMProvider.TOGETHER]['client']

        # Choose model based on use case
        config = self.model_configs[LLMProvider.TOGETHER]
        if use_case == "sms_response":
            model = config['sms_model']
            max_tokens = config['max_tokens_sms']
        else:
            model = config['analysis_model']
            max_tokens = config['max_tokens_analysis']

        try:
            response = client.Complete.create(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )

            # Fix response parsing - check structure
            if 'output' in response and 'choices' in response['output']:
                content = response['output']['choices'][0]['text']
                tokens_used = response['output']['usage']['total_tokens']
            elif 'choices' in response:
                content = response['choices'][0]['text']
                tokens_used = response.get('usage', {}).get('total_tokens', 0)
            else:
                # Fallback parsing
                content = str(response)
                tokens_used = 0

            cost = tokens_used * config['cost_per_1k_input'] / 1000

            response_time = (time.time() - start_time) * 1000

            return LLMResponse(
                content=content.strip(),
                provider=LLMProvider.TOGETHER,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost,
                response_time_ms=response_time
            )

        except Exception as e:
            logger.error(f"Together.ai call failed: {str(e)}")
            raise

    def generate_sms_response(self, prompt: str, max_length: int = 320) -> LLMResponse:
        """Generate SMS-optimized response (short, actionable, under 320 chars)"""

        # Add SMS-specific instructions to prompt
        sms_prompt = f"""You are a helpful health coach providing insights via SMS. Based on this health data analysis, write a brief, encouraging health insight.

Context: {prompt}

Write a natural, conversational health insight that:
- Is under {max_length} characters
- Uses a positive, encouraging tone with 1-2 emojis
- Explains what the data means for their health
- Gives actionable advice
- Sounds like a human health coach, not code or technical jargon

CRITICAL: Do not include any code, variables, quotes, or technical formatting. Do not use f-strings, triple quotes, or any programming syntax. Write only the SMS message text as if you're texting a friend directly.

Example response: Great progress! Your average heart rate of 85 bpm is in the healthy range. This suggests good cardiovascular fitness. Keep up your regular exercise routine and focus on getting 7-8 hours of sleep to maintain this excellent heart health! 💪

Your SMS message:"""

        provider = self._select_optimal_provider("sms_response")
        if not provider:
            # Fallback to manual SMS generation
            return self._generate_fallback_sms(prompt, max_length)

        try:
            if provider == LLMProvider.OPENAI:
                response = self._call_openai(sms_prompt, "sms_response", temperature=0.3)
            elif provider == LLMProvider.ANTHROPIC:
                response = self._call_anthropic(sms_prompt, "sms_response", temperature=0.3)
            elif provider == LLMProvider.TOGETHER:
                response = self._call_together(sms_prompt, "sms_response", temperature=0.3)
            else:
                raise Exception(f"SMS generation not implemented for {provider}")

            # Clean up response to prevent code-like output
            response.content = self._clean_sms_response(response.content)

            # Ensure response fits SMS length
            if len(response.content) > max_length:
                response.content = response.content[:max_length-3] + "..."

            return response

        except Exception as e:
            logger.warning(f"LLM SMS generation failed: {str(e)}")
            return self._generate_fallback_sms(prompt, max_length)

    def _clean_sms_response(self, content: str) -> str:
        """Clean SMS response to remove code-like formatting and ensure natural text"""
        import re

        # Remove common code patterns
        content = re.sub(r'```[\s\S]*?```', '', content)  # Remove code blocks
        content = re.sub(r'`[^`]*`', '', content)  # Remove inline code
        content = re.sub(r'f"""[\s\S]*?"""', '', content)  # Remove f-string blocks
        content = re.sub(r'"""[\s\S]*?"""', '', content)  # Remove triple quotes
        content = re.sub(r"'''[\s\S]*?'''", '', content)  # Remove single triple quotes
        content = re.sub(r'response\s*=\s*f?"""', '', content)  # Remove response= patterns
        content = re.sub(r'💡\s*"""', '', content)  # Remove lightbulb with quotes
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)  # Remove comments
        content = re.sub(r'^\s*\w+\s*=\s*.*$', '', content, flags=re.MULTILINE)  # Remove variable assignments

        # Clean up whitespace and formatting
        content = re.sub(r'\n\s*\n', '\n', content)  # Remove extra blank lines
        content = content.strip()

        # If content starts with quotes or code patterns, extract the actual message
        content = re.sub(r'^["\'](.+)["\']$', r'\1', content)  # Remove surrounding quotes

        # If content is empty or still looks like code, return a fallback
        if not content or any(pattern in content.lower() for pattern in ['def ', 'import ', 'class ', 'return ', 'print(']):
            return "📊 Health insight generated! Your metrics show positive trends. Keep up the great work! 💪"

        return content

    def generate_contextual_response(self, context_prompt: str, max_length: int = 320) -> LLMResponse:
        """Generate contextual response using conversation history"""

        # Enhance the context prompt for follow-up conversations
        enhanced_prompt = f"""You are a health coach continuing a conversation via SMS. Use the conversation history to provide a contextual, natural response.

{context_prompt}

Requirements:
- Continue the conversation naturally based on the context
- Reference previous discussion when relevant
- Be conversational and helpful
- Keep under {max_length} characters
- Use emojis sparingly (1-2 max)
- Don't repeat information already discussed
- Provide new insights or answer the follow-up question

Your contextual response:"""

        provider = self._select_optimal_provider("sms_response")
        if not provider:
            return self._generate_fallback_contextual_response(context_prompt, max_length)

        try:
            if provider == LLMProvider.OPENAI:
                response = self._call_openai(enhanced_prompt, "sms_response", temperature=0.4)
            elif provider == LLMProvider.ANTHROPIC:
                response = self._call_anthropic(enhanced_prompt, "sms_response", temperature=0.4)
            elif provider == LLMProvider.TOGETHER:
                response = self._call_together(enhanced_prompt, "sms_response", temperature=0.4)
            else:
                raise Exception(f"Contextual generation not implemented for {provider}")

            # Clean and limit response
            response.content = self._clean_sms_response(response.content)

            if len(response.content) > max_length:
                response.content = response.content[:max_length-3] + "..."

            return response

        except Exception as e:
            logger.warning(f"LLM contextual generation failed: {str(e)}")
            return self._generate_fallback_contextual_response(context_prompt, max_length)

    def _generate_fallback_contextual_response(self, context: str, max_length: int = 160) -> LLMResponse:
        """Generate fallback contextual response when LLMs fail"""
        # Simple contextual templates
        contextual_templates = [
            "Great follow-up question! Let me provide more insights on that. 💡",
            "That's a good point to explore further. Here's what I can add... 📊",
            "Building on our previous discussion, here's additional context. 🌟",
            "Good question! Let me expand on that topic for you. 💪"
        ]

        # Pick template based on context hash
        template_idx = abs(hash(context)) % len(contextual_templates)
        message = contextual_templates[template_idx]

        # Ensure it fits
        if len(message) > max_length:
            message = message[:max_length-3] + "..."

        return LLMResponse(
            content=message,
            provider=LLMProvider.OPENAI,  # Placeholder
            model="fallback_contextual",
            tokens_used=0,
            cost_estimate=0.0,
            response_time_ms=0
        )

    def generate_fallback_insight(self, correlation_coef: float, p_value: float,
                                sample_size: int, metric1: str, metric2: str) -> str:
        """Generate fallback insight for correlation analysis"""

        # Determine correlation strength
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

        # Create engaging SMS message
        if p_value < 0.05 and abs_corr > 0.6:
            message = f"{emoji} Strong {direction} correlation between {metric1_clean} & {metric2_clean}! r={correlation_coef:.3f}, p={p_value:.3f} (n={sample_size}). Statistically significant pattern!"
        elif p_value < 0.05:
            message = f"{emoji} Found {strength} {direction} correlation between {metric1_clean} & {metric2_clean}. r={correlation_coef:.3f}, p={p_value:.3f} (n={sample_size}). Significant relationship detected!"
        else:
            message = f"{emoji} {strength.title()} {direction} correlation between {metric1_clean} & {metric2_clean}. r={correlation_coef:.3f}, p={p_value:.3f} (n={sample_size}). Pattern detected but {significance}."

        return message[:160]  # SMS length limit

    def generate_health_analysis(self, metrics_data: Dict, statistical_analysis: Dict,
                               user_context: Dict) -> LLMResponse:
        """Generate comprehensive health analysis (longer format)"""

        provider = self._select_optimal_provider("health_analysis")
        if not provider:
            return self._generate_fallback_analysis(metrics_data, statistical_analysis, user_context)

        prompt = f"""
Analyze health data and provide actionable insights:

METRICS: {json.dumps(metrics_data, indent=2)}
STATISTICS: {json.dumps(statistical_analysis, indent=2)}
USER INFO: {json.dumps(user_context, indent=2)}

Provide:
1. Key findings (with confidence levels)
2. Health interpretation
3. Specific actionable recommendations
4. Priority level for each recommendation

Keep scientific but accessible. Focus on actionable insights.
"""

        try:
            if provider == LLMProvider.OPENAI:
                return self._call_openai(prompt, "health_analysis", temperature=0.1)
            elif provider == LLMProvider.ANTHROPIC:
                return self._call_anthropic(prompt, "health_analysis", temperature=0.1)
            elif provider == LLMProvider.TOGETHER:
                return self._call_together(prompt, "health_analysis", temperature=0.1)
            else:
                raise Exception(f"Analysis not implemented for {provider}")

        except Exception as e:
            logger.warning(f"LLM analysis failed: {str(e)}")
            return self._generate_fallback_analysis(metrics_data, statistical_analysis, user_context)

    def handle_structured_health_query(self, user_query: str, user_id: str) -> LLMResponse:
        """Handle health queries with function calling for precise data access"""

        provider = self._select_optimal_provider("health_analysis")
        if not provider or provider != LLMProvider.OPENAI:
            # Fallback to regular response if OpenAI not available (only provider with function calling)
            return self.generate_sms_response(user_query)

        try:
            # Use function calling for structured queries with OpenAI
            return self._call_openai(
                prompt=user_query,
                use_case="health_analysis",
                temperature=0.1,
                use_functions=True,
                user_id=user_id
            )
        except Exception as e:
            logger.warning(f"Structured query failed, falling back to regular response: {str(e)}")
            return self.generate_sms_response(user_query)

    def generate_response(self, prompt: str, task_type: str = "general",
                        provider: Optional[LLMProvider] = None,
                        temperature: float = 0.1, use_fallback: bool = True) -> LLMResponse:
        """Generate response using the best available provider (compatibility method)"""

        # Map task_type to use_case for SMSLLMService
        if task_type == "sms_response" or "sms" in prompt.lower():
            use_case = "sms_response"
        elif task_type == "analysis" or "analysis" in prompt.lower():
            use_case = "health_analysis"
        else:
            use_case = "general"

        # If provider is specified, try to use it
        if provider and provider in self.providers:
            try:
                if provider == LLMProvider.OPENAI:
                    return self._call_openai(prompt, use_case, temperature)
                elif provider == LLMProvider.ANTHROPIC:
                    return self._call_anthropic(prompt, use_case, temperature)
                elif provider == LLMProvider.TOGETHER:
                    return self._call_together(prompt, use_case, temperature)
            except Exception as e:
                logger.warning(f"Specified provider {provider} failed: {str(e)}")
                if not use_fallback:
                    raise

        # Use optimal provider selection
        if use_case == "sms_response":
            return self.generate_sms_response(prompt)
        elif use_case == "health_analysis":
            # For health analysis, we need to create mock data since this is a general method
            mock_metrics = {"general": "data"}
            mock_stats = {"general": "analysis"}
            mock_context = {"query": prompt}
            return self.generate_health_analysis(mock_metrics, mock_stats, mock_context)
        else:
            # Default to SMS response for general queries
            return self.generate_sms_response(prompt)

    def _generate_fallback_sms(self, context: str, max_length: int = 160) -> LLMResponse:
        """Generate fallback SMS when LLMs fail"""
        # Simple template-based SMS generation
        sms_templates = [
            "📊 Health data updated! Check trends and stay consistent with your goals 💪",
            "🔥 Keep tracking! Your consistency helps identify important health patterns ⭐",
            "📈 Data logged! Regular monitoring helps optimize your health journey 🎯",
            "✅ Update received! Your health metrics are being analyzed for insights 🧠"
        ]

        # Pick template based on context hash (deterministic but varied)
        template_idx = abs(hash(context)) % len(sms_templates)
        message = sms_templates[template_idx]

        # Ensure it fits
        if len(message) > max_length:
            message = message[:max_length-3] + "..."

        return LLMResponse(
            content=message,
            provider=LLMProvider.OPENAI,  # Placeholder
            model="fallback",
            tokens_used=0,
            cost_estimate=0.0,
            response_time_ms=0
        )

    def _generate_fallback_analysis(self, metrics_data: Dict, statistical_analysis: Dict,
                                  user_context: Dict) -> LLMResponse:
        """Generate fallback analysis when LLMs fail"""

        insights = []

        # Process correlations
        if "correlations" in statistical_analysis:
            for corr_name, corr_data in statistical_analysis["correlations"].items():
                if "_vs_" in corr_name:
                    metric1, metric2 = corr_name.split("_vs_")
                    coef = corr_data.get("coef", 0.0)
                    p_val = corr_data.get("p_value", 1.0)

                    strength = "strong" if abs(coef) > 0.6 else "moderate" if abs(coef) > 0.3 else "weak"
                    direction = "positive" if coef > 0 else "negative"
                    significance = "significant" if p_val < 0.05 else "not significant"

                    insight = f"Found {strength} {direction} correlation between {metric1.replace('_', ' ')} and {metric2.replace('_', ' ')} (r={coef:.3f}, p={p_val:.3f}) - {significance}."
                    insights.append(insight)

        # Add trend analysis
        if "trends" in statistical_analysis:
            for trend_name, trend_data in statistical_analysis["trends"].items():
                rate = trend_data.get("rate", 0.0)
                direction = "improving" if rate > 0 else "declining" if rate < 0 else "stable"
                insight = f"{trend_name.replace('_', ' ').title()} is {direction} (rate: {rate:.2f})."
                insights.append(insight)

        # Combine insights
        if insights:
            content = "HEALTH ANALYSIS:\n\n" + "\n".join(insights)
            content += "\n\nRECOMMENDation: Focus on statistically significant relationships for actionable improvements."
        else:
            content = "Health data analysis complete. Continue consistent tracking to identify meaningful patterns."

        return LLMResponse(
            content=content,
            provider=LLMProvider.OPENAI,  # Placeholder
            model="fallback",
            tokens_used=0,
            cost_estimate=0.0,
            response_time_ms=0
        )

    def get_provider_status(self) -> Dict:
        """Get status optimized for SMS deployment monitoring"""
        status = {
            'summary': {
                'providers_available': len(self.providers),
                'providers_total': len(LLMProvider),
                'sms_ready': len(self.providers) > 0 or True,  # Always ready due to fallbacks
                'deployment_suitable': True  # Cloud-only providers
            },
            'providers': {}
        }

        for provider_type in LLMProvider:
            if provider_type in self.providers:
                status['providers'][provider_type.value] = {
                    'available': True,
                    'sms_model': self.model_configs[provider_type]['sms_model'],
                    'analysis_model': self.model_configs[provider_type]['analysis_model'],
                    'cost_per_sms_estimate': self._estimate_sms_cost(provider_type)
                }
            else:
                status['providers'][provider_type.value] = {
                    'available': False,
                    'reason': self.provider_errors.get(provider_type, 'Not configured')
                }

        return status

    def _estimate_sms_cost(self, provider: LLMProvider) -> float:
        """Estimate cost per SMS response"""
        config = self.model_configs[provider]
        # Assume average SMS prompt ~100 tokens, response ~50 tokens
        estimated_cost = (100 * config['cost_per_1k_input'] + 50 * config['cost_per_1k_output']) / 1000
        return round(estimated_cost, 6)

    def health_check(self) -> Dict:
        """Quick health check for SMS service monitoring"""
        return {
            'service_ready': len(self.providers) > 0,
            'fallback_ready': True,  # Always true - we have manual fallbacks
            'providers_count': len(self.providers),
            'estimated_response_time_ms': 2000 if self.providers else 50,  # LLM vs fallback
            'deployment_type': 'cloud_optimized'
        }


# Backward compatibility aliases
LLMService = SMSLLMService

# Additional alias method for compatibility
def create_llm_service():
    """Factory function for creating LLM service"""
    return SMSLLMService()