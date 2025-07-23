import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sync_database import SyncDatabaseManager

# Simple logging setup
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main entry point for device data ingestion (POST) and retrieval (GET)
    
    POST: Device data ingestion from Windows clients
    GET: Retrieve individual device information by serial number
    """
    
    logger.info("=== REPORTMATE DEVICE API ===")
    logger.info(f"Method: {req.method}")
    logger.info(f"URL: {req.url}")
    
    # Handle GET requests for device retrieval
    if req.method == 'GET':
        return handle_get_device(req)
    
    # Handle POST requests for device data ingestion
    elif req.method == 'POST':
        return handle_post_device(req)
    
    else:
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {req.method} not supported. Use GET or POST.'
            }),
            status_code=405,
            mimetype="application/json"
        )

def handle_get_device(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle GET requests to retrieve device information by serial number
    URL format: /api/device/{serial_number}
    """
    try:
        # Get serial number from route parameter
        serial_number = req.route_params.get('serial_number')
        
        if not serial_number:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Serial number required',
                    'details': 'URL must include device serial number: /api/device/{serial_number}'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Retrieving device information for serial: {serial_number}")
        
        # Initialize database manager
        db_manager = SyncDatabaseManager()
        
        try:
            with db_manager.get_connection() as conn:
                # Get device from database
                device_query = """
                    SELECT 
                        id, device_id, name, serial_number, hostname, model, os, os_name, os_version,
                        processor, memory, storage, architecture, last_seen, status, ip_address,
                        mac_address, uptime, client_version, location, asset_tag, created_at, updated_at
                    FROM devices 
                    WHERE serial_number = %s OR id = %s
                    LIMIT 1
                """
                
                cursor = conn.cursor()
                cursor.execute(device_query, (serial_number, serial_number))
                device_result = cursor.fetchone()
                
                if not device_result:
                    cursor.close()
                    return func.HttpResponse(
                        json.dumps({
                            'success': False,
                            'error': 'Device not found',
                            'details': f'No device found with serial number: {serial_number}'
                        }),
                        status_code=404,
                        mimetype="application/json"
                    )
                
                # Convert result to dictionary (assuming column order matches the SELECT)
                columns = ['id', 'device_id', 'name', 'serial_number', 'hostname', 'model', 'os', 
                          'os_name', 'os_version', 'processor', 'memory', 'storage', 'architecture', 
                          'last_seen', 'status', 'ip_address', 'mac_address', 'uptime', 'client_version', 
                          'location', 'asset_tag', 'created_at', 'updated_at']
                
                device_data = dict(zip(columns, device_result))
                
                # Convert datetime objects to ISO strings
                if device_data.get('last_seen'):
                    device_data['last_seen'] = device_data['last_seen'].isoformat() + 'Z'
                if device_data.get('created_at'):
                    device_data['created_at'] = device_data['created_at'].isoformat() + 'Z'
                if device_data.get('updated_at'):
                    device_data['updated_at'] = device_data['updated_at'].isoformat() + 'Z'
                
                # Get module data for this device
                module_data_query = """
                    SELECT data_type, raw_data, collected_at, created_at
                    FROM device_data 
                    WHERE device_id = %s 
                    ORDER BY created_at DESC
                """
                
                cursor.execute(module_data_query, (serial_number,))
                module_results = cursor.fetchall()
                cursor.close()
                
                # Organize module data by type
                modules = {}
                for row in module_results:
                    data_type = row[0]
                    raw_data = row[1]
                    
                    if data_type not in modules:
                        modules[data_type] = raw_data
                
                device_data['modules'] = modules
                device_data['module_count'] = len(modules)
                
                logger.info(f"Successfully retrieved device: {device_data.get('name', serial_number)} with {len(modules)} modules")
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'device': device_data
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
                
        except Exception as db_error:
            logger.error(f"Database error retrieving device {serial_number}: {db_error}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database error',
                    'details': str(db_error)
                }),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Error retrieving device: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

def handle_post_device(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle POST requests for device data ingestion
    """
    logger.info("Processing POST request for device data")
    
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
        
        # Extract device info from Windows client format OR direct payload format
        device_id = device_data.get('Device', '') or device_data.get('deviceId', '')
        serial_number = device_data.get('SerialNumber', '') or device_data.get('serialNumber', '')
        timestamp = device_data.get('Ts', '') or device_data.get('ts', '') or device_data.get('timestamp', '')
        payload = device_data.get('Payload', {}) or device_data.get('payload', {}) or device_data.get('modules', {})
        
        # If no device_id found in top level, look in payload or device section
        if not device_id:
            # Check if data is in direct payload format (like our test data)
            if 'device' in device_data and isinstance(device_data['device'], dict):
                device_id = device_data['device'].get('serial_number', '')
            elif 'inventory' in device_data and isinstance(device_data['inventory'], dict):
                device_id = device_data['inventory'].get('serial_number', '')
            
            # If still no device_id, use the entire device_data as payload
            if not device_id:
                payload = device_data
                # Try to extract serial from various payload locations
                device_id = payload.get('inventory', {}).get('serial_number', '')
                if not device_id:
                    device_id = payload.get('device', {}).get('serial_number', '')
        
        logger.info(f"Device ID: {device_id}")
        logger.info(f"Serial Number: {serial_number}")
        logger.info(f"Timestamp: {timestamp}")
        
        # Count data in payload
        total_records = 0
        if isinstance(payload, dict):
            for module_name, module_data in payload.items():
                if isinstance(module_data, list):
                    total_records += len(module_data)
                    logger.info(f"  - {module_name}: {len(module_data)} records")
                else:
                    logger.info(f"  - {module_name}: 1 record")
                    total_records += 1
        
        logger.info(f"Total data records: {total_records}")
        
        # **CRITICAL FIX: Actually store the data in the database**
        try:
            logger.info("=== STORING DATA IN DATABASE ===")
            
            # Use simple pg8000 connection directly
            import os
            import pg8000
            from urllib.parse import urlparse
            
            # Get database connection string
            db_url = os.environ.get('DATABASE_URL')
            if not db_url:
                raise ValueError("DATABASE_URL not configured")
                
            # Parse connection string
            parsed = urlparse(db_url)
            conn_params = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:],
                'user': parsed.username,
                'password': parsed.password,
                'ssl_context': True
            }
            
            # Connect to database
            conn = pg8000.connect(**conn_params)
            cursor = conn.cursor()
            
            current_time = datetime.utcnow()
            
            # Extract device information from payload
            device_name = device_id  # Use device_id as default name
            os_name = 'Windows'
            
            # Try to get better device info from modules
            if isinstance(payload, dict):
                if 'inventory' in payload and isinstance(payload['inventory'], dict):
                    inventory = payload['inventory']
                    device_name = inventory.get('hostname', device_id)
                elif 'system' in payload and isinstance(payload['system'], dict):
                    system_info = payload['system']
                    if isinstance(system_info, list) and len(system_info) > 0:
                        system_info = system_info[0]
                    device_name = system_info.get('hostname', device_id)
                    os_name = system_info.get('name', 'Windows')
            
            logger.info(f"Device info: name={device_name}, os={os_name}")
            
            # First, insert/update device record
            device_query = """
                INSERT INTO devices (
                    id, name, serial_number, os, status, last_seen, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) 
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    os = EXCLUDED.os,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = EXCLUDED.updated_at,
                    status = EXCLUDED.status
            """
            
            cursor.execute(device_query, (
                device_id,      # id
                device_name,    # name  
                device_id,      # serial_number
                os_name,        # os
                'active',       # status
                current_time,   # last_seen
                current_time,   # created_at
                current_time    # updated_at
            ))
            
            logger.info(f"✅ Device record upserted for {device_id}")
            
            # Store each module's data in device_data table
            modules_stored = 0
            if isinstance(payload, dict):
                for module_name, module_data in payload.items():
                    if module_data:  # Only store non-empty data
                        # First delete existing data for this device/data_type
                        delete_query = "DELETE FROM device_data WHERE device_id = %s AND data_type = %s"
                        cursor.execute(delete_query, (device_id, module_name))
                        
                        # Insert new data
                        insert_query = """
                            INSERT INTO device_data (
                                device_id, data_type, raw_data, collected_at, created_at
                            ) VALUES (%s, %s, %s, %s, %s)
                        """
                        
                        # Convert data to JSON string
                        import json
                        raw_data_json = json.dumps(module_data)
                        
                        cursor.execute(insert_query, (
                            device_id,
                            module_name,
                            raw_data_json,
                            current_time,
                            current_time
                        ))
                        
                        record_count = len(module_data) if isinstance(module_data, list) else 1
                        logger.info(f"  ✅ {module_name}: {record_count} records stored")
                        modules_stored += 1
            
            # Commit all changes
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Successfully stored {modules_stored} modules for device {device_id}")
            logger.info("✅ DATABASE STORAGE COMPLETE")
                
        except Exception as db_error:
            logger.error(f"❌ Data processing failed: {db_error}", exc_info=True)
            # Return the actual error so we can debug
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Data processing failed',
                    'details': str(db_error),
                    'deviceId': device_id,
                    'serialNumber': serial_number,
                    'timestamp': timestamp,
                    'totalRecords': total_records,
                    'processed_at': datetime.utcnow().isoformat()
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Return success response
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Data received and stored successfully',
                'deviceId': device_id,
                'serialNumber': serial_number,
                'timestamp': timestamp,
                'totalRecords': total_records,
                'processed_at': datetime.utcnow().isoformat()
            }),
            status_code=200,
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
        logger.error(f"Unexpected error in device POST handler: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )



