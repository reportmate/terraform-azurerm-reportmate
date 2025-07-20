"""
GET /api/v1/devices - Device Management Endpoints
Lists all devices with comprehensive status information
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import azure.functions as func
import os
import sys

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import DatabaseManager
from shared.auth import AuthenticationManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle device management requests:
    - GET /api/v1/devices - List all devices
    - GET /api/v1/devices/{id} - Get specific device details
    """
    
    logger.info("=== DEVICE MANAGEMENT REQUEST ===")
    
    try:
        # Extract route parameters
        device_id = req.route_params.get('id')
        method = req.method.upper()
        
        logger.info(f"Method: {method}, Device ID: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        if method == 'GET':
            if device_id:
                # Get specific device
                return await get_device_details(db_manager, device_id)
            else:
                # List all devices
                return await list_all_devices(db_manager, req)
        
        # Method not allowed
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Method not allowed',
                'details': f'Method {method} is not supported for this endpoint'
            }),
            status_code=405,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in devices endpoint: {e}", exc_info=True)
        
        error_response = {
            'success': False,
            'error': 'Internal server error',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )

async def list_all_devices(db_manager: DatabaseManager, req: func.HttpRequest) -> func.HttpResponse:
    """
    List all devices with pagination and filtering
    """
    
    try:
        # Parse query parameters
        params = req.params
        limit = int(params.get('limit', '50'))
        offset = int(params.get('offset', '0'))
        machine_group = params.get('machine_group')
        business_unit = params.get('business_unit')
        status = params.get('status')
        
        logger.info(f"Listing devices: limit={limit}, offset={offset}")
        
        # Get devices from database
        devices = await db_manager.get_devices(
            limit=limit,
            offset=offset,
            machine_group=machine_group,
            business_unit=business_unit,
            status=status
        )
        
        # Get total count for pagination
        total_count = await db_manager.get_devices_count(
            machine_group=machine_group,
            business_unit=business_unit,
            status=status
        )
        
        logger.info(f"Found {len(devices)} devices (total: {total_count})")
        
        response_data = {
            'success': True,
            'devices': devices,
            'count': len(devices),
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json",
            headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate',
                'Pragma': 'no-cache'
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        
        error_response = {
            'success': False,
            'error': 'Failed to retrieve devices',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_details(db_manager: DatabaseManager, device_id: str) -> func.HttpResponse:
    """
    Get detailed information for a specific device
    """
    
    try:
        logger.info(f"Getting details for device: {device_id}")
        
        # Get device record
        device = await db_manager.get_device(device_id)
        
        if not device:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device not found',
                    'details': f'No device found with ID: {device_id}'
                }),
                status_code=404,
                mimetype="application/json"
            )
        
        # Get latest module data for the device
        modules_data = await db_manager.get_device_modules_data(device_id)
        
        # Combine device info with module data
        device_details = {
            'device': device,
            'modules': modules_data,
            'last_updated': device.get('last_seen'),
            'available_modules': list(modules_data.keys()) if modules_data else []
        }
        
        logger.info(f"Retrieved device details with {len(modules_data)} modules")
        
        response_data = {
            'success': True,
            'device': device_details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json",
            headers={
                'Cache-Control': 'no-store, no-cache, must-revalidate',
                'Pragma': 'no-cache'
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting device details: {e}", exc_info=True)
        
        error_response = {
            'success': False,
            'error': 'Failed to retrieve device details',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )