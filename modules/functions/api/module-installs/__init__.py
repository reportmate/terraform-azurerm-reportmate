"""
GET /api/v1/devices/{id}/installs - Device Installs Module
Retrieves managed installations (Munki, Cimian, etc.) for a specific device
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
    GET /api/v1/devices/{id}/installs
    Retrieve managed installations for a specific device
    """
    
    logger.info("=== DEVICE INSTALLS REQUEST ===")
    
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
        
        logger.info(f"Fetching installs data for device: {device_id}")
        
        # Get query parameters
        limit = int(req.params.get('limit', 50))
        offset = int(req.params.get('offset', 0))
        status_filter = req.params.get('status', '')
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device installs data
        installs_data = await get_device_installs(db_manager, device_id, limit, offset, status_filter)
        
        return func.HttpResponse(
            json.dumps(installs_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device installs endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_installs(db_manager: DatabaseManager, device_id: str, limit: int, offset: int, status_filter: str = '') -> Dict[str, Any]:
    """
    Retrieve comprehensive installs data for a specific device
    """
    
    try:
        # Get installs data from database
        installs = await db_manager.get_device_installs(device_id, limit, offset, status_filter)
        
        # Get total count for pagination
        total_count = await db_manager.get_device_installs_count(device_id, status_filter)
        
        if not installs:
            installs = []
        
        # Calculate installation statistics
        stats = calculate_install_statistics(installs)
        
        return {
            'success': True,
            'device_id': device_id,
            'installs': installs,
            'count': len(installs),
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'statistics': stats,
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device installs data: {e}")
        return {
            'success': False,
            'error': 'Database error',
            'details': str(e)
        }

def calculate_install_statistics(installs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate installation statistics and health metrics
    """
    
    stats = {
        'total_installs': len(installs),
        'by_status': {},
        'by_type': {},
        'by_source': {},
        'health_metrics': {},
        'recent_activity': {},
        'recommendations': [],
        'warnings': []
    }
    
    if not installs:
        return stats
    
    # Status breakdown
    status_counts = {}
    type_counts = {}
    source_counts = {}
    
    for install in installs:
        status = install.get('status', 'unknown')
        install_type = install.get('type', 'unknown')
        source = install.get('source', 'unknown')
        
        status_counts[status] = status_counts.get(status, 0) + 1
        type_counts[install_type] = type_counts.get(install_type, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
    
    stats['by_status'] = status_counts
    stats['by_type'] = type_counts
    stats['by_source'] = source_counts
    
    # Health metrics
    failed_installs = status_counts.get('failed', 0)
    pending_installs = status_counts.get('pending', 0)
    successful_installs = status_counts.get('installed', 0) + status_counts.get('success', 0)
    
    if stats['total_installs'] > 0:
        success_rate = (successful_installs / stats['total_installs']) * 100
        failure_rate = (failed_installs / stats['total_installs']) * 100
    else:
        success_rate = 0
        failure_rate = 0
    
    stats['health_metrics'] = {
        'success_rate': round(success_rate, 1),
        'failure_rate': round(failure_rate, 1),
        'pending_count': pending_installs,
        'failed_count': failed_installs,
        'successful_count': successful_installs
    }
    
    # Recent activity (last 7 days)
    recent_installs = []
    seven_days_ago = datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)
    
    for install in installs:
        install_date = install.get('install_date')
        if install_date:
            try:
                install_timestamp = datetime.fromisoformat(install_date.replace('Z', '+00:00')).timestamp()
                if install_timestamp > seven_days_ago:
                    recent_installs.append(install)
            except:
                pass
    
    stats['recent_activity'] = {
        'installs_last_7_days': len(recent_installs),
        'avg_installs_per_day': round(len(recent_installs) / 7, 1)
    }
    
    # Generate recommendations and warnings
    if failure_rate > 20:
        stats['warnings'].append(f"High failure rate: {failure_rate}% of installations failed")
    elif failure_rate > 10:
        stats['warnings'].append(f"Moderate failure rate: {failure_rate}% of installations failed")
    
    if pending_installs > 5:
        stats['warnings'].append(f"{pending_installs} installations are pending")
    
    if success_rate > 90:
        stats['recommendations'].append("Excellent installation success rate")
    elif success_rate > 75:
        stats['recommendations'].append("Good installation success rate")
    else:
        stats['recommendations'].append("Installation success rate needs improvement")
    
    # Management system recommendations
    if 'munki' in source_counts:
        stats['recommendations'].append("Munki managed software detected")
    
    if 'manual' in source_counts and source_counts['manual'] > stats['total_installs'] * 0.3:
        stats['recommendations'].append("Consider using managed installation tools for more manual installations")
    
    return stats
