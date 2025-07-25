"""
Device-specific Events Endpoint for ReportMate
Handles retrieving historical events for a specific device
"""
import logging
import json
import azure.functions as func
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.sync_database import SyncDatabaseManager

logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Device-specific events endpoint
    URL format: /api/device/{serial_number}/events
    """
    
    logger.info("=== REPORTMATE DEVICE EVENTS API ===")
    logger.info(f"Method: {req.method}")
    logger.info(f"URL: {req.url}")
    
    if req.method != 'GET':
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {req.method} not supported. Only GET is allowed.'
            }),
            status_code=405,
            mimetype="application/json"
        )
    
    try:
        # Get serial number from route parameter
        serial_number = req.route_params.get('serial_number')
        
        if not serial_number:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Missing serial number',
                    'details': 'Device serial number is required in the URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get query parameters for pagination and filtering
        limit = req.params.get('limit', '50')
        offset = req.params.get('offset', '0')
        kind = req.params.get('kind')  # Optional event type filter
        
        try:
            limit = int(limit)
            if limit > 1000:
                limit = 1000
        except ValueError:
            limit = 50
            
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
        
        logger.info(f"Retrieving events for device: {serial_number}")
        logger.info(f"Limit: {limit}, Offset: {offset}, Kind filter: {kind}")
        
        # Initialize database manager
        db_manager = SyncDatabaseManager()
        
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # First verify the device exists
                device_check_query = """
                    SELECT id, name FROM devices 
                    WHERE serial_number = %s OR id = %s
                    LIMIT 1
                """
                cursor.execute(device_check_query, (serial_number, serial_number))
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
                
                device_id = device_result[0]
                device_name = device_result[1]
                
                # Build the events query with optional filtering
                events_query = """
                    SELECT id, device_id, kind, source, payload, severity, ts
                    FROM events 
                    WHERE device_id = %s
                """
                query_params = [device_id]
                
                # Add kind filter if specified
                if kind:
                    events_query += " AND kind = %s"
                    query_params.append(kind)
                
                # Add ordering and pagination
                events_query += " ORDER BY ts DESC LIMIT %s OFFSET %s"
                query_params.extend([limit, offset])
                
                cursor.execute(events_query, query_params)
                events = cursor.fetchall()
                
                # Get total count for pagination info
                count_query = """
                    SELECT COUNT(*) FROM events WHERE device_id = %s
                """
                count_params = [device_id]
                
                if kind:
                    count_query += " AND kind = %s"
                    count_params.append(kind)
                
                cursor.execute(count_query, count_params)
                total_count = cursor.fetchone()[0]
                
                cursor.close()
                
                # Format events for response
                formatted_events = []
                for event in events:
                    event_data = {
                        'id': event[0],
                        'device_id': event[1],
                        'kind': event[2],
                        'source': event[3],
                        'severity': event[5] or 'info',
                        'timestamp': event[6].isoformat() if event[6] else None,
                        'payload': {}
                    }
                    
                    # Parse payload JSON
                    if event[4]:
                        try:
                            event_data['payload'] = json.loads(event[4]) if isinstance(event[4], str) else event[4]
                        except json.JSONDecodeError:
                            event_data['payload'] = {'raw': str(event[4])}
                    
                    formatted_events.append(event_data)
                
                logger.info(f"Successfully retrieved {len(formatted_events)} events for device {serial_number}")
                
                return func.HttpResponse(
                    json.dumps({
                        'success': True,
                        'device': {
                            'id': device_id,
                            'serial_number': serial_number,
                            'name': device_name
                        },
                        'events': formatted_events,
                        'pagination': {
                            'limit': limit,
                            'offset': offset,
                            'count': len(formatted_events),
                            'total': total_count,
                            'has_more': (offset + len(formatted_events)) < total_count
                        },
                        'filters': {
                            'kind': kind
                        }
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
                
        except Exception as db_error:
            logger.error(f"Database error retrieving events for device {serial_number}: {db_error}")
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
        logger.error(f"Error retrieving device events: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
