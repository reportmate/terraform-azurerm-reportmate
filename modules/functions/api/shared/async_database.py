"""
Async Database Manager for Azure Functions using asyncpg
"""
import asyncpg
import os
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class AsyncDatabaseManager:
    """Async database manager using asyncpg"""
    
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")
    
    async def get_connection(self):
        """Get an async database connection"""
        return await asyncpg.connect(self.connection_string)
    
    async def execute_query(self, query, *args):
        """Execute a query and return results"""
        conn = await self.get_connection()
        try:
            result = await conn.fetch(query, *args)
            return result
        finally:
            await conn.close()
    
    async def execute_single(self, query, *args):
        """Execute a query and return a single result"""
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(query, *args)
            return result
        finally:
            await conn.close()
    
    async def test_connection(self):
        """Test database connectivity"""
        try:
            conn = await self.get_connection()
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            return result == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
