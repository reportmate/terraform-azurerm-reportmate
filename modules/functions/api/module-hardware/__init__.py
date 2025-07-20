"""
GET /api/v1/devices/{id}/hardware - Device Hardware Module
Retrieves comprehensive hardware information for a specific device
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
    GET /api/v1/devices/{id}/hardware
    Retrieve hardware specifications for a specific device
    """
    
    logger.info("=== DEVICE HARDWARE REQUEST ===")
    
    try:
        # Extract device ID from route
        device_id = req.route_params.get('id')
        if not device_id:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device ID required',
                    'details': 'Device ID must be provided in the URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Fetching hardware for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device hardware data
        hardware_data = await get_device_hardware(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(hardware_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device hardware endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_hardware(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive hardware data for a specific device
    """
    
    try:
        # Get hardware data from database
        hardware = await db_manager.get_device_hardware(device_id)
        
        if not hardware:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No hardware data found for device {device_id}'
            }
        
        # Calculate hardware metrics and insights
        insights = calculate_hardware_insights(hardware)
        
        return {
            'success': True,
            'device_id': device_id,
            'hardware': {
                'processor': hardware.get('processor', 'Unknown'),
                'cores': hardware.get('cores'),
                'memory': hardware.get('memory', 'Unknown'),
                'memory_gb': hardware.get('memory_gb'),
                'storage': hardware.get('storage', 'Unknown'),
                'storage_type': hardware.get('storage_type', 'Unknown'),
                'graphics': hardware.get('graphics', 'Unknown'),
                'vram': hardware.get('vram'),
                'manufacturer': hardware.get('manufacturer', 'Unknown'),
                'model': hardware.get('model', 'Unknown'),
                'serial_number': hardware.get('serial_number', 'Unknown'),
                'bios_version': hardware.get('bios_version'),
                'motherboard': hardware.get('motherboard'),
                'chassis_type': hardware.get('chassis_type'),
                'form_factor': hardware.get('form_factor')
            },
            'performance': {
                'cpu_utilization': hardware.get('cpu_utilization'),
                'memory_utilization': hardware.get('memory_utilization'),
                'disk_utilization': hardware.get('disk_utilization'),
                'temperature': hardware.get('temperature'),
                'battery_level': hardware.get('battery_level')
            },
            'insights': insights,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device hardware: {e}")
        return {
            'success': False,
            'error': 'Failed to retrieve hardware data',
            'details': str(e)
        }

def calculate_hardware_insights(hardware: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate hardware insights and recommendations
    """
    
    insights = {
        'performance_score': 0,
        'recommendations': [],
        'warnings': [],
        'specifications': {}
    }
    
    # Memory analysis
    memory_gb = hardware.get('memory_gb', 0)
    if memory_gb:
        if memory_gb < 8:
            insights['warnings'].append('Low memory capacity - consider upgrading')
            insights['performance_score'] += 2
        elif memory_gb >= 16:
            insights['performance_score'] += 4
        else:
            insights['performance_score'] += 3
    
    # Storage analysis
    storage_type = hardware.get('storage_type', '').lower()
    if 'ssd' in storage_type:
        insights['performance_score'] += 3
        insights['specifications']['storage_type'] = 'SSD (Fast)'
    elif 'hdd' in storage_type:
        insights['recommendations'].append('Consider upgrading to SSD for better performance')
        insights['performance_score'] += 1
        insights['specifications']['storage_type'] = 'HDD (Traditional)'
    
    # CPU analysis
    cores = hardware.get('cores', 0)
    if cores:
        if cores >= 8:
            insights['performance_score'] += 4
        elif cores >= 4:
            insights['performance_score'] += 3
        else:
            insights['performance_score'] += 1
    
    # Performance monitoring
    cpu_util = hardware.get('cpu_utilization')
    if cpu_util and cpu_util > 90:
        insights['warnings'].append('High CPU utilization detected')
    
    memory_util = hardware.get('memory_utilization')
    if memory_util and memory_util > 90:
        insights['warnings'].append('High memory utilization detected')
    
    # Normalize performance score (0-10)
    insights['performance_score'] = min(10, insights['performance_score'])
    
    return insights
