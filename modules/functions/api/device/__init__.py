import azure.functions as func
import json
import logging
import re
from datetime import datetime, timezone, timedelta
import os
import sys
import asyncio

# Add the parent directory to the path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import modules with absolute path resolution
from shared.utils import calculate_device_status
from processor import DeviceDataProcessor
from shared.database import DatabaseManager
from shared.auth import AuthenticationManager

logger = logging.getLogger(__name__)

async def handle_device_data_ingestion(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle complete device data ingestion from Windows client
    Uses DeviceDataProcessor to process all modules including installs
    """
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"[{timestamp}] === DEVICE DATA INGESTION API ===")
    
    try:
        # Get request body
        req_body = req.get_body()
        if not req_body:
            logger.warning("Empty request body received")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Empty request body',
                    'message': 'No data received'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Decode and parse JSON
        body_str = req_body.decode('utf-8')
        logger.info(f"Request body size: {len(body_str)} characters")
        
        device_data = json.loads(body_str)
        logger.info(f"Parsed device data. Top-level keys: {list(device_data.keys())}")
        
        # Check for authentication passphrase
        passphrase = device_data.get('passphrase') or device_data.get('Passphrase') or req.headers.get('X-API-PASSPHRASE')
        if not passphrase:
            # Try to get default passphrase from environment
            passphrase = os.environ.get('DEFAULT_MACHINE_GROUP_PASSPHRASE', 's3cur3-p@ssphras3!')
            logger.info("Using default passphrase for device data processing")
        
        # Extract device identification for logging
        serial_number = None
        device_id = None
        
        # PRIMARY: Check metadata section (Windows client structure)
        if 'metadata' in device_data and device_data['metadata']:
            metadata = device_data['metadata']
            serial_number = metadata.get('serialNumber') or metadata.get('SerialNumber')
            device_id = metadata.get('deviceId') or metadata.get('DeviceId')
        
        # FALLBACK 1: Try to extract from payload wrapper (if present)
        if not serial_number and 'payload' in device_data and device_data['payload']:
            payload = device_data['payload']
            if 'device' in payload and payload['device']:
                device_dict = payload['device']
                serial_number = device_dict.get('serialNumber') or device_dict.get('SerialNumber')
                device_id = device_dict.get('deviceId') or device_dict.get('DeviceId')
        
        # FALLBACK 2: Check top-level fields
        if not serial_number:
            serial_number = device_data.get('serialNumber') or device_data.get('SerialNumber') or device_data.get('device')
        if not device_id:
            device_id = device_data.get('deviceId') or device_data.get('DeviceId')
        
        logger.info(f"Processing device data - Serial: {serial_number}, DeviceId: {device_id}")
        
        # Initialize database and authentication managers
        db_manager = DatabaseManager()
        auth_manager = AuthenticationManager()
        
        # Initialize the device data processor
        processor = DeviceDataProcessor(db_manager, auth_manager)
        
        # Process the device data through all module processors
        if serial_number:
            # Use the process_device_data_with_device_id method for explicit device identification
            logger.info(f"Processing with explicit device_id: {serial_number}")
            result = await processor.process_device_data_with_device_id(
                device_data, 
                passphrase, 
                serial_number
            )
        else:
            # Use the standard process_device_data method
            logger.info("Processing with automatic device identification")
            result = await processor.process_device_data(device_data, passphrase)
        
        if result['success']:
            logger.info(f"✅ Device data processing completed successfully")
            logger.info(f"   Device ID: {result.get('device_id', 'Unknown')}")
            logger.info(f"   Modules processed: {result.get('modules_processed', 0)}")
            logger.info(f"   Modules failed: {result.get('modules_failed', 0)}")
            
            if result.get('processing_errors'):
                logger.warning(f"Processing errors encountered: {result['processing_errors']}")
            
            # Return success response
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Device data processed successfully',
                    'device_id': result.get('device_id'),
                    'modules_processed': result.get('modules_processed', 0),
                    'modules_failed': result.get('modules_failed', 0),
                    'timestamp': timestamp,
                    'processing_summary': result.get('summary', {}),
                    'storage_result': result.get('storage_result', {})
                }),
                status_code=200,
                mimetype="application/json"
            )
        else:
            logger.error(f"❌ Device data processing failed: {result.get('error', 'Unknown error')}")
            logger.error(f"   Details: {result.get('details', 'No details provided')}")
            
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': result.get('error', 'Processing failed'),
                    'details': result.get('details', 'Unknown error during processing'),
                    'timestamp': timestamp
                }),
                status_code=500,
                mimetype="application/json"
            )
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Invalid JSON format',
                'details': str(e),
                'timestamp': timestamp
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error during device data ingestion: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e),
                'timestamp': timestamp
            }),
            status_code=500,
            mimetype="application/json"
        )
        manufacturer = device_data.get('manufacturer', '') or device_data.get('Manufacturer', '')
        
        logger.info(f"Registration data: device_id={device_id}, serial={serial_number}, name={computer_name}")
        
        # Validate required fields
        if not device_id or not serial_number:
            missing_fields = []
            if not device_id:
                missing_fields.append('deviceId')
            if not serial_number:
                missing_fields.append('serialNumber')
            
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Both deviceId and serialNumber are required for device registration',
                    'details': f'Missing fields: {", ".join(missing_fields)}'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Database connection parameters from DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database configuration missing',
                    'details': 'DATABASE_URL environment variable not found'
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse DATABASE_URL: postgresql://user:password@host:port/database?sslmode=require
        url_pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)'
        match = re.match(url_pattern, database_url)
        if not match:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Invalid database URL format',
                    'details': 'Could not parse DATABASE_URL'
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        db_user, db_password, db_host, db_port, db_name = match.groups()
        conn_params = {
            'host': db_host,
            'database': db_name,
            'user': db_user,
            'password': db_password,
            'port': int(db_port),
            'ssl_context': True  # Enable SSL for Azure PostgreSQL
        }
        
        try:
            # Connect to database
            conn = pg8000.connect(**conn_params)
            cursor = conn.cursor()
            current_time = datetime.utcnow()
            
            # Log the values being inserted for debugging
            logger.info(f"Inserting device registration:")
            logger.info(f"  id (serial_number): '{serial_number}'")
            logger.info(f"  device_id: '{device_id}'")
            logger.info(f"  name: '{computer_name}'")
            logger.info(f"  serial_number: '{serial_number}'")
            logger.info(f"  os: '{os_name}'")
            logger.info(f"  model: '{model}'")
            logger.info(f"  manufacturer: '{manufacturer}'")
            
            # Use UPSERT with comprehensive conflict handling
            device_query = """
                INSERT INTO devices (
                    id, device_id, name, serial_number, os, status, last_seen, 
                    model, manufacturer, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) 
                DO UPDATE SET 
                    device_id = EXCLUDED.device_id,
                    name = EXCLUDED.name,
                    os = EXCLUDED.os,
                    model = EXCLUDED.model,
                    manufacturer = EXCLUDED.manufacturer,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = EXCLUDED.updated_at,
                    status = EXCLUDED.status
            """
            
            cursor.execute(device_query, (
                serial_number,      # id (serial number as primary key)
                device_id,          # device_id (ReportMate internal UUID)
                computer_name,      # name
                serial_number,      # serial_number (same as id)
                os_name,           # os
                'active',          # status
                current_time,      # last_seen
                model,             # model
                manufacturer,      # manufacturer
                current_time,      # created_at
                current_time       # updated_at
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Device {serial_number} registered successfully")
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Device registered successfully',
                    'deviceId': device_id,
                    'serialNumber': serial_number,
                    'registered_at': current_time.isoformat()
                }),
                status_code=200,
                mimetype="application/json"
            )
            
        except Exception as reg_error:
            logger.error(f"❌ Device registration failed: {reg_error}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device registration failed',
                    'details': str(reg_error)
                }),
                status_code=500,
                mimetype="application/json"
            )
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Invalid JSON format',
                'details': str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in device registration: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

def handle_device_lookup(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle device lookup requests (GET /api/device/{serial_number})
    """
    logger.info("=== DEVICE LOOKUP API ===")
    
    try:
        # Get the serial number from the route
        serial_number = req.route_params.get('serial_number')
        
        if not serial_number:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Serial number required',
                    'details': 'Device serial number must be provided in the URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Looking up device with serial number: {serial_number}")
        
        # Database connection parameters from DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database configuration missing',
                    'details': 'DATABASE_URL environment variable not found'
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse DATABASE_URL
        url_pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/([^?]+)'
        match = re.match(url_pattern, database_url)
        if not match:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Invalid database URL format',
                    'details': 'Could not parse DATABASE_URL'
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        db_user, db_password, db_host, db_port, db_name = match.groups()
        conn_params = {
            'host': db_host,
            'database': db_name,
            'user': db_user,
            'password': db_password,
            'port': int(db_port),
            'ssl_context': True  # Enable SSL for Azure PostgreSQL
        }
        
        try:
            # Use DatabaseManager instead of direct connection
            db_manager = DatabaseManager()
            
            # Look up device by serial number (which is the primary key 'id')
            device_query = """
                SELECT 
                    id, device_id, name, serial_number, os, status, last_seen, 
                    model, manufacturer, created_at, updated_at
                FROM devices 
                WHERE id = %s OR serial_number = %s
                LIMIT 1
            """
            
            device_result = db_manager.execute_query(device_query, (serial_number, serial_number))
            
            if not device_result:
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Device not found',
                        'details': f'No device found with serial number: {serial_number}'
                    }),
                    status_code=404,
                    mimetype="application/json"
                )
            
            device_row = device_result[0]
            # Extract device information and calculate dynamic status from latest module data
            last_seen_time = device_row.get('last_seen')  # last_seen timestamp
            
            # Get module data for this device from all modular tables
            # These are the exact same tables that /api/events stores data into
            valid_modules = [
                'applications', 'displays', 'hardware', 'installs', 'inventory',
                'management', 'network', 'peripherals', 'printers', 'profiles', 'security', 'system'
            ]
            
            modules = {}
            latest_collection_time = None
            
            # Query each module table for this device's data
            for module_name in valid_modules:
                module_query = f"""
                    SELECT data, collected_at, created_at
                    FROM {module_name} 
                    WHERE device_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                
                try:
                    module_result = db_manager.execute_query(module_query, (device_row['id'],))  # Use id (serial number)
                    
                    if module_result and module_result[0].get('data'):  # If we have data
                        module_data = module_result[0]['data']  # JSON data
                        collected_at = module_result[0].get('collected_at')
                        
                        # Add collectedAt timestamp to module data for status calculation
                        if collected_at:  # collected_at from database
                            module_data['collectedAt'] = collected_at.isoformat() if hasattr(collected_at, 'isoformat') else str(collected_at)
                            
                            # Track the latest collection time across all modules
                            if not latest_collection_time or collected_at > latest_collection_time:
                                latest_collection_time = collected_at
                        
                        modules[module_name] = module_data
                        logger.info(f"✅ Retrieved {module_name} data for device {device_row['id']}")
                    else:
                        logger.info(f"⚠️ No {module_name} data found for device {device_row['id']}")
                        
                except Exception as module_error:
                    logger.warning(f"❌ Failed to query {module_name} table: {module_error}")
                    # Continue with other modules even if one fails
                    continue
            
            # Get recent events for status calculation (last 24 hours)
            events_query = """
                SELECT event_type, created_at
                FROM events 
                WHERE device_id = (SELECT id FROM devices WHERE device_id = %s)
                AND created_at >= NOW() - INTERVAL '24 hours'
                AND event_type IN ('warning', 'error')
                ORDER BY created_at DESC
                LIMIT 10
            """
            recent_events_result = db_manager.execute_query(events_query, (device_row['device_id'],))  # Use device_id (UUID)
            recent_events = [{'event_type': row['event_type'], 'created_at': row['created_at']} for row in recent_events_result]
            
            # Calculate status using latest collection time (function only takes one parameter)
            calculated_status = calculate_device_status(latest_collection_time or last_seen_time)
            
            device_data = {
                'id': device_row['id'],  # id (serial number)
                'deviceId': device_row['device_id'],  # device_id (ReportMate internal UUID)
                'name': device_row['name'],
                'serialNumber': device_row['serial_number'],
                'os': device_row['os'],
                'status': calculated_status,  # Now calculated from latest module data!
                'lastSeen': last_seen_time.isoformat() if hasattr(last_seen_time, 'isoformat') else str(last_seen_time) if last_seen_time else None,
                'model': device_row.get('model'),
                'manufacturer': device_row.get('manufacturer'),
                'createdAt': device_row['created_at'].isoformat() if device_row.get('created_at') and hasattr(device_row['created_at'], 'isoformat') else str(device_row.get('created_at')) if device_row.get('created_at') else None,
                'updatedAt': device_row['updated_at'].isoformat() if device_row.get('updated_at') and hasattr(device_row['updated_at'], 'isoformat') else str(device_row.get('updated_at')) if device_row.get('updated_at') else None
            }
            
            # Extract clientVersion from collected module data (look across all modules for version info)
            client_version = None  # No fallback - if not collected, keep empty
            
            # Look for version information in module data
            for module_name, module_data in modules.items():
                if isinstance(module_data, dict):
                    # Check for clientVersion in module metadata
                    if 'clientVersion' in module_data:
                        client_version = module_data['clientVersion']
                        break
                    # Check for version in various formats
                    elif 'version' in module_data:
                        client_version = module_data['version']
                        break
                    # Check nested metadata
                    elif 'metadata' in module_data and isinstance(module_data['metadata'], dict):
                        if 'clientVersion' in module_data['metadata']:
                            client_version = module_data['metadata']['clientVersion']
                            break
                        elif 'version' in module_data['metadata']:
                            client_version = module_data['metadata']['version']
                            break
            
            # Return device data in the expected clean format for frontend (matching sample-api.json)
            response_data = {
                'success': True,
                'device': {
                    'deviceId': device_data['deviceId'],
                    'serialNumber': device_data['serialNumber'],
                    'lastSeen': device_data['lastSeen'],
                    'createdAt': device_data['createdAt'],  # Registration date
                    'clientVersion': client_version,
                    'modules': modules
                }
            }
            
            logger.info(f"✅ Device lookup successful for {serial_number}")
            
            return func.HttpResponse(
                json.dumps(response_data),
                status_code=200,
                mimetype="application/json"
            )
            
        except Exception as lookup_error:
            logger.error(f"❌ Device lookup failed: {lookup_error}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device lookup failed',
                    'details': str(lookup_error)
                }),
                status_code=500,
                mimetype="application/json"
            )
    
    except Exception as e:
        logger.error(f"Unexpected error in device lookup: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Main entry point for the enhanced device data ingestion API"""
    if req.method == 'POST':
        # Use async handler for POST requests (device data ingestion)
        return asyncio.run(handle_device_data_ingestion(req))
    elif req.method == 'GET':
        return handle_device_lookup(req)
    else:
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {req.method} not supported. Use POST for device data ingestion or GET for device lookup.'
            }),
            status_code=405,
            mimetype="application/json"
        )
