"""
Azure OpenAI Embedding Service for Semantic Health Analysis
"""

import os
import json
import logging
from typing import List, Dict, Optional, Any
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AzureEmbeddingService:
    """Azure OpenAI embedding service for health data semantic analysis"""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding")
        self.gpt_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Azure OpenAI"""
        try:
            # Clean and prepare text
            cleaned_text = self._prepare_text_for_embedding(text)

            response = self.client.embeddings.create(
                input=cleaned_text,
                model=self.embedding_deployment
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding for text: {text[:50]}...")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * 1536

    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in batch"""
        try:
            # Clean texts
            cleaned_texts = [self._prepare_text_for_embedding(text) for text in texts]

            response = self.client.embeddings.create(
                input=cleaned_texts,
                model=self.embedding_deployment
            )

            embeddings = [data.embedding for data in response.data]
            logger.info(f"Generated {len(embeddings)} embeddings in batch")

            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * 1536 for _ in texts]

    def extract_structured_data(self, description: str) -> Dict[str, Any]:
        """Extract structured health data from natural language description"""
        try:
            extraction_prompt = f"""
Extract structured health data from this description: "{description}"

Return valid JSON with these fields (use null if not mentioned):
{{
    "supplements": [{{
        "name": "supplement name",
        "dosage": "amount with unit",
        "time": "HH:MM format or description",
        "frequency": "once/daily/etc"
    }}],
    "activities": [{{
        "activity": "exercise/meditation/etc",
        "duration": "duration with unit",
        "intensity": "low/moderate/high",
        "time": "time of day"
    }}],
    "symptoms": [{{
        "symptom": "symptom name",
        "severity": 1-10,
        "duration": "how long",
        "context": "when it occurred"
    }}],
    "mood_energy": {{
        "mood": 1-10,
        "energy": 1-10,
        "stress": 1-10,
        "sleep_quality": 1-10
    }},
    "environmental": {{
        "location": "home/office/gym",
        "weather": "sunny/rainy/cold",
        "social": "alone/with_friends/family"
    }},
    "timing": {{
        "meal_timing": "before/after meals",
        "sleep_timing": "bedtime preparation",
        "work_timing": "during/after work"
    }},
    "outcomes": [{{
        "outcome": "felt relaxed/energized/etc",
        "timing": "immediate/after 1hr/next day",
        "intensity": 1-10
    }}],
    "context": "overall context or situation"
}}

Only extract what's explicitly mentioned. Use null for missing information.
"""

            response = self.client.chat.completions.create(
                model=self.gpt_deployment,
                messages=[
                    {"role": "system", "content": "You are a health data extraction expert. Extract structured data from natural language descriptions. Always return valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )

            extracted_json = response.choices[0].message.content

            # Clean and parse JSON
            if "```json" in extracted_json:
                extracted_json = extracted_json.split("```json")[1].split("```")[0]
            elif "```" in extracted_json:
                extracted_json = extracted_json.split("```")[1].split("```")[0]

            structured_data = json.loads(extracted_json.strip())

            logger.info(f"Extracted structured data from: {description[:50]}...")
            return structured_data

        except Exception as e:
            logger.error(f"Failed to extract structured data: {str(e)}")
            # Return basic fallback structure
            return {
                "supplements": [],
                "activities": [],
                "symptoms": [],
                "mood_energy": {},
                "environmental": {},
                "timing": {},
                "outcomes": [],
                "context": description
            }

    def generate_tags(self, description: str, structured_data: Dict) -> List[str]:
        """Generate relevant tags for health event"""
        try:
            tag_prompt = f"""
Generate 3-7 relevant tags for this health event:
Description: {description}
Structured data: {json.dumps(structured_data, indent=2)}

Tags should be:
- Single words or short phrases
- Useful for searching and categorizing
- Health and wellness focused

Examples: ["supplement", "evening", "sleep_aid", "magnesium", "routine", "recovery"]

Return only a JSON array of strings.
"""

            response = self.client.chat.completions.create(
                model=self.gpt_deployment,
                messages=[
                    {"role": "system", "content": "Generate relevant tags for health events. Return only JSON array."},
                    {"role": "user", "content": tag_prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )

            tags_json = response.choices[0].message.content.strip()

            # Clean and parse JSON
            if "```json" in tags_json:
                tags_json = tags_json.split("```json")[1].split("```")[0]
            elif "```" in tags_json:
                tags_json = tags_json.split("```")[1].split("```")[0]

            tags = json.loads(tags_json)

            # Ensure it's a list of strings
            if isinstance(tags, list):
                tags = [str(tag).lower().strip() for tag in tags if tag]
                logger.debug(f"Generated tags: {tags}")
                return tags
            else:
                raise ValueError("Tags not returned as array")

        except Exception as e:
            logger.error(f"Failed to generate tags: {str(e)}")
            # Generate basic tags from structured data
            basic_tags = []

            if structured_data.get('supplements'):
                basic_tags.extend(['supplement'] + [s['name'].lower() for s in structured_data['supplements'] if s.get('name')])

            if structured_data.get('activities'):
                basic_tags.extend(['activity'] + [a['activity'].lower() for a in structured_data['activities'] if a.get('activity')])

            if 'sleep' in description.lower():
                basic_tags.append('sleep')
            if 'morning' in description.lower():
                basic_tags.append('morning')
            if 'evening' in description.lower():
                basic_tags.append('evening')

            return list(set(basic_tags))[:7]  # Limit to 7 unique tags

    def _prepare_text_for_embedding(self, text: str) -> str:
        """Clean and prepare text for embedding"""
        if not text or not isinstance(text, str):
            return ""

        # Basic cleaning
        cleaned = text.strip()

        # Remove excessive whitespace
        cleaned = ' '.join(cleaned.split())

        # Truncate if too long (OpenAI has token limits)
        if len(cleaned) > 8000:  # Conservative limit
            cleaned = cleaned[:8000] + "..."

        return cleaned

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            magnitude1 = np.linalg.norm(vec1)
            magnitude2 = np.linalg.norm(vec2)

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {str(e)}")
            return 0.0