"""
Database connection utilities for ReportMate API
"""

import logging
import os
import asyncpg
from typing import Optional, Dict, Any, List
import asyncio

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections and provides connection pooling
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.connection_string = os.getenv('DATABASE_CONNECTION_STRING')
        
    async def initialize_pool(self):
        """Initialize the connection pool"""
        if not self.connection_string:
            raise ValueError("DATABASE_CONNECTION_STRING environment variable not set")
        
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool"""
        if not self.pool:
            await self.initialize_pool()
        return await self.pool.acquire()
    
    async def release_connection(self, connection: asyncpg.Connection):
        """Release a connection back to the pool"""
        if self.pool:
            await self.pool.release(connection)
    
    async def close_pool(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")
    
    # Device-related methods
    async def get_devices(self, limit: int = 50, offset: int = 0, machine_group: str = '', 
                         business_unit: str = '', status: str = '') -> List[Dict[str, Any]]:
        """Get devices with filtering and pagination"""
        connection = await self.get_connection()
        try:
            query = """
                SELECT * FROM devices 
                WHERE ($3 = '' OR machine_group = $3)
                AND ($4 = '' OR business_unit = $4)
                AND ($5 = '' OR status = $5)
                ORDER BY last_seen DESC
                LIMIT $1 OFFSET $2
            """
            rows = await connection.fetch(query, limit, offset, machine_group, business_unit, status)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(connection)
    
    async def get_devices_count(self, machine_group: str = '', business_unit: str = '', status: str = '') -> int:
        """Get total count of devices with filtering"""
        connection = await self.get_connection()
        try:
            query = """
                SELECT COUNT(*) FROM devices 
                WHERE ($1 = '' OR machine_group = $1)
                AND ($2 = '' OR business_unit = $2)
                AND ($3 = '' OR status = $3)
            """
            result = await connection.fetchval(query, machine_group, business_unit, status)
            return result or 0
        finally:
            await self.release_connection(connection)
    
    async def get_device_details(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM devices WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    # Module-specific methods
    async def get_device_applications(self, device_id: str, limit: int = 50, offset: int = 0, 
                                    search: str = '', category: str = '') -> List[Dict[str, Any]]:
        """Get applications for a specific device"""
        connection = await self.get_connection()
        try:
            query = """
                SELECT * FROM device_applications 
                WHERE device_id = $1
                AND ($4 = '' OR name ILIKE '%' || $4 || '%')
                AND ($5 = '' OR category = $5)
                ORDER BY name
                LIMIT $2 OFFSET $3
            """
            rows = await connection.fetch(query, device_id, limit, offset, search, category)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(connection)
    
    async def get_device_hardware(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get hardware information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_hardware WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_security(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get security information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_security WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_network(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get network information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_network WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_system(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get system information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_system WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_inventory(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_inventory WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_management(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get management information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_management WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_profiles(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get profiles information for a specific device"""
        connection = await self.get_connection()
        try:
            query = "SELECT * FROM device_profiles WHERE device_id = $1"
            row = await connection.fetchrow(query, device_id)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def get_device_installs(self, device_id: str, limit: int = 50, offset: int = 0, 
                                status_filter: str = '') -> List[Dict[str, Any]]:
        """Get installs information for a specific device"""
        connection = await self.get_connection()
        try:
            query = """
                SELECT * FROM device_installs 
                WHERE device_id = $1
                AND ($4 = '' OR status = $4)
                ORDER BY install_date DESC
                LIMIT $2 OFFSET $3
            """
            rows = await connection.fetch(query, device_id, limit, offset, status_filter)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(connection)
    
    # Global/Analytics methods (placeholder implementations)
    async def get_global_applications(self, limit: int, offset: int, search: str = '', 
                                    category: str = '', publisher: str = '', 
                                    sort_by: str = 'name', sort_order: str = 'asc') -> List[Dict[str, Any]]:
        """Get global applications across all devices"""
        # Placeholder implementation
        return []
    
    async def get_fleet_overview(self, business_unit: str = '') -> Dict[str, Any]:
        """Get high-level fleet overview metrics"""
        # Placeholder implementation
        return {
            'total_devices': 0,
            'active_devices': 0,
            'inactive_devices': 0,
            'new_devices_30d': 0
        }
    
    async def get_device_statistics(self, start_date, end_date, business_unit: str = '') -> Dict[str, Any]:
        """Get detailed device statistics"""
        # Placeholder implementation
        return {
            'online_percentage': 0,
            'average_uptime': 0,
            'performance_scores': {}
        }

# Global database manager instance
db_manager = DatabaseManager()

async def get_db_connection():
    """Helper function to get a database connection"""
    return await db_manager.get_connection()

async def release_db_connection(connection):
    """Helper function to release a database connection"""
    await db_manager.release_connection(connection)
