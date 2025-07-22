"""
Synchronous Database Manager for Azure Functions
Simple PostgreSQL connection handling using multiple drivers
"""
import os
import logging
from contextlib import contextmanager
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SyncDatabaseManager:
    """Synchronous database manager for Azure Functions"""
    
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Parse the connection string
        parsed = urlparse(self.connection_string)
        self.connection_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:],  # Remove leading slash
            'user': parsed.username,
            'password': parsed.password
        }
        
        # Try to find an available PostgreSQL driver
        self.driver = None
        self.connect_func = None
        
        # Try psycopg2 first
        try:
            import psycopg2
            import psycopg2.extras
            self.driver = "psycopg2"
            self.connect_func = psycopg2.connect
            self.connection_params['sslmode'] = 'require'
            logger.info("Using psycopg2 driver")
        except ImportError:
            pass
        
        # Try pg8000 as fallback
        if not self.driver:
            try:
                import pg8000
                self.driver = "pg8000"
                self.connect_func = pg8000.connect
                self.connection_params['ssl_context'] = True
                logger.info("Using pg8000 driver")
            except ImportError:
                pass
        
        if not self.driver:
            raise ImportError("No PostgreSQL driver available (tried psycopg2, pg8000)")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection as a context manager"""
        conn = None
        try:
            conn = self.connect_func(**self.connection_params)
            yield conn
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
