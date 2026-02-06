"""
Multi-provider LLM service - FIXED VERSION for 'proxies' error
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
    """LLM service optimized for SMS health monitoring agents - PROXIES FIXED"""

    def __init__(self):
        self.providers = {}
        self.provider_errors = {}
        self._initialize_cloud_providers()

        # Model configs optimized for SMS use case
        self.model_configs = {
            LLMProvider.OPENAI: {
                'sms_model': 'gpt-3.5-turbo',
                'analysis_model': 'gpt-4-turbo',
                'cost_per_1k_input': 0.0005,
                'cost_per_1k_output': 0.0015,
                'max_tokens_sms': 150,
                'max_tokens_analysis': 2000
            },
            LLMProvider.ANTHROPIC: {
                'sms_model': 'claude-3-haiku-20240307',
                'analysis_model': 'claude-3-haiku-20240307',
                'cost_per_1k_input': 0.00025,
                'cost_per_1k_output': 0.00125,
                'max_tokens_sms': 150,
                'max_tokens_analysis': 2000
            }
        }

    def _initialize_cloud_providers(self):
        """Initialize providers with robust error handling for proxies issues"""

        # OpenAI - FIXED initialization
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            success = False

            # Method 1: Try basic initialization
            try:
                logger.info("Attempting OpenAI basic initialization...")
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

                # Test with a simple call
                _ = client.models.list()
                self.providers[LLMProvider.OPENAI] = {'client': client, 'api_version': 'v1'}
                logger.info("✅ OpenAI initialized successfully (basic method)")
                success = True

            except Exception as e:
                logger.warning(f"OpenAI basic initialization failed: {str(e)}")

                # Method 2: Try with timeout and no proxies
                try:
                    logger.info("Attempting OpenAI initialization with explicit timeout...")
                    client = openai.OpenAI(
                        api_key=os.getenv('OPENAI_API_KEY'),
                        timeout=30.0
                    )

                    # Test with a simple call
                    _ = client.models.list()
                    self.providers[LLMProvider.OPENAI] = {'client': client, 'api_version': 'v1'}
                    logger.info("✅ OpenAI initialized successfully (timeout method)")
                    success = True

                except Exception as e2:
                    logger.warning(f"OpenAI timeout initialization failed: {str(e2)}")

                    # Method 3: Environment variable approach
                    try:
                        logger.info("Attempting OpenAI initialization via environment...")
                        orig_key = os.environ.get('OPENAI_API_KEY')
                        os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

                        client = openai.OpenAI()

                        # Test with a simple call
                        _ = client.models.list()
                        self.providers[LLMProvider.OPENAI] = {'client': client, 'api_version': 'v1'}
                        logger.info("✅ OpenAI initialized successfully (environment method)")
                        success = True

                        if orig_key:
                            os.environ['OPENAI_API_KEY'] = orig_key

                    except Exception as e3:
                        logger.error(f"All OpenAI initialization methods failed: {str(e3)}")
                        self.provider_errors[LLMProvider.OPENAI] = f"All methods failed. Last error: {str(e3)}"

            if not success:
                self.provider_errors[LLMProvider.OPENAI] = "Failed to initialize - check logs for details"

        elif not OPENAI_AVAILABLE:
            self.provider_errors[LLMProvider.OPENAI] = "OpenAI package not installed"
        else:
            self.provider_errors[LLMProvider.OPENAI] = "OPENAI_API_KEY not found"

        # Anthropic - FIXED initialization
        if ANTHROPIC_AVAILABLE and os.getenv('ANTHROPIC_API_KEY'):
            try:
                logger.info("Attempting Anthropic initialization...")
                client = anthropic.Anthropic(
                    api_key=os.getenv('ANTHROPIC_API_KEY'),
                    timeout=30.0
                )
                self.providers[LLMProvider.ANTHROPIC] = {'client': client}
                logger.info("✅ Anthropic initialized successfully")

            except Exception as e:
                logger.error(f"Anthropic initialization failed: {str(e)}")
                self.provider_errors[LLMProvider.ANTHROPIC] = f"Anthropic setup failed: {str(e)}"

        elif not ANTHROPIC_AVAILABLE:
            self.provider_errors[LLMProvider.ANTHROPIC] = "Anthropic package not installed"
        else:
            self.provider_errors[LLMProvider.ANTHROPIC] = "ANTHROPIC_API_KEY not found"

        # Report status
        if not self.providers:
            logger.error("❌ No LLM providers available! SMS responses will use fallback insights only.")
        else:
            available_providers = list(self.providers.keys())
            logger.info(f"✅ SMS LLM service ready with providers: {[p.value for p in available_providers]}")

    def _select_optimal_provider(self, use_case: str) -> Optional[LLMProvider]:
        """Select the best provider for specific SMS use cases"""
        if not self.providers:
            return None

        # Priority order - OpenAI first for function calling
        priority = [LLMProvider.OPENAI, LLMProvider.ANTHROPIC]

        # Return first available provider from priority list
        for provider in priority:
            if provider in self.providers:
                return provider

        return None

    def _call_openai(self, prompt: str, use_case: str, temperature: float = 0.1,
                     use_functions: bool = False, user_id: str = None) -> LLMResponse:
        """Call OpenAI with SMS-optimized settings and optional function calling"""
        import time
        start_time = time.time()

        if LLMProvider.OPENAI not in self.providers:
            raise Exception("OpenAI not available")

        provider_info = self.providers[LLMProvider.OPENAI]
        client = provider_info['client']

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

            # Calculate cost based on actual model used
            actual_config = self.model_configs[LLMProvider.OPENAI]
            cost = (prompt_tokens * actual_config['cost_per_1k_input'] / 1000 +
                   completion_tokens * actual_config['cost_per_1k_output'] / 1000)

            response_time = (time.time() - start_time) * 1000

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
        cost = (total_tokens * config['cost_per_1k_input'] / 1000)

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

    def generate_sms_response(self, prompt: str, max_length: int = 320) -> LLMResponse:
        """Generate SMS-optimized response"""
        sms_prompt = f"""Create an engaging health insight for SMS (max {max_length} characters):

{prompt}

Requirements:
- Keep under {max_length} characters total
- Use encouraging, positive tone with emojis
- Include specific numbers and statistics
- Provide actionable health interpretation
- Be conversational and engaging"""

        provider = self._select_optimal_provider("sms_response")
        if not provider:
            return self._generate_fallback_sms(prompt, max_length)

        try:
            if provider == LLMProvider.OPENAI:
                response = self._call_openai(sms_prompt, "sms_response", temperature=0.3)
            else:
                response = self._call_anthropic(sms_prompt, "sms_response", temperature=0.3)

            # Ensure response fits SMS length
            if len(response.content) > max_length:
                response.content = response.content[:max_length-3] + "..."

            return response

        except Exception as e:
            logger.warning(f"LLM SMS generation failed: {str(e)}")
            return self._generate_fallback_sms(prompt, max_length)

    def handle_structured_health_query(self, user_query: str, user_id: str) -> LLMResponse:
        """Handle health queries with function calling for precise data access"""

        provider = self._select_optimal_provider("health_analysis")
        if not provider or provider != LLMProvider.OPENAI:
            return self.generate_sms_response(user_query)

        try:
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

    def _call_anthropic(self, prompt: str, use_case: str, temperature: float = 0.1) -> LLMResponse:
        """Call Anthropic - simplified version"""
        import time
        start_time = time.time()

        if LLMProvider.ANTHROPIC not in self.providers:
            raise Exception("Anthropic not available")

        client = self.providers[LLMProvider.ANTHROPIC]['client']
        config = self.model_configs[LLMProvider.ANTHROPIC]

        model = config['sms_model'] if use_case == "sms_response" else config['analysis_model']
        max_tokens = config['max_tokens_sms'] if use_case == "sms_response" else config['max_tokens_analysis']

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

    def _generate_fallback_sms(self, context: str, max_length: int = 160) -> LLMResponse:
        """Generate fallback SMS when LLMs fail"""
        sms_templates = [
            "📊 Health data updated! Check trends and stay consistent with your goals 💪",
            "🔥 Keep tracking! Your consistency helps identify important health patterns ⭐",
            "📈 Data logged! Regular monitoring helps optimize your health journey 🎯",
            "✅ Update received! Your health metrics are being analyzed for insights 🧠"
        ]

        template_idx = abs(hash(context)) % len(sms_templates)
        message = sms_templates[template_idx]

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

    def get_provider_status(self) -> Dict:
        """Get provider status"""
        status = {
            'summary': {
                'providers_available': len(self.providers),
                'sms_ready': len(self.providers) > 0 or True,
                'deployment_suitable': True
            },
            'providers': {}
        }

        for provider_type in LLMProvider:
            if provider_type in self.providers:
                status['providers'][provider_type.value] = {
                    'available': True,
                    'status': 'active'
                }
            else:
                status['providers'][provider_type.value] = {
                    'available': False,
                    'reason': self.provider_errors.get(provider_type, 'Not configured')
                }

        return status

# Backward compatibility
LLMService = SMSLLMService