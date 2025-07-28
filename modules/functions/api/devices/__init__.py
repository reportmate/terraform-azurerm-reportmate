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

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.async_database import AsyncDatabaseManager

logger = logging.getLogger(__name__)

async def list_devices_async():
    """List devices using async database connection"""
    try:
        db_manager = AsyncDatabaseManager()
        
        # Query to get devices with names from inventory data
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
                'active' as status,
                d.last_seen,
                d.created_at
            FROM devices d
            LEFT JOIN inventory i ON d.serial_number = i.device_id
            ORDER BY d.last_seen DESC NULLS LAST
            LIMIT 50
        """
        
        devices_raw = await db_manager.execute_query(query)
        
        devices = []
        for row in devices_raw:
            device = {
                'id': row['id'],
                'name': row['name'],  # Now comes from inventory.deviceName with fallback to serial_number
                'serial_number': row['serial_number'],
                'os': row['os'],
                'status': row['status'],
                'last_seen': row['last_seen'].isoformat() if row['last_seen'] else None,
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
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
