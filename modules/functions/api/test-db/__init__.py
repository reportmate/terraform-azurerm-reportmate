"""
Simple database test endpoint
"""
import logging
import json
import azure.functions as func
import os

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test basic imports and environment
    """
    
    try:
        # Check if initialize flag is set
        initialize = req.params.get('init', '').lower() == 'true'
        
        if initialize:
            logger.info("Database initialization requested...")
            
            # Try to initialize database tables
            try:
                from shared.sync_database import SyncDatabaseManager
                db_manager = SyncDatabaseManager()
                
                # Create comprehensive database schema
                schema_sql = """
                -- Enable UUID extension for primary keys
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                
                -- Create devices table with comprehensive schema
                CREATE TABLE IF NOT EXISTS devices (
                    id VARCHAR(255) PRIMARY KEY,
                    device_id VARCHAR(255) UNIQUE,
                    name VARCHAR(500),
                    serial_number VARCHAR(100) UNIQUE,
                    hostname VARCHAR(255),
                    model VARCHAR(500),
                    os VARCHAR(255),
                    os_name VARCHAR(100),
                    os_version VARCHAR(100),
                    os_build VARCHAR(100),
                    os_architecture VARCHAR(50),
                    processor VARCHAR(500),
                    memory VARCHAR(100),
                    graphics VARCHAR(500),
                    storage VARCHAR(100),
                    architecture VARCHAR(50),
                    last_seen TIMESTAMP WITH TIME ZONE,
                    status VARCHAR(50) DEFAULT 'unknown',
                    ip_address VARCHAR(45),
                    mac_address VARCHAR(17),
                    uptime VARCHAR(100),
                    client_version VARCHAR(50),
                    location VARCHAR(255),
                    asset_tag VARCHAR(100),
                    total_events INTEGER DEFAULT 0,
                    last_event_time TIMESTAMP WITH TIME ZONE,
                    disk_utilization INTEGER,
                    memory_utilization INTEGER,
                    cpu_utilization INTEGER,
                    temperature INTEGER,
                    battery_level INTEGER,
                    boot_time TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );

                -- Create device_data table for raw JSON storage
                CREATE TABLE IF NOT EXISTS device_data (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    data_type VARCHAR(100) NOT NULL,
                    raw_data JSONB,
                    collected_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    CONSTRAINT device_data_unique UNIQUE(device_id, data_type)
                );

                -- Create events table for activity logging
                CREATE TABLE IF NOT EXISTS events (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    device_id VARCHAR(255) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    event_source VARCHAR(100),
                    event_data JSONB,
                    severity VARCHAR(20) DEFAULT 'info',
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );

                -- Create applications table
                CREATE TABLE IF NOT EXISTS applications (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    device_id VARCHAR(255) NOT NULL,
                    name VARCHAR(500) NOT NULL,
                    version VARCHAR(100),
                    publisher VARCHAR(500),
                    install_location TEXT,
                    install_date TIMESTAMP,
                    size_bytes BIGINT,
                    architecture VARCHAR(50),
                    source VARCHAR(100) DEFAULT 'unknown',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create hardware table
                CREATE TABLE IF NOT EXISTS hardware (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    device_id VARCHAR(255) NOT NULL UNIQUE,
                    manufacturer VARCHAR(200),
                    model VARCHAR(500),
                    serial_number VARCHAR(100),
                    asset_tag VARCHAR(100),
                    processor_name VARCHAR(500),
                    processor_cores INTEGER,
                    processor_speed_ghz DECIMAL(5,2),
                    memory_total_gb DECIMAL(10,2),
                    memory_available_gb DECIMAL(10,2),
                    storage_total_gb DECIMAL(10,2),
                    storage_available_gb DECIMAL(10,2),
                    graphics_card TEXT,
                    network_adapters TEXT,
                    bios_version VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create system_info table
                CREATE TABLE IF NOT EXISTS system_info (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    device_id VARCHAR(255) NOT NULL UNIQUE,
                    os_name VARCHAR(200),
                    os_version VARCHAR(100),
                    os_build VARCHAR(100),
                    os_architecture VARCHAR(50),
                    os_edition VARCHAR(100),
                    display_version VARCHAR(100),
                    install_date TIMESTAMP,
                    boot_time TIMESTAMP,
                    uptime_seconds BIGINT,
                    locale VARCHAR(20),
                    timezone VARCHAR(100),
                    hostname VARCHAR(200),
                    computer_name VARCHAR(200),
                    domain_name VARCHAR(200),
                    last_boot_time TIMESTAMP,
                    cpu_usage DECIMAL(5,2),
                    memory_usage DECIMAL(5,2),
                    disk_usage DECIMAL(5,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create comprehensive indexes
                CREATE INDEX IF NOT EXISTS idx_devices_serial_number ON devices(serial_number);
                CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
                CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
                CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
                CREATE INDEX IF NOT EXISTS idx_device_data_device_id ON device_data(device_id);
                CREATE INDEX IF NOT EXISTS idx_device_data_data_type ON device_data(data_type);
                CREATE INDEX IF NOT EXISTS idx_events_device_id ON events(device_id);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_applications_device_id ON applications(device_id);
                CREATE INDEX IF NOT EXISTS idx_applications_name ON applications(name);
                CREATE INDEX IF NOT EXISTS idx_hardware_device_id ON hardware(device_id);
                CREATE INDEX IF NOT EXISTS idx_system_info_device_id ON system_info(device_id);
                """
                
                with db_manager.get_connection() as conn:
                    if db_manager.driver == "psycopg2":
                        with conn.cursor() as cursor:
                            cursor.execute(schema_sql)
                            conn.commit()
                    elif db_manager.driver == "pg8000":
                        cursor = conn.cursor()
                        cursor.execute(schema_sql)
                        conn.commit()
                        cursor.close()
                
                # Verify tables were created
                with db_manager.get_connection() as conn:
                    if db_manager.driver == "psycopg2":
                        with conn.cursor() as cursor:
                            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
                            tables = [row[0] for row in cursor.fetchall()]
                    elif db_manager.driver == "pg8000":
                        cursor = conn.cursor()
                        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
                        tables = [row[0] for row in cursor.fetchall()]
                        cursor.close()
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'message': 'Database initialized successfully',
                        'driver': db_manager.driver,
                        'tables_created': ['devices', 'device_data'],
                        'all_tables': tables
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
                
            except Exception as init_error:
                logger.error(f"Database initialization failed: {init_error}")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': f'Database initialization failed: {str(init_error)}'
                    }),
                    status_code=500,
                    mimetype="application/json"
                )
        
        # Regular test functionality below
        # Test DATABASE_URL
        db_url = os.getenv('DATABASE_URL')
        db_url_present = bool(db_url)
        
        # Test psycopg2 import
        try:
            import psycopg2
            psycopg2_available = True
            psycopg2_version = psycopg2.__version__
        except Exception as e:
            psycopg2_available = False
            psycopg2_version = f"Error: {str(e)}"
        
        # Test asyncpg import
        try:
            import asyncpg
            asyncpg_available = True
            asyncpg_version = asyncpg.__version__
        except Exception as e:
            asyncpg_available = False
            asyncpg_version = f"Error: {str(e)}"
        
        # Test SyncDatabaseManager import
        sync_db_available = False
        sync_db_error = "Not tested"
        try:
            import sys
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from shared.sync_database import SyncDatabaseManager
            db_manager = SyncDatabaseManager()
            sync_db_available = True
            sync_db_error = f"Success - using {db_manager.driver} driver"
        except Exception as e:
            sync_db_error = str(e)
        
        # Test basic connection with psycopg2 directly
        connection_test = "Not attempted"
        if psycopg2_available and db_url:
            try:
                import psycopg2
                conn = psycopg2.connect(db_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                connection_test = f"Success: {result}"
            except Exception as e:
                connection_test = f"Failed: {str(e)}"
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Basic test successful',
                'database_url_present': db_url_present,
                'database_url_preview': db_url[:50] + "..." if db_url else None,
                'psycopg2_available': psycopg2_available,
                'psycopg2_version': psycopg2_version,
                'asyncpg_available': asyncpg_available,
                'asyncpg_version': asyncpg_version,
                'sync_db_available': sync_db_available,
                'sync_db_error': sync_db_error,
                'connection_test': connection_test
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }),
            status_code=500,
            mimetype="application/json"
        )
