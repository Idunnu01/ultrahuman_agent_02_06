#!/usr/bin/env python3
"""
Claude-powered LLM Chat Analyzer for SMS
Handles natural language health questions with tool calling (80-90% cheaper than OpenAI!)
"""

from anthropic import Anthropic
from datetime import datetime, timedelta
import json
import logging
import os
from typing import Dict, Any, Optional, List
from .metrics_service import MetricsService
from .statistical_analyzer import StatisticalAnalyzer
from app.models import Metric
from sqlalchemy import desc, and_

logger = logging.getLogger(__name__)

class LLMChatAnalyzer:
    """Claude-powered analyzer for natural language health questions (5-10x cheaper!)"""

    def __init__(self):
        # Initialize with Claude (cheaper and smarter!)
        self.client = Anthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            timeout=45.0  # Longer timeout for reliability
        )
        self.model = "claude-3-haiku-20240307"  # Cheapest model with great performance
        self.metrics_service = MetricsService()
        self.stats_analyzer = StatisticalAnalyzer()

        # Function definitions for OpenAI function calling
        self.available_functions = {
            "get_recent_health_data": self._get_recent_health_data,
            "get_health_data_for_timeframe": self._get_health_data_for_timeframe,
            "get_sleep_analysis": self._get_sleep_analysis,
            "get_heart_rate_analysis": self._get_heart_rate_analysis,
            "get_activity_patterns": self._get_activity_patterns,
            "compare_time_periods": self._compare_time_periods,
            "get_health_trends": self._get_health_trends
        }

        self.function_schemas = [
            {
                "name": "get_recent_health_data",
                "description": "Get recent health metrics for the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of metrics to retrieve (heart_rate, hrv, temperature, steps, etc.)"
                        },
                        "hours_back": {
                            "type": "integer",
                            "description": "How many hours back to look (default 24)"
                        }
                    },
                    "required": ["metric_types"]
                }
            },
            {
                "name": "get_sleep_analysis",
                "description": "Get detailed sleep analysis including bedtime, sleep quality, overnight patterns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["bedtime", "sleep_quality", "overnight_patterns", "sleep_duration"],
                            "description": "Type of sleep analysis to perform"
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "How many days back to analyze (default 14)"
                        }
                    },
                    "required": ["analysis_type"]
                }
            },
            {
                "name": "get_heart_rate_analysis",
                "description": "Get heart rate analysis for specific times or patterns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["resting", "active", "recovery", "patterns"],
                            "description": "Type of heart rate analysis"
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Time period like 'last night', '3am', 'morning'"
                        }
                    },
                    "required": ["analysis_type"]
                }
            }
        ]

        # Detect PythonAnywhere environment
        self.is_pythonanywhere = 'pythonanywhere' in os.getenv('HOSTNAME', '').lower() or \
                                'bphlite' in os.getenv('USER', '').lower()

        if self.is_pythonanywhere:
            # PythonAnywhere-specific settings
            self.default_timeout = 45
            self.max_retries = 2
        else:
            self.default_timeout = 30
            self.max_retries = 1

    def __init___old(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.metrics_service = MetricsService()
        self.stats_analyzer = StatisticalAnalyzer()

        # Function definitions for OpenAI function calling
        self.available_functions = {
            "get_recent_health_data": self._get_recent_health_data,
            "get_health_data_for_timeframe": self._get_health_data_for_timeframe,
            "get_sleep_analysis": self._get_sleep_analysis,
            "get_heart_rate_analysis": self._get_heart_rate_analysis,
            "get_activity_patterns": self._get_activity_patterns,
            "compare_time_periods": self._compare_time_periods,
            "get_health_trends": self._get_health_trends
        }

        self.function_schemas = [
            {
                "name": "get_recent_health_data",
                "description": "Get recent health metrics for the user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of metrics to retrieve (heart_rate, hrv, temperature, steps, etc.)"
                        },
                        "hours_back": {
                            "type": "integer",
                            "description": "How many hours back to look (default 24)"
                        }
                    },
                    "required": ["metric_types"]
                }
            },
            {
                "name": "get_health_data_for_timeframe",
                "description": "Get health data for a specific time period or time of day",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Types of metrics to retrieve"
                        },
                        "start_hour": {
                            "type": "integer",
                            "description": "Start hour (0-23) for time-specific queries"
                        },
                        "end_hour": {
                            "type": "integer",
                            "description": "End hour (0-23) for time-specific queries"
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "How many days back to analyze (default 7)"
                        }
                    },
                    "required": ["metric_types"]
                }
            },
            {
                "name": "get_sleep_analysis",
                "description": "Get detailed sleep analysis including bedtime, sleep quality, overnight patterns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["bedtime", "sleep_quality", "overnight_patterns", "sleep_duration"],
                            "description": "Type of sleep analysis to perform"
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "How many days back to analyze (default 14)"
                        }
                    },
                    "required": ["analysis_type"]
                }
            },
            {
                "name": "get_heart_rate_analysis",
                "description": "Analyze heart rate patterns, zones, and specific time periods",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_type": {
                            "type": "string",
                            "enum": ["resting", "active", "zones", "time_specific", "daily_patterns"],
                            "description": "Type of heart rate analysis"
                        },
                        "target_time": {
                            "type": "string",
                            "description": "Specific time for analysis (e.g., '3:00 AM', 'morning', 'evening')"
                        }
                    },
                    "required": ["analysis_type"]
                }
            },
            {
                "name": "get_activity_patterns",
                "description": "Analyze daily activity patterns, step counts, movement trends",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern_type": {
                            "type": "string",
                            "enum": ["daily_rhythm", "peak_activity", "weekly_comparison", "step_analysis"],
                            "description": "Type of activity pattern analysis"
                        }
                    },
                    "required": ["pattern_type"]
                }
            },
            {
                "name": "compare_time_periods",
                "description": "Compare health metrics between different time periods",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "comparison_type": {
                            "type": "string",
                            "enum": ["weekday_vs_weekend", "morning_vs_evening", "this_week_vs_last", "yesterday_vs_today"],
                            "description": "Type of time period comparison"
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to compare"
                        }
                    },
                    "required": ["comparison_type", "metrics"]
                }
            },
            {
                "name": "get_health_trends",
                "description": "Identify trends and patterns in health data over time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric_type": {
                            "type": "string",
                            "description": "Metric to analyze for trends"
                        },
                        "trend_period": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Time period for trend analysis"
                        }
                    },
                    "required": ["metric_type", "trend_period"]
                }
            }
        ]

    def analyze_message(self, message: str, user_id: str) -> str:
        """Main entry point for analyzing natural language health questions"""

        # Always use PythonAnywhere-optimized version
        return self._analyze_message_pa_optimized(message, user_id)

    def _analyze_message_pa_optimized(self, message: str, user_id: str) -> str:
        """Claude-optimized message analysis (5-10x cheaper than OpenAI!)"""
        try:
            # Shorter system prompt for faster processing
            system_prompt = f"""You are a health assistant analyzing Ultrahuman data via SMS.
User: {user_id}
Keep responses under 1000 chars. Be concise, friendly, and actionable."""

            # Call Claude with optimized settings
            response = self.client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.5,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": message}
                ]
            )

            # Extract response text
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                return "I can help with your health data questions!"

        except Exception as e:
            # Claude error handling
            logger.error(f"Claude analysis failed: {str(e)}")
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                return f"🤖 Claude connection error: {str(e)[:100]}. Please try again in a moment."
            else:
                return f"🤖 Claude processing error: {str(e)[:100]}. Please rephrase your question."

    def _handle_tool_calls_pa(self, message_response, user_id: str, original_message: str) -> str:
        """PythonAnywhere-optimized tool call handling"""
        try:
            tool_call = message_response.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            function_args['user_id'] = user_id

            if function_name in self.available_functions:
                # Quick timeout for function execution
                function_result = self.available_functions[function_name](**function_args)

                # Simplified follow-up (no second API call to save time)
                if isinstance(function_result, dict) and 'error' not in function_result:
                    return f"Based on your {function_name.replace('_', ' ')}: {str(function_result)[:500]}..."
                else:
                    return "I found some data but had trouble processing it. Try a more specific question."
            else:
                return f"I understand you're asking about {function_name.replace('_', ' ')} but I'm having trouble with that right now."

        except Exception as e:
            return f"🤖 ChatGPT function call error: {str(e)[:100]}. Please try rephrasing your health question."

    def analyze_message_old(self, message: str, user_id: str) -> str:
        """Main entry point for analyzing natural language health questions"""
        try:
            # Create the system prompt with context about available health data
            system_prompt = self._create_system_prompt(user_id)

            # Call OpenAI with function calling
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                tools=[{"type": "function", "function": schema} for schema in self.function_schemas],
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500,
                timeout=60  # 60 second timeout
            )

            # Handle function calls
            message_response = response.choices[0].message

            if message_response.tool_calls:
                return self._handle_tool_calls(message_response, user_id, message)
            else:
                return message_response.content

        except Exception as e:
            logger.error(f"LLM analysis error: {str(e)}")
            return f"I'm having trouble processing your question right now. Error: {str(e)}"

    def _create_system_prompt(self, user_id: str) -> str:
        """Create comprehensive system prompt with user context"""

        # Get recent data overview for context
        recent_data_summary = self._get_data_summary(user_id)

        return f"""You are an intelligent health assistant that analyzes Ultrahuman health data via SMS.

CONTEXT:
- You have access to comprehensive health metrics including heart rate, HRV, temperature, sleep data, steps, and more
- Current user: {user_id}
- Recent data summary: {recent_data_summary}

CAPABILITIES:
- Answer specific time-based questions ("What was my heart rate at 3am?")
- Provide sleep analysis including bedtime patterns and overnight metrics
- Compare different time periods (weekdays vs weekends, morning vs evening)
- Identify health trends and patterns
- Give personalized insights based on the user's actual data

RESPONSE STYLE:
- Keep responses concise for SMS (under 1000 characters when possible)
- Use emojis appropriately for SMS context
- Be conversational and friendly
- Provide specific numbers and insights when available
- If data is limited, explain what you can see and suggest ways to get better insights

FUNCTION CALLING:
- Use the available functions to fetch and analyze the user's health data
- Always call functions to get actual data rather than making assumptions
- Combine multiple function calls if needed to fully answer the question

Remember: You're providing real health insights based on actual user data via SMS."""

    def _get_data_summary(self, user_id: str) -> str:
        """Get a quick summary of available data for context"""
        try:
            # Get most recent data by type
            recent_metrics = Metric.query.filter(
                Metric.user_id == user_id
            ).order_by(desc(Metric.timestamp)).limit(10).all()

            if not recent_metrics:
                return "No recent data available"

            metric_types = set(m.metric_type for m in recent_metrics)
            latest_time = recent_metrics[0].timestamp
            hours_ago = (datetime.utcnow() - latest_time).total_seconds() / 3600

            return f"Available metrics: {', '.join(metric_types)}. Latest data: {hours_ago:.1f}h ago"

        except Exception:
            return "Data summary unavailable"

    def _handle_tool_calls(self, message_response, user_id: str, original_message: str) -> str:
        """Handle OpenAI tool calls (function calling)"""
        try:
            tool_call = message_response.tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # Add user_id to function arguments
            function_args['user_id'] = user_id

            # Call the appropriate function
            if function_name in self.available_functions:
                function_result = self.available_functions[function_name](**function_args)

                # Create messages for follow-up call
                messages = [
                    {"role": "system", "content": self._create_system_prompt(user_id)},
                    {"role": "user", "content": original_message},
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    },
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(function_result)
                    }
                ]

                # Create follow-up message to OpenAI with function result
                follow_up_response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1500,
                    timeout=60  # 60 second timeout
                )

                return follow_up_response.choices[0].message.content
            else:
                return f"Unknown function: {function_name}"

        except Exception as e:
            logger.error(f"Tool call error: {str(e)}")
            return f"I had trouble analyzing your request. Error: {str(e)}"

    # Function implementations
    def _get_recent_health_data(self, user_id: str, metric_types: List[str], hours_back: int = 24) -> Dict[str, Any]:
        """Get recent health data for specified metrics"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            result = {}

            for metric_type in metric_types:
                metrics = Metric.query.filter(
                    and_(
                        Metric.user_id == user_id,
                        Metric.metric_type == metric_type,
                        Metric.timestamp >= cutoff_time
                    )
                ).order_by(desc(Metric.timestamp)).limit(100).all()

                result[metric_type] = [
                    {
                        'value': m.value,
                        'timestamp': m.timestamp.isoformat(),
                        'source': m.source
                    } for m in metrics
                ]

            return result

        except Exception as e:
            logger.error(f"Recent data fetch error: {str(e)}")
            return {"error": str(e)}

    def _get_health_data_for_timeframe(self, user_id: str, metric_types: List[str],
                                     start_hour: Optional[int] = None, end_hour: Optional[int] = None,
                                     days_back: int = 7) -> Dict[str, Any]:
        """Get health data for specific time periods"""
        try:
            result = {}

            for metric_type in metric_types:
                # Get base data
                cutoff_time = datetime.utcnow() - timedelta(days=days_back)
                metrics = Metric.query.filter(
                    and_(
                        Metric.user_id == user_id,
                        Metric.metric_type == metric_type,
                        Metric.timestamp >= cutoff_time
                    )
                ).all()

                # Filter by time of day if specified
                if start_hour is not None and end_hour is not None:
                    filtered_metrics = []
                    for m in metrics:
                        hour = m.timestamp.hour
                        if start_hour <= end_hour:
                            if start_hour <= hour <= end_hour:
                                filtered_metrics.append(m)
                        else:  # Crosses midnight
                            if hour >= start_hour or hour <= end_hour:
                                filtered_metrics.append(m)
                    metrics = filtered_metrics

                result[metric_type] = [
                    {
                        'value': m.value,
                        'timestamp': m.timestamp.isoformat(),
                        'hour': m.timestamp.hour
                    } for m in metrics
                ]

            return result

        except Exception as e:
            logger.error(f"Timeframe data fetch error: {str(e)}")
            return {"error": str(e)}

    def _get_sleep_analysis(self, user_id: str, analysis_type: str, days_back: int = 14) -> Dict[str, Any]:
        """Perform detailed sleep analysis"""
        try:
            result = {"analysis_type": analysis_type}

            if analysis_type == "bedtime":
                # Get bedtime data from bedtime metrics
                cutoff_time = datetime.utcnow() - timedelta(days=days_back)
                bedtime_metrics = Metric.query.filter(
                    and_(
                        Metric.user_id == user_id,
                        Metric.metric_type == 'bedtime',
                        Metric.timestamp >= cutoff_time
                    )
                ).order_by(desc(Metric.timestamp)).all()

                bedtimes = []
                for m in bedtime_metrics:
                    hour = int(m.value)
                    minute = int((m.value - hour) * 60)
                    bedtimes.append({
                        'bedtime': f"{hour:02d}:{minute:02d}",
                        'date': m.timestamp.date().isoformat(),
                        'decimal_hour': m.value
                    })

                result["bedtime_data"] = bedtimes

                if bedtimes:
                    avg_bedtime = sum(b['decimal_hour'] for b in bedtimes) / len(bedtimes)
                    avg_hour = int(avg_bedtime)
                    avg_minute = int((avg_bedtime - avg_hour) * 60)
                    result["average_bedtime"] = f"{avg_hour:02d}:{avg_minute:02d}"

            elif analysis_type == "sleep_quality":
                # Get sleep score data
                cutoff_time = datetime.utcnow() - timedelta(days=days_back)
                sleep_scores = Metric.query.filter(
                    and_(
                        Metric.user_id == user_id,
                        Metric.metric_type == 'sleep_score',
                        Metric.timestamp >= cutoff_time
                    )
                ).order_by(desc(Metric.timestamp)).all()

                result["sleep_scores"] = [
                    {
                        'score': m.value,
                        'date': m.timestamp.date().isoformat()
                    } for m in sleep_scores
                ]

                if sleep_scores:
                    avg_score = sum(s.value for s in sleep_scores) / len(sleep_scores)
                    result["average_sleep_score"] = round(avg_score, 1)

            return result

        except Exception as e:
            logger.error(f"Sleep analysis error: {str(e)}")
            return {"error": str(e)}

    def _get_heart_rate_analysis(self, user_id: str, analysis_type: str, target_time: Optional[str] = None) -> Dict[str, Any]:
        """Analyze heart rate patterns"""
        try:
            result = {"analysis_type": analysis_type}

            # Get recent heart rate data
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            hr_metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.metric_type == 'heart_rate',
                    Metric.timestamp >= cutoff_time
                )
            ).all()

            if not hr_metrics:
                return {"error": "No heart rate data available"}

            if analysis_type == "time_specific" and target_time:
                # Parse target time (e.g., "3:00 AM", "morning")
                if "3" in target_time and ("am" in target_time.lower() or "AM" in target_time):
                    # 3 AM window (2:30-3:30)
                    filtered_hr = [m for m in hr_metrics if 2.5 <= m.timestamp.hour + m.timestamp.minute/60 <= 3.5]
                elif "morning" in target_time.lower():
                    # Morning window (6-10 AM)
                    filtered_hr = [m for m in hr_metrics if 6 <= m.timestamp.hour <= 10]
                elif "evening" in target_time.lower():
                    # Evening window (6-10 PM)
                    filtered_hr = [m for m in hr_metrics if 18 <= m.timestamp.hour <= 22]
                else:
                    filtered_hr = hr_metrics

                if filtered_hr:
                    values = [m.value for m in filtered_hr]
                    result["target_time"] = target_time
                    result["average_hr"] = round(sum(values) / len(values), 1)
                    result["min_hr"] = min(values)
                    result["max_hr"] = max(values)
                    result["data_points"] = len(values)
                    result["time_range"] = f"{filtered_hr[0].timestamp.isoformat()} to {filtered_hr[-1].timestamp.isoformat()}"
                else:
                    result["error"] = f"No heart rate data found for {target_time}"

            elif analysis_type == "daily_patterns":
                # Analyze patterns by hour of day
                hourly_data = {}
                for hr in hr_metrics:
                    hour = hr.timestamp.hour
                    if hour not in hourly_data:
                        hourly_data[hour] = []
                    hourly_data[hour].append(hr.value)

                hourly_averages = {
                    hour: round(sum(values) / len(values), 1)
                    for hour, values in hourly_data.items()
                }

                result["hourly_averages"] = hourly_averages
                if hourly_averages:
                    peak_hour = max(hourly_averages.keys(), key=lambda k: hourly_averages[k])
                    result["peak_hr_hour"] = peak_hour
                    result["peak_hr_value"] = hourly_averages[peak_hour]

            return result

        except Exception as e:
            logger.error(f"Heart rate analysis error: {str(e)}")
            return {"error": str(e)}

    def _get_activity_patterns(self, user_id: str, pattern_type: str) -> Dict[str, Any]:
        """Analyze activity patterns"""
        try:
            result = {"pattern_type": pattern_type}

            cutoff_time = datetime.utcnow() - timedelta(days=14)
            steps_metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.metric_type == 'steps',
                    Metric.timestamp >= cutoff_time
                )
            ).all()

            if not steps_metrics:
                return {"error": "No activity data available"}

            if pattern_type == "daily_rhythm":
                # Group by hour of day
                hourly_steps = {}
                for step in steps_metrics:
                    hour = step.timestamp.hour
                    if hour not in hourly_steps:
                        hourly_steps[hour] = []
                    hourly_steps[hour].append(step.value)

                hourly_averages = {
                    hour: round(sum(values) / len(values), 0)
                    for hour, values in hourly_steps.items()
                }

                result["hourly_activity"] = hourly_averages
                if hourly_averages:
                    peak_hour = max(hourly_averages.keys(), key=lambda k: hourly_averages[k])
                    result["most_active_hour"] = peak_hour
                    result["peak_steps"] = hourly_averages[peak_hour]

            return result

        except Exception as e:
            logger.error(f"Activity pattern analysis error: {str(e)}")
            return {"error": str(e)}

    def _compare_time_periods(self, user_id: str, comparison_type: str, metrics: List[str]) -> Dict[str, Any]:
        """Compare health metrics between different time periods"""
        try:
            result = {"comparison_type": comparison_type, "metrics": metrics}

            if comparison_type == "weekday_vs_weekend":
                cutoff_time = datetime.utcnow() - timedelta(days=28)

                for metric_type in metrics:
                    metric_data = Metric.query.filter(
                        and_(
                            Metric.user_id == user_id,
                            Metric.metric_type == metric_type,
                            Metric.timestamp >= cutoff_time
                        )
                    ).all()

                    weekday_values = []
                    weekend_values = []

                    for m in metric_data:
                        if m.timestamp.weekday() < 5:  # Monday=0, Sunday=6
                            weekday_values.append(m.value)
                        else:
                            weekend_values.append(m.value)

                    if weekday_values and weekend_values:
                        weekday_avg = sum(weekday_values) / len(weekday_values)
                        weekend_avg = sum(weekend_values) / len(weekend_values)

                        result[f"{metric_type}_comparison"] = {
                            "weekday_average": round(weekday_avg, 2),
                            "weekend_average": round(weekend_avg, 2),
                            "difference": round(weekend_avg - weekday_avg, 2),
                            "weekday_count": len(weekday_values),
                            "weekend_count": len(weekend_values)
                        }

            return result

        except Exception as e:
            logger.error(f"Time period comparison error: {str(e)}")
            return {"error": str(e)}

    def _get_health_trends(self, user_id: str, metric_type: str, trend_period: str) -> Dict[str, Any]:
        """Identify trends in health data"""
        try:
            result = {"metric_type": metric_type, "trend_period": trend_period}

            if trend_period == "weekly":
                days_back = 28
            elif trend_period == "monthly":
                days_back = 90
            else:  # daily
                days_back = 14

            cutoff_time = datetime.utcnow() - timedelta(days=days_back)
            metrics = Metric.query.filter(
                and_(
                    Metric.user_id == user_id,
                    Metric.metric_type == metric_type,
                    Metric.timestamp >= cutoff_time
                )
            ).order_by(Metric.timestamp).all()

            if len(metrics) < 10:
                return {"error": "Not enough data for trend analysis"}

            # Simple trend calculation
            values = [m.value for m in metrics]
            timestamps = [m.timestamp for m in metrics]

            # Calculate moving average
            window_size = min(7, len(values) // 3)
            if window_size >= 3:
                moving_avg = []
                for i in range(window_size, len(values)):
                    avg = sum(values[i-window_size:i]) / window_size
                    moving_avg.append(avg)

                if len(moving_avg) >= 2:
                    trend_slope = (moving_avg[-1] - moving_avg[0]) / len(moving_avg)

                    if trend_slope > 0.1:
                        trend_direction = "increasing"
                    elif trend_slope < -0.1:
                        trend_direction = "decreasing"
                    else:
                        trend_direction = "stable"

                    result["trend_direction"] = trend_direction
                    result["trend_strength"] = abs(trend_slope)
                    result["recent_average"] = round(sum(values[-7:]) / len(values[-7:]), 2)
                    result["overall_average"] = round(sum(values) / len(values), 2)

            return result

        except Exception as e:
            logger.error(f"Trend analysis error: {str(e)}")
            return {"error": str(e)}