"""
Semantic Health Service - Natural language health event processing with PostgreSQL + pgvector
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import psycopg2.pool
from dotenv import load_dotenv

from services.azure_embedding_service import AzureEmbeddingService

load_dotenv()

logger = logging.getLogger(__name__)

class SemanticHealthService:
    """Service for processing natural language health events with semantic search"""

    def __init__(self):
        self.embedding_service = AzureEmbeddingService()
        self.connection_pool = None
        self._setup_connection_pool()

    def _setup_connection_pool(self):
        """Setup PostgreSQL connection pool"""
        try:
            # PostgreSQL connection string - update with your Railway/hosting details
            connection_params = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DATABASE', 'ultrahuman_semantic'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', ''),
                'sslmode': os.getenv('POSTGRES_SSLMODE', 'require')
            }

            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **connection_params
            )

            logger.info("PostgreSQL connection pool established")

        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL connection pool: {str(e)}")
            self.connection_pool = None

    def get_connection(self):
        """Get connection from pool"""
        if self.connection_pool:
            return self.connection_pool.getconn()
        return None

    def return_connection(self, conn):
        """Return connection to pool"""
        if self.connection_pool and conn:
            self.connection_pool.putconn(conn)

    def process_health_event(self, user_id: str, description: str, event_date: datetime = None) -> Dict[str, Any]:
        """Process natural language health event and store with semantic embedding"""

        if not event_date:
            event_date = datetime.now()

        try:
            logger.info(f"Processing health event for {user_id}: {description[:50]}...")

            # 1. Extract structured data using Azure OpenAI
            structured_data = self.embedding_service.extract_structured_data(description)

            # 2. Generate embedding for semantic search
            embedding = self.embedding_service.get_embedding(description)

            # 3. Generate relevant tags
            tags = self.embedding_service.generate_tags(description, structured_data)

            # 4. Store in database
            event_id = self._store_health_event(
                user_id=user_id,
                description=description,
                embedding=embedding,
                structured_data=structured_data,
                tags=tags,
                event_date=event_date
            )

            logger.info(f"Stored health event {event_id} for user {user_id}")

            return {
                'success': True,
                'event_id': event_id,
                'structured_data': structured_data,
                'tags': tags,
                'embedding_generated': len(embedding) > 0
            }

        except Exception as e:
            logger.error(f"Failed to process health event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _store_health_event(self, user_id: str, description: str, embedding: List[float],
                           structured_data: Dict, tags: List[str], event_date: datetime) -> int:
        """Store health event in PostgreSQL with pgvector embedding"""

        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Insert health event
                cur.execute("""
                    INSERT INTO health_events
                    (user_id, event_date, description, embedding, structured_data, tags)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    event_date,
                    description,
                    embedding,  # pgvector handles the list conversion
                    Json(structured_data),
                    tags
                ))

                event_id = cur.fetchone()['id']
                conn.commit()

                return event_id

        finally:
            self.return_connection(conn)

    def semantic_search(self, query: str, user_id: str, limit: int = 10,
                       similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar health events using semantic similarity"""

        try:
            # Get embedding for search query
            query_embedding = self.embedding_service.get_embedding(query)

            conn = self.get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Semantic similarity search using pgvector
                    cur.execute("""
                        SELECT
                            id,
                            event_date,
                            description,
                            structured_data,
                            tags,
                            (1 - (embedding <-> %s)) as similarity_score
                        FROM health_events
                        WHERE user_id = %s
                        AND (1 - (embedding <-> %s)) > %s
                        ORDER BY embedding <-> %s
                        LIMIT %s
                    """, (
                        query_embedding, user_id, query_embedding,
                        similarity_threshold, query_embedding, limit
                    ))

                    results = cur.fetchall()

                    # Convert to list of dicts for easier handling
                    search_results = []
                    for row in results:
                        search_results.append({
                            'id': row['id'],
                            'event_date': row['event_date'],
                            'description': row['description'],
                            'structured_data': row['structured_data'],
                            'tags': row['tags'],
                            'similarity_score': float(row['similarity_score'])
                        })

                    logger.info(f"Found {len(search_results)} similar events for query: {query[:50]}...")
                    return search_results

            finally:
                self.return_connection(conn)

        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []

    def find_successful_interventions(self, current_metrics: Dict[str, Any], user_id: str) -> List[Dict[str, Any]]:
        """Find interventions that helped in similar situations"""

        # Create search query from current metrics
        metrics_text = []
        for metric, value in current_metrics.items():
            if isinstance(value, dict) and 'latest_value' in value:
                metrics_text.append(f"{metric}: {value['latest_value']}")

        search_query = f"improved outcomes {' '.join(metrics_text)} successful intervention"

        # Search for similar successful periods
        similar_events = self.semantic_search(
            query=search_query,
            user_id=user_id,
            limit=15,
            similarity_threshold=0.6
        )

        # Filter for events with interventions and positive outcomes
        successful_interventions = []
        for event in similar_events:
            structured = event.get('structured_data', {})

            # Check if event has interventions
            has_interventions = (
                structured.get('supplements') or
                structured.get('activities') or
                len(event.get('tags', [])) > 2
            )

            # Check for positive outcomes
            outcomes = structured.get('outcomes', [])
            positive_outcomes = [
                o for o in outcomes
                if any(word in str(o.get('outcome', '')).lower()
                      for word in ['better', 'improved', 'great', 'good', 'energized', 'relaxed'])
            ]

            if has_interventions and (positive_outcomes or 'improve' in event['description'].lower()):
                successful_interventions.append({
                    **event,
                    'interventions': {
                        'supplements': structured.get('supplements', []),
                        'activities': structured.get('activities', []),
                        'timing': structured.get('timing', {})
                    },
                    'positive_outcomes': positive_outcomes
                })

        # Sort by similarity score and limit results
        successful_interventions.sort(key=lambda x: x['similarity_score'], reverse=True)

        return successful_interventions[:5]

    def get_historical_context(self, analysis_results: Dict, user_id: str) -> Dict[str, Any]:
        """Get historical context for current health analysis"""

        try:
            # Extract current state
            baseline_stats = analysis_results.get('baseline_statistics', {})

            # Create contextual search queries
            context_searches = []

            # Search for similar metric patterns
            for metric_name, stats in baseline_stats.items():
                if isinstance(stats, dict) and stats.get('latest_value') is not None:
                    latest = stats['latest_value']
                    context_searches.append({
                        'type': 'similar_metrics',
                        'metric': metric_name,
                        'query': f"{metric_name} {latest} similar pattern improved"
                    })

            # Search for correlations that worked before
            correlations = analysis_results.get('correlations', {})
            for corr_name, corr_data in correlations.items():
                if isinstance(corr_data, dict) and corr_data.get('significant'):
                    context_searches.append({
                        'type': 'correlation_success',
                        'correlation': corr_name,
                        'query': f"{corr_name.replace('_', ' ')} helped correlation improved"
                    })

            # Perform searches and collect context
            historical_context = {
                'similar_periods': [],
                'successful_interventions': [],
                'correlation_contexts': {}
            }

            for search in context_searches[:5]:  # Limit searches to avoid API overuse
                results = self.semantic_search(
                    query=search['query'],
                    user_id=user_id,
                    limit=3,
                    similarity_threshold=0.65
                )

                if search['type'] == 'similar_metrics':
                    historical_context['similar_periods'].extend(results)
                elif search['type'] == 'correlation_success':
                    historical_context['correlation_contexts'][search['correlation']] = results

            # Get successful interventions for current state
            interventions = self.find_successful_interventions(baseline_stats, user_id)
            historical_context['successful_interventions'] = interventions

            logger.info(f"Generated historical context with {len(historical_context['similar_periods'])} similar periods")

            return historical_context

        except Exception as e:
            logger.error(f"Failed to get historical context: {str(e)}")
            return {
                'similar_periods': [],
                'successful_interventions': [],
                'correlation_contexts': {}
            }

    def update_outcome_metrics(self, event_id: int, outcome_metrics: Dict[str, Any]):
        """Update health event with outcome metrics (next-day sleep score, etc.)"""

        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE health_events
                    SET outcome_metrics = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (Json(outcome_metrics), event_id))

                conn.commit()
                logger.info(f"Updated outcome metrics for event {event_id}")

        except Exception as e:
            logger.error(f"Failed to update outcome metrics: {str(e)}")
        finally:
            self.return_connection(conn)

    def get_recent_events(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent health events for a user"""

        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, event_date, description, structured_data, tags, outcome_metrics
                    FROM health_events
                    WHERE user_id = %s
                    AND event_date >= %s
                    ORDER BY event_date DESC
                """, (user_id, datetime.now() - timedelta(days=days)))

                events = cur.fetchall()
                return [dict(event) for event in events]

        except Exception as e:
            logger.error(f"Failed to get recent events: {str(e)}")
            return []
        finally:
            self.return_connection(conn)