"""
GET /api/v1/devices/{id}/applications - Device Applications Module
Retrieves comprehensive application inventory for a specific device
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
    GET /api/v1/devices/{id}/applications
    Retrieve application inventory for a specific device
    """
    
    logger.info("=== DEVICE APPLICATIONS REQUEST ===")
    
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
        
        logger.info(f"Fetching applications for device: {device_id}")
        
        # Get query parameters
        limit = int(req.params.get('limit', 50))
        offset = int(req.params.get('offset', 0))
        search = req.params.get('search', '')
        category = req.params.get('category', '')
        
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Get device applications
        applications_data = await get_device_applications(
            db_manager, device_id, limit, offset, search, category
        )
        
        return func.HttpResponse(
            json.dumps(applications_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error in device applications endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )

async def get_device_applications(
    db_manager: DatabaseManager, 
    device_id: str, 
    limit: int, 
    offset: int,
    search: str = '',
    category: str = ''
) -> Dict[str, Any]:
    """
    Retrieve applications data for a specific device with filtering and pagination
    """
    
    try:
        # Get applications data from database
        applications = await db_manager.get_device_applications(
            device_id, limit, offset, search, category
        )
        
        # Get total count for pagination
        total_count = await db_manager.get_device_applications_count(
            device_id, search, category
        )
        
        # Calculate application statistics
        stats = await calculate_application_stats(applications)
        
        return {
            'success': True,
            'device_id': device_id,
            'applications': applications,
            'stats': stats,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_count,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'search': search,
                'category': category
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device applications: {e}")
        return {
            'success': False,
            'error': 'Failed to retrieve applications',
            'details': str(e)
        }

async def calculate_application_stats(applications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate application statistics for the device
    """
    
    total_apps = len(applications)
    categories = {}
    publishers = {}
    
    for app in applications:
        # Count by category
        category = app.get('category', 'Unknown')
        categories[category] = categories.get(category, 0) + 1
        
        # Count by publisher
        publisher = app.get('publisher', 'Unknown')
        publishers[publisher] = publishers.get(publisher, 0) + 1
    
    return {
        'total_applications': total_apps,
        'categories': dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
        'top_publishers': dict(sorted(publishers.items(), key=lambda x: x[1], reverse=True)[:10]),
        'last_updated': datetime.utcnow().isoformat() + 'Z'
    }
