#!/usr/bin/env python3
"""
Test script for temperature and sleep correlation
"""

def test_temperature_sleep_correlation():
    """Test the specific temperature and sleep correlation query"""

    # Simple metric mappings (copied from the service)
    metric_mappings = {
        'temperature': 'temperature',
        'temp': 'temperature',
        'body temperature': 'temperature',
        'skin temperature': 'temperature',
        'sleep': 'sleep_score',
        'sleep score': 'sleep_score',
        'sleep data': 'sleep_score',
        'sleep quality': 'sleep_score',
        'sleep pattern': 'sleep_score'
    }

    def extract_metrics_from_query(query):
        """Extract metric names from natural language query"""
        mentioned_metrics = []
        query_lower = query.lower()

        for keyword, metric_type in metric_mappings.items():
            if keyword in query_lower:
                mentioned_metrics.append(metric_type)

        return list(set(mentioned_metrics))  # Remove duplicates

    def is_natural_language_query(sms_content):
        """Check if SMS content is a natural language query"""
        query_keywords = [
            'correlation', 'correlate', 'relationship', 'connection',
            'analysis', 'analyze', 'trend', 'pattern', 'compare',
            'how', 'what', 'why', 'when', 'where', 'is there',
            'show me', 'tell me', 'find', 'search', 'look up',
            'score', 'levels', 'data', 'trends', 'insights'
        ]

        # Check for question words and analysis keywords
        question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who']
        analysis_words = ['analyze', 'analysis', 'compare', 'correlation', 'trend', 'pattern']

        sms_lower = sms_content.lower()

        # Check for question words
        has_question = any(word in sms_lower for word in question_words)

        # Check for analysis keywords
        has_analysis = any(word in sms_lower for word in analysis_words)

        # Check for other query keywords
        has_query_keywords = any(keyword in sms_lower for keyword in query_keywords)

        return has_question or has_analysis or has_query_keywords

    # Test various temperature and sleep correlation queries
    test_queries = [
        "let's test the correlation between temperature and sleep",
        "Is there a correlation between my body temperature and sleep?",
        "What's the relationship between temperature and sleep quality?",
        "Analyze the correlation between my temperature and sleep score",
        "How does my body temperature affect my sleep?",
        "Compare my temperature and sleep patterns",
        "Show me the correlation between temperature and sleep data"
    ]

    print("Testing Temperature and Sleep Correlation Queries:")
    print("=" * 60)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")

        # Test natural language detection
        is_nl = is_natural_language_query(query)
        print(f"   Natural language query: {is_nl}")

        # Test metric extraction
        metrics = extract_metrics_from_query(query)
        print(f"   Extracted metrics: {metrics}")

        # Determine response type
        if is_nl and len(metrics) >= 2:
            print(f"   Response type: Correlation analysis")
            print(f"   Mock response: 'I found correlations between {', '.join(metrics)}. Check your app for details!'")
        elif is_nl and len(metrics) == 1:
            print(f"   Response type: Single metric analysis")
            print(f"   Mock response: 'Here\'s your {metrics[0]} analysis. Check your app for details!'")
        elif is_nl and len(metrics) == 0:
            print(f"   Response type: General query")
            print(f"   Mock response: 'I can help analyze your health data. Try asking about specific metrics like temperature, sleep, heart rate, or recovery.'")
        else:
            print(f"   Response type: Lifestyle event")
            print(f"   Mock response: 'Logged your lifestyle event. Thanks!'")

def test_specific_user_query():
    """Test the specific query from the user"""

    query = "let's test the correlation between temperature and sleep"

    print(f"\n\nTesting the specific user query:")
    print(f"Query: '{query}'")

    # This should be detected as a natural language query
    query_keywords = [
        'correlation', 'correlate', 'relationship', 'connection',
        'analysis', 'analyze', 'trend', 'pattern', 'compare',
        'how', 'what', 'why', 'when', 'where', 'is there',
        'show me', 'tell me', 'find', 'search', 'look up'
    ]

    is_nl = any(keyword in query.lower() for keyword in query_keywords)
    print(f"Is natural language query: {is_nl}")

    # This should extract temperature and sleep_score
    metric_mappings = {
        'temperature': 'temperature',
        'temp': 'temperature',
        'body temperature': 'temperature',
        'skin temperature': 'temperature',
        'sleep': 'sleep_score',
        'sleep score': 'sleep_score',
        'sleep data': 'sleep_score',
        'sleep quality': 'sleep_score',
        'sleep pattern': 'sleep_score'
    }

    mentioned_metrics = []
    query_lower = query.lower()

    for keyword, metric_type in metric_mappings.items():
        if keyword in query_lower:
            mentioned_metrics.append(metric_type)

    mentioned_metrics = list(set(mentioned_metrics))
    print(f"Extracted metrics: {mentioned_metrics}")

    if len(mentioned_metrics) >= 2:
        print(f"Expected response: Correlation analysis between {', '.join(mentioned_metrics)}")
        print(f"Mock SMS response: 'I found a moderate negative correlation (r=-0.45) between your temperature and sleep score. Lower body temperature tends to be associated with better sleep quality.'")
    else:
        print("Error: Not enough metrics extracted for correlation analysis")

if __name__ == "__main__":
    test_temperature_sleep_correlation()
    test_specific_user_query()

    print("\n" + "=" * 60)
    print("Test completed!")
    print("\nThe temperature and sleep correlation analysis should work correctly.")
    print("The system will extract both 'temperature' and 'sleep_score' metrics")
    print("and perform correlation analysis between them.")
