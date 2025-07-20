"""
GET /api/v1/devices/{id}/system - Device System Module
Retrieves comprehensive system information for a specific device
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
    GET /api/v1/devices/{id}/system
    Retrieve system information for a specific device
    """
    
    logger.info("=== DEVICE SYSTEM REQUEST ===")
    
    try:
        # Extract device ID from route
        device_id = req.route_params.get('id')
        if not device_id:
            return func.HttpResponse(
                json.dumps({
                    'success': False,
                    'error': 'Device ID required',
                    'details': 'Device ID must be provided in URL path'
                }),
                status_code=400,
                mimetype="application/json"
            )
        
        logger.info(f"Fetching system data for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device system data
        system_data = await get_device_system(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(system_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device system endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_system(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive system data for a specific device
    """
    
    try:
        # Get system data from database
        system = await db_manager.get_device_system(device_id)
        
        if not system:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No system data found for device {device_id}'
            }
        
        # Calculate system insights and health metrics
        insights = calculate_system_insights(system)
        
        return {
            'success': True,
            'device_id': device_id,
            'system_data': system,
            'insights': insights,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device system data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

def calculate_system_insights(system: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate system insights and health metrics
    """
    
    insights = {
        'health_score': 0,
        'performance_metrics': {},
        'recommendations': [],
        'warnings': [],
        'system_summary': {}
    }
    
    # Basic system information
    insights['system_summary'] = {
        'os_name': system.get('os_name', 'Unknown'),
        'os_version': system.get('os_version', 'Unknown'),
        'kernel_version': system.get('kernel_version', 'Unknown'),
        'architecture': system.get('architecture', 'Unknown'),
        'uptime_hours': system.get('uptime', 0) / 3600 if system.get('uptime') else 0
    }
    
    # Health score calculation
    health_score = 100
    
    # Check OS version currency
    os_version = system.get('os_version', '')
    if 'Windows 11' in os_version or 'Windows 10' in os_version:
        insights['recommendations'].append("Modern Windows version detected")
    elif 'Windows' in os_version:
        health_score -= 20
        insights['warnings'].append("Older Windows version detected - consider upgrading")
    
    # Check uptime
    uptime_hours = insights['system_summary']['uptime_hours']
    if uptime_hours > 720:  # 30 days
        health_score -= 10
        insights['warnings'].append("High uptime detected - consider restarting for updates")
    elif uptime_hours > 168:  # 7 days
        insights['recommendations'].append("Regular uptime detected")
    
    # Performance metrics
    insights['performance_metrics'] = {
        'uptime_days': round(uptime_hours / 24, 1),
        'last_boot': system.get('last_boot', ''),
        'cpu_load': system.get('cpu_load_avg', 0),
        'memory_pressure': system.get('memory_pressure', 0)
    }
    
    # Check for critical issues
    if system.get('disk_full', False):
        health_score -= 30
        insights['warnings'].append("Disk space critical")
    
    if system.get('memory_pressure', 0) > 80:
        health_score -= 15
        insights['warnings'].append("High memory usage detected")
    
    insights['health_score'] = max(0, health_score)
    
    return insights
