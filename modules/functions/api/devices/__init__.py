"""
Devices List Endpoint for ReportMate
Handles listing all devices and device search/filtering
"""
import logging
import json
import asyncio
import azure.functions as func
import os
import sys
from datetime import datetime, timezone, timedelta

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import AsyncDatabaseManager
from shared.utils import calculate_device_status

logger = logging.getLogger(__name__)

async def list_devices_async():
    """List devices using async database connection"""
    try:
        db_manager = AsyncDatabaseManager()
        
        # Query to get devices with names from inventory data and recent events
        query = """
            SELECT 
                d.device_id as id,
                COALESCE(
                    (i.data->>'deviceName')::text,
                    (i.data->>'device_name')::text,
                    d.serial_number,
                    'Unknown Device'
                ) as name,
                d.serial_number,
                d.os_version as os,
                d.last_seen,
                d.created_at,
                -- Get inventory data for filtering
                i.data as inventory_data
            FROM devices d
            LEFT JOIN inventory i ON d.serial_number = i.device_id
            ORDER BY d.last_seen DESC NULLS LAST
            LIMIT 50
        """
        
        devices_raw = await db_manager.execute_query(query)
        
        devices = []
        for row in devices_raw:
            # Get recent events for this device (last 24 hours)
            events_query = """
                SELECT event_type, created_at
                FROM events 
                WHERE device_id = (SELECT id FROM devices WHERE device_id = %s)
                AND created_at >= NOW() - INTERVAL '24 hours'
                AND event_type IN ('warning', 'error')
                ORDER BY created_at DESC
                LIMIT 10
            """
            recent_events = await db_manager.execute_query(events_query, (row['id'],))
            
            # Calculate dynamic status based on last_seen and recent events
            calculated_status = calculate_device_status(row['last_seen'], recent_events)
            
            # Extract inventory data for additional fields
            inventory_data = row.get('inventory_data', {}) or {}
            
            device = {
                'deviceId': row['id'],
                'serialNumber': row['serial_number'],
                'name': row['name'],  # Now comes from inventory.deviceName with fallback to serial_number
                'os': row['os'],
                'status': calculated_status,  # Now dynamically calculated with events!
                'lastSeen': row['last_seen'].isoformat() if row['last_seen'] else None,
                'totalEvents': 0,  # TODO: Calculate from events table
                'lastEventTime': row['last_seen'].isoformat() if row['last_seen'] else None,
                'modules': {
                    'inventory': {
                        'assetTag': inventory_data.get('assetTag'),
                        'deviceName': inventory_data.get('deviceName'),
                        'location': inventory_data.get('location'),
                        'usage': inventory_data.get('usage'),
                        'catalog': inventory_data.get('catalog')
                    }
                } if inventory_data else {}
            }
            devices.append(device)
        
        return {
            'success': True,
            'data': devices,
            'count': len(devices)
        }
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Devices list endpoint using async database
    """
    
    try:
        # Run async function
        result = asyncio.run(list_devices_async())

        if result['success']:
            return func.HttpResponse(
                json.dumps(result['data'], indent=2),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps(result, indent=2),
                status_code=500,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Error in devices endpoint: {e}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )
