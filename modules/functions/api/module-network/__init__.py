"""
GET /api/v1/devices/{id}/network - Device Network Module
Retrieves comprehensive network configuration for a specific device
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
    GET /api/v1/devices/{id}/network
    Retrieve network configuration for a specific device
    """
    
    logger.info("=== DEVICE NETWORK REQUEST ===")
    
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
        
        logger.info(f"Fetching network data for device: {device_id}")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device network data
        network_data = await get_device_network(db_manager, device_id)
        
        return func.HttpResponse(
            json.dumps(network_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device network endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_network(db_manager: DatabaseManager, device_id: str) -> Dict[str, Any]:
    """
    Retrieve comprehensive network data for a specific device
    """
    
    try:
        # Get network data from database
        network = await db_manager.get_device_network(device_id)
        
        if not network:
            return {
                'success': False,
                'error': 'Device not found',
                'details': f'No network data found for device {device_id}'
            }
        
        # Calculate network insights and analysis
        insights = calculate_network_insights(network)
        
        return {
            'success': True,
            'device_id': device_id,
            'network_data': network,
            'insights': insights,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device network data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

def calculate_network_insights(network: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate network insights and recommendations
    """
    
    insights = {
        'connectivity_score': 0,
        'security_score': 0,
        'performance_metrics': {},
        'recommendations': [],
        'warnings': [],
        'interfaces_summary': {}
    }
    
    interfaces = network.get('interfaces', [])
    active_interfaces = [iface for iface in interfaces if iface.get('status') == 'up']
    
    insights['interfaces_summary'] = {
        'total_interfaces': len(interfaces),
        'active_interfaces': len(active_interfaces),
        'wireless_interfaces': len([i for i in interfaces if 'wifi' in i.get('type', '').lower()]),
        'ethernet_interfaces': len([i for i in interfaces if 'ethernet' in i.get('type', '').lower()])
    }
    
    # Connectivity analysis
    if active_interfaces:
        insights['connectivity_score'] = min(100, len(active_interfaces) * 25)
        insights['recommendations'].append("Active network connectivity detected")
    else:
        insights['warnings'].append("No active network interfaces detected")
    
    # Security analysis
    if any(iface.get('encryption') for iface in interfaces):
        insights['security_score'] += 50
        insights['recommendations'].append("Encrypted network connections found")
    
    # Performance metrics
    total_bandwidth = sum(iface.get('speed', 0) for iface in active_interfaces)
    insights['performance_metrics'] = {
        'total_bandwidth_mbps': total_bandwidth,
        'average_latency_ms': network.get('latency', 0),
        'packet_loss_percent': network.get('packet_loss', 0)
    }
    
    return insights
