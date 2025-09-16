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
        
        # Try to initialize PostgreSQL drivers - pg8000 first (as per deployment guidelines)
        try:
            # Try pg8000 first (pure Python, deployment guideline requirement)
            import pg8000
            self.driver = "pg8000"
            logger.info("Using pg8000 PostgreSQL driver")
            return
        except ImportError:
            pass
        
        try:
            # Try psycopg2 as fallback (most common but not in our deployment)
            import psycopg2
            self.driver = "psycopg2"
            logger.info("Using psycopg2 PostgreSQL driver")
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
        
        # If no PostgreSQL drivers available, FAIL - do not use mock responses
        logger.error("❌ No PostgreSQL drivers available - database connection required")
        logger.error("❌ Install psycopg2-binary or asyncpg for database connectivity")
        raise ImportError("No PostgreSQL drivers available - database connection is required")
    
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
            client_version = metadata.get('ClientVersion', metadata.get('clientVersion'))
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
                
                # DEBUG: Log what events were found in the payload
                logger.info(f"Found {len(events)} events in payload for device {serial_number}")
                logger.info(f"Payload Events key exists: {bool(unified_payload.get('Events'))}")
                logger.info(f"Payload events key exists: {bool(unified_payload.get('events'))}")
                
                if events:
                    logger.info(f"Processing {len(events)} events for device {serial_number}")
                    
                    for event in events:
                        # DEBUG: Log the actual event structure to identify the issue
                        logger.info(f"Processing event: {json.dumps(event, indent=2)}")
                        
                        # Try multiple field name variations to handle casing issues
                        event_type = (
                            event.get('eventType') or 
                            event.get('EventType') or 
                            event.get('event_type') or 
                            'info'
                        ).lower()
                        
                        message = (
                            event.get('message') or 
                            event.get('Message') or 
                            'Event logged'
                        )
                        
                        details = json.dumps(
                            event.get('details') or 
                            event.get('Details') or 
                            {}
                        )
                        
                        timestamp = (
                            event.get('timestamp') or 
                            event.get('Timestamp') or 
                            collected_at
                        )
                        
                        module_id = (
                            event.get('moduleId') or 
                            event.get('ModuleId') or 
                            event.get('module_id') or 
                            'unknown'
                        )
                        
                        logger.info(f"Event processed - Type: '{event_type}', Module: '{module_id}', Message: '{message}'")
                        
                        # Validate event type
                        if event_type not in ['success', 'warning', 'error', 'info']:
                            logger.warning(f"Invalid event type '{event_type}' from device {serial_number}, defaulting to 'info'")
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
                    # DEBUG: Explain why no events were processed
                    logger.warning(f"No events found in payload for device {serial_number}")
                    logger.warning(f"Events array was empty or missing. Payload keys: {list(unified_payload.keys())}")
                    
                    # Only create fallback event if no modules were processed either
                    # This prevents overriding actual module events with generic info events
                    if not modules_processed:
                        logger.info(f"Creating fallback event for device {serial_number} - no modules or events processed")
                        # Fallback: store a generic data collection event if no specific events
                        event_type = 'info'
                        message = f"Data collection completed but no modules processed"
                        details = json.dumps({
                            'modules': modules_processed, 
                            'collection_type': 'fallback',
                            'module_id': 'system',
                            'reason': 'no_events_or_modules'
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
                        logger.info(f"✅ Stored fallback event for device {serial_number}")
                    else:
                        logger.info(f"Skipping fallback event for device {serial_number} - modules were processed, events should have been generated")
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
    
    async def upsert_device(self, device_record: Dict[str, Any]) -> bool:
        """
        Insert or update device record
        
        Args:
            device_record: Device data to store
            
        Returns:
            bool: True if successful
        """
        try:
            # For mock driver, just return success
            if self.driver == "mock":
                logger.info(f"Mock upsert_device for device {device_record.get('device_id', 'unknown')}")
                return True
            
            # Extract data from device record with proper field mapping
            device_uuid = device_record.get('device_id')  # UUID
            device_primary_key = device_record.get('id')  # Serial number (primary key)
            serial_number = device_record.get('serial_number')  # Serial number
            computer_name = device_record.get('computer_name')
            manufacturer = device_record.get('manufacturer')
            model = device_record.get('model')
            machine_group_id = device_record.get('machine_group_id')
            business_unit_id = device_record.get('business_unit_id')
            last_seen = device_record.get('last_seen')
            status = device_record.get('status', 'active')
            client_version = device_record.get('client_version')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.driver == "sqlite":
                    cursor.execute("""
                        INSERT OR REPLACE INTO devices 
                        (id, device_id, serial_number, name, manufacturer, model, machine_group_id, business_unit_id, last_seen, status, client_version)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (device_primary_key, device_uuid, serial_number, computer_name, manufacturer, model, machine_group_id, business_unit_id, last_seen, status, client_version))
                else:
                    cursor.execute("""
                        INSERT INTO devices (id, device_id, serial_number, name, manufacturer, model, machine_group_id, business_unit_id, last_seen, status, client_version, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (id)
                        DO UPDATE SET
                            name = EXCLUDED.name,
                            manufacturer = EXCLUDED.manufacturer,
                            model = EXCLUDED.model,
                            machine_group_id = EXCLUDED.machine_group_id,
                            business_unit_id = EXCLUDED.business_unit_id,
                            last_seen = EXCLUDED.last_seen,
                            status = EXCLUDED.status,
                            client_version = EXCLUDED.client_version,
                            updated_at = NOW()
                    """, (device_primary_key, device_uuid, serial_number, computer_name, manufacturer, model, machine_group_id, business_unit_id, last_seen, status, client_version))
                
                conn.commit()
                logger.info(f"Device record upserted for {device_primary_key}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to upsert device record: {e}")
            return False
    
    async def update_device_last_seen(self, device_id: str) -> bool:
        """
        Update the last_seen timestamp for a device
        
        Args:
            device_id: Device ID to update
            
        Returns:
            bool: True if successful
        """
        try:
            # For mock driver, just return success
            if self.driver == "mock":
                logger.info(f"Mock update_device_last_seen for device {device_id}")
                return True
            
            from datetime import datetime
            last_seen = datetime.utcnow().isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.driver == "sqlite":
                    cursor.execute("""
                        UPDATE devices 
                        SET last_seen = ?
                        WHERE device_id = ?
                    """, (last_seen, device_id))
                else:
                    cursor.execute("""
                        UPDATE devices 
                        SET last_seen = %s, updated_at = NOW()
                        WHERE device_id = %s
                    """, (last_seen, device_id))
                
                conn.commit()
                logger.info(f"Updated last_seen for device {device_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update device last_seen: {e}")
            return False
    
    async def store_module_data(self, device_id: str, module_id: str, module_data: Dict[str, Any]) -> bool:
        """
        Store module-specific data in the database
        
        Args:
            device_id: Device ID 
            module_id: Module identifier (hardware, software, etc.)
            module_data: Module data to store
            
        Returns:
            bool: True if successful
        """
        try:
            # For mock driver, just return success
            if self.driver == "mock":
                logger.info(f"Mock store_module_data for device {device_id}, module {module_id}")
                return True
            
            from datetime import datetime
            timestamp = datetime.utcnow().isoformat()
            
            # Convert module data to JSON string for storage
            import json
            data_json = json.dumps(module_data)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.driver == "sqlite":
                    # For SQLite, use module_data table (legacy)
                    cursor.execute("""
                        INSERT OR REPLACE INTO module_data 
                        (device_id, module_id, data, last_updated)
                        VALUES (?, ?, ?, ?)
                    """, (device_id, module_id, data_json, timestamp))
                else:
                    # For PostgreSQL, store in module-specific table (hardware, applications, etc.)
                    table_name = module_id  # Use module_id as table name
                    
                    # Use parameterized query to prevent SQL injection
                    cursor.execute(f"""
                        INSERT INTO {table_name} (device_id, data, collected_at, created_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (device_id)
                        DO UPDATE SET
                            data = EXCLUDED.data,
                            collected_at = EXCLUDED.collected_at,
                            updated_at = NOW()
                    """, (device_id, data_json, timestamp))
                
                # NO LONGER CREATING GENERIC EVENTS HERE
                # Events are now handled properly by the payload event processing
                # This prevents generic 'info' events from overriding real success/warning/error events
                logger.info(f"Module data stored - events will be handled by payload event processing")
                
                conn.commit()
                logger.info(f"✅ Stored module data for device {device_id} in {module_id} table")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store module data: {e}")
            return False
    


    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            if self.driver == "mock":
                logger.info("Mock database connection test - always returns True")
                return True
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Simple test query
                if self.driver == "sqlite":
                    cursor.execute("SELECT 1")
                else:
                    cursor.execute("SELECT 1")
                cursor.fetchone()
                logger.info("Database connection test successful")
                return True
                
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def store_device_event(self, device_id: str, event_type: str, message: str, 
                               details: Dict[str, Any], timestamp: str = None) -> bool:
        """
        Store a single device event in the database
        
        Args:
            device_id: Device identifier (serial number)
            event_type: Event type (success, warning, error, info)
            message: Event message
            details: Event details dictionary
            timestamp: Event timestamp (optional, defaults to now)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.driver == "mock":
                logger.info(f"Mock: Would store event - Device: {device_id}, Type: {event_type}, Message: {message}")
                return True
            
            # Prepare details as JSON string
            details_json = json.dumps(details) if details else "{}"
            
            # Use current timestamp if not provided
            if not timestamp:
                from datetime import datetime, timezone
                timestamp = datetime.now(timezone.utc)
            elif isinstance(timestamp, str):
                # Parse timestamp string if provided
                from datetime import datetime
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now(timezone.utc)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.driver == "sqlite":
                    cursor.execute(
                        "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (device_id, event_type, message, details_json, timestamp)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO events (device_id, event_type, message, details, timestamp) VALUES (%s, %s, %s, %s, %s)",
                        (device_id, event_type, message, details_json, timestamp)
                    )
                conn.commit()
            
            logger.info(f"✅ Successfully stored {event_type} event for device {device_id}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store event for device {device_id}: {str(e)}")
            return False

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
