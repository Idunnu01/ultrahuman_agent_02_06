"""
Enhanced SMS Service with Semantic Context
Combines your existing rich analysis with semantic health insights
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from services.semantic_health_service import SemanticHealthService

logger = logging.getLogger(__name__)

class EnhancedSMSService:
    """Enhanced SMS service that combines statistical analysis with semantic context"""

    def __init__(self):
        try:
            self.semantic_service = SemanticHealthService()
            self.semantic_enabled = True
            logger.info("Enhanced SMS service initialized with semantic capabilities")
        except Exception as e:
            logger.warning(f"Semantic service unavailable, falling back to basic mode: {str(e)}")
            self.semantic_service = None
            self.semantic_enabled = False

    def generate_super_rich_sms(self, analysis_results: Dict, user_id: str, report_date: str) -> str:
        """Generate super rich SMS combining statistical analysis + semantic context"""

        try:
            # Start with your existing rich analysis SMS
            base_sms = self._generate_base_rich_sms(analysis_results, user_id, report_date)

            # Add semantic context if available
            if self.semantic_enabled and self.semantic_service:
                semantic_context = self.semantic_service.get_historical_context(analysis_results, user_id)
                enhanced_sms = self._add_semantic_context(base_sms, semantic_context, analysis_results)
                return enhanced_sms

            return base_sms

        except Exception as e:
            logger.error(f"Enhanced SMS generation failed: {str(e)}")
            # Fallback to basic rich SMS
            return self._generate_base_rich_sms(analysis_results, user_id, report_date)

    def _generate_base_rich_sms(self, analysis_results: Dict, user_id: str, report_date: str) -> str:
        """Your existing rich SMS generation logic"""
        from datetime import datetime

        try:
            message_parts = []

            # Header with date
            if isinstance(report_date, str):
                try:
                    date_obj = datetime.strptime(report_date, '%Y-%m-%d')
                except:
                    date_obj = datetime.now()
            else:
                date_obj = report_date

            date_str = date_obj.strftime("%b %d")
            message_parts.append("🌅 Daily Health - " + date_str)

            # Extract data from analysis results
            baseline_stats = analysis_results.get('baseline_statistics', {})
            correlations = analysis_results.get('correlations', {})
            insights = analysis_results.get('insights', {})

            # Add key metrics with percentage changes
            metrics_added = 0
            if baseline_stats and isinstance(baseline_stats, dict):
                for metric_name, stats in baseline_stats.items():
                    if metrics_added >= 2:
                        break

                    if isinstance(stats, dict):
                        latest = stats.get('latest_value')
                        mean = stats.get('mean')

                        if latest is not None and mean is not None and mean != 0:
                            diff_pct = int((latest - mean) / mean * 100)

                            if abs(diff_pct) > 5:  # Significant change
                                direction = "↗️" if diff_pct > 0 else "↘️"
                                metric_display = metric_name.replace('_', ' ').title()

                                if 'sleep' in metric_name.lower():
                                    message_parts.append("💤 " + metric_display + ": " + direction + " " + str(abs(diff_pct)) + "%")
                                    metrics_added += 1
                                elif 'hrv' in metric_name.lower():
                                    message_parts.append("❤️ " + metric_display + ": " + direction + " " + str(abs(diff_pct)) + "%")
                                    metrics_added += 1
                                elif 'recovery' in metric_name.lower():
                                    message_parts.append("🏃 " + metric_display + ": " + direction + " " + str(abs(diff_pct)) + "%")
                                    metrics_added += 1

            # Add significant correlation
            if correlations and isinstance(correlations, dict):
                for corr_name, corr_data in correlations.items():
                    if isinstance(corr_data, dict):
                        corr_val = corr_data.get('correlation', 0)
                        significant = corr_data.get('significant', False)

                        if significant and abs(corr_val) > 0.4:
                            corr_display = corr_name.replace('_', ' ').title()
                            corr_pct = int(abs(corr_val) * 100)

                            if corr_val > 0:
                                message_parts.append("🔍 " + corr_display + ": +" + str(corr_pct) + "% link")
                            else:
                                message_parts.append("🔍 " + corr_display + ": -" + str(corr_pct) + "% inverse")
                            break

            # Add key insight
            if insights and isinstance(insights, dict):
                key_insights = insights.get('key_insights', [])
                if key_insights and len(key_insights) > 0:
                    insight = str(key_insights[0])
                    if len(insight) < 60:
                        message_parts.append("💡 " + insight)

            # Fallback if no rich content
            if len(message_parts) == 1:
                message_parts.append("📊 Health metrics analyzed")
                if baseline_stats:
                    message_parts.append("💪 " + str(len(baseline_stats)) + " metrics tracked")

            message_parts.append("Open dashboard for details.")

            # Join and check length
            result = "\\n".join(message_parts)

            if len(result) > 306:
                # Simple truncation
                lines = result.split("\\n")
                header = lines[0]
                ending = "Open dashboard for details."

                # Keep header, some content, and ending
                available = 306 - len(header) - len(ending) - 4
                content_lines = []
                current_len = 0

                for line in lines[1:-1]:
                    if current_len + len(line) < available:
                        content_lines.append(line)
                        current_len += len(line) + 1
                    else:
                        break

                if content_lines:
                    result = header + "\\n" + "\\n".join(content_lines) + "\\n" + ending
                else:
                    result = header + "\\n📊 Rich analysis ready\\n" + ending

            return result

        except Exception as e:
            logger.error(f"Base rich SMS generation failed: {str(e)}")
            # Ultimate fallback
            try:
                date_str = datetime.now().strftime("%b %d")
                return "🌅 Daily Health - " + date_str + "\\n📊 Comprehensive analysis complete\\n💪 Personalized insights available\\nOpen dashboard for details."
            except:
                return "🌅 Daily Health Update\\n📊 Your health metrics analyzed\\n💪 Rich insights in dashboard\\nOpen dashboard for details."

    def _add_semantic_context(self, base_sms: str, semantic_context: Dict, analysis_results: Dict) -> str:
        """Add semantic context to base SMS"""

        try:
            lines = base_sms.split("\\n")
            header = lines[0]
            ending = "Open dashboard for details."
            content_lines = lines[1:-1]  # Remove header and ending

            # Add semantic insights
            semantic_additions = []

            # 1. Add historical context for similar periods
            similar_periods = semantic_context.get('similar_periods', [])
            if similar_periods:
                best_period = similar_periods[0]
                period_date = best_period['event_date']
                if isinstance(period_date, datetime):
                    period_text = period_date.strftime("%b %Y")
                    # Check if we have room
                    test_addition = f"📈 Similar to {period_text} patterns"
                    if len("\\n".join([header] + content_lines + [test_addition, ending])) <= 306:
                        semantic_additions.append(test_addition)

            # 2. Add successful intervention context
            interventions = semantic_context.get('successful_interventions', [])
            if interventions and not semantic_additions:  # Only if we didn't add period context
                top_intervention = interventions[0]
                structured = top_intervention.get('interventions', {})
                supplements = structured.get('supplements', [])

                if supplements:
                    supp_name = supplements[0].get('name', '').lower()
                    if 'magnesium' in supp_name:
                        intervention_text = "💊 Evening magnesium helped similar patterns"
                    elif 'vitamin' in supp_name:
                        intervention_text = f"💊 {supp_name.title()} helped before"
                    else:
                        intervention_text = "💊 Past intervention available"

                    # Check if we have room
                    if len("\\n".join([header] + content_lines + [intervention_text, ending])) <= 306:
                        semantic_additions.append(intervention_text)

            # 3. Add correlation context from semantic search
            if not semantic_additions:  # Only if nothing else added
                correlation_contexts = semantic_context.get('correlation_contexts', {})
                for corr_name, contexts in correlation_contexts.items():
                    if contexts:
                        context = contexts[0]
                        if 'magnesium' in context['description'].lower():
                            context_text = "💡 Magnesium timing matters"
                            if len("\\n".join([header] + content_lines + [context_text, ending])) <= 306:
                                semantic_additions.append(context_text)
                                break

            # Combine everything
            final_lines = [header] + content_lines + semantic_additions + [ending]
            enhanced_sms = "\\n".join(final_lines)

            # Final length check
            if len(enhanced_sms) > 306:
                # Remove semantic additions and use base SMS
                return base_sms

            return enhanced_sms

        except Exception as e:
            logger.error(f"Failed to add semantic context: {str(e)}")
            return base_sms

    def process_health_note(self, user_id: str, description: str) -> Dict[str, Any]:
        """Process natural language health note"""

        if not self.semantic_enabled or not self.semantic_service:
            return {
                'success': False,
                'error': 'Semantic service not available'
            }

        try:
            result = self.semantic_service.process_health_event(user_id, description)

            if result.get('success'):
                logger.info(f"Processed health note for {user_id}: {description[:50]}...")

                return {
                    'success': True,
                    'event_id': result['event_id'],
                    'structured_data': result['structured_data'],
                    'tags': result['tags'],
                    'message': 'Health event processed and stored with semantic embedding'
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Failed to process health note: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def search_health_patterns(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Search health patterns using natural language"""

        if not self.semantic_enabled or not self.semantic_service:
            return []

        try:
            results = self.semantic_service.semantic_search(query, user_id, limit=10)

            logger.info(f"Found {len(results)} patterns for query: {query[:50]}...")

            return results

        except Exception as e:
            logger.error(f"Health pattern search failed: {str(e)}")
            return []