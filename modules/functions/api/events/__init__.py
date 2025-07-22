import azure.functions as func
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import sys
import asyncio

# Add the shared directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from database import DatabaseManager

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function for handling device events
    
    GET /api/events - Retrieve events with optional filtering
    POST /api/events - Store a new event
    """
    logging.info(f'Events API function processed a request: {req.method}')
    
    try:
        # Check authentication
        api_passphrase = req.headers.get('X-API-PASSPHRASE')
        expected_passphrase = os.environ.get('API_PASSPHRASE', 's3cur3-p@ssphras3!')
        
        if api_passphrase != expected_passphrase:
            logging.warning(f'Invalid API passphrase provided')
            return func.HttpResponse(
                json.dumps({'error': 'Invalid API passphrase'}),
                status_code=401,
                headers={'Content-Type': 'application/json'}
            )

        # Initialize database connection
        db_manager = DatabaseManager()
        
        if req.method == 'GET':
            return await handle_get_events(req, db_manager)
        elif req.method == 'POST':
            return await handle_post_event(req, db_manager)
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

async def handle_get_events(req: func.HttpRequest, db_manager: DatabaseManager) -> func.HttpResponse:
    """Handle GET requests for retrieving events"""
    try:
        # Parse query parameters
        device_id = req.params.get('device_id')
        event_type = req.params.get('event_type')
        limit = int(req.params.get('limit', 100))
        offset = int(req.params.get('offset', 0))
        
        # Limit the maximum number of events to prevent abuse
        limit = min(limit, 1000)
        
        # Build the query
        where_conditions = []
        params = []
        
        if device_id:
            where_conditions.append('device_id = $' + str(len(params) + 1))
            params.append(device_id)
            
        if event_type:
            where_conditions.append('event_type = $' + str(len(params) + 1))
            params.append(event_type)
        
        where_clause = ''
        if where_conditions:
            where_clause = 'WHERE ' + ' AND '.join(where_conditions)
        
        # Query events from device_events table
        query = f"""
            SELECT 
                id,
                device_id,
                event_type as kind,
                event_source,
                event_data as payload,
                severity,
                created_at as ts
            FROM device_events 
            {where_clause}
            ORDER BY created_at DESC 
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        
        params.extend([limit, offset])
        
        events = await db_manager.fetch_all(query, params)
        
        # Transform events to match expected format
        transformed_events = []
        for event in events:
            transformed_event = {
                'id': str(event['id']),
                'device': event['device_id'],
                'kind': event['kind'] or 'info',
                'ts': event['ts'].isoformat() if event['ts'] else datetime.now(timezone.utc).isoformat(),
                'payload': event['payload'] or {}
            }
            
            # Add event source if available
            if event.get('event_source'):
                transformed_event['source'] = event['event_source']
                
            # Add severity if available
            if event.get('severity'):
                transformed_event['severity'] = event['severity']
                
            transformed_events.append(transformed_event)
        
        logging.info(f'Retrieved {len(transformed_events)} events')
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'events': transformed_events,
                'count': len(transformed_events),
                'limit': limit,
                'offset': offset,
                'timestamp': datetime.now(timezone.utc).isoformat()
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

async def handle_post_event(req: func.HttpRequest, db_manager: DatabaseManager) -> func.HttpResponse:
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
        
        # Extract event fields with fallbacks
        device_id = event_data.get('device') or event_data.get('device_id') or event_data.get('Device')
        event_type = event_data.get('kind') or event_data.get('event_type') or event_data.get('Kind') or 'info'
        event_source = event_data.get('source') or event_data.get('event_source') or 'api'
        payload = event_data.get('payload') or event_data.get('Payload') or {}
        severity = event_data.get('severity') or 'info'
        
        if not device_id:
            return func.HttpResponse(
                json.dumps({'error': 'Device ID is required'}),
                status_code=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # Store the event
        insert_query = """
            INSERT INTO device_events (device_id, event_type, event_source, event_data, severity, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at
        """
        
        result = await db_manager.fetch_one(
            insert_query, 
            [device_id, event_type, event_source, json.dumps(payload), severity, datetime.now(timezone.utc)]
        )
        
        if result:
            logging.info(f'Stored event {result["id"]} for device {device_id}')
            
            return func.HttpResponse(
                json.dumps({
                    'success': True,
                    'message': 'Event stored successfully',
                    'event_id': str(result['id']),
                    'timestamp': result['created_at'].isoformat()
                }),
                status_code=201,
                headers={'Content-Type': 'application/json'}
            )
        else:
            raise Exception('Failed to store event - no result returned')
            
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
