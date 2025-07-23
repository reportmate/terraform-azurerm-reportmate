"""
Simple Database Manager for Azure Functions using pg8000
"""
import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AsyncDatabaseManager:
    """Simple database manager using pg8000 (compatible interface)"""
    
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
            'password': parsed.password,
            'ssl_context': True  # Use SSL for Azure
        }
    
    def get_connection(self):
        """Get a database connection"""
        try:
            import pg8000
            return pg8000.connect(**self.connection_params)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def execute_query(self, query, *args):
        """Execute a query and return results (sync method with async interface)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, args)
            result = cursor.fetchall()
            cursor.close()
            
            # Convert to list of dictionaries if needed
            if result and hasattr(cursor, 'description'):
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in result]
            
            return result
        finally:
            conn.close()
    
    async def execute_single(self, query, *args):
        """Execute a query and return a single result"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, args)
            result = cursor.fetchone()
            cursor.close()
            
            # Convert to dictionary if needed
            if result and hasattr(cursor, 'description'):
                columns = [desc[0] for desc in cursor.description]
                result = dict(zip(columns, result))
            
            return result
        finally:
            conn.close()
    
    async def test_connection(self):
        """Test database connectivity"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
