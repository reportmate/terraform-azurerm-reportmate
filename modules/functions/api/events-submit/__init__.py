"""
ReportMate Events API - Individual Event Submission
This handles submission of individual events with strict type validation
"""
import azure.functions as func
import json
import logging
import os
import sys
from datetime import datetime, timezone

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sync_database import SyncDatabaseManager

# Strictly allowed event types - no other types are permitted
ALLOWED_EVENT_TYPES = {'success', 'warning', 'error', 'info'}

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Individual Event Submission API
    POST /api/events/submit
    """
    logging.info(f'Individual Event API processed a request: {req.method}')
    
    if req.method != 'POST':
        return func.HttpResponse(
            json.dumps({'error': 'Method not allowed. Use POST.'}),
            status_code=405,
            headers={'Content-Type': 'application/json'}
        )
    
    try:
        return handle_event_submission(req)
        
    except Exception as e:
        logging.error(f'Error in individual event API: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )

def handle_event_submission(req: func.HttpRequest) -> func.HttpResponse:
    """Handle individual event submission with strict validation"""
    
    try:
        # Parse request body
        try:
            event_data = req.get_json()
        except ValueError as e:
            return func.HttpResponse(
                json.dumps({'error': 'Invalid JSON in request body'}),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        if not event_data:
            return func.HttpResponse(
                json.dumps({'error': 'No event data provided'}),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # Validate required fields
        required_fields = ['deviceId', 'serialNumber', 'kind', 'message']
        missing_fields = [field for field in required_fields if field not in event_data]
        
        if missing_fields:
            return func.HttpResponse(
                json.dumps({
                    'error': 'Missing required fields',
                    'missing_fields': missing_fields,
                    'required_fields': required_fields
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        device_id = event_data['deviceId']
        serial_number = event_data['serialNumber']
        event_kind = event_data['kind'].lower()
        message = event_data['message']
        
        # Strict event type validation - block any other types
        if event_kind not in ALLOWED_EVENT_TYPES:
            return func.HttpResponse(
                json.dumps({
                    'error': 'Invalid event type',
                    'provided_type': event_kind,
                    'allowed_types': list(ALLOWED_EVENT_TYPES),
                    'message': f'Event type must be one of: {", ".join(ALLOWED_EVENT_TYPES)}'
                }),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # Optional fields with defaults
        source = event_data.get('source', 'client')
        severity = event_data.get('severity', event_kind).lower()
        category = event_data.get('category', 'general')
        
        # Validate severity is also in allowed types
        if severity not in ALLOWED_EVENT_TYPES:
            severity = event_kind  # Default to event kind if invalid severity
        
        # Prepare event payload
        event_payload = {
            'message': message,
            'category': category,
            'timestamp': event_data.get('timestamp', datetime.now(timezone.utc).isoformat())
        }
        
        # Add any additional data provided
        if 'data' in event_data:
            event_payload['data'] = event_data['data']
        
        logging.info(f"Storing individual event: {event_kind} from {serial_number}")
        
        # Store in database
        try:
            db_manager = SyncDatabaseManager()
            
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                current_time = datetime.now(timezone.utc)
                
                # Verify device exists
                cursor.execute("""
                    SELECT id FROM devices 
                    WHERE serial_number = %s AND device_id = %s
                    LIMIT 1
                """, (serial_number, device_id))
                
                device_record = cursor.fetchone()
                if not device_record:
                    return func.HttpResponse(
                        json.dumps({
                            'error': 'Device not found',
                            'message': f'No device found with serial {serial_number} and ID {device_id}',
                            'suggestion': 'Device must be registered before submitting events'
                        }),
                        status_code=404,
                        headers={'Content-Type': 'application/json'}
                    )
                
                # Insert event
                event_query = """
                    INSERT INTO events (
                        device_id, event_type, message, details, 
                        timestamp, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(event_query, (
                    serial_number,                      # device_id (use serial as foreign key)
                    event_kind,                         # event_type (validated)
                    event_payload.get('message', f'{event_kind.title()} event'), # message
                    json.dumps(event_payload),          # details (JSON)
                    current_time,                       # timestamp
                    current_time                        # created_at
                ))
                
                # Update device last_seen
                cursor.execute("""
                    UPDATE devices 
                    SET last_seen = %s, updated_at = %s 
                    WHERE serial_number = %s
                """, (current_time, current_time, serial_number))
                
                conn.commit()
                cursor.close()
                
                logging.info(f"✅ Event stored successfully: {event_kind} from {serial_number}")
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'message': 'Event stored successfully',
                        'event_id': f"{serial_number}_{int(current_time.timestamp())}",
                        'device_id': device_id,
                        'serial_number': serial_number,
                        'event_type': event_kind,
                        'severity': severity,
                        'stored_at': current_time.isoformat()
                    }),
                    status_code=201,
                    headers={'Content-Type': 'application/json'}
                )
                
        except Exception as db_error:
            logging.error(f"Database error storing event: {db_error}", exc_info=True)
            return func.HttpResponse(
                json.dumps({
                    'error': 'Database error',
                    'details': str(db_error)
                }),
                status_code=500,
                headers={'Content-Type': 'application/json'}
            )
            
    except Exception as e:
        logging.error(f'Error processing event submission: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Failed to process event submission',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )
