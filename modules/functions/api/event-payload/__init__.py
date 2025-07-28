"""
Event Payload API for ReportMate
Retrieves the full payload for a specific event by ID
"""
import azure.functions as func
import json
import logging
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.sync_database import SyncDatabaseManager

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Retrieve full payload for a specific event
    """
    logging.info('Event Payload API function processed a request')
    
    try:
        # Get event ID from URL parameter
        event_id = req.route_params.get('eventId')
        
        if not event_id:
            return func.HttpResponse(
                json.dumps({'error': 'Event ID is required'}),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        logging.info(f'Fetching payload for event ID: {event_id}')
        
        # Initialize database manager
        db_manager = SyncDatabaseManager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Query event by ID to get full payload
            query = """
                SELECT id, device_id, event_type, message, details, timestamp
                FROM events 
                WHERE id = %s
                LIMIT 1
            """
            cursor.execute(query, (event_id,))
            event_row = cursor.fetchone()
            
            if not event_row:
                return func.HttpResponse(
                    json.dumps({
                        'error': 'Event not found',
                        'eventId': event_id
                    }),
                    status_code=404,
                    headers={'Content-Type': 'application/json'}
                )
            
            # Parse the event data
            event_id_db, device_id, event_type, message, details, timestamp = event_row
            
            # Parse details if it's JSON string
            payload = details
            if details and isinstance(details, str):
                try:
                    payload = json.loads(details)
                except json.JSONDecodeError:
                    # Keep as string if not valid JSON
                    payload = details
            
            # If payload is minimal OR this is a system event, try to fetch from modular tables
            if (not payload or 
                (isinstance(payload, dict) and len(payload) < 10) or 
                event_type == 'system'):
                logging.info(f'Event {event_id} requires full payload reconstruction from device modules')
                
                # Try to find recent modular data for this device around the event timestamp
                # This gives us the full data that was likely associated with this event
                enriched_payload = get_enriched_payload_from_modules(cursor, device_id, timestamp)
                if enriched_payload:
                    payload = enriched_payload
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'eventId': event_id,
                    'payload': payload,
                    'event': {
                        'id': event_id_db,
                        'device': device_id,
                        'kind': event_type,
                        'message': message,
                        'timestamp': timestamp.isoformat() if timestamp else None
                    }
                }),
                status_code=200,
                headers={'Content-Type': 'application/json'}
            )
            
    except Exception as e:
        logging.error(f'Error retrieving event payload: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'error': 'Failed to retrieve event payload',
                'details': str(e)
            }),
            status_code=500,
            headers={'Content-Type': 'application/json'}
        )


def get_enriched_payload_from_modules(cursor, device_id, event_timestamp):
    """
    Attempt to reconstruct full payload by fetching recent modular data for the device
    """
    try:
        logging.info(f"Attempting to reconstruct payload for device {device_id} at {event_timestamp}")
        
        # Define modules to check
        modules = ['inventory', 'system', 'hardware', 'network', 'security', 'applications', 'displays', 'management']
        
        enriched_payload = {}
        modules_found = 0
        
        # For each module, get the most recent data around the event timestamp
        for module in modules:
            try:
                # Query for data collected within 36 hours of the event timestamp
                # Use device_id directly as it should be the serial number in the events table
                query = f"""
                    SELECT data FROM {module}
                    WHERE device_id = %s 
                    AND collected_at BETWEEN (%s::timestamp - interval '36 hours') AND (%s::timestamp + interval '36 hours')
                    ORDER BY collected_at DESC
                    LIMIT 1
                """
                
                logging.info(f"Querying {module} table for device {device_id}")
                cursor.execute(query, (device_id, event_timestamp, event_timestamp))
                module_row = cursor.fetchone()
                
                if module_row and module_row[0]:
                    module_data = module_row[0]
                    if isinstance(module_data, str):
                        try:
                            module_data = json.loads(module_data)
                        except json.JSONDecodeError:
                            pass
                    enriched_payload[module] = module_data
                    modules_found += 1
                    logging.info(f"  ✅ Found {module} data for device {device_id}")
                else:
                    logging.info(f"  ❌ No {module} data found for device {device_id}")
                    
            except Exception as module_error:
                logging.warning(f'Could not fetch {module} data: {str(module_error)}')
                continue
        
        if enriched_payload:
            logging.info(f"Successfully reconstructed payload with {len(enriched_payload)} modules: {list(enriched_payload.keys())}")
            # Add metadata to indicate this is reconstructed
            enriched_payload['_metadata'] = {
                'source': 'reconstructed_from_modules',
                'device_id': device_id,
                'event_timestamp': event_timestamp.isoformat() if event_timestamp else None,
                'modules_found': list(enriched_payload.keys()),
                'modules_processed': modules_found
            }
            
            return enriched_payload
        else:
            logging.warning(f"No module data found for device {device_id}")
            
    except Exception as e:
        logging.warning(f'Failed to enrich payload from modules: {str(e)}')
        return None
    
    return None
