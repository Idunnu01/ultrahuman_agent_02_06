"""
Daily report generation tasks - the core 4 AM intelligence delivery
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from app.models import User, DailyReport
from services.statistical_analyzer import StatisticalAnalyzer
from services.llm_service import LLMService
from services.sms_service import SMSService
from services.learning_service import LearningService
from utils.database import db

logger = logging.getLogger(__name__)

def serialize_datetime(obj):
    """Helper: JSON-safe serialization for nested structures w/ numpy & pandas."""
    # Primitives first
    if obj is None or isinstance(obj, (str, bool, int, float)):
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return None
        return obj

    # Datetime / Timedelta
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return obj.total_seconds()

    # Numpy scalars
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if (np.isnan(obj) or np.isinf(obj)) else float(obj)

    # Pandas timestamp/timedelta scalars
    try:
        if isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return obj.isoformat() if isinstance(obj, pd.Timestamp) else obj.total_seconds()
    except Exception:
        pass

    # Arrays / Series / Frames
    if isinstance(obj, np.ndarray):
        return [serialize_datetime(x) for x in obj.tolist()]
    if isinstance(obj, pd.Series):
        return {k: serialize_datetime(v) for k, v in obj.to_dict().items()}
    if isinstance(obj, pd.DataFrame):
        return {k: serialize_datetime(v) for k, v in obj.to_dict('index').items()}

    # Containers
    if isinstance(obj, dict):
        return {serialize_datetime(k): serialize_datetime(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [serialize_datetime(x) for x in obj]

    # As a last resort, try pandas isna **only for true scalars**
    try:
        if not hasattr(obj, "__len__"):
            if pd.isna(obj):  # scalar only
                return None
    except Exception:
        pass

    # Fallback to string
    return str(obj)

def _pick_text(item):
    if not item:
        return ""
    # Try common fields in your analysis/insight dicts
    for k in ("summary", "text", "message", "insight", "title", "recommendation"):
        v = item.get(k) if isinstance(item, dict) else None
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Fallback: stringify a short slice
    return (str(item)[:140] + "…") if len(str(item)) > 140 else str(item)

def _compose_compact_sms(insights, recommendations, date_str=None):
    """
    Deterministic 2-segment SMS:
    - Prefix: day/status
    - 1–2 bullets of insights
    - 1 bullet of recommendation
    - Nudge to open dashboard
    Hard cap: 306 chars (2 GSM segments).
    """
    prefix = f"Daily health update"
    if date_str:
        prefix += f" ({date_str})"
    bullets = []

    # Top 1–2 insights
    if isinstance(insights, (list, tuple)) and insights:
        i1 = _pick_text(insights[0])
        if i1: bullets.append(f"• {i1}")
        if len(insights) > 1:
            i2 = _pick_text(insights[1])
            if i2: bullets.append(f"• {i2}")

    # Top 1 recommendation
    if isinstance(recommendations, (list, tuple)) and recommendations:
        r1 = _pick_text(recommendations[0])
        if r1: bullets.append(f"→ {r1}")

    # Minimal safety if nothing parsed
    if not bullets:
        bullets = ["• No major changes detected", "→ Keep your routine today"]

    msg = f"{prefix}: " + " ".join(bullets) + " | Open dashboard for details."
    # Enforce 306-char hard cap
    MAX_LEN = 306
    return (msg[:MAX_LEN-1] + "…") if len(msg) > MAX_LEN else msg


def _build_sms_prompt(base_sms: str, insights, recommendations, date_str: str) -> str:
    """
    Constrains the LLM to keep facts exact and structure consistent.
    We pass the compact, deterministic SMS as an anchor and allow only light rewording.
    """
    return f"""You are composing a concise SMS (<= 306 chars total).
Goal: Rephrase the BASE SMS with clear wording, keep all facts, include 1–2 insights + 1 recommendation, and end with 'Open dashboard for details.'

RULES:
- Do not fabricate metrics or numbers.
- Keep total length <= 306 characters (hard cap).
- Keep tone neutral, professional, no emojis.
- Do not add new bullets; preserve the content from BASE SMS.
- Prefer: '• ' for insights, '→ ' for the recommendation.
- Include the date if present.

DATE: {date_str}

BASE SMS:
{base_sms}
"""


def _pick_text(item):
    if not item:
        return ""
    # Try common fields in your analysis/insight dicts
    for k in ("summary", "text", "message", "insight", "title", "recommendation"):
        v = item.get(k) if isinstance(item, dict) else None
        if isinstance(v, str) and v.strip():
            return v.strip()
    # Fallback: stringify a short slice
    return (str(item)[:140] + "…") if len(str(item)) > 140 else str(item)

def _compose_compact_sms(insights, recommendations, date_str=None):
    """
    Deterministic 2-segment SMS:
    - Prefix: day/status
    - 1–2 bullets of insights
    - 1 bullet of recommendation
    - Nudge to open dashboard
    Hard cap: 306 chars (2 GSM segments).
    """
    prefix = f"Daily health update"
    if date_str:
        prefix += f" ({date_str})"
    bullets = []

    # Top 1–2 insights
    if isinstance(insights, (list, tuple)) and insights:
        i1 = _pick_text(insights[0])
        if i1: bullets.append(f"• {i1}")
        if len(insights) > 1:
            i2 = _pick_text(insights[1])
            if i2: bullets.append(f"• {i2}")

    # Top 1 recommendation
    if isinstance(recommendations, (list, tuple)) and recommendations:
        r1 = _pick_text(recommendations[0])
        if r1: bullets.append(f"→ {r1}")

    # Minimal safety if nothing parsed
    if not bullets:
        bullets = ["• No major changes detected", "→ Keep your routine today"]

    msg = f"{prefix}: " + " ".join(bullets) + " | Open dashboard for details."
    # Enforce 306-char hard cap
    MAX_LEN = 306
    return (msg[:MAX_LEN-1] + "…") if len(msg) > MAX_LEN else msg

def generate_daily_report(user_id: str, report_date: str = None) -> Dict:
    """Generate daily health report for a specific user"""

    try:
        # Parse report date
        if report_date:
            target_date = datetime.fromisoformat(report_date).date()
        else:
            target_date = datetime.utcnow().date()

        logger.info(f"Generating daily report for user {user_id}, date {target_date}")

        # Get user
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return {'error': f'User {user_id} not found or inactive'}

        # Check if report already exists
        existing_report = DailyReport.query.filter_by(
            user_id=user_id, report_date=target_date
        ).first()

        if existing_report and existing_report.sms_sent:
            logger.info(f"Report already exists and sent for user {user_id}, date {target_date}")
            return {'success': True, 'status': 'already_exists', 'report_id': existing_report.id}


        # Initialize services
        analyzer = StatisticalAnalyzer()
        llm_service = LLMService()
        sms_service = SMSService()
        learning_service = LearningService()

        # 1. Run comprehensive statistical analysis
        analysis_timeframe = timedelta(days=7)  # Analyze last 7 days
        analysis_results = analyzer.run_comprehensive_analysis(user_id, analysis_timeframe)

        if 'error' in analysis_results and not analysis_results.get('baseline_statistics'):
            logger.error(f"Statistical analysis failed for user {user_id}: {analysis_results['error']}")
            return {'error': f"Analysis failed: {analysis_results['error']}"}

        # 2. Extract key insights
        insights = _extract_key_insights(analysis_results)

        # 3. Generate personalized recommendations
        recommendations = _generate_recommendations(user_id, analysis_results, learning_service)

        # 4. Create daily summary
        daily_summary = _create_daily_summary(analysis_results, target_date)

        # 5. Generate LLM-powered insights
        try:
            llm_insights = llm_service.generate_health_analysis(
                metrics_data=daily_summary,
                statistical_analysis=analysis_results,
                user_context=_get_user_context(user)
            )
            if llm_insights:
                llm_insights = serialize_datetime(llm_insights)
        except Exception as e:
            logger.warning(f"LLM insights failed: {str(e)}, using fallback")
            llm_insights = _generate_fallback_insights(analysis_results)

        # 6. Create SMS report (LLM is ALWAYS involved)
        # Step 1: Compose deterministic draft (anchor content)
        base_sms = _compose_compact_sms(
            insights, recommendations, target_date.isoformat()
        )

        # Step 2: Ask the primary LLM to polish (strictly within constraints)
        sms_content = None
        prompt = _build_sms_prompt(base_sms, insights, recommendations, target_date.isoformat())
        try:
            # Primary LLM — keep it stable and compact
            sms_resp = llm_service.generate_sms_response(prompt, max_length=306)
            sms_content = sms_resp.content if hasattr(sms_resp, "content") else str(sms_resp)

            # Validate that we got a real response, not a prompt echo
            if sms_content and "You are composing" in sms_content:
                logger.warning("LLM returned prompt instructions instead of SMS content")
                sms_content = None

        except Exception as e:
            logger.warning(f"Primary LLM polish failed: {e}")

        # Step 3: Enhanced SMS with semantic context (priority fallback)
        if not sms_content or not isinstance(sms_content, str) or not sms_content.strip():
            try:
                logger.info("Using enhanced SMS with semantic context and health data")
                from services.enhanced_sms_service import EnhancedSMSService
                enhanced_sms_service = EnhancedSMSService()
                sms_content = enhanced_sms_service.generate_super_rich_sms(analysis_results, user_id, target_date.isoformat())
            except Exception as e:
                logger.warning(f"Enhanced SMS failed, falling back to rich analysis: {e}")
                # Fallback to your existing rich analysis
                try:
                    sms_content = _generate_rich_analysis_sms(analysis_results, user_id, target_date.isoformat())
                except Exception as e2:
                    logger.warning(f"Rich analysis SMS also failed: {e2}")

        # Step 4: Fallback to minimal LLM if needed (still an LLM path)
        if not sms_content or not isinstance(sms_content, str) or not sms_content.strip():
            try:
                from services.minimal_llm_service import MinimalLLMService
                minimal = MinimalLLMService()
                sms_content = minimal.generate(prompt, max_length=306)
            except Exception as e:
                logger.warning(f"Minimal LLM fallback failed: {e}")

        # Step 5: Final fallback to basic SMS
        if not sms_content or not isinstance(sms_content, str) or not sms_content.strip():
            sms_content = _generate_fallback_sms(insights, recommendations)

        # Enforce the 306-char cap defensively
        if len(sms_content) > 306:
            sms_content = sms_content[:305] + "…"


        # 7. Store report in database
        insights_serialized = serialize_datetime(insights)
        anomalies_serialized = serialize_datetime(analysis_results.get('anomaly_detection', {}))
        correlations_serialized = serialize_datetime(analysis_results.get('correlation_analysis', {}))
        trends_serialized = serialize_datetime(analysis_results.get('trend_analysis', {}))
        predictions_serialized = serialize_datetime(_generate_predictions(user_id, analysis_results))
        recommendations_serialized = serialize_datetime(recommendations)

        statistical_summary = {
            'confidence_score': analysis_results.get('confidence_assessments', {}).get('overall_confidence', 0.5),
            'data_quality': analysis_results.get('data_summary', {}).get('data_quality', {}),
            'analysis_methods': list(analysis_results.keys())
        }

        confidence_scores = {
            'overall': analysis_results.get('confidence_assessments', {}).get('overall_confidence', 0.5),
            'insights': 0.8 if insights else 0.0,
            'recommendations': 0.7 if recommendations else 0.0
        }

        # Create or update report
        if existing_report:
            existing_report.insights = insights_serialized
            existing_report.anomalies = anomalies_serialized
            existing_report.correlations = correlations_serialized
            existing_report.trends = trends_serialized
            existing_report.predictions = predictions_serialized
            existing_report.recommendations = recommendations_serialized
            existing_report.statistical_summary = statistical_summary
            existing_report.confidence_scores = confidence_scores
            existing_report.sms_content = sms_content
            existing_report.generated_at = datetime.utcnow()
            report = existing_report
        else:
            report = DailyReport(
                user_id=user_id,
                report_date=target_date,
                insights=insights_serialized,
                anomalies=anomalies_serialized,
                correlations=correlations_serialized,
                trends=trends_serialized,
                predictions=predictions_serialized,
                recommendations=recommendations_serialized,
                statistical_summary=statistical_summary,
                confidence_scores=confidence_scores,
                sms_content=sms_content,
                sms_sent=False
            )
            db.session.add(report)

        db.session.commit()

        # 8. Send SMS (optional - can be done separately)
        try:
            if user.phone_number and sms_content:
                sms_result = sms_service.send_sms(
                    user_id=user_id,
                    phone_number=user.phone_number,
                    message=sms_content,
                    message_type='daily_report'
                )
                if sms_result.get('success'):
                    report.sms_sent = True
                    report.sms_sent_at = datetime.utcnow()
                    db.session.commit()
                    logger.info(f"SMS sent successfully for user {user_id}")
                else:
                    logger.warning(f"SMS failed for user {user_id}: {sms_result.get('error')}")
        except Exception as e:
            logger.warning(f"SMS sending failed for user {user_id}: {str(e)}")

        return {
            'success': True,
            'report_id': report.id,
            'insights_count': len(insights),
            'recommendations_count': len(recommendations),
            'sms_sent': report.sms_sent
        }

    except Exception as e:
        logger.error(f"Daily report generation failed for user {user_id}: {str(e)}")
        return {'error': str(e)}

def _extract_key_insights(analysis_results: Dict) -> List[Dict]:
    """Extract key insights from analysis results"""
    insights = []

    try:
        # Extract correlation insights
        correlations = analysis_results.get('correlation_analysis', {})
        for corr_name, corr_data in correlations.items():
            if isinstance(corr_data, dict) and 'correlation_coefficient' in corr_data:
                coef = corr_data['correlation_coefficient']
                p_value = corr_data.get('p_value', 1.0)

                if abs(coef) > 0.5 and p_value < 0.05:
                    insights.append({
                        'type': 'correlation',
                        'message': f"Strong correlation found: {corr_name} (r={coef:.2f})",
                        'confidence': 1 - p_value,
                        'data': corr_data
                    })

        # Extract anomaly insights
        anomalies = analysis_results.get('anomaly_detection', {})
        for metric, anomaly_data in anomalies.items():
            if isinstance(anomaly_data, dict) and 'anomalies' in anomaly_data:
                anomaly_count = len(anomaly_data['anomalies'])
                if anomaly_count > 0:
                    insights.append({
                        'type': 'anomaly',
                        'message': f"{anomaly_count} anomalies detected in {metric}",
                        'confidence': 0.8,
                        'data': anomaly_data
                    })

        # Extract trend insights
        trends = analysis_results.get('trend_analysis', {})
        for metric, trend_data in trends.items():
            if isinstance(trend_data, dict) and 'trend_interpretation' in trend_data:
                direction = trend_data['trend_interpretation'].get('direction', 'stable')
                if direction != 'stable':
                    insights.append({
                        'type': 'trend',
                        'message': f"{metric} showing {direction} trend",
                        'confidence': 0.7,
                        'data': trend_data
                    })

    except Exception as e:
        logger.warning(f"Insight extraction failed: {str(e)}")
        insights = [{'type': 'error', 'message': 'Insight extraction failed', 'confidence': 0.0}]

    return insights

def _generate_recommendations(user_id: str, analysis_results: Dict, learning_service: LearningService) -> List[Dict]:
    """Generate personalized recommendations"""
    recommendations = []

    try:
        hrv_data = analysis_results.get('baseline_statistics', {}).get('hrv', {})
        if hrv_data and hrv_data.get('mean', 0) < 30:
            recommendations.append({
                'type': 'recovery',
                'priority': 'high',
                'message': 'Your HRV is below optimal levels. Consider: earlier bedtime, stress reduction, and avoiding late meals.',
                'actionable': True
            })

        sleep_data = analysis_results.get('baseline_statistics', {}).get('sleep_score', {})
        if sleep_data and sleep_data.get('mean', 0) < 70:
            recommendations.append({
                'type': 'sleep',
                'priority': 'high',
                'message': 'Sleep quality could improve. Try: consistent bedtime, cool room temperature, and avoiding screens 1 hour before bed.',
                'actionable': True
            })

        activity_data = analysis_results.get('baseline_statistics', {}).get('active_minutes', {})
        if activity_data and activity_data.get('mean', 0) < 30:
            recommendations.append({
                'type': 'activity',
                'priority': 'medium',
                'message': 'Consider increasing daily activity. Aim for at least 30 minutes of moderate exercise.',
                'actionable': True
            })

    except Exception as e:
        logger.warning(f"Recommendation generation failed: {str(e)}")
        recommendations = [{'type': 'error', 'message': 'Recommendation generation failed', 'priority': 'low'}]

    return recommendations

def _create_daily_summary(analysis_results: Dict, target_date: datetime) -> Dict:
    """Create daily summary from analysis results"""
    try:
        summary = {
            'date': target_date.isoformat(),
            'metrics_analyzed': list(analysis_results.get('baseline_statistics', {}).keys()),
            'insights_count': len(analysis_results.get('anomaly_detection', {})),
            'correlations_found': len(analysis_results.get('correlation_analysis', {})),
            'trends_identified': len(analysis_results.get('trend_analysis', {}))
        }

        baseline_stats = analysis_results.get('baseline_statistics', {})
        for metric, stats in baseline_stats.items():
            if isinstance(stats, dict) and 'mean' in stats:
                summary[f'{metric}_current'] = stats['mean']
                summary[f'{metric}_trend'] = stats.get('trend', 'stable')

        return summary

    except Exception as e:
        logger.warning(f"Daily summary creation failed: {str(e)}")
        return {'date': target_date.isoformat(), 'error': 'Summary creation failed'}

def _get_user_context(user: User) -> Dict:
    """Get user context for analysis"""
    try:
        return {
            'user_id': user.id,
            'age': getattr(user, 'age', None),
            'gender': getattr(user, 'gender', None),
            'activity_level': getattr(user, 'activity_level', 'moderate'),
            'health_goals': getattr(user, 'health_goals', []),
            'preferences': getattr(user, 'preferences', {})
        }
    except Exception as e:
        logger.warning(f"User context extraction failed: {str(e)}")
        return {'user_id': user.id}

def _generate_predictions(user_id: str, analysis_results: Dict) -> List[Dict]:
    """Generate health predictions based on analysis"""
    predictions = []

    try:
        trends = analysis_results.get('trend_analysis', {})
        for metric, trend_data in trends.items():
            if isinstance(trend_data, dict) and 'linear_trend' in trend_data:
                direction = trend_data['linear_trend'].get('direction', 'stable')
                if direction == 'improving':
                    predictions.append({
                        'metric': metric,
                        'prediction': 'Continued improvement expected',
                        'confidence': 0.7,
                        'timeframe': '1 week'
                    })
                elif direction == 'declining':
                    predictions.append({
                        'metric': metric,
                        'prediction': 'Decline may continue without intervention',
                        'confidence': 0.6,
                        'timeframe': '1 week'
                    })

    except Exception as e:
        logger.warning(f"Prediction generation failed: {str(e)}")
        predictions = []

    return predictions

def _generate_fallback_insights(analysis_results: Dict) -> str:
    """Generate fallback insights when LLM fails"""
    try:
        insights = []
        baseline_stats = analysis_results.get('baseline_statistics', {})
        for metric, stats in baseline_stats.items():
            if isinstance(stats, dict) and 'mean' in stats:
                mean_val = stats['mean']
                if metric == 'hrv' and mean_val < 30:
                    insights.append("Low HRV detected - focus on recovery")
                elif metric == 'sleep_score' and mean_val < 70:
                    insights.append("Sleep quality needs improvement")
                elif metric == 'active_minutes' and mean_val < 30:
                    insights.append("Activity level below recommendations")

        if insights:
            return " | ".join(insights)
        else:
            return "Health data analyzed successfully. Continue monitoring for patterns."

    except Exception as e:
        logger.warning(f"Fallback insight generation failed: {str(e)}")
        return "Health analysis completed. Monitor your metrics for insights."


def _generate_rich_analysis_sms(analysis_results, user_id, report_date):
    """Generate rich SMS using actual health analysis data"""
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
        result = "\n".join(message_parts)

        if len(result) > 306:
            # Simple truncation
            lines = result.split("\n")
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
                result = header + "\n" + "\n".join(content_lines) + "\n" + ending
            else:
                result = header + "\n📊 Rich analysis ready\n" + ending

        return result

    except Exception as e:
        # Safe fallback
        try:
            date_str = datetime.now().strftime("%b %d")
            return "🌅 Daily Health - " + date_str + "\n📊 Comprehensive analysis complete\n💪 Personalized insights available\nOpen dashboard for details."
        except:
            return "🌅 Daily Health Update\n📊 Your health metrics analyzed\n💪 Rich insights in dashboard\nOpen dashboard for details."


def _generate_rich_analysis_sms(analysis_results, user_id, report_date) -> str:
    """Generate fallback SMS when LLM fails"""
    try:
        message_parts = []

        if insights:
            message_parts.append(f"📊 {len(insights)} insights found")

        if recommendations:
            message_parts.append(f"💡 {len(recommendations)} recommendations")

        if message_parts:
            return " | ".join(message_parts) + " | Check your dashboard for details 📱"
        else:
            return "📊 Daily health report ready! Check your dashboard for insights 📱"

    except Exception as e:
        logger.warning(f"Fallback SMS generation failed: {str(e)}")
        return "📊 Daily health report completed! 📱"

def _generate_fallback_sms(insights_list: List = None, recommendations_list: List = None) -> str:
    """Generate fallback SMS when LLM fails"""
    try:
        # Basic health-focused templates
        templates = [
            "🔥 Keep tracking! Your consistency helps identify important health patterns ⭐",
            "📈 Data logged! Regular monitoring helps optimize your health journey 🎯",
            "💪 Health snapshot ready! Check your dashboard for personalized insights ✨",
            "🌟 Another day tracked! Small consistent steps lead to big health wins 🚀",
            "📊 Metrics updated! Your dedication to health tracking is paying off 💎"
        ]

        # Simple rotation based on current time
        import random
        template = random.choice(templates)

        # Ensure it fits SMS length limit
        if len(template) > 306:
            template = template[:300] + "..."

        return template

    except Exception as e:
        # Ultimate fallback
        return "🔥 Daily health check complete! Keep up the great work tracking your wellness journey ⭐"

def _generate_rich_analysis_sms(analysis_results, user_id, report_date):
    """Generate rich SMS using actual health analysis data"""
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
        # Safe fallback
        try:
            date_str = datetime.now().strftime("%b %d")
            return "🌅 Daily Health - " + date_str + "\\n📊 Comprehensive analysis complete\\n💪 Personalized insights available\\nOpen dashboard for details."
        except:
            return "🌅 Daily Health Update\\n📊 Your health metrics analyzed\\n💪 Rich insights in dashboard\\nOpen dashboard for details."

def generate_all_daily_reports():
    """Generate daily reports for all active users"""
    try:
        logger.info("Starting daily reports generation")

        users = User.query.filter_by(is_active=True).all()

        if not users:
            logger.info("No active users found")
            return {'status': 'no_users'}

        results = {
            'total_users': len(users),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        for user in users:
            try:
                result = generate_daily_report(user.id)
                if result.get('success'):
                    results['successful'] += 1
                    logger.info(f"Daily report generated successfully for user {user.id}")
                else:
                    results['failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    results['errors'].append(f"User {user.id}: {error_msg}")
                    logger.error(f"Daily report failed for user {user.id}: {error_msg}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"User {user.id}: {str(e)}")
                logger.error(f"Daily report generation failed for user {user.id}: {str(e)}")

        success_rate = (results['successful'] / results['total_users']) * 100 if results['total_users'] > 0 else 0

        logger.info(f"Daily reports completed. Success rate: {success_rate:.1f}%")
        logger.info(f"Successful: {results['successful']}, Failed: {results['failed']}")

        return results

    except Exception as e:
        logger.error(f"Daily reports generation failed: {str(e)}")
        return {'error': str(e)}

if __name__ == "__main__":
    # Test the daily report generation
    result = generate_all_daily_reports()
    print(json.dumps(result, indent=2, default=str))
