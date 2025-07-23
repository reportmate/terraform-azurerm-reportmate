import azure.functions as func
import json
import logging
from datetime import datetime, timezone

# Simple in-memory storage for events (for testing only)
EVENTS_STORE = []

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Simple events API without database - stores events in memory for testing
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
    """Handle GET requests for retrieving events"""
    try:
        # Return stored events
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'events': EVENTS_STORE,
                'count': len(EVENTS_STORE),
                'message': 'In-memory storage (testing only)'
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
    """Handle POST requests for storing new events"""
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
        
        logging.info(f"Received event data: {json.dumps(event_data, indent=2)}")
        
        # Extract event fields
        device_id = event_data.get('deviceId') or event_data.get('device') or event_data.get('device_id') or 'unknown-device'
        event_type = event_data.get('kind') or event_data.get('event_type') or 'device-report'
        
        # Create event record
        event_record = {
            'id': len(EVENTS_STORE) + 1,
            'device_id': device_id,
            'kind': event_type,
            'payload': event_data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'received_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Store in memory
        EVENTS_STORE.append(event_record)
        
        logging.info(f'Stored event {event_record["id"]} for device {device_id}')
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'message': 'Event stored successfully (in-memory)',
                'event_id': str(event_record['id']),
                'device_id': device_id,
                'stored_events_count': len(EVENTS_STORE)
            }),
            status_code=201,
            headers={'Content-Type': 'application/json'}
        )
            
    except Exception as e:
        logging.error(f'Error storing event: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Failed to store event',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )
