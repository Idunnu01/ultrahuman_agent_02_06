"""
Text-based semantic health service (fallback without pgvector)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import psycopg2.pool
from dotenv import load_dotenv

from services.azure_embedding_service import AzureEmbeddingService

load_dotenv()

logger = logging.getLogger(__name__)

class TextBasedSemanticService:
    """Text-based semantic health service without vector requirements"""

    def __init__(self):
        self.embedding_service = AzureEmbeddingService()
        self.connection_pool = None
        self._setup_connection_pool()

    def _setup_connection_pool(self):
        """Setup PostgreSQL connection pool"""
        try:
            connection_params = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': os.getenv('POSTGRES_PORT', '5432'),
                'database': os.getenv('POSTGRES_DATABASE', 'railway'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', ''),
                'sslmode': os.getenv('POSTGRES_SSLMODE', 'require')
            }

            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **connection_params
            )

            logger.info("PostgreSQL connection pool established for text-based service")

        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL connection pool: {str(e)}")
            self.connection_pool = None

    def process_health_event(self, user_id: str, description: str, event_date: datetime = None) -> Dict[str, Any]:
        """Process health event with text-based storage"""

        if not event_date:
            event_date = datetime.now()

        try:
            # Extract structured data
            structured_data = self.embedding_service.extract_structured_data(description)

            # Generate tags
            tags = self.embedding_service.generate_tags(description, structured_data)

            # Store in database
            event_id = self._store_health_event(
                user_id=user_id,
                description=description,
                structured_data=structured_data,
                tags=tags,
                event_date=event_date
            )

            return {
                'success': True,
                'event_id': event_id,
                'structured_data': structured_data,
                'tags': tags
            }

        except Exception as e:
            logger.error(f"Failed to process health event: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _store_health_event(self, user_id: str, description: str,
                           structured_data: Dict, tags: List[str], event_date: datetime) -> int:
        """Store health event in PostgreSQL"""

        conn = self.connection_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO health_events
                    (user_id, event_date, description, structured_data, tags)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    event_date,
                    description,
                    Json(structured_data),
                    tags
                ))

                event_id = cur.fetchone()['id']
                conn.commit()

                return event_id

        finally:
            self.connection_pool.putconn(conn)

    def text_search(self, query: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Text-based search using PostgreSQL full text search"""

        try:
            conn = self.connection_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Use PostgreSQL full text search
                    cur.execute("""
                        SELECT
                            id,
                            event_date,
                            description,
                            structured_data,
                            tags,
                            ts_rank_cd(to_tsvector('english', description || ' ' || array_to_string(tags, ' ')),
                                       plainto_tsquery('english', %s)) as rank
                        FROM health_events
                        WHERE user_id = %s
                        AND (to_tsvector('english', description || ' ' || array_to_string(tags, ' '))
                             @@ plainto_tsquery('english', %s))
                        ORDER BY rank DESC, event_date DESC
                        LIMIT %s
                    """, (query, user_id, query, limit))

                    results = cur.fetchall()

                    search_results = []
                    for row in results:
                        search_results.append({
                            'id': row['id'],
                            'event_date': row['event_date'],
                            'description': row['description'],
                            'structured_data': row['structured_data'],
                            'tags': row['tags'],
                            'relevance_score': float(row['rank'])
                        })

                    return search_results

            finally:
                self.connection_pool.putconn(conn)

        except Exception as e:
            logger.error(f"Text search failed: {str(e)}")
            return []
