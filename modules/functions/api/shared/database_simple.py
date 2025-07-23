"""
Simple synchronous database connection for Azure Functions using psycopg2
"""

import logging
import os
import json
import psycopg2
import psycopg2.extras
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Simple synchronous database manager using psycopg2
    """
    
    def __init__(self):
        self.connection_string = None
        self._parse_connection_string()
    
    def _parse_connection_string(self):
        """Parse the database connection string"""
        # Try different environment variable names
        db_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE_CONNECTION_STRING')
        
        if not db_url:
            raise ValueError("No database connection string found")
        
        self.connection_string = db_url
        logger.info(f"Database connection configured")
    
    def _get_connection(self):
        """Get a database connection"""
        return psycopg2.connect(self.connection_string)
    
    def execute(self, query: str, *params) -> int:
        """Execute a query and return affected row count"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Database execute error: {str(e)}")
            raise
    
    def fetch_one(self, query: str, *params) -> Optional[Dict[str, Any]]:
        """Fetch one row and return as dictionary"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Database fetch_one error: {str(e)}")
            raise
    
    def fetch_all(self, query: str, *params) -> List[Dict[str, Any]]:
        """Fetch all rows and return as list of dictionaries"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Database fetch_all error: {str(e)}")
            raise
