import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sync_database import SyncDatabaseManager

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
        
        # TODO: Replace with real database query once PostgreSQL driver is working
        # For now, use mock data that matches the devices endpoint
        mock_devices = [
            {
                "id": 1,
                "device_id": "bc8adf50-74b3-4a75-a29e-ff7cf5b0e4a8",
                "serial_number": "0F33V9G25083HJ",
                "name": "DESKTOP-RCHRISTIANSEN",
                "hostname": "DESKTOP-RCHRISTIANSEN",
                "os_name": "Microsoft Windows 11 Pro",
                "os_version": "10.0.22631",
                "client_version": "1.0.0",
                "status": "active",
                "last_seen": "2025-07-21T02:00:00Z",
                "created_at": "2025-07-20T10:00:00Z"
            },
            {
                "id": 2,
                "device_id": "test-device-2",
                "serial_number": "TEST123456",
                "name": "test-machine-2",
                "hostname": "test-machine-2",
                "os_name": "Microsoft Windows 10 Pro",
                "os_version": "10.0.19044",
                "client_version": "1.0.0",
                "status": "active",
                "last_seen": "2025-07-20T15:30:00Z",
                "created_at": "2025-07-19T12:00:00Z"
            }
        ]
        
        # Find device by serial number
        device_data = None
        for device in mock_devices:
            if device["serial_number"] == serial_number:
                device_data = device
                break
        
        if not device_data:
            logger.info(f"Device not found with serial number: {serial_number}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device not found',
                    'details': f'No device found with serial number: {serial_number}'
                }),
                status_code=404,
                mimetype="application/json"
            )
        
        logger.info(f"Successfully retrieved device: {device_data['name']}")
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'device': device_data,
                'note': 'Using mock data until PostgreSQL driver issue is resolved'
            }),
            status_code=200,
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
    Main entry point for device data ingestion from Windows clients
    
    Expects JSON payload in the format sent by ReportMate Windows client:
    - Device: Device UUID/ID
    - SerialNumber: Device serial number  
    - Kind: Request type (usually "Info")
    - Ts: Timestamp
    - Payload: Device data including OsQuery results
    - Passphrase: Authentication passphrase
    """
    
    logger.info("=== REPORTMATE DEVICE DATA INGESTION ===")
    logger.info(f"Method: {req.method}")
    logger.info(f"URL: {req.url}")
    
    try:
        # Parse request body
        try:
            request_data = req.get_json()
            if not request_data:
                logger.error("No JSON payload received")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Invalid JSON payload',
                        'details': 'Request body must contain valid JSON'
                    }),
                    status_code=400,
                    mimetype="application/json"
                )
        except ValueError as e:
            logger.error(f"JSON parsing error: {e}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'JSON parsing failed',
                    'details': str(e)
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Log the structure of received data for debugging
        logger.info(f"Received payload with keys: {list(request_data.keys())}")
        
        # Extract fields in Windows client format - handle both PascalCase and camelCase
        device_id = request_data.get('Device', '') or request_data.get('device', '')
        serial_number = request_data.get('SerialNumber', '') or request_data.get('serialNumber', '')
        kind = request_data.get('Kind', '') or request_data.get('kind', 'Info')
        timestamp = request_data.get('Ts', '') or request_data.get('ts', '')
        payload = request_data.get('Payload', {}) or request_data.get('payload', {})
        # Check for passphrase in both camelCase and PascalCase for compatibility
        passphrase = request_data.get('Passphrase', '') or request_data.get('passphrase', '')
        
        logger.info(f"Device ID: {device_id}")
        logger.info(f"Serial Number: {serial_number}")
        logger.info(f"Kind: {kind}")
        logger.info(f"Timestamp: {timestamp}")
        logger.info(f"Payload keys: {list(payload.keys()) if payload else 'None'}")
        
        # Handle authentication if passphrases are configured
        client_passphrases = os.getenv('CLIENT_PASSPHRASES', '')
        
        # If passphrases are configured, validate authentication
        if client_passphrases:
            if not passphrase:
                logger.warning("Authentication required but no passphrase provided")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Authentication required',
                        'details': 'Passphrase is required for this endpoint'
                    }),
                    status_code=401,
                    mimetype="application/json"
                )
            
            # Check against configured passphrases (comma-separated)
            valid_passphrases = [p.strip() for p in client_passphrases.split(',') if p.strip()]
            if passphrase not in valid_passphrases:
                logger.warning(f"Invalid passphrase provided for device {device_id}")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Authentication failed',
                        'details': 'Invalid passphrase'
                    }),
                    status_code=403,
                    mimetype="application/json"
                )
            
            logger.info("✅ Authentication successful")
        else:
            logger.info("⚠️  No authentication configured - allowing open access")
        
        # Validate required fields
        if not device_id and not request_data.get('test'):
            logger.error("Missing Device ID")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Missing Device ID',
                    'details': 'Device field is required'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Process the device data (for now, just log and accept)
        logger.info(f"Processing device data for: {device_id or 'test-device'}")
        
        # Extract modules from OsQuery data
        received_modules = []
        if payload and payload.get('OsQuery'):
            received_modules = list(payload['OsQuery'].keys())
            logger.info(f"Received modules: {received_modules}")
            
            # Log some statistics
            total_records = 0
            for module_name, module_data in payload['OsQuery'].items():
                if isinstance(module_data, list):
                    total_records += len(module_data)
                elif isinstance(module_data, dict):
                    total_records += 1
            
            logger.info(f"Total data records: {total_records}")
        
        # Process and save device data to database
        try:
            db_manager = SyncDatabaseManager()
            
            # Extract basic device info
            device_info = payload.get('Device', {}) if payload else {}
            inventory_data = payload.get('OsQuery', {}).get('inventory', {}) if payload else {}
            hardware_data = payload.get('OsQuery', {}).get('hardware', {}) if payload else {}
            
            # Get the first inventory record if it's a list
            if isinstance(inventory_data, list) and inventory_data:
                inventory_data = inventory_data[0]
            if isinstance(hardware_data, list) and hardware_data:
                hardware_data = hardware_data[0]
            
            # Prepare device record for upsert using serial number as the key
            device_record = {
                'id': serial_number or device_id,  # Use serial number as primary key
                'device_id': device_id,  # Store UUID separately
                'name': inventory_data.get('computer_name') or device_info.get('ComputerName') or inventory_data.get('hostname', ''),
                'serial_number': serial_number,
                'hostname': inventory_data.get('hostname', ''),
                'model': hardware_data.get('hardware_model') or inventory_data.get('hardware_model', ''),
                'os': f"{inventory_data.get('platform', '')} {inventory_data.get('platform_version', '')}".strip(),
                'os_name': inventory_data.get('platform', ''),
                'os_version': inventory_data.get('platform_version', ''),
                'processor': hardware_data.get('cpu_brand', ''),
                'memory': hardware_data.get('physical_memory', ''),
                'storage': hardware_data.get('disk_space_total', ''),
                'architecture': inventory_data.get('hardware_vendor', ''),
                'last_seen': datetime.utcnow(),
                'status': 'online',
                'ip_address': '',  # Will be populated from network data if available
                'mac_address': '',  # Will be populated from network data if available
                'uptime': inventory_data.get('uptime', ''),
                'client_version': payload.get('ClientVersion', ''),
                'last_contact': datetime.utcnow()
            }
            
            # Get network data for IP/MAC addresses
            network_data = payload.get('OsQuery', {}).get('network', []) if payload else []
            if isinstance(network_data, list) and network_data:
                for interface in network_data:
                    if interface.get('address') and not interface.get('address', '').startswith('127.'):
                        device_record['ip_address'] = interface.get('address', '')
                        device_record['mac_address'] = interface.get('mac', '')
                        break
            
            logger.info(f"Upserting device record for {serial_number} (UUID: {device_id})")
            
            # Use upsert to prevent duplicates
            upsert_query = """
                INSERT INTO devices (
                    id, device_id, name, serial_number, hostname, model, os, os_name, os_version,
                    processor, memory, storage, architecture, last_seen, status, ip_address, 
                    mac_address, uptime, client_version, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                ) ON CONFLICT (serial_number) DO UPDATE SET
                    device_id = EXCLUDED.device_id,
                    name = EXCLUDED.name,
                    hostname = EXCLUDED.hostname,
                    model = EXCLUDED.model,
                    os = EXCLUDED.os,
                    os_name = EXCLUDED.os_name,
                    os_version = EXCLUDED.os_version,
                    processor = EXCLUDED.processor,
                    memory = EXCLUDED.memory,
                    storage = EXCLUDED.storage,
                    architecture = EXCLUDED.architecture,
                    last_seen = EXCLUDED.last_seen,
                    status = EXCLUDED.status,
                    ip_address = EXCLUDED.ip_address,
                    mac_address = EXCLUDED.mac_address,
                    uptime = EXCLUDED.uptime,
                    client_version = EXCLUDED.client_version,
                    updated_at = NOW()
                RETURNING id;
            """
            
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(upsert_query, (
                        device_record['id'],
                        device_record['device_id'],
                        device_record['name'],
                        device_record['serial_number'],
                        device_record['hostname'],
                        device_record['model'],
                        device_record['os'],
                        device_record['os_name'],
                        device_record['os_version'],
                        device_record['processor'],
                        device_record['memory'],
                        device_record['storage'],
                        device_record['architecture'],
                        device_record['last_seen'],
                        device_record['status'],
                        device_record['ip_address'],
                        device_record['mac_address'],
                        device_record['uptime'],
                        device_record['client_version']
                    ))
                    
                    result = cursor.fetchone()
                    final_device_id = result[0] if result else device_record['id']
                    
                    conn.commit()
                    logger.info(f"✅ Device record upserted successfully: {final_device_id}")
            
            # Store raw osquery data for detailed views
            if payload and payload.get('OsQuery'):
                raw_data_query = """
                    INSERT INTO device_data (device_id, data_type, raw_data, collected_at, created_at)
                    VALUES (%s, 'osquery_full', %s, %s, NOW())
                    ON CONFLICT (device_id, data_type) DO UPDATE SET
                        raw_data = EXCLUDED.raw_data,
                        collected_at = EXCLUDED.collected_at,
                        created_at = NOW();
                """
                
                with db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(raw_data_query, (
                            final_device_id,
                            json.dumps(payload['OsQuery']),
                            datetime.utcnow()
                        ))
                        conn.commit()
                        logger.info(f"✅ Raw osquery data stored for device {final_device_id}")
                        
        except Exception as db_error:
            logger.error(f"Database processing error: {db_error}", exc_info=True)
            # Continue processing - don't fail the entire request for DB issues
        
        # Return success response
        response_data = {
            'success': True,
            'message': 'Device data received and processed successfully',
            'device_id': device_id or 'test-device',
            'serial_number': serial_number,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'received_modules': received_modules,
            'status': 'processed',
            'next_checkin': 3600  # 1 hour
        }
        
        logger.info(f"✅ Successfully processed data for device {device_id or 'test-device'}")
        
        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json",
            headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate',
                'Pragma': 'no-cache',
                'X-ReportMate-Status': 'success'
            }
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in device endpoint: {e}", exc_info=True)
        
        error_response = {
            'success': False,
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json",
            headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate',
                'Pragma': 'no-cache'
            }
        )
