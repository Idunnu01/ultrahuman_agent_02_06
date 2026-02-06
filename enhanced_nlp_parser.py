#!/usr/bin/env python3
"""
Enhanced NLP Parser - Combines new metric parsing with proven date parsing
"""

import re
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from dateutil import parser
import pytz

UTC = pytz.utc

def _floor_midnight(dt: datetime) -> datetime:
    """Return dt at 00:00 UTC."""
    return dt.astimezone(UTC).replace(hour=0, minute=0, second=0,
                                      microsecond=0, tzinfo=UTC)

@dataclass
class ParsedQuery:
    """Structured representation of a parsed health query"""
    metric_type: str
    aggregation: str
    time_period: str
    time_period_days: int
    query_type: str
    confidence: float
    raw_query: str
    extracted_entities: Dict
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    secondary_metric: Optional[str] = None

class EnhancedHealthQueryParser:
    """Enhanced parser using proven date parsing + metric detection"""

    def __init__(self):
        # Proven metric aliases from existing system
        self.metric_aliases = {
            # Heart rate variations
            'heart rate': 'heart_rate',
            'hr': 'heart_rate',
            'heartrate': 'heart_rate',
            'pulse': 'heart_rate',
            'bpm': 'heart_rate',
            'beats per minute': 'heart_rate',
            'cardiac rate': 'heart_rate',

            # HRV variations
            'hrv': 'hrv',
            'heart rate variability': 'hrv',
            'variability': 'hrv',
            'rr interval': 'hrv',

            # Sleep variations
            'sleep': 'sleep_score',
            'sleep score': 'sleep_score',
            'sleep quality': 'sleep_score',
            'sleep rating': 'sleep_score',
            'rest': 'sleep_score',
            'rest quality': 'sleep_score',

            # Temperature variations
            'temperature': 'temperature',
            'temp': 'temperature',
            'body temp': 'temperature',
            'body temperature': 'temperature',
            'fever': 'temperature',

            # Recovery variations
            'recovery': 'recovery',
            'recovery score': 'recovery',
            'readiness': 'recovery',
            'readiness score': 'recovery',

            # Steps variations
            'steps': 'steps',
            'step count': 'steps',
            'walking': 'steps',

            # Calories variations
            'calories': 'calories_burned',
            'calories burned': 'calories_burned',
            'energy': 'calories_burned',
            'calories burnt': 'calories_burned',
            'kcal': 'calories_burned',

            # Stress variations
            'stress': 'stress',
            'stress level': 'stress',
            'stress score': 'stress',
            'anxiety': 'stress',

            # Active minutes variations
            'active minutes': 'active_minutes',
            'activity minutes': 'active_minutes',
            'exercise time': 'active_minutes',
            'workout time': 'active_minutes',

            # Glucose variations
            'glucose': 'glucose',
            'blood sugar': 'glucose',
            'sugar': 'glucose',
            'blood glucose': 'glucose',

            # HbA1c variations
            'hba1c': 'hba1c',
            'hb a1c': 'hba1c',
            'hemoglobin a1c': 'hba1c',
            'glycated hemoglobin': 'hba1c',

            # VO2 Max variations
            'vo2 max': 'vo2_max',
            'vo2max': 'vo2_max',
            'cardio fitness': 'vo2_max',
            'aerobic fitness': 'vo2_max'
        }

        # Aggregation patterns
        self.aggregation_patterns = {
            'average': ['average', 'avg', 'mean', 'typical', 'usually', 'overall'],
            'max': ['max', 'maximum', 'highest', 'peak', 'top', 'best', 'high'],
            'min': ['min', 'minimum', 'lowest', 'bottom', 'worst', 'low'],
            'latest': ['latest', 'recent', 'current', 'last', 'now'],
            'trend': ['trend', 'trending', 'pattern', 'direction', 'improving', 'getting better']
        }

    def parse_query(self, query: str) -> ParsedQuery:
        """Enhanced parsing using proven date logic + metric detection"""

        query_lower = query.lower().strip()
        confidence = 0.0

        # 1. Parse metric using proven approach
        metric_type = self._parse_metric(query_lower)
        if metric_type:
            confidence += 0.4
        else:
            metric_type = 'heart_rate'  # Default fallback
            confidence += 0.1

        # 2. Parse aggregation
        aggregation = self._parse_aggregation(query_lower)
        confidence += 0.3 if aggregation != 'average' else 0.1

        # 3. Parse dates using proven logic
        start_date, end_date = self._parse_dates(query_lower)
        time_period_days = self._calculate_days(start_date, end_date)

        if start_date or end_date:
            confidence += 0.3
        else:
            confidence += 0.1
            time_period_days = 7  # Default

        # 4. Format time period
        time_period = self._format_time_period(time_period_days)

        # 5. Determine query type
        query_type = self._determine_query_type(query_lower)

        # 6. Extract entities and secondary metric for correlation queries
        entities = self._extract_entities(query_lower)
        secondary_metric = None

        if query_type == 'correlation':
            secondary_metric = self._parse_secondary_metric(query_lower, metric_type)
            if secondary_metric:
                confidence += 0.2

        return ParsedQuery(
            metric_type=metric_type,
            aggregation=aggregation,
            time_period=time_period,
            time_period_days=time_period_days,
            query_type=query_type,
            confidence=min(confidence, 1.0),
            raw_query=query,
            extracted_entities=entities,
            start_date=start_date,
            end_date=end_date,
            secondary_metric=secondary_metric
        )

    def _parse_metric(self, text: str) -> Optional[str]:
        """Parse metric using proven approach"""
        for alias in sorted(self.metric_aliases.keys(), key=len, reverse=True):
            if alias in text:
                return self.metric_aliases[alias]
        return None

    def _parse_dates(self, text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Proven date parsing logic"""
        today_utc = _floor_midnight(datetime.utcnow())
        yesterday_utc = today_utc - timedelta(days=1)

        # Simple keywords
        if "yesterday" in text:
            return yesterday_utc, None
        if "today" in text or "tonight" in text:
            return today_utc, None
        if "tomorrow" in text:
            return today_utc + timedelta(days=1), None

        # "last X days / past X days"
        m = re.search(r"(?:last|past|over)\s+(\d{1,2})\s?days?", text)
        if m:
            days = int(m.group(1))
            return today_utc - timedelta(days=days), today_utc

        # "last X weeks / past X weeks"
        m = re.search(r"(?:last|past|over)\s+(\d{1,2})\s?weeks?", text)
        if m:
            weeks = int(m.group(1))
            days = weeks * 7
            return today_utc - timedelta(days=days), today_utc

        # Enhanced week parsing (singular)
        if any(phrase in text for phrase in ["last week", "past week", "this week", "over past week"]):
            start = today_utc - timedelta(days=7)
            return start, today_utc

        if "this month" in text or "past month" in text:
            start = today_utc - timedelta(days=30)
            return start, today_utc

        # "recently", "lately"
        if "recently" in text or "lately" in text:
            start = today_utc - timedelta(days=7)
            return start, today_utc

        return None, None

    def _parse_aggregation(self, text: str) -> str:
        """Parse aggregation type"""
        for agg, patterns in self.aggregation_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return agg
        return 'average'  # Default

    def _calculate_days(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> int:
        """Calculate days between dates"""
        if start_date and end_date:
            return (end_date - start_date).days
        elif start_date:
            return 1  # Single day
        else:
            return 7  # Default

    def _format_time_period(self, days: int) -> str:
        """Format time period string"""
        if days == 1:
            return 'day'
        elif days == 7:
            return 'week'
        elif days == 30:
            return 'month'
        elif days < 7:
            return f'{days} days'
        elif days < 30:
            weeks = days // 7
            if weeks == 1:
                return 'week'
            else:
                return f'{weeks} weeks'
        else:
            months = days // 30
            if months == 1:
                return 'month'
            else:
                return f'{months} months'

    def _determine_query_type(self, text: str) -> str:
        """Determine query type"""
        if any(word in text for word in ['vs', 'versus', 'compared to', 'compare']):
            return 'comparison'
        elif any(word in text for word in ['correlation', 'relationship', 'related', 'between', 'and']):
            return 'correlation'
        elif any(word in text for word in ['trend', 'pattern', 'improving', 'getting']):
            return 'trend'
        else:
            return 'metric_query'

    def _extract_entities(self, text: str) -> Dict:
        """Extract additional entities"""
        entities = {}

        if any(word in text for word in ['better', 'worse', 'higher', 'lower']):
            entities['comparison_intent'] = True

        if any(word in text for word in ['workout', 'exercise', 'training']):
            entities['context'] = 'exercise'
        elif any(word in text for word in ['sleep', 'rest', 'night']):
            entities['context'] = 'sleep'

        return entities

    def _parse_secondary_metric(self, text: str, primary_metric: str) -> Optional[str]:
        """Parse secondary metric for correlation queries"""

        # Common correlation patterns - improved to handle more variations
        correlation_patterns = [
            r'correlation between (.+?) and (.+?)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'relationship between (.+?) and (.+?)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'(.+?) and (.+?) correlation(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'(.+?) vs (.+?)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'(.+?) versus (.+?)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'how\s+(?:are\s+)?(.+?)\s+and\s+(.+?)\s+(?:related|correlated)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'(.+?)\s+(?:related\s+to|correlated\s+with)\s+(.+?)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)',
            r'(.+?)\s+vs\s+(.+?)\s+(?:correlation|relationship)(?:\s+(?:last|past|over|yesterday|today|week|day|month)|$)'
        ]

        for pattern in correlation_patterns:
            match = re.search(pattern, text)
            if match:
                metric1_text = match.group(1).strip()
                metric2_text = match.group(2).strip()

                # Parse both metrics
                metric1 = self._parse_single_metric(metric1_text)
                metric2 = self._parse_single_metric(metric2_text)

                # Return the one that's NOT the primary metric
                if metric1 == primary_metric and metric2:
                    return metric2
                elif metric2 == primary_metric and metric1:
                    return metric1
                elif metric1 and not metric2:
                    return metric1
                elif metric2 and not metric1:
                    return metric2
                elif metric1 and metric2:
                    # Both found, return the second one by default
                    return metric2

        return None

    def _parse_single_metric(self, text: str) -> Optional[str]:
        """Parse a single metric from text"""
        text = text.lower().strip()

        # Direct metric lookup
        for alias in sorted(self.metric_aliases.keys(), key=len, reverse=True):
            if alias in text:
                return self.metric_aliases[alias]

        return None