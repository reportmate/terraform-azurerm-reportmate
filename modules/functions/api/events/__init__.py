import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import SimpleDatabaseManager

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
        db_manager = SimpleDatabaseManager()
        
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
                    SELECT id, device_id, event_type, message, details, timestamp
                    FROM events 
                    WHERE device_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """
                cursor.execute(query, (device_id, limit))
            else:
                query = """
                    SELECT id, device_id, event_type, message, details, timestamp
                    FROM events 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            events = cursor.fetchall()
            
            # Format events for response
            formatted_events = []
            for event in events:
                # Parse details if it's JSON
                details = event[4]
                if details and isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except json.JSONDecodeError:
                        details = {'raw': details}

                formatted_events.append({
                    'id': event[0],
                    'device': event[1],  # Use 'device' field name to match frontend
                    'kind': event[2],    # Map event_type to kind for frontend compatibility
                    'message': event[3],
                    'payload': details,  # Map details to payload for frontend compatibility
                    'ts': event[5].isoformat() if event[5] else None  # Map timestamp to ts for frontend
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
            db_manager = SimpleDatabaseManager()
            
            # Use the new store_event_data method for mock database handling
            storage_result = db_manager.store_event_data(unified_payload)
            
            if storage_result['success']:
                logging.info(f"✅ Successfully stored data for device {device_id}")
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'message': 'Unified payload processed successfully',
                        'device_id': device_id,
                        'serial_number': serial_number,
                        'modules_processed': storage_result.get('modules_processed', []),
                        'timestamp': storage_result.get('timestamp'),
                        'storage_mode': 'mock'  # Indicate we're using mock storage
                    }),
                    status_code=200,
                    headers={'Content-Type': 'application/json'}
                )
            else:
                logging.error(f"❌ Failed to store data: {storage_result}")
                return func.HttpResponse(
                    json.dumps({
                        'success': False,
                        'error': 'Database storage failed',
                        'details': storage_result.get('details', 'Unknown error'),
                        'device_id': device_id,
                        'serial_number': serial_number
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
                    'device_id': device_id,
                    'serial_number': serial_number
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
                    'device_id': device_id,
                    'serial_number': serial_number
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
