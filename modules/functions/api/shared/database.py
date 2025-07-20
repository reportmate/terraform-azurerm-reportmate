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
    
    # Module data storage methods
    async def store_module_data(self, device_id: str, module_id: str, module_data: Dict[str, Any]):
        """Store processed module data in the appropriate tables"""
        if module_id == 'printer':
            await self._store_printer_data(device_id, module_data)
        elif module_id == 'hardware':
            await self._store_hardware_data(device_id, module_data)
        elif module_id == 'applications':
            await self._store_applications_data(device_id, module_data)
        # Add other modules as needed
        else:
            logger.warning(f"No storage implementation for module: {module_id}")
    
    async def _store_printer_data(self, device_id: str, data: Dict[str, Any]):
        """Store printer module data in database"""
        connection = await self.get_connection()
        try:
            # Store printers
            if 'printers' in data:
                await self._upsert_printers(connection, device_id, data['printers'])
            
            # Store print drivers
            if 'print_drivers' in data:
                await self._upsert_print_drivers(connection, device_id, data['print_drivers'])
            
            # Store print ports
            if 'print_ports' in data:
                await self._upsert_print_ports(connection, device_id, data['print_ports'])
            
            # Store print processors
            if 'print_processors' in data:
                await self._upsert_print_processors(connection, device_id, data['print_processors'])
            
            # Store print jobs
            if 'print_jobs' in data:
                await self._upsert_print_jobs(connection, device_id, data['print_jobs'])
            
            # Store spooler info
            if 'spooler_info' in data:
                await self._upsert_spooler_info(connection, device_id, data['spooler_info'])
            
            # Store policy settings
            if 'policy_settings' in data:
                await self._upsert_policy_settings(connection, device_id, data['policy_settings'])
                
            logger.info(f"Successfully stored printer data for device {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to store printer data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)
    
    async def _upsert_printers(self, connection, device_id: str, printers: List[Dict[str, Any]]):
        """Upsert printer information"""
        # First, delete existing printers for this device
        await connection.execute("DELETE FROM device_printers WHERE device_id = $1", device_id)
        
        # Insert new printer data
        for printer in printers:
            await connection.execute("""
                INSERT INTO device_printers (
                    device_id, name, share_name, port_name, driver_name, location, comment,
                    status, printer_status, is_shared, is_network, is_default, is_online,
                    server_name, manufacturer, model, device_type, connection_type, ip_address,
                    priority, enable_bidirectional, keep_printed_jobs, enable_dev_query,
                    install_date, properties, last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26)
            """, device_id, printer.get('name'), printer.get('share_name'), printer.get('port_name'),
                printer.get('driver_name'), printer.get('location'), printer.get('comment'),
                printer.get('status'), printer.get('printer_status'), printer.get('is_shared'),
                printer.get('is_network'), printer.get('is_default'), printer.get('is_online'),
                printer.get('server_name'), printer.get('manufacturer'), printer.get('model'),
                printer.get('device_type'), printer.get('connection_type'), printer.get('ip_address'),
                printer.get('priority'), printer.get('enable_bidirectional'), printer.get('keep_printed_jobs'),
                printer.get('enable_dev_query'), printer.get('install_date'), 
                json.dumps(printer.get('properties', {})), printer.get('last_updated'))
    
    async def _upsert_print_drivers(self, connection, device_id: str, drivers: List[Dict[str, Any]]):
        """Upsert print driver information"""
        await connection.execute("DELETE FROM device_print_drivers WHERE device_id = $1", device_id)
        
        for driver in drivers:
            await connection.execute("""
                INSERT INTO device_print_drivers (
                    device_id, name, version, environment, config_file, data_file, driver_path,
                    help_file, monitor_name, default_data_type, provider, driver_version,
                    driver_date, is_signed, dependent_files, last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """, device_id, driver.get('name'), driver.get('version'), driver.get('environment'),
                driver.get('config_file'), driver.get('data_file'), driver.get('driver_path'),
                driver.get('help_file'), driver.get('monitor_name'), driver.get('default_data_type'),
                driver.get('provider'), driver.get('driver_version'), driver.get('driver_date'),
                driver.get('is_signed'), driver.get('dependent_files'), driver.get('last_updated'))
    
    async def _upsert_print_ports(self, connection, device_id: str, ports: List[Dict[str, Any]]):
        """Upsert print port information"""
        await connection.execute("DELETE FROM device_print_ports WHERE device_id = $1", device_id)
        
        for port in ports:
            await connection.execute("""
                INSERT INTO device_print_ports (
                    device_id, name, port_type, description, is_network, is_local,
                    timeout_seconds, transmission_retry, print_monitor, configuration, last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, device_id, port.get('name'), port.get('port_type'), port.get('description'),
                port.get('is_network'), port.get('is_local'), port.get('timeout_seconds'),
                port.get('transmission_retry'), port.get('print_monitor'),
                json.dumps(port.get('configuration', {})), port.get('last_updated'))
    
    async def _upsert_print_processors(self, connection, device_id: str, processors: List[Dict[str, Any]]):
        """Upsert print processor information"""
        await connection.execute("DELETE FROM device_print_processors WHERE device_id = $1", device_id)
        
        for processor in processors:
            await connection.execute("""
                INSERT INTO device_print_processors (
                    device_id, name, environment, dll_name, supported_datatypes, last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """, device_id, processor.get('name'), processor.get('environment'),
                processor.get('dll_name'), processor.get('supported_datatypes'), processor.get('last_updated'))
    
    async def _upsert_print_jobs(self, connection, device_id: str, jobs: List[Dict[str, Any]]):
        """Upsert print job information"""
        # Clean up old jobs (keep only last 30 days)
        await connection.execute("""
            DELETE FROM device_print_jobs 
            WHERE device_id = $1 AND submitted_time < NOW() - INTERVAL '30 days'
        """, device_id)
        
        for job in jobs:
            await connection.execute("""
                INSERT INTO device_print_jobs (
                    device_id, printer_name, job_id, document_name, user_name, status,
                    submitted_time, total_pages, pages_printed, size_bytes, priority,
                    start_time, until_time, last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (device_id, printer_name, job_id, submitted_time) DO UPDATE SET
                    status = EXCLUDED.status,
                    pages_printed = EXCLUDED.pages_printed,
                    last_updated = EXCLUDED.last_updated
            """, device_id, job.get('printer_name'), job.get('job_id'), job.get('document_name'),
                job.get('user_name'), job.get('status'), job.get('submitted_time'),
                job.get('total_pages'), job.get('pages_printed'), job.get('size_bytes'),
                job.get('priority'), job.get('start_time'), job.get('until_time'), job.get('last_updated'))
    
    async def _upsert_spooler_info(self, connection, device_id: str, spooler_info: Dict[str, Any]):
        """Upsert print spooler information"""
        await connection.execute("""
            INSERT INTO device_print_spooler (
                device_id, service_status, service_start_type, default_spool_directory,
                beep_enabled, net_popup, log_events, restart_job_on_pool_error,
                restart_job_on_pool_enabled, port_thread_priority, scheduler_thread_priority,
                total_jobs, last_updated
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            ON CONFLICT (device_id) DO UPDATE SET
                service_status = EXCLUDED.service_status,
                service_start_type = EXCLUDED.service_start_type,
                default_spool_directory = EXCLUDED.default_spool_directory,
                beep_enabled = EXCLUDED.beep_enabled,
                net_popup = EXCLUDED.net_popup,
                log_events = EXCLUDED.log_events,
                restart_job_on_pool_error = EXCLUDED.restart_job_on_pool_error,
                restart_job_on_pool_enabled = EXCLUDED.restart_job_on_pool_enabled,
                port_thread_priority = EXCLUDED.port_thread_priority,
                scheduler_thread_priority = EXCLUDED.scheduler_thread_priority,
                total_jobs = EXCLUDED.total_jobs,
                last_updated = EXCLUDED.last_updated
        """, device_id, spooler_info.get('service_status'), spooler_info.get('service_start_type'),
            spooler_info.get('default_spool_directory'), spooler_info.get('beep_enabled'),
            spooler_info.get('net_popup'), spooler_info.get('log_events'),
            spooler_info.get('restart_job_on_pool_error'), spooler_info.get('restart_job_on_pool_enabled'),
            spooler_info.get('port_thread_priority'), spooler_info.get('scheduler_thread_priority'),
            spooler_info.get('total_jobs'), spooler_info.get('last_updated'))
    
    async def _upsert_policy_settings(self, connection, device_id: str, policy_settings: Dict[str, Any]):
        """Upsert print policy settings"""
        await connection.execute("""
            INSERT INTO device_print_policies (
                device_id, disable_web_printing, disable_server_thread, disable_spooler_open_printers,
                spooler_priority, spooler_max_job_schedule, enable_logging, log_level,
                restrict_driver_installation, group_policy_settings, last_updated
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (device_id) DO UPDATE SET
                disable_web_printing = EXCLUDED.disable_web_printing,
                disable_server_thread = EXCLUDED.disable_server_thread,
                disable_spooler_open_printers = EXCLUDED.disable_spooler_open_printers,
                spooler_priority = EXCLUDED.spooler_priority,
                spooler_max_job_schedule = EXCLUDED.spooler_max_job_schedule,
                enable_logging = EXCLUDED.enable_logging,
                log_level = EXCLUDED.log_level,
                restrict_driver_installation = EXCLUDED.restrict_driver_installation,
                group_policy_settings = EXCLUDED.group_policy_settings,
                last_updated = EXCLUDED.last_updated
        """, device_id, policy_settings.get('disable_web_printing'),
            policy_settings.get('disable_server_thread'), policy_settings.get('disable_spooler_open_printers'),
            policy_settings.get('spooler_priority'), policy_settings.get('spooler_max_job_schedule'),
            policy_settings.get('enable_logging'), policy_settings.get('log_level'),
            policy_settings.get('restrict_driver_installation'),
            json.dumps(policy_settings.get('group_policy_settings', {})), policy_settings.get('last_updated'))
    
    async def _store_hardware_data(self, device_id: str, data: Dict[str, Any]):
        """Store hardware module data (placeholder)"""
        # TODO: Implement hardware data storage
        logger.info(f"Hardware data storage not yet implemented for device {device_id}")
    
    async def _store_applications_data(self, device_id: str, data: Dict[str, Any]):
        """Store applications module data (placeholder)"""
        # TODO: Implement applications data storage
        logger.info(f"Applications data storage not yet implemented for device {device_id}")
    
    async def upsert_device(self, device_record: Dict[str, Any]):
        """Upsert device record"""
        connection = await self.get_connection()
        try:
            await connection.execute("""
                INSERT INTO devices (device_id, computer_name, manufacturer, model, 
                                   machine_group_id, business_unit_id, last_seen, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (device_id) DO UPDATE SET
                    computer_name = EXCLUDED.computer_name,
                    manufacturer = EXCLUDED.manufacturer,
                    model = EXCLUDED.model,
                    last_seen = EXCLUDED.last_seen,
                    status = EXCLUDED.status
            """, device_record['device_id'], device_record['computer_name'],
                device_record['manufacturer'], device_record['model'],
                device_record.get('machine_group_id'), device_record.get('business_unit_id'),
                device_record['last_seen'], device_record['status'])
        finally:
            await self.release_connection(connection)
    
    async def update_device_last_seen(self, device_id: str):
        """Update device last seen timestamp"""
        connection = await self.get_connection()
        try:
            await connection.execute("""
                UPDATE devices SET last_seen = NOW() WHERE device_id = $1
            """, device_id)
        finally:
            await self.release_connection(connection)
    
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
