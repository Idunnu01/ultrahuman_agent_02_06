#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from services.metrics_service import _extract_two_metrics_freeform, _canonical_metric, METRIC_SYNONYMS
import re

def debug_metric_extraction():
    test_queries = [
        "What relationship is between my heart rate and sleep",
        "Correlation between heart rate and sleep",
        "Is there a correlation between my heart rate and sleep?"
    ]

    print("Debugging Metric Extraction:")
    print("=" * 50)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 30)

        # Test the extraction function
        metrics = _extract_two_metrics_freeform(query)
        print(f"Extracted metrics: {metrics}")

        # Test individual parts
        msg = query.lower()
        parts = re.split(r"\b(?:between|vs|versus|with|and|&)\b", msg)
        print(f"Split parts: {parts}")

        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                canonical = _canonical_metric(part)
                print(f"  Part {i}: '{part}' -> {canonical}")

        # Test specific terms
        test_terms = ["heart rate", "sleep", "my heart rate", "sleep score"]
        print("Direct term testing:")
        for term in test_terms:
            canonical = _canonical_metric(term)
            print(f"  '{term}' -> {canonical}")

def debug_metric_synonyms():
    print("\n" + "="*50)
    print("METRIC SYNONYMS:")
    for metric, synonyms in METRIC_SYNONYMS.items():
        print(f"{metric}: {synonyms}")

if __name__ == "__main__":
    debug_metric_extraction()
    debug_metric_synonyms()