#!/usr/bin/env python3
"""
Natural Language Parser for Health Queries
Understands flexible, conversational health questions
"""

import re
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class ParsedQuery:
    """Structured representation of a parsed health query"""
    metric_type: str              # heart_rate, hrv, sleep_score, etc.
    aggregation: str              # average, min, max, latest, trend
    time_period: str              # 7_days, 1_week, 1_month, etc.
    time_period_days: int         # converted to days
    query_type: str               # metric_query, comparison, trend, correlation
    confidence: float             # how confident we are in the parsing
    raw_query: str                # original query
    extracted_entities: Dict      # additional extracted info

class HealthQueryParser:
    """Advanced NLP parser for health queries"""

    def __init__(self):
        # Metric synonyms and variations
        self.metric_synonyms = {
            'heart_rate': [
                'heart rate', 'hr', 'heartrate', 'pulse', 'bpm', 'beats per minute',
                'cardiac', 'heart beat', 'heartbeat', 'heart rhythm', 'cardiac rate'
            ],
            'hrv': [
                'hrv', 'heart rate variability', 'variability', 'hrv score',
                'cardiac variability', 'rr interval', 'heart rhythm variability'
            ],
            'sleep_score': [
                'sleep', 'sleep score', 'sleep quality', 'sleep rating',
                'how well i slept', 'sleep performance', 'rest quality',
                'sleep index', 'sleep metrics', 'sleep data'
            ],
            'temperature': [
                'temperature', 'temp', 'body temp', 'body temperature',
                'fever', 'thermal', 'degrees'
            ],
            'recovery': [
                'recovery', 'recovery score', 'readiness', 'how recovered',
                'recovery index', 'recovery metrics', 'recovery status'
            ]
        }

        # Aggregation synonyms
        self.aggregation_synonyms = {
            'average': [
                'average', 'avg', 'mean', 'typical', 'usually', 'normally',
                'on average', 'generally', 'overall', 'median'
            ],
            'max': [
                'max', 'maximum', 'highest', 'peak', 'top', 'best',
                'most', 'high', 'upper', 'greatest'
            ],
            'min': [
                'min', 'minimum', 'lowest', 'bottom', 'worst', 'smallest',
                'least', 'low', 'lower', 'poorest'
            ],
            'latest': [
                'latest', 'recent', 'current', 'now', 'today', 'last',
                'most recent', 'current', 'present'
            ],
            'trend': [
                'trend', 'trending', 'pattern', 'direction', 'changing',
                'improving', 'getting better', 'getting worse', 'going up',
                'going down', 'progress', 'trajectory'
            ]
        }

        # Time period patterns and conversions
        self.time_patterns = {
            # Explicit numbers
            r'(\d+)\s*(day|days)': lambda m: int(m.group(1)),
            r'(\d+)\s*(week|weeks)': lambda m: int(m.group(1)) * 7,
            r'(\d+)\s*(month|months)': lambda m: int(m.group(1)) * 30,

            # Common phrases
            r'(yesterday|today)': lambda m: 1,
            r'(this\s+week|past\s+week)': lambda m: 7,
            r'(last\s+week)': lambda m: 7,
            r'(this\s+month|past\s+month)': lambda m: 30,
            r'(last\s+month)': lambda m: 30,
            r'(recently|lately)': lambda m: 7,
            r'(past\s+few\s+days)': lambda m: 3,
            r'(past\s+couple\s+days)': lambda m: 2,

            # Flexible patterns
            r'(last\s+)(\d+)': lambda m: int(m.group(2)),
            r'(past\s+)(\d+)': lambda m: int(m.group(2)),
            r'(over\s+the\s+last\s+)(\d+)\s*(day|days|week|weeks)':
                lambda m: int(m.group(2)) * (7 if 'week' in m.group(3) else 1),
        }

        # Question patterns
        self.question_patterns = [
            r'(what|how)\s+(was|is|has been)\s+my\s+',
            r'(show|tell|give)\s+me\s+',
            r'(can you|could you)\s+(show|tell|give)',
            r'i\s+(want|need)\s+to\s+(see|know|check)',
            r'(how\s+)?(high|low|good|bad)\s+(was|is)',
        ]

    def parse_query(self, query: str) -> ParsedQuery:
        """Parse natural language health query into structured format"""

        query_lower = query.lower().strip()
        confidence = 0.0

        # Extract metric type
        metric_type, metric_confidence = self._extract_metric(query_lower)
        confidence += metric_confidence * 0.4

        # Extract aggregation
        aggregation, agg_confidence = self._extract_aggregation(query_lower, metric_type)
        confidence += agg_confidence * 0.3

        # Extract time period
        time_period_days, time_confidence = self._extract_time_period(query_lower)
        confidence += time_confidence * 0.3

        # Determine query type
        query_type = self._determine_query_type(query_lower, aggregation)

        # Create time period string
        time_period = self._format_time_period(time_period_days)

        # Extract additional entities
        entities = self._extract_additional_entities(query_lower)

        return ParsedQuery(
            metric_type=metric_type,
            aggregation=aggregation,
            time_period=time_period,
            time_period_days=time_period_days,
            query_type=query_type,
            confidence=min(confidence, 1.0),
            raw_query=query,
            extracted_entities=entities
        )

    def _extract_metric(self, query: str) -> Tuple[str, float]:
        """Extract metric type from query with confidence score"""

        best_match = ('heart_rate', 0.0)  # Default fallback

        for metric, synonyms in self.metric_synonyms.items():
            for synonym in synonyms:
                if synonym in query:
                    # Calculate confidence based on synonym specificity
                    confidence = len(synonym) / len(query)  # Longer matches = higher confidence
                    confidence = min(confidence, 0.9)  # Cap at 0.9

                    if confidence > best_match[1]:
                        best_match = (metric, confidence)

        return best_match

    def _extract_aggregation(self, query: str, metric_type: str) -> Tuple[str, float]:
        """Extract aggregation type from query"""

        best_match = ('average', 0.0)  # Default

        for agg, synonyms in self.aggregation_synonyms.items():
            for synonym in synonyms:
                if synonym in query:
                    confidence = len(synonym) / len(query)
                    confidence = min(confidence, 0.9)

                    if confidence > best_match[1]:
                        best_match = (agg, confidence)

        # Special logic for certain patterns
        if 'how' in query and ('high' in query or 'low' in query):
            if 'high' in query:
                return ('max', 0.8)
            else:
                return ('min', 0.8)

        # If no explicit aggregation, infer from context
        if best_match[1] == 0:
            if any(word in query for word in ['trend', 'pattern', 'changing']):
                return ('trend', 0.6)
            elif metric_type == 'sleep_score':
                return ('average', 0.5)  # Sleep usually wants average
            else:
                return ('average', 0.4)  # Default to average

        return best_match

    def _extract_time_period(self, query: str) -> Tuple[int, float]:
        """Extract time period and convert to days"""

        for pattern, converter in self.time_patterns.items():
            match = re.search(pattern, query)
            if match:
                try:
                    days = converter(match)
                    confidence = 0.8 if days <= 365 else 0.4  # Reasonable time periods
                    return (days, confidence)
                except:
                    continue

        # Fallback patterns
        if 'week' in query:
            return (7, 0.6)
        elif 'month' in query:
            return (30, 0.6)
        elif 'day' in query:
            return (1, 0.6)
        else:
            return (7, 0.3)  # Default to 7 days

    def _determine_query_type(self, query: str, aggregation: str) -> str:
        """Determine the type of query"""

        if 'vs' in query or 'versus' in query or 'compared to' in query:
            return 'comparison'
        elif 'correlation' in query or 'relationship' in query or 'related' in query:
            return 'correlation'
        elif aggregation == 'trend' or 'trend' in query or 'pattern' in query:
            return 'trend'
        else:
            return 'metric_query'

    def _format_time_period(self, days: int) -> str:
        """Format time period as string"""
        if days == 1:
            return 'today'
        elif days == 7:
            return 'week'
        elif days == 30:
            return 'month'
        elif days < 7:
            return f'{days}_days'
        elif days < 30:
            weeks = days // 7
            return f'{weeks}_weeks'
        else:
            months = days // 30
            return f'{months}_months'

    def _extract_additional_entities(self, query: str) -> Dict:
        """Extract additional entities like comparisons, specific dates, etc."""
        entities = {}

        # Look for comparison words
        if any(word in query for word in ['better', 'worse', 'higher', 'lower']):
            entities['comparison_intent'] = True

        # Look for urgency indicators
        if any(word in query for word in ['urgent', 'worried', 'concerned', 'problem']):
            entities['urgency'] = 'high'

        # Look for specific health contexts
        if any(word in query for word in ['workout', 'exercise', 'training']):
            entities['context'] = 'exercise'
        elif any(word in query for word in ['sleep', 'rest', 'night']):
            entities['context'] = 'sleep'

        return entities

# Test examples
def test_parser():
    """Test the natural language parser with various queries"""

    parser = HealthQueryParser()

    test_queries = [
        "average heart rate last 7 days",
        "what's my avg HR over past week",
        "how was my heart rate doing recently",
        "show me heart rate stats from this month",
        "what was my highest pulse yesterday",
        "how good was my sleep last week",
        "tell me my HRV trend over the past 2 weeks",
        "recovery score this month",
        "how high was my heart rate during workouts",
        "compare my sleep to last month",
        "heart rate correlation with temperature",
        "am I getting better sleep lately?"
    ]

    print("🧠 NATURAL LANGUAGE PARSER TEST")
    print("=" * 50)

    for query in test_queries:
        parsed = parser.parse_query(query)
        print(f"\n📝 Query: '{query}'")
        print(f"   📊 Metric: {parsed.metric_type}")
        print(f"   🔢 Aggregation: {parsed.aggregation}")
        print(f"   📅 Time: {parsed.time_period} ({parsed.time_period_days} days)")
        print(f"   🎯 Type: {parsed.query_type}")
        print(f"   ✅ Confidence: {parsed.confidence:.2f}")

        if parsed.extracted_entities:
            print(f"   🏷️ Entities: {parsed.extracted_entities}")

if __name__ == "__main__":
    test_parser()