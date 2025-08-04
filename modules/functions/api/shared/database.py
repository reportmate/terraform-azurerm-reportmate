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
        """Store unified device payload with full modular data support"""
        
        try:
            # Extract metadata - handle both PascalCase (C#) and camelCase serialization
            metadata = unified_payload.get('Metadata', {}) or unified_payload.get('metadata', {})
            device_id = metadata.get('DeviceId', metadata.get('deviceId', 'unknown-device'))
            serial_number = metadata.get('SerialNumber', metadata.get('serialNumber', 'unknown-serial'))
            enabled_modules = metadata.get('EnabledModules', metadata.get('enabledModules', []))
            collected_at = metadata.get('CollectedAt', metadata.get('collectedAt', datetime.now(timezone.utc).isoformat()))
            client_version = metadata.get('ClientVersion', metadata.get('clientVersion', 'unknown'))
            platform = metadata.get('Platform', metadata.get('platform', 'Windows'))
            
            logger.info(f"Processing unified payload for device {serial_number} with {len(enabled_modules)} modules")
            
            # For mock database, just return success
            if self.driver == "mock":
                return {
                    'success': True,
                    'message': 'Data stored successfully (mock)',
                    'device_id': serial_number,
                    'serial_number': serial_number,
                    'modules_processed': enabled_modules,
                    'timestamp': collected_at,
                    'storage_mode': 'mock',
                    'internal_uuid': device_id
                }
            
            # Define all supported module names (matches database table names)
            ALL_MODULES = [
                'applications', 'displays', 'hardware', 'installs', 'inventory',
                'management', 'network', 'printers', 'profiles', 'security', 'system'
            ]
            
            modules_processed = []
            events_stored = 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. STORE/UPDATE DEVICE REGISTRATION
                logger.info(f"Updating device registration for {serial_number}")
                
                # Extract device info from metadata for device registration
                device_name = metadata.get('hostname', metadata.get('deviceName', serial_number))
                current_time = datetime.now(timezone.utc).isoformat()
                
                if self.driver == "sqlite":
                    cursor.execute("""
                        INSERT OR REPLACE INTO devices 
                        (id, device_id, name, serial_number, last_seen, client_version, status, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (serial_number, device_id, device_name, serial_number, collected_at, client_version, 'online', current_time, current_time))
                else:
                    cursor.execute("""
                        INSERT INTO devices 
                        (id, device_id, name, serial_number, last_seen, client_version, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            device_id = EXCLUDED.device_id,
                            name = EXCLUDED.name,
                            last_seen = EXCLUDED.last_seen,
                            client_version = EXCLUDED.client_version,
                            status = EXCLUDED.status,
                            updated_at = NOW()
                    """, (serial_number, device_id, device_name, serial_number, collected_at, client_version, 'online'))
                
                # 2. STORE MODULE DATA (the missing piece!)
                for module_name in ALL_MODULES:
                    # Check if this module has data in the payload (both PascalCase and camelCase)
                    module_data = unified_payload.get(module_name.capitalize(), unified_payload.get(module_name))
                    
                    if module_data and module_data is not None:
                        logger.info(f"Processing {module_name} module data")
                        
                        # Convert module data to JSON string for storage
                        module_json = json.dumps(module_data)
                        current_time = datetime.now(timezone.utc).isoformat()
                        
                        if self.driver == "sqlite":
                            cursor.execute(f"""
                                INSERT OR REPLACE INTO {module_name}
                                (device_id, data, collected_at, updated_at, created_at)
                                VALUES (?, ?, ?, ?, ?)
                            """, (serial_number, module_json, collected_at, current_time, current_time))
                        else:
                            cursor.execute(f"""
                                INSERT INTO {module_name}
                                (device_id, data, collected_at, updated_at, created_at)
                                VALUES (%s, %s, %s, NOW(), NOW())
                                ON CONFLICT (device_id) DO UPDATE SET
                                    data = EXCLUDED.data,
                                    collected_at = EXCLUDED.collected_at,
                                    updated_at = NOW()
                            """, (serial_number, module_json, collected_at))
                        
                        modules_processed.append(module_name)
                        logger.info(f"✅ Stored {module_name} module data for device {serial_number}")
                
                # 3. STORE EVENTS DATA
                events = unified_payload.get('Events', []) or unified_payload.get('events', [])
                
                if events:
                    for event in events:
                        event_type = event.get('eventType', 'info').lower()
                        message = event.get('message', 'Event logged')
                        details = json.dumps(event.get('details', {}))
                        timestamp = event.get('timestamp', collected_at)
                        module_id = event.get('moduleId', 'unknown')
                        
                        # Validate event type
                        if event_type not in ['success', 'warning', 'error', 'info']:
                            logger.warning(f"Invalid event type '{event_type}', defaulting to 'info'")
                            event_type = 'info'
                        
                        # Add moduleId to event details for filtering
                        event_details = json.loads(details)
                        event_details['module_id'] = module_id
                        details = json.dumps(event_details)
                        
                        if self.driver == "sqlite":
                            cursor.execute(
                                "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                                (serial_number, event_type, message, details, timestamp)
                            )
                        else:
                            cursor.execute(
                                "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (%s, %s, %s, %s, %s)",
                                (serial_number, event_type, message, details, timestamp)
                            )
                        events_stored += 1
                        
                    logger.info(f"✅ Stored {events_stored} events for device {serial_number}")
                else:
                    # Fallback: store a generic data collection event if no specific events
                    event_type = 'info'
                    message = f"Data collection completed for {len(modules_processed)} modules"
                    details = json.dumps({
                        'modules': modules_processed, 
                        'collection_type': 'routine',
                        'module_id': 'system'
                    })
                    
                    if self.driver == "sqlite":
                        cursor.execute(
                            "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                            (serial_number, event_type, message, details, collected_at)
                        )
                    else:
                        cursor.execute(
                            "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (%s, %s, %s, %s, %s)",
                            (serial_number, event_type, message, details, collected_at)
                        )
                    events_stored = 1
                    logger.info(f"✅ Stored fallback data collection event for device {serial_number}")
                
                return {
                    'success': True,
                    'message': f'Complete data storage: {len(modules_processed)} modules, {events_stored} events',
                    'device_id': serial_number,
                    'serial_number': serial_number,
                    'modules_processed': modules_processed,
                    'events_stored': events_stored,
                    'timestamp': collected_at,
                    'internal_uuid': device_id
                }
                
        except Exception as e:
            logger.error(f"Failed to store unified payload: {e}", exc_info=True)
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
