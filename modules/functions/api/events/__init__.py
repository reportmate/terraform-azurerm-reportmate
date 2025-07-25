import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sync_database import SyncDatabaseManager

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Events API for handling unified device data ingestion and retrieval
    """
    logging.info(f'Events API function processed a request: {req.method}')
    
    try:
        if req.method == 'GET':
            return handle_get_events(req)
        elif req.method == 'POST':
            return handle_post_event(req)
        else:
            return func.HttpResponse(
                json.dumps({'error': 'Method not allowed'}),
                status_code=405,
                headers={'Content-Type': 'application/json'}
            )
            
    except Exception as e:
        logging.error(f'Error in events API: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )

def handle_get_events(req: func.HttpRequest) -> func.HttpResponse:
    """Handle GET requests for retrieving events from database"""
    try:
        db_manager = SyncDatabaseManager()
        
        # Get query parameters
        device_id = req.params.get('device_id')
        limit = req.params.get('limit', '100')
        
        try:
            limit = int(limit)
            if limit > 1000:
                limit = 1000
        except ValueError:
            limit = 100
        
        # Query events from database
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if device_id:
                query = """
                    SELECT id, device_id, kind, source, payload, severity, ts
                    FROM events 
                    WHERE device_id = %s 
                    ORDER BY ts DESC 
                    LIMIT %s
                """
                cursor.execute(query, (device_id, limit))
            else:
                query = """
                    SELECT id, device_id, kind, source, payload, severity, ts
                    FROM events 
                    ORDER BY ts DESC 
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            events = cursor.fetchall()
            
            # Format events for response
            formatted_events = []
            for event in events:
                formatted_events.append({
                    'id': event[0],
                    'device_id': event[1],
                    'kind': event[2],
                    'source': event[3],
                    'payload': event[4],
                    'severity': event[5],
                    'timestamp': event[6].isoformat() if event[6] else None
                })
                formatted_events.append({
                    'id': event[0],
                    'device_id': event[1],
                    'kind': event[2],
                    'source': event[3],
                    'payload': event[4],
                    'severity': event[5],
                    'timestamp': event[6].isoformat() if event[6] else None
                })
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'events': formatted_events,
                'count': len(formatted_events),
                'device_id': device_id
            }),
            status_code=200,
            headers={'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        logging.error(f'Error retrieving events: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Failed to retrieve events',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )

def handle_post_event(req: func.HttpRequest) -> func.HttpResponse:
    """Handle POST requests for storing unified device payloads"""
    
    # Define allowed event types (strict validation)
    ALLOWED_EVENT_TYPES = {'success', 'warning', 'error', 'info', 'system'}
    
    try:
        # Parse request body
        try:
            unified_payload = req.get_json()
        except ValueError as e:
            return func.HttpResponse(
                json.dumps({'error': 'Invalid JSON in request body'}),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        if not unified_payload:
            return func.HttpResponse(
                json.dumps({'error': 'No payload data provided'}),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        logging.info(f"Received unified payload for processing")
        
        # Extract metadata from the unified payload
        metadata = unified_payload.get('metadata', {})
        device_id = metadata.get('deviceId', 'unknown-device')
        serial_number = metadata.get('serialNumber', 'unknown-serial')
        collection_type = metadata.get('collectionType', 'Full')
        enabled_modules = metadata.get('enabledModules', [])
        client_version = metadata.get('clientVersion', 'unknown')
        collected_at = metadata.get('collectedAt', datetime.now(timezone.utc).isoformat())
        
        # Validate required fields
        if device_id == 'unknown-device' or serial_number == 'unknown-serial':
            return func.HttpResponse(
                json.dumps({
                    'error': 'Invalid device identification',
                    'details': 'Both deviceId (UUID) and serialNumber are required'
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        logging.info(f"Processing unified payload for device {device_id} (serial: {serial_number})")
        logging.info(f"Collection type: {collection_type}, Modules: {enabled_modules}")
        
        # Store in database with unique serial number validation
        try:
            logging.info("=== STORING UNIFIED PAYLOAD IN DATABASE ===")
            
            # Initialize database manager
            db_manager = SyncDatabaseManager()
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                current_time = datetime.utcnow()
                
                # Check for existing device with same serial number but different device_id
                # This prevents duplicate device registrations
                cursor.execute("""
                    SELECT id, device_id FROM devices 
                    WHERE serial_number = %s AND device_id != %s
                    LIMIT 1
                """, (serial_number, device_id))
                
                conflicting_device = cursor.fetchone()
                if conflicting_device:
                    existing_id, existing_device_id = conflicting_device
                    logging.error(f"❌ Serial number {serial_number} already registered to different device {existing_device_id}")
                    return func.HttpResponse(
                        json.dumps({
                            'success': False,
                            'error': 'Serial number conflict',
                            'details': f'Serial number {serial_number} is already registered to device {existing_device_id}',
                            'device_id': device_id,
                            'serial_number': serial_number,
                            'conflicting_device_id': existing_device_id
                        }),
                        status_code=409,  # Conflict
                        headers={'Content-Type': 'application/json'}
                    )
                
                # Extract device information from unified payload
                device_name = serial_number  # Use serial as default name
                os_name = 'Windows'
                
                # First check if device_name is provided at the top level of the payload
                if 'device_name' in unified_payload:
                    device_name = unified_payload['device_name']
                
                # Try to get better device info from modules (fallback)
                if 'inventory' in unified_payload and isinstance(unified_payload['inventory'], dict):
                    inventory = unified_payload['inventory']
                    device_name = inventory.get('deviceName', device_name)
                
                if 'system' in unified_payload and isinstance(unified_payload['system'], dict):
                    system_info = unified_payload['system']
                    os_data = system_info.get('operatingSystem', {})
                    if isinstance(os_data, dict):
                        os_name = os_data.get('name', 'Windows')
                
                logging.info(f"Device info: name={device_name}, os={os_name}")
                
                # Insert/update device record using serial number as primary key
                device_query = """
                    INSERT INTO devices (
                        id, device_id, name, serial_number, os, status, last_seen, 
                        client_version, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) 
                    DO UPDATE SET 
                        device_id = EXCLUDED.device_id,
                        name = EXCLUDED.name,
                        os = EXCLUDED.os,
                        last_seen = EXCLUDED.last_seen,
                        client_version = EXCLUDED.client_version,
                        updated_at = EXCLUDED.updated_at,
                        status = EXCLUDED.status
                """
                
                cursor.execute(device_query, (
                    serial_number,   # id (use serial as primary key)
                    device_id,       # device_id (UUID)
                    device_name,     # name  
                    serial_number,   # serial_number
                    os_name,         # os
                    'active',        # status
                    current_time,    # last_seen
                    client_version,  # client_version
                    current_time,    # created_at
                    current_time     # updated_at
                ))
                
                logging.info(f"✅ Device record upserted for {serial_number} ({device_id})")
                
                # Store each module's data directly in its modular table
                modules_stored = 0
                
                # Define valid module tables (must match exactly what Windows client sends)
                valid_modules = {
                    'applications', 'displays', 'hardware', 'installs', 'inventory',
                    'management', 'network', 'printers', 'profiles', 'security', 'system'
                }
                
                for module_name, module_data in unified_payload.items():
                    # Skip metadata as it's not module data
                    if module_name == 'metadata':
                        continue
                    
                    # Only process valid modules that have dedicated tables
                    if module_name not in valid_modules:
                        logging.warning(f"Skipping unknown module: {module_name}")
                        continue
                        
                    if module_data:  # Only store non-empty data
                        # Special handling for inventory module - inject device name from top-level payload
                        if module_name == 'inventory' and isinstance(module_data, dict):
                            # Ensure the device name from the top-level payload is available in inventory data
                            if 'device_name' in unified_payload:
                                module_data['deviceName'] = unified_payload['device_name']
                                module_data['device_name'] = unified_payload['device_name']
                        
                        # Store directly in the module's dedicated table
                        module_insert_query = f"""
                            INSERT INTO {module_name} (
                                device_id, data, collected_at, created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (device_id) 
                            DO UPDATE SET
                                data = EXCLUDED.data,
                                collected_at = EXCLUDED.collected_at,
                                updated_at = EXCLUDED.updated_at
                        """
                        
                        cursor.execute(module_insert_query, (
                            serial_number,           # device_id (use serial as foreign key)
                            json.dumps(module_data), # data (JSON)
                            collected_at,            # collected_at
                            current_time,            # created_at
                            current_time             # updated_at
                        ))
                        
                        record_count = len(module_data) if isinstance(module_data, list) else 1
                        logging.info(f"  ✅ {module_name}: {record_count} records stored in dedicated table")
                        modules_stored += 1
                
                # Store event record for historical tracking with validated event type
                event_kind = 'system'        # Data collection is a system event (VALID)
                event_severity = 'info'      # Default severity (VALID)
                
                # Validate event type is in allowed list (strict validation)
                if event_kind not in ALLOWED_EVENT_TYPES:
                    logging.warning(f"Invalid event type '{event_kind}', defaulting to 'info'")
                    event_kind = 'info'
                
                if event_severity not in ALLOWED_EVENT_TYPES:
                    logging.warning(f"Invalid event severity '{event_severity}', defaulting to 'info'")
                    event_severity = 'info'
                
                event_query = """
                    INSERT INTO events (
                        device_id, kind, source, payload, 
                        severity, ts, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                event_data = {
                    'modules_processed': modules_stored,
                    'collection_type': collection_type,
                    'client_version': client_version,
                    'enabled_modules': enabled_modules,
                    'serial_number': serial_number,
                    'device_name': device_name
                }
                
                cursor.execute(event_query, (
                    serial_number,           # device_id (use serial as foreign key)
                    event_kind,             # kind (validated)
                    'runner.exe',           # source
                    json.dumps(event_data), # payload (JSON)
                    event_severity,         # severity (validated)
                    collected_at,           # ts
                    current_time            # created_at
                ))
                
                logging.info(f"✅ Event record stored for transmission")
                
                # Commit all changes
                conn.commit()
                cursor.close()
                
                logging.info(f"✅ Successfully stored {modules_stored} modules for device {serial_number}")
                logging.info("✅ DATABASE STORAGE COMPLETE")
                
        except Exception as db_error:
            logging.error(f"❌ Database storage failed: {db_error}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database storage failed',
                    'details': str(db_error),
                    'device_id': device_id,
                    'serial_number': serial_number
                }),
                status_code=500,
                headers={'Content-Type': 'application/json'}
            )
        
        # Success response
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Unified payload stored successfully',
                'device_id': device_id,
                'serial_number': serial_number,
                'modules_processed': len(enabled_modules),
                'client_version': client_version,
                'collected_at': collected_at,
                'processed_at': datetime.now(timezone.utc).isoformat()
            }),
            status_code=201,
            headers={'Content-Type': 'application/json'}
        )
            
    except Exception as e:
        logging.error(f'Error storing unified payload: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Failed to store unified payload',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )
