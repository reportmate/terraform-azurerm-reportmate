"""
GET /api/devices - Device Management Endpoints (Temporary Mock Version)
Lists all devices with comprehensive status information
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import azure.functions as func
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle device management requests:
    - GET /api/devices - List all devices
    - GET /api/devices/{id} - Get specific device details
    """
    
    logger.info("=== DEVICE MANAGEMENT REQUEST ===")
    
    try:
        # Extract route parameters
        device_id = req.route_params.get('id')
        method = req.method.upper()
        
        # Also check query parameters for device lookup
        device_id_param = req.params.get('device_id')
        serial_number_param = req.params.get('serial_number')
        
        # Use route param or query param
        lookup_id = device_id or device_id_param or serial_number_param
        
        logger.info(f"Method: {method}, Device ID: {lookup_id}")
        
        # Mock device data - only the actual reporting device
        mock_devices = [
            {
                "id": 1,
                "device_id": "bc8adf50-74b3-4a75-a29e-ff7cf5b0e4a8",
                "serial_number": "0F33V9G25083HJ",
                "name": "DESKTOP-RCHRISTIANSEN",
                "hostname": "DESKTOP-RCHRISTIANSEN",
                "os_name": "Microsoft Windows 11 Pro",
                "os_version": "10.0.22631",
                "client_version": "1.0.0",
                "status": "active",
                "last_seen": "2025-07-21T02:00:00Z",
                "created_at": "2025-07-20T10:00:00Z"
            }
        ]
        
        if method == 'GET':
            if lookup_id:
                # Get specific device
                return get_device_details(mock_devices, lookup_id)
            else:
                # List all devices
                return list_all_devices(mock_devices, req)
        else:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Method not allowed',
                    'details': f'Method {method} is not supported'
                }),
                status_code=405,
                mimetype="application/json"
            )
        
    except Exception as e:
        logger.error(f"Error in device management endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )


def list_all_devices(devices: List[Dict], req: func.HttpRequest) -> func.HttpResponse:
    """
    List all devices with pagination and filtering
    """
    
    try:
        # Get query parameters
        limit = int(req.params.get('limit', 50))
        offset = int(req.params.get('offset', 0))
        status_filter = req.params.get('status', '')
        search = req.params.get('search', '')
        
        logger.info(f"Listing devices: limit={limit}, offset={offset}, status={status_filter}, search={search}")
        
        # Apply filtering
        filtered_devices = devices
        
        if status_filter:
            filtered_devices = [d for d in filtered_devices if d['status'] == status_filter]
        
        if search:
            search_lower = search.lower()
            filtered_devices = [
                d for d in filtered_devices 
                if search_lower in d['name'].lower() or 
                   search_lower in d['serial_number'].lower() or
                   search_lower in d['hostname'].lower()
            ]
        
        # Apply pagination
        total_count = len(filtered_devices)
        paginated_devices = filtered_devices[offset:offset + limit]
        
        logger.info(f"Found {len(paginated_devices)} devices out of {total_count} total")
        
        return func.HttpResponse(
            json.dumps({
                'devices': paginated_devices,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                },
                'note': 'Using mock data until PostgreSQL driver issue is resolved'
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Failed to list devices',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )


def get_device_details(devices: List[Dict], device_id: str) -> func.HttpResponse:
    """
    Get detailed information for a specific device
    """
    
    try:
        logger.info(f"Getting details for device: {device_id}")
        
        # Find device by ID, device_id, or serial_number
        device = None
        for d in devices:
            if (str(d['id']) == device_id or 
                d['device_id'] == device_id or 
                d['serial_number'] == device_id):
                device = d
                break
        
        if not device:
            logger.warning(f"Device not found: {device_id}")
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device not found',
                    'details': f'No device found with ID: {device_id}'
                }),
                status_code=404,
                mimetype="application/json"
            )
        
        logger.info(f"Found device: {device['name']} ({device['serial_number']})")
        
        return func.HttpResponse(
            json.dumps({
                'success': True,
                'data': device,
                'note': 'Using mock data until PostgreSQL driver issue is resolved'
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error getting device details: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Failed to get device details',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
