"""
Database Manager for ReportMate Azure Functions
Handles database connections and queries safely
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SyncDatabaseManager:
    """Synchronous database manager for Azure Functions"""
    
    def __init__(self):
        self.connection = None
        self.connection_string = self._build_connection_string()
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        # First try DATABASE_URL if it exists (standard format)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            logger.info("Using DATABASE_URL connection string")
            return database_url
        
        # Fallback to individual environment variables
        logger.info("Using individual DB environment variables")
        return (
            f"host={os.getenv('DB_HOST', 'localhost')} "
            f"dbname={os.getenv('DB_NAME', 'reportmate')} "
            f"user={os.getenv('DB_USER', 'postgres')} "
            f"password={os.getenv('DB_PASSWORD', 'password')} "
            f"port={os.getenv('DB_PORT', '5432')} "
            f"sslmode=require"
        )
    
    def connect(self) -> bool:
        """Establish database connection"""
        try:
            if self.connection and not self.connection.closed:
                return True
                
            logger.info("Connecting to PostgreSQL database...")
            self.connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor,
                connect_timeout=10
            )
            self.connection.autocommit = True
            logger.info("Database connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self.connection = None
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
            finally:
                self.connection = None
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        try:
            if not self.connect():
                raise Exception("Could not establish database connection")
            
            with self.connection.cursor() as cursor:
                logger.debug(f"Executing query: {query[:100]}...")
                cursor.execute(query, params or ())
                
                # For SELECT queries, fetch results
                if query.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    logger.info(f"Query returned {len(results)} rows")
                    return [dict(row) for row in results]
                else:
                    # For non-SELECT queries, return affected row count
                    return [{'affected_rows': cursor.rowcount}]
                    
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
        finally:
            # Don't disconnect here - keep connection alive for performance
            pass
    
    def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            result = self.execute_query("SELECT 1 as test")
            return len(result) > 0 and result[0].get('test') == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
