import azure.functions as func
import json
import logging
import pg8000
import re
from datetime import datetime, timezone, timedelta
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import calculate_device_status

logger = logging.getLogger(__name__)

def handle_device_registration(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle device registration requests from Windows client
    """
    logger.info("=== DEVICE REGISTRATION API ===")
    
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
        logger.info(f"Parsed device data. Keys: {list(device_data.keys())}")
        
        # Extract registration data from Windows client
        device_id = device_data.get('device', '') or device_data.get('deviceId', '')
        serial_number = device_data.get('serialNumber', '') or device_data.get('SerialNumber', '')
        computer_name = device_data.get('computerName', '') or device_data.get('ComputerName', '')
        model = device_data.get('model', '') or device_data.get('Model', '')
        os_name = device_data.get('os', '') or device_data.get('OperatingSystem', '')
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
            # Connect to database
            conn = pg8000.connect(**conn_params)
            cursor = conn.cursor()
            
            # Look up device by serial number (which is the primary key 'id')
            device_query = """
                SELECT 
                    id, device_id, name, serial_number, os, status, last_seen, 
                    model, manufacturer, created_at, updated_at
                FROM devices 
                WHERE id = %s OR serial_number = %s
                LIMIT 1
            """
            
            cursor.execute(device_query, (serial_number, serial_number))
            device_row = cursor.fetchone()
            
            if not device_row:
                cursor.close()
                conn.close()
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Device not found',
                        'details': f'No device found with serial number: {serial_number}'
                    }),
                    status_code=404,
                    mimetype="application/json"
                )
            
            # Extract device information and calculate dynamic status from latest module data
            last_seen_time = device_row[6]  # last_seen timestamp
            
            # Get module data for this device from all modular tables
            # These are the exact same tables that /api/events stores data into
            valid_modules = [
                'applications', 'displays', 'hardware', 'installs', 'inventory',
                'management', 'network', 'printers', 'profiles', 'security', 'system'
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
                    cursor.execute(module_query, (device_row[0],))  # Use id (serial number)
                    module_row = cursor.fetchone()
                    
                    if module_row and module_row[0]:  # If we have data
                        module_data = module_row[0]  # JSON data
                        
                        # Add collectedAt timestamp to module data for status calculation
                        if module_row[1]:  # collected_at from database
                            module_data['collectedAt'] = module_row[1].isoformat()
                            
                            # Track the latest collection time across all modules
                            if not latest_collection_time or module_row[1] > latest_collection_time:
                                latest_collection_time = module_row[1]
                        
                        modules[module_name] = module_data
                        logger.info(f"✅ Retrieved {module_name} data for device {device_row[0]}")
                    else:
                        logger.info(f"⚠️ No {module_name} data found for device {device_row[0]}")
                        
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
            cursor.execute(events_query, (device_row[1],))  # Use device_id (UUID)
            recent_events = [{'event_type': row[0], 'created_at': row[1]} for row in cursor.fetchall()]
            
            # Calculate status using latest collection time and recent events
            calculated_status = calculate_device_status(latest_collection_time or last_seen_time, recent_events)
            
            device_data = {
                'id': device_row[0],  # id (serial number)
                'deviceId': device_row[1],  # device_id (ReportMate internal UUID)
                'name': device_row[2],
                'serialNumber': device_row[3],
                'os': device_row[4],
                'status': calculated_status,  # Now calculated from latest module data!
                'lastSeen': last_seen_time.isoformat() if last_seen_time else None,
                'model': device_row[7],
                'manufacturer': device_row[8],
                'createdAt': device_row[9].isoformat() if device_row[9] else None,
                'updatedAt': device_row[10].isoformat() if device_row[10] else None
            }
            
            # Build metadata with the latest collection time from any module
            metadata = {
                'deviceId': device_data['deviceId'],
                'serialNumber': device_data['serialNumber'],
                'collectedAt': latest_collection_time.isoformat() if latest_collection_time else device_data['lastSeen'],
                'clientVersion': '1.0.0'  # Default version
            }
            
            cursor.close()
            conn.close()
            
            # Return device data in the expected format
            response_data = {
                'success': True,
                'metadata': metadata,
                **modules  # Spread modules at the top level
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
    """Main entry point for the device API"""
    if req.method == 'POST':
        return handle_device_registration(req)
    elif req.method == 'GET':
        return handle_device_lookup(req)
    else:
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {req.method} not supported. Use POST for device registration or GET for device lookup.'
            }),
            status_code=405,
            mimetype="application/json"
        )
