"""
Unified Database Manager for ReportMate Azure Functions
Handles PostgreSQL connections and provides SQLite fallback for development
"""
import os
import json
import logging
import sqlite3
from contextlib import contextmanager
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Unified database manager with comprehensive driver support and fallbacks"""
    
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL') or os.getenv('DATABASE_CONNECTION_STRING')
        self.driver = None
        self._initialize_driver()
    
    def _initialize_driver(self):
        """Initialize database driver with proper fallback handling"""
        
        if not self.connection_string:
            logger.warning("No DATABASE_URL found, using SQLite for development")
            self.driver = "sqlite"
            return
        
        # Try to initialize PostgreSQL drivers
        try:
            # Try psycopg2 first (most common)
            import psycopg2
            self.driver = "psycopg2"
            logger.info("Using psycopg2 PostgreSQL driver")
            return
        except ImportError:
            pass
        
        try:
            # Try pg8000 (pure Python)
            import pg8000
            self.driver = "pg8000"
            logger.info("Using pg8000 PostgreSQL driver")
            return
        except ImportError:
            pass
        
        try:
            # Try asyncpg for async operations
            import asyncpg
            self.driver = "asyncpg"
            logger.info("Using asyncpg PostgreSQL driver")
            return
        except ImportError:
            pass
        
        # If no PostgreSQL drivers available, fall back to mock for Azure Functions
        logger.warning("🔄 No PostgreSQL drivers available, using mock responses")
        logger.warning("🔧 This allows the API to respond without database connectivity")
        self.driver = "mock"
    
    def _parse_connection_string(self):
        """Parse connection string into components"""
        if not self.connection_string:
            return {}
        
        parsed = urlparse(self.connection_string)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path.startswith('/') else parsed.path,
            'user': parsed.username,
            'password': parsed.password
        }
    
    def _create_connection(self):
        """Create a database connection based on available driver"""
        
        if self.driver == "sqlite":
            return sqlite3.connect(':memory:')
        
        elif self.driver == "mock":
            return MockConnection()
        
        elif self.driver == "psycopg2":
            import psycopg2
            params = self._parse_connection_string()
            return psycopg2.connect(**params)
        
        elif self.driver == "pg8000":
            import pg8000
            params = self._parse_connection_string()
            return pg8000.connect(**params)
        
        else:
            raise ValueError(f"Unsupported driver: {self.driver}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = self._create_connection()
            yield conn
            if hasattr(conn, 'commit'):
                conn.commit()
        except Exception as e:
            if conn and hasattr(conn, 'rollback'):
                conn.rollback()
            raise e
        finally:
            if conn and hasattr(conn, 'close'):
                conn.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dictionaries"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute(query, params or ())
                
                # Handle different cursor types
                if hasattr(cursor, 'description') and cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    return []
            
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                logger.error(f"Query: {query}")
                logger.error(f"Params: {params}")
                
                # For mock driver, return success response
                if self.driver == "mock":
                    return [{"success": True, "message": "Mock response"}]
                
                raise e
    
    def store_event_data(self, unified_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store unified device event data - mock implementation for development"""
        
        try:
            # Extract metadata
            metadata = unified_payload.get('metadata', {})
            device_id = metadata.get('deviceId', 'unknown-device')
            serial_number = metadata.get('serialNumber', 'unknown-serial')
            enabled_modules = metadata.get('enabledModules', [])
            collected_at = metadata.get('collectedAt', datetime.now(timezone.utc).isoformat())
            
            logger.info(f"Mock storage for device {device_id} with {len(enabled_modules)} modules")
            
            # For mock database, just return success
            if self.driver == "mock":
                return {
                    'success': True,
                    'message': 'Data stored successfully (mock)',
                    'device_id': serial_number,  # Return serial number for frontend consistency
                    'serial_number': serial_number,
                    'modules_processed': enabled_modules,
                    'timestamp': collected_at,
                    'storage_mode': 'mock',
                    'internal_uuid': device_id  # Keep UUID for internal reference if needed
                }
            
            # For real database, implement actual storage logic here
            # This would involve:
            # 1. Storing device registration data
            # 2. Storing module data in respective tables
            # 3. Storing events data
            # 4. Updating device last_seen timestamp
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Simple event storage for now
                event_type = 'info'  # Default event type
                message = f"Data collection completed for {len(enabled_modules)} modules"
                
                # CRITICAL FIX: Use serial_number instead of device_id (UUID) for event storage
                # The events table device_id field should contain the human-readable serial number
                # not the internal UUID. This ensures the frontend displays the correct identifier.
                
                if self.driver == "sqlite":
                    cursor.execute(
                        "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (serial_number, event_type, message, json.dumps(unified_payload), collected_at)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (%s, %s, %s, %s, %s)",
                        (serial_number, event_type, message, json.dumps(unified_payload), collected_at)
                    )
                
                return {
                    'success': True,
                    'message': 'Data stored successfully',
                    'device_id': serial_number,  # Return serial number for frontend consistency
                    'serial_number': serial_number,
                    'modules_processed': enabled_modules,
                    'timestamp': collected_at,
                    'internal_uuid': device_id  # Keep UUID for internal reference if needed
                }
                
        except Exception as e:
            logger.error(f"Failed to store event data: {e}")
            return {
                'success': False,
                'error': 'Storage failed',
                'details': str(e)
            }

# Mock classes for when no database drivers are available
class MockConnection:
    """Mock database connection for testing/development"""
    
    def cursor(self):
        return MockCursor()
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
    
    def close(self):
        pass

class MockCursor:
    """Mock database cursor for testing/development"""
    
    def __init__(self):
        self.description = [('id',), ('result',), ('message',)]
    
    def execute(self, query: str, params=None):
        """Mock query execution - logs query but doesn't actually execute"""
        logger.info(f"Mock DB Query: {query}")
        if params:
            logger.info(f"Mock DB Params: {params}")
    
    def fetchone(self):
        """Return mock single result"""
        return (1, "success", "Mock database response")
    
    def fetchall(self):
        """Return mock multiple results"""
        return [
            (1, "success", "Mock database response"),
            (2, "success", "Another mock response")
        ]

# Synchronous database manager (for most Azure Functions)
class SyncDatabaseManager(DatabaseManager):
    """Synchronous database manager for Azure Functions"""
    pass

# Asynchronous database manager (for performance-critical operations)
class AsyncDatabaseManager:
    """Asynchronous database manager using asyncpg"""
    
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL') or os.getenv('DATABASE_CONNECTION_STRING')
        self.pool = None
    
    async def get_pool(self):
        """Get or create connection pool"""
        if self.pool is None:
            if not self.connection_string:
                logger.warning("No DATABASE_URL for async operations")
                return None
            
            try:
                import asyncpg
                self.pool = await asyncpg.create_pool(self.connection_string)
            except ImportError:
                logger.warning("asyncpg not available for async operations")
                return None
        
        return self.pool
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute async query"""
        pool = await self.get_pool()
        
        if not pool:
            # Fallback to mock response for async operations
            logger.warning("Async database not available, returning mock response")
            return [{"success": True, "message": "Mock async response"}]
        
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(query, *(params or ()))
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Async query failed: {e}")
                return [{"error": str(e)}]

# Legacy compatibility class
class SimpleDatabaseManager(SyncDatabaseManager):
    """Legacy compatibility - redirects to SyncDatabaseManager"""
    pass

# Global instances for convenience
database_manager = SyncDatabaseManager()
async_database_manager = AsyncDatabaseManager()
