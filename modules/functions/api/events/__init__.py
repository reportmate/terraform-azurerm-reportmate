import azure.functions as func
import json
import logging
import os
import sys
import asyncio
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import SyncDatabaseManager

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Events API for handling unified device data ingestion and retrieval
    """
    logging.info(f'Events API function processed a request: {req.method}')
    
    try:
        if req.method == 'GET':
            return handle_get_events(req)
        elif req.method == 'POST':
            # Run the async POST handler
            return asyncio.run(handle_post_event(req))
        else:
            return func.HttpResponse(
                json.dumps({'error': f'Method {req.method} not allowed'}),
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
        
        # Test database connection first
        if not db_manager.test_connection():
            logging.warning("Database connection test failed for events")
            return func.HttpResponse(
                json.dumps({
                    'error': 'Database connection failed',
                    'details': 'Unable to connect to database for events retrieval'
                }),
                status_code=503,
                headers={'Content-Type': 'application/json'}
            )
        
        # Get query parameters
        device_id = req.params.get('device_id')
        limit = req.params.get('limit', '100')
        
        try:
            limit = int(limit)
            if limit > 1000:
                limit = 1000
        except ValueError:
            limit = 100
        
        # Query events from database using reliable method
        try:
            if device_id:
                query = """
                    SELECT id, device_id, event_type, message, details, timestamp
                    FROM events 
                    WHERE device_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """
                events_raw = db_manager.execute_query(query, (device_id, limit))
            else:
                query = """
                    SELECT id, device_id, event_type, message, details, timestamp
                    FROM events 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """
                events_raw = db_manager.execute_query(query, (limit,))
            
            logging.info(f"Retrieved {len(events_raw)} events from database")
            
            # Format events for response
            formatted_events = []
            for event in events_raw:
                try:
                    # Parse details if it's JSON
                    details = event.get('details', {})
                    if details and isinstance(details, str):
                        try:
                            details = json.loads(details)
                        except json.JSONDecodeError:
                            details = {'raw': details}

                    formatted_events.append({
                        'id': event.get('id'),
                        'device': event.get('device_id'),  # Use 'device' field name to match frontend
                        'kind': event.get('event_type'),    # Map event_type to kind for frontend compatibility
                        'message': event.get('message'),
                        'payload': details,  # Map details to payload for frontend compatibility
                        'ts': event.get('timestamp').isoformat() if event.get('timestamp') else None  # Map timestamp to ts for frontend
                    })
                except Exception as event_error:
                    logging.error(f"Error processing event row: {event_error}")
                    continue
        
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
            
        except Exception as query_error:
            logging.error(f'Database query error: {str(query_error)}', exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'error': 'Database query failed',
                    'details': str(query_error)
                }),
                status_code=500,
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

async def handle_post_event(req: func.HttpRequest) -> func.HttpResponse:
    """Handle POST requests for storing unified device payloads"""
    
    # Define allowed event types (strict validation)
    ALLOWED_EVENT_TYPES = {'success', 'warning', 'error', 'info'}
    
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
        
        # Validate required fields and ensure UUID + serial number combination
        if device_id == 'unknown-device' or serial_number == 'unknown-serial':
            return func.HttpResponse(
                json.dumps({
                    'error': 'Invalid device identification',
                    'details': 'Both deviceId (UUID) and serialNumber are required'
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # CRITICAL PROTECTION: Validate UUID format for device_id
        import re
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        if not re.match(uuid_pattern, device_id):
            return func.HttpResponse(
                json.dumps({
                    'error': 'Invalid device UUID format',
                    'details': f'deviceId must be a valid UUID format, got: {device_id}'
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # CRITICAL PROTECTION: Validate serial number is NOT a UUID
        if re.match(uuid_pattern, serial_number):
            return func.HttpResponse(
                json.dumps({
                    'error': 'Invalid serial number format',
                    'details': f'serialNumber must not be a UUID format, got: {serial_number}. Expected human-readable serial like 0F33V9G25083HJ'
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # CRITICAL PROTECTION: Ensure deviceId and serialNumber are different
        if device_id == serial_number:
            return func.HttpResponse(
                json.dumps({
                    'error': 'Device identification mismatch',
                    'details': 'deviceId (UUID) and serialNumber must be different values'
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        logging.info(f"Processing unified payload for device {device_id} (serial: {serial_number})")
        logging.info(f"Collection type: {collection_type}, Modules: {enabled_modules}")
        
        # Debug: Log the actual payload structure
        payload_keys = list(unified_payload.keys())
        logging.info(f"🔍 DEBUG: Unified payload top-level keys: {payload_keys}")
        
        # Check if OsQuery key exists and what's in it
        osquery_data = unified_payload.get('OsQuery', {})
        osquery_keys = list(osquery_data.keys()) if osquery_data else []
        logging.info(f"🔍 DEBUG: OsQuery section keys: {osquery_keys}")
        
        # Also check for other common data locations
        if 'modules' in unified_payload:
            modules_keys = list(unified_payload['modules'].keys()) if isinstance(unified_payload['modules'], dict) else []
            logging.info(f"🔍 DEBUG: modules section keys: {modules_keys}")
        if 'data' in unified_payload:
            data_keys = list(unified_payload['data'].keys()) if isinstance(unified_payload['data'], dict) else []
            logging.info(f"🔍 DEBUG: data section keys: {data_keys}")
        
        # Store in database with unique serial number validation
        try:
            logging.info("=== PROCESSING UNIFIED PAYLOAD WITH MODULE PROCESSORS ===")
            
            # Initialize the sophisticated processor that uses all module processors
            try:
                from shared.database import DatabaseManager
                from shared.auth import AuthenticationManager
                from processor import DeviceDataProcessor
                logging.info("✅ Successfully imported processor modules")
            except Exception as import_error:
                logging.error(f"❌ IMPORT ERROR: Failed to import processor modules: {import_error}")
                raise
            
            try:
                db_manager = DatabaseManager()
                auth_manager = AuthenticationManager()
                device_processor = DeviceDataProcessor(db_manager, auth_manager)
                logging.info("✅ Successfully initialized processor instances")
            except Exception as init_error:
                logging.error(f"❌ INIT ERROR: Failed to initialize processors: {init_error}")
                raise
            
            # Extract the passphrase from headers for authentication  
            passphrase = req.headers.get('X-API-PASSPHRASE', 's3cur3-p@ssphras3!')
            logging.info(f"🔍 Using passphrase: {passphrase[:10]}...")
            
            # Use the sophisticated processor that correctly processes all modules
            try:
                storage_result = await device_processor.process_device_data_with_device_id(
                    unified_payload,  # Pass the full unified payload which contains module data as top-level properties
                    passphrase,
                    serial_number  # Use serial number as device_id
                )
                logging.info(f"✅ Processor completed with result: {storage_result}")
            except Exception as process_error:
                logging.error(f"❌ PROCESSING ERROR: Device processor failed: {process_error}")
                raise
            
            if storage_result['success']:
                logging.info(f"✅ Successfully stored data for device {device_id}")
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'message': 'Unified payload processed successfully',
                        'device_id': serial_number,  # Return serial number for frontend consistency
                        'serial_number': serial_number,
                        'modules_processed': storage_result.get('modules_processed', 0),
                        'timestamp': storage_result.get('timestamp'),
                        'storage_mode': storage_result.get('storage_mode', 'database'),
                        'internal_uuid': device_id,  # Keep UUID for internal reference if needed
                        'debug_info': {  # TEMPORARY DEBUG INFO
                            'storage_result_keys': list(storage_result.keys()),
                            'processing_results_count': len(storage_result.get('processing_results', {})),
                            'available_modules': storage_result.get('summary', {}).get('available_modules', []),
                            'processing_errors': storage_result.get('processing_errors', [])
                        }
                    }),
                    status_code=200,
                    headers={'Content-Type': 'application/json'}
                )
            else:
                # FALLBACK: Even if module processing failed, update device last_seen for dashboard
                logging.warning(f"Module processing failed, but updating last_seen as fallback for device {serial_number}")
                try:
                    # Simple database update for last_seen field
                    fallback_db = SyncDatabaseManager()
                    
                    if fallback_db.test_connection():
                        update_query = """
                            UPDATE devices 
                            SET last_seen = NOW(), updated_at = NOW()
                            WHERE device_id = %s OR serial_number = %s
                        """
                        result = fallback_db.execute_query(update_query, (serial_number, serial_number))
                        
                        # Also create a basic event for tracking
                        event_insert = """
                            INSERT INTO events (device_id, event_type, message, timestamp, created_at)
                            VALUES (%s, 'info', 'Data transmission received (module processing failed)', NOW(), NOW())
                        """
                        fallback_db.execute_query(event_insert, (serial_number,))
                        
                        logging.info(f"✅ Fallback: Updated last_seen for device {serial_number}")
                    else:
                        logging.error("❌ Fallback database connection failed")
                        
                except Exception as fallback_error:
                    logging.error(f"❌ Fallback last_seen update failed: {fallback_error}")
                
                logging.error(f"❌ Failed to store data: {storage_result}")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Database storage failed',
                        'details': storage_result.get('details', 'Unknown error'),
                        'device_id': serial_number,  # Return serial number for frontend consistency
                        'serial_number': serial_number,
                        'modules_processed': 0,
                        'fallback_applied': True,
                        'message': 'last_seen updated despite processing failure',
                        'internal_uuid': device_id  # Keep UUID for internal reference if needed
                    }),
                    status_code=500,
                    headers={'Content-Type': 'application/json'}
                )
                
        except Exception as db_error:
            logging.error(f"Database storage error: {str(db_error)}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Database storage failed',
                    'details': str(db_error),
                    'device_id': serial_number,  # Return serial number for frontend consistency
                    'serial_number': serial_number,
                    'internal_uuid': device_id  # Keep UUID for internal reference if needed
                }),
                status_code=500,
                headers={'Content-Type': 'application/json'}
            )
            
    except Exception as e:
        logging.error(f'Error in events API POST handler: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )
# Debug update 08/07/2025 11:18:43
# Debug response 08/07/2025 11:21:35
