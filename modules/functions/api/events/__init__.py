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
        
        # MINIMAL TEST: Just try to create database manager
        try:
            db_manager = SyncDatabaseManager()
            logging.info("✅ Successfully initialized database manager")
        except Exception as init_error:
            logging.error(f"❌ Database init failed: {init_error}")
            return func.HttpResponse(
                json.dumps({
                    'error': 'Database initialization failed',
                    'details': str(init_error)
                }),
                status_code=500,
                headers={'Content-Type': 'application/json'}
            )
        
        # Test connection
        try:
            connection_ok = db_manager.test_connection()
            logging.info(f"✅ Database connection test result: {connection_ok}")
        except Exception as conn_error:
            logging.error(f"❌ Database connection test failed: {conn_error}")
            return func.HttpResponse(
                json.dumps({
                    'error': 'Database connection test failed',
                    'details': str(conn_error)
                }),
                status_code=500,
                headers={'Content-Type': 'application/json'}
            )
        
        # If we got this far, try basic event processing
        try:
            storage_result = db_manager.store_event_data(unified_payload)
            logging.info(f"✅ Database storage completed with result: {storage_result}")
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Event processing completed',
                    'details': storage_result
                }),
                status_code=200,
                headers={'Content-Type': 'application/json'}
            )
            
        except Exception as storage_error:
            logging.error(f"❌ Database storage failed: {storage_error}")
            return func.HttpResponse(
                json.dumps({
                    'error': 'Database storage failed',
                    'details': str(storage_error)
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
