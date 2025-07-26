"""
Database connection utilities for ReportMate API
"""

import logging
import os
import json
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections and provides connection pooling
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        # Check for both possible environment variable names
        self.connection_string = os.getenv('DATABASE_CONNECTION_STRING') or os.getenv('DATABASE_URL')
        
    async def initialize_pool(self):
        """Initialize the connection pool"""
        if not self.connection_string:
            raise ValueError("DATABASE_CONNECTION_STRING or DATABASE_URL environment variable not set")
        
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
    
    # Generic database query methods
    async def fetch_one(self, query: str, *params) -> Optional[Dict[str, Any]]:
        """Execute a query and return a single row as a dictionary"""
        connection = await self.get_connection()
        try:
            row = await connection.fetchrow(query, *params)
            return dict(row) if row else None
        finally:
            await self.release_connection(connection)
    
    async def fetch_all(self, query: str, *params) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as dictionaries"""
        connection = await self.get_connection()
        try:
            rows = await connection.fetch(query, *params)
            return [dict(row) for row in rows]
        finally:
            await self.release_connection(connection)
    
    async def execute(self, query: str, *params) -> Optional[str]:
        """Execute a query and return the result"""
        connection = await self.get_connection()
        try:
            result = await connection.execute(query, *params)
            return result
        finally:
            await self.release_connection(connection)
    
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
        logger.info(f"Storing {module_id} data for device {device_id}")
        
        if module_id == 'printers':
            await self._store_printer_data(device_id, module_data)
        elif module_id == 'hardware':
            await self._store_hardware_data(device_id, module_data)
        elif module_id == 'applications':
            await self._store_applications_data(device_id, module_data)
        elif module_id == 'system':
            await self._store_system_data(device_id, module_data)
        elif module_id == 'security':
            await self._store_security_data(device_id, module_data)
        elif module_id == 'network':
            await self._store_network_data(device_id, module_data)
        elif module_id == 'inventory':
            await self._store_inventory_data(device_id, module_data)
        elif module_id == 'management':
            await self._store_management_data(device_id, module_data)
        elif module_id == 'profiles':
            await self._store_profiles_data(device_id, module_data)
        elif module_id == 'installs':
            await self._store_installs_data(device_id, module_data)
        elif module_id == 'displays':
            await self._store_displays_data(device_id, module_data)
        else:
            logger.warning(f"No storage implementation for module: {module_id}")
            # Store in generic module_data table as fallback
            await self._store_generic_module_data(device_id, module_id, module_data)
    
    async def _store_network_data(self, device_id: str, data: Dict[str, Any]):
        """Store network module data in database"""
        connection = await self.get_connection()
        try:
            # Store network data as JSONB in the network table
            query = """
                INSERT INTO network (device_id, data, collected_at, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (device_id) DO UPDATE SET
                    data = $2,
                    collected_at = $3,
                    updated_at = NOW()
            """
            
            # Extract collected_at from data if available
            collected_at = data.get('collectedAt') or data.get('collected_at')
            if collected_at and isinstance(collected_at, str):
                try:
                    from datetime import datetime
                    collected_at = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
                except:
                    collected_at = datetime.utcnow()
            else:
                collected_at = datetime.utcnow()
            
            await connection.execute(query, device_id, json.dumps(data), collected_at)
            
            logger.info(f"Successfully stored network data for device {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to store network data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)
    
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
        """Store hardware module data"""
        connection = await self.get_connection()
        try:
            logger.info(f"Storing hardware data for device {device_id}")
            
            # Extract hardware information from the data
            hardware_info = data.get('hardware_summary', {})
            system_info = data.get('system_info', {})
            
            # Upsert hardware record
            await connection.execute("""
                INSERT INTO hardware (
                    device_id, manufacturer, model, serial_number, asset_tag,
                    processor_name, processor_cores, processor_speed_ghz,
                    memory_total_gb, memory_available_gb, storage_total_gb, storage_available_gb,
                    graphics_card, network_adapters, bios_version, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW(), NOW())
                ON CONFLICT (device_id) DO UPDATE SET
                    manufacturer = EXCLUDED.manufacturer,
                    model = EXCLUDED.model,
                    serial_number = EXCLUDED.serial_number,
                    processor_name = EXCLUDED.processor_name,
                    processor_cores = EXCLUDED.processor_cores,
                    processor_speed_ghz = EXCLUDED.processor_speed_ghz,
                    memory_total_gb = EXCLUDED.memory_total_gb,
                    memory_available_gb = EXCLUDED.memory_available_gb,
                    storage_total_gb = EXCLUDED.storage_total_gb,
                    storage_available_gb = EXCLUDED.storage_available_gb,
                    graphics_card = EXCLUDED.graphics_card,
                    network_adapters = EXCLUDED.network_adapters,
                    bios_version = EXCLUDED.bios_version,
                    updated_at = NOW()
            """, 
            device_id,
            hardware_info.get('manufacturer', ''),
            hardware_info.get('model', ''),
            hardware_info.get('serial_number', ''),
            hardware_info.get('asset_tag', ''),
            hardware_info.get('processor_name', ''),
            hardware_info.get('processor_cores', 0),
            hardware_info.get('processor_speed_ghz', 0.0),
            hardware_info.get('memory_total_gb', 0.0),
            hardware_info.get('memory_available_gb', 0.0),
            hardware_info.get('storage_total_gb', 0.0),
            hardware_info.get('storage_available_gb', 0.0),
            hardware_info.get('graphics_card', ''),
            json.dumps(hardware_info.get('network_adapters', [])),
            hardware_info.get('bios_version', '')
            )
            
            logger.info(f"Stored hardware data for device {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to store hardware data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)
    
    async def _store_applications_data(self, device_id: str, data: Dict[str, Any]):
        """Store applications module data"""
        connection = await self.get_connection()
        try:
            logger.info(f"Storing applications data for device {device_id}")
            
            # Clear existing applications for this device
            await connection.execute("""
                DELETE FROM applications WHERE device_id = $1
            """, device_id)
            
            # Insert new applications data
            applications = data.get('installed_applications', [])
            
            for app in applications:
                await connection.execute("""
                    INSERT INTO applications (
                        device_id, name, version, publisher, install_location,
                        install_date, size_bytes, architecture, source, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """, 
                device_id,
                app.get('name', 'Unknown'),
                app.get('version', ''),
                app.get('publisher', ''),
                app.get('install_location', ''),
                app.get('install_date'),
                app.get('size', 0),
                app.get('architecture', ''),
                'osquery'
                )
            
            logger.info(f"Stored {len(applications)} applications for device {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to store applications data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)
    
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

    # Additional module storage methods
    async def _store_system_data(self, device_id: str, data: Dict[str, Any]):
        """Store system module data"""
        connection = await self.get_connection()
        try:
            await connection.execute("""
                INSERT INTO system_info (
                    device_id, os_name, os_version, os_build, os_architecture, os_edition,
                    display_version, install_date, boot_time, uptime_seconds, locale, timezone,
                    computer_name, domain_name, last_boot_time, cpu_usage, memory_usage, disk_usage
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                ON CONFLICT (device_id) DO UPDATE SET
                    os_name = EXCLUDED.os_name,
                    os_version = EXCLUDED.os_version,
                    os_build = EXCLUDED.os_build,
                    os_architecture = EXCLUDED.os_architecture,
                    os_edition = EXCLUDED.os_edition,
                    display_version = EXCLUDED.display_version,
                    install_date = EXCLUDED.install_date,
                    boot_time = EXCLUDED.boot_time,
                    uptime_seconds = EXCLUDED.uptime_seconds,
                    locale = EXCLUDED.locale,
                    timezone = EXCLUDED.timezone,
                    computer_name = EXCLUDED.computer_name,
                    domain_name = EXCLUDED.domain_name,
                    last_boot_time = EXCLUDED.last_boot_time,
                    cpu_usage = EXCLUDED.cpu_usage,
                    memory_usage = EXCLUDED.memory_usage,
                    disk_usage = EXCLUDED.disk_usage,
                    updated_at = NOW()
            """, 
            device_id,
            data.get('system_summary', {}).get('os_name', ''),
            data.get('system_summary', {}).get('os_version', ''),
            data.get('system_summary', {}).get('os_build', ''),
            data.get('system_summary', {}).get('architecture', ''),
            data.get('system_summary', {}).get('os_edition', ''),
            data.get('system_summary', {}).get('display_version', ''),
            data.get('system_summary', {}).get('install_date'),
            data.get('system_summary', {}).get('boot_time'),
            data.get('performance_metrics', {}).get('uptime_seconds', 0),
            data.get('localization', {}).get('locale', ''),
            data.get('localization', {}).get('timezone', ''),
            data.get('system_summary', {}).get('computer_name', ''),
            data.get('system_summary', {}).get('domain_name', ''),
            data.get('system_summary', {}).get('last_boot_time'),
            data.get('performance_metrics', {}).get('cpu_usage', 0.0),
            data.get('performance_metrics', {}).get('memory_usage', 0.0),
            data.get('performance_metrics', {}).get('disk_usage', 0.0)
            )
            logger.info(f"Stored system data for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to store system data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)
    
    async def _store_security_data(self, device_id: str, data: Dict[str, Any]):
        """Store security module data"""
        connection = await self.get_connection()
        try:
            await connection.execute("""
                INSERT INTO security (
                    device_id, antivirus_name, antivirus_version, antivirus_enabled, antivirus_updated,
                    firewall_enabled, tpm_enabled, tmp_version, encryption_enabled, encryption_method,
                    secure_boot_enabled, defender_enabled, last_scan_date, threats_detected
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (device_id) DO UPDATE SET
                    antivirus_name = EXCLUDED.antivirus_name,
                    antivirus_version = EXCLUDED.antivirus_version,
                    antivirus_enabled = EXCLUDED.antivirus_enabled,
                    antivirus_updated = EXCLUDED.antivirus_updated,
                    firewall_enabled = EXCLUDED.firewall_enabled,
                    tmp_enabled = EXCLUDED.tmp_enabled,
                    tmp_version = EXCLUDED.tmp_version,
                    encryption_enabled = EXCLUDED.encryption_enabled,
                    encryption_method = EXCLUDED.encryption_method,
                    secure_boot_enabled = EXCLUDED.secure_boot_enabled,
                    defender_enabled = EXCLUDED.defender_enabled,
                    last_scan_date = EXCLUDED.last_scan_date,
                    threats_detected = EXCLUDED.threats_detected,
                    updated_at = NOW()
            """, 
            device_id,
            data.get('antivirus', {}).get('name', ''),
            data.get('antivirus', {}).get('version', ''),
            data.get('antivirus', {}).get('enabled', False),
            data.get('antivirus', {}).get('last_updated'),
            data.get('firewall', {}).get('enabled', False),
            data.get('tpm', {}).get('enabled', False),
            data.get('tpm', {}).get('version', ''),
            data.get('encryption', {}).get('enabled', False),
            data.get('encryption', {}).get('method', ''),
            data.get('secure_boot', {}).get('enabled', False),
            data.get('defender', {}).get('enabled', False),
            data.get('defender', {}).get('last_scan_date'),
            data.get('threats', {}).get('detected_count', 0)
            )
            logger.info(f"Stored security data for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to store security data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)
    
    async def _store_generic_module_data(self, device_id: str, module_id: str, data: Dict[str, Any]):
        """Store module data in generic module_data table"""
        connection = await self.get_connection()
        try:
            await connection.execute("""
                INSERT INTO module_data (device_id, module_id, data, collected_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (device_id, module_id) DO UPDATE SET
                    data = EXCLUDED.data,
                    collected_at = EXCLUDED.collected_at,
                    updated_at = NOW()
            """, 
            device_id, module_id, json.dumps(data), data.get('collected_at', datetime.utcnow())
            )
            logger.info(f"Stored {module_id} data in generic table for device {device_id}")
        except Exception as e:
            logger.error(f"Failed to store {module_id} data for device {device_id}: {e}")
            raise
        finally:
            await self.release_connection(connection)

# Global database manager instance
db_manager = DatabaseManager()

async def get_db_connection():
    """Helper function to get a database connection"""
    return await db_manager.get_connection()

async def release_db_connection(connection):
    """Helper function to release a database connection"""
    await db_manager.release_connection(connection)
