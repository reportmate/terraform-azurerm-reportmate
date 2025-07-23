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
        
        # Try pg8000 as primary driver (better Azure compatibility)
        try:
            import pg8000
            self.driver = "pg8000"
            self.connect_func = pg8000.connect
            # Azure PostgreSQL SSL configuration for pg8000
            self.connection_params['ssl_context'] = True  # Use SSL
            # Remove psycopg2-specific params that pg8000 doesn't understand
            if 'sslmode' in self.connection_params:
                del self.connection_params['sslmode']
            if 'sslcert' in self.connection_params:
                del self.connection_params['sslcert']
            if 'sslkey' in self.connection_params:
                del self.connection_params['sslkey']
            if 'sslrootcert' in self.connection_params:
                del self.connection_params['sslrootcert']
            logger.info("Using pg8000 driver with Azure SSL configuration")
        except ImportError:
            # Fallback to psycopg2
            try:
                import psycopg2
                self.driver = "psycopg2"
                self.connect_func = psycopg2.connect
                logger.info("Using psycopg2 driver as fallback")
            except ImportError:
                pass
        
        if not self.driver:
            raise ImportError("No PostgreSQL driver available (tried pg8000, psycopg2)")
    
    def _create_connection_with_retry(self, max_retries=3):
        """Create database connection with retry logic for Azure reliability"""
        last_error = None
        for attempt in range(max_retries):
            try:
                if self.driver == "pg8000":
                    # pg8000 connection
                    import pg8000
                    conn = pg8000.connect(**self.connection_params)
                    return conn
                elif self.driver == "psycopg2":
                    # psycopg2 connection
                    import psycopg2
                    # Convert params format for psycopg2
                    conn_params = {
                        'host': self.connection_params['host'],
                        'port': self.connection_params['port'],
                        'database': self.connection_params['database'],
                        'user': self.connection_params['user'],
                        'password': self.connection_params['password'],
                        'sslmode': 'require'  # Azure PostgreSQL requires SSL
                    }
                    conn = psycopg2.connect(**conn_params)
                    return conn
                else:
                    raise ValueError(f"Unknown driver: {self.driver}")
            except Exception as e:
                last_error = e
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    
        # If all attempts failed, raise the last error
        raise last_error
    
    @contextmanager
    def get_connection(self):
        """Get a database connection as a context manager with retry logic"""
        conn = None
        try:
            conn = self._create_connection_with_retry()
            logger.info(f"✅ Database connection successful using {self.driver}")
            yield conn
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"❌ Database connection error with {self.driver}: {e}")
            logger.error(f"Connection params (sanitized): host={self.connection_params.get('host')}, port={self.connection_params.get('port')}, database={self.connection_params.get('database')}, user={self.connection_params.get('user')}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def test_connection(self):
        """Test database connectivity with detailed logging"""
        try:
            logger.info(f"Testing database connection using {self.driver} driver...")
            with self.get_connection() as conn:
                if self.driver == "pg8000":
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    cursor.close()
                    success = result[0] == 1
                elif self.driver == "psycopg2":
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    cursor.close()
                    success = result[0] == 1
                else:
                    success = False
                    
                if success:
                    logger.info(f"✅ Database connection test successful with {self.driver}")
                return success
        except Exception as e:
            logger.error(f"❌ Database connection test failed with {self.driver}: {e}")
            return False
